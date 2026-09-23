from __future__ import annotations

import http.client
import base64
import hashlib
import json
import os
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import tempfile
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from mitmproxy import http as mitm_http

from wuji_capture.addon import CaptureAddon
from wuji_capture.control import CaptureControlServer, CaptureItemStore
from wuji_capture.protocol import WriterUnavailable, request as writer_request
from wuji_capture.supervisor import CaptureSupervisor, Settings, parse_pcap_stats_block
from wuji_capture.writer import DurableWriter


def unused_port() -> int:
    with socket.socket() as stream:
        stream.bind(("127.0.0.1", 0))
        return stream.getsockname()[1]


def wait_until(predicate, *, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("condition did not become true")


class TargetHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    evidence_root: Path
    barrier_checks: list[bool]
    expect_hits = 0
    trailer_hits = 0

    def do_POST(self):  # noqa: N802
        type(self).expect_hits += int(self.path == "/expect")
        type(self).trailer_hits += int(self.path == "/trailers")
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks = []
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if size == 0:
                    self.rfile.readline()
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)
            body = b"".join(chunks)
        else:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request_bodies = list((self.evidence_root / "exchanges").glob("*/request.body"))
        type(self).barrier_checks.append(
            len(request_bodies) == 1 and request_bodies[0].read_bytes() == body
        )
        response = b"\x00response\xff"
        self.send_response(200)
        self.send_header("Content-Length", str(len(response)))
        self.send_header("X-Duplicate", "first")
        self.send_header("X-Duplicate", "second")
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):  # noqa: N802
        if self.path == "/interim":
            self.connection.sendall(b"HTTP/1.1 103 Early Hints\r\nLink: </a>\r\n\r\n")
        body = b"tls-response" if self.path == "/tls" else b"final-response"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


@contextmanager
def target_server(tmp_path: Path, *, tls=False):
    TargetHandler.evidence_root = tmp_path / "evidence" / "http"
    TargetHandler.barrier_checks = []
    TargetHandler.expect_hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
    ca = None
    if tls:
        ca = tmp_path / "target-ca.crt"
        key = tmp_path / "target.key"
        cert = tmp_path / "target.crt"
        config = tmp_path / "target.cnf"
        config.write_text("""[req]
distinguished_name=dn
x509_extensions=ext
prompt=no
[dn]
CN=127.0.0.1
[ext]
subjectAltName=IP:127.0.0.1
basicConstraints=CA:TRUE
keyUsage=digitalSignature,keyEncipherment,keyCertSign
""")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-days", "1", "-keyout", str(key), "-out", str(cert),
            "-config", str(config),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ca.write_bytes(cert.read_bytes())
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], ca
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def capture_proxy(tmp_path: Path, *, upstream_ca: Path):
    root = tmp_path / "evidence"
    runtime_directory = tempfile.TemporaryDirectory(prefix="wuji-capture-", dir="/tmp")
    runtime = Path(runtime_directory.name)
    socket_path = runtime / "writer.sock"
    fault_path = runtime / "fault.json"
    proxy_port = unused_port()
    writer = subprocess.Popen([
        sys.executable, "-m", "wuji_capture.writer",
        "--socket", str(socket_path), "--root", str(root / "http"),
        "--fault-file", str(fault_path),
        "--maximum-request-body-bytes", "1048576",
        "--maximum-response-body-bytes", "1048576",
        "--maximum-session-bytes", "16777216",
        "--maximum-items", "100",
    ])
    wait_until(lambda: socket_path.exists())
    confdir = root / "mitmproxy"
    addon = Path(__file__).parents[1] / "src" / "wuji_capture" / "addon.py"
    environment = {
        **os.environ,
        "WUJI_CAPTURE_WRITER_SOCKET": str(socket_path),
        "WUJI_CAPTURE_FAULT_FILE": str(fault_path),
        "WUJI_CAPTURE_WRITER_TIMEOUT_SECONDS": "2",
        "WUJI_CAPTURE_MAX_BODY_BYTES": "1048576",
    }
    proxy = subprocess.Popen([
        str(Path(sys.executable).with_name("mitmdump")), "--quiet",
        "--mode", "regular", "--listen-host", "127.0.0.1",
        "--listen-port", str(proxy_port), "--set", f"confdir={confdir}",
        "--set", "http2=false", "--set", "http3=false",
        "--set", "rawtcp=false", "--set", "websocket=false",
        "--set", "connection_strategy=lazy", "--set", "body_size_limit=1048576",
        "--set", f"ssl_verify_upstream_trusted_ca={upstream_ca}",
        "-s", str(addon),
    ], env=environment)

    def proxy_ready():
        if proxy.poll() is not None:
            raise AssertionError("proxy exited during startup")
        try:
            with socket.create_connection(("127.0.0.1", proxy_port), timeout=0.2):
                return (confdir / "mitmproxy-ca-cert.pem").exists()
        except OSError:
            return False

    wait_until(proxy_ready)
    try:
        yield root, runtime, proxy_port, writer, proxy
    finally:
        for process in (proxy, writer):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        runtime_directory.cleanup()


