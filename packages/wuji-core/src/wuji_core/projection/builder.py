"""Pure display mapping; callers supply already-authorized records and relations.

The persistence layer owns the stable read and current access checks. Nothing in
this module reads another revision, assesses evidence, or grants a command.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wuji_core.contracts.execution import AgentRunRecord, TaskView, WorkItemView
from wuji_core.contracts.generated import GenericRecord
from wuji_core.contracts.knowledge import (
    ArtifactRecord,
    ClaimRecord,
    GoalRecord,
    IntentRecord,
    KnowledgeRef,
    ObservationRecord,
)
from wuji_core.contracts.views import RecordView, TopologyEdge, TopologyNode


def node_id(ref: KnowledgeRef) -> str:
    if not isinstance(ref, KnowledgeRef):
        raise TypeError("a KnowledgeRef is required")
    return f"{ref.entity_type.value}:{ref.id}@{ref.revision.root}"


def _label(text: str) -> str:
    return text if len(text) <= 8192 else text[:8191] + "…"


def _match(ref: KnowledgeRef, kind: str, identifier: str, revision: str) -> None:
    if (ref.entity_type.value, ref.id, ref.revision.root) != (
        kind,
        identifier,
        revision,
    ):
        raise ValueError("record payload does not match its exact reference")


def project_record(
    record: RecordView, *, allowed_actions: tuple[str, ...] = ()
) -> TopologyNode:
    """Render a canonical assessment without copying arbitrary record metadata."""
    if not isinstance(record, RecordView):
        raise TypeError("an authorized RecordView is required")
    ref, payload = record.ref, record.record.root
    kind, state = ref.entity_type.value, None
    if record.assessment is not None and not isinstance(payload, ClaimRecord):
        raise ValueError("only a Claim record can carry a Claim assessment")

    if isinstance(payload, ClaimRecord):
        _match(ref, "claim", payload.claim_id, payload.revision.root)
        # Eligibility has already been decided by FactLedger. A display hint
        # supplied alongside the record cannot promote an unassessed claim.
        assessment = record.assessment
        kind = "fact" if assessment is not None and assessment.eligible else "claim"
        if assessment is not None:
            state = (
                assessment.applicability_state.value
                if assessment.applicability_state.value != "current"
                else assessment.evidence_state.value
            )
        label = payload.text
    elif isinstance(payload, IntentRecord):
        _match(ref, "intent", payload.intent_id, payload.revision.root)
        label, state = payload.question, payload.acceptance_state.value
    elif isinstance(payload, TaskView):
        _match(ref, "origin", payload.task_id, payload.version.root)
        label, state = payload.name, payload.observed_state.value
    elif isinstance(payload, WorkItemView):
        _match(ref, "work_item", payload.work_item_id, payload.revision.root)
        label, state = (
            f"{payload.kind.value} · {payload.work_item_id}",
            payload.state.value,
        )
    elif isinstance(payload, AgentRunRecord):
        # Each attempt has its own immutable registered identity. Process and
        # result observations change the view of that identity, not run_epoch.
        _match(ref, "agent_run", payload.identity.agent_run_id, "1")
        label, state = (
            f"Run {payload.identity.agent_run_id}",
            payload.process_state.value,
        )
    elif isinstance(payload, GoalRecord):
        _match(ref, "goal", payload.goal_id, payload.revision.root)
        label, state = payload.text, payload.status.value
    elif isinstance(payload, ObservationRecord):
        _match(ref, "observation", payload.observation_id, payload.revision.root)
        label, state = f"Observation {payload.capture_id}", payload.completeness.value
    elif isinstance(payload, ArtifactRecord):
        _match(
            ref,
            "artifact",
            payload.artifact_ref.id,
            payload.artifact_ref.version.root,
        )
        label, state = (
            f"{payload.media_type} · {payload.size_bytes.root} B",
            payload.state.value,
        )
    elif isinstance(payload, GenericRecord) and kind in {
        "verification",
        "completion_review",
        "finding",
        "report",
    }:
        if ref != payload.ref:
            raise ValueError("generic record does not match its exact reference")
        label = payload.title
        status = payload.report_delivery_state or payload.test_result
        state = status.value if status is not None else None
    else:
        raise ValueError("unsupported record payload for this entity type")

    return TopologyNode.model_validate(
        {
            "id": node_id(ref),
            "ref": ref.model_copy(deep=True),
            "display_kind": kind,
            "label": _label(label),
            "state": state,
            "allowed_actions": sorted(set(allowed_actions)),
        }
    )


@dataclass(frozen=True)
class ProjectionRelation:
    relation_id: str
    source: KnowledgeRef
    target: KnowledgeRef
    edge_type: str
    label: str | None = None

    def __post_init__(self) -> None:
        for value, maximum in ((self.relation_id, 256), (self.edge_type, 128)):
            if not isinstance(value, str) or not 1 <= len(value) <= maximum:
                raise ValueError("invalid bounded relation identity or type")
        if not isinstance(self.source, KnowledgeRef) or not isinstance(
            self.target, KnowledgeRef
        ):
            raise TypeError("relation endpoints must be KnowledgeRefs")
        if self.label is not None and (
            not isinstance(self.label, str) or not self.label
        ):
            raise ValueError("relation label must be nonempty text or null")

    def edge_id(self) -> str:
        identity = [
            self.relation_id,
            node_id(self.source),
            node_id(self.target),
            self.edge_type,
        ]
        encoded = json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()
        return "relation:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ProjectionElements:
    nodes: tuple[TopologyNode, ...]
    edges: tuple[TopologyEdge, ...]


def build_projection(
    records: Sequence[RecordView],
    relations: Sequence[ProjectionRelation],
    *,
    allowed_actions: Mapping[str, tuple[str, ...]] | None = None,
) -> ProjectionElements:
    """Map only exact visible endpoints; never reconnect a historical edge."""
    actions = {} if allowed_actions is None else allowed_actions
    originals: dict[str, RecordView] = {}
    nodes: dict[str, TopologyNode] = {}
    for record in records:
        identifier = node_id(record.ref)
        if identifier in originals:
            if record != originals[identifier]:
                raise ValueError("conflicting records for one exact node identity")
            continue
        nodes[identifier] = project_record(
            record, allowed_actions=actions.get(identifier, ())
        )
        originals[identifier] = record

    edges: dict[str, TopologyEdge] = {}
    seen_relations: dict[str, ProjectionRelation] = {}
    for relation in relations:
        if not isinstance(relation, ProjectionRelation):
            raise TypeError("an authorized ProjectionRelation is required")
        source, target = node_id(relation.source), node_id(relation.target)
        if source not in nodes or target not in nodes:
            continue
        if relation.relation_id in seen_relations:
            if relation != seen_relations[relation.relation_id]:
                raise ValueError("conflicting data for one relation identity")
            continue
        identifier = relation.edge_id()
        edges[identifier] = TopologyEdge.model_validate(
            {
                "id": identifier,
                "source": source,
                "target": target,
                "edge_type": relation.edge_type,
                "label": _label(relation.label) if relation.label is not None else None,
            }
        )
        seen_relations[relation.relation_id] = relation
    return ProjectionElements(
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        edges=tuple(edges[key] for key in sorted(edges)),
    )
