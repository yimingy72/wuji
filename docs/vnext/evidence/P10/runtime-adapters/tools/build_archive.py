"""Build the publishable C0 archive from local, ignored runtime evidence.

The original files stay under work/. This script records their hashes and emits
only exact non-secret copies or recursively redacted derivatives under docs/.
"""

from __future__ import annotations

import base64
from collections import Counter
from datetime import UTC, datetime
import gzip
from hashlib import sha256
from http import HTTPStatus
import json
from pathlib import Path
import re
import shutil


REPOSITORY = Path(__file__).resolve().parents[6]
ARCHIVE = Path(__file__).resolve().parents[1]

EXACT_FILES = (
    ("work/vnext/c0-sol-first/raw/pytest.txt", "raw/history/collection-missing-task-runtime.txt"),
    ("work/vnext/c0-sol-second/raw/pytest.txt", "raw/history/collection-missing-kubernetes.txt"),
    ("work/vnext/c0-sol-target/raw/pytest.txt", "raw/history/initial-target-3pass-6tls-fail.txt"),
    ("work/vnext/c0-sol-target/raw/pod-collection.txt", "raw/pod/collection.txt"),
    ("work/vnext/c0-sol-remote-r2/raw/pytest.txt", "raw/remote/pytest-7pass.txt"),
    ("work/vnext/c0-sol-remote-r2/raw/default-template-compat.txt", "raw/pod/default-template-compat.txt"),
    ("work/vnext/c0-sol-remote-r2/README.md", "raw/history/prearchive-readme.md"),
    ("work/vnext/c0-sol-remote-r2/screenshots/verification.png", "screenshots/verification.png"),
)

REMOTE_CASES = {
    "main-revocation": "b822a945b704",
    "callback-lost-ack": "382794ef5011",
    "callback-503": "f39b985609cf",
    "callback-bad-ack": "2d7809d2e735",
    "dispatch-not-registered": "917e9296c298",
    "tamper-and-identity": "c42020885ee8",
}

HTTP_FILES = (
    ("main-revocation", "c0-kali-https.jsonl", "kali"),
    ("main-revocation", "c0-platform-https.jsonl", "platform"),
    ("main-revocation", "p06-tool-http-exchanges.jsonl", "gate-p03"),
    ("callback-lost-ack", "c0-platform-https.jsonl", "platform"),
    ("callback-503", "c0-platform-https.jsonl", "platform"),
    ("callback-bad-ack", "c0-platform-https.jsonl", "platform"),
    ("dispatch-not-registered", "c0-kali-https.jsonl", "kali"),
    ("dispatch-not-registered", "c0-platform-https.jsonl", "platform"),
    ("tamper-and-identity", "c0-kali-https.jsonl", "kali"),
    ("tamper-and-identity", "c0-platform-https.jsonl", "platform"),
)

POD_SQL = {
    "current-permit-lease-registration": "4f90f372f2f1",
    "foreign-owner-rejected": "1ec62e5feac8",
}

SENSITIVE_KEYS = {
    "authorization",
    "execution_token",
    "bearer_token",
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "private_key",
    "private_key_pem",
    "private_pem",
    "signing_key",
    "encryption_key",
    "task_key",
    "run_credential",
}
JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PRIVATE_KEY = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
    re.DOTALL,
)
BEARER = re.compile(r"(?i)Bearer\s+([^\s\"']+)")
PASSWORD_ASSIGNMENT = re.compile(r"(?i)(password\s*=\s*)([^\s,;]+)")


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _placeholder(kind: str, value) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"<REDACTED_{kind.upper()} sha256={_hash(data)}>"