def gap_reasons(root: Path) -> list[str]:
    return [
        json.loads(path.read_text())["metadata"]["reason"]
        for path in (root / "http" / "exchanges").glob("*/gap.json")
    ]


def test_writer_seal_reports_an_unfinished_exchange(tmp_path):
    writer = DurableWriter(
        tmp_path,
        maximum_request_body_bytes=1024,
        maximum_response_body_bytes=1024,
        maximum_session_bytes=1024 * 1024,
        maximum_items=100,
    )
    writer.handle({
        "op": "record",
        "exchange_id": "pending-flow",
        "stage": "request",
        "metadata": {"method": "GET", "url": "http://fixture.invalid/"},
        "body_base64": "",
    })
    seal = writer.handle({"op": "seal"})
    assert seal["completeness"] == "partial"
    assert seal["pending_exchange_count"] == 1
    assert seal["pending_exchange_ids"] == ["pending-flow"]


def test_http_tls_barriers_rejections_and_writer_failure(tmp_path):
    with target_server(tmp_path, tls=True) as (tls_port, ca):
        assert ca is not None
        with capture_proxy(tmp_path, upstream_ca=ca) as (root, runtime, proxy_port, writer, proxy):
            with target_server(tmp_path) as (http_port, _):
                connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=5)
                connection.putrequest(
                    "POST", f"http://127.0.0.1:{http_port}/echo", skip_host=True
                )
                connection.putheader("Host", "virtual-host.invalid")
                connection.putheader("X-Duplicate", "one")
                connection.putheader("X-Duplicate", "two")
                connection.putheader("Content-Length", "4")
                connection.endheaders(b"\x00A\xffB")
                response = connection.getresponse()
                assert response.status == 200
                assert response.read() == b"\x00response\xff"
                assert TargetHandler.barrier_checks == [True]

                request_meta = json.loads(next((root / "http" / "exchanges").glob("*/request.json")).read_text())
                assert request_meta["metadata"]["url"].startswith(f"http://127.0.0.1:{http_port}/")
                assert "virtual-host.invalid" not in request_meta["metadata"]["url"]
                assert [item for item in request_meta["metadata"]["headers"] if item[0].lower() == "x-duplicate"] == [
                    ["X-Duplicate", "one"], ["X-Duplicate", "two"]
                ]
                response_meta = json.loads(next((root / "http" / "exchanges").glob("*/response.json")).read_text())
                assert response_meta["body_length"] == len(b"\x00response\xff")

                client_context = ssl.create_default_context(
                    cafile=str(root / "mitmproxy" / "mitmproxy-ca-cert.pem")
                )
                tls_connection = http.client.HTTPSConnection(
                    "127.0.0.1", proxy_port, timeout=5, context=client_context
                )
                tls_connection.set_tunnel("127.0.0.1", tls_port)
                tls_connection.request("GET", "/tls")
                tls_response = tls_connection.getresponse()
                assert tls_response.status == 200
                assert tls_response.read() == b"tls-response"

                chunked = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=5)
                chunked.putrequest("POST", f"http://127.0.0.1:{http_port}/chunked")
                chunked.putheader("Transfer-Encoding", "chunked")
                chunked.endheaders(b"4\r\ndata\r\n0\r\n\r\n")
                chunked_response = chunked.getresponse()
                assert chunked_response.status == 200
                assert chunked_response.read() == b"\x00response\xff"

                with socket.create_connection(("127.0.0.1", proxy_port), timeout=2) as stream:
                    stream.sendall(
                        f"POST http://127.0.0.1:{http_port}/expect HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{http_port}\r\nContent-Length: 4\r\n"
                        "Expect: 100-continue\r\nConnection: close\r\n\r\n".encode()
                    )
                    stream.settimeout(2)
                    rejected = stream.recv(4096)
                assert b"100 Continue" not in rejected
                assert TargetHandler.expect_hits == 0
                wait_until(lambda: "expect_unsupported" in gap_reasons(root))

                with socket.create_connection(("127.0.0.1", proxy_port), timeout=2) as stream:
                    stream.sendall(
                        f"POST http://127.0.0.1:{http_port}/trailers HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{http_port}\r\nTransfer-Encoding: chunked\r\n"
                        "Trailer: X-Declared-Trailer\r\n"
                        "Connection: close\r\n\r\n".encode()
                    )
                    stream.settimeout(2)
                    stream.recv(4096)
                assert TargetHandler.trailer_hits == 0
                wait_until(lambda: "request_trailers_unsupported" in gap_reasons(root))

                interim = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=3)
                with pytest.raises((http.client.RemoteDisconnected, ConnectionError, TimeoutError)):
                    interim.request("GET", f"http://127.0.0.1:{http_port}/interim")
                    interim.getresponse()
                wait_until(lambda: "interim_response_unsupported" in gap_reasons(root))

                writer.terminate()
                writer.wait(timeout=5)
                failed = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=3)
                with pytest.raises((http.client.RemoteDisconnected, ConnectionError, TimeoutError)):
                    failed.request("GET", f"http://127.0.0.1:{http_port}/after-writer-failure")
                    failed.getresponse()
                wait_until(lambda: proxy.poll() is not None)
                assert (runtime / "fault.json").is_file()


