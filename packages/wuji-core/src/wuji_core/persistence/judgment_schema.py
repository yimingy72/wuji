"""P12 incremental: platform-authored Goal judgments and the closing decision.

``goal_criterion`` and ``criterion_judgment`` are read-only for the application
role, and the completion epoch had no producer for the final ``close`` action.
This migration adds two SECURITY DEFINER producers with explicit guards:

- ``record_criterion_judgment`` freezes the criterion definition, records the
  judgment for exactly that revision, and moves ``current_judgment_id`` only
  forward. A judgment about an *older* revision is still recorded (late
  counter-evidence) but never becomes current.
- ``prepare_completion_close`` writes the closing decision for the Task's own
  completion epoch with ``close_trigger`` and ``result_outcome`` as two
  independent fields.
"""

from psycopg import sql

from wuji_core.persistence.completion_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0023_p12_judgments"

_JUDGMENT = """CREATE FUNCTION vnext.record_criterion_judgment(
  t text, p text, k text, criterion_key text, criterion_revision numeric,
  judgment_key text, judgment_status text, judgment_applicability text,
  method text, definition_json text, source_receipt text, level integer) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.criterion_judgment;
  current_judgment text;
  latest_revision numeric;
  saved_definition text;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL
     OR current_setting('wuji.assess',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'criterion judgment requires assessment authority' USING ERRCODE='42501';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k,COALESCE(level,0)),false) THEN
    RAISE EXCEPTION 'criterion judgment out of scope' USING ERRCODE='42501';
  END IF;
  IF criterion_key IS NULL OR length(criterion_key) NOT BETWEEN 1 AND 256
     OR criterion_revision IS NULL OR criterion_revision < 1 OR criterion_revision <> trunc(criterion_revision)
     OR judgment_key IS NULL OR length(judgment_key) NOT BETWEEN 1 AND 256
     OR judgment_status NOT IN ('met','not_met','unknown','not_applicable')
     OR judgment_applicability NOT IN ('current','stale','disputed','retracted')
     OR method IS NULL OR length(method) NOT BETWEEN 1 AND 256
     OR definition_json IS NULL OR length(definition_json) NOT BETWEEN 2 AND 65536
     OR source_receipt IS NULL OR length(source_receipt) NOT BETWEEN 2 AND 65536 THEN
    RAISE EXCEPTION 'invalid criterion judgment input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.criterion_judgment j
    WHERE j.tenant_id=t AND j.project_id=p AND j.task_id=k AND j.judgment_id=judgment_key;
  IF FOUND THEN
    IF saved.source_receipt_json IS DISTINCT FROM source_receipt THEN
      RAISE EXCEPTION 'judgment key reused with different evidence' USING ERRCODE='23505';
    END IF;
    RETURN saved.judgment_id;
  END IF;
  SELECT c.definition_json, c.current_judgment_id INTO saved_definition, current_judgment
    FROM vnext.goal_criterion c
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k
      AND c.criterion_id=criterion_key AND c.revision=criterion_revision FOR UPDATE;
  IF NOT FOUND THEN
    -- A judgment about a revision the platform has not materialised yet still
    -- needs its own frozen criterion row; the current pointer below decides
    -- whether it may define the Goal.
    INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,revision,definition_json)
      VALUES(t,p,k,criterion_key,criterion_revision,definition_json);
  ELSIF saved_definition IS DISTINCT FROM definition_json THEN
    RAISE EXCEPTION 'criterion definition changed for that revision' USING ERRCODE='23505';
  END IF;
  INSERT INTO vnext.criterion_judgment(tenant_id,project_id,task_id,judgment_id,criterion_id,
    criterion_revision,status,applicability,source_receipt_json,access_level)
    VALUES(t,p,k,judgment_key,criterion_key,criterion_revision,judgment_status,
      judgment_applicability,source_receipt,COALESCE(level,0));
  SELECT MAX(c.revision) INTO latest_revision FROM vnext.goal_criterion c
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.criterion_id=criterion_key;
  IF criterion_revision = latest_revision THEN
    UPDATE vnext.goal_criterion SET current_judgment_id=judgment_key
      WHERE tenant_id=t AND project_id=p AND task_id=k
        AND criterion_id=criterion_key AND revision=criterion_revision;
  END IF;
  -- A judgment about a superseded revision is recorded for the report (late
  -- counter-evidence) but never becomes the current judgment.
  RETURN judgment_key;
END $$"""

