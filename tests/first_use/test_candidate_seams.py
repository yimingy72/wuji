"""A8 targeted seam assertions added after the frozen suite was collected.

Real launch service/PG for budget recovery; only external management transport
is synthetic. Adapter-observe cases isolate real production control flow with
recording DB/Pod boundaries. No Kubernetes, provider inference or real secrets.
"""
import importlib.util
import importlib
import json
import os
from pathlib import Path
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
    (output / (name + ".json")).write_text(json.dumps({"candidate_sha": "5cdbd170939f1d2e410868ab591381331f5cdba9", **value}, indent=2) + "\n")


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
    requests, persisted = [], False
    class Store:
        def get_or_create(self, tenant, task):
            return "sk-synthetic-budget-test-only-0000000000000000"
    with first_use_case(db_environment, audit_directory) as case:
        created = create_task(case, payload(), key="a8-lost-budget-create")
        task_id = created["task_id"]
        _start(case, task_id, key="a8-lost-budget-start")
        def gateway(request):
            nonlocal persisted
            requests.append({"method": request.method, "path": request.url.path})
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
                    try:
                        budget.ensure(task_id=task_id, tenant_id="tenant-fixture", model_alias="model-fixture", budget_usd="1")
                    except keys.TaskBudgetUnavailable:
                        # Explicit adapter protocol. The separate production
                        # prepare test below verifies the real mapping too.
                        raise LaunchUnknown("gateway_budget_unknown") from None
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
                "wire_calls": adapter.wire_calls, "mode": "real_pg_launch_synthetic_gateway",
                "http_exchanges": http_evidence(case.client)})
            assert first[0]["phase_status"] == "reconciling"
            assert requests == [{"method": "GET", "path": "/key/info"},
                                {"method": "POST", "path": "/key/generate"},
                                {"method": "GET", "path": "/key/info"}]
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
            raise keys.TaskBudgetUnavailable("gateway_budget_unknown")
    provisioner = adapter_module.ProductionLaunchProvisioner.__new__(adapter_module.ProductionLaunchProvisioner)
    provisioner.config = {"owner": ["tenant-fixture", "project-fixture", "template-task"], "definition": selected}
    provisioner.options = {"task_budget": UnknownBudget(), "deployment_auth_dir": "/synthetic-not-read"}
    provisioner._task_launch = lambda: launch
    provisioner._row = lambda *args: {"definition": selected}
    actual_error = None
    try:
        provisioner.prepare(SimpleNamespace(task_id="task-a8"))
    except Exception as error:
        actual_error = error
    record("production-budget-classification", {"exception_type": type(actual_error).__name__,
        "implements_launch_unknown": isinstance(actual_error, LaunchUnknown),
        "mode": "production_prepare_recording_prerequisites"})
    assert isinstance(actual_error, LaunchUnknown), "the production adapter must translate ambiguous budget operations into the launch recovery protocol"


def test_wire_observation_does_not_accept_pod_without_gate_binding(monkeypatch):
    adapter = module("ops/vnext/launch_adapter.py", "a8_wire_seam")
    calls = []
    class Store:
        def read(self, name):
            calls.append(name)
            return {"data": {"deployment.json": '{"executors":[]}'}}
    connection = SimpleNamespace(close=lambda: None)
    provisioner = adapter.ProductionLaunchProvisioner.__new__(adapter.ProductionLaunchProvisioner)
    provisioner.config, provisioner.options, provisioner.store = {}, {}, Store()
    provisioner._task_launch = lambda: SimpleNamespace(owner_connection=lambda _: connection, attempt_config=lambda _: object())
    provisioner._binding = lambda *args: {"task_id": "task-a8"}
    provisioner._pod_observation = lambda *args: {"status": "ready", "pod_uid": "pod-a8"}
    request = SimpleNamespace(phase="wire", external_ref="wire-a8", observed_runtime_uid=None)
    observed = provisioner.observe(request)
    record("wire-incomplete-binding", {"observed": observed, "configmap_reads": calls,
        "gate_has_task_binding": False, "mode": "production_observe_recording_boundaries"})
    assert observed["status"] != "ready", "a ready Pod cannot prove the separate Gate ConfigMap update succeeded"


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
        "runtime_attempt": 1, "execution_epoch": 2, "desired_state": "cancel"}
    provisioner._task_launch = lambda: SimpleNamespace(owner_connection=lambda _: Connection())
    provisioner.prepare = lambda request: calls.append("prepare") or {"status": "ready"}
    request = SimpleNamespace(phase="prepare", task_id="task-a8", definition_digest="a"*64,
                              profile_digest=adapter.task_profile_digest({}), external_ref="prepare-a8")
    observed = provisioner.observe(request)
    record("cancel-recovery-write", {"observed": observed, "write_producer_calls": calls,
        "known_task_state": "cancel", "mode": "production_observe_recording_boundaries"})
    assert calls == [], "stop reconciliation must not re-enter mutating prepare"
