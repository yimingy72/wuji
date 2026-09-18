-- A2 draft for A0 registration as vnext_0029_first_use_launch.
--
-- This file is intentionally not imported by the migration runner.  A0 owns
-- the append-only registration and parent-head check.  The launch table is a
-- progress ledger, not a second Task state machine: ControlService remains
-- the authority for activation/pause/cancel state.

CREATE TABLE vnext.task_launch_worker (
  tenant_id text NOT NULL,
  project_id text NOT NULL,
  subject text NOT NULL CHECK(length(subject) BETWEEN 1 AND 256),
  clearance integer NOT NULL DEFAULT 1 CHECK(clearance >= 0),
  enabled boolean NOT NULL DEFAULT true,
  PRIMARY KEY(tenant_id,project_id,subject),
  FOREIGN KEY(tenant_id,project_id) REFERENCES vnext.project(tenant_id,project_id)
);
REVOKE ALL ON vnext.task_launch_worker FROM PUBLIC;

CREATE TABLE vnext.task_launch (
  tenant_id text NOT NULL,
  project_id text NOT NULL,
  task_id text NOT NULL,
  operation_id text NOT NULL CHECK (length(operation_id) BETWEEN 1 AND 256),
  command_id text NOT NULL CHECK (length(command_id) BETWEEN 1 AND 256),
  input_digest text NOT NULL CHECK (input_digest ~ '^[a-f0-9]{64}$'),
  definition_digest text NOT NULL CHECK (definition_digest ~ '^[a-f0-9]{64}$'),
  profile_digest text NOT NULL CHECK (profile_digest ~ '^[a-f0-9]{64}$'),
  expected_control_version numeric NOT NULL
    CHECK (expected_control_version >= 1 AND expected_control_version = trunc(expected_control_version)),
  runtime_attempt numeric
    CHECK (runtime_attempt IS NULL OR (runtime_attempt >= 1 AND runtime_attempt = trunc(runtime_attempt))),
  execution_epoch numeric
    CHECK (execution_epoch IS NULL OR (execution_epoch >= 1 AND execution_epoch = trunc(execution_epoch))),
  phase text NOT NULL CHECK (phase IN ('prepare','activate','wire','capability','ready')),
  phase_status text NOT NULL CHECK (phase_status IN ('pending','running','reconciling','blocked','succeeded','cancelled','failed')),
  reason_code text CHECK (reason_code IS NULL OR reason_code ~ '^[a-z][a-z0-9_]{0,127}$'),
  allowed_actions_json text NOT NULL DEFAULT '[]'
    CHECK (jsonb_typeof(allowed_actions_json::jsonb) = 'array'),
  steps_json text NOT NULL DEFAULT '{}'
    CHECK (jsonb_typeof(steps_json::jsonb) = 'object'),
  request_json text NOT NULL CHECK (jsonb_typeof(request_json::jsonb) = 'object'),
  receipt_json text NOT NULL CHECK (jsonb_typeof(receipt_json::jsonb) = 'object'),
  lease_owner text,
  lease_token text,
  lease_expires_at timestamptz,
  revision numeric NOT NULL DEFAULT 1 CHECK (revision >= 1 AND revision = trunc(revision)),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id,project_id,task_id,operation_id),
  UNIQUE (tenant_id,project_id,task_id,command_id),
  FOREIGN KEY (tenant_id,project_id,task_id) REFERENCES vnext.task(tenant_id,project_id,task_id),
  CHECK ((phase = 'ready') = (phase_status = 'succeeded')),
  CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL))
);

ALTER TABLE vnext.task_launch ENABLE ROW LEVEL SECURITY;
CREATE POLICY task_launch_read ON vnext.task_launch FOR SELECT USING (
  tenant_id = current_setting('wuji.tenant',true)
  AND EXISTS (
    SELECT 1 FROM vnext.task_access a
    WHERE (a.tenant_id,a.project_id,a.task_id)=(task_launch.tenant_id,task_launch.project_id,task_launch.task_id)
      AND a.subject=current_setting('wuji.subject',true) AND a.can_read
  )
);
REVOKE ALL ON vnext.task_launch FROM PUBLIC;

