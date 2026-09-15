"""P15 personal topology layout preferences and optimistic CAS."""

from psycopg import sql

from wuji_core.persistence.pod_receiver_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0018_p15_layout"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0017_task_pod_receiver":
        raise ValueError("P15 layout migration parent changed")
    statements = (
        """CREATE TABLE vnext.layout_preference(
          tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
          subject text NOT NULL, view_name text NOT NULL CHECK(length(view_name) BETWEEN 1 AND 128),
          layout_schema text NOT NULL CHECK(layout_schema='wuji.layout.v1'),
          layout_revision numeric NOT NULL CHECK(layout_revision>=1 AND layout_revision=trunc(layout_revision)),
          selection_mode text NOT NULL CHECK(selection_mode IN ('explicit_revision','follow_latest')),
          entries_json text NOT NULL CHECK(jsonb_typeof(entries_json::jsonb)='array'),
          viewport_json text NOT NULL CHECK(jsonb_typeof(viewport_json::jsonb)='object'),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          PRIMARY KEY(tenant_id,project_id,task_id,subject,view_name,layout_schema),
          FOREIGN KEY(tenant_id,project_id,task_id,subject)
            REFERENCES vnext.task_access(tenant_id,project_id,task_id,subject)
        )""",
        "ALTER TABLE vnext.layout_preference ENABLE ROW LEVEL SECURITY",
        "REVOKE ALL ON vnext.layout_preference FROM PUBLIC",
        """CREATE POLICY layout_read ON vnext.layout_preference FOR SELECT USING(
          tenant_id=current_setting('wuji.tenant',true)
          AND project_id=current_setting('wuji.project',true)
          AND task_id=current_setting('wuji.task',true)
          AND subject=current_setting('wuji.subject',true)
          AND EXISTS(
            SELECT 1 FROM vnext.task_access a
            WHERE (a.tenant_id,a.project_id,a.task_id,a.subject)=
              (layout_preference.tenant_id,layout_preference.project_id,
               layout_preference.task_id,layout_preference.subject)
              AND a.can_read
          )
        )""",
        """CREATE POLICY layout_insert ON vnext.layout_preference FOR INSERT WITH CHECK(
          tenant_id=current_setting('wuji.tenant',true)
          AND project_id=current_setting('wuji.project',true)
          AND task_id=current_setting('wuji.task',true)
          AND subject=current_setting('wuji.subject',true)
          AND current_setting('wuji.layout',true)='true'
          AND EXISTS(
            SELECT 1 FROM vnext.task_access a
            WHERE (a.tenant_id,a.project_id,a.task_id,a.subject)=
              (layout_preference.tenant_id,layout_preference.project_id,
               layout_preference.task_id,layout_preference.subject)
              AND a.can_read
          )
        )""",
        """CREATE POLICY layout_update ON vnext.layout_preference FOR UPDATE USING(
          tenant_id=current_setting('wuji.tenant',true)
          AND project_id=current_setting('wuji.project',true)
          AND task_id=current_setting('wuji.task',true)
          AND subject=current_setting('wuji.subject',true)
          AND current_setting('wuji.layout',true)='true'
          AND EXISTS(
            SELECT 1 FROM vnext.task_access a
            WHERE (a.tenant_id,a.project_id,a.task_id,a.subject)=
              (layout_preference.tenant_id,layout_preference.project_id,
               layout_preference.task_id,layout_preference.subject)
              AND a.can_read
          )
        ) WITH CHECK(
          tenant_id=current_setting('wuji.tenant',true)
          AND project_id=current_setting('wuji.project',true)
          AND task_id=current_setting('wuji.task',true)
          AND subject=current_setting('wuji.subject',true)
          AND current_setting('wuji.layout',true)='true'
        )""",
    )
    for statement in statements:
        connection.execute(statement)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL("GRANT SELECT,INSERT,UPDATE ON vnext.layout_preference TO {}")
        .format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
