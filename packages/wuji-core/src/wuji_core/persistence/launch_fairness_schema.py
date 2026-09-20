"""Round-robin eligible launch leases without discarding unknown operations."""
from pathlib import Path
from psycopg import sql
from wuji_core.persistence.launch_observer_schema import HEAD as PARENT_HEAD

HEAD = "vnext_0031_launch_fair_claim"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0030_launch_observer_acl":
        raise ValueError("launch fairness migration parent changed")
    source = (Path(__file__).resolve().parents[1] / "execution/launch_schema_draft.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION vnext.claim_task_launch(")
    end = source.index("CREATE OR REPLACE FUNCTION vnext.renew_task_launch_lease(", start)
    function = source[start:end]
    replacements = {
        "subject,can_read,can_control,can_admit,clearance)":
            "subject,can_read,can_control,can_observe,can_admit,clearance)",
        "a.subject,true,true,true,a.clearance":
            "a.subject,true,true,true,true,a.clearance",
        "ORDER BY launch.created_at,launch.operation_id":
            "ORDER BY launch.updated_at,launch.created_at,launch.operation_id",
    }
    for old, new in replacements.items():
        if function.count(old) != 1:
            raise ValueError("frozen launch claim function changed")
        function = function.replace(old, new)
    connection.execute(function)
    connection.execute("REVOKE ALL ON FUNCTION vnext.claim_task_launch(text,integer,text) FROM PUBLIC")
    connection.execute(sql.SQL("GRANT EXECUTE ON FUNCTION vnext.claim_task_launch(text,integer,text) TO {}").format(sql.Identifier(application_role)))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
