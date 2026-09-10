"""Independent, post-run checks for the bounded Phase 1C P0 probe.

This checker only reads the redacted report, the persistent attempt ledger, and
the adapter source tree.  It never imports the adapter, opens a credential
file, starts a process, or contacts a model gateway.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator


EXPECTED_TOOL = "wuji_synthetic_check"
EXPECTED_PROTOCOLS = ("openai", "anthropic")
FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "headers",
    "access_token",
    "client_secret",
    "credential_value",
    "raw_exception",
    "request_body",
    "response_body",
}


class CheckFailure(RuntimeError):
    """A report or source invariant required by the P0 acceptance failed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckFailure(f"could not read JSON evidence: {path.name}") from exc
    if not isinstance(value, dict):
        raise CheckFailure(f"JSON evidence is not an object: {path.name}")
    return value


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def _check_source(source_root: Path) -> None:
    files = {path.name: path for path in source_root.glob("*.py")}
    required = {"credentials.py", "provider.py", "harness.py", "tools.py", "ipc_model.py"}
    _require(required <= files.keys(), "adapter source tree is missing a required module")

    sources = {
        name: path.read_text(encoding="utf-8")
        for name, path in files.items()
    }
    credential_users = {
        name
        for name, source in sources.items()
        if "load_api_key" in source
    }
    _require(
        credential_users <= {"credentials.py", "provider.py"},
        "credential loader is referenced outside the Provider boundary",
    )
    _require("def load_api_key" in sources["credentials.py"], "credential loader is missing")
    _require("load_api_key(credential_path)" in sources["provider.py"], "Provider does not load by path")
    _require("api_key" not in sources["harness.py"], "Harness source mentions an upstream key")
    _require("api_key" not in sources["ipc_model.py"], "IPC model source mentions an upstream key")
    _require(sources["provider.py"].count("max_retries=0") >= 2, "native clients do not both disable retries")
    _require("wuji_synthetic_check" in sources["tools.py"], "synthetic tool is missing")
    _require("GeneralPurposeSubagentProfile" in sources["harness.py"], "Harness subagent policy is not explicit")


def _check_usage(summary: Any, location: str) -> None:
    _require(isinstance(summary, dict), f"missing call summary: {location}")
    for key in ("actual_model", "finish_reason", "usage", "tool_call_ids"):
        _require(key in summary, f"missing {location}.{key}")
    usage = summary["usage"]
    _require(isinstance(usage, dict), f"usage is not an object: {location}")
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = usage.get(key)
        _require(
            value == "unknown" or (isinstance(value, int) and not isinstance(value, bool) and value >= 0),
            f"usage must be a nonnegative integer or unknown: {location}.{key}",
        )
    _require(isinstance(summary["tool_call_ids"], list), f"tool_call_ids is not a list: {location}")


def _check_protocol(report: dict[str, Any], protocol: str, adapter: str) -> None:
    section = report.get(protocol)
    _require(isinstance(section, dict), f"missing {protocol} section")
    _require(section.get("status") == "completed", f"{protocol} did not complete")
    _require(section.get("adapter") == adapter, f"unexpected {protocol} adapter")
    _require(section.get("tool_names") == [EXPECTED_TOOL], f"unexpected {protocol} tool names")
    tool_call_id = section.get("tool_call_id")
    _require(isinstance(tool_call_id, str) and bool(tool_call_id), f"{protocol} tool call ID is missing")
    calls = section.get("calls")
    _require(isinstance(calls, list) and len(calls) == 2, f"{protocol} must contain exactly two call summaries")
    for index, summary in enumerate(calls, start=1):
        _check_usage(summary, f"{protocol}.calls[{index}]")
    first_ids = calls[0]["tool_call_ids"]
    _require(first_ids == [tool_call_id], f"{protocol} first tool-call ID does not match the result")
    _require(calls[1]["tool_call_ids"] == [], f"{protocol} second call requested another tool")


def _check_ledger(report: dict[str, Any], ledger: dict[str, Any]) -> None:
    run_id = report.get("run_id")
    _require(isinstance(run_id, str) and bool(run_id), "run_id is missing")
    all_attempts = ledger.get("attempts")
    _require(isinstance(all_attempts, list), "ledger attempts is not a list")
    _require(len(all_attempts) <= 4, "persistent ledger contains more than four attempts")
    attempts = [item for item in all_attempts if isinstance(item, dict) and item.get("run_id") == run_id]
    _require(len(attempts) == 4, "the run did not reserve exactly four attempts")
    ids = [item.get("attempt_id") for item in attempts]
    _require(all(isinstance(item, str) and item for item in ids) and len(set(ids)) == 4, "attempt IDs are invalid")
    for protocol in EXPECTED_PROTOCOLS:
        local = [item for item in attempts if item.get("protocol") == protocol]
        _require(len(local) == 2, f"{protocol} did not reserve exactly two attempts")
        _require(sorted(item.get("sequence") for item in local) == [1, 2], f"{protocol} sequence is invalid")
    for item in attempts:
        _require(item.get("status") == "completed", "an attempt is not completed")
        _require(item.get("requested_model") == "qwen-flash", "requested model is not fixed qwen-flash")
        _check_usage(item, f"ledger attempt {item.get('attempt_id', 'unknown')}")


def check(report_path: Path, ledger_path: Path, source_root: Path) -> dict[str, Any]:
    report = _load_json(report_path)
    ledger = _load_json(ledger_path)
    _check_source(source_root)
    _require(report.get("status") == "completed", "report status is not completed")
    _require(report.get("requested_model") == "qwen-flash", "report model is not fixed qwen-flash")
    _require(report.get("skipped") == [], "report contains skipped protocol work")
    _require(
        report.get("limits")
        == {"shared_attempts": 4, "attempts_per_protocol": 2, "sdk_retries": 0, "max_output_tokens": 256},
        "probe limits do not match the approved bounds",
    )
    _require(
        report.get("environment")
        == {"provider_secrets_present_in_harness": False, "external_tracing_enabled": False},
        "Harness environment evidence is not clean",
    )
    cleanup = report.get("cleanup")
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("openai_provider_process_cleaned") is True
        and cleanup.get("anthropic_provider_process_cleaned") is True,
        "Provider cleanup evidence is incomplete",
    )
    _check_protocol(report, "openai", "deepagents")
    _check_protocol(report, "anthropic", "langchain-anthropic")
    _check_ledger(report, ledger)
    forbidden = sorted(set(_walk_keys(report)) & FORBIDDEN_KEYS)
    _require(not forbidden, f"report contains forbidden secret-bearing fields: {forbidden}")
    return {"ok": True, "run_id": report["run_id"], "attempts": 4, "protocols": list(EXPECTED_PROTOCOLS)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("packages/agent-integration/src/wuji_agent_integration"),
    )
    args = parser.parse_args(argv)
    try:
        result = check(args.report, args.ledger, args.source_root)
    except CheckFailure as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
