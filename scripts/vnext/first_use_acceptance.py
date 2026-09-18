#!/usr/bin/env python3
"""One public BFF control action per invocation; this is NOT an E2E verdict.

Cookie login is local_single_operator only. All mutations send the exact
Origin. Start never automatically pauses/cancels: A0 can collect model/tool
evidence before invoking the next control action. The journal is flushed
before each request and after each response, including failed/unknown calls.
Only the BFF Cookie is saved in an explicit restricted session file; no
credential enters the HTTP journal. Read-chain checking is a separate offline
consistency check of exported raw captures, not proof of their provenance.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

SCHEMA_VERSION = "wuji.first-use.control-driver.v2"
MAX_BYTES = 2 * 1024 * 1024
ID = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
SECRET_NAMES = {"authorization", "proxy-authorization", "cookie", "set-cookie",
                "api_key", "api-key", "apikey", "token", "access_token",
                "refresh_token", "secret", "password", "x-api-key", "x-wuji-local-bootstrap"}


class DriverError(RuntimeError):
    pass


class DriverBlocked(DriverError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_object(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise DriverError("input exceeds capture bound")
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise DriverError("input must be an object")
    return value


def write_object(path, value):
    """Atomic local output (0600); callers separate sessions from public evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        temporary.chmod(0o600)
        stream.write(encoded(value).decode() + "\n")
    temporary.replace(path)


def redact(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SECRET_NAMES else redact(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)Bearer\s+[^\s\";,]+", "Bearer [REDACTED]", value)
    return value


def headers_public(headers):
    return [[key, "[REDACTED]" if key.lower() in SECRET_NAMES else value]
            for key, value in headers.multi_items()]


def local_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        raise DriverBlocked("use an exact localhost BFF origin")
    return value.rstrip("/")


def safe_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise DriverError("invalid task identity")
    return value


def allowed_route(method, path):
    if (method, path) in {("POST", "/auth/login"), ("GET", "/auth/session"),
                          ("POST", "/auth/logout"), ("POST", "/api/v2/tasks")}:
        return True
    match = re.fullmatch(r"/api/v2/tasks/([A-Za-z0-9_.:-]{1,256})(/[^/?]+)?", path)
    return bool(match and ((method == "GET" and match[2] in {None, "/readiness", "/launch"})
                          or (method == "POST" and match[2] == "/commands")))


class LocalBFFClient:
    def __init__(self, base_url, journal, persist, *, timeout=10):
        self.base_url = local_origin(base_url)
        self.journal, self.persist = journal, persist
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout,
                                   trust_env=False, follow_redirects=False)

    def close(self):
        self.client.close()

    def request(self, method, path, *, body=None, key=None, bootstrap=None):
        if not allowed_route(method, path):
            raise DriverError("route is outside the public control allowlist")
        headers = {"Accept": "application/json"}
        if method == "POST":
            headers["Origin"] = self.base_url
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key:
            headers["Idempotency-Key"] = key
        if bootstrap is not None:
            if (method, path) != ("POST", "/auth/login"):
                raise DriverError("bootstrap credential only belongs to login")
            headers["x-wuji-local-bootstrap"] = bootstrap
        request = self.client.build_request(method, path, headers=headers,
                                            content=encoded(body) if body is not None else b"")
        entry = {"method": method, "url": str(request.url), "request_headers": headers_public(request.headers),
                 "request_body": encoded(redact(body)).decode() if body is not None else "",
                 "response_status": None, "response_headers": [], "response_body": None,
                 "outcome": "request_pending", "complete": False}
        self.journal["exchanges"].append(entry)
        self.persist()
        try:
            with closing(self.client.send(request, stream=True)) as response:
                entry.update(response_status=response.status_code,
                             response_headers=headers_public(response.headers))
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    remaining = max(0, MAX_BYTES - size)
                    size += len(chunk)
                    chunks.append(chunk[:remaining])
                    entry["response_body"] = redact(b"".join(chunks).decode("utf-8", errors="replace"))
                    if size > MAX_BYTES:
                        raise DriverError("response exceeds capture bound; evidence incomplete")
                raw = b"".join(chunks)
                # Public BFF contract is JSON; malformed bytes are retained in
                # the bounded ledger for diagnosis, never parsed as success.
                entry["response_body"] = redact(raw.decode("utf-8", errors="replace"))
                entry["complete"] = True
                entry["outcome"] = "http_response"
                if 300 <= response.status_code < 400:
                    raise DriverError("redirect refused; no follow-up request sent")
                document = strict_json(raw) if raw else {}
                if redact(document) != document:
                    entry["response_body"] = encoded(redact(document)).decode()
                    entry["body_redacted"] = True
                if not 200 <= response.status_code < 300:
                    raise DriverError(f"HTTP {response.status_code}")
                if not isinstance(document, dict):
                    raise DriverError("response is not a JSON object")
                return document
        except httpx.HTTPError as error:
            entry["outcome"] = "transport_unknown"
            entry["error_class"] = type(error).__name__
            raise DriverBlocked("response unknown; reconcile this operation before another mutation") from None
        finally:
            self.persist()

    def login(self, *, session_file, bootstrap=None):
        if session_file.exists():
            if session_file.is_symlink() or session_file.stat().st_mode & 0o077:
                raise DriverError("session file must be a restricted regular file (0600)")
            session_cookie = read_object(session_file)
            if session_cookie.get("base_url") != self.base_url:
                raise DriverError("session cookie belongs to another BFF origin")
            token = session_cookie.get("cookie")
            if not isinstance(token, str) or not 1 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
                raise DriverError("invalid session cookie")
            self.client.cookies.set("wuji_vnext_session", token)
        else:
            if not bootstrap:
                raise DriverBlocked("A0 must supply a restricted BFF session file or one-time local bootstrap input")
            self.request("POST", "/auth/login", bootstrap=bootstrap)
            token = self.client.cookies.get("wuji_vnext_session")
            if not token:
                raise DriverError("login did not set the BFF session cookie")
            write_object(session_file, {"base_url": self.base_url, "cookie": token})
        session = self.request("GET", "/auth/session")
        if session.get("authenticated") is not True:
            raise DriverBlocked("BFF session is not authenticated")
        if session.get("mode") != "local_single_operator":
            raise DriverBlocked("BFF did not identify local_single_operator mode")
        return session


