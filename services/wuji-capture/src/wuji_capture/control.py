"""Authenticated, path-free control and sealed-item reads for one capture attempt."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import ssl
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .storage import append_fsync, canonical_bytes


_PART = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ITEM_PART = re.compile(r"/v1/items/([1-9][0-9]*)/parts/([a-z][a-z0-9_]{0,63})\Z")


def _utc_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _file_part(root: Path, path: Path, part: str, media_type: str) -> dict:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            length += len(chunk)
            digest.update(chunk)
    return {
        "part": part,
        "media_type": media_type,
        "length": length,
        "sha256": digest.hexdigest(),
        "_path": str(path.relative_to(root)),
    }


class CaptureItemStore:
    def __init__(self, root: Path, *, maximum_items: int, maximum_session_bytes: int,
                 maximum_chunk_bytes: int):
        self.root = root
        self.maximum_items = maximum_items
        self.maximum_session_bytes = maximum_session_bytes
        self.maximum_chunk_bytes = maximum_chunk_bytes
        self.path = root / "control" / "items.ndjson"
        self.items: list[dict] = []
        self.known: set[str] = set()
        self.total_part_bytes = 0
        self.writer_offset = 0
        if self.path.exists():
            with self.path.open("rb") as stream:
                for raw in stream:
                    value = json.loads(raw)
                    if (
                        value.get("schema_version") != "wuji.capture-item.v1"
                        or value.get("item_seq") != len(self.items) + 1
                    ):
                        raise ValueError("capture item index is invalid")
                    self.items.append(value)
                    self.known.add(self._key(value))
                    self.total_part_bytes += sum(part["length"] for part in value["parts"])

    @staticmethod
    def _key(item: dict) -> str:
        return item["_key"]

    def _http_candidates(self) -> list[dict]:
        index = self.root / "http" / "index.ndjson"
        if not index.exists():
            return []
        candidates = []
        with index.open("rb") as stream:
            stream.seek(self.writer_offset)
            while raw := stream.readline():
                next_offset = stream.tell()
                record = json.loads(raw)
                stage = record.get("stage")
                if stage not in {"response", "gap"}:
                    self.writer_offset = next_offset
                    continue
                exchange_id = record.get("exchange_id")
                key = f"http_{stage}:{exchange_id}"
                if key in self.known:
                    self.writer_offset = next_offset
                    continue
                directory = self.root / "http" / "exchanges" / str(exchange_id)
                request = directory / "request.json"
                response = directory / "response.json"
                gap = directory / "gap.json"
                final = response if stage == "response" else gap
                final_document = json.loads(final.read_bytes())
                request_document = json.loads(request.read_bytes()) if request.exists() else {}
                request_metadata = request_document.get("metadata") or {}
                final_metadata = final_document.get("metadata") or {}
                parts = []
                selected = [
                    ("request_metadata", request, "application/json"),
                    ("request_body", directory / "request.body", "application/octet-stream"),
                    (("response_metadata" if stage == "response" else "gap"), final, "application/json"),
                ]
                if stage == "response":
                    selected.append(("response_body", directory / "response.body", "application/octet-stream"))
                for name, path, media in selected:
                    if path.exists():
                        parts.append(_file_part(self.root, path, name, media))
                metadata = final_metadata
                summary = {"exchange_id": str(exchange_id)}
                for field, maximum in (("method", 32), ("url", 2048)):
                    value = request_metadata.get(field)
                    if isinstance(value, str):
                        summary[field] = value[:maximum]
                status_code = final_metadata.get("status_code")
                if type(status_code) is int:
                    summary["status_code"] = status_code
                candidates.append({
                    "_key": key,
                    "_writer_offset": next_offset,
                    "schema_version": "wuji.capture-item.v1",
                    "kind": "gap" if stage == "gap" else "http_exchange",
                    "completeness": metadata.get("completeness", "partial") if stage == "gap" else "complete",
                    "observed_at": final_document["persisted_at"],
                    "parts": parts,
                    "metadata": summary,
                    "conditions": ([str(metadata.get("reason"))] if stage == "gap" and metadata.get("reason") else []),
                })
                break
        return candidates

    def _pcap_candidates(self, *, sealed: bool, pcap_stats: dict | None) -> list[dict]:
        paths = sorted(
            (path for path in (self.root / "pcap").glob("capture.pcap*") if path.is_file()),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
        )
        if not sealed and paths:
            paths = paths[:-1]
        candidates = []
        for path in paths:
            key = "pcap:" + path.name
            if key in self.known:
                continue
            candidates.append({
                "_key": key,
                "schema_version": "wuji.capture-item.v1",
                "kind": "pcap_segment",
                "completeness": (
                    "complete"
                    if pcap_stats is not None and pcap_stats.get("dropped_by_kernel") == 0
                    else "partial"
                ),
                "observed_at": _utc_from_timestamp(path.stat().st_mtime),
                "parts": [_file_part(self.root, path, "pcap", "application/vnd.tcpdump.pcap")],
                "metadata": {"segment_name": path.name, "pcap_stats": pcap_stats},
                "conditions": (
                    []
                    if pcap_stats is not None and pcap_stats.get("dropped_by_kernel") == 0
                    else ["pcap_drop_metrics_unavailable_or_nonzero"]
                ),
            })
        return candidates

    def _manifest_candidate(self) -> list[dict]:
        path = self.root / "manifest.json"
        if not path.exists() or "manifest" in self.known:
            return []
        document = json.loads(path.read_bytes())
        return [{
            "_key": "manifest",
            "schema_version": "wuji.capture-item.v1",
            "kind": "manifest",
            "completeness": document.get("completeness", "unknown"),
            "observed_at": document["sealed_at"],
            "parts": [_file_part(self.root, path, "manifest", "application/json")],
            "metadata": {},
            "conditions": list(document.get("reasons") or []),
        }]

    def _append_item(self, item: dict) -> None:
        if self._key(item) in self.known:
            return
        if len(self.items) >= self.maximum_items:
            raise ValueError("capture item limit exceeded")
        item_bytes = sum(part["length"] for part in item["parts"])
        if self.total_part_bytes + item_bytes > self.maximum_session_bytes:
            raise ValueError("capture session byte limit exceeded")
        item["item_seq"] = len(self.items) + 1
        public = self._public(item)
        item["content_digest"] = hashlib.sha256(canonical_bytes(public)).hexdigest()
        append_fsync(self.path, canonical_bytes(item) + b"\n")
        self.items.append(item)
        self.known.add(self._key(item))
        self.total_part_bytes += item_bytes
        if "_writer_offset" in item:
            self.writer_offset = item["_writer_offset"]

    def refresh(self, *, sealed: bool, pcap_stats: dict | None) -> None:
        while candidates := self._http_candidates():
            self._append_item(candidates[0])
        for item in self._pcap_candidates(sealed=sealed, pcap_stats=pcap_stats):
            self._append_item(item)
        if sealed:
            for item in self._manifest_candidate():
                self._append_item(item)

    @staticmethod
    def _public(item: dict) -> dict:
        return {
            key: ([{field: value for field, value in part.items() if field != "_path"}
                   for part in value] if key == "parts" else value)
            for key, value in item.items()
            if not key.startswith("_")
        }

    def page(self, *, after: int, limit: int) -> dict:
        if after < 0 or not 1 <= limit <= 256:
            raise ValueError("invalid item page")
        values = [self._public(item) for item in self.items[after:after + limit]]
        latest = self.items[-1]["item_seq"] if self.items else 0
        return {
            "schema_version": "wuji.capture-item-page.v1",
            "items": values,
            "latest_item_seq": latest,
        }

    def read_part(self, item_seq: int, part_name: str, *, offset: int, length: int) -> tuple[dict, bytes]:
        if not _PART.fullmatch(part_name) or offset < 0 or not 1 <= length <= self.maximum_chunk_bytes:
            raise ValueError("invalid part range")
        item = self.items[item_seq - 1] if item_seq <= len(self.items) else None
        part = None if item is None else next(
            (part for part in item["parts"] if part["part"] == part_name), None
        )
        if part is None or offset >= part["length"]:
            raise KeyError("capture part not found")
        path = (self.root / part["_path"]).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise KeyError("capture part not found")
        with path.open("rb") as stream:
            stream.seek(offset)
            body = stream.read(min(length, part["length"] - offset))
        return {
            **{key: value for key, value in part.items() if key != "_path"},
            "offset": offset,
            "end": offset + len(body),
            "chunk_sha256": hashlib.sha256(body).hexdigest(),
        }, body


class _ControlHandler(BaseHTTPRequestHandler):
    server_version = "wuji-capture-control"
    protocol_version = "HTTP/1.1"

    @property
    def control(self):
        return self.server.control  # type: ignore[attr-defined]

    def _authorized(self) -> bool:
        certificate = self.connection.getpeercert(binary_form=True)
        digest = hashlib.sha256(certificate or b"").hexdigest()
        return hmac.compare_digest(digest, self.control.client_fingerprint)

    def _json(self, status: HTTPStatus, value: dict) -> None:
        body = canonical_bytes(value) + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: HTTPStatus, code: str) -> None:
        self._json(status, {"schema_version": "wuji.capture-control-error.v1", "code": code})

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._error(HTTPStatus.FORBIDDEN, "client_certificate_mismatch")
            return
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/v1/status":
                self._json(HTTPStatus.OK, self.control.status())
                return
            if parsed.path == "/v1/items":
                query = parse_qs(parsed.query, strict_parsing=True)
                after = int(query.get("after", ["0"])[0])
                limit = int(query.get("limit", ["100"])[0])
                self._json(HTTPStatus.OK, self.control.items(after=after, limit=limit))
                return
            match = _ITEM_PART.fullmatch(parsed.path)
            if match is not None:
                query = parse_qs(parsed.query, strict_parsing=True)
                offset = int(query.get("offset", ["0"])[0])
                length = int(query.get("length", ["0"])[0])
                metadata, body = self.control.part(
                    int(match.group(1)), match.group(2), offset=offset, length=length
                )
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", metadata["media_type"])
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Range", f"bytes {metadata['offset']}-{metadata['end'] - 1}/{metadata['length']}")
                self.send_header("X-Wuji-Part-SHA256", metadata["sha256"])
                self.send_header("X-Wuji-Chunk-SHA256", metadata["chunk_sha256"])
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                return
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "capture_part_not_found")
            return
        except (TypeError, ValueError):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_capture_request")
            return
        self._error(HTTPStatus.NOT_FOUND, "not_found")

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._error(HTTPStatus.FORBIDDEN, "client_certificate_mismatch")
            return
        if self.headers.get("Content-Length", "0") != "0":
            self._error(HTTPStatus.BAD_REQUEST, "request_body_not_allowed")
            return
        parsed = urlsplit(self.path)
        if parsed.query:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_capture_request")
            return
        if parsed.path == "/v1/drain":
            self._json(HTTPStatus.OK, self.control.drain())
        elif parsed.path == "/v1/seal":
            self._json(HTTPStatus.OK, self.control.seal())
        else:
            self._error(HTTPStatus.NOT_FOUND, "not_found")

    def log_message(self, _format: str, *_args) -> None:
        return


class CaptureControlServer:
    def __init__(self, supervisor, *, host: str, port: int, certificate: str, private_key: str,
                 client_ca: str, client_fingerprint: str):
        self.supervisor = supervisor
        self.client_fingerprint = client_fingerprint
        self.server = ThreadingHTTPServer((host, port), _ControlHandler)
        self.server.control = self  # type: ignore[attr-defined]
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certificate, private_key)
        context.load_verify_locations(cafile=client_ca)
        context.verify_mode = ssl.CERT_REQUIRED
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def status(self) -> dict:
        return self.supervisor.control_status()

    def items(self, *, after: int, limit: int) -> dict:
        return self.supervisor.control_items(after=after, limit=limit)

    def part(self, item_seq: int, part: str, *, offset: int, length: int):
        return self.supervisor.control_part(item_seq, part, offset=offset, length=length)

    def drain(self) -> dict:
        return self.supervisor.control_drain()

    def seal(self) -> dict:
        return self.supervisor.control_seal()
