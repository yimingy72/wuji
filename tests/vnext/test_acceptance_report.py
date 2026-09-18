from __future__ import annotations

import importlib.util
import json
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


def test_missing_cases_are_not_run_and_cannot_become_pass():
    module = _module()
    report = module.build_report(
        [{"id": "AC-1", "title": "one", "tasks": ["P17"]}], []
    )
    assert report["overall_status"] == "incomplete"
    assert report["counts"]["not_run"] == 1
    assert report["results"][0]["status"] == "not_run"


def test_pass_requires_a_real_command_exit_code_and_evidence():
    module = _module()
    with pytest.raises(ValueError, match="lacks"):
        module.build_report(
            [{"id": "AC-1"}],
            [{"case_id": "AC-1", "status": "pass", "command": "pytest", "exit_code": 0}],
        )


def test_recorded_results_are_preserved_and_unknown_ids_rejected():
    module = _module()
    report = module.build_report(
        [{"id": "AC-1", "title": "one"}],
        [
            {
                "case_id": "AC-1",
                "status": "fail",
                "command": "pytest tests/vnext/test_end_to_end.py -q",
                "exit_code": 1,
                "evidence_refs": ["raw/result.json"],
                "note": "fixture unavailable",
            }
        ],
    )
    assert report["results"][0]["status"] == "fail"
    assert report["results"][0]["note"] == "fixture unavailable"
    with pytest.raises(ValueError, match="not in the catalog"):
        module.build_report(
            [{"id": "AC-1"}],
            [{"case_id": "AC-2", "status": "not_run"}],
        )


def test_catalog_has_all_cases_and_default_report_is_incomplete():
    module = _module()
    catalog = json.loads((ROOT / "docs/vnext/acceptance_cases.json").read_text())
    report = module.build_report(catalog, [])
    assert report["case_count"] == 75
    assert report["overall_status"] == "incomplete"
    assert report["counts"]["not_run"] == 75
