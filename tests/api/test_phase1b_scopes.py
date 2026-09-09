from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit

import httpx
import pytest

from conftest import Control, RunManifest, complete_fixture_login
from test_projects_permissions import contract, validate


pytestmark = pytest.mark.platform


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(run_manifest: RunManifest):
    control = Control(run_manifest)
    control.run("api", "restart", "--profile", "issuer_fixture")
    control.run("api", "wait-ready")
    try:
        yield
    finally:
        control.run("api", "restart", "--profile", "keycloak")
        control.run("api", "wait-ready")


@contextmanager
def login(manifest: RunManifest, user: str) -> Iterator[httpx.Client]:
    with httpx.Client(
        base_url=manifest.url("web"), follow_redirects=False, timeout=15
    ) as client:
        response = complete_fixture_login(client, manifest, user=user)
        assert response.status_code == 303
        assert response.headers["location"] == "/projects"
        yield client


def _scope_page(client: httpx.Client, project_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/projects/{project_id}/scopes")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body.get("items"), list)
    assert body["items"], "the B1 seed must expose at least one approved scope"
    return body["items"]


def _draft(scope: dict[str, Any], *, target_url: str | None = None) -> dict[str, Any]:
    origin = scope["origins"][0]
    parsed = urlsplit(origin)
    allowed = next(
        prefix for prefix in scope["allowed_path_prefixes"] if prefix != "/"
    ) if any(prefix != "/" for prefix in scope["allowed_path_prefixes"]) else "/"
    path = allowed.rstrip("/") + "/a" if allowed != "/" else "/a"
    if target_url is None:
        target_url = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    return {
        "name": "B1 最小范围预览",
        "scope": scope["binding"],
        "target_url": target_url,
        "tool": "http_observe",
        "method": "GET",
        "limits": scope["limits"],
    }


def _with_host_case_and_default_port(scope: dict[str, Any], path: str) -> str:
    parsed = urlsplit(scope["origins"][0])
    host = parsed.hostname or ""
    host = host.upper()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    default_port = 443 if parsed.scheme.casefold() == "https" else 80
    return urlunsplit((parsed.scheme.upper(), f"{host}:{parsed.port or default_port}", path, "", ""))


def test_operator_can_list_scope_and_preview_canonical_effective_scope(
    run_manifest: RunManifest, contract,
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        scopes = _scope_page(client, project_id)
        scope = scopes[0]
        allowed = next(
            prefix for prefix in scope["allowed_path_prefixes"] if prefix != "/"
        ) if any(prefix != "/" for prefix in scope["allowed_path_prefixes"]) else "/"
        path = allowed.rstrip("/") + "/a" if allowed != "/" else "/a"
        draft = _draft(scope, target_url=_with_host_case_and_default_port(scope, path))
        draft["limits"] = dict(scope["limits"])
        draft["limits"]["max_total_requests"] = min(7, scope["limits"]["max_total_requests"])
        response = client.post(
            f"/api/v1/projects/{project_id}/task-previews",
            headers={
                "Origin": run_manifest.url("web"),
                "X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"],
            },
            json=draft,
        )
        assert response.status_code == 200, response.text
        validate(contract, response)
        preview = response.json()
        assert preview["project_id"] == project_id
        assert preview["draft"]["scope"] == scope["binding"]
        assert preview["draft"]["target_url"] == _draft(scope)["target_url"]
        assert preview["can_create"] is False
        assert [blocker["code"] for blocker in preview["blockers"]] == ["CREATION_UNAVAILABLE"]
        assert preview["effective_scope"]["limits"]["max_total_requests"] == draft["limits"]["max_total_requests"]


def test_path_outside_scope_is_rejected_without_contacting_target(
    run_manifest: RunManifest,
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        scope = _scope_page(client, project_id)[0]
        excluded = scope["excluded_path_prefixes"][0]
        response = client.post(
            f"/api/v1/projects/{project_id}/task-previews",
            headers={
                "Origin": run_manifest.url("web"),
                "X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"],
            },
            json=_draft(scope, target_url=_with_host_case_and_default_port(scope, excluded)),
        )
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["can_create"] is False
        assert any(blocker["code"] == "SCOPE_DENIED" for blocker in preview["blockers"])


def test_scope_binding_from_another_project_is_not_accepted(
    run_manifest: RunManifest,
) -> None:
    project_a = run_manifest.seed("single_a")["project_ids"][0]
    project_b = run_manifest.seed("single_b")["project_ids"][0]
    assert project_a != project_b
    with login(run_manifest, "single_b") as other_client:
        foreign_scope = _scope_page(other_client, project_b)[0]
    with login(run_manifest, "single_a") as client:
        local_scope = _scope_page(client, project_a)[0]
        response = client.post(
            f"/api/v1/projects/{project_a}/task-previews",
            headers={
                "Origin": run_manifest.url("web"),
                "X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"],
            },
            json=_draft(local_scope) | {"scope": foreign_scope["binding"]},
        )
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"


def test_viewer_cannot_preview_and_operator_preview_requires_csrf(
    run_manifest: RunManifest,
) -> None:
    viewer_project = run_manifest.seed("viewer_a")["project_ids"][0]
    with login(run_manifest, "viewer_a") as viewer:
        scope = _scope_page(viewer, viewer_project)[0]
        csrf = viewer.get("/api/v1/session").json()["csrf_token"]
        denied = viewer.post(
            f"/api/v1/projects/{viewer_project}/task-previews",
            headers={"Origin": run_manifest.url("web"), "X-CSRF-Token": csrf},
            json=_draft(scope),
        )
        assert denied.status_code == 403
        assert denied.json()["code"] == "FORBIDDEN"

    operator_project = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as operator:
        scope = _scope_page(operator, operator_project)[0]
        missing_csrf = operator.post(
            f"/api/v1/projects/{operator_project}/task-previews",
            headers={"Origin": run_manifest.url("web")},
            json=_draft(scope),
        )
        assert missing_csrf.status_code == 403
        assert missing_csrf.json()["code"] == "FORBIDDEN"
