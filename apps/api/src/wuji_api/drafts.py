"""Incomplete user intent; saving a draft never authorizes execution."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wuji_api.scope_policy import normalize_origin, normalize_url

MAX_VERSION = 9_007_199_254_740_991
ShortText = Annotated[str, Field(max_length=2048)]


class DraftFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(default="", max_length=120)
    objective: str = Field(default="", max_length=8000)
    starting_point: str = Field(default="", max_length=8000)
    constraints: str = Field(default="", max_length=4000)
    reference_ids: list[UUID] = Field(default_factory=list, max_length=20)
    model_profile_version_id: UUID | None = None
    runtime_profile_version_id: UUID | None = None
    budget_usd: str | None = Field(default=None, pattern=r"^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$", json_schema_extra={"not": {"enum": ["0", "0.0", "0.00", "0.000", "0.0000", "0.00000", "0.000000"]}})

    @field_validator("budget_usd")
    @classmethod
    def positive_money(cls, value):
        if value is not None and Decimal(value) <= 0:
            raise ValueError("budget must be positive USD")
        if value is not None:
            return format(Decimal(value).normalize(), "f")
        return None


class CtfDraft(DraftFields):
    scenario: Literal["ctf"]
    challenge: str = Field(default="", max_length=8000)
    entry_url: str | None = Field(default=None, max_length=2048)

    @field_validator("entry_url")
    @classmethod
    def valid_url(cls, value):
        return normalize_url(value) if value is not None else None


class WebDraft(DraftFields):
    scenario: Literal["web_single"]
    entry_url: str | None = Field(default=None, max_length=2048)
    include_subdomains: bool = Field(default=False, strict=True)
    additional_origins: list[ShortText] = Field(default_factory=list, max_length=100)

    @field_validator("entry_url")
    @classmethod
    def valid_url(cls, value):
        return normalize_url(value) if value is not None else None

    @field_validator("additional_origins")
    @classmethod
    def valid_origins(cls, values):
        return list(dict.fromkeys(normalize_origin(value) for value in values))


class ComprehensiveDraft(DraftFields):
    scenario: Literal["comprehensive"]
    assets: list[ShortText] = Field(default_factory=list, max_length=100)
    access_notes: str = Field(default="", max_length=4000)


class ExerciseDraft(DraftFields):
    scenario: Literal["exercise"]
    organization_name: str = Field(default="", max_length=255)
    known_domains: list[Annotated[str, Field(max_length=253)]] = Field(default_factory=list, max_length=100)


class CodeAuditDraft(DraftFields):
    model_config = ConfigDict(json_schema_extra={"not": {
        "required": ["repository_url", "source_reference_id"],
        "properties": {"repository_url": {"type": "string"}, "source_reference_id": {"type": "string"}},
    }})
    scenario: Literal["code_audit"]
    repository_url: str | None = Field(default=None, max_length=2048)
    source_reference_id: UUID | None = None
    revision: str | None = Field(default=None, max_length=255)

    @field_validator("repository_url")
    @classmethod
    def valid_url(cls, value):
        return normalize_url(value) if value is not None else None

    @model_validator(mode="after")
    def one_source(self):
        if self.repository_url is not None and self.source_reference_id is not None:
            raise ValueError("choose repository or uploaded source")
        return self


class GoalTemplateReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1, strict=True)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class DraftFieldsV2(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal["2.0"]
    name: str = Field(default="", max_length=120)
    objective: str = Field(default="", max_length=8000)
    goal_template: GoalTemplateReference | None = None
    completion_criteria: list[Annotated[str, Field(max_length=1000)]] = Field(default_factory=list, max_length=20)
    supplemental_hints: str = Field(default="", max_length=8000)
    reference_ids: list[UUID] = Field(default_factory=list, max_length=20)
    model_profile_version_id: UUID | None = None
    runtime_profile_version_id: UUID | None = None
    budget_usd: str | None = Field(default=None, pattern=r"^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$")
    positive_money = field_validator("budget_usd")(classmethod(DraftFields.positive_money.__func__))


from wuji_api.task_authorization import TaskAuthorization

class CtfDraftV2(DraftFieldsV2):
    scenario: Literal["ctf"]
    challenge: str = Field(default="", max_length=8000)
    entry_url: str | None = Field(default=None, max_length=2048)
    valid_url = field_validator("entry_url")(classmethod(CtfDraft.valid_url.__func__))

class WebDraftV2(DraftFieldsV2):
    scenario: Literal["web_single"]
    entry_url: str | None = Field(default=None, max_length=2048)
    authorization: TaskAuthorization | None = None
    valid_url = field_validator("entry_url")(classmethod(WebDraft.valid_url.__func__))

class ComprehensiveDraftV2(DraftFieldsV2):
    scenario: Literal["comprehensive"]
    assets: list[ShortText] = Field(default_factory=list, max_length=100)
    access_notes: str = Field(default="", max_length=4000)

class ExerciseDraftV2(DraftFieldsV2):
    scenario: Literal["exercise"]
    organization_name: str = Field(default="", max_length=255)
    known_domains: list[Annotated[str, Field(max_length=253)]] = Field(default_factory=list, max_length=100)

class CodeAuditDraftV2(DraftFieldsV2):
    scenario: Literal["code_audit"]
    repository_url: str | None = Field(default=None, max_length=2048)
    source_reference_id: UUID | None = None
    revision: str | None = Field(default=None, max_length=255)
    valid_url = field_validator("repository_url")(classmethod(CodeAuditDraft.valid_url.__func__))
    one_source = model_validator(mode="after")(CodeAuditDraft.one_source)

LegacyDraftContent = Annotated[CtfDraft | WebDraft | ComprehensiveDraft | ExerciseDraft | CodeAuditDraft, Field(discriminator="scenario")]
NewDraftContent = Annotated[CtfDraftV2 | WebDraftV2 | ComprehensiveDraftV2 | ExerciseDraftV2 | CodeAuditDraftV2, Field(discriminator="scenario")]
DraftContent = LegacyDraftContent | NewDraftContent



def canonical_content(content: dict) -> bytes:
    def reject_nul(value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("NUL is not supported in draft text")
        if isinstance(value, dict):
            for item in value.values():
                reject_nul(item)
        elif isinstance(value, list):
            for item in value:
                reject_nul(item)
    reject_nul(content)
    return json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def content_digest(content: dict) -> str:
    return hashlib.sha256(b"wuji-draft-v1\n" + canonical_content(content)).hexdigest()


class SaveDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0, lt=MAX_VERSION, strict=True)
    content: DraftContent

    @model_validator(mode="after")
    def bounded_content(self):
        if len(canonical_content(self.content.model_dump(mode="json"))) > 65536:
            raise ValueError("draft content exceeds 64KiB")
        return self


class TaskDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    tenant_id: UUID
    project_id: UUID
    user_id: UUID
    version: int = Field(ge=1, le=MAX_VERSION)
    content: DraftContent
    selected_model_summary: dict | None = None
    last_created_task_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TaskDraftPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TaskDraftResponse] = Field(max_length=100)
    next_cursor: str | None = Field(max_length=512)
