"""Read-only, fixed-SHA A5 probes. Exit 1 means observed contract violations.

Uses real renderer code from Git and real generated DTOs. No target/model
network, credentials, production writes, or claims of end-to-end acceptance.
"""
import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
A5 = "25c5df3bbfdfc81c0d76c52686c62894a3f03bc8"


def frozen_module(commit, relative_path, name):
    source = subprocess.check_output(["git", "show", f"{commit}:{relative_path}"], cwd=ROOT, text=True)
    module = types.ModuleType(name)
    module.__file__ = f"{commit}:{relative_path}"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def exchange(*, location=None, truncated=False, body=b"harmless fixture"):
    headers = {"content-type": "text/plain; charset=utf-8"}
    if location:
        headers["location"] = location
    return {"schema_version": "wuji.http-exchange.v1", "tool_attempt_id": "attempt-a8",
            "target": "http://fixture.invalid:80", "request": {"method": "GET", "url": "http://fixture.invalid/", "headers": {}},
            "response": {"status": 302 if location else 200, "headers": headers,
                         "body_base64": base64.b64encode(body).decode(), "body_bytes": len(body), "truncated": truncated}}


def render(module, document, *, completeness="complete"):
    raw = json.dumps(document).encode()
    ref = {"id": "artifact-a8", "version": "1", "sha256": sha256(raw).hexdigest()}
    record = {"state": "sealed", "sha256": ref["sha256"], "size_bytes": len(raw),
              "media_type": module.HTTP_EXCHANGE_MEDIA_TYPE, "completeness": completeness}
    return module.render_http_exchange_v2("call-a8", artifact_ref=ref, artifact_record=record, raw=raw).model_dump(mode="json")


def probe(commit=A5):
    module = frozen_module(commit, "packages/wuji-core/src/wuji_core/admission/model_material.py", "a8_fixed_renderer")
    location_input = exchange(location="https://synthetic-user:synthetic-password@example.invalid/redirect")
    location = render(module, location_input)
    truncation_input = exchange(truncated=True)
    truncation = render(module, truncation_input)
    partial = render(module, truncation_input, completeness="partial")
    text = location["representation"]["text"] if location["representation"] else ""
    observations = [
        {"id": "A8-MAT-LOCATION", "expected": "userinfo absent from model material",
         "violation_observed": "synthetic-password" in text,
         "input": location_input, "actual": location},
        {"id": "A8-MAT-TRUNCATION", "expected": "capture truncation remains visible or packet omitted",
         "violation_observed": truncation["status"] == "delivered" and truncation["source"]["completeness"] == "complete" and not truncation["representation"]["truncated"] and "truncated" not in truncation["representation"]["text"],
         "input": truncation_input, "actual": truncation},
        {"id": "A8-MAT-PARTIAL", "expected": "an honestly partial source retains partial metadata",
         "violation_observed": partial["source"]["completeness"] != "partial", "actual": partial},
    ]
    return {"reviewed_sha": commit, "method": "fixed_source_pure_renderer_probe", "observations": observations,
            "violation_count": sum(item["violation_observed"] for item in observations)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default=A5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = probe(args.commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"reviewed_sha": output["reviewed_sha"], "violation_count": output["violation_count"],
                      "observations": [{"id": o["id"], "violation_observed": o["violation_observed"]} for o in output["observations"]]}))
    raise SystemExit(1 if output["violation_count"] else 0)
