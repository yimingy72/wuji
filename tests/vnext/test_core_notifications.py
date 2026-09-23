import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from agent_framework import (
    AgentSession,
    FileMemoryProvider,
    InMemoryHistoryProvider,
    SessionContext,
)

from wuji_core.admission import registry as registry_module
from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.contracts.sessions import SessionLimits
from wuji_core.blackboard.knowledge_reads import KnowledgeReadService
from wuji_core.blackboard.notifications import (
    BoardPublishService,
    KnowledgeNoticeService,
)
from wuji_core.execution.control import ExecutionObservation
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotQuery
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.notifications import KnowledgeNoticeProvider
from wuji_maf_worker.factory import build_agent
from wuji_maf_worker.history import WorkMemoryStore
from wuji_maf_worker.tools import FunctionBudget, GateFunctions, ModelCallIdentity
from support.p06 import ENVIRONMENT, OWNER, TASK
from support.p09 import (
    POD_UID,
    TOOL_REF,
    _publish_intent,
    scheduler_case,
    worker_credential,
)
from support.core_ctf import catalog as core_ctf_catalog
from support.core_ctf import component_registrar, profile_factory
from test_problem_maf import _final_stream, _profile, _tool_stream


def _assignment():
    return WorkerAssignment.model_validate(
        {
            "schema_version": "wuji.assignment.v2",
            "operation_id": "notice-operation",
            "identity": {
                "tenant_id": "tenant-notice",
                "project_id": "project-notice",
                "task_id": "task-notice",
                "work_item_id": "work-notice",
                "agent_run_id": "run-notice",
                "execution_epoch": "1",
                "run_epoch": "1",
                "runtime_attempt": "1",
                "receiver_id": "receiver-notice",
            },
            "work_kind": "explore",
            "snapshot_id": "snapshot-initial",
            "profile_refs": ["profile-notice"],
            "session_manifest_ref": None,
            "tool_definition_refs": [],
            "limits": {
                "max_work_items": 8,
                "max_reason_runs": 4,
                "max_model_requests": 16,
                "max_tool_calls": 8,
                "max_single_output_bytes": 1048576,
                "max_total_output_bytes": 2097152,
                "max_elapsed_seconds": 300,
                "max_attempts_per_work": 2,
                "repair_attempts": 0,
            },
            "resume_reason": None,
        }
    )


class Host:
    def __init__(self):
        self.cursors = []

    def knowledge_notices(self, _assignment, *, cursor, limit):
        self.cursors.append((cursor, limit))
        return {
            "schema_version": "wuji.knowledge-notices.v1",
            "next_cursor": "notice:7:0123456789abcdef01234567",
            "notices": [
                {
                    "category": "claim_published",
                    "ref": {
                        "entity_type": "claim",
                        "id": "claim-notice",
                        "revision": "1",
                    },
                    "snapshot_id": "snapshot-notice",
                    "source_work_ref": "work-source",
                    "metadata": {
                        "claim_kind": "observation-summary",
                        "assertion_role": "candidate_fact",
                        "effective_outcome": None,
                        "publication_id": None,
                        "asset_id": None,
                        "asset_revision": None,
                    },
                }
            ],
        }


def test_notice_cursor_advances_only_after_stream_result_and_state_restores():
    host = Host()
    provider = KnowledgeNoticeProvider(host=host, assignment=_assignment())
    session = AgentSession(session_id="session-notice")
    session_context = SessionContext(session_id=session.session_id, input_messages=[])
    asyncio.run(
        provider.before_run(
            agent=object(),
            session=session,
            context=session_context,
            state=session.state.setdefault(provider.source_id, {}),
        )
    )
    middleware = session_context.get_middleware()[0]
    chat = SimpleNamespace(
        stream=True,
        messages=[],
        stream_result_hooks=[],
    )

    async def next_call():
        return None

    asyncio.run(middleware.process(chat, next_call))
    state = session.state[provider.source_id]
    assert state == {}
    assert host.cursors == [(None, 16)]
    notice = strict_json_loads(chat.messages[0].text)
    assert notice["notices"][0]["ref"]["id"] == "claim-notice"
    assert "next_cursor" not in notice and "text" not in notice["notices"][0]

    response = object()
    assert asyncio.run(chat.stream_result_hooks[0](response)) is response
    assert state["cursor"] == "notice:7:0123456789abcdef01234567"
    restored = AgentSession.from_dict(session.to_dict())
    assert restored.state[provider.source_id] == state


