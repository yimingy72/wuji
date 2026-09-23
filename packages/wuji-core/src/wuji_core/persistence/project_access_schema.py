"""Project-scoped Task creation authority for projects with no existing Task."""

from psycopg import sql

from wuji_core.persistence.runtime_capture_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0040_project_access"

_CREATE_TASK = """
CREATE OR REPLACE FUNCTION vnext.create_task(project_key text, payload jsonb, start_points jsonb,
  create_key text, new_task text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  tenant_value text:=current_setting('wuji.tenant',true);
  subject_value text:=current_setting('wuji.subject',true);
  clearance_value integer;
  model_doc jsonb; runtime_doc jsonb; lock_value text;
  criterion jsonb;
  definition jsonb; request_digest text; receipt jsonb; saved vnext.task_create_command;
BEGIN
  IF tenant_value IS NULL OR tenant_value='' OR subject_value IS NULL OR subject_value='' THEN
    RAISE EXCEPTION 'authenticated tenant and subject required' USING ERRCODE='42501';
  END IF;
  IF project_key IS NULL OR project_key='' OR new_task IS NULL OR length(new_task) NOT BETWEEN 1 AND 256
    OR jsonb_typeof(payload)<>'object' OR jsonb_typeof(start_points)<>'array'
    OR jsonb_array_length(start_points)<1
    OR create_key IS NULL OR length(create_key) NOT BETWEEN 1 AND 256 THEN
    RAISE EXCEPTION 'invalid task creation input' USING ERRCODE='22023';
  END IF;
  request_digest:=encode(sha256((payload::text||'|'||start_points::text||'|'||project_key)::bytea),'hex');
  SELECT * INTO saved FROM vnext.task_create_command command
    WHERE (command.tenant_id,command.subject,command.idempotency_key)
      =(tenant_value,subject_value,create_key) FOR UPDATE;
  IF FOUND THEN
    IF saved.request_digest<>request_digest THEN
      RAISE EXCEPTION 'idempotency key reused with different input' USING ERRCODE='23505';
    END IF;
    RETURN saved.receipt_json;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM vnext.project project WHERE
      (project.tenant_id,project.project_id)=(tenant_value,project_key)) THEN
    RAISE EXCEPTION 'project not found' USING ERRCODE='42501';
  END IF;
  SELECT access.clearance INTO clearance_value FROM vnext.project_access access
    WHERE access.tenant_id=tenant_value AND access.project_id=project_key
      AND access.subject=subject_value AND access.can_create;
  IF clearance_value IS NULL THEN
    SELECT max(access.clearance) INTO clearance_value FROM vnext.task_access access
      JOIN vnext.task task USING(tenant_id,project_id,task_id)
      WHERE access.tenant_id=tenant_value AND access.project_id=project_key
        AND access.subject=subject_value AND access.can_control AND access.can_read;
  END IF;
  IF clearance_value IS NULL THEN
    RAISE EXCEPTION 'project control permission required' USING ERRCODE='42501';
  END IF;
  SELECT profile.document_json::jsonb INTO model_doc FROM vnext.published_profile profile
    WHERE profile.tenant_id=tenant_value AND profile.kind='model'
      AND profile.ref=payload->>'model_profile_ref' AND NOT profile.revoked
    ORDER BY profile.revision DESC LIMIT 1;
  IF model_doc IS NULL THEN
    RAISE EXCEPTION 'model profile not published' USING ERRCODE='23514';
  END IF;
  SELECT profile.document_json::jsonb, profile.lock_digest INTO runtime_doc, lock_value
    FROM vnext.published_profile profile
    WHERE profile.tenant_id=tenant_value AND profile.kind='runtime'
      AND profile.ref=payload->>'runtime_profile_ref' AND NOT profile.revoked
    ORDER BY profile.revision DESC LIMIT 1;
  IF runtime_doc IS NULL THEN
    RAISE EXCEPTION 'runtime profile not published' USING ERRCODE='23514';
  END IF;
  IF model_doc->>'ref' IS DISTINCT FROM payload->>'model_profile_ref'
    OR runtime_doc->>'ref' IS DISTINCT FROM payload->>'runtime_profile_ref'
    OR model_doc->>'published_at' IS NULL OR runtime_doc->>'published_at' IS NULL THEN
    RAISE EXCEPTION 'published profile document mismatch' USING ERRCODE='23514';
  END IF;
  definition:=jsonb_build_object('task',payload,'start_points',start_points,
    'model_profile',model_doc,'runtime_profile',runtime_doc,'lock_digest',lock_value);
  INSERT INTO vnext.task(tenant_id,project_id,task_id,definition_json,definition_digest)
    VALUES(tenant_value,project_key,new_task,definition::text,
      encode(sha256(definition::text::bytea),'hex'));
  INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,
    can_control,clearance)
    VALUES(tenant_value,project_key,new_task,subject_value,true,true,true,clearance_value);
  INSERT INTO vnext.task_assessment_policy(tenant_id,project_id,task_id,policy_version)
    VALUES(tenant_value,project_key,new_task,'assessment-policy-v1');
  IF jsonb_typeof(payload#>'{goal,criteria}')<>'array'
     OR jsonb_array_length(payload#>'{goal,criteria}')<1 THEN
    RAISE EXCEPTION 'task goal criteria required' USING ERRCODE='22023';
  END IF;
  FOR criterion IN SELECT value FROM jsonb_array_elements(payload#>'{goal,criteria}') LOOP
    IF jsonb_typeof(criterion)<>'object'
       OR criterion->>'criterion_id' IS NULL
       OR length(criterion->>'criterion_id') NOT BETWEEN 1 AND 256 THEN
      RAISE EXCEPTION 'invalid task goal criterion' USING ERRCODE='22023';
    END IF;
    INSERT INTO vnext.goal_criterion(
      tenant_id,project_id,task_id,criterion_id,revision,definition_json)
      VALUES(tenant_value,project_key,new_task,criterion->>'criterion_id',1,criterion::text);
  END LOOP;
  receipt:=jsonb_build_object('task_id',new_task,'tenant_id',tenant_value,
    'project_id',project_key,'version','1','name',payload->>'name',
    'scenario',payload->>'scenario','desired_state','pause','observed_state','ready',
    'goal_revision','1','execution_epoch','1','allowed_actions',jsonb_build_array());
  INSERT INTO vnext.task_create_command(tenant_id,subject,idempotency_key,request_digest,
    task_id,receipt_json)
    VALUES(tenant_value,subject_value,create_key,request_digest,new_task,receipt::text);
  RETURN receipt::text;
EXCEPTION WHEN unique_violation THEN
  SELECT * INTO saved FROM vnext.task_create_command command
    WHERE (command.tenant_id,command.subject,command.idempotency_key)
      =(tenant_value,subject_value,create_key);
  IF FOUND AND saved.request_digest=request_digest THEN
    RETURN saved.receipt_json;
  END IF;
  RAISE;
END $$;
"""

