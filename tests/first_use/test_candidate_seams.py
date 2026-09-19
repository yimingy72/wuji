"""A8 targeted seam assertions added after the frozen suite was collected.

Real launch service/PG for budget recovery; only external management transport
is synthetic. Adapter-observe cases isolate real production control flow with
recording DB/Pod boundaries. No Kubernetes, provider inference or real secrets.
"""
import importlib.util
import importlib
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import httpx

from conftest import audit_directory, db_environment  # existing isolated PG fixtures
from support.first_use import create_task, first_use_case, task_view, bearer
from test_task_creation import payload
from test_first_use_launch import FixtureLaunchAdapter, _start, _worker
from wuji_core.execution.launch import LaunchUnknown

ROOT = Path(__file__).resolve().parents[2]


def module(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def record(name, value):
    output = Path(os.environ["WUJI_A8_SEAM_EVIDENCE"])
    output.mkdir(parents=True, exist_ok=True)
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    (output / (name + ".json")).write_text(
        json.dumps({"candidate_sha": candidate_sha, **value}, indent=2) + "\n"
    )


def http_evidence(client):
    def headers(values):
        return {key: "[REDACTED TEST CREDENTIAL]" if key.lower() in {"authorization", "cookie", "set-cookie"} else value
                for key, value in values.items()}
    return [{"request": {"method": item.request.method, "url": item.request.url,
                         "headers": headers(item.request.headers), "body": item.request.body.decode()},
             "response": {"status": item.response.status_code, "headers": headers(item.response.headers),
                          "body": item.response.body.decode()}} for item in client.exchanges]


def test_lost_budget_response_remains_reconcilable_in_real_launch_worker(db_environment, audit_directory):
    keys = module("ops/vnext/task_model_keys.py", "a8_budget_seam")
    requests, key_reads, persisted = [], [], False
    class Store:
        def get_or_create(self, tenant, task):
            key_reads.append({"tenant_id": tenant, "task_id": task})
            return "sk-synthetic-budget-test-only-0000000000000000"
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="a8-lost-budget-create")
        task_id = created["task_id"]
        _start(case, task_id, key="a8-lost-budget-start")
        def gateway(request):
            nonlocal persisted
            requests.append({"method": request.method, "path": request.url.path,
                             "query": request.url.query.decode()})
            if request.method == "POST":
                persisted = True
                raise httpx.ReadTimeout("synthetic lost accepted response", request=request)
            if not persisted:
                return httpx.Response(404)
            return httpx.Response(200, json={"info": {"models": ["model-fixture"], "max_budget": 1,
                "metadata": {"wuji_task_id": task_id, "wuji_tenant_id": "tenant-fixture"}}})
        with httpx.Client(base_url="https://synthetic-budget.invalid", transport=httpx.MockTransport(gateway)) as client:
            budget = keys.NativeTaskBudget(Store(), client)
            class Adapter(FixtureLaunchAdapter):
                def prepare(self, incoming):
                    budget.ensure(task_id=task_id, tenant_id="tenant-fixture", model_alias="model-fixture", budget_usd="1")
                    return super().prepare(incoming)
                def observe(self, incoming):
                    if incoming["phase"] == "prepare":
                        budget.ensure(task_id=task_id, tenant_id="tenant-fixture", model_alias="model-fixture", budget_usd="1")
                    return super().observe(incoming)
            adapter = Adapter()
            worker = _worker(case, adapter)
            first = worker.run_once(limit=1)
            second = worker.run_once(limit=1)
            view = case.client.get(f"/api/v2/tasks/{task_id}/launch", headers=bearer(case)).json()
            record("budget-lost-response", {"first_progress": first, "second_progress": second,
                "launch": view, "gateway_key_persisted": persisted, "gateway_requests": requests,
                "task_key_reads": key_reads,
                "wire_calls": adapter.wire_calls, "mode": "real_pg_launch_synthetic_gateway",
                "http_exchanges": http_evidence(case.client)})
            assert first[0]["phase_status"] == "reconciling"
            assert [item | {"query": "[same-key]" if item["query"] else ""} for item in requests] == [
                {"method": "GET", "path": "/key/info", "query": "[same-key]"},
                {"method": "POST", "path": "/key/generate", "query": ""},
                {"method": "GET", "path": "/key/info", "query": "[same-key]"},
            ]
            assert requests[0]["query"] == requests[2]["query"]
            assert key_reads == [
                {"tenant_id": "tenant-fixture", "task_id": task_id},
                {"tenant_id": "tenant-fixture", "task_id": task_id},
            ]
            assert adapter.observe_calls[0]["allow_repair"] is True
            assert view["phase_status"] == "succeeded" and view["phase"] == "ready"
            assert adapter.wire_calls == 1


