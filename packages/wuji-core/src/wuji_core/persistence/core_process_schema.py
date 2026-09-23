"""Durable process actions over the existing canonical ToolCall/ToolAttempt ledger."""

from psycopg import sql

from wuji_core.persistence.task_explore_concurrency_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0037_core_process"
O = "tenant_id,project_id,task_id"
S = "tenant_id text NOT NULL,project_id text NOT NULL,task_id text NOT NULL"
SCOPE = "vnext.in_scope(tenant_id,project_id,task_id)"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0036_task_explore_concurrency":
        raise ValueError("Core process migration parent changed")
    app = sql.Identifier(application_role)
    action_check = "process_action IN ('exec','read','input','stop')"
    shape_check = """(
      (process_action IS NULL AND parent_process_attempt_id IS NULL)
      OR (process_action IS NOT NULL AND (
        (process_action='exec' AND parent_process_attempt_id IS NULL)
        OR (process_action IN ('read','input','stop') AND parent_process_attempt_id IS NOT NULL)
      ))
    )"""
    connection.execute(
        f"ALTER TABLE vnext.tool_call ADD process_action text CHECK({action_check}),"
        "ADD parent_process_attempt_id text,ADD CHECK(" + shape_check + ")"
    )
    connection.execute(
        f"ALTER TABLE vnext.tool_attempt ADD process_action text CHECK({action_check}),"
        "ADD parent_process_attempt_id text,ADD CHECK(" + shape_check + ")"
    )
    connection.execute(
        f"""CREATE TABLE vnext.process_execution({S},tool_attempt_id text NOT NULL,
        agent_run_id text NOT NULL,state text NOT NULL CHECK(state IN
        ('prepared','running','stopping','exited','unknown')),
        pid bigint CHECK(pid>0),pgid bigint CHECK(pgid>0),birth_id text,
        deadline timestamptz NOT NULL,started_at timestamptz,finished_at timestamptz,
        exit_code integer,signal integer CHECK(signal>0),stdout_spool_ref text,
        stderr_spool_ref text,stdout_bytes bigint NOT NULL DEFAULT 0 CHECK(stdout_bytes>=0),
        stderr_bytes bigint NOT NULL DEFAULT 0 CHECK(stderr_bytes>=0),
        finalization_state text NOT NULL DEFAULT 'pending'
          CHECK(finalization_state IN ('pending','draining','sealed','unknown')),
        output_completeness text NOT NULL DEFAULT 'unknown'
          CHECK(output_completeness IN ('complete','partial','unknown')),
        last_receipt_json text NOT NULL DEFAULT '{{}}'
          CHECK(jsonb_typeof(last_receipt_json::jsonb)='object'),
        last_receipt_digest text CHECK(last_receipt_digest IS NULL OR
          last_receipt_digest ~ '^[a-f0-9]{{64}}$'),
        updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        PRIMARY KEY({O},tool_attempt_id),
        FOREIGN KEY({O},tool_attempt_id) REFERENCES vnext.tool_attempt({O},tool_attempt_id),
        FOREIGN KEY({O},agent_run_id) REFERENCES vnext.agent_run({O},agent_run_id),
        CHECK(num_nonnulls(exit_code,signal)<=1),
        CHECK(state<>'prepared' OR (pid IS NULL AND pgid IS NULL AND birth_id IS NULL
          AND started_at IS NULL AND finished_at IS NULL)),
        CHECK(state<>'exited' OR (finished_at IS NOT NULL AND
          num_nonnulls(exit_code,signal)=1)),
        CHECK((pid IS NULL)=(pgid IS NULL)),
        CHECK((stdout_spool_ref IS NULL OR length(stdout_spool_ref) BETWEEN 1 AND 4096)
          AND (stderr_spool_ref IS NULL OR length(stderr_spool_ref) BETWEEN 1 AND 4096)))"""
    )
    connection.execute(
        f"ALTER TABLE vnext.tool_call ADD FOREIGN KEY({O},parent_process_attempt_id) "
        f"REFERENCES vnext.process_execution({O},tool_attempt_id)"
    )
    connection.execute(
        f"ALTER TABLE vnext.tool_attempt ADD FOREIGN KEY({O},parent_process_attempt_id) "
        f"REFERENCES vnext.process_execution({O},tool_attempt_id)"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_process_attempt_binding() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID))
          THEN RETURN NEW; END IF;
          IF NOT EXISTS(SELECT 1 FROM vnext.tool_call c WHERE
            (c.tenant_id,c.project_id,c.task_id,c.tool_call_id)=
              (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_call_id)
            AND c.process_action IS NOT DISTINCT FROM NEW.process_action
            AND c.parent_process_attempt_id IS NOT DISTINCT FROM
                NEW.parent_process_attempt_id)
          THEN RAISE EXCEPTION 'process attempt differs from its logical call'
            USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER process_attempt_binding BEFORE INSERT ON vnext.tool_attempt "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_process_attempt_binding()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_process_identity_update() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID))
          THEN RETURN NEW; END IF;
          IF NEW.process_action IS DISTINCT FROM OLD.process_action
             OR NEW.parent_process_attempt_id IS DISTINCT FROM OLD.parent_process_attempt_id
          THEN RAISE EXCEPTION 'process identity is immutable'
            USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER process_call_identity_immutable BEFORE UPDATE ON vnext.tool_call "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_process_identity_update()"
    )
    connection.execute(
        "CREATE TRIGGER process_attempt_identity_immutable BEFORE UPDATE ON vnext.tool_attempt "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_process_identity_update()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_process_execution_insert() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid=TG_RELID))
          THEN RETURN NEW; END IF;
          IF current_setting('wuji.request_purpose',true)<>'tool_request'
             OR NEW.state<>'prepared' OR NEW.last_receipt_json::jsonb<>'{}'::jsonb
             OR NEW.last_receipt_digest IS NOT NULL
             OR NOT EXISTS(SELECT 1 FROM vnext.tool_attempt a WHERE
               (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id,a.agent_run_id)=
               (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.tool_attempt_id,
                NEW.agent_run_id) AND a.process_action='exec'
                AND a.parent_process_attempt_id IS NULL AND a.status='admitted')
          THEN RAISE EXCEPTION 'process execution must start from an admitted exec'
            USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER process_execution_insert BEFORE INSERT ON vnext.process_execution "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_process_execution_insert()"
    )
    connection.execute("ALTER TABLE vnext.process_execution ENABLE ROW LEVEL SECURITY")
    connection.execute(
        f"CREATE POLICY scoped_read ON vnext.process_execution FOR SELECT USING({SCOPE})"
    )
    connection.execute(
        f"CREATE POLICY request_insert ON vnext.process_execution FOR INSERT WITH CHECK({SCOPE} "
        "AND current_setting('wuji.request_purpose',true)='tool_request')"
    )
    connection.execute(
        f"CREATE POLICY settlement_update ON vnext.process_execution FOR UPDATE USING({SCOPE} "
        "AND current_setting('wuji.request_purpose',true)='tool_settle') WITH CHECK(" + SCOPE + ")"
    )
    connection.execute(sql.SQL("GRANT SELECT,INSERT ON vnext.process_execution TO {}").format(app))
    connection.execute(
        sql.SQL("""GRANT UPDATE(state,pid,pgid,birth_id,started_at,finished_at,
        exit_code,signal,stdout_spool_ref,stderr_spool_ref,stdout_bytes,stderr_bytes,
        output_completeness,last_receipt_json,last_receipt_digest,finalization_state,updated_at)
        ON vnext.process_execution TO {}""").format(app)
    )
    connection.execute("REVOKE ALL ON FUNCTION vnext.guard_process_attempt_binding() FROM PUBLIC")
    connection.execute("REVOKE ALL ON FUNCTION vnext.guard_process_identity_update() FROM PUBLIC")
    connection.execute("REVOKE ALL ON FUNCTION vnext.guard_process_execution_insert() FROM PUBLIC")
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
