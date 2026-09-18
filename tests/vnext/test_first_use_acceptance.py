"""A8 driver regression tests. Controlled HTTP peers are NOT product E2E."""
import argparse
import base64
from contextlib import contextmanager
import copy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import socket
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("first_use_driver", ROOT / "scripts/vnext/first_use_acceptance.py")
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
SHA = "b" * 40


@contextmanager
def bff_peer(*, cancel_state="closed", start_state="running", fault=None):
    """Transport oracle only. Does not stand in for BFF/TaskService acceptance."""
    requests = []
    state = {"task_id": "fresh-task", "version": "1", "observed_state": "ready", "desired_state": "pause"}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.handle_request()
        def do_POST(self):
            self.handle_request()
        def handle_request(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            body = json.loads(raw) if raw else None
            requests.append({"method": self.command, "path": self.path, "body": body,
                             "raw_body": raw.decode(),
                             "cookie": self.headers.get("Cookie"), "origin": self.headers.get("Origin"),
                             "authorization": self.headers.get("Authorization")})
            if self.command == "POST" and self.headers.get("Origin") != origin:
                return self.reply(403, {"error": "origin"})
            if self.path == "/model":
                if body["messages"][-1]["role"] == "tool":
                    return self.reply(200, {"choices": [{"message": {"role": "assistant", "content": "received"}}]})
                return self.reply(200, {"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "native-1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]}}]})
            if self.path == "/auth/login":
                if self.headers.get("x-wuji-local-bootstrap") != "synthetic-bootstrap-only":
                    return self.reply(401, {"error": "bootstrap"})
                return self.reply(200, {"authenticated": True}, cookie=True)
            if self.headers.get("Cookie") != "wuji_vnext_session=synthetic-test-session":
                return self.reply(401, {"error": "cookie"})
            if self.path == "/auth/session":
                return self.reply(200, {"authenticated": True, "mode": "local_single_operator"})
            if self.path == "/api/v2/tasks" and self.command == "POST":
                if fault == "lost_create":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                if fault == "http_create":
                    return self.reply(502, {"code": "OPERATION_UNKNOWN"})
                if fault == "redirect_create":
                    return self.reply(307, {}, location=origin + "/should-not-follow")
                return self.reply(201, state)
            if self.path.endswith("/commands"):
                command = body["command"]
                state["version"] = str(int(state["version"]) + 1)
                state["desired_state"] = {"start": "run", "pause": "pause", "cancel": "cancel"}[command]
                state["observed_state"] = {"start": start_state, "pause": "paused", "cancel": cancel_state}[command]
                return self.reply(202, {"command_id": "command-" + command, "resource_version": state["version"]})
            if self.path.endswith("/readiness"):
                return self.reply(200, {"task_id": state["task_id"], "can_request_start": True})
            if self.path.endswith("/launch"):
                return self.reply(200, {"task_id": state["task_id"], "phase": "unknown"})
            return self.reply(200, state)
        def reply(self, status, value, *, cookie=False, location=None):
            raw = json.dumps(value).encode()
            self.send_response(status)
            if cookie:
                self.send_header("Set-Cookie", "wuji_vnext_session=synthetic-test-session; HttpOnly; Path=/; SameSite=Strict")
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(raw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield origin, requests, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def arguments(tmp_path, origin, action):
    payload = tmp_path / "create.json"
    driver.write_object(payload, {"name": "no marker or answer in Goal"})
    return argparse.Namespace(base_url=origin, action=action, create_payload=payload,
                              state=tmp_path / "state.json", output=tmp_path / f"{action}.json",
                              session_file=tmp_path / "session-private.json", bootstrap_env="A8_SYNTHETIC_BOOTSTRAP",
                              candidate_sha=SHA, timeout=1, poll_count=2, poll_interval=0)


@pytest.fixture(autouse=True)
def local_credential(monkeypatch):
    monkeypatch.setenv("A8_SYNTHETIC_BOOTSTRAP", "synthetic-bootstrap-only")


def test_cookie_origin_and_explicit_create_start_pause_cancel(tmp_path):
    with bff_peer() as (origin, requests, state):
        for action in ("create", "start", "read", "pause", "cancel"):
            args = arguments(tmp_path, origin, action)
            assert driver.control(args) == 0
            journal = driver.read_object(args.output)
            assert journal["scope"] == "http_control_only"
            assert journal["e2e_status"] == "not_run"
            assert journal["process_stop"] == "not_verified"
            if action == "start":
                assert [r["body"]["command"] for r in requests if r["path"].endswith("/commands")] == ["start"]
        assert state["observed_state"] == "closed"
        assert all(r["authorization"] is None for r in requests)
        assert all(r["origin"] == origin for r in requests if r["method"] == "POST")
        public = (tmp_path / "cancel.json").read_text()
        assert "synthetic-test-session" not in public
        assert "synthetic-bootstrap-only" not in public
        assert len([r for r in requests if r["path"] == "/auth/login"]) == 1
        assert "[REDACTED]" in public


@pytest.mark.parametrize("observed", ["paused", "reconciling", "quiescing", "running"])
def test_cancel_acceptance_is_not_stopped(tmp_path, observed):
    with bff_peer(cancel_state=observed) as (origin, requests, _):
        assert driver.control(arguments(tmp_path, origin, "create")) == 0
        args = arguments(tmp_path, origin, "cancel")
        assert driver.control(args) == 2
        journal = driver.read_object(args.output)
        assert journal["status"] == "blocked"
        assert journal["last_task"]["observed_state"] == observed
        assert journal["process_stop"] == "not_verified"
        assert len([r for r in requests if r["path"].endswith("/commands")]) == 1


def test_desired_state_never_satisfies_observed_wait():
    class Client:
        journal = {}
        def persist(self):
            pass
        def request(self, *args):
            return {"task_id": "task-a", "desired_state": "running", "observed_state": "reconciling"}
    with pytest.raises(driver.DriverBlocked):
        driver._poll_task(Client(), "task-a", target={"running"}, count=1)


@pytest.mark.parametrize("fault,code,outcome", [
    ("lost_create", 2, "transport_unknown"), ("http_create", 1, "http_response"),
    ("redirect_create", 1, "http_response"),
])
def test_failure_keeps_http_ledger_and_original_pending_key(tmp_path, fault, code, outcome):
    with bff_peer(fault=fault) as (origin, requests, _):
        args = arguments(tmp_path, origin, "create")
        assert driver.control(args) == code
        journal = driver.read_object(args.output)
        assert len(journal["exchanges"]) == 3
        assert journal["exchanges"][-1]["outcome"] == outcome
        state = driver.read_object(args.state)
        key = state["operations"]["create"]["key"]
        assert state["operations"]["create"]["status"] == "pending"
        assert not any(r["path"] == "/should-not-follow" for r in requests)
        args.output = tmp_path / "again.json"
        assert driver.control(args) == 2
        assert driver.read_object(args.state)["operations"]["create"]["key"] == key
        assert len([r for r in requests if r["path"] == "/api/v2/tasks"]) == 1


@pytest.mark.parametrize("url", ["https://example.invalid", "http://localhost/path", "http://u:p@localhost", "http://localhost/?token=x"])
def test_origin_cannot_redirect_or_contain_credentials(url):
    with pytest.raises(driver.DriverBlocked):
        driver.local_origin(url)


def test_capture_checker_requires_real_shape_and_is_total_on_bad_refs():
    for value in ({}, {"task_id": "task-a", "candidate_sha": SHA, "artifact_ref": None},
                  {"task_id": "task-a", "candidate_sha": SHA, "artifact_ref": []}):
        assert not driver.validate_read_chain(value, expected_task_id="task-a", expected_candidate_sha=SHA)["valid"]


@pytest.fixture
def captured_chain():
    # Raw requests/responses really cross a local HTTP socket. This tests the
    # verifier's parser/joins, not MAF/Gate or autonomous model capability.
    from tests.first_use.f1_f2_fixture import FixtureServer
    import httpx
    with FixtureServer() as target, bff_peer() as (origin, peer_requests, _):
        with httpx.Client(trust_env=False) as client:
            source = client.get(target.base_url + "/f1/entry").content
            marker = json.loads(source)["marker"]
            ref = {"id": "source-a", "version": "2", "sha256": sha256(source).hexdigest()}
            text = source.decode()
            material = {"schema_version": "wuji.model-material.v2", "tool_call_id": "tool-a", "status": "delivered",
                        "source": {"artifact_ref": ref, "artifact_sha256": ref["sha256"]},
                        "representation": {"encoding": "utf-8", "text": text, "byte_length": len(source),
                                           "representation_sha256": sha256(source).hexdigest()}}
            receipt = {"tool_call_id": "tool-a", "status": "complete", "result_ref": ref}
            captures = []
            requests = [{"messages": [{"role": "user", "content": "Read the approved entry"}]},
                        {"messages": [{"role": "tool", "tool_call_id": "native-1", "content": json.dumps({**receipt, "material": material}, ensure_ascii=False)}]}]
            for index, request in enumerate(requests):
                response = client.post(origin + "/model", headers={"Origin": origin}, json=request)
                captures.append({"task_id": "task-a", "run_id": "run-a", "model_attempt_id": f"m-{index}",
                                 "request": {"method": "POST", "url": origin + "/model", "body": peer_requests[-1]["raw_body"]},
                                 "response": {"status": response.status_code, "body": response.text}})
            return {"candidate_sha": SHA, "task_id": "task-a", "run_id": "run-a", "tool_call_id": "tool-a",
                    "native_tool_call_id": "native-1", "marker": marker, "artifact_ref": ref,
                    "source_bytes_base64": base64.b64encode(source).decode(),
                    "read_set": [{"entity_type": "artifact", "id": "source-a", "revision": "2"}],
                    "tool_receipt": receipt, "material": material, "model_captures": captures}


def verify(value):
    return driver.validate_read_chain(value, expected_task_id="task-a", expected_candidate_sha=SHA)


def test_two_raw_captures_verify_bytes_and_content(captured_chain):
    assert verify(captured_chain)["valid"]


def test_streamed_native_call_id_is_joined_from_actual_delta_shape(captured_chain):
    chunks = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": fragment}]}}]})
              for fragment in ("native-", "1")]
    captured_chain["model_captures"][0]["response"]["body"] = "\n\n".join(chunks + ["data: [DONE]"])
    assert verify(captured_chain)["valid"]


