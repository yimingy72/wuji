"""Pure checks for core capture readiness and bounded stop orchestration."""

from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from types import SimpleNamespace

import pytest

from wuji_core.execution import pod_runtime
from wuji_core.execution.pod_runtime import PodCaptureRegistration
from wuji_core.persistence.uow import DomainError
from wuji_task_runtime.models import RuntimeObservation
from wuji_task_runtime.capture_client import CaptureControlClient
from wuji_task_runtime.errors import RuntimeTransportError
from wuji_task_runtime.process_cleanup import ProcessCleanupClient


ANCHOR = datetime(2026, 9, 23, 0, 0, tzinfo=timezone.utc)


class Cursor:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return self.value


class Connection:
    def __init__(self, anchor=ANCHOR):
        self.anchor = anchor

    def execute(self, statement, parameters):
        assert "kind='control.applied'" in statement
        assert "kind='task.started'" in statement
        assert "kind='completion.control_applied'" in statement
        assert "payload_json::jsonb->>'action'='quiesce'" in statement
        assert parameters == (
            "tenant", "project", "task", "1",
            "tenant", "project", "task", "task",
            "tenant", "project", "task",
        )
        return Cursor((self.anchor,))


def transaction(anchor=ANCHOR):
    tx = SimpleNamespace(
        owner=("tenant", "project", "task"),
        task={"control_version": 2, "activated_at": ANCHOR},
        connection=Connection(anchor),
    )

    @contextmanager
    def open_transaction():
        yield tx

    return SimpleNamespace(transaction=open_transaction, tx=tx)


def core_config():
    return SimpleNamespace(
        task_id="task",
        runtime_attempt=1,
        execution_epoch=1,
        template_version="core-ctf-v1",
        namespace="core",
        pod_name="task-pod",
        capture_policy=SimpleNamespace(
            drain_timeout_seconds=5.0,
            seal_timeout_seconds=10.0,
        ),
    )


def bare_runtime(monkeypatch):
    runtime = pod_runtime.VNextPodRuntime.__new__(pod_runtime.VNextPodRuntime)
    runtime._mutex = RLock()
    runtime._require_open = lambda: None
    runtime.config = core_config()
    runtime.access = object()
    runtime.permits = transaction()
    runtime._registered = lambda _tx: None
    runtime._disable = lambda _uid: None
    monkeypatch.setattr(pod_runtime, "verify_pod_ownership", lambda *_args, **_kwargs: None)
    return runtime


def test_repeated_stop_uses_one_persisted_cleanup_window(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 23, 0, 0, tzinfo=tz)

    runtime = bare_runtime(monkeypatch)
    runtime.permits = transaction(FixedDatetime(2026, 9, 23, tzinfo=timezone.utc))
    deadlines = []
    runtime._drain_processes_and_capture = lambda _uid, *, deadline: (
        deadlines.append(deadline) or False
    )
    monkeypatch.setattr(pod_runtime, "datetime", FixedDatetime)
    monkeypatch.setattr(pod_runtime.time, "monotonic", lambda: 100.0)

    first = runtime.stop(pod_uid="pod-uid")
    runtime.permits.tx.task["control_version"] = 3
    second = runtime.stop(pod_uid="pod-uid")

    assert first.state == second.state == "stopping"
    assert deadlines == [115.0, 115.0]


def test_cleanup_window_expiry_forces_stop_and_marks_capture_gap(monkeypatch):
    runtime = pod_runtime.VNextPodRuntime.__new__(pod_runtime.VNextPodRuntime)
    runtime.config = core_config()
    runtime._capture_drained = False
    runtime._process_shutdown_confirmed = False
    runtime._process_shutdown_unknown = False
    runtime._capture_sealed = False
    runtime._capture_final_seq = None
    runtime._capture_seal_status = None
    runtime._capture_last_status = None
    runtime._capture_window_incomplete = False
    runtime._capture_session = None
    runtime._restore_capture_session = lambda _pod_uid: None
    calls = []
    runtime.capture_client = SimpleNamespace(
        bind_pod_uid=lambda _pod_uid: None,
        drain=lambda **kwargs: calls.append(("drain", kwargs["timeout_seconds"])),
        seal=lambda **kwargs: (
            calls.append(("seal", kwargs["timeout_seconds"]))
            or {"state": "sealed-complete", "latest_item_seq": 0}
        ),
    )
    runtime.process_shutdown = lambda **_kwargs: {
        "status": "accepted",
        "task_id": "task",
        "execution_epoch": "1",
        "runtime_attempt": "1",
        "archive_status": "complete",
    }
    runtime.pods = SimpleNamespace(read_pod=lambda *_args: {
        "status": {"containerStatuses": [
            {"name": "kali", "state": {"running": {}}}
        ]}
    })

    monkeypatch.setattr(pod_runtime.time, "monotonic", lambda: 100.0)
    assert runtime._drain_processes_and_capture("pod-uid", deadline=110.0) is False
    assert calls == [("drain", 10.0)]

    monkeypatch.setattr(pod_runtime.time, "monotonic", lambda: 111.0)
    assert runtime._drain_processes_and_capture("pod-uid", deadline=110.0) is True
    assert calls == [("drain", 10.0)]
    assert runtime._capture_window_incomplete is True


