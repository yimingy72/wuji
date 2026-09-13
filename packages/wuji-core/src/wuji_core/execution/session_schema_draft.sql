-- P08 UNNUMBERED DRAFT. Never run by the core author.
-- SOL/main integrates after the receiver-results migration, assigns the head,
-- and supplies SELECT set_config('wuji.p08_application_role', app_role, true).
-- This draft does not create a role, alter UoW, grant Worker control, or change
-- model_request/tool_request/model_settle/tool_settle into broader purposes.

ALTER TABLE vnext.session_manifest
  ADD manifest_ref text, ADD manifest_digest text, ADD frontier_digest text, ADD session_lineage text,
  ADD UNIQUE(tenant_id,project_id,task_id,manifest_ref),
  ADD CHECK ((manifest_ref IS NULL AND manifest_digest IS NULL AND frontier_digest IS NULL AND session_lineage IS NULL)
    OR (manifest_ref IS NOT NULL AND manifest_digest ~ '^[a-f0-9]{64}$'
      AND frontier_digest ~ '^[a-f0-9]{64}$' AND length(session_lineage)>0));
ALTER TABLE vnext.input_request ADD access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0);
CREATE UNIQUE INDEX one_current_work_per_session ON vnext.work_item(tenant_id,project_id,task_id,session_id) WHERE session_id IS NOT NULL;

CREATE TABLE vnext.session_capability(
  tenant_id text NOT NULL REFERENCES vnext.tenant, ref text NOT NULL, profile_digest text NOT NULL,
  document_json text NOT NULL, digest text NOT NULL CHECK(digest ~ '^[a-f0-9]{64}$'), revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY(tenant_id,ref));
CREATE INDEX session_capability_profiles ON vnext.session_capability(tenant_id,profile_digest) WHERE NOT revoked;

CREATE TABLE vnext.session_object(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  artifact_id text NOT NULL,artifact_revision numeric NOT NULL,agent_run_id text NOT NULL,writer_token_id text NOT NULL,
  role text NOT NULL CHECK(role IN ('dependency','archive','model_response','native_arguments','history_root','provider_root','memory_root')),
  refs_json text NOT NULL CHECK(jsonb_typeof(refs_json::jsonb)='array'),access_level integer NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,artifact_id,artifact_revision),
  FOREIGN KEY(tenant_id,project_id,task_id,artifact_id,artifact_revision) REFERENCES vnext.artifact(tenant_id,project_id,task_id,entity_id,revision),
  FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,agent_run_id));

CREATE TABLE vnext.session_holder(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  agent_run_id text NOT NULL,work_item_id text NOT NULL,manifest_ref text NOT NULL,
  session_lineage text NOT NULL,previous_run_id text NOT NULL,frontier_digest text NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,agent_run_id),
  FOREIGN KEY(tenant_id,project_id,task_id,work_item_id,agent_run_id) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,work_item_id,agent_run_id),
  FOREIGN KEY(tenant_id,project_id,task_id,previous_run_id) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,agent_run_id),
  FOREIGN KEY(tenant_id,project_id,task_id,manifest_ref) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,manifest_ref));

CREATE TABLE vnext.input_source(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  source_receipt_id text NOT NULL,input_request_id text NOT NULL,manifest_ref text NOT NULL,
  native_digest text NOT NULL,source_json text NOT NULL,receipt_json text NOT NULL,access_level integer NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,source_receipt_id),
  UNIQUE(tenant_id,project_id,task_id,manifest_ref,native_digest),
  UNIQUE(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,input_request_id) REFERENCES vnext.input_request(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,manifest_ref) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,manifest_ref));

