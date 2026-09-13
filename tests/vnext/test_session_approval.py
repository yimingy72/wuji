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
    FunctionInvocationContext,
    FunctionTool,
    SessionContext,
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
    request_predecessor_positions,
    work_row,
)
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.approvals import approval_response_message
from wuji_maf_worker.factory import HarnessProfile, parse_profile
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
    assert aggregate_schema.HEAD == session_schema.HEAD
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
    ) as case:
        case.upstream.release_first_response.set()
        initial_events = asyncio.run(
            _consume_runtime(case.runtime, case.assignment)
        )
        assert [event.kind for event in initial_events] == ["input_receipt"]
        original_binding = _published_session(case).history.frontier.pending_approvals[0]
        case.record_process(case.assignment, "exited")
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

        approval_ref = case.runtime.input_receipt.approval_refs[0]
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
            == case.runtime.session_receipt.manifest_ref
        )
        resumed = case.child_execute(resumed_assignment)

        assert resumed.exited["observation"]["process"]["exit_code"] == 0, (
            resumed.worker_stderr
        )
        assert resumed.final.state == "exited"
        assert resumed.credential.binding.session_lineage == (
            case.credential.binding.session_lineage
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
                (case.runtime.session_receipt.session_id,),
            ).fetchall()
        assert approval[0:2] == ("approve", "consumed")
        assert approval[2] == call[1]
        assert approval[3] == resumed_assignment.identity.agent_run_id
        assert call[0] == "complete"
        assert attempts == 1
        assert manifests == [("approval_boundary",), ("settled_boundary",)]


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
    ) as case:
        case.upstream.release_first_response.set()
        initial_events = asyncio.run(
            _consume_runtime(case.runtime, case.assignment)
        )
        assert [event.kind for event in initial_events] == ["input_receipt"]
        original = _published_session(case)
        original_binding = original.history.frontier.pending_approvals[0]
        case.record_process(case.assignment, "exited")

        approval_ref = case.runtime.input_receipt.approval_refs[0]
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
        assert resumed.credential.principal.token_id != case.credential.principal.token_id
        assert resumed.credential.binding.session_lineage == (
            case.credential.binding.session_lineage
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
        assert approval == ("reject", "decided", None, None)
        assert call == ("cancelled", None)
        assert attempts == 0
        assert current == (
            True,
            True,
            True,
            case.runtime.session_receipt.manifest_ref,
            case.credential.binding.session_lineage,
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

    positions = request_predecessor_positions(history, request_messages)

    assert {
        history.messages[position.message_index]["contents"][position.content_index][
            "type"
        ]
        for position in positions
    } == {"function_call", "function_result"}
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
    incomplete = request_predecessor_positions(history, without_tool_result)
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
