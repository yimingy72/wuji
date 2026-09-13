"""Task-wide Pod receiver registration under one trusted controller PG session."""

from psycopg import sql

from wuji_core.persistence.session_writer_exit_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0017_task_pod_receiver"


def statements():
    return (
        """CREATE TABLE vnext.task_pod_controller(
        tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
        controller_subject text NOT NULL,login_role name NOT NULL,
        enabled boolean NOT NULL DEFAULT false,
        PRIMARY KEY(tenant_id,project_id,task_id,controller_subject,login_role),
        FOREIGN KEY(tenant_id,project_id,task_id,controller_subject)
          REFERENCES vnext.task_access(tenant_id,project_id,task_id,subject))""",
        "ALTER TABLE vnext.task_pod_controller ENABLE ROW LEVEL SECURITY",
        "REVOKE ALL ON vnext.task_pod_controller FROM PUBLIC",
        """CREATE FUNCTION vnext.canonical_jsonb_text(value jsonb) RETURNS text
        LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog AS $$
        DECLARE kind text:=jsonb_typeof(value);rendered text;
        BEGIN
          IF kind='object' THEN
            SELECT '{'||COALESCE(string_agg(
              to_json(key)::text||':'||vnext.canonical_jsonb_text(item),
              ',' ORDER BY key COLLATE "C"),'')||'}'
              INTO rendered FROM jsonb_each(value) AS member(key,item);
          ELSIF kind='array' THEN
            SELECT '['||COALESCE(string_agg(
              vnext.canonical_jsonb_text(item),',' ORDER BY ordinal),'')||']'
              INTO rendered FROM jsonb_array_elements(value)
                WITH ORDINALITY AS member(item,ordinal);
          ELSE
            rendered:=value::text;
          END IF;
          RETURN rendered;
        END $$""",
        """CREATE FUNCTION vnext.register_task_pod_receiver(
          t text,p text,k text,a numeric,e numeric,definition_digest text,
          scope_digest text,receiver_id text,receiver_subject text,
          environment_ref text,credential_template_ref text,model_mode text,
          pod_uid text,harness_profiles_json text) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE lock_key bigint;taskrow vnext.task;caller vnext.task_access;
          receiver_acl vnext.task_access;controller vnext.task_pod_controller;
          template vnext.scheduler_identity_template;existing vnext.scheduler_receiver;
          definition jsonb;config jsonb;scope_text text;
        BEGIN
          lock_key:=hashtextextended(
            json_build_array('wuji.vnext.task-pod'::text,t::text,k::text)::text,0);
          IF NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory'
              AND pid=pg_backend_pid() AND granted AND mode='ExclusiveLock'
              AND objsubid=1
              AND classid::bigint=((lock_key >> 32)&4294967295)
              AND objid::bigint=(lock_key&4294967295)
              AND database=(SELECT oid FROM pg_database
                WHERE datname=current_database()))
          THEN RAISE EXCEPTION 'current Task Pod controller lock required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO controller FROM vnext.task_pod_controller
            WHERE (tenant_id,project_id,task_id,controller_subject,login_role,enabled)=
              (t,p,k,current_setting('wuji.subject',true),session_user::name,true)
            FOR SHARE;
          IF controller IS NULL THEN RAISE EXCEPTION 'trusted Task Pod controller required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO taskrow FROM vnext.task
            WHERE (tenant_id,project_id,task_id)=(t,p,k) FOR UPDATE;
          SELECT * INTO caller FROM vnext.task_access
            WHERE (tenant_id,project_id,task_id,subject)=
              (t,p,k,current_setting('wuji.subject',true)) FOR SHARE;
          SELECT * INTO receiver_acl FROM vnext.task_access
            WHERE (tenant_id,project_id,task_id,subject)=(t,p,k,receiver_subject)
            FOR SHARE;
          SELECT * INTO template FROM vnext.scheduler_identity_template
            WHERE (tenant_id,project_id,task_id,template_ref,enabled)=
              (t,p,k,credential_template_ref,true) FOR SHARE;
          SELECT document_json::jsonb INTO config FROM vnext.admission_config
            WHERE (tenant_id,project_id,task_id)=(t,p,k);
          definition:=taskrow.definition_json::jsonb;
          scope_text:=vnext.canonical_jsonb_text(
            definition->'task'->'authorization_scope');
          IF taskrow IS NULL OR caller IS NULL OR receiver_acl IS NULL OR template IS NULL
            OR config IS NULL OR definition IS NULL
            OR NOT caller.can_read OR NOT caller.can_admit OR NOT caller.can_observe
            OR NOT receiver_acl.can_read OR NOT receiver_acl.can_observe
            OR taskrow.runtime_attempt<>a OR taskrow.execution_epoch<>e
            OR taskrow.activated_at IS NULL OR NOT taskrow.execution_allowed
            OR taskrow.desired_state<>'run' OR taskrow.observed_state<>'running'
            OR taskrow.completion_epoch_id IS NOT NULL
            OR definition_digest !~ '^[a-f0-9]{64}$'
            OR scope_digest !~ '^[a-f0-9]{64}$'
            OR taskrow.definition_digest IS DISTINCT FROM definition_digest
            OR encode(sha256(convert_to(taskrow.definition_json,'UTF8')),'hex')
              IS DISTINCT FROM definition_digest
            OR encode(sha256(convert_to(scope_text,'UTF8')),'hex')
              IS DISTINCT FROM scope_digest
            OR (definition->'task'->>'authorization_expires_at')::timestamptz
              <=clock_timestamp()
            OR taskrow.activated_at+(
              (config->'runtime'->'limits'->>'max_elapsed_seconds')::integer
              *interval '1 second')<=clock_timestamp()
            OR definition->'task'->>'model_profile_ref'
              IS DISTINCT FROM config->'model'->>'ref'
            OR definition->'task'->>'runtime_profile_ref'
              IS DISTINCT FROM config->'runtime'->>'ref'
            OR definition->>'lock_digest'
              IS DISTINCT FROM config->'runtime'->>'lock_digest'
            OR definition->'model_profile'->>'ref'
              IS DISTINCT FROM config->'model'->>'ref'
            OR definition->'model_profile'->>'revision'
              IS DISTINCT FROM config->'model'->>'revision'
            OR definition->'model_profile'->>'published_at'
              IS DISTINCT FROM config->'model'->>'published_at'
            OR definition->'runtime_profile'->>'ref'
              IS DISTINCT FROM config->'runtime'->>'ref'
            OR definition->'runtime_profile'->>'revision'
              IS DISTINCT FROM config->'runtime'->>'revision'
            OR definition->'runtime_profile'->>'published_at'
              IS DISTINCT FROM config->'runtime'->>'published_at'
            OR harness_profiles_json::jsonb
              IS DISTINCT FROM definition->'worker_profiles'
            OR model_mode NOT IN ('synthetic','real')
            OR receiver_id IS NULL OR length(receiver_id) NOT BETWEEN 1 AND 256
            OR receiver_subject IS NULL OR length(receiver_subject) NOT BETWEEN 1 AND 256
            OR environment_ref IS NULL OR length(environment_ref) NOT BETWEEN 1 AND 256
            OR pod_uid IS NULL OR length(pod_uid) NOT BETWEEN 1 AND 256
          THEN RAISE EXCEPTION 'current fixed Task Pod receiver required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO existing FROM vnext.scheduler_receiver
            WHERE (tenant_id,project_id,task_id,runtime_attempt)=(t,p,k,a)
            FOR UPDATE;
          IF existing IS NULL THEN
            INSERT INTO vnext.scheduler_receiver(
              tenant_id,project_id,task_id,runtime_attempt,receiver_id,
              environment_ref,model_mode,receiver_subject,credential_template_ref,
              harness_profiles_json,pod_uid,enabled)
            VALUES(t,p,k,a,receiver_id,environment_ref,model_mode,receiver_subject,
              credential_template_ref,harness_profiles_json,pod_uid,true);
          ELSE
            IF ROW(existing.receiver_id,existing.receiver_subject,
              existing.environment_ref,existing.credential_template_ref,
              existing.model_mode,existing.pod_uid,
              existing.harness_profiles_json::jsonb)
              IS DISTINCT FROM ROW(receiver_id,receiver_subject,environment_ref,
                credential_template_ref,model_mode,pod_uid,
                harness_profiles_json::jsonb)
            THEN RAISE EXCEPTION 'Task Pod receiver identity cannot be replaced'
              USING ERRCODE='23514'; END IF;
            UPDATE vnext.scheduler_receiver SET enabled=true
              WHERE (tenant_id,project_id,task_id,runtime_attempt)=(t,p,k,a);
          END IF;
          RETURN true;
        END $$""",
        """CREATE FUNCTION vnext.disable_task_pod_receiver(
          t text,p text,k text,a numeric,receiver_id text,pod_uid text)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE lock_key bigint;taskrow vnext.task;caller vnext.task_access;
          receiver_acl vnext.task_access;controller vnext.task_pod_controller;
          existing vnext.scheduler_receiver;
        BEGIN
          lock_key:=hashtextextended(
            json_build_array('wuji.vnext.task-pod'::text,t::text,k::text)::text,0);
          IF NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory'
              AND pid=pg_backend_pid() AND granted AND mode='ExclusiveLock'
              AND objsubid=1
              AND classid::bigint=((lock_key >> 32)&4294967295)
              AND objid::bigint=(lock_key&4294967295)
              AND database=(SELECT oid FROM pg_database
                WHERE datname=current_database()))
          THEN RAISE EXCEPTION 'current Task Pod controller lock required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO controller FROM vnext.task_pod_controller
            WHERE (tenant_id,project_id,task_id,controller_subject,login_role,enabled)=
              (t,p,k,current_setting('wuji.subject',true),session_user::name,true)
            FOR SHARE;
          IF controller IS NULL THEN RAISE EXCEPTION 'trusted Task Pod controller required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO taskrow FROM vnext.task
            WHERE (tenant_id,project_id,task_id)=(t,p,k) FOR UPDATE;
          SELECT * INTO caller FROM vnext.task_access
            WHERE (tenant_id,project_id,task_id,subject)=
              (t,p,k,current_setting('wuji.subject',true)) FOR SHARE;
          IF taskrow IS NULL OR caller IS NULL OR NOT caller.can_read
            OR NOT caller.can_admit OR NOT caller.can_observe
          THEN RAISE EXCEPTION 'current Task Pod controller ACL required'
            USING ERRCODE='42501'; END IF;
          SELECT * INTO existing FROM vnext.scheduler_receiver
            WHERE (tenant_id,project_id,task_id,runtime_attempt)=(t,p,k,a)
            FOR UPDATE;
          IF existing IS NULL OR existing.receiver_id<>receiver_id
            OR existing.pod_uid<>pod_uid THEN RETURN false; END IF;
          SELECT * INTO receiver_acl FROM vnext.task_access
            WHERE (tenant_id,project_id,task_id,subject)=
              (t,p,k,existing.receiver_subject) FOR SHARE;
          IF receiver_acl IS NULL OR NOT receiver_acl.can_read
            OR NOT receiver_acl.can_observe
          THEN RAISE EXCEPTION 'current receiver ACL required'
            USING ERRCODE='42501'; END IF;
          UPDATE vnext.scheduler_receiver SET enabled=false
            WHERE (tenant_id,project_id,task_id,runtime_attempt)=(t,p,k,a);
          RETURN true;
        END $$""",
        "REVOKE ALL ON FUNCTION vnext.canonical_jsonb_text(jsonb) FROM PUBLIC",
        """REVOKE ALL ON FUNCTION
          vnext.register_task_pod_receiver(text,text,text,numeric,numeric,text,text,text,text,text,text,text,text,text),
          vnext.disable_task_pod_receiver(text,text,text,numeric,text,text)
          FROM PUBLIC""",
    )


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0016_p08_session_writer_exit":
        raise ValueError("Task Pod receiver migration parent changed")
    for statement in statements():
        connection.execute(statement)
    functions = (
        "vnext.register_task_pod_receiver(text,text,text,numeric,numeric,text,text,"
        "text,text,text,text,text,text,text),"
        "vnext.disable_task_pod_receiver(text,text,text,numeric,text,text)"
    )
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION " + functions + " TO {}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
