"""Reconcile infrastructure only; the API/dispatcher must separately admit execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import UUID

from .errors import (
    OwnershipError, PermitDenied, ResourceMissing, RuntimeConflict,
    RuntimeStateUnknown, RuntimeTransportError,
)
from .manifest import build_task_pod, verify_pod_ownership, verify_resource_ownership
from .models import ExecutionPermit, RuntimeObservation, TaskRuntimeConfig, validate_execution_permit


class PermitSource(Protocol):
    """Implemented by trusted control-plane storage, never by a caller-supplied flag."""

    def current(self, task_id: UUID | str) -> ExecutionPermit | None: ...


class PodClient(Protocol):
    def read_pod(self, namespace: str, name: str) -> dict | None: ...
    def list_task_pods(self, config: TaskRuntimeConfig) -> list[dict]: ...
    def read_resource(self, kind: str, namespace: str, name: str) -> dict | None: ...
    def create_pod(self, namespace: str, body: dict) -> dict: ...
    def patch_pod_deadline(
        self, namespace: str, name: str, *, uid: str, resource_version: str,
        active_deadline_seconds: int,
    ) -> dict: ...
    def delete_pod(self, namespace: str, name: str, *, uid: str, resource_version: str) -> bool: ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskRuntimeController:
    def __init__(self, pods: PodClient, permits: PermitSource, clock: Callable[[], datetime] = _utcnow):
        self.pods = pods
        self.permits = permits
        self.clock = clock

    def _require_permit(self, config: TaskRuntimeConfig) -> ExecutionPermit:
        try:
            permit = self.permits.current(config.task_id)
        except Exception:
            raise PermitDenied(
                "current start permission is unavailable", code="permit_unavailable"
            ) from None
        return validate_execution_permit(config, permit, self.clock())

    def _check_resources(self, config: TaskRuntimeConfig) -> None:
        resources = [
            ("agent_config", "ConfigMap"), ("kali_config", "ConfigMap"),
            ("agent_auth", "Secret"), ("kali_auth", "Secret"),
            ("agent_state", "PersistentVolumeClaim"), ("kali_work", "PersistentVolumeClaim"),
        ]
        if config.kali_receipts_enabled:
            resources.append(("kali_receipts", "PersistentVolumeClaim"))
        if config.template_version == "core-ctf-v1":
            resources.extend([
                ("capture_auth", "Secret"),
                ("capture_evidence", "PersistentVolumeClaim"),
            ])
            if not config.kali_receipts_enabled:
                resources.append(("kali_receipts", "PersistentVolumeClaim"))
        for key, kind in resources:
            name = config.resource_names[key]
            resource = self.pods.read_resource(kind, config.namespace, name)
            if resource is None:
                raise ResourceMissing(f"required {kind} is not present")
            verify_resource_ownership(resource, config)
            if resource.get("metadata", {}).get("name") != name:
                raise OwnershipError("resource identity does not match its requested name")

    def ensure(self, config: TaskRuntimeConfig) -> RuntimeObservation:
        self._require_permit(config)
        pod = self.pods.read_pod(config.namespace, config.pod_name)
        if pod is not None:
            verify_pod_ownership(pod, config)

        # The store must also provide an exclusive execution lease. This observation
        # is a conservative guard, not an atomic cluster-wide admission transaction.
        for other in self.pods.list_task_pods(config):
            verify_resource_ownership(other, config)
            if other.get("metadata", {}).get("name") != config.pod_name:
                raise RuntimeConflict("another runtime generation still exists; reconcile it before provisioning")

        if pod is None:
            self._check_resources(config)
            self._require_permit(config)
            try:
                pod = self.pods.create_pod(config.namespace, build_task_pod(config))
            except RuntimeTransportError as exc:
                if exc.status != 409:
                    raise
                pod = self.pods.read_pod(config.namespace, config.pod_name)
                if pod is None:
                    raise RuntimeStateUnknown("create-conflict-reconcile") from None
            verify_pod_ownership(pod, config)

        uid = pod["metadata"]["uid"]
        try:
            self._require_permit(config)
        except PermitDenied:
            stopped = self.stop(config, uid)
            return RuntimeObservation(stopped.state, stopped.pod_name, stopped.pod_uid, "permit_revoked")
        metadata = pod["metadata"]
        if metadata.get("deletionTimestamp"):
            return RuntimeObservation("stopping", config.pod_name, uid)
        status = pod.get("status", {})
        if config.template_version == "core-ctf-v1":
            init_statuses = status.get("initContainerStatuses", [])
            failed_init = any(
                item.get("state", {}).get("terminated", {}).get("exitCode") not in {None, 0}
                for item in init_statuses
            )
            terminated = {
                item.get("name")
                for item in status.get("containerStatuses", [])
                if item.get("state", {}).get("terminated") is not None
            }
            if failed_init or terminated or status.get("phase") in {"Failed", "Succeeded"}:
                code = (
                    "capture_enforcement_unavailable" if failed_init
                    else "capture_failed" if "capture" in terminated
                    else "runtime_container_terminated"
                )
                return RuntimeObservation(
                    "stopping", config.pod_name, uid, "runtime_failure", code
                )
        elif status.get("phase") in {"Failed", "Succeeded"}:
            raise RuntimeConflict("runtime generation ended; do not restart it implicitly")
        container_statuses = status.get("containerStatuses", [])
        ready_names = {
            item.get("name") for item in container_statuses
            if item.get("ready") is True and item.get("state", {}).get("running") is not None
        }
        pod_ready = any(
            item.get("type") == "Ready" and item.get("status") == "True"
            for item in status.get("conditions", [])
        )
        expected = {"agent", "kali"}
        init_ready = True
        if config.template_version == "core-ctf-v1":
            expected.add("capture")
            init_statuses = status.get("initContainerStatuses", [])
            init_ready = (
                {item.get("name") for item in init_statuses} == {"task-network-init"}
                and all(
                    item.get("state", {}).get("terminated", {}).get("exitCode") == 0
                    for item in init_statuses
                )
            )
        infrastructure_ready = (
            status.get("phase") == "Running"
            and pod_ready
            and {item.get("name") for item in container_statuses} == expected
            and ready_names == expected
            and init_ready
        )
        if infrastructure_ready and config.template_version == "core-ctf-v1":
            # M2b proves the local capture path. M2c must additionally bind the
            # Task capture registration before model work can be dispatched.
            return RuntimeObservation(
                "provisioning", config.pod_name, uid, "capture_registration_pending"
            )
        return RuntimeObservation("ready" if infrastructure_ready else "provisioning", config.pod_name, uid)

    def stop(self, config: TaskRuntimeConfig, pod_uid: str) -> RuntimeObservation:
        if not isinstance(pod_uid, str) or not pod_uid:
            raise OwnershipError("a previously observed Pod UID is required")
        pod = self.pods.read_pod(config.namespace, config.pod_name)
        if pod is None:
            if config.template_version == "core-ctf-v1":
                return RuntimeObservation(
                    "stopping", config.pod_name, pod_uid,
                    "Pod is absent without a persisted terminal observation",
                    "pod_terminal_unconfirmed",
                )
            return RuntimeObservation("stopped", config.pod_name, pod_uid)
        verify_pod_ownership(pod, config, require_template=False, expected_uid=pod_uid)
        metadata = pod["metadata"]
        if metadata.get("deletionTimestamp"):
            return RuntimeObservation("stopping", config.pod_name, pod_uid)
        if config.template_version == "core-ctf-v1":
            if self.core_terminal_observed(pod):
                return RuntimeObservation(
                    "stopped", config.pod_name, pod_uid, "container_terminal_observed"
                )
            version = metadata.get("resourceVersion")
            if not isinstance(version, str) or not version:
                raise OwnershipError("resourceVersion is required for conditional deadline update")
            patched = self.pods.patch_pod_deadline(
                config.namespace,
                config.pod_name,
                uid=pod_uid,
                resource_version=version,
                active_deadline_seconds=1,
            )
            verify_pod_ownership(
                patched, config, require_template=False, expected_uid=pod_uid
            )
            return RuntimeObservation(
                "stopping", config.pod_name, pod_uid, "pod_deadline_shortened"
            )
        version = metadata.get("resourceVersion")
        if not isinstance(version, str) or not version:
            raise OwnershipError("resourceVersion is required for conditional deletion")
        accepted = self.pods.delete_pod(
            config.namespace, config.pod_name, uid=pod_uid, resource_version=version,
        )
        return RuntimeObservation("stopping" if accepted else "stopped", config.pod_name, pod_uid)

    @staticmethod
    def core_terminal_states(pod: dict) -> dict[str, str] | None:
        status = pod.get("status") or {}
        if status.get("phase") not in {"Failed", "Succeeded"}:
            return None
        init_values = status.get("initContainerStatuses", [])
        if (
            {item.get("name") for item in init_values} != {"task-network-init"}
            or any(item.get("state", {}).get("terminated") is None for item in init_values)
        ):
            return None
        values = status.get("containerStatuses", [])
        if {item.get("name") for item in values} != {"agent", "kali", "capture"}:
            return None
        result = {}
        for item in values:
            if item.get("state", {}).get("terminated") is not None:
                result[item["name"]] = "terminated"
            elif (
                item.get("containerID") in {None, ""}
                and item.get("state", {}).get("waiting") is not None
                and item.get("restartCount", 0) == 0
                and item.get("started") in {None, False}
                and not (item.get("lastState") or {})
            ):
                result[item["name"]] = "not_started"
            else:
                return None
        return result

    @classmethod
    def core_terminal_observed(cls, pod: dict) -> bool:
        return cls.core_terminal_states(pod) is not None

    def delete_terminal(self, config: TaskRuntimeConfig, pod_uid: str) -> RuntimeObservation:
        if config.template_version != "core-ctf-v1":
            raise ValueError("terminal deletion is only defined for core-ctf-v1")
        pod = self.pods.read_pod(config.namespace, config.pod_name)
        if pod is None:
            return RuntimeObservation(
                "stopping", config.pod_name, pod_uid,
                "Pod disappeared before conditional terminal deletion",
                "pod_terminal_unconfirmed",
            )
        verify_pod_ownership(pod, config, require_template=False, expected_uid=pod_uid)
        if not self.core_terminal_observed(pod):
            return RuntimeObservation("stopping", config.pod_name, pod_uid)
        metadata = pod["metadata"]
        version = metadata.get("resourceVersion")
        if not isinstance(version, str) or not version:
            raise OwnershipError("resourceVersion is required for conditional deletion")
        self.pods.delete_pod(
            config.namespace, config.pod_name, uid=pod_uid, resource_version=version
        )
        return RuntimeObservation(
            "stopped", config.pod_name, pod_uid, "terminal_observation_persisted"
        )
