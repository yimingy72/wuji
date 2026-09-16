"""P06 external fixtures and signed identities, never admission or ledger logic."""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from types import ModuleType
from uuid import uuid4

import httpx
import pytest

from support.p03 import access
from support.http_capture import RecordedTestClient
from support.identity_provider import TestIdentityProvider
from test_knowledge_admission import IDENTITY, OWNER
from test_work_state_guards import control_case, observe, prepared_run, process
from wuji_core.http import canonical_json_bytes, create_app
from wuji_core.http.auth import Principal, TokenVerifier
from wuji_core.persistence.uow import AccessContext, UnitOfWork


TENANT = "tenant-fixture"
PROJECT = "project-fixture"
TASK = "task-fixture"
WORK = "work-fixture"
RUN = "run-fixture"
RECEIVER = "receiver-fixture"
ENVIRONMENT = "environment-fixture"
SESSION_LINEAGE = "session-lineage-fixture"
WORKSPACE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string", "minLength": 1}},
    "required": ["path"],
    "additionalProperties": False,
}

NATIVE_MODEL_REQUEST = {
    "model": "fixture-model",
    "messages": [
        {"role": "system", "content": "Use only the synthetic fixture."},
        {"role": "user", "content": "Read the fixture version."},
    ],
    "stream": False,
    "max_tokens": 64,
    "temperature": 0.125,
}

NATIVE_MODEL_RESPONSE = {
    "id": "chatcmpl-p06-fixture",
    "object": "chat.completion",
    "created": 1,
    "model": "fixture-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-p06-read",
                        "type": "function",
                        "function": {
                            "name": "read_fixture",
                            "arguments": '{"path":"version.txt"}',
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 17, "completion_tokens": 8, "total_tokens": 25},
}


@dataclass(frozen=True, slots=True)
class IssuedRunCredential:
    token: str
    principal: Principal
    verifier: TokenVerifier
    provider: TestIdentityProvider


def issue_run_credential(audit_directory: Path) -> IssuedRunCredential:
    """Issue and verify one real signed JWT; registration remains production-owned."""

    provider = TestIdentityProvider(
        audit_path=audit_directory / "p06-identity-events.jsonl"
    )
    token = provider.issue(
        subject="run-worker-fixture",
        tenant_id=TENANT,
        roles=["worker"],
    )
    verifier = TokenVerifier(
        public_key_pem=provider.public_key_pem,
        issuer=provider.issuer,
        audience=provider.audience,
    )
    return IssuedRunCredential(
        token=token,
        principal=verifier.verify(token),
        verifier=verifier,
        provider=provider,
    )


class SyntheticTaskKeyResolver:
    """Return an inert test key only at the ModelGate's private boundary."""

    def __init__(self) -> None:
        self.secret = "p06-synthetic-task-key"
        self.resolved_refs: list[str] = []

    def resolve(self, secret_ref: str) -> str:
        self.resolved_refs.append(secret_ref)
        return self.secret


@dataclass(frozen=True, slots=True)
class UpstreamExchange:
    method: str
    path: str
    headers: dict[str, str]
    request_body: bytes
    status_code: int
    response_headers: dict[str, str]
    response_body: bytes


PARTIAL_SSE = (
    b'data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk",'
    b'"created":1,"model":"fixture-model","choices":[{"index":0,'
    b'"delta":{"role":"assistant","content":"partial"},'
    b'"finish_reason":null}]}\n\n'
)


class PerRequestAsyncHttpClient:
    """Keep HTTPX connection pools inside RecordedTestClient's current event loop."""

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            trust_env=False,
            follow_redirects=False,
        ) as client:
            async with client.stream(method, url, **kwargs) as response:
                yield response