_TASK_OPTIONS = """
CREATE OR REPLACE FUNCTION vnext.task_options(project_key text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE tenant_value text:=current_setting('wuji.tenant',true); subject_value text:=current_setting('wuji.subject',true); result jsonb; missing jsonb:='[]'::jsonb; model_list jsonb; runtime_list jsonb;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM vnext.project_access a WHERE a.tenant_id=tenant_value AND a.project_id=project_key AND a.subject=subject_value AND a.can_create)
     AND NOT EXISTS (SELECT 1 FROM vnext.task_access a WHERE a.tenant_id=tenant_value AND a.project_id=project_key AND a.subject=subject_value AND a.can_read AND a.can_control) THEN
    RAISE EXCEPTION 'task options not found' USING ERRCODE='42501';
  END IF;
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'ref',p.ref,'name',COALESCE(p.document_json::jsonb->>'name',p.ref),'revision',p.revision::text,
      'digest',encode(sha256(convert_to(p.document_json,'UTF8')),'hex'),
      'capabilities',CASE WHEN jsonb_typeof(p.document_json::jsonb->'capabilities')='array' THEN p.document_json::jsonb->'capabilities'
        WHEN p.document_json::jsonb->>'protocol' IS NOT NULL THEN jsonb_build_array(p.document_json::jsonb->>'protocol') ELSE '[]'::jsonb END,
      'real_model_allowed',p.real_model_allowed
    ) ORDER BY p.ref,p.revision DESC),'[]'::jsonb)
    INTO model_list FROM vnext.published_profile p WHERE p.tenant_id=tenant_value AND p.kind='model' AND NOT p.revoked;
  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'ref',p.ref,'name',COALESCE(p.document_json::jsonb->>'name',p.ref),'revision',p.revision::text,
      'digest',encode(sha256(convert_to(p.document_json,'UTF8')),'hex'),
      'capabilities',CASE WHEN jsonb_typeof(p.document_json::jsonb->'capabilities')='array' THEN p.document_json::jsonb->'capabilities'
        WHEN jsonb_typeof(p.document_json::jsonb->'allowed_tool_refs')='array' THEN p.document_json::jsonb->'allowed_tool_refs' ELSE '[]'::jsonb END,
      'real_model_allowed',p.real_model_allowed,
      'max_explore_concurrency',CASE
        WHEN jsonb_typeof(p.document_json::jsonb#>'{task_run_limits,explore}')='number'
          AND (p.document_json::jsonb#>>'{task_run_limits,explore}')::numeric BETWEEN 1 AND 256
          AND (p.document_json::jsonb#>>'{task_run_limits,explore}')::numeric
            = trunc((p.document_json::jsonb#>>'{task_run_limits,explore}')::numeric)
        THEN (p.document_json::jsonb#>>'{task_run_limits,explore}')::integer
        ELSE NULL END
    ) ORDER BY p.ref,p.revision DESC),'[]'::jsonb)
    INTO runtime_list FROM vnext.published_profile p WHERE p.tenant_id=tenant_value AND p.kind='runtime' AND NOT p.revoked;
  IF jsonb_array_length(model_list)=0 THEN missing:=missing||jsonb_build_array(jsonb_build_object('id','model_profile','layer','profile','status','fail','reason_code','model_profile_unavailable','observed_at',clock_timestamp(),'evidence_ref',NULL,'remediation_owner','application','message','No published model profile is available.')); END IF;
  IF jsonb_array_length(runtime_list)=0 THEN missing:=missing||jsonb_build_array(jsonb_build_object('id','runtime_profile','layer','profile','status','fail','reason_code','runtime_profile_unavailable','observed_at',clock_timestamp(),'evidence_ref',NULL,'remediation_owner','application','message','No published runtime profile is available.')); END IF;
  result:=jsonb_build_object('project_id',project_key,'model_profiles',model_list,'runtime_profiles',runtime_list,'missing',missing);
  RETURN result::text;
END $$;
"""


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0039_runtime_capture":
        raise ValueError("project access migration parent changed")
    connection.execute(
        """CREATE TABLE vnext.project_access(
        tenant_id text NOT NULL,project_id text NOT NULL,subject text NOT NULL,
        can_create boolean NOT NULL DEFAULT false,
        clearance integer NOT NULL DEFAULT 0 CHECK(clearance>=0),
        PRIMARY KEY(tenant_id,project_id,subject),
        FOREIGN KEY(tenant_id,project_id)
          REFERENCES vnext.project(tenant_id,project_id))"""
    )
    connection.execute("ALTER TABLE vnext.project_access ENABLE ROW LEVEL SECURITY")
    connection.execute("REVOKE ALL ON vnext.project_access FROM PUBLIC")
    connection.execute(_CREATE_TASK)
    connection.execute(_TASK_OPTIONS)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.create_task(text,jsonb,jsonb,text,text) TO {}"
        ).format(app)
    )
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.task_options(text) TO {}").format(
            app
        )
    )
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.create_task(text,jsonb,jsonb,text,text) FROM PUBLIC"
    )
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.task_options(text) FROM PUBLIC"
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