CREATE TABLE vnext.approval_request(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  approval_ref text NOT NULL,input_request_id text NOT NULL,work_item_id text NOT NULL,
  session_id text NOT NULL,session_revision numeric NOT NULL,manifest_ref text NOT NULL,tool_call_id text NOT NULL,
  content_json text NOT NULL,binding_json text NOT NULL,parameters_digest text NOT NULL,tool_digest text NOT NULL,
  scope_digest text NOT NULL,profile_digest text NOT NULL,qualifications_json text NOT NULL,
  expires_at timestamptz NOT NULL,access_level integer NOT NULL,
  version numeric NOT NULL DEFAULT 1 CHECK(version>=1 AND version=trunc(version)),
  decision_status text NOT NULL DEFAULT 'pending' CHECK(decision_status IN ('pending','decided','consumed')),
  decision text CHECK(decision IN ('approve','reject')),decided_by text,decided_at timestamptz,decision_reason text,
  consumed_attempt_id text,consumed_by_run text,
  PRIMARY KEY(tenant_id,project_id,task_id,approval_ref),
  UNIQUE(tenant_id,project_id,task_id,manifest_ref,tool_call_id),
  UNIQUE(tenant_id,project_id,task_id,consumed_attempt_id),
  FOREIGN KEY(tenant_id,project_id,task_id,input_request_id) REFERENCES vnext.input_request(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,work_item_id) REFERENCES vnext.work_item(tenant_id,project_id,task_id,work_item_id),
  FOREIGN KEY(tenant_id,project_id,task_id,session_id,session_revision) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,session_id,revision),
  FOREIGN KEY(tenant_id,project_id,task_id,manifest_ref) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,manifest_ref),
  FOREIGN KEY(tenant_id,project_id,task_id,tool_call_id) REFERENCES vnext.tool_call(tenant_id,project_id,task_id,tool_call_id),
  FOREIGN KEY(tenant_id,project_id,task_id,consumed_attempt_id) REFERENCES vnext.tool_attempt(tenant_id,project_id,task_id,tool_attempt_id),
  FOREIGN KEY(tenant_id,project_id,task_id,consumed_by_run) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,agent_run_id),
  CHECK((decision_status='pending')=(decision IS NULL)),
  CHECK((decision_status='consumed')=(consumed_attempt_id IS NOT NULL AND consumed_by_run IS NOT NULL)),
  CHECK(decision_status<>'consumed' OR decision='approve'));

CREATE TABLE vnext.approval_command(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  idempotency_key text NOT NULL,approval_ref text NOT NULL,input_digest text NOT NULL,
  receipt_json text NOT NULL,access_level integer NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,idempotency_key),
  FOREIGN KEY(tenant_id,project_id,task_id,approval_ref) REFERENCES vnext.approval_request(tenant_id,project_id,task_id,approval_ref));

CREATE TABLE vnext.input_delivery(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  delivery_id text NOT NULL,input_request_id text NOT NULL,manifest_ref text NOT NULL,
  payload_json text NOT NULL,payload_digest text NOT NULL,access_level integer NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','delivered')),
  receiving_run_id text,delivered_at timestamptz,
  PRIMARY KEY(tenant_id,project_id,task_id,delivery_id),UNIQUE(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,input_request_id) REFERENCES vnext.input_request(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,manifest_ref) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,manifest_ref),
  FOREIGN KEY(tenant_id,project_id,task_id,receiving_run_id) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,agent_run_id),
  CHECK((status='delivered')=(receiving_run_id IS NOT NULL AND delivered_at IS NOT NULL)));

CREATE TABLE vnext.human_question(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  question_ref text NOT NULL,work_item_id text NOT NULL,manifest_ref text NOT NULL,
  question_text text NOT NULL,subject text NOT NULL,idempotency_key text NOT NULL,input_digest text NOT NULL,access_level integer NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,question_ref),UNIQUE(tenant_id,project_id,task_id,idempotency_key),
  FOREIGN KEY(tenant_id,project_id,task_id,work_item_id) REFERENCES vnext.work_item(tenant_id,project_id,task_id,work_item_id),
  FOREIGN KEY(tenant_id,project_id,task_id,manifest_ref) REFERENCES vnext.session_manifest(tenant_id,project_id,task_id,manifest_ref));
