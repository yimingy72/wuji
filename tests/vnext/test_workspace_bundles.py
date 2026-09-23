import asyncio
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from agent_framework import MCPStreamableHTTPTool

from support.p03 import access
from support.p06 import ENVIRONMENT, OWNER, TASK
from support.core_ctf import catalog as core_ctf_catalog
from support.core_ctf import (
    PROCESS_REFS,
    WORKSPACE_REFS,
    component_registrar,
    profile_factory,
)
from support.p09 import (
    POD_UID,
    explore_assignment,
    scheduler_case,
    worker_credential,
)
from test_core_notifications import _register_problem_capabilities, _start
from test_core_process import _ProcessGate, _assignment
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.admission.tools import ToolAdmission
from wuji_core.blackboard.knowledge_reads import KnowledgeReadService
from wuji_core.blackboard.notifications import BoardPublishService
from wuji_core.contracts import generated as wire
from wuji_core.contracts.admission import ToolCallReceipt, ToolCallRequest
from wuji_core.evidence.workspace_bundles import (
    MATERIALIZE_SCHEMA,
    PUBLISH_SCHEMA,
    WorkspaceBundleService,
)
from wuji_core.evidence.observations import EvidenceService
from wuji_core.evidence.runtime_capture import RuntimeCaptureService
from wuji_core.evidence.workspace_transfer import WorkspaceTransferHandler
from wuji_core.execution.pod_runtime import TaskPodLease
from wuji_core.execution.worker_bridge import WorkerHostBridge
from wuji_core.execution.workspace_gate import WorkspaceToolGate
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.native_mcp import MCP_INVOCATION_META, create_native_mcp_app
from wuji_core.persistence.snapshots import SnapshotQuery
from wuji_core.persistence.uow import DomainError, UnitOfWork, json_text


PUBLISH_REF = WORKSPACE_REFS["workspace_publish"]
MATERIALIZE_REF = WORKSPACE_REFS["workspace_materialize"]
IMAGE_DIGEST = "d" * 64
COMMAND_LOG_MEDIA_TYPE = "application/vnd.wuji.command-log+json"


class _LocalTransfer:
    def __init__(self, handler):
        self.handler = handler

    @staticmethod
    def _permit(permit):
        return SimpleNamespace(work_item_id=permit.identity.work_item_id)

    async def export(self, permit, request):
        return self.handler.export(self._permit(permit), request)

    async def import_publication(self, permit, request):
        return self.handler.import_publication(self._permit(permit), request)


def _request(credential, ref, arguments, suffix):
    return ToolCallRequest.model_validate(
        {
            "session_lineage": credential.binding.session_lineage,
            "message_id": "workspace-message-" + suffix,
            "provider_call_id": "workspace-call-" + suffix,
            "tool_definition_ref": ref,
            "arguments": arguments,
            "sdk_content_id": "workspace-occurrence-" + suffix,
            "sdk_approval_id": None,
            "approval_ref": None,
        }
    )


def _publish_arguments(*, expected=None):
    return {
        "purpose": "Parse the fixed fixture input.",
        "files": [{"relative_path": "src/solve.py"}],
        "entrypoint": {
            "relative_path": "src/solve.py",
            "interpreter_argv": ["/usr/bin/python3"],
        },
        "inputs_description": "One fixed fixture input.",
        "outputs_description": "A deterministic JSON answer.",
        "dependencies": [],
        "validation_statement": "The author ran the script on the fixture.",
        "limitations": ["isolated fixture"],
        "expected_base_publication_id": expected,
    }


def _capture_status(assignment):
    payload = {
        "schema_version": "wuji.runtime-capture-status.v1",
        "binding": {
            "task_id": TASK,
            "runtime_attempt": assignment.identity.runtime_attempt.root,
            "execution_epoch": assignment.identity.execution_epoch.root,
            "pod_uid": POD_UID,
        },
        "collector_ref": "collector-fixture",
        "environment_ref": ENVIRONMENT,
        "evidence_origin": "fixture_capture",
        "capture_layer": "runtime_capture",
        "state": "ready",
        "started_at": "2026-09-23T00:00:00Z",
        "status_digest": "0" * 64,
    }
    status = wire.RuntimeCaptureStatusV1.model_validate(payload)
    return status.model_copy(
        update={
            "status_digest": wire.Sha256Digest.model_validate(
                sha256(
                    canonical_json_bytes(
                        status.model_dump(mode="json", exclude={"status_digest"})
                    )
                ).hexdigest()
            )
        }
    )


