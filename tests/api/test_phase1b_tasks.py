from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters

from conftest import Control, RunManifest, complete_fixture_login


pytestmark = pytest.mark.platform


class ContractRequest:
    host_url = "http://127.0.0.1:4182"
    body = None
    content_type = "application/octet-stream"

    def __init__(self, request: httpx.Request):
        self.method = request.method.lower()
        self.path = request.url.path
        self.parameters = RequestParameters(
            query=dict(request.url.params), header=dict(request.headers)
        )


class ContractResponse:
    def __init__(self, response: httpx.Response):
        self.status_code = response.status_code
        self.content_type = response.headers.get("content-type", "")
        self.headers = response.headers
        self.data = response.content


@pytest.fixture(scope="module", autouse=True)
def controlled_issuer_profile(control: Control):
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


def validate(contract: OpenAPI, response: httpx.Response) -> None:
    contract.validate_response(
        ContractRequest(response.request), ContractResponse(response)
    )
    assert response.headers["cache-control"] == "no-store"


def csrf(client: httpx.Client) -> str:
    response = client.get("/api/v1/session")
    assert response.status_code == 200, response.text
    return str(response.json()["csrf_token"])


def write_headers(client: httpx.Client, key: str | None = None) -> dict[str, str]:
    headers = {
        "Origin": str(client.base_url).rstrip("/"),
        "X-CSRF-Token": csrf(client),
    }
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def scope_page(client: httpx.Client, project_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/projects/{project_id}/scopes")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"]
    return body["items"]


def draft_for_scope(scope: dict[str, Any], *, name: str = "B2/B3 API task") -> dict[str, Any]:
    parsed = urlsplit(scope["origins"][0])
    allowed = next(
        prefix for prefix in scope["allowed_path_prefixes"] if prefix != "/"
    ) if any(prefix != "/" for prefix in scope["allowed_path_prefixes"]) else "/"
    path = allowed.rstrip("/") + "/b23" if allowed != "/" else "/b23"
    return {
        "name": name,
        "scope": scope["binding"],
        "target_url": urlunsplit((parsed.scheme, parsed.netloc, path, "", "")),
        "tool": "http_observe",
        "method": "GET",
        "limits": dict(scope["limits"]),
    }


def preview(
    client: httpx.Client, project_id: str, *, name: str = "B2/B3 API task"
) -> dict[str, Any]:
    scope = scope_page(client, project_id)[0]
    draft = draft_for_scope(scope, name=name)
    response = client.post(
        f"/api/v1/projects/{project_id}/task-previews",
        headers=write_headers(client),
        json=draft,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_create"] is True
    assert body["blockers"] == []
    return body


def create_body(task_preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "preview_id": task_preview["preview_id"],
        "input_digest": task_preview["input_digest"],
        "draft": task_preview["draft"],
    }


def create_task(
    client: httpx.Client,
    project_id: str,
    task_preview: dict[str, Any],
    key: str | None = None,
    *,
    body: dict[str, Any] | None = None,
) -> httpx.Response:
    return client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=write_headers(client, key or str(uuid4())),
        json=create_body(task_preview) if body is None else body,
    )


def assert_error(
    contract: OpenAPI, response: httpx.Response, status: int, code: str
) -> None:
    assert response.status_code == status, response.text
    validate(contract, response)
    assert response.json()["code"] == code
    UUID(response.json()["trace_id"])


def expire_preview(manifest: RunManifest, preview_id: str) -> None:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE task_previews SET expires_at = clock_timestamp() - interval '1 second' "
            "WHERE id = %s",
            (preview_id,),
        )
        assert cursor.rowcount == 1


def make_legacy_false_preview(manifest: RunManifest, preview_id: str) -> None:
    dsn = manifest.data["credentials"]["database"]["management_dsn"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE task_previews SET can_create = false, "
            "blockers = %s::jsonb WHERE id = %s",
            (
                '[{"code":"CREATION_UNAVAILABLE","message":"legacy B1 preview"}]',
                preview_id,
            ),
        )
        assert cursor.rowcount == 1


