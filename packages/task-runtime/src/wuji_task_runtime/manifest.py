"""Deterministic Task Pods and fail-closed ownership/template checks."""

from __future__ import annotations

from kubernetes.utils.quantity import parse_quantity

from .errors import OwnershipError
from .models import LABEL_ATTEMPT, TaskRuntimeConfig


_NETWORK_INIT_SCRIPT = r"""
set -eu
chown 10001:10000 /mnt/agent-state /mnt/agent-tmp
chmod 0770 /mnt/agent-state /mnt/agent-tmp
chown 0:0 /mnt/kali-work /mnt/kali-receipts /mnt/kali-tmp
chmod 0700 /mnt/kali-work /mnt/kali-receipts /mnt/kali-tmp
chown 10004:10004 /mnt/capture-evidence /mnt/capture-runtime /mnt/capture-ca-public /mnt/capture-tmp
chmod 0700 /mnt/capture-evidence /mnt/capture-runtime /mnt/capture-tmp
chmod 0755 /mnt/capture-ca-public
ip6tables-restore --wait --noflush <<'EOF'
*filter
:WUJI_KALI_OUT -
-A WUJI_KALI_OUT -p tcp --sport 8444 -m conntrack --ctstate ESTABLISHED --ctdir REPLY -j ACCEPT
-A WUJI_KALI_OUT -j REJECT
-A OUTPUT -m owner --uid-owner 0 -j WUJI_KALI_OUT
COMMIT
EOF
iptables-restore --wait --noflush <<'EOF'
*filter
:WUJI_KALI_OUT -
-A WUJI_KALI_OUT -p tcp -d 127.0.0.1 --dport 8080 -j ACCEPT
-A WUJI_KALI_OUT -p tcp --sport 8444 -m conntrack --ctstate ESTABLISHED --ctdir REPLY -j ACCEPT
-A WUJI_KALI_OUT -j REJECT
-A OUTPUT -m owner --uid-owner 0 -j WUJI_KALI_OUT
COMMIT
EOF
""".strip()


def _build_legacy_task_pod(config: TaskRuntimeConfig) -> dict:
    names = config.resource_names
    volumes = []
    containers = []
    for role, uid, state, path in (
        ("agent", 10001, "agent_state", "/var/lib/wuji/agent"),
        ("kali", 10002, "kali_work", "/workspace"),
    ):
        config_volume = f"{role}-config"
        auth_volume = f"{role}-auth"
        state_volume = state.replace("_", "-")
        tmp_volume = f"{role}-tmp"
        volumes.extend([
            {"name": config_volume, "configMap": {"name": names[f"{role}_config"], "defaultMode": 0o444}},
            {"name": auth_volume, "secret": {"secretName": names[f"{role}_auth"], "defaultMode": 0o444}},
            {"name": state_volume, "persistentVolumeClaim": {"claimName": names[state]}},
            {"name": tmp_volume, "emptyDir": {"sizeLimit": config.tmp_size_limit}},
        ])
        containers.append({
            "name": role,
            "image": getattr(config, f"{role}_image"),
            "imagePullPolicy": "IfNotPresent",
            "resources": getattr(config, f"{role}_resources").as_pod_resources(),
            "securityContext": {
                "runAsUser": uid, "runAsNonRoot": True,
                "privileged": False, "allowPrivilegeEscalation": False,
                "readOnlyRootFilesystem": True, "procMount": "Default",
                "capabilities": {"drop": ["ALL"], "add": []},
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "volumeMounts": [
                {"name": config_volume, "mountPath": "/config", "readOnly": True},
                {"name": auth_volume, "mountPath": "/run/wuji/credentials", "readOnly": True},
                {"name": state_volume, "mountPath": path},
                {"name": tmp_volume, "mountPath": "/tmp"},
            ],
        })
        if role == "kali" and config.kali_receipts_enabled:
            volumes.append({
                "name": "kali-receipts",
                "persistentVolumeClaim": {"claimName": names["kali_receipts"]},
            })
            containers[-1]["volumeMounts"].append({
                "name": "kali-receipts",
                "mountPath": "/var/lib/wuji/kali-receipts",
            })
        if config.expose_pod_identity:
            containers[-1]["env"] = [
                {"name": name, "valueFrom": {"fieldRef": {"apiVersion": "v1", "fieldPath": field}}}
                for name, field in (
                    ("WUJI_POD_UID", "metadata.uid"),
                    ("WUJI_POD_NAME", "metadata.name"),
                    ("WUJI_POD_NAMESPACE", "metadata.namespace"),
                )
            ]
    return {
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": config.pod_name, "namespace": config.namespace,
                     "labels": config.identity_labels, "annotations": config.annotations},
        "spec": {
            "containers": containers, "volumes": volumes, "restartPolicy": "Never",
            "activeDeadlineSeconds": config.pod_deadline_seconds,
            "automountServiceAccountToken": False, "shareProcessNamespace": False,
            "hostNetwork": False, "hostPID": False, "hostIPC": False,
            "enableServiceLinks": False, "os": {"name": "linux"},
            "securityContext": {"runAsNonRoot": True, "fsGroup": 10000,
                                "fsGroupChangePolicy": "OnRootMismatch",
                                "seccompProfile": {"type": "RuntimeDefault"}},
        },
    }


