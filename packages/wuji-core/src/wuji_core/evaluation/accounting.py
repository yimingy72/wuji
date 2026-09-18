"""Accounting for offline evaluation records.

The gateway is the source of truth for prices.  This module only validates and
aggregates costs already recorded on a model-call receipt; it deliberately does
not contain a price table or make a provider request.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping


class AccountingError(ValueError):
    """Raised when an evaluation record cannot be accounted for safely."""


def _cost(value: object, *, field: str = "cost") -> Decimal:
    if isinstance(value, bool) or value is None:
        raise AccountingError(f"{field} must be a non-negative decimal")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AccountingError(f"{field} must be a non-negative decimal") from exc
    if not result.is_finite() or result < 0:
        raise AccountingError(f"{field} must be a non-negative finite decimal")
    return result


def _get(call: object, key: str) -> object:
    if isinstance(call, Mapping):
        return call.get(key)
    return getattr(call, key, None)


def _calls(calls: Iterable[Mapping[str, object] | object]) -> list[Mapping[str, object] | object]:
    if calls is None:  # type: ignore[comparison-overlap]
        raise AccountingError("calls must be an iterable")
    try:
        return list(calls)
    except TypeError as exc:
        raise AccountingError("calls must be an iterable") from exc


def total_cost(calls: Iterable[Mapping[str, object] | object]) -> Decimal:
    """Return the exact sum of all gateway-recorded call costs.

    Every role is included, including ``reason`` and ``summary``.  Missing,
    negative, NaN, and infinite values are rejected rather than treated as
    zero, because doing so would make an evaluation appear cheaper than it was.
    """

    total = Decimal("0")
    for call in _calls(calls):
        total += _cost(_get(call, "cost"))
    return total


def cost_by_role(calls: Iterable[Mapping[str, object] | object]) -> dict[str, Decimal]:
    """Aggregate costs by the recorded role without dropping unknown roles."""

    result: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for call in _calls(calls):
        role = _get(call, "role")
        if not isinstance(role, str) or not role.strip():
            raise AccountingError("role must be a non-empty string")
        result[role] += _cost(_get(call, "cost"))
    return dict(sorted(result.items()))


@dataclass(frozen=True)
class BudgetReport:
    budget: Decimal
    used: Decimal
    remaining: Decimal
    exceeded: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "budget": str(self.budget),
            "used": str(self.used),
            "remaining": str(self.remaining),
            "exceeded": self.exceeded,
        }


def budget_report(
    calls: Iterable[Mapping[str, object] | object], budget: object
) -> BudgetReport:
    """Compare all recorded calls with one fixed evaluation budget."""

    limit = _cost(budget, field="budget")
    used = total_cost(calls)
    return BudgetReport(
        budget=limit,
        used=used,
        remaining=max(Decimal("0"), limit - used),
        exceeded=used > limit,
    )


def evaluate_run(document: Mapping[str, object]) -> dict[str, object]:
    """Build a deterministic offline summary while preserving every trial.

    The input is an already-recorded run.  No field in this function can cause
    a model, tool, or target request.  ``results`` are counted as supplied; the
    evaluator never selects the best trial as a substitute for repeated runs.
    """

    if not isinstance(document, Mapping):
        raise AccountingError("evaluation document must be an object")
    calls = document.get("calls", [])
    if not isinstance(calls, list):
        raise AccountingError("calls must be a list")
    results = document.get("results", [])
    if not isinstance(results, list):
        raise AccountingError("results must be a list")
    budget = document.get("budget_usd")
    if budget is None:
        raise AccountingError("budget_usd is required")
    report = budget_report(calls, budget)
    statuses: defaultdict[str, int] = defaultdict(int)
    for result in results:
        if not isinstance(result, Mapping):
            raise AccountingError("each result must be an object")
        status = result.get("status")
        if not isinstance(status, str) or not status:
            raise AccountingError("each result requires a status")
        statuses[status] += 1
    return {
        "schema_version": "wuji.evaluation-summary.v1",
        "run_id": document.get("run_id"),
        "dataset_revision": document.get("dataset_revision"),
        "mode": document.get("mode"),
        "trial_count": len(results),
        "result_counts": dict(sorted(statuses.items())),
        "cost_by_role": {key: str(value) for key, value in cost_by_role(calls).items()},
        "budget": report.as_dict(),
        "results_preserved": True,
    }
