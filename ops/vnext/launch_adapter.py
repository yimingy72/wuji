"""Trusted deployment adapter for the persistent Task launch worker.

The launch worker owns the deployment boundary; the HTTP application owns the
Task/attempt decision.  This module therefore accepts only the small, already
authorised launch identity and obtains the concrete Kubernetes binding through
an injected trusted loader.  It never accepts a browser document, image, shell
command, Secret value, target URL, or model key.

``wire`` updates the mounted ConfigMaps in place.  Runtime and Gate processes
reload those files on their normal tick/request path, so adding a Task does not
roll a shared Deployment or interrupt another Task.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from functools import partial
from typing import Any, Callable, Mapping, Protocol


SCHEMA_VERSION = "wuji.runtime-launch-adapter.v1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY = re.compile(r"^[^\x00-\x20\x7f]{1,256}$")
_REVISION = re.compile(r"^[1-9][0-9]{0,30}$")
_ALLOWED_INPUT = frozenset({
    "task_id", "operation_id", "definition_digest", "profile_digest",
    "attempt", "epoch", "phase", "external_ref", "observed_runtime_uid",
    "allow_repair",
})
_FORBIDDEN_INPUT = frozenset({
    "secret", "secret_value", "token", "password", "api_key", "authorization",
    "shell", "command", "argv", "image", "images", "yaml", "manifest",
    "target", "target_url", "goal", "scope", "budget", "model", "model_key",
})


class LaunchAdapterError(RuntimeError):
    """Stable, redacted adapter failure suitable for a launch record."""

    def __init__(self, code: str, status: int = 409):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", code):
            raise ValueError("adapter error code must be bounded")
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class LaunchInput:
    task_id: str
    operation_id: str
    definition_digest: str
    profile_digest: str | None = None
    attempt: str | None = None
    epoch: str | None = None
    phase: str | None = None
    external_ref: str | None = None
    observed_runtime_uid: str | None = None
    allow_repair: bool = False

    @property
    def attempt_int(self) -> int | None:
        return None if self.attempt is None else int(self.attempt)

    @property
    def epoch_int(self) -> int | None:
        return None if self.epoch is None else int(self.epoch)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, phase: str) -> "LaunchInput":
        if not isinstance(value, Mapping):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        keys = set(value)
        if keys & _FORBIDDEN_INPUT or not keys <= _ALLOWED_INPUT:
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        if type(value.get("allow_repair", False)) is not bool or (value.get("allow_repair") and phase != "observe"):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        declared_phase = value.get("phase")
        if phase == "observe":
            if declared_phase not in (None, "prepare", "wire", "capability", "observe"):
                raise LaunchAdapterError("INVALID_SCHEMA", 422)
        elif declared_phase not in (None, phase):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        required = {"task_id", "operation_id", "definition_digest"}
        if phase != "prepare":
            required.add("attempt")
        if phase in {"wire", "observe", "capability"}:
            required |= {"profile_digest", "epoch"}
        if phase == "capability":
            required.add("observed_runtime_uid")
        if not required <= keys:
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        for key in ("task_id", "operation_id"):
            if not isinstance(value.get(key), str) or not _IDENTITY.fullmatch(value[key]):
                raise LaunchAdapterError("INVALID_SCHEMA", 422)
        for key in ("definition_digest", "profile_digest"):
            item = value.get(key)
            if key == "profile_digest" and item is None and phase == "prepare":
                continue
            if not isinstance(item, str) or not _DIGEST.fullmatch(item):
                raise LaunchAdapterError("INVALID_SCHEMA", 422)
        raw_attempt = value.get("attempt")
        if raw_attempt is None and phase == "prepare":
            attempt = None
        elif raw_attempt is None and phase == "observe" and declared_phase == "prepare":
            attempt = None
        else:
            attempt = str(raw_attempt) if type(raw_attempt) is int else raw_attempt
            if not isinstance(attempt, str) or not _REVISION.fullmatch(attempt):
                raise LaunchAdapterError("INVALID_SCHEMA", 422)
        raw_epoch = value.get("epoch")
        epoch = None if raw_epoch is None else str(raw_epoch) if type(raw_epoch) is int else raw_epoch
        if epoch is not None and (not isinstance(epoch, str) or not _REVISION.fullmatch(epoch)):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        for key in ("external_ref", "observed_runtime_uid"):
            item = value.get(key)
            if item is not None and (not isinstance(item, str) or not _IDENTITY.fullmatch(item)):
                raise LaunchAdapterError("INVALID_SCHEMA", 422)
        return cls(
            task_id=value["task_id"], operation_id=value["operation_id"],
            definition_digest=value["definition_digest"],
            profile_digest=value.get("profile_digest"), attempt=attempt,
            epoch=epoch, phase=declared_phase or phase,
            external_ref=value.get("external_ref") or value["operation_id"],
            observed_runtime_uid=value.get("observed_runtime_uid"),
            allow_repair=value.get("allow_repair", False),
        )

    def external_ref_for(self, action: str) -> str:
        raw = "|".join((action, self.task_id, self.operation_id, str(self.attempt),
                        self.definition_digest, self.profile_digest or ""))
        return f"wuji:{action}:{sha256(raw.encode()).hexdigest()[:32]}"


class ConfigMapStore(Protocol):
    """Small Kubernetes surface used by the real adapter and its focused tests."""

    def read(self, name: str) -> dict: ...
    def replace(self, name: str, document: dict) -> None: ...


class KubernetesConfigMapStore:
    """Bounded ConfigMap reader/writer; never returns Secret data in errors."""

    def __init__(self, core_api, *, namespace: str):
        if not isinstance(namespace, str) or not re.fullmatch(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?", namespace):
            raise ValueError("a bounded namespace is required")
        self.core_api, self.namespace = core_api, namespace

    def read(self, name: str) -> dict:
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?", name):
            raise LaunchAdapterError("INVALID_REFERENCE", 422)
        try:
            from kubernetes import client
            value = client.ApiClient().sanitize_for_serialization(
                self.core_api.read_namespaced_config_map(name, self.namespace)
            )
        except Exception as error:  # no Kubernetes body or URL enters ordinary logs
            status = getattr(error, "status", None)
            if status == 404:
                raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503) from None
            raise LaunchAdapterError("RUNTIME_CONFIG_UNKNOWN", 503) from None
        if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
            raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        return value

    def replace(self, name: str, document: dict) -> None:
        if not isinstance(document, dict) or document.get("kind") != "ConfigMap":
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        try:
            self.core_api.replace_namespaced_config_map(name, self.namespace, document)
        except Exception as error:
            status = getattr(error, "status", None)
            if status == 409:
                raise LaunchAdapterError("RUNTIME_CONFIG_CONFLICT", 409) from None
            raise LaunchAdapterError("RUNTIME_CONFIG_UNKNOWN", 503) from None


def _json(data: Any, *, code: str = "RUNTIME_CONFIG_UNAVAILABLE") -> Any:
    if not isinstance(data, str) or len(data.encode()) > 1 << 20:
        raise LaunchAdapterError(code, 503)
    try:
        return json.loads(data)
    except (TypeError, ValueError):
        raise LaunchAdapterError(code, 503) from None


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def task_profile_digest(definition: Mapping[str, Any]) -> str:
    """Match LaunchService's model/runtime/lock profile digest."""

    return sha256(_canonical({
        "model_profile": definition.get("model_profile"),
        "runtime_profile": definition.get("runtime_profile"),
        "lock_digest": definition.get("lock_digest"),
    })).hexdigest()


