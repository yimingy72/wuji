"""P12 incremental: a frozen report commit and append-only late amendments.

Closing a Task currently only fixes its state and the two completion decisions.
AC-053 requires more: the delivered report is frozen as immutable bytes with its
own digest, and later counter-evidence is appended as a dispute record instead
of rewriting history or reopening the Task.

Both tables stay read-only for the application role; two SECURITY DEFINER
producers write them with explicit guards. ``freeze`` only accepts an already
closed Task whose completion epoch matches, computes the digest server-side and
refuses the same report key with different bytes. ``amend`` appends one record
per amendment key and flips the commit's dispute state, never its body.
"""

from psycopg import sql

from wuji_core.persistence.judgment_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0024_p12_reports"

_TABLES = (
    f"""CREATE TABLE vnext.report_commit(
      tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
      report_id text NOT NULL, epoch_id text NOT NULL, close_trigger text NOT NULL,
      result_outcome text NOT NULL, body_json text NOT NULL, body_digest text NOT NULL,
      dispute_state text NOT NULL DEFAULT 'clear' CHECK(dispute_state IN ('clear','disputed')),
      access_level integer NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(tenant_id,project_id,task_id,report_id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES vnext.task(tenant_id,project_id,task_id))""",
    f"""CREATE TABLE vnext.report_amendment(
      tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
      amendment_id text NOT NULL, report_id text NOT NULL, reason text NOT NULL,
      evidence_json text NOT NULL, source_receipt_json text NOT NULL,
      authority text NOT NULL CHECK(authority IN ('assessor','controller')),
      access_level integer NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(tenant_id,project_id,task_id,amendment_id),
      FOREIGN KEY(tenant_id,project_id,task_id,report_id)
        REFERENCES vnext.report_commit(tenant_id,project_id,task_id,report_id))""",
)

_POLICIES = (
    "ALTER TABLE vnext.report_commit ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY scoped_read ON vnext.report_commit
       FOR SELECT USING(vnext.in_scope(tenant_id,project_id,task_id,access_level))""",
    "ALTER TABLE vnext.report_amendment ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY scoped_read ON vnext.report_amendment
       FOR SELECT USING(vnext.in_scope(tenant_id,project_id,task_id,access_level))""",
)

_FREEZE = """CREATE FUNCTION vnext.freeze_report_commit(
  t text, p text, k text, report_key text, epoch_key text, body text, level integer)
  RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.report_commit;
  taskrow vnext.task;
  digest_value text;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL
     OR current_setting('wuji.control',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'report commit requires control authority' USING ERRCODE='42501';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k,COALESCE(level,0)),false) THEN
    RAISE EXCEPTION 'report commit out of scope' USING ERRCODE='42501';
  END IF;
  IF report_key IS NULL OR length(report_key) NOT BETWEEN 1 AND 256
     OR epoch_key IS NULL OR length(epoch_key) NOT BETWEEN 1 AND 256
     OR body IS NULL OR length(body) NOT BETWEEN 2 AND 262144 THEN
    RAISE EXCEPTION 'invalid report commit input' USING ERRCODE='22023';
  END IF;
  digest_value := encode(sha256(body::bytea),'hex');
  SELECT * INTO saved FROM vnext.report_commit c
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.report_id=report_key;
  IF FOUND THEN
    IF saved.body_digest IS DISTINCT FROM digest_value
       OR saved.body_digest IS DISTINCT FROM encode(sha256(saved.body_json::bytea),'hex') THEN
      -- Either the caller sent different bytes for this key, or the stored row
      -- is no longer internally consistent. Both refuse instead of rewriting.
      RAISE EXCEPTION 'report key reused with different bytes' USING ERRCODE='23505';
    END IF;
    RETURN saved.report_id;
  END IF;
  SELECT * INTO taskrow FROM vnext.task x
    WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'task absent' USING ERRCODE='42501';
  END IF;
  IF taskrow.observed_state <> 'closed' OR taskrow.completion_epoch_id IS DISTINCT FROM epoch_key THEN
    RAISE EXCEPTION 'report freezes only after that Task closed on this epoch' USING ERRCODE='55000';
  END IF;
  INSERT INTO vnext.report_commit(tenant_id,project_id,task_id,report_id,epoch_id,close_trigger,
    result_outcome,body_json,body_digest,dispute_state,access_level)
  VALUES(t,p,k,report_key,epoch_key,taskrow.close_trigger,taskrow.result_outcome,body,digest_value,
    'clear',COALESCE(level,0));
  RETURN report_key;
END $$"""