def test_failed_stream_does_not_advance_notice_cursor():
    host = Host()
    state = {"cursor": "notice:4:aaaaaaaaaaaaaaaaaaaaaaaa"}
    provider = KnowledgeNoticeProvider(host=host, assignment=_assignment())
    session = AgentSession(session_id="session-notice-failure")
    session.state[provider.source_id] = state
    session_context = SessionContext(session_id=session.session_id, input_messages=[])
    asyncio.run(
        provider.before_run(
            agent=object(),
            session=session,
            context=session_context,
            state=state,
        )
    )
    middleware = session_context.get_middleware()[0]
    chat = SimpleNamespace(stream=True, messages=[], stream_result_hooks=[])

    async def fail():
        raise RuntimeError("synthetic stream failure")

    with pytest.raises(RuntimeError, match="synthetic stream failure"):
        asyncio.run(middleware.process(chat, fail))
    assert state == {"cursor": "notice:4:aaaaaaaaaaaaaaaaaaaaaaaa"}


def test_native_agent_polls_each_model_call_and_reads_notice_content_explicitly():
    profile, _snapshot = _profile(native=True)

    async def run():
        requests = []
        responses = [
            _tool_stream(
                1,
                "knowledge_list",
                '{"snapshot_id":"snapshot-initial","material_types":[],"cursor":null,"limit":10}',
            ),
            _tool_stream(
                2,
                "knowledge_read",
                '{"snapshot_id":"snapshot-live","ref":{"entity_type":"claim","id":"claim-live","revision":"1"},"selector":{"kind":"record_fields","fields":["text"]}}',
            ),
            _final_stream(),
        ]

        async def model_handler(request):
            requests.append(strict_json_loads(request.content))
            ordinal = len(requests)
            return httpx.Response(
                200,
                content=responses[ordinal - 1],
                request=request,
                headers={
                    "content-type": "text/event-stream",
                    "X-Wuji-Model-Attempt-ID": f"notice-attempt-{ordinal}",
                },
            )

        class LiveHost:
            def __init__(self):
                self.published = False
                self.read = False
                self.cursors = []

            def knowledge_notices(self, _assignment, *, cursor, limit):
                self.cursors.append((cursor, limit))
                notices = []
                if self.published and not self.read:
                    notices.append(
                        {
                            "category": "claim_published",
                            "ref": {
                                "entity_type": "claim",
                                "id": "claim-live",
                                "revision": "1",
                            },
                            "snapshot_id": "snapshot-live",
                            "source_work_ref": "other-work",
                            "metadata": {
                                "claim_kind": "observation-summary",
                                "assertion_role": "candidate_fact",
                                "effective_outcome": None,
                                "publication_id": None,
                                "asset_id": None,
                                "asset_revision": None,
                            },
                        }
                    )
                return {
                    "schema_version": "wuji.knowledge-notices.v1",
                    "next_cursor": (
                        "notice:2:bbbbbbbbbbbbbbbbbbbbbbbb"
                        if self.published
                        else "notice:1:aaaaaaaaaaaaaaaaaaaaaaaa"
                    ),
                    "notices": notices,
                }

            def knowledge_list(self, _assignment, **kwargs):
                assert kwargs["native_occurrence"]
                self.published = True
                return wire.KnowledgeListPageV1.model_validate(
                    {
                        "schema_version": "wuji.knowledge-index.v1",
                        "snapshot_id": kwargs["snapshot_id"],
                        "items": [],
                        "cursor": None,
                    }
                )

            def knowledge_read(self, _assignment, **kwargs):
                assert kwargs["ref"]["id"] == "claim-live"
                self.read = True
                text = '{"text":"explicitly read live evidence"}'
                return wire.KnowledgeDeliveryV1.model_validate(
                    {
                        "schema_version": "wuji.knowledge-delivery.v1",
                        "delivery_id": "delivery-live",
                        "kind": "knowledge_tool",
                        "snapshot_id": kwargs["snapshot_id"],
                        "ref": kwargs["ref"],
                        "source_digest": "b" * 64,
                        "selector": kwargs["selector"],
                        "renderer_version": "wuji-record-renderer.v1",
                        "redaction_policy_ref": "wuji-redaction.v1",
                        "text": text,
                        "representation_digest": sha256(text.encode()).hexdigest(),
                        "byte_length": len(text.encode()),
                        "source_completeness": "complete",
                        "representation_truncated": False,
                        "has_more": False,
                        "disclosure": "content",
                        "state": "prepared",
                        "work_item_id": "work-notice",
                        "agent_run_id": "run-notice",
                        "session_id": None,
                        "native_occurrence": kwargs["native_occurrence"],
                    }
                )

            def knowledge_refresh(self, *_args, **_kwargs):
                raise AssertionError("not selected")

        host = LiveHost()
        history = InMemoryHistoryProvider(source_id=profile.history_source_id)
        memory = WorkMemoryStore(
            limits=SessionLimits.model_validate(profile.session_limits),
            policy=profile.work_memory_policy,
        )
        memory_provider = FileMemoryProvider(
            memory, source_id=profile.memory_source_id, scope="notice-test"
        )
        identity = ModelCallIdentity(
            [],
            max_bytes=1_048_576,
            capability_manifest=[
                item.model_dump(mode="json")
                for item in profile.capability_manifest
                if item.name != "board_publish"
            ],
        )
        budget = FunctionBudget(profile.function_limits.model_dump(mode="python"))
        provider = KnowledgeNoticeProvider(host=host, assignment=_assignment())
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(model_handler),
            event_hooks={
                "request": [identity.request],
                "response": [identity.response],
            },
        ) as model_http, httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: httpx.Response(500))
        ) as tool_http:
            functions = GateFunctions(
                definitions=[],
                identity=identity,
                lineage="notice-lineage",
                client=tool_http,
                url="https://tool.invalid/internal/v2/tool-calls",
                native_approval=True,
                material_representation="wuji.model-material.v2",
                budget=budget,
                host=host,
                assignment=_assignment(),
            )
            agent, native = build_agent(
                resolved={
                    "limits": {
                        "max_model_requests": 8,
                        "max_tool_calls": 0,
                        "max_elapsed_seconds": 60,
                        "max_single_output_bytes": 1_048_576,
                        "max_total_output_bytes": 2_097_152,
                    },
                    "client_model": "fixture",
                },
                profile=profile,
                model_http=model_http,
                model_gate_url="https://model.invalid",
                run_credential="test-token",
                tools=functions.registered_knowledge_tools(),
                middleware=functions,
                response_parser=identity.parse_response,
                history=history,
                work_memory_provider=memory_provider,
                notification_provider=provider,
                environment_tool_count=0,
            )
            session = agent.create_session()
            budget.bind(session)
            stream = agent.run("fixed problem", session=session, stream=True)
            async for _update in stream:
                pass
            await stream.get_final_response()
            await native.close()

        rendered = [canonical_json_bytes(request).decode() for request in requests]
        assert len(rendered) == 3
        assert "claim-live" not in rendered[0]
        assert "claim-live" in rendered[1]
        assert "explicitly read live evidence" not in rendered[1]
        assert "explicitly read live evidence" in rendered[2]
        assert host.cursors == [
            (None, 16),
            ("notice:1:aaaaaaaaaaaaaaaaaaaaaaaa", 16),
            ("notice:2:bbbbbbbbbbbbbbbbbbbbbbbb", 16),
        ]
        assert session.state[provider.source_id]["cursor"] == (
            "notice:2:bbbbbbbbbbbbbbbbbbbbbbbb"
        )

    asyncio.run(run())


