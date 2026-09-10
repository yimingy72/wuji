"""CLI for the one approved P0 model/Harness validation run."""

from __future__ import annotations

import argparse
import json
import sys

from .isolation import scrub_harness_environment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the isolated Wuji Agent integration P0 probe")
    parser.add_argument("--credentials", help="0600 JSON file containing only api_key")
    parser.add_argument("--ledger", help="persistent JSON upstream-attempt ledger")
    parser.add_argument("--report", help="redacted JSON report output")
    parser.add_argument("--run-id", help="optional caller-owned audit run ID")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--fixture-cancel", action="store_true", help="run only the local delayed cancellation fixture")
    return parser


def main(argv: list[str] | None = None) -> int:
    scrub_harness_environment()
    args = _parser().parse_args(argv)
    try:
        if args.fixture_cancel:
            from .runner import run_cancellation_fixture

            result = run_cancellation_fixture()
        else:
            if not args.credentials or not args.ledger or not args.report:
                _parser().error("--credentials, --ledger, and --report are required for a real probe")
            from .runner import run_probe

            result = run_probe(
                credential_path=args.credentials,
                ledger_path=args.ledger,
                report_path=args.report,
                run_id=args.run_id,
                timeout_seconds=args.timeout_seconds,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as exc:
        error = {"ok": False, "error": {"stage": "probe", "code": type(exc).__name__}}
        print(json.dumps(error, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
