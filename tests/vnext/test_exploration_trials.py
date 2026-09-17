"""E06: the closed trial suite keeps its answer away from the run."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]


def _load_trials():
    path = ROOT / "scripts/vnext/exploration_trials.py"
    spec = importlib.util.spec_from_file_location("wuji_exploration_trials", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wuji_exploration_trials"] = module
    spec.loader.exec_module(module)
    return module


def test_fixtures_and_preflight_keep_every_answer_outside_the_run(tmp_path):
    trials = _load_trials()
    suite = tmp_path / "suite"
    written = trials.build_fixtures(suite)
    assert sorted(written) == sorted(trials.CASE_ORDER)
    assert (suite / "grader" / "A-reference.json").is_file()

    report = trials.preflight_suite(suite)
    assert report["blocked"] == [], report["cases"]
    assert report["same_goal_for_variants"] == {"CASE-B": True}
    for case in report["cases"]:
        assert {check["state"] for check in case["checks"]} == {"ok"}, case

    entry = (suite / "A-reference/materials/entry.json").read_text()
    assert "4.2.0" not in entry and "registry-oct.json" in entry
    assert "4.2.0" not in (suite / "A-reference/goal.txt").read_text()


def test_a_tampered_material_is_refused_before_a_run(tmp_path):
    trials = _load_trials()
    suite = tmp_path / "suite"
    trials.build_fixtures(suite)
    (suite / "B-conflict/materials/record-b.json").write_text(
        '{"service": "inventory", "version": "4.4.0"}\n'
    )

    report = trials.preflight_case("B-conflict", suite)
    assert "material:materials/record-b.json" in report["blocked"]


def test_case_run_config_publishes_only_this_case_materials(tmp_path):
    trials = _load_trials()
    suite = tmp_path / "suite"
    trials.build_fixtures(suite)
    deployment = {
        "owner": ["tenant", "project", "template-task"],
        "tool": {"ref": "workspace-read-v1"},
    }
    config = trials.case_run_config(
        suite=suite, name="B-conflict", deployment=deployment, task_id="task-1"
    )
    assert {item["path"] for item in config["materials"]} == {
        "materials/record-a.json",
        "materials/record-b.json",
    }
    assert config["trial"]["case"] == "B-conflict"
    # The deployment document is not mutated by building a case config.
    assert "materials" not in deployment
    assert config["tool"] == deployment["tool"]


def test_variant_labels_and_decoy_answers_stay_out_of_the_materials(tmp_path):
    trials = _load_trials()
    suite = tmp_path / "suite"
    trials.build_fixtures(suite)
    for name in trials.CASE_ORDER:
        grader = json.loads((suite / "grader" / f"{name}.json").read_text())
        expected = grader["expected"]
        answer_files = set(expected.get("answer_files") or ())
        for path in sorted((suite / name / "materials").glob("*.json")):
            relative = path.relative_to(suite / name).as_posix()
            text = path.read_text()
            assert name not in text, path
            if relative in answer_files:
                continue
            # A file that is not the material under study never carries the
            # expected answer or its decoy values.
            assert expected["answer"] not in text, path
            for version in expected.get("versions") or []:
                if version == expected.get("answer"):
                    continue
                assert version not in text, path