def _register_capture_session(case, environment, assignment):
    with environment.migration_connection() as connection:
        connection.execute(
            """UPDATE vnext.task_access SET can_control=true,can_admit=true
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND subject='observer-fixture'""",
            OWNER,
        )
        connection.execute(
            """INSERT INTO vnext.task_pod_controller(
            tenant_id,project_id,task_id,controller_subject,login_role,enabled)
            VALUES(%s,%s,%s,'observer-fixture',%s,true)
            ON CONFLICT(tenant_id,project_id,task_id,controller_subject,login_role)
            DO UPDATE SET enabled=true""",
            (*OWNER, environment.application_role),
        )
    with environment.additional_app_connection() as connection:
        lease = TaskPodLease(
            connection, SimpleNamespace(tenant_id=OWNER[0], task_id=TASK)
        )
        lease.acquire()
        try:
            service = RuntimeCaptureService(
                UnitOfWork(lease.borrow), artifacts=case.control.store
            )
            return service.register_session(
                case.receiver_access, _capture_status(assignment)
            )
        finally:
            lease.close()


def _seed_bounded_capture_inventory(case, session):
    collector = access("collector-fixture", role="collector")
    start = datetime(2026, 9, 23, tzinfo=timezone.utc)
    empty_digest = sha256(b"").hexdigest()
    with case.control.uow.transaction(
        collector, TASK, capability="capture"
    ) as tx:
        for item_seq in range(1, 1002):
            kind = "pcap_segment" if item_seq <= 936 else "http_exchange"
            observed_at = start + timedelta(milliseconds=item_seq)
            observation_id = f"capacity-capture-{item_seq:04d}"
            tx.connection.execute(
                """INSERT INTO vnext.observation(tenant_id,project_id,task_id,
                entity_id,revision,capture_id,tool_attempt_id,capture_session_id,
                capture_item_seq,collector_ref,capture_layer,observed_at,received_at,
                environment_ref,conditions_json,completeness,evidence_origin,
                access_level) VALUES(%s,%s,%s,%s,1,%s,NULL,%s,%s,%s,%s,%s,%s,%s,
                '[]','complete','fixture_capture',1)""",
                (
                    *tx.owner,
                    observation_id,
                    f"{session.capture_session_id}:{item_seq}",
                    session.capture_session_id,
                    item_seq,
                    "collector-fixture",
                    "runtime_capture",
                    observed_at,
                    observed_at,
                    ENVIRONMENT,
                ),
            )
            artifact_id = None
            if kind == "http_exchange":
                artifact_id = f"capacity-http-{item_seq:04d}"
                tx.connection.execute(
                    """INSERT INTO vnext.artifact(tenant_id,project_id,task_id,
                    entity_id,revision,state,body_removed,storage_key,sha256,size_bytes,
                    media_type,tool_attempt_id,agent_run_id,writer_subject,
                    capture_session_id,provenance,evidence_origin,capture_layer,
                    environment_ref,completeness,conditions_json,access_level)
                    VALUES(%s,%s,%s,%s,1,'sealed',false,%s,%s,0,
                    'application/vnd.wuji.http-exchange+json',NULL,NULL,NULL,%s,
                    'capture','fixture_capture','runtime_capture',%s,'complete','[]',1)""",
                    (
                        *tx.owner,
                        artifact_id,
                        uuid4(),
                        empty_digest,
                        session.capture_session_id,
                        ENVIRONMENT,
                    ),
                )
                tx.connection.execute(
                    """INSERT INTO vnext.observation_artifact(tenant_id,project_id,
                    task_id,observation_id,observation_revision,ordinal,artifact_id,
                    artifact_revision,access_level) VALUES(%s,%s,%s,%s,1,0,%s,1,1)""",
                    (*tx.owner, observation_id, artifact_id),
                )
            item_digest = sha256(
                f"{session.capture_session_id}:{item_seq}:{kind}".encode()
            ).hexdigest()
            envelope = {
                "schema_version": "wuji.runtime-capture-envelope.v1",
                "capture_session_id": session.capture_session_id,
                "binding": session.binding.model_dump(mode="json"),
                "collector_ref": "collector-fixture",
                "item_seq": item_seq,
                "kind": kind,
                "completeness": "complete",
                "observed_at": observed_at.isoformat(),
                "parts": [
                    {
                        "part": "exchange" if artifact_id else "pcap",
                        "media_type": (
                            "application/vnd.wuji.http-exchange+json"
                            if artifact_id
                            else "application/vnd.tcpdump.pcap"
                        ),
                        "length": 0,
                        "sha256": empty_digest,
                    }
                ],
                "metadata": {},
                "conditions": [],
                "item_digest": item_digest,
            }
            tx.connection.execute(
                """INSERT INTO vnext.capture_item(tenant_id,project_id,task_id,
                capture_session_id,item_seq,kind,completeness,disposition,item_digest,
                envelope_json,observation_id,observation_revision,observed_at,
                access_level) VALUES(%s,%s,%s,%s,%s,%s,'complete','accepted',%s,%s,
                %s,1,%s,1)""",
                (
                    *tx.owner,
                    session.capture_session_id,
                    item_seq,
                    kind,
                    item_digest,
                    json_text(envelope),
                    observation_id,
                    observed_at,
                ),
            )
        assert tx.connection.execute(
            """SELECT ingested_items FROM vnext.capture_session WHERE
            tenant_id=%s AND project_id=%s AND task_id=%s
              AND capture_session_id=%s""",
            (*tx.owner, session.capture_session_id),
        ).fetchone() == (1001,)