CREATE UNIQUE INDEX one_active_task_launch
  ON vnext.task_launch(tenant_id,project_id,task_id)
  WHERE phase_status IN ('pending','running','reconciling','blocked','failed');

CREATE OR REPLACE FUNCTION vnext._task_view_json(taskrow vnext.task)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT jsonb_build_object(
    'task_id', taskrow.task_id,
    'tenant_id', taskrow.tenant_id,
    'project_id', taskrow.project_id,
    'version', taskrow.control_version::text,
    'name', taskrow.definition_json::jsonb->'task'->>'name',
    'scenario', taskrow.definition_json::jsonb->'task'->>'scenario',
    'desired_state', taskrow.desired_state,
    'observed_state', taskrow.observed_state,
    'goal_revision', '1',
    'execution_epoch', taskrow.execution_epoch::text,
    'activated_at', taskrow.activated_at,
    'close_trigger', taskrow.close_trigger,
    'result_outcome', taskrow.result_outcome,
    'allowed_actions', CASE
      WHEN NOT EXISTS(SELECT 1 FROM vnext.task_access a
        WHERE (a.tenant_id,a.project_id,a.task_id)=(taskrow.tenant_id,taskrow.project_id,taskrow.task_id)
          AND a.subject=current_setting('wuji.subject',true) AND a.can_read AND a.can_control)
        THEN '[]'::jsonb
      WHEN taskrow.observed_state='closed' OR taskrow.desired_state IN ('cancel','finish') THEN '[]'::jsonb
      WHEN taskrow.activated_at IS NULL THEN jsonb_build_array('start','cancel')
      WHEN taskrow.desired_state='run' THEN jsonb_build_array('pause','cancel','finish')
      ELSE jsonb_build_array('resume','cancel')
    END
  )
$$;

CREATE OR REPLACE FUNCTION vnext.list_tasks(project_key text, limit_count integer, cursor_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb; tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true);
BEGIN
  IF project_key IS NULL OR length(project_key)<1 OR limit_count NOT BETWEEN 1 AND 100 THEN
    RAISE EXCEPTION 'invalid task list input' USING ERRCODE='22023';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM vnext.task_access a WHERE a.tenant_id=tenant_value AND a.project_id=project_key AND a.subject=subject_value AND a.can_read) THEN
    RAISE EXCEPTION 'task project not found' USING ERRCODE='42501';
  END IF;
  WITH visible AS (
    SELECT t AS taskrow, row_number() OVER (ORDER BY t.task_id) AS n
    FROM vnext.task t JOIN vnext.task_access a USING(tenant_id,project_id,task_id)
    WHERE t.tenant_id=tenant_value AND t.project_id=project_key AND a.subject=subject_value AND a.can_read
      AND (cursor_key IS NULL OR t.task_id>cursor_key)
    ORDER BY t.task_id LIMIT limit_count+1
  ), page AS (SELECT * FROM visible WHERE n<=limit_count)
  SELECT jsonb_build_object(
    'items', COALESCE((SELECT jsonb_agg(vnext._task_view_json(page.taskrow) ORDER BY (page.taskrow).task_id) FROM page),'[]'::jsonb),
    'next_cursor', CASE WHEN EXISTS(SELECT 1 FROM visible WHERE n=limit_count+1)
      THEN (SELECT (taskrow).task_id FROM page ORDER BY n DESC LIMIT 1) ELSE NULL END
  ) INTO result;
  RETURN result::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.read_task_launch(task_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true); t vnext.task; l vnext.task_launch; result jsonb;
