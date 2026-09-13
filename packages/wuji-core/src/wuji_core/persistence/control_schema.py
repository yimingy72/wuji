"""P05 canonical control extension. Future producer headers are read-only here."""

from psycopg import sql

HEAD = "vnext_0006_p05_control"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
FK = f"FOREIGN KEY({O}) REFERENCES vnext.task({O})"
REV = "numeric NOT NULL DEFAULT 1 CHECK(revision>=1 AND revision=trunc(revision))"


def upgrade(connection, application_role):
    statements = [
        "ALTER TABLE vnext.task_access ADD can_control boolean NOT NULL DEFAULT false,ADD can_observe boolean NOT NULL DEFAULT false,ADD can_admit boolean NOT NULL DEFAULT false",
        """ALTER TABLE vnext.task ADD control_version numeric NOT NULL DEFAULT 1 CHECK(control_version>=1 AND control_version=trunc(control_version)),
        ADD desired_state text NOT NULL DEFAULT 'pause' CHECK(desired_state IN ('run','pause','cancel','finish')),
        ADD observed_state text NOT NULL DEFAULT 'ready' CHECK(observed_state IN ('ready','running','quiescing','paused','reconciling','closed')),
        ADD activated_at timestamptz,ADD close_trigger text CHECK(close_trigger IN ('goal_satisfied','user_cancel','budget_exhausted','time_limit','no_progress','system_failure','operator_finish')),
        ADD result_outcome text CHECK(result_outcome IN ('complete','partial','inconclusive','not_assessed')),
        ADD completion_epoch_id text,ADD definition_json text,ADD definition_digest text,
        ADD CHECK((definition_json IS NULL)=(definition_digest IS NULL))""",
        """ALTER TABLE vnext.work_item ADD kind text NOT NULL DEFAULT 'explore' CHECK(kind IN ('reason','explore','report')),
        ADD desired_state text NOT NULL DEFAULT 'run' CHECK(desired_state IN ('run','hold','cancel')),
        ADD run_epoch numeric NOT NULL DEFAULT 1 CHECK(run_epoch>=1 AND run_epoch=trunc(run_epoch)),
        ADD current_run_id text,ADD intent_id text,ADD intent_revision numeric,ADD blocked_reason text,ADD terminal_reason text,
        ADD input_request_id text,ADD session_id text,ADD session_revision numeric,
        ADD CHECK(state IN ('ready','leased','running','waiting_input','blocked','stopping','suspended','reconciling','done','failed','cancelled')),
        ADD CHECK(revision>=1 AND revision=trunc(revision)),ADD CHECK((intent_id IS NULL)=(intent_revision IS NULL)),ADD CHECK((session_id IS NULL)=(session_revision IS NULL))""",
        f"ALTER TABLE vnext.work_item ADD FOREIGN KEY({O},intent_id,intent_revision) REFERENCES vnext.intent_revision({O},entity_id,revision)",
        f"CREATE UNIQUE INDEX one_unsettled_explore_per_intent ON vnext.work_item({O},intent_id,intent_revision) WHERE kind='explore' AND state NOT IN ('done','failed','cancelled')",
        """ALTER TABLE vnext.agent_run ADD start_operation_id text,ADD pod_uid text,ADD process_identity_json text,
        ADD started_at timestamptz,ADD exited_at timestamptz,ADD stop_kind text CHECK(stop_kind IN ('not_started','exited','environment_stopped')),
        ADD last_observation_id text,ADD result_state text NOT NULL DEFAULT 'none' CHECK(result_state IN ('none','received','accepted','rejected','historical_only','incomplete')),
        ADD result_submission_id text,ADD output_expectation text NOT NULL DEFAULT 'unknown' CHECK(output_expectation IN ('unknown','final_output','input_boundary')),
        ADD CHECK(process_state IN ('registered','starting','running','stopping','exited','unknown'))""",
        f"ALTER TABLE vnext.agent_run ADD UNIQUE({O},work_item_id,agent_run_id),ADD FOREIGN KEY({O},result_submission_id) REFERENCES vnext.result_submission({O},submission_id)",
        f"ALTER TABLE vnext.work_item ADD FOREIGN KEY({O},work_item_id,current_run_id) REFERENCES vnext.agent_run({O},work_item_id,agent_run_id)",
        f"CREATE TABLE vnext.work_suspension({S},work_item_id text NOT NULL,cause_kind text NOT NULL CHECK(cause_kind IN ('user_hold','task_pause','completion_epoch','scope_revoked')),cause_ref text NOT NULL,PRIMARY KEY({O},work_item_id,cause_kind,cause_ref),FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id))",
        f"CREATE TABLE vnext.control_receipt({S},operation_kind text NOT NULL CHECK(operation_kind IN ('task_command','work_command','completion_command')),operation_id text NOT NULL,input_digest text NOT NULL,receipt_json text NOT NULL,PRIMARY KEY(tenant_id,task_id,operation_kind,operation_id),{FK})",
        "CREATE TABLE vnext.capacity_pool(pool_key text PRIMARY KEY,tier text NOT NULL CHECK(tier IN ('global','model','tenant')),tenant_id text REFERENCES vnext.tenant,capacity integer NOT NULL CHECK(capacity>0),used integer NOT NULL DEFAULT 0 CHECK(used>=0),published_ref text NOT NULL CHECK(length(published_ref)>0),CHECK((tier='tenant')=(tenant_id IS NOT NULL)),CHECK(used<=capacity))",
        f"CREATE TABLE vnext.task_capacity_pool({S},pool_key text NOT NULL REFERENCES vnext.capacity_pool,PRIMARY KEY({O},pool_key),{FK})",
        f"CREATE TABLE vnext.capacity_reservation({S},agent_run_id text NOT NULL,pool_key text NOT NULL,state text NOT NULL CHECK(state IN ('reserved','running_or_unknown','released')),PRIMARY KEY({O},agent_run_id,pool_key),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),FOREIGN KEY({O},pool_key) REFERENCES vnext.task_capacity_pool({O},pool_key))",
        f"CREATE TABLE vnext.execution_observation({S},receipt_id text NOT NULL,agent_run_id text NOT NULL,kind text NOT NULL CHECK(kind IN ('not_started','started','exited','environment_stopped','unknown')),source_receipt text NOT NULL,source_digest text NOT NULL,subject text NOT NULL,observed_at timestamptz NOT NULL,PRIMARY KEY({O},receipt_id),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),FOREIGN KEY({O},subject) REFERENCES vnext.task_access({O},subject))",
        f"ALTER TABLE vnext.agent_run ADD FOREIGN KEY({O},last_observation_id) REFERENCES vnext.execution_observation({O},receipt_id)",
        # These are canonical producer headers, not P05 clients' self-reported facts.
        f"CREATE TABLE vnext.run_operation_settlement({S},agent_run_id text NOT NULL,status text NOT NULL CHECK(status IN ('pending','unknown','settled')),source_receipt_json text NOT NULL CHECK(jsonb_typeof(source_receipt_json::jsonb)='object'),PRIMARY KEY({O},agent_run_id),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id))",
        f"CREATE TABLE vnext.resource_reservation({S},resource_key text NOT NULL,agent_run_id text NOT NULL,state text NOT NULL CHECK(state IN ('reserved','unknown','released')),source_receipt_json text NOT NULL,PRIMARY KEY({O},resource_key,agent_run_id),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id))",
        f"CREATE TABLE vnext.session_manifest({S},session_id text NOT NULL,revision {REV},work_item_id text NOT NULL,owner_run_id text NOT NULL,manifest_json text NOT NULL,publication_id text NOT NULL,published_at timestamptz NOT NULL,access_level integer NOT NULL DEFAULT 0,PRIMARY KEY({O},session_id,revision),FOREIGN KEY({O},work_item_id,owner_run_id) REFERENCES vnext.agent_run({O},work_item_id,agent_run_id),FOREIGN KEY({O},publication_id) REFERENCES vnext.publication({O},publication_id))",
        f"CREATE TABLE vnext.input_request({S},input_request_id text NOT NULL,work_item_id text NOT NULL,wait_ref_json text NOT NULL,status text NOT NULL CHECK(status IN ('pending','resolved','revoked')),session_id text,session_revision numeric,source_receipt_json text NOT NULL,PRIMARY KEY({O},input_request_id),FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id),FOREIGN KEY({O},session_id,session_revision) REFERENCES vnext.session_manifest({O},session_id,revision),CHECK((session_id IS NULL)=(session_revision IS NULL)))",
        f"ALTER TABLE vnext.work_item ADD FOREIGN KEY({O},input_request_id) REFERENCES vnext.input_request({O},input_request_id),ADD FOREIGN KEY({O},session_id,session_revision) REFERENCES vnext.session_manifest({O},session_id,revision)",
        f"CREATE TABLE vnext.goal_criterion({S},criterion_id text NOT NULL,revision {REV},definition_json text NOT NULL,PRIMARY KEY({O},criterion_id,revision),{FK})",
        f"CREATE TABLE vnext.criterion_judgment({S},judgment_id text NOT NULL,criterion_id text NOT NULL,criterion_revision numeric NOT NULL,status text NOT NULL CHECK(status IN ('met','not_met','unknown','not_applicable')),applicability text NOT NULL CHECK(applicability IN ('current','stale','disputed','retracted')),source_receipt_json text NOT NULL,access_level integer NOT NULL DEFAULT 0,PRIMARY KEY({O},judgment_id),FOREIGN KEY({O},criterion_id,criterion_revision) REFERENCES vnext.goal_criterion({O},criterion_id,revision))",
        f"ALTER TABLE vnext.goal_criterion ADD current_judgment_id text,ADD FOREIGN KEY({O},current_judgment_id) REFERENCES vnext.criterion_judgment({O},judgment_id)",
        f"CREATE TABLE vnext.completion_decision({S},receipt_id text NOT NULL,epoch_id text NOT NULL,action text NOT NULL CHECK(action IN ('quiesce','abort','close')),expected_control_version numeric NOT NULL,board_revision numeric NOT NULL,deadline timestamptz NOT NULL,close_trigger text,result_outcome text,source_receipt_json text NOT NULL,PRIMARY KEY({O},receipt_id),{FK})",
    ]
    for statement in statements:
        connection.execute(statement)
    # Preserve the original DAG trigger and same-Task locks. Only replace its typed criterion FK.
    foreign_keys = connection.execute(
        "SELECT conname FROM pg_constraint WHERE conrelid='vnext.work_dependency'::regclass AND confrelid='vnext.entity_revision_registry'::regclass"
    ).fetchall()
    for (name,) in foreign_keys:
        connection.execute(
            sql.SQL("ALTER TABLE vnext.work_dependency DROP CONSTRAINT {}").format(
                sql.Identifier(name)
            )
        )
    # No fake criterion conversion: any pre-existing populated legacy criterion requires an explicit mapping.
    if connection.execute(
        "SELECT 1 FROM vnext.work_dependency WHERE criterion_id IS NOT NULL LIMIT 1"
    ).fetchone():
        raise ValueError(
            "existing dependency criterion requires explicit GoalCriterion mapping"
        )
    connection.execute(
        f"ALTER TABLE vnext.work_dependency ADD FOREIGN KEY({O},criterion_id,criterion_revision) REFERENCES vnext.goal_criterion({O},criterion_id,revision),ADD CHECK(criterion_type IS NULL OR criterion_type='goal_criterion')"
    )
    app = sql.Identifier(application_role)
    control = "(current_setting('wuji.control',true)='true' OR current_setting('wuji.admit',true)='true' OR current_setting('wuji.observe',true)='true')"
    connection.execute(
        """CREATE FUNCTION vnext.guard_task_control() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF (to_jsonb(NEW)-'board_revision'-'event_seq'-'observation_count') IS DISTINCT FROM (to_jsonb(OLD)-'board_revision'-'event_seq'-'observation_count')
        AND current_user<>(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=TG_RELID)
        AND current_setting('wuji.control',true) IS DISTINCT FROM 'true' AND current_setting('wuji.observe',true) IS DISTINCT FROM 'true' AND current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
        THEN RAISE EXCEPTION 'dedicated control authority required' USING ERRCODE='42501'; END IF; RETURN NEW; END $$"""
    )
    connection.execute(
        "CREATE TRIGGER task_control_authority BEFORE UPDATE ON vnext.task FOR EACH ROW EXECUTE FUNCTION vnext.guard_task_control()"
    )
    for table in [
        "work_suspension",
        "control_receipt",
        "task_capacity_pool",
        "capacity_reservation",
        "execution_observation",
        "run_operation_settlement",
        "resource_reservation",
        "session_manifest",
        "input_request",
        "goal_criterion",
        "criterion_judgment",
        "completion_decision",
    ]:
        name = sql.Identifier("vnext", table)
        scope = "vnext.in_scope(tenant_id,project_id,task_id" + (
            ",access_level)"
            if table in {"session_manifest", "criterion_judgment"}
            else ")"
        )
        connection.execute(
            sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(name)
        )
        connection.execute(
            sql.SQL(
                f"CREATE POLICY scoped_read ON {{}} FOR SELECT USING({scope})"
            ).format(name)
        )
        connection.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(name, app))
        if table in {
            "work_suspension",
            "control_receipt",
            "capacity_reservation",
            "execution_observation",
        }:
            power = (
                "current_setting('wuji.observe',true)='true'"
                if table == "execution_observation"
                else control
            )
            connection.execute(
                sql.SQL(
                    f"CREATE POLICY control_insert ON {{}} FOR INSERT WITH CHECK({scope} AND {power})"
                ).format(name)
            )
            connection.execute(sql.SQL("GRANT INSERT ON {} TO {}").format(name, app))
        if table in {
            "work_suspension",
            "capacity_reservation",
            "input_request",
            "session_manifest",
        }:
            # UPDATE visibility is needed for Session row locks; no Session columns are writable.
            connection.execute(
                sql.SQL(
                    f"CREATE POLICY control_update ON {{}} FOR UPDATE USING({scope} AND {control}) WITH CHECK({scope} AND {control})"
                ).format(name)
            )
            columns = {
                "work_suspension": "cause_ref",
                "capacity_reservation": "state",
                "input_request": "status",
                "session_manifest": "session_id",
            }[table]
            connection.execute(
                sql.SQL(f"GRANT UPDATE({columns}) ON {{}} TO {{}}").format(name, app)
            )
        if table == "work_suspension":
            connection.execute(
                sql.SQL(
                    f"CREATE POLICY control_delete ON {{}} FOR DELETE USING({scope} AND {control})"
                ).format(name)
            )
            connection.execute(sql.SQL("GRANT DELETE ON {} TO {}").format(name, app))
    # Updates to future published metadata are denied; SELECT FOR UPDATE remains available.
    connection.execute(
        "CREATE FUNCTION vnext.guard_session_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN IF NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'session is immutable' USING ERRCODE='42501'; END IF; RETURN NEW; END $$"
    )
    connection.execute(
        "CREATE TRIGGER session_immutable BEFORE UPDATE ON vnext.session_manifest FOR EACH ROW EXECUTE FUNCTION vnext.guard_session_immutable()"
    )
    connection.execute(
        "CREATE FUNCTION vnext.guard_input_revoke() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN IF NEW.status IS DISTINCT FROM OLD.status AND NEW.status<>'revoked' AND current_user<>(SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=TG_RELID) THEN RAISE EXCEPTION 'P08 owns input resolution' USING ERRCODE='42501'; END IF; RETURN NEW; END $$"
    )
    connection.execute(
        "CREATE TRIGGER input_revoke_only BEFORE UPDATE ON vnext.input_request FOR EACH ROW EXECUTE FUNCTION vnext.guard_input_revoke()"
    )
    for table, columns in {
        "task": "control_version,desired_state,observed_state,activated_at,close_trigger,result_outcome,completion_epoch_id,execution_allowed,execution_epoch",
        "work_item": "kind,desired_state,revision,run_epoch,current_run_id,intent_id,intent_revision,blocked_reason,terminal_reason,input_request_id,session_id,session_revision,state",
        "agent_run": "process_state,execution_allowed,process_identity_json,started_at,exited_at,stop_kind,last_observation_id",
    }.items():
        scope = "vnext.in_scope(tenant_id,project_id,task_id)"
        connection.execute(
            f"CREATE POLICY control_update ON vnext.{table} FOR UPDATE USING({scope} AND {control}) WITH CHECK({scope} AND {control})"
        )
        connection.execute(
            sql.SQL(f"GRANT UPDATE({columns}) ON vnext.{table} TO {{}}").format(app)
        )
        if table in {"work_item", "agent_run"}:
            connection.execute(
                f"CREATE POLICY admission_insert ON vnext.{table} FOR INSERT WITH CHECK({scope} AND current_setting('wuji.admit',true)='true')"
            )
            # An INSERT cannot set its own result projection.
            cols = (
                f"{O},work_item_id,kind,intent_id,intent_revision"
                if table == "work_item"
                else f"{O},agent_run_id,work_item_id,receiver_id,execution_epoch,run_epoch,runtime_attempt,environment_ref,model_mode,start_operation_id,pod_uid,output_expectation"
            )
            connection.execute(
                sql.SQL(f"GRANT INSERT({cols}) ON vnext.{table} TO {{}}").format(app)
            )
    connection.execute("DROP POLICY scoped_insert ON vnext.work_dependency")
    connection.execute(
        f"CREATE POLICY control_insert ON vnext.work_dependency FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id) AND {control})"
    )
    connection.execute("ALTER TABLE vnext.capacity_pool ENABLE ROW LEVEL SECURITY")
    pool_scope = "EXISTS(SELECT 1 FROM vnext.task_capacity_pool p WHERE p.pool_key=capacity_pool.pool_key AND p.tenant_id=current_setting('wuji.tenant',true) AND p.task_id=current_setting('wuji.task',true))"
    connection.execute(
        f"CREATE POLICY scoped_read ON vnext.capacity_pool FOR SELECT USING({pool_scope})"
    )
    connection.execute(
        f"CREATE POLICY control_update ON vnext.capacity_pool FOR UPDATE USING({pool_scope} AND {control}) WITH CHECK({pool_scope} AND {control})"
    )
    connection.execute(
        sql.SQL("GRANT SELECT,UPDATE(used) ON vnext.capacity_pool TO {}").format(app)
    )
    _result_projection(connection, app)
    # Rebuild only the projection from actual pre-P05 submissions/receipts. Do not
    # rewrite historical outcomes, epochs, or infer a Task activation from a Run.
    connection.execute(
        """WITH ranked AS (
        SELECT s.tenant_id,s.project_id,s.task_id,s.agent_run_id,s.submission_id,
        COALESCE(r.receipt_json::jsonb->>'status','received') AS status,
        row_number() OVER(PARTITION BY s.tenant_id,s.project_id,s.task_id,s.agent_run_id
          ORDER BY CASE WHEN r.receipt_json::jsonb->>'status'='accepted' THEN 0 ELSE 1 END,
          s.created_at DESC,s.submission_id DESC) AS position
        FROM vnext.result_submission s LEFT JOIN vnext.result_receipt r USING(tenant_id,project_id,task_id,submission_id))
        UPDATE vnext.agent_run a SET result_state=x.status,result_submission_id=x.submission_id
        FROM ranked x WHERE x.position=1 AND (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=(x.tenant_id,x.project_id,x.task_id,x.agent_run_id)"""
    )
    for fn in [
        "guard_session_immutable()",
        "guard_input_revoke()",
        "guard_task_control()",
    ]:
        connection.execute(f"REVOKE EXECUTE ON FUNCTION vnext.{fn} FROM PUBLIC")
        connection.execute(
            sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{fn} TO {{}}").format(app)
        )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))


def _result_projection(connection, app):
    connection.execute(
        """CREATE FUNCTION vnext.project_run_result(t text,p text,k text,r text,s text)
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
      AND EXISTS(SELECT 1 FROM vnext.run_operation_settlement x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r AND x.status='settled')
      AND NOT EXISTS(SELECT 1 FROM vnext.resource_reservation x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r AND x.state<>'released')
      AND NOT EXISTS(SELECT 1 FROM vnext.input_request i WHERE i.tenant_id=t AND i.project_id=p AND i.task_id=k AND i.work_item_id=ar.work_item_id AND i.status='pending')
      AND NOT EXISTS(SELECT 1 FROM vnext.result_submission x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.agent_run_id=r);
    END IF;
    RETURN (SELECT result_state FROM vnext.agent_run WHERE tenant_id=t AND project_id=p AND task_id=k AND agent_run_id=r);
    END $$"""
    )
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.project_run_result(text,text,text,text,text) FROM PUBLIC"
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.project_run_result(text,text,text,text,text) TO {}"
        ).format(app)
    )
