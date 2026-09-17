"""P17-A: a target tool reaches only the exact asset the Task approved.

The platform decides scope before a permit exists; Kali re-checks the permit's
resource key, performs one read-only HTTP exchange, and the capture layer seals
the raw document. Nothing here touches a real target: the "range" is a local
HTTP server inside the test process.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from uuid import uuid4

import pytest

from support.p03 import access as p03_access
from support.p06 import (
    ENVIRONMENT,
    OWNER,
    RECEIVER,
    SESSION_LINEAGE,
    TASK,
    TENANT,
    fresh_ledger,
    issue_run_credential,
    production,
    run_binding,
    task_admission_config,
    tool_headers,
)
from test_knowledge_admission import IDENTITY
from test_work_state_guards import control_case, observe, prepared_run, process
from wuji_core.admission import target_scope
from wuji_core.admission.common import digest
from wuji_core.admission.tools import HttpTargetExecutor
from wuji_core.contracts.admission import ToolCallRequest
from wuji_core.http import canonical_json_bytes, create_app, strict_json_loads
from wuji_core.persistence.uow import AccessContext, DomainError


PAGE = b"<html><body>wuji-range-marker</body></html>"
HTTP_TOOL = "fixture-http-target-v1"
HTTP_EXECUTOR = "http-target-fixture"
INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["url", "method"],
    "properties": {
        "url": {"type": "string", "minLength": 1, "maxLength": 4096},
        "method": {"type": "string", "enum": ["GET", "HEAD", "OPTIONS"]},
    },
}


class _Range(BaseHTTPRequestHandler):
    """A tiny local 'range': one page, one redirect, one oversized body."""

    protocol_version = "HTTP/1.1"
    requests: list[tuple[str, str]] = []
    large_bytes = 8192

    def log_message(self, *args):  # pragma: no cover - quiet test output
        return

    def _record(self):
        type(self).requests.append((self.command, self.path))

    def _body(self, payload: bytes, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def do_GET(self):
        self._record()
        if self.path == "/redirect":
            self._body(b"", status=302, headers={"Location": "/page"})
        elif self.path == "/large":
            self._body(b"x" * type(self).large_bytes)
        else:
            self._body(PAGE)

    def do_HEAD(self):
        self._record()
        self._body(b"", status=200)

    def do_OPTIONS(self):
        self._record()
        self._body(b"", status=204, headers={"Allow": "GET, HEAD, OPTIONS"})

    def do_POST(self):
        self._record()
        self._body(b"written", status=201)


@contextmanager
def target_range():
    _Range.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Range)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def http_request(provider_call_id, *, url, method="GET"):
    return {
        "session_lineage": SESSION_LINEAGE,
        "message_id": "message-p17-tool-1",
        "provider_call_id": provider_call_id,
        "tool_definition_ref": HTTP_TOOL,
        "arguments": {"url": url, "method": method},
        "sdk_content_id": None,
        "sdk_approval_id": None,
        "approval_ref": None,
    }


def scope_entry(port, host="127.0.0.1", protocol="http"):
    return {"host": host, "protocol": protocol, "port": port}


@contextmanager
def http_case(environment, tmp_path, audit_directory, *, port, max_total_output_bytes=8192):
    """The production tool Gate with one registered target tool."""

    registry_module = production("admission.registry")
    ledger_module = production("admission.ledger")
    tool_module = production("admission.tools")
    tool_http = production("http.tool_gate")
    evidence_http = production("http.evidence")
    credential = issue_run_credential(audit_directory)
    receipt_root = tmp_path / "receiver-inbox"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with control_case(environment, tmp_path, audit_directory) as control:
        with environment.migration_connection() as connection:
            definition = strict_json_loads(
                connection.execute(
                    "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
                ).fetchone()[0]
            )
            definition["authorization_scope"] = [
                *(definition.get("authorization_scope") or []),
                scope_entry(port),
            ]
            raw = canonical_json_bytes(definition).decode()
            connection.execute(
                "UPDATE vnext.task SET definition_json=%s,definition_digest=%s"
                " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (raw, sha256(raw.encode()).hexdigest(), *OWNER),
            )
            connection.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,"
                "can_read,clearance) VALUES(%s,%s,%s,%s,true,1)",
                (*OWNER, credential.principal.subject),
            )
            registry_module.register_tool_definition(
                connection,
                tenant_id=TENANT,
                definition=registry_module.ToolDefinition.model_validate(
                    {
                        "ref": HTTP_TOOL,
                        "revision": "1",
                        "published_at": "2026-09-13T00:00:00Z",
                        "name": "read_target_page",
                        "input_schema": INPUT_SCHEMA,
                        "executor_ref": HTTP_EXECUTOR,
                        "approval_required": False,
                        "allowed_target_kinds": ["http_target"],
                    }
                ),
            )
            registry_module.register_executor(
                connection,
                owner=OWNER,
                executor=registry_module.ExecutorRegistration.model_validate(
                    {
                        "ref": HTTP_EXECUTOR,
                        "receiver_id": RECEIVER,
                        "environment_ref": ENVIRONMENT,
                        "collector_subject": "collector-fixture",
                        "evidence_origin": "fixture_capture",
                        "capture_layer": "fixture_http_bytes",
                        "allowed_tool_refs": [HTTP_TOOL],
                    }
                ),
            )
            connection.execute(
                "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,"
                "published_ref) VALUES('model:fixture-model-v1','model',NULL,2,"
                "'fixture-capacity-v1')"
            )
            connection.execute(
                "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key)"
                " VALUES(%s,%s,%s,'model:fixture-model-v1')",
                OWNER,
            )
            registry_module.register_task_config(
                connection,
                owner=OWNER,
                config=task_admission_config(
                    registry_module,
                    gateway_url="http://127.0.0.1:9/v1/chat/completions",
                    max_total_output_bytes=max_total_output_bytes,
                    allowed_tool_refs=[HTTP_TOOL],
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
                    allowed_tool_refs=[HTTP_TOOL],
                ),
            )
        registry = registry_module.AdmissionRegistry(control.uow)
        ledger = ledger_module.AdmissionLedger(control.uow)
        admission = tool_module.ToolAdmission(control.uow, registry=registry, ledger=ledger)
        executor = HttpTargetExecutor(
            receipt_root=receipt_root,
            admission=admission,
            receiver_id=RECEIVER,
            environment_ref=ENVIRONMENT,
            timeout_seconds=10,
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
            executors={(*OWNER, HTTP_EXECUTOR): executor},
            collector_accesses={
                (*OWNER, HTTP_EXECUTOR): p03_access(
                    "collector-fixture", role="collector"
                )
            },
        )
        yield SimpleNamespace(
            **locals(),
            access=AccessContext(credential.principal, "p17-target-ledger-read"),
        )


def authorize(case, provider_call_id, *, url, method="GET"):
    request = ToolCallRequest.model_validate(
        http_request(provider_call_id, url=url, method=method)
    )
    return case.admission.authorize(case.access, request)


def attempt_row(case, attempt_id):
    with case.environment.migration_connection() as connection:
        return connection.execute(
            "SELECT status,output_media_type,output,output_completeness,limit_reason"
            " FROM vnext.tool_attempt WHERE tool_attempt_id=%s",
            (attempt_id,),
        ).fetchone()


def test_in_scope_read_only_exchange_is_executed_and_sealed_as_evidence(
    db_environment, tmp_path, audit_directory
):
    with target_range() as port:
        with http_case(db_environment, tmp_path, audit_directory, port=port) as case:
            url = f"http://127.0.0.1:{port}/page"
            permit = authorize(case, "call-target-1", url=url)
            assert permit.resource_keys == (
                f"target:http://127.0.0.1:{port}:read:{IDENTITY['agent_run_id']}",
            )
            result = asyncio.run(case.gate.execute_permit(case.access, permit))
            assert result.status == "complete", result
            row = attempt_row(case, permit.tool_attempt_id)
            assert row[0] == "complete"
            assert row[1] == "application/vnd.wuji.http-exchange+json"
            assert row[3] == "complete" and row[4] is None
            document = strict_json_loads(bytes(row[2]))
            assert document["schema_version"] == "wuji.http-exchange.v1"
            assert document["target"] == f"http://127.0.0.1:{port}"
            assert document["request"]["method"] == "GET"
            assert document["response"]["status"] == 200
            import base64

            assert base64.b64decode(document["response"]["body_base64"]) == PAGE
            assert document["response"]["truncated"] is False
            assert _Range.requests == [("GET", "/page")]
            # The capture layer sealed the exact bytes the executor returned.
            with case.environment.migration_connection() as connection:
                artifact = connection.execute(
                    "SELECT media_type,size_bytes,sha256,state FROM vnext.artifact"
                    " WHERE tool_attempt_id=%s",
                    (permit.tool_attempt_id,),
                ).fetchone()
            assert artifact[0] == "application/vnd.wuji.http-exchange+json"
            assert artifact[1] == len(bytes(row[2]))
            assert artifact[2] == sha256(bytes(row[2])).hexdigest()
            assert artifact[3] == "sealed"


def test_out_of_scope_target_is_refused_before_any_attempt(
    db_environment, tmp_path, audit_directory
):
    with target_range() as port:
        with http_case(db_environment, tmp_path, audit_directory, port=port) as case:
            def attempts():
                with case.environment.migration_connection() as connection:
                    return connection.execute(
                        "SELECT count(*) FROM vnext.tool_attempt WHERE tenant_id=%s"
                        " AND project_id=%s AND task_id=%s",
                        OWNER,
                    ).fetchone()[0]

            before = attempts()
            with pytest.raises(DomainError) as refused:
                authorize(
                    case,
                    "call-target-out-of-scope",
                    url=f"http://127.0.0.1:{port + 1}/page",
                )
            assert refused.value.code == "FORBIDDEN_TARGET"
            assert refused.value.status == 403
            assert attempts() == before, "an unapproved target never allocates an attempt"
            assert _Range.requests == [], "no request may reach an unapproved target"


@pytest.mark.parametrize(
    "url,method",
    [
        ("http://127.0.0.1:{port}/page", "POST"),
        ("ftp://127.0.0.1:{port}/page", "GET"),
        ("http://user:pass@127.0.0.1:{port}/page", "GET"),
        ("http://127.0.0.1:{port}/page\nX-Injected: 1", "GET"),
    ],
)
def test_only_bounded_read_only_target_requests_are_accepted(
    db_environment, tmp_path, audit_directory, url, method
):
    with target_range() as port:
        with http_case(db_environment, tmp_path, audit_directory, port=port) as case:
            with pytest.raises(DomainError) as refused:
                authorize(
                    case,
                    "call-target-invalid",
                    url=url.format(port=port),
                    method=method,
                )
            assert refused.value.code == "INVALID_SCHEMA"
            assert refused.value.status == 422
            assert _Range.requests == []


def test_a_redirect_is_recorded_instead_of_followed(
    db_environment, tmp_path, audit_directory
):
    with target_range() as port:
        with http_case(db_environment, tmp_path, audit_directory, port=port) as case:
            permit = authorize(
                case,
                "call-target-redirect",
                url=f"http://127.0.0.1:{port}/redirect",
            )
            result = asyncio.run(case.gate.execute_permit(case.access, permit))
            assert result.status == "complete"
            document = strict_json_loads(bytes(attempt_row(case, permit.tool_attempt_id)[2]))
            assert document["response"]["status"] == 302
            assert document["response"]["headers"]["location"] == "/page"
            assert _Range.requests == [("GET", "/redirect")], "no redirect is followed"


def test_an_oversized_body_is_truncated_and_marked_partial(
    db_environment, tmp_path, audit_directory
):
    with target_range() as port:
        with http_case(
            db_environment, tmp_path, audit_directory, port=port, max_total_output_bytes=2048
        ) as case:
            permit = authorize(
                case, "call-target-large", url=f"http://127.0.0.1:{port}/large"
            )
            result = asyncio.run(case.gate.execute_permit(case.access, permit))
            row = attempt_row(case, permit.tool_attempt_id)
            assert result.status == "complete"
            assert row[3] == "partial"
            document = strict_json_loads(bytes(row[2]))
            assert document["response"]["truncated"] is True
            assert len(bytes(row[2])) <= 2048


def test_the_executor_refuses_a_permit_that_does_not_match_its_own_key(
    db_environment, tmp_path, audit_directory
):
    with target_range() as port:
        with http_case(db_environment, tmp_path, audit_directory, port=port) as case:
            permit = authorize(case, "call-target-tamper", url=f"http://127.0.0.1:{port}/page")
            tampered = replace(
                permit,
                arguments={"url": f"http://127.0.0.1:{port + 1}/page", "method": "GET"},
            )
            assert digest(tampered.arguments) != permit.arguments_digest
            with pytest.raises(DomainError) as refused:
                case.executor._operate(tampered)
            assert refused.value.code == "FORBIDDEN_TARGET"
            assert _Range.requests == []
