"""Align new private launch leases with the published controller ACL.

Only new rows gain observation authority. Existing grants (including explicit
revocations) remain untouched through the original ON CONFLICT DO NOTHING.
"""
from pathlib import Path
from psycopg import sql
from wuji_core.persistence.launch_schema import HEAD as PARENT_HEAD

HEAD = "vnext_0030_launch_observer_acl"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0029_first_use_launch":
        raise ValueError("launch observer migration parent changed")
    source = (Path(__file__).resolve().parents[1] / "execution/launch_schema_draft.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION vnext.claim_task_launch(")
    end = source.index("CREATE OR REPLACE FUNCTION vnext.renew_task_launch_lease(", start)
    function = source[start:end]
    old_columns = "subject,can_read,can_control,can_admit,clearance)"
    old_values = "a.subject,true,true,true,a.clearance"
    if function.count(old_columns) != 1 or function.count(old_values) != 1:
        raise ValueError("frozen launch claim function changed")
    function = function.replace(old_columns, "subject,can_read,can_control,can_observe,can_admit,clearance)")
    function = function.replace(old_values, "a.subject,true,true,true,true,a.clearance")
    connection.execute(function)
    connection.execute("REVOKE ALL ON FUNCTION vnext.claim_task_launch(text,integer,text) FROM PUBLIC")
    connection.execute(sql.SQL("GRANT EXECUTE ON FUNCTION vnext.claim_task_launch(text,integer,text) TO {}").format(sql.Identifier(application_role)))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
