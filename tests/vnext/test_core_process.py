from __future__ import annotations

import asyncio
import base64
from contextlib import contextmanager
from hashlib import sha256
from importlib import util
from pathlib import Path
import sys
from threading import Event
import time
from types import SimpleNamespace

import httpx
import pytest
from agent_framework import Content, MCPStreamableHTTPTool
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from wuji_core.admission.remote_workspace import (
    ExecutorActionSigner,
    ExecutorActionVerifier,
    ExecutorDeploymentBinding,
    RemoteProcessExecutor,
)
from wuji_core.admission.ledger import AdmissionLedger
from wuji_core.admission import registry as registry_module
from wuji_core.admission.tools import ToolAdmission, ToolGate
from wuji_core.contracts import generated as wire
from wuji_core.contracts.admission import ToolCallReceipt, ToolCallRequest
from wuji_core.execution.process_gate import ProcessToolGate
from wuji_core.execution.process_supervisor import ProcessSupervisor
from wuji_core.execution.processes import PROCESS_TOOL_SCHEMAS
from wuji_core.evidence.observations import EvidenceService
from wuji_core.http import create_app
from wuji_core.http.auth import AuthenticationError, TokenVerifier
from wuji_core.http.native_mcp import MCP_INVOCATION_META, create_native_mcp_app
from wuji_core.http.process_executor import create_process_executor_router
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.tools import GateFunctions

