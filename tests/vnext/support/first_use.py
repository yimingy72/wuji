"""Shared real-PG/ASGI setup for the first-use API tests."""

from contextlib import contextmanager

from support.http_capture import RecordedTestClient
from test_task_creation import creation_case
from wuji_core.execution.control import ControlService
from wuji_core.execution.control_api import ControlAPI
from wuji_core.execution.launch import LaunchService
from wuji_core.execution.tasks import TaskService
from wuji_core.http import create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.commands import create_command_router
from wuji_core.http.launch import create_launch_router
from wuji_core.http.tasks import create_task_router


@contextmanager
def first_use_case(environment, audit_directory):
    """Build the real Task/Control/Launch HTTP composition over isolated PG."""

    with creation_case(environment, audit_directory) as case:
        case.client.close()
        control = ControlService(case.uow)
        launch = LaunchService(case.uow, control=control)
        verifier = TokenVerifier(
            public_key_pem=case.provider.public_key_pem,
            issuer=case.provider.issuer,
            audience=case.provider.audience,
        )
        client = RecordedTestClient(
            create_app(
                token_verifier=verifier,
                routers=[
                    create_task_router(TaskService(case.uow)),
                    create_launch_router(launch),
                    create_command_router(
                        ControlAPI(control, launch_service=launch)
                    ),
                ],
            ),
            audit_path=audit_directory / "first-use-http.jsonl",
        )
        case.client = client
        case.control = control
        case.launch = launch
        try:
            yield case
        finally:
            client.close()


def bearer(case, token=None):
    return {"Authorization": "Bearer " + (token or case.operator)}


def task_command(case, task_id, command, version, *, key, token=None, reason=None):
    return case.client.post(
        f"/api/v2/tasks/{task_id}/commands",
        headers={**bearer(case, token), "Idempotency-Key": key},
        json={
            "schema_version": "wuji.api.v2",
            "command": command,
            "expected_version": str(version),
            "reason": reason or f"first-use {command}",
        },
    )


def task_view(case, task_id, token=None):
    response = case.client.get(
        f"/api/v2/tasks/{task_id}", headers=bearer(case, token)
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_task(case, body, *, key):
    from test_task_creation import create

    response = create(case, body=body, key=key)
    assert response.status_code == 201, response.text
    return response.json()


def worker_access(case, subject="launch-worker"):
    from wuji_core.http.auth import Principal
    from wuji_core.persistence.uow import AccessContext

    return AccessContext(
        Principal(
            subject=subject,
            tenant_id="tenant-fixture",
            roles=frozenset({"controller"}),
            token_id=f"token-{subject}",
        ),
        "first-use-worker",
    )
