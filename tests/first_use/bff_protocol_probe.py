"""Exercise the driver's real A3 BFF protocol with a synthetic API downstream.

The BFF runs as the real ASGI application; no login/route/security logic is
mocked. Only its upstream API transport is synthetic. No PG/MAF/E2E verdict.
The supplied source is hashed before loading; uncommitted code is labelled.
"""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import types

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def probe(source, output, commit=None):
    driver = load(ROOT / "scripts/vnext/first_use_acceptance.py", "a8_control_probe")
    source_bytes = (subprocess.check_output(["git", "show", commit + ":services/wuji-web-gateway/main.py"], cwd=ROOT)
                    if commit else source.read_bytes())
    gateway = types.ModuleType("a8_real_bff")
    gateway.__file__ = str(source)
    sys.modules[gateway.__name__] = gateway
    exec(compile(source_bytes, str(source), "exec"), gateway.__dict__)
    origin = "http://127.0.0.1:44991"
    journal = {"scope": "real_bff_asgi_synthetic_upstream", "gateway_source_sha256": sha256(source_bytes).hexdigest(),
               "gateway_source_path": str(source), "fixed_gateway_commit": commit, "exchanges": [], "status": "in_progress"}
    upstream = []
    def responder(request):
        upstream.append({"method": request.method, "path": request.url.path})
        if request.method == "POST" and request.url.path == "/api/v2/tasks":
            return httpx.Response(201, json={"task_id": "task-a8", "version": "1", "desired_state": "pause", "observed_state": "ready"})
        if request.method == "POST":
            return httpx.Response(202, json={"command_id": "command-a8", "resource_version": "2"})
        return httpx.Response(200, json={"task_id": "task-a8", "version": "2", "observed_state": "running"})
    with tempfile.TemporaryDirectory(prefix="wuji-a8-bff-") as temporary:
        root = Path(temporary)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        signing = root / "signing.key"
        signing.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        session = root / "session.key"
        session.write_bytes(b"synthetic_session_key_32_bytes___")
        access = root / "local-access.token"
        token = "synthetic_local_access_32_characters___"
        access.write_text(token)
        ca = root / "ca.crt"
        ca.write_text("not used by injected synthetic API transport")
        settings = gateway.GatewaySettings.model_validate({
            "schema_version": "wuji.web-gateway.v2", "mode": "local_single_operator",
            "api_base_url": "https://api.fixture.invalid", "ca_file": str(ca),
            "signing_key_file": str(signing), "session_key_file": str(session),
            "local_access_token_file": str(access), "issuer": "fixture", "audience": "fixture",
            "subject": "operator-a8", "tenant_id": "tenant-a8", "project_id": "project-a8",
            "roles": ["operator"], "display_name": "A8 synthetic local operator", "allowed_origins": [origin]})
        app = gateway.create_gateway(settings, client=httpx.AsyncClient(transport=httpx.MockTransport(responder)))
        client = driver.LocalBFFClient(origin, journal, lambda: driver.write_object(output, journal))
        client.close()
        try:
            with TestClient(app, base_url=origin) as asgi:
                client.client = asgi
                session_file = root / "session-private.json"
                assert client.login(session_file=session_file, local_access=token)["mode"] == "local_single_operator"
                from test_task_creation import payload
                created = client.request("POST", "/api/v2/tasks", body=payload(project_id="project-a8"), key="a8-create")
                task = created["task_id"]
                for leaf in ("readiness", "launch"):
                    client.request("GET", f"/api/v2/tasks/{task}/{leaf}")
                for command in ("start", "pause", "cancel"):
                    client.request("POST", f"/api/v2/tasks/{task}/commands",
                                   body=driver.command_payload(command, "1", "synthetic upstream protocol check"), key="a8-" + command)
                # Existing Cookie works without another access exchange.
                assert client.login(session_file=session_file)["authenticated"]
                original_cookie = asgi.cookies.get("wuji_vnext_session")
                assert client.login(session_file=session_file, local_access=token, relogin=True)["authenticated"]
                with TestClient(app, base_url=origin) as old:
                    old.cookies.set("wuji_vnext_session", original_cookie)
                    old_client = driver.LocalBFFClient(origin, journal, lambda: driver.write_object(output, journal))
                    old_client.close()
                    old_client.client = old
                    try:
                        old_client.request("GET", "/auth/session")
                    except driver.DriverError:
                        assert journal["exchanges"][-1]["response_status"] == 401
                    else:
                        raise AssertionError("relogin did not revoke old session")
                client.request("POST", "/auth/logout")
                try:
                    client.request("GET", "/auth/session")
                except driver.DriverError:
                    assert journal["exchanges"][-1]["response_status"] == 401
                else:
                    raise AssertionError("logout did not revoke session")
                assert token not in json.dumps(journal)
                journal["status"] = "observed"
                journal["upstream_route_counts"] = upstream
        except Exception as error:
            journal["status"] = "failed"
            journal["error_class"] = type(error).__name__
            raise
        finally:
            driver.write_object(output, journal)
    return journal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gateway-commit", help="load the fixed source from Git instead of a moving checkout")
    args = parser.parse_args()
    evidence = probe(args.gateway_source, args.output, args.gateway_commit)
    print(json.dumps({"status": evidence["status"], "scope": evidence["scope"], "source_sha256": evidence["gateway_source_sha256"], "http_exchanges": len(evidence["exchanges"])}))
