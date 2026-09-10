"""Immutable internal configuration, not a public authorization request DTO."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import InvalidOperation
from typing import Literal
from uuid import UUID

from kubernetes.utils.quantity import parse_quantity

from .errors import InvalidRuntimeConfig

MANAGED_BY = "wuji-task-runtime-controller"
LABEL_MANAGED_BY = "app.kubernetes.io/managed-by"
LABEL_TASK = "wuji.dev/task-id"
LABEL_TENANT = "wuji.dev/tenant-id"
LABEL_ATTEMPT = "wuji.dev/runtime-attempt"
ANNOTATION_EPOCH = "wuji.dev/execution-epoch"
ANNOTATION_SCOPE = "wuji.dev/scope-digest"
ANNOTATION_CONFIG = "wuji.dev/config-digest"
ANNOTATION_TEMPLATE = "wuji.dev/template-digest"

_DNS_LABEL = re.compile(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}\Z")


def _positive_integer(value: int, name: str, maximum: int = 2_147_483_647) -> None:
    if type(value) is not int or not 0 < value <= maximum:
        raise InvalidRuntimeConfig(f"{name} must be a positive bounded integer")


def _uuid(value: UUID, name: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidRuntimeConfig(f"{name} must be a UUID")


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
class TaskRuntimeConfig:
    tenant_id: UUID
    task_id: UUID
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

    def __post_init__(self) -> None:
        _uuid(self.tenant_id, "tenant_id")
        _uuid(self.task_id, "task_id")
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
        _quantity(self.tmp_size_limit, "tmp_size_limit")

    @property
    def task_prefix(self) -> str:
        return f"wuji-task-{self.task_id.hex}"

    @property
    def pod_name(self) -> str:
        return f"{self.task_prefix}-a{self.runtime_attempt}"

    @property
    def resource_names(self) -> dict[str, str]:
        return {
            key: f"{self.task_prefix}-{suffix}"
            for key, suffix in (
                ("agent_config", "agent-config"), ("kali_config", "kali-config"),
                ("agent_auth", "agent-auth"), ("kali_auth", "kali-auth"),
                ("agent_state", "agent-state"), ("kali_work", "kali-work"),
            )
        }

    @property
    def identity_labels(self) -> dict[str, str]:
        return {
            LABEL_MANAGED_BY: MANAGED_BY,
            LABEL_TASK: str(self.task_id),
            LABEL_TENANT: str(self.tenant_id),
            LABEL_ATTEMPT: str(self.runtime_attempt),
        }

    @property
    def template_digest(self) -> str:
        value = asdict(self)
        value["tenant_id"] = str(self.tenant_id)
        value["task_id"] = str(self.task_id)
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def annotations(self) -> dict[str, str]:
        return {
            ANNOTATION_EPOCH: str(self.execution_epoch),
            ANNOTATION_SCOPE: self.scope_digest,
            ANNOTATION_CONFIG: self.config_digest,
            ANNOTATION_TEMPLATE: self.template_digest,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPermit:
    tenant_id: UUID
    task_id: UUID
    runtime_attempt: int
    execution_epoch: int
    scope_digest: str
    config_digest: str
    start_command_id: UUID
    expires_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.tenant_id, "tenant_id")
        _uuid(self.task_id, "task_id")
        _uuid(self.start_command_id, "start_command_id")
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
