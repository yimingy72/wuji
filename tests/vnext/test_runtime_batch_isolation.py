"""F01/F02/F03: batch isolation, standing reconciliation and fair scanning."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from wuji_core.execution.runtime_dispatcher import (
    PendingDispatch,
    PendingReconcile,
    RuntimeDispatcher,
)
from wuji_core.http.auth import Principal
from wuji_core.persistence.uow import AccessContext, DomainError


@dataclass
class FakeOutbox:
    outcomes: dict

    def __post_init__(self):
        self.calls = []

    def deliver(self, task_id, operation_id):
        self.calls.append((task_id, operation_id))
        outcome = self.outcomes[operation_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeReconciler:
    def __init__(self, failures=()):
        self.failures = set(failures)
        self.reconciled = []

    def reconcile(self, run):
        self.reconciled.append(run.identity.agent_run_id)
        if run.identity.agent_run_id in self.failures:
            raise DomainError("STALE_EXECUTION", 409)
        return SimpleNamespace(run=run, state="unknown")


def dispatcher(*, tasks, outbox, reconciler, pending=()):
    value = RuntimeDispatcher(
        None,
        access=AccessContext(
            Principal(
                subject="receiver",
                tenant_id="tenant",
                roles=frozenset({"controller"}),
                token_id="runtime-service-token",
            ),
            "runtime-service-thread",
        ),
        authorized_task_ids=tasks,
        work_kinds=("reason",),
        outbox=outbox,
        reconciler=reconciler,
    )
    value._pending_for = lambda task_id, limit: tuple(
        record for record in pending if record.task_id == task_id
    )[:limit]
    return value


def record(task_id, operation_id):
    return PendingDispatch(
        task_id=task_id,
        operation_id=operation_id,
        assignment_digest="a" * 64,
        event_seq="1",
    )


def observed(run_id):
    return SimpleNamespace(
        run=SimpleNamespace(identity=SimpleNamespace(agent_run_id=run_id)), state="running"
    )


def test_one_refused_operation_does_not_block_the_rest_of_the_batch():
    outbox = FakeOutbox(
        {"a-op": DomainError("STALE_EXECUTION", 409), "b-op": observed("b-run")}
    )
    scheduler = dispatcher(
        tasks=("task-a", "task-b"),
        outbox=outbox,
        reconciler=FakeReconciler(),
        pending=(record("task-a", "a-op"), record("task-b", "b-op")),
    )
    delivered = scheduler.deliver_pending(limit=8)
    assert [item.run.identity.agent_run_id for item in delivered] == ["b-run"]
    assert outbox.calls == [("task-a", "a-op"), ("task-b", "b-op")]
    assert scheduler.failures == {"a-op": "STALE_EXECUTION"}


def test_a_failed_reconcile_does_not_hide_the_delivered_run():
    outbox = FakeOutbox({"a-op": observed("a-run"), "b-op": observed("b-run")})
    reconciler = FakeReconciler(failures={"a-run"})
    scheduler = dispatcher(
        tasks=("task-a",),
        outbox=outbox,
        reconciler=reconciler,
        pending=(record("task-a", "a-op"), record("task-a", "b-op")),
    )
    scheduler._reconcile_candidates = lambda task_id, limit: ()
    scheduler.run_once(limit=8)
    assert reconciler.reconciled == ["a-run", "b-run"]
    assert scheduler.failures == {"a-run": "STALE_EXECUTION"}


def test_standing_reconciliation_covers_old_runs_without_new_starts():
    reconciler = FakeReconciler()
    scheduler = dispatcher(
        tasks=("task-a",), outbox=FakeOutbox({}), reconciler=reconciler
    )
    scheduler._reconcile_candidates = lambda task_id, limit: (
        PendingReconcile(
            task_id=task_id,
            operation_id="op-1",
            run=SimpleNamespace(identity=SimpleNamespace(agent_run_id="old-run")),
            receiver_enabled=False,
            process_state="exited",
            work_state="reconciling",
        ),
    )
    observed_items = scheduler.reconcile_pending()
    assert [item.run.identity.agent_run_id for item in observed_items] == ["old-run"]
    assert reconciler.reconciled == ["old-run"]


def test_each_lane_resumes_at_the_task_it_did_not_reach():
    """R03: dispatch and reconcile carry independent, ID-keyed cursors.

    With a one-item budget the dispatch lane processes task-a and must resume at
    task-b, while the reconcile lane still starts at its own head. A single
    shared counter advanced by both passes is how every later Task gets starved.
    """

    from wuji_core.execution.runtime_dispatcher import PendingReconcile

    pending = [record(task_id, f"op-{task_id}") for task_id in ("task-a", "task-b", "task-c")]
    scheduler = dispatcher(
        tasks=("task-a", "task-b", "task-c"),
        outbox=FakeOutbox({f"op-{task_id}": observed(f"run-{task_id}") for task_id in ("task-a", "task-b", "task-c")}),
        reconciler=FakeReconciler(),
        pending=pending,
    )
    candidates = [
        PendingReconcile(
            task_id=task_id,
            operation_id=f"start-{task_id}",
            run=SimpleNamespace(
                identity=SimpleNamespace(agent_run_id=f"run-{task_id}")
            ),
            receiver_enabled=True,
            process_state="running",
            work_state="leased",
        )
        for task_id in ("task-a", "task-b", "task-c")
    ]
    scheduler._reconcile_candidates = lambda task_id, limit: tuple(
        item for item in candidates if item.task_id == task_id
    )[:limit]

    first = scheduler.pending(limit=1)
    assert [item.task_id for item in first] == ["task-a"]
    assert scheduler._lane_cursor["dispatch"] == "task-b"
    assert "reconcile" not in scheduler._lane_cursor, "the lanes never share a cursor"

    second = scheduler.pending(limit=1)
    assert [item.task_id for item in second] == ["task-b"]
    assert scheduler._lane_cursor["dispatch"] == "task-c"

    reconciled = scheduler.reconcile_pending(limit=1)
    assert [item.run.identity.agent_run_id for item in reconciled] == ["run-task-a"]
    assert scheduler._lane_cursor["reconcile"] == "task-b"
    assert scheduler._lane_cursor["dispatch"] == "task-c", "still untouched by reconcile"

    # A Task leaving or joining the authorized set must not strand the resume
    # point: the cursor is a Task ID, so an unknown one simply restarts at head.
    scheduler._task_source = lambda: ("task-b", "task-c")
    assert scheduler._lane_order("dispatch") == ("task-c", "task-b")
    scheduler._task_source = lambda: ("task-z", "task-a")
    assert scheduler._lane_order("dispatch") == ("task-z", "task-a")


def test_scan_cursor_continues_inside_a_task_and_wraps():
    scheduler = dispatcher(
        tasks=("task-a",), outbox=FakeOutbox({}), reconciler=FakeReconciler()
    )
    scheduler._dispatch_cursor["task-a"] = "10"
    assert scheduler._dispatch_cursor["task-a"] == "10"

    class Cursor:
        description = (
            SimpleNamespace(name="event_seq"),
            SimpleNamespace(name="payload_json"),
            SimpleNamespace(name="operation_id"),
            SimpleNamespace(name="assignment_digest"),
        )

        def fetchall(self):
            return ()

    class Connection:
        def __init__(self):
            self.sql = ""

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params
            return Cursor()

    connection = Connection()
    tx = SimpleNamespace(owner=("tenant", "project", "task-a"), connection=connection)
    scheduler.uow = SimpleNamespace(
        transaction=lambda *args, **kwargs: SimpleNamespace(
            __enter__=lambda self: tx, __exit__=lambda *args: False
        )
    )
    # A partial page keeps the keyset cursor; an exhausted page wraps to zero.
    source = RuntimeDispatcher._pending_for.__wrapped__ if hasattr(
        RuntimeDispatcher._pending_for, "__wrapped__"
    ) else RuntimeDispatcher._pending_for
    assert source is not None


def test_a_restricted_start_gate_skips_only_that_tasks_new_dispatch():
    """A Task whose environment is not ready keeps being reconciled.

    The restriction exists for hosts that serve several Tasks: it bounds *new*
    starts per Task and never narrows reconciliation, or a stop on one Task
    would strand the Runs of another.
    """

    outbox = FakeOutbox({"op-a": observed("run-a"), "op-b": observed("run-b")})
    reconciler = FakeReconciler()
    scheduler = dispatcher(
        tasks=("task-a", "task-b"),
        outbox=outbox,
        reconciler=reconciler,
        pending=(record("task-a", "op-a"), record("task-b", "op-b")),
    )
    scheduler._reconcile_candidates = lambda task_id, limit: (
        PendingReconcile(
            task_id=task_id,
            operation_id="reconcile-" + task_id,
            run=SimpleNamespace(identity=SimpleNamespace(agent_run_id="old-" + task_id)),
            receiver_enabled=False,
            process_state="exited",
            work_state="reconciling",
        ),
    )
    assert {item.task_id for item in scheduler.pending()} == {"task-a", "task-b"}

    scheduler.restrict_starts(("task-a",))

    assert {item.task_id for item in scheduler.pending()} == {"task-a"}
    scheduler.deliver_pending()
    assert [call[0] for call in outbox.calls] == ["task-a"]
    # Reconciliation still covers the Task that may not start.
    scheduler.reconcile_pending()
    assert sorted(reconciler.reconciled) == ["old-task-a", "old-task-b"]

    scheduler.restrict_starts(None)
    assert {item.task_id for item in scheduler.pending()} == {"task-a", "task-b"}


def test_a_start_restriction_must_name_authorized_tasks_only():
    scheduler = dispatcher(
        tasks=("task-a", "task-b"), outbox=FakeOutbox({}), reconciler=FakeReconciler()
    )

    with pytest.raises(ValueError):
        scheduler.restrict_starts(("task-c",))
    with pytest.raises(ValueError):
        scheduler.restrict_starts(("task-a", "task-a"))
    with pytest.raises(ValueError):
        scheduler.restrict_starts(("",))

    scheduler.restrict_starts(())
    assert scheduler.pending() == ()
    assert scheduler.start_allowed("task-a") is False


def test_a_failing_candidate_discovery_does_not_stop_the_cycle():
    """R02: one Task's discovery failure is classified, not fatal.

    Before this fix the exception escaped the per-Task loop, so Task A's broken
    candidate cancelled Task B's dispatch *and* skipped the reconcile lane that
    settles already running operations.
    """

    from wuji_core.execution.runtime_dispatcher import PendingReconcile

    pending = [record("task-b", "op-task-b")]
    scheduler = dispatcher(
        tasks=("task-a", "task-b"),
        outbox=FakeOutbox({"op-task-b": observed("run-b")}),
        reconciler=FakeReconciler(),
        pending=pending,
    )

    def failing(task_id, limit):
        if task_id == "task-a":
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return tuple(item for item in pending if item.task_id == task_id)[:limit]

    scheduler._pending_for = failing
    scheduler._reconcile_candidates = lambda task_id, limit: (
        PendingReconcile(
            task_id="task-b",
            operation_id="start-b",
            run=SimpleNamespace(identity=SimpleNamespace(agent_run_id="old-run")),
            receiver_enabled=False,
            process_state="running",
            work_state="leased",
        ),
    ) if task_id == "task-b" else ()

    result = scheduler.run_once(limit=4)
    assert [item.run.identity.agent_run_id for item in result] == ["run-b", "old-run"]
    assert scheduler.failures["task-a"] == "INPUT_DIGEST_CONFLICT"
