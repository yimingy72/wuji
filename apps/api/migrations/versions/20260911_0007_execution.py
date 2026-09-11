"""Persistent execution admission, process/call receipts and evidence metadata."""
from alembic import context, op

revision="20260911_0007"
down_revision="20260911_0006"
branch_labels=None
depends_on=None

def upgrade():
    p=context.config.attributes["project_role"]
    a=context.config.attributes["auth_role"]
    e=context.config.attributes["execution_role"]
    op.execute("""
    DO $checks$ DECLARE n text; BEGIN
      FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='tasks'::regclass AND contype='c'
        AND conkey && ARRAY(SELECT attnum FROM pg_attribute WHERE attrelid='tasks'::regclass AND
          attname IN ('state','active_calls','unknown_calls','cleanup_state','egress_state','assessment_outcome','stop_reason'))::smallint[]
      LOOP EXECUTE format('ALTER TABLE tasks DROP CONSTRAINT %I',n); END LOOP;
      FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='command_receipts'::regclass AND contype='c'
        AND (SELECT attnum FROM pg_attribute WHERE attrelid='command_receipts'::regclass AND attname='kind')=ANY(conkey)
      LOOP EXECUTE format('ALTER TABLE command_receipts DROP CONSTRAINT %I',n); END LOOP;
    END $checks$;
    ALTER TABLE tasks DROP CONSTRAINT task_creation_kind_fields;
    ALTER TABLE tasks ADD COLUMN execution_epoch bigint NOT NULL DEFAULT 0 CHECK(execution_epoch>=0),
      ADD CONSTRAINT task_execution_states CHECK(
        (task_kind='legacy_http' AND execution_epoch=0 AND active_calls=0 AND unknown_calls=0
          AND cleanup_state='not_required' AND egress_state='not_granted' AND assessment_outcome='not_assessed'
          AND ((state='queued' AND version=1 AND stop_reason IS NULL)
            OR (state='cancelled' AND version=2 AND stop_reason='user_cancelled')))
        OR (task_kind='web_assessment' AND state IN
          ('ready','provisioning','running','completing','completed','cancelling','cancelled','reconciling')
          AND active_calls>=0 AND unknown_calls>=0
          AND cleanup_state IN ('not_required','pending','running','completed','failed','unknown')
          AND egress_state IN ('not_granted','fixture_only','revoking','revoked','unknown')
          AND assessment_outcome IN ('not_assessed','complete','partial','inconclusive'))),
      ADD CONSTRAINT task_creation_kind_fields CHECK(
        (task_kind='legacy_http' AND policy_id IS NOT NULL AND policy_version IS NOT NULL AND policy_hash IS NOT NULL
          AND task_authorization_id IS NULL AND creation_config_snapshot_id IS NULL AND creation_config IS NULL)
        OR (task_kind='web_assessment' AND policy_id IS NULL AND policy_version IS NULL AND policy_hash IS NULL
          AND task_authorization_id IS NOT NULL AND creation_config_snapshot_id IS NOT NULL AND creation_config IS NOT NULL
          AND jsonb_typeof(creation_config)='object' AND octet_length(creation_config::text)<=262144));
    ALTER TABLE command_receipts ADD CONSTRAINT command_kind_check CHECK(kind IN ('create','start','cancel'));

    CREATE TABLE execution_services (
      id text PRIMARY KEY CHECK(id='core'), instance_id uuid NOT NULL,
      config jsonb NOT NULL, heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE task_executions (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, project_id uuid NOT NULL, task_id uuid NOT NULL UNIQUE,
      start_command_id uuid NOT NULL REFERENCES command_receipts(id),
      epoch bigint NOT NULL CHECK(epoch>0), state text NOT NULL DEFAULT 'pending',
      service_instance_id uuid NOT NULL, execution_snapshot jsonb NOT NULL,
      native_project_id text, binding_state text NOT NULL DEFAULT 'pending',
      model_state text NOT NULL DEFAULT 'pending', key_hash text, secret_name text,
      model_spend numeric, cost_state text NOT NULL DEFAULT 'unknown',
      result jsonb, failure_reason text,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    CREATE TABLE runtime_attempts (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, project_id uuid NOT NULL, task_id uuid NOT NULL,
      execution_id uuid NOT NULL, attempt integer NOT NULL CHECK(attempt>0),
      namespace text NOT NULL,pod_name text NOT NULL,pod_uid text,state text NOT NULL DEFAULT 'pending',
      config jsonb NOT NULL,receipt jsonb,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(task_id,attempt),UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,execution_id) REFERENCES task_executions(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    CREATE TABLE agent_runs (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      execution_id uuid NOT NULL,runtime_attempt integer NOT NULL,
      execution_epoch bigint NOT NULL,phase text NOT NULL CHECK(phase IN ('bootstrap','reason','explore')),
      intent_id text,worker_profile_id text NOT NULL,worker_name text NOT NULL UNIQUE,
      state text NOT NULL DEFAULT 'registered',result_state text NOT NULL DEFAULT 'pending',
      assignment jsonb NOT NULL,receipt jsonb,output text,outcome text,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,execution_id) REFERENCES task_executions(tenant_id,project_id,task_id,id),
      FOREIGN KEY(task_id,runtime_attempt) REFERENCES runtime_attempts(task_id,attempt),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    CREATE UNIQUE INDEX one_active_intent_run ON agent_runs(task_id,phase,COALESCE(intent_id,''))
      WHERE state IN ('registered','running','unknown') OR result_state IN ('pending','unknown');
    CREATE TABLE tool_calls (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      agent_run_id uuid NOT NULL,request_id text NOT NULL,request_digest text NOT NULL,
      runtime_attempt integer NOT NULL,execution_epoch bigint NOT NULL,tool text NOT NULL,args jsonb NOT NULL,
      state text NOT NULL DEFAULT 'registered',result jsonb,receipt jsonb,cancel_requested boolean NOT NULL DEFAULT false,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(agent_run_id,request_id),UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(task_id,runtime_attempt) REFERENCES runtime_attempts(task_id,attempt)
    );
    CREATE TABLE tool_attempts (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      tool_call_id uuid NOT NULL,number integer NOT NULL DEFAULT 1,
      request jsonb NOT NULL,state text NOT NULL DEFAULT 'prepared',receipt jsonb,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tool_call_id,number),
      FOREIGN KEY(tenant_id,project_id,task_id,tool_call_id) REFERENCES tool_calls(tenant_id,project_id,task_id,id)
    );
    CREATE TABLE core_operations (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      agent_run_id uuid,kind text NOT NULL,request_digest text NOT NULL,request jsonb NOT NULL,
      state text NOT NULL DEFAULT 'prepared',response jsonb,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    CREATE TABLE task_artifacts (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      tool_call_id uuid,kind text NOT NULL,name text NOT NULL,mime text NOT NULL,size bigint NOT NULL CHECK(size>=0),
      sha256 text NOT NULL,storage_key text NOT NULL,state text NOT NULL DEFAULT 'available',
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,tool_call_id) REFERENCES tool_calls(tenant_id,project_id,task_id,id)
    );
    CREATE TABLE task_graph_snapshots (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      native_project_id text NOT NULL,graph jsonb NOT NULL,digest text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    """)
    # New states remain behind trusted execution/Operator operations, never the auth role.
    op.execute(f"""
    GRANT USAGE ON SCHEMA public TO {e};
    GRANT SELECT(execution_epoch), UPDATE(execution_epoch) ON tasks TO {p};
    GRANT SELECT,INSERT,UPDATE ON execution_services TO {e};
    GRANT SELECT ON execution_services TO {p};
    REVOKE ALL ON execution_services FROM PUBLIC,{a};
    """)
    user="NULLIF(current_setting('app.user_id',true),'')::uuid"
    tenant="NULLIF(current_setting('app.tenant_id',true),'')::uuid"
    project="NULLIF(current_setting('app.project_id',true),'')::uuid"
    tables=("task_executions","runtime_attempts","agent_runs","tool_calls","tool_attempts",
            "core_operations","task_artifacts","task_graph_snapshots")
    for table in tables:
        readable=f"""tenant_id={tenant} AND project_id={project} AND EXISTS(
            SELECT 1 FROM projects p JOIN tenants t ON t.id=p.tenant_id
            JOIN project_memberships pm ON pm.tenant_id=p.tenant_id AND pm.project_id=p.id
            JOIN tenant_memberships tm ON tm.tenant_id=pm.tenant_id AND tm.user_id=pm.user_id
            WHERE p.id={table}.project_id AND p.tenant_id={table}.tenant_id AND pm.user_id={user}
              AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled)"""
        op.execute(f"""
          ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
          CREATE POLICY core_execution_service ON {table} TO {e} USING(true) WITH CHECK(true);
          CREATE POLICY core_project_read ON {table} FOR SELECT TO {p} USING({readable});
          REVOKE ALL ON {table} FROM PUBLIC,{a},{p};
          GRANT SELECT,INSERT,UPDATE ON {table} TO {e};
          CREATE INDEX {table}_page ON {table}(tenant_id,project_id,task_id,created_at DESC,id DESC);
        """)
        public_columns={
          "task_executions":"id,tenant_id,project_id,task_id,start_command_id,epoch,state,service_instance_id,execution_snapshot,native_project_id,binding_state,model_state,model_spend,cost_state,result,failure_reason,created_at,updated_at",
          "runtime_attempts":"id,tenant_id,project_id,task_id,attempt,state,created_at,updated_at",
          "agent_runs":"id,tenant_id,project_id,task_id,phase,intent_id,worker_profile_id,state,result_state,outcome,created_at,updated_at",
          "tool_calls":"id,tenant_id,project_id,task_id,agent_run_id,tool,args,state,result,cancel_requested,created_at,updated_at",
          "task_artifacts":"id,tenant_id,project_id,task_id,tool_call_id,kind,name,mime,size,sha256,state,created_at",
          "task_graph_snapshots":"id,tenant_id,project_id,task_id,native_project_id,graph,digest,created_at",
        }.get(table)
        if public_columns:op.execute(f"GRANT SELECT({public_columns}) ON {table} TO {p}")
    op.execute(f"""
      CREATE POLICY core_operator_start ON task_executions FOR INSERT TO {p} WITH CHECK(
        tenant_id={tenant} AND project_id={project} AND EXISTS(
          SELECT 1 FROM project_memberships pm JOIN tenant_memberships tm
            ON tm.tenant_id=pm.tenant_id AND tm.user_id=pm.user_id
          WHERE pm.tenant_id=task_executions.tenant_id AND pm.project_id=task_executions.project_id
            AND pm.user_id={user} AND pm.enabled AND tm.enabled AND pm.role='operator' AND tm.role='operator'));
      GRANT INSERT(id,tenant_id,project_id,task_id,start_command_id,epoch,state,service_instance_id,execution_snapshot)
        ON task_executions TO {p};
      GRANT SELECT ON tasks,task_authorizations,model_versions,projects,tenants,users,
        project_memberships,tenant_memberships,command_receipts,task_events TO {e};
      GRANT UPDATE(state,version,execution_epoch,active_calls,unknown_calls,egress_state,
        cleanup_state,assessment_outcome,stop_reason,event_sequence,updated_at) ON tasks TO {e};
      GRANT INSERT ON task_events TO {e};
      CREATE POLICY core_existing_retired_model ON model_versions FOR SELECT TO {p} USING(
        tenant_id={tenant} AND kind='profile' AND state='retired' AND sync_state='synced'
        AND EXISTS(SELECT 1 FROM tasks t WHERE t.tenant_id=model_versions.tenant_id
          AND t.project_id={project} AND t.task_kind='web_assessment'
          AND t.creation_config->'model'->>'id'=model_versions.id::text));
    """)
    for table in ("tasks","task_authorizations","model_versions","projects","tenants","users",
                  "project_memberships","tenant_memberships","command_receipts","task_events"):
        op.execute(f"CREATE POLICY core_service_read ON {table} FOR SELECT TO {e} USING(true)")
    op.execute(f"""
      CREATE POLICY core_service_task_update ON tasks FOR UPDATE TO {e} USING(task_kind='web_assessment')
        WITH CHECK(task_kind='web_assessment');
      CREATE POLICY core_service_event_insert ON task_events FOR INSERT TO {e} WITH CHECK(
        EXISTS(SELECT 1 FROM tasks t WHERE t.id=task_events.task_id AND t.tenant_id=task_events.tenant_id
          AND t.project_id=task_events.project_id AND t.task_kind='web_assessment'));
    """)

def downgrade():
    raise RuntimeError("execution ledger cannot be destructively downgraded")
