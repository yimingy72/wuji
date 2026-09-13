"""P08 incremental Session writer revocation after the frozen 0014/0015 chain."""

from wuji_core.persistence.control_api_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0016_p08_session_writer_exit"


def statements():
    return (
        """CREATE OR REPLACE FUNCTION vnext.revoke_session_writer_on_exit()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        BEGIN
          IF OLD.process_state IS DISTINCT FROM 'exited'
            AND NEW.process_state='exited'
            AND NEW.output_expectation='input_boundary'
            AND current_setting('wuji.observe',true)='true'
            AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
            AND COALESCE(vnext.in_scope(NEW.tenant_id,NEW.project_id,NEW.task_id),false)
            AND EXISTS(
              SELECT 1
              FROM vnext.execution_observation observation
              JOIN vnext.scheduler_receiver receiver ON
                (receiver.tenant_id,receiver.project_id,receiver.task_id,
                 receiver.runtime_attempt,receiver.receiver_id,receiver.pod_uid,
                 receiver.receiver_subject)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.runtime_attempt,
                 NEW.receiver_id,NEW.pod_uid,current_setting('wuji.subject',true))
              JOIN vnext.work_item work ON
                (work.tenant_id,work.project_id,work.task_id,work.work_item_id,
                 work.current_run_id)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.work_item_id,
                 NEW.agent_run_id)
              JOIN vnext.session_manifest manifest ON
                (manifest.tenant_id,manifest.project_id,manifest.task_id,
                 manifest.session_id,manifest.revision,manifest.work_item_id,
                 manifest.owner_run_id)=
                (work.tenant_id,work.project_id,work.task_id,work.session_id,
                 work.session_revision,work.work_item_id,NEW.agent_run_id)
              JOIN vnext.input_request input ON
                (input.tenant_id,input.project_id,input.task_id,input.input_request_id,
                 input.work_item_id,input.session_id,input.session_revision)=
                (work.tenant_id,work.project_id,work.task_id,work.input_request_id,
                 work.work_item_id,manifest.session_id,manifest.revision)
              JOIN vnext.run_operation_settlement settlement ON
                (settlement.tenant_id,settlement.project_id,settlement.task_id,
                 settlement.agent_run_id,settlement.status)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id,'settled')
              WHERE (observation.tenant_id,observation.project_id,observation.task_id,
                     observation.agent_run_id,observation.receipt_id,
                     observation.kind,observation.subject)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id,
                 NEW.last_observation_id,'exited',current_setting('wuji.subject',true))
                AND receiver.enabled
                AND input.status IN ('pending','resolved')
                AND manifest.manifest_json::jsonb->>'recovery_class'='approval_boundary'
                AND settlement.source_receipt_json::jsonb->>'producer'='p08'
                AND settlement.source_receipt_json::jsonb->>'manifest_ref'=manifest.manifest_ref
                AND settlement.source_receipt_json::jsonb->>'input_request_id'=input.input_request_id
            )
          THEN
            UPDATE vnext.run_credential SET revoked=true
              WHERE (tenant_id,project_id,task_id,agent_run_id)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id);
            UPDATE vnext.run_writer SET revoked=true
              WHERE (tenant_id,project_id,task_id,agent_run_id)=
                (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.agent_run_id);
          END IF;
          RETURN NULL;
        END $$""",
        "DROP TRIGGER IF EXISTS session_writer_exit_revoke ON vnext.agent_run",
        """CREATE TRIGGER session_writer_exit_revoke
        AFTER UPDATE OF process_state ON vnext.agent_run
        FOR EACH ROW EXECUTE FUNCTION vnext.revoke_session_writer_on_exit()""",
        "REVOKE ALL ON FUNCTION vnext.revoke_session_writer_on_exit() FROM PUBLIC",
    )


def upgrade(connection, application_role):
    del application_role  # Trigger execution grants no direct application call.
    if PARENT_HEAD != "vnext_0015_p11_control_api":
        raise ValueError("P08 writer exit migration parent changed")
    for statement in statements():
        connection.execute(statement)
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
