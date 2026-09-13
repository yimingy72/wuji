"""P10 receiver-bound retained result settlement migration."""

from psycopg import sql

from wuji_core.persistence.uow import DomainError


HEAD = "vnext_0013_receiver_results"


def bind_receiver_result(tx, *, agent_run_id: str) -> None:
    """P09 call point after the immutable Assignment row is inserted."""
    if (
        tx.purpose != "admit"
        or not tx.permissions.get("can_admit")
        or not isinstance(agent_run_id, str)
        or not agent_run_id
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    tx.connection.execute(
        "SELECT vnext.bind_receiver_result(%s,%s,%s,%s)",
        (*tx.owner, agent_run_id),
    ).fetchone()


def upgrade(connection, application_role):
    statements = [
        """CREATE TABLE vnext.retained_result_binding(
          tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL,
          agent_run_id text NOT NULL,operation_id text NOT NULL,
          assignment_digest text NOT NULL CHECK(assignment_digest~'^[a-f0-9]{64}$'),
          receiver_subject text NOT NULL,source_writer_subject text NOT NULL,
          receiver_id text NOT NULL,runtime_attempt numeric NOT NULL,
          environment_ref text NOT NULL,pod_uid text NOT NULL,
          access_level integer NOT NULL CHECK(access_level>=0),
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          PRIMARY KEY(tenant_id,project_id,task_id,agent_run_id),
          UNIQUE(tenant_id,project_id,task_id,operation_id),
          FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id)
            REFERENCES vnext.scheduler_assignment(tenant_id,project_id,task_id,agent_run_id),
          FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id,receiver_subject)
            REFERENCES vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject),
          FOREIGN KEY(tenant_id,project_id,task_id,agent_run_id,source_writer_subject)
            REFERENCES vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject),
          CHECK(receiver_subject<>source_writer_subject))""",
        "ALTER TABLE vnext.retained_result_binding ENABLE ROW LEVEL SECURITY",
        "REVOKE ALL ON vnext.retained_result_binding FROM PUBLIC",
        """CREATE FUNCTION vnext.bind_receiver_result(t text,p text,k text,rid text)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE d vnext.scheduler_assignment; a vnext.agent_run;
          receiver vnext.scheduler_receiver; source vnext.run_writer;
          receiver_acl vnext.task_access; saved vnext.retained_result_binding;
          source_subject text; receiver_level integer;
        BEGIN
          IF current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR NOT EXISTS(SELECT 1 FROM vnext.task_access caller
              WHERE (caller.tenant_id,caller.project_id,caller.task_id,caller.subject)=
                (t,p,k,current_setting('wuji.subject',true))
              AND caller.can_read AND caller.can_admit)
          THEN RAISE EXCEPTION 'scheduler admission required' USING ERRCODE='42501'; END IF;
          SELECT * INTO d FROM vnext.scheduler_assignment
            WHERE (tenant_id,project_id,task_id,agent_run_id)=(t,p,k,rid);
          SELECT * INTO a FROM vnext.agent_run
            WHERE (tenant_id,project_id,task_id,agent_run_id)=(t,p,k,rid);
          IF NOT FOUND OR d.operation_id IS DISTINCT FROM a.start_operation_id
            OR d.assignment_digest IS DISTINCT FROM encode(sha256(convert_to(d.assignment_json,'UTF8')),'hex')
            OR d.assignment_json::jsonb->>'operation_id' IS DISTINCT FROM d.operation_id
            OR d.assignment_json::jsonb->'identity' IS DISTINCT FROM jsonb_build_object(
              'tenant_id',a.tenant_id,'project_id',a.project_id,'task_id',a.task_id,
              'work_item_id',a.work_item_id,'agent_run_id',a.agent_run_id,
              'receiver_id',a.receiver_id,'execution_epoch',a.execution_epoch::text,
              'run_epoch',a.run_epoch::text,'runtime_attempt',a.runtime_attempt::text)
          THEN RAISE EXCEPTION 'fixed scheduler assignment required' USING ERRCODE='42501'; END IF;
          SELECT * INTO receiver FROM vnext.scheduler_receiver
            WHERE (tenant_id,project_id,task_id,runtime_attempt,receiver_id)=
              (t,p,k,a.runtime_attempt,a.receiver_id);
          IF NOT FOUND OR receiver.environment_ref IS DISTINCT FROM a.environment_ref
            OR receiver.pod_uid IS DISTINCT FROM a.pod_uid
          THEN RAISE EXCEPTION 'registered receiver required' USING ERRCODE='42501'; END IF;
          SELECT * INTO receiver_acl FROM vnext.task_access
            WHERE (tenant_id,project_id,task_id,subject)=
              (t,p,k,receiver.receiver_subject);
          IF NOT FOUND OR NOT receiver_acl.can_read OR NOT receiver_acl.can_observe
            OR NOT receiver_acl.can_settle OR receiver_acl.can_write
            OR receiver_acl.can_model_output
          THEN RAISE EXCEPTION 'independent receiver settlement authority required' USING ERRCODE='42501'; END IF;
          SELECT binding_json::jsonb->>'subject' INTO source_subject
            FROM vnext.scheduler_credential
            WHERE (tenant_id,project_id,task_id,credential_ref,agent_run_id,bound)=
              (t,p,k,d.credential_ref,rid,true);
          SELECT * INTO source FROM vnext.run_writer
            WHERE (tenant_id,project_id,task_id,agent_run_id,subject)=
              (t,p,k,rid,source_subject);
          IF source_subject IS NULL OR NOT FOUND OR source.revoked OR source.can_settle
          THEN RAISE EXCEPTION 'exact non-settling source writer required' USING ERRCODE='42501'; END IF;
          receiver_level:=receiver_acl.clearance;
          INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,
            subject,agent_subject,revoked,can_settle)
          VALUES(t,p,k,rid,receiver.receiver_subject,source.agent_subject,false,true)
          ON CONFLICT DO NOTHING;
          SELECT * INTO source FROM vnext.run_writer
            WHERE (tenant_id,project_id,task_id,agent_run_id,subject)=
              (t,p,k,rid,receiver.receiver_subject);
          IF NOT FOUND OR source.revoked OR NOT source.can_settle
            OR source.agent_subject IS DISTINCT FROM
              (SELECT agent_subject FROM vnext.run_writer WHERE
                (tenant_id,project_id,task_id,agent_run_id,subject)=
                (t,p,k,rid,source_subject))
          THEN RAISE EXCEPTION 'receiver run binding conflict' USING ERRCODE='23514'; END IF;
          INSERT INTO vnext.retained_result_binding(
            tenant_id,project_id,task_id,agent_run_id,operation_id,
            assignment_digest,receiver_subject,source_writer_subject,
            receiver_id,runtime_attempt,environment_ref,pod_uid,access_level)
          VALUES(t,p,k,rid,d.operation_id,d.assignment_digest,
            receiver.receiver_subject,source_subject,a.receiver_id,a.runtime_attempt,
            a.environment_ref,a.pod_uid,receiver_level)
          ON CONFLICT DO NOTHING;
          SELECT * INTO saved FROM vnext.retained_result_binding
            WHERE (tenant_id,project_id,task_id,agent_run_id)=(t,p,k,rid);
          IF NOT FOUND OR (saved.operation_id,saved.assignment_digest,
              saved.receiver_subject,saved.source_writer_subject,saved.receiver_id,
              saved.runtime_attempt,saved.environment_ref,saved.pod_uid,saved.access_level)
            IS DISTINCT FROM (d.operation_id,d.assignment_digest,
              receiver.receiver_subject,source_subject,a.receiver_id,a.runtime_attempt,
              a.environment_ref,a.pod_uid,receiver_level)
          THEN RAISE EXCEPTION 'receiver result binding conflict' USING ERRCODE='23514'; END IF;
        END $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.bind_receiver_result(text,text,text,text) FROM PUBLIC",
        """CREATE FUNCTION vnext.lock_current_run_credential(
          t text,p text,k text,s text,j text)
        RETURNS TABLE(document_json text,revoked boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        BEGIN
          IF current_setting('wuji.model_output',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR current_setting('wuji.tenant',true) IS DISTINCT FROM t
            OR current_setting('wuji.project',true) IS DISTINCT FROM p
            OR current_setting('wuji.task',true) IS DISTINCT FROM k
            OR current_setting('wuji.subject',true) IS DISTINCT FROM s
            OR current_setting('wuji.token_id',true) IS DISTINCT FROM j
            OR NOT EXISTS(SELECT 1 FROM vnext.task_access acl WHERE
              (acl.tenant_id,acl.project_id,acl.task_id,acl.subject)=
              (t,p,k,s) AND acl.can_read AND acl.can_model_output)
          THEN RAISE EXCEPTION 'current model-output credential required'
            USING ERRCODE='42501'; END IF;
          RETURN QUERY SELECT c.document_json,c.revoked
            FROM vnext.run_credential c
            WHERE (c.tenant_id,c.project_id,c.task_id,c.subject,c.token_id)=
              (t,p,k,s,j)
            FOR SHARE;
        END $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.lock_current_run_credential(text,text,text,text,text) FROM PUBLIC",
        """CREATE FUNCTION vnext.open_receiver_result(
          t text,p text,k text,rid text,op text,digest text)
        RETURNS TABLE(source_writer_subject text,disposition text,access_level integer)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE binding vnext.retained_result_binding; assigned vnext.scheduler_assignment;
          runrow vnext.agent_run; taskrow vnext.task; receiver vnext.scheduler_receiver;
          source_credential vnext.run_credential; source_binding vnext.scheduler_credential;
          current_source boolean; current_run boolean;
        BEGIN
          IF current_setting('wuji.retained_result',true) IS DISTINCT FROM 'true'
            OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
            OR NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR NOT EXISTS(SELECT 1 FROM vnext.task_access acl
              WHERE (acl.tenant_id,acl.project_id,acl.task_id,acl.subject)=
                (t,p,k,current_setting('wuji.subject',true))
              AND acl.can_read AND acl.can_observe AND acl.can_settle
              AND NOT acl.can_write AND NOT acl.can_model_output)
          THEN RAISE EXCEPTION 'receiver settlement authority required' USING ERRCODE='42501'; END IF;
          SELECT * INTO binding FROM vnext.retained_result_binding
            WHERE (tenant_id,project_id,task_id,agent_run_id,operation_id,
              assignment_digest,receiver_subject)=
              (t,p,k,rid,op,digest,current_setting('wuji.subject',true));
          SELECT * INTO assigned FROM vnext.scheduler_assignment
            WHERE (tenant_id,project_id,task_id,agent_run_id,operation_id,assignment_digest)=
              (t,p,k,rid,op,digest);
          SELECT * INTO runrow FROM vnext.agent_run
            WHERE (tenant_id,project_id,task_id,agent_run_id,start_operation_id)=
              (t,p,k,rid,op);
          SELECT * INTO taskrow FROM vnext.task
            WHERE (tenant_id,project_id,task_id)=(t,p,k);
          IF binding IS NULL OR assigned IS NULL OR runrow IS NULL OR taskrow IS NULL
          THEN RAISE EXCEPTION 'retained result binding absent' USING ERRCODE='42501'; END IF;
          SELECT * INTO receiver FROM vnext.scheduler_receiver
            WHERE (tenant_id,project_id,task_id,runtime_attempt,receiver_id,
              receiver_subject,environment_ref,pod_uid)=
              (t,p,k,binding.runtime_attempt,binding.receiver_id,
              binding.receiver_subject,binding.environment_ref,binding.pod_uid);
          IF NOT FOUND OR runrow.receiver_id IS DISTINCT FROM binding.receiver_id
            OR runrow.runtime_attempt IS DISTINCT FROM binding.runtime_attempt
            OR runrow.environment_ref IS DISTINCT FROM binding.environment_ref
            OR runrow.pod_uid IS DISTINCT FROM binding.pod_uid
            OR NOT EXISTS(SELECT 1 FROM vnext.run_writer writer WHERE
              (writer.tenant_id,writer.project_id,writer.task_id,writer.agent_run_id,
               writer.subject,writer.can_settle,writer.revoked)=
              (t,p,k,rid,binding.receiver_subject,true,false))
          THEN RAISE EXCEPTION 'receiver registration changed' USING ERRCODE='42501'; END IF;
          SELECT * INTO source_binding FROM vnext.scheduler_credential
            WHERE (tenant_id,project_id,task_id,credential_ref,agent_run_id,bound)=
              (t,p,k,assigned.credential_ref,rid,true);
          SELECT * INTO source_credential FROM vnext.run_credential
            WHERE (tenant_id,project_id,task_id,agent_run_id,subject,token_id)=
              (t,p,k,rid,binding.source_writer_subject,
               source_binding.binding_json::jsonb->>'token_id')
            FOR SHARE;
          IF source_binding IS NULL OR source_credential IS NULL
            OR source_binding.binding_json IS DISTINCT FROM source_credential.document_json
            OR source_binding.binding_json::jsonb->>'subject'
              IS DISTINCT FROM binding.source_writer_subject
            OR NOT EXISTS(SELECT 1 FROM vnext.run_writer writer WHERE
              (writer.tenant_id,writer.project_id,writer.task_id,writer.agent_run_id,
               writer.subject,writer.can_settle,writer.revoked)=
              (t,p,k,rid,binding.source_writer_subject,false,false))
          THEN RAISE EXCEPTION 'source writer binding changed' USING ERRCODE='42501'; END IF;
          current_source:=NOT source_credential.revoked
            AND (source_credential.document_json::jsonb->>'expires_at')::timestamptz>clock_timestamp();
          current_run:=taskrow.execution_allowed AND runrow.execution_allowed
            AND taskrow.execution_epoch=runrow.execution_epoch
            AND taskrow.runtime_attempt=runrow.runtime_attempt;
          disposition:=CASE WHEN current_source AND current_run
            THEN 'accepted' ELSE 'historical_only' END;
          source_writer_subject:=binding.source_writer_subject;
          access_level:=binding.access_level;
          PERFORM set_config('wuji.write','true',true);
          PERFORM set_config('wuji.model_output','true',true);
          PERFORM set_config('wuji.domain_write',
            CASE WHEN disposition='accepted' THEN 'true' ELSE 'false' END,true);
          PERFORM set_config('wuji.retained_run',rid,true);
          PERFORM set_config('wuji.retained_assignment_digest',digest,true);
          RETURN NEXT;
        END $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.open_receiver_result(text,text,text,text,text,text) FROM PUBLIC",
        """CREATE OR REPLACE FUNCTION vnext.require_model_mutation(t text,p text,k text,r text,w text)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
          IF current_setting('wuji.model_output',true) IS DISTINCT FROM 'true'
            OR NOT COALESCE(vnext.in_scope(t,p,k),false)
            OR w IS DISTINCT FROM current_setting('wuji.subject',true)
            OR NOT EXISTS(SELECT 1 FROM vnext.run_writer b WHERE
              (b.tenant_id,b.project_id,b.task_id,b.agent_run_id,b.subject)=
              (t,p,k,r,w) AND NOT b.revoked)
            OR (current_setting('wuji.retained_result',true)='true' AND (
              current_setting('wuji.retained_run',true) IS DISTINCT FROM r
              OR NOT EXISTS(SELECT 1 FROM vnext.retained_result_binding b WHERE
                (b.tenant_id,b.project_id,b.task_id,b.agent_run_id,
                 b.receiver_subject,b.assignment_digest)=
                (t,p,k,r,w,current_setting('wuji.retained_assignment_digest',true)))))
          THEN RAISE EXCEPTION 'bound model output authority required' USING ERRCODE='42501'; END IF;
        END $$""",
        "REVOKE EXECUTE ON FUNCTION vnext.require_model_mutation(text,text,text,text,text) FROM PUBLIC",
    ]
    for statement in statements:
        connection.execute(statement)
    app = sql.Identifier(application_role)
    for signature in [
        "bind_receiver_result(text,text,text,text)",
        "lock_current_run_credential(text,text,text,text,text)",
        "open_receiver_result(text,text,text,text,text,text)",
        "require_model_mutation(text,text,text,text,text)",
    ]:
        connection.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION vnext.{} TO {}").format(
                sql.SQL(signature), app
            )
        )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