def test_required_only_snapshot_query_is_explicit_and_bounded():
    query = SnapshotQuery(
        entity_types=(), required_refs=(("claim", "claim-notice", "1"),)
    )
    assert query.payload() == {
        "entity_types": [],
        "max_references": 1000,
        "required_refs": [["claim", "claim-notice", "1"]],
    }
    with pytest.raises(ValueError, match="invalid bounded snapshot query"):
        SnapshotQuery(entity_types=(), required_refs=())


def _problem_profiles(_case):
    _, snapshot = _profile(native=True)
    profiles = {}
    for kind in ("explore", "reason", "report"):
        body = {
            **snapshot["body"],
            "ref": f"harness.{kind}.notice.test",
            "work_kind": kind,
            "instructions": f"Use the fixed {kind} notice fixture.",
            "tool_definition_refs": [TOOL_REF] if kind == "explore" else [],
            "capabilities": {
                **snapshot["body"]["capabilities"],
                "todo": kind == "explore",
            },
        }
        profiles[kind] = {
            "ref": body["ref"],
            "revision": body["revision"],
            "digest": sha256(canonical_json_bytes(body)).hexdigest(),
            "body": body,
        }
    return profiles


def _register_problem_capabilities(case, environment):
    config = case.control.scheduler_config
    client = registry_module.session_client_snapshot(config)
    runtime = config.runtime.model_dump(mode="json")
    framework = {
        "python": "3.13.15",
        "agent_framework_core": "1.18.0",
        "agent_framework_openai": "1.14.3",
    }
    with environment.migration_connection() as connection:
        for profile in case.profiles.values():
            body = profile["body"]
            registry_module.register_session_capability(
                connection,
                tenant_id=OWNER[0],
                capability={
                    "ref": registry_module.verified_session_capability_ref(
                        profile["digest"]
                    ),
                    "revision": "1",
                    "published_at": datetime.now(timezone.utc),
                    "validation_status": "verified",
                    "profile_snapshot": profile,
                    "profile_digest": profile["digest"],
                    "client_snapshot": client,
                    "client_digest": registry_module.configuration_digest(client),
                    "runtime_snapshot": runtime,
                    "runtime_digest": registry_module.configuration_digest(runtime),
                    "framework_snapshot": framework,
                    "framework_digest": registry_module.configuration_digest(
                        framework
                    ),
                    "lock_digest": body["lock_digest"],
                    "limits": body["session_limits"],
                    "recovery_classes": [
                        "settled_boundary",
                        "approval_boundary",
                    ],
                    "memory_mode": body["memory_mode"],
                    "approver_subjects": ["operator-fixture"],
                    "approval_ttl_seconds": 300,
                    "evidence_refs": ["tests/vnext/test_core_notifications.py"],
                },
            )


