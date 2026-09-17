"""P04 extension of the canonical P03 schema, never a parallel persistence stack."""

from hashlib import sha256
from psycopg import sql

HEAD = "vnext_0003_p04_knowledge"
POLICY_DOCUMENT = (
    "assessment-policy-v1: fixed claim/input/environment; qualified methods; "
    "unretracted support and contradiction => disputed/inconclusive; no model support; "
    "exact full assertion templates for json-pointer-equals-v1/json-pointer-absent-v1"
)
METHODS = [
    "json-pointer-equals-v1",
    "json-pointer-absent-v1",
    "human-attestation-v1",
    "model-review-v1",
]
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
FK = f"FOREIGN KEY({O}) REFERENCES vnext.task({O})"


def artifact_update_statement():
    """The effective artifact UPDATE trigger: model-output *or* evidence authority.

    ``_artifact_update_sql`` starts from the raw evidence variant; the knowledge
    migration rebinds it to ``require_artifact_mutation`` so a Run writer may
    seal its own output while a collector path still needs its bound attempt.
    Later migrations must reuse this instead of re-installing the sub-variant.
    """

    from wuji_core.persistence.schema import _artifact_update_sql

    return _artifact_update_sql(require_evidence=True).replace(
        "vnext.require_evidence_mutation(OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.tool_attempt_id)",
        "vnext.require_artifact_mutation(OLD.tenant_id,OLD.project_id,OLD.task_id,OLD.entity_id,OLD.revision)",
    )


