from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from wuji_core.contracts.generated import (
    ArtifactRecord,
    ArtifactState,
    AssertionRole,
    BlobRef,
    CaptureCompleteness,
    ClaimKind,
    ClaimRecord,
    EvidenceOrigin,
    IntentAcceptance,
    IntentRecord,
    KnowledgeRef,
    NodeEntityType,
    ObservationRecord,
    ProducerKind,
    RecordPayload,
    RecordView,
)
from wuji_maf_worker.context import (
    ContextLimitExceeded,
    ContextLimits,
    ContextRelation,
    build_context_bundle,
)


def _claim_view(
    ref: KnowledgeRef,
    *,
    kind: ClaimKind,
    assertion_role: AssertionRole,
    text: str,
    basis_refs: list[KnowledgeRef],
    limitations: list[str],
    structured_assertion: dict[str, Any] | None = None,
    display_kind: str = "claim",
    supersedes: KnowledgeRef | None = None,
    task_id: str = "task-context-1",
) -> RecordView:
    claim = ClaimRecord.model_validate(
        {
            "claim_id": ref.id,
            "revision": ref.revision.root,
            "task_id": task_id,
            "kind": kind,
            "assertion_role": assertion_role,
            "text": text,
            "structured_assertion": structured_assertion,
            "basis_refs": [item.model_dump(mode="json") for item in basis_refs],
            "limitations": limitations,
            "producer_kind": ProducerKind.agent,
            "producer_ref": "agent-reason-1",
            "created_at": datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc),
            "supersedes": supersedes,
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind=display_kind,
        record=RecordPayload(root=claim),
    )


def _intent_view(
    ref: KnowledgeRef,
    *,
    payload_id: str | None = None,
    basis_refs: list[KnowledgeRef] | None = None,
    task_id: str = "task-context-1",
) -> RecordView:
    intent = IntentRecord.model_validate(
        {
            "intent_id": payload_id or ref.id,
            "revision": ref.revision.root,
            "task_id": task_id,
            "question": "What evidence resolves this intent?",
            "basis_refs": [item.model_dump(mode="json") for item in (basis_refs or [])],
            "expected_output": "A bounded observation.",
            "acceptance_state": IntentAcceptance.admitted,
            "created_at": datetime(2026, 9, 13, 8, 1, tzinfo=timezone.utc),
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind="intent",
        record=RecordPayload(root=intent),
    )


def _observation_view(
    ref: KnowledgeRef,
    artifact_ref: BlobRef,
    *,
    payload_id: str | None = None,
    task_id: str = "task-context-1",
) -> RecordView:
    observation = ObservationRecord.model_validate(
        {
            "observation_id": payload_id or ref.id,
            "revision": ref.revision.root,
            "task_id": task_id,
            "capture_id": "capture-context-1",
            "tool_attempt_id": "tool-attempt-context-1",
            "collector_ref": "collector-context-1",
            "artifact_refs": [artifact_ref.model_dump(mode="json")],
            "capture_layer": "http-response",
            "observed_at": datetime(2026, 9, 13, 8, 2, tzinfo=timezone.utc),
            "received_at": datetime(2026, 9, 13, 8, 3, tzinfo=timezone.utc),
            "environment_ref": "fixture-context-1",
            "conditions": [],
            "completeness": CaptureCompleteness.complete,
            "evidence_origin": EvidenceOrigin.fixture_capture,
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind="observation",
        record=RecordPayload(root=observation),
    )


def _artifact_view(
    ref: KnowledgeRef,
    *,
    payload_id: str | None = None,
) -> RecordView:
    artifact = ArtifactRecord.model_validate(
        {
            "artifact_ref": {
                "id": payload_id or ref.id,
                "version": ref.revision.root,
                "sha256": "a" * 64,
            },
            "state": ArtifactState.sealed,
            "media_type": "application/json",
            "size_bytes": "128",
            "created_at": datetime(2026, 9, 13, 8, 4, tzinfo=timezone.utc),
        }
    )
    return RecordView(
        assessment=None,
        ref=ref,
        display_kind="artifact",
        record=RecordPayload(root=artifact),
    )


def test_bundle_preserves_exact_refs_hypothesis_counterevidence_and_limitations() -> (
    None
):
    hypothesis_ref = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.claim, "id": "claim-hypothesis", "revision": "2"}
    )
    counter_ref = KnowledgeRef.model_validate(
        {
            "entity_type": NodeEntityType.claim,
            "id": "claim-counterevidence",
            "revision": "7",
        }
    )
    hypothesis = _claim_view(
        hypothesis_ref,
        kind=ClaimKind.hypothesis,
        assertion_role=AssertionRole.hypothesis,
        text="The endpoint accepts the candidate token.",
        basis_refs=[counter_ref],
        limitations=["The anonymous path has not been reproduced."],
    )
    counterevidence = _claim_view(
        counter_ref,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="The same token was rejected by the second capture.",
        basis_refs=[],
        limitations=["Only one isolated environment was observed."],
    )

    bundle = build_context_bundle(
        [hypothesis, counterevidence],
        [hypothesis_ref, counter_ref],
        snapshot_id="snapshot-context-17",
        limits=ContextLimits(max_records=2, max_bytes=50_000),
        relations=[
            ContextRelation(
                source=counter_ref, target=hypothesis_ref, relation="opposes"
            )
        ],
    )

    payload = json.loads(bundle.text)
    exact_refs = [
        {"entity_type": "claim", "id": "claim-hypothesis", "revision": "2"},
        {"entity_type": "claim", "id": "claim-counterevidence", "revision": "7"},
    ]
    assert bundle.snapshot_id == "snapshot-context-17"
    assert [item.model_dump(mode="json") for item in bundle.read_set] == exact_refs
    assert [item.model_dump(mode="json") for item in bundle.record_refs] == exact_refs
    assert payload["schema_version"] == "wuji.context.v2"
    assert payload["read_set"] == exact_refs
    assert [item["ref"] for item in payload["records"]] == exact_refs
    assert payload["records"][0]["record"]["kind"] == "hypothesis"
    assert payload["records"][0]["record"]["assertion_role"] == "hypothesis"
    assert payload["records"][0]["record"]["limitations"] == [
        "The anonymous path has not been reproduced."
    ]
    assert payload["records"][1]["record"]["text"] == (
        "The same token was rejected by the second capture."
    )
    assert payload["records"][1]["record"]["limitations"] == [
        "Only one isolated environment was observed."
    ]
    assert payload["relations"] == [
        {"source": exact_refs[1], "target": exact_refs[0], "relation": "opposes"}
    ]
    assert (
        bundle.input_digest == hashlib.sha256(bundle.text.encode("utf-8")).hexdigest()
    )