def test_production_prepare_maps_unknown_budget_to_launch_unknown():
    adapter_module = module("ops/vnext/launch_adapter.py", "a8_production_budget_mapping")
    sys.path.insert(0, str(ROOT / "ops/vnext"))
    keys = importlib.import_module("task_model_keys")
    selected = {"task": {"external_analysis_approved": True, "budget": {"amount": "1"}},
                "model_profile": {"ref": "model-fixture", "revision": "1", "upstream_model": "model-fixture"},
                "runtime_profile": {"ref": "runtime-fixture", "revision": "1", "limits": {"max_elapsed_seconds": 60}}}
    connection = SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: (True,)), close=lambda: None)
    launch = SimpleNamespace(owner_connection=lambda config: connection, configured_evaluation_mode=lambda config: "real_model",
        finalise_definition=lambda *args, **kwargs: {"definition": selected},
        ensure_operator_actor=lambda *args, **kwargs: None, require_receiver_bearer_window=lambda *args, **kwargs: None)
    class UnknownBudget:
        def ensure(self, **kwargs):
            raise keys.TaskBudgetUnknown("gateway_budget_unknown")
    provisioner = adapter_module.ProductionLaunchProvisioner.__new__(adapter_module.ProductionLaunchProvisioner)
    provisioner.config = {"owner": ["tenant-fixture", "project-fixture", "template-task"], "definition": selected}
    provisioner.options = {"task_budget": UnknownBudget(), "deployment_auth_dir": "/synthetic-not-read"}
    provisioner._task_launch = lambda: launch
    provisioner._row = lambda *args: {
        "definition": selected,
        "desired_state": "run",
        "observed_state": "reconciling",
    }
    actual_error = None
    try:
        provisioner.prepare(SimpleNamespace(task_id="task-a8"))
    except Exception as error:
        actual_error = error
    record("production-budget-classification", {"exception_type": type(actual_error).__name__,
        "implements_launch_unknown": isinstance(actual_error, LaunchUnknown),
        "reason_code": getattr(actual_error, "reason_code", None),
        "mode": "production_prepare_recording_prerequisites"})
    assert type(actual_error) is keys.TaskBudgetUnknown
    assert isinstance(actual_error, LaunchUnknown)
    assert actual_error.reason_code == "gateway_budget_unknown"


WIRE_DIGEST = "a" * 64
WIRE_SCOPE = "b" * 64
WIRE_LOCK = "c" * 64


