"""P05 real PostgreSQL/services; seeded process/Session/criterion headers are
explicit prerequisites, never Supervisor, SDK, or Goal-verification evidence.
"""

from contextlib import contextmanager
from hashlib import sha256
from importlib import import_module
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
import psycopg

import pytest
from pydantic import ValidationError

from support.p03 import access
from wuji_core.contracts.execution import TaskCommand, WorkCommand, WorkDependency
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError
from test_knowledge_admission import (
    case,
    captured,
    result,
    payload,
    submit,
    OWNER,
    TASK,
    IDENTITY,
)


def production(name):
    try:
        return import_module("wuji_core.execution." + name)
    except ModuleNotFoundError as error:
        pytest.fail(f"P05 production entrypoint absent: {error.name}")


OPERATOR = access("operator-fixture", role="operator")
OBSERVER = access("observer-fixture", role="controller")


def definition():
    return {
        "task": {
            "schema_version": "wuji.api.v2",
            "project_id": OWNER[1],
            "name": "P05 isolated fixture",
            "scenario": "web_single",
            "goal": {
                "text": "Read the fixture version",
                "criteria": [
                    {
                        "criterion_id": "version",
                        "object": "fixture bytes",
                        "condition": "version captured",
                        "evidence_requirements": ["sealed bytes"],
                        "allowed_methods": ["deterministic"],
                        "responsible_party": "fixture-checker",
                        "required": True,
                    }
                ],
            },
            "authorization_scope": [
                {"host": "fixture.invalid", "protocol": "https", "port": 443}
            ],
            "authorization_expires_at": "2099-01-01T00:00:00Z",
            "model_profile_ref": "fixture-model-v1",
            "runtime_profile_ref": "fixture-runtime-v1",
            "budget": {"amount": "1", "currency": "USD"},
        },
        "start_points": ["https://fixture.invalid/entry"],
        "model_profile": {
            "ref": "fixture-model-v1",
            "revision": "1",
            "published_at": "2026-09-13T00:00:00Z",
        },
        "runtime_profile": {
            "ref": "fixture-runtime-v1",
            "revision": "1",
            "published_at": "2026-09-13T00:00:00Z",
        },
        "lock_digest": "a" * 64,
    }


@contextmanager
def control_case(env, tmp_path, audit):
    mod = production("control")
    with case(env, tmp_path, audit) as c:
        with env.migration_connection() as m:
            for subject, control, observe, admit in [
                ("operator-fixture", True, False, False),
                ("observer-fixture", False, True, False),
                ("scheduler-fixture", False, False, True),
                ("completion-fixture", True, False, False),
            ]:
                m.execute(
                    "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_control,can_observe,can_admit,clearance) VALUES(%s,%s,%s,%s,true,%s,%s,%s,1)",
                    (*OWNER, subject, control, observe, admit),
                )
            raw = canonical_json_bytes(definition()).decode()
            m.execute(
                "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
                (raw, sha256(raw.encode()).hexdigest(), TASK),
            )
            for key, tier, tenant, limit in [
                ("platform", "global", None, 2),
                ("tenant-fixture", "tenant", OWNER[0], 2),
            ]:
                m.execute(
                    "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES(%s,%s,%s,%s,'fixture-capacity-v1')",
                    (key, tier, tenant, limit),
                )
                m.execute(
                    "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,%s)",
                    (*OWNER, key),
                )
        c.control = mod.ControlService(c.uow, artifacts=c.store)
        c.control_module = mod
        yield c


def command(
    c,
    name,
    *,
    work=None,
    version=None,
    key=None,
    actor=OPERATOR,
    reason="fixture command",
):
    target = (
        c.control.read_work(actor, TASK, work)
        if work
        else c.control.read_task(actor, TASK)
    )
    value = (
        str(target["revision" if work else "control_version"])
        if version is None
        else str(version)
    )
    dto = (WorkCommand if work else TaskCommand).model_validate(
        {
            "schema_version": "wuji.api.v2",
            "command": name,
            "expected_version": value,
            "reason": reason,
        }
    )
    ctx = c.control_module.ControlCommandContext(
        actor, TASK, key or str(uuid4()), dto, work
    )
    return c.control.apply(ctx)


def observe(
    c, kind, *, run="run-fixture", work="work-fixture", receipt_id=None, process=None
):
    identity = {**IDENTITY, "agent_run_id": run, "work_item_id": work}
    body = dict(
        receipt_id=receipt_id or str(uuid4()),
        identity=identity,
        operation_id="start-" + run,
        environment_ref="environment-fixture",
        pod_uid="pod-fixture",
        kind=kind,
        observed_at="2026-09-13T01:00:00Z",
        process=process,
        reason="explicit native-receipt fixture; no process launched",
    )
    raw = canonical_json_bytes(body).decode()
    observation = c.control_module.ExecutionObservation.model_validate(
        {
            **body,
            "source_receipt": raw,
            "source_digest": sha256(raw.encode()).hexdigest(),
        }
    )
    return c.control.record_observation(OBSERVER, observation)


def prepared_run(c, *, state="leased"):
    with c.env.migration_connection() as m:
        m.execute(
            "UPDATE vnext.task SET activated_at=clock_timestamp(),desired_state='run',observed_state='running' WHERE task_id=%s",
            (TASK,),
        )
        m.execute(
            "UPDATE vnext.agent_run SET start_operation_id='start-run-fixture',pod_uid='pod-fixture' WHERE agent_run_id='run-fixture'"
        )
        m.execute(
            "UPDATE vnext.work_item SET current_run_id='run-fixture',state=%s WHERE work_item_id='work-fixture'",
            (state,),
        )
    with c.uow.transaction(
        access("scheduler-fixture", role="scheduler"), TASK, capability="admit"
    ) as tx:
        production("capacity").CapacityService.reserve(tx, "run-fixture")


def process(*, exited=False, code=0):
    return {
        "pid": 12345,
        "birth_id": "fixture-birth-id",
        "started_at": "2026-09-13T00:59:00Z",
        "exited_at": "2026-09-13T01:00:00Z" if exited else None,
        "exit_code": code if exited else None,
    }


def settled(c):
    with c.env.migration_connection() as m:
        m.execute(
            "INSERT INTO vnext.run_operation_settlement(tenant_id,project_id,task_id,agent_run_id,status,source_receipt_json) VALUES(%s,%s,%s,'run-fixture','settled',%s)",
            (
                *OWNER,
                '{"source":"P06 metadata fixture","operation_ids":["attempt-fixture"],"status":"settled"}',
            ),
        )


def test_result_is_not_exit_rule():
    rule = production("states").can_settle_done
    assert not rule(True, False, True)
    assert not rule(True, True, False)
    assert not rule(False, True, True)
    assert rule(True, True, True)
    from wuji_core.contracts.execution import WorkState

    with pytest.raises(ValueError):
        WorkState("superseded")


def test_criterion_reference_is_dedicated_and_condition_checked():
    try:
        value = WorkDependency.model_validate(
            {
                "predecessor_work_id": "w",
                "condition": "criterion_satisfied",
                "criterion_ref": {"criterion_id": "criterion", "revision": "2"},
            }
        )
    except ValidationError:
        pytest.fail("WorkDependency requires dedicated GoalCriterionRef")
    assert value.criterion_ref.criterion_id == "criterion"
    for body in [
        {"predecessor_work_id": "w", "condition": "criterion_satisfied"},
        {
            "predecessor_work_id": "w",
            "condition": "settled",
            "criterion_ref": {"criterion_id": "c", "revision": "1"},
        },
        {
            "predecessor_work_id": "w",
            "condition": "criterion_satisfied",
            "criterion_ref": {"entity_type": "goal", "id": "c", "revision": "1"},
        },
    ]:
        with pytest.raises(ValidationError):
            WorkDependency.model_validate(body)


def test_start_cas_idempotency_and_knowledge_cannot_control(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        initial = c.control.read_task(OPERATOR, TASK)
        assert initial["activated_at"] is None and initial["desired_state"] == "pause"
        assert not c.control.dispatchable(OPERATOR, TASK, "work-b")
        with pytest.raises(DomainError):
            command(c, "resume")
        with pytest.raises(DomainError):
            command(c, "start", actor=access("agent-fixture", role="agent"))
        receipt = command(c, "start", version=1, key="first")
        assert receipt.resource_version.root == "2"
        assert c.control.dispatchable(OPERATOR, TASK, "work-b")
        assert command(c, "start", version=1, key="first") == receipt
        with pytest.raises(DomainError, match="INPUT_DIGEST_CONFLICT"):
            command(c, "pause", version=1, key="first")
        with pytest.raises(DomainError, match="STALE_VERSION"):
            command(c, "pause", version=1)
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.outbox WHERE kind='task.started'"
                ).fetchone()[0]
                == 1
            )
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.agent_run"
                ).fetchone()[0]
                == 1
            )  # existing fixture only
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE subject='operator-fixture'"
            )
        with pytest.raises(DomainError):
            c.control.apply(
                c.control_module.ControlCommandContext(
                    OPERATOR,
                    TASK,
                    "first",
                    TaskCommand.model_validate(
                        {
                            "schema_version": "wuji.api.v2",
                            "command": "start",
                            "expected_version": "1",
                            "reason": "fixture command",
                        }
                    ),
                )
            )


def test_task_pause_preserves_hold_and_fresh_unstarted_work(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        command(c, "hold", work="work-b")
        command(c, "pause")
        command(c, "resume")
        work = c.control.read_work(OPERATOR, TASK, "work-b")
        assert work["state"] == "suspended" and work["desired_state"] == "hold"
        assert [x["cause_kind"] for x in work["suspension_causes"]] == ["user_hold"]
        assert not c.control.dispatchable(OPERATOR, TASK, "work-b")
        command(c, "resume", work="work-b")
        assert c.control.read_work(OPERATOR, TASK, "work-b")["state"] == "ready"
        # A registered legacy Run without receipts is not known-never-started.
        assert not c.control.dispatchable(OPERATOR, TASK, "work-fixture")


def test_accepted_result_keeps_capacity_until_stored_exit(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        env = result(c, payload())
        assert submit(c, env).json()["status"] == "accepted"
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "running"
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
                ).fetchone()[0]
                == 1
            )
        observe(c, "exited", process=process(exited=True))
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"]
            == "reconciling"
        )  # missing P06 settlement
        settled(c)
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "done"
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
                ).fetchone()[0]
                == 0
            )
        with pytest.raises(DomainError):
            command(c, "resume", work="work-fixture")


def test_hold_revokes_only_one_work_and_unknown_keeps_reservation(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        command(c, "hold", work="work-fixture")
        observe(c, "unknown")
        work = c.control.read_work(OPERATOR, TASK, "work-fixture")
        assert work["state"] == "reconciling" and work["desired_state"] == "hold"
        assert c.control.dispatchable(OPERATOR, TASK, "work-b")
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT execution_allowed FROM vnext.agent_run WHERE agent_run_id='run-fixture'"
                ).fetchone()[0]
                is False
            )
            assert (
                tx.connection.execute(
                    "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
                ).fetchone()[0]
                == 1
            )
        observe(c, "exited", process=process(exited=True))
        settled(c)
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "suspended"
        )
        command(c, "resume", work="work-fixture")
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "blocked"
        )  # no published Session


def test_dependencies_use_real_settlement_and_criterion_rows(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.work_item SET state='failed' WHERE work_item_id='work-fixture'"
            )
        deps = production("dependencies").DependencyService(c.uow)
        deps.add(
            OPERATOR,
            TASK,
            "work-b",
            WorkDependency.model_validate(
                {"predecessor_work_id": "work-fixture", "condition": "settled"}
            ),
        )
        assert deps.satisfied(OPERATOR, TASK, "work-b")
        with pytest.raises(DomainError):
            deps.add(
                OPERATOR,
                TASK,
                "work-fixture",
                WorkDependency.model_validate(
                    {"predecessor_work_id": "work-b", "condition": "settled"}
                ),
            )
        with c.env.migration_connection() as m:
            for wid in ["accepted-successor", "criterion-successor"]:
                m.execute(
                    "INSERT INTO vnext.work_item(tenant_id,project_id,task_id,work_item_id) VALUES(%s,%s,%s,%s)",
                    (*OWNER, wid),
                )
            m.execute(
                "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,revision,definition_json) VALUES(%s,%s,%s,'c',1,'{\"fixture\":\"not actual Goal evidence\"}')",
                OWNER,
            )
        deps.add(
            OPERATOR,
            TASK,
            "accepted-successor",
            WorkDependency.model_validate(
                {"predecessor_work_id": "work-fixture", "condition": "accepted_result"}
            ),
        )
        deps.add(
            OPERATOR,
            TASK,
            "criterion-successor",
            WorkDependency.model_validate(
                {
                    "predecessor_work_id": "work-b",
                    "condition": "criterion_satisfied",
                    "criterion_ref": {"criterion_id": "c", "revision": "1"},
                }
            ),
        )
        assert not deps.satisfied(OPERATOR, TASK, "accepted-successor")
        assert not deps.satisfied(OPERATOR, TASK, "criterion-successor")


def test_close_intent_preserves_partial_outcome_and_never_marks_unrun_done(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task SET result_outcome='partial' WHERE task_id=%s",
                (TASK,),
            )
        command(c, "cancel")
        task = c.control.read_task(OPERATOR, TASK)
        assert (
            task["close_trigger"] == "user_cancel"
            and task["result_outcome"] == "partial"
        )
        assert task["observed_state"] != "closed"
        assert c.control.read_work(OPERATOR, TASK, "work-b")["state"] == "cancelled"


def seed_session(c, *, pending=True, published=True):
    # Actual sealed objects and actual publication pins. This does not invoke SDK restoration.
    refs = []
    for content in [b'{"messages":[]}', b'{"provider":"fixture"}', b'{"memory":[]}']:
        ref = c.store.stage_model_output(
            access("worker-fixture", role="worker"),
            TASK,
            "run-fixture",
            content,
            "application/json",
        )
        c.store.seal(access("worker-fixture", role="worker"), TASK, ref)
        refs.append(ref)
    manifest = {
        "session_id": "session-fixture",
        "work_item_id": "work-fixture",
        "checkpoint_revision": "1",
        "owner_run_id": "run-fixture",
        "run_epoch": "1",
        "history_root": refs[0].model_dump(mode="json"),
        "message_end": "0",
        "provider_state_ref": refs[1].model_dump(mode="json"),
        "memory_manifest_ref": refs[2].model_dump(mode="json"),
        "pending_operation_refs": [],
        "lock_digest": "a" * 64,
        "recovery_class": "approval_boundary",
        "saved_at": "2026-09-13T01:00:00Z",
    }
    with c.env.migration_connection() as m:
        m.execute(
            "INSERT INTO vnext.publication(tenant_id,project_id,task_id,publication_id,kind) VALUES(%s,%s,%s,'session-publication','session')",
            OWNER,
        )
        if published:
            for ref in refs:
                m.execute(
                    "INSERT INTO vnext.publication_ref(tenant_id,project_id,task_id,publication_id,artifact_id,artifact_revision) VALUES(%s,%s,%s,'session-publication',%s,%s)",
                    (*OWNER, ref.id, ref.version.root),
                )
        m.execute(
            "INSERT INTO vnext.session_manifest(tenant_id,project_id,task_id,session_id,revision,work_item_id,owner_run_id,manifest_json,publication_id,published_at) VALUES(%s,%s,%s,'session-fixture',1,'work-fixture','run-fixture',%s,'session-publication',clock_timestamp())",
            (*OWNER, json.dumps(manifest)),
        )
        m.execute(
            "INSERT INTO vnext.input_request(tenant_id,project_id,task_id,input_request_id,work_item_id,wait_ref_json,status,session_id,session_revision,source_receipt_json) VALUES(%s,%s,%s,'input-fixture','work-fixture',%s,%s,'session-fixture',1,%s)",
            (
                *OWNER,
                '{"native_call_id":"call-fixture","question":"fixture input"}',
                "pending" if pending else "resolved",
                '{"source":"P08 persisted metadata fixture"}',
            ),
        )
        m.execute(
            "UPDATE vnext.work_item SET input_request_id='input-fixture',session_id='session-fixture',session_revision=1 WHERE work_item_id='work-fixture' AND task_id='task-fixture'"
        )
        m.execute(
            "UPDATE vnext.agent_run SET output_expectation='input_boundary' WHERE agent_run_id='run-fixture'"
        )
    return refs


def test_waiting_input_survives_pause_and_published_resume(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        seed_session(c)
        settled(c)
        observe(c, "exited", process=process(exited=True))
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"]
            == "waiting_input"
        )
        command(c, "pause")
        command(c, "resume")
        work = c.control.read_work(OPERATOR, TASK, "work-fixture")
        assert (
            work["state"] == "waiting_input"
            and work["input_request"]["status"] == "pending"
        )
        assert "call-fixture" in work["input_request"]["wait_ref_json"]
        assert work["result_state"] == "none"
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.input_request SET status='resolved' WHERE input_request_id='input-fixture'"
            )
        c.control.refresh(OBSERVER, TASK, "work-fixture")
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "ready"
        assert c.control.dispatchable(OPERATOR, TASK, "work-fixture")


def test_missing_session_pins_and_unsettled_operations_block_resume(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        seed_session(c, pending=False, published=False)
        command(c, "hold", work="work-fixture")
        observe(c, "exited", process=process(exited=True))
        # Local exit releases capacity, but hold cannot settle while tool outcomes are unknown.
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"]
            == "reconciling"
        )
        settled(c)
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        command(c, "resume", work="work-fixture")
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "blocked"


def completion(
    c,
    *,
    receipt,
    epoch="epoch-1",
    action="quiesce",
    trigger="budget_exhausted",
    outcome="partial",
):
    task = c.control.read_task(OPERATOR, TASK)
    with c.env.migration_connection() as m:
        m.execute(
            "INSERT INTO vnext.completion_decision(tenant_id,project_id,task_id,receipt_id,epoch_id,action,expected_control_version,board_revision,deadline,close_trigger,result_outcome,source_receipt_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'2099-01-01',%s,%s,%s)",
            (
                *OWNER,
                receipt,
                epoch,
                action,
                task["control_version"],
                task["board_revision"],
                trigger,
                outcome,
                '{"source":"P12 decision header fixture; not a completed review"}',
            ),
        )
    return c.control.apply_completion(
        access("completion-fixture", role="controller"), TASK, receipt
    )


def test_completion_epoch_abort_only_removes_its_own_cause(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        command(c, "hold", work="work-b")
        completion(c, receipt="quiesce-1")
        work = c.control.read_work(OPERATOR, TASK, "work-b")
        assert {r["cause_kind"] for r in work["suspension_causes"]} == {
            "user_hold",
            "completion_epoch",
        }
        with pytest.raises(DomainError):
            completion(c, receipt="wrong-abort", epoch="other-epoch", action="abort")
        completion(c, receipt="abort-1", action="abort")
        work = c.control.read_work(OPERATOR, TASK, "work-b")
        assert work["state"] == "suspended" and [
            r["cause_kind"] for r in work["suspension_causes"]
        ] == ["user_hold"]


def test_observer_acl_digest_birth_identity_and_no_raw_control_escalation(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        with pytest.raises(DomainError):
            with c.uow.transaction(OPERATOR, TASK, capability="observe"):
                pass
        with pytest.raises(DomainError):
            with c.uow.transaction(
                access("operator-fixture", role="agent"), TASK, capability="control"
            ):
                pass
        with pytest.raises(DomainError, match="STALE_EXECUTION"):
            observe(
                c, "exited", process={**process(exited=True), "birth_id": "reused-pid"}
            )
        with pytest.raises(ValidationError):
            c.control_module.ExecutionObservation.model_validate({"exited": True})
        for query in [
            "UPDATE vnext.task SET desired_state='pause'",
            "UPDATE vnext.agent_run SET result_state='accepted'",
        ]:
            with pytest.raises(psycopg.Error):
                with c.uow.transaction(
                    access("agent-fixture", role="agent"), TASK, capability="write"
                ) as tx:
                    tx.connection.execute(query)
        with c.uow.transaction(
            access("agent-fixture", role="agent"), TASK, capability="write"
        ) as tx:
            assert (
                tx.connection.execute(
                    "UPDATE vnext.work_item SET state='done'"
                ).rowcount
                == 0
            )
        with pytest.raises(psycopg.Error):
            with c.uow.transaction(OBSERVER, TASK, capability="observe") as tx:
                tx.connection.execute(
                    "SELECT vnext.project_run_result(%s,%s,%s,'run-fixture','nonexistent')",
                    OWNER,
                )


def test_result_projection_replay_incomplete_and_late_receipt(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        env = result(c, payload())
        c.committer.receive(access("worker-fixture", role="worker"), env)
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["result_state"]
            == "received"
        )
        assert submit(c, env).json()["status"] == "accepted"
        c.committer.receive(access("worker-fixture", role="worker"), env)
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["result_state"]
            == "accepted"
        )
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.agent_run SET output_expectation='final_output' WHERE agent_run_id='run-fixture'"
            )
        settled(c)
        observe(c, "exited", process=process(exited=True))
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["result_state"]
            == "accepted"
        )


def test_missing_final_output_cas_preserves_late_history(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        env = result(c, payload())
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.agent_run SET output_expectation='final_output' WHERE agent_run_id='run-fixture'"
            )
        settled(c)
        observe(c, "exited", process=process(exited=True))
        work = c.control.read_work(OPERATOR, TASK, "work-fixture")
        assert work["state"] == "failed" and work["result_state"] == "incomplete"
        command(c, "pause")
        assert submit(c, env).json()["status"] == "historical_only"
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["result_state"]
            == "historical_only"
        )
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "failed"


def test_capacity_limit_atomic_rollback_and_prelock_order(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.capacity_pool SET capacity=1 WHERE pool_key='tenant-fixture'"
            )
            m.execute(
                "INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,environment_ref,model_mode,start_operation_id,pod_uid) VALUES(%s,%s,%s,'run-b','work-b','receiver-fixture','environment-fixture','synthetic','start-run-b','pod-fixture')",
                OWNER,
            )
            m.execute(
                "UPDATE vnext.work_item SET state='leased',current_run_id='run-b' WHERE work_item_id='work-b' AND task_id='task-fixture'"
            )
        with pytest.raises(DomainError, match="LIMIT_BLOCKED"):
            with c.uow.transaction(
                access("scheduler-fixture", role="scheduler"), TASK, capability="admit"
            ) as tx:
                production("capacity").CapacityService.reserve(tx, "run-b")
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert tx.connection.execute(
                "SELECT used FROM vnext.capacity_pool ORDER BY pool_key"
            ).fetchall() == [(1,), (1,)]
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.capacity_reservation WHERE agent_run_id='run-b'"
                ).fetchone()[0]
                == 0
            )
        events = [
            json.loads(line) for line in c.env.audit_path.read_text().splitlines()
        ]
        # The recorder observes actual PostgreSQL queries, not mocked lock calls.
        queries = [
            e.get("request", {}).get("sql", "")
            for e in events
            if isinstance(e.get("request"), dict)
        ]
        assert any("FOR UPDATE OF p" in q for q in queries)


def test_criterion_current_fixed_judgment_and_failed_not_success(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        with c.env.migration_connection() as m:
            m.execute(
                "INSERT INTO vnext.goal_criterion(tenant_id,project_id,task_id,criterion_id,revision,definition_json) VALUES(%s,%s,%s,'c',1,'{}')",
                OWNER,
            )
            m.execute(
                "INSERT INTO vnext.criterion_judgment(tenant_id,project_id,task_id,judgment_id,criterion_id,criterion_revision,status,applicability,source_receipt_json) VALUES(%s,%s,%s,'j','c',1,'met','current',%s)",
                (*OWNER, '{"source":"explicit P12 metadata fixture"}'),
            )
            m.execute(
                "UPDATE vnext.goal_criterion SET current_judgment_id='j' WHERE criterion_id='c'"
            )
        deps = production("dependencies").DependencyService(c.uow)
        deps.add(
            OPERATOR,
            TASK,
            "work-b",
            WorkDependency.model_validate(
                {
                    "predecessor_work_id": "work-fixture",
                    "condition": "criterion_satisfied",
                    "criterion_ref": {"criterion_id": "c", "revision": "1"},
                }
            ),
        )
        assert deps.satisfied(OPERATOR, TASK, "work-b")
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.criterion_judgment SET applicability='stale' WHERE judgment_id='j'"
            )
        assert not deps.satisfied(OPERATOR, TASK, "work-b")


def test_cancel_preserves_independent_captured_evidence_without_fact(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        artifact, observation = captured(
            c, body=b'{"unparsed":"independent tool bytes"}'
        )
        observe(c, "started", process=process())
        command(c, "cancel", work="work-fixture")
        settled(c)
        observe(c, "exited", process=process(exited=True, code=1))
        assert (
            c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "cancelled"
        )
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.claim_revision"
                ).fetchone()[0]
                == 0
            )
            assert (
                tx.connection.execute(
                    "SELECT entity_id FROM vnext.observation"
                ).fetchone()[0]
                == observation["id"]
            )
            record = c.store.record(tx, artifact)
            assert (
                c.store.checked_bytes(record)
                == b'{"unparsed":"independent tool bytes"}'
            )


def test_known_not_started_receipt_allows_fresh_resume_and_releases_once(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        with c.env.migration_connection() as m:
            m.execute(
                "INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,environment_ref,model_mode,start_operation_id,pod_uid,execution_epoch) VALUES(%s,%s,%s,'run-b','work-b','receiver-fixture','environment-fixture','synthetic','start-run-b','pod-fixture',2)",
                OWNER,
            )
            m.execute(
                "UPDATE vnext.work_item SET state='leased',current_run_id='run-b' WHERE task_id='task-fixture' AND work_item_id='work-b'"
            )
        with c.uow.transaction(
            access("scheduler-fixture", role="scheduler"), TASK, capability="admit"
        ) as tx:
            production("capacity").CapacityService.reserve(tx, "run-b")
        command(c, "hold", work="work-b")
        body = {
            "receipt_id": "not-started",
            "identity": {
                **IDENTITY,
                "agent_run_id": "run-b",
                "work_item_id": "work-b",
                "execution_epoch": "2",
            },
            "operation_id": "start-run-b",
            "environment_ref": "environment-fixture",
            "pod_uid": "pod-fixture",
            "kind": "not_started",
            "observed_at": "2026-09-13T01:00:00Z",
            "process": None,
            "reason": "explicit Supervisor metadata prerequisite",
        }
        raw = canonical_json_bytes(body).decode()
        observation = c.control_module.ExecutionObservation.model_validate(
            {
                **body,
                "source_receipt": raw,
                "source_digest": sha256(raw.encode()).hexdigest(),
            }
        )
        c.control.record_observation(OBSERVER, observation)
        c.control.record_observation(OBSERVER, observation)
        command(c, "resume", work="work-b")
        assert c.control.dispatchable(OPERATOR, TASK, "work-b")
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
                ).fetchone()[0]
                == 0
            )


def test_shared_global_pool_serializes_two_tenants(
    db_environment, tmp_path, audit_directory
):
    from support.p03 import seed

    with control_case(db_environment, tmp_path, audit_directory) as c:
        with c.env.migration_connection() as m:
            seed(m, tenant="tenant-other", project="project-other", task="task-other")
            m.execute(
                "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_admit) VALUES('tenant-other','project-other','task-other','scheduler-other',true,true)"
            )
            m.execute(
                "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES('tenant-other','tenant','tenant-other',1,'fixture-pool-v1')"
            )
            for pool in ["platform", "tenant-other"]:
                m.execute(
                    "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES('tenant-other','project-other','task-other',%s)",
                    (pool,),
                )
            m.execute(
                "UPDATE vnext.capacity_pool SET capacity=1 WHERE pool_key='platform'"
            )
            m.execute(
                "UPDATE vnext.task SET activated_at=clock_timestamp(),desired_state='run',observed_state='running' WHERE task_id IN ('task-fixture','task-other')"
            )
            m.execute(
                "UPDATE vnext.work_item SET state='leased',current_run_id='run-fixture' WHERE work_item_id='work-fixture' AND task_id IN ('task-fixture','task-other')"
            )
        barrier = Barrier(2)

        def reserve(tenant, task, subject):
            barrier.wait(timeout=5)
            try:
                with c.uow.transaction(
                    access(subject, tenant=tenant, role="scheduler"),
                    task,
                    capability="admit",
                ) as tx:
                    production("capacity").CapacityService.reserve(tx, "run-fixture")
                return "reserved"
            except DomainError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [
                pool.submit(reserve, OWNER[0], TASK, "scheduler-fixture"),
                pool.submit(reserve, "tenant-other", "task-other", "scheduler-other"),
            ]
            assert sorted(j.result(timeout=10) for j in jobs) == [
                "LIMIT_BLOCKED",
                "reserved",
            ]
        with c.env.migration_connection() as m:
            assert (
                m.execute(
                    "SELECT used FROM vnext.capacity_pool WHERE pool_key='platform'"
                ).fetchone()[0]
                == 1
            )
            assert (
                m.execute(
                    "SELECT count(*) FROM vnext.capacity_reservation WHERE pool_key='platform'"
                ).fetchone()[0]
                == 1
            )


def test_two_connections_cannot_commit_dependency_cycle(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        barrier = Barrier(2)

        def add(source, target):
            barrier.wait(timeout=5)
            try:
                production("dependencies").DependencyService(c.uow).add(
                    OPERATOR,
                    TASK,
                    source,
                    WorkDependency.model_validate(
                        {"predecessor_work_id": target, "condition": "settled"}
                    ),
                )
                return "inserted"
            except DomainError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [
                pool.submit(add, "work-fixture", "work-b"),
                pool.submit(add, "work-b", "work-fixture"),
            ]
            assert sorted(j.result(timeout=10) for j in jobs) == [
                "INVALID_REFERENCE",
                "inserted",
            ]
        with c.uow.transaction(OPERATOR, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.work_dependency"
                ).fetchone()[0]
                == 1
            )


def test_missing_definition_and_pool_configuration_fail_closed(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task SET definition_json=NULL,definition_digest=NULL WHERE task_id='task-fixture'"
            )
        with pytest.raises(DomainError, match="CAPABILITY_UNAVAILABLE"):
            command(c, "start")
        assert c.control.read_task(OPERATOR, TASK)["activated_at"] is None
        with pytest.raises(DomainError):
            with c.uow.transaction(OPERATOR, "task-sibling", capability="control"):
                pass


def test_upgrade_projects_real_p04_receipts_without_activating_history(
    db_environment, tmp_path
):
    # Run the exact accepted previous migrator/committer only to construct an upgrade prerequisite.
    # This is a migration test, not a rerun of any P04 baseline suite.
    import subprocess
    from support.p03 import seed
    from wuji_core.persistence.schema import migrate
    from wuji_core.persistence.uow import UnitOfWork
    from wuji_core.evidence.artifacts import ArtifactStore
    from wuji_core.blackboard.claims import ClaimService
    from wuji_core.persistence.snapshots import SnapshotRepository

    def accepted_module(path):
        source = subprocess.check_output(
            ["git", "show", "2ce5250:packages/wuji-core/src/wuji_core/" + path],
            text=True,
        )
        namespace = {"__name__": "accepted_p04_migration_prerequisite"}
        exec(compile(source, path, "exec"), namespace)
        return namespace

    old_schema = accepted_module("persistence/schema.py")
    old_commit = accepted_module("blackboard/committer.py")
    with db_environment.migration_connection() as m:
        old_schema["migrate"](m, application_role=db_environment.application_role)
        seed(m)
        m.execute(
            "INSERT INTO vnext.knowledge_actor(tenant_id,project_id,task_id,subject,producer_kind) VALUES(%s,%s,%s,'agent-fixture','agent')",
            OWNER,
        )
        m.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_settle,can_model_output,clearance) VALUES(%s,%s,%s,'worker-fixture',true,true,true,true,1)",
            OWNER,
        )
        m.execute(
            "INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,can_settle) VALUES(%s,%s,%s,'run-fixture','worker-fixture','agent-fixture',true)",
            OWNER,
        )
    uow = UnitOfWork(db_environment.additional_app_connection)
    store = ArtifactStore(uow, tmp_path / "objects")
    worker = access("worker-fixture", role="worker")
    ref = store.stage_model_output(
        worker, TASK, "run-fixture", canonical_json_bytes(payload()), "application/json"
    )
    store.seal(worker, TASK, ref)
    snap = SnapshotRepository(uow).create(TASK, worker)
    envelope = {
        "schema_version": "wuji.result-envelope.v2",
        "submission_id": "old-result",
        "identity": IDENTITY,
        "snapshot_id": snap.snapshot_id,
        "read_set": [],
        "raw_output_ref": ref.model_dump(mode="json"),
        "raw_output_digest": ref.sha256.root,
        "payload": payload(),
        "producer_version": "accepted-P04-prerequisite",
    }
    commit = old_commit["ResultCommitter"](uow, store, ClaimService(uow))
    assert commit.submit(worker, envelope).status.value == "accepted"
    with db_environment.migration_connection() as m:
        before = m.execute("SELECT receipt_json FROM vnext.result_receipt").fetchone()[
            0
        ]
        migrate(m, application_role=db_environment.application_role)
        migrate(m, application_role=db_environment.application_role)
        assert m.execute(
            "SELECT result_state,result_submission_id FROM vnext.agent_run"
        ).fetchone() == ("accepted", "old-result")
        assert m.execute(
            "SELECT activated_at,desired_state FROM vnext.task"
        ).fetchone() == (None, "pause")
        assert (
            m.execute("SELECT receipt_json FROM vnext.result_receipt").fetchone()[0]
            == before
        )


def test_exit_receipt_before_running_notification_settles_without_illegal_edge(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        assert submit(c, result(c, payload())).json()["status"] == "accepted"
        settled(c)
        observe(c, "exited", process=process(exited=True))
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "done"


def test_completion_closes_with_partial_and_cancels_only_unsettled_work(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        assert submit(c, result(c, payload())).json()["status"] == "accepted"
        settled(c)
        observe(c, "exited", process=process(exited=True))
        completion(c, receipt="q")
        receipt = completion(c, receipt="close", action="close")
        task = c.control.read_task(OPERATOR, TASK)
        assert (
            task["observed_state"] == "closed"
            and task["close_trigger"] == "budget_exhausted"
            and task["result_outcome"] == "partial"
        )
        assert c.control.read_work(OPERATOR, TASK, "work-fixture")["state"] == "done"
        assert c.control.read_work(OPERATOR, TASK, "work-b")["state"] == "cancelled"
        assert (
            c.control.apply_completion(
                access("completion-fixture", role="controller"), TASK, "close"
            )
            == receipt
        )


def test_capacity_rechecks_work_hold_even_with_old_run_permission(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.work_item SET desired_state='hold' WHERE task_id='task-fixture' AND work_item_id='work-fixture'"
            )
        with pytest.raises(DomainError, match="STALE_EXECUTION"):
            with c.uow.transaction(
                access("scheduler-fixture", role="scheduler"), TASK, capability="admit"
            ) as tx:
                production("capacity").CapacityService.reserve(tx, "run-fixture")


def test_unknown_external_operation_keeps_task_reconciling_after_local_exit(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        observe(c, "exited", process=process(exited=True))
        command(c, "pause")
        assert c.control.read_task(OPERATOR, TASK)["observed_state"] == "reconciling"


def test_real_superseded_intent_cancels_work_with_reason_not_new_state(
    db_environment, tmp_path, audit_directory
):
    from wuji_core.contracts.knowledge import IntentProposal

    with control_case(db_environment, tmp_path, audit_directory) as c:
        command(c, "start")
        proposal = IntentProposal.model_validate(
            {
                "client_ref": "i",
                "question": "unverified question",
                "basis_refs": [],
                "expected_output": "record evidence",
            }
        )
        receipt = c.claims.propose_intent(
            access("agent-fixture", role="agent"),
            TASK,
            proposal,
            idempotency_key="intent",
        )
        ref = receipt.canonical_ref
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.work_item SET intent_id=%s,intent_revision=%s WHERE task_id='task-fixture' AND work_item_id='work-b'",
                (ref.id, ref.revision.root),
            )
        assert c.control.dispatchable(OPERATOR, TASK, "work-b")
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.intent_revision SET acceptance_state='superseded' WHERE entity_id=%s",
                (ref.id,),
            )
        assert not c.control.dispatchable(OPERATOR, TASK, "work-b")
        c.control.refresh(OBSERVER, TASK, "work-b")
        work = c.control.read_work(OPERATOR, TASK, "work-b")
        assert (
            work["state"] == "cancelled"
            and work["terminal_reason"] == "intent_superseded"
        )


def test_explicit_process_failure_keeps_accepted_result_separate(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        assert submit(c, result(c, payload())).json()["status"] == "accepted"
        settled(c)
        observe(c, "exited", process=process(exited=True, code=1))
        work = c.control.read_work(OPERATOR, TASK, "work-fixture")
        assert work["state"] == "failed" and work["result_state"] == "accepted"
