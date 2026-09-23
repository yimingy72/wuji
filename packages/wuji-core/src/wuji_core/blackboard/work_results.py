"""Internal, versioned interpretation of accepted WorkResultV3 documents."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from wuji_core.contracts.generated import (
    CapabilityGap,
    ProposalLocalRef,
    ProposalReference,
    UnresolvedItem,
    WorkResultOutcome,
    WorkResultV3,
)
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.http.json_boundary import strict_json_loads


PROJECTION_VERSION = "wuji.work-result-projection.v1"


class WorkResultProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["wuji.work-result-projection.v1"]
    declared_outcome: WorkResultOutcome
    effective_outcome: WorkResultOutcome
    summary: str
    canonical_refs: list[KnowledgeRef]
    invalid_refs: list[ProposalReference]
    unresolved_items: list[UnresolvedItem]
    capability_gaps: list[CapabilityGap]

    def effective_result(self):
        return WorkResultV3.model_validate(
            {
                "outcome": self.effective_outcome,
                "summary": self.summary,
                "answer_basis_refs": self.canonical_refs,
                "unresolved_items": self.unresolved_items,
                "capability_gaps": self.capability_gaps,
            }
        )


def project_work_result(result, *, local, valid_canonical):
    """Resolve only accepted same-batch refs and already delivered canonical refs."""

    result = WorkResultV3.model_validate(result)
    canonical, invalid, seen = [], [], set()
    for declared in result.answer_basis_refs:
        value = declared.root
        resolved = local.get(value.client_ref) if isinstance(value, ProposalLocalRef) else value
        if resolved is None or (
            isinstance(value, KnowledgeRef) and not valid_canonical(value)
        ):
            invalid.append(declared)
            continue
        key = (resolved.entity_type.value, resolved.id, resolved.revision.root)
        if key not in seen:
            seen.add(key)
            canonical.append(resolved)
    effective = result.outcome
    if invalid and effective == WorkResultOutcome.answered:
        effective = WorkResultOutcome.inconclusive
    return WorkResultProjection(
        schema_version=PROJECTION_VERSION,
        declared_outcome=result.outcome,
        effective_outcome=effective,
        summary=result.summary,
        canonical_refs=canonical,
        invalid_refs=invalid,
        unresolved_items=result.unresolved_items,
        capability_gaps=result.capability_gaps,
    )


def read_work_result(value):
    """Read new projections and conservatively interpret unversioned legacy rows."""

    if isinstance(value, str):
        value = strict_json_loads(value)
    if value.get("schema_version") == PROJECTION_VERSION:
        return WorkResultProjection.model_validate(value)
    legacy = WorkResultV3.model_validate(value)
    canonical = [
        item.root
        for item in legacy.answer_basis_refs
        if isinstance(item.root, KnowledgeRef)
    ]
    invalid = [
        item
        for item in legacy.answer_basis_refs
        if isinstance(item.root, ProposalLocalRef)
    ]
    effective = legacy.outcome
    if invalid and effective == WorkResultOutcome.answered:
        effective = WorkResultOutcome.inconclusive
    return WorkResultProjection(
        schema_version=PROJECTION_VERSION,
        declared_outcome=legacy.outcome,
        effective_outcome=effective,
        summary=legacy.summary,
        canonical_refs=canonical,
        invalid_refs=invalid,
        unresolved_items=legacy.unresolved_items,
        capability_gaps=legacy.capability_gaps,
    )
