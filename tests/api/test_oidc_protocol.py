from __future__ import annotations

import concurrent.futures
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import psycopg

from conftest import (
    RunManifest,
    assert_safe_callback_failure,
    authorize,
    begin_login,
    complete_fixture_login,
    finish_callback,
    fixture_control,
    fixture_stats,
    release_fixture_token,
)


pytestmark = pytest.mark.platform


def session_counts(manifest: RunManifest, user: str) -> dict[str, int]:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*), count(*) FILTER (WHERE revoked_at IS NULL "
            "AND absolute_expires_at > clock_timestamp() "
            "AND last_seen_at + interval '30 minutes' > clock_timestamp()) "
            "FROM sessions WHERE user_id = %s",
            (manifest.seed(user)["id"],),
        )
        total, active = cursor.fetchone()
    return {"total_count": total, "active_count": active}


def audit_snapshot(manifest: RunManifest) -> tuple[int, tuple[str, object] | None]:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM identity_audit")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT action, details FROM identity_audit ORDER BY id DESC LIMIT 1")
        latest = cursor.fetchone()
    return count, latest


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(control):
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    try:
        yield
    finally:
        control.run("api", "restart", "--profile", "keycloak")
        control.run("api", "wait-ready")


def test_valid_rs256_code_pkce_login_creates_opaque_session(client, run_manifest: RunManifest) -> None:
    response = complete_fixture_login(client, run_manifest)
    assert response.status_code == 303
    assert response.headers["location"] == "/projects"
    cookies = [cookie for cookie in client.cookies.jar if cookie.name == "wuji_session"]
    assert len(cookies) == 1
    assert {cookie.name for cookie in client.cookies.jar} == {"wuji_session"}
    cookie = cookies[0]
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cookie.get_nonstandard_attr("SameSite") == "Lax"
    assert cookie.path == "/"
    assert cookie.secure is False
    assert len(cookie.value) >= 43
    assert "." not in cookie.value, "session handle must not be a JWT"
    session = client.get("/api/v1/session")
    assert session.status_code == 200
    assert session.headers["cache-control"] == "no-store"
    assert "csrf_token" in session.json()


def test_handshake_state_and_browser_binding_are_hashed_and_expire_in_five_minutes(
    client, run_manifest: RunManifest
) -> None:
    fixture_control(run_manifest, "valid")
    login = begin_login(client)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    binding_cookie = next(cookie for cookie in client.cookies.jar if cookie.name != "wuji_session")
    dsn = run_manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT state_hash, binding_hash, nonce, code_verifier, "
            "extract(epoch FROM (expires_at - created_at)) FROM oidc_handshakes "
            "ORDER BY created_at DESC LIMIT 1"
        )
        state_hash, binding_hash, nonce, verifier, lifetime = cursor.fetchone()
    assert re.fullmatch(r"[a-f0-9]{64}", state_hash)
    assert re.fullmatch(r"[a-f0-9]{64}", binding_hash)
    assert state not in {state_hash, binding_hash}
    assert binding_cookie.value not in {state_hash, binding_hash}
    assert len(nonce) >= 32 and len(verifier) >= 43
    assert lifetime == 5 * 60


@pytest.mark.parametrize(
    "scenario",
    [
        "bad_nonce",
        "missing_nonce",
        "nonce_supported_false_wrong_nonce",
        "wrong_issuer",
        "wrong_audience_azp",
        "bad_signature",
        "wrong_algorithm",
        "expired",
        "future_nbf",
    ],
)
def test_invalid_id_token_never_creates_a_session(
    scenario: str, client, run_manifest: RunManifest, control
) -> None:
    before = session_counts(run_manifest, "protocol_user")
    response = complete_fixture_login(client, run_manifest, scenario=scenario)
    assert assert_safe_callback_failure(response) == "UNAUTHENTICATED"
    after = session_counts(run_manifest, "protocol_user")
    assert after == before
    assert client.get("/api/v1/session").status_code == 401


def test_authorization_error_is_a_safe_redirect(client, run_manifest: RunManifest) -> None:
    response = complete_fixture_login(client, run_manifest, scenario="authorization_error")
    assert assert_safe_callback_failure(response) == "UNAUTHENTICATED"