def _record_command_log(case, assignment, worker):
    ledger = AdmissionLedger(case.control.uow)
    admission = ToolAdmission(case.control.uow, registry=case.registry, ledger=ledger)
    command = "printf context-command-log"
    permit = admission.authorize(
        worker.access,
        _request(
            worker,
            PROCESS_REFS["kali_exec"],
            {"command": command, "cwd": None, "timeout_seconds": 5.0},
            "context-command-log",
        ),
    )
    observed_at = datetime(2026, 9, 23, 0, 1, tzinfo=timezone.utc)
    with case.control.env.migration_connection() as connection:
        connection.execute(
            """UPDATE vnext.tool_attempt SET started_at=%s,status='dispatched'
            WHERE tenant_id=%s AND project_id=%s AND task_id=%s
              AND tool_attempt_id=%s""",
            (observed_at, *OWNER, permit.tool_attempt_id),
        )
    stdout = b"context-command-log\n"
    document = canonical_json_bytes(
        {
            "schema_version": "wuji.command-log.v1",
            "handle": permit.tool_attempt_id,
            "command": command,
            "command_sha256": sha256(command.encode()).hexdigest(),
            "cwd": None,
            "started_at": observed_at.isoformat(),
            "finished_at": observed_at.isoformat(),
            "exit_code": 0,
            "signal": None,
            "assurance": "executor_reported",
            "stdout_bytes": len(stdout),
            "stdout_sha256": sha256(stdout).hexdigest(),
            "stdout_base64": base64.b64encode(stdout).decode(),
            "stderr_bytes": 0,
            "stderr_sha256": sha256(b"").hexdigest(),
            "stderr_base64": "",
            "truncated": False,
        }
    )
    collector = access("collector-fixture", role="collector")
    artifact = case.control.store.stage(
        collector,
        TASK,
        permit.tool_attempt_id,
        document,
        COMMAND_LOG_MEDIA_TYPE,
        completeness="complete",
        conditions=("executor-reported command output",),
        provenance="import",
        access_level=1,
    )
    case.control.store.seal(collector, TASK, artifact)
    receipt = EvidenceService(case.control.uow, case.control.store).ingest(
        collector,
        wire.CaptureEnvelope.model_validate(
            {
                "schema_version": "wuji.capture.v2",
                "capture_id": permit.tool_attempt_id,
                "identity": assignment.identity.model_dump(mode="json"),
                "tool_call_id": permit.tool_call_id,
                "tool_attempt_id": permit.tool_attempt_id,
                "artifact_refs": [artifact.model_dump(mode="json")],
                "capture_layer": "executor_reported_command_output",
                "observed_at": observed_at,
                "received_at": observed_at,
                "evidence_origin": "imported_unverified",
                "conditions": ["executor-reported command output"],
                "completeness": "complete",
            }
        ),
    )
    return artifact, receipt.observation_ref


