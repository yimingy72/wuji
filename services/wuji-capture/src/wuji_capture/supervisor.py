"""PID 1 supervisor for writer, tcpdump, and mitmproxy."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import BinaryIO

from .control import CaptureControlServer, CaptureItemStore
from .protocol import WriterUnavailable, request as writer_request
from .storage import atomic_write, canonical_bytes, fsync_directory, utc_now, write_fault


_PCAP_STATS_BLOCK = re.compile(
    r"(?m)^(?P<captured>[0-9]+)\s+packets?\s+captured\r?\n"
    r"^(?P<received>[0-9]+)\s+packets?\s+received by filter\r?\n"
    r"^(?P<dropped>[0-9]+)\s+packets?\s+dropped by kernel(?:\r?\n|\Z)",
    re.IGNORECASE,
)
_PCAP_LIVE_STATS = re.compile(
    r"(?m)^tcpdump:\s*(?P<captured>[0-9]+)\s+packets?\s+captured,\s*"
    r"(?P<received>[0-9]+)\s+packets?\s+received by filter,\s*"
    r"(?P<dropped>[0-9]+)\s+packets?\s+dropped by kernel(?:\r?\n|\Z)",
    re.IGNORECASE,
)


def parse_pcap_stats_block(text: str) -> dict[str, int] | None:
    """Return the last complete tcpdump statistics block in this text."""

    matches = [*_PCAP_STATS_BLOCK.finditer(text), *_PCAP_LIVE_STATS.finditer(text)]
    if not matches:
        return None
    match = max(matches, key=lambda value: value.end())
    return {
        "captured": int(match.group("captured")),
        "received_by_filter": int(match.group("received")),
        "dropped_by_kernel": int(match.group("dropped")),
    }


@dataclass(frozen=True)
class Settings:
    root: Path
    runtime: Path
    proxy_host: str
    proxy_port: int
    health_host: str
    health_port: int
    writer_timeout: float
    startup_timeout: float
    shutdown_timeout: float
    maximum_request_body_bytes: int
    maximum_response_body_bytes: int
    pcap_segment_bytes: int
    maximum_session_bytes: int
    maximum_items: int
    part_read_chunk_bytes: int
    drain_timeout: float
    seal_timeout: float
    interface: str
    tcpdump_bin: str
    capture_user: str | None
    mitmdump_bin: str
    upstream_ca: str | None
    ca_public_file: Path | None
    control_host: str | None
    control_port: int | None
    control_certificate: str | None
    control_private_key: str | None
    control_client_ca: str | None
    control_client_fingerprint: str | None
    binding: dict[str, object] | None

    @classmethod
    def environment(cls) -> "Settings":
        def positive(name: str, default: str, convert):
            value = convert(os.environ.get(name, default))
            if value <= 0:
                raise ValueError(f"{name} must be positive")
            return value

        interface = os.environ.get("WUJI_CAPTURE_INTERFACE", "any").strip()
        if not interface or len(interface) > 64:
            raise ValueError("WUJI_CAPTURE_INTERFACE must be a bounded interface name")
        public_ca = os.environ.get("WUJI_CAPTURE_CA_PUBLIC_FILE")
        if public_ca is not None and not Path(public_ca).is_absolute():
            raise ValueError("WUJI_CAPTURE_CA_PUBLIC_FILE must be absolute")
        capture_user = os.environ.get("WUJI_CAPTURE_DROP_USER", "wuji-capture").strip()
        legacy_body = os.environ.get("WUJI_CAPTURE_MAX_BODY_BYTES", str(8 * 1024 * 1024))
        segment_bytes = positive(
            "WUJI_CAPTURE_PCAP_SEGMENT_BYTES",
            str(positive("WUJI_CAPTURE_SEGMENT_MEGABYTES", "64", int) * 1_000_000),
            int,
        )
        if segment_bytes % 1_000_000:
            raise ValueError("WUJI_CAPTURE_PCAP_SEGMENT_BYTES must be a whole decimal megabyte")
        control_certificate = os.environ.get("WUJI_CAPTURE_CONTROL_TLS_CERT_FILE")
        control_private_key = os.environ.get("WUJI_CAPTURE_CONTROL_TLS_KEY_FILE")
        control_client_ca = os.environ.get("WUJI_CAPTURE_CONTROL_CLIENT_CA_FILE")
        fingerprint_file = os.environ.get("WUJI_CAPTURE_CONTROL_CLIENT_FINGERPRINT_FILE")
        control_values = (
            control_certificate, control_private_key, control_client_ca, fingerprint_file,
        )
        control_enabled = any(value is not None for value in control_values)
        if control_enabled and not all(value is not None for value in control_values):
            raise ValueError("capture control TLS configuration must be complete")
        binding = None
        client_fingerprint = None
        if control_enabled:
            task_id = os.environ.get("WUJI_TASK_ID", "")
            pod_uid = os.environ.get("WUJI_POD_UID", "")
            if not task_id or not pod_uid:
                raise ValueError("capture control identity is incomplete")
            binding = {
                "task_id": task_id,
                "runtime_attempt": positive("WUJI_RUNTIME_ATTEMPT", "0", int),
                "execution_epoch": positive("WUJI_EXECUTION_EPOCH", "0", int),
                "pod_uid": pod_uid,
            }
            client_fingerprint = Path(fingerprint_file).read_text().strip()
            if not re.fullmatch(r"[a-f0-9]{64}", client_fingerprint):
                raise ValueError("capture control client fingerprint is invalid")
        return cls(
            root=Path(os.environ.get("WUJI_CAPTURE_ROOT", "/var/lib/wuji-capture")),
            runtime=Path(os.environ.get("WUJI_CAPTURE_RUNTIME", "/run/wuji-capture")),
            proxy_host=os.environ.get("WUJI_CAPTURE_PROXY_HOST", "127.0.0.1"),
            proxy_port=positive("WUJI_CAPTURE_PROXY_PORT", "8080", int),
            health_host=os.environ.get("WUJI_CAPTURE_HEALTH_HOST", "127.0.0.1"),
            health_port=positive("WUJI_CAPTURE_HEALTH_PORT", "8085", int),
            writer_timeout=positive("WUJI_CAPTURE_WRITER_TIMEOUT_SECONDS", "5", float),
            startup_timeout=positive("WUJI_CAPTURE_STARTUP_TIMEOUT_SECONDS", "20", float),
            shutdown_timeout=positive("WUJI_CAPTURE_SHUTDOWN_TIMEOUT_SECONDS", "10", float),
            maximum_request_body_bytes=positive(
                "WUJI_CAPTURE_MAX_REQUEST_BODY_BYTES", legacy_body, int
            ),
            maximum_response_body_bytes=positive(
                "WUJI_CAPTURE_MAX_RESPONSE_BODY_BYTES", legacy_body, int
            ),
            pcap_segment_bytes=segment_bytes,
            maximum_session_bytes=positive(
                "WUJI_CAPTURE_MAX_SESSION_BYTES", str(1024 * 1024 * 1024), int
            ),
            maximum_items=positive("WUJI_CAPTURE_MAX_ITEMS", "10000", int),
            part_read_chunk_bytes=positive(
                "WUJI_CAPTURE_PART_READ_CHUNK_BYTES", str(1024 * 1024), int
            ),
            drain_timeout=positive("WUJI_CAPTURE_DRAIN_TIMEOUT_SECONDS", "5", float),
            seal_timeout=positive("WUJI_CAPTURE_SEAL_TIMEOUT_SECONDS", "10", float),
            interface=interface,
            tcpdump_bin=os.environ.get("WUJI_CAPTURE_TCPDUMP_BIN", "/opt/tcpdump/bin/tcpdump"),
            capture_user=capture_user or None,
            mitmdump_bin=os.environ.get("WUJI_CAPTURE_MITMDUMP_BIN", str(Path(sys.executable).with_name("mitmdump"))),
            upstream_ca=os.environ.get("WUJI_CAPTURE_UPSTREAM_CA") or None,
            ca_public_file=Path(public_ca) if public_ca is not None else None,
            control_host=(os.environ.get("WUJI_CAPTURE_CONTROL_HOST", "0.0.0.0")
                          if control_enabled else None),
            control_port=(positive("WUJI_CAPTURE_CONTROL_PORT", "8445", int)
                          if control_enabled else None),
            control_certificate=control_certificate,
            control_private_key=control_private_key,
            control_client_ca=control_client_ca,
            control_client_fingerprint=client_fingerprint,
            binding=binding,
        )


class _HealthHandler(BaseHTTPRequestHandler):
    server_version = "wuji-capture"

    def do_GET(self) -> None:  # noqa: N802
        supervisor = self.server.supervisor  # type: ignore[attr-defined]
        if self.path == "/health/live":
            status, document = supervisor.health(live=True)
        elif self.path == "/health/ready":
            status, document = supervisor.health(live=False)
        else:
            status, document = HTTPStatus.NOT_FOUND, {"status": "not_found"}
        body = canonical_bytes(document) + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args) -> None:
        return


class CaptureSupervisor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.writer_socket = settings.runtime / "writer.sock"
        self.fault_file = settings.runtime / "fault.json"
        self.status_file = settings.root / "status.json"
        self.children: dict[str, subprocess.Popen[bytes]] = {}
        self.logs: dict[str, BinaryIO] = {}
        self.ready = False
        self.draining = False
        self.sealing = False
        self.sealed = False
        self.sealed_state: str | None = None
        self.failure: str | None = None
        self.stop_event = threading.Event()
        self.health_server: ThreadingHTTPServer | None = None
        self.control_server: CaptureControlServer | None = None
        self.started_at = utc_now()
        self.pcap_stats: dict[str, int] | None = None
        self._pcap_stats_lock = threading.Lock()
        self._seal_lock = threading.Lock()
        self._item_lock = threading.Lock()
        self._logs_closed = False
        self._proxy_log_offset = 0
        self.drain_file = settings.runtime / "draining"
        self.item_store = CaptureItemStore(
            settings.root,
            maximum_items=settings.maximum_items,
            maximum_session_bytes=settings.maximum_session_bytes,
            maximum_chunk_bytes=settings.part_read_chunk_bytes,
        )

    def _status(self) -> dict[str, object]:
        state = (
            self.sealed_state if self.sealed
            else "failed" if self.failure
            else "sealing" if self.sealing
            else "draining" if self.draining
            else "ready" if self.ready
            else "starting"
        )
        return {
            "schema_version": "wuji.capture-status.v1",
            "binding": self.settings.binding,
            "state": state,
            "ready": self.ready and not self.failure and not self.draining,
            "failure": self.failure,
            "started_at": self.started_at,
            "observed_at": utc_now(),
            "children": {
                name: {"pid": process.pid, "running": process.poll() is None}
                for name, process in self.children.items()
            },
            "pcap_stats": self.pcap_stats,
            "latest_item_seq": self.item_store.items[-1]["item_seq"] if self.item_store.items else 0,
        }

    def _write_status(self) -> None:
        atomic_write(self.status_file, canonical_bytes(self._status()) + b"\n")

    def health(self, *, live: bool) -> tuple[HTTPStatus, dict[str, object]]:
        document = self._status()
        if live:
            return (HTTPStatus.OK if not self.failure else HTTPStatus.SERVICE_UNAVAILABLE), document
        healthy = bool(document["ready"])
        if healthy:
            try:
                writer_request(self.writer_socket, {"op": "ping"}, timeout=self.settings.writer_timeout)
            except WriterUnavailable as error:
                self._fail("writer health failed: " + str(error))
                healthy = False
                document = self._status()
        return (HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE), document

    def _start_health(self) -> None:
        server = ThreadingHTTPServer((self.settings.health_host, self.settings.health_port), _HealthHandler)
        server.supervisor = self  # type: ignore[attr-defined]
        thread = threading.Thread(target=server.serve_forever, name="capture-health", daemon=True)
        thread.start()
        self.health_server = server

    def _start_control(self) -> None:
        if self.settings.control_host is None:
            return
        server = CaptureControlServer(
            self,
            host=self.settings.control_host,
            port=self.settings.control_port,
            certificate=self.settings.control_certificate,
            private_key=self.settings.control_private_key,
            client_ca=self.settings.control_client_ca,
            client_fingerprint=self.settings.control_client_fingerprint,
        )
        thread = threading.Thread(
            target=server.serve_forever, name="capture-control", daemon=True
        )
        thread.start()
        self.control_server = server

    def _log(self, name: str) -> BinaryIO:
        path = self.settings.root / "logs" / f"{name}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open("ab", buffering=0)
        self.logs[name] = stream
        return stream

    def _spawn(self, name: str, command: list[str], *, environment: dict[str, str] | None = None) -> None:
        log = self._log(name)
        self.children[name] = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            env=environment,
            start_new_session=True,
        )

    def _writer_command(self) -> list[str]:
        return [
            sys.executable, "-m", "wuji_capture.writer",
            "--socket", str(self.writer_socket),
            "--root", str(self.settings.root / "http"),
            "--fault-file", str(self.fault_file),
            "--maximum-request-body-bytes", str(self.settings.maximum_request_body_bytes),
            "--maximum-response-body-bytes", str(self.settings.maximum_response_body_bytes),
            "--maximum-session-bytes", str(self.settings.maximum_session_bytes),
            "--maximum-items", str(self.settings.maximum_items),
        ]

    def _pcap_command(self) -> list[str]:
        output = self.settings.root / "pcap" / "capture.pcap"
        output.parent.mkdir(parents=True, exist_ok=True)
        # -C without -W appends monotonically numbered files and never wraps.
        # SIGUSR1 below reports this exact process handle's kernel statistics;
        # SIGUSR2 flushes its active output file before sealing.
        command = [
            self.settings.tcpdump_bin,
            "-i", self.settings.interface,
            "-nn", "-p", "-s", "0", "-U",
            "-C", str(self.settings.pcap_segment_bytes // 1_000_000),
            "-w", str(output),
        ]
        if self.settings.capture_user is not None:
            command[7:7] = ["-Z", self.settings.capture_user]
        return command

    def _proxy_command(self) -> tuple[list[str], dict[str, str]]:
        confdir = self.settings.root / "mitmproxy"
        confdir.mkdir(parents=True, exist_ok=True)
        addon = Path(__file__).with_name("addon.py")
        command = [
            self.settings.mitmdump_bin,
            "--quiet",
            "--mode", "regular",
            "--listen-host", self.settings.proxy_host,
            "--listen-port", str(self.settings.proxy_port),
            "--set", f"confdir={confdir}",
            "--set", "http2=false",
            "--set", "http3=false",
            "--set", "rawtcp=false",
            "--set", "websocket=false",
            "--set", "connection_strategy=lazy",
            "--set", "body_size_limit=" + str(max(
                self.settings.maximum_request_body_bytes,
                self.settings.maximum_response_body_bytes,
            )),
            "-s", str(addon),
        ]
        if self.settings.upstream_ca:
            command.extend(["--set", f"ssl_verify_upstream_trusted_ca={self.settings.upstream_ca}"])
        environment = {
            **os.environ,
            "WUJI_CAPTURE_WRITER_SOCKET": str(self.writer_socket),
            "WUJI_CAPTURE_FAULT_FILE": str(self.fault_file),
            "WUJI_CAPTURE_WRITER_TIMEOUT_SECONDS": str(self.settings.writer_timeout),
            "WUJI_CAPTURE_MAX_REQUEST_BODY_BYTES": str(self.settings.maximum_request_body_bytes),
            "WUJI_CAPTURE_MAX_RESPONSE_BODY_BYTES": str(self.settings.maximum_response_body_bytes),
            "WUJI_CAPTURE_DRAIN_FILE": str(self.drain_file),
        }
        return command, environment

    def _wait_writer(self, deadline: float) -> None:
        while time.monotonic() < deadline:
            process = self.children["writer"]
            if process.poll() is not None:
                raise RuntimeError("writer exited during startup")
            try:
                writer_request(self.writer_socket, {"op": "ping"}, timeout=0.5)
                return
            except WriterUnavailable:
                time.sleep(0.05)
        raise RuntimeError("writer startup timed out")

    def _wait_proxy(self, deadline: float) -> None:
        ca_path = self.settings.root / "mitmproxy" / "mitmproxy-ca-cert.pem"
        while time.monotonic() < deadline:
            if self.children["proxy"].poll() is not None:
                raise RuntimeError("proxy exited during startup")
            try:
                with socket.create_connection(("127.0.0.1", self.settings.proxy_port), timeout=0.25):
                    if ca_path.is_file():
                        return
            except OSError:
                pass
            time.sleep(0.05)
        raise RuntimeError("proxy startup timed out")

    def _publish_ca_bundle(self) -> None:
        destination = self.settings.ca_public_file
        if destination is None:
            return
        system_bundle = Path("/etc/ssl/certs/ca-certificates.crt")
        mitm_ca = self.settings.root / "mitmproxy" / "mitmproxy-ca-cert.pem"
        bundle = system_bundle.read_bytes().rstrip() + b"\n" + mitm_ca.read_bytes().rstrip() + b"\n"
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(destination, bundle)
        destination.chmod(0o444)

    def _wait_pcap(self, deadline: float) -> None:
        log_path = self.settings.root / "logs" / "pcap.log"
        while time.monotonic() < deadline:
            if self.children["pcap"].poll() is not None:
                raise RuntimeError("tcpdump exited during startup")
            if log_path.exists() and "listening on" in log_path.read_text(
                encoding="utf-8", errors="replace"
            ):
                return
            time.sleep(0.02)
        raise RuntimeError("tcpdump startup timed out")

    def start(self) -> None:
        self.settings.root.mkdir(parents=True, exist_ok=True)
        self.settings.runtime.mkdir(parents=True, exist_ok=True)
        self.fault_file.unlink(missing_ok=True)
        self.drain_file.unlink(missing_ok=True)
        self._start_health()
        deadline = time.monotonic() + self.settings.startup_timeout
        self._spawn("writer", self._writer_command(), environment=os.environ.copy())
        self._wait_writer(deadline)
        self._spawn("pcap", self._pcap_command(), environment=os.environ.copy())
        self._wait_pcap(deadline)
        initial_stats = self._refresh_pcap_stats(timeout=1.5)
        if initial_stats is None:
            raise RuntimeError("tcpdump did not report live capture statistics")
        if initial_stats["dropped_by_kernel"]:
            raise RuntimeError("tcpdump reported dropped packets")
        proxy, environment = self._proxy_command()
        self._spawn("proxy", proxy, environment=environment)
        self._wait_proxy(deadline)
        self._publish_ca_bundle()
        self._start_control()
        self.ready = True
        self._write_status()

    def _fail(self, reason: str) -> None:
        if self.failure is None:
            self.failure = reason[:1024]
            self.ready = False
            write_fault(self.fault_file, component="supervisor", reason=self.failure)
            try:
                self._write_status()
            except OSError:
                pass
            self.stop_event.set()

    def monitor(self) -> None:
        next_stats = time.monotonic() + 5
        while not self.stop_event.wait(0.1):
            if self.sealing or self.sealed:
                continue
            if self.fault_file.exists():
                self._fail("capture fault marker observed")
                break
            if self._proxy_protocol_failure():
                self._fail("proxy rejected an unsupported HTTP framing failure")
                break
            for name, process in self.children.items():
                status = process.poll()
                if status is not None:
                    self._fail(f"{name} exited unexpectedly with status {status}")
                    break
            if time.monotonic() >= next_stats:
                stats = self._refresh_pcap_stats(timeout=1.5)
                if stats is None:
                    self._fail("tcpdump live statistics became unavailable")
                    break
                if stats["dropped_by_kernel"]:
                    self._fail("tcpdump reported dropped packets")
                    break
                try:
                    self._check_session_limits()
                    with self._item_lock:
                        self.item_store.refresh(sealed=False, pcap_stats=stats)
                except (OSError, ValueError) as error:
                    self._fail(str(error))
                    break
                next_stats = time.monotonic() + 5

    def _proxy_protocol_failure(self) -> bool:
        path = self.settings.root / "logs" / "proxy.log"
        if not path.exists() or path.stat().st_size <= self._proxy_log_offset:
            return False
        with path.open("rb") as stream:
            stream.seek(self._proxy_log_offset)
            text = stream.read().decode("utf-8", errors="replace")
            self._proxy_log_offset = stream.tell()
        return "mitmproxy has crashed!" in text or "HTTP trailers are not implemented" in text

    def request_stop(self, _signum=None, _frame=None) -> None:
        self._begin_drain()
        self.stop_event.set()

    def _begin_drain(self) -> None:
        if not self.draining:
            self.draining = True
            self.ready = False
            atomic_write(self.drain_file, b"draining\n")
            try:
                self._write_status()
            except OSError:
                pass

    def _stop_child(self, name: str, *, timeout: float | None = None) -> int | None:
        process = self.children.get(name)
        if process is None:
            return None
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=(self.settings.shutdown_timeout if timeout is None else max(0, timeout)))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
        return process.returncode

    def _check_session_limits(self) -> None:
        total = sum(
            path.stat().st_size
            for directory in (self.settings.root / "http", self.settings.root / "pcap")
            if directory.exists()
            for path in directory.rglob("*")
            if path.is_file()
        )
        if total > self.settings.maximum_session_bytes:
            raise ValueError("capture session byte limit exceeded")

    @staticmethod
    def _file(path: Path) -> dict[str, object]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            os.fsync(stream.fileno())
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        fsync_directory(path.parent)
        return {"path": str(path), "size_bytes": size, "sha256": digest.hexdigest()}

    def _stats_since(self, offset: int, *, timeout: float) -> dict[str, int] | None:
        log_path = self.settings.root / "logs" / "pcap.log"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if log_path.exists() and log_path.stat().st_size > offset:
                with log_path.open("rb") as stream:
                    stream.seek(offset)
                    text = stream.read().decode("utf-8", errors="replace")
                stats = parse_pcap_stats_block(text)
                if stats is not None:
                    self.pcap_stats = stats
                    return stats
            time.sleep(0.02)
        return None

    def _refresh_pcap_stats(self, *, timeout: float) -> dict[str, int] | None:
        process = self.children.get("pcap")
        log_path = self.settings.root / "logs" / "pcap.log"
        if process is None or process.poll() is not None:
            return None
        with self._pcap_stats_lock:
            before = log_path.stat().st_size if log_path.exists() else 0
            try:
                os.kill(process.pid, signal.SIGUSR1)
            except ProcessLookupError:
                return None
            return self._stats_since(before, timeout=timeout)

    def _manifest(self, exits: dict[str, int | None], writer_seal: dict[str, object] | None) -> dict:
        pcap = [self._file(path) for path in sorted((self.settings.root / "pcap").glob("capture.pcap*"))]
        drops = None if self.pcap_stats is None else self.pcap_stats["dropped_by_kernel"]
        reasons: list[str] = []
        if self.failure:
            reasons.append(self.failure)
        if drops is None:
            reasons.append("pcap_drop_metrics_unavailable")
        elif drops:
            reasons.append("pcap_packets_dropped")
        if writer_seal is None:
            reasons.append("http_writer_not_sealed")
        elif writer_seal.get("completeness") != "complete":
            reasons.append("http_capture_incomplete")
        complete = not reasons and all(value in {0, -signal.SIGTERM} for value in exits.values() if value is not None)
        manifest = {
            "schema_version": "wuji.capture-manifest.v1",
            "state": "sealed-complete" if complete else "sealed-incomplete",
            "completeness": "complete" if complete else "partial" if pcap or writer_seal else "unknown",
            "started_at": self.started_at,
            "sealed_at": utc_now(),
            "reasons": reasons,
            "supported_protocols": ["HTTP/1.0", "HTTP/1.1", "TLS HTTP/1.1"],
            "pcap_drop_count": drops,
            "pcap_stats": self.pcap_stats,
            "pcap_segments": pcap,
            "writer_seal": writer_seal,
            "child_exit_status": exits,
        }
        atomic_write(self.settings.root / "manifest.json", canonical_bytes(manifest) + b"\n")
        return manifest

    def control_status(self) -> dict:
        with self._item_lock:
            if not self.sealing:
                self.item_store.refresh(sealed=self.sealed, pcap_stats=self.pcap_stats)
        return self._status()

    def control_items(self, *, after: int, limit: int) -> dict:
        with self._item_lock:
            self.item_store.refresh(sealed=self.sealed, pcap_stats=self.pcap_stats)
            page = self.item_store.page(after=after, limit=limit)
        return {**page, "binding": self.settings.binding, "state": self._status()["state"]}

    def control_part(self, item_seq: int, part: str, *, offset: int, length: int):
        with self._item_lock:
            return self.item_store.read_part(item_seq, part, offset=offset, length=length)

    def control_drain(self) -> dict:
        self._begin_drain()
        deadline = time.monotonic() + self.settings.drain_timeout
        pending = None
        while time.monotonic() < deadline:
            writer = self.children.get("writer")
            if writer is None or writer.poll() is not None:
                break
            try:
                status = writer_request(
                    self.writer_socket, {"op": "status"}, timeout=self.settings.writer_timeout
                )
            except WriterUnavailable:
                break
            pending = status.get("pending_exchange_count")
            if pending == 0:
                break
            time.sleep(0.05)
        return {**self._status(), "drain_complete": pending == 0,
                "pending_exchange_count": pending}

    def _seal(self) -> None:
        with self._seal_lock:
            if self.sealed:
                return
            self._begin_drain()
            self.sealing = True
            deadline = time.monotonic() + self.settings.seal_timeout

            def remaining() -> float:
                return max(0.0, deadline - time.monotonic())

            exits: dict[str, int | None] = {}
            exits["proxy"] = self._stop_child("proxy", timeout=remaining())
            writer_seal = None
            if self.children.get("writer") and self.children["writer"].poll() is None:
                try:
                    writer_seal = writer_request(
                        self.writer_socket,
                        {"op": "seal"},
                        timeout=min(self.settings.writer_timeout, remaining()),
                    )
                except WriterUnavailable as error:
                    self._fail("writer seal failed: " + str(error))
            exits["writer"] = self._stop_child("writer", timeout=remaining())
            pcap = self.children.get("pcap")
            if pcap is not None and pcap.poll() is None:
                try:
                    os.kill(pcap.pid, signal.SIGUSR2)
                except ProcessLookupError:
                    pass
                live_stats = self._refresh_pcap_stats(timeout=min(1.5, remaining()))
                if live_stats is None:
                    self._fail("tcpdump final live statistics became unavailable")
                elif live_stats["dropped_by_kernel"]:
                    self._fail("tcpdump reported dropped packets")
            pcap_log = self.settings.root / "logs" / "pcap.log"
            final_stats_offset = pcap_log.stat().st_size if pcap_log.exists() else 0
            exits["pcap"] = self._stop_child("pcap", timeout=remaining())
            if pcap is not None:
                final_stats = self._stats_since(
                    final_stats_offset, timeout=min(0.5, remaining())
                )
                if final_stats is None:
                    self._fail("tcpdump final statistics became unavailable")
                elif final_stats["dropped_by_kernel"]:
                    self._fail("tcpdump reported dropped packets")
            if not self._logs_closed:
                for stream in self.logs.values():
                    stream.close()
                self._logs_closed = True
            try:
                manifest = self._manifest(exits, writer_seal)
                self.sealed_state = manifest["state"]
                self.sealed = True
                with self._item_lock:
                    self.item_store.refresh(sealed=True, pcap_stats=self.pcap_stats)
            except (OSError, ValueError) as error:
                self._fail("manifest/index write failed: " + str(error))
            finally:
                self.sealing = False
                try:
                    self._write_status()
                except OSError:
                    pass

    def control_seal(self) -> dict:
        self.control_drain()
        self._seal()
        return self._status()

    def shutdown(self) -> int:
        self._seal()
        if self.control_server:
            self.control_server.close()
        if self.health_server:
            self.health_server.shutdown()
            self.health_server.server_close()
        return 1 if self.failure else 0


def main() -> int:
    settings = Settings.environment()
    supervisor = CaptureSupervisor(settings)
    signal.signal(signal.SIGTERM, supervisor.request_stop)
    signal.signal(signal.SIGINT, supervisor.request_stop)
    try:
        supervisor.start()
        supervisor.monitor()
    except Exception as error:
        supervisor._fail(str(error))
    return supervisor.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
