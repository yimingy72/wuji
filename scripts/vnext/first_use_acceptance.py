#!/usr/bin/env python3
"""Drive and independently check the first-use HTTP read chain.

This is an acceptance *driver*, not another report generator. It talks to a
local BFF through the public create/command/read routes, records complete
redacted request/response exchanges, and checks the read-chain references that
must connect a Task, Run, ToolCall, Artifact, model material and read-set.

The driver is deliberately bounded and local-only by default. It never reads
provider credentials, never prints bearer/cookie values, never contacts a
target on its own, and never injects the independent F1/F2 answer file. A
fixture URL is used only for optional request-counter observations.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen


SCHEMA_VERSION = "wuji.first-use.acceptance-driver.v1"
MAX_BODY_BYTES = 1_048_576
DEFAULT_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.25
POLL_LIMIT = 40

PUBLIC_ROUTE_PATTERNS = (
    re.compile(r"^/api/v2/tasks$"),
    re.compile(r"^/api/v2/tasks/[^/]+$"),
    re.compile(r"^/api/v2/tasks/[^/]+/commands$"),
    re.compile(r"^/api/v2/tasks/[^/]+/(?:readiness|launch)$"),
)
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[^\s,;]+"),
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class DriverError(RuntimeError):
    """An observed request or evidence contract failure."""


class DriverBlocked(DriverError):
    """The configured public chain is not available or evidence is missing."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def redact_headers(headers: Iterable[tuple[str, str]]) -> list[list[str]]:
    """Return headers safe for a public evidence package."""

    return [
        [name, "[REDACTED]" if name.lower() in SENSITIVE_HEADERS else value]
        for name, value in headers
    ]


def _safe_body(raw: bytes) -> tuple[str, bool]:
    truncated = len(raw) > MAX_BODY_BYTES
    bounded = raw[:MAX_BODY_BYTES]
    text = _redact_text(bounded.decode("utf-8", "replace"))
    if truncated:
        text += "\n[TRUNCATED_BY_ACCEPTANCE_DRIVER]"
    return text, truncated


