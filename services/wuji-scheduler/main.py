"""Deployment-composed Scheduler service. It never starts a Worker or migrates DB."""

import argparse
import importlib
import json
import signal
from threading import Event

from wuji_core.scheduling.claims import Scheduler


def run(scheduler, *, stop, interval_seconds=1.0):
    if not isinstance(scheduler, Scheduler) or not 0 < interval_seconds <= 60:
        raise ValueError("a composed Scheduler and a bounded interval are required")
    if not scheduler.ownership.acquire():
        raise RuntimeError("another Scheduler owns the database session lock")
    try:
        while not stop.is_set():
            receipt = scheduler.tick()
            # No Assignment body, credential, prompt or Task definition in logs.
            print(
                json.dumps(
                    {
                        "event": "scheduler_tick",
                        "admitted": len(receipt.assignments),
                        "selected": len(receipt.selected),
                        "blocked": len(receipt.blocked),
                    }
                ),
                flush=True,
            )
            stop.wait(interval_seconds)
    finally:
        scheduler.ownership.close()


def main():
    parser = argparse.ArgumentParser(
        description="Run the deployment-configured Wuji Scheduler"
    )
    parser.add_argument(
        "--factory",
        required=True,
        help="Installed deployment module:factory returning Scheduler",
    )
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    args = parser.parse_args()
    module, separator, attribute = args.factory.partition(":")
    if not separator or not module or not attribute.isidentifier():
        parser.error("factory must be an installed module:attribute")
    factory = getattr(importlib.import_module(module), attribute)
    scheduler = factory()
    stop = Event()

    def stopping(_signal, _frame):
        stop.set()

    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    run(scheduler, stop=stop, interval_seconds=args.interval_seconds)


if __name__ == "__main__":
    main()