_AMEND = """CREATE FUNCTION vnext.amend_report_commit(
  t text, p text, k text, report_key text, amendment_key text, reason text,
  evidence_json text, source_receipt text, authority text, level integer)
  RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.report_amendment;
  commit_row vnext.report_commit;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL THEN
    RAISE EXCEPTION 'report amendment requires a scoped caller' USING ERRCODE='42501';
  END IF;
  IF authority='assessor' AND current_setting('wuji.assess',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'report amendment requires assessment authority' USING ERRCODE='42501';
  END IF;
  IF authority='controller' AND current_setting('wuji.control',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'report amendment requires control authority' USING ERRCODE='42501';
  END IF;
  IF authority NOT IN ('assessor','controller') THEN
    RAISE EXCEPTION 'invalid report amendment authority' USING ERRCODE='22023';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k,COALESCE(level,0)),false) THEN
    RAISE EXCEPTION 'report amendment out of scope' USING ERRCODE='42501';
  END IF;
  IF amendment_key IS NULL OR length(amendment_key) NOT BETWEEN 1 AND 256
     OR report_key IS NULL OR length(report_key) NOT BETWEEN 1 AND 256
     OR reason IS NULL OR length(reason) NOT BETWEEN 1 AND 2048
     OR evidence_json IS NULL OR length(evidence_json) NOT BETWEEN 2 AND 65536
     OR source_receipt IS NULL OR length(source_receipt) NOT BETWEEN 2 AND 65536 THEN
    RAISE EXCEPTION 'invalid report amendment input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.report_amendment a
    WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.amendment_id=amendment_key;
  IF FOUND THEN
    IF saved.source_receipt_json IS DISTINCT FROM source_receipt THEN
      RAISE EXCEPTION 'amendment key reused with different evidence' USING ERRCODE='23505';
    END IF;
    RETURN saved.amendment_id;
  END IF;
  SELECT * INTO commit_row FROM vnext.report_commit c
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.report_id=report_key FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'report commit absent' USING ERRCODE='42501';
  END IF;
  INSERT INTO vnext.report_amendment(tenant_id,project_id,task_id,amendment_id,report_id,reason,
    evidence_json,source_receipt_json,authority,access_level)
  VALUES(t,p,k,amendment_key,report_key,reason,evidence_json,source_receipt,authority,COALESCE(level,0));
  UPDATE vnext.report_commit c SET dispute_state='disputed'
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.report_id=report_key;
  RETURN amendment_key;
END $$"""

_FREEZE_SIGNATURE = "text,text,text,text,text,text,integer"
_AMEND_SIGNATURE = "text,text,text,text,text,text,text,text,text,integer"


def statements():
    return _TABLES + _POLICIES + (_FREEZE, _AMEND)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0023_p12_judgments":
        raise ValueError("P12 report migration parent changed")
    for statement in statements():
        connection.execute(statement)
    app = sql.Identifier(application_role)
    for table in ("report_commit", "report_amendment"):
        connection.execute(
            sql.SQL("GRANT SELECT ON vnext.{} TO {}").format(sql.Identifier(table), app)
        )
    for name, signature in (
        ("freeze_report_commit", _FREEZE_SIGNATURE),
        ("amend_report_commit", _AMEND_SIGNATURE),
    ):
        connection.execute(
            sql.SQL("REVOKE EXECUTE ON FUNCTION vnext.{}(" + signature + ") FROM PUBLIC").format(
                sql.Identifier(name)
            )
        )
        connection.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION vnext.{}(" + signature + ") TO {}").format(
                sql.Identifier(name), app
            )
        )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
