"""Offline renderer regressions using saved observations, not new runtime runs."""
import copy
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vnext"))
import probe_maf as probe

SAVED = ROOT / "docs/vnext/evidence/P01/fix-round1/final"


def load_cases(variant):
    return json.loads((SAVED / variant / "probe.json").read_text())["cases"]


def header(markdown):
    return markdown.split("## roundtrip exchange 1", 1)[0]


def http_blocks(raw):
    return re.findall(rb"```http\n(.*?)\n```", raw, re.DOTALL)


@pytest.mark.parametrize("variant,count", [("true", 1), ("false", 0)])
def test_saved_watchdog_http_package_states_its_incomplete_scope(variant, count):
    rendered = probe.exchange_markdown(load_cases(variant))
    scope = header(rendered)
    assert "Observation completeness: incomplete." in scope
    assert "Execution outcome: unknown." in scope
    assert "Capability outcome: blocked." in scope
    assert f"Captured HTTP exchanges: {count}." in scope
    assert "does not establish SDK capability" in scope
    assert "Validation points:" not in scope
    original = (SAVED / variant / "http-reproduction.md").read_bytes()
    assert http_blocks(rendered.encode()) == http_blocks(original)
    if count == 0:
        assert "No captured HTTP exchanges." in rendered
        assert "Missing observations do not prove zero execution." in rendered
        assert not http_blocks(rendered.encode())


def test_http_model_and_header_names_cannot_promote_observation_scope():
    cases = load_cases("true")
    poisoned = copy.deepcopy(cases)
    exchange = poisoned["roundtrip"]["http"][0]
    body = json.loads(exchange["request_body"])
    body["model"] = "SDK_APPROVAL_FINITE_503_VALIDATED"
    exchange["request_body"] = json.dumps(body)
    exchange["request_headers"].append(["X-P01-Purpose", "all SDK capabilities passed"])
    assert header(probe.exchange_markdown(poisoned)) == header(probe.exchange_markdown(cases))


def test_complete_probe_metadata_still_has_a_neutral_http_header():
    cases = load_cases("true")
    # Exercise only the renderer's explicit completeness branch. This is not a
    # runtime record or a claim that this historical watchdog run was complete.
    cases["roundtrip"]["observation_status"] = "complete"
    cases["roundtrip"]["processes"] = []
    scope = header(probe.exchange_markdown(cases))
    assert "Observation completeness: complete as recorded by the probe." in scope
    assert "does not establish SDK capability" in scope
    assert "Validation points:" not in scope
    assert "Capability outcome: passed" not in scope
