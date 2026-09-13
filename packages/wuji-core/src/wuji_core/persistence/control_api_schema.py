"""P11 Work locator migration, reserved after the P08 0014 head."""

from psycopg import sql

from wuji_core.persistence.session_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0015_p11_control_api"


def statements():
    return (
        """CREATE FUNCTION vnext.task_for_work(w text) RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
          WITH visible AS (
            SELECT DISTINCT i.project_id,i.task_id
            FROM vnext.work_item i
            JOIN vnext.task_access a
              ON (a.tenant_id,a.project_id,a.task_id)=
                 (i.tenant_id,i.project_id,i.task_id)
            WHERE i.tenant_id=current_setting('wuji.tenant',true)
              AND i.work_item_id=w
              AND a.subject=current_setting('wuji.subject',true)
              AND a.can_read
          )
          SELECT CASE WHEN count(*)=1 THEN min(task_id) ELSE NULL END
          FROM visible
        $$""",
        "REVOKE ALL ON FUNCTION vnext.task_for_work(text) FROM PUBLIC",
    )


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0014_p08_session_approval":
        raise ValueError("P11 control API migration parent changed")
    for statement in statements():
        connection.execute(statement)
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.task_for_work(text) TO {}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
