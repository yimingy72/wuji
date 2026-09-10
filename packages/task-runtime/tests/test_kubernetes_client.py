from unittest.mock import Mock

import pytest
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from wuji_task_runtime import KubernetesPodClient
from wuji_task_runtime.errors import RuntimeStateUnknown, RuntimeTransportError


@pytest.fixture
def api():
    configuration = client.Configuration()
    configuration.host = "https://cluster.invalid"
    configuration.retries = 0
    with client.ApiClient(configuration) as api_client:
        yield client.CoreV1Api(api_client)


def test_delete_uses_server_uid_and_resource_version_preconditions(api):
    api.delete_namespaced_pod = Mock(return_value=client.V1Status(status="Success"))
    transport = KubernetesPodClient(api)
    assert transport.delete_pod("test", "owned", uid="pod-uid", resource_version="8")
    kwargs = api.delete_namespaced_pod.call_args.kwargs
    assert kwargs["body"].preconditions.uid == "pod-uid"
    assert kwargs["body"].preconditions.resource_version == "8"
    assert kwargs["namespace"] == "test" and kwargs["_request_timeout"] == (10, 10)


def test_notfound_is_absent_but_forbidden_and_unknown_writes_are_errors(api):
    transport = KubernetesPodClient(api)
    api.read_namespaced_pod = Mock(side_effect=ApiException(status=404))
    assert transport.read_pod("test", "owned") is None
    api.read_namespaced_pod.side_effect = ApiException(status=403, reason="SENSITIVE_SERVER_DETAILS")
    with pytest.raises(RuntimeTransportError) as caught:
        transport.read_pod("test", "owned")
    assert caught.value.status == 403 and "SENSITIVE" not in str(caught.value)
    api.create_namespaced_pod = Mock(side_effect=ApiException(status=500, reason="SENSITIVE_SERVER_DETAILS"))
    with pytest.raises(RuntimeStateUnknown) as caught:
        transport.create_pod("test", {})
    assert "SENSITIVE" not in str(caught.value)
    assert api.create_namespaced_pod.call_count == 1


def test_secret_values_are_not_returned_from_resource_preflight(api):
    api.read_namespaced_secret = Mock(return_value=client.V1Secret(
        metadata=client.V1ObjectMeta(name="owned", namespace="test"),
        data={"token": "SYNTHETIC_FIXTURE_VALUE"},
    ))
    result = KubernetesPodClient(api).read_resource("Secret", "test", "owned")
    assert result == {"metadata": {"name": "owned", "namespace": "test"}}


def test_transport_requires_explicitly_disabled_sdk_retries(api):
    api.api_client.configuration.retries = None
    with pytest.raises(ValueError, match="retries=0"):
        KubernetesPodClient(api)