CREATE TABLE vnext.input_answer(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  input_request_id text NOT NULL,idempotency_key text NOT NULL,payload_digest text NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,input_request_id),
  FOREIGN KEY(tenant_id,project_id,task_id,input_request_id) REFERENCES vnext.input_request(tenant_id,project_id,task_id,input_request_id));

CREATE FUNCTION vnext.guard_session_object() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a vnext.artifact;
BEGIN
  SELECT * INTO a FROM vnext.artifact WHERE (tenant_id,project_id,task_id,entity_id,revision)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.artifact_id,NEW.artifact_revision);
  IF NOT FOUND OR a.agent_run_id IS DISTINCT FROM NEW.agent_run_id OR a.writer_subject IS DISTINCT FROM current_setting('wuji.subject',true)
    OR NEW.writer_token_id IS DISTINCT FROM current_setting('wuji.token_id',true) OR a.state<>'sealed' OR a.provenance<>'model_output'
    OR a.access_level>NEW.access_level OR current_setting('wuji.model_output',true) IS DISTINCT FROM 'true'
    OR NOT EXISTS(SELECT 1 FROM vnext.run_credential c WHERE (c.tenant_id,c.project_id,c.task_id,c.agent_run_id,c.token_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id,NEW.writer_token_id)
      AND c.subject=current_setting('wuji.subject',true) AND NOT c.revoked AND (c.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp())
  THEN RAISE EXCEPTION 'sealed bytes from the actual Run writer required' USING ERRCODE='42501'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER session_object_guard BEFORE INSERT ON vnext.session_object FOR EACH ROW EXECUTE FUNCTION vnext.guard_session_object();

CREATE FUNCTION vnext.guard_session_holder() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE w vnext.work_item;s vnext.session_manifest;p vnext.agent_run;n vnext.agent_run;
BEGIN
  SELECT * INTO w FROM vnext.work_item WHERE (tenant_id,project_id,task_id,work_item_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.work_item_id);
  SELECT * INTO s FROM vnext.session_manifest WHERE (tenant_id,project_id,task_id,manifest_ref)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.manifest_ref);
  SELECT * INTO p FROM vnext.agent_run WHERE (tenant_id,project_id,task_id,agent_run_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.previous_run_id);
  SELECT * INTO n FROM vnext.agent_run WHERE (tenant_id,project_id,task_id,agent_run_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id);
  IF current_setting('wuji.admit',true) IS DISTINCT FROM 'true' OR w.current_run_id IS DISTINCT FROM NEW.agent_run_id
    OR w.state<>'leased' OR w.desired_state<>'run' OR s.work_item_id IS DISTINCT FROM w.work_item_id
    OR s.session_id IS DISTINCT FROM w.session_id OR s.revision IS DISTINCT FROM w.session_revision
    OR s.session_lineage IS DISTINCT FROM NEW.session_lineage OR s.frontier_digest IS DISTINCT FROM NEW.frontier_digest
    OR p.work_item_id IS DISTINCT FROM w.work_item_id OR p.stop_kind IS NULL
    OR n.work_item_id IS DISTINCT FROM w.work_item_id OR n.run_epoch IS DISTINCT FROM w.run_epoch
  THEN RAISE EXCEPTION 'exact stopped Session holder transfer required' USING ERRCODE='42501'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER session_holder_guard BEFORE INSERT ON vnext.session_holder FOR EACH ROW EXECUTE FUNCTION vnext.guard_session_holder();

