"""Task command request and public read-model DTOs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wuji_api.scopes import ScopeBindingModel, TaskDraftRequest
from wuji_api.task_creation import CreationConfigSnapshot


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: UUID
    input_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft: TaskDraftRequest


class TaskControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["start", "pause", "resume", "cancel"]
    expected_version: int = Field(ge=1, le=9_007_199_254_740_991)

    @field_validator("expected_version", mode="before")
    @classmethod
    def require_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("expected_version must be a JSON integer")
        return value


class ExecutionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_calls: int = Field(ge=0, le=9_007_199_254_740_991)
    unknown_calls: int = Field(ge=0, le=9_007_199_254_740_991)
    egress_state: Literal["not_granted"]


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str = Field(min_length=1, max_length=120)
    target_url: str = Field(min_length=1, max_length=2048)
    scope: ScopeBindingModel
    version: int = Field(ge=1, le=9_007_199_254_740_991)
    state: Literal["queued", "cancelled"]
    cleanup_state: Literal["not_required"]
    execution: ExecutionSummaryResponse
    allowed_actions: list[Literal["cancel"]] = Field(max_length=1)
    assessment_outcome: Literal["not_assessed"]
    stop_reason: Literal["user_cancelled"] | None
    created_at: datetime
    updated_at: datetime


class TaskAuthorizationBindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authorization_id: UUID
    version: int = Field(ge=1)
    hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class WebExecutionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_calls: int = Field(ge=0)
    unknown_calls: int = Field(ge=0)
    egress_state: Literal["not_granted", "fixture_only", "revoking", "revoked", "unknown"]


class WebTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_kind: Literal["web_assessment"] = "web_assessment"
    id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str = Field(min_length=1,max_length=120)
    target_url: str = Field(min_length=1,max_length=2048)
    scope: TaskAuthorizationBindingResponse
    version: int = Field(ge=1,le=9_007_199_254_740_991)
    state: Literal["ready","provisioning","running","completing","completed","cancelling","cancelled","reconciling"]
    cleanup_state: Literal["not_required","pending","running","completed","failed","unknown"]
    execution: WebExecutionSummaryResponse
    allowed_actions: list[Literal["start","cancel"]] = Field(max_length=2)
    assessment_outcome: Literal["not_assessed","complete","partial","inconclusive"]
    stop_reason: str | None
    creation_config: CreationConfigSnapshot
    start_blockers: list[str] = Field(default_factory=list,max_length=20)
    created_at: datetime
    updated_at: datetime


class TaskPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TaskResponse | WebTaskResponse] = Field(max_length=100)
    next_cursor: str | None


class TaskSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskResponse | WebTaskResponse
    event_cursor: str = Field(min_length=1, max_length=512)


class CommandReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: UUID
    idempotency_key: UUID
    kind: Literal["create", "start", "cancel"]
    disposition: Literal["accepted"]
    project_id: UUID
    task_id: UUID
    accepted_at: datetime
    accepted_task_version: int = Field(ge=1, le=9_007_199_254_740_991)
    request_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class TaskEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    event_id: UUID
    cursor: str = Field(min_length=1, max_length=512)
    tenant_id: UUID
    project_id: UUID
    task_id: UUID
    aggregate_version: int = Field(ge=1, le=9_007_199_254_740_991)
    type: Literal["task.changed"]
    occurred_at: datetime
    trace_id: UUID
    summary: str = Field(min_length=1, max_length=500)


class EventPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TaskEventResponse] = Field(max_length=100)
    next_cursor: str = Field(min_length=1, max_length=512)
    has_more: bool


def command_request_digest(
    *, kind: str, project_id: UUID, task_id: UUID | None, request: Mapping[str, Any]
) -> str:
    canonical = {
        "kind": kind,
        "project_id": str(project_id),
        "request": dict(request),
        "task_id": None if task_id is None else str(task_id),
    }
    encoded = json.dumps(
        canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(b"wuji-command-v1\n" + encoded).hexdigest()
