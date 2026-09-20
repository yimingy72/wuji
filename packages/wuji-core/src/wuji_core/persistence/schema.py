"""Independent migration head. SQL is applied by the migration owner only.

PostgreSQL is the authority for ownership, version existence and DAG integrity.
The application role cannot create authority parents, alter claims, or grant ACLs.
"""

from psycopg import sql

BASE_HEAD = "vnext_0001_p03"
EVIDENCE_HEAD = "vnext_0002_p03_evidence_authority"
from wuji_core.persistence.knowledge_schema import (
    HEAD as KNOWLEDGE_HEAD,
    VISIBILITY_HEAD,
    FRESHNESS_HEAD,
    upgrade as upgrade_knowledge,
    upgrade_visibility,
    upgrade_input_freshness,
)
from wuji_core.persistence.control_schema import (
    HEAD as CONTROL_HEAD,
    upgrade as upgrade_control,
)
from wuji_core.persistence.admission_schema import (
    HEAD as ADMISSION_HEAD,
    upgrade as upgrade_admission,
)
from wuji_core.persistence.admission_hardening_schema import (
    HEAD as ADMISSION_HARDENING_HEAD,
    upgrade as upgrade_admission_hardening,
)
from wuji_core.persistence.admission_request_guard_schema import (
    HEAD as ADMISSION_REQUEST_GUARD_HEAD,
    upgrade as upgrade_admission_request_guards,
)
from wuji_core.persistence.scheduler_schema import (
    HEAD as SCHEDULER_HEAD,
    upgrade as upgrade_scheduler,
)
from wuji_core.persistence.dispatch_fairness_schema import (
    HEAD as DISPATCH_FAIRNESS_HEAD,
    upgrade as upgrade_dispatch_fairness,
)
from wuji_core.persistence.projection_schema import (
    HEAD as PROJECTION_HEAD,
    upgrade as upgrade_projection,
)
from wuji_core.persistence.retained_result_schema import (
    HEAD as RETAINED_RESULT_HEAD,
    upgrade as upgrade_retained_results,
)
from wuji_core.persistence.session_schema import (
    HEAD as SESSION_HEAD,
    upgrade as upgrade_sessions,
)
from wuji_core.persistence.control_api_schema import (
    HEAD as CONTROL_API_HEAD,
    upgrade as upgrade_control_api,
)
from wuji_core.persistence.session_writer_exit_schema import (
    HEAD as SESSION_WRITER_EXIT_HEAD,
    upgrade as upgrade_session_writer_exit,
)
from wuji_core.persistence.pod_receiver_schema import (
    HEAD as POD_RECEIVER_HEAD,
    upgrade as upgrade_pod_receivers,
)
from wuji_core.persistence.layout_schema import (
    HEAD as LAYOUT_HEAD,
    upgrade as upgrade_layouts,
)
from wuji_core.persistence.task_creation_schema import (
    HEAD as TASK_CREATION_HEAD,
    upgrade as upgrade_task_creation,
)
from wuji_core.persistence.run_settlement_close_schema import (
    HEAD as RUN_SETTLEMENT_HEAD,
    upgrade as upgrade_run_settlement_close,
)
from wuji_core.persistence.environment_settlement_schema import (
    HEAD as ENVIRONMENT_SETTLEMENT_HEAD,
    upgrade as upgrade_environment_settlement,
)
from wuji_core.persistence.completion_schema import (
    HEAD as COMPLETION_HEAD,
    upgrade as upgrade_completion,
)
from wuji_core.persistence.judgment_schema import (
    HEAD as JUDGMENT_HEAD,
    upgrade as upgrade_judgments,
)
from wuji_core.persistence.report_schema import (
    HEAD as REPORT_HEAD,
    upgrade as upgrade_reports,
)
from wuji_core.persistence.view_stream_schema import (
    HEAD as VIEW_STREAM_HEAD,
    upgrade as upgrade_view_stream,
)
from wuji_core.persistence.delivery_schema import (
    HEAD as DELIVERY_HEAD,
    upgrade as upgrade_report_delivery,
)
from wuji_core.persistence.retention_schema import (
    HEAD as RETENTION_HEAD,
    upgrade as upgrade_artifact_purge,
)
from wuji_core.persistence.platform_settlement_schema import (
    HEAD as PLATFORM_SETTLEMENT_HEAD,
    upgrade as upgrade_platform_settlement,
)

# The migration chain's newest head; callers assert against this instead of a
# hard-coded historical identifier.
from wuji_core.persistence.launch_schema import HEAD as LAUNCH_HEAD, upgrade as upgrade_task_launch
from wuji_core.persistence.launch_observer_schema import HEAD as LAUNCH_OBSERVER_HEAD, upgrade as upgrade_launch_observer

HEAD = LAUNCH_OBSERVER_HEAD

OWNER = "tenant_id,project_id,task_id"
SCOPE_COLUMNS = (
    "tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL"
)
TASK_FK = f"FOREIGN KEY ({OWNER}) REFERENCES vnext.task({OWNER})"
REVISION = "numeric NOT NULL CHECK (revision >= 1 AND revision = trunc(revision))"