CREATE FUNCTION vnext.guard_approval_update() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF (to_jsonb(NEW)-'decision'-'decision_status'-'version'-'decided_by'-'decided_at'-'decision_reason'-'consumed_attempt_id'-'consumed_by_run')
      IS DISTINCT FROM (to_jsonb(OLD)-'decision'-'decision_status'-'version'-'decided_by'-'decided_at'-'decision_reason'-'consumed_attempt_id'-'consumed_by_run')
  THEN RAISE EXCEPTION 'approval source is immutable' USING ERRCODE='42501'; END IF;
  IF NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
  IF current_setting('wuji.control',true)='true' THEN
    IF OLD.decision_status<>'pending' OR NEW.decision_status<>'decided' OR NEW.version<>OLD.version+1
      OR NEW.decision IS NULL OR NEW.decided_by IS DISTINCT FROM current_setting('wuji.subject',true)
      OR NOT (OLD.qualifications_json::jsonb ? current_setting('wuji.subject',true))
      OR NEW.consumed_attempt_id IS NOT NULL OR NEW.consumed_by_run IS NOT NULL
    THEN RAISE EXCEPTION 'eligible pending approval decision required' USING ERRCODE='42501'; END IF;
  ELSIF current_setting('wuji.request_purpose',true)='tool_request' THEN
    IF OLD.decision_status<>'decided' OR OLD.decision<>'approve' OR NEW.decision_status<>'consumed'
      OR ROW(NEW.version,NEW.decision,NEW.decided_by,NEW.decided_at,NEW.decision_reason)
        IS DISTINCT FROM ROW(OLD.version,OLD.decision,OLD.decided_by,OLD.decided_at,OLD.decision_reason)
      OR NEW.consumed_attempt_id IS NULL OR NEW.consumed_by_run IS NULL
    THEN RAISE EXCEPTION 'one approved original operation required' USING ERRCODE='42501'; END IF;
  ELSE RAISE EXCEPTION 'approval authority required' USING ERRCODE='42501'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER approval_update BEFORE UPDATE ON vnext.approval_request FOR EACH ROW EXECUTE FUNCTION vnext.guard_approval_update();

CREATE FUNCTION vnext.check_approval_attempt() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE t text:=NEW.tenant_id;p text:=NEW.project_id;k text:=NEW.task_id;i text; a vnext.tool_attempt;c vnext.tool_call; approval vnext.approval_request; definition jsonb;
BEGIN
  IF TG_TABLE_NAME='approval_request' THEN
    SELECT * INTO approval FROM vnext.approval_request WHERE (tenant_id,project_id,task_id,approval_ref)=(t,p,k,NEW.approval_ref);
    IF approval.decision_status<>'consumed' THEN RETURN NEW; END IF;i:=approval.consumed_attempt_id;
  ELSE i:=NEW.tool_attempt_id; END IF;
  SELECT * INTO a FROM vnext.tool_attempt WHERE (tenant_id,project_id,task_id,tool_attempt_id)=(t,p,k,i);
  SELECT * INTO c FROM vnext.tool_call WHERE (tenant_id,project_id,task_id,tool_call_id)=(t,p,k,a.tool_call_id);
  SELECT document_json::jsonb INTO definition FROM vnext.tool_definition WHERE tenant_id=t AND ref=c.tool_definition_version;
  IF NOT COALESCE((definition->>'approval_required')::boolean,false) THEN RETURN NEW; END IF;
  SELECT * INTO approval FROM vnext.approval_request WHERE (tenant_id,project_id,task_id,consumed_attempt_id)=(t,p,k,i);
  IF NOT FOUND OR approval.decision_status<>'consumed' OR approval.decision<>'approve'
    OR approval.tool_call_id IS DISTINCT FROM c.tool_call_id OR approval.work_item_id IS DISTINCT FROM c.work_item_id
    OR approval.consumed_by_run IS DISTINCT FROM a.agent_run_id
    OR NOT EXISTS(SELECT 1 FROM vnext.outbox o WHERE (o.tenant_id,o.project_id,o.task_id)=(t,p,k)
      AND o.kind='tool.dispatch_requested' AND o.payload_json::jsonb->>'tool_call_id'=c.tool_call_id
      AND o.payload_json::jsonb->>'tool_attempt_id'=i)
  THEN RAISE EXCEPTION 'approval, original ToolCall, Attempt and Outbox must commit together' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER approval_attempt_commit AFTER INSERT OR UPDATE ON vnext.approval_request DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vnext.check_approval_attempt();
CREATE CONSTRAINT TRIGGER attempt_approval_commit AFTER INSERT ON vnext.tool_attempt DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vnext.check_approval_attempt();