def test_supervisor_co_stops_proxy_and_pcap_when_writer_dies(tmp_path):
    fake_pcap = tmp_path / "fake-tcpdump.py"
    fake_pcap.write_text("""#!/usr/bin/env python3
import os, signal, sys, time
running = True
output = sys.argv[sys.argv.index('-w') + 1]
os.makedirs(os.path.dirname(output), exist_ok=True)
handle = open(output, 'wb', buffering=0)
handle.write(b'pcap-fixture')
def stats(*_):
    sys.stderr.write('0 packets captured\\n0 packets received by filter\\n0 packets dropped by kernel\\n')
    sys.stderr.flush()
def flush(*_):
    handle.flush(); os.fsync(handle.fileno())
def stop(*_):
    global running; running = False
signal.signal(signal.SIGUSR1, stats)
signal.signal(signal.SIGUSR2, flush)
signal.signal(signal.SIGTERM, stop)
sys.stderr.write('tcpdump: listening on fixture\\n'); sys.stderr.flush()
while running: time.sleep(.05)
stats(); flush(); handle.close()
""")
    fake_pcap.chmod(0o755)
    root = tmp_path / "capture"
    runtime_directory = tempfile.TemporaryDirectory(prefix="wuji-supervisor-", dir="/tmp")
    runtime = Path(runtime_directory.name)
    proxy_port, health_port = unused_port(), unused_port()
    environment = {
        **os.environ,
        "WUJI_CAPTURE_ROOT": str(root),
        "WUJI_CAPTURE_RUNTIME": str(runtime),
        "WUJI_CAPTURE_PROXY_HOST": "127.0.0.1",
        "WUJI_CAPTURE_PROXY_PORT": str(proxy_port),
        "WUJI_CAPTURE_HEALTH_PORT": str(health_port),
        "WUJI_CAPTURE_TCPDUMP_BIN": str(fake_pcap),
        "WUJI_CAPTURE_DROP_USER": "ignored-by-fixture",
        "WUJI_CAPTURE_MITMDUMP_BIN": str(Path(sys.executable).with_name("mitmdump")),
        "WUJI_CAPTURE_STARTUP_TIMEOUT_SECONDS": "10",
        "WUJI_CAPTURE_SHUTDOWN_TIMEOUT_SECONDS": "3",
    }
    supervisor = subprocess.Popen(
        [sys.executable, "-m", "wuji_capture.supervisor"], env=environment
    )

    def ready():
        if supervisor.poll() is not None:
            raise AssertionError("supervisor exited during startup")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{health_port}/health/ready", timeout=1
            ) as response:
                return response.status == 200
        except OSError:
            return False

    try:
        wait_until(ready)
        status = json.loads((root / "status.json").read_text())
        writer_pid = status["children"]["writer"]["pid"]
        pcap_pid = status["children"]["pcap"]["pid"]
        os.kill(writer_pid, signal.SIGKILL)
        assert supervisor.wait(timeout=10) != 0
        with pytest.raises(ProcessLookupError):
            os.kill(pcap_pid, 0)
        manifest = json.loads((root / "manifest.json").read_text())
        assert manifest["state"] == "sealed-incomplete"
        assert manifest["pcap_stats"]["dropped_by_kernel"] == 0
        assert any("fault" in reason or "writer" in reason for reason in manifest["reasons"])
    finally:
        if supervisor.poll() is None:
            supervisor.terminate()
            supervisor.wait(timeout=5)
        runtime_directory.cleanup()