def _container_security(
    uid: int,
    gid: int,
    *,
    capabilities: list[str] | None = None,
    allow_privilege_escalation: bool = False,
) -> dict:
    return {
        "runAsUser": uid,
        "runAsGroup": gid,
        "runAsNonRoot": uid != 0,
        "privileged": False,
        "allowPrivilegeEscalation": allow_privilege_escalation,
        "readOnlyRootFilesystem": True,
        "procMount": "Default",
        "capabilities": {"drop": ["ALL"], "add": capabilities or []},
        "seccompProfile": {"type": "RuntimeDefault"},
    }


def _build_core_ctf_task_pod(config: TaskRuntimeConfig) -> dict:
    names = config.resource_names
    policy = config.capture_policy
    volumes = [
        {"name": "agent-config", "configMap": {"name": names["agent_config"], "defaultMode": 0o444}},
        {"name": "agent-auth", "secret": {"secretName": names["agent_auth"], "defaultMode": 0o440}},
        {"name": "agent-state", "persistentVolumeClaim": {"claimName": names["agent_state"]}},
        {"name": "agent-tmp", "emptyDir": {"sizeLimit": config.tmp_size_limit}},
        {"name": "kali-config", "configMap": {"name": names["kali_config"], "defaultMode": 0o444}},
        {"name": "kali-auth", "secret": {"secretName": names["kali_auth"], "defaultMode": 0o440}},
        {"name": "kali-work", "persistentVolumeClaim": {"claimName": names["kali_work"]}},
        {"name": "kali-receipts", "persistentVolumeClaim": {"claimName": names["kali_receipts"]}},
        {"name": "kali-tmp", "emptyDir": {"sizeLimit": config.tmp_size_limit}},
        {"name": "capture-auth", "secret": {"secretName": names["capture_auth"], "defaultMode": 0o440}},
        {"name": "capture-evidence", "persistentVolumeClaim": {"claimName": names["capture_evidence"]}},
        {"name": "capture-runtime", "emptyDir": {"sizeLimit": config.tmp_size_limit}},
        {"name": "capture-ca-public", "emptyDir": {"sizeLimit": "2Mi"}},
        {"name": "capture-tmp", "emptyDir": {"sizeLimit": config.tmp_size_limit}},
    ]
    init_mounts = [
        {"name": name, "mountPath": f"/mnt/{name}"}
        for name in (
            "agent-state", "agent-tmp", "kali-work", "kali-receipts", "kali-tmp",
            "capture-evidence", "capture-runtime", "capture-ca-public", "capture-tmp",
        )
    ]
    pod_identity = [
        {"name": name, "valueFrom": {"fieldRef": {"apiVersion": "v1", "fieldPath": field}}}
        for name, field in (
            ("WUJI_POD_UID", "metadata.uid"),
            ("WUJI_POD_NAME", "metadata.name"),
            ("WUJI_POD_NAMESPACE", "metadata.namespace"),
        )
    ]
    agent = {
        "name": "agent",
        "image": config.agent_image,
        "imagePullPolicy": "IfNotPresent",
        "resources": config.agent_resources.as_pod_resources(),
        "securityContext": _container_security(10001, 10000),
        "env": list(pod_identity),
        "volumeMounts": [
            {"name": "agent-config", "mountPath": "/config", "readOnly": True},
            {"name": "agent-auth", "mountPath": "/run/wuji/credentials", "readOnly": True},
            {"name": "agent-state", "mountPath": "/var/lib/wuji/agent"},
            {"name": "agent-tmp", "mountPath": "/tmp"},
        ],
    }
    kali = {
        "name": "kali",
        "image": config.kali_image,
        "imagePullPolicy": "IfNotPresent",
        "resources": config.kali_resources.as_pod_resources(),
        "securityContext": _container_security(0, 0),
        "env": [
            *pod_identity,
            {"name": "HTTP_PROXY", "value": "http://127.0.0.1:8080"},
            {"name": "HTTPS_PROXY", "value": "http://127.0.0.1:8080"},
            {"name": "http_proxy", "value": "http://127.0.0.1:8080"},
            {"name": "https_proxy", "value": "http://127.0.0.1:8080"},
            {"name": "REQUESTS_CA_BUNDLE", "value": "/run/wuji/capture-ca/ca-bundle.pem"},
            {"name": "SSL_CERT_FILE", "value": "/run/wuji/capture-ca/ca-bundle.pem"},
            {"name": "CURL_CA_BUNDLE", "value": "/run/wuji/capture-ca/ca-bundle.pem"},
        ],
        "volumeMounts": [
            {"name": "kali-config", "mountPath": "/config", "readOnly": True},
            {"name": "kali-auth", "mountPath": "/run/wuji/credentials", "readOnly": True},
            {"name": "kali-work", "mountPath": "/workspace"},
            {"name": "kali-receipts", "mountPath": "/var/lib/wuji/kali-receipts"},
            {"name": "kali-tmp", "mountPath": "/tmp"},
            {"name": "capture-ca-public", "mountPath": "/run/wuji/capture-ca", "readOnly": True},
        ],
    }
    capture = {
        "name": "capture",
        "image": config.capture_image,
        "imagePullPolicy": "IfNotPresent",
        "resources": config.capture_resources.as_pod_resources(),
        "securityContext": _container_security(
            10004,
            10004,
            capabilities=["NET_RAW"],
            allow_privilege_escalation=True,
        ),
        "env": [
            *pod_identity,
            {"name": "WUJI_CAPTURE_PROXY_HOST", "value": "127.0.0.1"},
            {"name": "WUJI_CAPTURE_PROXY_PORT", "value": "8080"},
            {"name": "WUJI_CAPTURE_HEALTH_HOST", "value": "127.0.0.1"},
            {"name": "WUJI_CAPTURE_HEALTH_PORT", "value": "8085"},
            {"name": "WUJI_CAPTURE_DROP_USER", "value": ""},
            {"name": "WUJI_CAPTURE_CA_PUBLIC_FILE", "value": "/run/wuji-ca-public/ca-bundle.pem"},
            {"name": "WUJI_CAPTURE_MAX_REQUEST_BODY_BYTES", "value": str(policy.max_request_body_bytes)},
            {"name": "WUJI_CAPTURE_MAX_RESPONSE_BODY_BYTES", "value": str(policy.max_response_body_bytes)},
            {"name": "WUJI_CAPTURE_PCAP_SEGMENT_BYTES", "value": str(policy.pcap_segment_bytes)},
            {"name": "WUJI_CAPTURE_MAX_SESSION_BYTES", "value": str(policy.max_session_bytes)},
            {"name": "WUJI_CAPTURE_MAX_ITEMS", "value": str(policy.max_items)},
            {"name": "WUJI_CAPTURE_PART_READ_CHUNK_BYTES", "value": str(policy.part_read_chunk_bytes)},
            {"name": "WUJI_CAPTURE_DRAIN_TIMEOUT_SECONDS", "value": str(policy.drain_timeout_seconds)},
            {"name": "WUJI_CAPTURE_SEAL_TIMEOUT_SECONDS", "value": str(policy.seal_timeout_seconds)},
            {"name": "WUJI_TASK_ID", "value": str(config.task_id)},
            {"name": "WUJI_RUNTIME_ATTEMPT", "value": str(config.runtime_attempt)},
            {"name": "WUJI_EXECUTION_EPOCH", "value": str(config.execution_epoch)},
            {"name": "WUJI_CAPTURE_CONTROL_HOST", "value": "0.0.0.0"},
            {"name": "WUJI_CAPTURE_CONTROL_PORT", "value": "8445"},
            {"name": "WUJI_CAPTURE_CONTROL_TLS_CERT_FILE", "value": "/run/wuji/capture-credentials/tls.crt"},
            {"name": "WUJI_CAPTURE_CONTROL_TLS_KEY_FILE", "value": "/run/wuji/capture-credentials/tls.key"},
            {"name": "WUJI_CAPTURE_CONTROL_CLIENT_CA_FILE", "value": "/run/wuji/capture-credentials/client-ca.crt"},
            {"name": "WUJI_CAPTURE_CONTROL_CLIENT_FINGERPRINT_FILE", "value": "/run/wuji/capture-credentials/client.sha256"},
        ],
        "ports": [
            {"name": "proxy", "containerPort": 8080, "protocol": "TCP"},
            {"name": "health", "containerPort": 8085, "protocol": "TCP"},
            {"name": "control", "containerPort": 8445, "protocol": "TCP"},
        ],
        "readinessProbe": {
            "exec": {"command": [
                "python", "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8085/health/ready', timeout=2).read()",
            ]},
            "periodSeconds": 2,
            "timeoutSeconds": 3,
            "failureThreshold": 2,
            "initialDelaySeconds": 0,
            "successThreshold": 1,
        },
        "livenessProbe": {
            "exec": {"command": [
                "python", "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8085/health/live', timeout=2).read()",
            ]},
            "periodSeconds": 5,
            "timeoutSeconds": 3,
            "failureThreshold": 2,
            "initialDelaySeconds": 0,
            "successThreshold": 1,
        },
        "volumeMounts": [
            {"name": "capture-auth", "mountPath": "/run/wuji/capture-credentials", "readOnly": True},
            {"name": "capture-evidence", "mountPath": "/var/lib/wuji-capture"},
            {"name": "capture-runtime", "mountPath": "/run/wuji-capture"},
            {"name": "capture-ca-public", "mountPath": "/run/wuji-ca-public"},
            {"name": "capture-tmp", "mountPath": "/tmp"},
        ],
    }
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": config.pod_name,
            "namespace": config.namespace,
            "labels": config.identity_labels,
            "annotations": config.annotations,
        },
        "spec": {
            "initContainers": [{
                "name": "task-network-init",
                "image": config.capture_image,
                "imagePullPolicy": "IfNotPresent",
                "command": ["/bin/sh", "-ec", _NETWORK_INIT_SCRIPT],
                "resources": config.capture_resources.as_pod_resources(),
                "securityContext": _container_security(
                    0, 0, capabilities=["CHOWN", "FOWNER", "NET_ADMIN"]
                ),
                "volumeMounts": init_mounts,
            }],
            "containers": [agent, kali, capture],
            "volumes": volumes,
            "restartPolicy": "Never",
            "activeDeadlineSeconds": config.pod_deadline_seconds,
            "automountServiceAccountToken": False,
            "shareProcessNamespace": False,
            "hostNetwork": False,
            "hostPID": False,
            "hostIPC": False,
            "enableServiceLinks": False,
            "os": {"name": "linux"},
            "securityContext": {
                "fsGroup": 10000,
                "fsGroupChangePolicy": "OnRootMismatch",
                "seccompProfile": {"type": "RuntimeDefault"},
            },
        },
    }