def _local_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise DriverBlocked(
            "first-use driver is local-only; use a localhost BFF endpoint and let A0 coordinate shared deployments"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise DriverError("base URL cannot contain credentials, query, or fragment")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _allowed_path(path: str) -> bool:
    return any(pattern.fullmatch(path) for pattern in PUBLIC_ROUTE_PATTERNS)


def _task_id(payload: dict[str, Any]) -> str:
    for key in ("task_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    raise DriverError("create response did not expose task_id")


def _revision(payload: dict[str, Any]) -> str:
    value = payload.get("version", payload.get("resource_version"))
    if isinstance(value, (str, int)) and str(value):
        return str(value)
    raise DriverError("task/command response did not expose a version")


def command_payload(command: str, expected_version: str, reason: str) -> dict[str, str]:
    if command not in {"start", "pause", "cancel"}:
        raise ValueError(f"unsupported first-use command: {command}")
    return {
        "schema_version": "wuji.api.v2",
        "command": command,
        "expected_version": str(expected_version),
        "reason": reason,
    }


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DriverError(f"cannot read JSON input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DriverError(f"JSON input must be an object: {path}")
    return value


class LocalBFFClient:
    """Small public-route client with a complete redacted exchange ledger."""

    def __init__(self, base_url: str, *, auth_value: str | None, timeout: float) -> None:
        self.base_url = _local_base_url(base_url)
        self.auth_value = auth_value
        self.timeout = timeout
        self.exchanges: list[dict[str, Any]] = []

    def request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[int, dict[str, Any] | None, dict[str, Any]]:
        if not _allowed_path(path):
            raise DriverError(f"path is outside the first-use public allowlist: {path}")
        url = self.base_url + path
        headers: list[tuple[str, str]] = [("Accept", "application/json")]
        if body is not None:
            headers.append(("Content-Type", "application/json"))
        if idempotency_key:
            headers.append(("Idempotency-Key", idempotency_key))
        if self.auth_value:
            headers.append(("Authorization", self.auth_value))
        request_body = _json_bytes(body) if body is not None else b""
        request = Request(
            url,
            data=request_body or None,
            headers=dict(headers),
            method=method,
        )
        status: int
        response_headers: list[tuple[str, str]] = []
        response_body = b""
        error: str | None = None
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = response.status
                response_headers = list(response.headers.items())
                response_body = response.read(MAX_BODY_BYTES + 1)
        except HTTPError as exc:
            status = exc.code
            response_headers = list(exc.headers.items())
            response_body = exc.read(MAX_BODY_BYTES + 1)
            error = f"HTTPError:{exc.code}"
        except URLError as exc:
            raise DriverBlocked(f"BFF unavailable at {self.base_url}: {exc.reason}") from exc

        request_text, request_truncated = _safe_body(request_body)
        response_text, response_truncated = _safe_body(response_body)
        parsed: dict[str, Any] | None = None
        if response_body:
            try:
                decoded = json.loads(response_body[:MAX_BODY_BYTES])
            except (UnicodeDecodeError, json.JSONDecodeError):
                decoded = None
            if isinstance(decoded, dict):
                parsed = decoded
        exchange = {
            "method": method,
            "url": url,
            "request_headers": redact_headers(headers),
            "request_body": request_text,
            "request_truncated": request_truncated,
            "response_status": status,
            "response_headers": redact_headers(response_headers),
            "response_body": response_text,
            "response_truncated": response_truncated,
        }
        if error:
            exchange["error"] = error
        self.exchanges.append(exchange)
        return status, parsed, exchange


def _is_accepted(status: int) -> bool:
    return 200 <= status < 300


def _poll_task(client: LocalBFFClient, task_id: str, *, target: set[str]) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for _ in range(POLL_LIMIT):
        status, body, _ = client.request(method="GET", path=f"/api/v2/tasks/{quote(task_id, safe='')}")
        if _is_accepted(status) and body:
            last = body
            if body.get("observed_state") in target or body.get("desired_state") in target:
                return body
        time.sleep(POLL_INTERVAL_SECONDS)
    if last is not None:
        observed = last.get("observed_state", last.get("desired_state"))
        raise DriverError(
            f"task {task_id} did not reach one of {sorted(target)}; last observed state={observed!r}"
        )
    raise DriverBlocked(f"task read did not return an object for {task_id}")


def _command(
    client: LocalBFFClient,
    *,
    task_id: str,
    command: str,
    task: dict[str, Any],
    reason: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    status, body, exchange = client.request(
        method="POST",
        path=f"/api/v2/tasks/{quote(task_id, safe='')}/commands",
        body=command_payload(command, _revision(task), reason),
        idempotency_key=f"first-use-{command}-{task_id}",
    )
    if not _is_accepted(status):
        raise DriverError(f"{command} was not accepted: HTTP {status}")
    return body, exchange


def run_first_use(args: argparse.Namespace) -> dict[str, Any]:
    auth_value = None
    if args.auth_env:
        auth_value = os.environ.get(args.auth_env)
        if auth_value and not auth_value.lower().startswith(("bearer ", "session ")):
            raise DriverError(f"{args.auth_env} must contain a bearer/session value; value is never printed")
    client = LocalBFFClient(args.base_url, auth_value=auth_value, timeout=args.timeout)
    create_payload = _read_json_file(Path(args.create_payload))
    task_refs: dict[str, Any] = {}

    create_key = "first-use-create-" + uuid.uuid4().hex
    status, created, _ = client.request(
        method="POST", path="/api/v2/tasks", body=create_payload, idempotency_key=create_key
    )
    if status != 201 or not created:
        raise DriverError(f"create did not return HTTP 201 TaskView: HTTP {status}")
    task_id = _task_id(created)
    task_refs["task_id"] = task_id
    task_refs["create_response"] = created

    status, before_start, _ = client.request(method="GET", path=f"/api/v2/tasks/{quote(task_id, safe='')}")
    if not _is_accepted(status) or not before_start:
        raise DriverError(f"created task could not be read back: HTTP {status}")
    task_refs["before_start"] = before_start

    status, readiness, _ = client.request(
        method="GET", path=f"/api/v2/tasks/{quote(task_id, safe='')}/readiness"
    )
    if not _is_accepted(status) or not readiness:
        raise DriverError(f"readiness did not return a report: HTTP {status}")
    task_refs["readiness_before_start"] = readiness

    if before_start.get("observed_state") not in {"ready", "paused"}:
        raise DriverError("create response is already active; driver refuses implicit start")

    start_receipt, _ = _command(
        client, task_id=task_id, command="start", task=before_start, reason="A8 first-use start"
    )
    task_refs["start_command"] = start_receipt
    running = _poll_task(client, task_id, target={"running"})
    task_refs["after_start"] = running

    status, launch, _ = client.request(method="GET", path=f"/api/v2/tasks/{quote(task_id, safe='')}/launch")
    if not _is_accepted(status) or not launch:
        raise DriverError(f"launch read did not return a launch view: HTTP {status}")
    task_refs["launch"] = launch

    status, readiness_after_start, _ = client.request(
        method="GET", path=f"/api/v2/tasks/{quote(task_id, safe='')}/readiness"
    )
    if not _is_accepted(status) or not readiness_after_start:
        raise DriverError(f"post-start readiness read failed: HTTP {status}")
    task_refs["readiness_after_start"] = readiness_after_start

    pause_receipt, _ = _command(
        client, task_id=task_id, command="pause", task=running, reason="A8 first-use pause"
    )
    task_refs["pause_command"] = pause_receipt
    paused = _poll_task(client, task_id, target={"paused", "quiescing", "reconciling"})
    task_refs["after_pause"] = paused

    cancel_receipt, _ = _command(
        client, task_id=task_id, command="cancel", task=paused, reason="A8 first-use cancel"
    )
    task_refs["cancel_command"] = cancel_receipt
    stopped = _poll_task(client, task_id, target={"closed", "paused", "reconciling"})
    task_refs["after_cancel"] = stopped

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "document_status": "observed_http_chain",
        "evaluation_mode": args.evaluation_mode,
        "candidate_sha": args.candidate_sha,
        "base_url": client.base_url,
        "create_idempotency_key": create_key,
        "task_refs": task_refs,
        "exchanges": client.exchanges,
        "read_chain": None,
        "read_chain_validation": None,
    }
    read_chain = _read_json_file(Path(args.read_chain))
    evidence["read_chain"] = read_chain
    evidence["read_chain_validation"] = validate_read_chain(read_chain)
    if not evidence["read_chain_validation"]["valid"]:
        raise DriverError("read-chain references are incomplete or inconsistent")
    return evidence


def _one_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def validate_read_chain(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the evidence contract without asserting a model conclusion."""

    errors: list[str] = []
    task_id = value.get("task_id")
    run_id = value.get("run_id")
    tool_call_id = value.get("tool_call_id")
    artifact_ref = value.get("artifact_ref")
    read_set = value.get("read_set")
    model_attempt_ids = value.get("model_attempt_ids")
    material = value.get("material")

    for item, name in ((task_id, "task_id"), (run_id, "run_id"), (tool_call_id, "tool_call_id")):
        try:
            _one_string(item, name)
        except ValueError as exc:
            errors.append(str(exc))
    if not isinstance(artifact_ref, dict) or not artifact_ref.get("id"):
        errors.append("artifact_ref.id must identify the sealed source artifact")
    elif not isinstance(artifact_ref.get("revision", "1"), (str, int)):
        errors.append("artifact_ref.revision must be a revision value")
    if not isinstance(read_set, list) or not read_set:
        errors.append("read_set must contain the exact material read reference")
    else:
        encoded_read_set = json.dumps(read_set, ensure_ascii=False, sort_keys=True)
        if str(tool_call_id) not in encoded_read_set and str(artifact_ref.get("id")) not in encoded_read_set:
            errors.append("read_set does not reference the observed ToolCall or source Artifact")
    if not isinstance(model_attempt_ids, list) or not model_attempt_ids or not all(
        isinstance(item, str) and item for item in model_attempt_ids
    ):
        errors.append("model_attempt_ids must list the actual model attempts")
    if not isinstance(material, dict):
        errors.append("material must contain the delivered/omitted model-material view")
    else:
        if material.get("status") != "delivered":
            errors.append("material.status must be delivered for a content-delivery claim")
        source = material.get("source")
        representation = material.get("representation")
        if not isinstance(source, dict):
            errors.append("material.source is missing")
        else:
            if not HEX64.fullmatch(str(source.get("artifact_sha256", ""))):
                errors.append("material.source.artifact_sha256 must be a SHA-256")
            if source.get("artifact_ref") != artifact_ref:
                errors.append("material.source.artifact_ref does not equal artifact_ref")
        if not isinstance(representation, dict):
            errors.append("material.representation is missing")
        else:
            if not HEX64.fullmatch(str(representation.get("representation_sha256", ""))):
                errors.append("material.representation.representation_sha256 must be a SHA-256")
            text = representation.get("text")
            if not isinstance(text, str) or not text:
                errors.append("material.representation.text must preserve delivered content")
            if representation.get("encoding") != "utf-8":
                errors.append("material.representation.encoding must be utf-8")
    return {"valid": not errors, "errors": errors}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run the public local BFF first-use chain")
    run.add_argument("--base-url", required=True)
    run.add_argument("--create-payload", required=True, type=Path)
    run.add_argument("--read-chain", required=True, type=Path)
    run.add_argument("--auth-env", help="environment variable containing a bearer/session value")
    run.add_argument("--candidate-sha", default=None)
    run.add_argument("--evaluation-mode", choices=("mechanism_synthetic", "real_model"), default="mechanism_synthetic")
    run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    run.add_argument("--output", required=True, type=Path)

    check = subparsers.add_parser("validate-read-chain", help="validate an actual read-chain evidence object")
    check.add_argument("--input", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            evidence = run_first_use(args)
            _write_json(args.output, evidence)
            print(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "status": "observed",
                "task_id": evidence["task_refs"]["task_id"],
                "exchange_count": len(evidence["exchanges"]),
                "read_chain": evidence["read_chain_validation"],
                "output": str(args.output),
            }, ensure_ascii=False, sort_keys=True))
            return 0
        value = _read_json_file(args.input)
        result = validate_read_chain(value)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["valid"] else 1
    except DriverBlocked as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (DriverError, OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
