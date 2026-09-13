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
        """CREATE FUNCTION vnext.guard_model_call_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF purpose='model_request' THEN
            IF OLD.send_state<>'not_sent' OR NEW.send_state<>'sending'
               OR ROW(NEW.response_state,NEW.billing_state,NEW.local_state,NEW.inflight,
                      NEW.upstream_status,NEW.content_type,NEW.gateway_usage_ref,
                      NEW.gateway_spend_ref,NEW.response_available,NEW.received_bytes,
                      NEW.retained_bytes,NEW.forwarded_bytes,NEW.output_bytes,
                      NEW.settlement_json)
                  IS DISTINCT FROM
                  ROW(OLD.response_state,OLD.billing_state,OLD.local_state,OLD.inflight,
                      OLD.upstream_status,OLD.content_type,OLD.gateway_usage_ref,
                      OLD.gateway_spend_ref,OLD.response_available,OLD.received_bytes,
                      OLD.retained_bytes,OLD.forwarded_bytes,OLD.output_bytes,
                      OLD.settlement_json) THEN
              RAISE EXCEPTION 'model request cannot mutate settlement fields' USING ERRCODE='42501';
            END IF;
          ELSIF purpose='model_settle' THEN
            IF OLD.send_state='not_sent' AND NEW.send_state IS DISTINCT FROM OLD.send_state THEN
              RAISE EXCEPTION 'model settlement cannot cross the send fence' USING ERRCODE='42501';
            END IF;
          ELSE
            RAISE EXCEPTION 'model write purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER model_call_purpose BEFORE UPDATE ON vnext.model_call "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_model_call_purpose()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_tool_attempt_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF purpose='tool_request' THEN
            IF OLD.status<>'admitted' OR NEW.status<>'dispatched'
               OR ROW(NEW.started_at,NEW.receipt_json,NEW.output,NEW.output_media_type,
                      NEW.output_completeness,NEW.capture_json,NEW.result_receipt_json,
                      NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes,
                      NEW.output_bytes,NEW.received_digest,NEW.limit_reason)
                  IS DISTINCT FROM
                  ROW(OLD.started_at,OLD.receipt_json,OLD.output,OLD.output_media_type,
                      OLD.output_completeness,OLD.capture_json,OLD.result_receipt_json,
                      OLD.received_bytes,OLD.retained_bytes,OLD.forwarded_bytes,
                      OLD.output_bytes,OLD.received_digest,OLD.limit_reason) THEN
              RAISE EXCEPTION 'tool request cannot mutate settlement fields' USING ERRCODE='42501';
            END IF;
          ELSIF purpose<>'tool_settle' THEN
            RAISE EXCEPTION 'tool write purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER tool_attempt_purpose BEFORE UPDATE ON vnext.tool_attempt "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_tool_attempt_purpose()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_tool_call_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF purpose='tool_request' THEN
            IF NEW.status NOT IN ('pending_approval','admitted','dispatched','cancel_requested','cancelled')
               OR (OLD.status IN ('complete','failed','cancelled') AND NEW IS DISTINCT FROM OLD) THEN
              RAISE EXCEPTION 'tool request cannot forge settlement status' USING ERRCODE='42501';
            END IF;
          ELSIF purpose<>'tool_settle' THEN
            RAISE EXCEPTION 'tool write purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER tool_call_purpose BEFORE UPDATE ON vnext.tool_call "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_tool_call_purpose()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_resource_reservation_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF purpose='tool_request' THEN
            IF OLD.state<>'released' OR NEW.state<>'reserved' THEN
              RAISE EXCEPTION 'tool request cannot release or settle resources' USING ERRCODE='42501';
            END IF;
          ELSIF purpose<>'tool_settle' THEN
            RAISE EXCEPTION 'tool resource write purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER resource_reservation_purpose BEFORE UPDATE ON "
        "vnext.resource_reservation FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_resource_reservation_purpose()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_run_settlement_purpose()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        BEGIN
          IF purpose='tool_request' AND NEW.status<>'pending' THEN
            RAISE EXCEPTION 'tool request cannot forge settled operations' USING ERRCODE='42501';
          ELSIF purpose NOT IN ('tool_request','tool_settle') THEN
            RAISE EXCEPTION 'tool settlement purpose required' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER run_settlement_purpose BEFORE UPDATE ON "
        "vnext.run_operation_settlement FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_run_settlement_purpose()"
    )
    for function in (
        "guard_admission_counter_purpose",
        "guard_model_call_purpose",
        "guard_tool_attempt_purpose",
        "guard_tool_call_purpose",
        "guard_resource_reservation_purpose",
        "guard_run_settlement_purpose",
    ):
        connection.execute(
            f"REVOKE EXECUTE ON FUNCTION vnext.{function}() FROM PUBLIC"
        )
        connection.execute(
            sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{function}() TO {{}}").format(
                app
            )
        )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
