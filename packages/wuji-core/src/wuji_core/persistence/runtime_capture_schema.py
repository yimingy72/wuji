"""M2c Task-level capture sessions, items and external terminal observations."""

from psycopg import sql

from wuji_core.persistence.workspace_bundle_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0039_runtime_capture"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
F = f"FOREIGN KEY({O}) REFERENCES vnext.task({O})"
SCOPE = "vnext.in_scope(tenant_id,project_id,task_id,access_level)"


def _artifact_source_constraint(connection):
    matches = connection.execute(
        """SELECT conname FROM pg_constraint
        WHERE conrelid='vnext.artifact'::regclass AND contype='c'
          AND pg_get_constraintdef(oid) LIKE '%agent_run_id IS NULL%'
          AND pg_get_constraintdef(oid) LIKE '%writer_subject IS NULL%'
          AND pg_get_constraintdef(oid) LIKE '%tool_attempt_id IS NOT NULL%'"""
    ).fetchall()
    if len(matches) != 1:
        raise ValueError("current Artifact source constraint was not found exactly once")
    return matches[0][0]


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0038_workspace_bundle":
        raise ValueError("Runtime capture migration parent changed")
    app = sql.Identifier(application_role)
    connection.execute(
        f"""CREATE TABLE vnext.capture_session({S},capture_session_id text NOT NULL,
        runtime_attempt numeric NOT NULL CHECK(runtime_attempt>=1 AND runtime_attempt=trunc(runtime_attempt)),
        execution_epoch numeric NOT NULL CHECK(execution_epoch>=1 AND execution_epoch=trunc(execution_epoch)),
        pod_uid text NOT NULL CHECK(length(pod_uid) BETWEEN 1 AND 256),
        environment_ref text NOT NULL CHECK(length(environment_ref) BETWEEN 1 AND 256),
        controller_subject text NOT NULL,collector_subject text NOT NULL,evidence_origin text NOT NULL
          CHECK(evidence_origin IN ('live_capture','fixture_capture')),
        capture_layer text NOT NULL CHECK(length(capture_layer) BETWEEN 1 AND 256),
        state text NOT NULL CHECK(state IN ('ready','draining','sealed','failed')),
        binding_digest text NOT NULL CHECK(binding_digest ~ '^[a-f0-9]{{64}}$'),
        status_digest text NOT NULL CHECK(status_digest ~ '^[a-f0-9]{{64}}$'),
        policy_json text NOT NULL CHECK(jsonb_typeof(policy_json::jsonb)='object'),
        policy_digest text NOT NULL CHECK(policy_digest ~ '^[a-f0-9]{{64}}$'),
        ingested_items bigint NOT NULL DEFAULT 0 CHECK(ingested_items>=0),
        retained_bytes bigint NOT NULL DEFAULT 0 CHECK(retained_bytes>=0),
        started_at timestamptz NOT NULL,updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        access_level integer NOT NULL CHECK(access_level>=0),
        PRIMARY KEY({O},capture_session_id),UNIQUE({O},runtime_attempt),{F},
        FOREIGN KEY({O},controller_subject) REFERENCES vnext.task_access({O},subject),
        FOREIGN KEY({O},collector_subject) REFERENCES vnext.task_access({O},subject))"""
    )
    connection.execute(
        f"""CREATE TABLE vnext.capture_item({S},capture_session_id text NOT NULL,
        item_seq bigint NOT NULL CHECK(item_seq BETWEEN 1 AND 1000000),
        kind text NOT NULL CHECK(kind IN ('http_exchange','pcap_segment','gap','manifest')),
        completeness text NOT NULL CHECK(completeness IN ('complete','partial','unknown')),
        disposition text NOT NULL CHECK(disposition IN ('accepted','historical_only')),
        item_digest text NOT NULL CHECK(item_digest ~ '^[a-f0-9]{{64}}$'),
        envelope_json text NOT NULL CHECK(jsonb_typeof(envelope_json::jsonb)='object'),
        observation_id text NOT NULL,observation_revision numeric NOT NULL DEFAULT 1
          CHECK(observation_revision=1),received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        observed_at timestamptz NOT NULL,access_level integer NOT NULL CHECK(access_level>=0),
        PRIMARY KEY({O},capture_session_id,item_seq),
        UNIQUE({O},observation_id,observation_revision),
        FOREIGN KEY({O},capture_session_id) REFERENCES vnext.capture_session({O},capture_session_id),{F})"""
    )
    connection.execute(
        f"""CREATE TABLE vnext.runtime_terminal_observation({S},
        terminal_observation_id text NOT NULL,capture_session_id text,
        runtime_attempt numeric NOT NULL CHECK(runtime_attempt>=1 AND runtime_attempt=trunc(runtime_attempt)),
        execution_epoch numeric NOT NULL CHECK(execution_epoch>=1 AND execution_epoch=trunc(execution_epoch)),
        pod_uid text NOT NULL CHECK(length(pod_uid) BETWEEN 1 AND 256),
        container_name text NOT NULL CHECK(container_name ~ '^[a-z][a-z0-9-]{{0,62}}$'),
        source_digest text NOT NULL CHECK(source_digest ~ '^[a-f0-9]{{64}}$'),
        document_json text NOT NULL CHECK(jsonb_typeof(document_json::jsonb)='object'),
        controller_subject text NOT NULL,observed_at timestamptz NOT NULL,
        access_level integer NOT NULL CHECK(access_level>=0),
        PRIMARY KEY({O},terminal_observation_id),
        UNIQUE({O},runtime_attempt,pod_uid,container_name),
        FOREIGN KEY({O},capture_session_id) REFERENCES vnext.capture_session({O},capture_session_id),
        FOREIGN KEY({O},controller_subject) REFERENCES vnext.task_access({O},subject),{F})"""
    )

    old = _artifact_source_constraint(connection)
    connection.execute(
        sql.SQL("ALTER TABLE vnext.artifact DROP CONSTRAINT {}").format(
            sql.Identifier(old)
        )
    )
    connection.execute(
        f"""ALTER TABLE vnext.artifact ADD COLUMN capture_session_id text,
        ADD FOREIGN KEY({O},capture_session_id)
          REFERENCES vnext.capture_session({O},capture_session_id),
        ADD CONSTRAINT artifact_source_binding CHECK(
          (provenance='model_output' AND agent_run_id IS NOT NULL
            AND writer_subject IS NOT NULL AND tool_attempt_id IS NULL
            AND capture_session_id IS NULL)
          OR (provenance='capture' AND agent_run_id IS NULL
            AND writer_subject IS NULL
            AND num_nonnulls(tool_attempt_id,capture_session_id)=1)
          OR (provenance='import' AND agent_run_id IS NULL
            AND writer_subject IS NULL AND tool_attempt_id IS NOT NULL
            AND capture_session_id IS NULL))"""
    )
    connection.execute(
        f"""ALTER TABLE vnext.observation ALTER COLUMN tool_attempt_id DROP NOT NULL,
        ADD COLUMN capture_session_id text,ADD COLUMN capture_item_seq bigint,
        ADD FOREIGN KEY({O},capture_session_id)
          REFERENCES vnext.capture_session({O},capture_session_id),
        ADD CONSTRAINT observation_source_binding CHECK(
          (tool_attempt_id IS NOT NULL AND capture_session_id IS NULL
            AND capture_item_seq IS NULL)
          OR (tool_attempt_id IS NULL AND capture_session_id IS NOT NULL
            AND capture_item_seq BETWEEN 1 AND 1000000)),
        ADD UNIQUE({O},capture_session_id,capture_item_seq)"""
    )
    connection.execute(
        f"""ALTER TABLE vnext.capture_item ADD FOREIGN KEY(
        {O},observation_id,observation_revision) REFERENCES vnext.observation(
        {O},entity_id,revision) DEFERRABLE INITIALLY DEFERRED"""
    )

    connection.execute(
        """CREATE FUNCTION vnext.guard_capture_session() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE taskrow vnext.task; receiver vnext.scheduler_receiver;
          caller vnext.task_access; collector vnext.task_access;
          controller vnext.task_pod_controller;config jsonb;expected_policy jsonb;
          lock_key bigint;capture_lock_key bigint; BEGIN
          lock_key:=hashtextextended(json_build_array(
            'wuji.vnext.task-pod'::text,NEW.tenant_id::text,
            NEW.task_id::text)::text,0);
          capture_lock_key:=hashtextextended(json_build_array(
            'wuji.vnext.capture-session'::text,NEW.tenant_id::text,
            NEW.project_id::text,NEW.task_id::text,
            NEW.capture_session_id::text)::text,0);
          IF TG_OP='UPDATE' AND pg_trigger_depth()>1
             AND (to_jsonb(NEW)-'ingested_items'-'retained_bytes'-'updated_at')
                 IS NOT DISTINCT FROM
                 (to_jsonb(OLD)-'ingested_items'-'retained_bytes'-'updated_at')
             AND (
               (current_setting('wuji.capture',true)='true' AND (
                 (NEW.ingested_items=OLD.ingested_items
                   AND NEW.retained_bytes>=OLD.retained_bytes)
                 OR (NEW.ingested_items=OLD.ingested_items+1
                   AND NEW.retained_bytes=OLD.retained_bytes)))
               OR (current_setting('wuji.gc',true)='true'
                 AND NEW.ingested_items=OLD.ingested_items
                 AND NEW.retained_bytes<=OLD.retained_bytes))
          THEN NEW.updated_at:=clock_timestamp(); RETURN NEW; END IF;
          SELECT * INTO taskrow FROM vnext.task WHERE
            (tenant_id,project_id,task_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id);
          SELECT * INTO receiver FROM vnext.scheduler_receiver WHERE
            (tenant_id,project_id,task_id,runtime_attempt)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.runtime_attempt);
          SELECT * INTO caller FROM vnext.task_access WHERE
            (tenant_id,project_id,task_id,subject)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.controller_subject);
          SELECT * INTO collector FROM vnext.task_access WHERE
            (tenant_id,project_id,task_id,subject)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.collector_subject);
          SELECT * INTO controller FROM vnext.task_pod_controller WHERE
            (tenant_id,project_id,task_id,controller_subject,login_role,enabled)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.controller_subject,
             session_user::name,true);
          SELECT document_json::jsonb INTO config FROM vnext.admission_config WHERE
            (tenant_id,project_id,task_id)=(NEW.tenant_id,NEW.project_id,NEW.task_id);
          expected_policy:=config->'runtime'->'capture_policy';
          IF NOT COALESCE(vnext.in_scope(
               NEW.tenant_id,NEW.project_id,NEW.task_id),false)
             OR current_setting('wuji.admit',true) IS DISTINCT FROM 'true'
             OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
             OR NEW.controller_subject IS DISTINCT FROM current_setting('wuji.subject',true)
             OR taskrow IS NULL OR receiver IS NULL OR caller IS NULL
             OR collector IS NULL OR controller IS NULL
             OR NOT caller.can_read OR NOT caller.can_admit OR NOT caller.can_observe
             OR NOT collector.can_read OR NOT (collector.can_capture OR collector.can_settle)
             OR NOT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory'
               AND pid=pg_backend_pid() AND granted AND mode='ExclusiveLock'
               AND objsubid=1
               AND classid::bigint=((lock_key >> 32)&4294967295)
               AND objid::bigint=(lock_key&4294967295)
               AND database=(SELECT oid FROM pg_database
                 WHERE datname=current_database()))
             OR (TG_OP='INSERT' AND (NEW.runtime_attempt IS DISTINCT FROM taskrow.runtime_attempt
               OR NEW.execution_epoch IS DISTINCT FROM taskrow.execution_epoch))
             OR receiver.pod_uid IS NULL
             OR NEW.pod_uid IS DISTINCT FROM receiver.pod_uid
             OR NEW.environment_ref IS DISTINCT FROM receiver.environment_ref
             OR (TG_OP='INSERT' AND (expected_policy IS NULL
               OR NEW.policy_json::jsonb<>expected_policy
               OR NEW.policy_digest<>encode(sha256(convert_to(
                    vnext.canonical_jsonb_text(expected_policy),'UTF8')),'hex')))
          THEN RAISE EXCEPTION 'current Runtime capture binding required'
            USING ERRCODE='42501'; END IF;
          PERFORM pg_advisory_xact_lock(capture_lock_key);
          IF TG_OP='UPDATE' AND (
               NEW.capture_session_id IS DISTINCT FROM OLD.capture_session_id
               OR NEW.controller_subject IS DISTINCT FROM OLD.controller_subject
               OR NEW.runtime_attempt IS DISTINCT FROM OLD.runtime_attempt
               OR NEW.execution_epoch IS DISTINCT FROM OLD.execution_epoch
               OR NEW.pod_uid IS DISTINCT FROM OLD.pod_uid
               OR NEW.environment_ref IS DISTINCT FROM OLD.environment_ref
               OR NEW.collector_subject IS DISTINCT FROM OLD.collector_subject
               OR NEW.evidence_origin IS DISTINCT FROM OLD.evidence_origin
               OR NEW.capture_layer IS DISTINCT FROM OLD.capture_layer
               OR NEW.binding_digest IS DISTINCT FROM OLD.binding_digest
               OR NEW.policy_json::jsonb IS DISTINCT FROM OLD.policy_json::jsonb
               OR NEW.policy_digest IS DISTINCT FROM OLD.policy_digest
               OR NEW.ingested_items IS DISTINCT FROM OLD.ingested_items
               OR NEW.retained_bytes IS DISTINCT FROM OLD.retained_bytes
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.access_level IS DISTINCT FROM OLD.access_level
               OR NOT ((OLD.state='ready' AND NEW.state IN ('ready','draining','sealed','failed'))
                 OR (OLD.state='draining' AND NEW.state IN ('draining','sealed','failed'))
                 OR (OLD.state=NEW.state AND OLD.state IN ('sealed','failed'))))
          THEN RAISE EXCEPTION 'Runtime capture session binding is immutable'
            USING ERRCODE='23514'; END IF;
          NEW.updated_at:=clock_timestamp(); RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER capture_session_guard BEFORE INSERT OR UPDATE ON "
        "vnext.capture_session FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_capture_session()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.require_runtime_capture_mutation(
          t text,p text,k text,c text) RETURNS void LANGUAGE plpgsql
        SET search_path=pg_catalog AS $$ DECLARE s vnext.capture_session;
        acl vnext.task_access; taskrow vnext.task; BEGIN
          SELECT * INTO s FROM vnext.capture_session WHERE
            (tenant_id,project_id,task_id,capture_session_id)=(t,p,k,c);
          SELECT * INTO acl FROM vnext.task_access WHERE
            (tenant_id,project_id,task_id,subject)=
            (t,p,k,current_setting('wuji.subject',true));
          SELECT * INTO taskrow FROM vnext.task WHERE
            (tenant_id,project_id,task_id)=(t,p,k);
          IF current_setting('wuji.capture',true) IS DISTINCT FROM 'true'
             OR NOT COALESCE(vnext.in_scope(t,p,k),false)
             OR s IS NULL OR acl IS NULL OR taskrow IS NULL
             OR s.collector_subject IS DISTINCT FROM current_setting('wuji.subject',true)
             OR NOT acl.can_read
             OR NOT ((taskrow.runtime_attempt=s.runtime_attempt
                   AND taskrow.execution_epoch=s.execution_epoch AND acl.can_capture)
               OR acl.can_settle)
          THEN RAISE EXCEPTION 'bound Runtime capture authority required'
            USING ERRCODE='42501'; END IF;
        END $$"""
    )
    connection.execute(
        """CREATE OR REPLACE FUNCTION vnext.require_artifact_mutation(
          t text,p text,k text,i text,v numeric) RETURNS void LANGUAGE plpgsql
        SET search_path=pg_catalog AS $$ DECLARE a vnext.artifact%ROWTYPE; BEGIN
          SELECT * INTO a FROM vnext.artifact WHERE tenant_id=t AND project_id=p
            AND task_id=k AND entity_id=i AND revision=v;
          IF NOT FOUND THEN RAISE EXCEPTION 'artifact absent'
            USING ERRCODE='42501'; END IF;
          IF a.agent_run_id IS NOT NULL THEN
            PERFORM vnext.require_model_mutation(t,p,k,a.agent_run_id,a.writer_subject);
          ELSIF a.capture_session_id IS NOT NULL THEN
            PERFORM vnext.require_runtime_capture_mutation(t,p,k,a.capture_session_id);
          ELSE PERFORM vnext.require_evidence_mutation(t,p,k,a.tool_attempt_id);
          END IF;
        END $$"""
    )
    connection.execute(
        """CREATE OR REPLACE FUNCTION vnext.check_artifact_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF NEW.agent_run_id IS NOT NULL THEN
            PERFORM vnext.require_model_mutation(NEW.tenant_id,NEW.project_id,
              NEW.task_id,NEW.agent_run_id,NEW.writer_subject);
          ELSIF NEW.capture_session_id IS NOT NULL THEN
            PERFORM vnext.require_runtime_capture_mutation(NEW.tenant_id,
              NEW.project_id,NEW.task_id,NEW.capture_session_id);
          ELSE PERFORM vnext.require_evidence_mutation(NEW.tenant_id,
            NEW.project_id,NEW.task_id,NEW.tool_attempt_id); END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        """CREATE FUNCTION vnext.account_runtime_capture_artifact()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE s vnext.capture_session;lock_key bigint;BEGIN
          IF NEW.capture_session_id IS NULL THEN RETURN NULL; END IF;
          PERFORM vnext.require_runtime_capture_mutation(NEW.tenant_id,
            NEW.project_id,NEW.task_id,NEW.capture_session_id);
          lock_key:=hashtextextended(json_build_array(
            'wuji.vnext.capture-session'::text,NEW.tenant_id::text,
            NEW.project_id::text,NEW.task_id::text,
            NEW.capture_session_id::text)::text,0);
          PERFORM pg_advisory_xact_lock(lock_key);
          SELECT * INTO s FROM vnext.capture_session WHERE
            (tenant_id,project_id,task_id,capture_session_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,
             NEW.capture_session_id) FOR UPDATE;
          IF s IS NULL OR s.retained_bytes+NEW.size_bytes>
               (s.policy_json::jsonb->>'max_session_bytes')::bigint
          THEN RAISE EXCEPTION 'Runtime capture byte limit exceeded'
            USING ERRCODE='22023'; END IF;
          UPDATE vnext.capture_session SET retained_bytes=retained_bytes+NEW.size_bytes
            WHERE (tenant_id,project_id,task_id,capture_session_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.capture_session_id);
          RETURN NULL;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER runtime_capture_artifact_account AFTER INSERT ON "
        "vnext.artifact FOR EACH ROW WHEN (NEW.capture_session_id IS NOT NULL) "
        "EXECUTE FUNCTION vnext.account_runtime_capture_artifact()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.release_runtime_capture_artifact()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        BEGIN
          IF OLD.capture_session_id IS NULL OR OLD.state='tombstoned'
             OR NEW.state<>'tombstoned' THEN RETURN NULL; END IF;
          IF current_setting('wuji.gc',true) IS DISTINCT FROM 'true'
             OR NOT COALESCE(vnext.in_scope(
               OLD.tenant_id,OLD.project_id,OLD.task_id),false)
          THEN RAISE EXCEPTION 'Runtime capture GC authority required'
            USING ERRCODE='42501'; END IF;
          PERFORM pg_advisory_xact_lock(hashtextextended(json_build_array(
            'wuji.vnext.capture-session'::text,OLD.tenant_id::text,
            OLD.project_id::text,OLD.task_id::text,
            OLD.capture_session_id::text)::text,0));
          UPDATE vnext.capture_session SET
            retained_bytes=retained_bytes-OLD.size_bytes
            WHERE (tenant_id,project_id,task_id,capture_session_id)=
            (OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.capture_session_id)
            AND retained_bytes>=OLD.size_bytes;
          IF NOT FOUND THEN RAISE EXCEPTION 'Runtime capture byte counter drift'
            USING ERRCODE='23514'; END IF;
          RETURN NULL;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER runtime_capture_artifact_release AFTER UPDATE ON "
        "vnext.artifact FOR EACH ROW WHEN (OLD.capture_session_id IS NOT NULL "
        "AND OLD.state<>'tombstoned' AND NEW.state='tombstoned') EXECUTE "
        "FUNCTION vnext.release_runtime_capture_artifact()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_capture_item() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE s vnext.capture_session;lock_key bigint;BEGIN
          lock_key:=hashtextextended(json_build_array(
            'wuji.vnext.capture-session'::text,NEW.tenant_id::text,
            NEW.project_id::text,NEW.task_id::text,
            NEW.capture_session_id::text)::text,0);
          PERFORM pg_advisory_xact_lock(lock_key);
          SELECT * INTO s FROM vnext.capture_session WHERE
          (tenant_id,project_id,task_id,capture_session_id)=
          (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.capture_session_id)
          FOR UPDATE;
          PERFORM vnext.require_runtime_capture_mutation(NEW.tenant_id,
            NEW.project_id,NEW.task_id,NEW.capture_session_id);
          IF s IS NULL OR NEW.access_level IS DISTINCT FROM s.access_level
             OR s.ingested_items+1>(s.policy_json::jsonb->>'max_items')::bigint
             OR NEW.item_seq<>s.ingested_items+1
          THEN
            RAISE EXCEPTION 'Runtime capture item limit exceeded'
              USING ERRCODE='22023'; END IF;
          UPDATE vnext.capture_session SET ingested_items=ingested_items+1
            WHERE (tenant_id,project_id,task_id,capture_session_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.capture_session_id);
          RETURN NEW; END $$"""
    )
    connection.execute(
        "CREATE TRIGGER capture_item_guard BEFORE INSERT ON vnext.capture_item "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_capture_item()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_runtime_terminal_observation()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE controller vnext.task_pod_controller;caller vnext.task_access;
          receiver vnext.scheduler_receiver;session vnext.capture_session;
          taskrow vnext.task;lock_key bigint;BEGIN
          lock_key:=hashtextextended(json_build_array(
            'wuji.vnext.task-pod'::text,NEW.tenant_id::text,
            NEW.task_id::text)::text,0);
          SELECT * INTO controller FROM vnext.task_pod_controller WHERE
            (tenant_id,project_id,task_id,controller_subject,login_role,enabled)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.controller_subject,
             session_user::name,true);
          SELECT * INTO caller FROM vnext.task_access WHERE
            (tenant_id,project_id,task_id,subject)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.controller_subject);
          SELECT * INTO receiver FROM vnext.scheduler_receiver WHERE
            (tenant_id,project_id,task_id,runtime_attempt)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.runtime_attempt);
          SELECT * INTO taskrow FROM vnext.task WHERE
            (tenant_id,project_id,task_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id);
          IF NEW.capture_session_id IS NOT NULL THEN
            SELECT * INTO session FROM vnext.capture_session WHERE
              (tenant_id,project_id,task_id,capture_session_id)=
              (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.capture_session_id);
          END IF;
          IF NOT COALESCE(vnext.in_scope(
               NEW.tenant_id,NEW.project_id,NEW.task_id),false)
             OR current_setting('wuji.control',true) IS DISTINCT FROM 'true'
             OR COALESCE(current_setting('wuji.request_purpose',true),'')<>''
             OR NEW.controller_subject IS DISTINCT FROM current_setting('wuji.subject',true)
             OR controller IS NULL OR caller IS NULL OR taskrow IS NULL
             OR NOT caller.can_read OR NOT caller.can_control OR NOT caller.can_observe
             OR NEW.runtime_attempt>taskrow.runtime_attempt
             OR NEW.execution_epoch>taskrow.execution_epoch
             OR (receiver IS NOT NULL AND (receiver.pod_uid IS NULL
               OR NEW.pod_uid IS DISTINCT FROM receiver.pod_uid))
             OR NOT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory'
               AND pid=pg_backend_pid() AND granted AND mode='ExclusiveLock'
               AND objsubid=1
               AND classid::bigint=((lock_key >> 32)&4294967295)
               AND objid::bigint=(lock_key&4294967295)
               AND database=(SELECT oid FROM pg_database
                 WHERE datname=current_database()))
             OR (NEW.capture_session_id IS NOT NULL AND (session IS NULL
               OR session.runtime_attempt IS DISTINCT FROM NEW.runtime_attempt
               OR session.execution_epoch IS DISTINCT FROM NEW.execution_epoch
               OR session.pod_uid IS DISTINCT FROM NEW.pod_uid
               OR session.controller_subject IS DISTINCT FROM NEW.controller_subject))
          THEN RAISE EXCEPTION 'trusted Runtime controller required'
            USING ERRCODE='42501'; END IF; RETURN NEW; END $$"""
    )
    connection.execute(
        "CREATE TRIGGER runtime_terminal_observation_guard BEFORE INSERT ON "
        "vnext.runtime_terminal_observation FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_runtime_terminal_observation()"
    )

    for table in ("capture_session", "capture_item", "runtime_terminal_observation"):
        connection.execute(f"ALTER TABLE vnext.{table} ENABLE ROW LEVEL SECURITY")
        connection.execute(
            f"CREATE POLICY scoped_read ON vnext.{table} FOR SELECT USING({SCOPE})"
        )
        connection.execute(
            sql.SQL(f"GRANT SELECT ON vnext.{table} TO {{}}").format(app)
        )
    connection.execute(
        f"CREATE POLICY controller_insert ON vnext.capture_session FOR INSERT WITH CHECK({SCOPE} "
        "AND current_setting('wuji.admit',true)='true' "
        "AND controller_subject=current_setting('wuji.subject',true))"
    )
    connection.execute(
        f"CREATE POLICY controller_update ON vnext.capture_session FOR UPDATE USING({SCOPE} "
        "AND current_setting('wuji.admit',true)='true' "
        "AND controller_subject=current_setting('wuji.subject',true)) WITH CHECK(" + SCOPE + ")"
    )
    connection.execute(
        f"CREATE POLICY capture_insert ON vnext.capture_item FOR INSERT WITH CHECK({SCOPE} "
        "AND current_setting('wuji.capture',true)='true')"
    )
    connection.execute(
        f"CREATE POLICY control_insert ON vnext.runtime_terminal_observation FOR INSERT WITH CHECK({SCOPE} "
        "AND current_setting('wuji.control',true)='true' "
        "AND controller_subject=current_setting('wuji.subject',true))"
    )
    connection.execute(
        sql.SQL("GRANT INSERT ON vnext.capture_session TO {}").format(app)
    )
    connection.execute(
        sql.SQL("GRANT UPDATE(state,status_digest,updated_at) ON vnext.capture_session TO {}").format(app)
    )
    connection.execute(sql.SQL("GRANT INSERT ON vnext.capture_item TO {}").format(app))
    connection.execute(
        sql.SQL("GRANT INSERT ON vnext.runtime_terminal_observation TO {}").format(app)
    )
    for signature in (
        "guard_capture_session()",
        "require_runtime_capture_mutation(text,text,text,text)",
        "account_runtime_capture_artifact()",
        "release_runtime_capture_artifact()",
        "guard_capture_item()",
        "guard_runtime_terminal_observation()",
    ):
        connection.execute(f"REVOKE ALL ON FUNCTION vnext.{signature} FROM PUBLIC")
        connection.execute(
            sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{signature} TO {{}}").format(app)
        )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
