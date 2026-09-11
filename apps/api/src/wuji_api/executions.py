"""Permission-filtered execution observations; no credential or storage locator fields."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from wuji_api.assessments import AssessmentReference

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class AgentRun(Strict):
    id: UUID
    phase: Literal["bootstrap", "reason", "explore"]
    intent_id: str | None
    worker_profile_id: str
    state: str
    result_state: str
    outcome: str | None
    created_at: datetime
    updated_at: datetime

class AgentRunPage(Strict):
    items: list[AgentRun] = Field(max_length=100)
    next_cursor: str | None

class ToolCall(Strict):
    id: UUID
    agent_run_id: UUID
    tool: str
    state: str
    args: dict
    result: dict | None
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime

class ToolCallPage(Strict):
    items: list[ToolCall] = Field(max_length=100)
    next_cursor: str | None

class Artifact(Strict):
    id: UUID
    tool_call_id: UUID | None
    kind: str
    name: str
    mime: str
    size: int = Field(ge=0)
    sha256: str
    state: str
    created_at: datetime

class ArtifactPage(Strict):
    items: list[Artifact] = Field(max_length=100)
    next_cursor: str | None

class GraphFact(Strict):
    id: str
    description: str

class GraphIntent(Strict):
    model_config = ConfigDict(extra="forbid",populate_by_name=True)
    id: str
    from_: list[str] = Field(alias="from")
    to: str | None
    description: str
    creator: str
    worker: str | None
    last_heartbeat_at: str | None
    created_at: str
    concluded_at: str | None

class GraphHint(Strict):
    id: str
    content: str
    creator: str
    created_at: str

class NativeGraph(Strict):
    project: dict
    facts: list[GraphFact]
    intents: list[GraphIntent]
    hints: list[GraphHint]

class BlackBoardSnapshot(Strict):
    state: Literal["pending", "available"]
    native_project_id: str | None
    graph: NativeGraph | None
    captured_at: datetime | None
    digest: str | None

class TaskResult(Strict):
    state: Literal["pending", "available"]
    goal_status: Literal["unknown", "met", "not_met"]
    summary: str
    limitations: list[str]
    artifact_ids: list[UUID]
    model_spend: str | None
    cost_state: str
    assessment: AssessmentReference | None = None
