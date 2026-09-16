"""Deployment entry for the private Wuji runtime Host and outbox consumer."""

from __future__ import annotations

import argparse
import importlib
import json
from contextlib import ExitStack
from threading import Event, Thread

from wuji_core.execution.runtime_dispatcher import RuntimeController, RuntimeDispatcher


def run(
    dispatcher: RuntimeDispatcher,
    *,
    stop: Event,
    interval_seconds: float = 1.0,
    batch_limit: int = 16,
    pod_environment=None,
) -> None:
    if (
        not isinstance(dispatcher, RuntimeDispatcher)
        or not isinstance(stop, Event)
        or not 0 < interval_seconds <= 60
        or type(batch_limit) is not int
        or not 1 <= batch_limit <= 256
    ):
        raise ValueError("a composed runtime and bounded loop are required")
    lifecycle = ExitStack()
    try:
        if pod_environment is not None:
            lifecycle.enter_context(pod_environment)
        while not stop.is_set():
            try:
                infrastructure = None
                if pod_environment is not None:
                    try:
                        infrastructure = pod_environment.ensure()
                    except Exception as error:
                        # The environment is also the only source of new starts,
                        # so its own failure must not stop existing Runs from
                        # being queried and settled below.
                        detail = {"event": "runtime_pod_environment_error"}
                        code = getattr(error, "code", None)
                        if isinstance(code, str) and 0 < len(code) <= 64:
                            detail["code"] = code
                        else:
                            detail["error"] = type(error).__name__
                        print(json.dumps(detail, sort_keys=True), flush=True)
                if infrastructure is not None and infrastructure.state != "ready":
                    # A non-ready Task environment is a bounded operator signal,
                    # not a silent wait: without it a disabled receiver or stale
                    # epoch looks like an idle runtime.  New starts stop here;
                    # reconciliation of existing Runs continues.
                    detail = {
                        "event": "runtime_pod_environment",
                        "state": infrastructure.state,
                    }
                    reason = getattr(infrastructure, "reason", None)
                    if isinstance(reason, str) and 0 < len(reason) <= 64:
                        detail["reason"] = reason
                    pod_name = getattr(infrastructure, "pod_name", None)
                    if isinstance(pod_name, str) and 0 < len(pod_name) <= 253:
                        detail["pod_name"] = pod_name
                    print(json.dumps(detail, sort_keys=True), flush=True)
                    reconciled = dispatcher.reconcile_pending()
                    print(
                        json.dumps(
                            {
                                "event": "runtime_reconcile_cycle",
                                "observed": len(reconciled),
                                "new_start": False,
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    stop.wait(interval_seconds)
                    continue
                observed = dispatcher.run_once(limit=batch_limit)
                states: dict[str, int] = {}
                for item in observed:
                    states[item.state] = states.get(item.state, 0) + 1
                print(
                    json.dumps(
                        {
                            "event": "runtime_dispatch_cycle",
                            "observed": len(observed),
                            "states": states,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                failures = getattr(dispatcher, "failures", None)
                if isinstance(failures, dict) and failures:
                    codes = sorted({code for code in failures.values() if isinstance(code, str)})
                    print(
                        json.dumps(
                            {
                                "event": "runtime_dispatch_skipped",
                                "count": len(failures),
                                "codes": codes[:8],
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    failures.clear()
            except Exception as error:
                # Never log Assignment, credentials, paths, request bodies or peer data.
                # A stable DomainError code (or the transport operation/status) is
                # bounded operator metadata and is required to diagnose a stuck
                # dispatch loop; raw exception messages are not logged.
                detail = {
                    "event": "runtime_dispatch_error",
                    "error": type(error).__name__,
                }
                code = getattr(error, "code", None)
                if isinstance(code, str) and 0 < len(code) <= 64:
                    detail["code"] = code
                operation = getattr(error, "operation", None)
                if isinstance(operation, str) and 0 < len(operation) <= 64:
                    detail["operation"] = operation
                status = getattr(error, "status", None)
                if type(status) is int:
                    detail["status"] = status
                print(json.dumps(detail, sort_keys=True), flush=True)
            stop.wait(interval_seconds)
    finally:
        try:
            dispatcher.close()
        finally:
            lifecycle.close()


def _load_factory(spec: str):
    module, separator, attribute = spec.partition(":")
    if not separator or not module or not attribute.isidentifier():
        raise ValueError("factory must be an installed module:attribute")
    factory = getattr(importlib.import_module(module), attribute)
    if not callable(factory):
        raise ValueError("runtime factory must be callable")
    return factory


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Run the deployment-configured Wuji runtime controller"
    )
    parser.add_argument(
        "--factory",
        required=True,
        help="Installed deployment module:factory returning RuntimeController",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--batch-limit", type=int, default=16)
    parser.add_argument("--ssl-certfile")
    parser.add_argument("--ssl-keyfile")
    args = parser.parse_args()
    if bool(args.ssl_certfile) != bool(args.ssl_keyfile):
        parser.error("TLS requires both certificate and key")
    controller = _load_factory(args.factory)()
    if not isinstance(controller, RuntimeController):
        raise ValueError("factory did not return RuntimeController")
    stop = Event()
    consumer = Thread(
        target=run,
        kwargs={
            "dispatcher": controller.dispatcher,
            "stop": stop,
            "interval_seconds": args.interval_seconds,
            "batch_limit": args.batch_limit,
            "pod_environment": getattr(controller, "pod_environment", None),
        },
        name="wuji-runtime-dispatch",
        daemon=False,
    )
    consumer.start()
    try:
        uvicorn.run(
            controller.app,
            host=args.host,
            port=args.port,
            access_log=False,
            ssl_certfile=args.ssl_certfile,
            ssl_keyfile=args.ssl_keyfile,
        )
    finally:
        stop.set()
        consumer.join()


if __name__ == "__main__":
    main()
