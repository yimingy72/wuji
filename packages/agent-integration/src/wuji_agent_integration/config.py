"""Validated, non-secret model configuration for the P0 probe."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Protocol(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


OPENAI_BASE_URL = "https://ai-api-gateway.app.baizhi.cloud/api/openai"
ANTHROPIC_BASE_URL = "https://ai-api-gateway.app.baizhi.cloud/api/anthropic"
PROBE_MODEL_ID = "qwen-flash"
MAX_OUTPUT_TOKENS = 256


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Public model settings. Credentials are deliberately absent."""

    protocol: Protocol
    base_url: str
    model_id: str
    timeout_seconds: float
    max_output_tokens: int

    def __post_init__(self) -> None:
        if not isinstance(self.protocol, Protocol):
            object.__setattr__(self, "protocol", Protocol(self.protocol))
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS")
        if self.base_url.endswith("/"):
            raise ValueError("base_url must not have a trailing slash")
        if not self.model_id or len(self.model_id) > 128:
            raise ValueError("model_id is invalid")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= self.max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError(f"max_output_tokens must be between 1 and {MAX_OUTPUT_TOKENS}")

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["protocol"] = self.protocol.value
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ModelConfig:
        expected = {"protocol", "base_url", "model_id", "timeout_seconds", "max_output_tokens"}
        if set(payload) != expected:
            raise ValueError("model configuration fields are invalid")
        return cls(
            protocol=Protocol(payload["protocol"]),
            base_url=str(payload["base_url"]),
            model_id=str(payload["model_id"]),
            timeout_seconds=float(payload["timeout_seconds"]),
            max_output_tokens=int(payload["max_output_tokens"]),
        )


def fixed_probe_configs(timeout_seconds: float = 20.0) -> tuple[ModelConfig, ModelConfig]:
    """Return the two approved configurations without doing model discovery."""

    return (
        ModelConfig(Protocol.OPENAI, OPENAI_BASE_URL, PROBE_MODEL_ID, timeout_seconds, MAX_OUTPUT_TOKENS),
        ModelConfig(Protocol.ANTHROPIC, ANTHROPIC_BASE_URL, PROBE_MODEL_ID, timeout_seconds, MAX_OUTPUT_TOKENS),
    )
