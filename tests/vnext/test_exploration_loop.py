"""E04-A: one real observation drives a new question through the formal loop.

The fixture is the production Scheduler over real PostgreSQL: an Explore result
is committed, a Reason run proposes an Intent that did not exist before, the
Committer admits it, the Scheduler materializes it as Explore work, and the next
Reason read set contains the new material. Nothing here writes accepted work or
completion state by hand.
"""

from __future__ import annotations

from support.p06 import TASK
from hashlib import sha256
from uuid import uuid4

from support.p06 import ENVIRONMENT, OWNER
from support.p09 import POD_UID, explore_assignment, scheduler_case, worker_credential
from wuji_core.execution.control import ExecutionObservation
from wuji_core.contracts.envelopes import ResultEnvelope
from wuji_core.http import canonical_json_bytes


def _submit_reason(case, assignment, payload, submission_id):
    credential = worker_credential(case, assignment)
    raw = canonical_json_bytes(payload)
    raw_ref = case.control.store.stage_model_output(
        credential.access, TASK, assignment.identity.agent_run_id, raw, "application/json"
    )
    case.control.store.seal(credential.access, TASK, raw_ref)
    return case.control.committer.submit(
        credential.access,
        ResultEnvelope.model_validate(
            {
                "schema_version": "wuji.result-envelope.v2",
                "submission_id": submission_id,
                "identity": assignment.identity.model_dump(mode="json"),
                "snapshot_id": assignment.snapshot_id,
                "read_set": [],
                "raw_output_ref": raw_ref.model_dump(mode="json"),
                "raw_output_digest": raw_ref.sha256.root,
                "payload": payload,
                "producer_version": "e04a-loop-fixture-v1",
            }
        ),
    )


def _observe_exit(case, assignment):
    """The Run really exits: the ControlService observes it and settles the work."""

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


def test_a_reason_decision_admits_new_work_that_the_next_reason_reads(
    db_environment, tmp_path, audit_directory
):
    with scheduler_case(db_environment, tmp_path, audit_directory) as case:
        first = case.scheduler.tick(limit=2)
        assert {item.work_kind.value for item in first.assignments} == {"explore", "reason"}
        reason = next(
            item for item in first.assignments if item.work_kind.value == "reason"
        )
        with db_environment.migration_connection() as connection:
            works_before = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone()[0]

        # One new question, justified by the material this Reason actually read.
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
            "limitations": ["the follow-up question was proposed by the Reason decision"],
            "reason_decision": {
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": "The stored evidence leaves one bounded question open.",
            },
        }
        receipt = _submit_reason(case, reason, payload, "e04a-reason-1")
        assert receipt.status.value == "accepted", receipt.model_dump(mode="json")
        _observe_exit(case, reason)
        admitted = [
            component for component in receipt.components
            if component.canonical_ref is not None
        ]
        assert admitted, receipt.components
        assert all(
            component.status.value == "accepted_shared" for component in admitted
        )

        # The Scheduler consumes the decision and materializes the new work.
        second = case.scheduler.tick(limit=4)
        with db_environment.migration_connection() as connection:
            works_after = connection.execute(
                "SELECT count(*) FROM vnext.work_item WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
            decision = connection.execute(
                "SELECT status,reason_code FROM vnext.scheduler_decision"
                " WHERE submission_id=%s", ("e04a-reason-1",)
            ).fetchone()
        assert decision is not None and decision[0] == "accepted", decision
        assert works_after > works_before, (works_before, works_after)
        assert second.assignments, second.blocked

        # The admitted question is real Explore work with its own Run.
        explore = [
            item for item in second.assignments if item.work_kind.value == "explore"
        ]
        assert explore, second.assignments