def upgrade(connection, application_role):
    statements = [
        "ALTER TABLE vnext.task_access ADD COLUMN can_model_output boolean NOT NULL DEFAULT false",
        f"CREATE TABLE vnext.knowledge_actor({S},subject text NOT NULL,producer_kind text NOT NULL CHECK(producer_kind IN ('agent','human','extractor','import')),qualified_human boolean NOT NULL DEFAULT false,PRIMARY KEY({O},subject),FOREIGN KEY({O},subject) REFERENCES vnext.task_access({O},subject))",
        f"CREATE TABLE vnext.run_writer({S},agent_run_id text NOT NULL,subject text NOT NULL,agent_subject text NOT NULL,revoked boolean NOT NULL DEFAULT false,can_settle boolean NOT NULL DEFAULT false,PRIMARY KEY({O},agent_run_id,subject),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),FOREIGN KEY({O},subject) REFERENCES vnext.task_access({O},subject),FOREIGN KEY({O},agent_subject) REFERENCES vnext.knowledge_actor({O},subject))",
        "CREATE TABLE vnext.assessment_policy(policy_version text PRIMARY KEY,document text NOT NULL,document_sha256 text NOT NULL,methods_json text NOT NULL)",
        f"CREATE TABLE vnext.task_assessment_policy({S},policy_version text NOT NULL REFERENCES vnext.assessment_policy,PRIMARY KEY({O}),{FK})",
        f"CREATE TABLE vnext.claim_editor({S},entity_id text NOT NULL,revision numeric NOT NULL,subject text NOT NULL,PRIMARY KEY({O},entity_id,revision,subject),FOREIGN KEY({O},entity_id,revision) REFERENCES vnext.claim_revision({O},entity_id,revision),FOREIGN KEY({O},subject) REFERENCES vnext.knowledge_actor({O},subject))",
        # Nullable only for preserved P03 rows. New service requires registered actors.
        f"ALTER TABLE vnext.claim_revision ADD COLUMN actor_subject text,ADD COLUMN agent_run_id text,ADD COLUMN basis_json text NOT NULL DEFAULT '[]',ADD FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),ADD FOREIGN KEY({O},actor_subject) REFERENCES vnext.knowledge_actor({O},subject)",
        f"CREATE TABLE vnext.intent_revision({S},entity_id text NOT NULL,revision numeric NOT NULL CHECK(revision>=1 AND revision=trunc(revision)),question text NOT NULL,expected_output text NOT NULL,basis_json text NOT NULL DEFAULT '[]',acceptance_state text NOT NULL DEFAULT 'admitted' CHECK(acceptance_state IN ('proposed','admitted','rejected','superseded')),producer_subject text NOT NULL,agent_run_id text,limitations_json text NOT NULL DEFAULT '[]',access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY({O},entity_id,revision),FOREIGN KEY({O},producer_subject) REFERENCES vnext.knowledge_actor({O},subject),FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),{FK})",
        "CREATE TRIGGER register_revision AFTER INSERT ON vnext.intent_revision FOR EACH ROW EXECUTE FUNCTION vnext.register_revision('intent')",
        "ALTER TABLE vnext.entity_relation DROP CONSTRAINT entity_relation_source_type_check,DROP CONSTRAINT entity_relation_relation_check,DROP CONSTRAINT entity_relation_target_type_check",
        "ALTER TABLE vnext.entity_relation ADD CHECK(source_type IN ('claim','intent','observation')),ADD CHECK(target_type IN ('claim','observation','artifact','intent')),ADD CHECK(relation IN ('cites','extracted_from','supersedes','input_to')),ADD CHECK((relation IN ('cites','extracted_from','supersedes') AND source_type='claim') OR (relation='input_to' AND source_type IN ('claim','observation') AND target_type='intent'))",
        f"ALTER TABLE vnext.assessment ADD COLUMN actor_subject text,ADD FOREIGN KEY({O},actor_subject) REFERENCES vnext.knowledge_actor({O},subject),ADD COLUMN policy_version text REFERENCES vnext.assessment_policy,ADD COLUMN environment_ref text,ADD COLUMN scope_json text NOT NULL DEFAULT '{{}}'",
        f"CREATE TABLE vnext.assessment_action({S},action_id text NOT NULL,target_id text NOT NULL,target_revision numeric NOT NULL DEFAULT 1,kind text NOT NULL CHECK(kind IN ('superseded','retracted','stale','disputed')),replacement_id text,replacement_revision numeric,reason text NOT NULL CHECK(length(reason)>0),actor_subject text NOT NULL,access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY({O},action_id),FOREIGN KEY({O},target_id,target_revision) REFERENCES vnext.assessment({O},assessment_id,revision),FOREIGN KEY({O},replacement_id,replacement_revision) REFERENCES vnext.assessment({O},assessment_id,revision),FOREIGN KEY({O},actor_subject) REFERENCES vnext.knowledge_actor({O},subject),CHECK((kind='superseded')=(replacement_id IS NOT NULL)),CHECK((replacement_id IS NULL)=(replacement_revision IS NULL)))",
        f"CREATE TABLE vnext.knowledge_operation({S},operation_kind text NOT NULL,operation_id text NOT NULL,input_digest text NOT NULL,receipt_json text NOT NULL,access_level integer NOT NULL DEFAULT 0,PRIMARY KEY(tenant_id,task_id,operation_kind,operation_id),{FK})",
        "ALTER TABLE vnext.artifact ALTER COLUMN tool_attempt_id DROP NOT NULL,ADD COLUMN agent_run_id text,ADD COLUMN writer_subject text",
        f"ALTER TABLE vnext.artifact ADD FOREIGN KEY({O},agent_run_id,writer_subject) REFERENCES vnext.run_writer({O},agent_run_id,subject),ADD CHECK((agent_run_id IS NULL AND writer_subject IS NULL AND tool_attempt_id IS NOT NULL) OR (agent_run_id IS NOT NULL AND writer_subject IS NOT NULL AND tool_attempt_id IS NULL AND provenance='model_output'))",
        f"CREATE TABLE vnext.result_submission({S},submission_id text NOT NULL,agent_run_id text NOT NULL,writer_subject text NOT NULL,input_digest text NOT NULL,envelope_json text NOT NULL,status text NOT NULL DEFAULT 'received' CHECK(status='received'),received_receipt_json text NOT NULL,artifact_id text NOT NULL,artifact_revision numeric NOT NULL,access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(tenant_id,task_id,submission_id),UNIQUE({O},submission_id),FOREIGN KEY({O},agent_run_id,writer_subject) REFERENCES vnext.run_writer({O},agent_run_id,subject),FOREIGN KEY({O},artifact_id,artifact_revision) REFERENCES vnext.artifact({O},entity_id,revision))",
        f"CREATE TABLE vnext.result_receipt({S},submission_id text NOT NULL,receipt_json text NOT NULL,access_level integer NOT NULL DEFAULT 0,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(tenant_id,task_id,submission_id),FOREIGN KEY({O},submission_id) REFERENCES vnext.result_submission({O},submission_id))",
    ]
    for statement in statements:
        connection.execute(statement)
    import json

    connection.execute(
        "INSERT INTO vnext.assessment_policy VALUES (%s,%s,%s,%s)",
        (
            "assessment-policy-v1",
            POLICY_DOCUMENT,
            sha256(POLICY_DOCUMENT.encode()).hexdigest(),
            json.dumps(METHODS),
        ),
    )
    # Domain existence checks keep the original trigger; only add a real Intent table.
    branches = []
    for table, kind in [
        ("claim_revision", "claim"),
        ("observation", "observation"),
        ("artifact", "artifact"),
        ("intent_revision", "intent"),
    ]:
        branches.append(
            f"WHEN '{kind}' THEN SELECT EXISTS(SELECT 1 FROM vnext.{table} WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND task_id=NEW.task_id AND entity_id=NEW.entity_id AND revision=NEW.revision AND access_level=NEW.access_level) INTO present;"
        )
    connection.execute(
        "CREATE OR REPLACE FUNCTION vnext.check_registry() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ DECLARE present boolean:=false; BEGIN CASE NEW.entity_type "
        + " ".join(branches)
        + " ELSE present:=false; END CASE; IF NOT present THEN RAISE EXCEPTION 'registry requires actual matching domain revision' USING ERRCODE='23503'; END IF; RETURN NULL; END $$"
    )
    connection.execute(
        """CREATE FUNCTION vnext.require_model_mutation(t text,p text,k text,r text,w text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF current_setting('wuji.model_output',true) IS DISTINCT FROM 'true' OR NOT COALESCE(vnext.in_scope(t,p,k),false)
        OR w IS DISTINCT FROM current_setting('wuji.subject',true) OR NOT EXISTS(SELECT 1 FROM vnext.run_writer b WHERE b.tenant_id=t AND b.project_id=p AND b.task_id=k AND b.agent_run_id=r AND b.subject=w AND NOT b.revoked)
        THEN RAISE EXCEPTION 'bound model output authority required' USING ERRCODE='42501'; END IF; END $$"""
    )
    connection.execute(
        """CREATE FUNCTION vnext.require_artifact_mutation(t text,p text,k text,i text,v numeric) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$ DECLARE a vnext.artifact%ROWTYPE; BEGIN
        SELECT * INTO a FROM vnext.artifact WHERE tenant_id=t AND project_id=p AND task_id=k AND entity_id=i AND revision=v;
        IF NOT FOUND THEN RAISE EXCEPTION 'artifact absent' USING ERRCODE='42501'; END IF;
        IF a.agent_run_id IS NOT NULL THEN PERFORM vnext.require_model_mutation(t,p,k,a.agent_run_id,a.writer_subject);
        ELSE PERFORM vnext.require_evidence_mutation(t,p,k,a.tool_attempt_id); END IF; END $$"""
    )
    connection.execute(artifact_update_statement())
    connection.execute(
        """CREATE OR REPLACE FUNCTION vnext.check_lease_mutation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ DECLARE target vnext.artifact_lease%ROWTYPE; BEGIN
        IF TG_OP='DELETE' THEN target:=OLD; ELSE target:=NEW; END IF;
        PERFORM vnext.require_artifact_mutation(target.tenant_id,target.project_id,target.task_id,target.artifact_id,target.artifact_revision);
        IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END $$"""
    )
    # Insert guards as well as RLS: a model writer cannot mutate a capture artifact.
    connection.execute(
        """CREATE FUNCTION vnext.check_artifact_insert() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
        IF NEW.agent_run_id IS NOT NULL THEN PERFORM vnext.require_model_mutation(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id,NEW.writer_subject);
        ELSE PERFORM vnext.require_evidence_mutation(NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_attempt_id); END IF; RETURN NEW; END $$"""
    )
    connection.execute(
        "CREATE TRIGGER artifact_insert_authority BEFORE INSERT ON vnext.artifact FOR EACH ROW EXECUTE FUNCTION vnext.check_artifact_insert()"
    )
    app = sql.Identifier(application_role)
    for table in [
        "knowledge_actor",
        "run_writer",
        "task_assessment_policy",
        "claim_editor",
        "intent_revision",
        "assessment_action",
        "knowledge_operation",
        "result_submission",
        "result_receipt",
    ]:
        level = table in [
            "intent_revision",
            "assessment_action",
            "knowledge_operation",
            "result_submission",
            "result_receipt",
        ]
        scope = f"vnext.in_scope(tenant_id,project_id,task_id{',access_level' if level else ''})"
        name = sql.Identifier("vnext", table)
        connection.execute(
            sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(name)
        )
        connection.execute(
            sql.SQL(
                f"CREATE POLICY scoped_read ON {{}} FOR SELECT USING ({scope})"
            ).format(name)
        )
        connection.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(name, app))
        if level:
            power = (
                "current_setting('wuji.assess',true)='true'"
                if table == "assessment_action"
                else "current_setting('wuji.domain_write',true)='true'"
            )
            if table in ["result_submission", "result_receipt"]:
                power = "current_setting('wuji.model_output',true)='true'"
            if table == "knowledge_operation":
                power = "(current_setting('wuji.domain_write',true)='true' OR current_setting('wuji.assess',true)='true')"
            connection.execute(
                sql.SQL(
                    f"CREATE POLICY scoped_insert ON {{}} FOR INSERT WITH CHECK ({scope} AND {power})"
                ).format(name)
            )
            connection.execute(sql.SQL("GRANT INSERT ON {} TO {}").format(name, app))
    connection.execute(
        sql.SQL("GRANT SELECT ON vnext.assessment_policy TO {}").format(app)
    )
    for table in ["artifact", "artifact_lease", "publication", "publication_ref"]:
        connection.execute(f"DROP POLICY scoped_insert ON vnext.{table}")
        power = (
            "(current_setting('wuji.capture',true)='true' OR current_setting('wuji.model_output',true)='true'"
            + (
                " OR current_setting('wuji.snapshot',true)='true'"
                if table in ["publication", "publication_ref"]
                else ""
            )
            + ")"
        )
        connection.execute(
            f"CREATE POLICY scoped_insert ON vnext.{table} FOR INSERT WITH CHECK(vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.write',true)='true' AND {power})"
        )
    for fn in [
        "require_model_mutation(text,text,text,text,text)",
        "require_artifact_mutation(text,text,text,text,numeric)",
        "check_artifact_insert()",
    ]:
        connection.execute(f"REVOKE EXECUTE ON FUNCTION vnext.{fn} FROM PUBLIC")
        connection.execute(
            sql.SQL(f"GRANT EXECUTE ON FUNCTION vnext.{fn} TO {{}}").format(app)
        )
    connection.execute("REVOKE ALL ON ALL TABLES IN SCHEMA vnext FROM PUBLIC")
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES (%s)", (HEAD,))


