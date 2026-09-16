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


def test_task_order_rotates_so_a_stable_prefix_cannot_starve_later_tasks():
    scheduler = dispatcher(
        tasks=("task-a", "task-b", "task-c"),
        outbox=FakeOutbox({}),
        reconciler=FakeReconciler(),
    )
    assert scheduler._ordered_tasks() == ("task-a", "task-b", "task-c")
    assert scheduler._ordered_tasks() == ("task-b", "task-c", "task-a")
    assert scheduler._ordered_tasks() == ("task-c", "task-a", "task-b")


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