def _wire_recording_fixture(adapter):
    sys.path.insert(0, str(ROOT / "ops/vnext"))
    task_launch = importlib.import_module("task_launch")
    task_id = "task-a8"
    profile = {
        "ref": "harness.reason.task.a8",
        "revision": "1",
        "body": {"lock_digest": WIRE_LOCK},
    }
    binding = {
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "task_id": task_id,
        "namespace": "wuji-vnext-test",
        "runtime_attempt": 1,
        "execution_epoch": 2,
        "scope_digest": WIRE_SCOPE,
        "config_digest": WIRE_DIGEST,
        "agent_image": "registry.invalid/agent@sha256:" + "d" * 64,
        "kali_image": "registry.invalid/kali@sha256:" + "e" * 64,
        "agent_resources": {"cpu_request": "100m", "memory_request": "128Mi", "cpu_limit": "1", "memory_limit": "512Mi"},
        "kali_resources": {"cpu_request": "100m", "memory_request": "128Mi", "cpu_limit": "1", "memory_limit": "512Mi"},
        "tmp_size_limit": "128Mi",
        "pod_deadline_seconds": 60,
        "expose_pod_identity": True,
        "kali_receipts_enabled": True,
        "receiver_id": "task-task-a8-a1",
        "environment_ref": "pod-environment-task-a8-a1",
        "executor_ref": "kali-workspace-v1",
        "worker_profiles": {"reason": profile},
    }
    baseline_runtime = {
        "task_config": {
            "tenant_id": "tenant-fixture", "task_id": "baseline-task",
            "runtime_attempt": 1, "execution_epoch": 1,
            "scope_digest": WIRE_SCOPE, "config_digest": WIRE_DIGEST,
        },
        "receiver": {"receiver_id": "baseline-receiver"},
    }
    baseline_gate = {
        "binding": {
            "tenant_id": "tenant-fixture", "project_id": "project-fixture",
            "task_id": "baseline-task", "executor_ref": "kali-workspace-v1",
            "receiver_id": "baseline-receiver", "environment_ref": "baseline-environment",
        },
        "base_url": "https://baseline.invalid",
        "gate_token_file": "/run/wuji/credentials/service.token",
        "collector_token_file": "/run/wuji/credentials/collector.token",
    }
    documents = {
        "runtime-config": {
            "kind": "ConfigMap", "metadata": {"name": "runtime-config", "resourceVersion": "1"},
            "data": {
                "deployment.json": json.dumps({"task_ids": ["baseline-task"], "pod_runtime": {"tasks": [baseline_runtime]}}),
                "profiles.json": json.dumps([{"ref": "harness.baseline", "revision": "1", "body": {"lock_digest": WIRE_LOCK}}]),
            },
        },
        "gates-config": {
            "kind": "ConfigMap", "metadata": {"name": "gates-config", "resourceVersion": "1"},
            "data": {"deployment.json": json.dumps({"executors": [baseline_gate]})},
        },
    }

    class Store:
        def __init__(self):
            self.documents = documents
            self.reads = []
            self.replacements = []

        def read(self, name):
            self.reads.append(name)
            return copy.deepcopy(self.documents[name])

        def replace(self, name, document):
            self.replacements.append(name)
            self.documents[name] = copy.deepcopy(document)

    runtime_config = SimpleNamespace(
        identity_labels={
            "app.kubernetes.io/managed-by": "wuji-task-runtime-controller",
            "wuji.dev/task-id": task_id,
            "wuji.dev/tenant-id": "tenant-fixture",
            "wuji.dev/runtime-attempt": "1",
        },
        pod_name="wuji-task-a8-a1",
    )
    service_reads = []

    class CoreAPI:
        def read_namespaced_service(self, name, namespace):
            service_reads.append({"name": name, "namespace": namespace})
            return SimpleNamespace(spec=SimpleNamespace(selector=runtime_config.identity_labels))

    connection = SimpleNamespace(close=lambda: None)
    launch = SimpleNamespace(
        owner_connection=lambda _: connection,
        task_service_names=task_launch.task_service_names,
        runtime_config_document=task_launch.runtime_config_document,
        attempt_config=lambda _: runtime_config,
    )
    store = Store()
    provisioner = adapter.ProductionLaunchProvisioner.__new__(adapter.ProductionLaunchProvisioner)
    provisioner.config = {"executor": {"collector_subject": "collector-fixture"}}
    provisioner.options = {"namespace": "wuji-vnext-test", "core_api": CoreAPI()}
    provisioner.store = store
    provisioner._task_launch = lambda: launch
    provisioner._binding = lambda *args: binding
    provisioner._row = lambda *args: {
        "definition": {}, "definition_digest": WIRE_DIGEST,
        "runtime_attempt": 1, "execution_epoch": 2,
        "desired_state": "run", "observed_state": "reconciling",
    }
    provisioner._ensure_resources = lambda _: ({"resources": "unchanged"}, runtime_config)
    provisioner._pod_observation = lambda *args: {"status": "ready", "pod_uid": "pod-a8"}
    return provisioner, store, service_reads, task_id


def test_wire_observation_does_not_accept_pod_without_gate_binding(monkeypatch):
    adapter = module("ops/vnext/launch_adapter.py", "a8_wire_seam")
    provisioner, store, service_reads, task_id = _wire_recording_fixture(adapter)
    provisioner._pod_observation = lambda *args: (_ for _ in ()).throw(
        AssertionError("Pod readiness must not be consulted before wire completeness")
    )
    request = adapter.LaunchInput.from_mapping({
        "task_id": task_id, "operation_id": "wire-a8",
        "definition_digest": WIRE_DIGEST, "profile_digest": WIRE_DIGEST,
        "attempt": 1, "epoch": 2, "phase": "wire", "external_ref": "wire-a8",
    }, phase="observe")
    observed = provisioner.observe(request)
    record("wire-incomplete-binding", {"observed": observed, "configmap_reads": store.reads,
        "service_reads": service_reads, "configmap_replacements": store.replacements,
        "gate_has_task_binding": False, "mode": "production_observe_recording_db_k8s_boundaries"})
    assert observed == {"status": "unknown", "phase_status": "reconciling",
                        "external_ref": "wire-a8", "reason_code": "wire_incomplete"}
    assert store.reads == ["runtime-config", "gates-config"]
    assert store.replacements == []
    assert service_reads == []


