"""Native v2 publication/recovery over the existing real PostgreSQL fixture."""

import asyncio
from hashlib import sha256

import pytest
from support.p08 import p08_candidate_case
from support.p06 import WORKSPACE_INPUT_SCHEMA
from test_problem_maf import _profile
from wuji_core.http import canonical_json_bytes
from wuji_core.execution.sessions import work_row
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.capability_manifest import build_capability_manifest
from wuji_maf_worker.factory import ProblemHarnessProfile


def native_profiles(profiles):
    _, snapshot = _profile()
    old = profiles["explore"]["body"]
    body = {
        **snapshot["body"],
        **{name: old[name] for name in (
            "ref", "revision", "instructions", "tool_definition_refs",
            "lock_digest", "session_limits", "max_output_tokens",
        )},
        "capability_manifest": build_capability_manifest(
            environment_tools=({
                "name": "read_fixture", "ref": old["tool_definition_refs"][0],
                "revision": "1",
                "input_schema": WORKSPACE_INPUT_SCHEMA,
            },),
            include_todo=True, include_memory=True, include_knowledge=True,
            session_limit=16, knowledge_limit=8, environment_limit=4,
        ),
        "function_limits": {
            **snapshot["body"]["function_limits"], "environment_action_per_work": 4,
        },
    }
    native = {"ref": body["ref"], "revision": body["revision"], "body": body,
              "digest": sha256(canonical_json_bytes(body)).hexdigest()}
    return {**profiles, "explore": ProblemHarnessProfile.from_snapshot(native).snapshot()}


def test_native_approval_checkpoint_is_published_and_read_back(
    db_environment, tmp_path, audit_directory
):
    with p08_candidate_case(
        db_environment, tmp_path, audit_directory,
        profile_transform=native_profiles, session_max_total_bytes=262_144, reject=True,
    ) as case:
        case.upstream.release_first_response.set()

        async def run(runtime, assignment):
            try:
                return [event async for event in runtime.execute(assignment)]
            finally:
                await runtime.aclose()

        events = asyncio.run(run(case.runtime, case.assignment))
        assert [event.kind for event in events] == ["input_receipt"]
        receipt = case.runtime.session_receipt
        assert receipt is not None
        published = case.sessions.load_published(
            case.scheduler.receiver_access, case.assignment.identity.task_id,
            receipt.session_id, revision=receipt.checkpoint_revision,
        )
        assert published.manifest.schema_version == "wuji.session.native.v2"
        assert published.manifest.boundary_kind == "approval_wait"
        assert published.receipt == receipt
        assert len(published.operation_fence.pending_approval_refs) == 1
        assert case.sessions.publish(
            case.scheduler.receiver_access, case.assignment, published.manifest,
            expected_revision=0,
        ) == receipt
        with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
            case.sessions.publish(
                case.scheduler.receiver_access, case.assignment,
                published.manifest.model_copy(update={"boundary_kind": "run_return"}),
                expected_revision=0,
            )
        case.record_process(case.assignment, "exited")
        approval_ref = case.runtime.input_receipt.approval_refs[0]
        response = case.approval_client.post(
            f"/api/v2/approvals/{approval_ref}/decisions",
            json={"schema_version": "wuji.api.v2", "decision": "reject",
                  "expected_version": "1", "reason": "native v2 original-call rejection"},
            headers={"Authorization": "Bearer " + case.approval_token,
                     "Idempotency-Key": "native-v2-reject"},
        )
        assert response.status_code == 202, response.text
        with case.control.uow.transaction(
            case.scheduler.receiver_access, case.assignment.identity.task_id,
            capability="observe",
        ) as tx:
            recovery = case.sessions.validate_recovery_in_transaction(
                tx, work_row(tx, case.assignment.identity.work_item_id)
            )
        assert recovery.resumable, recovery
        resumed_assignment = next(
            item for item in case.scheduler.scheduler.tick(limit=2).assignments
            if item.identity.work_item_id == case.assignment.identity.work_item_id
        )
        resumed = case.runtime_for(resumed_assignment)
        events = asyncio.run(run(resumed.runtime, resumed_assignment))
        assert resumed.runtime.session_receipt is not None
        assert resumed.runtime.session_receipt.checkpoint_revision == "2"
        assert case.upstream.received_tool_receipt is None
        assert case.upstream.received_rejection is not None
        with case.environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.tool_attempt WHERE task_id=%s AND tool_call_id=%s",
                (case.assignment.identity.task_id,
                 published.operation_fence.pending_approval_refs[0]),
            ).fetchone()[0] == 0
        with pytest.raises(DomainError, match="STALE_EXECUTION"):
            case.sessions.publish(
                case.scheduler.receiver_access, resumed_assignment,
                published.manifest, expected_revision=0,
            )
        case.record_process(resumed_assignment, "exited")
        with case.control.uow.transaction(
            case.scheduler.receiver_access, case.assignment.identity.task_id,
            capability="observe",
        ) as tx:
            work = work_row(tx, case.assignment.identity.work_item_id)
            old_recovery = case.sessions.validate_recovery_in_transaction(
                tx, {**work, "session_revision": 1}
            )
        assert not old_recovery.resumable
        assert old_recovery.reason_code in {"OPERATION_UNKNOWN", "SESSION_FRONTIER_MISMATCH"}
