"""New cancel requests settle through the existing durable Launch worker."""

from hashlib import sha256
import json

import pytest

from support.p03 import access, seed_capacity
from test_work_state_guards import definition
from wuji_core.completion.precheck import CompletionService
from wuji_core.completion.reports import ReportService
from wuji_core.contracts.execution import TaskCommand
from wuji_core.evidence.artifacts import ArtifactStore
from wuji_core.execution.control import ControlCommandContext, ControlService
from wuji_core.execution.launch import LaunchWorker
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.schema import migrate
from wuji_core.persistence.uow import DomainError, UnitOfWork


TENANT, PROJECT = "tenant-fixture", "project-fixture"
USER = access("operator-fixture", role="operator")
LAUNCH = access("launch-fixture", role="controller")
RUNTIME = access("runtime-fixture", role="controller")


class UnusedAdapter:
    def prepare(self, _): raise AssertionError("launch was not requested")
    def wire(self, _): raise AssertionError("launch was not requested")
    def observe(self, _): raise AssertionError("launch was not requested")
    def capability(self, _): raise AssertionError("launch was not requested")


def _task(connection, task_id, *, activated=False, result=False):
    body = definition()
    body["runtime_profile"]["capture_policy"] = {"mode": "fixture"}
    raw = canonical_json_bytes(body).decode()
    connection.execute(
        "INSERT INTO vnext.task(tenant_id,project_id,task_id,definition_json,definition_digest,"
        "desired_state,observed_state,activated_at,execution_epoch) VALUES(%s,%s,%s,%s,%s,%s,%s,"
        "CASE WHEN %s THEN clock_timestamp() ELSE NULL END,%s)",
        (TENANT, PROJECT, task_id, raw, sha256(raw.encode()).hexdigest(),
         "run" if activated else "pause", "running" if activated else "ready",
         activated, 2 if activated else 1),
    )
    connection.execute(
        "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,"
        "can_control,clearance) VALUES(%s,%s,%s,'operator-fixture',true,true,1)",
        (TENANT, PROJECT, task_id),
    )
    connection.execute(
        "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,"
        "revision,definition_json) VALUES(%s,%s,%s,'version',1,'{}')",
        (TENANT, PROJECT, task_id),
    )
    if result:
        connection.execute(
            "INSERT INTO vnext.work_item(tenant_id,project_id,task_id,work_item_id,"
            "state,kind,terminal_reason) VALUES(%s,%s,%s,'finished-work','done','explore','fixture_result')",
            (TENANT, PROJECT, task_id),
        )