BEGIN
  SELECT taskrow.* INTO t FROM vnext.task taskrow JOIN vnext.task_access a USING(tenant_id,project_id,task_id)
    WHERE taskrow.tenant_id=tenant_value AND taskrow.task_id=task_key AND a.subject=subject_value AND a.can_read LIMIT 1;
  IF NOT FOUND THEN RAISE EXCEPTION 'task not found' USING ERRCODE='42501'; END IF;
  SELECT launch.* INTO l FROM vnext.task_launch launch WHERE (launch.tenant_id,launch.project_id,launch.task_id)=(t.tenant_id,t.project_id,t.task_id) ORDER BY launch.created_at DESC LIMIT 1;
  result:=jsonb_build_object(
    'operation_id', CASE WHEN l.operation_id IS NULL THEN NULL ELSE l.operation_id END,
    'command_id', CASE WHEN l.command_id IS NULL THEN NULL ELSE l.command_id END,
    'task_id', t.task_id,
    'definition_digest', t.definition_digest,
    'profile_digest', CASE WHEN l.profile_digest IS NULL THEN NULL ELSE l.profile_digest END,
    'runtime_attempt', CASE WHEN l.runtime_attempt IS NULL THEN NULL ELSE l.runtime_attempt::text END,
    'execution_epoch', CASE WHEN l.execution_epoch IS NULL THEN NULL ELSE l.execution_epoch::text END,
    'phase', COALESCE(l.phase,'not_requested'),
    'phase_status', COALESCE(l.phase_status,'not_requested'),
    'reason_code', l.reason_code,
    'allowed_actions', CASE WHEN l.operation_id IS NULL THEN (vnext._task_view_json(t)->'allowed_actions') ELSE l.allowed_actions_json::jsonb END,
    'observed_at', COALESCE(l.updated_at,clock_timestamp())
  );
  RETURN result::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.task_options(project_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true); result jsonb; missing jsonb:='[]'::jsonb; model_list jsonb; runtime_list jsonb;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM vnext.task_access a WHERE a.tenant_id=tenant_value AND a.project_id=project_key AND a.subject=subject_value AND a.can_read AND a.can_control) THEN
    RAISE EXCEPTION 'task options not found' USING ERRCODE='42501';
  END IF;
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'ref',p.ref,'name',COALESCE(p.document_json::jsonb->>'name',p.ref),'revision',p.revision::text,
      'digest',encode(sha256(convert_to(p.document_json,'UTF8')),'hex'),
      'capabilities',CASE WHEN jsonb_typeof(p.document_json::jsonb->'capabilities')='array' THEN p.document_json::jsonb->'capabilities'
        WHEN p.document_json::jsonb->>'protocol' IS NOT NULL THEN jsonb_build_array(p.document_json::jsonb->>'protocol') ELSE '[]'::jsonb END,
      'real_model_allowed',CASE WHEN jsonb_typeof(p.document_json::jsonb->'real_model_allowed')='boolean' THEN (p.document_json::jsonb->>'real_model_allowed')::boolean ELSE false END
    ) ORDER BY p.ref,p.revision DESC),'[]'::jsonb)
    INTO model_list FROM vnext.published_profile p WHERE p.tenant_id=tenant_value AND p.kind='model' AND NOT p.revoked;
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'ref',p.ref,'name',COALESCE(p.document_json::jsonb->>'name',p.ref),'revision',p.revision::text,
      'digest',encode(sha256(convert_to(p.document_json,'UTF8')),'hex'),
      'capabilities',CASE WHEN jsonb_typeof(p.document_json::jsonb->'capabilities')='array' THEN p.document_json::jsonb->'capabilities'
        WHEN jsonb_typeof(p.document_json::jsonb->'allowed_tool_refs')='array' THEN p.document_json::jsonb->'allowed_tool_refs' ELSE '[]'::jsonb END,
      'real_model_allowed',CASE WHEN jsonb_typeof(p.document_json::jsonb->'real_model_allowed')='boolean' THEN (p.document_json::jsonb->>'real_model_allowed')::boolean ELSE false END
    ) ORDER BY p.ref,p.revision DESC),'[]'::jsonb)
    INTO runtime_list FROM vnext.published_profile p WHERE p.tenant_id=tenant_value AND p.kind='runtime' AND NOT p.revoked;
  IF jsonb_array_length(model_list)=0 THEN missing:=missing||jsonb_build_array(jsonb_build_object('id','model_profile','layer','profile','status','fail','reason_code','model_profile_unavailable','observed_at',clock_timestamp(),'evidence_ref',NULL,'remediation_owner','application','message','No published model profile is available.')); END IF;
  IF jsonb_array_length(runtime_list)=0 THEN missing:=missing||jsonb_build_array(jsonb_build_object('id','runtime_profile','layer','profile','status','fail','reason_code','runtime_profile_unavailable','observed_at',clock_timestamp(),'evidence_ref',NULL,'remediation_owner','application','message','No published runtime profile is available.')); END IF;
  result:=jsonb_build_object('project_id',project_key,'model_profiles',model_list,'runtime_profiles',runtime_list,'missing',missing);
  RETURN result::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.task_readiness(task_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true); t vnext.task; definition jsonb; model_ok boolean; runtime_ok boolean; checks jsonb; result jsonb; at timestamptz:=clock_timestamp();
