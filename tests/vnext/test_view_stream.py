"""P15 ViewStream: one saved view advances through authorized SSE batches."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from support.p03 import access
from support.p13 import (
    OWNER,
    projection_case,
    revise_claim,
    set_reader_access,
    supported_claim,
    topology,
)
from wuji_core.http import create_app
from wuji_core.http.views import create_view_router
from wuji_core.persistence import schema
from wuji_core.persistence.uow import DomainError


READER = access("reader-fixture", role="reader")
ASSESSOR = access("assessor-fixture", role="assessor")


def _view(case, *, node_limit: int = 300) -> dict:
    response = topology(case, node_limit=node_limit, edge_limit=600)
    assert response.status_code == 200, response.text
    return response.json()


def _step(case, view_id: str, cursor: str | None = None):
    return case.projection.stream_step(READER, view_id, cursor)


def test_the_stream_starts_idle_and_then_advances_the_same_view(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        view = _view(case)

        # Nothing has happened since the snapshot: a bounded step is idle.
        assert _step(case, view["view_id"]) is None

        revise_claim(case, claim, text="revised after the snapshot")
        batch = _step(case, view["view_id"])
        assert batch is not None
        assert batch["schema_version"] == "wuji.view-event.v3"
        assert batch["view_id"] == view["view_id"]
        assert batch["snapshot_id"] != view["snapshot_id"]
        assert batch["base_view_revision"] == "1"
        assert batch["view_revision"] == "2"
        assert batch["cursor"] and len(batch["cursor"]) >= 32
        assert {item["op"] for item in batch["patches"]} <= {
            "upsert_node", "remove_node", "upsert_edge", "remove_edge"
        }
        upserts = [item["value"] for item in batch["patches"] if item["op"] == "upsert_node"]
        assert any(item["ref"]["entity_type"] == "claim" for item in upserts)

        # The cursor resumes the same view and stays idle until the next change.
        assert _step(case, view["view_id"], batch["cursor"]) is None
        assert _step(case, view["view_id"], batch["cursor"]) is None


def test_a_cursor_from_an_older_view_revision_requires_a_resnapshot(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        view = _view(case)

        first_ref = revise_claim(case, claim, text="first stream change")
        first = _step(case, view["view_id"])
        assert first is not None

        # Another consumer advances the same saved view. The old cursor now
        # names a state the server no longer holds as its current baseline.
        second_claim = SimpleNamespace(body=claim.body, ref=first_ref)
        second_ref = revise_claim(case, second_claim, text="second stream change")
        second = _step(case, view["view_id"], first["cursor"])
        assert second is not None

        third_claim = SimpleNamespace(body=claim.body, ref=second_ref)
        revise_claim(case, third_claim, text="third stream change")
        with pytest.raises(DomainError) as stale:
            _step(case, view["view_id"], first["cursor"])
        assert stale.value.code == "VIEW_RESET_REQUIRED"


def test_a_view_only_advances_for_its_own_subject_and_cursor(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        first = _view(case)
        with pytest.raises(DomainError) as foreign:
            case.projection.stream_task(ASSESSOR, first["view_id"])
        assert foreign.value.code == "NOT_FOUND_OR_FORBIDDEN"

        revise_claim(case, claim, text="one change for the first view")
        batch = _step(case, first["view_id"])
        assert batch is not None and batch["view_id"] == first["view_id"]

        # A stream cursor is bound to its own view: another view cannot resume it
        # and the original view still can.
        second = _view(case)
        assert second["view_id"] != first["view_id"]
        with pytest.raises(DomainError) as wrong_view:
            _step(case, second["view_id"], batch["cursor"])
        assert wrong_view.value.code == "NOT_FOUND_OR_FORBIDDEN"
        assert _step(case, first["view_id"], batch["cursor"]) is None


def test_losing_access_stops_the_stream_instead_of_leaking(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        supported_claim(case)
        view = _view(case)
        set_reader_access(case, can_read=False)
        with pytest.raises(DomainError) as refused:
            _step(case, view["view_id"])
        assert refused.value.code == "NOT_FOUND_OR_FORBIDDEN"

        # A lowered clearance is an authorization change as well: the saved view
        # was bound to the old permissions and must not keep streaming.
        set_reader_access(case, can_read=True)
        fresh = _view(case)
        set_reader_access(case, can_read=True, clearance=0)
        with pytest.raises(DomainError) as lowered:
            _step(case, fresh["view_id"])
        assert lowered.value.code == "NOT_FOUND_OR_FORBIDDEN"


async def _stream_events(app, token, path, *, mutate=None, timeout=30.0):
    """Drive the real ASGI app and stop after the first response body chunk."""

    messages: list[dict] = []
    calls = 0
    started, first_body = asyncio.Event(), asyncio.Event()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"authorization", ("Bearer " + token).encode()),
            (b"accept", b"text/event-stream"),
        ],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
        "state": {},
    }

    async def receive():
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if message["type"] == "http.response.start":
            started.set()
        elif message["type"] == "http.response.body" and message.get("body"):
            first_body.set()

    task = asyncio.create_task(app(scope, receive, send))
    try:
        await asyncio.wait_for(started.wait(), timeout)
        if mutate is not None:
            await asyncio.to_thread(mutate)
        await asyncio.wait_for(first_body.wait(), timeout)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    return messages


def _frames(messages):
    start = next(m for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    ).decode()
    headers = {key.decode(): value.decode() for key, value in start["headers"]}
    return start["status"], headers, body


def test_the_signed_stream_route_emits_a_batch_after_the_change(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        view = _view(case)
        app = create_app(
            token_verifier=case.knowledge.verifier,
            routers=[create_view_router(case.projection)],
        )
        messages = asyncio.run(
            _stream_events(
                app,
                case.knowledge.tokens.reader,
                "/api/v2/views/" + view["view_id"] + "/events",
                mutate=lambda: revise_claim(
                    case, claim, text="revised while the stream was open"
                ),
            )
        )
        status, headers, body = _frames(messages)
        assert status == 200
        assert headers["content-type"].startswith("text/event-stream")
        assert headers["cache-control"] == "no-store"
        assert headers["x-accel-buffering"] == "no"
        assert body.startswith("id: ")
        lines = dict(
            line.split(": ", 1) for line in body.split("\n\n")[0].splitlines()
        )
        assert lines["event"] == "view"
        document = json.loads(lines["data"])
        assert document["view_id"] == view["view_id"]
        assert document["base_view_revision"] == "1"
        assert document["view_revision"] == "2"
        assert lines["id"] == document["cursor"]
        assert any(item["op"] == "upsert_node" for item in document["patches"])


def test_the_signed_stream_route_refuses_a_foreign_view(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        supported_claim(case)
        view = _view(case)
        app = create_app(
            token_verifier=case.knowledge.verifier,
            routers=[create_view_router(case.projection)],
        )
        messages = asyncio.run(
            _stream_events(
                app,
                case.knowledge.tokens.agent,
                "/api/v2/views/" + view["view_id"] + "/events",
            )
        )
        status, headers, body = _frames(messages)
        assert status == 404
        assert headers["content-type"] == "application/json"
        assert json.loads(body)["code"] == "NOT_FOUND_OR_FORBIDDEN"


def test_the_view_stream_only_exists_on_its_own_migration_head(
    db_environment, tmp_path, audit_directory
):
    # The P15 head is part of the chain, not necessarily the newest head:
    # later migrations (P16 delivery/purge) append to it.
    assert schema.VIEW_STREAM_HEAD == "vnext_0025_p15_view_stream"
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        with case.environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT 1 FROM vnext.schema_migration WHERE head=%s",
                (schema.VIEW_STREAM_HEAD,),
            ).fetchone() == (1,)
            revision = connection.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
                " WHERE conrelid='vnext.projection_view'::regclass"
                " AND conname='projection_view_view_revision_check'"
            ).fetchone()[0]
            assert "trunc(view_revision)" in revision
            kind = connection.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
                " WHERE conrelid='vnext.projection_cursor'::regclass"
                " AND conname='projection_cursor_kind_check'"
            ).fetchone()[0]
            assert "stream" in kind
