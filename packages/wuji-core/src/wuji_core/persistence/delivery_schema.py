"""P16 incremental: one immutable delivery record per frozen report.

AC-069 asks for deliveries that follow the media their profile actually
requires. A delivery therefore never invents material: it cites the frozen
report digest, indexes the sealed artifacts the profile asks for, and records
which required ones are missing. ``ready`` and ``incomplete`` are decided by the
manifest the platform composed, and the database refuses a ``ready`` row that
still lists a missing *required* material -- so the state cannot be talked into
looking complete.

The transport is part of the record. An ``offline`` delivery must store no HTTP
exchange at all, and an ``http`` delivery that claims ``ready`` must cite the
exchange receipt that actually happened. Nothing here fabricates a "not
applicable" HTTP record for an offline document.
"""

from psycopg import sql

from wuji_core.persistence.view_stream_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0026_p16_report_delivery"

_TABLES = (
    """CREATE TABLE vnext.report_delivery(
      tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
      delivery_id text NOT NULL, report_id text NOT NULL, report_digest text NOT NULL,
      epoch_id text NOT NULL, profile_id text NOT NULL, profile_digest text NOT NULL,
      profile_json text NOT NULL,
      state text NOT NULL CHECK(state IN ('delivery_pending','ready','incomplete','failed')),
      mode text NOT NULL CHECK(mode IN ('offline','http')),
      missing_json text, manifest_json text, manifest_digest text,
      exchange_json text, error_code text,
      access_level integer NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(tenant_id,project_id,task_id,delivery_id),
      FOREIGN KEY(tenant_id,project_id,task_id) REFERENCES vnext.task(tenant_id,project_id,task_id),
      FOREIGN KEY(tenant_id,project_id,task_id,report_id)
        REFERENCES vnext.report_commit(tenant_id,project_id,task_id,report_id))""",
)

