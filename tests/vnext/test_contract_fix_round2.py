from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import APIRouter

from wuji_core.contracts.knowledge import ClaimProposal
from wuji_core.http import JsonBoundaryLimits
from wuji_core.http.app import create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.json_boundary import (
    StrictJsonMiddleware,
    StrictJsonRoute,
    strict_json_loads,
)


def _scope(content_type: bytes | None = None) -> dict[str, object]:
    headers = [] if content_type is None else [(b"content-type", content_type)]
    return {
        "type": "http",
        "method": "POST",
        "path": "/api/v2/test/bounded",
        "headers": headers,
        "state": {},
    }


async def _drive(
    *,
    body: bytes,
    content_type: bytes | None,
    max_body_bytes: int = 7,
) -> tuple[list[bytes], list[dict[str, object]]]:
    delivered = False
    downstream_bodies: list[bytes] = []
    sent: list[dict[str, object]] = []

    async def receive():
        nonlocal delivered
        await asyncio.sleep(0)
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    async def downstream(scope, replay, send):
        message = await replay()
        downstream_bodies.append(message.get("body", b""))
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = StrictJsonMiddleware(
        downstream,
        limits=JsonBoundaryLimits(max_body_bytes=max_body_bytes),
    )
    await middleware(_scope(content_type), receive, send)
    return downstream_bodies, sent


@pytest.mark.parametrize(
    "content_type", [None, b"text/plain", b"application/octet-stream"]
)
def test_nonempty_unsupported_media_is_rejected_before_downstream(
    content_type: bytes | None,
) -> None:
    downstream, sent = asyncio.run(_drive(body=b"{}", content_type=content_type))

    assert downstream == []
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 422
    )
    response_body = next(
        item["body"] for item in sent if item["type"] == "http.response.body"
    )
    assert strict_json_loads(response_body)["message"] == (
        "Nonempty request body requires application/json."
    )


def test_headerless_body_is_still_subject_to_the_byte_limit() -> None:
    downstream, sent = asyncio.run(_drive(body=b'{"n":17}', content_type=None))

    assert downstream == []
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 422
    )


def test_empty_body_without_content_type_replays_to_downstream() -> None:
    downstream, sent = asyncio.run(_drive(body=b"", content_type=None))

    assert downstream == [b""]
    assert (
        next(item["status"] for item in sent if item["type"] == "http.response.start")
        == 204
    )


def test_disconnect_terminates_before_downstream_without_a_fabricated_response() -> (
    None
):
    messages = iter(
        [
            {"type": "http.request", "body": b"partial", "more_body": True},
            {"type": "http.disconnect"},
        ]
    )
    downstream_calls: list[str] = []
    sent: list[dict[str, object]] = []

    async def receive():
        await asyncio.sleep(0)
        return next(messages)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        downstream_calls.append("called")
        await receive()

    middleware = StrictJsonMiddleware(
        downstream, limits=JsonBoundaryLimits(max_body_bytes=7)
    )
    asyncio.run(middleware(_scope(None), receive, send))

    assert downstream_calls == []
    assert sent == []


def test_composition_rejects_strict_route_without_vnext_response_guard(
    api_client, test_tokens
) -> None:
    body = (
        b'{"client_ref":"c1","kind":"hypothesis","assertion_role":"hypothesis",'
        b'"text":"candidate","basis_refs":[],"limitations":[],"structured_assertion":'
        b'{"n":1.0000000000000001}}'
    )
    control = api_client.post(
        "/api/v2/test/claim-default",
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )
    assert control.status_code == 503
    assert control.json()["code"] == "CAPABILITY_UNAVAILABLE"

    alternative = APIRouter(route_class=StrictJsonRoute)

    @alternative.post("/api/v2/test/unguarded")
    async def unguarded(payload: ClaimProposal) -> dict[str, object]:
        return payload.model_dump(mode="python")

    verifier = TokenVerifier(
        public_key_pem=test_tokens.public_key_pem,
        issuer=test_tokens.issuer,
        audience=test_tokens.audience,
    )
    with pytest.raises(ValueError, match="must use VNextAPIRouter"):
        create_app(token_verifier=verifier, routers=[alternative])


def test_force_rollback_records_the_native_normal_exit_rollback(db_conn) -> None:
    before = db_conn.execute("SHOW application_name").fetchone()[0]
    db_conn.commit()

    with db_conn.transaction(force_rollback=True):
        db_conn.execute("SET application_name = 'p02-round2-force-rollback'")
        inside = db_conn.execute("SHOW application_name").fetchone()[0]

    after = db_conn.execute("SHOW application_name").fetchone()[0]
    assert inside == "p02-round2-force-rollback"
    assert after == before

    events = [
        json.loads(line)
        for line in db_conn.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    transaction_enter = next(
        event for event in events if event["operation"] == "transaction_enter"
    )
    assert transaction_enter["force_rollback"] is True
    transaction_exit = next(
        event
        for event in events
        if event["operation"] in {"transaction_commit", "transaction_rollback"}
    )
    assert transaction_exit == {
        "exception": None,
        "force_rollback": True,
        "operation": "transaction_rollback",
        "outcome": "forced_rollback",
        "response": "ok",
    }