CREATE OR REPLACE FUNCTION vnext.guard_input_revoke() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status AND NEW.status<>'revoked' THEN
    IF OLD.status<>'pending' OR NEW.status<>'resolved' OR current_setting('wuji.control',true) IS DISTINCT FROM 'true'
      OR NOT EXISTS(SELECT 1 FROM vnext.input_delivery d WHERE (d.tenant_id,d.project_id,d.task_id,d.input_request_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.input_request_id))
    THEN RAISE EXCEPTION 'P08 persisted decision required for resolution' USING ERRCODE='42501'; END IF;
  END IF;RETURN NEW;
END $$;

CREATE FUNCTION vnext.guard_input_delivery() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
  IF current_setting('wuji.request_purpose',true) IS DISTINCT FROM 'tool_request'
    OR OLD.status<>'pending' OR NEW.status<>'delivered' OR NEW.delivered_at IS NULL OR NEW.receiving_run_id IS NULL
    OR (to_jsonb(NEW)-'status'-'receiving_run_id'-'delivered_at') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'receiving_run_id'-'delivered_at')
    OR NOT EXISTS(SELECT 1 FROM vnext.session_holder h JOIN vnext.run_credential c USING(tenant_id,project_id,task_id,agent_run_id)
      WHERE (h.tenant_id,h.project_id,h.task_id,h.agent_run_id,h.manifest_ref)=(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.receiving_run_id,NEW.manifest_ref)
      AND c.subject=current_setting('wuji.subject',true) AND c.token_id=current_setting('wuji.token_id',true) AND NOT c.revoked)
  THEN RAISE EXCEPTION 'current fixed input delivery required' USING ERRCODE='42501'; END IF;RETURN NEW;
END $$;
CREATE TRIGGER input_delivery_update BEFORE UPDATE ON vnext.input_delivery FOR EACH ROW EXECUTE FUNCTION vnext.guard_input_delivery();

-- Preserve the exact P09 credential guard, changing only the expected lineage
-- expression to the already validated, immutable Session holder row for this Run.
-- Refuse migration if its known source seam has changed; SOL must then integrate
-- against the actual new definition rather than deleting a guard.
DO $$ DECLARE body text;old_expr text := $q$b->>'session_lineage' IS DISTINCT FROM 'run:'||a.agent_run_id$q$;
BEGIN
  body:=pg_get_functiondef('vnext.require_scheduler_identity(text,text,text,jsonb)'::regprocedure);
  IF strpos(body,old_expr)=0 THEN RAISE EXCEPTION 'P09 lineage guard changed; integrate explicitly'; END IF;
  body:=replace(body,old_expr,$q$b->>'session_lineage' IS DISTINCT FROM COALESCE((SELECT h.session_lineage FROM vnext.session_holder h WHERE h.tenant_id=t AND h.project_id=p AND h.task_id=k AND h.agent_run_id=a.agent_run_id),'run:'||a.agent_run_id)$q$);
  EXECUTE body;
END $$;

