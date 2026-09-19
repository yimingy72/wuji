"""Run one fixed-SHA Python collection/suite and retain native process output.

No uv synchronization, secret/config dumps, test filtering or skip overrides.
The caller supplies the verified interpreter and PYTHONPATH for this checkout.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "5cdbd170939f1d2e410868ab591381331f5cdba9"


def run(output, collect):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != CANDIDATE:
        raise SystemExit("candidate HEAD changed; select a new explicit run")
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "pytest", "tests/vnext", "-q"]
    command += ["--collect-only"] if collect else ["--tb=short", "-ra", "--junitxml=" + str(output / "junit.xml")]
    manifest = {"candidate_sha": head, "scope": "Python tests/vnext collection" if collect else "Python tests/vnext full suite",
                "command": command, "cwd": str(ROOT), "PYTHONPATH": os.environ.get("PYTHONPATH"),
                "started_at": datetime.now(timezone.utc).isoformat(), "exit_code": None,
                "record_type": "process_result_not_product_acceptance", "implicit_skips_added": False}
    meta = output / "manifest.json"
    meta.write_text(json.dumps(manifest, indent=2) + "\n")
    start = time.monotonic()
    print("Started " + manifest["scope"] + "; output=" + str(output), flush=True)
    with (output / "stdout.txt").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        process = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    manifest.update(exit_code=process.returncode, elapsed_seconds=round(time.monotonic() - start, 3),
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    head_after=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    manifest["output_sha256"] = {name: sha256((output / name).read_bytes()).hexdigest() for name in ("stdout.txt", "stderr.txt")}
    meta.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ("candidate_sha", "exit_code", "elapsed_seconds", "head_after")}), flush=True)
    return process.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.output.resolve(), args.collect_only))
