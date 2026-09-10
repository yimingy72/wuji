"""Use the unmodified native Server in-process; no network service or Agent runs."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
import requests
from requests.adapters import BaseAdapter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from cairn.server import db
from cairn.server.app import app
from wuji_cairn_bridge import AgentResult, CairnPlatformClient, CairnTaskBridge, DispatchContext, ExplorationInput, SQLAlchemyJournal, TaskKey
from wuji_cairn_bridge.errors import BindingConflict, DispatchDenied
from wuji_cairn_bridge.journal import metadata
from wuji_task_runtime import ContainerResources, ExecutionPermit, RuntimeObservation, TaskRuntimeConfig

NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


class InProcessAdapter(BaseAdapter):
    def __init__(self, core):
        self.core = core
        self.calls = []
        self.drop_path = None
        self.on_read = None

    def send(self, request, **kwargs):
        url = urlsplit(request.url)
        assert url.hostname == "cairn.test", "fixture must not send external requests"
        path = url.path + ("?" + url.query if url.query else "")
        self.calls.append((request.method, url.path, json.loads(request.body) if request.body else None))
        response = self.core.request(request.method, path, content=request.body, headers=dict(request.headers))
        if request.method == "GET" and self.on_read:
            self.on_read()
        if request.method == "POST" and self.drop_path == url.path:
            self.drop_path = None
            raise requests.ConnectionError("synthetic response loss after native commit")
        result = requests.Response()
        result.status_code = response.status_code
        result._content = response.content
        result.headers.update(response.headers)
        result.url = request.url
        result.request = request
        return result

    def close(self):
        pass


@pytest.fixture
def environment(tmp_path, monkeypatch):
    # Native lifespan calls configure(DEFAULT_DB). Never touch ~/.local/share/cairn.
    monkeypatch.setattr(db, "_db_path", None)
    monkeypatch.setattr(db, "DEFAULT_DB", tmp_path / "native.sqlite")
    engine = create_engine(f"sqlite:///{tmp_path / 'wuji-journal.sqlite'}")
    metadata.create_all(engine)  # Test setup only; constructors do not create tables.
    key = TaskKey(uuid4(), uuid4(), uuid4())
    resources = ContainerResources("100m", "128Mi", "1", "512Mi")
    runtime = TaskRuntimeConfig(key.tenant_id, key.task_id, "fixture", 1, 2, "a" * 64, "b" * 64,
                                "example.invalid/agent@sha256:" + "c" * 64,
                                "example.invalid/kali@sha256:" + "d" * 64,
                                resources, resources, "128Mi", 600)
    permit = ExecutionPermit(key.tenant_id, key.task_id, 1, 2, "a" * 64, "b" * 64, uuid4(), NOW + timedelta(minutes=1))
    context = DispatchContext(key, runtime, permit, RuntimeObservation("ready", runtime.pod_name, "fixture-uid"), "ready")

    class Controls:
        value = context

        def current(self, requested):
            return self.value if requested == key else None

    controls = Controls()
    with TestClient(app) as core:
        adapter = InProcessAdapter(core)
        native = CairnPlatformClient(uuid4(), "http://cairn.test")
        native._session().mount("http://cairn.test/", adapter)
        journal = SQLAlchemyJournal(engine)
        bridge = CairnTaskBridge(native, journal, controls, lambda: NOW)
        env = SimpleNamespace(key=key, controls=controls, native=native, journal=journal,
                              bridge=bridge, adapter=adapter, engine=engine)
        yield env
        native.close()
    engine.dispose()


def create(env):
    task = ExplorationInput(env.key, " Fixture task ", "Known fixture input", "Confirm fixture output", False)
    return task, env.bridge.ensure_project(task)


def running(env):
    env.controls.value = replace(env.controls.value, control_state="running", execution_ready=True)


def result_for(env, project_id):
    agent_run = uuid4()
    running(env)
    env.controls.value = replace(env.controls.value, active_agent_run_ids=frozenset({agent_run}))
    intent = env.native.create_intent(project_id, ["origin"], "Inspect fixture", str(agent_run)).data
    assert env.native.heartbeat(project_id, intent["id"], str(agent_run)).ok
    return AgentResult(env.key, uuid4(), agent_run, intent["id"], "Fixture result recorded", 1, 2, "a" * 64, "b" * 64)


def count_posts(env, path):
    return sum(method == "POST" and target == path for method, target, _ in env.adapter.calls)


def test_native_creation_replay_and_dispatch_admission(environment):
    env = environment
    task, bound = create(env)
    assert bound.state == "bound"
    assert env.bridge.get_project(env.key).project.status == "active"
    assert env.bridge.ensure_project(task).project_id == bound.project_id
    assert count_posts(env, "/projects") == 1
    payload = next(payload for method, path, payload in env.adapter.calls if method == "POST" and path == "/projects")
    assert set(payload) == {"title", "origin", "goal", "bootstrap_enabled"}
    assert payload["title"] == "Fixture task"
    assert env.bridge.eligible_projects() == []
    running(env)
    assert [p.id for p in env.bridge.eligible_projects()] == [bound.project_id]
    env.adapter.on_read = lambda: setattr(env.controls, "value", replace(env.controls.value, control_state="cancelled"))
    with pytest.raises(DispatchDenied):
        env.bridge.authorize_dispatch(env.key)
    assert env.bridge.eligible_projects() == []


def test_lost_create_response_does_not_create_another_project(environment):
    env = environment
    env.adapter.drop_path = "/projects"
    task, record = create(env)
    assert record.state == "unknown"
    restarted = CairnTaskBridge(env.native, SQLAlchemyJournal(env.engine), env.controls, lambda: NOW)
    assert restarted.ensure_project(task).state == "unknown"
    assert count_posts(env, "/projects") == 1
    assert len(env.native.list_projects()) == 1
    with pytest.raises(BindingConflict):
        restarted.ensure_project(replace(task, goal="different input"))


def test_native_conclusion_replay_and_lost_response_reconciliation(environment):
    env = environment
    _, bound = create(env)
    first = result_for(env, bound.project_id)
    applied = env.bridge.submit_result(first)
    assert applied.state == "applied"
    assert env.bridge.submit_result(first).fact_id == applied.fact_id
    path = f"/projects/{bound.project_id}/intents/{first.intent_id}/conclude"
    assert count_posts(env, path) == 1

    second = result_for(env, bound.project_id)
    path = f"/projects/{bound.project_id}/intents/{second.intent_id}/conclude"
    env.adapter.drop_path = path
    assert env.bridge.submit_result(second).state == "unknown"
    recovered = CairnTaskBridge(env.native, SQLAlchemyJournal(env.engine), env.controls, lambda: NOW)
    result = recovered.reconcile_result(env.key, second.operation_id)
    assert result.state == "applied"
    assert recovered.submit_result(second).fact_id == result.fact_id
    assert count_posts(env, path) == 1
    assert len(recovered.get_project(env.key).facts) == 4  # origin, goal, two actual results


def test_cancelled_or_unregistered_agent_result_does_not_write_core(environment):
    env = environment
    _, bound = create(env)
    result = result_for(env, bound.project_id)
    env.controls.value = replace(env.controls.value, control_state="cancelled")
    assert env.bridge.submit_result(result).state == "rejected"
    assert env.journal.get_result(env.key, result.operation_id).result == result
    assert count_posts(env, f"/projects/{bound.project_id}/intents/{result.intent_id}/conclude") == 0

    running(env)
    env.controls.value = replace(env.controls.value, active_agent_run_ids=frozenset())
    another = replace(result, operation_id=uuid4())
    assert env.bridge.submit_result(another).state == "rejected"


def test_late_rejection_preserves_inflight_result(environment, monkeypatch):
    env = environment
    _, bound = create(env)
    result = result_for(env, bound.project_id)

    def other_request_claims_before_revocation(key):
        # Both callers saw pending; the admitted caller claims while this one
        # is waiting for admission. Its already-started write must remain tracked.
        assert env.journal.claim_result(key, result.operation_id)
        env.controls.value = replace(env.controls.value, control_state="cancelled")
        raise DispatchDenied("revoked while the other request was in flight")

    monkeypatch.setattr(env.bridge, "authorize_dispatch", other_request_claims_before_revocation)
    assert env.bridge.submit_result(result).state == "sent"
    path = f"/projects/{bound.project_id}/intents/{result.intent_id}/conclude"
    assert count_posts(env, path) == 0

    # Complete the admitted caller's native write, then recover from the graph.
    response = env.native.conclude(bound.project_id, result.intent_id, str(result.agent_run_id), result.description)
    assert response.ok
    recovered = env.bridge.reconcile_result(env.key, result.operation_id)
    assert recovered.state == "applied"
    assert env.bridge.submit_result(result).fact_id == recovered.fact_id
    assert count_posts(env, path) == 1