from support.c0 import TestCertificateAuthority, TlsAsgiServer
from support.p03 import access
from support.p06 import (
    ENVIRONMENT,
    OWNER,
    RECEIVER,
    SESSION_LINEAGE,
    TASK,
    issue_run_credential,
    run_binding,
    task_admission_config,
)
from test_knowledge_admission import IDENTITY
from test_work_state_guards import control_case, observe, prepared_run, process


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _kali_factory():
    path = REPOSITORY_ROOT / "services" / "wuji-kali-executor" / "main.py"
    spec = util.spec_from_file_location("wuji_core_process_kali_service", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Kali executor service module is unavailable")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.create_kali_executor_app


def _supervisor(tmp_path: Path, *, max_output_bytes=256 * 1024):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return ProcessSupervisor(
        root=workspace,
        spool_root=tmp_path / "spool",
        max_active=4,
        max_output_bytes=max_output_bytes,
        stop_grace_seconds=0.25,
    )


def _wait_for_exit(supervisor, handle, *, timeout=5):
    cursor = {"stdout_offset": 0, "stderr_offset": 0}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        reply = supervisor.read(
            action_id="query-" + str(time.time_ns()),
            handle=handle,
            arguments_digest="query",
            cursor=cursor,
            max_bytes=65536,
            wait_ms=50,
            durable=False,
        )
        if reply.state.value == "exited" and not reply.has_more:
            return reply
        cursor = reply.next_cursor.model_dump(mode="json")
    raise AssertionError("process did not exit")


def test_process_supervisor_replays_exec_and_drains_long_output(tmp_path):
    supervisor = _supervisor(tmp_path)
    marker = tmp_path / "workspace" / "spawn-count"
    command = (
        "printf x >> spawn-count; "
        "python -c \"import sys; sys.stdout.write('a'*70000); "
        "sys.stderr.write('tail')\""
    )
    arguments_digest = sha256(command.encode()).hexdigest()
    first = supervisor.exec(
        action_id="attempt-exec",
        handle="attempt-exec",
        arguments_digest=arguments_digest,
        command=command,
        cwd=None,
        timeout_seconds=5,
    )
    replay = supervisor.exec(
        action_id="attempt-exec",
        handle="attempt-exec",
        arguments_digest=arguments_digest,
        command=command,
        cwd=None,
        timeout_seconds=5,
    )
    assert replay.handle == first.handle == "attempt-exec"
    _wait_for_exit(supervisor, "attempt-exec")

    stdout = bytearray()
    stderr = bytearray()
    cursor = {"stdout_offset": 0, "stderr_offset": 0}
    while True:
        reply = supervisor.read(
            action_id="query-" + str(time.time_ns()),
            handle="attempt-exec",
            arguments_digest="query",
            cursor=cursor,
            max_bytes=4096,
            durable=False,
        )
        for name, output in (("stdout", stdout), ("stderr", stderr)):
            chunk = getattr(reply, name)
            if chunk is not None:
                output.extend(base64.b64decode(chunk.data_base64, validate=True))
        cursor = reply.next_cursor.model_dump(mode="json")
        if not reply.has_more:
            break
    assert bytes(stdout) == b"a" * 70000
    assert bytes(stderr) == b"tail"
    assert marker.read_bytes() == b"x"


def test_process_supervisor_preserves_only_trusted_proxy_environment(
    tmp_path, monkeypatch
):
    trusted = {
        "HTTP_PROXY": "http://127.0.0.1:8080",
        "HTTPS_PROXY": "http://127.0.0.1:8080",
        "http_proxy": "http://127.0.0.1:8080",
        "https_proxy": "http://127.0.0.1:8080",
        "REQUESTS_CA_BUNDLE": "/run/wuji/capture-ca/ca-bundle.pem",
        "SSL_CERT_FILE": "/run/wuji/capture-ca/ca-bundle.pem",
        "CURL_CA_BUNDLE": "/run/wuji/capture-ca/ca-bundle.pem",
    }
    for name, value in trusted.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("PATH", "/trusted/bin")
    monkeypatch.setenv("UNTRUSTED_SECRET", "must-not-pass")
    supervisor = _supervisor(tmp_path)
    command = "printf '%s\\n' \"$PATH\" \"$HTTP_PROXY\" \"$HTTPS_PROXY\" \"$http_proxy\" \"$https_proxy\" \"$REQUESTS_CA_BUNDLE\" \"$SSL_CERT_FILE\" \"$CURL_CA_BUNDLE\" \"${UNTRUSTED_SECRET-unset}\""
    supervisor.exec(
        action_id="proxy-environment",
        handle="proxy-environment",
        arguments_digest=sha256(command.encode()).hexdigest(),
        command=command,
        cwd=None,
        timeout_seconds=5,
    )
    deadline = time.monotonic() + 5
    while True:
        reply = supervisor.read(
            action_id="proxy-query-" + str(time.time_ns()),
            handle="proxy-environment",
            arguments_digest="query",
            cursor={"stdout_offset": 0, "stderr_offset": 0},
            max_bytes=4096,
            wait_ms=50,
            durable=False,
        )
        if reply.state.value == "exited" and not reply.has_more:
            break
        assert time.monotonic() < deadline
    output = base64.b64decode(
        reply.stdout.data_base64, validate=True
    ).decode().splitlines()
    assert output == ["/trusted/bin", *trusted.values(), "unset"]


def test_process_supervisor_input_replay_unknown_stop_and_shutdown(tmp_path, monkeypatch):
    supervisor = _supervisor(tmp_path)
    supervisor.exec(
        action_id="attempt-input",
        handle="attempt-input",
        arguments_digest="exec-input",
        command="read value; printf '%s' \"$value\"",
        cwd=None,
        timeout_seconds=5,
    )
    first = supervisor.input(
        action_id="input-once",
        handle="attempt-input",
        arguments_digest="input-digest",
        data="only-once\n",
        eof=False,
    )
    replay = supervisor.input(
        action_id="input-once",
        handle="attempt-input",
        arguments_digest="input-digest",
        data="only-once\n",
        eof=False,
    )
    assert replay == first
    _wait_for_exit(supervisor, "attempt-input")
    result = supervisor.read(
        action_id="query-input",
        handle="attempt-input",
        arguments_digest="query",
        cursor={"stdout_offset": 0, "stderr_offset": 0},
        max_bytes=1024,
        durable=False,
    )
    assert base64.b64decode(result.stdout.data_base64) == b"only-once"

    supervisor.exec(
        action_id="attempt-ambiguous-input",
        handle="attempt-ambiguous-input",
        arguments_digest="exec-ambiguous",
        command="sleep 5",
        cwd=None,
        timeout_seconds=10,
    )
    monkeypatch.setattr("wuji_core.execution.process_supervisor.os.write", lambda *_: (_ for _ in ()).throw(OSError("lost")))
    with pytest.raises(OSError):
        supervisor.input(
            action_id="input-ambiguous",
            handle="attempt-ambiguous-input",
            arguments_digest="ambiguous-digest",
            data="x",
        )
    ambiguous = supervisor.input(
        action_id="input-ambiguous",
        handle="attempt-ambiguous-input",
        arguments_digest="ambiguous-digest",
        data="x",
    )
    assert ambiguous.state.value == "unknown"
    monkeypatch.undo()

    stopped = supervisor.stop(
        action_id="stop-ambiguous",
        handle="attempt-ambiguous-input",
        arguments_digest="stop-digest",
    )
    assert stopped.state.value == "exited"
    completed = Event()
    supervisor.shutdown(completed.set)
    assert completed.wait(2)
    with pytest.raises(DomainError) as stale:
        supervisor.exec(
            action_id="after-shutdown",
            handle="after-shutdown",
            arguments_digest="after-shutdown",
            command="true",
            cwd=None,
            timeout_seconds=1,
        )
    assert stale.value.code == "STALE_EXECUTION"


def _assignment():
    return {
        "schema_version": "wuji.assignment.v2",
        "operation_id": "operation-mcp",
        "identity": {
            "tenant_id": "tenant-fixture",
            "project_id": "project-mcp",
            "task_id": "task-mcp",
            "work_item_id": "work-mcp",
            "agent_run_id": "run-mcp",
            "execution_epoch": "1",
            "run_epoch": "1",
            "runtime_attempt": "1",
            "receiver_id": "receiver-mcp",
        },
        "work_kind": "explore",
        "snapshot_id": "snapshot-mcp",
        "profile_refs": ["profile-mcp"],
        "session_manifest_ref": None,
        "tool_definition_refs": ["tool-kali-exec-v1"],
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


class _ProcessGate(ProcessToolGate):
    def __init__(self):
        self.calls = []

    async def invoke(self, access, request, *, name=None):
        self.calls.append((access, request, name))
        reply = wire.ProcessReplyV1.model_validate(
            {
                "schema_version": "wuji.process-reply.v1",
                "handle": "attempt-mcp",
                "state": "running",
                "assurance": "executor_reported",
                "started_at": "2026-09-23T00:00:00Z",
                "finished_at": None,
                "exit_code": None,
                "signal": None,
                "stdout": None,
                "stderr": None,
                "cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "next_cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "has_more": False,
                "output_completeness": "unknown",
                "reason_code": None,
            }
        )
        receipt = ToolCallReceipt.model_validate(
            {
                "tool_call_id": "call-mcp",
                "operation_id": "call-mcp",
                "tool_attempt_id": "attempt-mcp",
                "status": "running",
                "evidence_receipt": None,
                "result_ref": None,
                "reason_code": None,
            }
        )
        return reply, receipt, None


class _ReceiptIdentity:
    def __init__(self):
        self.recorded = []

    def record_receipt(self, request, receipt):
        self.recorded.append((request, receipt))


def test_native_mcp_schema_defaults_and_maf_result_metadata(test_tokens):
    asyncio.run(_check_native_mcp_schema_defaults_and_maf_result_metadata(test_tokens))


async def _check_native_mcp_schema_defaults_and_maf_result_metadata(test_tokens):
    request = ToolCallRequest.model_validate(
        {
            "session_lineage": "lineage-mcp",
            "message_id": "message-mcp",
            "provider_call_id": "provider-call-mcp",
            "tool_definition_ref": "tool-kali-exec-v1",
            "arguments": {"command": "printf ok"},
            "sdk_content_id": "occurrence-mcp",
            "sdk_approval_id": None,
            "approval_ref": None,
        }
    )
    gate = _ProcessGate()
    native = create_native_mcp_app(
        token_verifier=TokenVerifier(
            public_key_pem=test_tokens.public_key_pem,
            issuer=test_tokens.issuer,
            audience=test_tokens.audience,
        ),
        process_gate=gate,
        allowed_hosts=["gate.example:8443"],
        allowed_origins=["http://gate.example:8443"],
    )
    parser = GateFunctions(
        definitions=[],
        identity=_ReceiptIdentity(),
        lineage="lineage-mcp",
        client=None,
        url="http://localhost:8000/internal/v2/tool-calls",
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=native.app),
        base_url="http://gate.example:8443",
        headers={"Authorization": "Bearer " + test_tokens.agent},
    )
    tool = MCPStreamableHTTPTool(
        name="wuji-native",
        url="http://gate.example:8443/internal/v2/mcp",
        allowed_tools=["kali_exec"],
        load_tools=True,
        load_prompts=False,
        parse_tool_results=parser.parse_mcp_result,
        terminate_on_close=False,
        http_client=client,
    )
    metadata = {
        MCP_INVOCATION_META: {
            "assignment": _assignment(),
            "native_occurrence": "occurrence-mcp",
            "tool_request": request.model_dump(mode="json"),
        }
    }
    async with native.starlette.router.lifespan_context(native.starlette):
        async with client, tool:
            assert len(tool.functions) == 1
            function = tool.functions[0]
            assert function.parameters() == PROCESS_TOOL_SCHEMAS["kali_exec"]
            assert "_meta" not in function.parameters()["properties"]
            assert function.additional_properties["_mcp_remote_name"] == "kali_exec"
            contents = await tool.call_tool(
                "kali_exec", command="printf ok", _meta=metadata
            )

    assert len(gate.calls) == 1
    assert gate.calls[0][1].arguments == {"command": "printf ok"}
    result_meta = contents[0].additional_properties[parser.MCP_CONTENT_META]
    assert result_meta[parser.MCP_RESULT_META]["kind"] == "process"
    await parser._record_mcp_result(
        SimpleNamespace(result=contents), name="kali_exec", request=request
    )
    assert parser.identity.recorded[0][1].status.value == "running"
    assert parser.receipts == []
    workspace_receipt = ToolCallReceipt.model_validate(
        {
            "tool_call_id": "workspace-call",
            "operation_id": "workspace-call",
            "tool_attempt_id": "workspace-attempt",
            "status": "complete",
            "evidence_receipt": None,
            "result_ref": None,
            "reason_code": None,
        }
    )
    workspace_result = Content.from_text(
        "{}",
        additional_properties={
            parser.MCP_CONTENT_META: {
                parser.MCP_RESULT_META: {
                    "kind": "workspace_publish",
                    "tool_receipt": workspace_receipt.model_dump(mode="json"),
                    "delivery": None,
                }
            }
        },
    )
    await parser._record_mcp_result(
        SimpleNamespace(result=[workspace_result]),
        name="workspace_publish",
        request=request,
    )
    assert parser.identity.recorded[-1][1] == workspace_receipt
    assert parser.receipts == []

    parent_receipt = ToolCallReceipt.model_validate(
        {
            "tool_call_id": "parent-process-call",
            "operation_id": "parent-process-call",
            "tool_attempt_id": "parent-process-attempt",
            "status": "complete",
            "evidence_receipt": {
                "capture_id": "parent-process-capture",
                "status": "accepted",
                "observation_ref": {
                    "entity_type": "observation",
                    "id": "parent-process-observation",
                    "revision": "1",
                },
                "artifact_refs": [
                    {"id": "parent-process-artifact", "version": "1", "sha256": "a" * 64}
                ],
                "request_id": "parent-process-request",
                "code": None,
            },
            "result_ref": {
                "id": "parent-process-artifact",
                "version": "1",
                "sha256": "a" * 64,
            },
            "reason_code": None,
        }
    )
    process_result = Content.from_text(
        "{}",
        additional_properties={
            parser.MCP_CONTENT_META: {
                parser.MCP_RESULT_META: {
                    "kind": "process",
                    "action_receipt": workspace_receipt.model_dump(mode="json"),
                    "parent_receipt": parent_receipt.model_dump(mode="json"),
                }
            }
        },
    )
    await parser._record_mcp_result(
        SimpleNamespace(result=[process_result]), name="kali_read", request=request
    )
    assert parser.receipts == []


def test_shutdown_endpoint_accepts_then_cleans_in_background(tmp_path):
    asyncio.run(_check_shutdown_endpoint_accepts_then_cleans_in_background(tmp_path))


def test_action_audience_is_accepted_by_kali_and_rejected_by_platform():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    binding = ExecutorDeploymentBinding(
        tenant_id="tenant-audience", project_id="project-audience",
        task_id="task-audience", executor_ref="executor-audience",
        receiver_id="receiver-audience", environment_ref="environment-audience",
        collector_subject="collector-audience", gate_subject="gate-audience",
    )
    signer = ExecutorActionSigner(
        private_key_pem=private_pem, kid="action-key",
        issuer="https://issuer.invalid", audience="wuji-platform:kali-action",
        subject="gate-audience",
    )
    token, expected = signer.issue_shutdown(
        binding, execution_epoch="1", runtime_attempt="1", reason="test audience"
    )
    verifier = ExecutorActionVerifier(
        public_key_pem=public_pem, issuer=signer.issuer,
        audience=signer.audience, subject=signer.subject, binding=binding,
    )
    assert verifier.verify_shutdown(token) == expected
    with pytest.raises(AuthenticationError):
        TokenVerifier(
            public_key_pem=public_pem,
            issuer=signer.issuer,
            audience="wuji-platform",
        ).verify(token)


def test_cleanup_accepts_an_older_epoch_for_the_same_current_attempt():
    owner = ("tenant-cleanup", "project-cleanup", "task-cleanup")
    receiver = {
        "receiver_id": "receiver-cleanup",
        "environment_ref": "environment-cleanup",
    }

    class Cursor:
        description = [SimpleNamespace(name=key) for key in receiver]

        def fetchone(self):
            return tuple(receiver.values())

    class Uow:
        @contextmanager
        def transaction(self, _access, task_id, *, capability):
            assert task_id == owner[2]
            assert capability == "control"
            yield SimpleNamespace(
                owner=owner,
                task={"runtime_attempt": 2, "execution_epoch": 5},
                connection=SimpleNamespace(execute=lambda *_args, **_kwargs: Cursor()),
            )

    executor = SimpleNamespace(
        drain=lambda **_kwargs: None,
        query_process=lambda *_args, **_kwargs: None,
        shutdown=lambda **_kwargs: None,
    )
    collector = SimpleNamespace()
    key = (*owner, "executor-cleanup")
    process_gate = object.__new__(ProcessToolGate)
    process_gate.admission = SimpleNamespace(uow=Uow())
    process_gate.gate = SimpleNamespace(
        executors={key: executor}, collector_accesses={key: collector}
    )
    process_gate.registry = SimpleNamespace(
        executor=lambda _tx, _ref: SimpleNamespace(
            protocol="process.v1",
            receiver_id=receiver["receiver_id"],
            environment_ref=receiver["environment_ref"],
        )
    )

    assert process_gate._cleanup_context(None, owner[2], "1", "2") == (
        key,
        executor,
        collector,
    )
    with pytest.raises(DomainError) as error:
        process_gate._cleanup_context(None, owner[2], "6", "2")
    assert (error.value.code, error.value.status) == ("STALE_EXECUTION", 409)


async def _check_shutdown_endpoint_accepts_then_cleans_in_background(tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    binding = ExecutorDeploymentBinding(
        tenant_id="tenant-shutdown",
        project_id="project-shutdown",
        task_id="task-shutdown",
        executor_ref="executor-shutdown",
        receiver_id="receiver-shutdown",
        environment_ref="environment-shutdown",
        collector_subject="collector-shutdown",
        gate_subject="gate-shutdown",
    )
    signer = ExecutorActionSigner(
        private_key_pem=private_pem,
        kid="shutdown-key",
        issuer="https://issuer.invalid",
        audience="wuji-kali",
        subject="gate-shutdown",
    )
    verifier = ExecutorActionVerifier(
        public_key_pem=public_pem,
        issuer=signer.issuer,
        audience=signer.audience,
        subject=signer.subject,
        binding=binding,
    )
    supervisor = _supervisor(tmp_path)
    supervisor.exec(
        action_id="shutdown-process",
        handle="shutdown-process",
        arguments_digest="shutdown-process",
        command="sleep 10",
        cwd=None,
        timeout_seconds=20,
    )
    callback = Event()
    app = _kali_factory()(
        token_verifier=TokenVerifier(
            public_key_pem=public_pem,
            issuer=signer.issuer,
            audience=signer.audience,
        ),
        binding=binding,
        admission=None,
        root=supervisor.root,
        receipt_root=supervisor.spool_root,
        tool_routes={},
        process_supervisor=supervisor,
        action_verifier=verifier,
        shutdown_callback=callback.set,
    )
    drain_token, drain_permit = signer.issue_shutdown(
        binding,
        execution_epoch="1",
        runtime_attempt="1",
        reason="test cleanup",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://kali.invalid"
    ) as client:
        drained = await client.post(
            "/internal/v2/process-control/drain",
            json={},
            headers={"Authorization": "Bearer " + drain_token},
        )
        assert drained.status_code == 200
        assert drained.json() == {
            "status": "drained",
            "task_id": binding.task_id,
            "runtime_attempt": "1",
            "request_id": drain_permit.jti,
        }
        assert not callback.is_set()
        assert _wait_for_exit(supervisor, "shutdown-process").state.value == "exited"
        token, permit = signer.issue_shutdown(
            binding,
            execution_epoch="1",
            runtime_attempt="1",
            reason="test cleanup",
        )
        response = await client.post(
            "/internal/v2/process-control/shutdown",
            json={},
            headers={"Authorization": "Bearer " + token},
        )
    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "task_id": binding.task_id,
        "runtime_attempt": "1",
        "request_id": permit.jti,
    }
    assert await asyncio.to_thread(callback.wait, 2)


@contextmanager
def _process_case(environment, tmp_path, audit_directory):
    credential = issue_run_credential(audit_directory)
    tool_refs = list(PROCESS_TOOL_SCHEMAS)
    with control_case(environment, tmp_path, audit_directory) as control:
        with environment.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,"
                "can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
                (*OWNER, credential.principal.subject),
            )
            connection.execute(
                "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,"
                "published_ref) VALUES('model:fixture-model-v1','model',NULL,2,"
                "'fixture-capacity-v1')"
            )
            connection.execute(
                "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,"
                "pool_key) VALUES(%s,%s,%s,'model:fixture-model-v1')",
                OWNER,
            )
            for name, schema in PROCESS_TOOL_SCHEMAS.items():
                registry_module.register_tool_definition(
                    connection,
                    tenant_id=OWNER[0],
                    definition={
                        "ref": name + "-v1",
                        "revision": "1",
                        "published_at": "2026-09-13T00:00:00Z",
                        "name": name,
                        "input_schema": schema,
                        "executor_ref": "process-fixture",
                        "approval_required": False,
                        "allowed_target_kinds": ["process"],
                    },
                )
            registry_module.register_executor(
                connection,
                owner=OWNER,
                executor={
                    "ref": "process-fixture",
                    "receiver_id": RECEIVER,
                    "environment_ref": ENVIRONMENT,
                    "collector_subject": "collector-fixture",
                    "evidence_origin": "imported_unverified",
                    "capture_layer": "executor_reported_command_output",
                    "allowed_tool_refs": [name + "-v1" for name in tool_refs],
                    "protocol": "process.v1",
                },
            )
            config = task_admission_config(
                registry_module,
                gateway_url="https://model.invalid",
                max_tool_calls=8,
                max_total_output_bytes=1 << 20,
                allowed_tool_refs=[name + "-v1" for name in tool_refs],
            ).model_dump(mode="json")
            config["runtime"]["buffer_bytes"] = 131072
            config["runtime"]["limits"]["max_single_output_bytes"] = 131072
            config["runtime"]["process_limits"] = {
                "max_active_execs": 2,
                "max_read_wait_milliseconds": 1000,
                "max_input_bytes": 4096,
                "stop_grace_seconds": 0.25,
            }
            registry_module.register_task_config(
                connection, owner=OWNER, config=config
            )
        prepared_run(control)
        observe(control, "started", process=process())
        with environment.migration_connection() as connection:
            registry_module.bind_run_credential(
                connection,
                binding=run_binding(
                    registry_module,
                    credential,
                    purposes=["tool_request"],
                    allowed_tool_refs=[name + "-v1" for name in tool_refs],
                ),
            )

        registry = registry_module.AdmissionRegistry(control.uow)
        ledger = AdmissionLedger(control.uow)
        admission = ToolAdmission(control.uow, registry=registry, ledger=ledger)
        evidence = EvidenceService(control.uow, control.store)
        process_workspace = tmp_path / "process-workspace"
        process_workspace.mkdir()
        supervisor = ProcessSupervisor(
            root=process_workspace,
            spool_root=(tmp_path / "process-spool"),
            max_active=2,
            max_output_bytes=131072,
            stop_grace_seconds=0.25,
        )
        binding = ExecutorDeploymentBinding(
            tenant_id=OWNER[0],
            project_id=OWNER[1],
            task_id=OWNER[2],
            executor_ref="process-fixture",
            receiver_id=RECEIVER,
            environment_ref=ENVIRONMENT,
            collector_subject="collector-fixture",
            gate_subject="gate-fixture",
        )
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        signer = ExecutorActionSigner(
            private_key_pem=private_pem,
            kid="process-key",
            issuer="https://process.invalid",
            audience="wuji-process",
            subject="gate-fixture",
        )
        verifier = ExecutorActionVerifier(
            public_key_pem=public_pem,
            issuer=signer.issuer,
            audience=signer.audience,
            subject=signer.subject,
            binding=binding,
        )
        kali_app = create_app(
            token_verifier=TokenVerifier(
                public_key_pem=public_pem,
                issuer=signer.issuer,
                audience=signer.audience,
            ),
            routers=[
                create_process_executor_router(
                    supervisor,
                    verifier=verifier,
                    binding=binding,
                    shutdown_callback=lambda: None,
                )
            ],
        )
        certificates = TestCertificateAuthority(tmp_path / "process-tls")
        with TlsAsgiServer(
            kali_app,
            identity=certificates.issue_server("kali"),
            audit_path=audit_directory / "process-kali-https.jsonl",
        ) as kali_server:
            remote = RemoteProcessExecutor(
                binding=binding,
                base_url=kali_server.url,
                ca_file=str(certificates.ca_file),
                signer=signer,
                max_output_bytes=131072,
            )
            gate = ToolGate(
                admission,
                registry=registry,
                ledger=ledger,
                artifacts=control.store,
                evidence=evidence,
                executors={(*OWNER, "process-fixture"): remote},
                collector_accesses={
                    (*OWNER, "process-fixture"): access(
                        "collector-fixture", role="collector"
                    )
                },
            )
            yield SimpleNamespace(
                control=control,
                credential=credential,
                access=wire_access(credential),
                gate=gate,
                process_gate=ProcessToolGate(gate),
                kali_server=kali_server,
                remote=remote,
            )


