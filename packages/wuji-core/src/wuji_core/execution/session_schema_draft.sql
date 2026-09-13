-- P08 UNNUMBERED DRAFT. Never run by the core author.
-- SOL/main integrates after the receiver-results migration, assigns the head,
-- and supplies SELECT set_config('wuji.p08_application_role', app_role, true).
-- This draft does not create a role, alter UoW, grant Worker control, or change
-- model_request/tool_request/model_settle/tool_settle into broader purposes.

ALTER TABLE vnext.session_manifest
  ADD manifest_ref text, ADD manifest_digest text, ADD frontier_digest text, ADD graph_digest text,
  ADD session_lineage text,
  ADD capability_ref text, ADD capability_digest text,
  ADD UNIQUE(tenant_id,project_id,task_id,manifest_ref),
  ADD CHECK ((manifest_ref IS NULL AND manifest_digest IS NULL AND frontier_digest IS NULL
      AND graph_digest IS NULL AND session_lineage IS NULL
      AND capability_ref IS NULL AND capability_digest IS NULL)
    OR (manifest_ref IS NOT NULL AND manifest_digest ~ '^[a-f0-9]{64}$'
      AND frontier_digest ~ '^[a-f0-9]{64}$' AND graph_digest ~ '^[a-f0-9]{64}$'
      AND length(session_lineage)>0
      AND length(capability_ref)>0 AND capability_digest ~ '^[a-f0-9]{64}$'));
ALTER TABLE vnext.input_request ADD access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0);
CREATE UNIQUE INDEX one_current_work_per_session ON vnext.work_item(tenant_id,project_id,task_id,session_id) WHERE session_id IS NOT NULL;

CREATE TABLE vnext.session_capability(
  tenant_id text NOT NULL REFERENCES vnext.tenant, ref text NOT NULL, profile_digest text NOT NULL,
  document_json text NOT NULL, digest text NOT NULL CHECK(digest ~ '^[a-f0-9]{64}$'), revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY(tenant_id,ref),UNIQUE(tenant_id,ref,digest));
CREATE INDEX session_capability_profiles ON vnext.session_capability(tenant_id,profile_digest) WHERE NOT revoked;

CREATE TABLE vnext.session_object(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  artifact_id text NOT NULL,artifact_revision numeric NOT NULL,agent_run_id text NOT NULL,writer_token_id text NOT NULL,
  role text NOT NULL CHECK(role IN ('dependency','archive','model_response','native_arguments','history_root','provider_root','memory_root')),
  refs_json text NOT NULL CHECK(jsonb_typeof(refs_json::jsonb)='array'),access_level integer NOT NULL,
  PRIMARY KEY(tenant_id,project_id,task_id,artifact_id,artifact_revision),
  FOREIGN KEY(tenant_id,project_id,task_id,artifact_id,artifact_revision) REFERENCES vnext.artifact(tenant_id,project_id,task_id,entity_id,revision),
  FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id) REFERENCES vnext.agent_run(tenant_id,project_id,task_id,agent_run_id));

CREATE TABLE vnext.session_stage(
  tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
  stage_id text NOT NULL,work_item_id text NOT NULL,session_id text NOT NULL,owner_run_id text NOT NULL,
  source_subject text NOT NULL,source_token_id text NOT NULL,source_clearance integer NOT NULL,
  history_id text NOT NULL,history_revision numeric NOT NULL,
  provider_id text NOT NULL,provider_revision numeric NOT NULL,
  memory_id text NOT NULL,memory_revision numeric NOT NULL,
  graph_digest text NOT NULL CHECK(graph_digest~'^[a-f0-9]{64}$'),
  graph_access_level integer NOT NULL CHECK(graph_access_level>=0),
  capability_ref text NOT NULL,capability_digest text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(tenant_id,project_id,task_id,stage_id),
  UNIQUE(tenant_id,project_id,task_id,history_id,history_revision,provider_id,provider_revision,memory_id,memory_revision),
  FOREIGN KEY(tenant_id,project_id,task_id,work_item_id,owner_run_id)
    REFERENCES vnext.agent_run(tenant_id,project_id,task_id,work_item_id,agent_run_id),
  FOREIGN KEY(tenant_id,capability_ref,capability_digest)
    REFERENCES vnext.session_capability(tenant_id,ref,digest));

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
  scope_json text NOT NULL CHECK(jsonb_typeof(scope_json::jsonb)='array'),
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

