"""P13 persistent authorized projection migration."""

from psycopg import sql


HEAD = "vnext_0012_p13_projection"


def upgrade(connection, application_role):
    statements = [
        """CREATE FUNCTION vnext.projection_reader(t text,p text,k text,s text,l integer DEFAULT 0)
        RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
          SELECT s=current_setting('wuji.subject',true)
            AND COALESCE(vnext.in_scope(t,p,k,l),false)
            AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE
              a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.subject=s
              AND a.can_read AND a.clearance>=l)
        $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.projection_reader(text,text,text,text,integer) FROM PUBLIC",
        """CREATE TABLE vnext.projection_materialization (
          tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
          subject text NOT NULL, snapshot_id text NOT NULL, initial_view_id text NOT NULL,
          query_json text NOT NULL CHECK(jsonb_typeof(query_json::jsonb)='object'),
          query_digest text NOT NULL, access_digest text NOT NULL, projection_version text NOT NULL,
          materialization_json text NOT NULL CHECK(jsonb_typeof(materialization_json::jsonb)='object'),
          internal_event_origin numeric NOT NULL CHECK(internal_event_origin>=0 AND internal_event_origin=trunc(internal_event_origin)),
          access_level integer NOT NULL CHECK(access_level>=0),
          created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
          PRIMARY KEY(tenant_id,project_id,task_id,snapshot_id),
          UNIQUE(tenant_id,project_id,task_id,snapshot_id,subject,access_digest,projection_version),
          FOREIGN KEY(tenant_id,project_id,task_id,snapshot_id)
            REFERENCES vnext.snapshot_manifest(tenant_id,project_id,task_id,snapshot_id),
          FOREIGN KEY(tenant_id,project_id,task_id,subject)
            REFERENCES vnext.task_access(tenant_id,project_id,task_id,subject)
        )""",
        """CREATE TABLE vnext.projection_view (
          tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
          subject text NOT NULL, view_id text NOT NULL, snapshot_id text NOT NULL,
          query_json text NOT NULL CHECK(jsonb_typeof(query_json::jsonb)='object'),
          query_digest text NOT NULL, access_digest text NOT NULL, projection_version text NOT NULL,
          view_revision numeric NOT NULL CHECK(view_revision=1),
          created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
          PRIMARY KEY(tenant_id,project_id,task_id,view_id),
          UNIQUE(tenant_id,project_id,task_id,view_id,subject,query_digest,access_digest,projection_version),
          FOREIGN KEY(tenant_id,project_id,task_id,snapshot_id,subject,access_digest,projection_version)
            REFERENCES vnext.projection_materialization(tenant_id,project_id,task_id,snapshot_id,subject,access_digest,projection_version)
        )""",
        """CREATE TABLE vnext.projection_cursor (
          tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
          subject text NOT NULL, handle text NOT NULL CHECK(length(handle)>=32),
          kind text NOT NULL CHECK(kind IN ('page','index')), view_id text,
          query_digest text NOT NULL, access_digest text NOT NULL, projection_version text NOT NULL,
          position_json text NOT NULL CHECK(jsonb_typeof(position_json::jsonb)='object'),
          expires_at timestamptz NOT NULL,
          PRIMARY KEY(tenant_id,project_id,task_id,handle),
          CHECK((kind='page')=(view_id IS NOT NULL)),
          FOREIGN KEY(tenant_id,project_id,task_id,subject)
            REFERENCES vnext.task_access(tenant_id,project_id,task_id,subject),
          FOREIGN KEY(tenant_id,project_id,task_id,view_id,subject,query_digest,access_digest,projection_version)
            REFERENCES vnext.projection_view(tenant_id,project_id,task_id,view_id,subject,query_digest,access_digest,projection_version)
        )""",
        """CREATE INDEX projection_history ON vnext.projection_materialization
          (tenant_id,project_id,task_id,subject,created_at DESC,snapshot_id)""",
        "CREATE INDEX projection_cursor_expiry ON vnext.projection_cursor(expires_at)",
        "ALTER TABLE vnext.projection_materialization ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE vnext.projection_view ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE vnext.projection_cursor ENABLE ROW LEVEL SECURITY",
        """CREATE POLICY projection_read ON vnext.projection_materialization FOR SELECT USING (
          vnext.projection_reader(tenant_id,project_id,task_id,subject,access_level)
        )""",
        """CREATE POLICY projection_insert ON vnext.projection_materialization FOR INSERT WITH CHECK (
          vnext.projection_reader(tenant_id,project_id,task_id,subject,access_level)
          AND current_setting('wuji.snapshot',true)='true'
          AND EXISTS(SELECT 1 FROM vnext.snapshot_manifest s
            WHERE (s.tenant_id,s.project_id,s.task_id,s.snapshot_id)=
              (projection_materialization.tenant_id,projection_materialization.project_id,
               projection_materialization.task_id,projection_materialization.snapshot_id)
            AND s.expires_at>=projection_materialization.expires_at
            AND s.access_level<=projection_materialization.access_level)
        )""",
        """CREATE POLICY projection_read ON vnext.projection_view FOR SELECT USING (
          vnext.projection_reader(tenant_id,project_id,task_id,subject)
          AND EXISTS(SELECT 1 FROM vnext.projection_materialization p
            WHERE (p.tenant_id,p.project_id,p.task_id,p.snapshot_id)=
              (projection_view.tenant_id,projection_view.project_id,projection_view.task_id,projection_view.snapshot_id))
        )""",
        """CREATE POLICY projection_insert ON vnext.projection_view FOR INSERT WITH CHECK (
          vnext.projection_reader(tenant_id,project_id,task_id,subject)
          AND current_setting('wuji.snapshot',true)='true'
          AND EXISTS(SELECT 1 FROM vnext.projection_materialization p
            WHERE (p.tenant_id,p.project_id,p.task_id,p.snapshot_id)=
              (projection_view.tenant_id,projection_view.project_id,projection_view.task_id,projection_view.snapshot_id)
            AND p.expires_at>=projection_view.expires_at)
        )""",
        """CREATE POLICY projection_read ON vnext.projection_cursor FOR SELECT USING (
          vnext.projection_reader(tenant_id,project_id,task_id,subject)
          AND (kind='index' OR EXISTS(SELECT 1 FROM vnext.projection_view v
            WHERE (v.tenant_id,v.project_id,v.task_id,v.view_id)=
              (projection_cursor.tenant_id,projection_cursor.project_id,projection_cursor.task_id,projection_cursor.view_id)))
        )""",
        """CREATE POLICY projection_insert ON vnext.projection_cursor FOR INSERT WITH CHECK (
          vnext.projection_reader(tenant_id,project_id,task_id,subject)
          AND current_setting('wuji.snapshot',true)='true'
          AND (kind='index' OR EXISTS(SELECT 1 FROM vnext.projection_view v
            WHERE (v.tenant_id,v.project_id,v.task_id,v.view_id)=
              (projection_cursor.tenant_id,projection_cursor.project_id,projection_cursor.task_id,projection_cursor.view_id)
            AND v.expires_at>=projection_cursor.expires_at))
        )""",
        """CREATE FUNCTION vnext.projection_run_origin(t text,p text,k text,r text)
        RETURNS TABLE(created_at timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
          SELECT o.created_at
          FROM vnext.agent_run a
          JOIN vnext.scheduler_assignment d
            ON (d.tenant_id,d.project_id,d.task_id,d.agent_run_id,d.work_item_id)=
               (a.tenant_id,a.project_id,a.task_id,a.agent_run_id,a.work_item_id)
          JOIN vnext.outbox o
            ON (o.tenant_id,o.project_id,o.task_id,o.event_seq)=
               (d.tenant_id,d.project_id,d.task_id,d.event_seq)
          JOIN vnext.task_access acl
            ON (acl.tenant_id,acl.project_id,acl.task_id)=(a.tenant_id,a.project_id,a.task_id)
          WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=(t,p,k,r)
            AND COALESCE(vnext.in_scope(t,p,k,o.access_level),false)
            AND acl.subject=current_setting('wuji.subject',true) AND acl.can_read
            AND acl.clearance>=o.access_level
            AND d.operation_id=a.start_operation_id
            AND o.kind='run.dispatch_requested'
            AND o.payload_json::jsonb->>'agent_run_id'=a.agent_run_id
            AND o.payload_json::jsonb->>'operation_id'=d.operation_id
            AND o.payload_json::jsonb->>'assignment_digest'=d.assignment_digest
            AND d.assignment_digest=encode(sha256(convert_to(d.assignment_json,'UTF8')),'hex')
            AND d.assignment_json::jsonb->>'operation_id'=d.operation_id
            AND d.assignment_json::jsonb->'identity'=jsonb_build_object(
              'tenant_id',a.tenant_id,'project_id',a.project_id,'task_id',a.task_id,
              'work_item_id',a.work_item_id,'agent_run_id',a.agent_run_id,
              'receiver_id',a.receiver_id,'execution_epoch',a.execution_epoch::text,
              'run_epoch',a.run_epoch::text,'runtime_attempt',a.runtime_attempt::text)
        $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.projection_run_origin(text,text,text,text) FROM PUBLIC",
        "REVOKE ALL ON vnext.projection_materialization,vnext.projection_view,vnext.projection_cursor FROM PUBLIC",
    ]
    for statement in statements:
        connection.execute(statement)

    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.projection_reader(text,text,text,text,integer) TO {}"
        ).format(app)
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.projection_run_origin(text,text,text,text) TO {}"
        ).format(app)
    )
    connection.execute(
        sql.SQL(
            "GRANT SELECT,INSERT ON vnext.projection_materialization,vnext.projection_view,vnext.projection_cursor TO {}"
        ).format(app)
    )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
