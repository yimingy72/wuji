"""P11 Task creation entry: real PostgreSQL, published profiles, signed HTTP."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from support.http_capture import RecordedTestClient
from support import identity_provider
from support.p03 import prepared, seed_control_actor
from wuji_core.admission.registry import (
    ModelProfile,
    RuntimeProfile,
    register_published_profile,
)
from wuji_core.contracts.execution import ExecutionLimits, TaskCreate
from wuji_core.execution.tasks import TaskService
from wuji_core.http import create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.tasks import create_task_router
from wuji_core.persistence.uow import DomainError


OWNER = ("tenant-fixture", "project-fixture", "task-fixture")
BASE = "/api/v2/tasks"
# The published runtime profile must name the Worker lock the Task Pod image
# actually ships; the owner command refuses a frozen definition that names
# anything else.
LOCK_DIGEST = sha256((Path(__file__).resolve().parents[2] / "packages" /
    "maf-worker" / "uv.lock").read_bytes()).hexdigest()
PUBLISHED_AT = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)


def model_profile() -> ModelProfile:
    return ModelProfile(
        ref="fixture-model-v1",
        revision="1",
        published_at=PUBLISHED_AT,
        capability_ref="synthetic-chat-completions-v1",
        protocol="chat_completions",
        client_model="synthetic-model",
        upstream_model="synthetic-model",
        gateway_url="http://127.0.0.1:8081/v1/chat/completions",
        task_key_ref="model-key",
        max_retries=0,
    )


def runtime_profile() -> RuntimeProfile:
    return RuntimeProfile(
        ref="fixture-runtime-v1",
        revision="1",
        published_at=PUBLISHED_AT,
        lock_digest=LOCK_DIGEST,
        limits=ExecutionLimits(
            max_work_items=4,
            max_reason_runs=2,
            max_model_requests=8,
            max_tool_calls=8,
            max_single_output_bytes=32768,
            max_total_output_bytes=131072,
            max_elapsed_seconds=1800,
            max_attempts_per_work=2,
            repair_attempts=0,
        ),
        chunk_bytes=512,
        buffer_bytes=4096,
        idle_timeout_seconds=15.0,
        total_timeout_seconds=60.0,
        max_pending_operations=4,
        max_inflight_tools=1,
        max_inflight_model_requests=1,
        allowed_tool_refs=["workspace-read-v1"],
    )


def publish_profiles(connection) -> None:
    register_published_profile(
        connection, tenant_id=OWNER[0], kind="model", document=model_profile()
    )
    register_published_profile(
        connection, tenant_id=OWNER[0], kind="runtime", document=runtime_profile()
    )


@contextmanager
def creation_case(environment, audit_directory):
    provider = identity_provider.TestIdentityProvider(audit_path=audit_directory / "identity-events.jsonl")
    with prepared(environment) as uow:
        with environment.migration_connection() as connection:
            seed_control_actor(connection)
            publish_profiles(connection)
        verifier = TokenVerifier(
            public_key_pem=provider.public_key_pem,
            issuer=provider.issuer,
            audience=provider.audience,
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=verifier,
                routers=[create_task_router(TaskService(uow))],
            ),
            audit_path=audit_directory / "task-creation-http.jsonl",
        )
        try:
            yield SimpleNamespace(
                environment=environment,
                uow=uow,
                provider=provider,
                client=client,
                operator=provider.issue(
                    subject="control-fixture",
                    tenant_id=OWNER[0],
                    roles=["operator"],
                ),
            )
        finally:
            client.close()


def payload(**overrides) -> dict:
    document = {
        "schema_version": "wuji.api.v2",
        "project_id": OWNER[1],
        "name": "Created fixture task",
        "scenario": "web_single",
        "goal": {
            "text": "Read the fixture version",
            "criteria": [
                {
                    "criterion_id": "version",
                    "object": "fixture bytes",
                    "condition": "version captured",
                    "evidence_requirements": ["sealed bytes"],
                    "allowed_methods": ["deterministic"],
                    "responsible_party": "fixture-checker",
                    "required": True,
                }
            ],
        },
        "authorization_scope": [
            {"host": "fixture.invalid", "protocol": "https", "port": 443}
        ],
        "authorization_expires_at": "2099-01-01T00:00:00Z",
        "model_profile_ref": "fixture-model-v1",
        "runtime_profile_ref": "fixture-runtime-v1",
        "budget": {"amount": "5", "currency": "USD"},
    }
    document.update(overrides)
    return document


def auth(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token, "Idempotency-Key": "create-fixture-1"}


def create(case, *, body=None, token=None, key="create-fixture-1"):
    headers = {"Authorization": "Bearer " + (token or case.operator)}
    if key is not None:
        headers["Idempotency-Key"] = key
    return case.client.post(BASE, headers=headers, json=body or payload())


def test_explicit_entry_points_preserve_path_query_and_match_scope():
    task = TaskCreate.model_validate(
        payload(entry_points=["https://fixture.invalid/read?format=plain"])
    )
    assert TaskService.start_points(task) == [
        "https://fixture.invalid/read?format=plain"
    ]

    with pytest.raises(DomainError) as mismatch:
        TaskService.start_points(
            TaskCreate.model_validate(
                payload(entry_points=["https://other.invalid/read"])
            )
        )
    assert mismatch.value.code == "INVALID_REFERENCE"


def test_task_creation_persists_a_non_running_task_with_only_creator_access(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        response = create(case)
        assert response.status_code == 201, response.text
        view = response.json()
        assert view == {
            "task_id": view["task_id"],
            "tenant_id": OWNER[0],
            "project_id": OWNER[1],
            "version": "1",
            "name": "Created fixture task",
            "scenario": "web_single",
            "desired_state": "pause",
            "observed_state": "ready",
            "goal_revision": "1",
            "execution_epoch": "1",
            "activated_at": None,
            "close_trigger": None,
            "result_outcome": None,
            "allowed_actions": [],
        }

        with db_environment.migration_connection() as connection:
            stored = connection.execute(
                """SELECT definition_json,definition_digest,desired_state,observed_state
                FROM vnext.task WHERE task_id=%s""",
                (view["task_id"],),
            ).fetchone()
            definition = json.loads(stored[0])
            assert sha256(stored[0].encode()).hexdigest() == stored[1]
            assert stored[2:] == ("pause", "ready")
            assert definition["task"]["name"] == "Created fixture task"
            assert definition["start_points"] == ["https://fixture.invalid:443"]
            assert definition["model_profile"] == model_profile().model_dump(mode="json")
            assert definition["runtime_profile"] == runtime_profile().model_dump(mode="json")
            assert definition["lock_digest"] == LOCK_DIGEST
            access = connection.execute(
                """SELECT subject,can_read,can_write,can_control,clearance
                FROM vnext.task_access WHERE task_id=%s""",
                (view["task_id"],),
            ).fetchall()
            assert access == [("control-fixture", True, True, True, 1)]
            policy = connection.execute(
                "SELECT policy_version FROM vnext.task_assessment_policy WHERE task_id=%s",
                (view["task_id"],),
            ).fetchone()
            assert policy == ("assessment-policy-v1",)
            for table in ("claim_revision", "intent_revision", "outbox", "agent_run", "work_item"):
                assert connection.execute(
                    f"SELECT count(*) FROM vnext.{table} WHERE task_id=%s",
                    (view["task_id"],),
                ).fetchone() == (0,)


def test_task_creation_replays_the_same_key_and_rejects_a_different_body(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        first = create(case)
        assert first.status_code == 201, first.text
        replay = create(case)
        assert replay.status_code == 201
        assert replay.json()["task_id"] == first.json()["task_id"]

        conflict = create(case, body=payload(name="Different task"))
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["code"] == "INPUT_DIGEST_CONFLICT"
        with db_environment.migration_connection() as connection:
            created = connection.execute(
                "SELECT count(*) FROM vnext.task WHERE project_id=%s AND task_id<>%s",
                (OWNER[1], OWNER[2]),
            ).fetchone()
            assert created == (1,)


def test_task_creation_requires_project_control_permission_and_auth(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        agent = case.provider.issue(
            subject="agent-fixture", tenant_id=OWNER[0], roles=["agent"]
        )
        denied = create(case, token=agent)
        assert denied.status_code == 404, denied.text
        assert denied.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"

        foreign = case.provider.issue(
            subject="control-fixture", tenant_id="tenant-other", roles=["operator"]
        )
        other_project = create(case, token=foreign, body=payload(project_id="project-other"))
        assert other_project.status_code == 404, other_project.text

        anonymous = case.client.post(
            BASE,
            headers={"Idempotency-Key": "create-fixture-1"},
            json=payload(),
        )
        assert anonymous.status_code == 401
        missing_key = case.client.post(
            BASE, headers={"Authorization": "Bearer " + case.operator}, json=payload()
        )
        assert missing_key.status_code == 422
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.task WHERE project_id=%s AND task_id<>%s",
                (OWNER[1], OWNER[2]),
            ).fetchone() == (0,)


def test_task_creation_rejects_unpublished_revoked_and_expired_inputs(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        unknown = create(
            case, body=payload(model_profile_ref="missing-model"), key="k-unknown"
        )
        assert unknown.status_code == 422, unknown.text
        assert unknown.json()["code"] == "INVALID_REFERENCE"

        expired = create(
            case,
            body=payload(authorization_expires_at="2020-01-01T00:00:00Z"),
            key="k-expired",
        )
        assert expired.status_code == 422, expired.text

        with db_environment.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.published_profile SET revoked=true WHERE kind='runtime'"
            )
        revoked = create(case, key="k-revoked")
        assert revoked.status_code == 422, revoked.text
        assert revoked.json()["code"] == "INVALID_REFERENCE"
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.task WHERE project_id=%s AND task_id<>%s",
                (OWNER[1], OWNER[2]),
            ).fetchone() == (0,)
