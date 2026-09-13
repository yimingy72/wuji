"""P06 request-write matrix for databases already at the 0008 head.

Matrix (I=insert, U=update):
- model_request: zero counter I/model count U; initial model_call I; send-fence U.
- model_settle: byte counter U; sent-call/chunk settlement only; no execution I.
- tool_request: zero counter I/tool count U; proposal/call/attempt/active claim/
  reserved resource/pending settlement I; attach/dispatch/cancel/safe-retry U.
- tool_settle: byte counter U and existing attempt/call/claim/resource settlement;
  no call, attempt, claim, or execution-resource I.
"""

from psycopg import sql


HEAD = "vnext_0009_p06_request_write_guards"


def _function(connection, name, body):
    connection.execute(f"CREATE OR REPLACE FUNCTION vnext.{name}() {body}")


def _trigger(connection, table, name, event, function):
    connection.execute(f"DROP TRIGGER IF EXISTS {name} ON vnext.{table}")
    connection.execute(
        f"CREATE TRIGGER {name} BEFORE {event} ON vnext.{table} "
        f"FOR EACH ROW EXECUTE FUNCTION vnext.{function}()"
    )


def upgrade(connection, application_role):
    app = sql.Identifier(application_role)
    owner = (
        "IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class "
        "WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;"
    )

    _function(
        connection,
        "guard_admission_counter_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true) NOT IN
           ('model_request','tool_request','model_settle','tool_settle')
           OR ROW(NEW.model_attempts,NEW.tool_attempts,NEW.output_bytes,
                  NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes)
              IS DISTINCT FROM ROW(0,0,0,0,0,0) THEN
          RAISE EXCEPTION 'admission counters must start at zero' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "admission_counter",
        "admission_counter_insert",
        "INSERT",
        "guard_admission_counter_insert",
    )

    _function(
        connection,
        "guard_model_call_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'model_request'
           OR NEW.send_state<>'not_sent' OR NEW.response_state<>'pending'
           OR NEW.billing_state<>'pending' OR NEW.local_state<>'inflight'
           OR NOT NEW.inflight OR NEW.upstream_status IS NOT NULL
           OR NEW.content_type IS NOT NULL OR NEW.gateway_usage_ref IS NOT NULL
           OR NEW.gateway_spend_ref IS NOT NULL OR NEW.response_available
           OR ROW(NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes,
                  NEW.output_bytes) IS DISTINCT FROM ROW(0,0,0,0)
           OR NEW.settlement_json IS NOT NULL THEN
          RAISE EXCEPTION 'model call must start before send and settlement' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection, "model_call", "model_call_insert", "INSERT", "guard_model_call_insert"
    )

    _function(
        connection,
        "guard_model_chunk_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'model_settle'
           OR NOT EXISTS(
             SELECT 1 FROM vnext.model_call c
             WHERE (c.tenant_id,c.project_id,c.task_id,c.model_attempt_id)=
                   (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.model_attempt_id)
               AND c.send_state='sent' AND c.inflight
           ) THEN
          RAISE EXCEPTION 'model response bytes require a sent inflight attempt' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "model_response_chunk",
        "model_chunk_insert",
        "INSERT",
        "guard_model_chunk_insert",
    )

    _function(
        connection,
        "guard_tool_call_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'tool_request'
           OR NEW.status NOT IN ('pending_approval','admitted')
           OR NEW.latest_attempt_id IS NOT NULL THEN
          RAISE EXCEPTION 'tool call must start as a proposal' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection, "tool_call", "tool_call_insert", "INSERT", "guard_tool_call_insert"
    )

    _function(
        connection,
        "guard_tool_attempt_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE call_status text; DECLARE prior_id text; BEGIN
        {owner}
        SELECT c.status,c.latest_attempt_id INTO call_status,prior_id
          FROM vnext.tool_call c
         WHERE (c.tenant_id,c.project_id,c.task_id,c.tool_call_id)=
               (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id);
        IF current_setting('wuji.request_purpose',true)<>'tool_request'
           OR NEW.status<>'admitted' OR NEW.started_at IS NOT NULL
           OR NEW.receipt_json<>'{{}}' OR NEW.permit_json IS NULL
           OR NEW.output IS NOT NULL OR NEW.output_media_type IS NOT NULL
           OR NEW.output_completeness IS NOT NULL OR NEW.capture_json IS NOT NULL
           OR NEW.result_receipt_json IS NOT NULL
           OR ROW(NEW.received_bytes,NEW.retained_bytes,NEW.forwarded_bytes,
                  NEW.output_bytes) IS DISTINCT FROM ROW(0,0,0,0)
           OR NEW.received_digest IS NOT NULL OR NEW.limit_reason IS NOT NULL
           OR NOT (
             (call_status='admitted' AND NEW.retry_request_id IS NULL)
             OR (call_status IN ('failed','cancelled')
                 AND NEW.retry_request_id IS NOT NULL AND prior_id IS NOT NULL
                 AND EXISTS(
                   SELECT 1 FROM vnext.tool_attempt p
                    WHERE (p.tenant_id,p.project_id,p.task_id,p.tool_attempt_id)=
                          (NEW.tenant_id,NEW.project_id,NEW.task_id,prior_id)
                      AND p.status IN ('failed','cancelled')
                      AND p.receipt_json::jsonb->>'status' IN ('not_started','exited')
                 ))
           ) THEN
          RAISE EXCEPTION 'tool attempt must start admitted from a valid call' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "tool_attempt",
        "tool_attempt_insert",
        "INSERT",
        "guard_tool_attempt_insert",
    )

    _function(
        connection,
        "guard_tool_claim_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'tool_request'
           OR NOT NEW.active OR NOT EXISTS(
             SELECT 1 FROM vnext.tool_attempt a
              WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_attempt_id)
                AND a.status='admitted'
           ) THEN
          RAISE EXCEPTION 'tool resource claim must start active' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "tool_resource_claim",
        "tool_claim_insert",
        "INSERT",
        "guard_tool_claim_insert",
    )

    _function(
        connection,
        "guard_collector_binding_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'tool_request'
           OR NEW.revoked OR NOT NEW.can_settle OR NOT EXISTS(
             SELECT 1 FROM vnext.tool_attempt a
              JOIN vnext.executor_registration e
                ON (e.tenant_id,e.project_id,e.task_id)=
                   (a.tenant_id,a.project_id,a.task_id)
               AND e.ref=a.permit_json::jsonb->>'executor_ref'
             WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)=
                   (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_attempt_id)
               AND a.status='admitted'
               AND e.document_json::jsonb->>'collector_subject'=NEW.subject
           ) THEN
          RAISE EXCEPTION 'collector binding requires its registered admitted attempt' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "collector_binding",
        "collector_binding_insert",
        "INSERT",
        "guard_collector_binding_insert",
    )

    _function(
        connection,
        "guard_resource_reservation_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'tool_request'
           OR NEW.state<>'reserved' OR NOT EXISTS(
             SELECT 1 FROM vnext.tool_attempt a
              WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id,a.agent_run_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,
                     NEW.source_receipt_json::jsonb->>'tool_attempt_id',NEW.agent_run_id)
                AND a.status='admitted'
           ) THEN
          RAISE EXCEPTION 'tool resource must start reserved for an admitted attempt' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "resource_reservation",
        "resource_reservation_insert",
        "INSERT",
        "guard_resource_reservation_insert",
    )

    _function(
        connection,
        "guard_run_settlement_insert",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
        IF purpose NOT IN ('tool_request','tool_settle')
           OR (purpose='tool_request' AND NEW.status<>'pending')
           OR (purpose='tool_settle' AND NEW.status NOT IN ('pending','settled'))
           OR NOT EXISTS(
             SELECT 1 FROM vnext.tool_attempt a
              WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
                AND a.status IS NOT NULL
           ) THEN
          RAISE EXCEPTION 'run settlement requires an existing tool attempt' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "run_operation_settlement",
        "run_settlement_insert",
        "INSERT",
        "guard_run_settlement_insert",
    )

    _function(
        connection,
        "guard_admission_counter_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
        IF NEW.model_attempts < OLD.model_attempts
           OR NEW.tool_attempts < OLD.tool_attempts
           OR NEW.output_bytes < OLD.output_bytes
           OR NEW.received_bytes < OLD.received_bytes
           OR NEW.retained_bytes < OLD.retained_bytes
           OR NEW.forwarded_bytes < OLD.forwarded_bytes THEN
          RAISE EXCEPTION 'admission counters cannot decrease' USING ERRCODE='42501';
        ELSIF purpose='model_request' AND
          ROW(NEW.tool_attempts,NEW.output_bytes,NEW.received_bytes,
              NEW.retained_bytes,NEW.forwarded_bytes) IS DISTINCT FROM
          ROW(OLD.tool_attempts,OLD.output_bytes,OLD.received_bytes,
              OLD.retained_bytes,OLD.forwarded_bytes) THEN
          RAISE EXCEPTION 'model request cannot mutate tool or output counters' USING ERRCODE='42501';
        ELSIF purpose='tool_request' AND
          ROW(NEW.model_attempts,NEW.output_bytes,NEW.received_bytes,
              NEW.retained_bytes,NEW.forwarded_bytes) IS DISTINCT FROM
          ROW(OLD.model_attempts,OLD.output_bytes,OLD.received_bytes,
              OLD.retained_bytes,OLD.forwarded_bytes) THEN
          RAISE EXCEPTION 'tool request cannot mutate model or output counters' USING ERRCODE='42501';
        ELSIF purpose IN ('model_settle','tool_settle') AND
          ROW(NEW.model_attempts,NEW.tool_attempts) IS DISTINCT FROM
          ROW(OLD.model_attempts,OLD.tool_attempts) THEN
          RAISE EXCEPTION 'settlement cannot mutate attempt counters' USING ERRCODE='42501';
        ELSIF purpose NOT IN ('model_request','tool_request','model_settle','tool_settle') THEN
          RAISE EXCEPTION 'request purpose required' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "admission_counter",
        "admission_counter_purpose",
        "UPDATE",
        "guard_admission_counter_purpose",
    )

    _function(
        connection,
        "guard_model_call_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
        IF purpose='model_request' THEN
          IF OLD.send_state<>'not_sent' OR NEW.send_state<>'sending'
             OR ROW(NEW.response_state,NEW.billing_state,NEW.local_state,NEW.inflight,
                    NEW.upstream_status,NEW.content_type,NEW.gateway_usage_ref,
                    NEW.gateway_spend_ref,NEW.response_available,NEW.received_bytes,
                    NEW.retained_bytes,NEW.forwarded_bytes,NEW.output_bytes,
                    NEW.settlement_json) IS DISTINCT FROM
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
        ELSE RAISE EXCEPTION 'model write purpose required' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "model_call",
        "model_call_purpose",
        "UPDATE",
        "guard_model_call_purpose",
    )

    _function(
        connection,
        "guard_tool_attempt_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
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
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "tool_attempt",
        "tool_attempt_purpose",
        "UPDATE",
        "guard_tool_attempt_purpose",
    )

    _function(
        connection,
        "guard_tool_call_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true);
        DECLARE attach boolean := false; DECLARE dispatched boolean := false;
        DECLARE cancel_intent boolean := false; DECLARE safe_retry boolean := false;
        BEGIN {owner}
        IF purpose='tool_request' THEN
          attach := OLD.status='admitted' AND OLD.latest_attempt_id IS NULL
            AND NEW.status='admitted' AND NEW.latest_attempt_id IS NOT NULL
            AND EXISTS(SELECT 1 FROM vnext.tool_attempt a
              WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_call_id,a.tool_attempt_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id,NEW.latest_attempt_id)
                AND a.status='admitted' AND a.retry_request_id IS NULL);
          dispatched := OLD.status='admitted' AND NEW.status='dispatched'
            AND NEW.latest_attempt_id=OLD.latest_attempt_id
            AND EXISTS(SELECT 1 FROM vnext.tool_attempt a
              WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.latest_attempt_id)
                AND a.status='dispatched');
          cancel_intent :=
            (OLD.status='pending_approval' AND OLD.latest_attempt_id IS NULL
             AND NEW.status='cancelled' AND NEW.latest_attempt_id IS NULL)
            OR (OLD.status IN ('admitted','dispatched','running','unknown','evidence_pending','cancel_requested')
                AND OLD.latest_attempt_id IS NOT NULL AND NEW.status='cancel_requested'
                AND NEW.latest_attempt_id=OLD.latest_attempt_id);
          safe_retry := OLD.status IN ('failed','cancelled')
            AND NEW.status='admitted' AND NEW.latest_attempt_id IS NOT NULL
            AND NEW.latest_attempt_id IS DISTINCT FROM OLD.latest_attempt_id
            AND EXISTS(SELECT 1 FROM vnext.tool_attempt n
              JOIN vnext.tool_attempt p
                ON (p.tenant_id,p.project_id,p.task_id,p.tool_attempt_id)=
                   (OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.latest_attempt_id)
              WHERE (n.tenant_id,n.project_id,n.task_id,n.tool_call_id,n.tool_attempt_id)=
                    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id,NEW.latest_attempt_id)
                AND n.status='admitted' AND n.retry_request_id IS NOT NULL
                AND p.status IN ('failed','cancelled')
                AND p.receipt_json::jsonb->>'status' IN ('not_started','exited'));
          IF NEW IS DISTINCT FROM OLD
             AND NOT (attach OR dispatched OR cancel_intent OR safe_retry) THEN
            RAISE EXCEPTION 'tool request transition is not registered' USING ERRCODE='42501';
          END IF;
        ELSIF purpose<>'tool_settle' THEN
          RAISE EXCEPTION 'tool write purpose required' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "tool_call",
        "tool_call_purpose",
        "UPDATE",
        "guard_tool_call_purpose",
    )

    _function(
        connection,
        "guard_tool_claim_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        {owner}
        IF current_setting('wuji.request_purpose',true)<>'tool_settle'
           OR NOT OLD.active OR NEW.active THEN
          RAISE EXCEPTION 'tool claim may only settle active to inactive' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "tool_resource_claim",
        "tool_claim_purpose",
        "UPDATE",
        "guard_tool_claim_purpose",
    )

    _function(
        connection,
        "guard_resource_reservation_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
        IF purpose='tool_request' THEN
          IF OLD.state<>'released' OR NEW.state<>'reserved' OR NOT EXISTS(
            SELECT 1 FROM vnext.tool_attempt a
             WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id,a.agent_run_id)=
                   (NEW.tenant_id,NEW.project_id,NEW.task_id,
                    NEW.source_receipt_json::jsonb->>'tool_attempt_id',NEW.agent_run_id)
               AND a.status='admitted'
          ) THEN RAISE EXCEPTION 'tool request cannot release or settle resources' USING ERRCODE='42501'; END IF;
        ELSIF purpose='tool_settle' THEN
          IF NOT ((OLD.state='reserved' AND NEW.state IN ('unknown','released'))
                  OR (OLD.state='unknown' AND NEW.state='released')
                  OR NEW IS NOT DISTINCT FROM OLD) THEN
            RAISE EXCEPTION 'invalid tool resource settlement transition' USING ERRCODE='42501';
          END IF;
        ELSE RAISE EXCEPTION 'tool resource write purpose required' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "resource_reservation",
        "resource_reservation_purpose",
        "UPDATE",
        "guard_resource_reservation_purpose",
    )

    _function(
        connection,
        "guard_run_settlement_purpose",
        f"""RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE purpose text := current_setting('wuji.request_purpose',true); BEGIN
        {owner}
        IF purpose='tool_request' THEN
          IF NEW.status<>'pending' OR NOT EXISTS(
            SELECT 1 FROM vnext.tool_attempt a
             WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                   (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id)
               AND a.status='admitted'
          ) THEN RAISE EXCEPTION 'tool request cannot forge settled operations' USING ERRCODE='42501'; END IF;
        ELSIF purpose='tool_settle' THEN
          IF NEW.status NOT IN ('pending','settled') THEN
            RAISE EXCEPTION 'invalid tool settlement state' USING ERRCODE='42501';
          END IF;
        ELSE RAISE EXCEPTION 'tool settlement purpose required' USING ERRCODE='42501';
        END IF; RETURN NEW; END $$""",
    )
    _trigger(
        connection,
        "run_operation_settlement",
        "run_settlement_purpose",
        "UPDATE",
        "guard_run_settlement_purpose",
    )

    functions = (
        "guard_admission_counter_insert",
        "guard_model_call_insert",
        "guard_model_chunk_insert",
        "guard_tool_call_insert",
        "guard_tool_attempt_insert",
        "guard_tool_claim_insert",
        "guard_collector_binding_insert",
        "guard_resource_reservation_insert",
        "guard_run_settlement_insert",
        "guard_admission_counter_purpose",
        "guard_model_call_purpose",
        "guard_tool_attempt_purpose",
        "guard_tool_call_purpose",
        "guard_tool_claim_purpose",
        "guard_resource_reservation_purpose",
        "guard_run_settlement_purpose",
    )
    for function in functions:
        connection.execute(f"REVOKE EXECUTE ON FUNCTION vnext.{function}() FROM PUBLIC")
        connection.execute(
            sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{function}() TO {{}}").format(app)
        )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