def _poll_task(client, task_id, *, target, count=40, interval=0.25):
    """Only observed_state satisfies a wait. Reconciling never means stopped."""
    last = None
    for index in range(count):
        last = client.request("GET", f"/api/v2/tasks/{safe_id(task_id)}")
        if last.get("task_id") != task_id:
            raise DriverError("task read returned a different identity")
        client.journal["last_task"] = last
        client.persist()
        if last.get("observed_state") in target:
            return last
        if index + 1 < count:
            time.sleep(interval)
    raise DriverBlocked(f"observation pending: {last.get('observed_state') if last else 'absent'}")


def command_payload(command, expected_version, reason):
    if command not in {"start", "pause", "cancel"} or not re.fullmatch(r"[1-9][0-9]*", str(expected_version)):
        raise DriverError("invalid command/version")
    return {"schema_version": "wuji.api.v2", "command": command,
            "expected_version": str(expected_version), "reason": reason}


def control(args):
    origin = local_origin(args.base_url)
    state = read_object(args.state) if args.state.exists() else {"base_url": origin, "operations": {}}
    if state.get("base_url") != origin:
        raise DriverError("state belongs to another BFF")
    journal = {"schema_version": SCHEMA_VERSION, "scope": "http_control_only",
               "candidate_sha": args.candidate_sha, "action": args.action,
               "status": "in_progress", "exchanges": [],
               "e2e_status": "not_run", "process_stop": "not_verified",
               "operations_settled": "not_verified", "billing": "not_verified"}
    def persist():
        write_object(args.output, redact(journal))
    persist()
    client = LocalBFFClient(origin, journal, persist, timeout=args.timeout)
    try:
        bootstrap = os.environ.get(args.bootstrap_env) if args.bootstrap_env else None
        session = client.login(session_file=args.session_file, bootstrap=bootstrap)
        journal["identity_mode"] = session["mode"]
        if args.action == "create":
            if state.get("task_id"):
                raise DriverError("journal already owns a task; use read or a new state file")
            if args.create_payload is None:
                raise DriverError("create requires --create-payload")
            body, path = read_object(args.create_payload), "/api/v2/tasks"
        else:
            task_id = safe_id(state.get("task_id"))
            task = client.request("GET", f"/api/v2/tasks/{task_id}")
            if task.get("task_id") != task_id:
                raise DriverError("read returned another Task")
            journal["last_task"] = task
            if args.action == "read":
                for leaf in ("readiness", "launch"):
                    journal[leaf] = client.request("GET", f"/api/v2/tasks/{task_id}/{leaf}")
                journal["status"] = "observed"
                return 0
            body = command_payload(args.action, task.get("version"), "A8 explicit HTTP control check")
            path = f"/api/v2/tasks/{task_id}/commands"
        previous = state["operations"].get(args.action)
        if previous:
            # No automatic retry, no regenerated key after lost responses.
            raise DriverBlocked("operation already recorded; inspect its original key and receipt")
        operation = {"key": "first-use-" + uuid4().hex, "body": body, "path": path, "status": "pending"}
        state["operations"][args.action] = operation
        if redact(body) != body:
            raise DriverError("create/control body contains a credential-shaped field")
        write_object(args.state, state)
        reply = client.request("POST", path, body=body, key=operation["key"])
        operation.update(status="accepted", receipt=reply)
        if args.action == "create":
            state["task_id"] = safe_id(reply.get("task_id"))
        write_object(args.state, redact(state))
        journal["task_id"] = state["task_id"]
        journal["receipt"] = reply
        target = {"create": {"ready"}, "start": {"running"}, "pause": {"paused"}, "cancel": {"closed"}}[args.action]
        journal["last_task"] = _poll_task(client, state["task_id"], target=target,
                                         count=args.poll_count, interval=args.poll_interval)
        for leaf in ("readiness", "launch"):
            journal[leaf] = client.request("GET", f"/api/v2/tasks/{state['task_id']}/{leaf}")
        journal["status"] = "observed"
        return 0
    except DriverBlocked as error:
        journal.update(status="blocked", error=str(error))
        return 2
    except (DriverError, ValueError, OSError) as error:
        journal.update(status="failed", error_class=type(error).__name__, error=str(error))
        return 1
    finally:
        client.close()
        persist()