class LocalModelUpstream:
    """A real localhost HTTP peer; all admission and accounting stay production-side."""

    def __init__(self, audit_path: Path) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                request_body = self.rfile.read(length)
                headers = {key.lower(): value for key, value in self.headers.items()}
                owner.request_started.set()
                if self.path != "/v1/chat/completions":
                    response_body = b'{"error":"not_found"}'
                    response_headers = {
                        "content-type": "application/json",
                        "content-length": str(len(response_body)),
                    }
                    owner._send(self, 404, response_body, response_headers)
                    owner._record(
                        UpstreamExchange(
                            "POST",
                            self.path,
                            headers,
                            request_body,
                            404,
                            response_headers,
                            response_body,
                        )
                    )
                    return
                if owner.behavior == "disconnect_before_headers":
                    owner.disconnect_requests.append((headers, request_body))
                    self.close_connection = True
                    try:
                        self.connection.shutdown(2)
                    except OSError:
                        pass
                    self.connection.close()
                    return
                if owner.behavior == "blocking_json":
                    owner.release_response.wait(timeout=10)
                if owner.behavior == "partial_stream":
                    response_headers = {
                        "content-type": "text/event-stream",
                        "connection": "close",
                    }
                    self.send_response_only(200)
                    for key, value in response_headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(PARTIAL_SSE)
                    self.wfile.flush()
                    self.close_connection = True
                    owner._record(
                        UpstreamExchange(
                            "POST",
                            self.path,
                            headers,
                            request_body,
                            200,
                            response_headers,
                            PARTIAL_SSE,
                        )
                    )
                    return
                response_body = canonical_json_bytes(NATIVE_MODEL_RESPONSE)
                response_headers = {
                    "content-type": "application/json",
                    "content-length": str(len(response_body)),
                }
                owner._send(self, 200, response_body, response_headers)
                owner._record(
                    UpstreamExchange(
                        "POST",
                        self.path,
                        headers,
                        request_body,
                        200,
                        response_headers,
                        response_body,
                    )
                )

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        self.behavior = "json"
        self.exchanges: list[UpstreamExchange] = []
        self.disconnect_requests: list[tuple[dict[str, str], bytes]] = []
        self.audit_path = audit_path
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.request_started = Event()
        self.release_response = Event()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"
        self.client = PerRequestAsyncHttpClient()

    @staticmethod
    def _send(
        handler: BaseHTTPRequestHandler,
        status: int,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        handler.send_response_only(status)
        effective = headers or {
            "content-type": "application/json",
            "content-length": str(len(body)),
        }
        for key, value in effective.items():
            handler.send_header(key, value)
        handler.end_headers()
        handler.wfile.write(body)

    def _record(self, exchange: UpstreamExchange) -> None:
        self.exchanges.append(exchange)
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "request": {
                            "method": exchange.method,
                            "url": self.url,
                            "headers": exchange.headers,
                            "body_base64": base64.b64encode(
                                exchange.request_body
                            ).decode("ascii"),
                        },
                        "response": {
                            "status_code": exchange.status_code,
                            "headers": exchange.response_headers,
                            "body_base64": base64.b64encode(
                                exchange.response_body
                            ).decode("ascii"),
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    def close(self) -> None:
        self.release_response.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def production(name: str):
    try:
        return import_module("wuji_core." + name)
    except ModuleNotFoundError as error:
        pytest.fail(f"P06 production entrypoint absent: {error.name}")


def migrate_earliest_v8_then_current(environment) -> None:
    """Create the exact 67a v8 schema, then exercise the public current upgrade."""

    root = Path(__file__).resolve().parents[2]
    revision = "67a8030e7c6a7c1cf767aa20a60fd6bfec5fe5e4"

    def source(path: str) -> str:
        return subprocess.check_output(
            ["git", "show", f"{revision}:{path}"],
            cwd=root,
            text=True,
        )

    module_name = "wuji_core.persistence.admission_hardening_schema"
    previous = sys.modules.get(module_name)
    historical_hardening = ModuleType(module_name)
    historical_hardening.__file__ = "git:" + revision + "/admission_hardening_schema.py"
    exec(
        compile(
            source(
                "packages/wuji-core/src/wuji_core/persistence/admission_hardening_schema.py"
            ),
            historical_hardening.__file__,
            "exec",
        ),
        historical_hardening.__dict__,
    )
    sys.modules[module_name] = historical_hardening
    historical_schema = ModuleType("p06_historical_schema")
    historical_schema.__file__ = "git:" + revision + "/schema.py"
    try:
        exec(
            compile(
                source("packages/wuji-core/src/wuji_core/persistence/schema.py"),
                historical_schema.__file__,
                "exec",
            ),
            historical_schema.__dict__,
        )
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous

    with environment.migration_connection() as connection:
        historical_schema.migrate(
            connection, application_role=environment.application_role
        )
        heads = {
            value[0]
            for value in connection.execute(
                "SELECT head FROM vnext.schema_migration"
            ).fetchall()
        }
        assert "vnext_0008_p06_admission_hardening" in heads
        assert "vnext_0009_p06_request_write_guards" not in heads

    from wuji_core.persistence.schema import migrate

    with environment.migration_connection() as connection:
        migrate(connection, application_role=environment.application_role)
        assert connection.execute(
            "SELECT 1 FROM vnext.schema_migration WHERE head='vnext_0009_p06_request_write_guards'"
        ).fetchone() == (1,)


def task_admission_config(
    registry_module,
    *,
    gateway_url: str,
    max_model_requests: int = 2,
    max_tool_calls: int = 2,
    max_total_output_bytes: int = 8192,
    allowed_tool_refs: list[str] | None = None,
):
    tool_refs = allowed_tool_refs or []
    return registry_module.TaskAdmissionConfig.model_validate(
        {
            "model": {
                "ref": "fixture-model-v1",
                "revision": "1",
                "published_at": "2026-09-13T00:00:00Z",
                "capability_ref": "fixture-chat-completions-capability-v1",
                "protocol": "chat_completions",
                "client_model": "fixture-model",
                "upstream_model": "fixture-upstream-model",
                "gateway_url": gateway_url,
                "task_key_ref": "fixture-task-key-ref",
                "max_retries": 0,
            },
            "runtime": {
                "ref": "fixture-runtime-v1",
                "revision": "1",
                "published_at": "2026-09-13T00:00:00Z",
                "lock_digest": "a" * 64,
                "limits": {
                    "max_work_items": 4,
                    "max_reason_runs": 2,
                    "max_model_requests": max_model_requests,
                    "max_tool_calls": max_tool_calls,
                    "max_single_output_bytes": 4096,
                    "max_total_output_bytes": max_total_output_bytes,
                    "max_elapsed_seconds": 300,
                    "max_attempts_per_work": 3,
                    "repair_attempts": 1,
                },
                "chunk_bytes": 512,
                "buffer_bytes": 1024,
                "idle_timeout_seconds": 5,
                "total_timeout_seconds": 30,
                "max_pending_operations": 4,
                "max_inflight_tools": 1,
                "max_inflight_model_requests": 1,
                "allowed_tool_refs": tool_refs,
            },
            "allowed_tool_refs": tool_refs,
        }
    )


def run_binding(
    registry_module,
    credential: IssuedRunCredential,
    *,
    identity: dict[str, str] | None = None,
    purposes: list[str] | None = None,
    allowed_tool_refs: list[str] | None = None,
):
    return registry_module.RunCredentialBinding.model_validate(
        {
            "identity": identity or IDENTITY,
            "subject": credential.principal.subject,
            "token_id": credential.principal.token_id,
            "expires_at": datetime.now(UTC) + timedelta(minutes=10),
            "purposes": purposes or ["model_request"],
            "session_lineage": SESSION_LINEAGE,
            "allowed_tool_refs": allowed_tool_refs or [],
        }
    )


def register_workspace_components(
    registry_module, connection, *, approval_required: bool = False
) -> None:
    registry_module.register_tool_definition(
        connection,
        tenant_id=TENANT,
        definition=registry_module.ToolDefinition.model_validate(
            {
                "ref": "fixture-reader-v1",
                "revision": "1",
                "published_at": "2026-09-13T00:00:00Z",
                "name": "read_fixture",
                "input_schema": WORKSPACE_INPUT_SCHEMA,
                "executor_ref": "workspace-reader-fixture",
                "approval_required": approval_required,
                "allowed_target_kinds": ["workspace_read"],
            }
        ),
    )
    registry_module.register_executor(
        connection,
        owner=OWNER,
        executor=registry_module.ExecutorRegistration.model_validate(
            {
                "ref": "workspace-reader-fixture",
                "receiver_id": RECEIVER,
                "environment_ref": ENVIRONMENT,
                "collector_subject": "collector-fixture",
                "evidence_origin": "fixture_capture",
                "capture_layer": "fixture_file_bytes",
                "allowed_tool_refs": ["fixture-reader-v1"],
            }
        ),
    )


@contextmanager
def model_case(
    environment,
    tmp_path: Path,
    audit_directory: Path,
    *,
    max_model_requests: int = 2,
    max_total_output_bytes: int = 8192,
    advertise_workspace_tool: bool = False,
):
    """Compose signed inbound HTTP over production P06 and an isolated real PG."""

    registry_module = production("admission.registry")
    ledger_module = production("admission.ledger")
    model_module = production("admission.models")
    model_http = production("http.model_gate")
    credential = issue_run_credential(audit_directory)
    upstream = LocalModelUpstream(audit_directory / "p06-upstream-exchanges.jsonl")
    key_resolver = SyntheticTaskKeyResolver()
    client = None
    try:
        with control_case(environment, tmp_path, audit_directory) as control:
            with environment.migration_connection() as connection:
                connection.execute(
                    "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
                    (*OWNER, credential.principal.subject),
                )
                connection.execute(
                    "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES('model:fixture-model-v1','model',NULL,2,'fixture-capacity-v1')"
                )
                connection.execute(
                    "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,'model:fixture-model-v1')",
                    OWNER,
                )
                if advertise_workspace_tool:
                    register_workspace_components(registry_module, connection)
                allowed_tool_refs = (
                    ["fixture-reader-v1"] if advertise_workspace_tool else []
                )
                registry_module.register_task_config(
                    connection,
                    owner=OWNER,
                    config=task_admission_config(
                        registry_module,
                        gateway_url=upstream.url,
                        max_model_requests=max_model_requests,
                        max_total_output_bytes=max_total_output_bytes,
                        allowed_tool_refs=allowed_tool_refs,
                    ),
                )
            prepared_run(control)
            observe(control, "started", process=process())
            with environment.migration_connection() as connection:
                registry_module.bind_run_credential(
                    connection,
                    binding=run_binding(
                        registry_module,
                        credential,
                        allowed_tool_refs=allowed_tool_refs,
                    ),
                )

            registry = registry_module.AdmissionRegistry(control.uow)
            ledger = ledger_module.AdmissionLedger(control.uow)
            admission = model_module.ModelAdmission(
                control.uow, registry=registry, ledger=ledger
            )
            gate = model_module.ModelGate(
                admission,
                registry=registry,
                ledger=ledger,
                key_resolver=key_resolver,
                transport=model_module.HttpxModelTransport(upstream.client),
            )
            client = RecordedTestClient(
                create_app(
                    token_verifier=credential.verifier,
                    routers=[model_http.create_model_router(gate)],
                ),
                audit_path=audit_directory / "p06-http-exchanges.jsonl",
            )
            yield SimpleNamespace(
                **locals(),
                access=AccessContext(credential.principal, "p06-ledger-read"),
            )
    finally:
        if client is not None:
            client.close()
        upstream.close()


def fresh_ledger(case):
    """Build a new production ledger instance over a new-connection UoW."""

    return case.ledger_module.AdmissionLedger(
        UnitOfWork(case.environment.additional_app_connection)
    )


def bind_secondary_model_run(case) -> IssuedRunCredential:
    """Provision a second real P05 Run so two Runs can race one Task quota."""

    token = case.credential.provider.issue(
        subject="run-worker-b-fixture",
        tenant_id=TENANT,
        roles=["worker"],
    )
    credential = IssuedRunCredential(
        token=token,
        principal=case.credential.verifier.verify(token),
        verifier=case.credential.verifier,
        provider=case.credential.provider,
    )
    identity = {
        **IDENTITY,
        "work_item_id": "work-b",
        "agent_run_id": "run-b",
    }
    with case.environment.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
            (*OWNER, credential.principal.subject),
        )
        connection.execute(
            "INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,environment_ref,model_mode,start_operation_id,pod_uid,execution_epoch,run_epoch,runtime_attempt) VALUES(%s,%s,%s,%s,%s,%s,%s,'synthetic',%s,%s,%s,%s,%s)",
            (
                *OWNER,
                identity["agent_run_id"],
                identity["work_item_id"],
                identity["receiver_id"],
                ENVIRONMENT,
                "start-run-b",
                "pod-fixture",
                int(identity["execution_epoch"]),
                int(identity["run_epoch"]),
                int(identity["runtime_attempt"]),
            ),
        )
        connection.execute(
            "UPDATE vnext.work_item SET state='leased',current_run_id=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s",
            (identity["agent_run_id"], *OWNER, identity["work_item_id"]),
        )
    with case.control.uow.transaction(
        access("scheduler-fixture", role="scheduler"), TASK, capability="admit"
    ) as tx:
        from wuji_core.execution.capacity import CapacityService

        CapacityService.reserve(tx, identity["agent_run_id"])
    observe(
        case.control,
        "started",
        run=identity["agent_run_id"],
        work=identity["work_item_id"],
        process=process(),
    )
    with case.environment.migration_connection() as connection:
        case.registry_module.bind_run_credential(
            connection,
            binding=run_binding(
                case.registry_module, credential, identity=identity
            ),
        )
    return credential


def bind_same_run_purpose(
    case,
    *,
    subject: str,
    purpose: str,
    allowed_tool_refs: list[str] | None = None,
):
    """Bind another least-privilege credential to the already-running Run."""

    token = case.credential.provider.issue(
        subject=subject,
        tenant_id=TENANT,
        roles=["worker"],
    )
    credential = IssuedRunCredential(
        token=token,
        principal=case.credential.verifier.verify(token),
        verifier=case.credential.verifier,
        provider=case.credential.provider,
    )
    with case.environment.migration_connection() as connection:
        connection.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
            (*OWNER, credential.principal.subject),
        )
        case.registry_module.bind_run_credential(
            connection,
            binding=run_binding(
                case.registry_module,
                credential,
                purposes=[purpose],
                allowed_tool_refs=(
                    allowed_tool_refs
                    if allowed_tool_refs is not None
                    else ["fixture-reader-v1"] if purpose == "tool_request" else []
                ),
            ),
        )
    return credential, AccessContext(
        credential.principal, "p06-cross-purpose-probe"
    )


