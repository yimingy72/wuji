from __future__ import annotations

from datetime import datetime, timedelta
import concurrent.futures
from decimal import Decimal
import re
import time

import httpx
import pytest
import psycopg

from conftest import RunManifest, authorize, begin_login, complete_fixture_login, fixture_control


pytestmark = pytest.mark.platform

USER_LOCK_SEED = 0x57554A49


def management_dsn(manifest: RunManifest) -> str:
    return manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def admin_dsn(manifest: RunManifest) -> str:
    return manifest.data["credentials"]["database"]["admin_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def set_latest_session_time(manifest: RunManifest, user: str, boundary: str) -> None:
    with psycopg.connect(management_dsn(manifest)) as connection, connection.cursor() as cursor:
        if boundary == "idle":
            cursor.execute(
                "UPDATE sessions SET last_seen_at = clock_timestamp() - interval '30 minutes 1 second', "
                "absolute_expires_at = created_at + interval '8 hours' "
                "WHERE id = (SELECT id FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1)",
                (manifest.seed(user)["id"],),
            )
        else:
            cursor.execute(
                "UPDATE sessions SET last_seen_at = clock_timestamp(), "
                "absolute_expires_at = created_at + interval '1 second' "
                "WHERE id = (SELECT id FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1)",
                (manifest.seed(user)["id"],),
            )
        assert cursor.rowcount == 1
    if boundary == "absolute":
        time.sleep(1.1)


def latest_session_times(manifest: RunManifest, user: str) -> tuple[datetime, datetime]:
    with psycopg.connect(management_dsn(manifest)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT last_seen_at, absolute_expires_at FROM sessions WHERE user_id = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (manifest.seed(user)["id"],),
        )
        return cursor.fetchone()


def active_session_count(manifest: RunManifest, user: str) -> int:
    with psycopg.connect(management_dsn(manifest)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM sessions WHERE user_id = %s AND revoked_at IS NULL "
            "AND absolute_expires_at > clock_timestamp() "
            "AND last_seen_at + interval '30 minutes' > clock_timestamp()",
            (manifest.seed(user)["id"],),
        )
        return cursor.fetchone()[0]


def waiting_advisory_locks(connection: psycopg.Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_locks waiting "
            "WHERE waiting.locktype = 'advisory' AND NOT waiting.granted AND EXISTS ("
            "SELECT 1 FROM pg_locks held WHERE held.pid = pg_backend_pid() "
            "AND held.locktype = 'advisory' AND held.granted "
            "AND held.database IS NOT DISTINCT FROM waiting.database "
            "AND held.classid = waiting.classid AND held.objid = waiting.objid "
            "AND held.objsubid = waiting.objsubid)"
        )
        return cursor.fetchone()[0]


def wait_for_advisory_waiters(connection: psycopg.Connection, expected: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if waiting_advisory_locks(connection) >= expected:
            return
        time.sleep(0.05)
    raise AssertionError(f"expected at least {expected} advisory lock waiters")


def wait_for_blocked_auth_backend(
    connection: psycopg.Connection, *, blocker_pid: int, auth_role: str
) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE usename = %s AND %s = ANY(pg_blocking_pids(pid))",
                (auth_role, blocker_pid),
            )
            if cursor.fetchone()[0] >= 1:
                return
        time.sleep(0.05)
    raise AssertionError("API auth backend did not wait on the held Session row")


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(control):
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    try:
        yield
    finally:
        control.run("api", "restart", "--profile", "keycloak")
        control.run("api", "wait-ready")


def logged_in(client: httpx.Client, manifest: RunManifest, user: str = "protocol_user") -> dict:
    callback = complete_fixture_login(client, manifest, user=user)
    assert callback.status_code == 303
    response = client.get("/api/v1/session")
    assert response.status_code == 200
    return response.json()


def test_session_expiry_is_minimum_of_idle_and_absolute_and_survives_restart(
    client, run_manifest: RunManifest, control
) -> None:
    session = logged_in(client, run_manifest)
    expires_at = datetime.fromisoformat(session["expires_at"])
    assert 0 < (expires_at - datetime.now(expires_at.tzinfo)).total_seconds() <= 30 * 60 + 5
    csrf = session["csrf_token"]
    cookie = client.cookies.get("wuji_session")
    with psycopg.connect(management_dsn(run_manifest)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT extract(epoch FROM (absolute_expires_at - created_at)), token_hash, csrf_token "
            "FROM sessions "
            "WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
            (run_manifest.seed("protocol_user")["id"],),
        )
        duration, token_hash, stored_csrf = cursor.fetchone()
        assert abs(duration - Decimal(8 * 60 * 60)) <= Decimal("0.001")
        assert re.fullmatch(r"[a-f0-9]{64}", token_hash)
        assert token_hash != cookie
        assert stored_csrf == csrf
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    after = client.get("/api/v1/session")
    assert after.status_code == 200
    assert after.json()["csrf_token"] == csrf
    assert client.cookies.get("wuji_session") == cookie


@pytest.mark.parametrize("boundary", ["idle", "absolute"], ids=["idle-30-minutes", "absolute-8-hours"])
def test_expired_session_is_not_extended_before_validation(
    boundary: str,
    client,
    run_manifest: RunManifest,
    control,
) -> None:
    logged_in(client, run_manifest)
    set_latest_session_time(run_manifest, "protocol_user", boundary)
    first = client.get("/api/v1/session")
    second = client.get("/api/v1/session")
    assert first.status_code == second.status_code == 401
    assert first.json()["code"] == second.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("boundary", ["idle", "absolute"])
def test_session_expiring_while_authentication_waits_on_row_lock_is_not_refreshed(
    boundary: str, client, run_manifest: RunManifest
) -> None:
    logged_in(client, run_manifest)
    user_id = run_manifest.seed("protocol_user")["id"]
    auth_role = run_manifest.data["database"]["roles"]["auth"]
    dsn = management_dsn(run_manifest)
    with psycopg.connect(dsn) as setup, setup.cursor() as cursor:
        database_now = cursor.execute("SELECT clock_timestamp()").fetchone()[0]
        deadline = database_now + timedelta(seconds=4)
        if boundary == "absolute":
            cursor.execute(
                "UPDATE sessions SET last_seen_at = clock_timestamp(), absolute_expires_at = %s "
                "WHERE id = (SELECT id FROM sessions WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT 1) RETURNING id, last_seen_at",
                (deadline, user_id),
            )
        else:
            cursor.execute(
                "UPDATE sessions SET last_seen_at = %s - interval '30 minutes', "
                "absolute_expires_at = clock_timestamp() + interval '1 hour' "
                "WHERE id = (SELECT id FROM sessions WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT 1) RETURNING id, last_seen_at",
                (deadline, user_id),
            )
        session_id, last_seen_before = cursor.fetchone()

    holder = psycopg.connect(dsn, autocommit=False)
    observer = psycopg.connect(admin_dsn(run_manifest), autocommit=True)
    try:
        locked_id = holder.execute(
            "SELECT id FROM sessions WHERE id = %s FOR UPDATE", (session_id,)
        ).fetchone()[0]
        assert locked_id == session_id
        blocker_pid = holder.execute("SELECT pg_backend_pid()").fetchone()[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(client.get, "/api/v1/session")
            try:
                wait_for_blocked_auth_backend(
                    observer, blocker_pid=blocker_pid, auth_role=auth_role
                )
                while holder.execute("SELECT clock_timestamp() < %s", (deadline,)).fetchone()[0]:
                    time.sleep(0.05)
                assert not pending.done()
            finally:
                holder.rollback()
            response = pending.result(timeout=15)
    finally:
        holder.close()
        observer.close()

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        last_seen_after = cursor.execute(
            "SELECT last_seen_at FROM sessions WHERE id = %s", (session_id,)
        ).fetchone()[0]
    assert last_seen_after == last_seen_before


def test_disable_then_enable_does_not_revive_existing_cookie(
    client, run_manifest: RunManifest, control
) -> None:
    logged_in(client, run_manifest)
    cookie = client.cookies.get("wuji_session")
    control.run("user", "disable", "--user", "protocol_user")
    try:
        assert client.get("/api/v1/session").status_code == 401
    finally:
        control.run("user", "enable", "--user", "protocol_user")
    client.cookies.set("wuji_session", cookie, domain="127.0.0.1", path="/")
    assert client.get("/api/v1/session").status_code == 401


def test_real_oidc_callback_and_disable_are_serialized_so_no_cookie_can_revive(
    client, run_manifest: RunManifest, control
) -> None:
    control.run("user", "enable", "--user", "protocol_user")
    fixture_control(run_manifest, "valid")
    callback = authorize(client, begin_login(client))
    cookie_header = "; ".join(f"{c.name}={c.value}" for c in client.cookies.jar)

    def finish_login() -> httpx.Response:
        return httpx.get(callback, headers={"Cookie": cookie_header}, follow_redirects=False, timeout=20)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        login_future = executor.submit(finish_login)
        disable_future = executor.submit(control.run, "user", "disable", "--user", "protocol_user")
        callback_response = login_future.result(timeout=30)
        disable_future.result(timeout=30)
    try:
        assert callback_response.status_code == 303
        possible_cookie = callback_response.cookies.get("wuji_session")
    finally:
        control.run("user", "enable", "--user", "protocol_user")
    if possible_cookie:
        with httpx.Client(base_url=run_manifest.url("web")) as stale:
            stale.cookies.set("wuji_session", possible_cookie, domain="127.0.0.1", path="/")
            assert stale.get("/api/v1/session").status_code == 401
    assert active_session_count(run_manifest, "protocol_user") == 0


def test_callback_and_disable_reach_same_user_lock_before_session_can_be_revived(
    client, run_manifest: RunManifest, control
) -> None:
    user_symbol = "protocol_user"
    user_id = run_manifest.seed(user_symbol)["id"]
    control.run("user", "enable", "--user", user_symbol)
    fixture_control(run_manifest, "valid")
    callback = authorize(client, begin_login(client))
    cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in client.cookies.jar)

    def finish_login() -> httpx.Response:
        return httpx.get(
            callback,
            headers={"Cookie": cookie_header},
            follow_redirects=False,
            timeout=30,
        )

    holder = psycopg.connect(management_dsn(run_manifest), autocommit=False)
    try:
        holder.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, %s))",
            (user_id, USER_LOCK_SEED),
        ).fetchone()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            login_future = executor.submit(finish_login)
            disable_future = None
            try:
                wait_for_advisory_waiters(holder, 1)
                disable_future = executor.submit(
                    control.run, "user", "disable", "--user", user_symbol
                )
                wait_for_advisory_waiters(holder, 2)
                assert not login_future.done()
                assert not disable_future.done()
            finally:
                holder.rollback()
            callback_response = login_future.result(timeout=30)
            assert disable_future is not None
            disable_future.result(timeout=30)
    finally:
        holder.close()

    try:
        assert callback_response.status_code == 303
        assert callback_response.headers["location"] == "/projects"
        stale_cookie = callback_response.cookies.get("wuji_session")
        assert stale_cookie
        assert active_session_count(run_manifest, user_symbol) == 0
    finally:
        control.run("user", "enable", "--user", user_symbol)

    with httpx.Client(base_url=run_manifest.url("web"), follow_redirects=False) as stale:
        stale.cookies.set("wuji_session", stale_cookie, domain="127.0.0.1", path="/")
        assert stale.get("/api/v1/session").status_code == 401


