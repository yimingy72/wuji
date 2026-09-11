"""Task-scoped authorization and immutable creation configuration."""
from alembic import context, op

revision = "20260911_0006"
down_revision = "20260911_0005"
branch_labels = None
depends_on = None

def upgrade():
    project_role = context.config.attributes["project_role"]
    auth_role = context.config.attributes["auth_role"]
    op.execute("""
    DO $checks$
    DECLARE n text;
    BEGIN
      FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='task_drafts'::regclass
          AND contype='c' AND pg_get_constraintdef(oid) LIKE '%schema_version%'
      LOOP EXECUTE format('ALTER TABLE task_drafts DROP CONSTRAINT %I',n); END LOOP;
      FOR n IN SELECT conname FROM pg_constraint WHERE conrelid='tasks'::regclass
          AND contype='c' AND (SELECT attnum FROM pg_attribute
              WHERE attrelid='tasks'::regclass AND attname='state')=ANY(conkey)
      LOOP EXECUTE format('ALTER TABLE tasks DROP CONSTRAINT %I',n); END LOOP;
    END $checks$;
    ALTER TABLE task_drafts ADD CONSTRAINT task_draft_schema_check
      CHECK((content->>'schema_version' IN ('1.0','2.0')) IS TRUE);
    ALTER TABLE task_drafts
      ADD COLUMN selected_model_summary jsonb,
      ADD COLUMN last_created_task_id uuid,
      ADD CONSTRAINT task_draft_owned_id UNIQUE(tenant_id,project_id,user_id,id);
    ALTER TABLE tasks
      ALTER COLUMN policy_id DROP NOT NULL,
      ALTER COLUMN policy_version DROP NOT NULL,
      ALTER COLUMN policy_hash DROP NOT NULL,
      ADD COLUMN task_kind text NOT NULL DEFAULT 'legacy_http',
      ADD COLUMN task_authorization_id uuid,
      ADD COLUMN creation_config_snapshot_id uuid UNIQUE,
      ADD COLUMN creation_config jsonb,
      ADD CONSTRAINT task_creation_kind CHECK(task_kind IN ('legacy_http','web_assessment')),
      ADD CONSTRAINT task_creation_initial_state CHECK(
        (state='queued' AND task_kind='legacy_http' AND version=1 AND stop_reason IS NULL)
        OR (state='ready' AND task_kind='web_assessment' AND version=1 AND stop_reason IS NULL)
        OR (state='cancelled' AND version=2 AND stop_reason='user_cancelled')),
      ADD CONSTRAINT task_creation_kind_fields CHECK(
        (task_kind='legacy_http' AND policy_id IS NOT NULL AND policy_version IS NOT NULL
          AND policy_hash IS NOT NULL AND task_authorization_id IS NULL
          AND creation_config_snapshot_id IS NULL AND creation_config IS NULL)
        OR (task_kind='web_assessment' AND policy_id IS NULL AND policy_version IS NULL
          AND policy_hash IS NULL AND task_authorization_id IS NOT NULL
          AND creation_config_snapshot_id IS NOT NULL AND creation_config IS NOT NULL
          AND jsonb_typeof(creation_config)='object' AND octet_length(creation_config::text)<=262144)
      );
    ALTER TABLE task_drafts ADD CONSTRAINT draft_last_task_fk
      FOREIGN KEY(tenant_id,project_id,last_created_task_id) REFERENCES tasks(tenant_id,project_id,id);

    CREATE TABLE task_authorizations (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, project_id uuid NOT NULL,
      task_id uuid NOT NULL, version bigint NOT NULL DEFAULT 1 CHECK(version=1),
      scope jsonb NOT NULL CHECK(jsonb_typeof(scope)='object'),
      scope_hash char(64) NOT NULL CHECK(scope_hash ~ '^[a-f0-9]{64}$'),
      valid_from timestamptz NOT NULL, valid_until timestamptz NOT NULL,
      confirmed_by uuid NOT NULL REFERENCES users(id),
      permissions_version bigint NOT NULL CHECK(permissions_version>=1),
      confirmation_text_version text NOT NULL,
      confirmed_at timestamptz NOT NULL,
      UNIQUE(tenant_id,project_id,task_id,id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES tasks(tenant_id,project_id,id)
        DEFERRABLE INITIALLY DEFERRED,
      CHECK(valid_until>valid_from)
    );
    ALTER TABLE tasks ADD CONSTRAINT task_own_authorization_fk
      FOREIGN KEY(tenant_id,project_id,id,task_authorization_id)
      REFERENCES task_authorizations(tenant_id,project_id,task_id,id)
      DEFERRABLE INITIALLY DEFERRED;

    CREATE TABLE task_creation_previews (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, project_id uuid NOT NULL,
      user_id uuid NOT NULL REFERENCES users(id), draft_id uuid NOT NULL,
      draft_version bigint NOT NULL CHECK(draft_version>=1),
      draft_digest char(64) NOT NULL, permissions_version bigint NOT NULL,
      normalized_content jsonb NOT NULL, model_snapshot jsonb,
      input_digest char(64) NOT NULL, authorization_digest char(64) NOT NULL,
      can_create boolean NOT NULL, blockers jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), expires_at timestamptz NOT NULL,
      FOREIGN KEY(tenant_id,project_id,user_id,draft_id)
        REFERENCES task_drafts(tenant_id,project_id,user_id,id),
      CHECK(jsonb_typeof(normalized_content)='object'),
      CHECK(jsonb_typeof(blockers)='array'),
      CHECK((can_create AND jsonb_array_length(blockers)=0)
         OR (NOT can_create AND jsonb_array_length(blockers)>0)),
      CHECK(expires_at>created_at)
    );
    CREATE INDEX creation_preview_owner ON task_creation_previews(tenant_id,project_id,user_id,id);
    """)
    user = "NULLIF(current_setting('app.user_id',true),'')::uuid"
    tenant = "NULLIF(current_setting('app.tenant_id',true),'')::uuid"
    project = "NULLIF(current_setting('app.project_id',true),'')::uuid"
    for table, personal in (("task_authorizations", False), ("task_creation_previews", True)):
        base = f"""tenant_id={tenant} AND project_id={project} AND EXISTS(
          SELECT 1 FROM projects p JOIN tenants t ON t.id=p.tenant_id
          JOIN project_memberships pm ON pm.tenant_id=p.tenant_id AND pm.project_id=p.id
          JOIN tenant_memberships tm ON tm.tenant_id=pm.tenant_id AND tm.user_id=pm.user_id
          WHERE p.tenant_id={table}.tenant_id AND p.id={table}.project_id
            AND pm.user_id={user} AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled"""
        own = f" AND user_id={user}" if personal else ""
        read = base + ")" + own
        write = base + " AND pm.role='operator' AND tm.role='operator')" + own
        if not personal:
            write += f" AND confirmed_by={user}"
        op.execute(f"""
          ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
          CREATE POLICY creation_read ON {table} FOR SELECT USING({read});
          CREATE POLICY creation_insert ON {table} FOR INSERT WITH CHECK({write});
          REVOKE ALL ON {table} FROM PUBLIC,{project_role},{auth_role};
          GRANT SELECT,INSERT ON {table} TO {project_role};
        """)
    op.execute(f"""
      GRANT SELECT(task_kind,task_authorization_id,creation_config_snapshot_id,creation_config)
        ON tasks TO {project_role};
      GRANT INSERT(task_kind,task_authorization_id,creation_config_snapshot_id,creation_config)
        ON tasks TO {project_role};
      GRANT INSERT(selected_model_summary,last_created_task_id)
        ON task_drafts TO {project_role};
      GRANT UPDATE(selected_model_summary,last_created_task_id)
        ON task_drafts TO {project_role};
    """)

def downgrade():
    # Keep business data rather than silently widening or deleting authorization.
    op.execute("""
    DO $guard$ BEGIN
      IF EXISTS(SELECT 1 FROM tasks WHERE task_kind='web_assessment')
        OR EXISTS(SELECT 1 FROM task_drafts WHERE content->>'schema_version'='2.0')
      THEN RAISE EXCEPTION 'cannot downgrade task creation with preserved business data'; END IF;
    END $guard$;
    """)
    raise RuntimeError("task creation downgrade is intentionally unsupported; restore a verified backup")