def model_headers(
    case, request_id: str, credential: IssuedRunCredential | None = None
) -> dict[str, str]:
    effective = credential or case.credential
    return {
        "Authorization": "Bearer " + effective.token,
        "Content-Type": "application/json",
        "X-Wuji-Request-ID": request_id,
    }


class BlockingSettlementExecutor:
    """Read a real file after permit CAS, while allowing a revocation race."""

    def __init__(self, tool_module, admission, workspace: Path) -> None:
        self.tool_module = tool_module
        self.admission = admission
        self.workspace = workspace.resolve()
        self.receiver_id = RECEIVER
        self.started = Event()
        self.release = Event()
        self.dispatches = 0
        self.receipts: dict[str, object] = {}

    def _receipt(self, permit, *, status: str, output: bytes | None):
        now = datetime.now(UTC)
        receipt_id = str(uuid4())
        source = {
            "tool_attempt_id": permit.tool_attempt_id,
            "receiver_id": self.receiver_id,
            "environment_ref": ENVIRONMENT,
            "arguments_digest": permit.arguments_digest,
            "receipt_id": receipt_id,
        }
        if output is not None:
            source["output_bytes"] = len(output)
            source["output_sha256"] = sha256(output).hexdigest()
        return self.tool_module.ToolExecutionReceipt.model_validate(
            {
                "tool_attempt_id": permit.tool_attempt_id,
                "receiver_id": self.receiver_id,
                "receipt_id": receipt_id,
                "status": status,
                "started_at": now if status == "exited" else None,
                "exited_at": now if status == "exited" else None,
                "source_receipt": source,
                "output": output,
                "media_type": "application/octet-stream" if output is not None else None,
                "completeness": "complete" if output is not None else "unknown",
                "error_code": None,
            }
        )

    async def dispatch(self, permit):
        await asyncio.to_thread(
            self.admission.check_execution,
            permit,
            receiver_id=self.receiver_id,
        )
        self.dispatches += 1
        self.started.set()
        await asyncio.to_thread(self.release.wait, 5)
        target = (self.workspace / permit.arguments["path"]).resolve()
        assert target.is_relative_to(self.workspace)
        receipt = self._receipt(permit, status="exited", output=target.read_bytes())
        self.receipts[permit.tool_attempt_id] = receipt
        return receipt

    async def query(self, permit):
        await asyncio.to_thread(
            self.admission.validate_receipt_permit,
            permit,
            receiver_id=self.receiver_id,
        )
        return self.receipts.get(permit.tool_attempt_id) or self._receipt(
            permit, status="unknown", output=None
        )

    async def cancel(self, permit, *, reason: str):
        del reason
        return await self.query(permit)


