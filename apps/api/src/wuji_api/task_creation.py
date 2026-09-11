"""Public creation requests and deterministic preview validation."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from wuji_api.drafts import DraftContent, NewDraftContent, GoalTemplateReference, canonical_content
from wuji_api.task_authorization import TaskAuthorization
from wuji_api.model_config import ProfileConfig
from wuji_api.task_authorization import authorization_digest, permits_url
from wuji_api.scenario_profiles import valid_template
import hashlib
class CreationBlocked(Exception): pass
class CreationPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: UUID
    draft_version: int = Field(ge=1,strict=True)
class ScopeConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: Literal[True]
    @field_validator("accepted", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True: raise ValueError("explicit creator confirmation required")
        return value
    authorization_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
class NewCreateTaskRequest(CreationPreviewRequest):
    creation_kind: Literal["saved_web_draft"]
    preview_id: UUID
    input_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope_confirmation: ScopeConfirmation
class CreationBlocker(BaseModel):
    code: str
    message: str
class TaskCreationPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: UUID
    project_id: UUID
    start_available: Literal[False] = False
    draft_id: UUID
    draft_version: int
    normalized_content: DraftContent
    model_snapshot: dict | None
    input_digest: str
    authorization_digest: str
    can_create: bool
    blockers: list[CreationBlocker]
    created_at: datetime
    expires_at: datetime

def evaluate_creation(content, model, now):
    blockers=[]
    def block(code,message): blockers.append({"code":code,"message":message})
    if content.get("schema_version") != "2.0": block("LEGACY_DRAFT_REQUIRES_REVIEW","旧草稿需显式确认新版授权和完成条件")
    if content["scenario"] != "web_single": block("SCENARIO_DRAFT_ONLY","此场景目前仅支持保存草稿")
    if not content.get("name") or not content.get("objective") or not any(s.strip() for s in content.get("completion_criteria",[])): block("GOAL_INCOMPLETE","请填写名称、目标及完成条件")
    if not valid_template(content.get("goal_template"),content["scenario"]): block("TEMPLATE_UNAVAILABLE","模板版本不可用")
    if content.get("reference_ids") or content.get("runtime_profile_version_id"): block("UNSUPPORTED_REFERENCE","首批创建不支持此引用")
    if model is None: block("MODEL_UNAVAILABLE","请选择可用的已发布模型方案")
    if not content.get("budget_usd"): block("BUDGET_REQUIRED","请填写 USD 金额预算")
    scope=content.get("authorization")
    if scope is None: block("AUTHORIZATION_REQUIRED","请填写本任务授权")
    else:
        if not scope.get("valid_until") or datetime.fromisoformat(scope["valid_until"].replace("Z","+00:00")) <= now: block("AUTHORIZATION_EXPIRED","授权期限缺失或已过期")
        if not content.get("entry_url") or not permits_url(scope,content["entry_url"]): block("ENTRY_OUTSIDE_AUTHORIZATION","入口未被授权或已排除")
    return blockers, authorization_digest(scope)
def preview_digest(value):
    return hashlib.sha256(b"wuji-creation-preview-v1\n"+canonical_content(value)).hexdigest()


class SelectedModelSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    definition_id: UUID
    number: int = Field(ge=1)
    name: str
    state_revision: int = Field(ge=1)
    config: ProfileConfig


class CreationConfigSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    id: UUID
    scenario: Literal["web_single"]
    goal_template: GoalTemplateReference | None
    objective: str = Field(min_length=1,max_length=8000)
    completion_criteria: list[str] = Field(min_length=1,max_length=20)
    supplemental_hints: str = Field(max_length=8000)
    actual_input: NewDraftContent
    authorization: TaskAuthorization
    authorization_id: UUID
    authorization_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    model: SelectedModelSnapshot
    budget_usd: str
    created_by: UUID
    created_at: datetime
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
