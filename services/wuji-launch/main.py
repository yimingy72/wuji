"""Private durable launch consumer, separate from every HTTP application."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import signal
from threading import Event


_SAFE = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")
_PROGRESS = ("task_id", "operation_id", "phase", "phase_status", "reason_code")


def run(worker, *, stop: Event, interval_seconds=1.0, batch_limit=4):
    if (
        not callable(getattr(worker, "run_once", None))
        or not isinstance(stop, Event)
        or not 0 < interval_seconds <= 60
        or type(batch_limit) is not int
        or not 1 <= batch_limit <= 32
    ):
        raise ValueError("a durable worker and bounded polling are required")
    while not stop.is_set():
        try:
            progress = worker.run_once(limit=batch_limit)
            for item in progress:
                detail = {"event": "task_launch_progress"}
                for key in _PROGRESS:
                    value = item.get(key)
                    if isinstance(value, str) and _SAFE.fullmatch(value):
                        detail[key] = value
                print(json.dumps(detail, sort_keys=True), flush=True)
        except Exception as error:
            # Raw peer/config/SQL messages can contain credentials or target data.
            detail = {"event": "task_launch_cycle_error", "error": type(error).__name__}
            code = getattr(error, "code", None)
            if isinstance(code, str) and _SAFE.fullmatch(code):
                detail["code"] = code
            print(json.dumps(detail, sort_keys=True), flush=True)
        stop.wait(interval_seconds)


def _load_factory(spec):
    module, separator, attribute = spec.partition(":")
    if not separator or not module or not attribute.isidentifier():
        raise ValueError("factory must be an installed module:attribute")
    factory = getattr(importlib.import_module(module), attribute)
    if not callable(factory):
        raise ValueError("launch factory must be callable")
    return factory


def main():
    from wuji_core.execution.launch import LaunchWorker

    parser = argparse.ArgumentParser(description="Consume durable Wuji start commands")
    parser.add_argument("--factory", default="deployment:build_launch_worker")
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--batch-limit", type=int, default=4)
    args = parser.parse_args()
    worker = _load_factory(args.factory)()
    if not isinstance(worker, LaunchWorker):
        raise ValueError("factory did not return a durable LaunchWorker")
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    try:
        run(worker, stop=stop, interval_seconds=args.interval_seconds, batch_limit=args.batch_limit)
    finally:
        close = getattr(worker.adapter, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    main()
