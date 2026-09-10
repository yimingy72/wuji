from __future__ import annotations

import copy
import base64
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator
from uuid import UUID, uuid4

import httpx
import pytest
import psycopg
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters

from conftest import RunManifest, complete_fixture_login


pytestmark = pytest.mark.platform


class ContractRequest:
    host_url = "http://127.0.0.1:4182"
    body = None
    content_type = "application/octet-stream"

    def __init__(self, request: httpx.Request):
        self.method = request.method.lower()
        self.path = request.url.path
        self.parameters = RequestParameters(query=dict(request.url.params), header=dict(request.headers))


class ContractResponse:
    def __init__(self, response: httpx.Response):
        self.status_code = response.status_code
        self.content_type = response.headers.get("content-type", "")
        self.headers = response.headers
        self.data = response.content


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(control):
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    try:
        yield
    finally:
        control.run("api", "restart", "--profile", "keycloak")
        control.run("api", "wait-ready")


@pytest.fixture(scope="module")
def contract() -> OpenAPI:
    return OpenAPI.from_file_path("packages/contracts/openapi.yaml")


@contextmanager
def login(manifest: RunManifest, user: str) -> Iterator[httpx.Client]:
    with httpx.Client(
        base_url=manifest.url("web"), follow_redirects=False, timeout=15
    ) as client:
        response = complete_fixture_login(client, manifest, user=user)
        assert response.status_code == 303
        assert response.headers["location"] == "/projects"
        yield client


def permission_args(manifest: RunManifest, user: str, project_id: str, role: str = "viewer") -> list[str]:
    project = manifest.project(project_id)
    return [
        "--scope", "project",
        "--user", user,
        "--tenant", manifest.tenant_symbol(project["tenant_id"]),
        "--project", manifest.project_symbol(project_id),
        "--role", role,
    ]


def permission_state(manifest: RunManifest, user: str, project_id: str) -> dict[str, Any]:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT permissions_version FROM users WHERE id = %s", (manifest.seed(user)["id"],))
        version = cursor.fetchone()[0]
        cursor.execute(
            "SELECT enabled, role FROM project_memberships WHERE project_id = %s AND user_id = %s",
            (project_id, manifest.seed(user)["id"]),
        )
        row = cursor.fetchone()
        cursor.execute("SELECT count(*) FROM identity_audit WHERE user_id = %s", (manifest.seed(user)["id"],))
        audit_count = cursor.fetchone()[0]
    return {
        "permissions_version": version,
        "membership": None if row is None else {"enabled": row[0], "role": row[1]},
        "audit_count": audit_count,
    }


def user_state(manifest: RunManifest, user: str) -> dict[str, Any]:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT enabled, permissions_version FROM users WHERE id = %s",
            (manifest.seed(user)["id"],),
        )
        enabled, version = cursor.fetchone()
        cursor.execute("SELECT count(*) FROM identity_audit WHERE user_id = %s", (manifest.seed(user)["id"],))
        audits = cursor.fetchone()[0]
    return {"enabled": enabled, "permissions_version": version, "audit_count": audits}


def validate(contract: OpenAPI, response: httpx.Response) -> None:
    contract.validate_response(ContractRequest(response.request), ContractResponse(response))
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "user",
    ["single_a", "single_b", "dual_ab", "no_projects", "tenant_split_u1", "tenant_split_u2"],
)
def test_project_list_is_exactly_current_membership_and_contract_valid(
    user: str, run_manifest: RunManifest, contract: OpenAPI
) -> None:
    with login(run_manifest, user) as client:
        response = client.get("/api/v1/projects", params={"limit": 100})
        assert response.status_code == 200
        validate(contract, response)
        body = response.json()
        assert {item["id"] for item in body["items"]} == set(run_manifest.seed(user)["project_ids"])
        project_b_id = run_manifest.data["seed_entities"]["projects"]["project_b_primary"]["id"]
        expected = {}
        for item in body["items"]:
            is_operator = user in {"single_a", "single_b"} or (
                user == "dual_ab" and item["id"] == project_b_id
            )
            expected[item["id"]] = (
                ["project.read", "task.preview", "task.read", "task.create", "task.control"]
                if is_operator
                else ["project.read", "task.read"]
            )
        assert {item["id"]: item["permissions"] for item in body["items"]} == expected
        assert body["next_cursor"] is None