VISIBILITY_HEAD = "vnext_0004_p04_assessment_visibility"


def upgrade_visibility(connection, application_role):
    """Check the complete dependency set without exposing hidden rows to readers."""
    connection.execute(
        """CREATE FUNCTION vnext.assessment_visibility_complete(t text,p text,k text,c text,v numeric)
        RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE allowed_level integer;
        BEGIN
        IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN RETURN false; END IF;
        SELECT least(a.clearance,COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1))
        INTO allowed_level FROM vnext.task_access a WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k
        AND a.subject=current_setting('wuji.subject',true) AND a.can_read;
        IF allowed_level IS NULL OR NOT EXISTS(SELECT 1 FROM vnext.claim_revision x WHERE
            x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.entity_id=c AND x.revision=v
            AND x.access_level<=allowed_level) THEN RETURN false; END IF;
        RETURN NOT EXISTS(SELECT 1 FROM vnext.assessment a WHERE
            a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.claim_id=c AND a.claim_revision=v
            AND a.access_level>allowed_level)
        AND NOT EXISTS(SELECT 1 FROM vnext.assessment_action x JOIN vnext.assessment a
            ON (a.tenant_id,a.project_id,a.task_id,a.assessment_id,a.revision)=
               (x.tenant_id,x.project_id,x.task_id,x.target_id,x.target_revision)
            WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.claim_id=c AND a.claim_revision=v
            AND x.access_level>allowed_level)
        AND NOT EXISTS(SELECT 1 FROM vnext.assessment_input i JOIN vnext.assessment a
            ON (a.tenant_id,a.project_id,a.task_id,a.assessment_id,a.revision)=
               (i.tenant_id,i.project_id,i.task_id,i.assessment_id,i.assessment_revision)
            LEFT JOIN vnext.entity_revision_registry r
            ON (r.tenant_id,r.project_id,r.task_id,r.entity_type,r.entity_id,r.revision)=
               (i.tenant_id,i.project_id,i.task_id,i.entity_type,i.entity_id,i.revision)
            WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k AND a.claim_id=c AND a.claim_revision=v
            AND (i.access_level>allowed_level OR r.entity_id IS NULL OR r.access_level>allowed_level));
        END $$"""
    )
    fn = "vnext.assessment_visibility_complete(text,text,text,text,numeric)"
    connection.execute(f"REVOKE EXECUTE ON FUNCTION {fn} FROM PUBLIC")
    connection.execute(
        sql.SQL(f"GRANT EXECUTE ON FUNCTION {fn} TO {{}}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES (%s)", (VISIBILITY_HEAD,)
    )


FRESHNESS_HEAD = "vnext_0005_p04_input_freshness"


def upgrade_input_freshness(connection, application_role):
    """A scoped boolean about authoritative versions, never hidden revision data."""
    connection.execute(
        """CREATE FUNCTION vnext.claim_input_current(t text,p text,k text,c text,v numeric)
        RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE allowed_level integer;
        BEGIN
        IF NOT COALESCE(vnext.in_scope(t,p,k),false) THEN RETURN NULL; END IF;
        SELECT least(a.clearance,COALESCE(NULLIF(current_setting('wuji.clearance',true),'')::integer,-1))
        INTO allowed_level FROM vnext.task_access a WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k
        AND a.subject=current_setting('wuji.subject',true) AND a.can_read;
        IF allowed_level IS NULL OR NOT EXISTS(SELECT 1 FROM vnext.claim_revision x WHERE
            x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.entity_id=c AND x.revision=v
            AND x.access_level<=allowed_level) THEN RETURN NULL; END IF;
        RETURN NOT EXISTS(SELECT 1 FROM vnext.claim_revision x WHERE
            x.tenant_id=t AND x.project_id=p AND x.task_id=k AND x.entity_id=c AND x.revision>v);
        END $$"""
    )
    fn = "vnext.claim_input_current(text,text,text,text,numeric)"
    connection.execute(f"REVOKE EXECUTE ON FUNCTION {fn} FROM PUBLIC")
    connection.execute(
        sql.SQL(f"GRANT EXECUTE ON FUNCTION {fn} TO {{}}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES (%s)", (FRESHNESS_HEAD,)
    )