class SimulatedProcessExit(BaseException):
    pass


class CancelDeliveryProbe:
    """Expose the durable cancel-delivery window without simulating admission."""

    def __init__(self, tool_module, admission, *, crash: bool) -> None:
        self.tool_module = tool_module
        self.admission = admission
        self.crash = crash
        self.cancel_calls = 0

    def _receipt(self, permit):
        receipt_id = str(uuid4())
        return self.tool_module.ToolExecutionReceipt.model_validate(
            {
                "tool_attempt_id": permit.tool_attempt_id,
                "receiver_id": RECEIVER,
                "receipt_id": receipt_id,
                "status": "not_started",
                "started_at": None,
                "exited_at": None,
                "source_receipt": {
                    "tool_attempt_id": permit.tool_attempt_id,
                    "receiver_id": RECEIVER,
                    "environment_ref": ENVIRONMENT,
                    "arguments_digest": permit.arguments_digest,
                    "receipt_id": receipt_id,
                },
                "output": None,
                "media_type": None,
                "completeness": "unknown",
                "error_code": "cancelled_before_start",
            }
        )

    async def dispatch(self, permit):
        del permit
        raise AssertionError("cancel probe must not dispatch")

    async def query(self, permit):
        await asyncio.to_thread(
            self.admission.validate_receipt_permit,
            permit,
            receiver_id=RECEIVER,
        )
        return self._receipt(permit)

    async def cancel(self, permit, *, reason: str):
        del reason
        self.cancel_calls += 1
        if self.crash:
            raise SimulatedProcessExit
        return await self.query(permit)


