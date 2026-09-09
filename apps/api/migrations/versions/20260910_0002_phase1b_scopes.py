"""Add Phase 1B approved scopes and task previews.

Revision ID: 20260910_0002
Revises: 20260909_0001
Create Date: 2026-09-10
"""

from __future__ import annotations

from alembic import context, op

revision = "20260910_0002"
down_revision = "20260909_0001"
branch_labels = None
depends_on = None


def _role(name: str) -> str:
    return context.config.attributes[name]


def upgrade() -> None:
    project_role = _role("project_role")
    op.execute(
        """
        CREATE TABLE authorization_records (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            subject varchar(500) NOT NULL CHECK (length(btrim(subject)) > 0),
            basis varchar(1000) NOT NULL CHECK (length(btrim(basis)) > 0),
            approved_by varchar(320) NOT NULL CHECK (length(btrim(approved_by)) > 0),
            valid_from timestamptz NOT NULL,
            valid_until timestamptz NOT NULL,
            revoked_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT authorization_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT authorization_tenant_project_id_key
              UNIQUE (tenant_id, project_id, id),
            CHECK (valid_until > valid_from)
        );

        CREATE TABLE scope_policy_versions (
            policy_id uuid NOT NULL,
            version bigint NOT NULL CHECK (version BETWEEN 1 AND 9007199254740991),
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            authorization_id uuid NOT NULL,
            scope jsonb NOT NULL CHECK (jsonb_typeof(scope) = 'object'),
            policy_hash char(64) NOT NULL CHECK (policy_hash ~ '^[a-f0-9]{64}$'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (policy_id, version),
            CONSTRAINT scope_policy_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT scope_policy_authorization_fk
              FOREIGN KEY (tenant_id, project_id, authorization_id)
              REFERENCES authorization_records(tenant_id, project_id, id) ON DELETE RESTRICT,
            CONSTRAINT scope_policy_tenant_project_version_key
              UNIQUE (tenant_id, project_id, policy_id, version),
            CONSTRAINT scope_policy_tenant_project_version_hash_key
              UNIQUE (tenant_id, project_id, policy_id, version, policy_hash)
        );
        CREATE INDEX scope_policy_project_page_idx
          ON scope_policy_versions (tenant_id, project_id, created_at DESC, policy_id DESC, version DESC);

        CREATE TABLE task_previews (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            permissions_version bigint NOT NULL
              CHECK (permissions_version BETWEEN 1 AND 9007199254740991),
            draft jsonb NOT NULL CHECK (jsonb_typeof(draft) = 'object'),
            input_digest char(64) NOT NULL CHECK (input_digest ~ '^[a-f0-9]{64}$'),
            policy_id uuid NOT NULL,
            policy_version bigint NOT NULL CHECK (policy_version BETWEEN 1 AND 9007199254740991),
            policy_hash char(64) NOT NULL CHECK (policy_hash ~ '^[a-f0-9]{64}$'),
            effective_scope jsonb NOT NULL CHECK (jsonb_typeof(effective_scope) = 'object'),
            can_create boolean NOT NULL DEFAULT false,
            blockers jsonb NOT NULL CHECK (jsonb_typeof(blockers) = 'array'),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            expires_at timestamptz NOT NULL,
            CONSTRAINT task_preview_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT task_preview_policy_fk
              FOREIGN KEY (tenant_id, project_id, policy_id, policy_version, policy_hash)
              REFERENCES scope_policy_versions(
                tenant_id, project_id, policy_id, version, policy_hash
              )
              ON DELETE RESTRICT,
            CHECK (expires_at <= created_at + interval '5 minutes'),
            CHECK (jsonb_array_length(blockers) >= 1),
            CHECK (NOT can_create)
        );
        CREATE INDEX task_preview_current_user_idx
          ON task_previews (tenant_id, project_id, user_id, created_at DESC);

        ALTER TABLE authorization_records ENABLE ROW LEVEL SECURITY;
        ALTER TABLE scope_policy_versions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_previews ENABLE ROW LEVEL SECURITY;

        CREATE POLICY authorization_project_read ON authorization_records
          FOR SELECT
          USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = authorization_records.tenant_id
                AND pm.project_id = authorization_records.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.enabled AND tm.enabled
            )
          );

        CREATE POLICY scope_policy_project_read ON scope_policy_versions
          FOR SELECT
          USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = scope_policy_versions.tenant_id
                AND pm.project_id = scope_policy_versions.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.enabled AND tm.enabled
            )
          );

        CREATE POLICY task_preview_current_user_read ON task_previews
          FOR SELECT
          USING (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = task_previews.tenant_id
                AND pm.project_id = task_previews.project_id
                AND pm.user_id = task_previews.user_id
                AND pm.enabled AND tm.enabled
            )
          );

        CREATE POLICY task_preview_operator_insert ON task_previews
          FOR INSERT
          WITH CHECK (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = task_previews.tenant_id
                AND pm.project_id = task_previews.project_id
                AND pm.user_id = task_previews.user_id
                AND pm.role = 'operator' AND tm.role = 'operator'
                AND pm.enabled AND tm.enabled
            )
          );
        """
    )
    op.execute(
        f"""
        REVOKE ALL ON authorization_records, scope_policy_versions, task_previews
          FROM PUBLIC, {project_role};

        GRANT SELECT (id, tenant_id, project_id, valid_from, valid_until, revoked_at)
          ON authorization_records TO {project_role};
        GRANT SELECT (policy_id, version, tenant_id, project_id, authorization_id,
          scope, policy_hash, created_at) ON scope_policy_versions TO {project_role};
        GRANT SELECT (id, tenant_id, project_id, user_id, permissions_version, draft,
          input_digest, policy_id, policy_version, policy_hash, effective_scope, can_create,
          blockers, created_at, expires_at) ON task_previews TO {project_role};
        GRANT INSERT (id, tenant_id, project_id, user_id, permissions_version, draft,
          input_digest, policy_id, policy_version, policy_hash, effective_scope, can_create,
          blockers, expires_at) ON task_previews TO {project_role};

        DO $revoke_temp$
        BEGIN
          EXECUTE format(
            'REVOKE TEMPORARY ON DATABASE %I FROM {project_role}', current_database()
          );
        END
        $revoke_temp$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS task_previews;
        DROP TABLE IF EXISTS scope_policy_versions;
        DROP TABLE IF EXISTS authorization_records;
        """
    )