_CLOSE = """CREATE FUNCTION vnext.prepare_completion_close(
  t text, p text, k text, receipt_key text, epoch_key text, expected_control_version numeric,
  expected_board_revision numeric, deadline timestamptz, close_trigger text,
  result_outcome text, source_receipt text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.completion_decision;
  taskrow vnext.task;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL OR current_setting('wuji.control',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'closing decision requires control authority' USING ERRCODE='42501';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN
    RAISE EXCEPTION 'closing decision out of scope' USING ERRCODE='42501';
  END IF;
  IF receipt_key IS NULL OR length(receipt_key) NOT BETWEEN 1 AND 256
     OR epoch_key IS NULL OR length(epoch_key) NOT BETWEEN 1 AND 256
     OR close_trigger IS NULL OR close_trigger NOT IN ('goal_satisfied','user_cancel',
        'budget_exhausted','time_limit','no_progress','system_failure','operator_finish')
     OR result_outcome IS NULL OR result_outcome NOT IN ('complete','partial','inconclusive','not_assessed')
     OR deadline IS NULL OR source_receipt IS NULL OR length(source_receipt) NOT BETWEEN 2 AND 65536 THEN
    RAISE EXCEPTION 'invalid closing decision input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.completion_decision d
    WHERE d.tenant_id=t AND d.project_id=p AND d.task_id=k AND d.receipt_id=receipt_key;
  IF FOUND THEN
    IF saved.source_receipt_json IS DISTINCT FROM source_receipt OR saved.action<>'close' THEN
      RAISE EXCEPTION 'closing receipt reused with different input' USING ERRCODE='23505';
    END IF;
    RETURN saved.receipt_id;
  END IF;
  SELECT * INTO taskrow FROM vnext.task x
    WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'task absent' USING ERRCODE='42501';
  END IF;
  IF taskrow.completion_epoch_id IS DISTINCT FROM epoch_key THEN
    RAISE EXCEPTION 'closing decision does not match the open completion epoch' USING ERRCODE='40001';
  END IF;
  IF taskrow.control_version<>expected_control_version OR taskrow.board_revision<>expected_board_revision THEN
    RAISE EXCEPTION 'closing decision is stale' USING ERRCODE='40001';
  END IF;
  INSERT INTO vnext.completion_decision(tenant_id,project_id,task_id,receipt_id,epoch_id,action,
    expected_control_version,board_revision,deadline,close_trigger,result_outcome,source_receipt_json)
  VALUES(t,p,k,receipt_key,epoch_key,'close',expected_control_version,expected_board_revision,
    deadline,close_trigger,result_outcome,source_receipt);
  RETURN receipt_key;
END $$"""

_JUDGMENT_SIGNATURE = (
    "text,text,text,text,numeric,text,text,text,text,text,text,integer"
)
_CLOSE_SIGNATURE = (
    "text,text,text,text,text,numeric,numeric,timestamptz,text,text,text"
)


def statements():
    return (_JUDGMENT, _CLOSE)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0022_p12_completion":
        raise ValueError("P12 judgment migration parent changed")
    for statement in statements():
        connection.execute(statement)
    for name, signature in (
        ("record_criterion_judgment", _JUDGMENT_SIGNATURE),
        ("prepare_completion_close", _CLOSE_SIGNATURE),
    ):
        connection.execute(
            sql.SQL("REVOKE EXECUTE ON FUNCTION vnext.{}(" + signature + ") FROM PUBLIC").format(
                sql.Identifier(name)
            )
        )
        connection.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION vnext.{}(" + signature + ") TO {}").format(
                sql.Identifier(name), sql.Identifier(application_role)
            )
        )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
