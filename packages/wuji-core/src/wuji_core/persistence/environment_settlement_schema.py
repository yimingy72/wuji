"""P05 incremental: settle a Run whose environment ended without evidence.

Task A attempt 2 proved the gap: a Run can be registered, never delivered (the
attempt's receiver bearer expired), and then lose its Pod when the attempt
window closed. ``vnext.project_run_result`` only projected ``incomplete`` when a
``run_operation_settlement`` row existed, and ``vnext_0020`` lets only a Run
credential publish the empty operation set. A Run that never started has no
credential, so nothing could ever settle it and ``roll_runtime_attempt`` stayed
blocked by ``attempt_has_unsettled_run``.

This migration keeps the projection function as the single writer of
``result_state`` and adds one bounded alternative to the settlement precheck:
the platform may project a Run whose last observation is ``environment_stopped``
when it holds no execution evidence at all -- no process identity, no admitted
tool attempt, no model request in flight. That is not proof the process never
ran; it is the statement that the platform cannot obtain further evidence, so
the Run is recorded as ``incomplete`` instead of holding its Work item forever.
Every other precondition (owning scope, ``wuji.observe``, final output
expectation, no unreleased reservation, no pending input request, no result
submission) still applies.
"""

from psycopg import sql

from wuji_core.persistence.run_settlement_close_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0021_p05_environment_settlement"

_PROJECTION = """CREATE OR REPLACE FUNCTION vnext.project_run_result(t text,p text,k text,r text,s text)
    RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
    DECLARE chosen text; status_value text; existing text; source_level integer;
    BEGIN
    IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN RAISE EXCEPTION 'result scope denied' USING ERRCODE='42501'; END IF;
    SELECT result_state INTO existing FROM vnext.agent_run WHERE tenant_id=t AND project_id=p AND task_id=k AND agent_run_id=r;
    IF NOT FOUND THEN RAISE EXCEPTION 'run absent' USING ERRCODE='42501'; END IF;
    IF s IS NOT NULL THEN
      PERFORM vnext.require_model_mutation(t,p,k,r,current_setting('wuji.subject',true));
      SELECT rs.access_level INTO source_level FROM vnext.result_submission rs WHERE tenant_id=t AND project_id=p AND task_id=k AND submission_id=s AND agent_run_id=r AND writer_subject=current_setting('wuji.subject',true);
      IF NOT FOUND OR NOT COALESCE(vnext.in_scope(t,p,k,source_level),false) THEN RAISE EXCEPTION 'matching submission required' USING ERRCODE='42501'; END IF;
      SELECT receipt_json::jsonb->>'status' INTO status_value FROM vnext.result_receipt WHERE tenant_id=t AND project_id=p AND task_id=k AND submission_id=s;
      status_value:=COALESCE(status_value,'received');
      IF status_value NOT IN ('received','accepted','rejected','historical_only') THEN RAISE EXCEPTION 'invalid result receipt' USING ERRCODE='23514'; END IF;
      IF existing='accepted' OR (status_value='received' AND existing NOT IN ('none','incomplete')) THEN RETURN existing; END IF;
      UPDATE vnext.agent_run SET result_state=status_value,result_submission_id=s WHERE tenant_id=t AND project_id=p AND task_id=k AND agent_run_id=r;
    ELSE
      IF current_setting('wuji.observe',true) IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'observer required' USING ERRCODE='42501'; END IF;
      UPDATE vnext.agent_run ar SET result_state='incomplete'
      WHERE ar.tenant_id=t AND ar.project_id=p AND ar.task_id=k AND ar.agent_run_id=r AND ar.result_state='none'
      AND ar.output_expectation='final_output' AND ar.process_state='exited' AND ar.stop_kind IN ('exited','environment_stopped')
      AND EXISTS(SELECT 1 FROM vnext.execution_observation e WHERE e.tenant_id=t AND e.project_id=p AND e.task_id=k AND e.agent_run_id=r AND e.receipt_id=ar.last_observation_id AND e.kind IN ('exited','environment_stopped'))
      AND (
        EXISTS(SELECT 1 FROM vnext.run_operation_settlement x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r AND x.status='settled')
        OR (
          ar.stop_kind='environment_stopped'
          AND ar.process_identity_json IS NULL
          AND NOT EXISTS(SELECT 1 FROM vnext.tool_attempt a WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.agent_run_id=r AND (a.status IS NOT NULL OR a.started_at IS NOT NULL))
          AND NOT EXISTS(SELECT 1 FROM vnext.model_call m WHERE m.tenant_id=t AND m.project_id=p AND m.task_id=k AND m.agent_run_id=r AND m.inflight)
        )
      )
      AND NOT EXISTS(SELECT 1 FROM vnext.resource_reservation x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r AND x.state<>'released')
      AND NOT EXISTS(SELECT 1 FROM vnext.input_request i WHERE i.tenant_id=t AND i.project_id=p AND i.task_id=k AND i.work_item_id=ar.work_item_id AND i.status='pending')
      AND NOT EXISTS(SELECT 1 FROM vnext.result_submission x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r);
    END IF;
    RETURN (SELECT result_state FROM vnext.agent_run WHERE tenant_id=t AND project_id=p AND task_id=k AND agent_run_id=r);
    END $$"""


def statements():
    return (_PROJECTION,)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0020_p06_run_settlement_close":
        raise ValueError("P05 environment settlement migration parent changed")
    for statement in statements():
        connection.execute(statement)
    # CREATE OR REPLACE keeps the existing ACLs; restate them so the projection
    # never becomes callable by PUBLIC through a future replacement.
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.project_run_result(text,text,text,text,text) FROM PUBLIC"
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.project_run_result(text,text,text,text,text) TO {}"
        ).format(sql.Identifier(application_role))
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
