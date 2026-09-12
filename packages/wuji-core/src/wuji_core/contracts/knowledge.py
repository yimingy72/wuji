"""Knowledge contracts and policy invariants."""

from typing import Self

from pydantic import model_validator

from wuji_core.contracts import generated as _wire
from wuji_core.contracts.generated import (
    ApplicabilityState,
    ArtifactRecord,
    ArtifactState,
    AssertionRole,
    AssessmentCommand as GeneratedAssessmentCommand,
    AssessmentMethod,
    AssessmentReceipt,
    ClaimKind,
    ClaimProposal,
    ClaimRecord,
    ComponentReceipt,
    ComponentReceiptStatus,
    EvidenceState,
    FactAssessment as GeneratedFactAssessment,
    GroundingState,
    GoalContractInput,
    GoalCriterionInput,
    GoalRecord,
    GoalStatus,
    IntentAcceptance,
    IntentProposal,
    IntentRecord,
    KnowledgeRef,
    NodeEntityType,
    ObservationRecord,
    ProducerKind,
    ProposalLocalRef,
    ProposalReference,
)


class FactAssessment(GeneratedFactAssessment):
    """Generated assessment shape plus the no-self-certification policy."""

    @model_validator(mode="after")
    def reject_model_only_support(self) -> Self:
        if (
            self.method_kind is AssessmentMethod.model_review
            and self.evidence_state is EvidenceState.supported
        ):
            raise ValueError("model_review cannot independently mark evidence supported")
        return self


FactAssessment.model_rebuild(_types_namespace=vars(_wire))


class AssessmentCommand(GeneratedAssessmentCommand):
    """Generated command shape that applies the qualified assessment policy."""

    @model_validator(mode="after")
    def validate_assessment_policy(self) -> Self:
        FactAssessment.model_validate(self.assessment.model_dump(mode="python"))
        return self


AssessmentCommand.model_rebuild(_types_namespace=vars(_wire))


__all__ = [
    "ApplicabilityState",
    "ArtifactRecord",
    "ArtifactState",
    "AssertionRole",
    "AssessmentCommand",
    "AssessmentMethod",
    "AssessmentReceipt",
    "ClaimKind",
    "ClaimProposal",
    "ClaimRecord",
    "ComponentReceipt",
    "ComponentReceiptStatus",
    "EvidenceState",
    "FactAssessment",
    "GroundingState",
    "GoalContractInput",
    "GoalCriterionInput",
    "GoalRecord",
    "GoalStatus",
    "IntentAcceptance",
    "IntentProposal",
    "IntentRecord",
    "KnowledgeRef",
    "NodeEntityType",
    "ObservationRecord",
    "ProducerKind",
    "ProposalLocalRef",
    "ProposalReference",
]
