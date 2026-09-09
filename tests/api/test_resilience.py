from __future__ import annotations

import time

import httpx
import pytest
import psycopg
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters

from conftest import RunManifest, complete_fixture_login


pytestmark = pytest.mark.platform


class ContractRequest:
    host_url = "http://127.0.0.1:4182"
    method = "get"
    body = None
    content_type = "application/octet-stream"

    def __init__(self, response: httpx.Response):
        self.path = response.request.url.path
        self.parameters = RequestParameters(query=dict(response.request.url.params))


class ContractResponse:
    def __init__(self, response: httpx.Response):
        self.status_code = response.status_code
        self.content_type = response.headers.get("content-type", "")
        self.headers = response.headers
        self.data = response.content


def wait_status(url: str, expected: int, timeout: float = 60) -> httpx.Response:
    deadline = time.monotonic() + timeout
    last: httpx.Response | None = None
    while time.monotonic() < deadline:
        try:
            last = httpx.get(url, timeout=2)
            if last.status_code == expected:
                return last
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise AssertionError(f"{url} did not return {expected}; last={last}")


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(control):
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    try:
        yield
    finally:
        control.run("db-forward", "resume")
        control.run("unmigrated", "stop")
        control.run("api", "restart", "--profile", "keycloak")
        control.run("api", "wait-ready")


def login(client: httpx.Client, manifest: RunManifest) -> None:
    response = complete_fixture_login(client, manifest, user="dual_ab")
    assert response.status_code == 303
    assert client.get("/api/v1/session").status_code == 200


def assert_service_unavailable(response: httpx.Response) -> None:
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.headers["cache-control"] == "no-store"


def seed_state(manifest: RunManifest) -> dict[str, object]:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        counts: dict[str, int] = {}
        for table in (
            "users", "external_identities", "tenants", "projects", "tenant_memberships", "project_memberships"
        ):
            cursor.execute(f"SELECT count(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        cursor.execute("SELECT version_num FROM alembic_version")
        revision = cursor.fetchone()[0]
    return {"counts": counts, "revision": revision}


def test_api_to_database_network_loss_fails_closed_then_recovers_same_session(
    client, run_manifest: RunManifest, control
) -> None:
    login(client, run_manifest)
    original_cookie = client.cookies.get("wuji_session")
    csrf = client.get("/api/v1/session").json()["csrf_token"]
    original_projects = client.get("/api/v1/projects", params={"limit": 1}).json()
    original_cursor = original_projects["next_cursor"]
    control.run("db-forward", "pause")
    wait_status(f'{run_manifest.url("api")}/health/ready', 503)
    assert httpx.get(f'{run_manifest.url("api")}/health/live').status_code == 200
    contract = OpenAPI.from_file_path("packages/contracts/openapi.yaml")
    session_failure = client.get("/api/v1/session")
    project_failure = client.get("/api/v1/projects")
    assert_service_unavailable(session_failure)
    assert_service_unavailable(project_failure)
    logout_failure = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": run_manifest.url("web"), "X-CSRF-Token": csrf},
    )
    assert_service_unavailable(logout_failure)
    contract.validate_response(ContractRequest(session_failure), ContractResponse(session_failure))
    contract.validate_response(ContractRequest(project_failure), ContractResponse(project_failure))
    discovery = httpx.get(f'{run_manifest.data["realm"]["issuer"]}/.well-known/openid-configuration')
    assert discovery.status_code == 200

    control.run("db-forward", "resume")
    control.run("api", "wait-ready")
    assert client.cookies.get("wuji_session") == original_cookie
    assert client.get("/api/v1/session").status_code == 200
    recovered = client.get("/api/v1/projects", params={"limit": 1}).json()
    assert recovered["items"] == original_projects["items"]
    if original_cursor:
        assert client.get(
            "/api/v1/projects", params={"limit": 1, "cursor": original_cursor}
        ).status_code == 200


def test_postgresql_pod_recreation_preserves_same_run_data_and_session(
    client, run_manifest: RunManifest, control
) -> None:
    login(client, run_manifest)
    original_cookie = client.cookies.get("wuji_session")
    original_projects = client.get("/api/v1/projects", params={"limit": 1}).json()
    original_cursor = original_projects["next_cursor"]
    result = control.run("postgres", "pod-recreate")
    assert result["namespace"] == "wuji-test"
    control.run("postgres", "wait-all-ready")
    control.run("api", "wait-ready")
    assert client.cookies.get("wuji_session") == original_cookie
    assert client.get("/api/v1/session").status_code == 200
    recovered = client.get("/api/v1/projects", params={"limit": 1}).json()
    assert recovered["items"] == original_projects["items"]
    if original_cursor:
        assert client.get(
            "/api/v1/projects", params={"limit": 1, "cursor": original_cursor}
        ).status_code == 200


def test_fresh_unmigrated_database_is_live_but_never_ready_or_authorized(
    run_manifest: RunManifest, control
) -> None:
    started = control.run("unmigrated", "start")
    assert started["database"] != run_manifest.data["database"]["name"]
    try:
        live = wait_status(f'{run_manifest.url("unmigrated_api")}/health/live', 200)
        assert live.json() == {"status": "live"}
        assert_service_unavailable(
            wait_status(f'{run_manifest.url("unmigrated_api")}/health/ready', 503)
        )
        assert_service_unavailable(
            httpx.get(f'{run_manifest.url("unmigrated_api")}/api/v1/session')
        )
        observed = control.run("query", "unmigrated-revision")
        assert observed["alembic_version_present"] is False
        assert observed["business_tables_present"] is False
    finally:
        control.run("unmigrated", "stop")


def test_migration_and_seed_replay_are_idempotent_and_preserve_rows(
    run_manifest: RunManifest, control
) -> None:
    before = seed_state(run_manifest)
    first = control.run("database", "migrate")
    control.run("database", "seed")
    second = control.run("database", "migrate")
    control.run("database", "seed")
    after = seed_state(run_manifest)
    assert first["revision"] == second["revision"] == "20260909_0001"
    assert after == before
