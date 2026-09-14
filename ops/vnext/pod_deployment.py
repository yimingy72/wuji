"""Service-lifetime resource owner; permission and lease logic lives in C0."""

from kubernetes import client

from deployment_common import read_file, token
from wuji_core.execution.pod_runtime import PodReceiverRegistration, VNextPodRuntime
from wuji_task_runtime.kubernetes_client import KubernetesPodClient
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig


class PodEnvironment:
    def __init__(self, deployment, config):
        self.deployment, self.config = deployment, config
        self.runtime = self.connection = self.api = None

    def __enter__(self):
        values = dict(self.config["task_config"])
        if values.get("namespace") != "wuji-vnext-test" or values.get("expose_pod_identity") is not True:
            raise ValueError("isolated namespace and real Downward API identity required")
        for role in ("agent", "kali"):
            values[role + "_resources"] = ContainerResources(**values[role + "_resources"])
        task_config = TaskRuntimeConfig(**values)
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
        try:
            self.runtime = VNextPodRuntime(task_config, connection=self.connection,
                access=self.deployment.access(), control=self.deployment.control,
                pods=KubernetesPodClient(client.CoreV1Api(self.api)),
                receiver=PodReceiverRegistration(**self.config["receiver"]))
            self.runtime.__enter__()
            return self
        except BaseException:
            self.connection.close()
            self.api.close()
            raise

    def ensure(self):
        observation = self.runtime.ensure()
        if observation.state == "ready":
            discovery = client.DiscoveryV1Api(self.api)
            service_names = self.config.get("service_names", {"agent": "task-agent", "kali": "task-kali"})
            if (not isinstance(service_names, dict)
                    or set(service_names) != {"agent", "kali"}
                    or any(not isinstance(value, str) or not value for value in service_names.values())):
                raise ValueError("fixed Task Pod service names are required")
            for service_name in (service_names["agent"], service_names["kali"]):
                slices = discovery.list_namespaced_endpoint_slice(
                    self.runtime.config.namespace,
                    label_selector="kubernetes.io/service-name=" + service_name,
                    _request_timeout=(5, 5))
                targets = {endpoint.target_ref.uid for item in slices.items
                    for endpoint in item.endpoints
                    if endpoint.target_ref is not None and endpoint.conditions.ready is True}
                if targets != {observation.pod_uid}:
                    raise ValueError("Service targets do not match the observed Task Pod UID")
        return observation

    def __exit__(self, *exc):
        try:
            return self.runtime.__exit__(*exc)
        finally:
            self.connection.close()
            self.api.close()
