"""P11 Task creation entry over deployment-published model/runtime profiles.

The application role keeps its existing row-level security: it cannot insert
`vnext.task`, `vnext.task_access` or `vnext.task_assessment_policy` directly.
Creation therefore runs through one SECURITY DEFINER function that derives the
tenant and subject from the transaction settings, requires project control
permission, resolves only published profiles of that tenant and records the
idempotent receipt in the same transaction.
"""

from psycopg import sql

from wuji_core.persistence.layout_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0019_p11_task_creation"

_CREATE_TASK = """
CREATE FUNCTION vnext.create_task(project_key text, payload jsonb, start_points jsonb,
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
  SELECT max(access.clearance) INTO clearance_value FROM vnext.task_access access
    JOIN vnext.task task USING(tenant_id,project_id,task_id)
    WHERE access.tenant_id=tenant_value AND access.project_id=project_key
      AND access.subject=subject_value AND access.can_control AND access.can_read;
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


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0018_p15_layout":
        raise ValueError("P11 task creation migration parent changed")
    statements = (
        """CREATE TABLE vnext.published_profile(
          tenant_id text NOT NULL REFERENCES vnext.tenant,
          kind text NOT NULL CHECK(kind IN ('model','runtime')),
          ref text NOT NULL CHECK(length(ref) BETWEEN 1 AND 256),
          revision numeric NOT NULL CHECK(revision>=1 AND revision=trunc(revision)),
          document_json text NOT NULL CHECK(jsonb_typeof(document_json::jsonb)='object'),
          lock_digest text CHECK(lock_digest IS NULL OR lock_digest ~ '^[a-f0-9]{64}$'),
          published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          revoked boolean NOT NULL DEFAULT false,
          PRIMARY KEY(tenant_id,kind,ref,revision),
          CHECK((kind='runtime')=(lock_digest IS NOT NULL)))""",
        "ALTER TABLE vnext.published_profile ENABLE ROW LEVEL SECURITY",
        "REVOKE ALL ON vnext.published_profile FROM PUBLIC",
        """CREATE POLICY published_profile_read ON vnext.published_profile FOR SELECT USING(
          tenant_id=current_setting('wuji.tenant',true) AND NOT revoked)""",
        """CREATE TABLE vnext.task_create_command(
          tenant_id text NOT NULL, subject text NOT NULL,
          idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 256),
          request_digest text NOT NULL CHECK(request_digest ~ '^[a-f0-9]{64}$'),
          task_id text NOT NULL, receipt_json text NOT NULL
            CHECK(jsonb_typeof(receipt_json::jsonb)='object'),
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          PRIMARY KEY(tenant_id,subject,idempotency_key))""",
        "REVOKE ALL ON vnext.task_create_command FROM PUBLIC",
        _CREATE_TASK,
    )
    for statement in statements:
        connection.execute(statement)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL("GRANT SELECT ON vnext.published_profile TO {}").format(app)
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.create_task(text,jsonb,jsonb,text,text) TO {}"
        ).format(app)
    )
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.create_task(text,jsonb,jsonb,text,text) FROM PUBLIC"
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