class _NativeWorkspaceGate(WorkspaceToolGate):
    def __init__(self):
        self.calls = []

    async def invoke(self, access, request, *, name, assignment):
        self.calls.append((access, request, name, assignment))
        return (
            wire.WorkspacePublishResultV1.model_validate(
                {
                    "schema_version": "wuji.workspace-publish-result.v1",
                    "status": "head_unavailable",
                    "publication_id": None,
                    "manifest_ref": None,
                    "asset_id": None,
                    "asset_revision": None,
                    "parent_publication_id": None,
                    "current_publication_id": None,
                    "delivery": None,
                }
            ),
            ToolCallReceipt.model_validate(
                {
                    "tool_call_id": "workspace-native-call",
                    "operation_id": "workspace-native-call",
                    "tool_attempt_id": "workspace-native-attempt",
                    "status": "complete",
                    "evidence_receipt": None,
                    "result_ref": None,
                    "reason_code": None,
                }
            ),
        )


def test_native_mcp_passes_the_frozen_assignment_to_workspace_gate(test_tokens):
    async def run():
        assignment = {**_assignment(), "tool_definition_refs": [PUBLISH_REF]}
        arguments = _publish_arguments()
        request = ToolCallRequest.model_validate(
            {
                "session_lineage": "lineage-workspace-native",
                "message_id": "message-workspace-native",
                "provider_call_id": "provider-workspace-native",
                "tool_definition_ref": PUBLISH_REF,
                "arguments": arguments,
                "sdk_content_id": "occurrence-workspace-native",
                "sdk_approval_id": None,
                "approval_ref": None,
            }
        )
        gate = _NativeWorkspaceGate()
        native = create_native_mcp_app(
            token_verifier=TokenVerifier(
                public_key_pem=test_tokens.public_key_pem,
                issuer=test_tokens.issuer,
                audience=test_tokens.audience,
            ),
            process_gate=_ProcessGate(),
            workspace_gate=gate,
        )
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=native.app),
            base_url="http://localhost:8000",
            headers={"Authorization": "Bearer " + test_tokens.agent},
        )
        tool = MCPStreamableHTTPTool(
            name="wuji-native-workspace",
            url="http://localhost:8000/internal/v2/mcp",
            allowed_tools=["workspace_publish"],
            load_tools=True,
            load_prompts=False,
            terminate_on_close=False,
            http_client=client,
        )
        metadata = {
            MCP_INVOCATION_META: {
                "assignment": assignment,
                "native_occurrence": "occurrence-workspace-native",
                "tool_request": request.model_dump(mode="json"),
            }
        }
        async with native.starlette.router.lifespan_context(native.starlette):
            async with client, tool:
                assert tool.functions[0].parameters() == PUBLISH_SCHEMA
                await tool.call_tool(
                    "workspace_publish", **arguments, _meta=metadata
                )
        assert len(gate.calls) == 1
        assert gate.calls[0][2] == "workspace_publish"
        assert gate.calls[0][3] == wire.WorkerAssignment.model_validate(assignment)

    asyncio.run(run())