@contextmanager
def tool_case(
    environment,
    tmp_path: Path,
    audit_directory: Path,
    *,
    approval_required: bool = False,
    max_tool_calls: int = 2,
    max_total_output_bytes: int = 8192,
):
    """Compose the production tool Gate with a real local workspace read."""

    registry_module = production("admission.registry")
    ledger_module = production("admission.ledger")
    model_module = production("admission.models")
    tool_module = production("admission.tools")
    model_http = production("http.model_gate")
    tool_http = production("http.tool_gate")
    evidence_http = production("http.evidence")
    credential = issue_run_credential(audit_directory)
    upstream = LocalModelUpstream(
        audit_directory / "p06-upstream-exchanges.jsonl"
    )
    key_resolver = SyntheticTaskKeyResolver()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    receipt_root = tmp_path / "receiver-inbox"
    expected_output = b"fixture-version=17\n"
    (workspace / "version.txt").write_bytes(expected_output)
    client = None
    with control_case(environment, tmp_path, audit_directory) as control:
        with environment.migration_connection() as connection:
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
                (*OWNER, credential.principal.subject),
            )
            connection.execute(
                "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES('model:fixture-model-v1','model',NULL,2,'fixture-capacity-v1')"
            )
            connection.execute(
                "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,'model:fixture-model-v1')",
                OWNER,
            )
            register_workspace_components(
                registry_module,
                connection,
                approval_required=approval_required,
            )
            registry_module.register_task_config(
                connection,
                owner=OWNER,
                config=task_admission_config(
                    registry_module,
                    gateway_url=upstream.url,
                    max_tool_calls=max_tool_calls,
                    max_total_output_bytes=max_total_output_bytes,
                    allowed_tool_refs=["fixture-reader-v1"],
                ),
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
                    allowed_tool_refs=["fixture-reader-v1"],
                ),
            )

        registry = registry_module.AdmissionRegistry(control.uow)
        ledger = ledger_module.AdmissionLedger(control.uow)
        admission = tool_module.ToolAdmission(
            control.uow, registry=registry, ledger=ledger
        )
        executor = tool_module.WorkspaceReadExecutor(
            root=workspace,
            receipt_root=receipt_root,
            admission=admission,
            receiver_id=RECEIVER,
            environment_ref=ENVIRONMENT,
        )
        evidence = production("evidence.observations").EvidenceService(
            control.uow, control.store
        )
        gate = tool_module.ToolGate(
            admission,
            registry=registry,
            ledger=ledger,
            artifacts=control.store,
            evidence=evidence,
            executors={(*OWNER, "workspace-reader-fixture"): executor},
            collector_accesses={
                (*OWNER, "workspace-reader-fixture"): access(
                    "collector-fixture", role="collector"
                )
            },
        )
        model_admission = model_module.ModelAdmission(
            control.uow, registry=registry, ledger=ledger
        )
        model_gate = model_module.ModelGate(
            model_admission,
            registry=registry,
            ledger=ledger,
            key_resolver=key_resolver,
            transport=model_module.HttpxModelTransport(upstream.client),
            tool_capabilities=tool_module.ToolCapabilityResolver(gate),
        )
        app = create_app(
            token_verifier=credential.verifier,
            routers=[
                model_http.create_model_router(model_gate),
                tool_http.create_tool_router(gate),
                evidence_http.create_evidence_router(evidence),
            ],
        )
        client = RecordedTestClient(
            app, audit_path=audit_directory / "p06-tool-http-exchanges.jsonl"
        )
        try:
            yield SimpleNamespace(
                **locals(),
                access=AccessContext(credential.principal, "p06-tool-ledger-read"),
            )
        finally:
            if client is not None:
                client.close()
            upstream.close()


def tool_headers(case, request_id: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + case.credential.token,
        "Content-Type": "application/json",
        "X-Wuji-Request-ID": request_id,
    }
