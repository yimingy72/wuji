"""P07 M1 real HTTP/SDK/PG test host; no runtime or Gate substitutes."""

from __future__ import annotations

import asyncio
import base64
import json
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from pathlib import Path
from threading import Event, Lock, Thread
from types import SimpleNamespace
from urllib.parse import urlsplit

from support.p03 import access
from support.p06 import (
    ENVIRONMENT,
    OWNER,
    RECEIVER,
    TASK,
    PerRequestAsyncHttpClient,
    SyntheticTaskKeyResolver,
    issue_run_credential,
    register_workspace_components,
    run_binding,
    task_admission_config,
)
from test_work_state_guards import control_case, observe, prepared_run, process
from wuji_core.contracts.execution import WorkerAssignment
from wuji_core.http import canonical_json_bytes, create_app, strict_json_loads
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import AccessContext
from wuji_maf_worker.context import ContextLimits, build_context_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TOOL_DEFINITION_REF = "fixture-reader-v1"
PROFILE_REF = "harness.explore.m1.v1"
MODEL_ROUTE = "/internal/v2/model/chat/completions"
TOOL_ROUTE = "/internal/v2/tool-calls"


def maf_runtime_type():
    """Return the production runtime type without substituting a test runtime."""

    try:
        module = import_module("wuji_maf_worker.runtime")
    except ModuleNotFoundError as error:
        raise AssertionError("P07 M1 MafRuntime production assembly is absent") from error
    runtime_type = getattr(module, "MafRuntime", None)
    if runtime_type is None:
        raise AssertionError("P07 M1 MafRuntime production assembly is absent")
    return runtime_type


def _safe_headers(headers) -> dict[str, str]:
    values = {key.lower(): value for key, value in headers.items()}
    if "authorization" in values:
        values["authorization"] = "Bearer [REDACTED TEST CREDENTIAL]"
    return values


def _append_exchange(path: Path, exchange: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(exchange, sort_keys=True) + "\n")


def _encoded_exchange(
    exchange: "HttpExchange", *, url: str
) -> dict[str, object]:
    return {
        "request": {
            "method": exchange.method,
            "url": url,
            "headers": exchange.request_headers,
            "body_base64": base64.b64encode(exchange.request_body).decode("ascii"),
        },
        "response": {
            "status_code": exchange.status_code,
            "headers": exchange.response_headers,
            "body_base64": base64.b64encode(exchange.response_body).decode("ascii"),
        },
    }


@dataclass(frozen=True, slots=True)
class HttpExchange:
    method: str
    path: str
    request_headers: dict[str, str]
    request_body: bytes
    status_code: int
    response_headers: dict[str, str]
    response_body: bytes


class LocalAsgiServer:
    """Serve the real platform ASGI app over an ephemeral localhost socket."""

    def __init__(self, app, audit_path: Path) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:
                self._handle()

            def do_POST(self) -> None:
                self._handle()

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                request_body = self.rfile.read(length)
                split = urlsplit(self.path)
                request_sent = False
                response_complete = asyncio.Event()
                response_status = 500
                response_headers: list[tuple[bytes, bytes]] = []
                response_chunks: list[bytes] = []

                async def receive():
                    nonlocal request_sent
                    if not request_sent:
                        request_sent = True
                        return {
                            "type": "http.request",
                            "body": request_body,
                            "more_body": False,
                        }
                    await response_complete.wait()
                    return {"type": "http.disconnect"}

                async def send(message):
                    nonlocal response_status, response_headers
                    if message["type"] == "http.response.start":
                        response_status = message["status"]
                        response_headers = list(message.get("headers", []))
                    elif message["type"] == "http.response.body":
                        response_chunks.append(message.get("body", b""))
                        if not message.get("more_body", False):
                            response_complete.set()

                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.3"},
                    "http_version": "1.1",
                    "method": self.command,
                    "scheme": "http",
                    "path": split.path,
                    "raw_path": split.path.encode("ascii"),
                    "query_string": split.query.encode("ascii"),
                    "root_path": "",
                    "headers": [
                        (key.lower().encode("latin-1"), value.encode("latin-1"))
                        for key, value in self.headers.items()
                    ],
                    "client": self.client_address,
                    "server": self.server.server_address,
                }
                asyncio.run(owner.app(scope, receive, send))
                response_body = b"".join(response_chunks)
                normalized_headers = {
                    key.decode("latin-1").lower(): value.decode("latin-1")
                    for key, value in response_headers
                    if key.lower() not in {b"content-length", b"connection"}
                }
                normalized_headers.update(
                    {"content-length": str(len(response_body)), "connection": "close"}
                )
                self.send_response_only(response_status)
                for key, value in normalized_headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body)
                self.wfile.flush()
                self.close_connection = True
                exchange = HttpExchange(
                    self.command,
                    self.path,
                    _safe_headers(self.headers),
                    request_body,
                    response_status,
                    normalized_headers,
                    response_body,
                )
                with owner.exchange_lock:
                    owner.exchanges.append(exchange)
                _append_exchange(
                    owner.audit_path,
                    _encoded_exchange(exchange, url=owner.url + self.path),
                )

            def log_message(self, *_args) -> None:
                return None

        self.app = app
        self.audit_path = audit_path
        self.exchanges: list[HttpExchange] = []
        self.exchange_lock = Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _sse(*chunks: dict[str, object]) -> bytes:
    return b"".join(
        b"data: " + canonical_json_bytes(chunk) + b"\n\n" for chunk in chunks
    ) + b"data: [DONE]\n\n"