def test_new_login_in_same_browser_revokes_replaced_session(
    client, run_manifest: RunManifest
) -> None:
    logged_in(client, run_manifest)
    old_cookie = client.cookies.get("wuji_session")
    logged_in(client, run_manifest)
    new_cookie = client.cookies.get("wuji_session")
    assert old_cookie != new_cookie
    with httpx.Client(base_url=run_manifest.url("web"), follow_redirects=False) as old_session:
        old_session.cookies.set("wuji_session", old_cookie, domain="127.0.0.1", path="/")
        assert old_session.get("/api/v1/session").status_code == 401


def test_logout_requires_bound_csrf_and_allowed_origin(
    client, run_manifest: RunManifest
) -> None:
    session = logged_in(client, run_manifest)
    csrf = session["csrf_token"]
    cases = [
        {},
        {"X-CSRF-Token": "wrong", "Origin": run_manifest.url("web")},
        {"X-CSRF-Token": csrf, "Origin": "https://example.invalid"},
        {"X-CSRF-Token": csrf},
    ]
    for headers in cases:
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/v1/session").status_code == 200

    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf, "Origin": run_manifest.url("web")},
    )
    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/session").status_code == 401


def test_logout_with_authoritatively_invalid_session_returns_401_and_clears_cookie(
    run_manifest: RunManifest,
) -> None:
    with httpx.Client(base_url=run_manifest.url("web"), follow_redirects=False) as anonymous:
        anonymous.cookies.set("wuji_session", "invalid-opaque-handle", domain="127.0.0.1", path="/")
        response = anonymous.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": "not-bound", "Origin": run_manifest.url("web")},
        )
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHENTICATED"
        assert any(
            value.lower().startswith("wuji_session=")
            and ("max-age=0" in value.lower() or "expires=" in value.lower())
            for value in response.headers.get_list("set-cookie")
        )


def test_successful_business_requests_advance_idle_expiry_but_health_does_not(
    client, run_manifest: RunManifest, control
) -> None:
    logged_in(client, run_manifest)
    with psycopg.connect(management_dsn(run_manifest)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE sessions SET last_seen_at = clock_timestamp() - interval '20 minutes', "
            "absolute_expires_at = created_at + interval '8 hours' "
            "WHERE id = (SELECT id FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1)",
            (run_manifest.seed("protocol_user")["id"],),
        )
    before = latest_session_times(run_manifest, "protocol_user")
    assert client.get("/health/live").status_code == 200
    health = latest_session_times(run_manifest, "protocol_user")
    assert health[0] == before[0]
    assert client.get("/api/v1/projects").status_code == 200
    business = latest_session_times(run_manifest, "protocol_user")
    assert business[0] > health[0]
