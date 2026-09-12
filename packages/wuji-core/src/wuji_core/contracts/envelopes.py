"""Trusted runtime envelopes and untrusted Agent payloads."""

from typing import Self

from pydantic import model_validator

from wuji_core.contracts import generated as _wire
from wuji_core.contracts.generated import (
    AgentPayload,
    BlobRef,
    CaptureCompleteness,
    CaptureEnvelope,
    EvidenceOrigin,
    EvidenceReceipt as GeneratedEvidenceReceipt,
    EvidenceReceiptStatus,
    ErrorCode,
    ErrorResponse,
    ReasonDecision,
    ReasonDecisionPayload,
    ResultEnvelope,
    ResultReceipt,
    ResultReceiptStatus,
    RunIdentity,
    WorkerAssignment,
)


class EvidenceReceipt(GeneratedEvidenceReceipt):
    """Apply OpenAPI's status/reference conditional not emitted by codegen."""

    @model_validator(mode="after")
    def validate_published_observation(self) -> Self:
        published = self.status in {
            EvidenceReceiptStatus.accepted,
            EvidenceReceiptStatus.historical_only,
        }
        if published != (self.observation_ref is not None):
            raise ValueError("published evidence must reference its observation only")
        if (
            self.observation_ref is not None
            and self.observation_ref.entity_type.value != "observation"
        ):
            raise ValueError("evidence receipt must reference an observation")
        return self


EvidenceReceipt.model_rebuild(_types_namespace=vars(_wire))


__all__ = [
    "AgentPayload",
    "BlobRef",
    "CaptureCompleteness",
    "CaptureEnvelope",
    "EvidenceOrigin",
    "EvidenceReceipt",
    "EvidenceReceiptStatus",
    "ErrorCode",
    "ErrorResponse",
    "ReasonDecision",
    "ReasonDecisionPayload",
    "ResultEnvelope",
    "ResultReceipt",
    "ResultReceiptStatus",
    "RunIdentity",
    "WorkerAssignment",
]
