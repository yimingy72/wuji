"""Bounded client for the Gate-owned Task process cleanup sequence."""

from __future__ import annotations

import http.client
import json
import ssl
import time
from pathlib import Path
from urllib.parse import urlsplit

from .errors import RuntimeStateUnknown, RuntimeTransportError


class ProcessCleanupClient:
    def __init__(
        self,
        base_url: str,
        *,
        ca_file: str,
        bearer_token,
        timeout_seconds: float = 45,
        maximum_json_bytes: int = 1024 * 1024,
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
            or not Path(ca_file).is_absolute()
            or not callable(bearer_token)
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 60
            or type(maximum_json_bytes) is not int
            or not 1 <= maximum_json_bytes <= 1024 * 1024
        ):
            raise ValueError("bounded verified process cleanup endpoint required")
        self.host, self.port = parsed.hostname, parsed.port or 443
        self.context = ssl.create_default_context(cafile=ca_file)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.bearer_token = bearer_token
        self.timeout = float(timeout_seconds)
        self.maximum_json_bytes = maximum_json_bytes

    def cleanup(
        self,
        *,
        task_id: str,
        execution_epoch: int,
        runtime_attempt: int,
        reason: str,
        timeout_seconds: float | None = None,
    ) -> dict:
        if (
            timeout_seconds is not None
            and (
                isinstance(timeout_seconds, bool)
                or not isinstance(timeout_seconds, (int, float))
            )
        ):
            raise ValueError("process cleanup timeout must be numeric")
        payload = {
            "task_id": task_id,
            "execution_epoch": str(execution_epoch),
            "runtime_attempt": str(runtime_attempt),
            "reason": reason,
        }
        token = self.bearer_token()
        if (
            not isinstance(token, str)
            or not token
            or not token.isascii()
            or any(character.isspace() for character in token)
        ):
            raise RuntimeTransportError("process-cleanup-credential")
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        timeout = self.timeout if timeout_seconds is None else min(
            self.timeout, float(timeout_seconds)
        )
        if timeout <= 0:
            raise RuntimeTransportError("process-cleanup-deadline")
        deadline = time.monotonic() + timeout

        def remaining() -> float:
            value = deadline - time.monotonic()
            if value <= 0:
                raise RuntimeTransportError("process-cleanup-deadline")
            return value

        connection = http.client.HTTPSConnection(
            self.host, self.port, context=self.context, timeout=timeout
        )
        try:
            connection.request(
                "POST",
                "/internal/v2/process-control/cleanup",
                body=body,
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if connection.sock is not None:
                connection.sock.settimeout(remaining())
            response = connection.getresponse()
            raw = bytearray()
            while len(raw) <= self.maximum_json_bytes:
                if response.fp is None:
                    break
                sock = connection.sock or response.fp.raw._sock
                sock.settimeout(remaining())
                chunk = response.read(min(65536, self.maximum_json_bytes + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
        except RuntimeTransportError:
            raise
        except Exception:
            raise RuntimeTransportError("process-cleanup") from None
        finally:
            connection.close()
        if len(raw) > self.maximum_json_bytes:
            raise RuntimeTransportError("process-cleanup-response-too-large")
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeTransportError("process-cleanup-json") from None
        if response.status != 200 or not isinstance(value, dict):
            raise RuntimeStateUnknown("process-cleanup-status", response.status)
        expected = {
            "schema_version", "status", "task_id", "execution_epoch", "runtime_attempt",
            "drain_status", "archive_status", "archived_processes",
            "unresolved_processes", "shutdown_status", "container_exit_confirmed",
        }
        if (
            set(value) != expected
            or value["status"] != "accepted"
            or value["task_id"] != task_id
            or value["execution_epoch"] != str(execution_epoch)
            or value["runtime_attempt"] != str(runtime_attempt)
            or value["drain_status"] not in {"drained", "unknown"}
            or value["archive_status"] not in {"complete", "incomplete"}
            or value["shutdown_status"] != "accepted"
            or value["container_exit_confirmed"] is not False
            or type(value["archived_processes"]) is not int
            or type(value["unresolved_processes"]) is not int
        ):
            raise RuntimeStateUnknown("process-cleanup-binding")
        return value
