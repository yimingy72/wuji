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
                if pod_environment is not None:
                    infrastructure = pod_environment.ensure()
                    if infrastructure.state != "ready":
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
            except Exception as error:
                # Never log Assignment, credentials, paths, request bodies or peer data.
                print(
                    json.dumps(
                        {
                            "event": "runtime_dispatch_error",
                            "error": type(error).__name__,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
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
