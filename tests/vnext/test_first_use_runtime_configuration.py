"""Refresh the real runtime composition without restarting existing routes."""

from dataclasses import replace
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))

from deployment_common import Deployment, Settings
from wuji_core.admission.common import digest
from wuji_core.admission.tools import ToolCapabilityResolver
from wuji_core.execution.dispatch_outbox import TaskSupervisorTransport
from wuji_core.execution.process_gate import ProcessToolGate
from wuji_core.execution.workspace_gate import WorkspaceToolGate
from wuji_core.persistence.uow import DomainError
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


def test_empty_profile_catalog_uses_the_explicit_worker_lock(tmp_path):
    k8s = module("scripts/vnext/k8s.py", "empty_profile_catalog_k8s")
    tls = tmp_path / "tls"
    k8s.certificates(tls, services=())
    public_key = tmp_path / "identity.pub"
    public_key.write_bytes(
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    profiles = tmp_path / "profiles.json"
    profiles.write_text("[]")
    settings = Settings(
        role="runtime",
        database_file="/fixture/database.json",
        public_key_file=str(public_key),
        issuer="https://identity.invalid",
        audience="fixture",
        service_token_file="/fixture/service.token",
        ca_file=str(tls / "ca.crt"),
        artifact_root=str(tmp_path / "artifacts"),
        profiles_file=str(profiles),
        worker_lock_digest="a" * 64,
    )

    deployment = Deployment(settings)

    assert deployment.profiles == []
    assert deployment.lock_digest == "a" * 64
    with pytest.raises(ValueError, match="empty profile catalog"):
        Deployment(settings.model_copy(update={"worker_lock_digest": None}))


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


def test_gate_waits_for_one_projected_executor_refresh():
    gates = module("ops/vnext/gate_deployment.py", "gate_executor_refresh_test")
    calls = []

    class Gate:
        def _assembly(self, access, ref):
            calls.append((access, ref))
            if len(calls) == 1:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return "available"

    refreshes = []
    wrapper = gates.RefreshingToolGate(
        Gate(),
        SimpleNamespace(refresh=lambda *_: refreshes.append("refresh")),
        object(),
        refresh_timeout_seconds=1,
        refresh_interval_seconds=0.1,
        sleep=lambda _seconds: None,
        monotonic=lambda: 0,
    )

    assert wrapper._assembly("access", "tool-ref") == "available"
    assert calls == [("access", "tool-ref"), ("access", "tool-ref")]
    assert refreshes == ["refresh", "refresh"]


def test_core_model_tools_use_their_real_process_and_workspace_assemblies():
    gates = module("ops/vnext/gate_deployment.py", "core_model_assembly_test")
    owner = ("tenant", "project", "task")
    process = SimpleNamespace(name="kali_exec", allowed_target_kinds=["process"], executor_ref="core")
    workspace = SimpleNamespace(name="workspace_publish", allowed_target_kinds=["workspace_bundle"],
                                executor_ref="core", ref="workspace-ref")
    registration = SimpleNamespace(ref="core", protocol="process.v1", collector_subject="collector",
                                   allowed_tool_refs=["workspace-ref"])
    executor = SimpleNamespace(
        invoke=lambda *_a, **_k: None,
        query_process=lambda *_a, **_k: None,
        export=lambda *_a, **_k: None,
        import_publication=lambda *_a, **_k: None,
    )

    @contextmanager
    def transaction(_access, task_id):
        assert task_id == owner[2]
        yield SimpleNamespace(owner=owner)

    registry = SimpleNamespace(
        binding=lambda _access: SimpleNamespace(identity=SimpleNamespace(task_id=owner[2])),
        tool=lambda _tx, ref: {"process-ref": process, "workspace-ref": workspace}[ref],
        executor=lambda _tx, _ref: registration,
    )
    gate = SimpleNamespace(
        registry=registry,
        admission=SimpleNamespace(uow=SimpleNamespace(transaction=transaction)),
        executors={(*owner, "core"): executor},
        collector_accesses={(*owner, "core"): SimpleNamespace(
            principal=SimpleNamespace(subject="collector")
        )},
        _assembly=lambda *_: pytest.fail("Core model tool entered the legacy executor contract"),
    )
    refresher = SimpleNamespace(refresh=lambda *_: None)
    wrapper = gates.RefreshingToolGate(gate, refresher, object())
    process_gate = ProcessToolGate(gate)
    workspace_gate = WorkspaceToolGate(gate, SimpleNamespace())
    transfer = gates.WorkspaceTransferDispatch(gate)
    assert wrapper._assembly(None, "process-ref", assemble=process_gate._assembly)[-1] == "exec"
    assert wrapper._assembly(
        None, "workspace-ref",
        assemble=lambda access, ref: (
            workspace_gate._definition(access, ref, "workspace_publish"),
            transfer.require_available(owner, "core"),
        ),
    )[1] is executor
    del gate.executors[(*owner, "core")]
    with pytest.raises(DomainError, match="CAPABILITY_UNAVAILABLE"):
        transfer.require_available(owner, "core")


def test_model_capability_resolver_routes_published_tool_kinds(monkeypatch):
    import wuji_core.admission.tools as tool_module

    definitions = {
        "process-ref": SimpleNamespace(allowed_target_kinds=["process"]),
        "workspace-ref": SimpleNamespace(allowed_target_kinds=["workspace_bundle"]),
    }

    @contextmanager
    def transaction(_access, _task_id, *, capability):
        assert capability == "model_request"
        yield object()

    registry = SimpleNamespace(
        binding=lambda _access: SimpleNamespace(identity=SimpleNamespace(task_id="task")),
        config=lambda _tx: object(),
        tool=lambda _tx, ref: definitions[ref],
    )
    gate = SimpleNamespace(registry=registry, admission=SimpleNamespace(
        uow=SimpleNamespace(transaction=transaction)
    ))
    monkeypatch.setattr(tool_module, "current_run", lambda *_args: (object(), object()))
    monkeypatch.setattr(tool_module, "model_function_capabilities", lambda *_args: ({
        "kali_exec": {"category": "environment_action", "source_ref": "process-ref", "input_schema_digest": digest({})},
        "workspace_publish": {"category": "environment_action", "source_ref": "workspace-ref", "input_schema_digest": digest({})},
    }, set()))
    seen = []
    advertised = [SimpleNamespace(
        function=SimpleNamespace(name=name),
        model_dump=lambda name=name, **_kwargs: {"function": {"name": name, "parameters": {}}},
    ) for name in ("kali_exec", "workspace_publish")]
    ToolCapabilityResolver(gate, assemble=lambda *args: seen.append(args)).require_available(
        None, advertised
    )
    assert [item[1:] for item in seen] == [
        ("process-ref", "process", "kali_exec"),
        ("workspace-ref", "workspace_bundle", "workspace_publish"),
    ]


def test_runtime_refuses_to_start_without_the_session_transport(monkeypatch):
    runtime = module("services/wuji-runtime/deployment.py", "runtime_session_required_test")
    settings = SimpleNamespace(
        supervisor_url="https://supervisor.invalid",
        receiver_token_file="/run/receiver.token",
        host_origin="https://runtime.invalid",
        model_gate_url="https://gates.invalid/model",
        tool_gate_url="https://gates.invalid/tools",
        task_ids=["task"],
        session_transport=False,
    )
    monkeypatch.setattr(runtime, "load_settings", lambda _role: settings)

    with pytest.raises(ValueError, match="fixed runtime"):
        runtime.build_runtime()
