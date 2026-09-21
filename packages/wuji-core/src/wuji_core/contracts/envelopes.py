"""Trusted runtime envelopes and untrusted Agent payloads."""

from typing import Self

from pydantic import model_validator

from wuji_core.contracts import generated as _wire
from wuji_core.contracts.generated import (
    AgentPayload,
    AgentPayloadV3 as GeneratedAgentPayloadV3,
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
    ResultEnvelopeV3,
    ResultReceipt,
    ResultReceiptStatus,
    RunIdentity,
    WorkerAssignment,
)


class AgentPayloadV3(GeneratedAgentPayloadV3):
    """Apply the role split that OpenAPI cannot infer from the payload alone."""

    def for_work_kind(self, work_kind: str):
        if work_kind == "reason":
            if self.reason_decision is None or self.work_result is not None:
                raise ValueError("Reason requires reason_decision and forbids work_result")
            if len(self.intent_proposals) > 3:
                raise ValueError("Reason proposal limit exceeded")
            decision = self.reason_decision.decision.value
            if decision == "propose_intents" and not self.intent_proposals:
                raise ValueError("propose_intents requires at least one proposal")
            if decision == "wait" and not self.reason_decision.wait_refs:
                raise ValueError("wait requires at least one fixed condition")
        elif work_kind == "explore":
            if self.reason_decision is not None or self.work_result is None:
                raise ValueError("Explore requires work_result and forbids reason_decision")
            if len(self.intent_proposals) > 2:
                raise ValueError("Explore proposal limit exceeded")
        else:
            raise ValueError("AgentPayloadV3 is published only for Reason and Explore")
        return self


AgentPayloadV3.model_rebuild(_types_namespace=vars(_wire))


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
    "AgentPayloadV3",
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
    "ResultEnvelopeV3",
    "ResultReceipt",
    "ResultReceiptStatus",
    "RunIdentity",
    "WorkerAssignment",
]