def _parent(name, key, columns, extra=""):
    return f"CREATE TABLE vnext.{name} ({SCOPE_COLUMNS}, {key} text NOT NULL, {columns}, PRIMARY KEY ({OWNER},{key}), {TASK_FK}{extra})"


def statements():
    yield "CREATE SCHEMA IF NOT EXISTS vnext"
    yield "CREATE TABLE vnext.schema_migration(head text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT clock_timestamp())"
    yield "CREATE TABLE vnext.tenant(tenant_id text PRIMARY KEY)"
    yield "CREATE TABLE vnext.project(tenant_id text NOT NULL REFERENCES vnext.tenant,project_id text NOT NULL,PRIMARY KEY(tenant_id,project_id))"
    yield f"""CREATE TABLE vnext.task ({SCOPE_COLUMNS}, PRIMARY KEY({OWNER}), UNIQUE(tenant_id,task_id),
        FOREIGN KEY(tenant_id,project_id) REFERENCES vnext.project(tenant_id,project_id),
        execution_allowed boolean NOT NULL DEFAULT true,
        execution_epoch numeric NOT NULL DEFAULT 1 CHECK(execution_epoch>=1 AND execution_epoch=trunc(execution_epoch)),
        runtime_attempt numeric NOT NULL DEFAULT 1 CHECK(runtime_attempt>=1 AND runtime_attempt=trunc(runtime_attempt)),
        board_revision numeric NOT NULL DEFAULT 0, event_seq numeric NOT NULL DEFAULT 0,
        observation_count numeric NOT NULL DEFAULT 0,
        CHECK(board_revision>=0 AND event_seq>=0 AND observation_count>=0))"""
    yield f"""CREATE TABLE vnext.task_access ({SCOPE_COLUMNS}, subject text NOT NULL,
        can_read boolean NOT NULL DEFAULT false, can_write boolean NOT NULL DEFAULT false,
        can_capture boolean NOT NULL DEFAULT false, can_settle boolean NOT NULL DEFAULT false,
        can_gc boolean NOT NULL DEFAULT false, can_assess boolean NOT NULL DEFAULT false,
        clearance integer NOT NULL DEFAULT 0 CHECK(clearance>=0), PRIMARY KEY({OWNER},subject),{TASK_FK})"""
    yield _parent(
        "work_item",
        "work_item_id",
        "state text NOT NULL DEFAULT 'ready', revision numeric NOT NULL DEFAULT 1",
    )
    yield _parent(
        "agent_run",
        "agent_run_id",
        """work_item_id text NOT NULL, receiver_id text NOT NULL,
        execution_epoch numeric NOT NULL DEFAULT 1, run_epoch numeric NOT NULL DEFAULT 1,
        runtime_attempt numeric NOT NULL DEFAULT 1, environment_ref text NOT NULL,
        model_mode text NOT NULL CHECK(model_mode IN ('synthetic','real','unknown')),
        execution_allowed boolean NOT NULL DEFAULT true, process_state text NOT NULL DEFAULT 'registered' """,
        f", FOREIGN KEY({OWNER},work_item_id) REFERENCES vnext.work_item({OWNER},work_item_id)",
    )
    yield _parent(
        "tool_call",
        "tool_call_id",
        """session_lineage text NOT NULL, message_id text NOT NULL,
        provider_call_id text NOT NULL, tool_definition_version text NOT NULL""",
        f", UNIQUE({OWNER},session_lineage,message_id,provider_call_id,tool_definition_version)",
    )
    yield _parent(
        "tool_attempt",
        "tool_attempt_id",
        """tool_call_id text NOT NULL, agent_run_id text NOT NULL,
        started_at timestamptz, evidence_origin text NOT NULL CHECK(evidence_origin IN ('live_capture','fixture_capture','imported_unverified')),
        capture_layer text NOT NULL, receipt_json text NOT NULL CHECK(jsonb_typeof(receipt_json::jsonb)='object')""",
        f", FOREIGN KEY({OWNER},tool_call_id) REFERENCES vnext.tool_call({OWNER},tool_call_id), FOREIGN KEY({OWNER},agent_run_id) REFERENCES vnext.agent_run({OWNER},agent_run_id)",
    )
    yield f"""CREATE TABLE vnext.collector_binding ({SCOPE_COLUMNS}, tool_attempt_id text NOT NULL,
        subject text NOT NULL, revoked boolean NOT NULL DEFAULT false, can_settle boolean NOT NULL DEFAULT false,
        PRIMARY KEY({OWNER},tool_attempt_id,subject), FOREIGN KEY({OWNER},tool_attempt_id) REFERENCES vnext.tool_attempt({OWNER},tool_attempt_id))"""
    yield f"""CREATE TABLE vnext.entity_revision_registry ({SCOPE_COLUMNS}, entity_type text NOT NULL,
        entity_id text NOT NULL, revision {REVISION}, access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0),
        PRIMARY KEY({OWNER},entity_type,entity_id,revision), {TASK_FK})"""
    yield f"""CREATE TABLE vnext.claim_revision ({SCOPE_COLUMNS}, entity_id text NOT NULL, revision {REVISION},
        kind text NOT NULL CHECK(kind IN ('observation-summary','hypothesis','derived-conclusion')),
        assertion_role text NOT NULL CHECK(assertion_role IN ('candidate_fact','explanation','hypothesis')),
        text text NOT NULL CHECK(length(text) BETWEEN 1 AND 32768), structured_json text,
        producer_kind text NOT NULL CHECK(producer_kind IN ('agent','human','extractor','import')),
        producer_ref text NOT NULL, limitations_json text NOT NULL DEFAULT '[]',
        access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({OWNER},entity_id,revision), {TASK_FK})"""
    yield f"""CREATE TABLE vnext.artifact ({SCOPE_COLUMNS}, entity_id text NOT NULL, revision {REVISION},
        state text NOT NULL CHECK(state IN ('staged','sealed','tombstoned')), body_removed boolean NOT NULL DEFAULT false, storage_key uuid NOT NULL UNIQUE,
        sha256 text NOT NULL CHECK(sha256 ~ '^[a-f0-9]{{64}}$'), size_bytes bigint NOT NULL CHECK(size_bytes>=0),
        media_type text NOT NULL CHECK(length(media_type) BETWEEN 1 AND 256), tool_attempt_id text NOT NULL,
        provenance text NOT NULL CHECK(provenance IN ('capture','model_output','import')),
        evidence_origin text NOT NULL CHECK(evidence_origin IN ('live_capture','fixture_capture','imported_unverified')),
        capture_layer text NOT NULL, environment_ref text NOT NULL,
        completeness text NOT NULL CHECK(completeness IN ('complete','partial','unknown')),
        conditions_json text NOT NULL DEFAULT '[]', access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0),
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({OWNER},entity_id,revision), FOREIGN KEY({OWNER},tool_attempt_id) REFERENCES vnext.tool_attempt({OWNER},tool_attempt_id),{TASK_FK})"""
    yield f"""CREATE TABLE vnext.observation ({SCOPE_COLUMNS}, entity_id text NOT NULL, revision {REVISION} CHECK(revision=1),
        capture_id text NOT NULL, tool_attempt_id text NOT NULL, collector_ref text NOT NULL,
        capture_layer text NOT NULL, observed_at timestamptz NOT NULL, received_at timestamptz NOT NULL,
        environment_ref text NOT NULL, conditions_json text NOT NULL,
        completeness text NOT NULL CHECK(completeness IN ('complete','partial','unknown')),
        evidence_origin text NOT NULL CHECK(evidence_origin IN ('live_capture','fixture_capture','imported_unverified')),
        access_level integer NOT NULL DEFAULT 0 CHECK(access_level>=0),
        PRIMARY KEY({OWNER},entity_id,revision), UNIQUE({OWNER},capture_id),
        FOREIGN KEY({OWNER},tool_attempt_id,collector_ref) REFERENCES vnext.collector_binding({OWNER},tool_attempt_id,subject),{TASK_FK})"""
    yield f"""CREATE TABLE vnext.observation_artifact ({SCOPE_COLUMNS}, observation_id text NOT NULL,
        observation_revision numeric NOT NULL, ordinal integer NOT NULL CHECK(ordinal>=0 AND ordinal<256),
        artifact_id text NOT NULL, artifact_revision numeric NOT NULL, access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY({OWNER},observation_id,observation_revision,ordinal), UNIQUE({OWNER},observation_id,observation_revision,artifact_id,artifact_revision),
        FOREIGN KEY({OWNER},observation_id,observation_revision) REFERENCES vnext.observation({OWNER},entity_id,revision),
        FOREIGN KEY({OWNER},artifact_id,artifact_revision) REFERENCES vnext.artifact({OWNER},entity_id,revision))"""
    yield f"""CREATE TABLE vnext.assessment ({SCOPE_COLUMNS}, assessment_id text NOT NULL, revision {REVISION} DEFAULT 1,
        claim_id text NOT NULL, claim_revision numeric NOT NULL,
        grounding_state text NOT NULL DEFAULT 'unchecked' CHECK(grounding_state IN ('unchecked','linked','content_checked','invalid')),
        evidence_state text NOT NULL DEFAULT 'unassessed' CHECK(evidence_state IN ('unassessed','supported','contradicted','inconclusive')),
        applicability_state text NOT NULL DEFAULT 'current' CHECK(applicability_state IN ('current','stale','disputed','retracted')),
        method_kind text NOT NULL CHECK(method_kind IN ('deterministic','reproduced_check','human_attestation','model_review')),
        method_version text NOT NULL, reviewer_ref text NOT NULL, reason text NOT NULL,
        conditions_json text NOT NULL DEFAULT '[]', access_level integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        CHECK(NOT(method_kind='model_review' AND evidence_state='supported')),
        PRIMARY KEY({OWNER},assessment_id,revision), FOREIGN KEY({OWNER},claim_id,claim_revision) REFERENCES vnext.claim_revision({OWNER},entity_id,revision))"""
    yield f"""CREATE TABLE vnext.assessment_input ({SCOPE_COLUMNS},assessment_id text NOT NULL,assessment_revision numeric NOT NULL,
        entity_type text NOT NULL,entity_id text NOT NULL,revision numeric NOT NULL,access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY({OWNER},assessment_id,assessment_revision,entity_type,entity_id,revision),
        FOREIGN KEY({OWNER},assessment_id,assessment_revision) REFERENCES vnext.assessment({OWNER},assessment_id,revision),
        FOREIGN KEY({OWNER},entity_type,entity_id,revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision))"""
    yield f"""CREATE TABLE vnext.entity_relation ({SCOPE_COLUMNS},source_type text NOT NULL CHECK(source_type='claim'),
        source_id text NOT NULL,source_revision numeric NOT NULL,
        relation text NOT NULL CHECK(relation IN ('cites','extracted_from','supersedes')),
        target_type text NOT NULL CHECK(target_type IN ('claim','observation','artifact')),target_id text NOT NULL,target_revision numeric NOT NULL,
        access_level integer NOT NULL DEFAULT 0,
        CHECK(relation<>'extracted_from' OR target_type='observation'),
        CHECK(relation<>'supersedes' OR (source_type=target_type AND source_id=target_id AND source_revision>target_revision)),
        PRIMARY KEY({OWNER},source_type,source_id,source_revision,relation,target_type,target_id,target_revision),
        FOREIGN KEY({OWNER},source_type,source_id,source_revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision),
        FOREIGN KEY({OWNER},target_type,target_id,target_revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision))"""
    yield f"""CREATE TABLE vnext.work_dependency ({SCOPE_COLUMNS}, work_item_id text NOT NULL, predecessor_id text NOT NULL,
        condition text NOT NULL CHECK(condition IN ('settled','accepted_result','criterion_satisfied')),
        criterion_type text,criterion_id text,criterion_revision numeric,
        CHECK((condition='criterion_satisfied')=(criterion_id IS NOT NULL)),
        CHECK((criterion_id IS NULL AND criterion_type IS NULL AND criterion_revision IS NULL) OR (criterion_id IS NOT NULL AND criterion_type IS NOT NULL AND criterion_revision IS NOT NULL)),
        PRIMARY KEY({OWNER},work_item_id,predecessor_id),
        FOREIGN KEY({OWNER},work_item_id) REFERENCES vnext.work_item({OWNER},work_item_id),
        FOREIGN KEY({OWNER},predecessor_id) REFERENCES vnext.work_item({OWNER},work_item_id),
        FOREIGN KEY({OWNER},criterion_type,criterion_id,criterion_revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision))"""
    yield f"""CREATE TABLE vnext.evidence_receipt ({SCOPE_COLUMNS},capture_id text NOT NULL,
        operation_kind text NOT NULL DEFAULT 'evidence_ingest' CHECK(operation_kind='evidence_ingest'),
        input_digest text NOT NULL,original_envelope text NOT NULL,
        status text NOT NULL CHECK(status IN ('accepted','historical_only')),
        observation_type text NOT NULL DEFAULT 'observation' CHECK(observation_type='observation'),
        observation_id text NOT NULL,observation_revision numeric NOT NULL,
        receipt_json text NOT NULL,access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY(tenant_id,task_id,operation_kind,capture_id),
        FOREIGN KEY({OWNER},observation_type,observation_id,observation_revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision))"""
    yield f"""CREATE TABLE vnext.outbox ({SCOPE_COLUMNS},event_seq numeric NOT NULL,kind text NOT NULL,
        payload_json text NOT NULL,access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY({OWNER},event_seq),{TASK_FK})"""
    yield f"""CREATE TABLE vnext.publication ({SCOPE_COLUMNS},publication_id text NOT NULL,kind text NOT NULL,
        access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY({OWNER},publication_id),{TASK_FK})"""
    yield f"""CREATE TABLE vnext.publication_ref ({SCOPE_COLUMNS},publication_id text NOT NULL,artifact_id text NOT NULL,
        artifact_revision numeric NOT NULL,access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY({OWNER},publication_id,artifact_id,artifact_revision),
        FOREIGN KEY({OWNER},publication_id) REFERENCES vnext.publication({OWNER},publication_id),
        FOREIGN KEY({OWNER},artifact_id,artifact_revision) REFERENCES vnext.artifact({OWNER},entity_id,revision))"""
    yield f"""CREATE TABLE vnext.artifact_lease ({SCOPE_COLUMNS},artifact_id text NOT NULL,artifact_revision numeric NOT NULL,
        lease_owner text NOT NULL,expires_at timestamptz NOT NULL,access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY({OWNER},artifact_id,artifact_revision,lease_owner),
        FOREIGN KEY({OWNER},artifact_id,artifact_revision) REFERENCES vnext.artifact({OWNER},entity_id,revision))"""
    yield f"""CREATE TABLE vnext.snapshot_manifest ({SCOPE_COLUMNS},snapshot_id text NOT NULL,publication_id text NOT NULL,
        query_json text NOT NULL,query_digest text NOT NULL,access_digest text NOT NULL,manifest_json text NOT NULL,
        access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL,expires_at timestamptz NOT NULL,
        PRIMARY KEY({OWNER},snapshot_id),FOREIGN KEY({OWNER},publication_id) REFERENCES vnext.publication({OWNER},publication_id))"""
    yield f"""CREATE TABLE vnext.snapshot_ref ({SCOPE_COLUMNS},snapshot_id text NOT NULL,ordinal integer NOT NULL,
        entity_type text NOT NULL,entity_id text NOT NULL,revision numeric NOT NULL,access_level integer NOT NULL DEFAULT 0,
        PRIMARY KEY({OWNER},snapshot_id,ordinal),FOREIGN KEY({OWNER},snapshot_id) REFERENCES vnext.snapshot_manifest({OWNER},snapshot_id),
        FOREIGN KEY({OWNER},entity_type,entity_id,revision) REFERENCES vnext.entity_revision_registry({OWNER},entity_type,entity_id,revision))"""
    yield """CREATE FUNCTION vnext.in_scope(t text,p text,k text,l integer DEFAULT 0) RETURNS boolean
        LANGUAGE sql STABLE SET search_path=pg_catalog AS $$ SELECT
        t=current_setting('wuji.tenant',true) AND p=current_setting('wuji.project',true)
        AND k=current_setting('wuji.task',true) AND l<=COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1) $$"""
    yield """CREATE FUNCTION vnext.register_revision() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        BEGIN INSERT INTO vnext.entity_revision_registry(tenant_id,project_id,task_id,entity_type,entity_id,revision,access_level)
        VALUES(NEW.tenant_id,NEW.project_id,NEW.task_id,TG_ARGV[0],NEW.entity_id,NEW.revision,NEW.access_level);
        RETURN NEW; END $$"""
    branches = []
    for name, kind in [
        ("claim_revision", "claim"),
        ("artifact", "artifact"),
        ("observation", "observation"),
    ]:
        yield f"CREATE TRIGGER register_revision AFTER INSERT ON vnext.{name} FOR EACH ROW EXECUTE FUNCTION vnext.register_revision('{kind}')"
        branches.append(
            f"WHEN '{kind}' THEN SELECT EXISTS(SELECT 1 FROM vnext.{name} WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id AND entity_id=NEW.entity_id AND revision=NEW.revision AND access_level=NEW.access_level) INTO present;"
        )
    yield """CREATE FUNCTION vnext.check_registry() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE present boolean := false; BEGIN CASE NEW.entity_type """ + " ".join(
        branches
    ) + """
        ELSE present := false; END CASE;
        IF NOT present THEN RAISE EXCEPTION 'registry requires actual matching domain revision' USING ERRCODE='23503'; END IF;
        RETURN NULL; END $$"""
    yield """CREATE CONSTRAINT TRIGGER registry_domain_exists AFTER INSERT OR UPDATE ON vnext.entity_revision_registry
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vnext.check_registry()"""
    yield """CREATE FUNCTION vnext.check_dependency() RETURNS trigger LANGUAGE plpgsql VOLATILE SET search_path=pg_catalog AS $$
        DECLARE cyclic boolean; BEGIN
        PERFORM 1 FROM vnext.task WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id FOR UPDATE;
        WITH RECURSIVE reachable(id) AS (SELECT NEW.predecessor_id UNION SELECT d.predecessor_id FROM vnext.work_dependency d JOIN reachable r ON d.work_item_id=r.id WHERE d.tenant_id=NEW.tenant_id AND d.project_id=NEW.project_id AND d.task_id=NEW.task_id)
        SELECT EXISTS(SELECT 1 FROM reachable WHERE id=NEW.work_item_id) INTO cyclic;
        IF cyclic THEN RAISE EXCEPTION 'work dependency cycle' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"""
    yield "CREATE TRIGGER dependency_dag BEFORE INSERT OR UPDATE ON vnext.work_dependency FOR EACH ROW EXECUTE FUNCTION vnext.check_dependency()"
    yield """CREATE FUNCTION vnext.check_reference_level() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE required_level integer; BEGIN
        SELECT access_level INTO required_level FROM vnext.entity_revision_registry WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id AND entity_type=NEW.target_type AND entity_id=NEW.target_id AND revision=NEW.target_revision;
        IF required_level IS NOT NULL AND (NEW.access_level<required_level OR EXISTS(SELECT 1 FROM vnext.entity_revision_registry WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id AND entity_type=NEW.source_type AND entity_id=NEW.source_id AND revision=NEW.source_revision AND access_level<required_level)) THEN
        RAISE EXCEPTION 'derived record must inherit source access level' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"""
    yield "CREATE TRIGGER relation_access BEFORE INSERT ON vnext.entity_relation FOR EACH ROW EXECUTE FUNCTION vnext.check_reference_level()"
    yield """CREATE FUNCTION vnext.artifact_retained(t text,p text,k text,i text,v numeric) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
        IF NOT COALESCE(vnext.in_scope(t,p,k),false) OR current_setting('wuji.gc',true) IS DISTINCT FROM 'true' THEN
            RAISE EXCEPTION 'retention access denied' USING ERRCODE='42501'; END IF;
        RETURN EXISTS(SELECT 1 FROM vnext.publication_ref WHERE tenant_id=t AND project_id=p AND task_id=k AND artifact_id=i AND artifact_revision=v)
          OR EXISTS(SELECT 1 FROM vnext.artifact_lease WHERE tenant_id=t AND project_id=p AND task_id=k AND artifact_id=i AND artifact_revision=v AND expires_at>clock_timestamp())
          OR EXISTS(SELECT 1 FROM vnext.observation_artifact WHERE tenant_id=t AND project_id=p AND task_id=k AND artifact_id=i AND artifact_revision=v)
          OR EXISTS(SELECT 1 FROM vnext.entity_relation WHERE tenant_id=t AND project_id=p AND task_id=k AND target_type='artifact' AND target_id=i AND target_revision=v)
          OR EXISTS(SELECT 1 FROM vnext.assessment_input WHERE tenant_id=t AND project_id=p AND task_id=k AND entity_type='artifact' AND entity_id=i AND revision=v)
          OR EXISTS(SELECT 1 FROM vnext.snapshot_ref WHERE tenant_id=t AND project_id=p AND task_id=k AND entity_type='artifact' AND entity_id=i AND revision=v);
        END $$"""
    yield _artifact_update_sql()
    yield "CREATE TRIGGER artifact_immutable BEFORE UPDATE ON vnext.artifact FOR EACH ROW EXECUTE FUNCTION vnext.check_artifact_update()"
    yield """CREATE FUNCTION vnext.check_publication_ref() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE a vnext.artifact%ROWTYPE; BEGIN
        SELECT * INTO a FROM vnext.artifact WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id AND entity_id=NEW.artifact_id AND revision=NEW.artifact_revision FOR UPDATE;
        IF NOT FOUND OR a.state<>'sealed' THEN RAISE EXCEPTION 'publication requires a sealed artifact' USING ERRCODE='23503'; END IF;
        IF NEW.access_level<a.access_level THEN RAISE EXCEPTION 'publication access level too low' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"""
    yield "CREATE TRIGGER publication_sealed BEFORE INSERT ON vnext.publication_ref FOR EACH ROW EXECUTE FUNCTION vnext.check_publication_ref()"