def build_task_pod(config: TaskRuntimeConfig) -> dict:
    if config.template_version == "legacy-v1":
        return _build_legacy_task_pod(config)
    return _build_core_ctf_task_pod(config)


def verify_resource_ownership(resource: dict, config: TaskRuntimeConfig) -> None:
    metadata = resource.get("metadata") or {}
    if metadata.get("namespace") != config.namespace:
        raise OwnershipError("resource namespace does not match Task")
    labels = metadata.get("labels") or {}
    for key, value in config.identity_labels.items():
        if key != LABEL_ATTEMPT and labels.get(key) != value:
            raise OwnershipError("resource ownership does not match Task")
    annotations = metadata.get("annotations") or {}
    if any(annotations.get(key) != value for key, value in config.ownership_annotations.items()):
        raise OwnershipError("resource original identity does not match Task")


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        items = [_canonical(item) for item in value]
        if items and all(isinstance(item, dict) and "name" in item for item in items):
            return sorted(items, key=lambda item: item["name"])
        return items
    return value


def _normalized_spec(spec: dict) -> dict:
    """Allow API defaults, retaining all executable/security-bearing additions."""
    result = _canonical(spec)
    for key in ("hostNetwork", "hostPID", "hostIPC", "shareProcessNamespace"):
        result.setdefault(key, False)
    defaults = {
        "dnsPolicy": "ClusterFirst", "schedulerName": "default-scheduler",
        "terminationGracePeriodSeconds": 30, "serviceAccountName": "default",
        "serviceAccount": "default", "priority": 0,
        "preemptionPolicy": "PreemptLowerPriority",
        "initContainers": [], "ephemeralContainers": [],
    }
    for key, default in defaults.items():
        if result.get(key) == default:
            result.pop(key)
    # Scheduling observations are not executable container/template changes.
    result.pop("nodeName", None)
    tolerations = result.get("tolerations")
    if tolerations is not None and all(item in (
        {"key": "node.kubernetes.io/not-ready", "operator": "Exists", "effect": "NoExecute", "tolerationSeconds": 300},
        {"key": "node.kubernetes.io/unreachable", "operator": "Exists", "effect": "NoExecute", "tolerationSeconds": 300},
    ) for item in tolerations):
        result.pop("tolerations")
    for container in [*result.get("initContainers", []), *result.get("containers", [])]:
        for limits in container.get("resources", {}).values():
            if isinstance(limits, dict):
                for resource, quantity in limits.items():
                    try:
                        limits[resource] = str(parse_quantity(quantity).normalize())
                    except (ValueError, TypeError, ArithmeticError):
                        raise OwnershipError("invalid observed resource quantity") from None
        security = container.get("securityContext", {})
        if "capabilities" in security:
            security["capabilities"].setdefault("add", [])
        for key, default in {
            "imagePullPolicy": "IfNotPresent", "terminationMessagePath": "/dev/termination-log",
            "terminationMessagePolicy": "File", "stdin": False, "stdinOnce": False,
            "tty": False, "env": [], "envFrom": [], "ports": [],
        }.items():
            if container.get(key) == default:
                container.pop(key)
        for mount in container.get("volumeMounts", []):
            if mount.get("readOnly") is False:
                mount.pop("readOnly")
    for volume in result.get("volumes", []):
        if "sizeLimit" in volume.get("emptyDir", {}):
            try:
                volume["emptyDir"]["sizeLimit"] = str(parse_quantity(volume["emptyDir"]["sizeLimit"]).normalize())
            except (ValueError, TypeError, ArithmeticError):
                raise OwnershipError("invalid observed volume quantity") from None
        for source in ("secret", "configMap", "persistentVolumeClaim"):
            detail = volume.get(source, {})
            for key in ("optional", "readOnly"):
                if detail.get(key) is False:
                    detail.pop(key)
    return result


def verify_pod_ownership(
    pod: dict, config: TaskRuntimeConfig, *, require_template: bool = True,
    expected_uid: str | None = None,
) -> None:
    verify_resource_ownership(pod, config)
    metadata = pod.get("metadata") or {}
    if metadata.get("name") != config.pod_name:
        raise OwnershipError("Pod name does not match Task attempt")
    if (metadata.get("labels") or {}).get(LABEL_ATTEMPT) != str(config.runtime_attempt):
        raise OwnershipError("Pod attempt does not match")
    uid = metadata.get("uid")
    if not isinstance(uid, str) or not uid or (expected_uid is not None and uid != expected_uid):
        raise OwnershipError("Pod UID is missing or does not match")
    if require_template:
        annotations = metadata.get("annotations") or {}
        if any(annotations.get(key) != value for key, value in config.annotations.items()):
            raise OwnershipError("Pod execution/template binding does not match")
        if _normalized_spec(pod.get("spec") or {}) != _normalized_spec(build_task_pod(config)["spec"]):
            raise OwnershipError("Pod managed template does not match")
