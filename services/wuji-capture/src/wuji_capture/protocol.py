"""Small local protocol between the proxy addon and durable writer."""

from __future__ import annotations

import json
import socket
import struct
from pathlib import Path
from typing import Any


MAX_FRAME_BYTES = 64 * 1024 * 1024


class WriterUnavailable(RuntimeError):
    pass


def _read_exact(stream: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.recv(remaining)
        if not chunk:
            raise WriterUnavailable("writer closed the local connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_frame(stream: socket.socket, *, maximum: int = MAX_FRAME_BYTES) -> dict[str, Any]:
    length = struct.unpack("!I", _read_exact(stream, 4))[0]
    if length < 2 or length > maximum:
        raise WriterUnavailable("invalid writer frame length")
    try:
        value = json.loads(_read_exact(stream, length))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WriterUnavailable("invalid writer frame") from error
    if not isinstance(value, dict):
        raise WriterUnavailable("writer frame must be an object")
    return value


def send_frame(stream: socket.socket, value: dict[str, Any]) -> None:
    encoded = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(encoded) > MAX_FRAME_BYTES:
        raise WriterUnavailable("writer frame is too large")
    stream.sendall(struct.pack("!I", len(encoded)) + encoded)


def request(socket_path: str | Path, value: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
            stream.settimeout(timeout)
            stream.connect(str(socket_path))
            send_frame(stream, value)
            response = receive_frame(stream, maximum=1024 * 1024)
    except (OSError, WriterUnavailable) as error:
        raise WriterUnavailable("durable writer unavailable") from error
    if response.get("ok") is not True:
        raise WriterUnavailable(str(response.get("error") or "durable writer rejected record"))
    return response
