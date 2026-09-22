import asyncio
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace

import httpx
from agent_framework import AgentSession, Content, Message

from support.m1 import _sse
from wuji_core.admission.common import model_function_capabilities
from wuji_core.contracts.admission import ToolCallReceipt
from wuji_core.contracts import generated as wire
from wuji_core.contracts.sessions import NativeCallBinding, SessionCompatibility, SessionLimits
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.worker_host import PlatformWorkerHost
from wuji_maf_worker.capability_manifest import build_capability_manifest
from wuji_maf_worker.factory import ProblemHarnessProfile, build_agent
from wuji_maf_worker.history import BoundedWorkMemoryProvider, HistoryArchive, WorkMemoryStore
from wuji_maf_worker.runtime import CheckpointBeforeModel, _settled_boundary
from wuji_maf_worker.remote_host import HostTransportError
from wuji_maf_worker.sessions import NativeSessionAdapter
from wuji_maf_worker.tools import FunctionBudget, GateFunctions, ModelCallIdentity


def test_problem_model_capabilities_use_the_current_run_profile_without_assignment_read():
    profile, snapshot = _profile()
    tx = SimpleNamespace(
        task={
            "definition_json": canonical_json_bytes(
                {"worker_profiles": {"explore": snapshot}}
            ).decode()
        },
        run_binding=SimpleNamespace(allowed_tool_refs=()),
    )
    config = SimpleNamespace(
        allowed_tool_refs=(), runtime=SimpleNamespace(allowed_tool_refs=())
    )

    capabilities, environment_refs = model_function_capabilities(
        tx, object(), config, {"agent_run_id": "run-1"}, {"kind": "explore"}
    )

    assert set(capabilities) == {
        item.name for item in profile.capability_manifest
    }
    assert environment_refs == set()


def test_problem_result_binding_digests_the_v3_brief_components():
    semantic = {
        "schema_version": "wuji.work-brief.v1",
        "brief": {"question": "obtain authorized evidence"},
        "knowledge_index": [],
        "initial_deliveries": [],
    }
    text = canonical_json_bytes(semantic).decode()
    binding = PlatformWorkerHost._context_binding(SimpleNamespace(
        text=text, snapshot_id="snapshot-1", input_digest=sha256(text.encode()).hexdigest(),
        read_set=(), record_refs=(),
    ))

    assert binding["schema_version"] == "wuji.work-brief.v1"
    assert binding["brief_digest"] == sha256(
        canonical_json_bytes(semantic["brief"])
    ).hexdigest()
    assert binding["knowledge_index_digest"] == sha256(b"[]").hexdigest()
    assert binding["initial_deliveries_digest"] == sha256(b"[]").hexdigest()
    assert "relations_digest" not in binding