def test_workspace_transfer_hashes_source_and_imports_an_independent_copy(tmp_path):
    workspace = tmp_path / "workspace"
    source = workspace / "work" / "work-a" / "src" / "solve.py"
    source.parent.mkdir(parents=True)
    source_bytes = b"print('sealed-source')\n"
    source.write_bytes(source_bytes)
    (workspace / "work" / "work-b").mkdir(parents=True)
    handler = WorkspaceTransferHandler(
        root=workspace,
        environment_ref=ENVIRONMENT,
        image_digest=IMAGE_DIGEST,
    )
    exported = handler.export(
        SimpleNamespace(work_item_id="work-a"),
        wire.WorkspaceExportRequestV1(
            files=[{"relative_path": "src/solve.py"}]
        ),
    )
    assert exported.files[0].sha256.root == sha256(source_bytes).hexdigest()
    imported = handler.import_publication(
        SimpleNamespace(work_item_id="work-b"),
        wire.WorkspaceImportRequestV1(
            publication_id="publication-copy",
            manifest_digest="e" * 64,
            files=[exported.files[0].model_dump(mode="json")],
        ),
    )
    destination = imported.files[0]
    assert destination.sha256.root == sha256(source_bytes).hexdigest()
    copied = workspace / destination.destination_path.removeprefix(str(workspace) + "/")
    assert copied.read_bytes() == source_bytes
    copied.write_bytes(b"modified import\n")
    assert source.read_bytes() == source_bytes


