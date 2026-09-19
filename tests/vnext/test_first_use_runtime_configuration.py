"""Refresh the real runtime composition without restarting existing routes."""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))

from deployment_common import Settings
from wuji_core.execution.dispatch_outbox import TaskSupervisorTransport
from wuji_maf_worker.factory import HarnessProfile


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class Transport:
    def query(self, *args, **kwargs): pass
    def start(self, *args, **kwargs): pass
    def control(self, *args, **kwargs): pass


def test_tasks_routes_and_profiles_refresh_together_and_conflicts_preserve_old_state(tmp_path, monkeypatch):
    runtime = module("services/wuji-runtime/deployment.py", "runtime_first_use_config_test")
    path = tmp_path / "profiles.json"
    profile = HarnessProfile(ref="harness.original", revision="1", work_kind="reason",
        instructions="Read stored material only.", tool_definition_refs=("read-record",), lock_digest="a"*64,
        max_context_records=32, max_context_bytes=65536, max_output_tokens=512)
    def entry(task):
        return {"task_config": {"task_id": task}, "supervisor_url": f"https://{task}.invalid"}
    old = Settings(role="runtime", database_file="/fixture/db", public_key_file="/fixture/public",
        issuer="fixture", audience="fixture", service_token_file="/fixture/token", ca_file="/fixture/ca",
        profiles_file=str(path), task_ids=["task-a"], pod_runtime={"tasks": [entry("task-a")]})
    latest = old.model_copy(update={"task_ids": ["task-a", "task-b"],
                                   "pod_runtime": {"tasks": [entry("task-a"), entry("task-b")]}})
    published = [profile.snapshot(), replace(profile, ref="harness.next").snapshot()]
    path.write_text(json.dumps(published))
    deployment = SimpleNamespace(settings=old, profiles=[profile.snapshot()], lock_digest="a"*64)
    transport = TaskSupervisorTransport(by_task={"task-a": Transport()})
    state = runtime.RuntimeConfiguration(deployment, transport)
    observations = []
    state.environment = SimpleNamespace(refresh=lambda value: observations.append(value))
    monkeypatch.setattr(runtime, "load_settings", lambda _: latest)
    monkeypatch.setattr(runtime, "_supervisor_transport", lambda settings, _: TaskSupervisorTransport(
        by_task={task: Transport() for task in settings.task_ids}))
    state.refresh()
    assert state.task_ids == ("task-a", "task-b")
    assert set(transport.by_task) == {"task-a", "task-b"}
    assert deployment.profiles == published
    assert len(observations) == 1
    state.refresh()
    assert len(observations) == 1
    path.write_text(json.dumps([replace(profile, instructions="changed fixed bytes").snapshot(), published[1]]))
    with pytest.raises(ValueError, match="profile bytes changed"):
        state.refresh()
    assert deployment.profiles == published and len(observations) == 1
    latest = latest.model_copy(update={"task_ids": ["task-a", "task-b", "task-c"]})
    with pytest.raises(ValueError, match="discovery"):
        state.refresh()
    assert state.task_ids == ("task-a", "task-b")


def test_material_refresh_wrapper_preserves_explicit_representation():
    gates = module("ops/vnext/gate_deployment.py", "gate_first_use_config_test")
    calls = []
    class Gate:
        def result_material(self, access, call, *, representation=None):
            calls.append((access, call, representation))
            return "existing-material"
    refresher = SimpleNamespace(refresh=lambda *_: None)
    wrapper = gates.RefreshingToolGate(Gate(), refresher, object())
    assert wrapper.result_material("access", "call", representation="wuji.model-material.v2") == "existing-material"
    assert calls == [("access", "call", "wuji.model-material.v2")]
