"""E04-A: an accepted result drives the next question through the real loop.

The fixture is the production Scheduler over real PostgreSQL. A Run submits its
result, closes its own operation set and exits; only then may an exit
observation settle the work. From there the Committer admits a question that did
not exist before, the Scheduler materializes it as Explore work, and a new
material claim reaches the next Reason read set. Nothing here writes accepted
state, work or completion by hand.
"""

from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

from support.p06 import ENVIRONMENT, TASK
from support.p09 import (
    POD_UID,
    SCHEDULER,
    explore_assignment,
    scheduler_case,
    worker_credential,
)
from wuji_core.admission.tools import close_operation_set
from wuji_core.contracts.envelopes import ResultEnvelope
from wuji_core.execution.control import ExecutionObservation
from wuji_core.http import canonical_json_bytes
from wuji_core.scheduling.triggers import TriggerRepository


def _submit(case, assignment, payload, submission_id):
    credential = worker_credential(case, assignment)
    raw = canonical_json_bytes(payload)
    raw_ref = case.control.store.stage_model_output(
        credential.access, TASK, assignment.identity.agent_run_id, raw, "application/json"
    )
    case.control.store.seal(credential.access, TASK, raw_ref)
    receipt = case.control.committer.submit(
        credential.access,
        ResultEnvelope.model_validate(
            {
                "schema_version": "wuji.result-envelope.v2",
                "submission_id": submission_id,
                "identity": assignment.identity.model_dump(mode="json"),
                "snapshot_id": assignment.snapshot_id,
                "read_set": [],
                "raw_output_ref": raw_output_ref(raw_ref),
                "raw_output_digest": raw_ref.sha256.root,
                "payload": payload,
                "producer_version": "e04a-loop-fixture-v1",
            }
        ),
    )
    return credential, receipt


def raw_output_ref(ref):
    return ref.model_dump(mode="json")


def _close_and_exit(case, assignment, credential):
    """The Run closes its own operation set, then the platform sees it exit."""

    with case.control.uow.transaction(
        credential.access, TASK, capability="tool_settle"
    ) as tx:
        close_operation_set(tx, reason_run(assignment))
    body = {
        "receipt_id": str(uuid4()),
        "identity": assignment.identity.model_dump(mode="json"),
        "operation_id": assignment.operation_id,
        "environment_ref": ENVIRONMENT,
        "pod_uid": POD_UID,
        "kind": "exited",
        "observed_at": "2026-09-17T08:00:00Z",
        "process": {
            "pid": 4321,
            "birth_id": "e04a-fixture-birth",
            "started_at": "2026-09-17T07:59:00Z",
            "exited_at": "2026-09-17T08:00:00Z",
            "exit_code": 0,
        },
        "reason": "the fixture run exited after its accepted result",
    }
    source = canonical_json_bytes(body).decode()
    observation = ExecutionObservation.model_validate(
        {
            **body,
            "source_receipt": source,
            "source_digest": sha256(source.encode()).hexdigest(),
        }
    )
    return case.control.control.record_observation(case.receiver_access, observation)


def reason_run(assignment):
    return assignment.identity.agent_run_id


def test_an_accepted_reason_decision_admits_work_that_the_scheduler_executes(
    db_environment, tmp_path, audit_directory
):
    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4
    ) as case:
        first = case.scheduler.tick(limit=2)
        assert {item.work_kind.value for item in first.assignments} == {"explore", "reason"}
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        with db_environment.migration_connection() as connection:
            works_before = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone()[0]

        payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [],
            "intent_proposals": [
                {
                    "client_ref": "runtime-followup",
                    "question": (
                        "Read the second isolated fixture input and cite the exact"
                        " evidence it returned."
                    ),
                    "basis_refs": [case.claim_ref.model_dump(mode="json")],
                    "expected_output": "wuji.agent-payload.v2",
                }
            ],
            "limitations": ["the follow-up question came from the Reason decision"],
            "reason_decision": {
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": "The stored evidence leaves one bounded question open.",
            },
        }
        credential, receipt = _submit(case, reason, payload, "e04a-reason-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        admitted = [
            component for component in receipt.components
            if component.canonical_ref is not None
        ]
        assert admitted and all(
            component.status.value == "accepted_shared" for component in admitted
        )
        _close_and_exit(case, reason, credential)

        second = case.scheduler.tick(limit=4)
        assert second.blocked == (), second.blocked
        with db_environment.migration_connection() as connection:
            decision = connection.execute(
                "SELECT status, reason_code FROM vnext.scheduler_decision"
                " WHERE submission_id=%s",
                ("e04a-reason-1",),
            ).fetchone()
            works_after = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
            reason_state = connection.execute(
                "SELECT state FROM vnext.work_item WHERE task_id=%s AND kind='reason'",
                (TASK,),
            ).fetchone()
        assert decision == ("accepted", None)
        assert reason_state == ("done",)
        # The new question is real work, not a stored string.
        assert works_after > works_before
        assert [item.work_kind.value for item in second.assignments].count("explore") >= 1


def test_a_committed_claim_reaches_the_next_reason_read_set(
    db_environment, tmp_path, audit_directory
):
    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4
    ) as case:
        first = case.scheduler.tick(limit=2)
        explore = explore_assignment(first)
        payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [
                {
                    "client_ref": "fixture-read",
                    "kind": "observation-summary",
                    "assertion_role": "candidate_fact",
                    "text": "The registered Kali read returned durable evidence.",
                    "basis_refs": [
                        {
                            "entity_type": "artifact",
                            "id": case.artifact_ref.id,
                            "revision": case.artifact_ref.version.root,
                        }
                    ],
                    "limitations": ["one isolated fixture read"],
                }
            ],
            "intent_proposals": [],
            "limitations": ["explore produced the raw read for later reasoning"],
        }
        with db_environment.migration_connection() as connection:
            before_work_items = [
                row[0] for row in connection.execute(
                    "SELECT work_item_id FROM vnext.work_item WHERE task_id=%s", (TASK,)
                ).fetchall()
            ]
        credential, receipt = _submit(case, explore, payload, "e04a-explore-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        claim_ref = next(
            component.canonical_ref for component in receipt.components
            if component.canonical_ref is not None
        )
        _close_and_exit(case, explore, credential)

        case.scheduler.tick(limit=4)
        with db_environment.migration_connection() as connection:
            explore_state = connection.execute(
                "SELECT state FROM vnext.work_item WHERE task_id=%s AND work_item_id=%s",
                (TASK, explore.identity.work_item_id),
            ).fetchone()
            claim_row = connection.execute(
                "SELECT kind, assertion_role FROM vnext.claim_revision"
                " WHERE task_id=%s AND entity_id=%s",
                (TASK, claim_ref.id),
            ).fetchone()
        assert explore_state == ("done",)
        assert claim_row == ("observation-summary", "candidate_fact")
        with db_environment.migration_connection() as connection:
            run_state = connection.execute(
                "SELECT process_state, result_state FROM vnext.agent_run WHERE agent_run_id=%s",
                (explore.identity.agent_run_id,),
            ).fetchone()
            material = connection.execute(
                "SELECT source_key FROM vnext.scheduler_progress"
                " WHERE task_id=%s AND category='material'",
                (TASK,),
            ).fetchall()
        assert run_state == ("exited", "accepted")
        # One material row, keyed by the accepted canonical reference itself, so
        # a replayed event cannot look like new knowledge.
        assert len(material) == 1, material
        assert material[0][0].startswith("material:")

        # Re-delivering the same outbox event adds neither a generation nor work.
        with db_environment.migration_connection() as connection:
            submission_event = connection.execute(
                "SELECT max(event_seq) FROM vnext.outbox"
                " WHERE task_id=%s AND kind='result_committed'",
                (TASK,),
            ).fetchone()[0]
        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            repository = TriggerRepository(artifacts=case.control.store)
            before_replay = repository.read(tx)
            repository.record(tx, event_seq=submission_event)
            after_replay = repository.read(tx)
        assert after_replay.trigger_generation == before_replay.trigger_generation
        with db_environment.migration_connection() as connection:
            replayed_material = connection.execute(
                "SELECT count(*) FROM vnext.scheduler_progress"
                " WHERE task_id=%s AND category='material'",
                (TASK,),
            ).fetchone()[0]
            work_count = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        assert replayed_material == len(material)
        assert work_count == len(before_work_items)


