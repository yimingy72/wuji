"""Public model configuration: intent, never arbitrary LiteLLM parameters."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from wuji_api.scope_policy import normalize_url

Amount = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$")]
Capacity = Annotated[int, Field(ge=1, le=9_007_199_254_740_991, strict=True)]


def normalize_base(value: str) -> str:
    normalized = normalize_url(value)
    if urlsplit(normalized).query:
        raise ValueError("model base URL cannot contain query parameters")
    return normalized.rstrip("/")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def database_text(cls, value):
        def inspect(item):
            if isinstance(item, str):
                if "\x00" in item:
                    raise ValueError("NUL is not supported")
                item.encode("utf-8")
            elif isinstance(item, dict):
                for child in item.values(): inspect(child)
            elif isinstance(item, list):
                for child in item: inspect(child)
        inspect(value)
        return value


class ServiceConfig(StrictModel):
    protocol: Literal["openai", "anthropic"]
    base_url: str = Field(min_length=1, max_length=2048)

    @field_validator("base_url")
    @classmethod
    def base(cls, value):
        return normalize_base(value)


class ModelPricing(StrictModel):
    source: str = Field(min_length=1, max_length=500)
    input_per_million: Amount
    output_per_million: Amount
    cache_mode: Literal["standard_input", "separate"]
    cache_read_per_million: Amount | None = None
    cache_creation_per_million: Amount | None = None

    @model_validator(mode="after")
    def complete_prices(self):
        if Decimal(self.input_per_million) == 0 and Decimal(self.output_per_million) == 0:
            raise ValueError("zero-cost budget exemption is not supported in this release")
        separate = (self.cache_read_per_million, self.cache_creation_per_million)
        if self.cache_mode == "separate" and any(v is None for v in separate):
            raise ValueError("separate cache pricing must include both prices")
        if self.cache_mode == "standard_input" and any(v is not None for v in separate):
            raise ValueError("standard cache pricing uses the input price")
        return self


class ProfileConfig(StrictModel):
    service_version_id: UUID
    model_id: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    context_window: Capacity | None = None
    max_output_tokens: Capacity | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=60, strict=True)
    pricing: ModelPricing | None = None

    @model_validator(mode="after")
    def capacity(self):
        if self.context_window and self.max_output_tokens and self.max_output_tokens > self.context_window:
            raise ValueError("output capacity exceeds context capacity")
        return self


class ServiceVersionRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    config: ServiceConfig
    api_key: SecretStr = Field(min_length=1, max_length=4096, json_schema_extra={"writeOnly": True})

    @field_validator("api_key")
    @classmethod
    def literal_secret(cls, value):
        raw = value.get_secret_value()
        if raw != raw.strip() or any(ord(c) < 32 for c in raw) or raw.startswith("os.environ/"):
            raise ValueError("API key must be a literal credential")
        return value


class ProfileVersionRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    config: ProfileConfig


class ModelVersionCommand(StrictModel):
    action: Literal["publish", "retire", "revoke"]
    expected_version: Capacity


class ModelCheckRequest(StrictModel):
    pass


class TenantResponse(StrictModel):
    id: UUID
    name: str
    permissions: list[Literal["model.config.read", "model.config.write"]]


class TenantPage(StrictModel):
    items: list[TenantResponse] = Field(max_length=100)
    next_cursor: str | None


class ModelDefinitionResponse(StrictModel):
    id: UUID
    tenant_id: UUID
    kind: Literal["service", "profile"]
    name: str
    created_at: datetime


class ModelDefinitionPage(StrictModel):
    items: list[ModelDefinitionResponse] = Field(max_length=100)
    next_cursor: str | None


class ModelVersionResponse(StrictModel):
    id: UUID
    tenant_id: UUID
    definition_id: UUID
    kind: Literal["service", "profile"]
    number: Capacity
    name: str
    config: ServiceConfig | ProfileConfig
    state: Literal["draft", "published", "retired", "revoked"]
    state_revision: Capacity
    sync_state: Literal["pending", "synced", "failed", "unknown"]
    created_at: datetime


class ModelVersionPage(StrictModel):
    items: list[ModelVersionResponse] = Field(max_length=100)
    next_cursor: str | None


class ModelOperationResult(StrictModel):
    error_code: str | None = None
    usage: None = None
    cost_usd: None = None


class ModelOperationResponse(StrictModel):
    id: UUID
    kind: Literal["create_service", "create_profile", "check", "publish", "retire", "revoke"]
    version_id: UUID
    state: Literal["prepared", "sent", "succeeded", "failed", "unknown"]
    result: ModelOperationResult
    created_at: datetime
    updated_at: datetime


def public_model(model, row):
    return model.model_validate({key: row[key] for key in model.model_fields if key in row})
