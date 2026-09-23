"""One live Task per supervisor endpoint: routing never crosses Tasks."""

from __future__ import annotations

import pytest

from wuji_core.execution.dispatch_outbox import (
    SupervisorHttpTransport,
    TaskSupervisorTransport,
)


class RecordingTransport:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def query(self, operation_id, *, task_id=None):
        self.calls.append(("query", operation_id, task_id))
        return {"transport": self.name}

    def start(self, assignment, *, profile_id, task_id=None):
        self.calls.append(("start", assignment.operation_id, task_id, profile_id))
        return {"transport": self.name}

    def control(self, operation_id, *, control_operation_id, action, identity, task_id=None):
        self.calls.append(("control", operation_id, task_id, action))
        return {"transport": self.name}


class Assignment:
    def __init__(self, task_id, operation_id="operation-1"):
        self.operation_id = operation_id
        self.identity = type("Identity", (), {"task_id": task_id})()


def test_each_task_is_served_by_its_own_endpoint():
    default, first, second = (
        RecordingTransport("default"),
        RecordingTransport("first"),
        RecordingTransport("second"),
    )
    router = TaskSupervisorTransport(default=default, by_task={"task-a": first, "task-b": second})

    assert router.query("operation-1", task_id="task-a")["transport"] == "first"
    assert router.query("operation-1", task_id="task-b")["transport"] == "second"
    assert router.start(Assignment("task-b"), profile_id="explore")["transport"] == "second"
    assert router.control(
        "operation-1", control_operation_id="control-1", action="stop", identity=None,
        task_id="task-a",
    )["transport"] == "first"
    # Every call carries the Task it was routed for, including the Assignment one.
    assert ("start", "operation-1", "task-b", "explore") in second.calls
    assert all(call[-1] == "task-a" for call in first.calls if call[0] == "query")


def test_a_task_without_its_own_endpoint_uses_the_deployment_default():
    default, first = RecordingTransport("default"), RecordingTransport("first")
    router = TaskSupervisorTransport(default=default, by_task={"task-a": first})

    assert router.query("operation-1", task_id="task-unknown")["transport"] == "default"
    assert router.query("operation-1", task_id=None)["transport"] == "default"


def test_a_router_without_any_endpoint_for_a_task_refuses():
    first = RecordingTransport("first")
    router = TaskSupervisorTransport(by_task={"task-a": first})

    with pytest.raises(ValueError):
        router.query("operation-1", task_id="task-b")


def test_the_router_requires_real_transports():
    with pytest.raises(ValueError):
        TaskSupervisorTransport(by_task={"task-a": object()})
    with pytest.raises(ValueError):
        TaskSupervisorTransport()
    with pytest.raises(ValueError):
        TaskSupervisorTransport(by_task={"": RecordingTransport("x")})


def test_an_explicit_empty_router_can_receive_its_first_task_later():
    router = TaskSupervisorTransport(allow_empty=True)
    first = RecordingTransport("first")

    router.replace_routes({"task-a": first})

    assert router.query("operation-1", task_id="task-a") == {"transport": "first"}


def test_a_task_id_is_never_sent_to_the_wrong_transport():
    calls = []

    class Spy(RecordingTransport):
        def query(self, operation_id, *, task_id=None):
            calls.append((self.name, task_id))
            return super().query(operation_id, task_id=task_id)

    router = TaskSupervisorTransport(
        default=Spy("default"), by_task={"task-a": Spy("first")}
    )
    router.query("operation-1", task_id="task-a")
    router.query("operation-1", task_id="task-b")

    assert calls == [("first", "task-a"), ("default", "task-b")]


def test_the_single_endpoint_transport_still_accepts_the_task_hint():
    """A deployment with one Service stays valid; the hint is not authority."""

    transport = SupervisorHttpTransport.__new__(SupervisorHttpTransport)
    assert callable(transport.query)
    assert callable(transport.start)
    assert callable(transport.control)
    import inspect

    for method in (transport.query, transport.start, transport.control):
        assert "task_id" in inspect.signature(method).parameters