def _replaceable(value: dict) -> dict:
    value = json.loads(json.dumps(value))
    metadata = value.setdefault("metadata", {})
    for key in ("managedFields", "creationTimestamp", "selfLink"):
        metadata.pop(key, None)
    value.pop("status", None)
    return value


def _task_id(entry: Mapping[str, Any]) -> str:
    config = entry.get("task_config")
    task_id = config.get("task_id") if isinstance(config, Mapping) else None
    if not isinstance(task_id, str) or not _IDENTITY.fullmatch(task_id):
        raise LaunchAdapterError("INVALID_REFERENCE", 422)
    return task_id


def _attempt(entry: Mapping[str, Any]) -> int:
    value = (entry.get("task_config") or {}).get("runtime_attempt")
    if type(value) is not int or value < 1:
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    return value


def _digest(entry: Mapping[str, Any], key: str = "config_digest") -> str:
    value = (entry.get("task_config") or {}).get(key)
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    return value


def _same_entry(old: Mapping[str, Any], new: Mapping[str, Any]) -> bool:
    return _canonical(old) == _canonical(new)


def _legal_attempt_update(old: Mapping[str, Any], new: Mapping[str, Any]) -> bool:
    """Only the same owner may advance to the next attempt with same definition."""

    old_config, new_config = old.get("task_config") or {}, new.get("task_config") or {}
    if any(old_config.get(key) != new_config.get(key) for key in ("tenant_id", "task_id", "config_digest", "scope_digest")):
        return False
    if _attempt(new) <= _attempt(old):
        return False
    if _attempt(new) != _attempt(old) + 1:
        return False
    old_epoch, new_epoch = old_config.get("execution_epoch"), new_config.get("execution_epoch")
    return type(old_epoch) is int and type(new_epoch) is int and new_epoch > old_epoch


def merge_runtime_document(document: dict, entry: Mapping[str, Any]) -> str:
    """Add/update one Task entry without dropping another Task or legacy field."""

    if not isinstance(document, dict) or not isinstance(entry, Mapping):
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    pod = document.get("pod_runtime")
    if not isinstance(pod, dict):
        raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
    tasks = pod.get("tasks")
    if tasks is None:
        legacy = pod.get("task_config")
        receiver = pod.get("receiver")
        if not isinstance(legacy, dict) or not isinstance(receiver, dict):
            raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        tasks = [{"task_config": legacy, "receiver": receiver}]
    if not isinstance(tasks, list) or not tasks or len(tasks) > 64:
        raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
    task = _task_id(entry)
    changed, found = False, False
    merged = []
    for old in tasks:
        if not isinstance(old, dict) or _task_id(old) == task:
            if not isinstance(old, dict):
                raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
            if _task_id(old) != task:
                raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
            found = True
            if _same_entry(old, entry):
                merged.append(old)
            elif _legal_attempt_update(old, entry):
                merged.append(dict(entry))
                changed = True
            else:
                raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        else:
            merged.append(old)
    if not found:
        merged.append(dict(entry))
        changed = True
    if len(merged) > 64:
        raise LaunchAdapterError("LIMIT_BLOCKED", 429)
    if len({ _task_id(item) for item in merged }) != len(merged):
        raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
    merged.sort(key=_task_id)
    if document.get("task_ids") != [_task_id(item) for item in merged]:
        document["task_ids"] = [_task_id(item) for item in merged]
        changed = True
    if pod.get("tasks") != merged or "task_config" in pod or "receiver" in pod:
        pod.pop("task_config", None)
        pod.pop("receiver", None)
        pod["tasks"] = merged
        changed = True
    return "replaced" if changed else "unchanged"


