"""Purpose-isolated upgrade for databases already at the P06 admission head."""

from psycopg import sql


HEAD = "vnext_0008_p06_admission_hardening"
SCOPE = "vnext.in_scope(tenant_id,project_id,task_id)"
MODEL_REQUEST = "current_setting('wuji.request_purpose',true)='model_request'"
MODEL_SETTLE = "current_setting('wuji.request_purpose',true)='model_settle'"
MODEL = (
    "current_setting('wuji.request_purpose',true) "
    "IN ('model_request','model_settle')"
)
TOOL_REQUEST = "current_setting('wuji.request_purpose',true)='tool_request'"
TOOL_SETTLE = "current_setting('wuji.request_purpose',true)='tool_settle'"
TOOL = (
    "current_setting('wuji.request_purpose',true) "
    "IN ('tool_request','tool_settle')"
)
POWER = (
    "current_setting('wuji.request_purpose',true) "
    "IN ('model_request','tool_request','model_settle','tool_settle')"
)


def _replace_insert(connection, table, predicate):
    connection.execute(f"DROP POLICY IF EXISTS request_insert ON vnext.{table}")
    connection.execute(
        f"CREATE POLICY request_insert ON vnext.{table} FOR INSERT "
        f"WITH CHECK({SCOPE} AND {predicate})"
    )


def _replace_update(connection, table, predicate):
    connection.execute(f"DROP POLICY IF EXISTS request_update ON vnext.{table}")
    connection.execute(
        f"CREATE POLICY request_update ON vnext.{table} FOR UPDATE "
        f"USING({SCOPE} AND {predicate}) WITH CHECK({SCOPE} AND {predicate})"
    )


def upgrade(connection, application_role):
    app = sql.Identifier(application_role)

    connection.execute(
        "ALTER TABLE vnext.tool_attempt ADD received_digest text,"
        "ADD limit_reason text CHECK(limit_reason IS NULL OR "
        "limit_reason='LIMIT_BLOCKED'),"
        "ADD CHECK(received_digest IS NULL OR "
        "received_digest ~ '^[a-f0-9]{64}$')"
    )
    connection.execute(
        sql.SQL(
            "GRANT UPDATE(received_digest,limit_reason) ON "
            "vnext.tool_attempt TO {}"
        ).format(app)
    )

    _replace_insert(connection, "admission_counter", POWER)
    _replace_update(connection, "admission_counter", POWER)
    _replace_insert(connection, "admission_audit", POWER)

    _replace_insert(connection, "model_call", MODEL_REQUEST)
    _replace_update(connection, "model_call", MODEL)
    _replace_insert(connection, "model_response_chunk", MODEL_SETTLE)

    _replace_insert(connection, "tool_resource_claim", TOOL_REQUEST)
    _replace_update(connection, "tool_resource_claim", TOOL_SETTLE)
    _replace_insert(connection, "tool_cancel_receipt", TOOL_REQUEST)

    for table in (
        "tool_call",
        "tool_attempt",
        "resource_reservation",
    ):
        _replace_insert(connection, table, TOOL_REQUEST)
        _replace_update(connection, table, TOOL)
    _replace_insert(connection, "run_operation_settlement", TOOL)
    _replace_update(connection, "run_operation_settlement", TOOL)
    _replace_insert(connection, "collector_binding", TOOL_REQUEST)

    connection.execute(
        """CREATE FUNCTION vnext.guard_admission_counter_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF NEW.model_attempts < OLD.model_attempts
             OR NEW.tool_attempts < OLD.tool_attempts
             OR NEW.output_bytes < OLD.output_bytes
             OR NEW.received_bytes < OLD.received_bytes
             OR NEW.retained_bytes < OLD.retained_bytes
             OR NEW.forwarded_bytes < OLD.forwarded_bytes THEN
            RAISE EXCEPTION 'admission counters cannot decrease' USING ERRCODE='42501';
          END IF;
          IF purpose='model_request' THEN
            IF ROW(NEW.tool_attempts,NEW.output_bytes,NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes)
               IS DISTINCT FROM
               ROW(OLD.tool_attempts,OLD.output_bytes,OLD.received_bytes,OLD.retained_bytes,OLD.forwarded_bytes) THEN
              RAISE EXCEPTION 'model request cannot mutate tool or output counters' USING ERRCODE='42501';
            END IF;
          ELSIF purpose='tool_request' THEN
            IF ROW(NEW.model_attempts,NEW.output_bytes,NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes)
               IS DISTINCT FROM
               ROW(OLD.model_attempts,OLD.output_bytes,OLD.received_bytes,OLD.retained_bytes,OLD.forwarded_bytes) THEN
              RAISE EXCEPTION 'tool request cannot mutate model or output counters' USING ERRCODE='42501';
            END IF;
          ELSIF purpose IN ('model_settle','tool_settle') THEN
            IF ROW(NEW.model_attempts,NEW.tool_attempts)
               IS DISTINCT FROM ROW(OLD.model_attempts,OLD.tool_attempts) THEN
              RAISE EXCEPTION 'settlement cannot mutate attempt counters' USING ERRCODE='42501';
            END IF;
          ELSE
            RAISE EXCEPTION 'request purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER admission_counter_purpose BEFORE UPDATE ON "
        "vnext.admission_counter FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_admission_counter_purpose()"
    )
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.guard_admission_counter_purpose() "
        "FROM PUBLIC"
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION "
            "vnext.guard_admission_counter_purpose() TO {}"
        ).format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
