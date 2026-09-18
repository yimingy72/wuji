"""A closed HTTP peer for the first-use F1/F2 mechanism checks.

The peer has no outbound network path and never contacts a model provider.  It
exists to make the two important observations deterministic while the real
Wuji chain is assembled around it:

* F1 returns a one-time marker and Chinese text.  The source endpoint accepts
  only that marker and records the complete exchange.
* F2 has two variants.  Each entry points at a different, approved read path;
  the other path is deliberately unavailable.  A test can therefore prove
  that a later choice was based on the entry material rather than a fixed
  answer.

The ``/model/requests`` sink is intentionally a capture-only endpoint for
mechanism tests.  It is not MAF, a gateway, or a model-effectiveness test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
from threading import Lock, Thread
from time import time
from typing import Any
from urllib.parse import parse_qs, urlsplit


SCHEMA_VERSION = "wuji.first-use.fixture.v1"
F1_MESSAGE = "首用夹具 F1：请读取实际来源，并保留这段中文材料。"
F2_MESSAGE = "首用夹具 F2：请依据入口文档决定下一条已批准的安全读取路径。"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _header_pairs(handler: BaseHTTPRequestHandler) -> list[list[str]]:
    return [[name, value] for name, value in handler.headers.raw_items()]


@dataclass
class Exchange:
    exchange_id: str
    received_at: float
    method: str
    path: str
    query: dict[str, list[str]]
    request_headers: list[list[str]]
    request_body: str
    response_status: int
    response_headers: list[list[str]]
    response_body: str

    def as_dict(self) -> dict[str, Any]:
        request_line = self.method + " " + self.path
        if self.query:
            encoded = "&".join(
                f"{key}={value}"
                for key, values in sorted(self.query.items())
                for value in values
            )
            request_line += "?" + encoded
        response_reason = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
        }.get(self.response_status, "Response")
        request_http = (
            request_line
            + " HTTP/1.1\r\n"
            + "".join(f"{key}: {value}\r\n" for key, value in self.request_headers)
            + "\r\n"
            + self.request_body
        )
        response_http = (
            f"HTTP/1.1 {self.response_status} {response_reason}\r\n"
            + "".join(f"{key}: {value}\r\n" for key, value in self.response_headers)
            + "\r\n"
            + self.response_body
        )
        return {
            "exchange_id": self.exchange_id,
            "received_at": self.received_at,
            "method": self.method,
            "path": self.path,
            "query": self.query,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "request_http": request_http,
            "response_http": response_http,
        }


@dataclass
class FixtureState:
    """Thread-safe state and full exchange log for one fixture instance."""

    active_marker: str | None = None
    consumed_markers: set[str] = field(default_factory=set)
    exchanges: list[Exchange] = field(default_factory=list)
    _counter: int = 0
    lock: Lock = field(default_factory=Lock, repr=False)

    def next_id(self) -> str:
        with self.lock:
            self._counter += 1
            return f"fx-{self._counter:04d}"

    def set_marker(self, marker: str) -> None:
        with self.lock:
            self.active_marker = marker

    def consume_marker(self, marker: str) -> bool:
        with self.lock:
            if marker != self.active_marker or marker in self.consumed_markers:
                return False
            self.consumed_markers.add(marker)
            return True

    def append(self, exchange: Exchange) -> None:
        with self.lock:
            self.exchanges.append(exchange)

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return [exchange.as_dict() for exchange in self.exchanges]


class _FixtureHandler(BaseHTTPRequestHandler):
    server: "_FixtureHTTPServer"

    def log_message(self, *_args: Any) -> None:
        # Test output should be evidence-controlled, not an unbounded access log.
        return

    @property
    def state(self) -> FixtureState:
        return self.server.state

    def _request_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > 256 * 1024:
            return b""
        return self.rfile.read(length)

    def _reply(
        self,
        status: int,
        payload: Any,
        *,
        request_body: bytes,
        media_type: str = "application/json",
    ) -> None:
        body = payload if isinstance(payload, bytes) else _json_bytes(payload)
        headers = [
            ["Content-Type", media_type],
            ["Content-Length", str(len(body))],
            ["Cache-Control", "no-store"],
            ["Connection", "close"],
        ]
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()
        self.close_connection = True
        self.server.record(
            method=self.command,
            path=urlsplit(self.path).path,
            query=parse_qs(urlsplit(self.path).query, keep_blank_values=True),
            request_headers=_header_pairs(self),
            request_body=request_body.decode("utf-8", "replace"),
            response_status=status,
            response_headers=headers,
            response_body=body.decode("utf-8", "replace"),
        )

    def _route(self, body: bytes) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query, keep_blank_values=True)
        reply = lambda status, payload: self._reply(status, payload, request_body=body)

        if self.command == "GET" and path == "/healthz":
            reply(200, {"schema_version": SCHEMA_VERSION, "status": "ok"})
            return

        if self.command == "GET" and path == "/events":
            exchanges = self.state.snapshot()
            reply(
                200,
                {
                    "schema_version": SCHEMA_VERSION,
                    "exchange_count": len(exchanges),
                    "f1_source_count": sum(
                        item["path"] == "/f1/source" and item["response_status"] == 200
                        for item in exchanges
                    ),
                    "f2_success_count": sum(
                        item["path"].startswith("/f2/")
                        and item["path"].endswith(("/guide-a", "/guide-b"))
                        and item["response_status"] == 200
                        for item in exchanges
                    ),
                    "exchanges": exchanges,
                },
            )
            return

        if self.command == "GET" and path == "/f1/entry":
            marker = "f1-" + secrets.token_hex(12)
            self.state.set_marker(marker)
            reply(
                200,
                {
                    "fixture": "F1",
                    "marker": marker,
                    "message": F1_MESSAGE,
                    "source_path": "/f1/source?marker=" + marker,
                    "one_time": True,
                },
            )
            return

        if self.command == "GET" and path == "/f1/source":
            marker = (query.get("marker") or [""])[0]
            if not self.state.consume_marker(marker):
                reply(
                    409,
                    {"fixture": "F1", "error": "marker_invalid_or_consumed"},
                )
                return
            reply(
                200,
                {
                    "fixture": "F1",
                    "marker": marker,
                    "source": {
                        "media_type": "application/json; charset=utf-8",
                        "text": "{\"service\":\"inventory\",\"mode\":\"observe\",\"version\":\"4.2.0\"}",
                    },
                    "message": F1_MESSAGE,
                },
            )
            return

        if self.command == "POST" and path == "/model/requests":
            try:
                request = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                reply(400, {"error": "request_body_must_be_utf8_json"})
                return
            if not isinstance(request, dict) or request.get("role") not in {"first", "second"}:
                reply(422, {"error": "role_must_be_first_or_second"})
                return
            reply(201, {"accepted": True, "request_id": self.state.next_id()})
            return

        if self.command == "GET" and path.startswith("/f2/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) != 3:
                reply(404, {"error": "unknown_f2_path"})
                return
            _, variant, leaf = parts
            aliases = {"a": "a", "variant-a": "a", "b": "b", "variant-b": "b"}
            normalized = aliases.get(variant)
            if normalized is None:
                reply(404, {"error": "unknown_f2_variant"})
                return
            expected_leaf = "guide-a" if normalized == "a" else "guide-b"
            if leaf == "entry":
                reply(
                    200,
                    {
                        "fixture": "F2",
                        "variant": normalized,
                        "message": F2_MESSAGE,
                        "guide_path": f"/f2/{variant}/{expected_leaf}",
                        "allowed_read": True,
                    },
                )
                return
            if leaf != expected_leaf:
                reply(404, {"fixture": "F2", "error": "guide_not_published"})
                return
            mode = "observe-a" if normalized == "a" else "observe-b"
            reply(
                200,
                {
                    "fixture": "F2",
                    "variant": normalized,
                    "document": {
                        "service": "inventory",
                        "mode": mode,
                        "version": "4.2.0" if normalized == "a" else "4.3.1",
                    },
                    "message": F2_MESSAGE,
                },
            )
            return

        reply(404, {"error": "fixture_route_not_found"})

    def do_GET(self) -> None:
        self._route(b"")

    def do_POST(self) -> None:
        self._route(self._request_body())


class _FixtureHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, state: FixtureState) -> None:
        super().__init__(("127.0.0.1", 0), _FixtureHandler)
        self.state = state

    def record(
        self,
        *,
        method: str,
        path: str,
        query: dict[str, list[str]],
        request_headers: list[list[str]],
        request_body: str,
        response_status: int,
        response_headers: list[list[str]],
        response_body: str,
    ) -> None:
        self.state.append(
            Exchange(
                exchange_id=self.state.next_id(),
                received_at=time(),
                method=method,
                path=path,
                query=query,
                request_headers=request_headers,
                request_body=request_body,
                response_status=response_status,
                response_headers=response_headers,
                response_body=response_body,
            )
        )


class FixtureServer:
    """Context manager for a local-only F1/F2 HTTP fixture."""

    def __init__(self) -> None:
        self.state = FixtureState()
        self.server = _FixtureHTTPServer(self.state)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> "FixtureServer":
        self.thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def exchanges(self) -> list[dict[str, Any]]:
        return self.state.snapshot()

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "evaluation_mode": "mechanism_synthetic",
            "base_url": self.base_url,
            "routes": {
                "health": "/healthz",
                "events": "/events",
                "f1_entry": "/f1/entry",
                "f1_source": "/f1/source?marker=<one-time-marker>",
                "f2_entry_a": "/f2/a/entry",
                "f2_guide_a": "/f2/a/guide-a",
                "f2_entry_b": "/f2/b/entry",
                "f2_guide_b": "/f2/b/guide-b",
                "model_capture": "/model/requests",
            },
            "outbound_network": False,
            "target_persistence": False,
        }