def validate_read_chain(value, *, expected_task_id, expected_candidate_sha):
    """Check an exported *raw capture* chain, without trusting supplied hashes.

Required: source_bytes_base64; BlobRef(id/version/sha256); exact read_set;
tool_receipt; material v2; two ordered model HTTP captures including their raw
request/response bodies. Captures are exported by A0 on the trusted boundary;
local consistency alone cannot authenticate the exporter or prove E2E.
"""
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    try:
        check(value["task_id"] == expected_task_id, "wrong Task")
        check(value["candidate_sha"] == expected_candidate_sha, "wrong candidate")
        for identity_name in ("run_id", "tool_call_id", "native_tool_call_id"):
            check(isinstance(value[identity_name], str) and bool(value[identity_name]), "missing " + identity_name)
        ref = value["artifact_ref"]
        check(isinstance(ref, dict) and set(ref) == {"id", "version", "sha256"}, "invalid BlobRef")
        if errors:
            return {"valid": False, "errors": errors, "scope": "offline_capture_consistency"}
        check(isinstance(ref["id"], str) and bool(ref["id"]), "missing artifact id")
        check(isinstance(ref["version"], str) and bool(re.fullmatch(r"[1-9][0-9]*", ref["version"])), "invalid version")
        check(isinstance(ref["sha256"], str) and bool(SHA.fullmatch(ref["sha256"])), "invalid source hash")
        source = base64.b64decode(value["source_bytes_base64"], validate=True)
        check(len(source) <= MAX_BYTES and sha256(source).hexdigest() == ref["sha256"], "source bytes/hash mismatch")
        exact = {"entity_type": "artifact", "id": ref["id"], "revision": ref["version"]}
        check(isinstance(value["read_set"], list) and exact in value["read_set"], "exact source revision absent from read_set")
        material, receipt = value["material"], value["tool_receipt"]
        check(receipt["result_ref"] == ref and receipt["status"] == "complete", "receipt source/status mismatch")
        check(receipt["tool_call_id"] == value["tool_call_id"], "receipt ToolCall mismatch")
        check(material["tool_call_id"] == receipt["tool_call_id"], "material ToolCall mismatch")
        check(material["schema_version"] == "wuji.model-material.v2" and material["status"] == "delivered", "not delivered v2")
        check(material["source"]["artifact_ref"] == ref and material["source"]["artifact_sha256"] == ref["sha256"], "material source binding mismatch")
        rep = material["representation"]
        raw_text = rep["text"].encode("utf-8")
        check(rep["encoding"] == "utf-8" and type(rep["byte_length"]) is int and len(raw_text) == rep["byte_length"], "representation byte length/encoding mismatch")
        check(sha256(raw_text).hexdigest() == rep["representation_sha256"], "representation hash mismatch")
        check(len(raw_text) <= 32768 and len(raw_text) > 0, "representation size invalid")
        captures = value["model_captures"]
        check(isinstance(captures, list) and len(captures) == 2, "need two ordered raw model captures")
        first, second = captures
        for capture in captures:
            check(capture["task_id"] == expected_task_id and capture["run_id"] == value["run_id"], "capture identity mismatch")
            check(capture["request"]["method"] == "POST" and capture["response"]["status"] == 200, "incomplete model HTTP exchange")
            check(isinstance(capture["model_attempt_id"], str) and bool(capture["model_attempt_id"]), "missing model attempt")
            check(bool(capture["response"]["body"]), "missing model response body")
        check(first["model_attempt_id"] != second["model_attempt_id"], "model attempts not distinct")
        requests = [strict_json(c["request"]["body"]) for c in captures]
        # F1 marker is generated at the HTTP source, never in the first prompt.
        marker = value["marker"]
        check(isinstance(marker, str) and len(marker) >= 16 and marker.encode() in source, "marker absent from source")
        check(marker not in json.dumps(requests[0], ensure_ascii=False), "marker was preloaded")
        native_call = value["native_tool_call_id"]
        check(native_call in native_call_ids(first["response"]["body"]), "first model did not issue the tool call")
        check(marker in rep["text"], "marker absent from representation")
        delivered = []
        for message in requests[1]["messages"]:
            if message.get("role") == "tool" and message.get("tool_call_id") == native_call:
                delivered.append(strict_json(message["content"]))
        check(len(delivered) == 1, "second raw request lacks a unique matching tool message")
        if delivered:
            check(delivered[0] == {**receipt, "material": material}, "second model received different content/references")
    except (KeyError, TypeError, ValueError, AttributeError, UnicodeError, RecursionError) as error:
        errors.append("malformed capture: " + type(error).__name__)
    return {"valid": not errors, "errors": errors, "scope": "offline_capture_consistency"}