def test_cancel_finalization_three_boundaries(db_environment, tmp_path):
    env = db_environment
    with env.migration_connection() as owner:
        migrate(owner, application_role=env.application_role)
        owner.execute("INSERT INTO vnext.tenant(tenant_id) VALUES(%s)", (TENANT,))
        owner.execute("INSERT INTO vnext.project(tenant_id,project_id) VALUES(%s,%s)", (TENANT, PROJECT))
        owner.execute(
            "INSERT INTO vnext.task_launch_worker(tenant_id,project_id,subject) "
            "VALUES(%s,%s,'launch-fixture')", (TENANT, PROJECT),
        )
        _task(owner, "cancel-done", activated=True, result=True)
        _task(owner, "cancel-prelaunch")
        _task(owner, "cancel-unknown", activated=True)
        _task(owner, "legacy-cancel")
        for task_id in ("cancel-done", "cancel-prelaunch", "cancel-unknown", "legacy-cancel"):
            seed_capacity(owner, task=task_id)
        owner.execute(
            "UPDATE vnext.task SET desired_state='cancel',observed_state='quiescing',"
            "close_trigger='user_cancel' WHERE task_id='legacy-cancel'"
        )
        owner.execute(
            "INSERT INTO vnext.task_launch(tenant_id,project_id,task_id,operation_id,"
            "command_id,input_digest,definition_digest,profile_digest,expected_control_version,"
            "phase,phase_status,reason_code,steps_json,request_json,receipt_json) "
            "VALUES(%s,%s,'cancel-prelaunch','preflight','preflight',%s,%s,%s,1,'prepare',"
            "'failed','receiver_bearer_expires_before_attempt_window',%s,'{}','{}')",
            (TENANT, PROJECT, "a" * 64, "b" * 64, "c" * 64,
             '{"prepare":{"phase_status":"failed"}}'),
        )
        for task_id in ("cancel-done", "cancel-unknown"):
            owner.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,"
                "can_read,can_control,can_observe,clearance) "
                "VALUES(%s,%s,%s,'runtime-fixture',true,true,true,1)",
                (TENANT, PROJECT, task_id),
            )
            owner.execute(
                "INSERT INTO vnext.task_pod_controller(tenant_id,project_id,task_id,"
                "controller_subject,login_role,enabled) "
                "VALUES(%s,%s,%s,'runtime-fixture',%s,true)",
                (TENANT, PROJECT, task_id, env.application_role),
            )
    uow = UnitOfWork(env.additional_app_connection)
    control = ControlService(uow)
    completion = CompletionService(uow, control=control)
    reports = ReportService(uow, artifacts=ArtifactStore(uow, tmp_path / "artifacts"))
    task = control.read_task(USER, "cancel-done")
    with pytest.raises(DomainError) as spoof:
        control.apply(ControlCommandContext(
            USER, "cancel-done", "spoofed-failure",
            TaskCommand.model_validate({"schema_version": "wuji.api.v2",
                                        "command": "cancel",
                                        "expected_version": str(task["control_version"]),
                                        "reason": "not an authority"}),
            cancel_source="system_failure",
        ))
    assert spoof.value.code == "NOT_FOUND_OR_FORBIDDEN"
    for task_id in ("cancel-done", "cancel-prelaunch", "cancel-unknown"):
        actor = RUNTIME if task_id == "cancel-unknown" else USER
        task = control.read_task(actor, task_id)
        control.apply(ControlCommandContext(
            actor, task_id, "cancel:" + task_id,
            TaskCommand.model_validate({"schema_version": "wuji.api.v2",
                                        "command": "cancel",
                                        "expected_version": str(task["control_version"]),
                                        "reason": "fixture cancellation"}),
            cancel_source="system_failure" if task_id == "cancel-unknown" else "user_cancel",
        ))
    with env.additional_app_connection() as connection:
        with connection.transaction():
            for key, value in {"tenant": TENANT, "project": PROJECT,
                               "task": "cancel-done", "subject": "runtime-fixture",
                               "control": "true", "clearance": "1",
                               "write": "true", "request_purpose": ""}.items():
                connection.execute("SELECT set_config(%s,%s,true)", ("wuji." + key, value))
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(json_build_array("
                "'wuji.vnext.task-pod'::text,%s::text,%s::text)::text,0))",
                (TENANT, "cancel-done"),
            )
            for name in ("task-network-init", "agent", "kali", "capture"):
                connection.execute(
                    "INSERT INTO vnext.runtime_terminal_observation(tenant_id,project_id,task_id,"
                    "terminal_observation_id,runtime_attempt,execution_epoch,pod_uid,container_name,"
                    "source_digest,document_json,controller_subject,observed_at,access_level) "
                    "VALUES(%s,%s,%s,%s,1,2,'pod-fixture',%s,%s,%s,'runtime-fixture',"
                    "clock_timestamp(),0)",
                    (TENANT, PROJECT, "cancel-done", "terminal:" + name,
                     name, "a" * 64, '{"state":"terminated"}'),
                )
    worker = LaunchWorker(uow, access=LAUNCH, control=control, adapter=UnusedAdapter(),
                          worker_id="launch-fixture", completion=completion, reports=reports)
    worker.run_once(limit=4)
    with env.migration_connection() as owner:
        rows = owner.execute(
            "SELECT task_id,observed_state,result_outcome,completion_epoch_id "
            "FROM vnext.task ORDER BY task_id"
        ).fetchall()
        statuses = {task_id: (state, outcome, epoch) for task_id, state, outcome, epoch in rows}
        assert statuses["cancel-done"][:2] == ("closed", "not_assessed")
        assert statuses["cancel-prelaunch"][:2] == ("closed", "not_assessed")
        assert statuses["cancel-unknown"][0] != "closed"
        assert owner.execute("SELECT close_trigger,cancel_settlement_source FROM vnext.task "
                             "WHERE task_id='cancel-unknown'").fetchone() == (
                                 "system_failure", "system_failure")
        assert statuses["legacy-cancel"][2] is None
        reports_by_task = dict(owner.execute(
            "SELECT task_id,count(*) FROM vnext.report_commit GROUP BY task_id"
        ).fetchall())
        assert reports_by_task == {"cancel-done": 1, "cancel-prelaunch": 1}
        body = json.loads(owner.execute(
            "SELECT body_json FROM vnext.report_commit WHERE task_id='cancel-done'"
        ).fetchone()[0])
        assert body["result_outcome"] == "not_assessed"
        assert any(item["state"] == "done" for item in body["work_items"])
        assert body["criteria"][0]["status"] == "missing"
