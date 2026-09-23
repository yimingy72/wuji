"""Dedicated fsync writer for finite HTTP exchanges."""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import socket
from pathlib import Path
from typing import Any

from .protocol import WriterUnavailable, receive_frame, send_frame
from .storage import (
    append_fsync,
    atomic_write,
    canonical_bytes,
    checked_name,
    sha256_bytes,
    utc_now,
    write_fault,
)


class DurableWriter:
    def __init__(
        self,
        root: Path,
        *,
        maximum_request_body_bytes: int,
        maximum_response_body_bytes: int,
        maximum_session_bytes: int,
        maximum_items: int,
        fail_after: int | None = None,
    ):
        self.root = root
        self.maximum_request_body_bytes = maximum_request_body_bytes
        self.maximum_response_body_bytes = maximum_response_body_bytes
        self.maximum_session_bytes = maximum_session_bytes
        self.maximum_items = maximum_items
        self.fail_after = fail_after
        self.operations = 0
        self.index = root / "index.ndjson"
        self.indexed = self._read_index()

    def _read_index(self) -> set[tuple[str, str]]:
        result: set[tuple[str, str]] = set()
        if not self.index.exists():
            return result
        with self.index.open("rb") as stream:
            for raw in stream:
                try:
                    item = json.loads(raw)
                    result.add((item["exchange_id"], item["stage"]))
                except (json.JSONDecodeError, KeyError, TypeError):
                    break
        return result

    def _body(self, value: object, stage: str) -> bytes:
        if not isinstance(value, str):
            raise ValueError("body_base64 must be a string")
        try:
            body = base64.b64decode(value, validate=True)
        except ValueError as error:
            raise ValueError("invalid body_base64") from error
        maximum = (
            self.maximum_request_body_bytes
            if stage == "request"
            else self.maximum_response_body_bytes
        )
        if len(body) > maximum:
            raise ValueError("body exceeds the finite capture limit")
        return body

    def _record(self, value: dict[str, Any]) -> dict[str, Any]:
        exchange_id = checked_name(value.get("exchange_id"), "exchange_id")
        stage = value.get("stage")
        if stage not in {"request", "response", "gap"}:
            raise ValueError("invalid capture stage")
        metadata = value.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        body = b"" if stage == "gap" else self._body(value.get("body_base64"), stage)
        core = {
            "schema_version": "wuji.http-capture-record.v1",
            "exchange_id": exchange_id,
            "stage": stage,
            "metadata": metadata,
            "body_length": len(body),
            "body_sha256": sha256_bytes(body),
        }
        digest = sha256_bytes(canonical_bytes(core))
        document = {**core, "record_digest": digest, "persisted_at": utc_now()}
        directory = self.root / "exchanges" / exchange_id
        metadata_path = directory / f"{stage}.json"
        body_path = directory / f"{stage}.body"
        key = (exchange_id, stage)

        if key not in self.indexed:
            exchanges = {indexed_exchange for indexed_exchange, _ in self.indexed}
            if exchange_id not in exchanges and len(exchanges) >= self.maximum_items:
                raise ValueError("capture item limit exceeded")
            current_bytes = sum(
                path.stat().st_size
                for path in self.root.glob("exchanges/*/*.body")
                if path.is_file()
            )
            existing_bytes = body_path.stat().st_size if body_path.exists() else 0
            if current_bytes - existing_bytes + len(body) > self.maximum_session_bytes:
                raise ValueError("capture session byte limit exceeded")

        if metadata_path.exists():
            existing = json.loads(metadata_path.read_bytes())
            if existing.get("record_digest") != digest:
                raise ValueError("capture stage replay changed content")
        else:
            if stage != "gap":
                atomic_write(body_path, body)
            atomic_write(metadata_path, canonical_bytes(document) + b"\n")

        if key not in self.indexed:
            index_item = {
                "exchange_id": exchange_id,
                "stage": stage,
                "record_digest": digest,
                "metadata_path": str(metadata_path.relative_to(self.root)),
                "body_path": None if stage == "gap" else str(body_path.relative_to(self.root)),
                "persisted_at": document["persisted_at"],
            }
            append_fsync(self.index, canonical_bytes(index_item) + b"\n")
            self.indexed.add(key)
        return {"record_digest": digest, "body_length": len(body)}

    def handle(self, value: dict[str, Any]) -> dict[str, Any]:
        operation = value.get("op")
        if operation == "ping":
            probe = canonical_bytes({"checked_at": utc_now(), "pid": os.getpid()}) + b"\n"
            atomic_write(self.root / "health" / "writer-probe.json", probe)
            return {"ok": True, "status": "ready"}
        if operation in {"status", "seal"}:
            exchanges: dict[str, set[str]] = {}
            for exchange_id, stage in self.indexed:
                exchanges.setdefault(exchange_id, set()).add(stage)
            pending = sorted(
                exchange_id
                for exchange_id, stages in exchanges.items()
                if "request" in stages and not stages.intersection({"response", "gap"})
            )
            gap_count = sum("gap" in stages for stages in exchanges.values())
            summary = {
                "schema_version": "wuji.capture-writer-seal.v1",
                "record_count": len(self.indexed),
                "exchange_count": len(exchanges),
                "pending_exchange_count": len(pending),
                "pending_exchange_ids": pending,
                "gap_exchange_count": gap_count,
                "completeness": "partial" if pending or gap_count else "complete",
                "index_sha256": sha256_bytes(self.index.read_bytes()) if self.index.exists() else sha256_bytes(b""),
            }
            if operation == "seal":
                summary["sealed_at"] = utc_now()
                atomic_write(self.root / "writer-seal.json", canonical_bytes(summary) + b"\n")
            return {"ok": True, **summary}
        if operation != "record":
            raise ValueError("unsupported writer operation")
        self.operations += 1
        if self.fail_after is not None and self.operations > self.fail_after:
            raise OSError("injected durable writer failure")
        return {"ok": True, **self._record(value)}


