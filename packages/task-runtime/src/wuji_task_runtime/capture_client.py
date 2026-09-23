"""Bounded mTLS client for the Task-local capture control endpoint."""

from __future__ import annotations

import hashlib
import http.client
import json
import ssl
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .errors import RuntimeStateUnknown, RuntimeTransportError


class CaptureControlClient:
    def __init__(
        self,
        base_url: str,
        *,
        ca_file: str,
        certificate_file: str,
        private_key_file: str,
        expected_binding: dict[str, object],
        timeout_seconds: float = 5,
        maximum_json_bytes: int = 1024 * 1024,
        maximum_chunk_bytes: int = 8 * 1024 * 1024,
    ):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("capture control requires a fixed HTTPS origin")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("capture control timeout must be positive")
        if type(maximum_json_bytes) is not int or not 1 <= maximum_json_bytes <= 16 * 1024 * 1024:
            raise ValueError("capture JSON limit is invalid")
        if type(maximum_chunk_bytes) is not int or not 1 <= maximum_chunk_bytes <= 8 * 1024 * 1024:
            raise ValueError("capture chunk limit is invalid")
        required_binding = {"task_id", "runtime_attempt", "execution_epoch", "pod_uid"}
        if set(expected_binding) != required_binding or expected_binding["pod_uid"] is not None:
            raise ValueError("capture binding is incomplete")
        for path in (ca_file, certificate_file, private_key_file):
            if not Path(path).is_absolute():
                raise ValueError("capture TLS paths must be absolute")
        context = ssl.create_default_context(cafile=ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certificate_file, private_key_file)
        self.host = parsed.hostname
        self.port = parsed.port or 443
        self.context = context
        self.expected_binding = dict(expected_binding)
        self.timeout = float(timeout_seconds)
        self.maximum_json_bytes = maximum_json_bytes
        self.maximum_chunk_bytes = maximum_chunk_bytes

    def bind_pod_uid(self, pod_uid: str) -> None:
        if not isinstance(pod_uid, str) or not pod_uid:
            raise ValueError("observed Pod UID is required")
        current = self.expected_binding["pod_uid"]
        if current not in {None, pod_uid}:
            raise RuntimeStateUnknown("capture-pod-uid-changed")
        self.expected_binding["pod_uid"] = pod_uid

    def _request(
        self, method: str, path: str, *, timeout_seconds: float | None = None
    ) -> tuple[http.client.HTTPResponse, bytes]:
        timeout = self.timeout if timeout_seconds is None else min(self.timeout, timeout_seconds)
        if timeout <= 0:
            raise RuntimeTransportError("capture-control-deadline")
        connection = http.client.HTTPSConnection(
            self.host, self.port, context=self.context, timeout=timeout
        )
        deadline = time.monotonic() + timeout

        def remaining() -> float:
            value = deadline - time.monotonic()
            if value <= 0:
                raise RuntimeTransportError("capture-control-deadline")
            return value

        try:
            connection.request(method, path, body=None, headers={"Accept": "application/json"})
            if connection.sock is not None:
                connection.sock.settimeout(remaining())
            response = connection.getresponse()
            maximum = self.maximum_chunk_bytes if "/parts/" in path else self.maximum_json_bytes
            body = bytearray()
            while len(body) <= maximum:
                if response.fp is None:
                    break
                # getresponse() may release connection.sock for Connection: close;
                # the response still owns the same socket while reading its body.
                sock = connection.sock or response.fp.raw._sock
                sock.settimeout(remaining())
                chunk = response.read(min(65536, maximum + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            if len(body) > maximum:
                raise RuntimeTransportError("capture-response-too-large")
            return response, bytes(body)
        except RuntimeTransportError:
            raise
        except ssl.SSLError:
            raise RuntimeTransportError("capture-control-tls") from None
        except TimeoutError:
            raise RuntimeTransportError("capture-control-timeout") from None
        except OSError:
            raise RuntimeTransportError("capture-control-connect") from None
        except Exception:
            raise RuntimeTransportError("capture-control") from None
        finally:
            connection.close()

    def _json(
        self, method: str, path: str, *, timeout_seconds: float | None = None
    ) -> dict:
        response, body = self._request(
            method, path, timeout_seconds=timeout_seconds
        )
        if response.status != 200:
            raise RuntimeStateUnknown("capture-control-status", response.status)
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeTransportError("capture-control-json") from None
        if not isinstance(value, dict):
            raise RuntimeTransportError("capture-control-json")
        binding = value.get("binding")
        if self.expected_binding["pod_uid"] is None or binding != self.expected_binding:
            raise RuntimeStateUnknown("capture-binding-mismatch")
        return value

    def status(self) -> dict:
        return self._json("GET", "/v1/status")

    def items(
        self, *, after: int, limit: int = 100,
        timeout_seconds: float | None = None,
    ) -> dict:
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError("capture page is invalid")
        return self._json(
            "GET", "/v1/items?" + urlencode({"after": after, "limit": limit}),
            timeout_seconds=timeout_seconds,
        )

    def drain(self, *, timeout_seconds: float | None = None) -> dict:
        return self._json("POST", "/v1/drain", timeout_seconds=timeout_seconds)

    def seal(self, *, timeout_seconds: float | None = None) -> dict:
        return self._json("POST", "/v1/seal", timeout_seconds=timeout_seconds)

    def read_part(
        self, item_seq: int, part: dict, *, offset: int,
        timeout_seconds: float | None = None,
    ) -> bytes:
        if (
            type(item_seq) is not int or item_seq < 1
            or not isinstance(part, dict)
            or set(part) != {"part", "media_type", "length", "sha256"}
            or not isinstance(part.get("part"), str)
            or not isinstance(part.get("media_type"), str)
            or type(part.get("length")) is not int
            or part["length"] < 0
            or not isinstance(part.get("sha256"), str)
            or len(part["sha256"]) != 64
            or type(offset) is not int or offset < 0 or offset >= part["length"]
        ):
            raise ValueError("capture part request is invalid")
        length = min(self.maximum_chunk_bytes, part["length"] - offset)
        path = (
            f"/v1/items/{item_seq}/parts/{part['part']}?"
            + urlencode({"offset": offset, "length": length})
        )
        response, body = self._request("GET", path, timeout_seconds=timeout_seconds)
        if response.status != 206:
            raise RuntimeStateUnknown("capture-part-status", response.status)
        expected_range = f"bytes {offset}-{offset + len(body) - 1}/{part['length']}"
        if (
            response.getheader("Content-Range") != expected_range
            or response.getheader("X-Wuji-Part-SHA256") != part["sha256"]
            or response.getheader("X-Wuji-Chunk-SHA256") != hashlib.sha256(body).hexdigest()
            or len(body) != length
        ):
            raise RuntimeStateUnknown("capture-part-mismatch")
        return body