def test_failed_reauthentication_preserves_old_session_without_creating_a_new_one(
    client, run_manifest: RunManifest, control
) -> None:
    success = complete_fixture_login(client, run_manifest)
    assert success.headers["location"] == "/projects"
    old_cookie = client.cookies.get("wuji_session")
    before = session_counts(run_manifest, "protocol_user")
    assert_safe_callback_failure(complete_fixture_login(client, run_manifest, scenario="bad_nonce"))
    assert client.cookies.get("wuji_session") == old_cookie
    assert client.get("/api/v1/session").status_code == 200
    after = session_counts(run_manifest, "protocol_user")
    assert after == before


def test_discovery_issuer_must_exactly_match_configuration(client, run_manifest: RunManifest, control) -> None:
    fixture_control(run_manifest, "discovery_wrong_issuer")
    # Restart clears Authlib's discovery cache so this checks metadata itself.
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    response = client.get("/api/v1/auth/login", params={"return_to": "/projects"})
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert "unexpected" not in response.text
    fixture_control(run_manifest, "valid")
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")


def test_wrong_state_and_cross_browser_callback_are_rejected(
    client, run_manifest: RunManifest
) -> None:
    fixture_control(run_manifest, "valid")
    login = begin_login(client)
    callback = authorize(client, login)
    parsed = urlparse(callback)
    query = parse_qs(parsed.query)
    query["state"] = ["wrong-state"]
    wrong_state = parsed._replace(query=str(httpx.QueryParams(query))).geturl()
    assert_safe_callback_failure(client.get(wrong_state))

    fixture_control(run_manifest, "valid")
    owner = begin_login(client)
    callback = authorize(client, owner)
    with httpx.Client(follow_redirects=False, timeout=10) as other_browser:
        assert_safe_callback_failure(other_browser.get(callback))
    owner_response = finish_callback(client, callback)
    assert owner_response.status_code == 303
    assert owner_response.headers["location"] == "/projects"


def test_claim_failure_consumes_handshake_and_cannot_be_retried(
    client, run_manifest: RunManifest, control
) -> None:
    fixture_control(run_manifest, "bad_nonce")
    callback = authorize(client, begin_login(client))
    before = session_counts(run_manifest, "protocol_user")["total_count"]
    assert_safe_callback_failure(finish_callback(client, callback))
    assert_safe_callback_failure(finish_callback(client, callback))
    after = session_counts(run_manifest, "protocol_user")["total_count"]
    assert after == before


def test_token_endpoint_failure_consumes_handshake_and_retry_cannot_create_session(
    client, run_manifest: RunManifest
) -> None:
    fixture_control(run_manifest, "token_error")
    callback = authorize(client, begin_login(client))
    before = session_counts(run_manifest, "protocol_user")
    assert assert_safe_callback_failure(finish_callback(client, callback)) == "SERVICE_UNAVAILABLE"
    assert assert_safe_callback_failure(finish_callback(client, callback)) == "UNAUTHENTICATED"
    assert session_counts(run_manifest, "protocol_user") == before


def test_new_handshake_replaces_old_binding(client, run_manifest: RunManifest) -> None:
    fixture_control(run_manifest, "valid")
    first = begin_login(client)
    first_callback = authorize(client, first)
    second = begin_login(client)
    second_callback = authorize(client, second)
    assert_safe_callback_failure(finish_callback(client, first_callback))
    success = finish_callback(client, second_callback)
    assert success.status_code == 303
    assert success.headers["location"] == "/projects"


def test_login_while_current_binding_is_exchanging_returns_409(
    client, run_manifest: RunManifest
) -> None:
    fixture_control(run_manifest, "blocked_valid")
    callback = authorize(client, begin_login(client))
    cookie_header = "; ".join(f"{c.name}={c.value}" for c in client.cookies.jar)

    def finish() -> httpx.Response:
        return httpx.get(callback, headers={"Cookie": cookie_header}, follow_redirects=False, timeout=20)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(finish)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not fixture_stats(run_manifest)["token_waiting"]:
            time.sleep(0.05)
        assert fixture_stats(run_manifest)["token_waiting"] is True
        retry = httpx.get(
            f'{run_manifest.url("web")}/api/v1/auth/login?return_to=%2Fprojects',
            headers={"Cookie": cookie_header},
            follow_redirects=False,
            timeout=10,
        )
        assert retry.status_code == 409
        assert retry.json()["code"] == "INVALID_TRANSITION"
        release_fixture_token(run_manifest)
        completed = pending.result(timeout=15)
    assert completed.status_code == 303
    assert completed.headers["location"] == "/projects"


