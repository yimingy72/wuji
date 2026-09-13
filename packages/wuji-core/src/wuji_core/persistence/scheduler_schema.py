"""P09 durable scheduling and narrowly scoped admission-owned publication.

Main allocated this migration after M1 released its database window.
Receiver records are deployment prerequisites, never proof that a process ran.
"""

from psycopg import sql

HEAD = "vnext_0010_p09_scheduler"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
F = f"FOREIGN KEY({O}) REFERENCES vnext.task({O})"
TABLES = (
    "scheduler_state", "scheduler_work", "scheduler_trigger", "scheduler_reason_lease",
    "scheduler_decision", "scheduler_waiter", "scheduler_wait_predicate",
    "scheduler_assignment", "scheduler_block", "scheduler_progress", "scheduler_receiver",
    "scheduler_identity_template",
)


def upgrade(connection, application_role):
    for statement in statements():
        connection.execute(statement)
    for statement in privileges(application_role):
        connection.execute(statement)
    # Add a parallel, narrowly scoped INSERT policy. Existing P03/P04/P06
    # policies and all actual-mutation guards are left untouched.
    power = """current_setting('wuji.admit',true)='true'
        AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
        AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE
        a.tenant_id=current_setting('wuji.tenant',true)
        AND a.project_id=current_setting('wuji.project',true)
        AND a.task_id=current_setting('wuji.task',true)
        AND a.subject=current_setting('wuji.subject',true) AND a.can_read AND a.can_admit)"""
    for table in ("publication", "publication_ref", "snapshot_manifest", "snapshot_ref"):
        qualifier = ""
        if table == "publication":
            qualifier = " AND kind='snapshot'"
        elif table == "publication_ref":
            qualifier = """ AND EXISTS(SELECT 1 FROM vnext.publication p
              WHERE (p.tenant_id,p.project_id,p.task_id,p.publication_id)=
              (publication_ref.tenant_id,publication_ref.project_id,publication_ref.task_id,publication_ref.publication_id)
              AND p.kind='snapshot')"""
        elif table == "snapshot_manifest":
            qualifier = """ AND EXISTS(SELECT 1 FROM vnext.publication p
              WHERE (p.tenant_id,p.project_id,p.task_id,p.publication_id)=
              (snapshot_manifest.tenant_id,snapshot_manifest.project_id,snapshot_manifest.task_id,snapshot_manifest.publication_id)
              AND p.kind='snapshot')"""
        connection.execute(f"CREATE POLICY scheduler_snapshot_insert ON vnext.{table} FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND {power}{qualifier})")
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))


