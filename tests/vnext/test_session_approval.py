"""P08 SessionManifest and native approval acceptance tests."""

import asyncio
from hashlib import sha256
from inspect import Parameter

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
)
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_maf_worker.approvals import approval_response_message
from wuji_maf_worker.factory import HarnessProfile, parse_profile
from wuji_maf_worker.history import PinnedMemoryContextProvider, VersionedMemoryStore
from wuji_maf_worker.tools import ModelCallIdentity


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