def _artifact_update_sql(*, require_evidence=False):
    statement = """CREATE OR REPLACE FUNCTION vnext.check_artifact_update() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        BEGIN
        IF (to_jsonb(NEW)-'state'-'body_removed') IS DISTINCT FROM (to_jsonb(OLD)-'state'-'body_removed') OR (NEW.body_removed AND NEW.state<>'tombstoned') OR (OLD.state='tombstoned' AND NOT (NEW.state='tombstoned' AND NOT OLD.body_removed AND NEW.body_removed)) OR (OLD.state='sealed' AND NEW.state<>'tombstoned') THEN
        RAISE EXCEPTION 'artifact metadata is immutable' USING ERRCODE='23514'; END IF;
        IF NEW.state='tombstoned' AND OLD.state<>'tombstoned' THEN
        IF current_setting('wuji.gc',true) IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'GC authority required' USING ERRCODE='42501'; END IF;
        -- A live lease is an in-flight commit: neither GC nor purge may take
        -- bytes that another writer is still going to publish.
        IF EXISTS(SELECT 1 FROM vnext.artifact_lease l WHERE l.tenant_id=OLD.tenant_id AND l.project_id=OLD.project_id AND l.task_id=OLD.task_id AND l.artifact_id=OLD.entity_id AND l.artifact_revision=OLD.revision AND l.expires_at>clock_timestamp()) THEN
        RAISE EXCEPTION 'artifact is leased' USING ERRCODE='23514'; END IF;
        IF current_setting('wuji.purge',true) IS DISTINCT FROM 'true' AND vnext.artifact_retained(OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.entity_id,OLD.revision) THEN
        RAISE EXCEPTION 'artifact is retained' USING ERRCODE='23514'; END IF; END IF; RETURN NEW; END $$"""
    if require_evidence:
        statement = statement.replace(
            "        BEGIN\n",
            "        BEGIN\n"
            "        IF OLD.state='staged' AND NEW.state='sealed' THEN\n"
            "        PERFORM vnext.require_evidence_mutation(OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.tool_attempt_id);\n"
            "        END IF;\n",
            1,
        )
    return statement