def test_lost_exchange_stops_blocking_login_after_handshake_expiry(
    client, run_manifest: RunManifest, control
) -> None:
    fixture_control(run_manifest, "blocked_valid")
    callback = authorize(client, begin_login(client))
    dsn = run_manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT extract(epoch FROM (expires_at - created_at)) FROM oidc_handshakes "
            "ORDER BY created_at DESC LIMIT 1"
        )
        assert cursor.fetchone()[0] == 5 * 60
    cookie_header = "; ".join(f"{c.name}={c.value}" for c in client.cookies.jar)

    def finish() -> httpx.Response | None:
        try:
            return httpx.get(callback, headers={"Cookie": cookie_header}, follow_redirects=False, timeout=20)
        except httpx.HTTPError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(finish)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not fixture_stats(run_manifest)["token_waiting"]:
            time.sleep(0.05)
        assert fixture_stats(run_manifest)["token_waiting"] is True
        control.run("api", "restart", "--profile", "issuer_fixture")
        control.run("api", "wait-ready")
        release_fixture_token(run_manifest)
        pending.result(timeout=15)
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE oidc_handshakes SET expires_at = created_at + interval '1 second' "
            "WHERE id = (SELECT id FROM oidc_handshakes ORDER BY created_at DESC LIMIT 1)"
        )
        assert cursor.rowcount == 1
    time.sleep(1.1)
    retry = client.get("/api/v1/auth/login", params={"return_to": "/projects"})
    assert retry.status_code == 302


def test_callback_is_one_time_and_concurrent_consumption_creates_at_most_one_session(
    client, run_manifest: RunManifest, control
) -> None:
    fixture_control(run_manifest, "valid")
    callback = authorize(client, begin_login(client))
    cookie_header = "; ".join(f"{c.name}={c.value}" for c in client.cookies.jar)
    before = session_counts(run_manifest, "protocol_user")["total_count"]

    def invoke() -> httpx.Response:
        return httpx.get(callback, headers={"Cookie": cookie_header}, follow_redirects=False, timeout=15)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: invoke(), range(2)))
    successes = [response for response in responses if response.headers.get("location") == "/projects"]
    assert len(successes) <= 1
    assert len(successes) == 1
    for response in responses:
        assert response.status_code == 303
    after = session_counts(run_manifest, "protocol_user")["total_count"]
    assert after - before == 1

    replay = httpx.get(callback, headers={"Cookie": cookie_header}, follow_redirects=False, timeout=15)
    assert_safe_callback_failure(replay)
    final = session_counts(run_manifest, "protocol_user")["total_count"]
    assert final == after


def test_illegal_return_targets_are_structured_422(client) -> None:
    for value in ("https://example.invalid/", "//example.invalid/", "/projects/../admin", "/"):
        response = client.get("/api/v1/auth/login", params={"return_to": value})
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_FAILED"
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "query",
    [{}, {"code": "orphan-code"}, {"state": "orphan-state"}, {"error": "access_denied"}],
)
def test_malformed_or_orphan_callback_always_uses_safe_browser_redirect(client, query) -> None:
    assert_safe_callback_failure(client.get("/api/v1/auth/callback", params=query))


def test_callback_protocol_values_and_tokens_are_absent_from_api_logs(
    client, run_manifest: RunManifest
) -> None:
    fixture_control(run_manifest, "bad_nonce")
    audit_before, _ = audit_snapshot(run_manifest)
    login = begin_login(client)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    callback = authorize(client, login)
    code = parse_qs(urlparse(callback).query)["code"][0]
    assert_safe_callback_failure(finish_callback(client, callback))
    audit_after, latest = audit_snapshot(run_manifest)
    assert audit_after == audit_before + 1
    assert latest is not None
    assert "oidc" in latest[0].lower() and "fail" in latest[0].lower()
    audit_text = str(latest[1])
    assert state not in audit_text and code not in audit_text
    assert "phase1a-access-token-log-canary-" not in audit_text
    log_path = Path(run_manifest.data["processes"]["api"]["log_path"])
    log = log_path.read_text(encoding="utf-8", errors="replace")
    assert state not in log
    assert code not in log
    assert "phase1a-code-log-canary-" not in log
    assert "phase1a-access-token-log-canary-" not in log
    assert not re.search(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", log)
    assert "/api/v1/auth/callback?" not in log