DO $$ DECLARE app name:=current_setting('wuji.p08_application_role'); name text; scope text; power text;
BEGIN
  FOREACH name IN ARRAY ARRAY['session_object','session_holder','input_source','approval_request','approval_command','input_delivery','human_question','input_answer'] LOOP
    scope:='vnext.in_scope(tenant_id,project_id,task_id'||CASE WHEN name IN ('session_holder','input_answer') THEN ')' ELSE ',access_level)' END;
    EXECUTE format('ALTER TABLE vnext.%I ENABLE ROW LEVEL SECURITY',name);
    EXECUTE format('CREATE POLICY scoped_read ON vnext.%I FOR SELECT USING(%s)',name,scope);
    EXECUTE format('GRANT SELECT ON vnext.%I TO %I',name,app);
    power:=CASE WHEN name='session_object' THEN 'current_setting(''wuji.model_output'',true)=''true'''
      WHEN name='session_holder' THEN 'current_setting(''wuji.admit'',true)=''true'''
      WHEN name IN ('input_source','approval_request') THEN 'current_setting(''wuji.observe'',true)=''true'''
      ELSE 'current_setting(''wuji.control'',true)=''true''' END;
    EXECUTE format('CREATE POLICY session_insert ON vnext.%I FOR INSERT WITH CHECK(%s AND %s)',name,scope,power);
    EXECUTE format('GRANT INSERT ON vnext.%I TO %I',name,app);
  END LOOP;
  ALTER TABLE vnext.session_capability ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_read ON vnext.session_capability FOR SELECT USING(tenant_id=current_setting('wuji.tenant',true));
  EXECUTE format('GRANT SELECT ON vnext.session_capability TO %I',app);
  CREATE POLICY approval_update ON vnext.approval_request FOR UPDATE
    USING(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND (current_setting('wuji.control',true)='true' OR current_setting('wuji.request_purpose',true)='tool_request'))
    WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level));
  EXECUTE format('GRANT UPDATE(decision,decision_status,version,decided_by,decided_at,decision_reason,consumed_attempt_id,consumed_by_run) ON vnext.approval_request TO %I',app);
  CREATE POLICY delivery_update ON vnext.input_delivery FOR UPDATE USING(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.request_purpose',true)='tool_request') WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level));
  EXECUTE format('GRANT UPDATE(status,receiving_run_id,delivered_at) ON vnext.input_delivery TO %I',app);
  CREATE POLICY session_publish ON vnext.session_manifest FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.observe',true)='true');
  CREATE POLICY input_intake ON vnext.input_request FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.observe',true)='true');
  EXECUTE format('GRANT INSERT ON vnext.session_manifest,vnext.input_request TO %I',app);
  CREATE POLICY session_publication ON vnext.publication FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.observe',true)='true' AND kind='session_manifest');
  CREATE POLICY session_pin ON vnext.publication_ref FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.observe',true)='true' AND EXISTS(SELECT 1 FROM vnext.publication p WHERE (p.tenant_id,p.project_id,p.task_id,p.publication_id)=(publication_ref.tenant_id,publication_ref.project_id,publication_ref.task_id,publication_ref.publication_id) AND p.kind='session_manifest'));
  -- Receiver may verify the current writer binding at Session publication. This
  -- exposes binding metadata only, grants no credential mutation or result power.
  CREATE POLICY session_receiver_binding ON vnext.run_credential FOR SELECT USING(
    vnext.in_scope(tenant_id,project_id,task_id) AND current_setting('wuji.observe',true)='true'
    AND EXISTS(SELECT 1 FROM vnext.agent_run ar JOIN vnext.scheduler_receiver rx USING(tenant_id,project_id,task_id,runtime_attempt,receiver_id)
      JOIN vnext.work_item wi USING(tenant_id,project_id,task_id,work_item_id)
      WHERE (ar.tenant_id,ar.project_id,ar.task_id,ar.agent_run_id)=(run_credential.tenant_id,run_credential.project_id,run_credential.task_id,run_credential.agent_run_id)
      AND rx.receiver_subject=current_setting('wuji.subject',true) AND rx.enabled
      AND wi.current_run_id=ar.agent_run_id AND wi.run_epoch=ar.run_epoch));
  FOREACH name IN ARRAY ARRAY['input_request','approval_request'] LOOP
    EXECUTE format('CREATE POLICY session_locator ON vnext.%I FOR SELECT USING(tenant_id=current_setting(''wuji.tenant'',true) AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE (a.tenant_id,a.project_id,a.task_id)=(%I.tenant_id,%I.project_id,%I.task_id) AND a.subject=current_setting(''wuji.subject'',true) AND a.can_read AND a.clearance>=%I.access_level))',name,name,name,name,name);
  END LOOP;
END $$;

REVOKE EXECUTE ON FUNCTION vnext.guard_session_object(),vnext.guard_session_holder(),vnext.guard_approval_update(),vnext.check_approval_attempt(),vnext.guard_input_delivery() FROM PUBLIC;
-- Immutable source/holder/object rows have no UPDATE/DELETE grants. Existing
-- session_immutable/publication_sealed and artifact GC pin/lease rules remain.
