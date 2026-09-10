from dataclasses import replace

import pytest

from wuji_task_runtime.errors import OwnershipError
from wuji_task_runtime.manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from wuji_task_runtime.models import LABEL_TASK


def observed(config):
    pod = build_task_pod(config)
    pod["metadata"].update(uid="pod-uid", resourceVersion="7")
    return pod


def test_two_containers_and_isolated_credentials(config):
    pod = build_task_pod(config)
    agent, kali = pod["spec"]["containers"]
    assert [agent["name"], kali["name"]] == ["agent", "kali"]
    assert agent["image"] != kali["image"]
    assert len(pod["spec"]["volumes"]) == 8
    for container, role, uid in ((agent, "agent", 10001), (kali, "kali", 10002)):
        mounts = {mount["mountPath"]: mount for mount in container["volumeMounts"]}
        assert mounts["/run/wuji/credentials"] == {
            "name": f"{role}-auth", "mountPath": "/run/wuji/credentials", "readOnly": True,
        }
        assert container["securityContext"]["runAsUser"] == uid
        assert container["securityContext"]["capabilities"] == {"drop": ["ALL"], "add": []}
        assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert pod["spec"]["automountServiceAccountToken"] is False


def test_owned_pod_reuses_with_defaults_and_list_reordering(config):
    pod = observed(config)
    pod["spec"]["containers"].reverse()
    pod["spec"]["volumes"].reverse()
    pod["spec"]["dnsPolicy"] = "ClusterFirst"
    pod["spec"]["nodeName"] = "test-node"
    for container in pod["spec"]["containers"]:
        container["volumeMounts"].reverse()
        container["imagePullPolicy"] = "IfNotPresent"
    verify_pod_ownership(pod, config, expected_uid="pod-uid")


@pytest.mark.parametrize("change", ["image", "privilege", "task", "secret", "env", "extra-container"])
def test_drift_is_rejected(config, change):
    pod = observed(config)
    agent = pod["spec"]["containers"][0]
    if change == "image":
        agent["image"] = config.kali_image
    elif change == "privilege":
        agent["securityContext"]["capabilities"]["add"] = ["NET_ADMIN"]
    elif change == "task":
        pod["metadata"]["labels"][LABEL_TASK] = "another-task"
    elif change == "secret":
        pod["spec"]["volumes"][1]["secret"]["secretName"] = config.resource_names["kali_auth"]
    elif change == "env":
        agent["env"] = [{"name": "INJECTED", "value": "yes"}]
    else:
        pod["spec"]["containers"].append({"name": "extra", "image": config.agent_image})
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, config)


def test_stop_matches_original_uid_without_requiring_new_template(config):
    pod = observed(config)
    upgraded = replace(config, config_digest="e" * 64, execution_epoch=3)
    verify_pod_ownership(pod, upgraded, require_template=False, expected_uid="pod-uid")
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, upgraded, require_template=False, expected_uid="replacement")
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, upgraded)


def test_task_resources_do_not_require_attempt_or_bound_pvc(config):
    labels = dict(config.identity_labels)
    labels.pop("wuji.dev/runtime-attempt")
    resource = {"metadata": {"namespace": config.namespace, "labels": labels}, "status": {"phase": "Pending"}}
    verify_resource_ownership(resource, config)
    resource["metadata"]["labels"][LABEL_TASK] = "another-task"
    with pytest.raises(OwnershipError):
        verify_resource_ownership(resource, config)


def test_api_resource_quantity_canonicalization_is_not_drift(config):
    pod = observed(config)
    pod["spec"]["containers"][0]["resources"]["limits"]["cpu"] = "1000m"
    pod["spec"]["containers"][1]["resources"]["limits"]["memory"] = "1024Mi"
    pod["spec"]["volumes"][3]["emptyDir"]["sizeLimit"] = "134217728"
    verify_pod_ownership(pod, config)
