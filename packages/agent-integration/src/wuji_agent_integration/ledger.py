"""Small persistent attempt ledger with process-safe reservations."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class AttemptLimitExceeded(RuntimeError):
    pass


class LedgerError(RuntimeError):
    pass


def _unknown_usage() -> dict[str, str]:
    return {"input_tokens": "unknown", "output_tokens": "unknown", "total_tokens": "unknown"}


class CallLedger:
    """Atomically reserve every upstream attempt before the SDK is invoked."""

    def __init__(self, path: str, *, max_total_attempts: int = 4) -> None:
        if not 1 <= max_total_attempts <= 4:
            raise ValueError("max_total_attempts must be between 1 and 4")
        self.path = Path(path)
        self.max_total_attempts = max_total_attempts

    def reserve(self, *, run_id: str, protocol: str, requested_model: str, sequence: int) -> str:
        attempt_id = str(uuid4())

        def mutate(document: dict[str, Any]) -> None:
            attempts = document["attempts"]
            if len(attempts) >= self.max_total_attempts:
                raise AttemptLimitExceeded("shared upstream attempt limit has been reached")
            local = [item for item in attempts if item.get("protocol") == protocol]
            if len(local) >= 2 or sequence > 2:
                raise AttemptLimitExceeded("protocol probe attempt limit has been reached")
            attempts.append(
                {
                    "attempt_id": attempt_id,
                    "run_id": run_id,
                    "purpose": "organization_model_configuration_check",
                    "protocol": protocol,
                    "requested_model": requested_model,
                    "sequence": sequence,
                    "reserved_at": datetime.now(UTC).isoformat(),
                    "status": "started",
                    "actual_model": "unknown",
                    "finish_reason": "unknown",
                    "usage": _unknown_usage(),
                }
            )

        self._mutate(mutate)
        return attempt_id

    def complete(self, attempt_id: str, result: dict[str, Any]) -> None:
        def mutate(document: dict[str, Any]) -> None:
            entry = next((item for item in document["attempts"] if item.get("attempt_id") == attempt_id), None)
            if entry is None:
                raise LedgerError("reserved attempt was not found")
            entry.update(
                {
                    "completed_at": datetime.now(UTC).isoformat(),
                    "status": "completed",
                    "actual_model": result.get("actual_model", "unknown"),
                    "finish_reason": result.get("finish_reason", "unknown"),
                    "usage": result.get("usage", _unknown_usage()),
                    "tool_call_ids": result.get("tool_call_ids", []),
                }
            )

        self._mutate(mutate)

    def mark_unknown(self, attempt_id: str, error_code: str) -> None:
        def mutate(document: dict[str, Any]) -> None:
            entry = next((item for item in document["attempts"] if item.get("attempt_id") == attempt_id), None)
            if entry is None:
                raise LedgerError("reserved attempt was not found")
            entry.update(
                {
                    "completed_at": datetime.now(UTC).isoformat(),
                    "status": "unknown",
                    "error_code": error_code,
                }
            )

        self._mutate(mutate)

    def snapshot_for_run(self, run_id: str) -> list[dict[str, Any]]:
        document = self._read()
        return [dict(item) for item in document["attempts"] if item.get("run_id") == run_id]

    def _read(self) -> dict[str, Any]:
        return self._with_locked_file(None)

    def _mutate(self, callback: Any) -> None:
        self._with_locked_file(callback)

    def _with_locked_file(self, callback: Any) -> dict[str, Any]:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        os.chmod(self.path, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            raw = os.read(descriptor, 2_000_001)
            if len(raw) > 2_000_000:
                raise LedgerError("ledger is too large")
            if raw:
                try:
                    document = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise LedgerError("ledger is not valid JSON") from exc
            else:
                document = {"schema_version": 1, "attempts": []}
            if (
                not isinstance(document, dict)
                or document.get("schema_version") != 1
                or not isinstance(document.get("attempts"), list)
            ):
                raise LedgerError("ledger schema is invalid")
            if callback is not None:
                callback(document)
                encoded = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.write(descriptor, encoded)
                os.ftruncate(descriptor, len(encoded))
                os.fsync(descriptor)
            return document
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
