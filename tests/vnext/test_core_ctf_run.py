"""The mechanism runner requires actual container evidence, not Task labels."""

from copy import deepcopy
import time

import pytest

from run_core_ctf import (
    Browser as HttpBrowser,
    RetryableReadFailure,
    RunFailure,
    _cancel_and_stop,
    _redacted_headers,
    _runtime_stopped,
    _wait_chain,
)


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


def test_wait_chain_exits_when_task_is_cancelled_before_completion(monkeypatch, tmp_path):
    class Browser:
        def json(self, _method, path):
            if path.endswith("/launch"):
                return {"phase_status": "running"}
            return {"desired_state": "cancel", "observed_state": "quiescing", "version": 2}

    monkeypatch.setattr("run_core_ctf._read_chain", lambda _browser, _task_id: None)
    monkeypatch.setattr("run_core_ctf.time.sleep", lambda _seconds: pytest.fail("cancelled Task was polled again"))
    with pytest.raises(RunFailure, match="Task cancelled before the mechanism chain"):
        _wait_chain(
            Browser(), "task", deadline=time.monotonic() + 1,
            poll=0.001, events=tmp_path / "events.jsonl",
        )


def test_wait_chain_retries_a_transient_exploration_read(monkeypatch, tmp_path):
    class Browser:
        def json(self, _method, path):
            if path.endswith("/launch"):
                return {"phase_status": "succeeded"}
            return {"desired_state": "run", "observed_state": "running", "version": 2}

    calls = 0

    def read_chain(_browser, _task_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RetryableReadFailure("GET /exploration returned 503")
        return {"verified": True}

    monkeypatch.setattr("run_core_ctf._read_chain", read_chain)
    monkeypatch.setattr("run_core_ctf.time.sleep", lambda _seconds: None)
    assert _wait_chain(
        Browser(), "task", deadline=time.monotonic() + 1,
        poll=0.001, events=tmp_path / "events.jsonl",
    ) == {"verified": True, "task": {"desired_state": "run", "observed_state": "running", "version": 2}}
    assert calls == 2
    assert '"phase":"read_retry"' in (tmp_path / "events.jsonl").read_text()


def test_get_503_is_retryable_without_retrying_a_write(tmp_path):
    class Response:
        status = 503
        headers = {}

        def read(self, _limit):
            return b'{}'

        def close(self):
            pass

    class Opener:
        def open(self, _request, timeout):
            return Response()

    browser = HttpBrowser("http://127.0.0.1:1", tmp_path / "http.jsonl")
    browser.opener = Opener()
    with pytest.raises(RetryableReadFailure):
        browser.json("GET", "/exploration")
    with pytest.raises(RunFailure, match="POST /commands returned 503"):
        browser.json("POST", "/commands", body={})
