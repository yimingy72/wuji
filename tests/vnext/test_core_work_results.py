from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

from wuji_core.blackboard.work_results import (
    project_work_result,
    read_work_result,
)
from wuji_core.contracts.generated import (
    IntentAcceptance,
    IntentRecord,
    RecordPayload,
    RecordView,
    WorkResultV3,
)
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.execution.worker_bridge import WorkerHostBridge, snapshot_work_brief
from wuji_core.projection.builder import node_id
from wuji_core.projection.exploration import build_exploration


def _ref(kind, identity, revision="1"):
    return KnowledgeRef.model_validate(
        {"entity_type": kind, "id": identity, "revision": revision}
    )


def test_projection_normalizes_only_accepted_local_refs_and_ui_uses_effective_outcome():
    accepted = _ref("claim", "claim-accepted")
    raw = WorkResultV3.model_validate(
        {
            "outcome": "answered",
            "summary": "The model declared the problem answered.",
            "answer_basis_refs": [
                {"client_ref": "accepted"},
                {"client_ref": "missing"},
            ],
            "unresolved_items": ["Confirm the rejected basis."],
            "capability_gaps": [],
        }
    )
    projection = project_work_result(
        raw, local={"accepted": accepted}, valid_canonical=lambda _ref: False
    )

    assert projection.declared_outcome.value == "answered"
    assert projection.effective_outcome.value == "inconclusive"
    assert projection.canonical_refs == [accepted]
    assert [item.root.client_ref for item in projection.invalid_refs] == ["missing"]
    legacy = read_work_result(raw.model_dump(mode="json"))
    assert legacy.effective_outcome.value == "inconclusive"
    assert legacy.canonical_refs == []

    stored = read_work_result(projection.model_dump(mode="json"))
    intent_ref = _ref("intent", "intent-ui")
    intent = IntentRecord.model_validate(
        {
            "intent_id": intent_ref.id,
            "revision": intent_ref.revision.root,
            "task_id": "task-ui",
            "question": "Is the fixed problem answered?",
            "basis_refs": [],
            "expected_output": "A supported answer.",
            "acceptance_state": IntentAcceptance.admitted,
            "created_at": datetime(2026, 9, 22, tzinfo=timezone.utc),
        }
    )
    record = RecordView(
        assessment=None,
        ref=intent_ref,
        display_kind="intent",
        record=RecordPayload(root=intent),
    )
    problems, _insights, _relations = build_exploration(
        (record,),
        (),
        metadata={
            node_id(intent_ref): {
                "work_item_id": "work-ui",
                "state": "done",
                "work_result": stored.effective_result(),
                "attempts": [],
            }
        },
    )
    assert problems[0].work_result.outcome.value == "inconclusive"
    assert problems[0].work_result.answer_basis_refs[0].root == accepted


def test_snapshot_brief_is_repeatable_and_names_source_work_without_expanding_refs():
    claim = _ref("claim", "claim-visible")
    hidden = _ref("claim", "claim-not-in-snapshot")
    result = project_work_result(
        WorkResultV3.model_validate(
            {
                "outcome": "inconclusive",
                "summary": "A prior route stopped at a bounded gap.",
                "answer_basis_refs": [claim, hidden],
                "unresolved_items": ["Try the independent route."],
                "capability_gaps": ["Missing decoder."],
            }
        ),
        local={},
        valid_canonical=lambda _ref: True,
    ).model_dump(mode="json")
    states = {
        "work_items": {
            "work-a": {"state": "done", "intent": None},
            "work-b": {"state": "running", "intent": None},
            "work-c": {
                "state": "running",
                "intent": {"question": "Can the alternate parser decode it?"},
            },
        },
        "agent_runs": {
            "run-a": {
                "work_item_id": "work-a",
                "run_epoch": "2",
                "work_result": result,
            }
        },
        "tool_attempts": [
            {
                "work_item_id": "work-b",
                "tool_attempt_id": "attempt-b",
                "tool_definition_version": "shell.v1",
                "status": "complete",
            }
        ],
    }
    manifest = SimpleNamespace(states=deepcopy(states), refs=(claim,))

    first = snapshot_work_brief(manifest, "work-b")
    live_new_result = {"work_item_id": "work-live", "summary": "not frozen"}
    second = snapshot_work_brief(manifest, "work-b")

    assert live_new_result["summary"] not in " ".join(first[0])
    assert first == second
    assert any("Work work-c" in item and "正在进行" in item for item in first[0])
    result_summary = next(item for item in first[0] if "Work work-a · 结果" in item)
    assert "claim:claim-visible@1" in result_summary
    assert "claim-not-in-snapshot" not in result_summary
    assert any("Work work-b · 环境工具" in item for item in first[0])
    assert first[1] == ["Work work-a: Try the independent route."]
    assert first[2] == ["Work work-a: Missing decoder."]


def test_problem_metadata_reader_prefers_frozen_assessments_and_only_falls_back_for_claims():
    refs = (
        _ref("artifact", "artifact-unused"),
        _ref("observation", "observation-unused"),
        _ref("claim", "claim-needed"),
        _ref("intent", "intent-needed"),
    )

    class Ledger:
        def __init__(self):
            self.seen = []

        def read(self, _access, _task_id, ref, *, snapshot_id):
            self.seen.append((ref, snapshot_id))
            return SimpleNamespace(assessment="historical-assessment")

    bridge = object.__new__(WorkerHostBridge)
    bridge.ledger = Ledger()
    assignment = SimpleNamespace(identity=SimpleNamespace(task_id="task-context"))
    manifest = SimpleNamespace(
        snapshot_id="snapshot-context",
        refs=refs,
        states={"claim_assessments": {"claim-needed@1": None}},
    )

    records = bridge._problem_records(object(), assignment, manifest)

    assert [(item.ref, item.assessment) for item in records] == [(refs[2], None)]
    assert bridge.ledger.seen == []

    historical = SimpleNamespace(
        snapshot_id="snapshot-context", refs=refs, states={}
    )
    records = bridge._problem_records(object(), assignment, historical)
    assert [(item.ref, item.assessment) for item in records] == [
        (refs[2], "historical-assessment")
    ]
    assert [ref.entity_type.value for ref, _snapshot in bridge.ledger.seen] == [
        "claim"
    ]