def test_bundle_rejects_claim_basis_ref_missing_from_read_set() -> None:
    claim_ref = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.claim, "id": "claim-dependent", "revision": "1"}
    )
    missing_basis_ref = KnowledgeRef.model_validate(
        {
            "entity_type": NodeEntityType.observation,
            "id": "observation-missing",
            "revision": "3",
        }
    )
    claim = _claim_view(
        claim_ref,
        kind=ClaimKind.derived_conclusion,
        assertion_role=AssertionRole.explanation,
        text="This conclusion depends on an omitted observation.",
        basis_refs=[missing_basis_ref],
        limitations=[],
    )

    with pytest.raises(ValueError):
        build_context_bundle(
            [claim],
            [claim_ref],
            snapshot_id="snapshot-context-18",
            limits=ContextLimits(max_records=1, max_bytes=50_000),
        )


def test_utf8_budget_rejects_whole_context_without_mutating_or_dropping_counterevidence() -> (
    None
):
    hypothesis_ref = KnowledgeRef.model_validate(
        {
            "entity_type": NodeEntityType.claim,
            "id": "claim-utf8-hypothesis",
            "revision": "1",
        }
    )
    counter_ref = KnowledgeRef.model_validate(
        {
            "entity_type": NodeEntityType.claim,
            "id": "claim-utf8-counter",
            "revision": "1",
        }
    )
    records = [
        _claim_view(
            hypothesis_ref,
            kind=ClaimKind.hypothesis,
            assertion_role=AssertionRole.hypothesis,
            text="假设：令牌可能有效。" * 20,
            basis_refs=[],
            limitations=["尚未复现。"],
        ),
        _claim_view(
            counter_ref,
            kind=ClaimKind.observation_summary,
            assertion_role=AssertionRole.candidate_fact,
            text="反证：隔离环境拒绝了令牌。" * 20,
            basis_refs=[],
            limitations=["仅观察一次。"],
        ),
    ]
    originals = [record.model_copy(deep=True) for record in records]
    complete = build_context_bundle(
        records,
        [hypothesis_ref, counter_ref],
        snapshot_id="snapshot-utf8-budget",
        limits=ContextLimits(max_records=2, max_bytes=100_000),
        relations=[
            ContextRelation(
                source=counter_ref, target=hypothesis_ref, relation="opposes"
            )
        ],
    )
    payload = json.loads(complete.text)
    assert len(complete.text.encode("utf-8")) > len(complete.text)
    assert [item["ref"]["id"] for item in payload["records"]] == [
        "claim-utf8-hypothesis",
        "claim-utf8-counter",
    ]

    with pytest.raises(ContextLimitExceeded):
        build_context_bundle(
            records,
            [hypothesis_ref, counter_ref],
            snapshot_id="snapshot-utf8-budget",
            limits=ContextLimits(max_records=2, max_bytes=len(complete.text)),
            relations=[
                ContextRelation(
                    source=counter_ref, target=hypothesis_ref, relation="opposes"
                )
            ],
        )

    assert records == originals


