"""P01 boundary tests: installed SDK + real loopback HTTP + cold processes."""
import functools
import hashlib
import inspect
import json
import os
from importlib.metadata import distribution, distributions
from pathlib import Path
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vnext"))
import probe_maf as probe


@functools.lru_cache(maxsize=1)
def results():
    out = Path(os.environ.get("P01_EVIDENCE_DIR", tempfile.mkdtemp(prefix="p01-")))
    return probe.run_probe(out)


def test_factory_is_from_installed_distribution():
    from agent_framework import create_harness_agent
    dist = distribution("agent-framework-core")
    assert dist.version == "1.18.0"
    assert "client" in inspect.signature(create_harness_agent).parameters
    assert Path(inspect.getfile(create_harness_agent)).resolve() in {
        Path(dist.locate_file(f)).resolve() for f in dist.files
    }


def test_released_wheel_and_installed_files_match_lock():
    record = probe.distribution_record()
    assert record["lock_sha256"] == hashlib.sha256((ROOT / "packages/maf-worker/uv.lock").read_bytes()).hexdigest()
    for name in ("agent-framework-core", "agent-framework-openai"):
        item = record["maf"][name]
        assert item["verified_file_count"] > 10
        assert item["wheel_sha256"] == probe.WHEELS[name]["sha256"]
        assert len(item["installed_manifest_sha256"]) == 64


def test_other_released_wheel_fails_pinned_digest_check():
    # Use a real different core release, not a fabricated hash/string mutation.
    paths = probe.prepare_wheels()
    with pytest.raises(ValueError, match="wheel SHA-256 mismatch"):
        probe.verify_wheel(paths["control"], probe.WHEELS["agent-framework-core"]["sha256"])


def test_isolated_runtime_has_no_legacy_kernel():
    names = {d.metadata["Name"].lower() for d in distributions()}
    assert {"wuji-core", "wuji-maf-worker", "agent-framework-core"} <= names
    assert not any(probe.legacy_name(name) for name in names)
    lock = probe.distribution_record()["locked_packages"]
    assert lock
    assert not any(probe.legacy_name(p["name"]) for p in lock)
    assert not any("git" in p["source"] for p in lock)
    assert not probe.legacy_name("agent-framework-core")
    with pytest.raises(ValueError, match="legacy runtime"):
        probe.verify_runtime_inventory(names, [["node", "pi", "--print"]])
    for case in results()["cases"].values():
        for process in case["processes"]:
            assert not any(probe.legacy_name(m) for m in process["result"]["loaded_modules"])


def test_real_harness_tool_roundtrip():
    case = results()["cases"]["roundtrip"]
    probe.verify_roundtrip(case)
    assert len(case["events"]) == 1
    event = case["events"][0]
    assert event["record"] == {"id": "synthetic-001", "value": "offline-p01-record"}
    assert event["fixture_sha256"] == hashlib.sha256(case["fixture_text"].encode()).hexdigest()
    requests = case["http"]
    assert len(requests) == 2
    assert json.loads(requests[1]["request_body"])["messages"][-1] == {
        "role": "tool", "tool_call_id": "call-p01-read", "content": case["fixture_text"]
    }


def test_session_restores_history_in_fresh_process():
    case = results()["cases"]["roundtrip"]
    first, restored = [p["result"] for p in case["processes"]]
    assert first["pid"] != restored["pid"]
    assert restored["session_before"] == first["session_after"]
    assert restored["session_after"]["session_id"] == first["session_after"]["session_id"]
    assert len(case["restore_http"]) == 1
    messages = json.loads(case["restore_http"][0]["request_body"])["messages"]
    assert any(m.get("tool_call_id") == "call-p01-read" for m in messages)
    assert any(m.get("content") == "offline-p01-record received" for m in messages)
    assert len(case["events"]) == 1


@pytest.mark.parametrize("decision,count", [("approve", 1), ("reject", 0)])
def test_native_approval_restores_original_call_across_processes(decision, count):
    case = results()["cases"][decision]
    pending, resumed = [p["result"] for p in case["processes"]]
    assert case["events_before_resume"] == []
    assert pending["pid"] != resumed["pid"]
    assert resumed["session_before"] == pending["session_after"]
    assert resumed["approval_response"]["id"] == pending["approval_request"]["id"]
    assert pending["approval_request"]["id"] == pending["approval_request"]["function_call"]["id"]
    assert resumed["approval_response"]["function_call"]["call_id"] == "call-p01-read"
    assert resumed["approval_response"]["function_call"] == pending["approval_request"]["function_call"]
    assert resumed["approval_response"]["approved"] is (decision == "approve")
    assert len(case["events"]) == count
    messages = json.loads(case["restore_http"][0]["request_body"])["messages"]
    tool_results = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_results) == 1 and tool_results[0]["tool_call_id"] == "call-p01-read"
    if decision == "approve":
        assert tool_results[0]["content"] == case["fixture_text"]
    else:
        assert "reject" in tool_results[0]["content"].lower()


def test_explicit_nonempty_tool_advertisements_and_unknown_call():
    for name, case in results()["cases"].items():
        for exchange in case["http"] + case["restore_http"]:
            definitions = json.loads(exchange["request_body"])["tools"]
            assert definitions and len(definitions) == 1
            assert definitions[0]["type"] == "function"
            assert definitions[0]["function"]["name"] == "read_record"
            assert definitions[0]["function"]["parameters"]["required"] == ["record_id"]
    unknown = results()["cases"]["unknown"]
    assert unknown["events"] == []
    assert len(unknown["http"]) == 1
    error = unknown["processes"][0]["result"]["error"]
    assert "unregistered_probe_tool" in error["message"]


def test_http_failure_has_no_hidden_retry_or_tool_execution():
    case = results()["cases"]["http-error"]
    assert len(case["http"]) == 1
    assert case["http"][0]["response_status"] == 503
    assert case["events"] == []
    assert "503" in case["processes"][0]["result"]["error"]["message"]


def test_nonexecuting_stub_cannot_pass_call_count():
    with pytest.raises(AssertionError, match="actual read_record execution count"):
        probe.verify_roundtrip(results()["cases"]["stub"])


def test_cli_gate_blocks_incomplete_native_approval_evidence():
    import copy
    record = copy.deepcopy(results())
    record["cases"]["approve"]["processes"][0]["result"].pop("approval_request")
    assert probe.capability_outcomes(record)["approval_boundary"]["status"] == "blocked"


def test_cli_gate_requires_observed_nonempty_tool_table():
    import copy
    record = copy.deepcopy(results())
    exchange = record["cases"]["roundtrip"]["http"][0]
    payload = json.loads(exchange["request_body"])
    payload["tools"] = []
    exchange["request_body"] = json.dumps(payload)
    assert probe.capability_outcomes(record)["tool_profile"]["status"] == "blocked"
