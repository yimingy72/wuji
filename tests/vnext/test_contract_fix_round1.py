from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest
import psycopg
from fastapi import APIRouter
from psycopg import sql
from pydantic import ValidationError

from wuji_core.contracts import generated
from wuji_core.contracts.knowledge import ClaimProposal
from wuji_core.http.app import create_app
from wuji_core.http.json_boundary import (
    DEFAULT_JSON_LIMITS,
    InvalidJsonDocument,
    canonical_json_bytes,
    JsonBoundaryLimits,
    StrictJsonMiddleware,
    strict_json_loads,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _p01_roundtrip_http() -> list[dict[str, object]]:
    record = json.loads(
        (REPOSITORY_ROOT / "docs" / "vnext" / "capability-record.json").read_text(
            encoding="utf-8"
        )
    )
    return record["raw_sdk_and_http"]["cases"]["roundtrip"]["http"]


def _json_scope() -> dict[str, object]:
    return {
        "type": "http",
        "method": "POST",
        "path": "/api/v2/test/claim",
        "headers": [(b"content-type", b"application/json")],
        "state": {},
    }


async def _drive_json_boundary(messages: list[dict[str, object]]):
    downstream_calls: list[str] = []
    sent: list[dict[str, object]] = []
    queue = iter(messages)

    async def receive():
        await asyncio.sleep(0)
        return next(queue)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        downstream_calls.append("called")
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = StrictJsonMiddleware(downstream)
    await middleware(_json_scope(), receive, send)
    return downstream_calls, sent


@pytest.mark.parametrize("resource_type", ["task", "work_item", "approval"])
def test_command_receipt_identifies_its_actual_resource(resource_type: str) -> None:
    receipt = generated.CommandReceipt.model_validate(
        {
            "command_id": "command-1",
            "disposition": "accepted",
            "resource_ref": {
                "entity_type": resource_type,
                "id": f"{resource_type}-1",
                "revision": "1",
            },
            "resource_version": "1",
            "request_id": "request-1",
        }
    )

    assert receipt.resource_ref.entity_type.value == resource_type


@pytest.mark.parametrize("resource_type", ["task", "approval"])
def test_command_resources_do_not_expand_canonical_knowledge_refs(
    resource_type: str,
) -> None:
    with pytest.raises(ValidationError):
        generated.KnowledgeRef.model_validate(
            {"entity_type": resource_type, "id": "not-knowledge", "revision": "1"}
        )


def test_saved_p01_tool_call_response_matches_chat_completions_contract() -> None:
    first_exchange = _p01_roundtrip_http()[0]

    response = generated.ChatCompletionResponse.model_validate(
        strict_json_loads(first_exchange["response_body"])
    )

    assert response.created == 1
    assert response.usage.prompt_tokens == 10
    assert response.choices[0].message.content is None
    assert response.choices[0].message.tool_calls[0].function.name == "read_record"


def test_saved_p01_continuation_request_matches_chat_completions_contract() -> None:
    second_exchange = _p01_roundtrip_http()[1]

    request = generated.ChatCompletionRequest.model_validate(
        strict_json_loads(second_exchange["request_body"])
    )

    assistant = request.messages[2]
    assert assistant.role.value == "assistant"
    assert assistant.content is None
    assert assistant.tool_calls[0].id == "call-p01-read"
    assert request.messages[3].tool_call_id.root == "call-p01-read"


def test_unknown_schema_version_has_a_distinct_asgi_error(
    api_client, test_tokens
) -> None:
    response = api_client.post(
        "/api/v2/test/task-command",
        json={
            "schema_version": "wuji.api.v3",
            "command": "start",
            "expected_version": "1",
            "reason": "fixture request",
        },
        headers={"Authorization": f"Bearer {test_tokens.agent}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA_VERSION"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "wuji.api.v3" not in response.text


def test_unknown_input_key_is_redacted_from_public_error_location(
    api_client, test_tokens
) -> None:
    secret_key = "SENSITIVE_CANDIDATE_SECRET"
    response = api_client.post(
        "/api/v2/test/claim",
        json={
            "client_ref": "claim-1",
            "kind": "hypothesis",
            "assertion_role": "hypothesis",
            "text": "candidate",
            "basis_refs": [],
            "limitations": [],
            secret_key: "ignored",
        },
        headers={"Authorization": f"Bearer {test_tokens.agent}"},
    )

    assert response.status_code == 422
    assert secret_key not in response.text
    assert response.json()["details"]["errors"][0]["loc"] == ["body", "<field>"]


def test_public_validation_diagnostics_are_bounded(api_client, test_tokens) -> None:
    extras = {f"unknown_{index}": index for index in range(20)}
    response = api_client.post(
        "/api/v2/test/claim",
        json={
            "client_ref": "claim-1",
            "kind": "hypothesis",
            "assertion_role": "hypothesis",
            "text": "candidate",
            "basis_refs": [],
            "limitations": [],
            **extras,
        },
        headers={"Authorization": f"Bearer {test_tokens.agent}"},
    )

    assert response.status_code == 422
    assert len(response.json()["details"]["errors"]) == 16
    assert response.json()["details"]["truncated"] is True
    assert all(
        error["loc"] == ["body", "<field>"]
        for error in response.json()["details"]["errors"]
    )
    assert all(key not in response.text for key in extras)


def test_recorded_database_wraps_real_transaction_cursor_and_iteration(db_conn) -> None:
    with db_conn.transaction():
        with db_conn.cursor() as cursor:
            cursor.execute("CREATE TEMP TABLE p02_audit(value integer NOT NULL)")
            cursor.execute("INSERT INTO p02_audit(value) VALUES (%s), (%s)", (2, 1))
            cursor.execute("SELECT count(*) FROM p02_audit")
            assert cursor.fetchone() == (2,)
            cursor.execute("SELECT value FROM p02_audit ORDER BY value")
            assert list(cursor) == [(1,), (2,)]

    events = [
        json.loads(line)
        for line in db_conn.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    operations = [event["operation"] for event in events]
    assert operations.count("cursor_execute") == 4
    assert "fetchone" in operations
    assert operations.count("iteration_row") == 2
    assert "iteration_complete" in operations
    assert "transaction_commit" in operations


def test_recorded_database_logs_execute_error_and_real_rollback(db_conn) -> None:
    with pytest.raises(psycopg.errors.DivisionByZero):
        with db_conn.transaction():
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT 1 / 0")

    assert db_conn.execute("SELECT 1").fetchone() == (1,)
    events = [
        json.loads(line)
        for line in db_conn.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event["operation"] == "cursor_execute_error"
        and event["response"]["sqlstate"] == "22012"
        for event in events
    )
    assert any(event["operation"] == "transaction_rollback" for event in events)


def test_database_environment_exposes_migration_and_second_app_connections(
    db_environment,
) -> None:
    with db_environment.migration_connection() as migration:
        assert migration.execute("SELECT current_user").fetchone() == (
            db_environment.migration_role,
        )
        migration.execute("CREATE TABLE vnext.p02_shared(value integer NOT NULL)")
        migration.execute("INSERT INTO vnext.p02_shared(value) VALUES (17)")
        migration.execute(
            sql.SQL("GRANT SELECT ON vnext.p02_shared TO {}").format(
                sql.Identifier(db_environment.application_role)
            )
        )

    with db_environment.additional_app_connection() as second_app:
        identity = second_app.execute(
            "SELECT current_user, pg_backend_pid()"
        ).fetchone()
        assert identity[0] == db_environment.application_role
        assert second_app.execute("SELECT value FROM vnext.p02_shared").fetchone() == (
            17,
        )

    events = [
        json.loads(line)
        for line in db_environment.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(event["operation"] == "migration_connect" for event in events)
    assert any(event["operation"] == "additional_app_connect" for event in events)


def test_chunked_json_body_is_rejected_at_the_configured_byte_bound() -> None:
    messages = [
        {"type": "http.request", "body": b"{" + b" " * 700_000, "more_body": True},
        {"type": "http.request", "body": b" " * 348_576 + b"}", "more_body": False},
    ]

    downstream, sent = asyncio.run(_drive_json_boundary(messages))

    assert downstream == []
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 422
    )


def test_json_boundary_terminates_when_client_disconnects_mid_body() -> None:
    async def scenario() -> bool:
        try:
            await asyncio.wait_for(
                _drive_json_boundary(
                    [
                        {
                            "type": "http.request",
                            "body": b'{"partial":',
                            "more_body": True,
                        },
                        {"type": "http.disconnect"},
                    ]
                ),
                timeout=0.05,
            )
        except TimeoutError:
            return False
        return True

    assert asyncio.run(scenario()) is True


def test_large_integer_parser_failure_returns_safe_asgi_error(
    api_client, test_tokens
) -> None:
    body = (
        b'{"client_ref":"c1","kind":"hypothesis","assertion_role":"hypothesis",'
        b'"text":"candidate","basis_refs":[],"limitations":[],"structured_assertion":'
        b'{"n":' + b"9" * 4301 + b"}}"
    )

    response = api_client.post(
        "/api/v2/test/claim",
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_json_nesting_beyond_configured_depth_is_rejected(
    api_client, test_tokens
) -> None:
    nested = "0"
    for _ in range(65):
        nested = '{"child":' + nested + "}"
    body = (
        '{"client_ref":"c1","kind":"hypothesis","assertion_role":"hypothesis",'
        '"text":"candidate","basis_refs":[],"limitations":[],"structured_assertion":'
        + nested
        + "}"
    ).encode()

    response = api_client.post(
        "/api/v2/test/claim",
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA"


def test_json_body_read_deadline_returns_a_safe_error() -> None:
    downstream: list[str] = []
    sent: list[dict[str, object]] = []

    async def receive():
        await asyncio.sleep(0.05)
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        downstream.append("called")

    middleware = StrictJsonMiddleware(
        app, limits=JsonBoundaryLimits(read_timeout_seconds=0.01)
    )
    asyncio.run(middleware(_json_scope(), receive, send))

    assert downstream == []
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 422
    )


def test_strict_json_boundary_replays_the_original_body_bytes() -> None:
    original = b'{ "message": " value ", "items": [2, 1] }'
    received: list[dict[str, object]] = []
    sent: list[dict[str, object]] = []

    async def receive():
        await asyncio.sleep(0)
        return {"type": "http.request", "body": original, "more_body": False}

    async def send(message):
        sent.append(message)

    async def app(scope, replay, send):
        received.append(await replay())
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    asyncio.run(StrictJsonMiddleware(app)(_json_scope(), receive, send))

    assert received == [{"type": "http.request", "body": original, "more_body": False}]
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 204
    )


def test_decimal_parser_preserves_finite_exponent_and_integer_types() -> None:
    parsed = strict_json_loads(b'{"large":1e400,"count":17}')

    assert parsed["large"] == Decimal("1e400")
    assert parsed["large"].is_finite()
    assert type(parsed["count"]) is int


def test_canonical_json_keeps_distinct_high_precision_numbers() -> None:
    first = canonical_json_bytes(b'{"n":1.0000000000000001}')
    second = canonical_json_bytes(b'{"n":1.0}')
    third = canonical_json_bytes(b'{"n":1.0000000000000002}')

    assert first == b'{"n":1.0000000000000001}'
    assert len({first, second, third}) == 3


@pytest.mark.parametrize("number", ["1e400", "1.0000000000000001"])
def test_decimal_number_survives_actual_asgi_and_pydantic_path(
    api_client, test_tokens, number: str
) -> None:
    body = (
        '{"client_ref":"c1","kind":"hypothesis","assertion_role":"hypothesis",'
        '"text":"candidate","basis_refs":[],"limitations":[],"structured_assertion":'
        f'{{"n":{number}}}'
        "}"
    ).encode()

    response = api_client.post(
        "/api/v2/test/claim",
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    parsed = strict_json_loads(response.content)
    assert parsed["structured_assertion"]["n"] == Decimal(number)
    assert f'"n":"{number}"'.encode() not in response.content
    assert b'"n":null' not in response.content


@pytest.mark.parametrize("body", [b'{"n":1e10001}', b'{"n":0e10001}'])
def test_json_safety_limits_are_explicit_and_finite(body: bytes) -> None:
    assert DEFAULT_JSON_LIMITS == JsonBoundaryLimits(
        max_body_bytes=1_048_576,
        read_timeout_seconds=5.0,
        max_nesting_depth=64,
        max_number_characters=256,
        max_decimal_adjusted_exponent=10_000,
    )
    with pytest.raises(InvalidJsonDocument, match="decimal exponent exceeds"):
        strict_json_loads(body)


def test_decimal_encoder_applies_the_configured_exponent_limit() -> None:
    with pytest.raises(InvalidJsonDocument, match="decimal exponent exceeds"):
        canonical_json_bytes({"n": Decimal("1e10001")})
    with pytest.raises(InvalidJsonDocument, match="integer token exceeds"):
        canonical_json_bytes({"n": 10**4301})


def test_create_app_rejects_routes_that_bypass_strict_request_extension(
    test_tokens,
) -> None:
    router = APIRouter()

    @router.post("/api/v2/test/plain")
    async def plain_route(payload: ClaimProposal):
        return payload

    from wuji_core.http.auth import TokenVerifier

    verifier = TokenVerifier(
        public_key_pem=test_tokens.public_key_pem,
        issuer=test_tokens.issuer,
        audience=test_tokens.audience,
    )
    with pytest.raises(ValueError, match="must use VNextAPIRouter"):
        create_app(token_verifier=verifier, routers=[router])


@pytest.mark.parametrize(
    "path", ["/api/v2/test/claim-default", "/api/v2/test/claim-model-default"]
)
def test_ordinary_endpoint_fails_before_lossy_decimal_response_encoding(
    api_client, test_tokens, path: str
) -> None:
    body = (
        b'{"client_ref":"c1","kind":"hypothesis","assertion_role":"hypothesis",'
        b'"text":"candidate","basis_refs":[],"limitations":[],"structured_assertion":'
        b'{"n":1.0000000000000001}}'
    )

    response = api_client.post(
        path,
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 503
    assert response.json()["code"] == "CAPABILITY_UNAVAILABLE"
    assert "1.0000000000000001" not in response.text
    assert "1.0" not in response.text
