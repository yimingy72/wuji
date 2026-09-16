"""P06 incremental: a Run that never opened an operation can still close it.

``vnext.guard_run_settlement_insert`` originally required an existing
``tool_attempt`` row before any settlement row could exist. A Run refused before
its first tool attempt registers nothing at all, so no producer ever published a
settlement for it and ``vnext.operations_settled`` could never accept it: the
Work item stayed at ``operations_unsettled`` forever even though the platform
held no open operation for that Run.

The guard keeps its original rule for every Run that had an admitted tool attempt
and adds one bounded case: a Run may publish ``settled`` for an empty operation
set, which requires that no attempt is in a non-terminal state, no model request
is in flight and no resource is reserved or unreleased. A proposal that was
never admitted (a NULL attempt status) cannot have executed anything, and a
later admission still moves the settlement back to ``pending``. The empty
operation set is then explicit rather than indistinguishable from unknown.
"""

from wuji_core.persistence.task_creation_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0020_p06_run_settlement_close"


def statements():
    return (
        """CREATE OR REPLACE FUNCTION vnext.guard_run_settlement_insert()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class
             WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
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
    )


def upgrade(connection, application_role):
    del application_role  # Trigger execution grants no direct application call.
    if PARENT_HEAD != "vnext_0019_p11_task_creation":
        raise ValueError("P06 run settlement migration parent changed")
    for statement in statements():
        connection.execute(statement)
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
