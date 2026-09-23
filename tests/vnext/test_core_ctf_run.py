"""The mechanism runner requires actual container evidence, not Task labels."""

from copy import deepcopy
import time

import pytest

from run_core_ctf import RunFailure, _cancel_and_stop, _redacted_headers, _runtime_stopped


def test_runner_requires_one_complete_terminal_binding_and_redacts_sessions():
    binding = {
        "task_id": "task", "runtime_attempt": "1",
        "execution_epoch": "2", "pod_uid": "pod-uid",
    }
    runtime = {
        "state": "stopped", "runtime_attempt": "1", "pod_uid": "pod-uid",
        "terminal_observations": [
            {"container_name": name, "state": "terminated", "binding": binding}
            for name in ("task-network-init", "agent", "kali", "capture")
        ],
    }
    assert _runtime_stopped(runtime, "task")
    assert not _runtime_stopped(runtime, "another-task")
    missing = deepcopy(runtime)
    missing["terminal_observations"].pop()
    assert not _runtime_stopped(missing, "task")
    mixed = deepcopy(runtime)
    mixed["terminal_observations"][0]["binding"] = {**binding, "pod_uid": "old-pod"}
    assert not _runtime_stopped(mixed, "task")
    assert _redacted_headers([("Set-Cookie", "private"), ("Content-Type", "application/json")]) == {
        "Set-Cookie": "<redacted>", "Content-Type": "application/json",
    }


def test_failed_cleanup_accepts_external_stop_without_a_capture_session(tmp_path):
    binding = {
        "task_id": "task", "runtime_attempt": "1",
        "execution_epoch": "2", "pod_uid": "pod-uid",
    }
    runtime = {
        "state": "stopped", "runtime_attempt": "1", "pod_uid": "pod-uid",
        "terminal_observations": [
            {"container_name": name, "state": "terminated", "binding": binding}
            for name in ("task-network-init", "agent", "kali", "capture")
        ],
    }

    class Browser:
        def json(self, _method, path):
            if path.endswith("/overview"):
                return {"runtime": runtime}
            if path.endswith("/capture-sessions"):
                return {"sessions": []}
            return {"task_id": "task", "desired_state": "cancel", "observed_state": "quiescing"}

    browser = Browser()
    stopped, sessions, overview = _cancel_and_stop(
        browser, "task", "cancel-key", deadline=time.monotonic() + 1,
        poll=0.001, events=tmp_path / "failed-events.jsonl",
        require_capture_seal=False,
    )
    assert stopped["observed_state"] == "quiescing"
    assert sessions == {"sessions": []} and overview["runtime"] == runtime
    with pytest.raises(RunFailure, match="capture seal"):
        _cancel_and_stop(
            browser, "task", "cancel-key", deadline=time.monotonic() + 0.02,
            poll=0.001, events=tmp_path / "strict-events.jsonl",
        )