BEGIN
  SELECT taskrow.* INTO t FROM vnext.task taskrow JOIN vnext.task_access a USING(tenant_id,project_id,task_id)
    WHERE taskrow.tenant_id=tenant_value AND taskrow.task_id=task_key AND a.subject=subject_value AND a.can_read LIMIT 1;
  IF NOT FOUND THEN RAISE EXCEPTION 'task not found' USING ERRCODE='42501'; END IF;
  definition:=t.definition_json::jsonb;
  model_ok:=EXISTS(SELECT 1 FROM vnext.published_profile p WHERE p.tenant_id=t.tenant_id AND p.kind='model' AND p.ref=definition->'task'->>'model_profile_ref' AND NOT p.revoked);
  runtime_ok:=EXISTS(SELECT 1 FROM vnext.published_profile p WHERE p.tenant_id=t.tenant_id AND p.kind='runtime' AND p.ref=definition->'task'->>'runtime_profile_ref' AND NOT p.revoked AND p.lock_digest=definition->>'lock_digest');
  checks:=jsonb_build_array(
    jsonb_build_object('id','identity','layer','identity','status','pass','reason_code','identity_authorized','observed_at',at,'evidence_ref',NULL,'remediation_owner','application','message','Current identity can read this Task.'),
    jsonb_build_object('id','definition','layer','profile','status',CASE WHEN t.definition_digest IS NOT NULL THEN 'pass' ELSE 'fail' END,'reason_code',CASE WHEN t.definition_digest IS NOT NULL THEN 'definition_frozen' ELSE 'definition_missing' END,'observed_at',at,'evidence_ref',NULL,'remediation_owner','application','message','The Task definition is frozen for launch.'),
    jsonb_build_object('id','budget','layer','budget','status',CASE WHEN (definition->'task'->'budget'->>'amount') IS NOT NULL THEN 'pass' ELSE 'fail' END,'reason_code',CASE WHEN (definition->'task'->'budget'->>'amount') IS NOT NULL THEN 'budget_registered' ELSE 'budget_missing' END,'observed_at',at,'evidence_ref',NULL,'remediation_owner','user','message','The Task carries a registered budget.'),
    jsonb_build_object('id','model_profile','layer','model','status',CASE WHEN model_ok THEN 'pass' ELSE 'fail' END,'reason_code',CASE WHEN model_ok THEN 'model_profile_published' ELSE 'model_profile_unavailable' END,'observed_at',at,'evidence_ref',NULL,'remediation_owner','gateway','message','Published model profile status; no model request was made.'),
    jsonb_build_object('id','runtime_profile','layer','runtime','status',CASE WHEN runtime_ok THEN 'pass' ELSE 'fail' END,'reason_code',CASE WHEN runtime_ok THEN 'runtime_profile_published' ELSE 'runtime_profile_unavailable' END,'observed_at',at,'evidence_ref',NULL,'remediation_owner','infrastructure','message','Published runtime and lock status; no resource was deployed.'),
    jsonb_build_object('id','target','layer','target','status','unknown','reason_code','target_not_probed','observed_at',at,'evidence_ref',NULL,'remediation_owner','user','message','Target reachability is not probed by readiness.'),
    jsonb_build_object('id','material','layer','material','status','not_applicable','reason_code','material_not_required','observed_at',at,'evidence_ref',NULL,'remediation_owner','application','message','No material probe is performed by readiness.')
  );
  checks:=checks||jsonb_build_array(jsonb_build_object(
    'id','scope','layer','target','status',CASE WHEN (definition->'task'->>'authorization_expires_at')::timestamptz>at THEN 'pass' ELSE 'fail' END,
    'reason_code',CASE WHEN (definition->'task'->>'authorization_expires_at')::timestamptz>at THEN 'scope_current' ELSE 'scope_expired' END,
    'observed_at',at,'evidence_ref',NULL,'remediation_owner','user','message','Authorization deadline only; target connectivity remains untested.'));
  result:=jsonb_build_object('task_id',t.task_id,'definition_digest',t.definition_digest,'observed_at',at,'can_request_start',
    model_ok AND runtime_ok AND t.definition_digest IS NOT NULL AND t.observed_state='ready' AND t.desired_state='pause'
    AND (definition->'task'->>'authorization_expires_at')::timestamptz>at
    AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE (a.tenant_id,a.project_id,a.task_id)=(t.tenant_id,t.project_id,t.task_id) AND a.subject=subject_value AND a.can_control),
    'checks',checks);
  RETURN result::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.accept_task_launch(project_key text, task_key text, operation_key text, expected_version text, input_digest_value text, definition_digest_value text, profile_digest_value text, request_doc jsonb, receipt_doc jsonb)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true); t vnext.task; old vnext.task_launch;
