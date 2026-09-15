"""P08 SessionManifest and native approval acceptance tests."""

import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from inspect import Parameter
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from agent_framework import (
    AgentFileStore,
    AgentSession,
    Content,
    ContextWindowCompactionStrategy,
    FunctionInvocationContext,
    FunctionTool,
    Message,
    SessionContext,
    apply_compaction,
)

from support.p08 import (
    MODEL_ATTEMPT_ID,
    NATIVE_ARGUMENTS,
    PROVIDER_CALL_ID,
    REQUIRED,
    SDK_CONTENT_ID,
    SESSION_LINEAGE,
    TASK,
    TOOL_CALL_ID,
    TOOL_DEFINITION,
    parameter_shape,
    pending_native_identity,
    p08_candidate_case,
    session_limits,
    session_repository_type,
)
from wuji_core.contracts.sessions import (
    ApprovalDeliveryDecision,
    HumanInput,
    InputPayload,
    MessagePosition,
    NativeCallBinding,
    native_rejection_content,
)
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.admission.registry import SessionCapabilityRegistration
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.execution.sessions import (
    document,
    provider_messages,
    predecessor_covers_result,
    request_predecessor_positions,
    work_row,
)
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.approvals import approval_response_message
from wuji_maf_worker.factory import HarnessProfile, SessionHarnessProfile, parse_profile
from wuji_maf_worker.history import PinnedMemoryContextProvider, VersionedMemoryStore
from wuji_maf_worker.tools import ModelCallIdentity


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _capability_document(*, status, evidence_refs, candidate_binding):
    published_at = datetime(2026, 9, 13, tzinfo=timezone.utc)
    profile_body = {
        "schema_version": "wuji.harness.session.v1",
        "ref": "harness.explore.p08-candidate.v1",
        "revision": "1",
        "work_kind": "explore",
        "lock_digest": "b" * 64,
        "memory_mode": "disabled",
        "session_limits": session_limits().model_dump(mode="python"),
        "compaction_enabled": True,
        "capabilities": {},
    }
    profile_snapshot = {
        "ref": profile_body["ref"],
        "revision": profile_body["revision"],
        "body": profile_body,
        "digest": sha256(canonical_json_bytes(profile_body)).hexdigest(),
    }
    client_snapshot = {
        "ref": "fixture-model-v1",
        "revision": "1",
        "protocol": "chat_completions",
        "client_model": "p08-synthetic",
        "upstream_model": "p08-synthetic-upstream",
        "capability_ref": "chat-completions-fixture",
        "max_retries": 0,
    }
    runtime_snapshot = {"ref": "runtime-p08-v1", "revision": "1"}
    framework_snapshot = {
        "python": "3.13.15",
        "agent_framework_core": "1.18.0",
        "agent_framework_openai": "1.14.3",
    }
    return {
        "ref": "session-capability-p08-candidate",
        "revision": "1",
        "published_at": published_at,
        "validation_status": status,
        "candidate_binding": candidate_binding,
        "profile_snapshot": profile_snapshot,
        "profile_digest": profile_snapshot["digest"],
        "client_snapshot": client_snapshot,
        "client_digest": sha256(canonical_json_bytes(client_snapshot)).hexdigest(),
        "runtime_snapshot": runtime_snapshot,
        "runtime_digest": sha256(canonical_json_bytes(runtime_snapshot)).hexdigest(),
        "framework_snapshot": framework_snapshot,
        "framework_digest": sha256(canonical_json_bytes(framework_snapshot)).hexdigest(),
        "lock_digest": profile_body["lock_digest"],
        "limits": profile_body["session_limits"],
        "recovery_classes": ["settled_boundary", "approval_boundary"],
        "memory_mode": "disabled",
        "approver_subjects": ["operator-p08"],
        "approval_ttl_seconds": 300,
        "evidence_refs": evidence_refs,
    }


