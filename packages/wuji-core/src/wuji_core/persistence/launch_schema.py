"""Append-only first-use catalog and durable launch operations."""

from pathlib import Path

from psycopg import sql

from wuji_core.persistence.platform_settlement_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0029_first_use_launch"
FUNCTIONS = (
    "list_tasks(text,integer,text)", "read_task_launch(text)",
    "task_options(text)", "task_readiness(text)",
    "accept_task_launch(text,text,text,text,text,text,text,jsonb,jsonb)",
    "claim_task_launch(text,integer,text)",
    "renew_task_launch_lease(text,text,integer)",
    "record_task_launch_step(text,text,text,text,jsonb)",
)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0028_p06_platform_run_settlement":
        raise ValueError("launch migration parent changed")
    source = Path(__file__).resolve().parents[1] / "execution/launch_schema_draft.sql"
    connection.execute(source.read_text(encoding="utf-8"))
    connection.execute("REVOKE ALL ON FUNCTION vnext._task_view_json(vnext.task) FROM PUBLIC")
    for signature in FUNCTIONS:
        connection.execute("REVOKE ALL ON FUNCTION vnext." + signature + " FROM PUBLIC")
        connection.execute(sql.SQL("GRANT EXECUTE ON FUNCTION vnext." + signature + " TO {}").format(sql.Identifier(application_role)))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
