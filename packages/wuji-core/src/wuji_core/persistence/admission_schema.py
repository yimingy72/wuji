"""P06 request-purpose ledger, extending the canonical P03/P05 parents."""

from psycopg import sql

HEAD = "vnext_0007_p06_admission"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
FK = f"FOREIGN KEY({O}) REFERENCES vnext.task({O})"
SCOPE = "vnext.in_scope(tenant_id,project_id,task_id)"
POWER = "current_setting('wuji.request_purpose',true) IN ('model_request','tool_request','model_settle','tool_settle')"
TOOL = "current_setting('wuji.request_purpose',true) IN ('tool_request','tool_settle')"


def upgrade(connection, application_role):
    app = sql.Identifier(application_role)
    statements = [
        f"CREATE TABLE vnext.admission_config({S},document_json text NOT NULL,PRIMARY KEY({O}),{FK})",
        "CREATE TABLE vnext.tool_definition(tenant_id text NOT NULL REFERENCES vnext.tenant,ref text NOT NULL,document_json text NOT NULL,revoked boolean NOT NULL DEFAULT false,PRIMARY KEY(tenant_id,ref))",
        f"CREATE TABLE vnext.executor_registration({S},ref text NOT NULL,document_json text NOT NULL,PRIMARY KEY({O},ref),{FK})",
        f"CREATE TABLE vnext.run_credential({S},subject text NOT NULL,token_id text NOT NULL,agent_run_id text NOT NULL,document_json text NOT NULL,revoked boolean NOT NULL DEFAULT false,PRIMARY KEY(tenant_id,subject,token_id),FOREIGN KEY({O},subject) REFERENCES vnext.task_access({O},subject),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id))",
        f"CREATE TABLE vnext.admission_counter({S},model_attempts bigint NOT NULL DEFAULT 0,tool_attempts bigint NOT NULL DEFAULT 0,output_bytes bigint NOT NULL DEFAULT 0,received_bytes bigint NOT NULL DEFAULT 0,retained_bytes bigint NOT NULL DEFAULT 0,forwarded_bytes bigint NOT NULL DEFAULT 0,PRIMARY KEY({O}),{FK},CHECK(model_attempts>=0 AND tool_attempts>=0 AND output_bytes>=0 AND received_bytes>=0 AND retained_bytes>=0 AND forwarded_bytes>=0))",
        f"""CREATE TABLE vnext.model_call({S},model_attempt_id text NOT NULL,agent_run_id text NOT NULL,
        subject text NOT NULL,token_id text NOT NULL,logical_request_id text NOT NULL,input_digest text NOT NULL,
        request_json text NOT NULL,profile_json text NOT NULL,settlement_token text NOT NULL,
        send_state text NOT NULL DEFAULT 'not_sent' CHECK(send_state IN ('not_sent','sending','sent','unknown')),
        response_state text NOT NULL DEFAULT 'pending' CHECK(response_state IN ('pending','complete','partial','unknown')),
        billing_state text NOT NULL DEFAULT 'pending' CHECK(billing_state IN ('pending','reported','unknown')),
        local_state text NOT NULL DEFAULT 'inflight' CHECK(local_state IN ('inflight','ended','unknown')),
        inflight boolean NOT NULL DEFAULT true,upstream_status integer,content_type text,
        gateway_usage_ref text,gateway_spend_ref text,response_available boolean NOT NULL DEFAULT false,
        received_bytes bigint NOT NULL DEFAULT 0,retained_bytes bigint NOT NULL DEFAULT 0,
        forwarded_bytes bigint NOT NULL DEFAULT 0,output_bytes bigint NOT NULL DEFAULT 0,
        settlement_json text,access_level integer NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({O},model_attempt_id),UNIQUE({O},agent_run_id,logical_request_id),
        FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),
        CHECK(inflight=(local_state<>'ended')),
        CHECK(received_bytes>=0 AND retained_bytes>=0 AND forwarded_bytes>=0 AND output_bytes>=0))""",
        f"CREATE UNIQUE INDEX one_model_inflight_per_run ON vnext.model_call({O},agent_run_id) WHERE inflight",
        f"CREATE TABLE vnext.model_response_chunk({S},model_attempt_id text NOT NULL,ordinal bigint NOT NULL,data bytea NOT NULL,access_level integer NOT NULL,PRIMARY KEY({O},model_attempt_id,ordinal),FOREIGN KEY({O},model_attempt_id) REFERENCES vnext.model_call({O},model_attempt_id))",
        f"CREATE TABLE vnext.admission_audit({S},audit_id text NOT NULL,kind text NOT NULL,subject text NOT NULL,request_id text NOT NULL,details_json text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY({O},audit_id),{FK})",
        "ALTER TABLE vnext.tool_call ADD work_item_id text,ADD input_digest text,ADD request_json text,ADD status text,ADD latest_attempt_id text,ADD access_level integer NOT NULL DEFAULT 0",
        f"ALTER TABLE vnext.tool_call ADD FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id)",
        """ALTER TABLE vnext.tool_attempt ADD status text,ADD permit_json text,ADD output bytea,ADD output_media_type text,
        ADD output_completeness text,ADD capture_json text,ADD result_receipt_json text,ADD retry_request_id text,
        ADD received_bytes bigint NOT NULL DEFAULT 0,ADD retained_bytes bigint NOT NULL DEFAULT 0,
        ADD forwarded_bytes bigint NOT NULL DEFAULT 0,ADD output_bytes bigint NOT NULL DEFAULT 0""",
        f"CREATE UNIQUE INDEX tool_retry_request ON vnext.tool_attempt({O},tool_call_id,retry_request_id) WHERE retry_request_id IS NOT NULL",
        f"ALTER TABLE vnext.tool_call ADD FOREIGN KEY({O},latest_attempt_id) REFERENCES vnext.tool_attempt({O},tool_attempt_id)",
        f"CREATE TABLE vnext.tool_resource_claim({S},resource_key text NOT NULL,tool_attempt_id text NOT NULL,active boolean NOT NULL DEFAULT true,PRIMARY KEY({O},resource_key,tool_attempt_id),FOREIGN KEY({O},tool_attempt_id) REFERENCES vnext.tool_attempt({O},tool_attempt_id))",
        f"CREATE UNIQUE INDEX one_active_tool_resource ON vnext.tool_resource_claim({O},resource_key) WHERE active",
        f"CREATE TABLE vnext.tool_cancel_receipt({S},tool_call_id text NOT NULL,operation_id text NOT NULL,input_digest text NOT NULL,receipt_json text NOT NULL,PRIMARY KEY({O},tool_call_id,operation_id),FOREIGN KEY({O},tool_call_id) REFERENCES vnext.tool_call({O},tool_call_id))",
    ]
    for statement in statements:
        connection.execute(statement)
    tables = ["admission_config", "executor_registration", "run_credential", "admission_counter", "model_call", "model_response_chunk", "admission_audit", "tool_resource_claim", "tool_cancel_receipt"]
    writable = set(tables) - {"admission_config", "executor_registration", "run_credential"}
    for table in tables:
        scope = SCOPE
        if table in {"model_call", "model_response_chunk"}:
            scope = "vnext.in_scope(tenant_id,project_id,task_id,access_level)"
        locator = f"tenant_id=current_setting('wuji.tenant',true) AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE (a.tenant_id,a.project_id,a.task_id)=({table}.tenant_id,{table}.project_id,{table}.task_id) AND a.subject=current_setting('wuji.subject',true) AND a.can_read" + (f" AND a.clearance>={table}.access_level" if table == "model_call" else "") + ")"
        if table == "run_credential":
            scope = "tenant_id=current_setting('wuji.tenant',true) AND subject=current_setting('wuji.subject',true) AND token_id=current_setting('wuji.token_id',true)"
        elif table == "model_call":
            scope = f"({scope}) OR (current_setting('wuji.task',true)='' AND {locator})"
        connection.execute(f"ALTER TABLE vnext.{table} ENABLE ROW LEVEL SECURITY")
        connection.execute(f"CREATE POLICY scoped_read ON vnext.{table} FOR SELECT USING({scope})")
        connection.execute(sql.SQL(f"GRANT SELECT ON vnext.{table} TO {{}}").format(app))
        if table in writable:
            connection.execute(f"CREATE POLICY request_insert ON vnext.{table} FOR INSERT WITH CHECK({SCOPE} AND {POWER})")
            connection.execute(sql.SQL(f"GRANT INSERT ON vnext.{table} TO {{}}").format(app))
        if table in writable - {"admission_audit", "model_response_chunk", "tool_cancel_receipt"}:
            connection.execute(f"CREATE POLICY request_update ON vnext.{table} FOR UPDATE USING({SCOPE} AND {POWER}) WITH CHECK({SCOPE} AND {POWER})")
            columns = {
                "admission_counter": "model_attempts,tool_attempts,output_bytes,received_bytes,retained_bytes,forwarded_bytes",
                "model_call": "send_state,response_state,billing_state,local_state,inflight,upstream_status,content_type,gateway_usage_ref,gateway_spend_ref,response_available,received_bytes,retained_bytes,forwarded_bytes,output_bytes,settlement_json",
                "tool_resource_claim": "active",
            }[table]
            connection.execute(sql.SQL(f"GRANT UPDATE({columns}) ON vnext.{table} TO {{}}").format(app))
    connection.execute("ALTER TABLE vnext.tool_definition ENABLE ROW LEVEL SECURITY")
    connection.execute("CREATE POLICY tenant_read ON vnext.tool_definition FOR SELECT USING(tenant_id=current_setting('wuji.tenant',true))")
    connection.execute(sql.SQL("GRANT SELECT ON vnext.tool_definition TO {}").format(app))
    for table in ["tool_call", "tool_attempt", "collector_binding", "run_operation_settlement", "resource_reservation"]:
        connection.execute(f"CREATE POLICY request_insert ON vnext.{table} FOR INSERT WITH CHECK({SCOPE} AND {TOOL})")
        connection.execute(sql.SQL(f"GRANT INSERT ON vnext.{table} TO {{}}").format(app))
        if table != "collector_binding":
            connection.execute(f"CREATE POLICY request_update ON vnext.{table} FOR UPDATE USING({SCOPE} AND {TOOL}) WITH CHECK({SCOPE} AND {TOOL})")
            columns = {
                "tool_call": "status,latest_attempt_id",
                "tool_attempt": "status,started_at,receipt_json,output,output_media_type,output_completeness,capture_json,result_receipt_json,received_bytes,retained_bytes,forwarded_bytes,output_bytes",
                "run_operation_settlement": "status,source_receipt_json",
                "resource_reservation": "state,source_receipt_json",
            }[table]
            connection.execute(sql.SQL(f"GRANT UPDATE({columns}) ON vnext.{table} TO {{}}").format(app))
    # FOR UPDATE prelocks need UPDATE row visibility but must never grant a Run
    # the right to change capacity or Work state. Actual mutation is guarded.
    connection.execute(f"CREATE POLICY request_lock ON vnext.work_item FOR UPDATE USING({SCOPE} AND {POWER}) WITH CHECK({SCOPE} AND {POWER})")
    connection.execute(f"CREATE POLICY request_lock ON vnext.capacity_pool FOR UPDATE USING({POWER} AND EXISTS(SELECT 1 FROM vnext.task_capacity_pool p WHERE p.pool_key=capacity_pool.pool_key AND p.tenant_id=current_setting('wuji.tenant',true) AND p.task_id=current_setting('wuji.task',true)))")
    connection.execute("""CREATE FUNCTION vnext.guard_request_lock_only() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF current_setting('wuji.request_purpose',true) IN ('model_request','tool_request','model_settle','tool_settle') AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'request purpose cannot mutate control or capacity' USING ERRCODE='42501'; END IF; RETURN NEW; END $$""")
    for table in ["work_item", "capacity_pool"]:
        connection.execute(f"CREATE TRIGGER request_lock_only BEFORE UPDATE ON vnext.{table} FOR EACH ROW EXECUTE FUNCTION vnext.guard_request_lock_only()")
    connection.execute("REVOKE EXECUTE ON FUNCTION vnext.guard_request_lock_only() FROM PUBLIC")
    connection.execute(sql.SQL("GRANT EXECUTE ON FUNCTION vnext.guard_request_lock_only() TO {}").format(app))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