def test_a_new_claim_reaches_the_next_reason_read_set(
    db_environment, tmp_path, audit_directory
):
    """The loop's point: material produced by one work changes the next Reason."""

    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4
    ) as case:
        first = case.scheduler.tick(limit=2)
        explore = explore_assignment(first)
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )

        credential, receipt = _submit(
            case,
            explore,
            {
                "schema_version": "wuji.agent-payload.v2",
                "claims": [
                    {
                        "client_ref": "loop-read",
                        "kind": "observation-summary",
                        "assertion_role": "candidate_fact",
                        "text": "The registered Kali read returned durable evidence.",
                        "basis_refs": [
                            {
                                "entity_type": "artifact",
                                "id": case.artifact_ref.id,
                                "revision": case.artifact_ref.version.root,
                            }
                        ],
                        "limitations": ["one isolated fixture read"],
                    }
                ],
                "intent_proposals": [],
                "limitations": ["explore produced the raw read"],
            },
            "e04a-explore-2",
        )
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        claim_ref = next(
            component.canonical_ref for component in receipt.components
            if component.canonical_ref is not None
        )
        _close_and_exit(case, explore, credential)

        reason_credential, reason_receipt = _submit(
            case,
            reason,
            {
                "schema_version": "wuji.agent-payload.v2",
                "claims": [],
                "intent_proposals": [
                    {
                        "client_ref": "loop-followup",
                        "question": "Read the second isolated fixture input and cite it.",
                        "basis_refs": [case.claim_ref.model_dump(mode="json")],
                        "expected_output": "wuji.agent-payload.v2",
                    }
                ],
                "limitations": ["the follow-up question came from the stored evidence"],
                "reason_decision": {
                    "decision": "propose_intents",
                    "wait_refs": [],
                    "reason": "One bounded question remains open.",
                },
            },
            "e04a-reason-2",
        )
        assert reason_receipt.status.value == "accepted", reason_receipt.model_dump(mode="json")
        _close_and_exit(case, reason, reason_credential)

        second = case.scheduler.tick(limit=6)
        assert second.blocked == (), second.blocked
        fresh = [
            item for item in second.assignments
            if item.work_kind.value == "reason"
            and item.identity.agent_run_id != reason.identity.agent_run_id
        ]
        assert fresh, [item.work_kind.value for item in second.assignments]

        new_assignment = fresh[0]
        new_credential = worker_credential(case, new_assignment)
        # The new Run's own fixed input is the proof: its snapshot read set must
        # contain the claim the previous work produced.
        manifest = case.snapshots.get(
            TASK, new_credential.access, new_assignment.snapshot_id
        )
        assert claim_ref in manifest.refs, (claim_ref, manifest.refs)