def native_call_ids(body):
    """Read complete JSON or Chat Completions SSE, retaining fragmented IDs."""
    if not body.lstrip().startswith("data:"):
        response = strict_json(body)
        return [call["id"] for call in response["choices"][0]["message"].get("tool_calls", [])]
    fragments = {}
    for line in body.splitlines():
        if not line.startswith("data:") or line[5:].strip() == "[DONE]":
            continue
        chunk = strict_json(line[5:].strip())
        for choice in chunk.get("choices", []):
            for call in choice.get("delta", {}).get("tool_calls", []):
                index = (choice["index"], call["index"])
                fragments[index] = fragments.get(index, "") + call.get("id", "")
    return list(fragments.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("control", help="one explicit HTTP control action; no E2E verdict")
    run.add_argument("--action", choices=("create", "read", "start", "pause", "cancel"), required=True)
    run.add_argument("--base-url", required=True)
    run.add_argument("--create-payload", type=Path)
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--session-file", type=Path, required=True, help="restricted 0600 BFF Cookie file, never Git/public evidence")
    run.add_argument("--bootstrap-env", help="A0-supplied one-time local login credential; never a provider key")
    run.add_argument("--candidate-sha", required=True)
    run.add_argument("--timeout", type=float, default=10)
    run.add_argument("--poll-count", type=int, default=40)
    run.add_argument("--poll-interval", type=float, default=0.25)
    verify = commands.add_parser("validate-read-chain")
    verify.add_argument("--input", type=Path, required=True)
    verify.add_argument("--task-id", required=True)
    verify.add_argument("--candidate-sha", required=True)
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha):
            raise DriverError("full candidate SHA required")
        if args.command == "control":
            if not 1 <= args.poll_count <= 120 or not 0 <= args.poll_interval <= 2 or not 0 < args.timeout <= 30:
                raise DriverError("invalid polling/request bound")
            paths = [args.state.resolve(), args.output.resolve(), args.session_file.resolve()]
            if args.create_payload:
                paths.append(args.create_payload.resolve())
            if len(paths) != len(set(paths)) or args.output.exists():
                raise DriverError("use distinct state/session/input paths and a fresh evidence output")
            if args.session_file.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
                raise DriverError("keep the restricted session file outside the repository")
            code = control(args)
            print(json.dumps({"exit_code": code, "scope": "http_control_only", "evidence": str(args.output)}))
            return code
        result = validate_read_chain(read_object(args.input), expected_task_id=args.task_id,
                                     expected_candidate_sha=args.candidate_sha)
        print(json.dumps(result))
        return 0 if result["valid"] else 1
    except (DriverError, OSError, ValueError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 2 if isinstance(error, DriverBlocked) else 1


if __name__ == "__main__":
    raise SystemExit(main())
