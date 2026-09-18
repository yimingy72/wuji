"""Focused A7 deployment-adapter checks; no Kubernetes or Secret reads."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "wuji_launch_adapter", ROOT / "ops" / "vnext" / "launch_adapter.py"
)
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)

DIGEST = "a" * 64
SCOPE = "b" * 64
LOCK = "c" * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def task_entry(task_id: str):
    return {
        "task_config": {
            "tenant_id": "tenant-a", "project_id": "project-a", "task_id": task_id,
            "runtime_attempt": 1, "execution_epoch": 2,
            "scope_digest": SCOPE, "config_digest": DIGEST,
        },
        "receiver": {"receiver_id": "receiver-" + task_id},
        "service_names": {"agent": "task-agent-" + task_id, "kali": "task-kali-" + task_id},
        "supervisor_url": "https://task-agent-" + task_id + ".wuji-vnext-test.svc:8443",
    }


def gate_entry(task_id: str):
    return {
        "binding": {
            "tenant_id": "tenant-a", "project_id": "project-a", "task_id": task_id,
            "executor_ref": "kali-workspace-v1", "receiver_id": "receiver-" + task_id,
            "environment_ref": "environment-" + task_id, "runtime_attempt": 1,
        },
        "base_url": "https://task-kali-" + task_id + ".wuji-vnext-test.svc:8444",
        "gate_token_file": "/run/wuji/credentials/service.token",
        "collector_token_file": "/run/wuji/credentials/collector.token",
    }


class Store:
    def __init__(self, runtime, gates):
        self.documents = {"runtime-config": runtime, "gates-config": gates}
        self.replacements = []

    def read(self, name):
        return copy.deepcopy(self.documents[name])

    def replace(self, name, document):
        self.replacements.append(name)
        self.documents[name] = copy.deepcopy(document)


def make_store():
    profile = {"ref": "harness.reason.task.a", "revision": "1", "body": {"lock_digest": LOCK}}
    runtime = {
        "kind": "ConfigMap", "metadata": {"name": "runtime-config", "resourceVersion": "7"},
        "data": {
            "deployment.json": json.dumps({"task_ids": ["task-a"], "pod_runtime": {"tasks": [task_entry("task-a")]}}),
            "profiles.json": json.dumps([profile]),
        },
    }
    gates = {
        "kind": "ConfigMap", "metadata": {"name": "gates-config", "resourceVersion": "9"},
        "data": {"deployment.json": json.dumps({"executors": [gate_entry("task-a")]})},
    }
    return Store(runtime, gates), profile


def test_wire_adds_one_task_without_rollout_or_dropping_existing_task():
    store, old_profile = make_store()
    profiles = [{"ref": "harness.explore.task.b", "revision": "1", "body": {"lock_digest": LOCK}}]
    profile_digest = hashlib.sha256(canonical(profiles)).hexdigest()
    binding = {"runtime_entry": task_entry("task-b"), "gate_entry": gate_entry("task-b"),
               "profiles": profiles, "profile_digest": profile_digest}
    adapter_instance = adapter.DeploymentLaunchAdapter(
        {"namespace": "wuji-vnext-test"},
        {"store": store, "binding_loader": lambda request: binding},
    )
    result = adapter_instance.wire({
        "task_id": "task-b", "operation_id": "op-b", "definition_digest": DIGEST,
        "profile_digest": profile_digest, "attempt": 1, "epoch": 2,
    })
    runtime = json.loads(store.documents["runtime-config"]["data"]["deployment.json"])
    gates = json.loads(store.documents["gates-config"]["data"]["deployment.json"])
    assert sorted(runtime["task_ids"]) == ["task-a", "task-b"]
    assert {item["task_config"]["task_id"] for item in runtime["pod_runtime"]["tasks"]} == {"task-a", "task-b"}
    assert {item["binding"]["task_id"] for item in gates["executors"]} == {"task-a", "task-b"}
    assert result["rolled_deployments"] == []
    assert store.replacements == ["runtime-config", "gates-config"]
    assert old_profile in json.loads(store.documents["runtime-config"]["data"]["profiles.json"])


def test_same_task_digest_conflict_and_secret_input_fail_closed():
    store, _ = make_store()
    with pytest.raises(adapter.LaunchAdapterError) as error:
        adapter.merge_runtime_document(
            json.loads(store.documents["runtime-config"]["data"]["deployment.json"]),
            {**task_entry("task-a"), "task_config": {**task_entry("task-a")["task_config"], "config_digest": "d" * 64}},
        )
    assert error.value.code == "INPUT_DIGEST_CONFLICT"
    with pytest.raises(adapter.LaunchAdapterError) as error:
        adapter.LaunchInput.from_mapping({
            "task_id": "task-a", "operation_id": "op", "definition_digest": DIGEST,
            "attempt": 1, "secret": "must-not-be-accepted",
        }, phase="prepare")
    assert error.value.code == "INVALID_SCHEMA"


def test_same_task_next_attempt_requires_same_definition_and_contiguous_attempt():
    document = {"task_ids": ["task-a"], "pod_runtime": {"tasks": [task_entry("task-a")]}}
    next_entry = copy.deepcopy(task_entry("task-a"))
    next_entry["task_config"]["runtime_attempt"] = 2
    next_entry["task_config"]["execution_epoch"] = 3
    assert adapter.merge_runtime_document(document, next_entry) == "replaced"
    skipped = copy.deepcopy(next_entry)
    skipped["task_config"]["runtime_attempt"] = 4
    with pytest.raises(adapter.LaunchAdapterError) as error:
        adapter.merge_runtime_document(document, skipped)
    assert error.value.code == "INPUT_DIGEST_CONFLICT"