BEGIN
  -- Authorization is intentionally before idempotency replay.  A revoked
  -- subject must not learn the old receipt for a formerly visible operation.
  SELECT taskrow.* INTO t FROM vnext.task taskrow JOIN vnext.task_access a USING(tenant_id,project_id,task_id)
    WHERE taskrow.tenant_id=tenant_value AND taskrow.project_id=project_key AND taskrow.task_id=task_key AND a.subject=subject_value AND a.can_read AND a.can_control FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'task start forbidden' USING ERRCODE='42501'; END IF;
  SELECT * INTO old FROM vnext.task_launch WHERE (tenant_id,project_id,task_id,operation_id)=(tenant_value,project_key,task_key,operation_key) FOR UPDATE;
  IF FOUND THEN
    IF old.input_digest<>input_digest_value THEN RAISE EXCEPTION 'launch key reused with different input' USING ERRCODE='23505'; END IF;
    RETURN old.receipt_json;
  END IF;
  IF t.definition_digest<>definition_digest_value OR t.control_version::text<>expected_version THEN
    RAISE EXCEPTION 'stale Task start' USING ERRCODE='40001';
  END IF;
  IF t.activated_at IS NOT NULL OR t.observed_state='closed' OR t.desired_state IN ('cancel','finish') THEN
    RAISE EXCEPTION 'Task cannot start' USING ERRCODE='55000';
  END IF;
  IF EXISTS (SELECT 1 FROM vnext.task_launch active WHERE (active.tenant_id,active.project_id,active.task_id)=(tenant_value,project_key,task_key) AND active.phase_status IN ('pending','running','reconciling','blocked','failed')) THEN
    RAISE EXCEPTION 'another launch is active' USING ERRCODE='55000';
  END IF;
  INSERT INTO vnext.task_launch(tenant_id,project_id,task_id,operation_id,command_id,input_digest,definition_digest,profile_digest,expected_control_version,runtime_attempt,execution_epoch,phase,phase_status,request_json,receipt_json)
    VALUES(tenant_value,project_key,task_key,operation_key,operation_key,input_digest_value,definition_digest_value,profile_digest_value,expected_version::numeric,t.runtime_attempt,t.execution_epoch,'prepare','pending',request_doc::text,receipt_doc::text);
  RETURN receipt_doc::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.claim_task_launch(worker_key text, lease_seconds integer, subject_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l vnext.task_launch; token text:=md5(random()::text||clock_timestamp()::text||worker_key); result jsonb;
BEGIN
  IF worker_key IS NULL OR length(worker_key)<1 OR subject_key IS DISTINCT FROM current_setting('wuji.subject',true) OR lease_seconds NOT BETWEEN 1 AND 300 THEN
    RAISE EXCEPTION 'invalid launch lease' USING ERRCODE='22023';
  END IF;
  SELECT launch.* INTO l FROM vnext.task_launch launch
    JOIN vnext.task_launch_worker a USING(tenant_id,project_id)
    WHERE launch.tenant_id=current_setting('wuji.tenant',true) AND a.subject=subject_key AND a.enabled
      AND launch.phase_status IN ('pending','running','reconciling')
      AND (launch.lease_expires_at IS NULL OR launch.lease_expires_at<=clock_timestamp() OR launch.lease_owner=worker_key)
    ORDER BY launch.created_at,launch.operation_id LIMIT 1 FOR UPDATE SKIP LOCKED;
  IF NOT FOUND THEN RETURN NULL; END IF;
  INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_control,can_admit,clearance)
    SELECT l.tenant_id,l.project_id,l.task_id,a.subject,true,true,true,a.clearance
    FROM vnext.task_launch_worker a WHERE (a.tenant_id,a.project_id,a.subject)=(l.tenant_id,l.project_id,subject_key) AND a.enabled
    ON CONFLICT(tenant_id,project_id,task_id,subject) DO NOTHING;
  UPDATE vnext.task_launch SET lease_owner=worker_key,lease_token=token,lease_expires_at=clock_timestamp()+make_interval(secs=>lease_seconds),revision=revision+1,updated_at=clock_timestamp()
    WHERE (tenant_id,project_id,task_id,operation_id)=(l.tenant_id,l.project_id,l.task_id,l.operation_id);
  SELECT jsonb_build_object(
    'operation_id',l.operation_id,'command_id',l.command_id,'task_id',l.task_id,'definition_digest',l.definition_digest,'profile_digest',l.profile_digest,
    'expected_control_version',l.expected_control_version::text,'runtime_attempt',l.runtime_attempt::text,'execution_epoch',l.execution_epoch::text,
    'phase',l.phase,'phase_status',l.phase_status,'reason_code',l.reason_code,'allowed_actions',l.allowed_actions_json::jsonb,'steps',l.steps_json::jsonb,
    'lease_token',token,'observed_at',clock_timestamp()
  ) INTO result;
  RETURN result::text;
