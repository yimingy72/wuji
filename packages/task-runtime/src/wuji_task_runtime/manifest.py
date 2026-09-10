"""Deterministic Task Pods and fail-closed ownership/template checks."""

from __future__ import annotations

from kubernetes.utils.quantity import parse_quantity

from .errors import OwnershipError
from .models import LABEL_ATTEMPT, TaskRuntimeConfig


def build_task_pod(config: TaskRuntimeConfig) -> dict:
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


def verify_resource_ownership(resource: dict, config: TaskRuntimeConfig) -> None:
    metadata = resource.get("metadata") or {}
    if metadata.get("namespace") != config.namespace:
        raise OwnershipError("resource namespace does not match Task")
    labels = metadata.get("labels") or {}
    for key, value in config.identity_labels.items():
        if key != LABEL_ATTEMPT and labels.get(key) != value:
            raise OwnershipError("resource ownership does not match Task")


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
    for container in result.get("containers", []):
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
