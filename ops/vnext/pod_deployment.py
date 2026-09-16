"""Service-lifetime resource owner; permission and lease logic lives in C0.

The Kubernetes client is imported inside the methods that touch the API: the
configuration parser stays importable (and testable) without it, and the local
`ops/vnext/kubernetes/` directory can never shadow the installed package.
"""

from deployment_common import read_file, token
from pod_task_config import start_eligible_task_ids, task_entries
from wuji_core.execution.pod_runtime import PodReceiverRegistration, VNextPodRuntime
from wuji_task_runtime.kubernetes_client import KubernetesPodClient
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig


class PodEnvironment:
    """Every configured Task Pod, ensured independently.

    One Task whose Pod is not ready must not stop another Task's new starts, and
    it must never stop reconciliation of existing Runs: the loop restricts only
    new deliveries to the Tasks that reported `ready`.
    """

    def __init__(self, deployment, config):
        self.deployment, self.config = deployment, config
        self.runtimes: dict[str, VNextPodRuntime] = {}
        self.observations: dict[str, object] = {}
        self.failures: dict[str, str] = {}
        self.service_names = config.get("service_names", {"agent": "task-agent", "kali": "task-kali"})
        self.connection = self.api = None

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
        self.connection = self.deployment.connect()
        pods = KubernetesPodClient(client.CoreV1Api(self.api))
        try:
            for task_id, values, receiver in task_entries(self.config):
                if values.get("namespace") != "wuji-vnext-test" or values.get("expose_pod_identity") is not True:
                    raise ValueError("isolated namespace and real Downward API identity required")
                if values.get("task_id") != task_id:
                    raise ValueError("Task entry identifier does not match its config")
                for role in ("agent", "kali"):
                    values[role + "_resources"] = ContainerResources(**values[role + "_resources"])
                runtime = VNextPodRuntime(
                    TaskRuntimeConfig(**values),
                    connection=self.connection,
                    access=self.deployment.access(),
                    control=self.deployment.control,
                    pods=pods,
                    receiver=PodReceiverRegistration(**receiver),
                )
                runtime.__enter__()
                self.runtimes[task_id] = runtime
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
                    for service_name in (self.service_names["agent"], self.service_names["kali"]):
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
            if self.connection is not None:
                self.connection.close()
            if self.api is not None:
                self.api.close()
        if error is not None:
            raise error