def merge_gate_document(document: dict, entry: Mapping[str, Any]) -> str:
    """Merge one Task executor, preserving every other Task binding."""

    if not isinstance(document, dict) or not isinstance(entry, Mapping):
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    binding = entry.get("binding")
    if not isinstance(binding, dict):
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    owner_keys = ("tenant_id", "project_id", "task_id", "executor_ref")
    if any(not isinstance(binding.get(key), str) or not binding[key] for key in owner_keys):
        raise LaunchAdapterError("INVALID_SCHEMA", 422)
    executors = document.get("executors")
    if not isinstance(executors, list) or not executors or len(executors) > 256:
        raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
    key = tuple(binding[key] for key in owner_keys)
    changed, found = False, False
    merged = []
    for old in executors:
        old_binding = old.get("binding") if isinstance(old, dict) else None
        if not isinstance(old_binding, dict):
            raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        old_key = tuple(old_binding.get(item) for item in owner_keys)
        if old_key != key:
            merged.append(old)
            continue
        found = True
        if _canonical(old) != _canonical(entry):
            # A Gate ref is immutable for the current attempt.  A new attempt
            # uses a new receiver/environment binding and is explicitly allowed.
            def attempt_of(value):
                prefix = "task-" + value["task_id"] + "-a"
                receiver = value.get("receiver_id", "")
                suffix = receiver.removeprefix(prefix)
                if receiver.startswith(prefix) and re.fullmatch(r"[1-9][0-9]*", suffix):
                    number = int(suffix)
                    if value.get("environment_ref") == f"pod-environment-{value['task_id']}-a{number}":
                        return number
                return None
            old_attempt, new_attempt = attempt_of(old_binding), attempt_of(binding)
            if old_attempt is None or new_attempt != old_attempt + 1:
                raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
            merged.append(dict(entry))
            changed = True
        else:
            merged.append(old)
    if not found:
        merged.append(dict(entry))
        changed = True
    if len(merged) > 256:
        raise LaunchAdapterError("LIMIT_BLOCKED", 429)
    if len({tuple((item.get("binding") or {}).get(key) for key in owner_keys) for item in merged}) != len(merged):
        raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
    document["executors"] = merged
    return "replaced" if changed else "unchanged"


def merge_profiles(document: list, incoming: list) -> tuple[str, list]:
    """Append same-lock profiles; never silently retire a live profile."""

    if not isinstance(document, list) or not document or not isinstance(incoming, list) or not incoming:
        raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
    locks = {(item.get("body") or {}).get("lock_digest") for item in incoming}
    if len(locks) != 1 or None in locks:
        raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
    existing_locks = {
        (item.get("body") or {}).get("lock_digest")
        for item in document if isinstance(item, dict)
    }
    if None in existing_locks or not existing_locks <= locks:
        raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
    result = list(document)
    positions = {(item.get("ref"), item.get("revision")): index for index, item in enumerate(result) if isinstance(item, dict)}
    changed = False
    for item in incoming:
        if not isinstance(item, dict) or not item.get("ref") or not item.get("revision"):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        key = (item["ref"], item["revision"])
        index = positions.get(key)
        if index is None:
            result.append(item)
            positions[key] = len(result) - 1
            changed = True
        elif _canonical(result[index]) != _canonical(item):
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
    return "replaced" if changed else "unchanged", result