def statements():
    yield "CREATE SEQUENCE vnext.scheduler_selection_order AS bigint"
    yield f"""CREATE TABLE vnext.scheduler_state({S},
        trigger_generation bigint NOT NULL DEFAULT 0,
        consumed_generation bigint NOT NULL DEFAULT 0,
        inflight_reason_work_id text, failure_count integer NOT NULL DEFAULT 0,
        retry_at timestamptz,blocked_reason text,
        last_selected bigint NOT NULL DEFAULT 0,no_progress_count bigint NOT NULL DEFAULT 0,
        preparation_block_reason text,preparation_release_condition text,
        PRIMARY KEY({O}),{F},
        CHECK(trigger_generation>=consumed_generation AND consumed_generation>=0),
        CHECK(failure_count>=0 AND no_progress_count>=0),
        FOREIGN KEY({O},inflight_reason_work_id) REFERENCES vnext.work_item({O},work_item_id))"""
    yield f"""CREATE TABLE vnext.scheduler_work({S},work_item_id text NOT NULL,
        key_digest text NOT NULL,key_json text NOT NULL,intent_id text,intent_revision numeric,
        priority integer NOT NULL CHECK(priority BETWEEN -10 AND 10),
        ready_since timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({O},work_item_id),UNIQUE({O},key_digest),
        UNIQUE({O},intent_id,intent_revision),
        CHECK((intent_id IS NULL)=(intent_revision IS NULL)),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id),
        FOREIGN KEY({O},intent_id,intent_revision) REFERENCES vnext.intent_revision({O},entity_id,revision))"""
    yield f"""CREATE TABLE vnext.scheduler_trigger({S},event_key text NOT NULL,
        event_seq numeric,generation bigint,reason text NOT NULL,
        PRIMARY KEY({O},event_key),UNIQUE({O},generation),{F},
        FOREIGN KEY({O},event_seq) REFERENCES vnext.outbox({O},event_seq),
        CHECK(generation IS NULL OR generation>0))"""
    yield f"""CREATE TABLE vnext.scheduler_reason_lease({S},work_item_id text NOT NULL,
        processing_generation bigint NOT NULL CHECK(processing_generation>0),
        snapshot_id text NOT NULL,status text NOT NULL CHECK(status IN ('inflight','consumed','failed')),
        PRIMARY KEY({O},work_item_id),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id),
        FOREIGN KEY({O},snapshot_id) REFERENCES vnext.snapshot_manifest({O},snapshot_id))"""
    yield f"""CREATE TABLE vnext.scheduler_decision({S},submission_id text NOT NULL,
        work_item_id text NOT NULL,processing_generation bigint NOT NULL,
        status text NOT NULL CHECK(status IN ('accepted','rejected')),
        reason_code text,decision_json text NOT NULL,raw_digest text NOT NULL,
        PRIMARY KEY({O},submission_id),
        FOREIGN KEY({O},submission_id) REFERENCES vnext.result_submission({O},submission_id),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id))"""
    yield f"""CREATE TABLE vnext.scheduler_waiter({S},waiter_id text NOT NULL,
        work_item_id text NOT NULL,processing_generation bigint NOT NULL,
        predicate_digest text NOT NULL,status text NOT NULL CHECK(status IN ('waiting','ready')),
        PRIMARY KEY({O},waiter_id),UNIQUE({O},work_item_id,processing_generation),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id))"""
    yield f"""CREATE TABLE vnext.scheduler_wait_predicate({S},waiter_id text NOT NULL,
        ordinal integer NOT NULL,kind text NOT NULL CHECK(kind IN (
        'work_settled.v1','work_accepted_result.v1','criterion_satisfied.v1','input_resolved.v1')),
        work_ref text,criterion_id text,criterion_revision numeric,input_ref text,
        PRIMARY KEY({O},waiter_id,ordinal),
        FOREIGN KEY({O},waiter_id) REFERENCES vnext.scheduler_waiter({O},waiter_id),
        FOREIGN KEY({O},work_ref) REFERENCES vnext.work_item({O},work_item_id),
        FOREIGN KEY({O},criterion_id,criterion_revision) REFERENCES vnext.goal_criterion({O},criterion_id,revision),
        FOREIGN KEY({O},input_ref) REFERENCES vnext.input_request({O},input_request_id),
        CHECK((kind='input_resolved.v1' AND input_ref IS NOT NULL AND work_ref IS NULL AND criterion_id IS NULL AND criterion_revision IS NULL)
          OR (kind IN ('work_settled.v1','work_accepted_result.v1') AND work_ref IS NOT NULL AND input_ref IS NULL AND criterion_id IS NULL AND criterion_revision IS NULL)
          OR (kind='criterion_satisfied.v1' AND work_ref IS NOT NULL AND criterion_id IS NOT NULL AND criterion_revision IS NOT NULL AND input_ref IS NULL)))"""
    yield f"""CREATE TABLE vnext.scheduler_assignment({S},agent_run_id text NOT NULL,
        work_item_id text NOT NULL,operation_id text NOT NULL,snapshot_id text NOT NULL,
        assignment_json text NOT NULL,assignment_digest text NOT NULL,
        credential_ref text NOT NULL,event_seq numeric NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({O},agent_run_id),UNIQUE({O},operation_id),
        FOREIGN KEY({O},work_item_id,agent_run_id) REFERENCES vnext.agent_run({O},work_item_id,agent_run_id),
        FOREIGN KEY({O},snapshot_id) REFERENCES vnext.snapshot_manifest({O},snapshot_id),
        FOREIGN KEY({O},event_seq) REFERENCES vnext.outbox({O},event_seq))"""
    yield f"""CREATE TABLE vnext.scheduler_block({S},work_item_id text NOT NULL,
        reason_code text NOT NULL,responsible_role text NOT NULL,release_condition text NOT NULL,
        machine_recheck boolean NOT NULL,PRIMARY KEY({O},work_item_id),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id))"""
    yield f"""CREATE TABLE vnext.scheduler_progress({S},source_key text NOT NULL,
        category text NOT NULL CHECK(category IN ('material','resolved_blocker')),
        event_seq numeric NOT NULL,PRIMARY KEY({O},source_key),
        FOREIGN KEY({O},event_seq) REFERENCES vnext.outbox({O},event_seq))"""
    yield f"""CREATE TABLE vnext.scheduler_identity_template({S},template_ref text NOT NULL,
        issuer text NOT NULL,audience text NOT NULL,signing_key_ref text NOT NULL,signing_kid text NOT NULL,
        encryption_key_ref text NOT NULL,clearance integer NOT NULL CHECK(clearance>=0),
        enabled boolean NOT NULL DEFAULT false,PRIMARY KEY({O},template_ref),{F})"""
    yield f"""CREATE TABLE vnext.scheduler_receiver({S},runtime_attempt numeric NOT NULL,
        receiver_id text NOT NULL,environment_ref text NOT NULL,
        model_mode text NOT NULL CHECK(model_mode IN ('synthetic','real','unknown')),
        receiver_subject text NOT NULL,credential_template_ref text NOT NULL,
        harness_profiles_json text NOT NULL,enabled boolean NOT NULL DEFAULT false,
        PRIMARY KEY({O},runtime_attempt),{F},
        FOREIGN KEY({O},receiver_subject) REFERENCES vnext.task_access({O},subject),
        FOREIGN KEY({O},credential_template_ref) REFERENCES vnext.scheduler_identity_template({O},template_ref))"""
    yield from credential_statements()
    yield from snapshot_reader_statements()
    yield """CREATE FUNCTION vnext.guard_scheduler_state() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF NEW.trigger_generation<OLD.trigger_generation OR NEW.consumed_generation<OLD.consumed_generation
           OR NEW.last_selected<OLD.last_selected THEN
          RAISE EXCEPTION 'scheduler watermarks cannot regress' USING ERRCODE='23514';
        END IF; RETURN NEW; END $$"""
    yield "CREATE TRIGGER scheduler_state_monotonic BEFORE UPDATE ON vnext.scheduler_state FOR EACH ROW EXECUTE FUNCTION vnext.guard_scheduler_state()"
    yield "REVOKE EXECUTE ON FUNCTION vnext.guard_scheduler_state() FROM PUBLIC"


