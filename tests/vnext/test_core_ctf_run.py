"""The mechanism runner requires actual container evidence, not Task labels."""

from copy import deepcopy

from run_core_ctf import _redacted_headers, _runtime_stopped


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
