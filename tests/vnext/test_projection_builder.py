from __future__ import annotations

import json

import pytest

from wuji_core.contracts.generated import RecordView
from wuji_core.projection.builder import (
    ProjectionRelation,
    build_projection,
    project_record,
)


def _assessment(*, eligible: bool) -> dict[str, object]:
    return {
        "policy_version": "assessment-policy-v1",
        "grounding_state": "content_checked" if eligible else "unchecked",
        "evidence_state": "supported" if eligible else "unassessed",
        "applicability_state": "current",
        "eligible": eligible,
        "assessment_ids": ["assessment-1"] if eligible else [],
        "conditions": [],
        "limitations": [],
    }


def _claim(
    claim_id: str,
    *,
    revision: str = "1",
    payload_revision: str | None = None,
    text: str = "Public claim",
    display_kind: str = "claim",
    assessment: dict[str, object] | None = None,
    payload_id: str | None = None,
) -> RecordView:
    return RecordView.model_validate(
        {
            "assessment": assessment,
            "ref": {
                "entity_type": "claim",
                "id": claim_id,
                "revision": revision,
            },
            "display_kind": display_kind,
            "record": {
                "claim_id": payload_id or claim_id,
                "revision": payload_revision or revision,
                "task_id": "task-fixture",
                "kind": "hypothesis",
                "assertion_role": "hypothesis",
                "text": text,
                "structured_assertion": {"private": "DO-NOT-LEAK"},
                "basis_refs": [],
                "limitations": ["PRIVATE-LIMITATION"],
                "producer_kind": "agent",
                "producer_ref": "PRIVATE-PRODUCER",
                "created_at": "2026-09-13T00:00:00Z",
                "supersedes": None,
            },
        }
    )


def _agent_run(*, ref_revision: str = "1", run_epoch: str = "7") -> RecordView:
    return RecordView.model_validate(
        {
            "ref": {
                "entity_type": "agent_run",
                "id": "run-fixture",
                "revision": ref_revision,
            },
            "display_kind": "agent_run",
            "record": {
                "identity": {
                    "tenant_id": "tenant-fixture",
                    "project_id": "project-fixture",
                    "task_id": "task-fixture",
                    "work_item_id": "work-fixture",
                    "agent_run_id": "run-fixture",
                    "execution_epoch": "3",
                    "run_epoch": run_epoch,
                    "runtime_attempt": "2",
                    "receiver_id": "receiver-fixture",
                },
                "process_state": "running",
                "result_state": "none",
                "model_mode": "synthetic",
                "created_at": "2026-09-13T00:00:00Z",
                "exited_at": None,
                "session_manifest": None,
            },
        }
    )


def test_claim_assessment_changes_display_without_changing_statement_identity(
) -> None:
    unassessed = _claim(
        "claim-1", display_kind="fact", assessment=_assessment(eligible=False)
    )
    supported = _claim(
        "claim-1", display_kind="claim", assessment=_assessment(eligible=True)
    )

    before = project_record(unassessed)
    after = project_record(supported)

    assert before.id == after.id == "claim:claim-1@1"
    assert before.display_kind == "claim"
    assert after.display_kind == "fact"


def test_relation_to_claim_revision_one_is_not_retargeted_to_revision_two() -> None:
    supporting = _claim("supporting-claim")
    current = _claim("claim-1", revision="2")
    relation = ProjectionRelation(
        relation_id="supports-claim-1-v1",
        source=supporting.ref,
        target=_claim("claim-1", revision="1").ref,
        edge_type="supports",
        label="PRIVATE-HIDDEN-EDGE-LABEL",
    )

    projection = build_projection([supporting, current], [relation])

    assert projection.edges == ()
    assert "PRIVATE-HIDDEN-EDGE-LABEL" not in json.dumps(
        [node.model_dump(mode="json") for node in projection.nodes]
    )


def test_visible_relation_keeps_exact_endpoints_and_stable_identity() -> None:
    source = _claim("supporting-claim")
    target = _claim("claim-1", revision="2")
    relation = ProjectionRelation(
        relation_id="supports-claim-1-v2",
        source=source.ref,
        target=target.ref,
        edge_type="supports",
        label="Supports current claim",
    )

    edge = build_projection([target, source], [relation]).edges[0]
    renamed_edge = build_projection(
        [source, target],
        [
            ProjectionRelation(
                relation_id=relation.relation_id,
                source=source.ref,
                target=target.ref,
                edge_type=relation.edge_type,
                label="Renamed display label",
            )
        ],
    ).edges[0]

    assert (edge.source, edge.target, edge.edge_type, edge.label.root) == (
        "claim:supporting-claim@1",
        "claim:claim-1@2",
        "supports",
        "Supports current claim",
    )
    assert edge.id == renamed_edge.id


def test_duplicate_records_collapse_but_conflicting_same_id_is_rejected() -> None:
    original = _claim("claim-1")
    duplicate = _claim("claim-1")
    conflicting = _claim("claim-1", text="Conflicting body")

    collapsed = build_projection([duplicate, original], [])

    assert isinstance(collapsed.nodes, tuple)
    assert collapsed.nodes == (project_record(original),)
    with pytest.raises(ValueError):
        build_projection([original, conflicting], [])


def test_payload_identity_must_match_the_record_view_reference() -> None:
    mismatched = _claim("claim-1", payload_id="claim-other")

    with pytest.raises(ValueError):
        project_record(mismatched)


def test_payload_revision_must_match_the_record_view_reference() -> None:
    mismatched = _claim("claim-1", revision="2", payload_revision="1")

    with pytest.raises(ValueError):
        project_record(mismatched)


def test_missing_assessment_cannot_promote_forged_fact_display() -> None:
    node = project_record(_claim("claim-1", display_kind="fact", assessment=None))

    assert node.display_kind == "claim"
    assert node.state is None


def test_agent_run_identity_is_fixed_at_revision_one_not_run_epoch() -> None:
    node = project_record(_agent_run(ref_revision="1", run_epoch="7"))

    assert node.id == "agent_run:run-fixture@1"
    assert node.state.root == "running"
    with pytest.raises(ValueError):
        project_record(_agent_run(ref_revision="7", run_epoch="7"))


def test_projection_node_contains_only_public_display_fields() -> None:
    node = project_record(_claim("claim-1"))

    assert node.model_dump(mode="json") == {
        "id": "claim:claim-1@1",
        "ref": {"entity_type": "claim", "id": "claim-1", "revision": "1"},
        "display_kind": "claim",
        "label": "Public claim",
        "state": None,
        "allowed_actions": [],
    }