def _receipt_from_tool_content(value):
    if isinstance(value, dict):
        if "evidence_receipt" in value and "tool_call_id" in value:
            return value
        for item in value.values():
            found = _receipt_from_tool_content(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _receipt_from_tool_content(item)
            if found is not None:
                return found
    elif isinstance(value, str):
        try:
            parsed = strict_json_loads(value)
        except ValueError:
            return None
        return _receipt_from_tool_content(parsed)
    return None


class NativeSseModel:
    """Native Chat Completions SSE peer deriving its claim from a real receipt."""

    def __init__(self, audit_path: Path) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:
                with owner.exchange_lock:
                    ordinal = len(owner.exchanges)
                    length = int(self.headers.get("Content-Length", "0"))
                    request_body = self.rfile.read(length)
                    try:
                        payload = strict_json_loads(request_body)
                        if (
                            self.path != "/v1/chat/completions"
                            or payload["stream"] is not True
                        ):
                            raise ValueError(
                                "M1 requires native streaming chat completions"
                            )
                        if ordinal == 0:
                            owner.first_request_started.set()
                            owner.release_first_response.wait(timeout=10)
                            response_body = owner._tool_call_stream()
                        elif ordinal == 1:
                            receipt = _receipt_from_tool_content(payload["messages"])
                            if receipt is None:
                                raise ValueError(
                                    "second request lacks the actual tool receipt"
                                )
                            evidence = receipt.get("evidence_receipt")
                            observation_ref = (
                                evidence.get("observation_ref")
                                if isinstance(evidence, dict)
                                else None
                            )
                            if not observation_ref:
                                raise ValueError(
                                    "tool receipt lacks a persisted Observation"
                                )
                            owner.received_tool_receipt = receipt
                            response_body = owner._final_stream(observation_ref)
                        else:
                            raise ValueError(
                                "synthetic model received an unbounded request"
                            )
                        status = 200
                        response_headers = {
                            "content-type": "text/event-stream",
                            "cache-control": "no-cache",
                            "content-length": str(len(response_body)),
                            "connection": "close",
                        }
                    except (KeyError, TypeError, ValueError) as error:
                        status = 422
                        response_body = canonical_json_bytes(
                            {
                                "error": {
                                    "message": str(error),
                                    "type": "invalid_request_error",
                                }
                            }
                        )
                        response_headers = {
                            "content-type": "application/json",
                            "content-length": str(len(response_body)),
                            "connection": "close",
                        }
                    self.send_response_only(status)
                    for key, value in response_headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(response_body)
                    self.wfile.flush()
                    self.close_connection = True
                    exchange = HttpExchange(
                        self.command,
                        self.path,
                        _safe_headers(self.headers),
                        request_body,
                        status,
                        response_headers,
                        response_body,
                    )
                    owner.exchanges.append(exchange)
                    _append_exchange(
                        owner.audit_path,
                        _encoded_exchange(exchange, url=owner.url),
                    )

            def log_message(self, *_args) -> None:
                return None

        self.audit_path = audit_path
        self.exchanges: list[HttpExchange] = []
        self.exchange_lock = Lock()
        self.first_request_started = Event()
        self.release_first_response = Event()
        self.received_tool_receipt: dict[str, object] | None = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = PerRequestAsyncHttpClient()

    @staticmethod
    def _tool_call_stream() -> bytes:
        return _sse(
            {
                "id": "chatcmpl-m1-tool",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "fixture-upstream-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-m1-read",
                                    "type": "function",
                                    "function": {
                                        "name": "read_fixture",
                                        "arguments": '{"path":"version.txt"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl-m1-tool",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "fixture-upstream-model",
                "choices": [
                    {"index": 0, "delta": {}, "finish_reason": "tool_calls"}
                ],
            },
        )

    @staticmethod
    def _final_stream(observation_ref: dict[str, str]) -> bytes:
        payload = {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [
                {
                    "client_ref": "m1-workspace-evidence",
                    "kind": "observation-summary",
                    "assertion_role": "candidate_fact",
                    "text": "The workspace read produced an accepted evidence receipt.",
                    "structured_assertion": {"workspace_read_evidence": "accepted"},
                    "basis_refs": [observation_ref],
                    "limitations": ["single isolated workspace read"],
                }
            ],
            "intent_proposals": [],
            "limitations": ["synthetic localhost protocol endpoint"],
        }
        return _sse(
            {
                "id": "chatcmpl-m1-final",
                "object": "chat.completion.chunk",
                "created": 2,
                "model": "fixture-upstream-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": canonical_json_bytes(payload).decode("utf-8"),
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl-m1-final",
                "object": "chat.completion.chunk",
                "created": 2,
                "model": "fixture-upstream-model",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
        )

    def close(self) -> None:
        self.release_first_response.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _actual_lock_digest() -> str:
    return sha256(
        (REPOSITORY_ROOT / "packages/maf-worker/uv.lock").read_bytes()
    ).hexdigest()


def _with_runtime_lock(config, lock_digest: str):
    return config.model_copy(
        update={
            "runtime": config.runtime.model_copy(
                update={"lock_digest": lock_digest}
            )
        }
    )


def _install_profile(control, profile) -> None:
    with control.env.migration_connection() as connection:
        definition_json = connection.execute(
            "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
        ).fetchone()[0]
        definition = strict_json_loads(definition_json)
        definition["lock_digest"] = profile.lock_digest
        definition["worker_profiles"] = {"explore": profile.snapshot()}
        raw = canonical_json_bytes(definition).decode("utf-8")
        connection.execute(
            "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
            (raw, sha256(raw.encode("utf-8")).hexdigest(), TASK),
        )


@contextmanager
def m1_case(environment, tmp_path: Path, audit_directory: Path):
    """Compose actual MAF, Gates, P03/P04 stores, and isolated PostgreSQL."""

    factory_module = import_module("wuji_maf_worker.factory")
    runtime_module = import_module("wuji_maf_worker.runtime")
    host_module = import_module("wuji_core.worker_host")
    registry_module = import_module("wuji_core.admission.registry")
    ledger_module = import_module("wuji_core.admission.ledger")
    model_module = import_module("wuji_core.admission.models")
    tool_module = import_module("wuji_core.admission.tools")
    model_http = import_module("wuji_core.http.model_gate")
    tool_http = import_module("wuji_core.http.tool_gate")
    evidence_http = import_module("wuji_core.http.evidence")
    records_http = import_module("wuji_core.http.records")

    lock_digest = _actual_lock_digest()
    profile = factory_module.HarnessProfile(
        ref=PROFILE_REF,
        revision="1",
        work_kind="explore",
        instructions=(
            "Read the registered workspace fixture once. Return one candidate Claim "
            "based only on the resulting evidence receipt."
        ),
        tool_definition_refs=(TOOL_DEFINITION_REF,),
        lock_digest=lock_digest,
        max_context_records=128,
        max_context_bytes=65_536,
        max_output_tokens=2_048,
    )
    credential = issue_run_credential(audit_directory)
    upstream = NativeSseModel(audit_directory / "model-upstream-http.jsonl")
    key_resolver = SyntheticTaskKeyResolver()
    gate_server = None
    try:
        with control_case(environment, tmp_path, audit_directory) as control:
            _install_profile(control, profile)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            expected_output = b"fixture-version=17\n"
            (workspace / "version.txt").write_bytes(expected_output)
            receipt_root = tmp_path / "receiver-inbox"
            task_config = _with_runtime_lock(
                task_admission_config(
                    registry_module,
                    gateway_url=upstream.url,
                    max_model_requests=4,
                    max_tool_calls=2,
                    max_total_output_bytes=65_536,
                    allowed_tool_refs=[TOOL_DEFINITION_REF],
                ),
                lock_digest,
            )
            with environment.migration_connection() as connection:
                connection.execute(
                    "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_settle,can_model_output,clearance) VALUES(%s,%s,%s,%s,true,true,true,true,1)",
                    (*OWNER, credential.principal.subject),
                )
                connection.execute(
                    "INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,can_settle) VALUES(%s,%s,%s,'run-fixture',%s,'agent-fixture',true)",
                    (*OWNER, credential.principal.subject),
                )
                connection.execute(
                    "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES('model:fixture-model-v1','model',NULL,2,'fixture-capacity-v1')"
                )
                connection.execute(
                    "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,'model:fixture-model-v1')",
                    OWNER,
                )
                register_workspace_components(registry_module, connection)
                registry_module.register_task_config(
                    connection, owner=OWNER, config=task_config
                )
            prepared_run(control)
            observe(control, "started", process=process())
            with environment.migration_connection() as connection:
                registry_module.bind_run_credential(
                    connection,
                    binding=run_binding(
                        registry_module,
                        credential,
                        purposes=["model_request", "tool_request"],
                        allowed_tool_refs=[TOOL_DEFINITION_REF],
                    ),
                )

            host_access = AccessContext(
                credential.principal, "m1-host-composition"
            )
            registry = registry_module.AdmissionRegistry(control.uow)
            ledger = ledger_module.AdmissionLedger(control.uow)
            tool_admission = tool_module.ToolAdmission(
                control.uow, registry=registry, ledger=ledger
            )
            executor = tool_module.WorkspaceReadExecutor(
                root=workspace,
                receipt_root=receipt_root,
                admission=tool_admission,
                receiver_id=RECEIVER,
                environment_ref=ENVIRONMENT,
            )
            evidence = import_module("wuji_core.evidence.observations").EvidenceService(
                control.uow, control.store
            )
            tool_gate = tool_module.ToolGate(
                tool_admission,
                registry=registry,
                ledger=ledger,
                artifacts=control.store,
                evidence=evidence,
                executors={"workspace-reader-fixture": executor},
                collector_accesses={
                    "workspace-reader-fixture": access(
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
                tool_capabilities=tool_module.ToolCapabilityResolver(tool_gate),
            )
            app = create_app(
                token_verifier=credential.verifier,
                routers=[
                    model_http.create_model_router(model_gate),
                    tool_http.create_tool_router(tool_gate),
                    evidence_http.create_evidence_router(evidence),
                    records_http.create_records_router(control.view),
                ],
            )
            gate_server = LocalAsgiServer(
                app, audit_directory / "platform-gate-http.jsonl"
            )
            snapshot = SnapshotRepository(control.uow).create(
                TASK, host_access
            )
            context = build_context_bundle(
                [],
                snapshot.refs,
                snapshot_id=snapshot.snapshot_id,
                limits=ContextLimits(max_records=128, max_bytes=65_536),
            )
            assignment = WorkerAssignment.model_validate(
                {
                    "schema_version": "wuji.assignment.v2",
                    "operation_id": "start-run-fixture",
                    "identity": {
                        "tenant_id": OWNER[0],
                        "project_id": OWNER[1],
                        "task_id": TASK,
                        "work_item_id": "work-fixture",
                        "agent_run_id": "run-fixture",
                        "execution_epoch": "1",
                        "run_epoch": "1",
                        "runtime_attempt": "1",
                        "receiver_id": RECEIVER,
                    },
                    "work_kind": "explore",
                    "snapshot_id": snapshot.snapshot_id,
                    "profile_refs": [PROFILE_REF],
                    "session_manifest_ref": None,
                    "tool_definition_refs": [TOOL_DEFINITION_REF],
                    "limits": task_config.runtime.limits.model_dump(mode="json"),
                    "resume_reason": None,
                }
            )
            host = host_module.PlatformWorkerHost(
                uow=control.uow,
                registry=registry,
                access=host_access,
                artifacts=control.store,
                committer=control.committer,
                profiles=(profile.snapshot(),),
                lock_digest=lock_digest,
            )

            def new_runtime():
                return runtime_module.MafRuntime(
                    host=host,
                    context=context,
                    run_credential=credential.token,
                    model_gate_url=gate_server.url + "/internal/v2/model",
                    tool_gate_url=gate_server.url + TOOL_ROUTE,
                )

            yield SimpleNamespace(**locals())
    finally:
        if gate_server is not None:
            gate_server.close()
        upstream.close()


def gate_headers(case, request_id: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + case.credential.token,
        "Content-Type": "application/json",
        "X-Wuji-Request-ID": request_id,
    }


def table_count(case, table: str) -> int:
    relations = {
        "assessment": "assessment",
        "claim_revision": "claim_revision",
        "model_attempt": "model_call",
        "observation": "observation",
        "result_receipt": "result_receipt",
        "result_submission": "result_submission",
        "tool_attempt": "tool_attempt",
    }
    if table not in relations:
        raise ValueError("unsupported M1 table count")
    with case.environment.migration_connection() as connection:
        return connection.execute(
            f"SELECT count(*) FROM vnext.{relations[table]}"
        ).fetchone()[0]


def recorded_requests(case, path: str) -> list[dict[str, object]]:
    return [
        strict_json_loads(exchange.request_body)
        for exchange in case.gate_server.exchanges
        if exchange.path == path
    ]
