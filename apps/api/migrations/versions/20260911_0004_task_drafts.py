"""Add user-owned task drafts without changing executable tasks.

Revision ID: 20260911_0004
Revises: 20260910_0003
Create Date: 2026-09-11
"""

from __future__ import annotations

from alembic import context, op

revision = "20260911_0004"
down_revision = "20260910_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    project_role = context.config.attributes["project_role"]
    auth_role = context.config.attributes["auth_role"]
    op.execute(
        """
        CREATE TABLE task_drafts (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            content jsonb NOT NULL,
            content_digest char(64) NOT NULL CHECK (content_digest ~ '^[a-f0-9]{64}$'),
            version bigint NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT task_draft_project_fk FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CHECK (jsonb_typeof(content) = 'object'),
            CHECK ((content->'schema_version' = '"1.0"'::jsonb) IS TRUE),
            CHECK ((content->>'scenario' IN
              ('ctf', 'web_single', 'comprehensive', 'exercise', 'code_audit')) IS TRUE),
            CHECK (octet_length(content::text) <= 131072),
            CHECK (updated_at >= created_at)
        );
        CREATE INDEX task_draft_user_page_idx
          ON task_drafts (tenant_id, project_id, user_id, created_at DESC, id DESC);
        ALTER TABLE task_drafts ENABLE ROW LEVEL SECURITY;
        """
    )
    # jsonb's textual rendering adds whitespace; the store enforces the exact
    # 64KiB canonical input limit while this bound also protects direct writes.
    readable = """
        user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
        AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
        AND EXISTS (
          SELECT 1 FROM projects p
          JOIN tenants t ON t.id = p.tenant_id
          JOIN project_memberships pm
            ON pm.tenant_id = p.tenant_id AND pm.project_id = p.id
          JOIN tenant_memberships tm
            ON tm.tenant_id = p.tenant_id AND tm.user_id = pm.user_id
          WHERE p.tenant_id = task_drafts.tenant_id AND p.id = task_drafts.project_id
            AND pm.user_id = task_drafts.user_id
            AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled
            {operator}
        )
    """
    writable = readable.format(operator="AND pm.role = 'operator' AND tm.role = 'operator'")
    op.execute(
        f"""
        CREATE POLICY task_draft_owner_read ON task_drafts
          FOR SELECT USING ({readable.format(operator='')});
        CREATE POLICY task_draft_operator_insert ON task_drafts
          FOR INSERT WITH CHECK ({writable});
        CREATE POLICY task_draft_operator_update ON task_drafts
          FOR UPDATE USING ({writable}) WITH CHECK ({writable});

        REVOKE ALL ON task_drafts FROM PUBLIC, {project_role}, {auth_role};
        GRANT SELECT ON task_drafts TO {project_role};
        GRANT INSERT (id, tenant_id, project_id, user_id, content, content_digest, version)
          ON task_drafts TO {project_role};
        GRANT UPDATE (content, content_digest, version, updated_at)
          ON task_drafts TO {project_role};
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE task_drafts")
