"""Pure checks for the mounted runtime ConfigMap refresh boundary."""

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "vnext"))
SPEC = importlib.util.spec_from_file_location("pod_deployment", ROOT / "ops" / "vnext" / "pod_deployment.py")
pod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pod
SPEC.loader.exec_module(pod)


def entry(task_id, attempt=1, epoch=2):
    return {
        "task_config": {
            "task_id": task_id, "tenant_id": "tenant", "namespace": "wuji-vnext-test",
            "runtime_attempt": attempt, "execution_epoch": epoch,
            "scope_digest": "a" * 64, "config_digest": "b" * 64,
            "agent_resources": {"cpu_request": "1m", "memory_request": "1Mi", "cpu_limit": "1m", "memory_limit": "1Mi"},
            "kali_resources": {"cpu_request": "1m", "memory_request": "1Mi", "cpu_limit": "1m", "memory_limit": "1Mi"},
            "agent_image": "registry/agent@sha256:" + "1" * 64,
            "kali_image": "registry/kali@sha256:" + "2" * 64,
            "tmp_size_limit": "1Mi", "pod_deadline_seconds": 30,
            "expose_pod_identity": True, "kali_receipts_enabled": True,
        },
        "receiver": {
            "receiver_id": "receiver-" + task_id, "receiver_subject": "receiver",
            "environment_ref": "env-" + task_id, "credential_template_ref": "template",
            "model_mode": "synthetic",
        },
    }


def test_trusted_config_file_is_bounded_and_digest_aware(tmp_path):
    path = tmp_path / "deployment.json"
    path.write_text('{"pod_runtime":{"tasks":[]}}')
    reader = pod.TrustedConfigFile(path)
    assert reader.read_json()["pod_runtime"]["tasks"] == []
    assert reader.read_json() is None
    path.write_text('{"pod_runtime":{"tasks":[1]}}')
    assert reader.read_json()["pod_runtime"]["tasks"] == [1]


def test_refresh_adds_task_but_refuses_removing_known_task():
    class Runtime:
        def __init__(self, task_id):
            self.config = type("Config", (), {
                "runtime_attempt": 1, "execution_epoch": 2,
                "config_digest": "b" * 64, "scope_digest": "a" * 64,
            })()

    class Environment(pod.PodEnvironment):
        def _add_entry(self, task_id, values, receiver, item):
            self.runtimes[task_id] = Runtime(task_id)
            self._entries[task_id] = (values, receiver)

    env = Environment.__new__(Environment)
    env.runtimes = {"task-a": Runtime("task-a")}
    env._entries = {"task-a": (entry("task-a")["task_config"], entry("task-a")["receiver"])}
    env.observations = {}
    env.entry_service_names = {}
    env.service_names = {"agent": "task-agent", "kali": "task-kali"}
    env.refresh({"tasks": [entry("task-a"), entry("task-b")]})
    assert set(env.runtimes) == {"task-a", "task-b"}
    with pytest.raises(Exception) as error:
        env.refresh({"tasks": [entry("task-a")]})
    assert getattr(error.value, "code", None) == "ACTIVE_TASK_REMOVAL"
