"""Service-lifetime resource owner; permission and lease logic lives in C0.

The Kubernetes client is imported inside the methods that touch the API: the
configuration parser stays importable (and testable) without it, and the local
`ops/vnext/kubernetes/` directory can never shadow the installed package.
"""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from deployment_common import token
from pod_task_config import entry_service_names, start_eligible_task_ids, task_entries
from wuji_core.execution.pod_runtime import PodReceiverRegistration, VNextPodRuntime
from wuji_core.persistence.uow import DomainError
from wuji_task_runtime.kubernetes_client import KubernetesPodClient
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig


class TrustedConfigFile:
    """Read a mounted ConfigMap projection without exposing its contents."""

    def __init__(self, path="/config/deployment.json", *, max_bytes=1 << 20):
        path = Path(path)
        if not path.is_absolute() or type(max_bytes) is not int or not 1 <= max_bytes <= 16 << 20:
            raise ValueError("bounded absolute ConfigMap path required")
        self.path, self.max_bytes = path, max_bytes
        self._digest = None

    def read_json(self):
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(self.max_bytes + 1)
        except OSError as error:
            raise DomainError("RUNTIME_CONFIG_UNAVAILABLE", 503) from error
        if not 0 < len(raw) <= self.max_bytes:
            raise DomainError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        digest = sha256(raw).hexdigest()
        if digest == self._digest:
            return None
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as error:
            raise DomainError("RUNTIME_CONFIG_UNAVAILABLE", 503) from error
        self._digest = digest
        return value