def privileges(application_role):
    """Only new-table privileges. Shared producer grants require main's allocation."""
    app = sql.Identifier(application_role)
    power = """current_setting('wuji.admit',true)='true'
        AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
        AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE
        (a.tenant_id,a.project_id,a.task_id)=(tenant_id,project_id,task_id)
        AND a.tenant_id=current_setting('wuji.tenant',true)
        AND a.project_id=current_setting('wuji.project',true)
        AND a.task_id=current_setting('wuji.task',true)
        AND a.subject=current_setting('wuji.subject',true) AND a.can_read AND a.can_admit)"""
    for table in TABLES:
        target = sql.Identifier("vnext", table)
        scope = "vnext.in_scope(tenant_id,project_id,task_id)"
        # Internal scheduler rows may carry sensitive references. Scheduler ACL
        # is required even for read; they are not a public topology projection.
        yield sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(target)
        yield sql.SQL(f"CREATE POLICY scheduler_read ON {{}} FOR SELECT USING({scope} AND {power})").format(target)
        yield sql.SQL("GRANT SELECT ON {} TO {}").format(target, app)
        if table == "scheduler_assignment":
            receiver = """current_setting('wuji.observe',true)='true'
                AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
                AND EXISTS(SELECT 1 FROM vnext.agent_run a JOIN vnext.scheduler_receiver r
                USING(tenant_id,project_id,task_id,runtime_attempt,receiver_id)
                WHERE (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
                (scheduler_assignment.tenant_id,scheduler_assignment.project_id,scheduler_assignment.task_id,scheduler_assignment.agent_run_id)
                AND r.receiver_subject=current_setting('wuji.subject',true))"""
            yield sql.SQL(f"CREATE POLICY receiver_read ON {{}} FOR SELECT USING({scope} AND {receiver})").format(target)
        if table == "scheduler_receiver":
            yield sql.SQL(f"""CREATE POLICY receiver_read ON {{}} FOR SELECT USING({scope}
                AND current_setting('wuji.observe',true)='true'
                AND receiver_subject=current_setting('wuji.subject',true)
                AND COALESCE(current_setting('wuji.request_purpose',true),'')='')""").format(target)
        if table in {"scheduler_receiver", "scheduler_identity_template"}:
            continue
        yield sql.SQL(f"CREATE POLICY scheduler_insert ON {{}} FOR INSERT WITH CHECK({scope} AND {power})").format(target)
        yield sql.SQL("GRANT INSERT ON {} TO {}").format(target, app)
        columns = {
            "scheduler_state": "trigger_generation,consumed_generation,inflight_reason_work_id,failure_count,retry_at,blocked_reason,last_selected,no_progress_count,preparation_block_reason,preparation_release_condition",
            "scheduler_reason_lease": "processing_generation,snapshot_id,status",
            "scheduler_waiter": "status",
            "scheduler_block": "reason_code,responsible_role,release_condition,machine_recheck",
        }.get(table)
        if columns:
            yield sql.SQL(f"CREATE POLICY scheduler_update ON {{}} FOR UPDATE USING({scope} AND {power}) WITH CHECK({scope} AND {power})").format(target)
            yield sql.SQL(f"GRANT UPDATE({columns}) ON {{}} TO {{}}").format(target, app)
        if table == "scheduler_block":
            yield sql.SQL(f"CREATE POLICY scheduler_delete ON {{}} FOR DELETE USING({scope} AND {power})").format(target)
            yield sql.SQL("GRANT DELETE ON {} TO {}").format(target, app)
    yield sql.SQL("GRANT USAGE ON SEQUENCE vnext.scheduler_selection_order TO {}").format(app)
    yield sql.SQL("GRANT EXECUTE ON FUNCTION vnext.guard_scheduler_state() TO {}").format(app)
    for signature in (
        "stage_scheduler_credential(text,text,text,text,text,text,bytea,bytea)",
        "bind_scheduler_credential(text,text,text,text,text)",
        "read_scheduler_credential(text,text,text,text)",
        "bind_scheduler_snapshot(text,text,text,text,text)",
        "can_read_scheduler_snapshot(text,text,text,text)",
    ):
        yield sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{signature} TO {{}}").format(app)