class RuntimeLaunchAdapter:
    """Real ConfigMap-backed adapter called by the persistent launch worker.

    ``binding_loader`` is supplied by the trusted launch worker and reads its
    frozen DB/operation state.  It is deliberately not part of the launch
    request, keeping browser data outside the deployment boundary.
    """

    def __init__(self, *, store: ConfigMapStore, binding_loader: Callable[[LaunchInput], Mapping[str, Any]],
                 runtime_configmap: str = "runtime-config", gates_configmap: str = "gates-config"):
        if not callable(binding_loader):
            raise ValueError("trusted binding loader is required")
        self.store = store
        self.binding_loader = binding_loader
        self.runtime_configmap, self.gates_configmap = runtime_configmap, gates_configmap

    def prepare(self, input: Mapping[str, Any]) -> dict:
        request = LaunchInput.from_mapping(input, phase="prepare")
        return {"status": "ready", "external_ref": request.external_ref_for("prepare"),
                "summary": "deployment binding accepted"}

    def wire(self, input: Mapping[str, Any]) -> dict:
        request = LaunchInput.from_mapping(input, phase="wire")
        binding = self.binding_loader(request)
        if not isinstance(binding, Mapping):
            raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        runtime_entry = binding.get("runtime_entry")
        gate_entry = binding.get("gate_entry")
        profiles = binding.get("profiles")
        if not isinstance(runtime_entry, Mapping) or not isinstance(gate_entry, Mapping) or not isinstance(profiles, list):
            raise LaunchAdapterError("RUNTIME_CONFIG_UNAVAILABLE", 503)
        if _task_id(runtime_entry) != request.task_id or _digest(runtime_entry) != request.definition_digest:
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        declared_profile_digest = binding.get("profile_digest")
        if declared_profile_digest is not None and declared_profile_digest != request.profile_digest:
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        if not isinstance(request.profile_digest, str) or not _DIGEST.fullmatch(request.profile_digest):
            raise LaunchAdapterError("INVALID_SCHEMA", 422)
        worker_profiles_digest = binding.get("worker_profiles_digest")
        if worker_profiles_digest is not None and sha256(_canonical(profiles)).hexdigest() != worker_profiles_digest:
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        runtime = self.store.read(self.runtime_configmap)
        gates = self.store.read(self.gates_configmap)
        runtime = _replaceable(runtime)
        gates = _replaceable(gates)
        runtime_data, gates_data = runtime["data"], gates["data"]
        runtime_doc = _json(runtime_data.get("deployment.json"))
        gates_doc = _json(gates_data.get("deployment.json"))
        profiles_doc = _json(runtime_data.get("profiles.json"))
        runtime_action = merge_runtime_document(runtime_doc, runtime_entry)
        profile_action, profiles_doc = merge_profiles(profiles_doc, profiles)
        gate_action = merge_gate_document(gates_doc, gate_entry)
        runtime_data["deployment.json"] = _canonical(runtime_doc).decode()
        runtime_data["profiles.json"] = _canonical(profiles_doc).decode()
        gates_data["deployment.json"] = _canonical(gates_doc).decode()
        # No rollout, no restart and no Secret/PVC read: kubelet projects the
        # trusted ConfigMap file and the service-side reload hooks consume it.
        self.store.replace(self.runtime_configmap, runtime)
        self.store.replace(self.gates_configmap, gates)
        return {
            "external_ref": request.external_ref_for("wire"),
            "status": "ready",
            "summary": f"runtime={runtime_action};profiles={profile_action};gates={gate_action}",
            "runtime_configmap": self.runtime_configmap,
            "gates_configmap": self.gates_configmap,
            "rolled_deployments": [],
        }

    def observe(self, input: Mapping[str, Any]) -> dict:
        request = LaunchInput.from_mapping(input, phase="observe")
        runtime = self.store.read(self.runtime_configmap)
        runtime_doc = _json(runtime["data"].get("deployment.json"))
        task = next((item for item in ((runtime_doc.get("pod_runtime") or {}).get("tasks") or [])
                     if isinstance(item, dict) and _task_id(item) == request.task_id), None)
        if task is None or (request.attempt_int is not None and _attempt(task) != request.attempt_int) or _digest(task) != request.definition_digest:
            raise LaunchAdapterError("STALE_EXECUTION", 409)
        return {"status": "pending", "external_ref": request.external_ref,
                "summary": "Task binding is present in the trusted runtime ConfigMap"}

    def capability(self, input: Mapping[str, Any]) -> dict:
        request = LaunchInput.from_mapping(input, phase="capability")
        if not request.observed_runtime_uid:
            raise LaunchAdapterError("INVALID_REFERENCE", 422)
        runtime = self.store.read(self.runtime_configmap)
        runtime_doc = _json(runtime["data"].get("deployment.json"))
        task = next((item for item in ((runtime_doc.get("pod_runtime") or {}).get("tasks") or [])
                     if isinstance(item, dict) and _task_id(item) == request.task_id), None)
        if task is None or (request.attempt_int is not None and _attempt(task) != request.attempt_int) or _digest(task) != request.definition_digest:
            raise LaunchAdapterError("STALE_EXECUTION", 409)
        return {"external_ref": request.external_ref,
                "status": "ready",
                "summary": "capability may bind only the caller-observed runtime UID",
                "observed_runtime_uid": request.observed_runtime_uid}