CREATE FUNCTION vnext.guard_input_intake_insert() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
  IF current_setting('wuji.observe',true) IS DISTINCT FROM 'true'
    OR NEW.status<>'pending' OR NEW.session_id IS NULL OR NEW.session_revision IS NULL
    OR jsonb_typeof(NEW.wait_ref_json::jsonb)<>'object'
    OR jsonb_typeof(NEW.source_receipt_json::jsonb)<>'object'
    OR NOT EXISTS(SELECT 1 FROM vnext.session_manifest sm WHERE
      (sm.tenant_id,sm.project_id,sm.task_id,sm.session_id,sm.revision,sm.work_item_id)=
      (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.session_id,NEW.session_revision,NEW.work_item_id)
      AND sm.access_level<=NEW.access_level)
  THEN RAISE EXCEPTION 'input intake must start pending from a published Session' USING ERRCODE='42501'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER input_intake_insert BEFORE INSERT ON vnext.input_request FOR EACH ROW EXECUTE FUNCTION vnext.guard_input_intake_insert();

CREATE FUNCTION vnext.guard_approval_intake_insert() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE callrow vnext.tool_call; inputrow vnext.input_request; manifest vnext.session_manifest;
  toolrow vnext.tool_definition; capability vnext.session_capability; taskrow vnext.task;
  native_args jsonb;
BEGIN
  IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
  IF current_setting('wuji.observe',true) IS DISTINCT FROM 'true'
    OR NEW.version<>1 OR NEW.decision_status<>'pending' OR NEW.decision IS NOT NULL
    OR NEW.decided_by IS NOT NULL OR NEW.decided_at IS NOT NULL OR NEW.decision_reason IS NOT NULL
    OR NEW.consumed_attempt_id IS NOT NULL OR NEW.consumed_by_run IS NOT NULL
    OR jsonb_typeof(NEW.content_json::jsonb)<>'object'
    OR jsonb_typeof(NEW.binding_json::jsonb)<>'object'
    OR jsonb_typeof(NEW.qualifications_json::jsonb)<>'array'
    OR jsonb_array_length(NEW.qualifications_json::jsonb)=0
  THEN RAISE EXCEPTION 'approval intake must start pending without a decision' USING ERRCODE='42501'; END IF;
  SELECT * INTO inputrow FROM vnext.input_request WHERE
    (tenant_id,project_id,task_id,input_request_id,work_item_id,session_id,session_revision,status)=
    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.input_request_id,NEW.work_item_id,
     NEW.session_id,NEW.session_revision,'pending');
  SELECT * INTO manifest FROM vnext.session_manifest WHERE
    (tenant_id,project_id,task_id,session_id,revision,work_item_id,manifest_ref)=
    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.session_id,NEW.session_revision,
     NEW.work_item_id,NEW.manifest_ref);
  SELECT * INTO callrow FROM vnext.tool_call WHERE
    (tenant_id,project_id,task_id,tool_call_id,work_item_id,status)=
    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id,NEW.work_item_id,'pending_approval');
  SELECT * INTO toolrow FROM vnext.tool_definition WHERE
    tenant_id=NEW.tenant_id AND ref=callrow.tool_definition_version AND NOT revoked;
  SELECT * INTO taskrow FROM vnext.task WHERE
    (tenant_id,project_id,task_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id);
  SELECT * INTO capability FROM vnext.session_capability WHERE
    tenant_id=NEW.tenant_id AND ref=manifest.capability_ref
    AND digest=manifest.capability_digest AND profile_digest=NEW.profile_digest AND NOT revoked
    AND document_json::jsonb->>'profile_digest'=NEW.profile_digest
    AND document_json::jsonb->'approver_subjects'=NEW.qualifications_json::jsonb;
  native_args:=CASE jsonb_typeof(NEW.content_json::jsonb->'function_call'->'arguments')
    WHEN 'string' THEN (NEW.content_json::jsonb->'function_call'->>'arguments')::jsonb
    ELSE NEW.content_json::jsonb->'function_call'->'arguments' END;
  IF inputrow IS NULL OR manifest IS NULL OR callrow IS NULL OR toolrow IS NULL
    OR capability IS NULL OR taskrow IS NULL OR callrow.latest_attempt_id IS NOT NULL
    OR NOT (manifest.manifest_json::jsonb->'pending_operation_refs' ? NEW.tool_call_id)
    OR callrow.session_lineage IS DISTINCT FROM manifest.session_lineage
    OR NEW.binding_json::jsonb->>'tool_call_id' IS DISTINCT FROM NEW.tool_call_id
    OR NEW.binding_json::jsonb->>'provider_call_id' IS DISTINCT FROM callrow.provider_call_id
    OR NEW.binding_json::jsonb->>'message_id' IS DISTINCT FROM callrow.message_id
    OR NEW.binding_json::jsonb->>'tool_definition_ref' IS DISTINCT FROM callrow.tool_definition_version
    OR NEW.binding_json::jsonb->>'arguments_digest' IS DISTINCT FROM NEW.parameters_digest
    OR NEW.content_json::jsonb->>'id' IS DISTINCT FROM NEW.binding_json::jsonb->>'sdk_approval_id'
    OR NEW.content_json::jsonb->'function_call'->>'id' IS DISTINCT FROM NEW.binding_json::jsonb->>'sdk_content_id'
    OR NEW.content_json::jsonb->'function_call'->>'call_id' IS DISTINCT FROM callrow.provider_call_id
    OR native_args IS DISTINCT FROM callrow.request_json::jsonb->'arguments'
    OR NEW.tool_digest IS DISTINCT FROM encode(sha256(convert_to(toolrow.document_json,'UTF8')),'hex')
    OR NEW.scope_digest IS DISTINCT FROM encode(sha256(convert_to(NEW.scope_json,'UTF8')),'hex')
    OR NEW.scope_json::jsonb IS DISTINCT FROM taskrow.definition_json::jsonb->'task'->'authorization_scope'
  THEN RAISE EXCEPTION 'approval intake source differs from the published frontier' USING ERRCODE='42501'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER approval_intake_insert BEFORE INSERT ON vnext.approval_request FOR EACH ROW EXECUTE FUNCTION vnext.guard_approval_intake_insert();

