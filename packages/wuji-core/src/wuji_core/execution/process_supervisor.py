"""Bounded Kali process supervisor; every result remains executor-reported."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import select
import signal
import subprocess
from threading import Condition, Event, RLock, Thread
import time

from wuji_core.contracts.generated import ProcessCursorV1, ProcessReplyV1
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError


TRUSTED_NETWORK_ENV = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "CURL_CA_BUNDLE",
)


def _now():
    return datetime.now(timezone.utc)


@dataclass
class _Process:
    handle: str
    process: subprocess.Popen
    pgid: int
    started_at: datetime
    deadline: float
    stdout_path: Path
    stderr_path: Path
    birth_id: str
    output_limit: int
    lock: RLock = field(default_factory=RLock)
    termination_lock: RLock = field(default_factory=RLock)
    changed: Condition = field(init=False)
    stop_requested: Event = field(default_factory=Event)
    output_bytes: int = 0
    truncated: bool = False
    finished_at: datetime | None = None
    streams_open: int = 2

    def __post_init__(self):
        self.changed = Condition(self.lock)


class ProcessSupervisor:
    def __init__(
        self,
        *,
        root,
        spool_root,
        max_active=64,
        max_output_bytes=16 * 1024 * 1024,
        stop_grace_seconds=2.0,
        clock=time.monotonic,
    ):
        self.root = Path(root).resolve()
        self.spool_root = Path(spool_root).resolve()
        if (
            not self.root.is_dir()
            or self.spool_root == self.root
            or self.root in self.spool_root.parents
            or type(max_active) is not int
            or not 1 <= max_active <= 64
            or type(max_output_bytes) is not int
            or max_output_bytes < 1
            or not 0 < float(stop_grace_seconds) <= 60
        ):
            raise ValueError("bounded workspace and external process spool are required")
        self.spool_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.max_active = max_active
        self.max_output_bytes = max_output_bytes
        self.stop_grace_seconds = float(stop_grace_seconds)
        self._clock = clock
        self._lock = RLock()
        self._processes: dict[str, _Process] = {}
        self._shutting_down = Event()
        self._shutdown_complete = Event()
        self._shutdown_callbacks = []

    @staticmethod
    def _key(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        return sha256(value.encode()).hexdigest()

    def _path(self, handle, suffix):
        return self.spool_root / (self._key(handle) + suffix)

    def _atomic_json(self, path, value):
        temporary = path.with_name(path.name + ".tmp-" + os.urandom(8).hex())
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical_json_bytes(value))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(self.spool_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _action(self, action_id, digest_value, operate):
        path = self._path(action_id, ".action.json")
        with self._lock:
            if path.exists():
                value = json.loads(path.read_text())
                if value.get("action_id") != action_id or value.get("digest") != digest_value:
                    raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                if value.get("state") != "complete":
                    return None
                return ProcessReplyV1.model_validate(value["reply"])
            self._atomic_json(
                path,
                {"action_id": action_id, "digest": digest_value, "state": "prepared"},
            )
        try:
            reply = operate()
        except Exception:
            # A replay cannot prove whether the side effect happened after the
            # prepared fence, so it must not perform the action again.
            raise
        with self._lock:
            self._atomic_json(
                path,
                {
                    "action_id": action_id,
                    "digest": digest_value,
                    "state": "complete",
                    "reply": reply.model_dump(mode="json"),
                },
            )
        return reply

    def _cwd(self, value):
        path = self.root if value is None else Path(value)
        path = (self.root / path).resolve() if not path.is_absolute() else path.resolve()
        if path != self.root and self.root not in path.parents:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        if not path.is_dir():
            raise DomainError("INVALID_REFERENCE", 422)
        return path

    def _environment(self):
        environment = {
            "HOME": str(self.root),
            "PATH": os.environ.get(
                "PATH",
                "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            ),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "TERM": os.environ.get("TERM", "dumb"),
        }
        environment.update(
            (name, os.environ[name])
            for name in TRUSTED_NETWORK_ENV
            if name in os.environ
        )
        return environment

    def exec(self, *, action_id, handle, arguments_digest, command, cwd, timeout_seconds):
        def operate():
            if self._shutting_down.is_set():
                raise DomainError("STALE_EXECUTION", 409)
            with self._lock:
                existing = self._processes.get(handle)
                if existing is not None:
                    return self._reply(existing, ProcessCursorV1(stdout_offset=0, stderr_offset=0), 0)
                active = sum(self._refresh(item) != "exited" for item in self._processes.values())
                if active >= self.max_active:
                    raise DomainError("LIMIT_BLOCKED", 429)
                stdout_path = self._path(handle, ".stdout")
                stderr_path = self._path(handle, ".stderr")
                for path in (stdout_path, stderr_path):
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    os.close(fd)
                started = _now()
                process = subprocess.Popen(
                    ["/bin/bash", "--noprofile", "--norc", "-c", command],
                    cwd=self._cwd(cwd),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                    close_fds=True,
                    env=self._environment(),
                )
                os.set_blocking(process.stdin.fileno(), False)
                item = _Process(
                    handle=handle,
                    process=process,
                    pgid=os.getpgid(process.pid),
                    started_at=started,
                    deadline=self._clock() + float(timeout_seconds),
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    birth_id=f"{process.pid}:{time.time_ns()}",
                    output_limit=self.max_output_bytes,
                )
                self._processes[handle] = item
                for stream, path in ((process.stdout, stdout_path), (process.stderr, stderr_path)):
                    Thread(target=self._drain, args=(item, stream, path), daemon=True).start()
                Thread(target=self._monitor, args=(item,), daemon=True).start()
                self._write_process_record(item)
            return self._reply(item, ProcessCursorV1(stdout_offset=0, stderr_offset=0), 0)

        reply = self._action(action_id, arguments_digest, operate)
        if reply is None:
            return self._unknown(handle)
        return reply

    def _drain(self, item, stream, path):
        try:
            with path.open("ab", buffering=0) as target:
                while chunk := stream.read(65536):
                    with item.changed:
                        remaining = max(0, item.output_limit - item.output_bytes)
                        kept = chunk[:remaining]
                        if kept:
                            target.write(kept)
                            item.output_bytes += len(kept)
                        if len(kept) != len(chunk):
                            item.truncated = True
                            item.stop_requested.set()
                        item.changed.notify_all()
        finally:
            with item.changed:
                item.streams_open -= 1
                item.changed.notify_all()

    @staticmethod
    def _group_alive(item):
        try:
            os.killpg(item.pgid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _terminate(self, item):
        with item.termination_lock:
            try:
                os.killpg(item.pgid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                return
            deadline = self._clock() + self.stop_grace_seconds
            while self._group_alive(item) and self._clock() < deadline:
                time.sleep(min(0.02, max(0, deadline - self._clock())))
            if self._group_alive(item):
                try:
                    os.killpg(item.pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def _monitor(self, item):
        while True:
            with item.changed:
                if item.process.poll() is not None and item.streams_open == 0:
                    break
            if item.stop_requested.wait(timeout=min(0.1, max(0.01, item.deadline - self._clock()))):
                self._terminate(item)
            if self._clock() >= item.deadline:
                item.truncated = True
                self._terminate(item)
        item.process.wait()
        with item.changed:
            item.finished_at = item.finished_at or _now()
            item.changed.notify_all()
        self._write_process_record(item)

    def _write_process_record(self, item):
        code = item.process.poll()
        self._atomic_json(
            self._path(item.handle, ".process.json"),
            {
                "handle": item.handle,
                "pid": item.process.pid,
                "pgid": item.pgid,
                "birth_id": item.birth_id,
                "started_at": item.started_at.isoformat(),
                "finished_at": None if item.finished_at is None else item.finished_at.isoformat(),
                "exit_code": code if code is not None and code >= 0 else None,
                "signal": -code if code is not None and code < 0 else None,
                "truncated": item.truncated,
            },
        )

    def _find(self, handle):
        with self._lock:
            item = self._processes.get(handle)
        if item is None:
            record = self._path(handle, ".process.json")
            if record.exists():
                return None
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        return item

    def _refresh(self, item):
        code = item.process.poll()
        if code is None or item.streams_open:
            return "stopping" if item.stop_requested.is_set() else "running"
        with item.changed:
            item.finished_at = item.finished_at or _now()
        return "exited"

    @staticmethod
    def _chunk(path, offset, maximum):
        size = path.stat().st_size
        if offset > size:
            raise DomainError("INVALID_REFERENCE", 422)
        with path.open("rb") as stream:
            stream.seek(offset)
            data = stream.read(maximum)
        if not data:
            return None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        return {
            "offset": offset,
            "next_offset": offset + len(data),
            "data_base64": base64.b64encode(data).decode("ascii"),
            "text": text,
            "byte_length": len(data),
            "sha256": sha256(data).hexdigest(),
        }

    def _reply(self, item, cursor, maximum):
        state = self._refresh(item)
        stdout = self._chunk(item.stdout_path, cursor.stdout_offset, maximum)
        remaining = maximum - (0 if stdout is None else stdout["byte_length"])
        stderr = self._chunk(item.stderr_path, cursor.stderr_offset, remaining)
        next_cursor = {
            "stdout_offset": cursor.stdout_offset if stdout is None else stdout["next_offset"],
            "stderr_offset": cursor.stderr_offset if stderr is None else stderr["next_offset"],
        }
        code = item.process.poll()
        has_more = (
            next_cursor["stdout_offset"] < item.stdout_path.stat().st_size
            or next_cursor["stderr_offset"] < item.stderr_path.stat().st_size
        )
        return ProcessReplyV1.model_validate(
            {
                "schema_version": "wuji.process-reply.v1",
                "handle": item.handle,
                "state": state,
                "assurance": "executor_reported",
                "started_at": item.started_at,
                "finished_at": item.finished_at,
                "exit_code": code if code is not None and code >= 0 else None,
                "signal": -code if code is not None and code < 0 else None,
                "stdout": stdout,
                "stderr": stderr,
                "cursor": cursor,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "output_completeness": (
                    "partial" if item.truncated else "complete" if state == "exited" else "unknown"
                ),
                "reason_code": "LIMIT_BLOCKED" if item.truncated else None,
            }
        )

    def _unknown(self, handle):
        return ProcessReplyV1.model_validate(
            {
                "schema_version": "wuji.process-reply.v1",
                "handle": handle,
                "state": "unknown",
                "assurance": "executor_reported",
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "signal": None,
                "stdout": None,
                "stderr": None,
                "cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "next_cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "has_more": False,
                "output_completeness": "unknown",
                "reason_code": "OPERATION_UNKNOWN",
            }
        )

    def read(
        self, *, action_id, handle, arguments_digest, cursor, max_bytes,
        wait_ms=0, durable=True
    ):
        cursor = ProcessCursorV1.model_validate(cursor)

        def operate():
            item = self._find(handle)
            if item is None:
                return self._unknown(handle)
            deadline = self._clock() + wait_ms / 1000
            with item.changed:
                while (
                    self._refresh(item) != "exited"
                    and cursor.stdout_offset >= item.stdout_path.stat().st_size
                    and cursor.stderr_offset >= item.stderr_path.stat().st_size
                    and self._clock() < deadline
                ):
                    item.changed.wait(timeout=max(0, deadline - self._clock()))
            return self._reply(item, cursor, max_bytes)

        reply = self._action(action_id, arguments_digest, operate) if durable else operate()
        return self._unknown(handle) if reply is None else reply

    def input(self, *, action_id, handle, arguments_digest, data, eof=False):
        def operate():
            if self._shutting_down.is_set():
                raise DomainError("STALE_EXECUTION", 409)
            item = self._find(handle)
            if item is None or item.process.poll() is not None or item.process.stdin is None:
                return self._unknown(handle)
            pending = memoryview(data.encode("utf-8"))
            deadline = self._clock() + self.stop_grace_seconds
            while pending:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    raise TimeoutError("stdin write did not complete")
                _, writable, _ = select.select(
                    (), (item.process.stdin.fileno(),), (), remaining
                )
                if not writable:
                    raise TimeoutError("stdin write did not complete")
                written = os.write(item.process.stdin.fileno(), pending)
                pending = pending[written:]
            if eof:
                item.process.stdin.close()
            return self._reply(item, ProcessCursorV1(stdout_offset=0, stderr_offset=0), 0)

        reply = self._action(action_id, arguments_digest, operate)
        return self._unknown(handle) if reply is None else reply

    def stop(self, *, action_id, handle, arguments_digest):
        def operate():
            item = self._find(handle)
            if item is None:
                return self._unknown(handle)
            item.stop_requested.set()
            self._terminate(item)
            return self._reply(item, ProcessCursorV1(stdout_offset=0, stderr_offset=0), 0)

        reply = self._action(action_id, arguments_digest, operate)
        return self._unknown(handle) if reply is None else reply

    def shutdown(self, on_complete):
        if not callable(on_complete):
            raise ValueError("shutdown completion callback is required")
        with self._lock:
            complete = self._shutdown_complete.is_set()
            if complete:
                pass
            else:
                self._shutdown_callbacks.append(on_complete)
                if self._shutting_down.is_set():
                    return
                self._shutting_down.set()
        if complete:
            on_complete()
            return

        def clean():
            with self._lock:
                processes = tuple(self._processes.values())
            for item in processes:
                item.stop_requested.set()
                self._terminate(item)
            deadline = self._clock() + self.stop_grace_seconds
            for item in processes:
                with item.changed:
                    while self._refresh(item) != "exited" and self._clock() < deadline:
                        item.changed.wait(timeout=max(0, deadline - self._clock()))
            with self._lock:
                self._shutdown_complete.set()
                callbacks, self._shutdown_callbacks = self._shutdown_callbacks, []
            for callback in callbacks:
                try:
                    callback()
                except Exception:
                    pass

        Thread(target=clean, name="wuji-process-shutdown", daemon=True).start()