def test_create_list_snapshot_cancel_and_event_replay(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        task_preview = preview(client, project_id)
        key = str(uuid4())
        created = create_task(client, project_id, task_preview, key)
        assert created.status_code == 202, created.text
        validate(contract, created)
        receipt = created.json()
        assert receipt["kind"] == "create"
        assert receipt["disposition"] == "accepted"
        assert receipt["project_id"] == project_id
        assert receipt["accepted_task_version"] == 1
        task_id = receipt["task_id"]
        UUID(task_id)
        UUID(receipt["command_id"])
        assert receipt["idempotency_key"] == key

        receipt_read = client.get(
            f"/api/v1/projects/{project_id}/commands/{receipt['command_id']}"
        )
        assert receipt_read.status_code == 200, receipt_read.text
        validate(contract, receipt_read)
        assert receipt_read.json() == receipt
        key_lookup = client.get(
            f"/api/v1/projects/{project_id}/command-keys/{key}"
        )
        assert key_lookup.status_code == 200, key_lookup.text
        validate(contract, key_lookup)
        assert key_lookup.json() == receipt

        listed = client.get(f"/api/v1/projects/{project_id}/tasks")
        assert listed.status_code == 200, listed.text
        validate(contract, listed)
        listed_task = next(item for item in listed.json()["items"] if item["id"] == task_id)
        assert listed_task["state"] == "queued"
        assert listed_task["version"] == 1

        queued = client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert queued.status_code == 200, queued.text
        validate(contract, queued)
        queued_snapshot = queued.json()
        assert queued_snapshot["task"]["state"] == "queued"
        assert queued_snapshot["task"]["version"] == 1
        assert queued_snapshot["task"]["execution"] == {
            "active_calls": 0,
            "unknown_calls": 0,
            "egress_state": "not_granted",
        }
        assert queued_snapshot["task"]["cleanup_state"] == "not_required"
        assert queued_snapshot["task"]["assessment_outcome"] == "not_assessed"
        assert queued_snapshot["task"]["stop_reason"] is None
        assert queued_snapshot["task"]["allowed_actions"] == ["cancel"]
        initial_cursor = queued_snapshot["event_cursor"]

        cancel_key = str(uuid4())
        cancelled = client.post(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/commands",
            headers=write_headers(client, cancel_key),
            json={"action": "cancel", "expected_version": 1},
        )
        assert cancelled.status_code == 202, cancelled.text
        validate(contract, cancelled)
        cancel_receipt = cancelled.json()
        assert cancel_receipt["kind"] == "cancel"
        assert cancel_receipt["task_id"] == task_id
        assert cancel_receipt["accepted_task_version"] == 2

        snapshot = client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert snapshot.status_code == 200, snapshot.text
        validate(contract, snapshot)
        cancelled_task = snapshot.json()["task"]
        assert cancelled_task["state"] == "cancelled"
        assert cancelled_task["version"] == 2
        assert cancelled_task["allowed_actions"] == []
        assert cancelled_task["stop_reason"] == "user_cancelled"
        assert cancelled_task["execution"]["active_calls"] == 0
        assert cancelled_task["execution"]["unknown_calls"] == 0
        assert cancelled_task["execution"]["egress_state"] == "not_granted"

        events = client.get(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/events",
            params={"after": initial_cursor, "limit": 1},
        )
        assert events.status_code == 200, events.text
        validate(contract, events)
        event_page = events.json()
        assert event_page["items"]
        assert any(
            event["aggregate_version"] == 2 and event["type"] == "task.changed"
            for event in event_page["items"]
        )


def test_same_key_replay_and_two_concurrent_requests_create_one_task(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        task_name = f"concurrent same key {uuid4()}"
        task_preview = preview(client, project_id, name=task_name)
        key = str(uuid4())

        def send() -> httpx.Response:
            return create_task(client, project_id, task_preview, key)

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: send(), range(2)))
        for response in responses:
            assert response.status_code == 202, response.text
            validate(contract, response)
        receipts = [response.json() for response in responses]
        assert len({receipt["task_id"] for receipt in receipts}) == 1
        assert len({receipt["command_id"] for receipt in receipts}) == 1
        assert len({receipt["request_digest"] for receipt in receipts}) == 1
        assert all(receipt["idempotency_key"] == key for receipt in receipts)

        replay = create_task(client, project_id, task_preview, key)
        assert replay.status_code == 202
        validate(contract, replay)
        assert replay.json() == receipts[0]
        listed = client.get(f"/api/v1/projects/{project_id}/tasks")
        assert listed.status_code == 200
        matching = [item for item in listed.json()["items"] if item["name"] == task_name]
        assert len(matching) == 1
        assert matching[0]["id"] == receipts[0]["task_id"]