@pytest.mark.parametrize("fault", ["source", "text", "length", "hash", "version", "substring", "task", "capture_task", "capture_text", "preloaded"])
def test_capture_tampering_fails(captured_chain, fault):
    value = copy.deepcopy(captured_chain)
    if fault == "source":
        value["source_bytes_base64"] = base64.b64encode(b"wrong").decode()
    elif fault == "text":
        value["material"]["representation"]["text"] += "forged"
    elif fault == "length":
        value["material"]["representation"]["byte_length"] += 1
    elif fault == "hash":
        value["material"]["representation"]["representation_sha256"] = "a" * 64
    elif fault == "version":
        value["read_set"][0]["revision"] = "20"
    elif fault == "substring":
        value["read_set"] = [{"hint": "source-a at revision 2"}]
    elif fault == "task":
        value["task_id"] = "other-task"
    elif fault == "capture_task":
        value["model_captures"][1]["task_id"] = "other-task"
    elif fault == "capture_text":
        value["model_captures"][1]["request"]["body"] = '{"messages":[]}'
    else:
        value["model_captures"][0]["request"]["body"] = json.dumps({"messages": [{"role": "user", "content": value["marker"]}]})
    assert not verify(value)["valid"]


@pytest.mark.parametrize("scenario", ["environment_after_started", "environment_empty", "exited_empty", "environment_unknown_tool"])
def test_a1_frozen_environment_settlement_boundaries(tmp_path, scenario):
    """Real isolated PG, frozen A1 ControlService; no real child/Pod evidence."""
    from tests.first_use.review_material import frozen_module
    from support.postgres import isolated_database_environment
    from test_work_state_guards import control_case, prepared_run, observe, process, OPERATOR, TASK, OWNER
    frozen = frozen_module("8b84081dbaf124d3aa3eae009e732dedf16bf1e6",
                           "packages/wuji-core/src/wuji_core/execution/control.py", "a8_a1_control")
    manifest = Path(os.environ.get("WUJI_A8_PG_MANIFEST", ROOT / "work/vnext/postgres-fixture.json"))
    with isolated_database_environment(manifest_path=manifest, audit_path=tmp_path / "pg.jsonl") as env:
        with control_case(env, tmp_path, tmp_path) as case:
            case.control = frozen.ControlService(case.uow, artifacts=case.store, sessions=case.sessions)
            case.control_module = frozen
            # P03's reusable seed has a started legacy ToolAttempt and an
            # unknown output expectation. Make these *input prerequisites*
            # explicit before the control action; never change its result.
            with env.migration_connection() as connection:
                connection.execute("UPDATE vnext.agent_run SET output_expectation='final_output' WHERE tenant_id=%s AND project_id=%s AND task_id=%s", OWNER)
                connection.execute("UPDATE vnext.tool_attempt SET started_at=NULL WHERE tenant_id=%s AND project_id=%s AND task_id=%s", OWNER)
            prepared_run(case)
            if scenario in {"environment_after_started", "exited_empty", "environment_unknown_tool"}:
                observe(case, "started", process=process())
            if scenario == "environment_unknown_tool":
                with env.migration_connection() as connection:
                    connection.execute("UPDATE vnext.tool_attempt SET status='unknown' WHERE tenant_id=%s AND project_id=%s AND task_id=%s", OWNER)
            if scenario == "exited_empty":
                observe(case, "exited", process=process(exited=True))
            else:
                observe(case, "environment_stopped")
            work = case.control.read_work(OPERATOR, TASK, "work-fixture")
            with case.uow.transaction(OPERATOR, TASK) as tx:
                settlements = tx.connection.execute("SELECT status FROM vnext.run_operation_settlement WHERE tenant_id=%s AND project_id=%s AND task_id=%s", OWNER).fetchall()
            evidence_root = os.environ.get("WUJI_A8_REVIEW_EVIDENCE")
            if evidence_root:
                driver.write_object(Path(evidence_root) / (scenario + ".json"), {
                    "reviewed_sha": "8b84081dbaf124d3aa3eae009e732dedf16bf1e6", "method": "real_isolated_pg_seeded_process_metadata",
                    "scenario": scenario, "work": {key: work[key] for key in ("state", "blocked_reason", "terminal_reason", "result_state")},
                    "operation_settlements": settlements})
            if scenario in {"environment_after_started", "environment_unknown_tool"}:
                assert work["state"] == "reconciling"
                assert work["blocked_reason"] == "operations_unsettled"
                assert settlements == []
            elif scenario == "environment_empty":
                assert work["state"] == "failed"
                assert work["terminal_reason"] == "environment_stopped_before_observation"
                assert settlements == []
            else:
                assert settlements == [("settled",)]
                assert work["state"] == "failed"  # exit without result is incomplete, not success