def snapshot_reader_statements():
    yield f"""CREATE TABLE vnext.scheduler_snapshot_reader({S},snapshot_id text NOT NULL,
        agent_run_id text NOT NULL,subject text NOT NULL,clearance integer NOT NULL,
        PRIMARY KEY({O},snapshot_id,subject),
        FOREIGN KEY({O},snapshot_id) REFERENCES vnext.snapshot_manifest({O},snapshot_id),
        FOREIGN KEY({O},agent_run_id) REFERENCES vnext.scheduler_assignment({O},agent_run_id),
        FOREIGN KEY({O},agent_run_id,subject) REFERENCES vnext.run_writer({O},agent_run_id,subject))"""
    yield "ALTER TABLE vnext.scheduler_snapshot_reader ENABLE ROW LEVEL SECURITY"
    yield """CREATE FUNCTION vnext.bind_scheduler_snapshot(t text,p text,k text,r text,s text)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE b text; level integer; doc text;
        BEGIN
          SELECT c.binding_json INTO doc FROM vnext.scheduler_credential c WHERE
            c.tenant_id=t AND c.project_id=p AND c.task_id=k AND c.agent_run_id=r AND c.bound;
          IF NOT FOUND THEN RAISE EXCEPTION 'bound credential required' USING ERRCODE='42501'; END IF;
          PERFORM vnext.require_scheduler_identity(t,p,k,doc::jsonb);
          b:=doc::jsonb->>'subject';
          SELECT a.clearance INTO level FROM vnext.task_access a WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.subject=b AND a.can_read;
          IF level IS NULL OR NOT EXISTS(SELECT 1 FROM vnext.scheduler_assignment d
            JOIN vnext.snapshot_manifest m USING(tenant_id,project_id,task_id,snapshot_id)
            WHERE d.tenant_id=t AND d.project_id=p AND d.task_id=k AND d.agent_run_id=r
            AND d.snapshot_id=s AND m.access_level<=level)
          THEN RAISE EXCEPTION 'assignment snapshot clearance required' USING ERRCODE='42501'; END IF;
          INSERT INTO vnext.scheduler_snapshot_reader(tenant_id,project_id,task_id,snapshot_id,agent_run_id,subject,clearance)
            VALUES(t,p,k,s,r,b,level);
        END $$"""
    yield """CREATE FUNCTION vnext.can_read_scheduler_snapshot(t text,p text,k text,s text)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
        SELECT COALESCE(vnext.in_scope(t,p,k),false) AND EXISTS(
          SELECT 1 FROM vnext.scheduler_snapshot_reader r JOIN vnext.task_access a
            USING(tenant_id,project_id,task_id,subject)
          JOIN vnext.run_writer w USING(tenant_id,project_id,task_id,agent_run_id,subject)
          JOIN vnext.scheduler_assignment d USING(tenant_id,project_id,task_id,agent_run_id,snapshot_id)
          WHERE r.tenant_id=t AND r.project_id=p AND r.task_id=k AND r.snapshot_id=s
            AND r.subject=current_setting('wuji.subject',true) AND a.can_read AND NOT w.revoked
            AND a.clearance=r.clearance AND a.clearance=COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1)) $$"""
    yield "REVOKE EXECUTE ON FUNCTION vnext.bind_scheduler_snapshot(text,text,text,text,text) FROM PUBLIC"
    yield "REVOKE EXECUTE ON FUNCTION vnext.can_read_scheduler_snapshot(text,text,text,text) FROM PUBLIC"


