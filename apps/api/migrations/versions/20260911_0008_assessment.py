"""Append-only bounded Web assessments and their actual evidence."""
from alembic import context, op

revision="20260911_0008"
down_revision="20260911_0007"
branch_labels=None
depends_on=None

def upgrade():
    p=context.config.attributes["project_role"]
    a=context.config.attributes["auth_role"]
    e=context.config.attributes["execution_role"]
    op.execute("""
    ALTER TABLE task_artifacts ADD CONSTRAINT artifact_task_identity UNIQUE(tenant_id,project_id,task_id,id);
    CREATE TABLE assessment_plans (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      revision integer NOT NULL CHECK(revision>0),progress_digest text NOT NULL,snapshot jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(task_id,revision),UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
    );
    CREATE TABLE observations (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      tool_call_id uuid NOT NULL UNIQUE,agent_run_id uuid NOT NULL,runtime_attempt integer NOT NULL,
      artifact_id uuid NOT NULL,body_artifact_id uuid NOT NULL,target_url text NOT NULL,method text NOT NULL,metadata jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,tool_call_id) REFERENCES tool_calls(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,artifact_id) REFERENCES task_artifacts(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,body_artifact_id) REFERENCES task_artifacts(tenant_id,project_id,task_id,id),
      FOREIGN KEY(task_id,runtime_attempt) REFERENCES runtime_attempts(task_id,attempt)
    );
    CREATE TABLE verification_runs (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      coverage_item_id uuid NOT NULL,target_url text NOT NULL,rule_id text NOT NULL,
      claim text NOT NULL,agent_run_id uuid NOT NULL,intent_id text,submission_call_id uuid NOT NULL UNIQUE,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,submission_call_id) REFERENCES tool_calls(tenant_id,project_id,task_id,id)
    );
    CREATE TABLE verification_result_revisions (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      verification_run_id uuid NOT NULL,revision integer NOT NULL CHECK(revision>0),
      verdict text NOT NULL CHECK(verdict IN ('unassessed','confirmed','not_reproduced','inconclusive')),
      reason text NOT NULL,limitations jsonb NOT NULL,supersedes_result_id uuid,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(verification_run_id,revision),UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,verification_run_id) REFERENCES verification_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,supersedes_result_id) REFERENCES verification_result_revisions(tenant_id,project_id,task_id,id)
    );
    CREATE TABLE evidence_links (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      verification_result_id uuid NOT NULL,observation_id uuid NOT NULL,artifact_id uuid NOT NULL,
      relation text NOT NULL CHECK(relation IN ('supports','refutes','limits')),selector jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(verification_result_id,observation_id),
      FOREIGN KEY(tenant_id,project_id,task_id,verification_result_id) REFERENCES verification_result_revisions(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,observation_id) REFERENCES observations(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,artifact_id) REFERENCES task_artifacts(tenant_id,project_id,task_id,id)
    );
    CREATE TABLE completion_reviews (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,project_id uuid NOT NULL,task_id uuid NOT NULL,
      agent_run_id uuid NOT NULL,request_digest text NOT NULL,progress_digest text NOT NULL,
      decision text NOT NULL CHECK(decision IN ('needs_followup','stop_with_results')),
      reason text NOT NULL,missing jsonb NOT NULL,attempt_number integer NOT NULL CHECK(attempt_number>=0),
      trigger_state text NOT NULL CHECK(trigger_state IN ('pending','claimed','settled')),
      claimed_run_id uuid,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(agent_run_id,request_digest),
      FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id,claimed_run_id) REFERENCES agent_runs(tenant_id,project_id,task_id,id)
    );
    """)
    user="NULLIF(current_setting('app.user_id',true),'')::uuid"
    tenant="NULLIF(current_setting('app.tenant_id',true),'')::uuid"
    project="NULLIF(current_setting('app.project_id',true),'')::uuid"
    for table in ("assessment_plans","observations","verification_runs","verification_result_revisions","evidence_links","completion_reviews"):
        readable=f"""tenant_id={tenant} AND project_id={project} AND EXISTS(
          SELECT 1 FROM projects p JOIN tenants t ON t.id=p.tenant_id
          JOIN project_memberships pm ON pm.tenant_id=p.tenant_id AND pm.project_id=p.id
          JOIN tenant_memberships tm ON tm.tenant_id=pm.tenant_id AND tm.user_id=pm.user_id
          WHERE p.id={table}.project_id AND p.tenant_id={table}.tenant_id AND pm.user_id={user}
            AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled)"""
        op.execute(f"""
          ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
          CREATE POLICY assessment_service ON {table} TO {e} USING(true) WITH CHECK(true);
          CREATE POLICY assessment_project_read ON {table} FOR SELECT TO {p} USING({readable});
          REVOKE ALL ON {table} FROM PUBLIC,{a},{p};
          GRANT SELECT,INSERT ON {table} TO {e};
          CREATE INDEX {table}_page ON {table}(tenant_id,project_id,task_id,created_at DESC,id DESC);
        """)
        if table!="completion_reviews":op.execute(f"GRANT SELECT ON {table} TO {p}")
    op.execute(f"GRANT UPDATE(trigger_state,claimed_run_id) ON completion_reviews TO {e}")

def downgrade():
    raise RuntimeError("assessment evidence cannot be destructively downgraded")
