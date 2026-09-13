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
    TOOL_CALL_ID,
    TOOL_DEFINITION,
    parameter_shape,
    pending_native_identity,
    session_limits,
    session_repository_type,
)
from wuji_core.contracts.sessions import (
    ApprovalDeliveryDecision,
    HumanInput,
    InputPayload,
    NativeCallBinding,
)
from wuji_core.contracts.execution import SessionManifest
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.admission.registry import SessionCapabilityRegistration
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.execution.sessions import (
    document,
    provider_messages,
    request_predecessor_positions,
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
