"""Add Phase 1B tasks, command receipts, and task event outbox.

Revision ID: 20260910_0003
Revises: 20260910_0002
Create Date: 2026-09-10
"""

from __future__ import annotations

from alembic import context, op

revision = "20260910_0003"
down_revision = "20260910_0002"
branch_labels = None
depends_on = None


def _role(name: str) -> str:
    return context.config.attributes[name]


def upgrade() -> None:
    project_role = _role("project_role")
    op.execute(
        """
        DO $drop_old_preview_checks$
        DECLARE constraint_name text;
        BEGIN
          FOR constraint_name IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'task_previews'::regclass
              AND contype = 'c'
              AND (
                pg_get_constraintdef(oid) ~* 'NOT can_create'
                OR pg_get_constraintdef(oid) ~* 'jsonb_array_length[(]blockers[)] >= 1'
              )
          LOOP
            EXECUTE format('ALTER TABLE task_previews DROP CONSTRAINT %I', constraint_name);
          END LOOP;
        END
        $drop_old_preview_checks$;

        ALTER TABLE task_previews
          ADD CONSTRAINT task_preview_creation_consistency_check
          CHECK (
            (can_create AND jsonb_array_length(blockers) = 0)
            OR (NOT can_create AND jsonb_array_length(blockers) >= 1)
          );

        CREATE TABLE tasks (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            draft jsonb NOT NULL CHECK (jsonb_typeof(draft) = 'object'),
            input_digest char(64) NOT NULL CHECK (input_digest ~ '^[a-f0-9]{64}$'),
            policy_id uuid NOT NULL,
            policy_version bigint NOT NULL CHECK (policy_version BETWEEN 1 AND 9007199254740991),
            policy_hash char(64) NOT NULL CHECK (policy_hash ~ '^[a-f0-9]{64}$'),
            effective_scope jsonb NOT NULL CHECK (jsonb_typeof(effective_scope) = 'object'),
            version bigint NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991),
            state varchar(16) NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'cancelled')),
            cleanup_state varchar(24) NOT NULL DEFAULT 'not_required'
              CHECK (cleanup_state = 'not_required'),
            active_calls bigint NOT NULL DEFAULT 0 CHECK (active_calls = 0),
            unknown_calls bigint NOT NULL DEFAULT 0 CHECK (unknown_calls = 0),
            egress_state varchar(16) NOT NULL DEFAULT 'not_granted'
              CHECK (egress_state = 'not_granted'),
            assessment_outcome varchar(24) NOT NULL DEFAULT 'not_assessed'
              CHECK (assessment_outcome = 'not_assessed'),
            stop_reason varchar(32) CHECK (stop_reason IS NULL OR stop_reason = 'user_cancelled'),
            event_sequence bigint NOT NULL DEFAULT 0
              CHECK (event_sequence BETWEEN 0 AND 9007199254740991),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT task_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT task_policy_fk
              FOREIGN KEY (tenant_id, project_id, policy_id, policy_version, policy_hash)
              REFERENCES scope_policy_versions(
                tenant_id, project_id, policy_id, version, policy_hash
              ) ON DELETE RESTRICT,
            CONSTRAINT task_tenant_project_id_key UNIQUE (tenant_id, project_id, id),
            CHECK (
              (state = 'queued' AND stop_reason IS NULL AND version = 1)
              OR (state = 'cancelled' AND stop_reason = 'user_cancelled' AND version = 2)
            ),
            CHECK (updated_at >= created_at)
        );
        CREATE INDEX task_project_page_idx
          ON tasks (tenant_id, project_id, created_at DESC, id DESC);

        CREATE TABLE command_receipts (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            idempotency_key uuid NOT NULL,
            kind varchar(16) NOT NULL CHECK (kind IN ('create', 'cancel')),
            task_id uuid NOT NULL,
            request_digest char(64) NOT NULL CHECK (request_digest ~ '^[a-f0-9]{64}$'),
            disposition varchar(16) NOT NULL DEFAULT 'accepted' CHECK (disposition = 'accepted'),
            accepted_task_version bigint NOT NULL
              CHECK (accepted_task_version BETWEEN 1 AND 9007199254740991),
            accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT command_receipt_project_fk
              FOREIGN KEY (tenant_id, project_id)
              REFERENCES projects(tenant_id, id) ON DELETE RESTRICT,
            CONSTRAINT command_receipt_task_fk
              FOREIGN KEY (tenant_id, project_id, task_id)
              REFERENCES tasks(tenant_id, project_id, id) ON DELETE RESTRICT,
            CONSTRAINT command_receipt_user_project_key
              UNIQUE (user_id, project_id, idempotency_key)
        );
        CREATE INDEX command_receipt_user_id_idx
          ON command_receipts (tenant_id, project_id, user_id, id);

        CREATE TABLE task_events (
            event_id uuid NOT NULL UNIQUE,
            tenant_id uuid NOT NULL,
            project_id uuid NOT NULL,
            task_id uuid NOT NULL,
            sequence bigint NOT NULL CHECK (sequence BETWEEN 1 AND 9007199254740991),
            aggregate_version bigint NOT NULL
              CHECK (aggregate_version BETWEEN 1 AND 9007199254740991),
            event_type varchar(40) NOT NULL CHECK (event_type = 'task.changed'),
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            trace_id uuid NOT NULL,
            summary varchar(500) NOT NULL CHECK (length(btrim(summary)) > 0),
            outbox_status varchar(16) NOT NULL DEFAULT 'pending' CHECK (outbox_status = 'pending'),
            published_at timestamptz,
            PRIMARY KEY (task_id, sequence),
            CONSTRAINT task_event_task_fk
              FOREIGN KEY (tenant_id, project_id, task_id)
              REFERENCES tasks(tenant_id, project_id, id) ON DELETE RESTRICT,
            CHECK (published_at IS NULL)
        );
        CREATE INDEX task_event_project_task_idx
          ON task_events (tenant_id, project_id, task_id, sequence);

        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE command_receipts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;

        CREATE POLICY task_project_read ON tasks
          FOR SELECT USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = tasks.tenant_id AND pm.project_id = tasks.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.enabled AND tm.enabled
            )
          );
        CREATE POLICY task_operator_insert ON tasks
          FOR INSERT WITH CHECK (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = tasks.tenant_id AND pm.project_id = tasks.project_id
                AND pm.user_id = tasks.user_id AND pm.role = 'operator' AND tm.role = 'operator'
                AND pm.enabled AND tm.enabled
            )
          );
        CREATE POLICY task_operator_update ON tasks
          FOR UPDATE USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = tasks.tenant_id AND pm.project_id = tasks.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.role = 'operator' AND tm.role = 'operator'
                AND pm.enabled AND tm.enabled
            )
          ) WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
          );

        CREATE POLICY command_receipt_submitter_read ON command_receipts
          FOR SELECT USING (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = command_receipts.tenant_id
                AND pm.project_id = command_receipts.project_id
                AND pm.user_id = command_receipts.user_id
                AND pm.enabled AND tm.enabled
            )
          );
        CREATE POLICY command_receipt_operator_insert ON command_receipts
          FOR INSERT WITH CHECK (
            user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            AND tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = command_receipts.tenant_id
                AND pm.project_id = command_receipts.project_id
                AND pm.user_id = command_receipts.user_id
                AND pm.role = 'operator' AND tm.role = 'operator'
                AND pm.enabled AND tm.enabled
            )
          );

        CREATE POLICY task_event_project_read ON task_events
          FOR SELECT USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = task_events.tenant_id
                AND pm.project_id = task_events.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.enabled AND tm.enabled
            )
          );
        CREATE POLICY task_event_operator_insert ON task_events
          FOR INSERT WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
            AND EXISTS (
              SELECT 1 FROM project_memberships pm
              JOIN tenant_memberships tm
                ON tm.tenant_id = pm.tenant_id AND tm.user_id = pm.user_id
              WHERE pm.tenant_id = task_events.tenant_id
                AND pm.project_id = task_events.project_id
                AND pm.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND pm.role = 'operator' AND tm.role = 'operator'
                AND pm.enabled AND tm.enabled
            )
          );
        """
    )
    op.execute(
        f"""
        REVOKE ALL ON tasks, command_receipts, task_events FROM PUBLIC, {project_role};

        GRANT SELECT (id, tenant_id, project_id, draft, policy_id, policy_version,
          version, state, cleanup_state, active_calls, unknown_calls, egress_state,
          assessment_outcome, stop_reason, event_sequence, created_at, updated_at)
          ON tasks TO {project_role};
        GRANT INSERT (id, tenant_id, project_id, user_id, draft, input_digest,
          policy_id, policy_version, policy_hash, effective_scope, version, state,
          cleanup_state, active_calls, unknown_calls, egress_state, assessment_outcome,
          stop_reason, event_sequence) ON tasks TO {project_role};
        GRANT UPDATE (version, state, stop_reason, event_sequence, updated_at)
          ON tasks TO {project_role};

        GRANT SELECT (id, tenant_id, project_id, user_id, idempotency_key, kind,
          task_id, request_digest, disposition, accepted_task_version, accepted_at)
          ON command_receipts TO {project_role};
        GRANT INSERT (id, tenant_id, project_id, user_id, idempotency_key, kind,
          task_id, request_digest, disposition, accepted_task_version)
          ON command_receipts TO {project_role};

        GRANT SELECT (event_id, tenant_id, project_id, task_id, sequence,
          aggregate_version, event_type, occurred_at, trace_id, summary)
          ON task_events TO {project_role};
        GRANT INSERT (event_id, tenant_id, project_id, task_id, sequence,
          aggregate_version, event_type, trace_id, summary)
          ON task_events TO {project_role};

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
        DROP TABLE IF EXISTS task_events;
        DROP TABLE IF EXISTS command_receipts;
        DROP TABLE IF EXISTS tasks;
        ALTER TABLE task_previews DROP CONSTRAINT IF EXISTS task_preview_creation_consistency_check;
        ALTER TABLE task_previews
          ADD CONSTRAINT task_preview_blockers_nonempty_check
          CHECK (jsonb_array_length(blockers) >= 1),
          ADD CONSTRAINT task_preview_creation_disabled_check
          CHECK (NOT can_create);
        """
    )
