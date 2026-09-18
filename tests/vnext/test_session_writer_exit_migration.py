"""P08 0016 upgrade and exact exit-revocation boundaries."""

import asyncio

import pytest

from support.p03 import access
from support.p08 import p08_candidate_case
from test_knowledge_admission import OWNER, TASK
from wuji_core.persistence import schema
from wuji_core.persistence import session_writer_exit_schema


@pytest.mark.parametrize(
    "known_0014",
    ["with_6f_trigger", "without_dd400_trigger"],
)
def test_0016_upgrades_both_known_0014_shapes_without_replaying_session_ddl(
    db_environment,
    monkeypatch,
    known_0014,
):
    with monkeypatch.context() as patch:
        patch.setattr(schema, "upgrade_control_api", lambda *_args: None)
        patch.setattr(schema, "upgrade_session_writer_exit", lambda *_args: None)
        patch.setattr(schema, "upgrade_pod_receivers", lambda *_args: None)
        # Later heads (0018 onward) must be skipped too, otherwise the
        # aggregate head is applied and this check's "stopped after the session
        # head" premise for the 0016 upgrade no longer holds.
        patch.setattr(schema, "upgrade_layouts", lambda *_args: None)
        patch.setattr(schema, "upgrade_task_creation", lambda *_args: None)
        patch.setattr(schema, "upgrade_run_settlement_close", lambda *_args: None)
        patch.setattr(schema, "upgrade_environment_settlement", lambda *_args: None)
        patch.setattr(schema, "upgrade_completion", lambda *_args: None)
        patch.setattr(schema, "upgrade_judgments", lambda *_args: None)
        patch.setattr(schema, "upgrade_reports", lambda *_args: None)
        patch.setattr(schema, "upgrade_view_stream", lambda *_args: None)
        patch.setattr(schema, "upgrade_report_delivery", lambda *_args: None)
        patch.setattr(schema, "upgrade_artifact_purge", lambda *_args: None)
        patch.setattr(schema, "upgrade_platform_settlement", lambda *_args: None)
        with db_environment.migration_connection() as connection:
            schema.migrate(
                connection,
                application_role=db_environment.application_role,
            )
            heads = {
                row[0]
                for row in connection.execute(
                    "SELECT head FROM vnext.schema_migration"
                ).fetchall()
            }
            assert schema.SESSION_HEAD in heads
            assert schema.CONTROL_API_HEAD not in heads
            assert session_writer_exit_schema.HEAD not in heads
            assert schema.HEAD not in heads

    with db_environment.migration_connection() as connection:
        connection.execute("INSERT INTO vnext.tenant VALUES('upgrade-tenant')")
        connection.execute(
            "INSERT INTO vnext.project VALUES('upgrade-tenant','upgrade-project')"
        )
        connection.execute(
            "INSERT INTO vnext.task(tenant_id,project_id,task_id) "
            "VALUES('upgrade-tenant','upgrade-project','upgrade-task')"
        )
        if known_0014 == "without_dd400_trigger":
            connection.execute(
                "DROP TRIGGER session_writer_exit_revoke ON vnext.agent_run"
            )
            connection.execute(
                "DROP FUNCTION vnext.revoke_session_writer_on_exit()"
            )

    with db_environment.migration_connection() as connection:
        schema.migrate(
            connection,
            application_role=db_environment.application_role,
        )
        assert connection.execute(
            "SELECT count(*) FROM vnext.schema_migration WHERE head=ANY(%s)",
            (
                [
                    schema.SESSION_HEAD,
                    schema.CONTROL_API_HEAD,
                    session_writer_exit_schema.HEAD,
                    schema.HEAD,
                ],
            ),
        ).fetchone() == (4,)
        assert connection.execute(
            "SELECT count(*) FROM vnext.tenant WHERE tenant_id='upgrade-tenant'"
        ).fetchone() == (1,)
        function = connection.execute(
            """SELECT p.prosecdef,p.proconfig
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='vnext'
              AND p.proname='revoke_session_writer_on_exit'"""
        ).fetchone()
        trigger = connection.execute(
            """SELECT count(*) FROM pg_trigger
            WHERE tgrelid='vnext.agent_run'::regclass
              AND tgname='session_writer_exit_revoke' AND NOT tgisinternal"""
        ).fetchone()
        assert function == (True, ["search_path=pg_catalog"])
        assert trigger == (1,)

    with db_environment.additional_app_connection() as connection:
        assert connection.execute(
            "SELECT has_function_privilege(current_user,"
            "'vnext.revoke_session_writer_on_exit()','EXECUTE')"
        ).fetchone() == (False,)


@pytest.mark.parametrize(
    ("boundary", "expected_revoked"),
    [
        ("valid", True),
        ("wrong_receiver", False),
        ("wrong_session_input", False),
        ("unsettled", False),
    ],
)
def test_0016_revokes_only_the_exact_settled_session_boundary(
    db_environment,
    tmp_path,
    audit_directory,
    boundary,
    expected_revoked,
):
    with p08_candidate_case(db_environment, tmp_path, audit_directory) as case:
        case.upstream.release_first_response.set()
        events = asyncio.run(_consume(case.runtime, case.assignment))
        assert [event.kind for event in events] == ["input_receipt"]
        observer = case.scheduler.receiver_access

        with case.environment.migration_connection() as connection:
            if boundary == "wrong_receiver":
                connection.execute(
                    """INSERT INTO vnext.task_access(
                    tenant_id,project_id,task_id,subject,can_read,can_observe,clearance)
                    VALUES(%s,%s,%s,'wrong-p08-receiver',true,true,1)""",
                    OWNER,
                )
                observer = access("wrong-p08-receiver", role="controller")
            elif boundary == "wrong_session_input":
                connection.execute(
                    "UPDATE vnext.work_item SET input_request_id=NULL "
                    "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                    "AND work_item_id=%s",
                    (*OWNER, case.assignment.identity.work_item_id),
                )
            elif boundary == "unsettled":
                connection.execute(
                    "UPDATE vnext.run_operation_settlement SET status='pending' "
                    "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                    "AND agent_run_id=%s",
                    (*OWNER, case.assignment.identity.agent_run_id),
                )

        case.record_process(case.assignment, "exited", access=observer)

        with case.environment.migration_connection() as connection:
            state = connection.execute(
                """SELECT credential.revoked,writer.revoked
                FROM vnext.run_credential credential
                JOIN vnext.run_writer writer
                  USING(tenant_id,project_id,task_id,agent_run_id,subject)
                WHERE credential.tenant_id=%s AND credential.project_id=%s
                  AND credential.task_id=%s AND credential.agent_run_id=%s
                  AND credential.subject=%s AND credential.token_id=%s""",
                (
                    *OWNER,
                    case.assignment.identity.agent_run_id,
                    case.credential.principal.subject,
                    case.credential.principal.token_id,
                ),
            ).fetchone()
        assert state == (expected_revoked, expected_revoked)


async def _consume(runtime, assignment):
    try:
        return [event async for event in runtime.execute(assignment)]
    finally:
        await runtime.aclose()
