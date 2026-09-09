"""Create the Phase 1A identity and project authority tables.

Revision ID: 20260909_0001
Revises:
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import context, op

revision = "20260909_0001"
down_revision = None
branch_labels = None
depends_on = None


def _role(name: str) -> str:
    # env.py admits only lower-case PostgreSQL identifiers.
    return context.config.attributes[name]


def upgrade() -> None:
    auth_role = _role("auth_role")
    project_role = _role("project_role")
    op.execute(
        """
        CREATE TABLE users (
            id uuid PRIMARY KEY,
            display_name varchar(100) NOT NULL CHECK (length(display_name) > 0),
            enabled boolean NOT NULL DEFAULT true,
            permissions_version bigint NOT NULL DEFAULT 1 CHECK (permissions_version >= 1),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );

        CREATE TABLE external_identities (
            id uuid PRIMARY KEY,
            issuer varchar(512) NOT NULL,
            subject varchar(255) NOT NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            username varchar(255),
            email varchar(320),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT external_identity_issuer_subject_key UNIQUE (issuer, subject)
        );

        CREATE TABLE tenants (
            id uuid PRIMARY KEY,
            name varchar(120) NOT NULL CHECK (length(name) > 0),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );

        CREATE TABLE tenant_memberships (
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            role varchar(16) NOT NULL CHECK (role IN ('operator', 'viewer')),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (tenant_id, user_id),
            CONSTRAINT tenant_membership_tenant_user_key UNIQUE (tenant_id, user_id)
        );

        CREATE TABLE projects (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            name varchar(120) NOT NULL CHECK (length(name) > 0),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT project_tenant_id_key UNIQUE (tenant_id, id)
        );

        CREATE TABLE project_memberships (
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            user_id uuid NOT NULL,
            role varchar(16) NOT NULL CHECK (role IN ('operator', 'viewer')),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (tenant_id, project_id, user_id),
            CONSTRAINT project_membership_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT project_membership_tenant_user_fk
              FOREIGN KEY (tenant_id, user_id)
              REFERENCES tenant_memberships(tenant_id, user_id) ON DELETE RESTRICT
        );

        CREATE TABLE sessions (
            id uuid PRIMARY KEY,
            token_hash char(64) NOT NULL UNIQUE,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            csrf_token varchar(128) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            last_seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            absolute_expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            CHECK (absolute_expires_at > created_at)
        );
        CREATE INDEX sessions_user_active_idx ON sessions (user_id, revoked_at);

        CREATE TABLE oidc_handshakes (
            id uuid PRIMARY KEY,
            state_hash char(64) NOT NULL UNIQUE,
            binding_hash char(64) NOT NULL,
            nonce varchar(128) NOT NULL,
            code_verifier varchar(128) NOT NULL,
            return_to varchar(2048) NOT NULL,
            status varchar(16) NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending', 'exchanging', 'consumed', 'failed', 'replaced')),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            expires_at timestamptz NOT NULL,
            claimed_at timestamptz,
            consumed_at timestamptz,
            CHECK (expires_at > created_at)
        );
        CREATE INDEX oidc_handshake_binding_idx
          ON oidc_handshakes (binding_hash, expires_at DESC);

        CREATE TABLE identity_audit (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id uuid REFERENCES users(id) ON DELETE RESTRICT,
            action varchar(80) NOT NULL,
            actor varchar(160) NOT NULL,
            details jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );
        CREATE INDEX identity_audit_user_created_idx
          ON identity_audit (user_id, created_at DESC);

        ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
        ALTER TABLE project_memberships ENABLE ROW LEVEL SECURITY;

        CREATE POLICY tenant_membership_current_user ON tenant_memberships
          FOR SELECT
          USING (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND enabled
          );

        CREATE POLICY project_membership_current_user ON project_memberships
          FOR SELECT
          USING (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND enabled
            AND EXISTS (
              SELECT 1 FROM tenant_memberships tm
              WHERE tm.tenant_id = project_memberships.tenant_id
                AND tm.user_id = project_memberships.user_id
                AND tm.enabled
            )
            AND (
              NULLIF(current_setting('app.tenant_id', true), '') IS NULL
              OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            AND (
              NULLIF(current_setting('app.project_id', true), '') IS NULL
              OR project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            )
          );

        CREATE POLICY project_current_user ON projects
          FOR SELECT
          USING (
            enabled
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              WHERE pm.tenant_id = projects.tenant_id
                AND pm.project_id = projects.id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.enabled
            )
            AND (
              NULLIF(current_setting('app.tenant_id', true), '') IS NULL
              OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            AND (
              NULLIF(current_setting('app.project_id', true), '') IS NULL
              OR id = NULLIF(current_setting('app.project_id', true), '')::uuid
            )
          );

        CREATE POLICY tenant_current_user ON tenants
          FOR SELECT
          USING (
            enabled
            AND EXISTS (
              SELECT 1 FROM tenant_memberships tm
              WHERE tm.tenant_id = tenants.id
                AND tm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND tm.enabled
            )
            AND (
              NULLIF(current_setting('app.tenant_id', true), '') IS NULL
              OR id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
          );
        """
    )

    op.execute(
        f"""
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;

        GRANT SELECT ON users, external_identities TO {auth_role};
        GRANT SELECT, INSERT, UPDATE, DELETE ON sessions, oidc_handshakes TO {auth_role};
        GRANT INSERT ON identity_audit TO {auth_role};
        GRANT USAGE, SELECT ON SEQUENCE identity_audit_id_seq TO {auth_role};
        GRANT SELECT ON alembic_version TO {auth_role};

        GRANT SELECT (id, name, enabled, created_at) ON tenants TO {project_role};
        GRANT SELECT (tenant_id, user_id, role, enabled, created_at, updated_at)
          ON tenant_memberships TO {project_role};
        GRANT SELECT (id, tenant_id, name, enabled, created_at) ON projects TO {project_role};
        GRANT SELECT (tenant_id, project_id, user_id, role, enabled, created_at, updated_at)
          ON project_memberships TO {project_role};
        GRANT SELECT ON alembic_version TO {project_role};
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS identity_audit;
        DROP TABLE IF EXISTS oidc_handshakes;
        DROP TABLE IF EXISTS sessions;
        DROP TABLE IF EXISTS project_memberships;
        DROP TABLE IF EXISTS projects;
        DROP TABLE IF EXISTS tenant_memberships;
        DROP TABLE IF EXISTS tenants;
        DROP TABLE IF EXISTS external_identities;
        DROP TABLE IF EXISTS users;
        """
    )
