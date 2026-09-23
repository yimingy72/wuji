from dataclasses import replace

import pytest

from wuji_task_runtime.errors import OwnershipError
from wuji_task_runtime.manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from wuji_task_runtime.models import CapturePolicy, LABEL_TASK


def observed(config):
    pod = build_task_pod(config)
    pod["metadata"].update(uid="pod-uid", resourceVersion="7")
    return pod


def core_config(config):
    return replace(
        config,
        template_version="core-ctf-v1",
        expose_pod_identity=True,
        kali_receipts_enabled=True,
        capture_image="example.invalid/capture@sha256:" + "e" * 64,
        capture_resources=replace(
            config.agent_resources,
            cpu_request="50m",
            memory_request="64Mi",
            cpu_limit="500m",
            memory_limit="256Mi",
        ),
        capture_policy=CapturePolicy(
            max_request_body_bytes=8_388_608,
            max_response_body_bytes=8_388_608,
            pcap_segment_bytes=64_000_000,
            max_session_bytes=1_073_741_824,
            max_items=10_000,
            part_read_chunk_bytes=1_048_576,
            drain_timeout_seconds=5.0,
            seal_timeout_seconds=10.0,
        ),
    )


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


def test_legacy_template_digest_is_unchanged(config):
    assert config.template_digest == "b3f43c62f657444d5a7b87f622b3ed904304b08ff1307fe5833efcf858444bda"


def test_core_ctf_template_has_trusted_init_and_isolated_capture(config):
    config = core_config(config)
    pod = build_task_pod(config)
    assert [item["name"] for item in pod["spec"]["initContainers"]] == ["task-network-init"]
    assert [item["name"] for item in pod["spec"]["containers"]] == ["agent", "kali", "capture"]
    init = pod["spec"]["initContainers"][0]
    assert init["securityContext"]["capabilities"] == {
        "drop": ["ALL"], "add": ["CHOWN", "FOWNER", "NET_ADMIN"],
    }
    script = init["command"][2]
    assert "--uid-owner 0" in script
    assert "--sport 8444 -m conntrack --ctstate ESTABLISHED --ctdir REPLY" in script
    assert "-d 127.0.0.1 --dport 8080" in script
    assert "ip6tables-restore" in script and "::1" not in script

    containers = {item["name"]: item for item in pod["spec"]["containers"]}
    kali, capture = containers["kali"], containers["capture"]
    assert kali["securityContext"]["runAsUser"] == 0
    assert kali["securityContext"]["capabilities"] == {"drop": ["ALL"], "add": []}
    assert capture["securityContext"]["runAsUser"] == 10004
    assert capture["securityContext"]["capabilities"] == {"drop": ["ALL"], "add": ["NET_RAW"]}
    assert capture["securityContext"]["allowPrivilegeEscalation"] is True
    kali_mounts = {item["name"]: item for item in kali["volumeMounts"]}
    capture_mounts = {item["name"]: item for item in capture["volumeMounts"]}
    assert "capture-evidence" not in kali_mounts and "capture-auth" not in kali_mounts
    assert capture_mounts["capture-evidence"]["mountPath"] == "/var/lib/wuji-capture"
    assert capture_mounts["capture-auth"]["mountPath"] == "/run/wuji/capture-credentials"
    assert kali_mounts["capture-ca-public"]["readOnly"] is True
    env = {item["name"]: item.get("value") for item in kali["env"]}
    assert env["HTTP_PROXY"] == "http://127.0.0.1:8080"
    assert env["REQUESTS_CA_BUNDLE"] == "/run/wuji/capture-ca/ca-bundle.pem"
    assert "NO_PROXY" not in env
    capture_env = {item["name"]: item.get("value") for item in capture["env"]}
    assert capture_env["WUJI_CAPTURE_MAX_REQUEST_BODY_BYTES"] == "8388608"
    assert capture_env["WUJI_CAPTURE_PCAP_SEGMENT_BYTES"] == "64000000"
    verify_pod_ownership(observed(config), config, expected_uid="pod-uid")


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


def test_core_pod_accepts_kubernetes_omission_of_empty_env_value(config):
    core = core_config(config)
    pod = observed(core)
    capture = next(item for item in pod["spec"]["containers"] if item["name"] == "capture")
    drop_user = next(item for item in capture["env"] if item["name"] == "WUJI_CAPTURE_DROP_USER")
    assert drop_user.pop("value") == ""
    verify_pod_ownership(pod, core, expected_uid="pod-uid")
    drop_user["value"] = "root"
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, core, expected_uid="pod-uid")


def test_core_pod_accepts_kubernetes_omission_of_zero_probe_delay(config):
    core = core_config(config)
    pod = observed(core)
    capture = next(item for item in pod["spec"]["containers"] if item["name"] == "capture")
    for name in ("livenessProbe", "readinessProbe"):
        assert capture[name].pop("initialDelaySeconds") == 0
    verify_pod_ownership(pod, core, expected_uid="pod-uid")
    capture["readinessProbe"]["initialDelaySeconds"] = 1
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, core, expected_uid="pod-uid")


def test_revoked_core_pod_only_allows_platform_shortened_deadline(config):
    core = core_config(config)
    pod = observed(core)
    pod["spec"]["activeDeadlineSeconds"] = 1
    with pytest.raises(OwnershipError):
        verify_pod_ownership(pod, core, expected_uid="pod-uid")
    verify_pod_ownership(
        pod, core, expected_uid="pod-uid", allow_shortened_deadline=True
    )
    pod["spec"]["containers"][0]["image"] = core.kali_image
    with pytest.raises(OwnershipError):
        verify_pod_ownership(
            pod, core, expected_uid="pod-uid", allow_shortened_deadline=True
        )


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