class ProductionLaunchProvisioner:
    """Owner-side implementation of prepare, resource wire and capability.

    The launch worker owns this object.  It reuses the existing owner helpers
    from ``task_launch`` and never exposes the owner connection, Secret bytes,
    or the Task definition through the public API.
    """

    def __init__(self, config: Mapping[str, Any], options: Mapping[str, Any], store: ConfigMapStore):
        required = {
            "core_api", "batch_api", "namespace", "agent_image", "kali_image",
            "agent_auth_dir", "kali_auth_dir", "deployment_auth_dir", "gates_auth_dir",
            "runtime_origin", "gate_url", "evidence_ref",
        }
        if not isinstance(config, Mapping) or not isinstance(options, Mapping) or not required <= set(options):
            raise ValueError("trusted production launch configuration is incomplete")
        if not isinstance(config.get("owner"), list) or len(config["owner"]) != 3:
            raise ValueError("trusted owner Task binding is required")
        self.config, self.options, self.store = config, options, store

    @staticmethod
    def _task_launch():
        try:
            import task_launch
            return task_launch
        except (ImportError, ValueError) as error:
            raise LaunchAdapterError("RUNTIME_ADAPTER_UNAVAILABLE", 503) from error

    def _owner(self, task_id):
        return self.config["owner"][0], self.config["owner"][1], task_id

    def _row(self, connection, task_id):
        task_launch = self._task_launch()
        value = connection.execute(
            "SELECT definition_json, definition_digest, runtime_attempt, execution_epoch, control_version, activated_at, desired_state, observed_state"
            " FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            self._owner(task_id),
        ).fetchone()
        if value is None or not value[0]:
            raise LaunchAdapterError("INVALID_REFERENCE", 422)
        from wuji_core.http import strict_json_loads
        return {
            "definition": strict_json_loads(value[0]), "definition_digest": value[1],
            "runtime_attempt": int(value[2]), "execution_epoch": int(value[3]),
            "control_version": str(value[4]), "activated_at": value[5],
            "desired_state": value[6], "observed_state": value[7],
        }

    def _binding(self, request, connection, *, pod_uid=None):
        task_launch = self._task_launch()
        prepared = self._row(connection, request.task_id)
        owner = self._owner(request.task_id)
        executor_ref = self.config["executor"]["ref"]
        registration = connection.execute(
            "SELECT document_json FROM vnext.executor_registration"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND ref=%s",
            (*owner, executor_ref),
        ).fetchone()
        if registration is None:
            raise LaunchAdapterError("CAPABILITY_UNAVAILABLE", 503)
        from wuji_core.http import strict_json_loads
        registered = strict_json_loads(registration[0])
        binding = task_launch.binding_document(
            self.config, request.task_id,
            agent_image=self.options["agent_image"], kali_image=self.options["kali_image"],
            prepared=prepared,
            extra={
                "receiver_id": registered["receiver_id"],
                "environment_ref": registered["environment_ref"],
                "executor_ref": registered["ref"],
                "runtime_origin": self.options["runtime_origin"],
                "gate_url": self.options["gate_url"],
                "namespace": self.options["namespace"],
                "evidence_ref": self.options["evidence_ref"],
                "pod_deadline_seconds": prepared["definition"]["runtime_profile"]["limits"]["max_elapsed_seconds"],
            },
        )
        if binding["definition_digest"] != request.definition_digest:
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        if request.attempt_int is not None and binding["runtime_attempt"] != request.attempt_int:
            raise LaunchAdapterError("STALE_EXECUTION", 409)
        if request.epoch_int is not None and binding["execution_epoch"] != request.epoch_int:
            raise LaunchAdapterError("STALE_EXECUTION", 409)
        actual_profile_digest = task_profile_digest(prepared["definition"])
        if request.profile_digest is not None and request.profile_digest != actual_profile_digest:
            raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
        if pod_uid is not None:
            binding["pod_uid"] = pod_uid
        return binding

    def prepare(self, request):
        task_launch = self._task_launch()
        owner = self._owner(request.task_id)
        connection = task_launch.owner_connection(self.config)
        budget_metadata = None
        try:
            task = self._row(connection, request.task_id)
            if task["desired_state"] in {"cancel", "finish"} or task["observed_state"] == "closed":
                raise LaunchAdapterError("STALE_EXECUTION", 409)
            selected = task["definition"]
            if (task_launch.configured_evaluation_mode(self.config) == "real_model"
                    and selected["task"].get("external_analysis_approved") is not True):
                raise LaunchAdapterError("CAPABILITY_UNAVAILABLE", 503)
            template = self.config["definition"]
            for kind in ("model", "runtime"):
                field = kind + "_profile"
                if _canonical(selected[field]) != _canonical(template[field]):
                    raise LaunchAdapterError("CAPABILITY_UNAVAILABLE", 503)
                if task_launch.configured_evaluation_mode(self.config) == "real_model":
                    published = connection.execute(
                        "SELECT real_model_allowed FROM vnext.published_profile "
                        "WHERE tenant_id=%s AND kind=%s AND ref=%s AND revision=%s AND NOT revoked",
                        (owner[0], kind, selected[field]["ref"], selected[field]["revision"]),
                    ).fetchone()
                    if not published or published[0] is not True:
                        raise LaunchAdapterError("CAPABILITY_UNAVAILABLE", 503)
            if task_launch.configured_evaluation_mode(self.config) == "real_model" and self.options.get("task_budget") is None:
                raise LaunchAdapterError("CAPABILITY_UNAVAILABLE", 503)
            prepared = task_launch.finalise_definition(connection, owner=owner, config=self.config)
            task_launch.ensure_operator_actor(
                connection, owner=owner,
                subject=self.config.get("operator_subject", "operator"),
            )
            task_launch.require_receiver_bearer_window(
                Path(self.options["deployment_auth_dir"]) / "receiver.token",
                window_seconds=prepared["definition"]["runtime_profile"]["limits"]["max_elapsed_seconds"],
            )
            task_budget = self.options.get("task_budget")
            if task_budget is not None:
                model_profile = prepared["definition"].get("model_profile") or {}
                budget_metadata = task_budget.ensure(
                    task_id=request.task_id,
                    tenant_id=owner[0],
                    model_alias=model_profile.get("upstream_model"),
                    budget_usd=prepared["definition"]["task"]["budget"]["amount"],
                )
            published = task_launch.publish_admission(
                connection, owner=owner, config=self.config,
                definition=prepared["definition"], attempt=prepared["runtime_attempt"],
                pool_keys=task_launch.deployment_pool_keys(connection, self.config),
            )
            initial = task_launch.initial_intent_document(self.config, prepared["definition"])
            if initial is not None:
                task_launch.admit_initial_intent(
                    partial(task_launch.application_connection, self.config),
                    access=task_launch.operator_access(
                        self.config, signing_key_file=self.options.get("signing_key_file")
                    ), task=request.task_id, document=initial,
                    idempotency_key=f"task-launch-intent-{request.task_id}",
                )
            binding = task_launch.binding_document(
                self.config, request.task_id,
                agent_image=self.options["agent_image"], kali_image=self.options["kali_image"],
                prepared=prepared,
                extra={
                    **published,
                    "runtime_origin": self.options["runtime_origin"],
                    "gate_url": self.options["gate_url"],
                    "namespace": self.options["namespace"],
                    "evidence_ref": self.options["evidence_ref"],
                    "pod_deadline_seconds": prepared["definition"]["runtime_profile"]["limits"]["max_elapsed_seconds"],
                },
            )
        finally:
            connection.close()
        result = {
            "external_ref": request.external_ref_for("prepare"),
            "status": "ready",
            "phase_status": "succeeded",
            "definition_digest": prepared["definition_digest"],
            "prepared_definition_digest": prepared["definition_digest"],
            "profile_digest": task_profile_digest(prepared["definition"]),
            "prepared_profile_digest": task_profile_digest(prepared["definition"]),
            "runtime_attempt": prepared["runtime_attempt"],
            "execution_epoch": prepared["execution_epoch"],
            "reason_first": initial is None,
        }
        if budget_metadata is not None:
            # NativeTaskBudget returns public metadata only; never copy key refs
            # or Secret material into a launch binding.
            result["budget"] = {
                key: value for key, value in budget_metadata.items()
                if key in {"task_id", "tenant_id", "model_alias", "budget_usd", "status"}
            }
        return result

    def _ensure_resources(self, binding):
        task_launch = self._task_launch()
        core, namespace = self.options["core_api"], self.options["namespace"]
        material = task_launch.requirement_material(
            self.config,
            agent_auth_dir=self.options["agent_auth_dir"],
            kali_auth_dir=self.options["kali_auth_dir"],
            deployment_auth_dir=self.options["deployment_auth_dir"],
            gates_auth_dir=self.options["gates_auth_dir"],
        )
        _, objects = task_launch.task_objects(binding, material, namespace=namespace)
        actions = {}
        for body in objects:
            actions[body["metadata"]["name"]] = task_launch.ensure_object(
                core, body["kind"], body, namespace=namespace
            )
        job = task_launch.initializer_job(
            binding, namespace=namespace, image=self.options["kali_image"],
            materials=task_launch.deployment_materials(self.config),
        )
        batch = self.options["batch_api"]
        try:
            batch.create_namespaced_job(namespace, job)
            actions[job["metadata"]["name"]] = "created"
        except Exception as error:
            if getattr(error, "status", None) != 409:
                raise LaunchAdapterError("WORKSPACE_INIT_FAILED", 503) from error
            actions[job["metadata"]["name"]] = "unchanged"
        deadline = time.monotonic() + 120
        while True:
            status = batch.read_namespaced_job_status(job["metadata"]["name"], namespace).status
            if status.succeeded:
                break
            if status.failed or time.monotonic() > deadline:
                raise LaunchAdapterError("WORKSPACE_INIT_FAILED", 503)
            time.sleep(2)
        names = task_launch.task_service_names(binding["task_id"])
        config = task_launch.attempt_config(binding)
        for role, port in (("agent", 8443), ("kali", 8444)):
            try:
                existing = core.read_namespaced_service(names[role], namespace)
                selector = getattr(getattr(existing, "spec", None), "selector", None) or {}
                labels = config.identity_labels
                if any(selector.get(key) != labels[key] for key in ("wuji.dev/task-id", "wuji.dev/tenant-id")):
                    raise LaunchAdapterError("INPUT_DIGEST_CONFLICT", 409)
            except LaunchAdapterError:
                raise
            except Exception as error:
                if getattr(error, "status", None) != 404:
                    raise LaunchAdapterError("RUNTIME_CONFIG_UNKNOWN", 503) from error
            actions[names[role]] = task_launch.ensure_task_service(
                core, names[role], config.identity_labels, port, namespace=namespace
            )
        return actions, config

    def _update_configmaps(self, request, binding, *, write=True):
        task_launch = self._task_launch()
        names = task_launch.task_service_names(request.task_id)
        runtime_entry = {
            "task_config": task_launch.runtime_config_document(binding),
            "receiver": {
                "receiver_id": binding["receiver_id"], "receiver_subject": "receiver",
                "environment_ref": binding["environment_ref"],
                "credential_template_ref": "deployment-worker-v1",
                "model_mode": "synthetic" if binding.get("evaluation_mode") == "mechanism_synthetic" else "real",
            },
            "service_names": names,
            "supervisor_url": f"https://{names['agent']}.{self.options['namespace']}.svc:8443",
        }
        gate_entry = {
            "binding": {
                "tenant_id": binding["tenant_id"], "project_id": binding["project_id"],
                "task_id": binding["task_id"], "executor_ref": binding["executor_ref"],
                "receiver_id": binding["receiver_id"], "environment_ref": binding["environment_ref"],
                "collector_subject": self.config["executor"]["collector_subject"],
                "gate_subject": "gate",
            },
            "base_url": f"https://{names['kali']}.{self.options['namespace']}.svc:8444",
            "gate_token_file": "/run/wuji/credentials/service.token",
            "collector_token_file": "/run/wuji/credentials/collector.token",
        }
        runtime, gates = _replaceable(self.store.read("runtime-config")), _replaceable(self.store.read("gates-config"))
        runtime_doc = _json(runtime["data"].get("deployment.json"))
        gates_doc = _json(gates["data"].get("deployment.json"))
        profiles_doc = _json(runtime["data"].get("profiles.json"))
        runtime_action = merge_runtime_document(runtime_doc, runtime_entry)
        profile_action, profiles_doc = merge_profiles(profiles_doc, list(binding["worker_profiles"].values()))
        gate_action = merge_gate_document(gates_doc, gate_entry)
        runtime["data"]["deployment.json"] = _canonical(runtime_doc).decode()
        runtime["data"]["profiles.json"] = _canonical(profiles_doc).decode()
        gates["data"]["deployment.json"] = _canonical(gates_doc).decode()
        if write:
            if runtime_action != "unchanged" or profile_action != "unchanged":
                self.store.replace("runtime-config", runtime)
            if gate_action != "unchanged":
                self.store.replace("gates-config", gates)
        return {"runtime": runtime_action, "profiles": profile_action, "gates": gate_action}

    def _wire_complete(self, request, binding):
        """A Pod alone does not prove the separate configuration writes landed."""
        try:
            actions = self._update_configmaps(request, binding, write=False)
            if any(value != "unchanged" for value in actions.values()):
                return False
            task_launch = self._task_launch()
            config = task_launch.attempt_config(binding)
            for name in task_launch.task_service_names(binding["task_id"]).values():
                service = self.options["core_api"].read_namespaced_service(name, self.options["namespace"])
                if service.spec.selector != config.identity_labels:
                    return False
            return True
        except (KeyError, TypeError, AttributeError, LaunchAdapterError):
            return False

    def _pod_observation(self, config, expected_uid=None):
        core, namespace = self.options["core_api"], self.options["namespace"]
        try:
            pod = core.read_namespaced_pod(config.pod_name, namespace)
        except Exception as error:
            if getattr(error, "status", None) == 404:
                return {"status": "pending", "pod_uid": None}
            raise LaunchAdapterError("POD_STATE_UNKNOWN", 503) from error
        uid = getattr(getattr(pod, "metadata", None), "uid", None)
        if expected_uid is not None and uid != expected_uid:
            raise LaunchAdapterError("STALE_EXECUTION", 409)
        status = getattr(pod, "status", None)
        phase = getattr(status, "phase", None)
        ready = sum(1 for item in (getattr(status, "container_statuses", None) or []) if item.ready is True)
        if phase == "Running" and ready == 2:
            return {"status": "ready", "pod_uid": uid}
        if phase in {"Failed", "Succeeded"}:
            return {"status": "failed", "pod_uid": uid}
        return {"status": "pending", "pod_uid": uid}

    def wire(self, request):
        task_launch = self._task_launch()
        connection = task_launch.owner_connection(self.config)
        try:
            binding = self._binding(request, connection)
        finally:
            connection.close()
        actions, runtime_config = self._ensure_resources(binding)
        config_actions = self._update_configmaps(request, binding)
        observation = self._pod_observation(runtime_config)
        return {
            "external_ref": request.external_ref_for("wire"),
            "status": "ready" if observation["status"] == "ready" else "pending" if observation["status"] == "pending" else "unknown",
            "phase_status": observation["status"], "actions": {**actions, "configmaps": config_actions},
            "pod_uid": observation["pod_uid"], "rolled_deployments": [],
        }

    def observe(self, request):
        task_launch = self._task_launch()
        connection = task_launch.owner_connection(self.config)
        try:
            if request.phase == "prepare":
                prepared = self._row(connection, request.task_id)
                may_repair = (getattr(request, "allow_repair", False)
                              and prepared.get("desired_state") not in {"cancel", "finish"}
                              and prepared.get("observed_state") != "closed")
                # create_task's original five-field jsonb body remains fixed.
                # Finalization adds trusted runtime fields and changes encoding;
                # reconstructing the DB-native original binds a lost response
                # to the same accepted input, without inventing a new launch.
                original_digest = connection.execute(
                    "SELECT encode(sha256(convert_to(jsonb_build_object("
                    "'task',definition_json::jsonb->'task',"
                    "'start_points',definition_json::jsonb->'start_points',"
                    "'model_profile',definition_json::jsonb->'model_profile',"
                    "'runtime_profile',definition_json::jsonb->'runtime_profile',"
                    "'lock_digest',definition_json::jsonb->'lock_digest')::text,'UTF8')),'hex') "
                    "FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                    self._owner(request.task_id),
                ).fetchone()[0]
                admission = connection.execute(
                    "SELECT 1 FROM vnext.admission_config WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                    self._owner(request.task_id),
                ).fetchone()
                executor = connection.execute(
                    "SELECT 1 FROM vnext.executor_registration WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                    self._owner(request.task_id),
                ).fetchone()
                current_profile = task_profile_digest(prepared["definition"])
                if (
                    request.definition_digest not in {prepared["definition_digest"], original_digest}
                    or current_profile != request.profile_digest
                ):
                    return {
                        "status": "unknown", "phase_status": "reconciling",
                        "external_ref": request.external_ref,
                        "reason_code": "prepared_digest_not_recorded",
                        "prepared_definition_digest": prepared["definition_digest"],
                        "prepared_profile_digest": current_profile,
                    }
                if admission is None or executor is None:
                    if may_repair:
                        # Explicit active recovery only; prepare rechecks the
                        # current Task and reconciles the same key before writes.
                        return self.prepare(request)
                    return {"status": "unknown", "phase_status": "reconciling",
                            "external_ref": request.external_ref,
                            "reason_code": "prepare_incomplete_readonly"}
                return {
                    "status": "ready", "phase_status": "succeeded",
                    "external_ref": request.external_ref,
                    "prepared_definition_digest": prepared["definition_digest"],
                    "prepared_profile_digest": current_profile,
                    "definition_digest": prepared["definition_digest"],
                    "runtime_attempt": prepared["runtime_attempt"],
                    "execution_epoch": prepared["execution_epoch"],
                }
            binding = self._binding(request, connection)
            if not self._wire_complete(request, binding):
                if getattr(request, "allow_repair", False):
                    task = self._row(connection, request.task_id)
                    if task["desired_state"] == "run" and task["observed_state"] != "closed":
                        # Stable resource names and per-Task CAS merges repair
                        # only missing steps, never roll shared deployments.
                        repaired = self.wire(request)
                        if request.phase != "capability" or repaired.get("status") != "ready":
                            return repaired
                        # Capability is its own phase, not implied by repaired
                        # routing. Continue through UID-bound publication below.
                    else:
                        return {"status": "unknown", "phase_status": "reconciling",
                                "external_ref": request.external_ref, "reason_code": "wire_incomplete"}
                else:
                    return {"status": "unknown", "phase_status": "reconciling",
                            "external_ref": request.external_ref, "reason_code": "wire_incomplete"}
            state = self._pod_observation(task_launch.attempt_config(binding), request.observed_runtime_uid)
            if request.phase == "capability" and state["status"] == "ready" and getattr(request, "allow_repair", False):
                if request.observed_runtime_uid is None:
                    raise LaunchAdapterError("STALE_EXECUTION", 409)
                binding["pod_uid"] = state["pod_uid"]
                task_launch.publish_capabilities(connection, config=self.config, binding=binding)
        finally:
            connection.close()
        status = "ready" if state["status"] == "ready" else "pending" if state["status"] == "pending" else "unknown"
        return {"external_ref": request.external_ref, "status": status,
                "phase_status": state["status"], "pod_uid": state["pod_uid"]}

    def capability(self, request):
        task_launch = self._task_launch()
        connection = task_launch.owner_connection(self.config)
        try:
            binding = self._binding(request, connection, pod_uid=request.observed_runtime_uid)
            state = self._pod_observation(task_launch.attempt_config(binding), request.observed_runtime_uid)
            if state["status"] != "ready":
                return {"external_ref": request.external_ref, "status": "pending" if state["status"] == "pending" else "unknown",
                        "phase_status": state["status"], "pod_uid": state["pod_uid"]}
            result = task_launch.publish_capabilities(connection, config=self.config, binding=binding)
        finally:
            connection.close()
        return {"external_ref": request.external_ref, "status": "ready", "phase_status": "succeeded",
                "pod_uid": request.observed_runtime_uid, **result}


