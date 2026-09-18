"""Accounting for offline evaluation records.

The gateway is the source of truth for prices.  This module only validates and
aggregates costs already recorded on a model-call receipt; it deliberately does
not contain a price table or make a provider request.
"""

from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
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


_METADATA_ALIASES: dict[str, tuple[str, ...]] = {
    "dataset_revision": ("dataset_revision", "dataset_id", "dataset"),
    "model": ("model", "model_id", "model_revision"),
    "tools": ("tools", "toolset"),
    "budget_usd": ("budget_usd", "total_budget_usd"),
}
_REQUIRED_METADATA = tuple(_METADATA_ALIASES)


def _canonical(value: object, *, field: str) -> str:
    """Return a stable comparison key for JSON metadata."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise AccountingError(f"{field} must contain JSON-compatible metadata") from exc


def _metadata_from(source: Mapping[str, object], *, field: str) -> dict[str, object]:
    """Read direct or nested metadata without silently accepting conflicts."""

    nested = source.get("metadata")
    if nested is None:
        nested_source: Mapping[str, object] = {}
    elif isinstance(nested, Mapping):
        nested_source = nested
    else:
        raise AccountingError(f"{field}.metadata must be an object")

    result: dict[str, object] = {}
    for canonical_name, aliases in _METADATA_ALIASES.items():
        candidates: list[object] = []
        for candidate_source in (nested_source, source):
            for alias in aliases:
                if alias in candidate_source:
                    candidates.append(candidate_source[alias])
        if not candidates:
            continue
        first = candidates[0]
        if any(
            _canonical(first, field=f"{field}.{canonical_name}")
            != _canonical(candidate, field=f"{field}.{canonical_name}")
            for candidate in candidates[1:]
        ):
            raise AccountingError(f"conflicting {field}.{canonical_name} metadata")
        result[canonical_name] = deepcopy(first)
    return result


def _normalise_metadata(metadata: Mapping[str, object], *, field: str) -> dict[str, object]:
    missing = [name for name in _REQUIRED_METADATA if name not in metadata]
    if missing:
        raise AccountingError(f"{field} is missing metadata: {', '.join(missing)}")

    dataset = metadata["dataset_revision"]
    if dataset is None or dataset == "" or dataset == [] or dataset == {}:
        raise AccountingError(f"{field}.dataset_revision must be non-empty")
    _canonical(dataset, field=f"{field}.dataset_revision")

    model = metadata["model"]
    if model is None or model == "" or model == [] or model == {}:
        raise AccountingError(f"{field}.model must be non-empty")
    _canonical(model, field=f"{field}.model")

    tools = metadata["tools"]
    if not isinstance(tools, list):
        raise AccountingError(f"{field}.tools must be a list")
    _canonical(tools, field=f"{field}.tools")

    budget = _cost(metadata["budget_usd"], field=f"{field}.budget_usd")
    return {
        "dataset_revision": dataset,
        "model": model,
        "tools": tools,
        "budget_usd": budget,
    }


def _metadata_equal(left: Mapping[str, object], right: Mapping[str, object], name: str) -> bool:
    if name == "budget_usd":
        return left[name] == right[name]
    if name == "tools":
        left_tools = sorted(_canonical(item, field="tools") for item in left[name])  # type: ignore[arg-type]
        right_tools = sorted(_canonical(item, field="tools") for item in right[name])  # type: ignore[arg-type]
        return left_tools == right_tools
    return _canonical(left[name], field=name) == _canonical(right[name], field=name)


def _metadata_for_output(metadata: Mapping[str, object]) -> dict[str, object]:
    return {
        "dataset_revision": deepcopy(metadata["dataset_revision"]),
        "model": deepcopy(metadata["model"]),
        "tools": deepcopy(metadata["tools"]),
        "budget_usd": str(metadata["budget_usd"]),
    }


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


def _validated_results(results: object) -> list[Mapping[str, object]]:
    if not isinstance(results, list):
        raise AccountingError("results must be a list")
    validated: list[Mapping[str, object]] = []
    for result in results:
        if not isinstance(result, Mapping):
            raise AccountingError("each result must be an object")
        status = result.get("status")
        if not isinstance(status, str) or not status.strip():
            raise AccountingError("each result requires a non-empty status")
        validated.append(result)
    return validated


def _run_summary(
    *,
    calls: object,
    results: object,
    budget: object,
    metadata: Mapping[str, object] | None = None,
    architecture: str | None = None,
) -> dict[str, object]:
    if not isinstance(calls, list):
        raise AccountingError("calls must be a list")
    validated_results = _validated_results(results)
    report = budget_report(calls, budget)
    statuses: defaultdict[str, int] = defaultdict(int)
    for result in validated_results:
        statuses[result["status"]] += 1  # type: ignore[index]

    summary: dict[str, object] = {
        "trial_count": len(validated_results),
        "results": deepcopy(validated_results),
        "result_counts": dict(sorted(statuses.items())),
        "cost_by_role": {key: str(value) for key, value in cost_by_role(calls).items()},
        "total_cost": str(report.used),
        "budget": report.as_dict(),
        "results_preserved": True,
    }
    if architecture is not None:
        summary["architecture"] = architecture
    if metadata is not None:
        summary["metadata"] = _metadata_for_output(metadata)
    return summary


def _architecture_runs(document: Mapping[str, object]) -> list[tuple[str, Mapping[str, object]]] | None:
    raw = document.get("architectures")
    if raw is None:
        raw = document.get("architecture_runs")
    if raw is None:
        raw = document.get("runs")
    if raw is None:
        return None

    runs: list[tuple[str, Mapping[str, object]]] = []
    if isinstance(raw, Mapping):
        for name, run in raw.items():
            if not isinstance(name, str) or not name.strip():
                raise AccountingError("architecture names must be non-empty strings")
            if not isinstance(run, Mapping):
                raise AccountingError("each architecture run must be an object")
            run_copy = dict(run)
            run_name = run_copy.get("name", run_copy.get("architecture", name))
            if run_name != name:
                raise AccountingError("architecture mapping key does not match its name")
            run_copy.setdefault("name", name)
            runs.append((name, run_copy))
    elif isinstance(raw, list):
        for run in raw:
            if not isinstance(run, Mapping):
                raise AccountingError("each architecture run must be an object")
            name = run.get("name", run.get("architecture"))
            if not isinstance(name, str) or not name.strip():
                raise AccountingError("each architecture run requires a name")
            runs.append((name, run))
    else:
        raise AccountingError("architectures must be a list or object")

    if len(runs) != 2:
        raise AccountingError("fair comparison requires exactly two architecture runs")
    names = [name for name, _ in runs]
    if len(set(names)) != len(names):
        raise AccountingError("architecture names must be unique")
    return runs


def _evaluate_comparison(document: Mapping[str, object]) -> dict[str, object]:
    runs = _architecture_runs(document)
    assert runs is not None

    shared = _metadata_from(document, field="evaluation")
    normalised_runs: list[tuple[str, Mapping[str, object], dict[str, object]]] = []
    for name, run in runs:
        run_metadata = dict(shared)
        run_metadata.update(_metadata_from(run, field=f"architecture[{name}]"))
        normalised = _normalise_metadata(run_metadata, field=f"architecture[{name}]")
        normalised_runs.append((name, run, normalised))

    baseline = normalised_runs[0][2]
    for name, _run, metadata in normalised_runs[1:]:
        for field in _REQUIRED_METADATA:
            if not _metadata_equal(baseline, metadata, field):
                raise AccountingError(
                    f"fair comparison metadata mismatch for {field}: "
                    f"architecture[{normalised_runs[0][0]}] != architecture[{name}]"
                )

    architecture_summaries: dict[str, object] = {}
    for name, run, _metadata in normalised_runs:
        if "calls" not in run or "results" not in run:
            raise AccountingError(f"architecture[{name}] requires calls and results")
        architecture_summaries[name] = _run_summary(
            calls=run["calls"],
            results=run["results"],
            budget=baseline["budget_usd"],
            metadata=baseline,
            architecture=name,
        )

    comparison: dict[str, object] = {
        "schema_version": "wuji.evaluation-summary.v2",
        "metadata_validated": True,
        "metadata": _metadata_for_output(baseline),
        "architecture_names": [name for name, _run, _metadata in normalised_runs],
        "architectures": architecture_summaries,
        "results_preserved": True,
        "trial_count": sum(
            summary["trial_count"]  # type: ignore[index]
            for summary in architecture_summaries.values()
        ),
    }
    if "run_id" in document:
        comparison["run_id"] = document["run_id"]
    if "mode" in document:
        comparison["mode"] = document["mode"]
    return comparison


def evaluate_comparison(document: Mapping[str, object]) -> dict[str, object]:
    """Summarize exactly two already-recorded, fairly comparable runs.

    Both architecture runs must use the same dataset revision, model, tool
    set, and total USD budget.  The evaluator only reads JSON-like records; it
    never starts a model, tool, or target request.
    """

    if not isinstance(document, Mapping):
        raise AccountingError("evaluation document must be an object")
    return _evaluate_comparison(document)


def evaluate_run(document: Mapping[str, object]) -> dict[str, object]:
    """Build a deterministic offline summary while preserving every trial.

    The input is an already-recorded run.  No field in this function can cause
    a model, tool, or target request.  ``results`` are counted as supplied; the
    evaluator never selects the best trial as a substitute for repeated runs.
    """

    if not isinstance(document, Mapping):
        raise AccountingError("evaluation document must be an object")
    if any(key in document for key in ("architectures", "architecture_runs", "runs")):
        return _evaluate_comparison(document)
    if "calls" not in document or "results" not in document:
        raise AccountingError("calls and results are required")
    if "budget_usd" not in document:
        raise AccountingError("budget_usd is required")

    mode = document.get("mode")
    if mode == "effectiveness_real_model":
        results = _validated_results(document["results"])
        if any(result["status"] != "not_run" for result in results):  # type: ignore[index]
            raise AccountingError("real-model effectiveness must remain not_run")

    summary = _run_summary(
        calls=document["calls"],
        results=document["results"],
        budget=document["budget_usd"],
    )
    summary.update(
        {
            "schema_version": "wuji.evaluation-summary.v1",
            "run_id": document.get("run_id"),
            "dataset_revision": document.get("dataset_revision"),
            "mode": mode,
        }
    )
    return summary
