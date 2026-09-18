"""Offline P17 result-contract checks.

These tests exercise only the acceptance report merger.  They do not run a
product workflow or contact a model, target, cluster, or Kubernetes API.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _module():
    path = ROOT / "scripts/vnext/run_acceptance.py"
    spec = importlib.util.spec_from_file_location("wuji_run_acceptance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(*, case_id="AC-1", status="pass"):
    return {
        "case_id": case_id,
        "status": status,
        "command": "offline-contract-fixture",
        "exit_code": 0,
        "evidence_refs": ["offline-fixture"],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [("command", ""), ("exit_code", 1), ("evidence_refs", [])],
)
def test_recorded_pass_requires_command_zero_and_evidence(field, value):
    module = _module()
    result = _record()
    result[field] = value

    with pytest.raises(ValueError, match="lacks"):
        module.build_report([{"id": "AC-1"}], [result])


def test_complete_recorded_pass_is_accepted_by_the_contract_only():
    module = _module()
    report = module.build_report([{"id": "AC-1"}], [_record()])

    assert report["overall_status"] == "pass"
    assert report["counts"]["pass"] == 1
    assert report["results"][0]["evidence_refs"] == ["offline-fixture"]


def test_unknown_case_is_rejected():
    module = _module()

    with pytest.raises(ValueError, match="not in the catalog"):
        module.build_report([{"id": "AC-1"}], [_record(case_id="AC-unknown")])


def test_duplicate_recorded_case_is_rejected():
    module = _module()

    with pytest.raises(ValueError, match="duplicate recorded result"):
        module.build_report([{"id": "AC-1"}], [_record(), _record()])


def test_duplicate_catalog_case_is_rejected():
    module = _module()

    with pytest.raises(ValueError, match="duplicate catalog case"):
        module.build_report([{"id": "AC-1"}, {"id": "AC-1"}], [])


@pytest.mark.parametrize(
    ("recorded", "message"),
    [
        ({"status": "pass"}, "requires case_id"),
        ({"case_id": "AC-1"}, "invalid status"),
    ],
)
def test_recorded_result_missing_required_field_is_rejected(recorded, message):
    module = _module()

    with pytest.raises(ValueError, match=message):
        module.build_report([{"id": "AC-1"}], [recorded])
