"""Immutable internal configuration, not a public authorization request DTO."""

from __future__ import annotations

import hashlib
import json
import re
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import InvalidOperation
from typing import Literal
from uuid import UUID

from kubernetes.utils.quantity import parse_quantity

from .errors import InvalidRuntimeConfig, PermitDenied

MANAGED_BY = "wuji-task-runtime-controller"
LABEL_MANAGED_BY = "app.kubernetes.io/managed-by"
LABEL_TASK = "wuji.dev/task-id"
LABEL_TENANT = "wuji.dev/tenant-id"
LABEL_ATTEMPT = "wuji.dev/runtime-attempt"
ANNOTATION_EPOCH = "wuji.dev/execution-epoch"
ANNOTATION_SCOPE = "wuji.dev/scope-digest"
ANNOTATION_CONFIG = "wuji.dev/config-digest"
ANNOTATION_TEMPLATE = "wuji.dev/template-digest"
ANNOTATION_TASK = "wuji.dev/task-id"
ANNOTATION_TENANT = "wuji.dev/tenant-id"

_DNS_LABEL = re.compile(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}\Z")
_LABEL_VALUE = re.compile(r"[A-Za-z0-9](?:[-A-Za-z0-9_.]{0,61}[A-Za-z0-9])?\Z")


def _positive_integer(value: int, name: str, maximum: int = 2_147_483_647) -> None:
    if type(value) is not int or not 0 < value <= maximum:
        raise InvalidRuntimeConfig(f"{name} must be a positive bounded integer")


