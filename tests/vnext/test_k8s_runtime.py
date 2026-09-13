"""C1 deployment/verified TLS checks. No PG or Kubernetes runtime is simulated."""

import asyncio
import importlib.util
from pathlib import Path
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from wuji_core.execution.dispatch_outbox import SupervisorHttpTransport
from wuji_core.http.auth import TokenVerifier
from wuji_maf_worker.remote_host import HostTransportError, RemoteWorkerHost
from support.identity_provider import TestIdentityProvider as IdentityProvider


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("c1_k8s_operations", ROOT / "scripts/vnext/k8s.py")
operations = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(operations)


def test_deployment_ca_is_verified_by_worker_httpx_and_controller_urllib(tmp_path):
    operations.certificates(tmp_path / "tls")
    trusted = ssl.create_default_context(cafile=tmp_path / "tls/ca.crt")
    tls_server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_server.load_cert_chain(tmp_path / "tls/runtime.crt", tmp_path / "tls/runtime.key")

    class Handler(BaseHTTPRequestHandler):
        # Transport-only peer: it returns no Task/Run/permit/result assertions.
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"transport":"verified-tls"}')

        do_GET = do_POST

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = tls_server.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever)
    thread.start()
    provider = IdentityProvider(audit_path=tmp_path / "identity.jsonl")
    verifier = TokenVerifier(public_key_pem=provider.public_key_pem,
        issuer=provider.issuer, audience=provider.audience)
    bearer = provider.issue(subject="tls-worker", tenant_id="tls-test", roles=["worker"])
    receiver = {"receiver_id":"tls-receiver", "runtime_attempt":"1",
                "environment_ref":"tls-only", "pod_uid":"not-a-runtime-observation"}
    url = f"https://127.0.0.1:{server.server_port}"
    try:
        host = RemoteWorkerHost(url, run_credential=bearer, token_verifier=verifier,
            receiver=receiver, spool_directory=tmp_path / "worker", ssl_context=trusted)
        assert asyncio.run(host._request_async("tls-probe", {})) == {"transport":"verified-tls"}
        untrusted = RemoteWorkerHost(url, run_credential=bearer, token_verifier=verifier,
            receiver=receiver, spool_directory=tmp_path / "untrusted")
        with pytest.raises(HostTransportError):
            asyncio.run(untrusted._request_async("tls-probe", {}))
        transport = SupervisorHttpTransport(url, authorization=lambda: bearer, ssl_context=trusted)
        with transport.opener.open(url, timeout=3) as response:
            assert response.read() == b'{"transport":"verified-tls"}'
        unchecked = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        unchecked.check_hostname = False
        unchecked.verify_mode = ssl.CERT_NONE
        with pytest.raises(ValueError, match="verified TLS"):
            SupervisorHttpTransport(url, authorization=lambda: bearer, ssl_context=unchecked)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_deployment_bundle_refuses_foreign_namespace_and_ca_private_key(tmp_path):
    import json
    foreign = {"apiVersion":"v1", "kind":"ConfigMap", "metadata":{
        "name":"config", "namespace":"wuji-test", "labels":operations.LABELS}}
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(foreign))
    with pytest.raises(ValueError, match="owned namespace"):
        operations.manifest_objects(bundle)
    with pytest.raises(ValueError, match="CA signing key"):
        operations.secret_manifest("tls", {"tls.key":tmp_path / "ca.key"})
