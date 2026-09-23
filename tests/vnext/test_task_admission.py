"""P11-C: owner-side admission publication makes a created Task schedulable."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from support.p03 import access
from test_task_creation import (
    OWNER,
    create,
    creation_case,
    model_profile,
    runtime_profile,
)
from wuji_core.admission.registry import (
    RuntimeProfile,
    TaskRunLimits,
    configuration_digest,
    publish_task_admission,
)
from wuji_core.http import canonical_json_bytes
from wuji_core.contracts.execution import TaskCommand
from wuji_core.execution.control import ControlService
from wuji_core.execution.control_api import ControlAPI


OPERATOR = access("control-fixture", role="operator")


def admission_config() -> dict:
    model = model_profile()
    runtime = runtime_profile()
    return {
        "model": model.model_dump(mode="json"),
        "runtime": runtime.model_dump(mode="json"),
        "allowed_tool_refs": list(runtime.allowed_tool_refs),
    }


def test_runtime_run_limits_are_bounded_without_changing_legacy_profile_bytes():
    legacy = runtime_profile()
    old_bytes = canonical_json_bytes(legacy.model_dump(mode="json"))
    reparsed = RuntimeProfile.model_validate_json(old_bytes)

    assert reparsed.task_run_limits is None
    assert canonical_json_bytes(reparsed.model_dump(mode="json")) == old_bytes
    assert configuration_digest(reparsed.model_dump(mode="json")) == (
        configuration_digest(legacy.model_dump(mode="json"))
    )

    configured = legacy.model_copy(
        update={"task_run_limits": TaskRunLimits(explore=4, reason=1)}
    )
    assert configured.model_dump(mode="json")["task_run_limits"] == {
        "explore": 4,
        "reason": 1,
    }
    for invalid in (
        {"explore": 0, "reason": 1},
        {"explore": 257, "reason": 1},
        {"explore": 4, "reason": 2},
    ):
        with pytest.raises(ValidationError):
            TaskRunLimits.model_validate(invalid)


def publish(connection, task_id: str) -> None:
    publish_task_admission(
        connection,
        owner=(OWNER[0], OWNER[1], task_id),
        admission=admission_config(),
        capacity_pool_keys=("platform", OWNER[0]),
        access_grants=(
            {
                "subject": "scheduler-fixture",
                "can_read": True,
                "can_admit": True,
                "clearance": 1,
            },
            {
                "subject": "pod-controller",
                "can_read": True,
                "can_control": True,
                "can_admit": True,
                "can_observe": True,
                "clearance": 1,
            },
        ),
        scheduler_identity={
            "template_ref": "deployment-worker-v1",
            "issuer": "https://identity.wuji-vnext-test.invalid",
            "audience": "wuji-vnext-deployment",
            "signing_key_ref": "signing-key",
            "signing_kid": "deployment-key",
            "encryption_key_ref": "encryption-key",
            "clearance": 1,
        },
        pod_controller={
            "controller_subject": "pod-controller",
            "login_role": "wuji_pod",
        },
    )


def seed_pools(connection) -> None:
    for pool_key, tier, tenant in (
        ("platform", "global", None),
        (OWNER[0], "tenant", OWNER[0]),
    ):
        connection.execute(
            """INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref)
            VALUES(%s,%s,%s,4,'fixture-capacity-v1') ON CONFLICT (pool_key) DO NOTHING""",
            (pool_key, tier, tenant),
        )


def test_owner_publication_binds_a_created_task_to_admission_capacity_and_identity(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]

        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.admission_config WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (0,)
            seed_pools(connection)
            publish(connection, task_id)

            stored = connection.execute(
                """SELECT document_json FROM vnext.admission_config
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s""",
                (OWNER[0], OWNER[1], task_id),
            ).fetchone()
            assert stored is not None
            import json

            assert json.loads(stored[0]) == admission_config()
            pools = connection.execute(
                "SELECT pool_key FROM vnext.task_capacity_pool WHERE task_id=%s ORDER BY pool_key",
                (task_id,),
            ).fetchall()
            assert pools == [("platform",), (OWNER[0],)]
            template = connection.execute(
                """SELECT issuer,audience,clearance,enabled FROM vnext.scheduler_identity_template
                WHERE task_id=%s AND template_ref='deployment-worker-v1'""",
                (task_id,),
            ).fetchone()
            assert template == (
                "https://identity.wuji-vnext-test.invalid",
                "wuji-vnext-deployment",
                1,
                True,
            )
            controller = connection.execute(
                """SELECT controller_subject,login_role,enabled FROM vnext.task_pod_controller
                WHERE task_id=%s""",
                (task_id,),
            ).fetchone()
            assert controller == ("pod-controller", "wuji_pod", True)
            grants = connection.execute(
                """SELECT subject,can_admit,can_control,can_observe FROM vnext.task_access
                WHERE task_id=%s ORDER BY subject""",
                (task_id,),
            ).fetchall()
            assert grants == [
                ("control-fixture", False, True, False),
                ("pod-controller", True, True, True),
                ("scheduler-fixture", True, False, False),
            ]
            # Publishing the same admission twice is a no-op, not a rewrite.
            publish(connection, task_id)


def test_start_is_accepted_after_admission_and_keeps_the_created_definition(
    db_environment, tmp_path, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        created = create(case)
        task_id = created.json()["task_id"]
        control = ControlService(case.uow)
        api = ControlAPI(control)

        with db_environment.migration_connection() as connection:
            seed_pools(connection)
            publish(connection, task_id)

        receipt = api.command_task(
            OPERATOR,
            task_id,
            TaskCommand.model_validate(
                {
                    "schema_version": "wuji.api.v2",
                    "command": "start",
                    "expected_version": "1",
                    "reason": "fixture start",
                }
            ),
            idempotency_key="start-fixture-1",
        )
        assert receipt.disposition == "accepted"
        assert receipt.resource_version.root == "2"

        with db_environment.migration_connection() as connection:
            task = connection.execute(
                """SELECT desired_state,observed_state,execution_allowed,execution_epoch,
                activated_at IS NOT NULL,definition_digest FROM vnext.task WHERE task_id=%s""",
                (task_id,),
            ).fetchone()
            assert task[:4] == ("run", "running", True, 2)
            assert task[4] is True
            assert len(task[5]) == 64
            events = connection.execute(
                "SELECT kind FROM vnext.outbox WHERE task_id=%s ORDER BY event_seq",
                (task_id,),
            ).fetchall()
            assert ("task.started",) in events
            # The admission publication is unchanged by the command.
            assert connection.execute(
                "SELECT count(*) FROM vnext.admission_config WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (1,)
            assert connection.execute(
                "SELECT count(*) FROM vnext.task_capacity_pool WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (2,)
