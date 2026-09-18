"""First-use Task catalog/readiness checks against real PG and ASGI routes."""

from hashlib import sha256
import json

import pytest

from test_task_creation import OWNER, payload
from support.first_use import (
    bearer,
    create_task,
    first_use_case,
    task_view,
)


def _task_rows(connection, task_id):
    return connection.execute(
        "SELECT definition_json,definition_digest FROM vnext.task WHERE task_id=%s",
        (task_id,),
    ).fetchone()


def _expire_task(connection, task_id):
    raw, _digest = _task_rows(connection, task_id)
    definition = json.loads(raw)
    definition["task"]["authorization_expires_at"] = "2000-01-01T00:00:00Z"
    saved = json.dumps(definition, separators=(",", ":"), sort_keys=True)
    connection.execute(
        "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
        (saved, sha256(saved.encode()).hexdigest(), task_id),
    )


def test_catalog_preserves_entry_path_and_has_no_implicit_start(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(
            case,
            payload(entry_points=["https://fixture.invalid/read?format=plain"]),
            key="catalog-entry-point",
        )
        task_id = created["task_id"]

        listed = case.client.get(
            f"/api/v2/tasks?project_id={OWNER[1]}&limit=20",
            headers=bearer(case),
        )
        assert listed.status_code == 200, listed.text
        assert any(item["task_id"] == task_id for item in listed.json()["items"])

        detail = task_view(case, task_id)
        assert detail["desired_state"] == "pause"
        assert detail["observed_state"] == "ready"

        launch = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert launch.status_code == 200, launch.text
        assert launch.json()["phase"] == "not_requested"
        assert launch.json()["phase_status"] == "not_requested"
        assert launch.json()["operation_id"] is None

        with db_environment.migration_connection() as connection:
            definition, _ = _task_rows(connection, task_id)
            assert json.loads(definition)["start_points"] == [
                "https://fixture.invalid/read?format=plain"
            ]
            assert connection.execute(
                "SELECT count(*) FROM vnext.model_call WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (0,)
            assert connection.execute(
                "SELECT count(*) FROM vnext.tool_call WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (0,)


def test_task_list_cursor_is_last_returned_item_not_limit_plus_one(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = [
            create_task(case, payload(name=f"catalog-{index}"), key=f"catalog-{index}")
            for index in range(3)
        ]
        first = case.client.get(
            f"/api/v2/tasks?project_id={OWNER[1]}&limit=2",
            headers=bearer(case),
        )
        assert first.status_code == 200, first.text
        first_items = first.json()["items"]
        assert len(first_items) == 2
        cursor = first.json()["next_cursor"]
        assert cursor == first_items[-1]["task_id"]

        second = case.client.get(
            f"/api/v2/tasks?project_id={OWNER[1]}&limit=2&cursor={cursor}",
            headers=bearer(case),
        )
        assert second.status_code == 200, second.text
        second_ids = {item["task_id"] for item in second.json()["items"]}
        assert {item["task_id"] for item in first_items}.isdisjoint(second_ids)
        full = case.client.get(
            f"/api/v2/tasks?project_id={OWNER[1]}&limit=100",
            headers=bearer(case),
        )
        assert full.status_code == 200, full.text
        expected_prefix = [item["task_id"] for item in full.json()["items"][:4]]
        assert [item["task_id"] for item in first_items] + [
            item["task_id"] for item in second.json()["items"]
        ] == expected_prefix


def test_options_do_not_infer_real_model_permission_from_profile_name(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        create_task(case, payload(), key="catalog-options")
        response = case.client.get(
            f"/api/v2/projects/{OWNER[1]}/task-options",
            headers=bearer(case),
        )
        assert response.status_code == 200, response.text
        document = response.json()
        assert document["project_id"] == OWNER[1]
        assert document["model_profiles"]
        assert document["runtime_profiles"]
        assert all(
            option["real_model_allowed"] is False
            for option in document["model_profiles"] + document["runtime_profiles"]
        )
        serialized = json.dumps(document)
        assert "task_key_ref" not in serialized
        assert "gateway_url" not in serialized


def test_read_capabilities_cannot_start_and_expired_scope_cannot_start(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="catalog-readiness")
        task_id = created["task_id"]
        reader = case.provider.issue(
            subject="catalog-reader", tenant_id=OWNER[0], roles=["reader"]
        )
        with db_environment.migration_connection() as connection:
            connection.execute(
                """INSERT INTO vnext.task_access(
                    tenant_id,project_id,task_id,subject,can_read,can_control,clearance
                ) VALUES(%s,%s,%s,%s,true,false,1)
                ON CONFLICT (tenant_id,project_id,task_id,subject)
                DO UPDATE SET can_read=true,can_control=false""",
                (*OWNER[:2], task_id, "catalog-reader"),
            )

        reader_view = task_view(case, task_id, reader)
        assert reader_view["allowed_actions"] == []
        reader_readiness = case.client.get(
            f"/api/v2/tasks/{task_id}/readiness", headers=bearer(case, reader)
        )
        assert reader_readiness.status_code == 200, reader_readiness.text
        assert reader_readiness.json()["can_request_start"] is False

        with db_environment.migration_connection() as connection:
            _expire_task(connection, task_id)
        owner_readiness = case.client.get(
            f"/api/v2/tasks/{task_id}/readiness", headers=bearer(case)
        )
        assert owner_readiness.status_code == 200, owner_readiness.text
        assert owner_readiness.json()["can_request_start"] is False


def test_create_idempotent_replay_after_task_revoke_is_hidden(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        body = payload(name="revoked replay")
        created = create_task(case, body, key="revoked-create")
        with db_environment.migration_connection() as connection:
            connection.execute(
                "UPDATE vnext.task_access SET can_read=false,can_control=false WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
                (*OWNER, "control-fixture"),
            )
        replay = case.client.post(
            "/api/v2/tasks",
            headers={**bearer(case), "Idempotency-Key": "revoked-create"},
            json=body,
        )
        assert replay.status_code == 404, replay.text
        assert replay.json()["code"] == "NOT_FOUND_OR_FORBIDDEN"
        assert created["task_id"]
