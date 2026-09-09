#!/usr/bin/env python3
"""Loopback-only OIDC issuer used by the Phase 1A protocol tests.

The fixture deliberately implements the public authorization-code/PKCE surface
instead of importing Wuji internals.  A test can select one token defect at a
time through the authenticated loopback control endpoint.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import stat
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from authlib.jose import JsonWebToken
from cryptography.hazmat.primitives.asymmetric import rsa


ALLOWED_SCENARIOS = {
    "valid",
    "authorization_error",
    "bad_nonce",
    "missing_nonce",
    "nonce_supported_false_wrong_nonce",
    "wrong_issuer",
    "wrong_audience_azp",
    "bad_signature",
    "wrong_algorithm",
    "expired",
    "future_nbf",
    "discovery_wrong_issuer",
    "blocked_valid",
    "token_error",
}


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def public_jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, str]:
    numbers = key.public_key().public_numbers()
    width = (key.key_size + 7) // 8
    exponent_width = (numbers.e.bit_length() + 7) // 8
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": b64url(numbers.n.to_bytes(width, "big")),
        "e": b64url(numbers.e.to_bytes(exponent_width, "big")),
    }


@dataclass(frozen=True)
class IssuedCode:
    client_id: str
    redirect_uri: str
    nonce: str
    code_challenge: str
    scenario: str


class State:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self.issuer = manifest["urls"]["issuer_fixture"].rstrip("/")
        self.client_id = manifest["credentials"]["oidc_fixture"]["client_id"]
        self.client_secret = manifest["credentials"]["oidc_fixture"]["client_secret"]
        self.control_token = manifest["credentials"]["oidc_fixture"]["control_token"]
        self.users = manifest["seed_users"]
        self.user_symbol = "protocol_user"
        self.callback = f'{manifest["urls"]["web"].rstrip("/")}/api/v1/auth/callback'
        self.scenario = "valid"
        self.codes: dict[str, IssuedCode] = {}
        self.authorization_count = 0
        self.token_count = 0
        self.lock = threading.Lock()
        self.token_waiting = threading.Event()
        self.token_release = threading.Event()
        self.signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = "phase-1a-fixture"

    def reset(self, scenario: str, user_symbol: str = "protocol_user") -> None:
        if scenario not in ALLOWED_SCENARIOS:
            raise ValueError("unknown scenario")
        if user_symbol not in self.users or "fixture_sub" not in self.users[user_symbol]:
            raise ValueError("unknown fixture user")
        with self.lock:
            self.scenario = scenario
            self.user_symbol = user_symbol
            self.codes.clear()
            self.authorization_count = 0
            self.token_count = 0
            self.token_waiting.clear()
            self.token_release.clear()


def read_manifest(path: Path) -> dict[str, Any]:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(f"run manifest must not be accessible by group/other (mode={mode:o})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise SystemExit("unsupported run manifest schema")
    return data


class Handler(BaseHTTPRequestHandler):
    server: "IssuerServer"

    def log_message(self, format: str, *args: object) -> None:
        # Never include authorization query values in fixture logs.
        safe_path = urlparse(self.path).path
        print(f"oidc-fixture {self.command} {safe_path}", flush=True)

    def json_response(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        state = self.server.fixture_state
        if parsed.path == "/health":
            self.json_response(HTTPStatus.OK, {"status": "ready"})
            return
        if parsed.path == "/.well-known/openid-configuration":
            issuer = state.issuer
            if state.scenario == "discovery_wrong_issuer":
                issuer = f"{issuer}/unexpected"
            self.json_response(
                HTTPStatus.OK,
                {
                    "issuer": issuer,
                    "authorization_endpoint": f"{state.issuer}/authorize",
                    "token_endpoint": f"{state.issuer}/token",
                    "jwks_uri": f"{state.issuer}/jwks",
                    "response_types_supported": ["code"],
                    "response_modes_supported": ["query"],
                    "grant_types_supported": ["authorization_code"],
                    "subject_types_supported": ["public"],
                    "id_token_signing_alg_values_supported": ["RS256"],
                    "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
                    "code_challenge_methods_supported": ["S256"],
                    "claims_supported": ["iss", "sub", "aud", "exp", "iat", "nonce"],
                },
            )
            return
        if parsed.path == "/jwks":
            self.json_response(HTTPStatus.OK, {"keys": [public_jwk(state.signing_key, state.kid)]})
            return
        if parsed.path == "/authorize":
            self.authorize(parse_qs(parsed.query, keep_blank_values=True))
            return
        if parsed.path == "/_control/stats":
            if not self.authorized_control():
                return
            with state.lock:
                payload = {
                    "scenario": state.scenario,
                    "authorization_count": state.authorization_count,
                    "token_count": state.token_count,
                    "outstanding_codes": len(state.codes),
                    "token_waiting": state.token_waiting.is_set(),
                }
            self.json_response(HTTPStatus.OK, payload)
            return
        self.json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/token":
            self.token()
            return
        if parsed.path == "/_control":
            if not self.authorized_control():
                return
            try:
                payload = json.loads(self.read_body())
                if payload.get("action") == "release_token":
                    self.server.fixture_state.token_release.set()
                    self.json_response(HTTPStatus.OK, {"released": True})
                    return
                self.server.fixture_state.reset(payload["scenario"], payload.get("user", "protocol_user"))
            except (KeyError, ValueError, json.JSONDecodeError):
                self.json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid_scenario"})
                return
            self.json_response(
                HTTPStatus.OK,
                {
                    "scenario": self.server.fixture_state.scenario,
                    "user": self.server.fixture_state.user_symbol,
                },
            )
            return
        self.json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def authorized_control(self) -> bool:
        expected = f"Bearer {self.server.fixture_state.control_token}"
        if secrets.compare_digest(self.headers.get("Authorization", ""), expected):
            return True
        self.json_response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

    @staticmethod
    def one(query: dict[str, list[str]], name: str) -> str:
        values = query.get(name, [])
        if len(values) != 1 or not values[0]:
            raise ValueError(name)
        return values[0]

    def authorize(self, query: dict[str, list[str]]) -> None:
        state = self.server.fixture_state
        try:
            client_id = self.one(query, "client_id")
            redirect_uri = self.one(query, "redirect_uri")
            response_type = self.one(query, "response_type")
            response_mode = self.one(query, "response_mode")
            oauth_state = self.one(query, "state")
            nonce = self.one(query, "nonce")
            challenge = self.one(query, "code_challenge")
            challenge_method = self.one(query, "code_challenge_method")
            if client_id != state.client_id or redirect_uri != state.callback:
                raise ValueError("client")
            if response_type != "code" or response_mode != "query" or challenge_method != "S256":
                raise ValueError("flow")
        except ValueError:
            self.json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
            return
        with state.lock:
            state.authorization_count += 1
            scenario = state.scenario
            user_symbol = state.user_symbol
        if scenario == "authorization_error":
            self.redirect(f"{redirect_uri}?{urlencode({'error': 'access_denied', 'state': oauth_state})}")
            return
        code = f"phase1a-code-log-canary-{secrets.token_urlsafe(24)}"
        with state.lock:
            state.codes[code] = IssuedCode(client_id, redirect_uri, nonce, challenge, f"{scenario}:{user_symbol}")
        self.redirect(f"{redirect_uri}?{urlencode({'code': code, 'state': oauth_state})}")

    def token(self) -> None:
        state = self.server.fixture_state
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" not in content_type:
            self.json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
            return
        form = parse_qs(self.read_body().decode(), keep_blank_values=True)
        try:
            code = self.one(form, "code")
            grant_type = self.one(form, "grant_type")
            verifier = self.one(form, "code_verifier")
            redirect_uri = self.one(form, "redirect_uri")
            client_id = form.get("client_id", [""])[0]
            client_secret = form.get("client_secret", [""])[0]
            authorization = self.headers.get("Authorization", "")
            if authorization.startswith("Basic "):
                raw = base64.b64decode(authorization[6:]).decode()
                client_id, client_secret = raw.split(":", 1)
            if grant_type != "authorization_code":
                raise ValueError("grant")
            if client_id != state.client_id or not secrets.compare_digest(client_secret, state.client_secret):
                raise ValueError("client")
            with state.lock:
                issued = state.codes.pop(code)
            digest = b64url(hashlib.sha256(verifier.encode()).digest())
            if issued.client_id != client_id or issued.redirect_uri != redirect_uri or issued.code_challenge != digest:
                raise ValueError("binding")
        except (KeyError, ValueError):
            self.json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid_grant"})
            return
        with state.lock:
            state.token_count += 1
        now = int(time.time())
        scenario, user_symbol = issued.scenario.split(":", 1)
        if scenario == "token_error":
            self.json_response(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "temporarily_unavailable"})
            return
        if scenario == "blocked_valid":
            state.token_waiting.set()
            if not state.token_release.wait(timeout=15):
                self.json_response(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "temporarily_unavailable"})
                return
            state.token_waiting.clear()
        user = state.users[user_symbol]
        claims: dict[str, Any] = {
            "iss": state.issuer,
            "sub": user["fixture_sub"],
            "aud": state.client_id,
            "exp": now + 300,
            "iat": now,
            "nonce": issued.nonce,
            "preferred_username": user["username"],
            "email": user["email"],
        }
        if scenario == "bad_nonce":
            claims["nonce"] = "not-the-handshake-nonce"
        elif scenario == "missing_nonce":
            claims.pop("nonce")
        elif scenario == "nonce_supported_false_wrong_nonce":
            claims["nonce_supported"] = False
            claims["nonce"] = "not-the-handshake-nonce"
        elif scenario == "wrong_issuer":
            claims["iss"] = f"{state.issuer}/unexpected"
        elif scenario == "wrong_audience_azp":
            claims["aud"] = "another-client"
            claims["azp"] = state.client_id
        elif scenario == "expired":
            claims["exp"] = now - 1
            claims["iat"] = now - 30
        elif scenario == "future_nbf":
            claims["nbf"] = now + 60
        signing_key = state.attacker_key if scenario == "bad_signature" else state.signing_key
        algorithm = "RS512" if scenario == "wrong_algorithm" else "RS256"
        headers = {"alg": algorithm, "kid": state.kid, "typ": "JWT"}
        id_token = JsonWebToken([algorithm]).encode(headers, claims, signing_key).decode()
        self.json_response(
            HTTPStatus.OK,
            {
                "access_token": f"phase1a-access-token-log-canary-{secrets.token_urlsafe(24)}",
                "token_type": "Bearer",
                "expires_in": 300,
                "id_token": id_token,
            },
        )


class IssuerServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], fixture_state: State):
        super().__init__(address, Handler)
        self.fixture_state = fixture_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18083)
    parser.add_argument("--run-file", type=Path, required=True)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("the controlled issuer may only bind to loopback")
    manifest = read_manifest(args.run_file.resolve())
    expected = urlparse(manifest["urls"]["issuer_fixture"])
    if expected.hostname not in {"127.0.0.1", "::1", "localhost"} or expected.port != args.port:
        raise SystemExit("issuer URL and listener do not match")
    server = IssuerServer((args.host, args.port), State(manifest))
    try:
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
