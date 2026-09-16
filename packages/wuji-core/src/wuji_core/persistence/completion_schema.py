"""P12 incremental: a platform-authored completion decision can be persisted.

``vnext.completion_decision`` is read-only for the application role on purpose:
the P05 state machine consumes a *canonical* decision and must never accept a
caller's own close/Goal assertion. Until now nothing could write one, so the
P12 precheck had no way to propose a completion epoch.

This migration adds one SECURITY DEFINER producer with explicit guards: the
transaction must carry control authority for that exact Task, the Task must be
activated and not already closing, and the expected control version and board
revision must still match. The receipt key makes the call idempotent; reusing a
key with different source bytes is refused instead of overwriting a decision.
"""

from psycopg import sql

from wuji_core.persistence.environment_settlement_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0022_p12_completion"

_PREPARE = """CREATE FUNCTION vnext.prepare_completion_quiesce(
  t text, p text, k text, receipt_key text, epoch_key text,
  expected_control_version numeric, expected_board_revision numeric,
  deadline timestamptz, close_trigger text, source_receipt text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  taskrow vnext.task;
  saved vnext.completion_decision;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL OR current_setting('wuji.control',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'completion decision requires control authority' USING ERRCODE='42501';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN
    RAISE EXCEPTION 'completion decision out of scope' USING ERRCODE='42501';
  END IF;
  IF receipt_key IS NULL OR length(receipt_key) NOT BETWEEN 1 AND 256
     OR epoch_key IS NULL OR length(epoch_key) NOT BETWEEN 1 AND 256
     OR close_trigger IS NULL OR close_trigger NOT IN ('goal_satisfied','budget_exhausted',
        'time_limit','no_progress','system_failure','operator_finish')
     OR deadline IS NULL OR source_receipt IS NULL OR length(source_receipt) NOT BETWEEN 1 AND 65536 THEN
    RAISE EXCEPTION 'invalid completion decision input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.completion_decision d
    WHERE d.tenant_id=t AND d.project_id=p AND d.task_id=k AND d.receipt_id=receipt_key;
  IF FOUND THEN
    IF saved.source_receipt_json IS DISTINCT FROM source_receipt OR saved.action<>'quiesce' THEN
      RAISE EXCEPTION 'completion receipt reused with different input' USING ERRCODE='23505';
    END IF;
    RETURN saved.receipt_id;
  END IF;
  SELECT * INTO taskrow FROM vnext.task x
    WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'task absent' USING ERRCODE='42501';
  END IF;
  IF taskrow.activated_at IS NULL OR taskrow.observed_state='closed' OR taskrow.completion_epoch_id IS NOT NULL THEN
    RAISE EXCEPTION 'task cannot start a completion epoch' USING ERRCODE='55000';
  END IF;
  IF taskrow.control_version<>expected_control_version OR taskrow.board_revision<>expected_board_revision THEN
    RAISE EXCEPTION 'completion decision is stale' USING ERRCODE='40001';
  END IF;
  INSERT INTO vnext.completion_decision(tenant_id,project_id,task_id,receipt_id,epoch_id,action,
    expected_control_version,board_revision,deadline,close_trigger,result_outcome,source_receipt_json)
  VALUES(t,p,k,receipt_key,epoch_key,'quiesce',expected_control_version,expected_board_revision,
    deadline,close_trigger,NULL,source_receipt);
  RETURN receipt_key;
END $$"""


def statements():
    return (_PREPARE,)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0021_p05_environment_settlement":
        raise ValueError("P12 completion migration parent changed")
    for statement in statements():
        connection.execute(statement)
    connection.execute(
        sql.SQL(
            "REVOKE EXECUTE ON FUNCTION vnext.prepare_completion_quiesce("
            "text,text,text,text,text,numeric,numeric,timestamptz,text,text) FROM PUBLIC"
        )
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.prepare_completion_quiesce("
            "text,text,text,text,text,numeric,numeric,timestamptz,text,text) TO {}"
        ).format(sql.Identifier(application_role))
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