def _upgrade_evidence_authority(connection, application_role):
    # Mutation triggers leave UPDATE visibility intact for SELECT ... FOR UPDATE.
    # Capability is derived by UoW; binding is rechecked against actual stored rows.
    connection.execute(
        """CREATE FUNCTION vnext.require_evidence_mutation(t text,p text,k text,attempt text)
        RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF current_setting('wuji.capture',true) IS DISTINCT FROM 'true'
          OR NOT COALESCE(vnext.in_scope(t,p,k),false)
          OR NOT EXISTS(SELECT 1 FROM vnext.collector_binding b
            WHERE b.tenant_id=t AND b.project_id=p AND b.task_id=k AND b.tool_attempt_id=attempt
            AND b.subject=current_setting('wuji.subject',true) AND NOT b.revoked) THEN
            RAISE EXCEPTION 'bound evidence authority required' USING ERRCODE='42501';
        END IF; END $$"""
    )
    connection.execute(_artifact_update_sql(require_evidence=True))
    connection.execute("""CREATE FUNCTION vnext.check_lease_mutation() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE target vnext.artifact_lease%ROWTYPE; attempt text;
        BEGIN
        IF TG_OP='DELETE' THEN target:=OLD; ELSE target:=NEW; END IF;
        SELECT tool_attempt_id INTO attempt FROM vnext.artifact
            WHERE tenant_id=target.tenant_id AND project_id=target.project_id AND task_id=target.task_id
            AND entity_id=target.artifact_id AND revision=target.artifact_revision;
        IF NOT FOUND THEN RAISE EXCEPTION 'bound evidence authority required' USING ERRCODE='42501'; END IF;
        PERFORM vnext.require_evidence_mutation(target.tenant_id,target.project_id,target.task_id,attempt);
        IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END $$""")
    connection.execute(
        "CREATE TRIGGER lease_mutation_authority BEFORE INSERT OR UPDATE OR DELETE ON vnext.artifact_lease FOR EACH ROW EXECUTE FUNCTION vnext.check_lease_mutation()"
    )
    functions = "vnext.require_evidence_mutation(text,text,text,text),vnext.check_lease_mutation()"
    connection.execute(f"REVOKE EXECUTE ON FUNCTION {functions} FROM PUBLIC")
    connection.execute(
        sql.SQL(f"GRANT EXECUTE ON FUNCTION {functions} TO {{}}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES (%s)", (EVIDENCE_HEAD,)
    )


TABLES = {
    "task": False,
    "work_item": False,
    "agent_run": False,
    "tool_call": False,
    "tool_attempt": False,
    "collector_binding": False,
    "entity_revision_registry": True,
    "claim_revision": True,
    "artifact": True,
    "observation": True,
    "observation_artifact": True,
    "assessment": True,
    "assessment_input": True,
    "entity_relation": True,
    "work_dependency": False,
    "evidence_receipt": True,
    "outbox": True,
    "publication": True,
    "publication_ref": True,
    "artifact_lease": True,
    "snapshot_manifest": True,
    "snapshot_ref": True,
}
IMMUTABLE = {
    "claim_revision",
    "observation",
    "observation_artifact",
    "entity_revision_registry",
    "assessment",
    "assessment_input",
    "entity_relation",
    "evidence_receipt",
    "outbox",
    "publication",
    "publication_ref",
    "snapshot_manifest",
    "snapshot_ref",
    "work_dependency",
}


def migrate(connection, *, application_role: str) -> None:
    """Install fresh or advance the known vnext base head without rewriting data."""
    with connection.transaction():
        role = connection.execute(
            "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        ).fetchone()
        if role != (False, False):
            raise ValueError("migrate under the non-superuser migration role")
        existing = connection.execute(
            "SELECT to_regclass('vnext.schema_migration')"
        ).fetchone()[0]
        if existing:
            heads = {
                r[0]
                for r in connection.execute(
                    "SELECT head FROM vnext.schema_migration"
                ).fetchall()
            }
            chain = [
                BASE_HEAD,
                EVIDENCE_HEAD,
                KNOWLEDGE_HEAD,
                VISIBILITY_HEAD,
                FRESHNESS_HEAD,
                CONTROL_HEAD,
                ADMISSION_HEAD,
                ADMISSION_HARDENING_HEAD,
                ADMISSION_REQUEST_GUARD_HEAD,
                SCHEDULER_HEAD,
                DISPATCH_FAIRNESS_HEAD,
                PROJECTION_HEAD,
                RETAINED_RESULT_HEAD,
                SESSION_HEAD,
                CONTROL_API_HEAD,
                SESSION_WRITER_EXIT_HEAD,
                POD_RECEIVER_HEAD,
                LAYOUT_HEAD,
                TASK_CREATION_HEAD,
                RUN_SETTLEMENT_HEAD,
                ENVIRONMENT_SETTLEMENT_HEAD,
                COMPLETION_HEAD,
                JUDGMENT_HEAD,
                REPORT_HEAD,
                VIEW_STREAM_HEAD,
                DELIVERY_HEAD,
                RETENTION_HEAD,
                PLATFORM_SETTLEMENT_HEAD,
                LAUNCH_HEAD,
                LAUNCH_OBSERVER_HEAD,
            ]
            if not heads or heads != set(chain[: len(heads)]):
                raise ValueError("unrecognized vnext migration head")
            upgrades = [
                _upgrade_evidence_authority,
                upgrade_knowledge,
                upgrade_visibility,
                upgrade_input_freshness,
                upgrade_control,
                upgrade_admission,
                upgrade_admission_hardening,
                upgrade_admission_request_guards,
                upgrade_scheduler,
                upgrade_dispatch_fairness,
                upgrade_projection,
                upgrade_retained_results,
                upgrade_sessions,
                upgrade_control_api,
                upgrade_session_writer_exit,
                upgrade_pod_receivers,
                upgrade_layouts,
                upgrade_task_creation,
                upgrade_run_settlement_close,
                upgrade_environment_settlement,
                upgrade_completion,
                upgrade_judgments,
                upgrade_reports,
                upgrade_view_stream,
                upgrade_report_delivery,
                upgrade_artifact_purge,
                upgrade_platform_settlement,
                upgrade_task_launch,
                upgrade_launch_observer,
            ]
            for upgrade in upgrades[len(heads) - 1 :]:
                upgrade(connection, application_role)
            return
        for statement in statements():
            connection.execute(statement)
        app = sql.Identifier(application_role)
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA vnext TO {}").format(app))
        connection.execute("REVOKE ALL ON ALL TABLES IN SCHEMA vnext FROM PUBLIC")
        connection.execute(
            "REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA vnext FROM PUBLIC"
        )
        connection.execute(
            sql.SQL("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vnext TO {}").format(app)
        )
        connection.execute("ALTER TABLE vnext.task_access ENABLE ROW LEVEL SECURITY")
        connection.execute(
            "CREATE POLICY access_self ON vnext.task_access FOR SELECT USING (tenant_id=current_setting('wuji.tenant',true) AND subject=current_setting('wuji.subject',true))"
        )
        connection.execute(
            sql.SQL("GRANT SELECT ON vnext.task_access TO {}").format(app)
        )
        for table, level in TABLES.items():
            name = sql.Identifier("vnext", table)
            scope = (
                "vnext.in_scope(tenant_id,project_id,task_id"
                + (",access_level" if level else "")
                + ")"
            )
            connection.execute(
                sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(name)
            )
            read_scope = scope
            if table == "artifact":
                read_scope += " OR (current_setting('wuji.task',true)='' AND tenant_id=current_setting('wuji.tenant',true) AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE a.tenant_id=artifact.tenant_id AND a.project_id=artifact.project_id AND a.task_id=artifact.task_id AND a.subject=current_setting('wuji.subject',true) AND a.can_read AND a.clearance>=artifact.access_level))"
            connection.execute(
                sql.SQL(
                    f"CREATE POLICY scoped_read ON {{}} FOR SELECT USING ({read_scope})"
                ).format(name)
            )
            connection.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(name, app))
            if table in IMMUTABLE or table in {"artifact", "artifact_lease"}:
                privilege = "current_setting('wuji.write',true)='true'"
                if table in {
                    "observation",
                    "observation_artifact",
                    "evidence_receipt",
                    "artifact",
                    "artifact_lease",
                }:
                    privilege += " AND current_setting('wuji.capture',true)='true'"
                if (
                    table == "claim_revision"
                    or table == "entity_relation"
                    or table == "work_dependency"
                ):
                    privilege += " AND current_setting('wuji.domain_write',true)='true'"
                if table in {"publication", "publication_ref"}:
                    privilege += " AND (current_setting('wuji.capture',true)='true' OR current_setting('wuji.snapshot',true)='true')"
                if table in {"snapshot_manifest", "snapshot_ref"}:
                    privilege += " AND current_setting('wuji.snapshot',true)='true'"
                if table in {"assessment", "assessment_input"}:
                    privilege += " AND current_setting('wuji.assess',true)='true'"
                connection.execute(
                    sql.SQL(
                        f"CREATE POLICY scoped_insert ON {{}} FOR INSERT WITH CHECK ({scope} AND {privilege})"
                    ).format(name)
                )
                connection.execute(
                    sql.SQL("GRANT INSERT ON {} TO {}").format(name, app)
                )
            if table in {"task", "artifact", "artifact_lease"}:
                connection.execute(
                    sql.SQL(
                        f"CREATE POLICY scoped_update ON {{}} FOR UPDATE USING ({scope} AND current_setting('wuji.write',true)='true') WITH CHECK ({scope})"
                    ).format(name)
                )
                columns = (
                    "(board_revision,event_seq,observation_count)"
                    if table == "task"
                    else (
                        "(state,body_removed)"
                        if table == "artifact"
                        else "(expires_at)"
                    )
                )
                connection.execute(
                    sql.SQL(f"GRANT UPDATE {columns} ON {{}} TO {{}}").format(name, app)
                )
            if table == "artifact_lease":
                connection.execute(
                    sql.SQL(
                        f"CREATE POLICY scoped_delete ON {{}} FOR DELETE USING ({scope} AND current_setting('wuji.write',true)='true')"
                    ).format(name)
                )
                connection.execute(
                    sql.SQL("GRANT DELETE ON {} TO {}").format(name, app)
                )
        connection.execute(
            "INSERT INTO vnext.schema_migration(head) VALUES (%s)", (BASE_HEAD,)
        )
        _upgrade_evidence_authority(connection, application_role)
        upgrade_knowledge(connection, application_role)
        upgrade_visibility(connection, application_role)
        upgrade_input_freshness(connection, application_role)
        upgrade_control(connection, application_role)
        upgrade_admission(connection, application_role)
        upgrade_admission_hardening(connection, application_role)
        upgrade_admission_request_guards(connection, application_role)
        upgrade_scheduler(connection, application_role)
        upgrade_dispatch_fairness(connection, application_role)
        upgrade_projection(connection, application_role)
        upgrade_retained_results(connection, application_role)
        upgrade_sessions(connection, application_role)
        upgrade_control_api(connection, application_role)
        upgrade_session_writer_exit(connection, application_role)
        upgrade_pod_receivers(connection, application_role)
        upgrade_layouts(connection, application_role)
        upgrade_task_creation(connection, application_role)
        upgrade_run_settlement_close(connection, application_role)
        upgrade_environment_settlement(connection, application_role)
        upgrade_completion(connection, application_role)
        upgrade_judgments(connection, application_role)
        upgrade_reports(connection, application_role)
        upgrade_view_stream(connection, application_role)
        upgrade_report_delivery(connection, application_role)
        upgrade_artifact_purge(connection, application_role)
        upgrade_platform_settlement(connection, application_role)
        upgrade_task_launch(connection, application_role)
        upgrade_launch_observer(connection, application_role)