def _identity(value: UUID | str, name: str) -> None:
    if isinstance(value, UUID):
        return
    if (not isinstance(value, str) or not 1 <= len(value) <= 256
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise InvalidRuntimeConfig(f"{name} must be a UUID or a bounded opaque identifier")


def _identity_label(value: UUID | str) -> str:
    text = str(value)
    if _LABEL_VALUE.fullmatch(text):
        return text
    return "id-" + hashlib.sha256(text.encode()).hexdigest()[:40]


def _digest(value: str, name: str) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise InvalidRuntimeConfig(f"{name} must be a lowercase SHA-256 digest")


def _quantity(value: str, name: str):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise InvalidRuntimeConfig(f"{name} must be a Kubernetes resource quantity")
    try:
        quantity = parse_quantity(value)
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("not positive")
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise InvalidRuntimeConfig(f"{name} must be a positive resource quantity") from exc
    return quantity


@dataclass(frozen=True, slots=True)
class ContainerResources:
    cpu_request: str
    memory_request: str
    cpu_limit: str
    memory_limit: str

    def __post_init__(self) -> None:
        for resource in ("cpu", "memory"):
            request = _quantity(getattr(self, f"{resource}_request"), f"{resource}_request")
            limit = _quantity(getattr(self, f"{resource}_limit"), f"{resource}_limit")
            if request > limit:
                raise InvalidRuntimeConfig(f"{resource} request exceeds its limit")

    def as_pod_resources(self) -> dict:
        return {
            "requests": {"cpu": self.cpu_request, "memory": self.memory_request},
            "limits": {"cpu": self.cpu_limit, "memory": self.memory_limit},
        }


@dataclass(frozen=True, slots=True)
class CapturePolicy:
    max_request_body_bytes: int
    max_response_body_bytes: int
    pcap_segment_bytes: int
    max_session_bytes: int
    max_items: int
    part_read_chunk_bytes: int
    drain_timeout_seconds: float
    seal_timeout_seconds: float

    def __post_init__(self) -> None:
        for name, maximum in (
            ("max_request_body_bytes", 8_388_608),
            ("max_response_body_bytes", 8_388_608),
            ("pcap_segment_bytes", 67_108_864),
            ("max_session_bytes", 1_099_511_627_776),
            ("max_items", 1_000_000),
            ("part_read_chunk_bytes", 8_388_608),
        ):
            _positive_integer(getattr(self, name), name, maximum)
        if self.pcap_segment_bytes % 1_000_000:
            raise InvalidRuntimeConfig("pcap_segment_bytes must be a whole tcpdump decimal megabyte")
        for name in ("drain_timeout_seconds", "seal_timeout_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InvalidRuntimeConfig(f"{name} must be a finite positive number")
            if not math.isfinite(value) or not 0 < value <= 300:
                raise InvalidRuntimeConfig(f"{name} must be at most 300 seconds")


@dataclass(frozen=True, slots=True)
class TaskRuntimeConfig:
    tenant_id: UUID | str
    task_id: UUID | str
    namespace: str
    runtime_attempt: int
    execution_epoch: int
    scope_digest: str
    config_digest: str
    agent_image: str
    kali_image: str
    agent_resources: ContainerResources
    kali_resources: ContainerResources
    tmp_size_limit: str
    pod_deadline_seconds: int
    expose_pod_identity: bool = False
    kali_receipts_enabled: bool = False
    template_version: Literal["legacy-v1", "core-ctf-v1"] = "legacy-v1"
    capture_image: str | None = None
    capture_resources: ContainerResources | None = None
    capture_policy: CapturePolicy | None = None

    def __post_init__(self) -> None:
        _identity(self.tenant_id, "tenant_id")
        _identity(self.task_id, "task_id")
        if type(self.expose_pod_identity) is not bool:
            raise InvalidRuntimeConfig("expose_pod_identity must be a boolean")
        if type(self.kali_receipts_enabled) is not bool:
            raise InvalidRuntimeConfig("kali_receipts_enabled must be a boolean")
        if self.template_version not in {"legacy-v1", "core-ctf-v1"}:
            raise InvalidRuntimeConfig("template_version is not supported")
        if not isinstance(self.namespace, str) or not _DNS_LABEL.fullmatch(self.namespace):
            raise InvalidRuntimeConfig("namespace must be a DNS label")
        _positive_integer(self.runtime_attempt, "runtime_attempt")
        _positive_integer(self.execution_epoch, "execution_epoch", 9_007_199_254_740_991)
        _positive_integer(self.pod_deadline_seconds, "pod_deadline_seconds")
        _digest(self.scope_digest, "scope_digest")
        _digest(self.config_digest, "config_digest")
        for role in ("agent", "kali"):
            image = getattr(self, f"{role}_image")
            if not isinstance(image, str) or not _IMAGE.fullmatch(image):
                raise InvalidRuntimeConfig(f"{role}_image must use an immutable sha256 reference")
            if not isinstance(getattr(self, f"{role}_resources"), ContainerResources):
                raise InvalidRuntimeConfig(f"{role}_resources must be ContainerResources")
        if self.template_version == "legacy-v1":
            if (
                self.capture_image is not None
                or self.capture_resources is not None
                or self.capture_policy is not None
            ):
                raise InvalidRuntimeConfig("legacy-v1 cannot configure capture")
        else:
            if not isinstance(self.capture_image, str) or not _IMAGE.fullmatch(self.capture_image):
                raise InvalidRuntimeConfig("capture_image must use an immutable sha256 reference")
            if not isinstance(self.capture_resources, ContainerResources):
                raise InvalidRuntimeConfig("capture_resources must be ContainerResources")
            if not isinstance(self.capture_policy, CapturePolicy):
                raise InvalidRuntimeConfig("capture_policy must be CapturePolicy")
        _quantity(self.tmp_size_limit, "tmp_size_limit")

    @property
    def task_prefix(self) -> str:
        if isinstance(self.task_id, UUID):
            return f"wuji-task-{self.task_id.hex}"
        # Kubernetes names are derived infrastructure identifiers. The original
        # domain identity is retained in the config and ownership annotations.
        identity = json.dumps([str(self.tenant_id), self.task_id], separators=(",", ":"))
        return "wuji-task-v-" + hashlib.sha256(identity.encode()).hexdigest()[:32]

    @property
    def pod_name(self) -> str:
        return f"{self.task_prefix}-a{self.runtime_attempt}"

    @property
    def resource_names(self) -> dict[str, str]:
        # Every runtime attempt owns its own ConfigMaps, Secrets and volumes.
        # Sharing the previous attempt's agent state would let a new generation
        # present a different receiver identity against persisted durable state,
        # which the supervisor inbox correctly refuses (RECEIVER_IDENTITY_CONFLICT).
        return {
            key: f"{self.task_prefix}-a{self.runtime_attempt}-{suffix}"
            for key, suffix in (
                ("agent_config", "agent-config"), ("kali_config", "kali-config"),
                ("agent_auth", "agent-auth"), ("kali_auth", "kali-auth"),
                ("agent_state", "agent-state"), ("kali_work", "kali-work"),
                ("kali_receipts", "kali-receipts"),
                ("capture_auth", "capture-auth"),
                ("capture_evidence", "capture-evidence"),
            )
        }

    @property
    def identity_labels(self) -> dict[str, str]:
        return {
            LABEL_MANAGED_BY: MANAGED_BY,
            LABEL_TASK: _identity_label(self.task_id),
            LABEL_TENANT: _identity_label(self.tenant_id),
            LABEL_ATTEMPT: str(self.runtime_attempt),
        }

    @property
    def template_digest(self) -> str:
        value = asdict(self)
        value["tenant_id"] = str(self.tenant_id)
        value["task_id"] = str(self.task_id)
        if not self.expose_pod_identity:
            # Preserve the existing UUID-based template digest by default.
            value.pop("expose_pod_identity")
        if not self.kali_receipts_enabled:
            value.pop("kali_receipts_enabled")
        if self.template_version == "legacy-v1":
            # These fields did not exist in the original two-container
            # serialization. Omitting their defaults keeps every old digest
            # stable while giving the new template an explicit version.
            value.pop("template_version")
            value.pop("capture_image")
            value.pop("capture_resources")
            value.pop("capture_policy")
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def annotations(self) -> dict[str, str]:
        return {
            **self.ownership_annotations,
            ANNOTATION_EPOCH: str(self.execution_epoch),
            ANNOTATION_SCOPE: self.scope_digest,
            ANNOTATION_CONFIG: self.config_digest,
            ANNOTATION_TEMPLATE: self.template_digest,
        }

    @property
    def ownership_annotations(self) -> dict[str, str]:
        if isinstance(self.task_id, UUID) and isinstance(self.tenant_id, UUID):
            return {}
        return {ANNOTATION_TASK: str(self.task_id), ANNOTATION_TENANT: str(self.tenant_id)}


@dataclass(frozen=True, slots=True)
class ExecutionPermit:
    tenant_id: UUID | str
    task_id: UUID | str
    runtime_attempt: int
    execution_epoch: int
    scope_digest: str
    config_digest: str
    start_command_id: UUID | str
    expires_at: datetime

    def __post_init__(self) -> None:
        _identity(self.tenant_id, "tenant_id")
        _identity(self.task_id, "task_id")
        _identity(self.start_command_id, "start_command_id")
        _positive_integer(self.runtime_attempt, "runtime_attempt")
        _positive_integer(self.execution_epoch, "execution_epoch", 9_007_199_254_740_991)
        _digest(self.scope_digest, "scope_digest")
        _digest(self.config_digest, "config_digest")
        if not isinstance(self.expires_at, datetime) or self.expires_at.utcoffset() is None:
            raise InvalidRuntimeConfig("expires_at must be a timezone-aware datetime")


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    state: Literal["provisioning", "ready", "stopping", "stopped"]
    pod_name: str
    pod_uid: str | None
    reason: str | None = None
    code: str | None = None


def validate_execution_permit(config: TaskRuntimeConfig, permit: ExecutionPermit | None, now: datetime) -> ExecutionPermit:
    """Shared binding check; the caller still obtains permission from trusted storage."""
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise PermitDenied("controller clock must include a timezone", code="permit_clock_invalid")
    if not isinstance(permit, ExecutionPermit):
        raise PermitDenied("current start permission is missing", code="permit_missing")
    if permit.expires_at <= now:
        # The attempt window is activated_at + the published max_elapsed_seconds.
        # Only a new runtime attempt can restore permission.
        raise PermitDenied("current start permission has expired", code="permit_expired")
    for field in ("tenant_id", "task_id", "runtime_attempt", "execution_epoch", "scope_digest", "config_digest"):
        if getattr(permit, field) != getattr(config, field):
            raise PermitDenied(f"current permission does not match {field}", code="permit_binding_mismatch")
    return permit