def test_idempotency_conflict_and_control_version_replay_order(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        task_preview = preview(client, project_id, name="idempotency order")
        create_key = str(uuid4())
        created = create_task(client, project_id, task_preview, create_key)
        assert created.status_code == 202
        task_id = created.json()["task_id"]

        changed = copy.deepcopy(create_body(task_preview))
        changed["draft"]["name"] = "different request"
        mismatch = create_task(
            client, project_id, task_preview, create_key, body=changed
        )
        assert_error(contract, mismatch, 409, "IDEMPOTENCY_CONFLICT")

        cancel_key = str(uuid4())
        command_path = f"/api/v1/projects/{project_id}/tasks/{task_id}/commands"
        accepted = client.post(
            command_path,
            headers=write_headers(client, cancel_key),
            json={"action": "cancel", "expected_version": 1},
        )
        assert accepted.status_code == 202
        validate(contract, accepted)

        replay_old_version = client.post(
            command_path,
            headers=write_headers(client, cancel_key),
            json={"action": "cancel", "expected_version": 999},
        )
        assert_error(contract, replay_old_version, 409, "IDEMPOTENCY_CONFLICT")

        replay_original = client.post(
            command_path,
            headers=write_headers(client, cancel_key),
            json={"action": "cancel", "expected_version": 1},
        )
        assert replay_original.status_code == 202
        validate(contract, replay_original)
        assert replay_original.json() == accepted.json()

        new_key = str(uuid4())
        wrong_version = client.post(
            command_path,
            headers=write_headers(client, new_key),
            json={"action": "cancel", "expected_version": 1},
        )
        assert_error(contract, wrong_version, 409, "VERSION_CONFLICT")

        terminal_key = str(uuid4())
        terminal_control = client.post(
            command_path,
            headers=write_headers(client, terminal_key),
            json={"action": "cancel", "expected_version": 2},
        )
        assert_error(contract, terminal_control, 409, "INVALID_TRANSITION")


def test_invalid_preview_inputs_expired_preview_and_legacy_b1_preview(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        input_preview = preview(client, project_id, name="invalid input")
        invalid_digest = create_body(input_preview)
        invalid_digest["input_digest"] = "0" * 64
        mismatch = create_task(
            client,
            project_id,
            input_preview,
            str(uuid4()),
            body=invalid_digest,
        )
        assert_error(contract, mismatch, 422, "VALIDATION_FAILED")

        expired_preview = preview(client, project_id, name="expired preview")
        expire_preview(run_manifest, expired_preview["preview_id"])
        expired = create_task(client, project_id, expired_preview, str(uuid4()))
        assert_error(contract, expired, 409, "PREVIEW_EXPIRED")

        legacy_preview = preview(client, project_id, name="legacy false preview")
        make_legacy_false_preview(run_manifest, legacy_preview["preview_id"])
        legacy_create = create_task(client, project_id, legacy_preview, str(uuid4()))
        assert_error(contract, legacy_create, 409, "VERSION_CONFLICT")


def test_viewer_reads_task_but_cannot_write_and_receipt_is_creator_only(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as owner:
        task_preview = preview(owner, project_id, name="viewer boundary")
        key = str(uuid4())
        created = create_task(owner, project_id, task_preview, key)
        assert created.status_code == 202
        receipt = created.json()
        task_id = receipt["task_id"]

        with login(run_manifest, "dual_ab") as viewer:
            listing = viewer.get(f"/api/v1/projects/{project_id}/tasks")
            assert listing.status_code == 200, listing.text
            validate(contract, listing)
            assert any(item["id"] == task_id for item in listing.json()["items"])

            snapshot = viewer.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
            assert snapshot.status_code == 200
            validate(contract, snapshot)
            assert snapshot.json()["task"]["allowed_actions"] == []

            viewer_create = create_task(
                viewer, project_id, task_preview, str(uuid4())
            )
            assert_error(contract, viewer_create, 403, "FORBIDDEN")

            viewer_control = viewer.post(
                f"/api/v1/projects/{project_id}/tasks/{task_id}/commands",
                headers=write_headers(viewer, str(uuid4())),
                json={"action": "cancel", "expected_version": 1},
            )
            assert_error(contract, viewer_control, 403, "FORBIDDEN")

            hidden_receipt = viewer.get(
                f"/api/v1/projects/{project_id}/commands/{receipt['command_id']}"
            )
            assert_error(contract, hidden_receipt, 404, "NOT_FOUND")
            hidden_key = viewer.get(
                f"/api/v1/projects/{project_id}/command-keys/{key}"
            )
            assert_error(contract, hidden_key, 404, "NOT_FOUND")

        foreign_project = run_manifest.seed("single_b")["project_ids"][0]
        foreign_tasks = owner.get(f"/api/v1/projects/{foreign_project}/tasks")
        assert_error(contract, foreign_tasks, 404, "NOT_FOUND")


def test_event_cursor_small_page_and_empty_page_preserve_position(
    run_manifest: RunManifest, contract: OpenAPI
) -> None:
    project_id = run_manifest.seed("single_a")["project_ids"][0]
    with login(run_manifest, "single_a") as client:
        task_preview = preview(client, project_id, name="event cursor")
        created = create_task(client, project_id, task_preview, str(uuid4()))
        assert created.status_code == 202
        task_id = created.json()["task_id"]
        first_snapshot = client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert first_snapshot.status_code == 200
        first_cursor = first_snapshot.json()["event_cursor"]

        cancel = client.post(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/commands",
            headers=write_headers(client, str(uuid4())),
            json={"action": "cancel", "expected_version": 1},
        )
        assert cancel.status_code == 202

        page = client.get(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/events",
            params={"after": first_cursor, "limit": 1},
        )
        assert page.status_code == 200, page.text
        validate(contract, page)
        body = page.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["aggregate_version"] == 2
        assert body["has_more"] is False
        next_cursor = body["next_cursor"]
        assert next_cursor

        empty = client.get(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/events",
            params={"after": next_cursor, "limit": 1},
        )
        assert empty.status_code == 200, empty.text
        validate(contract, empty)
        empty_body = empty.json()
        assert empty_body["items"] == []
        assert empty_body["has_more"] is False
        assert empty_body["next_cursor"] == next_cursor
