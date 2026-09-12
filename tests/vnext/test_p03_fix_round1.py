"""Only P03 review R1 mutation authority and R2 same-loop responsiveness."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from threading import Event, Lock
import time

import httpx
import psycopg
import pytest

from wuji_core.contracts.envelopes import BlobRef
from wuji_core.persistence.snapshots import SnapshotRepository
from support.http_capture import (
    CapturedExchange,
    CapturedRequest,
    CapturedResponse,
    _serializable,
)
from support.p03 import access, capture_case


def _attempt_sql_mutations(case, actor, capability, ref):
    outcomes = []
    with case.uow.transaction(actor, "task-fixture", capability=capability) as tx:
        identity = tx.connection.execute(
            "SELECT current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        ).fetchone()
        assert identity[1:] == (False, False)
        before = tx.connection.execute(
            "SELECT expires_at FROM vnext.artifact_lease WHERE artifact_id=%s",
            (ref.id,),
        ).fetchone()
        statements = [
            (
                "UPDATE vnext.artifact SET state='sealed' WHERE entity_id=%s RETURNING state",
                "seal",
            ),
            (
                "UPDATE vnext.artifact_lease SET expires_at=clock_timestamp()-interval '1 second' WHERE artifact_id=%s RETURNING expires_at",
                "expire_lease",
            ),
            (
                "DELETE FROM vnext.artifact_lease WHERE artifact_id=%s RETURNING lease_owner",
                "delete_lease",
            ),
        ]
        for statement, operation in statements:
            # Observe a real DML result/error, then roll back each attempt independently.
            # This keeps the red run non-destructive and lets all three gaps be observed.
            try:
                with tx.connection.transaction(force_rollback=True):
                    values = tx.connection.execute(statement, (ref.id,)).fetchall()
                    outcomes.append(
                        {
                            "operation": operation,
                            "sqlstate": None,
                            "changed_rows": len(values),
                        }
                    )
            except psycopg.errors.InsufficientPrivilege as error:
                outcomes.append(
                    {
                        "operation": operation,
                        "sqlstate": error.sqlstate,
                        "changed_rows": 0,
                    }
                )
        assert tx.connection.execute(
            "SELECT state FROM vnext.artifact WHERE entity_id=%s", (ref.id,)
        ).fetchone() == ("staged",)
        assert (
            tx.connection.execute(
                "SELECT expires_at FROM vnext.artifact_lease WHERE artifact_id=%s",
                (ref.id,),
            ).fetchone()
            == before
        )
    return outcomes


@pytest.mark.parametrize(
    "subject,role,capability",
    [
        ("agent-fixture", "agent", "write"),
        ("agent-fixture", "agent", "snapshot"),
        ("collector-fixture", "collector", "snapshot"),
    ],
)
def test_non_evidence_context_cannot_mutate_artifact_or_collector_lease(
    db_environment, tmp_path, audit_directory, test_tokens, subject, role, capability
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        ref = case.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b"staged R1 fixture",
            "text/plain",
        )
        outcomes = _attempt_sql_mutations(
            case, access(subject, role=role), capability, ref
        )
        (audit_directory / "mutation-outcomes.json").write_text(
            json.dumps(outcomes, indent=2) + "\n"
        )
        assert [item["sqlstate"] for item in outcomes] == ["42501"] * 3, outcomes


def test_evidence_flag_still_requires_nonrevoked_stored_binding(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        ref = case.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b"binding R1 fixture",
            "text/plain",
        )
        with db_environment.migration_connection() as db:
            db.execute(
                "UPDATE vnext.collector_binding SET revoked=true WHERE tenant_id='tenant-fixture' AND task_id='task-fixture'"
            )
        outcomes = _attempt_sql_mutations(case, access(), "evidence", ref)
        (audit_directory / "mutation-outcomes.json").write_text(
            json.dumps(outcomes, indent=2) + "\n"
        )
        assert [item["sqlstate"] for item in outcomes] == ["42501"] * 3, outcomes


def test_bound_evidence_mutations_keep_seal_snapshot_publication_and_gc(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        ref = case.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b"published R1 fixture",
            "text/plain",
        )
        case.store.acquire_lease(
            access(), "task-fixture", ref, lease_owner="staging", seconds=120
        )
        case.store.seal(access(), "task-fixture", ref)
        # Reader snapshot must retain FOR UPDATE visibility used by publication_ref.
        reader = access("reader-fixture", role="reader")
        snapshot = SnapshotRepository(case.uow).create("task-fixture", reader)
        assert len(snapshot.refs) == 3
        for current in [ref, *[BlobRef.model_validate(wire) for wire in case.refs]]:
            case.store.release_lease(
                access(), "task-fixture", current, lease_owner="staging"
            )
        orphan = case.store.stage(
            access(),
            "task-fixture",
            "attempt-fixture",
            b"orphan R1 fixture",
            "text/plain",
        )
        case.store.seal(access(), "task-fixture", orphan)
        case.store.release_lease(
            access(), "task-fixture", orphan, lease_owner="staging"
        )
        assert case.store.collect_garbage(
            access(), "task-fixture", older_than=datetime.now(timezone.utc)
        ) == [orphan.id]
        assert case.store.read(reader, ref.id, "1")[0] == b"published R1 fixture"
        response = case.client.post(
            "/internal/v2/evidence", json=case.envelope, headers=case.headers
        )
        assert response.status_code == 202, response.text


def test_task_lock_does_not_block_an_unrelated_request_on_same_asgi_loop(
    db_environment, tmp_path, audit_directory, test_tokens
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        held, ingest_waiting, response_done, release_started = (
            Event(),
            Event(),
            Event(),
            Event(),
        )
        events = []
        events_lock = Lock()

        def record(event, **details):
            with events_lock:
                events.append(
                    {"event": event, "monotonic_ns": time.monotonic_ns(), **details}
                )

        def hold_and_observe():
            try:
                with case.uow.transaction(
                    access(), "task-fixture", capability="write"
                ) as tx:
                    holder_pid = tx.connection.execute(
                        "SELECT pg_backend_pid()"
                    ).fetchone()[0]
                    record("task_lock_acquired", holder_pid=holder_pid)
                    held.set()
                    # This is a second real app connection, querying real lock blockers.
                    with db_environment.additional_app_connection() as observer:
                        deadline = time.monotonic() + 2
                        while time.monotonic() < deadline:
                            blocked = observer.execute(
                                "SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND usename=current_user AND %s=ANY(pg_blocking_pids(pid))",
                                (holder_pid,),
                            ).fetchall()
                            observer.commit()
                            if blocked:
                                record(
                                    "ingest_waiting_on_task_lock",
                                    backend_pids=[row[0] for row in blocked],
                                )
                                ingest_waiting.set()
                                break
                            response_done.wait(0.01)
                    if not ingest_waiting.is_set():
                        raise AssertionError("No actual ingest lock wait observed")
                    progressed = response_done.wait(3)
                    record(
                        "lock_release_requested",
                        reason=(
                            "response_completed" if progressed else "finite_fallback"
                        ),
                    )
                    release_started.set()
                record("task_lock_released")
            finally:
                release_started.set()
                held.set()

        async def exercise():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=case.client._app),
                base_url="http://testserver",
            ) as client:

                async def request(method, url, **kwargs):
                    response = await client.request(method, url, **kwargs)
                    await response.aread()
                    req = response.request
                    exchange = CapturedExchange(
                        CapturedRequest(
                            req.method, str(req.url), dict(req.headers), req.content
                        ),
                        CapturedResponse(
                            response.status_code,
                            dict(response.headers),
                            response.content,
                        ),
                    )
                    with (audit_directory / "http-exchanges.jsonl").open("a") as stream:
                        stream.write(
                            json.dumps(_serializable(exchange), sort_keys=True) + "\n"
                        )
                    return response

                ingest = asyncio.create_task(
                    request(
                        "POST",
                        "/internal/v2/evidence",
                        json=case.envelope,
                        headers=case.headers,
                    )
                )
                try:
                    assert await asyncio.to_thread(ingest_waiting.wait, 2)
                    content = await request(
                        "GET",
                        f'/api/v2/artifacts/{case.refs[0]["id"]}/content?version=1',
                        headers={"Authorization": "Bearer " + test_tokens.reader},
                    )
                    progressed_before_release = not release_started.is_set()
                    record(
                        "unrelated_response_completed",
                        status=content.status_code,
                        before_release=progressed_before_release,
                    )
                    response_done.set()
                    receipt = await ingest
                    assert (
                        content.status_code == 200 and content.content == case.data[0]
                    )
                    assert receipt.status_code == 202, receipt.text
                    assert (
                        progressed_before_release
                    ), "ASGI request stalled until the real Task lock was released"
                finally:
                    response_done.set()
                    if not ingest.done():
                        await ingest

        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(hold_and_observe)
            try:
                assert held.wait(2)
                asyncio.run(asyncio.wait_for(exercise(), timeout=8))
            finally:
                response_done.set()
                holder.result(timeout=6)
                (audit_directory / "concurrency-events.json").write_text(
                    json.dumps(events, indent=2) + "\n"
                )