def test_pcap_stats_parser_requires_one_complete_block():
    assert parse_pcap_stats_block(
        "old tail: 99 packets captured\n"
        "7 packets captured\n8 packets received by filter\n"
    ) is None
    assert parse_pcap_stats_block(
        "7 packets captured\n8 packets received by filter\n2 packets dropped by kernel\n"
    ) == {"captured": 7, "received_by_filter": 8, "dropped_by_kernel": 2}
    assert parse_pcap_stats_block(
        "tcpdump: 9 packets captured, 10 packets received by filter, "
        "0 packets dropped by kernel\n"
    ) == {"captured": 9, "received_by_filter": 10, "dropped_by_kernel": 0}


def test_actual_nonempty_trailers_are_detected_without_a_declaration():
    request = mitm_http.Request.make("POST", "http://fixture.invalid/", b"data")
    request.trailers = mitm_http.Headers([(b"X-Undeclared-Trailer", b"value")])
    assert CaptureAddon._has_trailers(request) is True


def test_capture_item_index_is_incremental_and_keeps_late_gap(tmp_path):
    root = tmp_path / "capture"
    writer = DurableWriter(
        root / "http",
        maximum_request_body_bytes=1024,
        maximum_response_body_bytes=1024,
        maximum_session_bytes=1024 * 1024,
        maximum_items=100,
    )
    encode = lambda value: base64.b64encode(value).decode("ascii")
    writer.handle({
        "op": "record", "exchange_id": "exchange-a", "stage": "request",
        "metadata": {"method": "GET"}, "body_base64": encode(b""),
    })
    writer.handle({
        "op": "record", "exchange_id": "exchange-a", "stage": "response",
        "metadata": {"status_code": 200}, "body_base64": encode(b"response"),
    })
    writer.handle({
        "op": "record", "exchange_id": "exchange-a", "stage": "gap",
        "metadata": {"reason": "late_gap", "completeness": "partial"},
    })
    pcap = root / "pcap"
    pcap.mkdir(parents=True)
    (pcap / "capture.pcap").write_bytes(b"closed")
    time.sleep(0.01)
    (pcap / "capture.pcap1").write_bytes(b"active")
    store = CaptureItemStore(
        root, maximum_items=10, maximum_session_bytes=1024 * 1024,
        maximum_chunk_bytes=4,
    )
    store.refresh(sealed=False, pcap_stats={"dropped_by_kernel": 0})
    assert [item["kind"] for item in store.page(after=0, limit=10)["items"]] == [
        "http_exchange", "gap", "pcap_segment",
    ]
    metadata, body = store.read_part(1, "response_body", offset=0, length=4)
    assert body == b"resp" and metadata["length"] == len(b"response")
    lines = (root / "control" / "items.ndjson").read_text().splitlines()
    store.refresh(sealed=False, pcap_stats={"dropped_by_kernel": 0})
    assert (root / "control" / "items.ndjson").read_text().splitlines() == lines

    manifest = {
        "sealed_at": "2026-09-23T00:00:00Z",
        "completeness": "complete",
        "reasons": [],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    store.refresh(sealed=True, pcap_stats={"dropped_by_kernel": 0})
    assert [item["kind"] for item in store.page(after=3, limit=10)["items"]] == [
        "pcap_segment", "manifest",
    ]


def test_control_server_requires_the_pinned_mtls_client(tmp_path):
    ca_key, ca_cert = tmp_path / "ca.key", tmp_path / "ca.crt"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-subj", "/CN=control-ca", "-keyout", str(ca_key), "-out", str(ca_cert),
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def certificate(name, extended, san=None):
        key, csr, cert = (tmp_path / f"{name}.{suffix}" for suffix in ("key", "csr", "crt"))
        subprocess.run([
            "openssl", "req", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={name}",
            "-keyout", str(key), "-out", str(csr),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        extension = tmp_path / f"{name}.ext"
        extension.write_text(f"extendedKeyUsage={extended}\n" + (f"subjectAltName={san}\n" if san else ""))
        subprocess.run([
            "openssl", "x509", "-req", "-days", "1", "-in", str(csr),
            "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial",
            "-extfile", str(extension), "-out", str(cert),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return key, cert

    server_key, server_cert = certificate("capture", "serverAuth", "IP:127.0.0.1")
    client_key, client_cert = certificate("runtime", "clientAuth")
    other_key, other_cert = certificate("other-runtime", "clientAuth")
    fingerprint = hashlib.sha256(
        ssl.PEM_cert_to_DER_cert(client_cert.read_text())
    ).hexdigest()
    binding = {"task_id": "task", "runtime_attempt": 1, "execution_epoch": 2, "pod_uid": "pod"}

    root, runtime = tmp_path / "capture", tmp_path / "runtime"
    root.mkdir()
    runtime.mkdir()
    supervisor = CaptureSupervisor(Settings(
        root=root, runtime=runtime,
        proxy_host="127.0.0.1", proxy_port=unused_port(),
        health_host="127.0.0.1", health_port=unused_port(),
        writer_timeout=1.0, startup_timeout=1.0, shutdown_timeout=1.0,
        maximum_request_body_bytes=1024, maximum_response_body_bytes=1024,
        pcap_segment_bytes=1_000_000, maximum_session_bytes=1024 * 1024,
        maximum_items=100, part_read_chunk_bytes=1024,
        drain_timeout=0.1, seal_timeout=1.0,
        interface="any", tcpdump_bin="tcpdump", capture_user=None,
        mitmdump_bin="mitmdump", upstream_ca=None, ca_public_file=None,
        control_host=None, control_port=None, control_certificate=None,
        control_private_key=None, control_client_ca=None,
        control_client_fingerprint=None, binding=binding,
    ))
    supervisor.ready = True
    supervisor._write_status()

    port = unused_port()
    server = CaptureControlServer(
        supervisor, host="127.0.0.1", port=port,
        certificate=str(server_cert), private_key=str(server_key),
        client_ca=str(ca_cert), client_fingerprint=fingerprint,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, key, cert):
        context = ssl.create_default_context(cafile=str(ca_cert))
        context.load_cert_chain(cert, key)
        connection = http.client.HTTPSConnection("127.0.0.1", port, context=context, timeout=2)
        connection.request(method, path)
        response = connection.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        connection.close()
        return response.status, headers, body

    try:
        code, _, body = request("GET", "/v1/status", str(client_key), str(client_cert))
        assert code == 200 and json.loads(body)["binding"] == binding
        code, _, body = request("GET", "/v1/status", str(other_key), str(other_cert))
        assert code == 403 and json.loads(body)["code"] == "client_certificate_mismatch"

        code, _, body = request("POST", "/v1/drain", str(client_key), str(client_cert))
        assert code == 200 and json.loads(body)["state"] == "draining"
        code, _, body = request("POST", "/v1/seal", str(client_key), str(client_cert))
        assert code == 200 and json.loads(body)["state"] == "sealed-incomplete"

        code, _, body = request("GET", "/v1/status", str(client_key), str(client_cert))
        assert code == 200 and json.loads(body)["state"] == "sealed-incomplete"
        code, _, body = request(
            "GET", "/v1/items?after=0&limit=10", str(client_key), str(client_cert)
        )
        item = json.loads(body)["items"][0]
        assert code == 200 and item["kind"] == "manifest"
        part = item["parts"][0]
        code, headers, body = request(
            "GET",
            f"/v1/items/{item['item_seq']}/parts/manifest?offset=0&length={part['length']}",
            str(client_key), str(client_cert),
        )
        assert code == 206 and hashlib.sha256(body).hexdigest() == part["sha256"]
        assert headers["X-Wuji-Part-SHA256"] == part["sha256"]
    finally:
        server.close()
        thread.join(timeout=2)