class PodEnvironment:
    """Every configured Task Pod, ensured independently.

    One Task whose Pod is not ready must not stop another Task's new starts, and
    it must never stop reconciliation of existing Runs: the loop restricts only
    new deliveries to the Tasks that reported `ready`.
    """

    def __init__(self, deployment, config):
        self.deployment, self.config = deployment, config
        self.runtimes: dict[str, VNextPodRuntime] = {}
        self._entries: dict[str, tuple[dict, dict]] = {}
        self.connections: dict[str, object] = {}
        self.observations: dict[str, object] = {}
        self.failures: dict[str, str] = {}
        self.service_names = config.get("service_names", {"agent": "task-agent", "kali": "task-kali"})
        self.entry_service_names = {}
        for item in config.get("tasks") or []:
            if not isinstance(item, dict):
                continue
            values = item.get("task_config")
            task_id = values.get("task_id") if isinstance(values, dict) else None
            if isinstance(task_id, str) and task_id:
                self.entry_service_names[task_id] = entry_service_names(
                    item, self.service_names
                )
        self.connection = self.api = None
        self._config_file = None

    @staticmethod
    def _normalise(values):
        values = deepcopy(values)
        for role in ("agent", "kali"):
            values[role + "_resources"] = ContainerResources(**values[role + "_resources"])
        return values

    def _add_entry(self, task_id, values, receiver, entry):
        if values.get("namespace") != "wuji-vnext-test" or values.get("expose_pod_identity") is not True:
            raise ValueError("isolated namespace and real Downward API identity required")
        if values.get("task_id") != task_id or not isinstance(receiver, dict):
            raise ValueError("Task entry identity is invalid")
        values = self._normalise(values)
        config = TaskRuntimeConfig(**values)
        connection = self.deployment.connect()
        try:
            runtime = VNextPodRuntime(
                config,
                connection=connection,
                access=self.deployment.access(),
                control=self.deployment.control,
                pods=self._pods,
                receiver=PodReceiverRegistration(**receiver),
            )
            runtime.__enter__()
        except BaseException:
            connection.close()
            raise
        self.connections[task_id] = connection
        self.runtimes[task_id] = runtime
        self._entries[task_id] = (values, deepcopy(receiver))
        self.entry_service_names[task_id] = entry_service_names(
            entry, self.service_names
        )

    def refresh(self, config):
        """Incrementally add Tasks or advance a stopped Task by one attempt.

        The ConfigMap projection is append/replace-only.  Removing a known Task,
        changing a fixed binding in place, or skipping an attempt is refused;
        the existing runtime objects remain untouched on refusal.
        """

        entries = task_entries(config)
        incoming = {}
        if config.get("tasks"):
            for task_id, values, receiver in entries:
                item = next(
                    item for item in config["tasks"]
                    if item.get("task_config", {}).get("task_id") == task_id
                )
                incoming[task_id] = (values, receiver, item)
        else:
            # Legacy single-task shape is only accepted while it is the same
            # already-known Task; new Tasks must use the bounded list shape.
            incoming = {entries[0][0]: (entries[0][1], entries[0][2], config)}
        if set(self.runtimes) - set(incoming):
            raise DomainError("ACTIVE_TASK_REMOVAL", 409)
        for task_id, (values, receiver, item) in incoming.items():
            if task_id not in self.runtimes:
                self._add_entry(task_id, values, receiver, item)
                continue
            old_values, old_receiver = self._entries[task_id]
            current = self.runtimes[task_id].config
            new_values = self._normalise(values)
            if old_values == new_values and old_receiver == receiver and self.entry_service_names[task_id] == entry_service_names(item, self.service_names):
                continue
            if (
                new_values.get("runtime_attempt") != current.runtime_attempt + 1
                or new_values.get("execution_epoch", 0) <= current.execution_epoch
                or new_values.get("config_digest") != current.config_digest
                or new_values.get("scope_digest") != current.scope_digest
            ):
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            observation = self.observations.get(task_id)
            if getattr(observation, "state", observation) != "stopped":
                raise DomainError("ACTIVE_TASK_ATTEMPT", 409)
            old_runtime = self.runtimes.pop(task_id)
            old_runtime.__exit__(None, None, None)
            old_connection = self.connections.pop(task_id, None)
            if old_connection is not None:
                old_connection.close()
            self._entries.pop(task_id, None)
            self._add_entry(task_id, values, receiver, item)
        self.config = config
        self.service_names = config.get("service_names", self.service_names)
        return tuple(sorted(self.runtimes))

    def refresh_from_file(self, path="/config/deployment.json", *, max_bytes=1 << 20):
        """Reload once from the projected ConfigMap; return False when unchanged."""

        if self._config_file is None or self._config_file.path != Path(path):
            self._config_file = TrustedConfigFile(path, max_bytes=max_bytes)
        document = self._config_file.read_json()
        if document is None:
            return False
        pod_runtime = document.get("pod_runtime") if isinstance(document, dict) else None
        if not isinstance(pod_runtime, dict):
            raise DomainError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        try:
            self.refresh(pod_runtime)
        except BaseException:
            # A malformed or conflicting projection must be retried on the
            # next tick after the owner has repaired it.
            self._config_file._digest = None
            raise
        return True

    def __enter__(self):
        from kubernetes import client

        api_config = client.Configuration()
        api_config.host = self.config["kubernetes_url"]
        if not api_config.host.startswith("https://"):
            raise ValueError("verified Kubernetes HTTPS endpoint required")
        api_config.ssl_ca_cert = self.config["kubernetes_ca_file"]
        api_config.api_key = {"authorization": "Bearer " + token(self.config["kubernetes_token_file"])}
        api_config.verify_ssl = True
        api_config.retries = 0
        self.api = client.ApiClient(api_config)
        self._pods = KubernetesPodClient(client.CoreV1Api(self.api))
        try:
            for task_id, values, receiver in task_entries(self.config):
                entry = next((item for item in self.config.get("tasks", [])
                              if item.get("task_config", {}).get("task_id") == task_id), self.config)
                self._add_entry(task_id, values, receiver, entry)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def _endpoint_uids(self, namespace, service_name):
        from kubernetes import client

        discovery = client.DiscoveryV1Api(self.api)
        slices = discovery.list_namespaced_endpoint_slice(
            namespace,
            label_selector="kubernetes.io/service-name=" + service_name,
            _request_timeout=(5, 5),
        )
        return {
            endpoint.target_ref.uid
            for item in slices.items
            for endpoint in item.endpoints
            if endpoint.target_ref is not None and endpoint.conditions.ready is True
        }

    def ensure(self):
        """Ensure every Task Pod; one Task never hides or stops another.

        Returns the per-Task observation mapping that `start_eligible_task_ids`
        reads. A Task whose Pod cannot be ensured is recorded as not ready with a
        bounded failure code, and the other Tasks still get their chance.
        """

        if (
            not isinstance(self.service_names, dict)
            or set(self.service_names) != {"agent", "kali"}
            or any(not isinstance(value, str) or not value for value in self.service_names.values())
        ):
            raise ValueError("fixed Task Pod service names are required")
        self.observations, self.failures = {}, {}
        for task_id, runtime in self.runtimes.items():
            try:
                observation = runtime.ensure()
                if observation is None or not getattr(observation, "state", None):
                    raise ValueError("Task Pod observation is empty")
                if observation.state == "ready":
                    # Each Task may publish its own Service names; two live Task
                    # Pods can never share one Service without cross-Task starts.
                    names = self.entry_service_names.get(task_id, self.service_names)
                    for service_name in (names["agent"], names["kali"]):
                        if self._endpoint_uids(runtime.config.namespace, service_name) != {observation.pod_uid}:
                            raise ValueError("Service targets do not match the observed Task Pod UID")
            except Exception as error:
                code = getattr(error, "code", None)
                self.failures[task_id] = (
                    code if isinstance(code, str) and 0 < len(code) <= 64 else type(error).__name__
                )
                self.observations[task_id] = "error"
                continue
            self.observations[task_id] = observation
        return dict(self.observations)

    def start_eligible_task_ids(self):
        return start_eligible_task_ids(self.observations)

    def __exit__(self, *exc):
        error = None
        try:
            for runtime in self.runtimes.values():
                try:
                    runtime.__exit__(*exc)
                except Exception as failure:  # keep closing the remaining Tasks
                    error = error or failure
        finally:
            self.runtimes = {}
            for connection in self.connections.values():
                connection.close()
            self.connections = {}
            self.connection = None
            if self.api is not None:
                self.api.close()
        if error is not None:
            raise error