def test_a_completion_request_is_answered_once_with_a_durable_review(
    db_environment, tmp_path, audit_directory
):
    """E05: the Reason asks; the platform answers with one review, never a close."""

    from wuji_core.completion.precheck import CompletionService

    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4,
        completion=lambda control: CompletionService(
            control.uow, control=control.control
        ),
    ) as case:
        first = case.scheduler.tick(limit=2)
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        credential, receipt = _submit(
            case,
            reason,
            {
                "schema_version": "wuji.agent-payload.v2",
                "claims": [],
                "intent_proposals": [],
                "limitations": ["the Reason asks the platform to review completion"],
                "reason_decision": {
                    "decision": "propose_completion",
                    "wait_refs": [],
                    "reason": "The stored evidence looks sufficient to the Reason.",
                },
            },
            "e05-completion-1",
        )
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, reason, credential)

        # The request is emitted while the decision is consumed; the next tick
        # is what reads it and answers with the review.
        case.scheduler.tick(limit=4)
        case.scheduler.tick(limit=4)
        with db_environment.migration_connection() as connection:
            reviews = [
                row[0] and json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload_json FROM vnext.outbox"
                    " WHERE task_id=%s AND kind='completion.reviewed'"
                    " ORDER BY event_seq",
                    (TASK,),
                ).fetchall()
            ]
            request_events = connection.execute(
                "SELECT count(*) FROM vnext.outbox"
                " WHERE task_id=%s AND kind='reason.completion_requested'",
                (TASK,),
            ).fetchone()[0]
            task_state = connection.execute(
                "SELECT desired_state, observed_state, control_version FROM vnext.task"
                " WHERE task_id=%s", (TASK,),
            ).fetchone()
        assert request_events == 1
        assert len(reviews) == 1, reviews
        review = reviews[0]
        assert review["schema_version"] == "wuji.completion-review.v1"
        # Nothing was judged, so the platform must not answer "ready".
        assert review["decision"] in {"wait", "blocked"}, review
        assert review["reasons"], review
        assert review["basis"]["request_event_seq"]
        assert review["basis"]["control_version"] == str(task_state[2])
        assert len(review["review_digest"]) == 64
        # The review answers a request; it never closes the Task by itself.
        assert task_state[1] != "closed"

        # Re-delivering the same request event cannot mint a second review.
        with db_environment.migration_connection() as connection:
            request_seq = connection.execute(
                "SELECT max(event_seq) FROM vnext.outbox"
                " WHERE task_id=%s AND kind='reason.completion_requested'",
                (TASK,),
            ).fetchone()[0]
        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            repository = TriggerRepository(artifacts=case.control.store)
            repository.record(tx, event_seq=request_seq)
        with db_environment.migration_connection() as connection:
            again = connection.execute(
                "SELECT count(*) FROM vnext.outbox"
                " WHERE task_id=%s AND kind='completion.reviewed'",
                (TASK,),
            ).fetchone()[0]
        assert again == 1

        # A review with a gap is the feedback that wakes the next Reason, and it
        # travels in that Run's frozen input rather than in a log line.
        third = case.scheduler.tick(limit=6)
        assert third.blocked == (), third.blocked
        fresh = [
            item for item in third.assignments
            if item.work_kind.value == "reason"
            and item.identity.agent_run_id != reason.identity.agent_run_id
        ]
        assert fresh, [item.work_kind.value for item in third.assignments]
        new_credential = worker_credential(case, fresh[0])
        manifest = case.snapshots.get(
            TASK, new_credential.access, fresh[0].snapshot_id
        )
        delivered = manifest.states.get("completion_review")
        assert delivered is not None and delivered["review_id"] == review["review_id"]
        assert delivered["decision"] == review["decision"]


def test_a_sealed_model_output_never_becomes_board_material(
    db_environment, tmp_path, audit_directory
):
    """A Run's own private output must not come back as the next Run's input."""

    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4
    ) as case:
        first = case.scheduler.tick(limit=2)
        explore = explore_assignment(first)
        payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [
                {
                    "client_ref": "board-scope-read",
                    "kind": "observation-summary",
                    "assertion_role": "candidate_fact",
                    "text": "The registered Kali read returned durable evidence.",
                    "basis_refs": [
                        {
                            "entity_type": "artifact",
                            "id": case.artifact_ref.id,
                            "revision": case.artifact_ref.version.root,
                        }
                    ],
                    "limitations": ["one isolated fixture read"],
                }
            ],
            "intent_proposals": [],
            "limitations": ["explore produced the raw read for later reasoning"],
        }
        credential, receipt = _submit(case, explore, payload, "board-scope-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, explore, credential)
        case.scheduler.tick(limit=4)

        with db_environment.migration_connection() as connection:
            private = connection.execute(
                "SELECT entity_id FROM vnext.artifact WHERE task_id=%s"
                " AND agent_run_id=%s AND provenance='model_output' LIMIT 1",
                (TASK, explore.identity.agent_run_id),
            ).fetchone()
            assert private is not None
            snapshot_id = connection.execute(
                "SELECT snapshot_id FROM vnext.snapshot_manifest WHERE task_id=%s"
                " ORDER BY created_at DESC LIMIT 1",
                (TASK,),
            ).fetchone()[0]
            refs = {
                (row[0], row[1], str(row[2]))
                for row in connection.execute(
                    "SELECT entity_type,entity_id,revision FROM vnext.snapshot_ref"
                    " WHERE task_id=%s AND snapshot_id=%s",
                    (TASK, snapshot_id),
                ).fetchall()
            }
        assert ("artifact", private[0], "1") not in refs
        assert (
            "artifact",
            case.artifact_ref.id,
            str(case.artifact_ref.version.root),
        ) in refs