class DeploymentLaunchAdapter(RuntimeLaunchAdapter):
    """A0-facing constructor for the real ``services/wuji-launch`` worker.

    ``config`` is a trusted, mounted deployment document and may contain only
    bounded non-secret settings.  ``options`` carries process-local objects
    supplied by the owner worker: a ``ConfigMapStore`` plus the Kubernetes
    APIs and owner-only paths needed by ``ProductionLaunchProvisioner``.  A
    ``binding_loader`` is accepted only for the isolated ConfigMap adapter
    fixture; production uses the existing owner DB helpers itself.  Neither
    mapping is browser input.

    Required config fields:

    * ``namespace``: the fixed Kubernetes namespace;
    * ``runtime_configmap`` / ``gates_configmap``: ConfigMap names, normally
      ``runtime-config`` and ``gates-config``;
    * optional ``max_config_bytes``: bounded JSON read size (default 1 MiB).

    Required options fields:

    * ``store``: ``ConfigMapStore`` implementation, normally
      ``KubernetesConfigMapStore``;
    * production without ``binding_loader``: ``core_api``, ``batch_api``,
      immutable agent/Kali image refs, owner-auth mount directories, fixed
      runtime/Gate origins, and the evidence reference.  ``task_budget`` is
      optional and is called once during prepare when A0 supplies it.
    """

    def __init__(self, config: Mapping[str, Any], options: Mapping[str, Any]):
        if not isinstance(config, Mapping) or not isinstance(options, Mapping):
            raise ValueError("trusted adapter config and options are required")
        namespace = config.get("namespace")
        if not isinstance(namespace, str) or not re.fullmatch(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?", namespace):
            raise ValueError("trusted adapter namespace is required")
        max_bytes = config.get("max_config_bytes", 1 << 20)
        if type(max_bytes) is not int or not 1 <= max_bytes <= 16 << 20:
            raise ValueError("trusted adapter config bound is invalid")
        store = options.get("store")
        binding_loader = options.get("binding_loader")
        if store is None or not callable(getattr(store, "read", None)) or not callable(getattr(store, "replace", None)):
            raise ValueError("a ConfigMapStore is required")
        # Keep only bounded, non-secret settings.  The namespace is validated
        # above; max_config_bytes is retained for A0's file-store implementation.
        self.namespace = namespace
        self.max_config_bytes = max_bytes
        self.production = None
        if not callable(binding_loader):
            self.production = ProductionLaunchProvisioner(config, options, store)
            # The base class still supplies the common request validation and
            # ConfigMap store. Production methods below do the real work.
            binding_loader = lambda _request: {}
        super().__init__(
            store=store,
            binding_loader=binding_loader,
            runtime_configmap=config.get("runtime_configmap", "runtime-config"),
            gates_configmap=config.get("gates_configmap", "gates-config"),
        )

    def prepare(self, input):
        request = LaunchInput.from_mapping(input, phase="prepare")
        return self.production.prepare(request) if self.production else super().prepare(input)

    def wire(self, input):
        request = LaunchInput.from_mapping(input, phase="wire")
        return self.production.wire(request) if self.production else super().wire(input)

    def observe(self, input):
        request = LaunchInput.from_mapping(input, phase="observe")
        return self.production.observe(request) if self.production else super().observe(input)

    def capability(self, input):
        request = LaunchInput.from_mapping(input, phase="capability")
        return self.production.capability(request) if self.production else super().capability(input)


# Short name retained for callers that imported the adapter during the initial
# handoff; A0 should use DeploymentLaunchAdapter in the launch worker.
LaunchAdapter = DeploymentLaunchAdapter