def test_bundle_normalizes_forged_fact_hint_and_keeps_precise_decimal_as_number() -> (
    None
):
    claim_ref = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.claim, "id": "claim-decimal", "revision": "9"}
    )
    precise = Decimal("0.123456789012345678901234567890123456789")
    claim = _claim_view(
        claim_ref,
        kind=ClaimKind.hypothesis,
        assertion_role=AssertionRole.hypothesis,
        text="A display hint cannot promote this hypothesis.",
        basis_refs=[],
        limitations=[],
        structured_assertion={"confidence": precise},
        display_kind="fact",
    )

    bundle = build_context_bundle(
        [claim],
        [claim_ref],
        snapshot_id="snapshot-decimal",
        limits=ContextLimits(max_records=1, max_bytes=50_000),
    )

    payload = json.loads(bundle.text, parse_float=Decimal)
    assert payload["records"][0]["display_kind"] == "claim"
    assert payload["records"][0]["record"]["assertion_role"] == "hypothesis"
    assert (
        payload["records"][0]["record"]["structured_assertion"]["confidence"] == precise
    )
    assert f'"confidence":{precise}' in bundle.text


def test_exact_ref_duplicates_collapse_but_revisions_and_conflicts_do_not() -> None:
    revision_one = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.claim, "id": "claim-duplicate", "revision": "1"}
    )
    revision_two = KnowledgeRef.model_validate(
        {"entity_type": NodeEntityType.claim, "id": "claim-duplicate", "revision": "2"}
    )
    record = _claim_view(
        revision_one,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="Identical content.",
        basis_refs=[],
        limitations=[],
    )

    bundle = build_context_bundle(
        [record, record.model_copy(deep=True)],
        [revision_one, revision_one.model_copy(deep=True), revision_two],
        snapshot_id="snapshot-duplicates",
        limits=ContextLimits(max_records=2, max_bytes=50_000),
    )

    assert [(ref.id, ref.revision.root) for ref in bundle.read_set] == [
        ("claim-duplicate", "1"),
        ("claim-duplicate", "2"),
    ]
    assert [(ref.id, ref.revision.root) for ref in bundle.record_refs] == [
        ("claim-duplicate", "1")
    ]
    assert len(json.loads(bundle.text)["records"]) == 1

    conflicting = _claim_view(
        revision_one,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="Conflicting content for the same exact reference.",
        basis_refs=[],
        limitations=[],
    )
    with pytest.raises(ValueError):
        build_context_bundle(
            [record, conflicting],
            [revision_one],
            snapshot_id="snapshot-conflict",
            limits=ContextLimits(max_records=2, max_bytes=50_000),
        )


def test_all_explicit_record_and_relation_refs_must_be_in_read_set() -> None:
    current_claim_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-current", "revision": "2"}
    )
    superseded_claim_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-current", "revision": "1"}
    )
    claim = _claim_view(
        current_claim_ref,
        kind=ClaimKind.derived_conclusion,
        assertion_role=AssertionRole.explanation,
        text="This claim supersedes an earlier revision.",
        basis_refs=[],
        limitations=[],
        supersedes=superseded_claim_ref,
    )
    intent_ref = KnowledgeRef.model_validate(
        {"entity_type": "intent", "id": "intent-dependent", "revision": "1"}
    )
    missing_basis_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-basis", "revision": "4"}
    )
    intent = _intent_view(intent_ref, basis_refs=[missing_basis_ref])
    observation_ref = KnowledgeRef.model_validate(
        {"entity_type": "observation", "id": "observation-artifact", "revision": "3"}
    )
    blob_ref = BlobRef.model_validate(
        {"id": "artifact-evidence", "version": "5", "sha256": "b" * 64}
    )
    observation = _observation_view(observation_ref, blob_ref)

    missing_record_refs = [
        ([claim], [current_claim_ref]),
        ([intent], [intent_ref]),
        ([observation], [observation_ref]),
    ]
    for records, read_set in missing_record_refs:
        with pytest.raises(ValueError):
            build_context_bundle(
                records,
                read_set,
                snapshot_id="snapshot-missing-explicit-ref",
                limits=ContextLimits(max_records=1, max_bytes=50_000),
            )

    with pytest.raises(ValueError):
        build_context_bundle(
            [],
            [current_claim_ref],
            snapshot_id="snapshot-missing-relation-endpoint",
            limits=ContextLimits(max_records=1, max_bytes=50_000),
            relations=[
                ContextRelation(
                    source=current_claim_ref,
                    target=missing_basis_ref,
                    relation="supports",
                )
            ],
        )


