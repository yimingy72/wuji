from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from wuji_core.evaluation.accounting import (
    AccountingError,
    cost_by_role,
    evaluate_comparison,
    evaluate_run,
    total_cost,
)


def test_reason_and_summary_are_part_of_total_budget() -> None:
    calls = [
        {"cost": "0.02", "role": "reason"},
        {"cost": "0.03", "role": "explore"},
        {"cost": "0.01", "role": "summary"},
    ]
    assert total_cost(calls) == Decimal("0.06")
    assert cost_by_role(calls) == {
        "explore": Decimal("0.03"),
        "reason": Decimal("0.02"),
        "summary": Decimal("0.01"),
    }


@pytest.mark.parametrize("value", ["-0.01", "NaN", "Infinity", None, True])
def test_invalid_gateway_cost_is_not_silently_zero(value: object) -> None:
    with pytest.raises(AccountingError):
        total_cost([{"cost": value, "role": "explore"}])


def test_offline_summary_preserves_repeated_trials_and_marks_budget_overrun() -> None:
    summary = evaluate_run(
        {
            "run_id": "eval-1",
            "dataset_revision": "fixture-v1",
            "mode": "synthetic",
            "budget_usd": "0.05",
            "calls": [
                {"cost": "0.02", "role": "reason"},
                {"cost": "0.02", "role": "explore"},
                {"cost": "0.02", "role": "summary"},
            ],
            "results": [
                {"trial": 1, "status": "pass"},
                {"trial": 2, "status": "fail"},
            ],
        }
    )
    assert summary["trial_count"] == 2
    assert summary["results_preserved"] is True
    assert summary["result_counts"] == {"fail": 1, "pass": 1}
    assert summary["budget"]["used"] == "0.06"
    assert summary["budget"]["exceeded"] is True


def _fair_comparison_document() -> dict[str, object]:
    return {
        "run_id": "fair-1",
        "mode": "mechanism_synthetic",
        "dataset_revision": "fixture-v2",
        "model": {"name": "fixture-model", "revision": "v1"},
        "tools": [{"name": "read_record", "version": "v1"}],
        "budget_usd": "0.10",
        "architectures": [
            {
                "name": "single_harness",
                "calls": [
                    {"cost": "0.01", "role": "reason"},
                    {"cost": "0.02", "role": "explore"},
                    {"cost": "0.03", "role": "summary"},
                ],
                "results": [
                    {"trial": 1, "status": "fail", "failure_type": "wrong_answer"},
                    {"trial": 2, "status": "pass", "score": 1},
                ],
            },
            {
                "name": "blackboard",
                "calls": [
                    {"cost": "0.02", "role": "reason"},
                    {"cost": "0.01", "role": "explore"},
                    {"cost": "0.04", "role": "summary"},
                ],
                "results": [
                    {"trial": 1, "status": "fail", "failure_type": "timeout"},
                    {"trial": 2, "status": "pass", "score": 1},
                ],
            },
        ],
    }


def test_fair_comparison_validates_shared_metadata_and_preserves_each_trial() -> None:
    document = _fair_comparison_document()
    summary = evaluate_comparison(document)

    assert summary["metadata_validated"] is True
    assert summary["metadata"] == {
        "dataset_revision": "fixture-v2",
        "model": {"name": "fixture-model", "revision": "v1"},
        "tools": [{"name": "read_record", "version": "v1"}],
        "budget_usd": "0.10",
    }
    assert summary["architecture_names"] == ["single_harness", "blackboard"]
    architectures = summary["architectures"]
    assert architectures["single_harness"]["total_cost"] == "0.06"
    assert architectures["blackboard"]["total_cost"] == "0.07"
    assert architectures["single_harness"]["cost_by_role"] == {
        "explore": "0.02",
        "reason": "0.01",
        "summary": "0.03",
    }
    assert architectures["single_harness"]["results"] == document["architectures"][0]["results"]
    assert architectures["blackboard"]["results"] == document["architectures"][1]["results"]
    assert architectures["single_harness"]["result_counts"] == {"fail": 1, "pass": 1}
    assert architectures["blackboard"]["result_counts"] == {"fail": 1, "pass": 1}
    assert "best_trial" not in summary
    assert summary["results_preserved"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_revision", "fixture-other"),
        ("model", {"name": "other-model", "revision": "v1"}),
        ("tools", [{"name": "different_tool", "version": "v1"}]),
        ("budget_usd", "0.11"),
    ],
)
def test_fair_comparison_rejects_metadata_mismatch(field: str, value: object) -> None:
    document = _fair_comparison_document()
    document["architectures"][1][field] = value  # type: ignore[index]

    with pytest.raises(AccountingError, match=field):
        evaluate_run(document)


def test_real_effectiveness_input_stays_not_run() -> None:
    summary = evaluate_run(
        {
            "mode": "effectiveness_real_model",
            "budget_usd": "1",
            "calls": [],
            "results": [{"trial": 1, "status": "not_run"}],
        }
    )
    assert summary["result_counts"] == {"not_run": 1}


def test_cli_reads_json_and_writes_only_a_local_summary(tmp_path: Path) -> None:
    input_path = tmp_path / "run.json"
    output_path = tmp_path / "summary.json"
    input_path.write_text(
        json.dumps(
            {
                "run_id": "cli-1",
                "budget_usd": "1",
                "calls": [{"cost": "0.10", "role": "explore"}],
                "results": [{"status": "not_run"}],
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/vnext/run_evaluation.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    assert json.loads(output_path.read_text(encoding="utf-8"))["trial_count"] == 1