def test_active_wire_repair_completes_configmaps_profiles_services_and_continues():
    adapter = module("ops/vnext/launch_adapter.py", "a8_wire_repair_seam")
    provisioner, store, service_reads, task_id = _wire_recording_fixture(adapter)
    repairing = adapter.LaunchInput.from_mapping({
        "task_id": task_id, "operation_id": "wire-repair-a8",
        "definition_digest": WIRE_DIGEST, "profile_digest": WIRE_DIGEST,
        "attempt": 1, "epoch": 2, "phase": "wire", "external_ref": "wire-repair-a8",
        "allow_repair": True,
    }, phase="observe")
    repaired = provisioner.observe(repairing)
    readonly = adapter.LaunchInput.from_mapping({
        "task_id": task_id, "operation_id": "wire-repair-a8",
        "definition_digest": WIRE_DIGEST, "profile_digest": WIRE_DIGEST,
        "attempt": 1, "epoch": 2, "phase": "wire", "external_ref": "wire-repair-a8",
    }, phase="observe")
    observed = provisioner.observe(readonly)
    runtime = json.loads(store.documents["runtime-config"]["data"]["deployment.json"])
    profiles = json.loads(store.documents["runtime-config"]["data"]["profiles.json"])
    gates = json.loads(store.documents["gates-config"]["data"]["deployment.json"])
    task_ids = [item["task_config"]["task_id"] for item in runtime["pod_runtime"]["tasks"]]
    gate_task_ids = [item["binding"]["task_id"] for item in gates["executors"]]
    profile_refs = [item["ref"] for item in profiles]
    record("wire-repair-continues", {
        "repair_result": repaired, "readonly_observation": observed,
        "configmap_reads": store.reads, "configmap_replacements": store.replacements,
        "service_reads": service_reads, "runtime_task_ids": task_ids,
        "gate_task_ids": gate_task_ids, "profile_refs": profile_refs,
        "mode": "production_observe_recording_db_k8s_boundaries",
    })
    assert repaired["status"] == "ready"
    assert observed == {"external_ref": "wire-repair-a8", "status": "ready",
                        "phase_status": "ready", "pod_uid": "pod-a8"}
    assert store.replacements == ["runtime-config", "gates-config"]
    assert task_id in task_ids
    assert task_id in gate_task_ids
    assert "harness.reason.task.a8" in profile_refs
    assert [item["name"] for item in service_reads] == [
        "task-agent-taska8", "task-kali-taska8"
    ]


def test_cancelled_prepare_observation_does_not_invoke_prepare_again():
    adapter = module("ops/vnext/launch_adapter.py", "a8_cancel_seam")
    calls = []
    class Connection:
        def execute(self, query, args):
            return SimpleNamespace(fetchone=lambda: ("a" * 64,) if "encode(sha256" in query else None)
        def close(self):
            pass
    provisioner = adapter.ProductionLaunchProvisioner.__new__(adapter.ProductionLaunchProvisioner)
    provisioner.config = {}
    provisioner._owner = lambda task: ("tenant-a8", "project-a8", task)
    provisioner._row = lambda *args: {"definition": {}, "definition_digest": "a"*64,
        "runtime_attempt": 1, "execution_epoch": 2,
        "desired_state": "cancel", "observed_state": "quiescing"}
    provisioner._task_launch = lambda: SimpleNamespace(owner_connection=lambda _: Connection())
    provisioner.prepare = lambda request: calls.append("prepare") or {"status": "ready"}
    request = SimpleNamespace(phase="prepare", task_id="task-a8", definition_digest="a"*64,
                              profile_digest=adapter.task_profile_digest({}), external_ref="prepare-a8",
                              allow_repair=True)
    observed = provisioner.observe(request)
    record("cancel-recovery-write", {"observed": observed, "write_producer_calls": calls,
        "known_task_state": {"desired_state": "cancel", "observed_state": "quiescing"},
        "repair_requested": True, "mode": "production_observe_recording_db_boundary"})
    assert observed == {"status": "unknown", "phase_status": "reconciling",
                        "external_ref": "prepare-a8", "reason_code": "prepare_incomplete_readonly"}
    assert calls == []
