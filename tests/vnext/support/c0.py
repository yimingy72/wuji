"""C0 transport fixtures: real loopback TLS and complete HTTP capture only."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from wuji_core.http import canonical_json_bytes, strict_json_loads


_DROP_CONNECTION = object()


@dataclass(frozen=True, slots=True)
class TlsServerIdentity:
    ca_file: Path
    certificate_file: Path
    private_key_file: Path


class TestCertificateAuthority:
    """Issue short-lived localhost certificates from an isolated test CA."""

    __test__ = False

    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Wuji C0 test CA")])
        now = datetime.now(UTC)
        self._certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self._key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=2))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(self._key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._key.public_key()
                ),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(self._key, hashes.SHA256())
        )
        self.ca_file = root / "ca.pem"
        self.ca_file.write_bytes(self._certificate.public_bytes(serialization.Encoding.PEM))

    def issue_server(self, name: str) -> TlsServerIdentity:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self._certificate.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=1))
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
                ),
                critical=False,
            )
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._key.public_key()
                ),
                critical=False,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(self._key, hashes.SHA256())
        )
        certificate_file = self.root / f"{name}.crt"
        private_key_file = self.root / f"{name}.key"
        certificate_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        private_key_file.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        private_key_file.chmod(0o600)
        return TlsServerIdentity(self.ca_file, certificate_file, private_key_file)


@dataclass(frozen=True, slots=True)
class NetworkExchange:
    method: str
    path: str
    request_headers: dict[str, str]
    request_body: bytes
    status_code: int | None
    response_headers: dict[str, str]
    response_body: bytes


class ScriptedHttpFault:
    """Change one selected response after the production ASGI call has returned."""

    def __init__(
        self,
        *,
        path: str,
        phase: str,
        mode: str,
        purpose: str | None = None,
        times: int | None = 1,
    ):
        if phase not in {"before", "after"} or mode not in {
            "drop",
            "status_503",
            "bad_ack",
        }:
            raise ValueError("unsupported C0 HTTP fault")
        if times is not None and (type(times) is not int or times < 1):
            raise ValueError("fault count must be positive or unlimited")
        self.path, self.phase, self.mode = path, phase, mode
        self.purpose, self.times = purpose, times
        self.hits = 0
        self._lock = Lock()

    def _matches(self, phase: str, path: str, body: bytes) -> bool:
        if phase != self.phase or path != self.path:
            return False
        if self.purpose is not None:
            try:
                if strict_json_loads(body).get("purpose") != self.purpose:
                    return False
            except (AttributeError, ValueError):
                return False
        with self._lock:
            if self.times is not None and self.hits >= self.times:
                return False
            self.hits += 1
            return True

    def before(self, path: str, body: bytes):
        if self._matches("before", path, body):
            return _DROP_CONNECTION
        return None

    def after(
        self,
        path: str,
        request_body: bytes,
        status: int,
        headers: dict[str, str],
        response_body: bytes,
    ):
        if not self._matches("after", path, request_body):
            return status, headers, response_body
        if self.mode == "drop":
            return _DROP_CONNECTION
        if self.mode == "status_503":
            body = canonical_json_bytes(
                {"code": "CAPABILITY_UNAVAILABLE", "message": "post-commit ACK unavailable"}
            )
            return 503, {"content-type": "application/json"}, body
        value = strict_json_loads(response_body)
        value["permit_digest"] = "0" * 64 if value.get("permit_digest") != "0" * 64 else "1" * 64
        return status, {"content-type": "application/json"}, canonical_json_bytes(value)


class TlsAsgiServer:
    """Serve a production ASGI app through a real TLS socket on an ephemeral port."""

    def __init__(
        self,
        app,
        *,
        identity: TlsServerIdentity,
        audit_path: Path,
        fault: ScriptedHttpFault | None = None,
    ):
        owner = self
        self.app, self.audit_path, self.fault = app, audit_path, fault
        self.exchanges: list[NetworkExchange] = []
        self._lock = Lock()
        audit_path.parent.mkdir(parents=True, exist_ok=True)

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self._handle()

            def _handle(self):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                request_body = self.rfile.read(length)
                path = urlsplit(self.path).path
                request_headers = {
                    key.lower(): value for key, value in self.headers.items()
                }
                if owner.fault is not None and owner.fault.before(path, request_body) is _DROP_CONNECTION:
                    owner._record(
                        NetworkExchange(
                            self.command,
                            self.path,
                            request_headers,
                            request_body,
                            None,
                            {},
                            b"",
                        )
                    )
                    self._drop()
                    return

                request_sent = False
                response_status = 500
                response_headers: list[tuple[bytes, bytes]] = []
                response_chunks: list[bytes] = []

                async def receive():
                    nonlocal request_sent
                    if not request_sent:
                        request_sent = True
                        return {
                            "type": "http.request",
                            "body": request_body,
                            "more_body": False,
                        }
                    return {"type": "http.disconnect"}

                async def send(message):
                    nonlocal response_status, response_headers
                    if message["type"] == "http.response.start":
                        response_status = message["status"]
                        response_headers = list(message.get("headers", []))
                    elif message["type"] == "http.response.body":
                        response_chunks.append(message.get("body", b""))

                split = urlsplit(self.path)
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.3"},
                    "http_version": "1.1",
                    "method": self.command,
                    "scheme": "https",
                    "path": split.path,
                    "raw_path": split.path.encode("ascii"),
                    "query_string": split.query.encode("ascii"),
                    "root_path": "",
                    "headers": [
                        (key.lower().encode("latin-1"), value.encode("latin-1"))
                        for key, value in self.headers.items()
                    ],
                    "client": self.client_address,
                    "server": self.server.server_address,
                }
                asyncio.run(owner.app(scope, receive, send))
                body = b"".join(response_chunks)
                headers = {
                    key.decode("latin-1").lower(): value.decode("latin-1")
                    for key, value in response_headers
                    if key.lower() not in {b"content-length", b"connection"}
                }
                result = (response_status, headers, body)
                if owner.fault is not None:
                    result = owner.fault.after(path, request_body, *result)
                if result is _DROP_CONNECTION:
                    owner._record(
                        NetworkExchange(
                            self.command,
                            self.path,
                            request_headers,
                            request_body,
                            None,
                            {},
                            b"",
                        )
                    )
                    self._drop()
                    return
                response_status, headers, body = result
                headers = {**headers, "content-length": str(len(body)), "connection": "close"}
                owner._record(
                    NetworkExchange(
                        self.command,
                        self.path,
                        request_headers,
                        request_body,
                        response_status,
                        headers,
                        body,
                    )
                )
                self.send_response_only(response_status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                self.close_connection = True

            def _drop(self):
                self.close_connection = True
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()

            def log_message(self, *args):
                return None

        class Server(ThreadingHTTPServer):
            daemon_threads = True

        server = Server(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(identity.certificate_file, identity.private_key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        self.server = server
        self.url = f"https://127.0.0.1:{server.server_address[1]}"
        self.thread = Thread(target=server.serve_forever, daemon=True)
        self.thread.start()

    def _record(self, exchange: NetworkExchange):
        document = {
            "request": {
                "method": exchange.method,
                "url": self.url + exchange.path,
                "headers": exchange.request_headers,
                "body_base64": base64.b64encode(exchange.request_body).decode("ascii"),
            },
            "response": {
                "status_code": exchange.status_code,
                "headers": exchange.response_headers,
                "body_base64": base64.b64encode(exchange.response_body).decode("ascii"),
            },
        }
        with self._lock:
            self.exchanges.append(exchange)
            with self.audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(document, sort_keys=True) + "\n")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