def serve(
    socket_path: Path,
    root: Path,
    fault_path: Path,
    maximum_request_body_bytes: int,
    maximum_response_body_bytes: int,
    maximum_session_bytes: int,
    maximum_items: int,
) -> int:
    fail_raw = os.environ.get("WUJI_CAPTURE_WRITER_FAIL_AFTER")
    fail_after = int(fail_raw) if fail_raw is not None else None
    writer = DurableWriter(
        root,
        maximum_request_body_bytes=maximum_request_body_bytes,
        maximum_response_body_bytes=maximum_response_body_bytes,
        maximum_session_bytes=maximum_session_bytes,
        maximum_items=maximum_items,
        fail_after=fail_after,
    )
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(socket_path))
        os.chmod(socket_path, 0o660)
        listener.listen(16)
        listener.settimeout(0.25)
        while not stopping:
            try:
                stream, _ = listener.accept()
            except TimeoutError:
                continue
            with stream:
                stream.settimeout(10)
                try:
                    response = writer.handle(receive_frame(stream))
                    send_frame(stream, response)
                except (OSError, ValueError, WriterUnavailable) as error:
                    write_fault(fault_path, component="writer", reason=str(error))
                    try:
                        send_frame(stream, {"ok": False, "error": "durable writer failed"})
                    except OSError:
                        pass
                    return 70
    socket_path.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--fault-file", type=Path, required=True)
    parser.add_argument("--maximum-request-body-bytes", type=int, required=True)
    parser.add_argument("--maximum-response-body-bytes", type=int, required=True)
    parser.add_argument("--maximum-session-bytes", type=int, required=True)
    parser.add_argument("--maximum-items", type=int, required=True)
    args = parser.parse_args()
    if any(
        value < 1
        for value in (
            args.maximum_request_body_bytes,
            args.maximum_response_body_bytes,
            args.maximum_session_bytes,
            args.maximum_items,
        )
    ):
        parser.error("capture limits must be positive")
    return serve(
        args.socket,
        args.root,
        args.fault_file,
        args.maximum_request_body_bytes,
        args.maximum_response_body_bytes,
        args.maximum_session_bytes,
        args.maximum_items,
    )


if __name__ == "__main__":
    raise SystemExit(main())
