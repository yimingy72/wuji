"""Harmless watchdog child. No MAF imports or SDK capability claims."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--worker", type=Path, required=True)
args = parser.parse_args()
config = json.loads(args.worker.read_text())
directory = Path(config["directory"])
with (directory / "watchdog-starts.txt").open("a") as file:
    file.write(str(os.getpid()) + "\n")
print("watchdog stdout ✓", flush=True)
print("watchdog stderr ✓", file=sys.stderr, flush=True)
if config["watchdog_observations"]:
    request = urllib.request.Request(
        config["url"] + "/chat/completions",
        data=json.dumps({"model": "watchdog-no-sdk", "tools": [], "messages": [
            {"role": "user", "content": "watchdog reporting fixture; no SDK invocation"}
        ]}).encode(),
        headers={"Content-Type": "application/json", "X-P01-Purpose": "watchdog-no-sdk"},
    )
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=2) as response:
        body = response.read()
    raw = (directory / "record.json").read_bytes()
    event = {"source": "watchdog fixture, not MAF", "operation": "read_fixture", "pid": os.getpid(),
             "sha256": hashlib.sha256(raw).hexdigest(), "bytes_read": len(raw)}
    (directory / "reads.jsonl").write_text(json.dumps(event) + "\n")
    observation = {"source": "watchdog fixture, not MAF", "pid": os.getpid(), "response_bytes": len(body)}
    (directory / "initial-result.json").write_text(json.dumps(observation))
# Bounded even if the outer watchdog regresses; no target or SDK side effects.
time.sleep(10)