def test_sealed_capture_reaches_the_final_watermark_before_persisting_sealed(monkeypatch):
    runtime = pod_runtime.VNextPodRuntime.__new__(pod_runtime.VNextPodRuntime)
    runtime.config = core_config()
    runtime._capture_drained = True
    runtime._process_shutdown_confirmed = True
    runtime._process_shutdown_unknown = False
    runtime._capture_sealed = False
    runtime._capture_final_seq = None
    runtime._capture_seal_status = None
    runtime._capture_last_status = None
    runtime._capture_window_incomplete = False
    runtime._capture_cursor = 1
    runtime._capture_session = SimpleNamespace(
        capture_session_id="session", state="draining"
    )
    runtime._restore_capture_session = lambda _pod_uid: None
    runtime.capture_client = SimpleNamespace(
        bind_pod_uid=lambda _pod_uid: None,
        seal=lambda **_kwargs: {
            "binding": {}, "state": "sealed-complete", "ready": False,
            "started_at": "2026-09-23T00:00:00Z", "latest_item_seq": 3,
        },
    )
    runtime.pods = SimpleNamespace(read_pod=lambda *_args: {
        "status": {"containerStatuses": [
            {"name": "kali", "state": {"terminated": {"exitCode": 0}}}
        ]}
    })
    persisted = []
    runtime._remember_capture_status = lambda local, *, state=None: (
        persisted.append(state or local["state"]) or runtime._capture_session
    )
    runtime._ingest_capture_items = lambda **_kwargs: (
        setattr(runtime, "_capture_cursor", runtime._capture_cursor + 1) or True
    )
    runtime._mark_capture_incomplete = lambda: persisted.append("failed")
    monkeypatch.setattr(pod_runtime.time, "monotonic", lambda: 100.0)

    assert runtime._drain_processes_and_capture("pod-uid", deadline=110.0) is True
    assert runtime._capture_cursor == 3
    assert persisted == ["sealed-complete"]


def test_sealed_capture_no_progress_is_persisted_as_incomplete(monkeypatch):
    runtime = pod_runtime.VNextPodRuntime.__new__(pod_runtime.VNextPodRuntime)
    runtime.config = core_config()
    runtime._capture_drained = True
    runtime._process_shutdown_confirmed = True
    runtime._process_shutdown_unknown = False
    runtime._capture_sealed = False
    runtime._capture_final_seq = None
    runtime._capture_seal_status = None
    runtime._capture_last_status = None
    runtime._capture_window_incomplete = False
    runtime._capture_cursor = 1
    runtime._capture_session = SimpleNamespace(
        capture_session_id="session", state="draining"
    )
    runtime._restore_capture_session = lambda _pod_uid: None
    runtime.capture_client = SimpleNamespace(
        bind_pod_uid=lambda _pod_uid: None,
        seal=lambda **_kwargs: {
            "binding": {}, "state": "sealed-complete", "ready": False,
            "started_at": "2026-09-23T00:00:00Z", "latest_item_seq": 2,
        },
    )
    runtime.pods = SimpleNamespace(read_pod=lambda *_args: {
        "status": {"containerStatuses": [
            {"name": "kali", "state": {"terminated": {"exitCode": 0}}}
        ]}
    })
    persisted = []
    runtime._ingest_capture_items = lambda **_kwargs: False
    runtime._mark_capture_incomplete = lambda: persisted.append("failed")
    monkeypatch.setattr(pod_runtime.time, "monotonic", lambda: 100.0)

    assert runtime._drain_processes_and_capture("pod-uid", deadline=110.0) is True
    assert persisted == ["failed"]


