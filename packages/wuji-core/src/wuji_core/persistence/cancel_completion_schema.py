"""New cancellations only: trusted source, fair launch-worker claim and P12 epoch."""

from psycopg import sql

from wuji_core.persistence.project_access_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0041_cancel_completion"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0040_project_access":
        raise ValueError("cancel completion migration parent changed")
    connection.execute("""ALTER TABLE vnext.task
        ADD COLUMN cancel_settlement_source text
          CHECK(cancel_settlement_source IN ('user_cancel','system_failure')),
        ADD COLUMN cancel_settlement_polled_at timestamptz""")
    connection.execute(sql.SQL(
        "GRANT UPDATE(cancel_settlement_source) ON vnext.task TO {}"
    ).format(sql.Identifier(application_role)))
    connection.execute("""CREATE FUNCTION vnext.claim_cancel_settlement(subject_key text)
    RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
    DECLARE selected vnext.task; clearance_value integer; result jsonb;
    BEGIN
      IF subject_key IS NULL OR subject_key IS DISTINCT FROM current_setting('wuji.subject',true) THEN
        RAISE EXCEPTION 'authenticated launch worker required' USING ERRCODE='42501';
      END IF;
      SELECT t.* INTO selected FROM vnext.task t
      JOIN vnext.task_launch_worker w ON (w.tenant_id,w.project_id)=(t.tenant_id,t.project_id)
      WHERE t.tenant_id=current_setting('wuji.tenant',true)
        AND w.subject=subject_key AND w.enabled
        AND t.desired_state='cancel' AND t.cancel_settlement_source IS NOT NULL
        AND (t.observed_state<>'closed' OR NOT EXISTS (
          SELECT 1 FROM vnext.report_commit r WHERE
          (r.tenant_id,r.project_id,r.task_id,r.epoch_id)=
          (t.tenant_id,t.project_id,t.task_id,t.completion_epoch_id)))
        AND NOT EXISTS (SELECT 1 FROM vnext.task_access a WHERE
          (a.tenant_id,a.project_id,a.task_id,a.subject)=
          (t.tenant_id,t.project_id,t.task_id,subject_key)
          AND (NOT a.can_read OR NOT a.can_control))
      ORDER BY t.cancel_settlement_polled_at NULLS FIRST,t.task_id
      LIMIT 1 FOR UPDATE OF t SKIP LOCKED;
      IF NOT FOUND THEN RETURN NULL; END IF;
      SELECT w.clearance INTO clearance_value FROM vnext.task_launch_worker w WHERE
        (w.tenant_id,w.project_id,w.subject)=
        (selected.tenant_id,selected.project_id,subject_key) AND w.enabled;
      INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_control,clearance)
        VALUES(selected.tenant_id,selected.project_id,selected.task_id,subject_key,true,true,clearance_value)
        ON CONFLICT DO NOTHING;
      UPDATE vnext.task SET cancel_settlement_polled_at=clock_timestamp() WHERE
        (tenant_id,project_id,task_id)=
        (selected.tenant_id,selected.project_id,selected.task_id);
      result:=jsonb_build_object('task_id',selected.task_id,'source',selected.cancel_settlement_source);
      RETURN result::text;
    END $$""")
    connection.execute("""CREATE FUNCTION vnext.prepare_cancel_completion_quiesce(
      t text,p text,k text,receipt_key text,epoch_key text,
      expected_control_version numeric,expected_board_revision numeric,
      deadline timestamptz,close_trigger text,source_receipt text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
    DECLARE taskrow vnext.task; saved vnext.completion_decision;
    BEGIN
      IF current_setting('wuji.control',true) IS DISTINCT FROM 'true'
        OR NOT COALESCE(vnext.in_scope(t,p,k),false)
        OR current_setting('wuji.subject',true) IS NULL THEN
        RAISE EXCEPTION 'completion decision requires control authority' USING ERRCODE='42501';
      END IF;
      IF receipt_key IS NULL OR length(receipt_key) NOT BETWEEN 1 AND 256
        OR epoch_key IS NULL OR length(epoch_key) NOT BETWEEN 1 AND 256
        OR close_trigger NOT IN ('user_cancel','system_failure')
        OR deadline IS NULL OR source_receipt IS NULL
        OR length(source_receipt) NOT BETWEEN 1 AND 65536 THEN
        RAISE EXCEPTION 'invalid cancel completion decision' USING ERRCODE='22023';
      END IF;
      SELECT * INTO saved FROM vnext.completion_decision d WHERE
        (d.tenant_id,d.project_id,d.task_id,d.receipt_id)=(t,p,k,receipt_key);
      IF FOUND THEN
        IF saved.source_receipt_json IS DISTINCT FROM source_receipt OR saved.action<>'quiesce'
          OR saved.close_trigger IS DISTINCT FROM close_trigger THEN
          RAISE EXCEPTION 'completion receipt reused with different input' USING ERRCODE='23505';
        END IF;
        RETURN saved.receipt_id;
      END IF;
      SELECT * INTO taskrow FROM vnext.task x WHERE
        (x.tenant_id,x.project_id,x.task_id)=(t,p,k) FOR UPDATE;
      IF NOT FOUND OR taskrow.desired_state<>'cancel'
        OR taskrow.observed_state='closed' OR taskrow.completion_epoch_id IS NOT NULL
        OR taskrow.cancel_settlement_source IS DISTINCT FROM close_trigger
        OR taskrow.close_trigger IS DISTINCT FROM close_trigger THEN
        RAISE EXCEPTION 'task cannot start a cancel completion epoch' USING ERRCODE='55000';
      END IF;
      IF taskrow.control_version<>expected_control_version
        OR taskrow.board_revision<>expected_board_revision THEN
        RAISE EXCEPTION 'completion decision is stale' USING ERRCODE='40001';
      END IF;
      INSERT INTO vnext.completion_decision(tenant_id,project_id,task_id,receipt_id,epoch_id,action,
        expected_control_version,board_revision,deadline,close_trigger,result_outcome,source_receipt_json)
      VALUES(t,p,k,receipt_key,epoch_key,'quiesce',expected_control_version,
        expected_board_revision,deadline,close_trigger,NULL,source_receipt);
      RETURN receipt_key;
    END $$""")
    connection.execute("""CREATE FUNCTION vnext.is_current_task_pod_controller(
      t text,p text,k text) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
    BEGIN
      IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN RETURN false; END IF;
      RETURN EXISTS(SELECT 1 FROM vnext.task_pod_controller c WHERE
        (c.tenant_id,c.project_id,c.task_id,c.controller_subject,c.login_role,c.enabled)=
        (t,p,k,current_setting('wuji.subject',true),session_user::name,true));
    END $$""")
    connection.execute("""CREATE FUNCTION vnext.prelaunch_no_start(
      t text,p text,k text) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
    BEGIN
      IF current_setting('wuji.control',true) IS DISTINCT FROM 'true'
        OR NOT COALESCE(vnext.in_scope(t,p,k),false) THEN
        RAISE EXCEPTION 'Task control authority required' USING ERRCODE='42501';
      END IF;
      RETURN NOT EXISTS(SELECT 1 FROM vnext.task_launch l WHERE
        (l.tenant_id,l.project_id,l.task_id)=(t,p,k)
        AND NOT (l.phase='prepare' AND l.phase_status='failed'
          AND l.reason_code='receiver_bearer_expires_before_attempt_window'
          AND l.steps_json::jsonb ? 'prepare'
          AND l.steps_json::jsonb - 'prepare' = '{}'::jsonb))
        AND NOT EXISTS(SELECT 1 FROM vnext.task_pod_controller c WHERE
          (c.tenant_id,c.project_id,c.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.scheduler_receiver r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.agent_run r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.runtime_terminal_observation r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.capture_session r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.tool_attempt r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k))
        AND NOT EXISTS(SELECT 1 FROM vnext.process_execution r WHERE
          (r.tenant_id,r.project_id,r.task_id)=(t,p,k));
    END $$""")
    for signature in (
        "claim_cancel_settlement(text)",
        "prepare_cancel_completion_quiesce(text,text,text,text,text,numeric,numeric,timestamptz,text,text)",
        "is_current_task_pod_controller(text,text,text)",
        "prelaunch_no_start(text,text,text)",
    ):
        connection.execute("REVOKE ALL ON FUNCTION vnext." + signature + " FROM PUBLIC")
        connection.execute(sql.SQL("GRANT EXECUTE ON FUNCTION vnext." + signature + " TO {}")
            .format(sql.Identifier(application_role)))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
