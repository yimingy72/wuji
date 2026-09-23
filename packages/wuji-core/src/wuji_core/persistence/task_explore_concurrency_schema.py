"""Freeze Task Explore concurrency against the selected RuntimeProfile."""

from psycopg import sql

from wuji_core.persistence.native_approval_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0036_task_explore_concurrency"


_TASK_OPTIONS = """
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
    if PARENT_HEAD != "vnext_0035_native_approval_membership":
        raise ValueError("Task Explore concurrency migration parent changed")
    connection.execute("""CREATE FUNCTION vnext.guard_task_explore_concurrency() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE requested jsonb; published jsonb;
        BEGIN
          requested:=NEW.definition_json::jsonb#>'{task,explore_concurrency}';
          IF requested IS NULL THEN RETURN NEW; END IF;
          published:=NEW.definition_json::jsonb#>'{runtime_profile,task_run_limits,explore}';
          IF jsonb_typeof(requested) IS DISTINCT FROM 'number'
             OR jsonb_typeof(published) IS DISTINCT FROM 'number' THEN
            RAISE EXCEPTION 'Task Explore concurrency requires a capable RuntimeProfile'
              USING ERRCODE='23514';
          END IF;
          IF requested::numeric<>trunc(requested::numeric)
             OR published::numeric<>trunc(published::numeric)
             OR requested::numeric NOT BETWEEN 1 AND 256
             OR published::numeric NOT BETWEEN 1 AND 256
             OR requested::numeric>published::numeric THEN
            RAISE EXCEPTION 'Task Explore concurrency exceeds the selected RuntimeProfile'
              USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$""")
    connection.execute("""CREATE TRIGGER task_explore_concurrency_guard
        BEFORE INSERT OR UPDATE OF definition_json ON vnext.task
        FOR EACH ROW EXECUTE FUNCTION vnext.guard_task_explore_concurrency()""")
    connection.execute(_TASK_OPTIONS)
    connection.execute("REVOKE ALL ON FUNCTION vnext.guard_task_explore_concurrency() FROM PUBLIC")
    connection.execute("REVOKE ALL ON FUNCTION vnext.task_options(text) FROM PUBLIC")
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.task_options(text) TO {}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