def test_terminal_persistence_failure_keeps_the_pod(monkeypatch):
    runtime = bare_runtime(monkeypatch)
    runtime._cleanup_deadline = lambda _tx: 100.0
    runtime._drain_processes_and_capture = lambda _uid, *, deadline: True
    runtime._process_shutdown_unknown = False
    runtime._capture_window_incomplete = False
    runtime.pods = SimpleNamespace(read_pod=lambda *_args: {"metadata": {"uid": "pod-uid"}})
    deleted = []
    runtime.controller = SimpleNamespace(
        stop=lambda *_args: RuntimeObservation("stopped", "task-pod", "pod-uid"),
        delete_terminal=lambda *_args: deleted.append(True),
    )
    runtime._record_terminal_observations = lambda *_args: (_ for _ in ()).throw(
        DomainError("terminal_store_unavailable", 503)
    )

    with pytest.raises(DomainError) as failure:
        runtime.stop(pod_uid="pod-uid")

    assert failure.value.code == "terminal_store_unavailable"
    assert deleted == []


@pytest.mark.parametrize("complete", [True, False])
def test_missing_pod_recovers_only_from_the_complete_terminal_set(
    monkeypatch, complete
):
    runtime = bare_runtime(monkeypatch)
    runtime._cleanup_deadline = lambda _tx: 100.0
    runtime._drain_processes_and_capture = lambda _uid, *, deadline: True
    runtime.controller = SimpleNamespace(stop=lambda *_args: RuntimeObservation(
        "stopping", "task-pod", "pod-uid",
        "Pod is absent without a persisted terminal observation",
        "pod_terminal_unconfirmed",
    ))
    states = {
        "task-network-init": "terminated",
        "agent": "terminated",
        "kali": "terminated",
        "capture": "terminated",
    }
    if not complete:
        states.pop("capture")
    runtime.capture_service = SimpleNamespace(
        terminal_container_states=lambda *_args, **_kwargs: states
    )

    result = runtime.stop(pod_uid="pod-uid")

    assert result.state == ("stopped" if complete else "stopping")


@pytest.mark.parametrize("client_kind", ["capture", "process"])
def test_cleanup_rpc_deadline_bounds_the_entire_response(monkeypatch, client_kind):
    clock = [100.0]
    socket_timeouts = []

    class Socket:
        def settimeout(self, seconds):
            socket_timeouts.append(seconds)

    class Response:
        status = 200
        fp = SimpleNamespace(raw=SimpleNamespace(_sock=Socket()))

        def read(self, _length):
            clock[0] += 3.0
            return b"x"

    class Connection:
        sock = Socket()

        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args, **_kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    if client_kind == "capture":
        from wuji_task_runtime import capture_client as module
        client = CaptureControlClient.__new__(CaptureControlClient)
        client.maximum_chunk_bytes = client.maximum_json_bytes = 1024
        client.timeout = 2.0
        call = lambda: client._request("GET", "/v1/items", timeout_seconds=2.0)
    else:
        from wuji_task_runtime import process_cleanup as module
        client = ProcessCleanupClient.__new__(ProcessCleanupClient)
        client.maximum_json_bytes = 1024
        client.timeout = 2.0
        client.bearer_token = lambda: "token"
        call = lambda: client.cleanup(
            task_id="task", execution_epoch=1, runtime_attempt=1,
            reason="stop", timeout_seconds=2.0,
        )
    client.host, client.port, client.context = "localhost", 443, object()
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)

    with pytest.raises(RuntimeTransportError):
        call()
    assert socket_timeouts == [2.0, 2.0]


def test_partial_seal_persists_a_failed_capture_session(monkeypatch):
    runtime = bare_runtime(monkeypatch)
    runtime.capture_registration = PodCaptureRegistration(
        collector_ref="collector", evidence_origin="fixture_capture",
        capture_layer="proxy+pcap",
    )
    runtime.receiver = SimpleNamespace(environment_ref="environment")
    status = runtime._capture_status_document({
        "binding": {"pod_uid": "pod-uid"},
        "state": "sealed-incomplete",
        "started_at": "2026-09-23T00:00:00Z",
    })
    assert status.state.value == "failed"