def test_session_repository_exposes_frozen_publish_and_load_contract():
    repository_type = session_repository_type()

    assert parameter_shape(repository_type) == (
        ("uow", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("artifacts", Parameter.KEYWORD_ONLY, REQUIRED),
        ("registry", Parameter.KEYWORD_ONLY, REQUIRED),
    )
    assert parameter_shape(repository_type.publish) == (
        ("self", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("access", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("assignment", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("manifest", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("expected_revision", Parameter.KEYWORD_ONLY, REQUIRED),
    )
    assert parameter_shape(repository_type.load_published) == (
        ("self", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("access", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("task_id", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("session_id", Parameter.POSITIONAL_OR_KEYWORD, REQUIRED),
        ("revision", Parameter.KEYWORD_ONLY, None),
    )


def test_p08_migration_follows_receiver_results_and_keeps_session_guards():
    from wuji_core.persistence import schema as aggregate_schema
    from wuji_core.persistence import session_schema

    ddl = "\n".join(session_schema.statements())

    assert session_schema.PARENT_HEAD == "vnext_0013_receiver_results"
    assert session_schema.HEAD == "vnext_0014_p08_session_approval"
    # 0015-0018 extend the same ordered chain; the aggregate schema must keep
    # importing and applying exactly this session head.
    assert aggregate_schema.SESSION_HEAD == session_schema.HEAD
    assert "writer_token_id" in ddl
    assert "CREATE TABLE vnext.session_capability" in ddl
    assert "approval_admit boolean := false" in ddl
    assert "OLD.status='pending_approval'" in ddl
    assert "NEW.status='admitted' AND NEW.latest_attempt_id IS NULL" in ddl
    assert "exact approved Session operation required" in ddl
    assert "guard_input_intake_insert" in ddl
    assert "input intake must start pending" in ddl
    assert "guard_approval_intake_insert" in ddl
    assert "approval intake must start pending" in ddl
    assert "check_approval_intake_source" in ddl
    assert "approval, original ToolCall, Attempt and Outbox must commit together" in ddl
    assert "require_scheduler_identity(text,text,text,jsonb)" in ddl


def test_p08_migration_installs_after_receiver_results_with_private_stage_guards(
    db_environment,
):
    from wuji_core.persistence.schema import migrate

    with db_environment.migration_connection() as connection:
        migrate(connection, application_role=db_environment.application_role)
        heads = {
            row[0]
            for row in connection.execute(
                "SELECT head FROM vnext.schema_migration"
            ).fetchall()
        }
        assert "vnext_0013_receiver_results" in heads
        assert "vnext_0014_p08_session_approval" in heads
        assert connection.execute(
            "SELECT to_regclass('vnext.session_stage')"
        ).fetchone() == ("vnext.session_stage",)
        functions = {
            row[0]
            for row in connection.execute(
                """SELECT proname FROM pg_proc p JOIN pg_namespace n
                ON n.oid=p.pronamespace WHERE n.nspname='vnext'
                  AND proname IN ('record_session_stage',
                    'check_session_stage_for_publish',
                    'guard_session_manifest_insert',
                    'mechanism_candidate_receiver_matches',
                    'guard_approval_intake_insert')"""
            ).fetchall()
        }
        assert functions == {
            "record_session_stage",
            "check_session_stage_for_publish",
            "guard_session_manifest_insert",
            "mechanism_candidate_receiver_matches",
            "guard_approval_intake_insert",
        }


def test_real_sdk_candidate_publishes_native_approval_boundary(
    db_environment,
    tmp_path,
    audit_directory,
):
    with p08_candidate_case(
        db_environment,
        tmp_path,
        audit_directory,
    ) as case:
        case.upstream.release_first_response.set()
        events = asyncio.run(_consume_runtime(case.runtime, case.assignment))

        assert len(events) == 1
        assert events[0].kind == "input_receipt"
        assert case.runtime.input_receipt is not None
        assert case.runtime.session_receipt is not None
        with case.environment.migration_connection() as connection:
            manifest = connection.execute(
                "SELECT manifest_json::jsonb->>'recovery_class',"
                "capability_ref,capability_digest FROM vnext.session_manifest "
                "WHERE task_id=%s",
                (TASK,),
            ).fetchone()
            approval = connection.execute(
                "SELECT status,latest_attempt_id FROM vnext.tool_call "
                "WHERE task_id=%s AND work_item_id=%s AND session_lineage=%s",
                (
                    TASK,
                    case.assignment.identity.work_item_id,
                    case.credential.binding.session_lineage,
                ),
            ).fetchone()
            attempts = connection.execute(
                "SELECT count(*) FROM vnext.tool_attempt attempt "
                "JOIN vnext.tool_call call USING(tenant_id,project_id,task_id,tool_call_id) "
                "WHERE attempt.task_id=%s AND call.work_item_id=%s "
                "AND call.session_lineage=%s",
                (
                    TASK,
                    case.assignment.identity.work_item_id,
                    case.credential.binding.session_lineage,
                ),
            ).fetchone()[0]
        assert manifest[0] == "approval_boundary"
        assert manifest[1] == "session-capability-p08-candidate"
        assert len(manifest[2]) == 64
        assert approval == ("pending_approval", None)
        assert attempts == 0


def test_real_approval_http_resumes_original_session_and_executes_once(
    db_environment,
    tmp_path,
    audit_directory,
):
    with p08_candidate_case(
        db_environment,
        tmp_path,
        audit_directory,
        initial_child=True,
    ) as case:
        case.upstream.release_first_response.set()
        initial = case.child_execute(case.assignment, expect_input=True)
        assert initial.exited["observation"]["process"]["exit_code"] == 0
        assert initial.started.observation.process.pid == initial.exited[
            "observation"
        ]["process"]["pid"]
        assert initial.input_receipt is not None
        assert initial.session_receipt is not None
        original_binding = _published_session(case).history.frontier.pending_approvals[0]
        with case.control.uow.transaction(
            case.scheduler.receiver_access,
            TASK,
            capability="observe",
        ) as tx:
            recovery = case.sessions.validate_recovery_in_transaction(
                tx,
                work_row(tx, case.assignment.identity.work_item_id),
            )
        assert recovery.resumable, recovery

        approval_ref = initial.input_receipt.approval_refs[0]
        response = case.approval_client.post(
            f"/api/v2/approvals/{approval_ref}/decisions",
            json={
                "schema_version": "wuji.api.v2",
                "decision": "approve",
                "expected_version": "1",
                "reason": "fixed synthetic P08 approval",
            },
            headers={
                "Authorization": "Bearer " + case.approval_token,
                "Idempotency-Key": "p08-approve-once",
            },
        )
        assert response.status_code == 202, response.text

        resumed_assignment = next(
            item
            for item in case.scheduler.scheduler.tick(limit=2).assignments
            if item.identity.work_item_id == case.assignment.identity.work_item_id
        )
        assert resumed_assignment.session_manifest_ref is not None
        assert (
            resumed_assignment.session_manifest_ref.root
            == initial.session_receipt.manifest_ref
        )
        resumed = case.child_execute(resumed_assignment)

        assert resumed.exited["observation"]["process"]["exit_code"] == 0, (
            resumed.worker_stderr
        )
        assert resumed.final.state == "exited"
        assert resumed.credential.binding.session_lineage == (
            initial.credential.binding.session_lineage
        )
        assert case.upstream.received_tool_receipt is not None
        restored_binding = _published_session(case).provider_state.call_bindings[0]
        assert restored_binding == original_binding
        assert restored_binding.provider_response_ref == original_binding.provider_response_ref
        assert restored_binding.arguments_ref == original_binding.arguments_ref
        with case.environment.migration_connection() as connection:
            approval = connection.execute(
                "SELECT decision,decision_status,consumed_attempt_id,consumed_by_run "
                "FROM vnext.approval_request WHERE approval_ref=%s",
                (approval_ref,),
            ).fetchone()
            call = connection.execute(
                "SELECT status,latest_attempt_id FROM vnext.tool_call "
                "WHERE tool_call_id=%s",
                (case.upstream.received_tool_receipt["tool_call_id"],),
            ).fetchone()
            attempts = connection.execute(
                "SELECT count(*) FROM vnext.tool_attempt WHERE tool_call_id=%s",
                (case.upstream.received_tool_receipt["tool_call_id"],),
            ).fetchone()[0]
            manifests = connection.execute(
                "SELECT manifest_json::jsonb->>'recovery_class' "
                "FROM vnext.session_manifest WHERE session_id=%s ORDER BY revision",
                (initial.session_receipt.session_id,),
            ).fetchall()
            retired = connection.execute(
                "SELECT credential.revoked,writer.revoked FROM vnext.run_credential credential "
                "JOIN vnext.run_writer writer USING(tenant_id,project_id,task_id,agent_run_id,subject) "
                "WHERE credential.agent_run_id=%s AND credential.subject=%s "
                "AND credential.token_id=%s",
                (
                    case.assignment.identity.agent_run_id,
                    initial.credential.principal.subject,
                    initial.credential.principal.token_id,
                ),
            ).fetchone()
            capacity = connection.execute(
                "SELECT state FROM vnext.capacity_reservation WHERE agent_run_id=%s "
                "ORDER BY pool_key",
                (case.assignment.identity.agent_run_id,),
            ).fetchall()
        assert approval[0:2] == ("approve", "consumed")
        assert approval[2] == call[1]
        assert approval[3] == resumed_assignment.identity.agent_run_id
        assert call[0] == "complete"
        assert attempts == 1
        assert manifests == [("approval_boundary",), ("settled_boundary",)]
        assert retired == (True, True)
        assert capacity and {state for (state,) in capacity} == {"released"}


def test_real_rejection_http_restores_native_denial_without_execution(
    db_environment,
    tmp_path,
    audit_directory,
):
    with p08_candidate_case(
        db_environment,
        tmp_path,
        audit_directory,
        reject=True,
        initial_child=True,
    ) as case:
        case.upstream.release_first_response.set()
        initial = case.child_execute(case.assignment, expect_input=True)
        assert initial.exited["observation"]["process"]["exit_code"] == 0
        assert initial.started.observation.process.pid == initial.exited[
            "observation"
        ]["process"]["pid"]
        assert initial.input_receipt is not None
        assert initial.session_receipt is not None
        original = _published_session(case)
        original_binding = original.history.frontier.pending_approvals[0]

        approval_ref = initial.input_receipt.approval_refs[0]
        response = case.approval_client.post(
            f"/api/v2/approvals/{approval_ref}/decisions",
            json={
                "schema_version": "wuji.api.v2",
                "decision": "reject",
                "expected_version": "1",
                "reason": "fixed synthetic P08 rejection",
            },
            headers={
                "Authorization": "Bearer " + case.approval_token,
                "Idempotency-Key": "p08-reject-once",
            },
        )
        assert response.status_code == 202, response.text

        resumed_assignment = next(
            item
            for item in case.scheduler.scheduler.tick(limit=2).assignments
            if item.identity.work_item_id == case.assignment.identity.work_item_id
        )
        resumed = case.child_execute(resumed_assignment)

        assert resumed.exited["observation"]["process"]["exit_code"] == 0, (
            resumed.worker_stderr
        )
        assert resumed.final.state == "exited"
        assert resumed.credential.principal.token_id != initial.credential.principal.token_id
        assert resumed.credential.binding.session_lineage == (
            initial.credential.binding.session_lineage
        )
        assert case.upstream.received_tool_receipt is None
        assert case.upstream.received_rejection == {
            "role": "tool",
            "tool_call_id": original_binding.provider_call_id,
            "content": native_rejection_content(
                original_binding.provider_call_id
            )["result"],
        }
        published = _published_session(case)
        assert published.provider_state.call_bindings[0] == original_binding
        assert len(published.history.frontier.rejected_calls) == 1
        rejected = published.history.frontier.rejected_calls[0]
        rejection_properties = original.provider_state.pending_contents[0][
            "function_call"
        ]["additional_properties"]
        assert rejected.approval_ref == approval_ref
        assert rejected.decision_version == "2"
        assert rejected.call_binding == original_binding
        assert rejected.result_content == native_rejection_content(
            original_binding.provider_call_id,
            additional_properties=rejection_properties,
        )
        with case.environment.migration_connection() as connection:
            approval = connection.execute(
                "SELECT decision,decision_status,consumed_attempt_id,consumed_by_run "
                "FROM vnext.approval_request WHERE approval_ref=%s",
                (approval_ref,),
            ).fetchone()
            call = connection.execute(
                "SELECT status,latest_attempt_id FROM vnext.tool_call "
                "WHERE tool_call_id=%s",
                (original_binding.tool_call_id,),
            ).fetchone()
            attempts = connection.execute(
                "SELECT count(*) FROM vnext.tool_attempt WHERE tool_call_id=%s",
                (original_binding.tool_call_id,),
            ).fetchone()[0]
            current = connection.execute(
                "SELECT access.can_read,access.can_write,access.can_model_output,"
                "holder.manifest_ref,holder.session_lineage "
                "FROM vnext.task_access access JOIN vnext.session_holder holder ON "
                "(holder.tenant_id,holder.project_id,holder.task_id,holder.agent_run_id)="
                "(access.tenant_id,access.project_id,access.task_id,%s) "
                "WHERE access.subject=%s",
                (
                    resumed_assignment.identity.agent_run_id,
                    resumed.credential.principal.subject,
                ),
            ).fetchone()
            retired = connection.execute(
                "SELECT credential.revoked,writer.revoked FROM vnext.run_credential credential "
                "JOIN vnext.run_writer writer USING(tenant_id,project_id,task_id,agent_run_id,subject) "
                "WHERE credential.agent_run_id=%s AND credential.subject=%s "
                "AND credential.token_id=%s",
                (
                    case.assignment.identity.agent_run_id,
                    initial.credential.principal.subject,
                    initial.credential.principal.token_id,
                ),
            ).fetchone()
            capacity = connection.execute(
                "SELECT state FROM vnext.capacity_reservation WHERE agent_run_id=%s "
                "ORDER BY pool_key",
                (case.assignment.identity.agent_run_id,),
            ).fetchall()
            result = connection.execute(
                "SELECT receipt.receipt_json,run.result_state "
                "FROM vnext.agent_run run JOIN vnext.result_submission submission ON "
                "(submission.tenant_id,submission.project_id,submission.task_id,"
                "submission.agent_run_id,submission.submission_id)="
                "(run.tenant_id,run.project_id,run.task_id,run.agent_run_id,"
                "run.result_submission_id) JOIN vnext.result_receipt receipt ON "
                "(receipt.tenant_id,receipt.project_id,receipt.task_id,"
                "receipt.submission_id)=(submission.tenant_id,submission.project_id,"
                "submission.task_id,submission.submission_id) "
                "WHERE run.agent_run_id=%s",
                (resumed_assignment.identity.agent_run_id,),
            ).fetchone()
        assert approval == ("reject", "decided", None, None)
        assert call == ("cancelled", None)
        assert attempts == 0
        assert current == (
            True,
            True,
            True,
            initial.session_receipt.manifest_ref,
            initial.credential.binding.session_lineage,
        )
        assert retired == (True, True)
        assert capacity and {state for (state,) in capacity} == {"released"}
        result_receipt = strict_json_loads(result[0])
        assert result[1] == "accepted"
        assert result_receipt["status"] == "accepted"
        assert result_receipt["code"] is None
        assert result_receipt["components"] == []


def test_fixed_memory_and_native_compaction_survive_two_child_generations(
    db_environment,
    tmp_path,
    audit_directory,
):
    fixed_memory = {
        "counterevidence.txt": b"the current hypothesis remains unconfirmed\n",
        "facts/current.txt": b"fixture memory revision seven\n",
    }
    with p08_candidate_case(
        db_environment,
        tmp_path,
        audit_directory,
        initial_child=True,
        memory_files=fixed_memory,
        compaction_enabled=True,
        max_context_window_tokens=1_200,
        max_output_tokens=80,
        session_max_total_bytes=131_072,
    ) as case:
        case.upstream.release_first_response.set()
        initial = case.child_execute(case.assignment, expect_input=True)
        assert initial.exited["observation"]["process"]["exit_code"] == 0, (
            initial.worker_stderr
        )
        assert initial.input_receipt is not None
        assert initial.session_receipt is not None
        first = _published_session(case)
        assert first.memory.enabled is True
        assert {file.path for file in first.memory.files} == set(fixed_memory)
        for file in first.memory.files:
            key = file.ref.id + "@" + file.ref.version.root
            assert first.object_bytes[key] == fixed_memory[file.path]
            assert file.ref.sha256.root == case.memory_source_refs[
                file.path
            ].sha256.root

        approval_ref = initial.input_receipt.approval_refs[0]
        response = case.approval_client.post(
            f"/api/v2/approvals/{approval_ref}/decisions",
            json={
                "schema_version": "wuji.api.v2",
                "decision": "approve",
                "expected_version": "1",
                "reason": "fixed memory and compaction recovery",
            },
            headers={
                "Authorization": "Bearer " + case.approval_token,
                "Idempotency-Key": "p08-memory-compaction-approve",
            },
        )
        assert response.status_code == 202, response.text
        resumed_assignment = next(
            item
            for item in case.scheduler.scheduler.tick(limit=2).assignments
            if item.identity.work_item_id == case.assignment.identity.work_item_id
        )
        resumed = case.child_execute(resumed_assignment)
        assert resumed.exited["observation"]["process"]["exit_code"] == 0, (
            resumed.worker_stderr
        )

        final = _published_session(case)
        assert final.receipt.checkpoint_revision == "2"
        assert len(final.history.frontier.model_entries) == 2
        original_binding = first.provider_state.call_bindings[0]
        restored_binding = final.provider_state.call_bindings[0]
        assert restored_binding.model_dump(exclude={"position"}) == (
            original_binding.model_dump(exclude={"position"})
        )
        assert restored_binding.position.model_dump(exclude={"message_digest"}) == (
            original_binding.position.model_dump(exclude={"message_digest"})
        )
        assert final.history.frontier.archived_history_refs
        for file in final.memory.files:
            key = file.ref.id + "@" + file.ref.version.root
            assert final.object_bytes[key] == fixed_memory[file.path]
        excluded = [
            message
            for message in final.history.messages
            if message.get("additional_properties", {}).get("_excluded") is True
        ]
        assert {message["role"] for message in excluded} == {"assistant", "tool"}
        assert {
            message["additional_properties"]["_group"]["id"]
            for message in excluded
        } == {"group_chatcmpl-m1-tool"}
        assert {
            message["additional_properties"]["_exclude_reason"]
            for message in excluded
        } == {"truncation"}
        for entry in final.history.frontier.model_entries:
            assert entry.request_messages
            assert entry.request_messages_digest == sha256(
                canonical_json_bytes(entry.request_messages)
            ).hexdigest()
        assert all(
            sum(
                "wuji.session.memory-context.v1" in message.get("content", "")
                for message in entry.request_messages
                if isinstance(message.get("content"), str)
            ) == 1
            for entry in final.history.frontier.model_entries
        )


def _published_session(case):
    with case.control.uow.transaction(
        case.scheduler.receiver_access,
        TASK,
        capability="observe",
    ) as tx:
        return case.sessions._load_in_transaction(
            tx,
            work_row(tx, case.assignment.identity.work_item_id),
        )


async def _consume_runtime(runtime, assignment):
    events = [event async for event in runtime.execute(assignment)]
    await runtime.aclose()
    return events


def test_mechanism_candidate_requires_exact_short_lived_binding_without_fake_pass():
    published_at = datetime(2026, 9, 13, tzinfo=timezone.utc)
    binding = {
        "tenant_id": "tenant-p08",
        "project_id": "project-p08",
        "task_id": "task-p08",
        "receiver_id": "receiver-p08",
        "runtime_attempt": "1",
        "pod_uid": "pod-p08",
        "model_gateway_digest": "c" * 64,
        "expires_at": published_at + timedelta(minutes=30),
    }

    candidate = SessionCapabilityRegistration.model_validate(
        _capability_document(
            status="mechanism_candidate",
            evidence_refs=[],
            candidate_binding=binding,
        )
    )

    assert candidate.validation_status == "mechanism_candidate"
    assert candidate.evidence_refs == []
    assert candidate.candidate_binding.model_dump(mode="json") == {
        **binding,
        "expires_at": "2026-09-13T00:30:00Z",
    }
    identity = RunIdentity.model_validate(
        {
            "tenant_id": binding["tenant_id"],
            "project_id": binding["project_id"],
            "task_id": binding["task_id"],
            "work_item_id": "work-p08",
            "agent_run_id": "run-p08",
            "receiver_id": binding["receiver_id"],
            "execution_epoch": "1",
            "run_epoch": "1",
            "runtime_attempt": binding["runtime_attempt"],
        }
    )
    assert candidate.candidate_binding.matches_identity(identity)
    assert not candidate.candidate_binding.matches_identity(
        identity.model_copy(update={"receiver_id": "other-receiver"})
    )
    with pytest.raises(ValueError, match="short-lived exact binding"):
        SessionCapabilityRegistration.model_validate(
            _capability_document(
                status="mechanism_candidate",
                evidence_refs=[],
                candidate_binding={
                    **binding,
                    "expires_at": published_at + timedelta(hours=2),
                },
            )
        )


def test_verified_session_capability_requires_real_evidence_and_new_immutable_record():
    verified = _capability_document(
        status="verified",
        evidence_refs=["docs/vnext/evidence/P08/final/binding.json"],
        candidate_binding=None,
    )
    verified["ref"] = "session-capability-p08-verified"

    registration = SessionCapabilityRegistration.model_validate(verified)

    assert registration.validation_status == "verified"
    assert registration.candidate_binding is None
    with pytest.raises(ValueError, match="verified capability requires actual evidence"):
        SessionCapabilityRegistration.model_validate(
            _capability_document(
                status="verified",
                evidence_refs=[],
                candidate_binding=None,
            )
        )


def test_rejected_frontier_binds_persisted_decision_to_actual_native_result():
    from wuji_core.contracts.sessions import (
        MessagePosition,
        RejectedCallFrontierEntry,
        native_rejection_content,
    )

    p01 = json.loads(
        (REPOSITORY_ROOT / "docs/vnext/capability-record.json").read_text(
            encoding="utf-8"
        )
    )
    resumed = p01["raw_sdk_and_http"]["cases"]["reject"]["processes"][1][
        "result"
    ]
    messages = resumed["session_after"]["state"]["in_memory"]["messages"]
    result_message_index = next(
        index for index, message in enumerate(messages) if message["role"] == "tool"
    )
    result_message = messages[result_message_index]
    assert len(result_message["contents"]) == 1
    actual_p01_result = result_message["contents"][0]
    actual_p01_call_id = resumed["approval_response"]["function_call"]["call_id"]
    assert actual_p01_result == native_rejection_content(actual_p01_call_id)

    original, pending, _native_response = pending_native_identity()
    binding = original.export_bindings()[0]
    restored = ModelCallIdentity([TOOL_DEFINITION], max_bytes=65_536)
    restored.restore_bindings(
        call_bindings=(binding,),
        pending_contents=(Content.from_dict(pending.to_dict()),),
        lineage=SESSION_LINEAGE,
    )
    decision = ApprovalDeliveryDecision(
        approval_ref="approval-p08-reject",
        decision_version="2",
        decision="reject",
        pending_content=pending.to_dict(),
        call_binding=binding,
    )
    payload = InputPayload(kind="approval", decisions=(decision,))
    restored.bind_delivery(
        HumanInput(
            delivery_id="delivery-p08-reject",
            input_request_id="input-p08-reject",
            manifest_ref="manifest-p08",
            payload_digest=sha256(
                canonical_json_bytes(payload.model_dump(mode="python"))
            ).hexdigest(),
            payload=payload,
        )
    )

    assert restored.rejected_decisions() == (decision,)
    result_content = native_rejection_content(binding.provider_call_id)
    result_message = {
        "role": "tool",
        "contents": [result_content],
        "additional_properties": {},
        "type": "message",
    }
    result_message_index = 2
    result_position = MessagePosition(
        message_index=result_message_index,
        content_index=0,
        message_digest=sha256(canonical_json_bytes(result_message)).hexdigest(),
        content_digest=sha256(canonical_json_bytes(result_content)).hexdigest(),
    )
    entry = RejectedCallFrontierEntry(
        approval_ref=decision.approval_ref,
        decision_version=decision.decision_version,
        call_binding=binding,
        result_position=result_position,
        result_content=result_content,
        result_digest=result_position.content_digest,
    )

    assert entry.result_content["type"] == "function_result"
    assert entry.result_content["call_id"] == binding.provider_call_id
    assert entry.result_content["items"][0]["text"] == entry.result_content["result"]


def test_p06_request_messages_bind_tool_result_to_earlier_native_position():
    p01 = json.loads(
        (REPOSITORY_ROOT / "docs/vnext/capability-record.json").read_text(
            encoding="utf-8"
        )
    )
    case = p01["raw_sdk_and_http"]["cases"]["reject"]
    resumed = case["processes"][1]["result"]
    history = SimpleNamespace(
        messages=tuple(
            resumed["session_after"]["state"]["in_memory"]["messages"]
        )
    )
    request_messages = tuple(
        json.loads(case["restore_http"][0]["request_body"])["messages"]
    )

    instructions = request_messages[0]["content"]
    with pytest.raises(DomainError) as missing:
        request_predecessor_positions(history, request_messages)
    assert missing.value.code == "SESSION_FRONTIER_MISMATCH"
    with pytest.raises(DomainError) as wrong:
        request_predecessor_positions(
            history, request_messages, instructions="Read a different instruction."
        )
    assert wrong.value.code == "SESSION_FRONTIER_MISMATCH"

    positions = request_predecessor_positions(
        history, request_messages, instructions=instructions
    )

    assert {
        history.messages[position.message_index]["contents"][position.content_index][
            "type"
        ]
        for position in positions
    } == {"text", "function_call", "function_result"}
    result_position = next(
        position
        for position in positions
        if history.messages[position.message_index]["contents"][
            position.content_index
        ]["type"]
        == "function_result"
    )
    assert result_position.message_index < len(history.messages) - 1

    without_tool_result = tuple(
        message for message in request_messages if message.get("role") != "tool"
    )
    incomplete = request_predecessor_positions(
        history, without_tool_result, instructions=instructions
    )
    assert all(
        history.messages[position.message_index]["contents"][position.content_index][
            "type"
        ]
        != "function_result"
        for position in incomplete
    )


def test_session_manifest_uses_json_mode_for_canonical_saved_at_bytes():
    blob = {
        "id": "session-root-p08",
        "version": "1",
        "sha256": "a" * 64,
    }
    manifest = SessionManifest.model_validate(
        {
            "session_id": "native-session-p08",
            "work_item_id": "work-p08",
            "checkpoint_revision": "1",
            "owner_run_id": "run-p08",
            "run_epoch": "1",
            "history_root": blob,
            "message_end": "1",
            "provider_state_ref": {**blob, "id": "provider-root-p08"},
            "memory_manifest_ref": {**blob, "id": "memory-root-p08"},
            "pending_operation_refs": [],
            "lock_digest": "b" * 64,
            "recovery_class": "settled_boundary",
            "saved_at": datetime(2026, 9, 13, tzinfo=timezone.utc),
        }
    )

    body = document(manifest)
    encoded = canonical_json_bytes(body)

    assert isinstance(manifest.model_dump(mode="python")["saved_at"], datetime)
    assert body["saved_at"] == "2026-09-13T00:00:00Z"
    assert strict_json_loads(encoded) == body


def test_provider_sse_preserves_full_call_identity_and_raw_argument_fragments():
    provider_call_id = "p" * 1024
    raw = (
        b'data: {"choices":[{"index":0,"delta":{"tool_calls":['
        b'{"index":0,"id":"'
        + provider_call_id.encode("ascii")
        + b'","function":{"name":"read_fixture","arguments":"{\\"path\\":"}}]}}]}\n\n'
        b'data: {"choices":[{"index":0,"delta":{"tool_calls":['
        b'{"index":0,"function":{"arguments":"\\"version.txt\\"}"}}]}}]}\n\n'
        b'data: [DONE]\n\n'
    )

    parsed = provider_messages(raw, "text/event-stream")

    assert parsed == {
        0: {
            "content": "",
            "tool_calls": [
                {
                    "id": provider_call_id,
                    "function": {
                        "name": "read_fixture",
                        "arguments": NATIVE_ARGUMENTS,
                    },
                }
            ],
        }
    }
    binding = NativeCallBinding(
        model_attempt_id=MODEL_ATTEMPT_ID,
        message_id=f"model-attempt:{MODEL_ATTEMPT_ID}:choice:0",
        provider_call_id=provider_call_id,
        sdk_content_id=SDK_CONTENT_ID,
        tool_definition_ref=TOOL_DEFINITION["ref"],
        native_arguments=NATIVE_ARGUMENTS,
        arguments_digest=sha256(
            canonical_json_bytes(strict_json_loads(NATIVE_ARGUMENTS))
        ).hexdigest(),
    )
    assert binding.provider_call_id == provider_call_id

    with pytest.raises(DomainError) as incomplete:
        provider_messages(raw.rsplit(b"data: [DONE]", 1)[0], "text/event-stream")
    assert incomplete.value.code == "OPERATION_UNKNOWN"


def test_existing_m1_profile_snapshot_remains_the_original_false_capability_shape():
    profile = HarnessProfile(
        ref="harness.explore.m1.v1",
        revision="1",
        work_kind="explore",
        instructions="Read the registered fixture once.",
        tool_definition_refs=(TOOL_DEFINITION["ref"],),
        lock_digest="a" * 64,
        max_context_records=32,
        max_context_bytes=65_536,
        max_output_tokens=2_048,
    )

    snapshot = profile.snapshot()

    assert snapshot["body"]["capabilities"] == {
        name: False
        for name in (
            "todo",
            "mode",
            "file_memory",
            "file_access",
            "skills",
            "shell",
            "web_search",
            "background_agents",
            "outer_loop",
            "auto_approval",
            "compaction",
            "restoration",
            "mcp",
        )
    }
    assert "schema_version" not in snapshot["body"]
    assert snapshot["digest"] == sha256(
        canonical_json_bytes(snapshot["body"])
    ).hexdigest()
    assert parse_profile(snapshot) == profile


def test_pre_invocation_identity_capture_preserves_public_native_approval_content():
    identity, pending, native_response = pending_native_identity()

    binding = identity.export_bindings()[0]
    restored_content = Content.from_dict(pending.to_dict())

    assert native_response.messages[0].contents[-1] is pending
    assert restored_content.to_dict() == pending.to_dict()
    assert binding.model_attempt_id == MODEL_ATTEMPT_ID
    assert binding.message_id == f"model-attempt:{MODEL_ATTEMPT_ID}:choice:0"
    assert binding.provider_call_id == PROVIDER_CALL_ID
    assert binding.sdk_content_id == SDK_CONTENT_ID
    assert binding.sdk_approval_id == SDK_CONTENT_ID
    assert binding.native_arguments == NATIVE_ARGUMENTS
    assert binding.tool_call_id == TOOL_CALL_ID


def test_restored_approved_callback_uses_original_lineage_attempt_and_approval_ref():
    original, pending, _native_response = pending_native_identity()
    binding = original.export_bindings()[0]
    restored = ModelCallIdentity([TOOL_DEFINITION], max_bytes=65_536)
    restored.restore_bindings(
        call_bindings=(binding,),
        pending_contents=(Content.from_dict(pending.to_dict()),),
        lineage=SESSION_LINEAGE,
    )
    decision = ApprovalDeliveryDecision(
        approval_ref="approval-p08",
        decision_version="1",
        decision="approve",
        pending_content=pending.to_dict(),
        call_binding=binding,
    )
    payload = InputPayload(kind="approval", decisions=(decision,))
    delivery = HumanInput(
        delivery_id="delivery-p08",
        input_request_id="input-p08",
        manifest_ref="manifest-p08",
        payload_digest=sha256(
            canonical_json_bytes(payload.model_dump(mode="python"))
        ).hexdigest(),
        payload=payload,
    )
    restored.bind_delivery(delivery)
    tool = FunctionTool(
        name=TOOL_DEFINITION["name"],
        input_model=TOOL_DEFINITION["input_schema"],
        func=lambda **_arguments: None,
        approval_mode="always_require",
    )
    approval_response = approval_response_message(
        pending_content=pending,
        decision="approve",
    ).contents[0]
    context = FunctionInvocationContext(
        function=tool,
        arguments={"path": "version.txt"},
        metadata={
            "call_id": PROVIDER_CALL_ID,
            "function_call_occurrence_id": SDK_CONTENT_ID,
            "approval_response": approval_response,
        },
    )

    request = restored.bind(context, TOOL_DEFINITION, SESSION_LINEAGE)

    assert request.model_dump(mode="json") == {
        "session_lineage": SESSION_LINEAGE,
        "message_id": f"model-attempt:{MODEL_ATTEMPT_ID}:choice:0",
        "provider_call_id": PROVIDER_CALL_ID,
        "tool_definition_ref": TOOL_DEFINITION["ref"],
        "arguments": {"path": "version.txt"},
        "sdk_content_id": SDK_CONTENT_ID,
        "sdk_approval_id": SDK_CONTENT_ID,
        "approval_ref": "approval-p08",
    }

    # When the SDK does rebind the response it records the private approval
    # request id; a value that does not match the pending request must still
    # fail closed even though the public content carries the right identity.
    forged_body = approval_response.to_dict()
    forged_body["additional_properties"] = {"_approval_request_id": "af-foreign"}
    context.metadata["approval_response"] = Content.from_dict(forged_body)
    with pytest.raises(ValueError, match="approval_request_id"):
        restored.bind(context, TOOL_DEFINITION, SESSION_LINEAGE)


def test_versioned_memory_store_keeps_only_fixed_relative_utf8_bytes():
    store = VersionedMemoryStore(
        limits=session_limits(),
        files={"facts/current.txt": b"fixed revision one"},
    )

    assert isinstance(store, AgentFileStore)
    assert asyncio.run(store.read("facts/current.txt")) == "fixed revision one"
    asyncio.run(store.write("notes.txt", "bounded note"))
    assert store.snapshot_files() == {
        "facts/current.txt": b"fixed revision one",
        "notes.txt": b"bounded note",
    }
    with pytest.raises(ValueError, match="inside this fixed Session store"):
        asyncio.run(store.read("../latest.txt"))


def test_pinned_memory_context_injects_complete_versioned_input_without_tools_or_model():
    store = VersionedMemoryStore(
        limits=session_limits(),
        files={
            "counterevidence.txt": b"hypothesis remains unconfirmed",
            "facts/current.txt": b"fixed revision one",
        },
    )
    provider = PinnedMemoryContextProvider(
        source_id="pinned_memory",
        store=store,
        max_context_bytes=65_536,
    )
    session = AgentSession(session_id="native-session-p08")
    context = SessionContext(session_id=session.session_id, input_messages=[])
    state = {}

    asyncio.run(
        provider.before_run(
            agent=object(),
            session=session,
            context=context,
            state=state,
        )
    )

    messages = context.get_messages()
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert strict_json_loads(messages[0].text) == {
        "schema_version": "wuji.session.memory-context.v1",
        "session_id": session.session_id,
        "files": [
            {
                "path": "counterevidence.txt",
                "text": "hypothesis remains unconfirmed",
            },
            {"path": "facts/current.txt", "text": "fixed revision one"},
        ],
    }
    assert context.tools == []
    assert context.instructions == []
    assert set(state) == {"content_digest"}

    asyncio.run(store.write("facts/current.txt", "mutable latest", overwrite=True))
    with pytest.raises(
        ValueError,
        match="memory provider no longer matches its fixed publication",
    ):
        asyncio.run(
            provider.before_run(
                agent=object(),
                session=session,
                context=SessionContext(
                    session_id=session.session_id,
                    input_messages=[],
                ),
                state=state,
            )
        )


def test_session_profile_binds_nonempty_memory_to_fixed_artifact_revisions():
    common = {
        "ref": "harness.explore.memory-p08.v1",
        "revision": "1",
        "work_kind": "explore",
        "instructions": "Use the fixed memory input.",
        "tool_definition_refs": (TOOL_DEFINITION["ref"],),
        "lock_digest": "a" * 64,
        "max_context_records": 32,
        "max_context_bytes": 65_536,
        "max_output_tokens": 512,
        "history_source_id": "history_memory_p08",
        "memory_source_id": "memory_input_p08",
        "session_limits": session_limits(),
        "max_context_window_tokens": 4_096,
        "compaction_enabled": False,
    }
    memory_input = {
        "path": "facts/current.txt",
        "ref": {
            "entity_type": "artifact",
            "id": "memory-artifact-p08",
            "revision": "7",
        },
    }
    profile = SessionHarnessProfile(
        **common,
        memory_mode="pinned_context",
        memory_inputs=(memory_input,),
    )

    snapshot = profile.snapshot()

    assert snapshot["body"]["memory_inputs"] == [memory_input]
    assert parse_profile(snapshot) == profile
    disabled = SessionHarnessProfile(**common, memory_mode="disabled")
    assert "memory_inputs" not in disabled.snapshot()["body"]
    with pytest.raises(ValueError, match="unique pinned artifact"):
        SessionHarnessProfile(
            **common,
            memory_mode="disabled",
            memory_inputs=(memory_input,),
        )


def test_public_compaction_keeps_full_tool_history_and_maps_request_summary():
    def text_message(role, text):
        return Message(role=role, contents=[Content.from_text(text)])

    def tool_group(number):
        return [
            Message(
                role="assistant",
                contents=[
                    Content.from_function_call(
                        f"call-{number}",
                        "read_fixture",
                        arguments={"path": f"file-{number}.txt"},
                        id=f"occ-{number}",
                    )
                ],
            ),
            Message(
                role="tool",
                contents=[
                    Content.from_function_result(
                        f"call-{number}",
                        result="result-" + ("x" * 320),
                    )
                ],
            ),
        ]

    messages = [text_message("user", "first-" + ("q" * 320))]
    messages += tool_group(1)
    messages += [text_message("user", "middle-" + ("m" * 320))]
    messages += tool_group(2)
    messages += [text_message("user", "latest-" + ("z" * 320))]
    original = [message.to_dict() for message in messages]
    strategy = ContextWindowCompactionStrategy(
        max_context_window_tokens=1_200,
        max_output_tokens=80,
        keep_last_tool_call_groups=1,
        preserve_first_user_group=True,
        tool_eviction_threshold=0.5,
        truncation_threshold=0.8,
    )

    projected = asyncio.run(apply_compaction(messages, strategy=strategy))
    complete = [message.to_dict() for message in messages]
    request_messages = []
    for message in (item.to_dict() for item in projected):
        if message["role"] == "assistant" and any(
            content["type"] == "function_call" for content in message["contents"]
        ):
            calls = []
            for content in message["contents"]:
                if content["type"] != "function_call":
                    continue
                arguments = content["arguments"]
                if not isinstance(arguments, str):
                    arguments = canonical_json_bytes(arguments).decode()
                calls.append(
                    {
                        "id": content["call_id"],
                        "type": "function",
                        "function": {
                            "name": content["name"],
                            "arguments": arguments,
                        },
                    }
                )
            request_messages.append({"role": "assistant", "tool_calls": calls})
        elif message["role"] == "tool":
            content = message["contents"][0]
            request_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": content["call_id"],
                    "content": content["result"],
                }
            )
        else:
            request_messages.append(
                {
                    "role": message["role"],
                    "content": "".join(
                        content.get("text", "") for content in message["contents"]
                    ),
                }
            )

    summary = complete[1]
    first_call, first_result = complete[2:4]
    assert first_call["contents"] == original[1]["contents"]
    assert first_result["contents"] == original[2]["contents"]
    assert first_call["additional_properties"]["_excluded"] is True
    assert first_result["additional_properties"]["_excluded"] is True
    assert summary["additional_properties"]["_excluded"] is False
    assert summary["additional_properties"]["_group"][
        "_summary_of_message_ids"
    ] == [first_call["message_id"], first_result["message_id"]]
    assert len(projected) == 6 < len(complete)

    history = SimpleNamespace(messages=tuple(complete), message_end=len(complete))
    predecessors = request_predecessor_positions(history, tuple(request_messages))
    result_position = MessagePosition(
        message_index=3,
        content_index=0,
        message_digest=sha256(canonical_json_bytes(first_result)).hexdigest(),
        content_digest=sha256(
            canonical_json_bytes(first_result["contents"][0])
        ).hexdigest(),
        native_message_id=first_result["message_id"],
    )
    assert predecessor_covers_result(history, predecessors, result_position)