def test_supported_payloads_require_exact_identity_and_known_tasks_cannot_mix() -> None:
    claim_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-wrapper", "revision": "1"}
    )
    claim = _claim_view(
        claim_ref,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="Payload identity differs from the wrapper.",
        basis_refs=[],
        limitations=[],
    )
    mismatched_claim = claim.model_copy(
        update={
            "ref": KnowledgeRef.model_validate(
                {"entity_type": "claim", "id": "claim-other-wrapper", "revision": "1"}
            )
        },
        deep=True,
    )
    intent_ref = KnowledgeRef.model_validate(
        {"entity_type": "intent", "id": "intent-wrapper", "revision": "1"}
    )
    mismatched_intent = _intent_view(intent_ref, payload_id="intent-payload")
    observation_ref = KnowledgeRef.model_validate(
        {"entity_type": "observation", "id": "observation-wrapper", "revision": "1"}
    )
    blob_ref = BlobRef.model_validate(
        {"id": "artifact-linked", "version": "1", "sha256": "c" * 64}
    )
    linked_artifact_ref = KnowledgeRef.model_validate(
        {
            "entity_type": "artifact",
            "id": blob_ref.id,
            "revision": blob_ref.version.root,
        }
    )
    mismatched_observation = _observation_view(
        observation_ref, blob_ref, payload_id="observation-payload"
    )
    artifact_ref = KnowledgeRef.model_validate(
        {"entity_type": "artifact", "id": "artifact-wrapper", "revision": "1"}
    )
    mismatched_artifact = _artifact_view(artifact_ref, payload_id="artifact-payload")

    mismatch_cases = [
        (mismatched_claim, [mismatched_claim.ref]),
        (mismatched_intent, [intent_ref]),
        (mismatched_observation, [observation_ref, linked_artifact_ref]),
        (mismatched_artifact, [artifact_ref]),
    ]
    for record, read_set in mismatch_cases:
        with pytest.raises(ValueError):
            build_context_bundle(
                [record],
                read_set,
                snapshot_id="snapshot-payload-mismatch",
                limits=ContextLimits(max_records=1, max_bytes=50_000),
            )

    first_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-task-one", "revision": "1"}
    )
    second_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-task-two", "revision": "1"}
    )
    first = _claim_view(
        first_ref,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="First task record.",
        basis_refs=[],
        limitations=[],
        task_id="task-one",
    )
    second = _claim_view(
        second_ref,
        kind=ClaimKind.observation_summary,
        assertion_role=AssertionRole.candidate_fact,
        text="Second task record.",
        basis_refs=[],
        limitations=[],
        task_id="task-two",
    )
    with pytest.raises(ValueError):
        build_context_bundle(
            [first, second],
            [first_ref, second_ref],
            snapshot_id="snapshot-mixed-task",
            limits=ContextLimits(max_records=2, max_bytes=50_000),
        )


def test_context_contract_rejects_invalid_limits_and_bounded_labels() -> None:
    with pytest.raises(ValueError):
        ContextLimits(max_records=0, max_bytes=1)
    with pytest.raises(ValueError):
        ContextLimits(max_records=1, max_bytes=0)

    claim_ref = KnowledgeRef.model_validate(
        {"entity_type": "claim", "id": "claim-label", "revision": "1"}
    )
    with pytest.raises(ValueError):
        ContextRelation(source=claim_ref, target=claim_ref, relation="")
    with pytest.raises(ValueError):
        ContextRelation(source=claim_ref, target=claim_ref, relation="r" * 129)
    with pytest.raises(ValueError):
        build_context_bundle(
            [],
            [],
            snapshot_id="s" * 257,
            limits=ContextLimits(max_records=1, max_bytes=50_000),
        )