def _start(case, assignment, suffix):
    now = datetime.now(timezone.utc)
    body = {
        "receipt_id": str(uuid4()),
        "identity": assignment.identity.model_dump(mode="json"),
        "operation_id": assignment.operation_id,
        "environment_ref": ENVIRONMENT,
        "pod_uid": POD_UID,
        "kind": "started",
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "process": {
            "pid": 7000 + suffix,
            "birth_id": f"notice-birth-{suffix}",
            "started_at": (now - timedelta(seconds=1))
            .isoformat()
            .replace("+00:00", "Z"),
            "exited_at": None,
            "exit_code": None,
        },
        "reason": "bounded notification fixture process",
    }
    source = canonical_json_bytes(body).decode()
    case.control.control.record_observation(
        case.receiver_access,
        ExecutionObservation.model_validate(
            {
                **body,
                "source_receipt": source,
                "source_digest": sha256(source.encode()).hexdigest(),
            }
        ),
    )


def test_board_publish_is_atomic_idempotent_and_other_run_reads_notice_content(
    db_environment, tmp_path, audit_directory
):
    core = core_ctf_catalog(explore_limit=3, pool_capacity=4)
    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_work_items=8,
        capacity=4,
        max_single_output_bytes=65_536,
        max_total_output_bytes=262_144,
        profiles=profile_factory(core),
        task_run_limits={"explore": 3, "reason": 1},
        explore_concurrency=3,
        component_registrar=component_registrar(core),
        admission_config=core["admission"],
        seed_intent=False,
    ) as case:
        _register_problem_capabilities(case, db_environment)
        with db_environment.migration_connection() as connection:
            connection.execute(
                """UPDATE vnext.scheduler_state
                SET pending_since=clock_timestamp()-interval '1 second'
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                OWNER,
            )
        reason_receipt = case.scheduler.tick(limit=1)
        reason = next(
            item
            for item in reason_receipt.assignments
            if item.work_kind.value == "reason"
        )
        _start(case, reason, 2)
        _artifact_ref, claim_ref, _intent_ref = _publish_intent(
            case.control, access_level=1, start=False
        )
        explore = next(
            item
            for item in case.scheduler.tick(limit=1).assignments
            if item.work_kind.value == "explore"
        )
        _start(case, explore, 1)
        explore_worker = worker_credential(case, explore)
        reason_worker = worker_credential(case, reason)
        notices = KnowledgeNoticeService(case.control.uow, registry=case.registry)
        initial_notices = notices.list(
            reason_worker.access, reason, cursor=None, limit=16
        )
        assert len(initial_notices.notices) == 1
        reads = KnowledgeReadService(
            case.control.uow,
            ledger=case.control.view,
            artifacts=case.control.store,
        )
        basis = reads.read(
            explore_worker.access,
            explore,
            snapshot_id=explore.snapshot_id,
            ref=claim_ref,
            selector={
                "kind": "record_fields",
                "fields": [
                    "text",
                    "basis_refs",
                    "limitations",
                    "kind",
                    "assertion_role",
                ],
            },
            native_occurrence="notice-basis-read",
        )
        reads.attach(
            explore_worker.access,
            explore,
            deliveries=[
                {
                    "delivery_id": basis.delivery_id,
                    "representation_digest": basis.representation_digest.root,
                }
            ],
            channel="function_result",
        )
        publisher = BoardPublishService(
            case.control.uow, registry=case.registry, knowledge_reads=reads
        )
        claim = {
            "client_ref": "live-notice-claim",
            "kind": "observation-summary",
            "assertion_role": "candidate_fact",
            "text": "The delivered fixture evidence produced a live finding.",
            "structured_assertion": {"fixture": "live"},
            "basis_refs": [claim_ref.model_dump(mode="json")],
            "limitations": ["isolated fixture"],
        }
        with db_environment.migration_connection() as connection:
            event_seq = int(
                connection.execute(
                    "SELECT event_seq FROM vnext.task WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s",
                    OWNER,
                ).fetchone()[0]
            )
            connection.execute(
                """INSERT INTO vnext.outbox(tenant_id,project_id,task_id,
                event_seq,kind,payload_json,access_level)
                SELECT %s,%s,%s,%s+value,'capture.item_ingested','{}',0
                FROM generate_series(1,300) AS value""",
                (*OWNER, event_seq),
            )
            connection.execute(
                """UPDATE vnext.task SET event_seq=event_seq+300,
                board_revision=board_revision+300 WHERE tenant_id=%s
                AND project_id=%s AND task_id=%s""",
                OWNER,
            )
        published = publisher.publish(
            explore_worker.access,
            explore,
            native_occurrence="board-publish-live-1",
            claim=claim,
        )
        replay = publisher.publish(
            explore_worker.access,
            explore,
            native_occurrence="board-publish-live-1",
            claim=claim,
        )
        assert replay == published
        assert published.delivery.state.value == "prepared"
        with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
            publisher.publish(
                explore_worker.access,
                explore,
                native_occurrence="board-publish-live-1",
                claim={**claim, "text": "Changed replay payload."},
            )
        reads.attach(
            explore_worker.access,
            explore,
            deliveries=[
                {
                    "delivery_id": published.delivery.delivery_id,
                    "representation_digest": published.delivery.representation_digest.root,
                }
            ],
            channel="function_result",
        )
        page = notices.list(
            reason_worker.access,
            reason,
            cursor=initial_notices.next_cursor,
            limit=16,
        )
        assert len(page.notices) == 1
        notice = page.notices[0]
        assert notice.ref == published.receipt.canonical_ref
        assert notice.source_work_ref.root == explore.identity.work_item_id
        with case.control.uow.transaction(reason_worker.access, TASK) as tx:
            assert tx.connection.execute(
                "SELECT count(*) FROM vnext.knowledge_delivery WHERE task_id=%s "
                "AND work_item_id=%s AND delivery_json::jsonb#>>'{ref,id}'=%s",
                (TASK, reason.identity.work_item_id, notice.ref.id),
            ).fetchone() == (0,)
        content = reads.read(
            reason_worker.access,
            reason,
            snapshot_id=notice.snapshot_id,
            ref=notice.ref,
            selector={
                "kind": "record_fields",
                "fields": ["text", "basis_refs", "limitations", "kind"],
            },
            native_occurrence="notice-content-read",
        )
        assert "live finding" in content.text
        after = notices.list(
            reason_worker.access, reason, cursor=page.next_cursor, limit=16
        )
        assert after.notices == []
        with pytest.raises(DomainError):
            notices.list(
                reason_worker.access,
                reason.model_copy(
                    update={
                        "identity": reason.identity.model_copy(
                            update={"task_id": "another-task"}
                        )
                    }
                ),
                cursor=None,
                limit=16,
            )
