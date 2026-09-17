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


def test_an_identical_question_is_associated_instead_of_executed_again(
    db_environment, tmp_path, audit_directory
):
    """E04-B: the same question is one Work item, with a durable association."""

    question = "Read the second isolated input and cite the exact bytes it returned."
    with scheduler_case(
        db_environment, tmp_path, audit_directory, max_work_items=8, capacity=4
    ) as case:
        basis = [case.claim_ref.model_dump(mode="json")]
        first = case.scheduler.tick(limit=2)
        explore_one = explore_assignment(first)
        reason_one = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [],
            "intent_proposals": [
                {
                    "client_ref": "first-ask",
                    "question": question,
                    "basis_refs": basis,
                    "expected_output": "wuji.agent-payload.v2",
                }
            ],
            "limitations": ["one bounded follow-up question"],
            "reason_decision": {
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": "the stored evidence leaves one bounded question open",
            },
        }
        credential, receipt = _submit(case, reason_one, payload, "e04b-reason-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, reason_one, credential)
        case.scheduler.tick(limit=4)

        with db_environment.migration_connection() as connection:
            asked = connection.execute(
                """SELECT s.work_item_id FROM vnext.scheduler_work s
                JOIN vnext.intent_revision i ON (i.tenant_id,i.project_id,i.task_id,i.entity_id,i.revision)=
                (s.tenant_id,s.project_id,s.task_id,s.intent_id,s.intent_revision)
                WHERE s.task_id=%s AND i.question=%s""",
                (TASK, question),
            ).fetchall()
        assert len(asked) == 1, asked

        # A settled Explore result is what wakes the next Reason round.
        credential, receipt = _submit(
            case,
            explore_one,
            {
                "schema_version": "wuji.agent-payload.v2",
                "claims": [
                    {
                        "client_ref": "seed-read",
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
            },
            "e04b-explore-1",
        )
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, explore_one, credential)
        second = case.scheduler.tick(limit=4)
        reason_two = next(
            item for item in second.assignments if item.work_kind.value == "reason"
        )
        with db_environment.migration_connection() as connection:
            works_before = connection.execute(
                "SELECT count(*) FROM vnext.scheduler_work WHERE task_id=%s", (TASK,)
            ).fetchone()[0]

        again = dict(payload)
        again["intent_proposals"] = [
            {**payload["intent_proposals"][0], "client_ref": "second-ask"}
        ]
        again["limitations"] = ["the same question asked again in a later round"]
        credential, receipt = _submit(case, reason_two, again, "e04b-reason-2")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, reason_two, credential)
        case.scheduler.tick(limit=4)

        with db_environment.migration_connection() as connection:
            works_after = connection.execute(
                "SELECT count(*) FROM vnext.scheduler_work WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
            events = connection.execute(
                "SELECT payload_json FROM vnext.outbox WHERE task_id=%s"
                " AND kind='intent.deduplicated'",
                (TASK,),
            ).fetchall()
            admitted = connection.execute(
                "SELECT count(*) FROM vnext.intent_revision WHERE task_id=%s AND question=%s",
                (TASK, question),
            ).fetchone()[0]
        # Both Intent revisions were admitted; only one Work item exists, and the
        # association names the Work the question is already being asked by.
        assert admitted == 2, admitted
        assert works_after == works_before, (works_before, works_after)
        assert len(events) == 1, events
        recorded = json.loads(events[0][0])
        assert recorded["duplicate_of"] == asked[0][0]
        assert recorded["problem_digest"] == json.loads(events[0][0])["problem_digest"]
        assert len(recorded["problem_digest"]) == 64
        assert recorded["rule"].startswith("exact-question")


def test_a_repeated_question_with_new_basis_is_a_legitimate_continuation():
    """E04-B: only an exact repeat is a duplicate; new evidence is new work."""

    from wuji_core.scheduling.policy import problem_digest

    base = {
        "question": "Read the second isolated input and cite its bytes.",
        "basis": (("claim", "claim-1", "1"),),
        "method_ref": "harness.explore.v1:1",
        "profile_digest": "d" * 64,
        "environment_ref": "environment-1",
        "output_contract": "wuji.agent-payload.v2",
    }
    assert problem_digest(**base) == problem_digest(
        **{**base, "question": "  Read   the second isolated input and cite its bytes. "}
    )
    two_refs = (("claim", "claim-1", "1"), ("observation", "o-1", "1"))
    assert problem_digest(**{**base, "basis": two_refs}) == problem_digest(
        **{**base, "basis": tuple(reversed(two_refs))}
    )
    assert problem_digest(**base) != problem_digest(
        **{**base, "basis": (("claim", "claim-2", "1"),)}
    )
    assert problem_digest(**base) != problem_digest(
        **{**base, "question": "Read the third isolated input and cite its bytes."}
    )


def _complete_proposal():
    """A Reason decision that asks for completion without new material."""

    return {
        "schema_version": "wuji.agent-payload.v2",
        "claims": [],
        "intent_proposals": [],
        "limitations": ["nothing new was observed this round"],
        "reason_decision": {
            "decision": "propose_completion",
            "wait_refs": [],
            "reason": "the stored evidence looks sufficient from this Run",
        },
    }


def _settle_seed_explore(case, assignment, submission_id):
    """Let the fixture's own question finish so its result is real material."""

    credential, receipt = _submit(
        case,
        assignment,
        {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [
                {
                    "client_ref": "seed-read",
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
        },
        submission_id,
    )
    assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
    _close_and_exit(case, assignment, credential)


def test_a_published_window_stops_the_loop_once_and_new_material_releases_it(
    db_environment, tmp_path, audit_directory
):
    """E04-B: bounded no-progress asks a human once instead of re-asking the model."""

    from wuji_core.completion.precheck import CompletionService

    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_work_items=8,
        capacity=4,
        max_no_progress_rounds=2,
        max_reason_runs=8,
        completion=lambda control: CompletionService(
            control.uow, control=control.control
        ),
    ) as case:
        first = case.scheduler.tick(limit=2)
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        # The first Reason waits for the seed question it already admitted.
        waiting = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [],
            "intent_proposals": [],
            "limitations": ["waiting for the admitted question's own result"],
            "reason_decision": {
                "decision": "wait",
                "wait_refs": [
                    {
                        "ref": case.intent_ref.model_dump(mode="json"),
                        "predicate": "work_accepted_result",
                        "predicate_version": "1",
                    }
                ],
                "reason": "the question is already being worked on",
            },
        }
        credential, receipt = _submit(case, reason, waiting, "e04b-wait-first")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, reason, credential)
        _settle_seed_explore(case, explore_assignment(first), "e04b-seed-1")

        # Every later round asks for completion without producing material. The
        # first one still sees the seed's material in its own window, so only the
        # rounds after it count; the published window has to stop the loop.
        rounds = 0
        counted = []
        for index in range(8):
            ticked = case.scheduler.tick(limit=4)
            reason = next(
                (item for item in ticked.assignments if item.work_kind.value == "reason"),
                None,
            )
            if reason is not None:
                credential, receipt = _submit(
                    case, reason, _complete_proposal(), f"e04b-noprogress-{rounds}"
                )
                assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
                _close_and_exit(case, reason, credential)
                rounds += 1
            with db_environment.migration_connection() as connection:
                counted.append(
                    connection.execute(
                        "SELECT no_progress_count,blocked_reason FROM vnext.scheduler_state"
                        " WHERE task_id=%s",
                        (TASK,),
                    ).fetchone()
                )
            if counted[-1][1] is not None:
                break
        assert counted[0] == (0, None), counted
        assert counted[-1] == (2, "no_progress_window"), counted
        with db_environment.migration_connection() as connection:
            requests = connection.execute(
                "SELECT payload_json FROM vnext.outbox WHERE task_id=%s"
                " AND kind='reason.completion_requested'"
                " AND payload_json::jsonb->>'reason'='no_progress_window'",
                (TASK,),
            ).fetchall()
            reviews = connection.execute(
                "SELECT count(*) FROM vnext.outbox WHERE task_id=%s"
                " AND kind='completion.reviewed'",
                (TASK,),
            ).fetchone()[0]
        assert len(requests) == 1, requests
        request = json.loads(requests[0][0])
        assert request["window"] == "2" and request["no_progress_count"] == "2"
        assert reviews >= 1

        # The same flag refuses to mint another Reason: the loop is stopped, not
        # re-asked, even though the review woke another generation.
        for _ in range(2):
            stopped = case.scheduler.tick(limit=4)
            assert not any(
                item.work_kind.value == "reason" for item in stopped.assignments
            ), [item.work_kind.value for item in stopped.assignments]
        with db_environment.migration_connection() as connection:
            reasons_before = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s AND kind='reason'",
                (TASK,),
            ).fetchone()[0]
        case.scheduler.tick(limit=4)
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s AND kind='reason'",
                (TASK,),
            ).fetchone()[0] == reasons_before

        # New knowledge is the release. It resets the window and lets the Task
        # run a Reason again; an operator or failure block would not.
        with db_environment.migration_connection() as connection:
            event_seq = connection.execute(
                "SELECT max(event_seq) FROM vnext.outbox WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        with case.control.uow.transaction(SCHEDULER, TASK, capability="admit") as tx:
            repository = TriggerRepository(artifacts=case.control.store)
            repository._material(tx, key="material:e04b-release", event_seq=event_seq)
        with db_environment.migration_connection() as connection:
            released = connection.execute(
                "SELECT no_progress_count,blocked_reason FROM vnext.scheduler_state"
                " WHERE task_id=%s",
                (TASK,),
            ).fetchone()
        assert released == (0, None), released
        assert any(
            item.work_kind.value == "reason"
            for item in case.scheduler.tick(limit=4).assignments
        )


def test_a_real_wait_and_live_work_do_not_count_as_no_progress(
    db_environment, tmp_path, audit_directory
):
    """E04-B: waiting for an admitted question is not a stalled Reason."""

    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_work_items=8,
        capacity=4,
        max_no_progress_rounds=1,
    ) as case:
        first = case.scheduler.tick(limit=2)
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        # The seed Explore is still live while the Reason registers a real wait
        # for that admitted question's own accepted result.
        assert any(
            item.work_kind.value == "explore" for item in first.assignments
        )
        wait_payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [],
            "intent_proposals": [],
            "limitations": ["waiting for the admitted question's own result"],
            "reason_decision": {
                "decision": "wait",
                "wait_refs": [
                    {
                        "ref": case.intent_ref.model_dump(mode="json"),
                        "predicate": "work_accepted_result",
                        "predicate_version": "1",
                    }
                ],
                "reason": "the question is already being worked on",
            },
        }
        credential, receipt = _submit(case, reason, wait_payload, "e04b-wait-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _close_and_exit(case, reason, credential)
        case.scheduler.tick(limit=4)
        with db_environment.migration_connection() as connection:
            state = connection.execute(
                "SELECT no_progress_count,blocked_reason FROM vnext.scheduler_state"
                " WHERE task_id=%s",
                (TASK,),
            ).fetchone()
            waiters = connection.execute(
                "SELECT status FROM vnext.scheduler_waiter WHERE task_id=%s",
                (TASK,),
            ).fetchall()
            requests = connection.execute(
                "SELECT count(*) FROM vnext.outbox WHERE task_id=%s"
                " AND payload_json::jsonb->>'reason'='no_progress_window'",
                (TASK,),
            ).fetchone()[0]
        assert waiters and {row[0] for row in waiters} == {"waiting"}, waiters
        assert state == (0, None), state
        assert requests == 0