def test_cross_tenant_and_same_tenant_split_users_cannot_read_each_others_projects(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    pairs = [
        ("single_a", "single_b"),
        ("single_b", "single_a"),
        ("tenant_split_u1", "tenant_split_u2"),
        ("tenant_split_u2", "tenant_split_u1"),
    ]
    for reader, owner in pairs:
        foreign_id = run_manifest.seed(owner)["project_ids"][0]
        with login(run_manifest, reader) as client:
            response = client.get(f"/api/v1/projects/{foreign_id}")
            assert response.status_code == 404
            assert response.json()["code"] == "NOT_FOUND"
            validate(contract, response)


def test_inaccessible_and_nonexistent_project_have_same_public_error_shape(
    run_manifest: RunManifest
) -> None:
    with login(run_manifest, "single_a") as client:
        inaccessible = client.get(
            f'/api/v1/projects/{run_manifest.seed("single_b")["project_ids"][0]}'
        )
        missing = client.get(f"/api/v1/projects/{uuid4()}")
    assert inaccessible.status_code == missing.status_code == 404
    left = copy.deepcopy(inaccessible.json())
    right = copy.deepcopy(missing.json())
    UUID(left.pop("trace_id"))
    UUID(right.pop("trace_id"))
    assert left == right


def test_session_project_and_unauthenticated_error_responses_validate_against_openapi(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        for path in ("/api/v1/session", f"/api/v1/projects/{project_id}"):
            response = client.get(path)
            assert response.status_code == 200
            validate(contract, response)
    with httpx.Client(base_url=run_manifest.url("web"), follow_redirects=False) as anonymous:
        response = anonymous.get("/api/v1/session")
        assert response.status_code == 401
        validate(contract, response)


def test_runtime_openapi_only_publishes_phase1a_routes(run_manifest: RunManifest) -> None:
    document = httpx.get(f'{run_manifest.url("api")}/openapi.json').json()
    paths = set(document["paths"])
    required = {
        "/health/live",
        "/health/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/callback",
        "/api/v1/auth/logout",
        "/api/v1/session",
        "/api/v1/projects",
        "/api/v1/projects/{project_id}",
    }
    assert paths == required
    assert not any("task" in path or "scope" in path or "artifact" in path for path in paths)


def test_cursor_is_signed_user_bound_and_permissions_version_bound(
    run_manifest: RunManifest, control, contract: OpenAPI
) -> None:
    with login(run_manifest, "dual_ab") as owner:
        first = owner.get("/api/v1/projects", params={"limit": 1})
        validate(contract, first)
        cursor = first.json()["next_cursor"]
        assert cursor
        encoded_payload = cursor.split(".", 1)[0]
        payload = json.loads(
            base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        )
        assert payload["exp"] - payload["iat"] == 900
        second = owner.get("/api/v1/projects", params={"limit": 1, "cursor": cursor})
        assert second.status_code == 200
        validate(contract, second)
        assert second.json()["items"][0]["id"] != first.json()["items"][0]["id"]

        payload_part, signature_part = cursor.split(".", 1)
        index = len(signature_part) // 2
        replacement = "A" if signature_part[index] != "A" else "B"
        tampered_cursor = (
            f"{payload_part}.{signature_part[:index]}{replacement}{signature_part[index + 1:]}"
        )
        tampered = owner.get(
            "/api/v1/projects", params={"limit": 1, "cursor": tampered_cursor}
        )
        assert tampered.status_code == 422
        assert tampered.json()["code"] == "VALIDATION_FAILED"
        validate(contract, tampered)

        with login(run_manifest, "single_a") as other:
            cross_user = other.get(
                "/api/v1/projects", params={"limit": 1, "cursor": cursor}
            )
            assert cross_user.status_code == 422
            assert cross_user.json()["code"] == "VALIDATION_FAILED"
            validate(contract, cross_user)

        control.run("cursor", "bump-permissions-version", "--user", "dual_ab")
        stale = owner.get("/api/v1/projects", params={"limit": 1, "cursor": cursor})
        assert stale.status_code == 410
        assert stale.json()["code"] == "CURSOR_EXPIRED"
        validate(contract, stale)


def test_expired_cursor_returns_410(run_manifest: RunManifest, control) -> None:
    control.run(
        "api", "restart", "--profile", "issuer_fixture", "--cursor-ttl-seconds", "1"
    )
    control.run("api", "wait-ready")
    try:
        with login(run_manifest, "dual_ab") as client:
            cursor = client.get("/api/v1/projects", params={"limit": 1}).json()["next_cursor"]
            assert cursor
            time.sleep(2)
            response = client.get("/api/v1/projects", params={"limit": 1, "cursor": cursor})
            assert response.status_code == 410
            assert response.json()["code"] == "CURSOR_EXPIRED"
    finally:
        control.run(
            "api", "restart", "--profile", "issuer_fixture", "--cursor-ttl-seconds", "900"
        )
        control.run("api", "wait-ready")


def test_limit_validation_is_structured_and_route_surface_is_phase1a_only(
    run_manifest: RunManifest
) -> None:
    with login(run_manifest, "single_a") as client:
        for value in (0, 101):
            response = client.get("/api/v1/projects", params={"limit": value})
            assert response.status_code == 422
            assert response.json()["code"] == "VALIDATION_FAILED"
        project_id = run_manifest.seed("single_a")["project_ids"][0]
        for path in (
            f"/api/v1/projects/{project_id}/tasks",
            f"/api/v1/projects/{project_id}/scopes",
            f"/api/v1/projects/{project_id}/artifacts",
        ):
            response = client.get(path)
            assert response.status_code == 404


def test_permission_change_version_and_audit_commit_atomically_and_noop_is_idempotent(
    run_manifest: RunManifest, control
) -> None:
    user = "single_a"
    project = run_manifest.seed(user)["project_ids"][0]
    before = permission_state(run_manifest, user, project)
    role = before["membership"]["role"]
    args = permission_args(run_manifest, user, project, role)
    changed = control.run("permissions", "revoke", *args)
    after = permission_state(run_manifest, user, project)
    try:
        assert changed["changed"] is True
        assert after["permissions_version"] == before["permissions_version"] + 1
        assert after["audit_count"] == before["audit_count"] + 1
        assert after["membership"] == {"enabled": False, "role": role}
        noop = control.run("permissions", "revoke", *args)
        unchanged = permission_state(run_manifest, user, project)
        assert noop["changed"] is False
        assert unchanged == after
    finally:
        control.run("permissions", "grant", *args)


def test_audit_failure_rolls_back_membership_and_version(run_manifest: RunManifest, control) -> None:
    user = "single_a"
    project = run_manifest.seed(user)["project_ids"][0]
    before = permission_state(run_manifest, user, project)
    args = permission_args(run_manifest, user, project, before["membership"]["role"])
    control.run_expect_failure("permissions", "revoke", *args, "--simulate-audit-failure")
    after = permission_state(run_manifest, user, project)
    assert after == before


def test_revoked_tenant_membership_hides_all_projects_in_that_tenant_but_keeps_session(
    run_manifest: RunManifest, control
) -> None:
    user = "dual_ab"
    tenant_symbol = "tenant_a"
    tenant_id = run_manifest.data["seed_entities"]["tenants"][tenant_symbol]["id"]
    tenant_project_ids = {
        project["id"]
        for project in run_manifest.data["seed_entities"]["projects"].values()
        if project["tenant_id"] == tenant_id
    }
    args = [
        "--scope", "tenant", "--user", user, "--tenant", tenant_symbol, "--role", "viewer"
    ]
    with login(run_manifest, user) as client:
        before_version = client.get("/api/v1/session").json()["permissions_version"]
        control.run("permissions", "revoke", *args)
        try:
            response = client.get("/api/v1/projects", params={"limit": 100})
            assert response.status_code == 200
            observed = {item["id"] for item in response.json()["items"]}
            assert observed.isdisjoint(tenant_project_ids)
            assert observed == set(run_manifest.seed(user)["project_ids"]) - tenant_project_ids
            session = client.get("/api/v1/session")
            assert session.status_code == 200
            assert session.json()["permissions_version"] == before_version + 1
        finally:
            control.run("permissions", "grant", *args)


def test_user_status_version_audit_and_noop_are_atomic(run_manifest: RunManifest, control) -> None:
    user = "viewer_a"
    before = user_state(run_manifest, user)
    assert before["enabled"] is True
    disabled_result = control.run("user", "disable", "--user", user)
    try:
        disabled = user_state(run_manifest, user)
        assert disabled_result["changed"] is True
        assert disabled == {
            "enabled": False,
            "permissions_version": before["permissions_version"] + 1,
            "audit_count": before["audit_count"] + 1,
        }
        noop_result = control.run("user", "disable", "--user", user)
        assert noop_result["changed"] is False
        assert user_state(run_manifest, user) == disabled
    finally:
        control.run("user", "enable", "--user", user)
    restored = user_state(run_manifest, user)
    assert restored["enabled"] is True
    assert restored["permissions_version"] == before["permissions_version"] + 2
    assert restored["audit_count"] == before["audit_count"] + 2