_POLICIES = (
    "ALTER TABLE vnext.report_delivery ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY scoped_read ON vnext.report_delivery
       FOR SELECT USING(vnext.in_scope(tenant_id,project_id,task_id,access_level))""",
)

_RECORD = """CREATE FUNCTION vnext.record_report_delivery(
  t text, p text, k text, delivery_key text, report_key text, report_digest text,
  profile_key text, profile_json text, state text, mode text, missing_json text,
  manifest_json text, exchange_json text, error_code text, level integer)
  RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.report_delivery;
  commit_row vnext.report_commit;
  taskrow vnext.task;
  required_missing integer;
  manifest_value text;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL
     OR current_setting('wuji.control',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'report delivery requires control authority' USING ERRCODE='42501';
  END IF;
  IF NOT COALESCE(vnext.in_scope(t,p,k,COALESCE(level,0)),false) THEN
    RAISE EXCEPTION 'report delivery out of scope' USING ERRCODE='42501';
  END IF;
  IF delivery_key IS NULL OR length(delivery_key) NOT BETWEEN 1 AND 256
     OR report_key IS NULL OR length(report_key) NOT BETWEEN 1 AND 256
     OR profile_key IS NULL OR length(profile_key) NOT BETWEEN 1 AND 256
     OR report_digest IS NULL OR report_digest !~ '^[0-9a-f]{64}$'
     OR profile_json IS NULL OR length(profile_json) NOT BETWEEN 2 AND 65536
     OR state IS NULL OR state NOT IN ('delivery_pending','ready','incomplete','failed')
     OR mode IS NULL OR mode NOT IN ('offline','http') THEN
    RAISE EXCEPTION 'invalid report delivery input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.report_delivery d
    WHERE d.tenant_id=t AND d.project_id=p AND d.task_id=k AND d.delivery_id=delivery_key;
  IF FOUND THEN
    IF saved.report_id IS DISTINCT FROM report_key
       OR saved.report_digest IS DISTINCT FROM report_digest
       OR saved.profile_json IS DISTINCT FROM profile_json
       OR saved.state IS DISTINCT FROM state
       OR saved.mode IS DISTINCT FROM mode
       OR saved.missing_json IS DISTINCT FROM missing_json
       OR saved.manifest_json IS DISTINCT FROM manifest_json
       OR saved.exchange_json IS DISTINCT FROM exchange_json
       OR saved.error_code IS DISTINCT FROM error_code THEN
      RAISE EXCEPTION 'delivery key reused with different content' USING ERRCODE='23505';
    END IF;
    RETURN saved.delivery_id;
  END IF;
  SELECT * INTO commit_row FROM vnext.report_commit c
    WHERE c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.report_id=report_key;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'report commit absent' USING ERRCODE='42501';
  END IF;
  SELECT * INTO taskrow FROM vnext.task x
    WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'task absent' USING ERRCODE='42501';
  END IF;
  IF taskrow.observed_state <> 'closed'
     OR taskrow.completion_epoch_id IS DISTINCT FROM commit_row.epoch_id THEN
    RAISE EXCEPTION 'a delivery only follows that closed Task report' USING ERRCODE='55000';
  END IF;
  IF commit_row.body_digest IS DISTINCT FROM report_digest THEN
    RAISE EXCEPTION 'delivery must cite the frozen report bytes' USING ERRCODE='55000';
  END IF;
  IF manifest_json IS NOT NULL THEN
    IF length(manifest_json) NOT BETWEEN 2 AND 262144 THEN
      RAISE EXCEPTION 'invalid delivery manifest input' USING ERRCODE='22023';
    END IF;
    manifest_value := manifest_json;
  END IF;
  IF missing_json IS NULL THEN
    required_missing := NULL;
  ELSE
    IF length(missing_json) NOT BETWEEN 2 AND 65536 THEN
      RAISE EXCEPTION 'invalid delivery missing input' USING ERRCODE='22023';
    END IF;
    BEGIN
      SELECT count(*) INTO required_missing FROM jsonb_array_elements(missing_json::jsonb) e
        WHERE COALESCE((e->>'required')::boolean,false);
    EXCEPTION WHEN others THEN
      RAISE EXCEPTION 'delivery missing list is not a JSON array' USING ERRCODE='22023';
    END;
  END IF;
  IF state='ready' THEN
    IF manifest_value IS NULL OR required_missing IS NULL OR required_missing <> 0 THEN
      RAISE EXCEPTION 'a ready delivery has no missing required material' USING ERRCODE='22023';
    END IF;
  ELSIF state='incomplete' THEN
    IF manifest_value IS NULL OR required_missing IS NULL OR required_missing < 1 THEN
      RAISE EXCEPTION 'an incomplete delivery names the missing material' USING ERRCODE='22023';
    END IF;
  ELSIF state='failed' THEN
    IF error_code IS NULL OR error_code !~ '^[a-z][a-z0-9_]{1,63}$' THEN
      RAISE EXCEPTION 'a failed delivery carries a bounded error code' USING ERRCODE='22023';
    END IF;
  ELSE
    IF manifest_value IS NOT NULL OR missing_json IS NOT NULL
       OR exchange_json IS NOT NULL OR error_code IS NOT NULL THEN
      RAISE EXCEPTION 'a pending delivery claims nothing yet' USING ERRCODE='22023';
    END IF;
  END IF;
  IF mode='offline' THEN
    IF exchange_json IS NOT NULL THEN
      RAISE EXCEPTION 'an offline delivery stores no HTTP exchange' USING ERRCODE='22023';
    END IF;
  ELSIF state='ready' THEN
    IF exchange_json IS NULL OR length(exchange_json) NOT BETWEEN 2 AND 65536 THEN
      RAISE EXCEPTION 'an http delivery cites the exchange that happened' USING ERRCODE='22023';
    END IF;
  END IF;
  IF exchange_json IS NOT NULL AND length(exchange_json) NOT BETWEEN 2 AND 65536 THEN
    RAISE EXCEPTION 'invalid delivery exchange input' USING ERRCODE='22023';
  END IF;
  INSERT INTO vnext.report_delivery(tenant_id,project_id,task_id,delivery_id,report_id,
    report_digest,epoch_id,profile_id,profile_digest,profile_json,state,mode,missing_json,
    manifest_json,manifest_digest,exchange_json,error_code,access_level)
  VALUES(t,p,k,delivery_key,report_key,report_digest,commit_row.epoch_id,profile_key,
    encode(sha256(profile_json::bytea),'hex'),profile_json,state,mode,missing_json,
    manifest_value,
    CASE WHEN manifest_value IS NULL THEN NULL
         ELSE encode(sha256(manifest_value::bytea),'hex') END,
    exchange_json,error_code,COALESCE(level,0));
  RETURN delivery_key;
END $$"""

_SIGNATURE = ",".join(["text"] * 14 + ["integer"])


def statements():
    return _TABLES + _POLICIES + (_RECORD,)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0025_p15_view_stream":
        raise ValueError("P16 delivery migration parent changed")
    for statement in statements():
        connection.execute(statement)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL("GRANT SELECT ON vnext.report_delivery TO {}").format(app)
    )
    connection.execute(
        sql.SQL("REVOKE EXECUTE ON FUNCTION vnext.record_report_delivery(" + _SIGNATURE + ") FROM PUBLIC")
    )
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.record_report_delivery(" + _SIGNATURE + ") TO {}").format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