END $$;

CREATE OR REPLACE FUNCTION vnext.renew_task_launch_lease(operation_key text, token_key text, lease_seconds integer)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF lease_seconds NOT BETWEEN 1 AND 300 THEN RETURN false; END IF;
  UPDATE vnext.task_launch SET lease_expires_at=clock_timestamp()+make_interval(secs=>lease_seconds),updated_at=clock_timestamp(),revision=revision+1
    WHERE tenant_id=current_setting('wuji.tenant',true) AND operation_id=operation_key AND lease_token=token_key AND lease_expires_at>clock_timestamp()
      AND EXISTS(SELECT 1 FROM vnext.task_launch_worker w WHERE (w.tenant_id,w.project_id)=(task_launch.tenant_id,task_launch.project_id) AND w.subject=current_setting('wuji.subject',true) AND w.enabled);
  RETURN FOUND;
END $$;

CREATE OR REPLACE FUNCTION vnext.record_task_launch_step(operation_key text, token_key text, phase_key text, status_key text, patch jsonb)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l vnext.task_launch; step jsonb; next_phase text; next_status text; result jsonb; lease_seconds integer:=COALESCE((patch->>'lease_seconds')::integer,30);
BEGIN
  SELECT * INTO l FROM vnext.task_launch WHERE tenant_id=current_setting('wuji.tenant',true) AND operation_id=operation_key AND lease_token=token_key AND lease_expires_at>clock_timestamp()
    AND EXISTS(SELECT 1 FROM vnext.task_launch_worker w WHERE (w.tenant_id,w.project_id)=(task_launch.tenant_id,task_launch.project_id) AND w.subject=current_setting('wuji.subject',true) AND w.enabled) FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF phase_key IS DISTINCT FROM l.phase OR jsonb_typeof(patch)<>'object' OR octet_length(patch::text)>65536 THEN
    RAISE EXCEPTION 'invalid launch phase update' USING ERRCODE='22023';
  END IF;
  step:=COALESCE(l.steps_json::jsonb->phase_key,'{}'::jsonb)||patch||jsonb_build_object('phase_status',status_key,'external_ref',COALESCE(patch->>'external_ref',operation_key));
  next_phase:=COALESCE(patch->>'next_phase',phase_key);
  next_status:=CASE WHEN status_key='succeeded' AND next_phase='ready' THEN 'succeeded' WHEN status_key='succeeded' THEN 'pending' ELSE status_key END;
  IF patch->>'definition_digest' IS NOT NULL AND patch->>'definition_digest'<>l.definition_digest THEN
    IF phase_key<>'prepare' OR status_key<>'succeeded' OR NOT EXISTS(
      SELECT 1 FROM vnext.task t WHERE (t.tenant_id,t.project_id,t.task_id)=(l.tenant_id,l.project_id,l.task_id)
        AND t.definition_digest=patch->>'definition_digest' AND t.activated_at IS NULL
    ) THEN RAISE EXCEPTION 'invalid prepared definition' USING ERRCODE='42501'; END IF;
  END IF;
  UPDATE vnext.task_launch SET phase=next_phase,phase_status=next_status,definition_digest=COALESCE(patch->>'definition_digest',definition_digest),reason_code=NULLIF(patch->>'reason_code',''),allowed_actions_json=COALESCE((patch->'allowed_actions')::text,allowed_actions_json),steps_json=(l.steps_json::jsonb||jsonb_build_object(phase_key,step))::text,
    runtime_attempt=COALESCE(NULLIF(patch->>'runtime_attempt','')::numeric,runtime_attempt),execution_epoch=COALESCE(NULLIF(patch->>'execution_epoch','')::numeric,execution_epoch),lease_expires_at=CASE WHEN (status_key='running' OR (status_key='succeeded' AND next_phase<>'ready')) THEN clock_timestamp()+make_interval(secs=>lease_seconds) ELSE NULL END,lease_owner=CASE WHEN (status_key='running' OR (status_key='succeeded' AND next_phase<>'ready')) THEN lease_owner ELSE NULL END,lease_token=CASE WHEN (status_key='running' OR (status_key='succeeded' AND next_phase<>'ready')) THEN lease_token ELSE NULL END,revision=revision+1,updated_at=clock_timestamp()
    WHERE (tenant_id,project_id,task_id,operation_id)=(l.tenant_id,l.project_id,l.task_id,l.operation_id)
    RETURNING * INTO l;
  SELECT jsonb_build_object('operation_id',l.operation_id,'command_id',l.command_id,'task_id',l.task_id,'definition_digest',l.definition_digest,'profile_digest',l.profile_digest,'expected_control_version',l.expected_control_version::text,'runtime_attempt',l.runtime_attempt::text,'execution_epoch',l.execution_epoch::text,'phase',l.phase,'phase_status',l.phase_status,'reason_code',l.reason_code,'allowed_actions',l.allowed_actions_json::jsonb,'steps',l.steps_json::jsonb,'lease_token',COALESCE(l.lease_token,token_key),'observed_at',l.updated_at) INTO result;
  RETURN result::text;
