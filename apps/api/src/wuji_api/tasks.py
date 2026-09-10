"""Task command request and public read-model DTOs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wuji_api.scopes import ScopeBindingModel, TaskDraftRequest


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: UUID
    input_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft: TaskDraftRequest


class TaskControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["pause", "resume", "cancel"]
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


class TaskPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TaskResponse] = Field(max_length=100)
    next_cursor: str | None


class TaskSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskResponse
    event_cursor: str = Field(min_length=1, max_length=512)


class CommandReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: UUID
    idempotency_key: UUID
    kind: Literal["create", "cancel"]
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