def _sanitize_string(value: str, redactions: Counter) -> str:
    stripped = value.strip()
    if stripped[:1] in {"{", "["}:
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        else:
            sanitized = _sanitize(parsed, redactions)
            return json.dumps(sanitized, sort_keys=True, separators=(",", ":"))

    def private(match):
        redactions["private_key"] += 1
        return _placeholder("private_key", match.group(0))

    def jwt(match):
        redactions["jwt"] += 1
        return _placeholder("jwt", match.group(0))

    def bearer(match):
        redactions["bearer"] += 1
        return "Bearer " + _placeholder("bearer", match.group(1))

    def password(match):
        redactions["password"] += 1
        return match.group(1) + _placeholder("password", match.group(2))

    value = PRIVATE_KEY.sub(private, value)
    value = JWT.sub(jwt, value)
    value = BEARER.sub(bearer, value)
    return PASSWORD_ASSIGNMENT.sub(password, value)


def _sanitize(value, redactions: Counter, *, key: str | None = None):
    normalized = key.lower().replace("-", "_") if isinstance(key, str) else None
    if normalized in SENSITIVE_KEYS and value is not None:
        redactions[normalized] += 1
        return _placeholder(normalized, value)
    if isinstance(value, dict):
        return {name: _sanitize(item, redactions, key=name) for name, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, redactions) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value, redactions)
    return value


def _sanitize_http_document(document: dict, redactions: Counter) -> dict:
    result = dict(document)
    for side in ("request", "response"):
        message = dict(result[side])
        headers = dict(message.get("headers") or {})
        for name, value in list(headers.items()):
            headers[name] = _sanitize(value, redactions, key=name)
        message["headers"] = headers
        encoded = message.get("body_base64")
        if encoded is not None:
            raw = base64.b64decode(encoded, validate=True)
            try:
                decoded = raw.decode("utf-8")
            except UnicodeDecodeError:
                sanitized = raw
            else:
                sanitized = _sanitize_string(decoded, redactions).encode("utf-8")
            message["body_base64"] = base64.b64encode(sanitized).decode("ascii")
        result[side] = message
    result["redactions"] = dict(sorted(redactions.items()))
    return result


def _entry(source: Path, destination: Path, transformation: str, redactions: Counter, extra=None):
    source_data = source.read_bytes()
    archived_data = destination.read_bytes()
    value = {
        "source_path": str(source.relative_to(REPOSITORY)),
        "original_sha256": _hash(source_data),
        "original_bytes": len(source_data),
        "archived_path": str(destination.relative_to(ARCHIVE)),
        "archived_sha256": _hash(archived_data),
        "archived_bytes": len(archived_data),
        "transformation": transformation,
        "redactions": dict(sorted(redactions.items())),
    }
    if extra:
        value.update(extra)
    return value


def exact_copy(source_name: str, destination_name: str):
    source, destination = REPOSITORY / source_name, ARCHIVE / destination_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return _entry(source, destination, "exact-copy", Counter())