END $$;

-- A0 must grant EXECUTE on the functions above to the application/launch
-- service role, and register this file as vnext_0029_first_use_launch after
-- vnext_0028_p06_platform_run_settlement.  No owner DSN or credentials are
-- present in this draft.

-- API-10 hardening: 0019's create function replayed the idempotency row before
-- checking current visibility.  0029 replaces only the function body; it does
-- not rewrite the 0019 migration or existing receipts.
CREATE OR REPLACE FUNCTION vnext.create_task(project_key text, payload jsonb, start_points jsonb,
  create_key text, new_task text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  tenant_value text:=current_setting('wuji.tenant',true);
  subject_value text:=current_setting('wuji.subject',true);
  clearance_value integer;
  model_doc jsonb; runtime_doc jsonb; lock_value text;
  definition jsonb; request_digest text; receipt jsonb; saved vnext.task_create_command;
BEGIN
  IF tenant_value IS NULL OR tenant_value='' OR subject_value IS NULL OR subject_value='' THEN
    RAISE EXCEPTION 'authenticated tenant and subject required' USING ERRCODE='42501';
  END IF;
  IF project_key IS NULL OR project_key='' OR new_task IS NULL OR length(new_task) NOT BETWEEN 1 AND 256
    OR jsonb_typeof(payload)<>'object' OR jsonb_typeof(start_points)<>'array'
    OR jsonb_array_length(start_points)<1 OR create_key IS NULL OR length(create_key) NOT BETWEEN 1 AND 256 THEN
    RAISE EXCEPTION 'invalid task creation input' USING ERRCODE='22023';
  END IF;
  request_digest:=encode(sha256((payload::text||'|'||start_points::text||'|'||project_key)::bytea),'hex');
  SELECT * INTO saved FROM vnext.task_create_command command
    WHERE (command.tenant_id,command.subject,command.idempotency_key)=(tenant_value,subject_value,create_key) FOR UPDATE;
  IF NOT EXISTS(SELECT 1 FROM vnext.project project WHERE (project.tenant_id,project.project_id)=(tenant_value,project_key)) THEN
    RAISE EXCEPTION 'project not found' USING ERRCODE='42501';
  END IF;
  SELECT max(access.clearance) INTO clearance_value FROM vnext.task_access access
    JOIN vnext.task task USING(tenant_id,project_id,task_id)
    WHERE access.tenant_id=tenant_value AND access.project_id=project_key AND access.subject=subject_value AND access.can_control AND access.can_read;
  IF clearance_value IS NULL AND (saved.task_id IS NULL OR NOT EXISTS(
    SELECT 1 FROM vnext.task_access visible WHERE visible.tenant_id=tenant_value AND visible.task_id=saved.task_id AND visible.subject=subject_value AND visible.can_read)) THEN
    RAISE EXCEPTION 'project control permission required' USING ERRCODE='42501';
  END IF;
  IF saved.task_id IS NOT NULL THEN
    IF saved.request_digest<>request_digest THEN RAISE EXCEPTION 'idempotency key reused with different input' USING ERRCODE='23505'; END IF;
    RETURN saved.receipt_json;
  END IF;
  SELECT profile.document_json::jsonb INTO model_doc FROM vnext.published_profile profile
    WHERE profile.tenant_id=tenant_value AND profile.kind='model' AND profile.ref=payload->>'model_profile_ref' AND NOT profile.revoked ORDER BY profile.revision DESC LIMIT 1;
  IF model_doc IS NULL THEN RAISE EXCEPTION 'model profile not published' USING ERRCODE='23514'; END IF;
  SELECT profile.document_json::jsonb, profile.lock_digest INTO runtime_doc, lock_value FROM vnext.published_profile profile
    WHERE profile.tenant_id=tenant_value AND profile.kind='runtime' AND profile.ref=payload->>'runtime_profile_ref' AND NOT profile.revoked ORDER BY profile.revision DESC LIMIT 1;
  IF runtime_doc IS NULL THEN RAISE EXCEPTION 'runtime profile not published' USING ERRCODE='23514'; END IF;
  IF model_doc->>'ref' IS DISTINCT FROM payload->>'model_profile_ref' OR runtime_doc->>'ref' IS DISTINCT FROM payload->>'runtime_profile_ref' OR model_doc->>'published_at' IS NULL OR runtime_doc->>'published_at' IS NULL THEN
    RAISE EXCEPTION 'published profile document mismatch' USING ERRCODE='23514';
  END IF;
  definition:=jsonb_build_object('task',payload,'start_points',start_points,'model_profile',model_doc,'runtime_profile',runtime_doc,'lock_digest',lock_value);
  INSERT INTO vnext.task(tenant_id,project_id,task_id,definition_json,definition_digest)
    VALUES(tenant_value,project_key,new_task,definition::text,encode(sha256(definition::text::bytea),'hex'));
  INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_control,clearance)
    VALUES(tenant_value,project_key,new_task,subject_value,true,true,true,clearance_value);
  INSERT INTO vnext.task_assessment_policy(tenant_id,project_id,task_id,policy_version)
    VALUES(tenant_value,project_key,new_task,'assessment-policy-v1');
  receipt:=jsonb_build_object('task_id',new_task,'tenant_id',tenant_value,'project_id',project_key,'version','1','name',payload->>'name','scenario',payload->>'scenario','desired_state','pause','observed_state','ready','goal_revision','1','execution_epoch','1','allowed_actions',jsonb_build_array());
  INSERT INTO vnext.task_create_command(tenant_id,subject,idempotency_key,request_digest,task_id,receipt_json)
    VALUES(tenant_value,subject_value,create_key,request_digest,new_task,receipt::text);
  RETURN receipt::text;
EXCEPTION WHEN unique_violation THEN
  SELECT * INTO saved FROM vnext.task_create_command command WHERE (command.tenant_id,command.subject,command.idempotency_key)=(tenant_value,subject_value,create_key);
  IF saved.task_id IS NOT NULL AND saved.request_digest=request_digest THEN RETURN saved.receipt_json; END IF;
  RAISE;
END $$;
