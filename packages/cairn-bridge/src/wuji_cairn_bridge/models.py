from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Literal, Protocol
from uuid import UUID

from cairn.server.models import CreateProjectRequest
from wuji_task_runtime import ExecutionPermit, RuntimeObservation, TaskRuntimeConfig

from .errors import InvalidBridgeInput


def require_uuid(value, name: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidBridgeInput(f"{name} must be a UUID")


def native_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise InvalidBridgeInput("invalid native resource identifier")
    return value


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class TaskKey:
    tenant_id: UUID
    project_id: UUID
    task_id: UUID

    def __post_init__(self):
        for name in ("tenant_id", "project_id", "task_id"):
            require_uuid(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ExplorationInput:
    key: TaskKey
    title: str
    origin: str
    goal: str
    bootstrap_enabled: bool = True

    def to_native(self) -> CreateProjectRequest:
        if not isinstance(self.key, TaskKey) or type(self.bootstrap_enabled) is not bool:
            raise InvalidBridgeInput("invalid exploration input")
        try:
            return CreateProjectRequest(title=self.title, origin=self.origin, goal=self.goal, bootstrap_enabled=self.bootstrap_enabled)
        except Exception:
            raise InvalidBridgeInput("invalid native project input") from None

    @property
    def request_digest(self) -> str:
        return digest(self.to_native().model_dump(mode="json", exclude_none=True))


@dataclass(frozen=True, slots=True)
class DispatchContext:
    key: TaskKey
    runtime_config: TaskRuntimeConfig
    permit: ExecutionPermit | None
    observation: RuntimeObservation | None
    control_state: str
    execution_ready: bool = False
    active_agent_run_ids: frozenset[UUID] = frozenset()


class ControlSource(Protocol):
    """Trusted Task storage; a model or public request must not supply this state."""

    def current(self, key: TaskKey) -> DispatchContext | None: ...


@dataclass(frozen=True, slots=True)
class AgentResult:
    key: TaskKey
    operation_id: UUID
    agent_run_id: UUID
    intent_id: str
    description: str
    runtime_attempt: int
    execution_epoch: int
    scope_digest: str
    config_digest: str

    def __post_init__(self):
        if not isinstance(self.key, TaskKey):
            raise InvalidBridgeInput("result Task identity is required")
        require_uuid(self.operation_id, "operation_id")
        require_uuid(self.agent_run_id, "agent_run_id")
        native_id(self.intent_id)
        if not isinstance(self.description, str) or not self.description.strip():
            raise InvalidBridgeInput("result description is required")
        object.__setattr__(self, "description", self.description.strip())
        for name in ("runtime_attempt", "execution_epoch"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise InvalidBridgeInput(f"{name} must be a positive integer")
        for name in ("scope_digest", "config_digest"):
            if not isinstance(getattr(self, name), str) or not re.fullmatch(r"[a-f0-9]{64}", getattr(self, name)):
                raise InvalidBridgeInput(f"{name} must be a SHA-256 digest")

    def request_digest(self, server_id: UUID, project_id: str) -> str:
        return digest({"result": asdict(self), "server_id": str(server_id), "native_project_id": native_id(project_id)})


BindingState = Literal["pending", "sent", "bound", "rejected", "unknown"]
ResultState = Literal["pending", "sent", "applied", "rejected", "unknown", "conflict"]


@dataclass(frozen=True, slots=True)
class BindingRecord:
    key: TaskKey
    server_id: UUID
    request_digest: str
    state: BindingState
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResultRecord:
    result: AgentResult
    server_id: UUID
    project_id: str
    request_digest: str
    state: ResultState
    fact_id: str | None = None