def wire_access(credential):
    from wuji_core.persistence.uow import AccessContext

    return AccessContext(credential.principal, "process-test")


def test_process_mcp_gate_records_and_seals_command_log(
    db_environment, tmp_path, audit_directory
):
    asyncio.run(
        _check_process_mcp_gate_records_and_seals_command_log(
            db_environment, tmp_path, audit_directory
        )
    )


async def _check_process_mcp_gate_records_and_seals_command_log(
    db_environment, tmp_path, audit_directory
):
    with _process_case(db_environment, tmp_path, audit_directory) as case:
        native = create_native_mcp_app(
            token_verifier=case.credential.verifier,
            process_gate=case.process_gate,
        )
        request = ToolCallRequest.model_validate(
            {
                "session_lineage": SESSION_LINEAGE,
                "message_id": "message-process",
                "provider_call_id": "provider-process",
                "tool_definition_ref": "kali_exec-v1",
                "arguments": {
                    "command": "printf gate-ok; printf gate-err >&2"
                },
                "sdk_content_id": "occurrence-process",
                "sdk_approval_id": None,
                "approval_ref": None,
            }
        )
        assignment = _assignment()
        assignment["identity"] = IDENTITY
        assignment["tool_definition_refs"] = ["kali_exec-v1"]
        metadata = {
            MCP_INVOCATION_META: {
                "assignment": assignment,
                "native_occurrence": "occurrence-process",
                "tool_request": request.model_dump(mode="json"),
            }
        }
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=native.app),
            base_url="http://localhost:8000",
            headers={"Authorization": "Bearer " + case.credential.token},
        )
        tool = MCPStreamableHTTPTool(
            name="wuji-native",
            url="http://localhost:8000/internal/v2/mcp",
            allowed_tools=["kali_exec"],
            load_tools=True,
            load_prompts=False,
            terminate_on_close=False,
            http_client=client,
        )
        async with native.starlette.router.lifespan_context(native.starlette):
            async with client, tool:
                first = await tool.session.call_tool(
                    "kali_exec",
                    arguments={"command": request.arguments["command"]},
                    meta=metadata,
                )
                replay = await tool.session.call_tool(
                    "kali_exec",
                    arguments={"command": request.arguments["command"]},
                    meta=metadata,
                )
                first_meta = first.meta[GateFunctions.MCP_RESULT_META]
                replay_meta = replay.meta[GateFunctions.MCP_RESULT_META]
                assert first.structuredContent["handle"] == replay.structuredContent["handle"]
                assert first_meta["action_receipt"]["tool_call_id"] == replay_meta[
                    "action_receipt"
                ]["tool_call_id"]
                call_id = first_meta["action_receipt"]["tool_call_id"]
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    receipt = await asyncio.to_thread(
                        case.gate.ledger.tool_call, case.access, call_id
                    )
                    if receipt.status.value == "complete":
                        break
                    await asyncio.sleep(0.05)
                else:
                    raise AssertionError("process receipt was not finalized")

        assert receipt.evidence_receipt.status.value == "accepted"
        assert receipt.result_ref is not None
        with case.control.uow.transaction(case.access, TASK) as tx:
            record = case.control.store.record(tx, receipt.result_ref)
            command_log = case.control.store.checked_bytes(record)
        document = wire_json(command_log)
        assert base64.b64decode(document["stdout_base64"]) == b"gate-ok"
        assert base64.b64decode(document["stderr_base64"]) == b"gate-err"
        assert document["assurance"] == "executor_reported"
        assert [item.path for item in case.kali_server.exchanges].count(
            "/internal/v2/process/exec"
        ) == 1
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT state,finalization_state,stdout_bytes,stderr_bytes FROM "
                "vnext.process_execution WHERE tool_attempt_id=%s",
                (receipt.tool_attempt_id.root,),
            ).fetchone() == ("exited", "sealed", 7, 8)


def wire_json(raw):
    from wuji_core.http import strict_json_loads

    return strict_json_loads(raw)
