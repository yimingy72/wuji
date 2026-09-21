"""Problem-centered work bindings and bounded knowledge deliveries."""

from psycopg import sql

from wuji_core.persistence.launch_fairness_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0032_problem_core"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
SCOPE = "vnext.in_scope(tenant_id,project_id,task_id,access_level)"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0031_launch_fair_claim":
        raise ValueError("problem core migration parent changed")
    connection.execute(
        "ALTER TABLE vnext.intent_revision ADD planning_json text,"
        "ADD CONSTRAINT intent_planning_json_object CHECK(planning_json IS NULL OR jsonb_typeof(planning_json::jsonb)='object')"
    )
    connection.execute(
        "ALTER TABLE vnext.result_submission ADD work_result_json text,"
        "ADD CONSTRAINT result_work_json_object CHECK(work_result_json IS NULL OR jsonb_typeof(work_result_json::jsonb)='object')"
    )
    connection.execute(
        "ALTER TABLE vnext.scheduler_waiter DROP CONSTRAINT scheduler_waiter_status_check,"
        "ADD CONSTRAINT scheduler_waiter_status_check CHECK(status IN ('waiting','ready','unsatisfiable'))"
    )
    connection.execute(
        "ALTER TABLE vnext.scheduler_state ADD pending_since timestamptz,ADD max_pending_at timestamptz,"
        "ADD CONSTRAINT scheduler_pending_window CHECK((pending_since IS NULL)=(max_pending_at IS NULL) "
        "AND (pending_since IS NULL OR max_pending_at>=pending_since))"
    )
    connection.execute(
        sql.SQL("GRANT UPDATE(pending_since,max_pending_at) ON vnext.scheduler_state TO {}").format(
            sql.Identifier(application_role)
        )
    )
    connection.execute(f"""CREATE TABLE vnext.intent_work_binding({S},
        intent_id text NOT NULL,intent_revision numeric NOT NULL,
        canonical_work_item_id text NOT NULL,problem_digest text NOT NULL,
        binding_kind text NOT NULL CHECK(binding_kind IN ('primary','exact_duplicate')),
        rule_version text NOT NULL,source_event_ref numeric,
        access_level integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({O},intent_id,intent_revision),
        FOREIGN KEY({O},intent_id,intent_revision)
          REFERENCES vnext.intent_revision({O},entity_id,revision),
        FOREIGN KEY({O},canonical_work_item_id)
          REFERENCES vnext.work_item({O},work_item_id),
        FOREIGN KEY({O},source_event_ref) REFERENCES vnext.outbox({O},event_seq),
        CHECK(problem_digest ~ '^[a-f0-9]{{64}}$'))""")
    connection.execute(f"""CREATE TABLE vnext.knowledge_delivery({S},
        delivery_id text NOT NULL,kind text NOT NULL CHECK(kind IN
          ('initial_context','knowledge_tool','environment_material','refresh')),
        work_item_id text NOT NULL,agent_run_id text,snapshot_id text NOT NULL,
        session_id text,native_occurrence text,idempotency_key text NOT NULL,
        request_digest text NOT NULL,delivery_json text NOT NULL,
        representation_digest text NOT NULL,
        state text NOT NULL CHECK(state IN ('prepared','attached')),
        attached_manifest_ref text,access_level integer NOT NULL DEFAULT 0,
        prepared_at timestamptz NOT NULL DEFAULT clock_timestamp(),attached_at timestamptz,
        PRIMARY KEY({O},delivery_id),UNIQUE({O},idempotency_key),
        FOREIGN KEY({O},work_item_id) REFERENCES vnext.work_item({O},work_item_id),
        FOREIGN KEY({O},work_item_id,agent_run_id)
          REFERENCES vnext.agent_run({O},work_item_id,agent_run_id),
        FOREIGN KEY({O},snapshot_id) REFERENCES vnext.snapshot_manifest({O},snapshot_id),
        CHECK(request_digest ~ '^[a-f0-9]{{64}}$'),
        CHECK(representation_digest ~ '^[a-f0-9]{{64}}$'),
        CHECK(jsonb_typeof(delivery_json::jsonb)='object'),
        CHECK((state='prepared' AND attached_manifest_ref IS NULL AND attached_at IS NULL)
          OR (state='attached' AND attached_manifest_ref IS NOT NULL AND attached_at IS NOT NULL)),
        CHECK((kind='initial_context' AND native_occurrence IS NULL)
          OR (kind<>'initial_context' AND agent_run_id IS NOT NULL AND native_occurrence IS NOT NULL)))""")
    connection.execute(
        "CREATE UNIQUE INDEX knowledge_delivery_native_occurrence ON vnext.knowledge_delivery"
        "(tenant_id,project_id,task_id,agent_run_id,native_occurrence) WHERE native_occurrence IS NOT NULL"
    )
    app = sql.Identifier(application_role)
    for table in ("intent_work_binding", "knowledge_delivery"):
        target = sql.Identifier("vnext", table)
        connection.execute(sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(target))
        connection.execute(sql.SQL(f"CREATE POLICY scoped_read ON {{}} FOR SELECT USING ({SCOPE})").format(target))
        connection.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(target, app))
    admission = (
        f"{SCOPE} AND current_setting('wuji.admit',true)='true' "
        "AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE "
        "a.tenant_id=intent_work_binding.tenant_id "
        "AND a.project_id=intent_work_binding.project_id "
        "AND a.task_id=intent_work_binding.task_id "
        "AND a.subject=current_setting('wuji.subject',true) AND a.can_read AND a.can_admit)"
    )
    connection.execute(
        "CREATE POLICY scheduler_binding_insert ON vnext.intent_work_binding FOR INSERT WITH CHECK(" + admission + ")"
    )
    connection.execute(sql.SQL("GRANT INSERT ON vnext.intent_work_binding TO {}").format(app))
    writer = f"{SCOPE} AND (current_setting('wuji.admit',true)='true' OR current_setting('wuji.model_output',true)='true')"
    connection.execute(
        "CREATE POLICY delivery_insert ON vnext.knowledge_delivery FOR INSERT WITH CHECK(" + writer + ")"
    )
    connection.execute(
        "CREATE POLICY delivery_update ON vnext.knowledge_delivery FOR UPDATE USING(" + writer + ") WITH CHECK(" + writer + ")"
    )
    connection.execute(sql.SQL("GRANT INSERT ON vnext.knowledge_delivery TO {}").format(app))
    connection.execute(
        sql.SQL("GRANT UPDATE(state,attached_manifest_ref,attached_at) ON vnext.knowledge_delivery TO {}").format(app)
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_work_result_update() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF OLD.work_result_json IS NOT NULL OR NEW.work_result_json IS NULL
             OR (to_jsonb(NEW)-'work_result_json')<>(to_jsonb(OLD)-'work_result_json') THEN
            RAISE EXCEPTION 'accepted WorkResult is append-only' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER result_work_result_append BEFORE UPDATE ON vnext.result_submission "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_work_result_update()"
    )
    result_scope = "vnext.in_scope(tenant_id,project_id,task_id,access_level) AND current_setting('wuji.model_output',true)='true'"
    connection.execute(
        "CREATE POLICY result_work_result_update ON vnext.result_submission FOR UPDATE "
        "USING(" + result_scope + ") WITH CHECK(" + result_scope + ")"
    )
    connection.execute(
        sql.SQL("GRANT UPDATE(work_result_json) ON vnext.result_submission TO {}").format(app)
    )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
