"""Immutable organization model configuration and durable management operations."""
from alembic import context, op

revision = "20260911_0005"
down_revision = "20260911_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    project_role = context.config.attributes["project_role"]
    auth_role = context.config.attributes["auth_role"]
    op.execute("""
    CREATE TABLE tenant_admin_grants (
      tenant_id uuid NOT NULL REFERENCES tenants(id), user_id uuid NOT NULL,
      enabled boolean NOT NULL DEFAULT true,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY (tenant_id,user_id),
      FOREIGN KEY (tenant_id,user_id) REFERENCES tenant_memberships(tenant_id,user_id)
    );
    CREATE TABLE model_definitions (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id),
      kind varchar NOT NULL CHECK(kind IN ('service','profile')), name text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,kind,id)
    );
    CREATE TABLE model_versions (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id),
      kind varchar NOT NULL CHECK(kind IN ('service','profile')), definition_id uuid NOT NULL,
      number bigint NOT NULL CHECK(number > 0), name text NOT NULL, config jsonb NOT NULL,
      service_version_id uuid, service_kind varchar NOT NULL DEFAULT 'service' CHECK(service_kind='service'),
      gateway_instance_id uuid NOT NULL, native_id varchar NOT NULL,
      request_digest char(64) NOT NULL CHECK(request_digest ~ '^[a-f0-9]{64}$'),
      state varchar NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','published','retired','revoked')),
      state_revision bigint NOT NULL DEFAULT 1 CHECK(state_revision BETWEEN 1 AND 9007199254740991),
      sync_state varchar NOT NULL DEFAULT 'pending' CHECK(sync_state IN ('pending','synced','failed','unknown')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(tenant_id,kind,id), UNIQUE(tenant_id,id), UNIQUE(definition_id,number),
      UNIQUE(gateway_instance_id,native_id),
      FOREIGN KEY(tenant_id,kind,definition_id) REFERENCES model_definitions(tenant_id,kind,id),
      FOREIGN KEY(tenant_id,service_kind,service_version_id) REFERENCES model_versions(tenant_id,kind,id),
      CHECK(jsonb_typeof(config)='object'),
      CHECK((kind='service' AND service_version_id IS NULL) OR (kind='profile' AND service_version_id IS NOT NULL))
    );
    CREATE TABLE model_operations (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id),
      user_id uuid NOT NULL REFERENCES users(id), idempotency_key uuid NOT NULL,
      kind varchar NOT NULL CHECK(kind IN ('create_service','create_profile','check','publish','retire','revoke')),
      version_id uuid NOT NULL, request_digest char(64) NOT NULL CHECK(request_digest ~ '^[a-f0-9]{64}$'),
      state varchar NOT NULL DEFAULT 'prepared' CHECK(state IN ('prepared','sent','succeeded','failed','unknown')),
      result jsonb NOT NULL DEFAULT '{"error_code":null,"usage":null,"cost_usd":null}'::jsonb,
      sent_at timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(tenant_id,version_id) REFERENCES model_versions(tenant_id,id),
      UNIQUE(tenant_id,user_id,idempotency_key), CHECK(jsonb_typeof(result)='object')
    );
    CREATE INDEX model_definition_page ON model_definitions(tenant_id,kind,created_at DESC,id DESC);
    CREATE INDEX model_version_page ON model_versions(tenant_id,definition_id,created_at DESC,id DESC);
    CREATE INDEX model_operation_check ON model_operations(tenant_id,version_id,kind,created_at DESC,id DESC);
    """)
    user = "NULLIF(current_setting('app.user_id',true),'')::uuid"
    tenant = "NULLIF(current_setting('app.tenant_id',true),'')::uuid"
    project = "NULLIF(current_setting('app.project_id',true),'')::uuid"
    op.execute(f"""
    ALTER TABLE tenant_admin_grants ENABLE ROW LEVEL SECURITY;
    CREATE POLICY own_admin_grant ON tenant_admin_grants FOR SELECT USING(user_id={user});
    REVOKE ALL ON tenant_admin_grants FROM PUBLIC,{project_role},{auth_role};
    GRANT SELECT ON tenant_admin_grants TO {project_role};
    """)
    for table in ("model_definitions", "model_versions", "model_operations"):
        admin = f"""tenant_id={tenant} AND EXISTS (
          SELECT 1 FROM tenant_admin_grants g JOIN tenants t ON t.id=g.tenant_id
          JOIN tenant_memberships tm ON tm.tenant_id=g.tenant_id AND tm.user_id=g.user_id
          WHERE g.tenant_id={table}.tenant_id AND g.user_id={user} AND g.enabled AND t.enabled AND tm.enabled)"""
        read = admin
        if table == "model_versions":
            read += f""" OR (tenant_id={tenant} AND kind='profile' AND state='published' AND sync_state='synced'
              AND EXISTS(SELECT 1 FROM projects p JOIN tenants t ON t.id=p.tenant_id
                JOIN project_memberships pm ON pm.project_id=p.id AND pm.tenant_id=p.tenant_id
                JOIN tenant_memberships tm ON tm.tenant_id=pm.tenant_id AND tm.user_id=pm.user_id
                WHERE p.id={project} AND p.tenant_id=model_versions.tenant_id AND pm.user_id={user}
                  AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled))"""
        if table == "model_operations":
            admin += f" AND user_id={user}"
        op.execute(f"""
          ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
          CREATE POLICY model_read ON {table} FOR SELECT USING({read});
          CREATE POLICY model_insert ON {table} FOR INSERT WITH CHECK({admin});
          REVOKE ALL ON {table} FROM PUBLIC,{project_role},{auth_role};
          GRANT SELECT,INSERT ON {table} TO {project_role};
        """)
        if table != "model_definitions":
            columns = "state,state_revision,sync_state" if table == "model_versions" else "state,result,sent_at,updated_at"
            op.execute(f"""CREATE POLICY model_update ON {table} FOR UPDATE USING({admin}) WITH CHECK({admin});
              GRANT UPDATE({columns}) ON {table} TO {project_role};""")


def downgrade() -> None:
    op.execute("DROP TABLE model_operations,model_versions,model_definitions,tenant_admin_grants")