CREATE FUNCTION vnext.check_approval_intake_source() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT EXISTS(SELECT 1 FROM vnext.input_source src WHERE
    (src.tenant_id,src.project_id,src.task_id,src.input_request_id,src.manifest_ref)=
    (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.input_request_id,NEW.manifest_ref)
    AND src.receipt_json::jsonb->'approval_refs' ? NEW.approval_ref)
  THEN RAISE EXCEPTION 'approval intake requires its trusted source receipt' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER approval_intake_source AFTER INSERT ON vnext.approval_request
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vnext.check_approval_intake_source();

CREATE FUNCTION vnext.record_session_stage(
  t text,p text,k text,stage text,work text,session text,runid text,
  hid text,hrev numeric,pid text,prev numeric,mid text,mrev numeric,
  graph text,graph_level integer,capref text,capdigest text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE level integer; saved vnext.session_stage;
BEGIN
  SELECT clearance INTO level FROM vnext.task_access WHERE
    (tenant_id,project_id,task_id,subject)=(t,p,k,current_setting('wuji.subject',true))
    AND can_read;
  IF current_setting('wuji.request_purpose',true)<>'tool_request'
    OR NOT COALESCE(vnext.in_scope(t,p,k,graph_level),false)
    OR level IS NULL OR level<graph_level
    OR NOT EXISTS(SELECT 1 FROM vnext.run_credential credential
      JOIN vnext.run_writer writer USING(tenant_id,project_id,task_id,agent_run_id,subject)
      WHERE (credential.tenant_id,credential.project_id,credential.task_id,
             credential.agent_run_id,credential.subject,credential.token_id)=
        (t,p,k,runid,current_setting('wuji.subject',true),current_setting('wuji.token_id',true))
        AND NOT credential.revoked AND NOT writer.revoked
        AND (credential.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp())
    OR NOT EXISTS(SELECT 1 FROM vnext.session_capability capability WHERE
      (capability.tenant_id,capability.ref,capability.digest,capability.revoked)=
      (t,capref,capdigest,false))
    OR (SELECT count(*) FROM vnext.session_object object WHERE
      object.tenant_id=t AND object.project_id=p AND object.task_id=k
      AND object.agent_run_id=runid AND object.writer_token_id=current_setting('wuji.token_id',true)
      AND (object.artifact_id,object.artifact_revision,object.role) IN
        ((hid,hrev,'history_root'),(pid,prev,'provider_root'),(mid,mrev,'memory_root')))<>3
  THEN RAISE EXCEPTION 'complete current source Session stage required' USING ERRCODE='42501'; END IF;
  INSERT INTO vnext.session_stage(tenant_id,project_id,task_id,stage_id,work_item_id,session_id,
    owner_run_id,source_subject,source_token_id,source_clearance,history_id,history_revision,
    provider_id,provider_revision,memory_id,memory_revision,graph_digest,graph_access_level,
    capability_ref,capability_digest)
  VALUES(t,p,k,stage,work,session,runid,current_setting('wuji.subject',true),
    current_setting('wuji.token_id',true),level,hid,hrev,pid,prev,mid,mrev,graph,graph_level,capref,capdigest)
  ON CONFLICT DO NOTHING;
  SELECT * INTO saved FROM vnext.session_stage WHERE
    (tenant_id,project_id,task_id,stage_id)=(t,p,k,stage);
  IF saved IS NULL OR ROW(saved.work_item_id,saved.session_id,saved.owner_run_id,
      saved.source_subject,saved.source_token_id,saved.source_clearance,
      saved.history_id,saved.history_revision,saved.provider_id,saved.provider_revision,
      saved.memory_id,saved.memory_revision,saved.graph_digest,saved.graph_access_level,
      saved.capability_ref,saved.capability_digest)
    IS DISTINCT FROM ROW(work,session,runid,current_setting('wuji.subject',true),
      current_setting('wuji.token_id',true),level,hid,hrev,pid,prev,mid,mrev,
      graph,graph_level,capref,capdigest)
  THEN RAISE EXCEPTION 'Session stage identity conflict' USING ERRCODE='23514'; END IF;
  RETURN stage;
END $$;

CREATE FUNCTION vnext.check_session_stage_for_publish(
  t text,p text,k text,work text,session text,runid text,
  hid text,hrev numeric,pid text,prev numeric,mid text,mrev numeric,
  graph text,capref text,capdigest text)
RETURNS TABLE(stage_id text,source_clearance integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF current_setting('wuji.observe',true) IS DISTINCT FROM 'true'
    OR NOT COALESCE(vnext.in_scope(t,p,k),false) THEN
    RAISE EXCEPTION 'registered receiver publication required' USING ERRCODE='42501'; END IF;
  RETURN QUERY SELECT stage.stage_id,source_acl.clearance
  FROM vnext.session_stage stage
  JOIN vnext.task_access source_acl ON
    (source_acl.tenant_id,source_acl.project_id,source_acl.task_id,source_acl.subject)=
    (stage.tenant_id,stage.project_id,stage.task_id,stage.source_subject)
  JOIN vnext.run_credential credential ON
    (credential.tenant_id,credential.project_id,credential.task_id,credential.agent_run_id,
     credential.subject,credential.token_id)=
    (stage.tenant_id,stage.project_id,stage.task_id,stage.owner_run_id,
     stage.source_subject,stage.source_token_id)
  JOIN vnext.run_writer writer ON
    (writer.tenant_id,writer.project_id,writer.task_id,writer.agent_run_id,writer.subject)=
    (stage.tenant_id,stage.project_id,stage.task_id,stage.owner_run_id,stage.source_subject)
  JOIN vnext.agent_run run ON
    (run.tenant_id,run.project_id,run.task_id,run.work_item_id,run.agent_run_id)=
    (stage.tenant_id,stage.project_id,stage.task_id,stage.work_item_id,stage.owner_run_id)
  JOIN vnext.scheduler_receiver receiver ON
    (receiver.tenant_id,receiver.project_id,receiver.task_id,receiver.runtime_attempt,
     receiver.receiver_id,receiver.receiver_subject,receiver.pod_uid)=
    (run.tenant_id,run.project_id,run.task_id,run.runtime_attempt,
     run.receiver_id,current_setting('wuji.subject',true),run.pod_uid)
  WHERE (stage.tenant_id,stage.project_id,stage.task_id,stage.work_item_id,
         stage.session_id,stage.owner_run_id,stage.history_id,stage.history_revision,
         stage.provider_id,stage.provider_revision,stage.memory_id,stage.memory_revision,
         stage.graph_digest,stage.capability_ref,stage.capability_digest)=
    (t,p,k,work,session,runid,hid,hrev,pid,prev,mid,mrev,graph,capref,capdigest)
    AND receiver.enabled AND source_acl.can_read
    AND source_acl.clearance>=stage.graph_access_level
    AND NOT credential.revoked AND NOT writer.revoked
    AND (credential.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp();
  IF NOT FOUND THEN RAISE EXCEPTION 'current source Session stage required' USING ERRCODE='42501'; END IF;
END $$;

CREATE FUNCTION vnext.guard_session_manifest_insert() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
  PERFORM * FROM vnext.check_session_stage_for_publish(
    NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.work_item_id,NEW.session_id,NEW.owner_run_id,
    NEW.manifest_json::jsonb->'history_root'->>'id',
    (NEW.manifest_json::jsonb->'history_root'->>'version')::numeric,
    NEW.manifest_json::jsonb->'provider_state_ref'->>'id',
    (NEW.manifest_json::jsonb->'provider_state_ref'->>'version')::numeric,
    NEW.manifest_json::jsonb->'memory_manifest_ref'->>'id',
    (NEW.manifest_json::jsonb->'memory_manifest_ref'->>'version')::numeric,
    NEW.graph_digest,NEW.capability_ref,NEW.capability_digest);
  RETURN NEW;
END $$;
CREATE TRIGGER session_manifest_insert BEFORE INSERT ON vnext.session_manifest
  FOR EACH ROW EXECUTE FUNCTION vnext.guard_session_manifest_insert();

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

-- Extend the exact 0009 tool_request state machine with one P08 approval edge.
-- Every other transition remains byte-for-byte equivalent to the 0009 guard.
CREATE OR REPLACE FUNCTION vnext.guard_tool_call_purpose() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE purpose text := current_setting('wuji.request_purpose',true);
DECLARE approval_admit boolean := false; DECLARE attach boolean := false;
DECLARE dispatched boolean := false; DECLARE cancel_intent boolean := false;
DECLARE safe_retry boolean := false;
BEGIN
  IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
  IF purpose='tool_request' THEN
    approval_admit := OLD.status='pending_approval' AND OLD.latest_attempt_id IS NULL
      AND NEW.status='admitted' AND NEW.latest_attempt_id IS NULL
      AND (to_jsonb(NEW)-'status') IS NOT DISTINCT FROM (to_jsonb(OLD)-'status')
      AND EXISTS(
        SELECT 1 FROM vnext.approval_request ar
        JOIN vnext.session_manifest sm ON
          (sm.tenant_id,sm.project_id,sm.task_id,sm.session_id,sm.revision,sm.manifest_ref)=
          (ar.tenant_id,ar.project_id,ar.task_id,ar.session_id,ar.session_revision,ar.manifest_ref)
        JOIN vnext.session_holder h ON
          (h.tenant_id,h.project_id,h.task_id,h.manifest_ref,h.session_lineage)=
          (sm.tenant_id,sm.project_id,sm.task_id,sm.manifest_ref,sm.session_lineage)
        JOIN vnext.work_item w ON
          (w.tenant_id,w.project_id,w.task_id,w.work_item_id,w.current_run_id)=
          (h.tenant_id,h.project_id,h.task_id,h.work_item_id,h.agent_run_id)
        JOIN vnext.agent_run run ON
          (run.tenant_id,run.project_id,run.task_id,run.work_item_id,run.agent_run_id)=
          (w.tenant_id,w.project_id,w.task_id,w.work_item_id,w.current_run_id)
        JOIN vnext.run_credential credential ON
          (credential.tenant_id,credential.project_id,credential.task_id,credential.agent_run_id,
           credential.subject,credential.token_id)=
          (run.tenant_id,run.project_id,run.task_id,run.agent_run_id,
           current_setting('wuji.subject',true),current_setting('wuji.token_id',true))
        WHERE (ar.tenant_id,ar.project_id,ar.task_id,ar.tool_call_id)=
          (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id)
          AND ar.work_item_id=NEW.work_item_id
          AND ar.decision_status='decided' AND ar.decision='approve'
          AND ar.expires_at>clock_timestamp()
          AND h.session_lineage=NEW.session_lineage
          AND w.desired_state='run' AND run.execution_allowed
          AND run.run_epoch=w.run_epoch
          AND NOT credential.revoked
          AND (credential.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp()
          AND ar.binding_json::jsonb->>'tool_call_id'=NEW.tool_call_id
          AND ar.binding_json::jsonb->>'message_id'=NEW.message_id
          AND ar.binding_json::jsonb->>'provider_call_id'=NEW.provider_call_id
          AND ar.binding_json::jsonb->>'tool_definition_ref'=NEW.tool_definition_version
          AND ar.binding_json::jsonb->>'arguments_digest'=ar.parameters_digest
          AND ar.content_json::jsonb->>'id'=ar.binding_json::jsonb->>'sdk_approval_id'
          AND ar.content_json::jsonb->'function_call'->>'id'=ar.binding_json::jsonb->>'sdk_content_id'
          AND ar.content_json::jsonb->'function_call'->>'call_id'=NEW.provider_call_id
          AND CASE jsonb_typeof(ar.content_json::jsonb->'function_call'->'arguments')
            WHEN 'string' THEN (ar.content_json::jsonb->'function_call'->>'arguments')::jsonb
            ELSE ar.content_json::jsonb->'function_call'->'arguments' END
              = NEW.request_json::jsonb->'arguments'
          AND NEW.request_json::jsonb->>'session_lineage'=NEW.session_lineage
          AND NEW.request_json::jsonb->>'message_id'=NEW.message_id
          AND NEW.request_json::jsonb->>'provider_call_id'=NEW.provider_call_id
          AND NEW.request_json::jsonb->>'tool_definition_ref'=NEW.tool_definition_version
          AND NEW.request_json::jsonb->>'sdk_content_id'=ar.binding_json::jsonb->>'sdk_content_id'
          AND NEW.request_json::jsonb->>'sdk_approval_id'=ar.binding_json::jsonb->>'sdk_approval_id');
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
        JOIN vnext.tool_attempt p ON
          (p.tenant_id,p.project_id,p.task_id,p.tool_attempt_id)=
          (OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.latest_attempt_id)
        WHERE (n.tenant_id,n.project_id,n.task_id,n.tool_call_id,n.tool_attempt_id)=
              (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id,NEW.latest_attempt_id)
          AND n.status='admitted' AND n.retry_request_id IS NOT NULL
          AND p.status IN ('failed','cancelled')
          AND p.receipt_json::jsonb->>'status' IN ('not_started','exited'));
    IF NEW IS DISTINCT FROM OLD
       AND NOT (approval_admit OR attach OR dispatched OR cancel_intent OR safe_retry) THEN
      IF OLD.status='pending_approval' AND NEW.status='admitted' THEN
        RAISE EXCEPTION 'exact approved Session operation required' USING ERRCODE='42501';
      END IF;
      RAISE EXCEPTION 'tool request transition is not registered' USING ERRCODE='42501';
    END IF;
  ELSIF purpose<>'tool_settle' THEN
    RAISE EXCEPTION 'tool write purpose required' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
END $$;

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

CREATE FUNCTION vnext.settle_session_input_boundary(
  t text,p text,k text,runid text,inputid text,manifestref text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE saved text;
BEGIN
  IF current_setting('wuji.observe',true) IS DISTINCT FROM 'true'
    OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
    OR NOT COALESCE(vnext.in_scope(t,p,k),false)
    OR NOT EXISTS(
      SELECT 1
      FROM vnext.agent_run run
      JOIN vnext.work_item work ON
        (work.tenant_id,work.project_id,work.task_id,work.work_item_id,work.current_run_id,
         work.input_request_id)=
        (run.tenant_id,run.project_id,run.task_id,run.work_item_id,run.agent_run_id,inputid)
      JOIN vnext.scheduler_receiver receiver ON
        (receiver.tenant_id,receiver.project_id,receiver.task_id,receiver.runtime_attempt,
         receiver.receiver_id,receiver.pod_uid,receiver.receiver_subject)=
        (run.tenant_id,run.project_id,run.task_id,run.runtime_attempt,run.receiver_id,
         run.pod_uid,current_setting('wuji.subject',true))
      JOIN vnext.session_manifest manifest ON
        (manifest.tenant_id,manifest.project_id,manifest.task_id,manifest.owner_run_id,
         manifest.work_item_id,manifest.manifest_ref)=
        (run.tenant_id,run.project_id,run.task_id,run.agent_run_id,run.work_item_id,manifestref)
      JOIN vnext.input_request input ON
        (input.tenant_id,input.project_id,input.task_id,input.input_request_id,
         input.work_item_id,input.session_id,input.session_revision,input.status)=
        (manifest.tenant_id,manifest.project_id,manifest.task_id,inputid,
         manifest.work_item_id,manifest.session_id,manifest.revision,'pending')
      WHERE (run.tenant_id,run.project_id,run.task_id,run.agent_run_id)=
        (t,p,k,runid)
        AND receiver.enabled
        AND manifest.manifest_json::jsonb->>'recovery_class'='approval_boundary'
    )
    OR EXISTS(
      SELECT 1 FROM vnext.tool_attempt attempt
      WHERE (attempt.tenant_id,attempt.project_id,attempt.task_id,attempt.agent_run_id)=
        (t,p,k,runid)
        AND attempt.status IS NOT NULL
        AND attempt.status NOT IN ('complete','cancelled','failed')
    )
  THEN RAISE EXCEPTION 'settled published input boundary required' USING ERRCODE='42501'; END IF;
  INSERT INTO vnext.run_operation_settlement(
    tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json)
  VALUES(t,p,k,runid,'settled',jsonb_build_object(
    'producer','p08','basis','published_approval_boundary',
    'input_request_id',inputid,'manifest_ref',manifestref)::text)
  ON CONFLICT(tenant_id,project_id,task_id,agent_run_id) DO UPDATE
    SET status=EXCLUDED.status,source_receipt_json=EXCLUDED.source_receipt_json
    WHERE vnext.run_operation_settlement.status='settled'
  RETURNING status INTO saved;
  IF saved IS DISTINCT FROM 'settled' THEN
    RAISE EXCEPTION 'unsettled operation cannot become an input boundary' USING ERRCODE='42501'; END IF;
  UPDATE vnext.agent_run SET output_expectation='input_boundary'
    WHERE (tenant_id,project_id,task_id,agent_run_id)=(t,p,k,runid);
END $$;

CREATE FUNCTION vnext.mechanism_candidate_receiver_matches(
  t text,p text,k text,attempt numeric,receiverid text,pod text,
  workkind text,profile text,runid text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT COALESCE(vnext.in_scope(t,p,k),false)
    AND EXISTS(
      SELECT 1
      FROM vnext.scheduler_receiver receiver
      JOIN vnext.scheduler_identity_template template ON
        (template.tenant_id,template.project_id,template.task_id,template.template_ref)=
        (receiver.tenant_id,receiver.project_id,receiver.task_id,receiver.credential_template_ref)
      JOIN vnext.task_access receiver_acl ON
        (receiver_acl.tenant_id,receiver_acl.project_id,receiver_acl.task_id,receiver_acl.subject)=
        (receiver.tenant_id,receiver.project_id,receiver.task_id,receiver.receiver_subject)
      WHERE (receiver.tenant_id,receiver.project_id,receiver.task_id,
             receiver.runtime_attempt,receiver.receiver_id,receiver.pod_uid)=
        (t,p,k,attempt,receiverid,pod)
        AND receiver.enabled AND receiver.model_mode='synthetic' AND template.enabled
        AND receiver.harness_profiles_json::jsonb->workkind=profile::jsonb
        AND receiver_acl.can_read AND receiver_acl.can_observe AND receiver_acl.can_settle
        AND NOT receiver_acl.can_write AND NOT receiver_acl.can_model_output
    )
    AND (
      (
        current_setting('wuji.request_purpose',true) IN ('model_request','tool_request')
        AND length(runid)>0
        AND EXISTS(
          SELECT 1
          FROM vnext.agent_run run
          JOIN vnext.work_item work ON
            (work.tenant_id,work.project_id,work.task_id,work.work_item_id,work.current_run_id)=
            (run.tenant_id,run.project_id,run.task_id,run.work_item_id,run.agent_run_id)
          JOIN vnext.task_access source_acl ON
            (source_acl.tenant_id,source_acl.project_id,source_acl.task_id,source_acl.subject)=
            (run.tenant_id,run.project_id,run.task_id,current_setting('wuji.subject',true))
          JOIN vnext.run_credential credential ON
            (credential.tenant_id,credential.project_id,credential.task_id,
             credential.agent_run_id,credential.subject,credential.token_id)=
            (run.tenant_id,run.project_id,run.task_id,run.agent_run_id,
             current_setting('wuji.subject',true),current_setting('wuji.token_id',true))
          JOIN vnext.run_writer writer ON
            (writer.tenant_id,writer.project_id,writer.task_id,writer.agent_run_id,writer.subject)=
            (run.tenant_id,run.project_id,run.task_id,run.agent_run_id,
             current_setting('wuji.subject',true))
          WHERE (run.tenant_id,run.project_id,run.task_id,run.runtime_attempt,
                 run.receiver_id,run.pod_uid,run.agent_run_id)=
            (t,p,k,attempt,receiverid,pod,runid)
            AND source_acl.can_read AND NOT credential.revoked AND NOT writer.revoked
            AND (credential.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp()
            AND credential.document_json::jsonb->'purposes' ? current_setting('wuji.request_purpose',true)
        )
      )
      OR (
        COALESCE(current_setting('wuji.request_purpose',true),'')=''
        AND runid=''
        AND EXISTS(
          SELECT 1 FROM vnext.task_access caller
          WHERE (caller.tenant_id,caller.project_id,caller.task_id,caller.subject)=
            (t,p,k,current_setting('wuji.subject',true))
            AND caller.can_read
            AND (
              (current_setting('wuji.control',true)='true' AND caller.can_control)
              OR (current_setting('wuji.admit',true)='true' AND caller.can_admit)
              OR (current_setting('wuji.observe',true)='true' AND caller.can_observe
                AND caller.subject=(SELECT receiver_subject FROM vnext.scheduler_receiver
                  WHERE (tenant_id,project_id,task_id,runtime_attempt,receiver_id,pod_uid)=
                    (t,p,k,attempt,receiverid,pod)))
              OR (current_setting('wuji.control',true)<>'true'
                AND current_setting('wuji.admit',true)<>'true'
                AND current_setting('wuji.observe',true)<>'true')
            )
        )
      )
    )
$$;

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
  ALTER TABLE vnext.session_stage ENABLE ROW LEVEL SECURITY;
  REVOKE ALL ON vnext.session_stage FROM PUBLIC;
  EXECUTE format('GRANT EXECUTE ON FUNCTION vnext.record_session_stage(text,text,text,text,text,text,text,text,numeric,text,numeric,text,numeric,text,integer,text,text) TO %I',app);
  EXECUTE format('GRANT EXECUTE ON FUNCTION vnext.check_session_stage_for_publish(text,text,text,text,text,text,text,numeric,text,numeric,text,numeric,text,text,text) TO %I',app);
  EXECUTE format('GRANT EXECUTE ON FUNCTION vnext.mechanism_candidate_receiver_matches(text,text,text,numeric,text,text,text,text,text) TO %I',app);
  EXECUTE format('GRANT EXECUTE ON FUNCTION vnext.settle_session_input_boundary(text,text,text,text,text,text) TO %I',app);
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

REVOKE EXECUTE ON FUNCTION vnext.guard_input_intake_insert(),vnext.guard_approval_intake_insert(),
  vnext.check_approval_intake_source(),vnext.guard_session_object(),vnext.guard_session_holder(),
  vnext.guard_approval_update(),vnext.check_approval_attempt(),vnext.guard_input_delivery(),
  vnext.record_session_stage(text,text,text,text,text,text,text,text,numeric,text,numeric,text,numeric,text,integer,text,text),
  vnext.check_session_stage_for_publish(text,text,text,text,text,text,text,numeric,text,numeric,text,numeric,text,text,text),
  vnext.mechanism_candidate_receiver_matches(text,text,text,numeric,text,text,text,text,text),
  vnext.settle_session_input_boundary(text,text,text,text,text,text),
  vnext.guard_session_manifest_insert() FROM PUBLIC;
-- Immutable source/holder/object rows have no UPDATE/DELETE grants. Existing
-- session_immutable/publication_sealed and artifact GC pin/lease rules remain.
