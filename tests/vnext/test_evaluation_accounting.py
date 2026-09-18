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
