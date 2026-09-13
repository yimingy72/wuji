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
            raise PermitDenied("current start permission is unavailable") from None
        return validate_execution_permit(config, permit, self.clock())

    def _check_resources(self, config: TaskRuntimeConfig) -> None:
        resources = [
            ("agent_config", "ConfigMap"), ("kali_config", "ConfigMap"),
            ("agent_auth", "Secret"), ("kali_auth", "Secret"),
            ("agent_state", "PersistentVolumeClaim"), ("kali_work", "PersistentVolumeClaim"),
        ]
        if config.kali_receipts_enabled:
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
        if status.get("phase") in {"Failed", "Succeeded"}:
            raise RuntimeConflict("runtime generation ended; do not restart it implicitly")
        ready_names = {
            item.get("name") for item in status.get("containerStatuses", [])
            if item.get("ready") is True and item.get("state", {}).get("running") is not None
        }
        pod_ready = any(
            item.get("type") == "Ready" and item.get("status") == "True"
            for item in status.get("conditions", [])
        )
        infrastructure_ready = status.get("phase") == "Running" and pod_ready and ready_names == {"agent", "kali"}
        return RuntimeObservation("ready" if infrastructure_ready else "provisioning", config.pod_name, uid)

    def stop(self, config: TaskRuntimeConfig, pod_uid: str) -> RuntimeObservation:
        if not isinstance(pod_uid, str) or not pod_uid:
            raise OwnershipError("a previously observed Pod UID is required")
        pod = self.pods.read_pod(config.namespace, config.pod_name)
        if pod is None:
            return RuntimeObservation("stopped", config.pod_name, pod_uid)
        verify_pod_ownership(pod, config, require_template=False, expected_uid=pod_uid)
        metadata = pod["metadata"]
        if metadata.get("deletionTimestamp"):
            return RuntimeObservation("stopping", config.pod_name, pod_uid)
        version = metadata.get("resourceVersion")
        if not isinstance(version, str) or not version:
            raise OwnershipError("resourceVersion is required for conditional deletion")
        accepted = self.pods.delete_pod(
            config.namespace, config.pod_name, uid=pod_uid, resource_version=version,
        )
        return RuntimeObservation("stopping" if accepted else "stopped", config.pod_name, pod_uid)