def test_workspace_bundle_a_to_b_fixed_version_materialize_and_cas(
    db_environment, tmp_path, audit_directory
):
    core = core_ctf_catalog(explore_limit=3, pool_capacity=6)
    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        max_work_items=12,
        max_single_output_bytes=65_536,
        max_total_output_bytes=2_097_152,
        capacity=6,
        explore_concurrency=3,
        task_run_limits={"explore": 3, "reason": 1},
        profiles=profile_factory(core),
        component_registrar=component_registrar(core),
        admission_config=core["admission"],
    ) as case:
        _register_problem_capabilities(case, db_environment)
        first = case.scheduler.tick(limit=4)
        assignment_a = explore_assignment(first)
        _start(case, assignment_a, 31)
        worker_a = worker_credential(case, assignment_a)

        workspace = tmp_path / "workspace"
        source_a = workspace / "work" / assignment_a.identity.work_item_id / "src"
        source_a.mkdir(parents=True)
        source_v1 = b"print('workspace-v1')\n"
        (source_a / "solve.py").write_bytes(source_v1)
        handler = WorkspaceTransferHandler(
            root=workspace,
            environment_ref=ENVIRONMENT,
            image_digest=IMAGE_DIGEST,
        )
        reads = KnowledgeReadService(
            case.control.uow,
            ledger=case.control.view,
            artifacts=case.control.store,
        )
        service = WorkspaceBundleService(
            case.control.uow,
            registry=case.registry,
            artifacts=case.control.store,
            knowledge_reads=reads,
            transfer=_LocalTransfer(handler),
        )
        ledger = AdmissionLedger(case.control.uow)
        admission = ToolAdmission(
            case.control.uow, registry=case.registry, ledger=ledger
        )
        gate = WorkspaceToolGate(
            SimpleNamespace(
                admission=admission,
                registry=case.registry,
                ledger=ledger,
            ),
            service,
        )

        publish_a = _request(
            worker_a, PUBLISH_REF, _publish_arguments(), "a-publish-v1"
        )
        published_v1, _receipt = asyncio.run(
            gate.invoke(
                worker_a.access,
                publish_a,
                name="workspace_publish",
                assignment=assignment_a,
            )
        )
        replayed_v1, _receipt = asyncio.run(
            gate.invoke(
                worker_a.access,
                publish_a,
                name="workspace_publish",
                assignment=assignment_a,
            )
        )
        assert replayed_v1 == published_v1
        assert published_v1.status.value == "published"
        assert published_v1.delivery.state.value == "prepared"
        reads.attach(
            worker_a.access,
            assignment_a,
            deliveries=[
                {
                    "delivery_id": published_v1.delivery.delivery_id,
                    "representation_digest": published_v1.delivery.representation_digest.root,
                }
            ],
            channel="function_result",
        )
        with db_environment.migration_connection() as connection:
            progress_before_model_output = connection.execute(
                "SELECT count(*) FROM vnext.scheduler_progress WHERE task_id=%s "
                "AND category='material'",
                (TASK,),
            ).fetchone()[0]

        publisher = BoardPublishService(
            case.control.uow, registry=case.registry, knowledge_reads=reads
        )
        claim = publisher.publish(
            worker_a.access,
            assignment_a,
            native_occurrence="workspace-claim-v1",
            claim={
                "client_ref": "workspace-claim-v1",
                "kind": "observation-summary",
                "assertion_role": "candidate_fact",
                "text": "The published script parses the fixed fixture input.",
                "structured_assertion": {"publication_id": published_v1.publication_id.root},
                "basis_refs": [
                    {
                        "entity_type": "artifact",
                        "id": published_v1.manifest_ref.id,
                        "revision": published_v1.manifest_ref.version.root,
                    }
                ],
                "limitations": ["author validation is not capture evidence"],
            },
        )
        reads.attach(
            worker_a.access,
            assignment_a,
            deliveries=[
                {
                    "delivery_id": claim.delivery.delivery_id,
                    "representation_digest": claim.delivery.representation_digest.root,
                }
            ],
            channel="function_result",
        )
        intent = case.control.claims.propose_intent(
            access("reader-fixture", role="human"),
            TASK,
            {
                "client_ref": "workspace-consumer-intent",
                "question": "Reuse the exact published script version.",
                "basis_refs": [claim.receipt.canonical_ref.model_dump(mode="json")],
                "expected_output": "A result from the fixed script version.",
            },
            idempotency_key="workspace-consumer-intent",
        )
        assert intent.canonical_ref is not None

        second = case.scheduler.tick(limit=6)
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.scheduler_progress WHERE task_id=%s "
                "AND category='material'",
                (TASK,),
            ).fetchone()[0] == progress_before_model_output
        assignment_b = next(
            item
            for item in second.assignments
            if item.work_kind.value == "explore"
            and item.identity.work_item_id != assignment_a.identity.work_item_id
        )
        _start(case, assignment_b, 32)
        worker_b = worker_credential(case, assignment_b)
        work_b = workspace / "work" / assignment_b.identity.work_item_id
        work_b.mkdir(parents=True)
        manifest_b = case.snapshots.get(TASK, worker_b.access, assignment_b.snapshot_id)
        assert any(
            ref.entity_type.value == "artifact"
            and ref.id == published_v1.manifest_ref.id
            and ref.revision.root == published_v1.manifest_ref.version.root
            for ref in manifest_b.refs
        )

        bridge = object.__new__(WorkerHostBridge)
        bridge.uow = case.control.uow
        bridge.registry = case.registry
        bridge.ledger = case.control.view
        bridge.artifacts = case.control.store
        bridge.knowledge_reads = reads
        records = bridge._problem_records(
            worker_b.access, assignment_b, manifest_b
        )
        context_b = bridge._problem_context(
            worker_b.access,
            assignment_b,
            manifest_b,
            records,
            case.profiles["explore"]["body"],
        )
        assert context_b.schema_version.root == "wuji.worker-context.v4"
        assert strict_json_loads(context_b.text)["snapshot_id"] == manifest_b.snapshot_id
        assert context_b.workspace_binding.runtime_attempt == assignment_b.identity.runtime_attempt
        assert [item.publication_id for item in context_b.published_asset_index] == [
            published_v1.publication_id.root
        ]

        materialize_b = _request(
            worker_b,
            MATERIALIZE_REF,
            {
                "publication_id": published_v1.publication_id.root,
                "manifest_ref": published_v1.manifest_ref.model_dump(mode="json"),
            },
            "b-materialize-v1",
        )
        materialized, _receipt = asyncio.run(
            gate.invoke(
                worker_b.access,
                materialize_b,
                name="workspace_materialize",
                assignment=assignment_b,
            )
        )
        imported = workspace / materialized.imports_root.removeprefix("/workspace/")
        imported_file = imported / "src" / "solve.py"
        assert imported_file.read_bytes() == source_v1

        source_v2 = b"print('workspace-v2')\n"
        imported_file.write_bytes(b"locally modified copy\n")
        source_b = work_b / "src"
        source_b.mkdir(exist_ok=True)
        (source_b / "solve.py").write_bytes(source_v2)
        publish_b = _request(
            worker_b,
            PUBLISH_REF,
            _publish_arguments(expected=published_v1.publication_id.root),
            "b-publish-v2",
        )
        published_v2, _receipt = asyncio.run(
            gate.invoke(
                worker_b.access,
                publish_b,
                name="workspace_publish",
                assignment=assignment_b,
            )
        )
        assert published_v2.asset_id == published_v1.asset_id
        assert published_v2.asset_revision.root == "2"
        assert published_v2.parent_publication_id.root == published_v1.publication_id.root

        stale = _request(
            worker_a,
            PUBLISH_REF,
            _publish_arguments(expected=published_v1.publication_id.root),
            "a-stale-publish",
        )
        conflict, _receipt = asyncio.run(
            gate.invoke(
                worker_a.access,
                stale,
                name="workspace_publish",
                assignment=assignment_a,
            )
        )
        assert conflict.status.value == "publication_conflict"
        assert conflict.current_publication_id.root == published_v2.publication_id.root

        with case.control.uow.transaction(worker_b.access, TASK) as tx:
            old_members = tx.connection.execute(
                "SELECT artifact_id,artifact_revision FROM vnext.publication_ref "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                "AND publication_id=%s ORDER BY artifact_id,artifact_revision",
                (*tx.owner, published_v1.publication_id.root),
            ).fetchall()
            manifest_record = case.control.store.record(tx, published_v1.manifest_ref)
        assert len(old_members) == 2
        assert sha256(case.control.store.checked_bytes(manifest_record)).hexdigest() == (
            published_v1.manifest_ref.sha256.root
        )
        assert source_v1 not in imported_file.read_bytes()

        with pytest.raises(DomainError, match="STALE_EXECUTION"):
            asyncio.run(
                service.materialize(
                    admission.authorize(
                        worker_b.access,
                        _request(
                            worker_b,
                            MATERIALIZE_REF,
                            {
                                "publication_id": published_v1.publication_id.root,
                                "manifest_ref": published_v1.manifest_ref.model_dump(mode="json"),
                            },
                            "b-wrong-assignment",
                        ),
                    ),
                    {
                        "publication_id": published_v1.publication_id.root,
                        "manifest_ref": published_v1.manifest_ref.model_dump(mode="json"),
                    },
                    assignment_b.model_copy(update={"snapshot_id": assignment_a.snapshot_id}),
                )
            )

