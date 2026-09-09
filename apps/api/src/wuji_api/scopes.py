"""B1 scope request/response DTOs and boundary validation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from wuji_api.scope_policy import normalize_approved_scope


class LimitsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_total_requests: int = Field(ge=1, le=200)
    requests_per_second: Annotated[FiniteFloat, Field(gt=0, le=2)]
    max_concurrent_requests: int = Field(ge=1, le=2)
    request_timeout_seconds: int = Field(ge=1, le=10)
    max_response_bytes: int = Field(ge=1, le=1_048_576)
    max_runtime_seconds: int = Field(ge=1, le=600)

    @field_validator(
        "max_total_requests",
        "max_concurrent_requests",
        "request_timeout_seconds",
        "max_response_bytes",
        "max_runtime_seconds",
        mode="before",
    )
    @classmethod
    def require_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("integer limit must be a JSON integer")
        return value

    @field_validator("requests_per_second", mode="before")
    @classmethod
    def require_number(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("requests_per_second must be a JSON number")
        return value


class ScopeBindingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: UUID
    version: int = Field(ge=1, le=9_007_199_254_740_991)

    @field_validator("version", mode="before")
    @classmethod
    def require_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("version must be a JSON integer")
        return value


class TaskDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    scope: ScopeBindingModel
    target_url: str = Field(min_length=1, max_length=2048)
    tool: Literal["http_observe"]
    method: Literal["GET", "HEAD"]
    limits: LimitsModel

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class ApprovedScopeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding: ScopeBindingModel
    label: str = Field(min_length=1, max_length=120)
    valid_until: datetime
    origins: list[str] = Field(max_length=20)
    allowed_path_prefixes: list[str] = Field(max_length=100)
    excluded_path_prefixes: list[str] = Field(max_length=100)
    allowed_methods: list[Literal["GET", "HEAD"]] = Field(max_length=2)
    limits: LimitsModel


class ScopePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ApprovedScopeResponse] = Field(max_length=100)
    next_cursor: str | None


class PreviewBlockerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "MISSING_ADAPTER",
        "MISSING_IDENTITY",
        "SCOPE_DENIED",
        "AUTHORIZATION_EXPIRED",
        "CREATION_UNAVAILABLE",
    ]
    message: str = Field(min_length=1, max_length=300)


class TaskPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: UUID
    project_id: UUID
    draft: TaskDraftRequest
    input_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    effective_scope: ApprovedScopeResponse
    expires_at: datetime
    can_create: bool
    blockers: list[PreviewBlockerResponse] = Field(min_length=1, max_length=20)


class AuthorizationImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    project_id: UUID
    subject: str = Field(min_length=1, max_length=500)
    basis: str = Field(min_length=1, max_length=1000)
    approved_by: str = Field(min_length=1, max_length=320)
    valid_from: datetime
    valid_until: datetime

    @field_validator("subject", "basis", "approved_by")
    @classmethod
    def trim_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "AuthorizationImport":
        if self.valid_from.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("authorization timestamps must include a timezone")
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self


class ScopePolicyImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: UUID
    version: int = Field(ge=1, le=9_007_199_254_740_991)
    label: str = Field(min_length=1, max_length=120)
    origins: list[str] = Field(min_length=1, max_length=20)
    allowed_path_prefixes: list[str] = Field(min_length=1, max_length=100)
    excluded_path_prefixes: list[str] = Field(max_length=100)
    allowed_methods: list[Literal["GET", "HEAD"]] = Field(min_length=1, max_length=2)
    limits: LimitsModel

    @field_validator("version", mode="before")
    @classmethod
    def require_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("version must be a JSON integer")
        return value


class ScopeImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization: AuthorizationImport
    scope: ScopePolicyImport

    def normalized_scope(self) -> dict[str, Any]:
        return normalize_approved_scope(
            self.scope.model_dump(mode="json", exclude={"policy_id", "version"})
        )