def sanitize_jsonl(source_name: str, destination_name: str, *, compress: bool = False):
    source, destination = REPOSITORY / source_name, ARCHIVE / destination_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = Counter()
    output = bytearray()
    with source.open(encoding="utf-8") as stream:
        for line in stream:
            line_redactions = Counter()
            value = _sanitize(json.loads(line), line_redactions)
            total.update(line_redactions)
            output.extend(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            output.extend(b"\n")
    if compress:
        destination.write_bytes(gzip.compress(bytes(output), mtime=0))
        extra = {
            "sanitized_uncompressed_sha256": _hash(bytes(output)),
            "sanitized_uncompressed_bytes": len(output),
        }
        transformation = "recursive-redaction+gzip-mtime-0"
    else:
        destination.write_bytes(output)
        extra = None
        transformation = "recursive-redaction"
    return _entry(source, destination, transformation, total, extra)


def sanitize_http(source_name: str, destination_name: str):
    source, destination = REPOSITORY / source_name, ARCHIVE / destination_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = Counter()
    lines = []
    with source.open(encoding="utf-8") as stream:
        for line in stream:
            line_redactions = Counter()
            value = _sanitize_http_document(json.loads(line), line_redactions)
            total.update(line_redactions)
            lines.append(json.dumps(value, sort_keys=True, separators=(",", ":")))
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _entry(source, destination, "decoded-json-recursive-redaction+reencoded-base64", total)


def _body(document: dict) -> str:
    encoded = document.get("body_base64")
    if encoded is None:
        return ""
    raw = base64.b64decode(encoded, validate=True)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "base64:" + encoded


def build_http_reproduction(http_destinations):
    lines = [
        "# C0 runtime adapters · complete redacted HTTP packets",
        "",
        "These packets are decoded from the final captured JSONL files. Method, URL, headers, request body, status, response headers and response body are complete. Authorization/JWT and `execution_token` values are replaced by SHA-256-bearing placeholders; reissue fixture credentials and recalculate Content-Length before replay. No TLS verification setting was relaxed.",
        "",
    ]
    for case, peer, relative in http_destinations:
        path = ARCHIVE / relative
        lines.extend([f"## {case} · {peer}", ""])
        with path.open(encoding="utf-8") as stream:
            for index, line in enumerate(stream, 1):
                exchange = json.loads(line)
                request, response = exchange["request"], exchange["response"]
                lines.extend([f"### Exchange {index}", "", "Request:", "", "```http"])
                lines.append(f"{request['method']} {request['url']} HTTP/1.1")
                lines.extend(f"{name}: {value}" for name, value in sorted(request["headers"].items()))
                lines.extend(["", _body(request), "```", "", "Response:", "", "```http"])
                status = response.get("status_code")
                if status is None:
                    lines.append("NO HTTP RESPONSE (connection closed before ACK)")
                else:
                    try:
                        phrase = HTTPStatus(status).phrase
                    except ValueError:
                        phrase = ""
                    lines.append(f"HTTP/1.1 {status} {phrase}".rstrip())
                    lines.extend(
                        f"{name}: {value}" for name, value in sorted(response["headers"].items())
                    )
                    lines.extend(["", _body(response)])
                lines.extend(["```", ""])
    (ARCHIVE / "http-reproduction.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    entries = [exact_copy(source, destination) for source, destination in EXACT_FILES]
    http_destinations = []
    for case, filename, peer in HTTP_FILES:
        node = REMOTE_CASES[case]
        source = f"work/vnext/c0-sol-remote-r2/raw/{node}/{filename}"
        destination = f"raw/http/{case}/{peer}.jsonl"
        entries.append(sanitize_http(source, destination))
        http_destinations.append((case, peer, destination))
    for case, node in REMOTE_CASES.items():
        entries.append(
            sanitize_jsonl(
                f"work/vnext/c0-sol-remote-r2/raw/{node}/postgres-events.jsonl",
                f"raw/sql/remote-{case}.postgres-events.jsonl.gz",
                compress=True,
            )
        )
        entries.append(
            sanitize_jsonl(
                f"work/vnext/c0-sol-remote-r2/raw/{node}/p06-identity-events.jsonl",
                f"raw/identity/remote-{case}.p06-identity-events.jsonl",
            )
        )
    for case, node in POD_SQL.items():
        entries.append(
            sanitize_jsonl(
                f"work/vnext/c0-sol-target/raw/{node}/postgres-events.jsonl",
                f"raw/sql/pod-{case}.postgres-events.jsonl.gz",
                compress=True,
            )
        )
    build_http_reproduction(http_destinations)
    index = {
        "schema_version": "wuji.c0-runtime-adapters-evidence.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_binding": {
            "test_base_head": "890b54064f370c6e9ace2bc5d92cce2a86a1eefc",
            "code_commit": "d2beac6980aab7959367299f91e4dd2558de9b59",
            "remote_result": "7 passed in 14.81s",
            "pod_result": "2 passed within the initial 3-pass/6-TLS-failure run",
        },
        "policy": {
            "originals": "local ignored work/ files; never staged",
            "publishable_derivative": "recursive credential redaction with per-secret and per-file SHA-256 provenance",
            "private_keys": "not present in captured source set and not copied",
        },
        "files": entries,
    }
    (ARCHIVE / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "files": len(entries),
                "redactions": sum(sum(item["redactions"].values()) for item in entries),
                "index": str((ARCHIVE / "index.json").relative_to(REPOSITORY)),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