def test_context_v4_bounds_large_capture_and_refreshes_command_and_workspace(
    db_environment, tmp_path, audit_directory
):
    core = core_ctf_catalog(explore_limit=3, pool_capacity=6)
    with scheduler_case(
        db_environment,
        tmp_path,
        audit_directory,
        capacity=6,
        explore_concurrency=3,
        task_run_limits={"explore": 3, "reason": 1},
        profiles=profile_factory(core),
        component_registrar=component_registrar(core),
        admission_config=core["admission"],
    ) as case:
        _register_problem_capabilities(case, db_environment)
        assignment = explore_assignment(case.scheduler.tick(limit=4))
        _start(case, assignment, 41)
        worker = worker_credential(case, assignment)
        reads = KnowledgeReadService(
            case.control.uow,
            ledger=case.control.view,
            artifacts=case.control.store,
        )
        query = SnapshotQuery(
            entity_types=("claim", "intent", "observation"),
            max_references=150,
            required_refs=((
                "artifact",
                case.artifact_ref.id,
                case.artifact_ref.version.root,
            ),),
            capture_http_limit=64,
        )
        baseline = case.snapshots.create(TASK, worker.access, query=query)

        workspace = tmp_path / "capacity-workspace"
        source = workspace / "work" / assignment.identity.work_item_id / "src"
        source.mkdir(parents=True)
        (source / "solve.py").write_bytes(b"print('bounded-context')\n")
        handler = WorkspaceTransferHandler(
            root=workspace,
            environment_ref=ENVIRONMENT,
            image_digest=IMAGE_DIGEST,
        )
        workspace_service = WorkspaceBundleService(
            case.control.uow,
            registry=case.registry,
            artifacts=case.control.store,
            knowledge_reads=reads,
            transfer=_LocalTransfer(handler),
        )
        ledger = AdmissionLedger(case.control.uow)
        admission = ToolAdmission(
            case.control.uow, registry=case.registry, ledger=ledger
        )
        workspace_gate = WorkspaceToolGate(
            SimpleNamespace(
                admission=admission,
                registry=case.registry,
                ledger=ledger,
            ),
            workspace_service,
        )
        published, _receipt = asyncio.run(
            workspace_gate.invoke(
                worker.access,
                _request(
                    worker,
                    PUBLISH_REF,
                    _publish_arguments(),
                    "context-workspace-publication",
                ),
                name="workspace_publish",
                assignment=assignment,
            )
        )
        assert published.status.value == "published"

        command_ref, command_observation = _record_command_log(
            case, assignment, worker
        )
        session = _register_capture_session(case, db_environment, assignment)
        _seed_bounded_capture_inventory(case, session)

        refreshed = reads.refresh(
            worker.access,
            assignment,
            snapshot_id=baseline.snapshot_id,
            native_occurrence="capacity-context-refresh",
        )
        fresh = case.snapshots.get(TASK, worker.access, refreshed.snapshot_id)
        assert fresh.query == query
        refs = {
            (ref.entity_type.value, ref.id, ref.revision.root)
            for ref in fresh.refs
        }
        assert (
            "artifact",
            case.artifact_ref.id,
            case.artifact_ref.version.root,
        ) in refs
        assert (
            case.claim_ref.entity_type.value,
            case.claim_ref.id,
            case.claim_ref.revision.root,
        ) in refs
        assert (
            case.intent_ref.entity_type.value,
            case.intent_ref.id,
            case.intent_ref.revision.root,
        ) in refs
        assert (
            command_observation.entity_type.value,
            command_observation.id,
            command_observation.revision.root,
        ) in refs
        assert (
            "artifact",
            command_ref.id,
            command_ref.version.root,
        ) in refs
        assert (
            "artifact",
            published.manifest_ref.id,
            published.manifest_ref.version.root,
        ) in refs
        assert ("observation", "capacity-capture-0937", "1") not in refs
        assert ("observation", "capacity-capture-0001", "1") not in refs
        for item_seq in range(938, 1002):
            assert ("observation", f"capacity-capture-{item_seq:04d}", "1") in refs
            assert ("artifact", f"capacity-http-{item_seq:04d}", "1") in refs

        inventory = fresh.states["capture_inventory"]
        assert inventory == {
            "capture_session_id": session.capture_session_id,
            "latest_item_seq": "1001",
            "included_http_observations": 64,
            "omitted_http_count": 1,
            "raw_inventory_omitted": True,
        }
        assert fresh.states["workspace_assets"] == {
            "included_latest_manifests": 1,
            "omitted_latest_manifests": 0,
        }
        command = reads.read(
            worker.access,
            assignment,
            snapshot_id=fresh.snapshot_id,
            ref={
                "entity_type": "artifact",
                "id": command_ref.id,
                "revision": command_ref.version.root,
            },
            selector={"kind": "text_range", "start": 0, "end": 16_384},
            native_occurrence="capacity-command-read",
        )
        assert "context-command-log" in command.text

        bridge = object.__new__(WorkerHostBridge)
        bridge.uow = case.control.uow
        bridge.registry = case.registry
        bridge.ledger = case.control.view
        bridge.artifacts = case.control.store
        bridge.knowledge_reads = reads
        index = bridge._published_asset_index(worker.access, assignment, fresh)
        assert [(item.publication_id, item.asset_revision.root) for item in index] == [
            (published.publication_id.root, "1")
        ]
