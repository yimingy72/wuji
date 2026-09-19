"""First-use durable launch tests: real PG, signed HTTP, and adapter seams."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json

import pytest

from support.p03 import access
from support.first_use import (
    bearer,
    create_task,
    first_use_case,
    task_command,
    task_view,
    worker_access,
)
from test_task_creation import OWNER, payload
from wuji_core.contracts.execution import TaskCommand
from wuji_core.execution.control import ControlCommandContext
from wuji_core.execution.launch import LaunchWorker
from wuji_core.persistence.uow import DomainError


class CrashAfterLease(BaseException):
    pass


class FixtureLaunchAdapter:
    """Deterministic deployment seam; no owner credential or K8s access."""

    def __init__(self, *, ready=True, crash_prepare=False, on_prepare=None):
        self.ready = ready
        self.crash_prepare = crash_prepare
        self.on_prepare = on_prepare
        self.prepare_calls = 0
        self.wire_calls = 0
        self.wire_inputs = []
        self.observe_calls = []
        self.capability_calls = 0
        self.prepared_definition_digest = None

    def prepare(self, input):
        self.prepare_calls += 1
        if self.crash_prepare:
            raise CrashAfterLease
        if self.on_prepare is not None:
            self.prepared_definition_digest = self.on_prepare(input)
        response = {
            "status": "ready",
            "external_ref": "prepare:" + input["operation_id"],
            "summary": {"fixture": True},
        }
        if self.prepared_definition_digest:
            response["definition_digest"] = self.prepared_definition_digest
        return response

    def wire(self, input):
        self.wire_calls += 1
        self.wire_inputs.append(dict(input))
        if not self.ready:
            return {
                "status": "pending",
                "external_ref": "wire:" + input["operation_id"],
                "summary": {"runtime_uid": None},
            }
        return {
            "status": "ready",
            "external_ref": "wire:" + input["operation_id"],
            "runtime_uid": "pod-fixture-uid",
            "summary": {"runtime_uid": "pod-fixture-uid"},
        }

    def observe(self, input):
        self.observe_calls.append(dict(input))
        if input["phase"] == "wire" and not self.ready:
            return {
                "status": "pending",
                "external_ref": input["external_ref"],
                "summary": {"runtime_uid": None},
            }
        return {
            "status": "ready",
            "external_ref": input["external_ref"],
            "runtime_uid": "pod-fixture-uid",
            "summary": {"runtime_uid": "pod-fixture-uid"},
        }

    def capability(self, input):
        self.capability_calls += 1
        assert input["observed_runtime_uid"] == "pod-fixture-uid"
        return {
            "status": "ready",
            "external_ref": "capability:" + input["operation_id"],
            "summary": {"published": True},
        }


def _register_worker(connection, *, subject="launch-worker"):
    connection.execute(
        """INSERT INTO vnext.task_launch_worker(tenant_id,project_id,subject)
        VALUES(%s,%s,%s) ON CONFLICT DO NOTHING""",
        (OWNER[0], OWNER[1], subject),
    )


def _start(case, task_id, *, key="launch-start"):
    view = task_view(case, task_id)
    response = task_command(
        case,
        task_id,
        "start",
        view["version"],
        key=key,
    )
    assert response.status_code == 202, response.text
    return response


def _worker(case, adapter, *, subject="launch-worker"):
    with case.environment.migration_connection() as connection:
        _register_worker(connection, subject=subject)
    prepare = adapter.prepare
    def publish_then_prepare(input):
        # Simulate the deployment boundary's real persisted prerequisite;
        # never bypass Control's capacity guard just to make activation pass.
        from support.p03 import seed_capacity
        with case.environment.migration_connection() as connection:
            seed_capacity(connection, task=input["task_id"])
        return prepare(input)
    adapter.prepare = publish_then_prepare
    return LaunchWorker(
        case.uow,
        access=worker_access(case, subject),
        control=case.control,
        adapter=adapter,
        worker_id="worker-" + subject,
        lease_seconds=2,
    )


def _expire_lease(case, task_id):
    with case.environment.migration_connection() as connection:
        connection.execute(
            """UPDATE vnext.task_launch
            SET lease_expires_at=clock_timestamp()-interval '1 second'
            WHERE task_id=%s""",
            (task_id,),
        )


def test_start_replay_keeps_receipt_and_initial_attempt_identity(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-replay-create")
        task_id = created["task_id"]
        first = _start(case, task_id, key="launch-replay")
        replay = task_command(
            case, task_id, "start", "1", key="launch-replay"
        )
        changed = task_command(
            case,
            task_id,
            "start",
            "1",
            key="launch-replay",
            reason="different public command",
        )
        assert replay.status_code == 202, replay.text
        assert replay.json() == first.json()
        assert changed.status_code == 409, changed.text
        assert changed.json()["code"] == "INPUT_DIGEST_CONFLICT"

        launch = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert launch.status_code == 200, launch.text
        assert launch.json()["runtime_attempt"] == "1"
        assert launch.json()["execution_epoch"] == "1"


def test_claim_requires_project_worker_and_grants_minimal_task_acl(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-worker-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-worker-start")
        adapter = FixtureLaunchAdapter()
        worker = LaunchWorker(
            case.uow,
            access=worker_access(case),
            control=case.control,
            adapter=adapter,
            worker_id="unregistered-worker",
            lease_seconds=2,
        )
        assert worker.run_once(limit=1) == []
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                """SELECT count(*) FROM vnext.task_access
                WHERE task_id=%s AND subject=%s""",
                (task_id, "launch-worker"),
            ).fetchone() == (0,)

        worker = _worker(case, adapter)
        progress = worker.run_once(limit=1)
        assert progress and progress[-1]["task_id"] == task_id
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                """SELECT can_read,can_control,can_admit
                FROM vnext.task_access WHERE task_id=%s AND subject=%s""",
                (task_id, "launch-worker"),
            ).fetchone() == (True, True, True)
        launch = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert launch.json()["phase"] == "ready"
        assert launch.json()["phase_status"] == "succeeded"


def test_cancel_before_activate_does_not_wire_or_publish(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-cancel-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-cancel-start")
        operator = access("control-fixture", role="operator")

        def cancel_after_prepare(_input):
            current = case.control.read_task(operator, task_id)
            command = TaskCommand.model_validate(
                {
                    "schema_version": "wuji.api.v2",
                    "command": "cancel",
                    "expected_version": str(current["control_version"]),
                    "reason": "cancel before activation",
                }
            )
            case.control.apply(
                ControlCommandContext(
                    operator, task_id, "cancel-before-activate", command
                )
            )

        adapter = FixtureLaunchAdapter(on_prepare=cancel_after_prepare)
        worker = _worker(case, adapter)
        worker.run_once(limit=1)
        assert adapter.wire_calls == 0
        assert adapter.capability_calls == 0
        task = task_view(case, task_id)
        assert task["desired_state"] == "cancel"
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT activated_at FROM vnext.task WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (None,)


def test_prepare_crash_reclaims_by_observing_fixed_external_ref(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-crash-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-crash-start")
        crashing = FixtureLaunchAdapter(crash_prepare=True)
        worker = _worker(case, crashing)
        with pytest.raises(CrashAfterLease):
            worker.run_once(limit=1)
        _expire_lease(case, task_id)

        recovered = FixtureLaunchAdapter()
        worker = _worker(case, recovered, subject="launch-worker-recovered")
        worker.run_once(limit=1)
        assert recovered.prepare_calls == 0
        assert any(item["phase"] == "prepare" for item in recovered.observe_calls)
        launch = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert launch.json()["phase_status"] == "succeeded"


def test_wire_pending_never_publishes_capability_until_ready(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-pending-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-pending-start")
        adapter = FixtureLaunchAdapter(ready=False)
        worker = _worker(case, adapter)
        worker.run_once(limit=1)
        pending = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert pending.json()["phase"] == "wire"
        assert pending.json()["phase_status"] == "pending"
        assert adapter.capability_calls == 0

        adapter.ready = True
        worker.run_once(limit=1)
        ready = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert ready.json()["phase"] == "ready"
        assert ready.json()["phase_status"] == "succeeded"
        assert adapter.capability_calls == 1


def test_prepare_definition_digest_rebinds_wire_but_not_public_input_digest(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-finalise-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-finalise-start")
        prepared_digest = {}

        def finalise_definition(_input):
            with case.environment.migration_connection() as connection:
                row = connection.execute(
                    "SELECT definition_json FROM vnext.task WHERE task_id=%s",
                    (task_id,),
                ).fetchone()
                document = json.loads(row[0])
                document["prepared_marker"] = "finalised-by-prepare"
                raw = json.dumps(document, separators=(",", ":"), sort_keys=True)
                digest = sha256(raw.encode()).hexdigest()
                connection.execute(
                    "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
                    (raw, digest, task_id),
                )
                prepared_digest["value"] = digest
                return digest

        adapter = FixtureLaunchAdapter(on_prepare=finalise_definition)
        worker = _worker(case, adapter)
        worker.run_once(limit=1)
        with db_environment.migration_connection() as connection:
            task_digest = connection.execute(
                "SELECT definition_digest FROM vnext.task WHERE task_id=%s",
                (task_id,),
            ).fetchone()[0]
            job = connection.execute(
                """SELECT definition_digest,input_digest,request_json
                FROM vnext.task_launch WHERE task_id=%s""",
                (task_id,),
            ).fetchone()
        assert task_digest == prepared_digest["value"]
        assert job[0] == prepared_digest["value"]
        assert adapter.wire_inputs[0]["definition_digest"] == prepared_digest["value"]
        original_command = TaskCommand.model_validate(
            {
                "schema_version": "wuji.api.v2",
                "command": "start",
                "expected_version": "1",
                "reason": "first-use start",
            }
        )
        from wuji_core.http import canonical_json_bytes

        expected_input_digest = sha256(
            canonical_json_bytes(
                {"task_id": task_id, "command": original_command.model_dump(mode="json")}
            )
        ).hexdigest()
        assert job[1] == expected_input_digest


def test_activation_receipt_replay_after_worker_response_loss_does_not_increment_epoch(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-ack-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-ack-start")
        adapter = FixtureLaunchAdapter()
        worker = _worker(case, adapter)
        original_record = worker._record

        def lose_activation_ack(job, phase, status, **patch):
            if phase == "activate" and status == "succeeded":
                raise CrashAfterLease
            return original_record(job, phase, status, **patch)

        worker._record = lose_activation_ack
        with pytest.raises(CrashAfterLease):
            worker.run_once(limit=1)
        first_epoch = task_view(case, task_id)["execution_epoch"]
        _expire_lease(case, task_id)
        recovered = _worker(case, FixtureLaunchAdapter(), subject="launch-worker-ack")
        recovered.run_once(limit=1)
        assert task_view(case, task_id)["execution_epoch"] == first_epoch


def test_two_start_keys_have_one_durable_launch_operation(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-race-create")
        task_id = created["task_id"]

        def submit(key):
            actor = access("control-fixture", role="operator")
            command = TaskCommand.model_validate(
                {
                    "schema_version": "wuji.api.v2",
                    "command": "start",
                    "expected_version": "1",
                    "reason": "concurrent start",
                }
            )
            try:
                return case.launch.accept_start(
                    actor, task_id, command, idempotency_key=key
                )
            except DomainError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit, ("race-a", "race-b")))
        assert sum(hasattr(result, "command_id") for result in results) == 1
        errors = [result for result in results if isinstance(result, DomainError)]
        assert len(errors) == 1
        assert errors[0].code in {"STALE_EXECUTION", "INPUT_DIGEST_CONFLICT"}
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.task_launch WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (1,)


def test_api12_unknown_launch_rejects_start_and_bare_resume_without_new_operation(
    db_environment, audit_directory
):
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="launch-api12-create")
        task_id = created["task_id"]
        _start(case, task_id, key="launch-api12-start")
        before = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert before.status_code == 200, before.text
        original = before.json()

        with db_environment.migration_connection() as connection:
            connection.execute(
                """UPDATE vnext.task_launch
                SET phase_status='reconciling',reason_code='operation_unknown',
                    lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL
                WHERE task_id=%s""",
                (task_id,),
            )

        current = task_view(case, task_id)
        start_again = task_command(
            case,
            task_id,
            "start",
            current["version"],
            key="launch-api12-start-again",
            reason="attempt recovery by starting again",
        )
        resume = task_command(
            case,
            task_id,
            "resume",
            current["version"],
            key="launch-api12-resume",
            reason="attempt bare resume recovery",
        )
        assert start_again.status_code == 409, start_again.text
        assert resume.status_code == 409, resume.text

        after = case.client.get(
            f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)
        )
        assert after.status_code == 200, after.text
        assert after.json()["operation_id"] == original["operation_id"]
        assert after.json()["phase_status"] == "reconciling"
        assert after.json()["runtime_attempt"] == original["runtime_attempt"]
        assert after.json()["execution_epoch"] == original["execution_epoch"]
        assert set(task_view(case, task_id)["allowed_actions"]).isdisjoint(
            {"start", "resume"}
        )
        with db_environment.migration_connection() as connection:
            assert connection.execute(
                "SELECT count(*) FROM vnext.task_launch WHERE task_id=%s",
                (task_id,),
            ).fetchone() == (1,)


def test_unprepared_task_can_cancel_but_cannot_bypass_capacity_to_activate(
    db_environment, audit_directory,
):
    with first_use_case(db_environment, audit_directory) as case:
        task_id = create_task(case, payload(), key="never-started-cancel")["task_id"]
        operator = access("control-fixture", role="operator")
        with pytest.raises(DomainError, match="CAPABILITY_UNAVAILABLE"):
            case.control.activate_task(operator, task_id, operation_id="no-pool-start",
                                       expected_version="1", reason="must require published capacity")
        response = task_command(case, task_id, "cancel", "1", key="cancel-before-prepare")
        assert response.status_code == 202, response.text
        assert task_view(case, task_id)["desired_state"] == "cancel"
        with db_environment.migration_connection() as connection:
            assert connection.execute("SELECT activated_at FROM vnext.task WHERE task_id=%s", (task_id,)).fetchone() == (None,)
            assert connection.execute("SELECT count(*) FROM vnext.agent_run WHERE task_id=%s", (task_id,)).fetchone() == (0,)