def credential_statements():
    yield f"""CREATE TABLE vnext.scheduler_credential({S},credential_ref text NOT NULL,
        agent_run_id text NOT NULL,template_ref text NOT NULL,binding_json text NOT NULL,
        encryption_key_ref text NOT NULL,nonce bytea NOT NULL CHECK(octet_length(nonce)=12),
        ciphertext bytea NOT NULL CHECK(octet_length(ciphertext)>16),bound boolean NOT NULL DEFAULT false,
        PRIMARY KEY({O},credential_ref),UNIQUE({O},agent_run_id),
        FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),
        FOREIGN KEY({O},template_ref) REFERENCES vnext.scheduler_identity_template({O},template_ref))"""
    yield "ALTER TABLE vnext.scheduler_credential ENABLE ROW LEVEL SECURITY"
    yield f"ALTER TABLE vnext.scheduler_assignment ADD FOREIGN KEY({O},credential_ref) REFERENCES vnext.scheduler_credential({O},credential_ref) DEFERRABLE INITIALLY DEFERRED"
    yield """CREATE FUNCTION vnext.require_scheduler_identity(t text,p text,k text,b jsonb)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE i jsonb:=b->'identity'; a vnext.agent_run; w vnext.work_item; taskrow vnext.task;
        cfg jsonb; profile jsonb; expiry timestamptz;
        BEGIN
          IF NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT EXISTS(SELECT 1 FROM vnext.task_access x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k
              AND x.subject=current_setting('wuji.subject',true) AND x.can_read AND x.can_admit)
          THEN RAISE EXCEPTION 'scheduler identity authority required' USING ERRCODE='42501'; END IF;
          SELECT * INTO taskrow FROM vnext.task WHERE tenant_id=t AND project_id=p AND task_id=k;
          SELECT * INTO a FROM vnext.agent_run WHERE tenant_id=t AND project_id=p AND task_id=k AND agent_run_id=i->>'agent_run_id';
          IF NOT FOUND THEN RAISE EXCEPTION 'registered run required' USING ERRCODE='42501'; END IF;
          SELECT * INTO w FROM vnext.work_item WHERE tenant_id=t AND project_id=p AND task_id=k AND work_item_id=a.work_item_id;
          IF NOT FOUND OR w.current_run_id IS DISTINCT FROM a.agent_run_id OR w.run_epoch<>a.run_epoch
            OR w.state<>'leased' OR w.desired_state<>'run' OR NOT a.execution_allowed OR a.process_state<>'registered'
            OR a.start_operation_id IS NULL OR a.stop_kind IS NOT NULL
            OR NOT taskrow.execution_allowed OR taskrow.desired_state<>'run' OR taskrow.activated_at IS NULL
            OR taskrow.observed_state<>'running' OR taskrow.completion_epoch_id IS NOT NULL OR a.execution_epoch<>taskrow.execution_epoch
            OR a.runtime_attempt<>taskrow.runtime_attempt
            OR EXISTS(SELECT 1 FROM vnext.work_suspension x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.work_item_id=w.work_item_id)
            OR i IS DISTINCT FROM jsonb_build_object('tenant_id',t,'project_id',p,'task_id',k,
              'work_item_id',a.work_item_id,'agent_run_id',a.agent_run_id,'execution_epoch',a.execution_epoch::text,
              'run_epoch',a.run_epoch::text,'runtime_attempt',a.runtime_attempt::text,'receiver_id',a.receiver_id)
            OR b->>'subject' IS DISTINCT FROM 'run.worker:'||a.agent_run_id
            OR b->>'session_lineage' IS DISTINCT FROM 'run:'||a.agent_run_id
            OR b->'purposes' IS DISTINCT FROM '["model_request","tool_request"]'::jsonb
            OR COALESCE(length(b->>'token_id'),0)=0
          THEN RAISE EXCEPTION 'current minimal run binding required' USING ERRCODE='42501'; END IF;
          SELECT document_json::jsonb INTO cfg FROM vnext.admission_config WHERE tenant_id=t AND project_id=p AND task_id=k;
          profile:=taskrow.definition_json::jsonb->'worker_profiles'->w.kind;
          expiry:=(b->>'expires_at')::timestamptz;
          IF cfg IS NULL OR profile IS NULL OR expiry<=clock_timestamp()
            OR expiry>(taskrow.definition_json::jsonb->'task'->>'authorization_expires_at')::timestamptz
            OR expiry>taskrow.activated_at+((cfg->'runtime'->'limits'->>'max_elapsed_seconds')::integer*interval '1 second')
            OR b->'allowed_tool_refs' IS DISTINCT FROM profile->'body'->'tool_definition_refs'
            OR NOT (b->'allowed_tool_refs' <@ cfg->'allowed_tool_refs')
            OR NOT (b->'allowed_tool_refs' <@ cfg->'runtime'->'allowed_tool_refs')
            OR NOT EXISTS(SELECT 1 FROM vnext.capacity_reservation r WHERE r.tenant_id=t AND r.project_id=p AND r.task_id=k AND r.agent_run_id=a.agent_run_id)
            OR EXISTS(SELECT 1 FROM vnext.task_capacity_pool q LEFT JOIN vnext.capacity_reservation r
              ON (r.tenant_id,r.project_id,r.task_id,r.pool_key,r.agent_run_id)=(q.tenant_id,q.project_id,q.task_id,q.pool_key,a.agent_run_id)
              WHERE q.tenant_id=t AND q.project_id=p AND q.task_id=k AND (r.state IS NULL OR r.state='released'))
          THEN RAISE EXCEPTION 'fixed profile, expiry and reservations required' USING ERRCODE='42501'; END IF;
        END $$"""
    yield """CREATE FUNCTION vnext.stage_scheduler_credential(t text,p text,k text,tr text,body text,ref text,n bytea,c bytea)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE b jsonb:=body::jsonb; template vnext.scheduler_identity_template;
        BEGIN
          PERFORM vnext.require_scheduler_identity(t,p,k,b);
          SELECT x.* INTO template FROM vnext.scheduler_identity_template x JOIN vnext.scheduler_receiver r
          ON (r.tenant_id,r.project_id,r.task_id,r.credential_template_ref)=(x.tenant_id,x.project_id,x.task_id,x.template_ref)
          WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.template_ref=tr AND x.enabled AND r.enabled
            AND r.runtime_attempt=(b->'identity'->>'runtime_attempt')::numeric AND r.receiver_id=b->'identity'->>'receiver_id';
          IF NOT FOUND OR template.clearance>COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1)
            OR template.clearance>(SELECT clearance FROM vnext.task_access WHERE tenant_id=t AND project_id=p AND task_id=k AND subject=current_setting('wuji.subject',true))
            OR length(ref) NOT BETWEEN 1 AND 256
          THEN RAISE EXCEPTION 'published identity template required' USING ERRCODE='42501'; END IF;
          INSERT INTO vnext.scheduler_credential(tenant_id,project_id,task_id,credential_ref,agent_run_id,
            template_ref,binding_json,encryption_key_ref,nonce,ciphertext)
          VALUES(t,p,k,ref,b->'identity'->>'agent_run_id',tr,body,template.encryption_key_ref,n,c);
        END $$"""
    yield """CREATE FUNCTION vnext.bind_scheduler_credential(t text,p text,k text,ref text,body text)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE b jsonb:=body::jsonb; saved vnext.scheduler_credential; level integer; runid text;
        BEGIN
          PERFORM vnext.require_scheduler_identity(t,p,k,b);
          SELECT * INTO saved FROM vnext.scheduler_credential WHERE tenant_id=t AND project_id=p AND task_id=k AND credential_ref=ref FOR UPDATE;
          IF NOT FOUND OR saved.binding_json::jsonb IS DISTINCT FROM b THEN RAISE EXCEPTION 'staged binding required' USING ERRCODE='42501'; END IF;
          IF saved.bound THEN RETURN; END IF;
          SELECT clearance INTO level FROM vnext.scheduler_identity_template WHERE tenant_id=t AND project_id=p AND task_id=k AND template_ref=saved.template_ref AND enabled;
          IF level IS NULL OR level>COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1)
          THEN RAISE EXCEPTION 'current template required' USING ERRCODE='42501'; END IF;
          runid:=b->'identity'->>'agent_run_id';
          INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_model_output,clearance)
            VALUES(t,p,k,'run.worker:'||runid,true,true,true,level);
          INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,clearance)
            VALUES(t,p,k,'run.agent:'||runid,true,level);
          INSERT INTO vnext.knowledge_actor(tenant_id,project_id,task_id,subject,producer_kind,qualified_human)
            VALUES(t,p,k,'run.agent:'||runid,'agent',false);
          INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,revoked,can_settle)
            VALUES(t,p,k,runid,'run.worker:'||runid,'run.agent:'||runid,false,false);
          INSERT INTO vnext.run_credential(tenant_id,project_id,task_id,subject,token_id,agent_run_id,document_json)
            VALUES(t,p,k,'run.worker:'||runid,b->>'token_id',runid,body);
          UPDATE vnext.scheduler_credential SET bound=true WHERE tenant_id=t AND project_id=p AND task_id=k AND credential_ref=ref;
        END $$"""
    yield """CREATE FUNCTION vnext.read_scheduler_credential(t text,p text,k text,ref text)
        RETURNS TABLE(binding_json text,encryption_key_ref text,nonce bytea,ciphertext bytea)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
        IF NOT COALESCE(vnext.in_scope(t,p,k),false) OR current_setting('wuji.observe',true) IS DISTINCT FROM 'true'
          OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
          OR NOT EXISTS(SELECT 1 FROM vnext.task_access x WHERE x.tenant_id=t AND x.project_id=p AND x.task_id=k
            AND x.subject=current_setting('wuji.subject',true) AND x.can_read AND x.can_observe)
        THEN RAISE EXCEPTION 'registered receiver required' USING ERRCODE='42501'; END IF;
        RETURN QUERY SELECT s.binding_json,s.encryption_key_ref,s.nonce,s.ciphertext
          FROM vnext.scheduler_credential s JOIN vnext.agent_run a USING(tenant_id,project_id,task_id,agent_run_id)
          JOIN vnext.scheduler_receiver r USING(tenant_id,project_id,task_id,runtime_attempt,receiver_id)
          JOIN vnext.task z USING(tenant_id,project_id,task_id)
          JOIN vnext.work_item w ON (w.tenant_id,w.project_id,w.task_id,w.work_item_id,w.current_run_id)=
            (a.tenant_id,a.project_id,a.task_id,a.work_item_id,a.agent_run_id)
          JOIN vnext.run_credential c ON (c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.subject,c.token_id)=
            (s.tenant_id,s.project_id,s.task_id,s.agent_run_id,s.binding_json::jsonb->>'subject',s.binding_json::jsonb->>'token_id')
          WHERE s.tenant_id=t AND s.project_id=p AND s.task_id=k AND s.credential_ref=ref AND s.bound
            AND NOT c.revoked AND r.enabled AND r.receiver_subject=current_setting('wuji.subject',true)
            AND a.execution_allowed AND a.stop_kind IS NULL AND a.execution_epoch=z.execution_epoch
            AND a.runtime_attempt=z.runtime_attempt AND w.run_epoch=a.run_epoch AND w.desired_state='run'
            AND z.execution_allowed AND z.desired_state='run' AND (s.binding_json::jsonb->>'expires_at')::timestamptz>clock_timestamp();
        END $$"""
    yield """CREATE FUNCTION vnext.scheduler_credential_published() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
        IF NOT EXISTS(SELECT 1 FROM vnext.scheduler_credential c JOIN vnext.scheduler_assignment a
          USING(tenant_id,project_id,task_id,credential_ref,agent_run_id)
          WHERE c.tenant_id=NEW.tenant_id AND c.project_id=NEW.project_id AND c.task_id=NEW.task_id
          AND c.credential_ref=NEW.credential_ref AND c.bound)
        THEN RAISE EXCEPTION 'credential must commit with bound assignment' USING ERRCODE='23514'; END IF;
        RETURN NULL; END $$"""
    yield "CREATE CONSTRAINT TRIGGER credential_assignment_commit AFTER INSERT ON vnext.scheduler_credential DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vnext.scheduler_credential_published()"
    for signature in (
        "require_scheduler_identity(text,text,text,jsonb)",
        "stage_scheduler_credential(text,text,text,text,text,text,bytea,bytea)",
        "bind_scheduler_credential(text,text,text,text,text)",
        "read_scheduler_credential(text,text,text,text)",
        "scheduler_credential_published()",
    ):
        yield f"REVOKE EXECUTE ON FUNCTION vnext.{signature} FROM PUBLIC"
