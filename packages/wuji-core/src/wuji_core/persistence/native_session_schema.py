"""Native MAF Session codec and knowledge handoff state."""

from psycopg import sql

from wuji_core.persistence.task_goal_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0034_native_session_v2"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0033_task_goal_criteria":
        raise ValueError("native Session migration parent changed")
    connection.execute(
        """DO $$ DECLARE item record; BEGIN
        FOR item IN SELECT conname FROM pg_constraint
          WHERE conrelid='vnext.session_object'::regclass
          AND contype='c' AND pg_get_constraintdef(oid) LIKE '%role%'
        LOOP EXECUTE format('ALTER TABLE vnext.session_object DROP CONSTRAINT %I',item.conname); END LOOP;
        END $$"""
    )
    connection.execute(
        "ALTER TABLE vnext.session_object ADD CONSTRAINT session_object_role_check "
        "CHECK(role IN ('dependency','archive','model_response','native_arguments',"
        "'history_root','provider_root','memory_root','native_state',"
        "'dependency_manifest','operation_fence'))"
    )
    connection.execute(
        "ALTER TABLE vnext.knowledge_delivery ADD protocol_version text NOT NULL DEFAULT 'v1',"
        "ADD handoff_id text,ADD handoff_channel text,ADD handoff_at timestamptz,"
        "ADD CONSTRAINT knowledge_delivery_protocol_check CHECK(protocol_version IN ('v1','v2')),"
        "ADD CONSTRAINT knowledge_delivery_handoff_channel_check "
        "CHECK(handoff_channel IS NULL OR handoff_channel IN ('initial_input','function_result'))"
    )
    connection.execute(
        """DO $$ DECLARE item record; BEGIN
        FOR item IN SELECT conname FROM pg_constraint
          WHERE conrelid='vnext.knowledge_delivery'::regclass AND contype='c'
          AND pg_get_constraintdef(oid) LIKE '%state%'
        LOOP EXECUTE format('ALTER TABLE vnext.knowledge_delivery DROP CONSTRAINT %I',item.conname); END LOOP;
        END $$"""
    )
    connection.execute(
        "ALTER TABLE vnext.knowledge_delivery ADD CONSTRAINT knowledge_delivery_state_check "
        "CHECK(state IN ('prepared','attached','returned_to_framework')),"
        "ADD CONSTRAINT knowledge_delivery_protocol_state_check CHECK("
        "(protocol_version='v1' AND ((state='prepared' AND attached_manifest_ref IS NULL "
        "AND attached_at IS NULL AND handoff_id IS NULL AND handoff_channel IS NULL AND handoff_at IS NULL) "
        "OR (state='attached' AND attached_manifest_ref IS NOT NULL AND attached_at IS NOT NULL "
        "AND handoff_id IS NULL AND handoff_channel IS NULL AND handoff_at IS NULL))) OR "
        "(protocol_version='v2' AND attached_manifest_ref IS NULL AND attached_at IS NULL AND "
        "((state='prepared' AND handoff_id IS NULL AND handoff_channel IS NULL AND handoff_at IS NULL) OR "
        "(state='returned_to_framework' AND handoff_id IS NOT NULL AND handoff_channel IS NOT NULL "
        "AND handoff_at IS NOT NULL))))"
    )
    connection.execute(
        "CREATE UNIQUE INDEX knowledge_delivery_handoff_id ON vnext.knowledge_delivery"
        "(tenant_id,project_id,task_id,handoff_id) WHERE handoff_id IS NOT NULL"
    )
    connection.execute(
        sql.SQL(
            "GRANT UPDATE(protocol_version,state,handoff_id,handoff_channel,handoff_at) "
            "ON vnext.knowledge_delivery TO {}"
        ).format(sql.Identifier(application_role))
    )
    connection.execute(
        """CREATE OR REPLACE FUNCTION vnext.record_session_stage(
          t text,p text,k text,stage text,work text,session text,runid text,
          hid text,hrev numeric,pid text,prev numeric,mid text,mrev numeric,
          graph text,graph_level integer,capref text,capdigest text)
        RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE level integer; saved vnext.session_stage;
        BEGIN
          SELECT clearance INTO level FROM vnext.task_access WHERE
            (tenant_id,project_id,task_id,subject)=(t,p,k,current_setting('wuji.subject',true)) AND can_read;
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
            OR NOT EXISTS(SELECT 1 FROM vnext.session_object object WHERE
              object.tenant_id=t AND object.project_id=p AND object.task_id=k
              AND object.agent_run_id=runid AND object.writer_token_id=current_setting('wuji.token_id',true)
              GROUP BY object.tenant_id HAVING count(*) FILTER(WHERE
                (object.artifact_id,object.artifact_revision,object.role) IN
                  ((hid,hrev,'history_root'),(pid,prev,'provider_root'),(mid,mrev,'memory_root'))) = 3
                OR count(*) FILTER(WHERE
                (object.artifact_id,object.artifact_revision,object.role) IN
                  ((hid,hrev,'native_state'),(pid,prev,'dependency_manifest'),(mid,mrev,'operation_fence'))) = 3)
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
        END $$"""
    )
    connection.execute(
        """CREATE OR REPLACE FUNCTION vnext.guard_session_manifest_insert()
        RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE body jsonb:=NEW.manifest_json::jsonb;
        BEGIN
          IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
          IF body->>'schema_version'='wuji.session.native.v2' THEN
            PERFORM * FROM vnext.check_session_stage_for_publish(
              NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.work_item_id,NEW.session_id,NEW.owner_run_id,
              body->'native_state_ref'->>'id',(body->'native_state_ref'->>'version')::numeric,
              body->'dependency_manifest_ref'->>'id',(body->'dependency_manifest_ref'->>'version')::numeric,
              body->'operation_fence_ref'->>'id',(body->'operation_fence_ref'->>'version')::numeric,
              NEW.graph_digest,NEW.capability_ref,NEW.capability_digest);
          ELSE
            PERFORM * FROM vnext.check_session_stage_for_publish(
              NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.work_item_id,NEW.session_id,NEW.owner_run_id,
              body->'history_root'->>'id',(body->'history_root'->>'version')::numeric,
              body->'provider_state_ref'->>'id',(body->'provider_state_ref'->>'version')::numeric,
              body->'memory_manifest_ref'->>'id',(body->'memory_manifest_ref'->>'version')::numeric,
              NEW.graph_digest,NEW.capability_ref,NEW.capability_digest);
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        """DO $$ DECLARE body text; old_expr text := $q$manifest.manifest_json::jsonb->>'recovery_class'='approval_boundary'$q$;
        BEGIN body:=pg_get_functiondef('vnext.settle_session_input_boundary(text,text,text,text,text,text)'::regprocedure);
          IF strpos(body,old_expr)=0 THEN RAISE EXCEPTION 'Session input settlement guard changed'; END IF;
          body:=replace(body,old_expr,$q$COALESCE(manifest.manifest_json::jsonb->>'recovery_class',manifest.manifest_json::jsonb->>'boundary_kind') IN ('approval_boundary','approval_wait')$q$);
          EXECUTE body;
        END $$"""
    )
    connection.execute(
        """DO $$ DECLARE body text; old_expr text := $q$manifest.manifest_json::jsonb->>'recovery_class'='approval_boundary'$q$;
        BEGIN body:=pg_get_functiondef('vnext.revoke_session_writer_on_exit()'::regprocedure);
          IF strpos(body,old_expr)=0 THEN RAISE EXCEPTION 'Session writer exit guard changed'; END IF;
          body:=replace(body,old_expr,$q$COALESCE(manifest.manifest_json::jsonb->>'recovery_class',manifest.manifest_json::jsonb->>'boundary_kind') IN ('approval_boundary','approval_wait')$q$);
          EXECUTE body;
        END $$"""
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )
