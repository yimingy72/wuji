"""Only P05 review F1/F2 and the directly affected hold/wait control.

Real services, PostgreSQL, sealed objects and explicit producer metadata; not
Supervisor execution, SDK restoration or a P11 control-HTTP implementation.
"""

import json

from test_work_state_guards import (
    OBSERVER,
    OPERATOR,
    TASK,
    command,
    completion,
    control_case,
    observe,
    prepared_run,
    process,
    resumable_session,
    seed_session,
    settled,
)
from test_knowledge_admission import headers


def task_control(task):
    return {
        key: task[key]
        for key in (
            "desired_state",
            "observed_state",
            "execution_allowed",
            "control_version",
            "execution_epoch",
            "runtime_attempt",
            "activated_at",
            "completion_epoch_id",
            "close_trigger",
            "result_outcome",
        )
    }


def work_wait(work):
    return {
        "state": work["state"],
        "blocked_reason": work["blocked_reason"],
        "desired_state": work["desired_state"],
        "result_state": work["result_state"],
        "suspension_causes": work["suspension_causes"],
        "input_request_id": work["input_request_id"],
        "input_status": work["input_request"]["status"],
        "wait_ref": work["input_request"]["wait_ref_json"],
    }


def record(audit, **values):
    (audit / "observed-result.json").write_text(
        json.dumps(values, ensure_ascii=False, indent=2, default=str) + "\n"
    )


def test_f1_closed_cancel_survives_reconcile_and_late_observation(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        command(c, "cancel")
        settled(c)
        observe(c, "exited", process=process(exited=True))
        completion(c, receipt="q-review", trigger="user_cancel")
        completion(c, receipt="close-review", action="close", trigger="user_cancel")
        before = task_control(c.control.read_task(OPERATOR, TASK))
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        reconciled = task_control(c.control.read_task(OPERATOR, TASK))
        receipt = observe(
            c, "exited", process=process(exited=True), receipt_id="late-exit-review"
        )
        after = task_control(c.control.read_task(OPERATOR, TASK))
        with c.uow.transaction(OPERATOR, TASK) as tx:
            stored = tx.connection.execute(
                "SELECT receipt_id,kind FROM vnext.execution_observation WHERE receipt_id=%s",
                (receipt,),
            ).fetchone()
        record(
            audit_directory,
            before=before,
            after_reconcile=reconciled,
            after_late_observation=after,
            stored_history_receipt=stored,
        )
        assert before["observed_state"] == "closed"
        assert not before["execution_allowed"]
        assert stored == ("late-exit-review", "exited")
        assert reconciled == before
        assert after == before


def test_f2_settlement_after_exit_restores_published_pending_input(
    db_environment, tmp_path, audit_directory, monkeypatch
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        refs = seed_session(c)
        resumable_session(monkeypatch, c)
        # The real byte route supplies the complete HTTP packet for this same
        # checkpoint prerequisite. It is not a fabricated control endpoint.
        response = c.client.get(
            f"/api/v2/artifacts/{refs[0].id}/content",
            params={"version": refs[0].version.root},
            headers=headers(c, "worker"),
        )
        assert response.status_code == 200
        assert response.content == b'{"messages":[]}'
        observe(c, "exited", process=process(exited=True))
        before = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        settled(c)
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        reconciled = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        c.control.refresh(OBSERVER, TASK, "work-fixture")
        after = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        record(
            audit_directory,
            before_settlement=before,
            after_reconcile=reconciled,
            after_refresh=after,
        )
        # A complete exited receipt now runs the platform P06 settlement path
        # before this replay helper is called.
        assert before["state"] == "waiting_input"
        assert before["blocked_reason"] is None
        assert reconciled["state"] == after["state"] == "waiting_input"
        assert after["blocked_reason"] is None
        assert after["input_status"] == "pending"
        assert after["wait_ref"] == before["wait_ref"]
        assert after["result_state"] == "none"
        assert not after["suspension_causes"]


def test_f2_hold_keeps_published_wait_suspended_until_explicit_resume(
    db_environment, tmp_path, audit_directory
):
    with control_case(db_environment, tmp_path, audit_directory) as c:
        prepared_run(c)
        observe(c, "started", process=process())
        seed_session(c)
        command(c, "hold", work="work-fixture")
        observe(c, "exited", process=process(exited=True))
        before = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        settled(c)
        c.control.reconcile(OBSERVER, TASK, "work-fixture")
        c.control.refresh(OBSERVER, TASK, "work-fixture")
        held = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        command(c, "resume", work="work-fixture")
        resumed = work_wait(c.control.read_work(OPERATOR, TASK, "work-fixture"))
        record(
            audit_directory,
            before_settlement=before,
            after_settlement_held=held,
            after_explicit_resume=resumed,
        )
        # The observed exit settles the closed operation set before the helper
        # replays the same settlement; the user hold remains authoritative.
        assert before["state"] == "suspended"
        assert held["state"] == "suspended" and held["desired_state"] == "hold"
        assert held["suspension_causes"] == [
            {"cause_kind": "user_hold", "cause_ref": "work-fixture"}
        ]
        assert held["blocked_reason"] is None
        assert resumed["state"] == "waiting_input"
        assert held["input_status"] == resumed["input_status"] == "pending"
        assert before["wait_ref"] == held["wait_ref"] == resumed["wait_ref"]
        assert held["result_state"] == resumed["result_state"] == "none"
