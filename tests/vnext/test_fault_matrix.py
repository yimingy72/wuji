"""Offline status-matrix checks for the P17 acceptance report merger."""

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


@pytest.mark.parametrize("status", ["fail", "not_run", "blocked"])
def test_non_pass_statuses_never_aggregate_as_pass(status):
    module = _module()
    report = module.build_report(
        [{"id": "AC-1"}],
        [
            {
                "case_id": "AC-1",
                "status": status,
                "command": "offline-contract-fixture",
                "exit_code": 0,
                "evidence_refs": ["offline-fixture"],
            }
        ],
    )

    assert report["overall_status"] == "incomplete"
    assert report["counts"][status] == 1
    assert report["results"][0]["status"] == status


def test_missing_result_defaults_to_not_run_and_keeps_gate_incomplete():
    module = _module()
    report = module.build_report([{"id": "AC-1"}], [])

    assert report["overall_status"] == "incomplete"
    assert report["counts"]["not_run"] == 1
    assert report["results"][0]["status"] == "not_run"
