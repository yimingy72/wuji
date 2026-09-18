"""P06 incremental: the platform may settle a Run it observed exit.

A Run publishes its own operation settlement when it finishes. A Run that dies
before doing so — the observed M2/E08 failure was a broken transport to the model
gate — leaves its Work pinned at ``operations_unsettled`` or ``OPERATION_UNKNOWN``
forever, because only the Run's own credential was allowed to write that row and
that Run is gone.

The guard's existing rule is preserved: a settlement for a Run with no admitted
tool attempt is accepted only when every durable axis is closed (no non-terminal
attempt, no in-flight model request, no reserved resource). This migration adds
exactly one bounded case on top of it: a controller or reconciler purpose may
publish ``settled`` for the same fully-closed Run **and** only when a terminal
execution observation proves the process can start nothing further. A partially
open Run is still refused, so unknown operations never become settled by
assumption.
"""

from wuji_core.persistence.retention_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0028_p06_platform_run_settlement"


PLATFORM = (
    "current_setting('wuji.observe',true)='true' "
    "OR current_setting('wuji.control',true)='true'"
)


def _replace_policies(connection):
    """Allow the platform's bounded post-exit settlement on both write paths."""

    for policy in ("scoped_insert", "request_insert"):
        connection.execute(
            "DROP POLICY IF EXISTS " + policy + " ON vnext.run_operation_settlement"
        )
    for policy in ("scoped_update", "request_update"):
        connection.execute(
            "DROP POLICY IF EXISTS " + policy + " ON vnext.run_operation_settlement"
        )
    scope = "vnext.in_scope(tenant_id,project_id,task_id)"
    tool = "current_setting('wuji.request_purpose',true) IN ('tool_request','tool_settle')"
    platform = "(" + PLATFORM + ")"
    connection.execute(
        "CREATE POLICY request_insert ON vnext.run_operation_settlement FOR INSERT "
        "WITH CHECK(" + scope + " AND (" + tool + " OR (" + platform + " AND status='settled')))"
    )
    connection.execute(
        "CREATE POLICY request_update ON vnext.run_operation_settlement FOR UPDATE "
        "USING(" + scope + " AND (" + tool + " OR " + platform + ")) "
        "WITH CHECK(" + scope + " AND (" + tool + " OR (" + platform + " AND status='settled')))"
    )


def statements():
    return (
        """CREATE OR REPLACE FUNCTION vnext.guard_run_settlement_insert()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        DECLARE observed boolean := false;
        DECLARE platform boolean := current_setting('wuji.observe',true)='true'
          OR current_setting('wuji.control',true)='true'; BEGIN
        IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class
             WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
        IF platform THEN
          SELECT EXISTS(
            SELECT 1 FROM vnext.execution_observation o
             WHERE (o.tenant_id,o.project_id,o.task_id,o.agent_run_id)=
                   (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
               AND o.kind IN ('not_started','exited','environment_stopped')
          ) INTO observed;
        END IF;
        IF platform THEN
          IF NEW.status<>'settled' OR NOT observed
             OR EXISTS(
               SELECT 1 FROM vnext.tool_attempt a
                WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                      (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                  AND a.status IS NOT NULL
                  AND a.status NOT IN ('complete','cancelled','failed')
             )
             OR EXISTS(
               SELECT 1 FROM vnext.model_call m
                WHERE (m.tenant_id,m.project_id,m.task_id,m.agent_run_id)=
                      (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                  AND m.inflight
             )
             OR EXISTS(
               SELECT 1 FROM vnext.resource_reservation r
                WHERE (r.tenant_id,r.project_id,r.task_id,r.agent_run_id)=
                      (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                  AND r.state<>'released'
             ) THEN
            RAISE EXCEPTION 'platform settlement requires an observed exit and closed operations' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END IF;
        IF purpose NOT IN ('tool_request','tool_settle')
           OR (purpose='tool_request' AND NEW.status<>'pending')
           OR (purpose='tool_settle' AND NEW.status NOT IN ('pending','settled'))
           OR NOT (
             EXISTS(
               SELECT 1 FROM vnext.tool_attempt a
                WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                      (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                  AND a.status IS NOT NULL
             )
             OR (
               NEW.status='settled'
               AND NOT EXISTS(
                 SELECT 1 FROM vnext.tool_attempt a
                  WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                        (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                    AND a.status IS NOT NULL
                    AND a.status NOT IN ('complete','cancelled','failed')
               )
               AND NOT EXISTS(
                 SELECT 1 FROM vnext.model_call m
                  WHERE (m.tenant_id,m.project_id,m.task_id,m.agent_run_id)=
                        (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                    AND m.inflight
               )
               AND NOT EXISTS(
                 SELECT 1 FROM vnext.resource_reservation r
                  WHERE (r.tenant_id,r.project_id,r.task_id,r.agent_run_id)=
                        (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                    AND r.state<>'released'
               )
             )
           ) THEN
           RAISE EXCEPTION 'run settlement requires an existing tool attempt or an empty operation set' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
        """CREATE OR REPLACE FUNCTION vnext.guard_run_settlement_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        DECLARE platform boolean := current_setting('wuji.observe',true)='true'
          OR current_setting('wuji.control',true)='true'; BEGIN
        IF platform THEN
          IF NEW.status<>'settled' THEN
            RAISE EXCEPTION 'platform settlement may only publish settled operations' USING ERRCODE='42501';
          END IF;
        ELSIF purpose='tool_request' AND NEW.status<>'pending' THEN
          RAISE EXCEPTION 'tool request cannot forge settled operations' USING ERRCODE='42501';
        ELSIF purpose NOT IN ('tool_request','tool_settle') THEN
          RAISE EXCEPTION 'tool settlement purpose required' USING ERRCODE='42501';
        END IF;
        RETURN NEW;
        END $$""",
    )


def upgrade(connection, application_role):
    del application_role  # Trigger execution grants no direct application call.
    if PARENT_HEAD != "vnext_0027_p16_artifact_purge":
        raise ValueError("platform settlement migration parent changed")
    for statement in statements():
        connection.execute(statement)
    _replace_policies(connection)
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
