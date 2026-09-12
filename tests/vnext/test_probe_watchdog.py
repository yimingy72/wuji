"""Only the real subprocess watchdog/reporting boundary, never SDK feasibility."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vnext"))
import probe_maf as probe


@pytest.mark.parametrize("observations", [True, False], ids=["available-observations", "unknown-observations"])
def test_outer_watchdog_publishes_blocked_cli_evidence(monkeypatch, tmp_path, capsys, observations):
    destination = Path(os.environ.get("P01_WATCHDOG_EVIDENCE_DIR", tmp_path)) / str(observations).lower()
    real_run = subprocess.run
    commands = []

    def run_harmless_child(command, **kwargs):
        # Change only executable payload/deadline at the OS boundary. The actual
        # subprocess.run raises TimeoutExpired; no completed result is fabricated.
        assert command[2] == "--worker"
        command[1] = str(ROOT / "tests/vnext/watchdog_child.py")
        config_path = Path(command[-1])
        config = json.loads(config_path.read_text())
        config["watchdog_observations"] = observations
        config_path.write_text(json.dumps(config))
        commands.append(list(command))
        kwargs["timeout"] = 0.75
        return real_run(command, **kwargs)

    def unrelated_distribution_check():
        pytest.fail("timeout reporting must not trigger unrelated SDK/distribution verification")

    monkeypatch.setattr(probe.subprocess, "run", run_harmless_child)
    monkeypatch.setattr(probe, "distribution_record", unrelated_distribution_check)
    monkeypatch.setattr(sys, "argv", ["probe_maf.py", "--output-dir", str(destination)])
    assert probe.main() == 2
    output = capsys.readouterr().out
    (destination / "cli-output.txt").write_text(output)
    assert "blocked" in output and "reads= unknown" in output
    assert len(commands) == 1  # Never retry/resume the timed-out SDK operation.
    aggregate = json.loads((destination / "probe.json").read_text())
    assert aggregate["capabilities"]["watchdog"]["status"] == "blocked"
    assert set(aggregate["cases"]) == {"roundtrip"}
    case = json.loads((destination / "roundtrip/case.json").read_text())
    assert aggregate["cases"]["roundtrip"] == case
    process = json.loads((destination / "roundtrip/initial-process.json").read_text())
    assert case["processes"] == [process]
    assert process["outcome"] == "timed_out"
    assert process["exit_code"] is None
    assert process["execution_outcome"] == "unknown"
    assert process["error"]["type"] == "TimeoutExpired"
    assert process["command"] == commands[0]
    assert process["deadline"]["timeout_seconds"] == 0.75
    assert process["deadline"]["expired_at_or_after"] >= process["deadline"]["started_at"]
    assert base64.b64decode(process["stdout_base64"]) == "watchdog stdout ✓\n".encode()
    assert base64.b64decode(process["stderr_base64"]) == "watchdog stderr ✓\n".encode()
    assert process["stdout"] == "watchdog stdout ✓\n" and process["stderr"] == "watchdog stderr ✓\n"
    assert case["events"] is None  # Missing/incomplete evidence cannot become zero execution.
    assert case["observation_status"] == "incomplete"
    assert len((destination / "roundtrip/watchdog-starts.txt").read_text().splitlines()) == 1
    assert (destination / "http-reproduction.md").is_file()
    if observations:
        assert process["result"]["source"] == "watchdog fixture, not MAF"
        assert process["result_state"] == "available_at_timeout"
        assert case["observed_event_count"] == 1 and len(case["available_events"]) == 1
        assert case["available_events"][0]["operation"] == "read_fixture"
        assert len(case["http"]) == 1
        exchange = json.loads((destination / "roundtrip/http.json").read_text())[0]
        assert exchange == case["http"][0]
        assert "watchdog reporting fixture" in exchange["request_body"]
        assert exchange["response_status"] == 200 and exchange["response_body"]
        assert "watchdog reporting fixture" in (destination / "http-reproduction.md").read_text()
    else:
        assert "HTTP observed= unknown" in output
        assert process["result"] is None and process["result_state"] == "missing_at_timeout"
        assert case["available_events"] == []
        assert case["observed_event_count"] is None
        assert case["http_observation_count"] is None


def test_reporting_does_not_overwrite_an_existing_evidence_run(tmp_path):
    (tmp_path / "roundtrip").mkdir()
    original = b'{"historical_run":"preserve exact bytes"}\n'
    (tmp_path / "probe.json").write_bytes(original)
    with pytest.raises(FileExistsError):
        probe.run_probe(tmp_path)
    assert (tmp_path / "probe.json").read_bytes() == original