def _tool_stream(ordinal, name, arguments):
    return _sse(
        {
            "id": f"chatcmpl-problem-{ordinal}", "object": "chat.completion.chunk",
            "created": ordinal, "model": "fixture",
            "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{
                "index": 0, "id": f"call-problem-{ordinal}", "type": "function",
                "function": {"name": name, "arguments": arguments},
            }]}, "finish_reason": None}],
        },
        {
            "id": f"chatcmpl-problem-{ordinal}", "object": "chat.completion.chunk",
            "created": ordinal, "model": "fixture",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _final_stream():
    payload = {
        "schema_version": "wuji.agent-payload.v3",
        "claims": [], "intent_proposals": [], "reason_decision": None,
        "work_result": {
            "outcome": "answered", "summary": "The fixed material answered the problem.",
            "answer_basis_refs": [{"entity_type": "claim", "id": "claim-1", "revision": "1"}],
            "unresolved_items": [], "capability_gaps": [],
        },
        "input_acknowledgements": [],
    }
    return _sse(
        {
            "id": "chatcmpl-problem-final", "object": "chat.completion.chunk",
            "created": 4, "model": "fixture",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": canonical_json_bytes(payload).decode()}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-problem-final", "object": "chat.completion.chunk",
            "created": 4, "model": "fixture",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _profile():
    from pathlib import Path

    lock = sha256((Path(__file__).resolve().parents[2] / "packages/maf-worker/uv.lock").read_bytes()).hexdigest()
    function_limits = {
        "session_state_per_work": 16, "knowledge_read_per_work": 8,
        "environment_action_per_work": 0, "total_per_work": 24,
        "total_per_task": 24,
    }
    manifest = build_capability_manifest(
        environment_tools=(), include_todo=True, include_memory=True,
        include_knowledge=True, session_limit=16, knowledge_limit=8,
        environment_limit=0,
    )
    body = {
        "ref": "harness.explore.problem.test", "revision": "1", "work_kind": "explore",
        "instructions": "Solve the fixed problem and return AgentPayloadV3.",
        "tool_definition_refs": [], "material_representation": "wuji.model-material.v2",
        "lock_digest": lock, "max_context_records": 64, "max_context_bytes": 65536,
        "max_output_tokens": 4096,
        "capabilities": {"todo": True, "mode": False, "file_memory": True,
            "file_access": False, "skills": False, "shell": False,
            "web_search": False, "background_agents": False, "outer_loop": False,
            "auto_approval": False, "compaction": True, "restoration": True,
            "mcp": False, "native_approval": True, "versioned_memory": True},
        "schema_version": "wuji.harness.problem.v1",
        "history_source_id": "history", "memory_mode": "work_memory",
        "memory_source_id": "problem_memory",
        "session_limits": {"max_objects": 32, "max_reference_depth": 8,
            "max_object_bytes": 65536, "max_total_bytes": 262144,
            "max_messages": 128, "max_pending_approvals": 4},
        "max_context_window_tokens": 65536, "compaction_enabled": True,
        "context_policy": {"policy_revision": "1", "initial_brief_bytes": 16384,
            "index_limit": 64, "default_read_bytes": 8192, "max_read_bytes": 16384,
            "max_delivered_bytes": 32768, "max_refreshes": 2,
            "renderer_version": "wuji-http-renderer.v2", "redaction_policy_ref": "wuji-redaction.v1"},
        "capability_manifest": manifest,
        "planning_policy": {"policy_revision": "1", "reason_proposal_limit": 3,
            "explore_proposal_limit": 2, "coalesce_milliseconds": 500,
            "max_delay_milliseconds": 5000, "no_progress_rounds": 3},
        "work_memory_policy": {"store": "agent_file_store", "max_files": 8,
            "max_file_bytes": 8192, "max_total_bytes": 32768,
            "path_pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"},
        "function_limits": function_limits, "tool_choice_policy": "auto",
        "completion_mode": "review_then_close",
    }
    snapshot = {"ref": body["ref"], "revision": "1", "body": body,
                "digest": sha256(canonical_json_bytes(body)).hexdigest()}
    return ProblemHarnessProfile.from_snapshot(snapshot), snapshot


def test_problem_checkpoint_persists_the_current_tool_result_group():
    profile, snapshot = _profile()
    compatibility = SessionCompatibility.model_validate({
        "profile_snapshot": snapshot, "client_snapshot": {}, "runtime_snapshot": {},
        "framework_snapshot": {"agent_framework_core": "1.18.0"},
        "lock_digest": profile.lock_digest, "capability_ref": "problem-test",
        "capability_digest": "a" * 64, "validation_status": "verified",
    })
    history = HistoryArchive(
        compatibility=compatibility,
        limits=SessionLimits.model_validate(profile.session_limits),
    )
    history.bind_context(
        session_id="session-1", session_lineage="lineage-1",
        assignment=SimpleNamespace(identity=SimpleNamespace(work_item_id="work-1")),
        context=SimpleNamespace(snapshot_id="snapshot-1", read_set=()),
    )
    history.model_identity = SimpleNamespace(attempt_id="attempt-1")
    session = AgentSession(session_id="session-1")
    call = Message(role="assistant", contents=[Content.from_function_call(
        "provider-call-1", "http_target_get", arguments={"url": "http://fixture.invalid"},
        id="native-call-1",
    )])
    provider_context = Message(
        role="user", contents=[Content.from_text("provider-only context")],
        additional_properties={"_context_source": "problem_todo"},
    )
    result = Message(role="tool", contents=[Content.from_function_result(
        "provider-call-1", result="fixed result",
    )])

    async def settle():
        state = session.state.setdefault(history.source_id, {})
        await history.save_messages(session.session_id, [call], state=state)
        return await _settled_boundary(
            history, session, [call, provider_context, result]
        )

    boundary_session, stored = asyncio.run(settle())

    assert [item.to_dict() for item in stored] == [call.to_dict(), result.to_dict()]
    assert session.state[history.source_id]["messages"][-1].contents[0].type == "function_call"
    assert boundary_session.state[history.source_id]["messages"][-1].contents[0].type == "function_result"
    binding = NativeCallBinding(
        model_attempt_id="attempt-1", message_id="model-attempt:attempt-1:choice:0",
        provider_call_id="provider-call-1", sdk_content_id="native-call-1",
        tool_definition_ref="http-target-v1", native_arguments='{"url":"http://fixture.invalid"}',
        arguments_digest=sha256(b'{"url":"http://fixture.invalid"}').hexdigest(),
        tool_call_id="tool-call-1",
    )
    receipt = ToolCallReceipt.model_validate({
        "tool_call_id": "tool-call-1", "operation_id": "operation-1",
        "tool_attempt_id": "attempt-1", "status": "complete",
        "evidence_receipt": {
            "observation_ref": {"entity_type": "observation", "id": "observation-1", "revision": "1"},
            "capture_id": "capture-1", "status": "accepted", "artifact_refs": [{
                "id": "artifact-1", "version": "1", "sha256": "b" * 64,
            }], "request_id": "request-1", "code": None,
        },
        "result_ref": {"id": "artifact-1", "version": "1", "sha256": "b" * 64},
        "reason_code": None,
    })
    history.observe_messages(
        stored, model_attempt_id="attempt-1",
        call_bindings=(binding,), tool_receipts=(receipt,),
    )
    boundary = NativeSessionAdapter(
        compatibility=compatibility, limits=profile.session_limits,
    ).export_settled_boundary(
        session=boundary_session, messages=stored, history=history,
        call_bindings=(binding,), tool_receipts=(receipt,),
        memory=WorkMemoryStore(
            limits=profile.session_limits,
            policy=profile.work_memory_policy.model_dump(mode="python"),
        ),
        observed_at=datetime.now(timezone.utc),
    )
    assert len(boundary.history.frontier.tool_entries[0].positions) == 2


def test_problem_harness_uses_native_todo_memory_and_host_knowledge_in_one_session():
    profile, snapshot = _profile()

    async def run():
        limits = SessionLimits.model_validate(profile.session_limits)
        compatibility = SessionCompatibility.model_validate({
            "profile_snapshot": snapshot, "client_snapshot": {}, "runtime_snapshot": {},
            "framework_snapshot": {"python": "3.13.15", "agent_framework_core": "1.18.0", "agent_framework_openai": "1.14.3"},
            "lock_digest": profile.lock_digest, "capability_ref": "problem-test",
            "capability_digest": "a" * 64, "validation_status": "verified",
        })
        history = HistoryArchive(compatibility=compatibility, limits=limits)
        memory = WorkMemoryStore(limits=limits, policy=profile.work_memory_policy)
        memory_provider = BoundedWorkMemoryProvider(
            memory, source_id=profile.memory_source_id, scope="test-scope"
        )
        checkpoints = []

        async def checkpoint(session, messages):
            checkpoints.append(await _settled_boundary(history, session, messages))

        requests = []
        responses = [
            _tool_stream(1, "todos_add", '{"todos":[{"title":"read material"}]}'),
            _tool_stream(2, "file_memory_write", '{"file_name":"notes.md","content":"local note"}'),
            _tool_stream(3, "knowledge_read", '{"snapshot_id":"snapshot-1","ref":{"entity_type":"claim","id":"claim-1","revision":"1"},"selector":{"kind":"record_fields","fields":["text"]}}'),
            _tool_stream(4, "knowledge_read", '{"snapshot_id":"snapshot-1","ref":{"entity_type":"claim","id":"claim-1","revision":"1"},"selector":{"kind":"record_fields","fields":["text"]}}'),
            _final_stream(),
        ]

        async def model_handler(request):
            requests.append(strict_json_loads(request.content))
            ordinal = len(requests)
            return httpx.Response(
                200, content=responses[ordinal - 1], request=request,
                headers={"content-type": "text/event-stream", "X-Wuji-Model-Attempt-ID": f"attempt-{ordinal}"},
            )

        class Host:
            def __init__(self):
                self.reads = 0

            def knowledge_read(self, _assignment, **kwargs):
                assert kwargs["native_occurrence"]
                self.reads += 1
                if self.reads == 1:
                    error = HostTransportError("bounded knowledge refusal")
                    error.status_code = 422
                    error.code = "INVALID_REFERENCE"
                    raise error
                return wire.KnowledgeDeliveryV1.model_validate({
                    "schema_version": "wuji.knowledge-delivery.v1",
                    "delivery_id": "delivery-1", "kind": "knowledge_tool",
                    "snapshot_id": "snapshot-1", "ref": kwargs["ref"],
                    "source_digest": "b" * 64, "selector": kwargs["selector"],
                    "renderer_version": "wuji-record-renderer.v1",
                    "redaction_policy_ref": "wuji-redaction.v1", "text": '{"text":"evidence"}',
                    "representation_digest": sha256(b'{"text":"evidence"}').hexdigest(),
                    "byte_length": len(b'{"text":"evidence"}'), "source_completeness": "complete",
                    "representation_truncated": False, "has_more": False,
                    "disclosure": "content", "state": "prepared", "work_item_id": "work-1",
                    "agent_run_id": "run-1", "session_id": None,
                    "native_occurrence": kwargs["native_occurrence"],
                })

            def knowledge_list(self, *_args, **_kwargs):
                raise AssertionError("not selected")

            def knowledge_refresh(self, *_args, **_kwargs):
                raise AssertionError("not selected")

        identity = ModelCallIdentity(
            [], max_bytes=1_048_576,
            capability_manifest=[item.model_dump(mode="json") for item in profile.capability_manifest],
        )
        budget = FunctionBudget(profile.function_limits.model_dump(mode="python"))
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(model_handler),
            event_hooks={"request": [identity.request], "response": [identity.response]},
        ) as model_http, httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(500))) as tool_http:
            functions = GateFunctions(
                definitions=[], identity=identity, lineage="lineage", client=tool_http,
                url="https://tool.invalid/internal/v2/tool-calls", native_approval=True,
                material_representation="wuji.model-material.v2", budget=budget,
                host=Host(), assignment=object(),
            )
            agent, native = build_agent(
                resolved={"limits": {"max_model_requests": 8, "max_tool_calls": 0,
                    "max_elapsed_seconds": 60, "max_single_output_bytes": 1_048_576,
                    "max_total_output_bytes": 2_097_152}, "client_model": "fixture"},
                profile=profile, model_http=model_http,
                model_gate_url="https://model.invalid", run_credential="test-token",
                tools=functions.registered_knowledge_tools(), middleware=functions,
                response_parser=identity.parse_response, history=history,
                work_memory_provider=memory_provider, environment_tool_count=0,
                extra_middleware=(CheckpointBeforeModel(checkpoint),),
            )
            session = agent.create_session()
            budget.bind(session)
            stream = agent.run("fixed problem", session=session, stream=True)
            async for _update in stream:
                pass
            final = await stream.get_final_response()
            await native.close()
        assert wire.AgentPayloadV3.model_validate_json(final.messages[-1].text)
        assert session.state["problem_todo"]["items"][0]["title"] == "read material"
        assert any(body.decode() == "local note" for body in memory.snapshot_files().values())
        assert functions.knowledge_deliveries[0]["delivery_id"] == "delivery-1"
        assert len(identity.local_mapping) == 4
        assert all(request.get("tool_choice", "auto") != "required" for request in requests)
        assert all(request["messages"][0]["content"] == profile.instructions for request in requests)
        assert all(
            "### Current todo list" not in message.get("content", "")
            for request in requests for message in request["messages"]
        )
        assert len(checkpoints) == len(requests) - 1
        for request in requests:
            result_ids = [
                message["tool_call_id"] for message in request["messages"]
                if message["role"] == "tool"
            ]
            assert len(result_ids) == len(set(result_ids))

    asyncio.run(run())
