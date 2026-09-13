"""P11 real PostgreSQL and signed HTTP checks; execution is window-owned."""

from uuid import uuid4

import pytest

from support.http_capture import RecordedTestClient
from support.p03 import access
from test_knowledge_admission import OWNER, TASK
from test_work_state_guards import OPERATOR, control_case
from wuji_core.contracts.execution import CommandReceipt
from wuji_core.execution.control_api import ControlAPI, task_for_work
from wuji_core.http import create_app
from wuji_core.http.commands import create_command_router
from wuji_core.persistence import control_api_schema
from wuji_core.persistence.uow import DomainError


WORK = "work-b"


def _install_locator(case):
    with case.env.migration_connection() as connection:
        assert connection.execute(
            "SELECT 1 FROM vnext.schema_migration WHERE head=%s",
            (control_api_schema.HEAD,),
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT to_regprocedure('vnext.task_for_work(text)')"
        ).fetchone()[0] is not None


def _client(case, audit_directory):
    token = case.provider.issue(
        subject="operator-fixture",
        tenant_id=OWNER[0],
        roles=["operator"],
    )
    client = RecordedTestClient(
        create_app(
            token_verifier=case.verifier,
            routers=[create_command_router(ControlAPI(case.control))],
        ),
        audit_path=audit_directory / "control-api-http.jsonl",
    )
    return client, token


def _post(client, token, path, command, version):
    return client.post(
        path,
        json={
            "schema_version": "wuji.api.v2",
            "command": command,
            "expected_version": str(version),
            "reason": "P11 signed HTTP control check",
        },
        headers={
            "Authorization": "Bearer " + token,
            "Idempotency-Key": str(uuid4()),
        },
    )


def _receipt(response, resource_type, resource_id):
    assert response.status_code == 202, response.text
    receipt = CommandReceipt.model_validate(response.json())
    assert receipt.disposition.value == "accepted"
    assert receipt.resource_ref.entity_type.value == resource_type
    assert receipt.resource_ref.id == resource_id
    return receipt


def test_signed_http_applies_task_and_work_commands_through_control_service(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        _install_locator(case)
        client, token = _client(case, audit_directory)
        try:
            task = case.control.read_task(OPERATOR, TASK)
            _receipt(
                _post(
                    client,
                    token,
                    f"/api/v2/tasks/{TASK}/commands",
                    "start",
                    task["control_version"],
                ),
                "task",
                TASK,
            )

            work = case.control.read_work(OPERATOR, TASK, WORK)
            _receipt(
                _post(
                    client,
                    token,
                    f"/api/v2/work-items/{WORK}/commands",
                    "hold",
                    work["revision"],
                ),
                "work_item",
                WORK,
            )
            work = case.control.read_work(OPERATOR, TASK, WORK)
            assert work["desired_state"] == "hold"
            _receipt(
                _post(
                    client,
                    token,
                    f"/api/v2/work-items/{WORK}/commands",
                    "resume",
                    work["revision"],
                ),
                "work_item",
                WORK,
            )

            task = case.control.read_task(OPERATOR, TASK)
            _receipt(
                _post(
                    client,
                    token,
                    f"/api/v2/tasks/{TASK}/commands",
                    "pause",
                    task["control_version"],
                ),
                "task",
                TASK,
            )
            task = case.control.read_task(OPERATOR, TASK)
            assert task["desired_state"] == "pause"
            _receipt(
                _post(
                    client,
                    token,
                    f"/api/v2/tasks/{TASK}/commands",
                    "resume",
                    task["control_version"],
                ),
                "task",
                TASK,
            )
        finally:
            client.close()


def test_work_locator_hides_missing_and_ambiguous_global_ids(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as case:
        _install_locator(case)
        reader = access("reader-fixture", role="reader")
        for work_item_id in (WORK, "missing-work"):
            with pytest.raises(DomainError, match="NOT_FOUND_OR_FORBIDDEN"):
                task_for_work(case.control.uow, reader, work_item_id)
