"""Issuer-signed bearer identity verification for vNext ASGI routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import RSAKey
from joserfc.jwt import JWTClaimsRegistry
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class AuthenticationError(ValueError):
    """Raised when a bearer token cannot establish a trusted principal."""


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    token_id: str


class TokenVerifier:
    """Verify tokens from one configured issuer and audience."""

    def __init__(self, *, public_key_pem: bytes, issuer: str, audience: str) -> None:
        self._public_key = RSAKey.import_key(public_key_pem)
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> Principal:
        try:
            decoded = jwt.decode(token, self._public_key, algorithms=["RS256"])
            JWTClaimsRegistry(
                leeway=5,
                iss={"essential": True, "value": self._issuer},
                aud={"essential": True, "value": self._audience},
                sub={"essential": True},
                exp={"essential": True},
                iat={"essential": True},
                nbf={"essential": True},
                jti={"essential": True},
                tenant_id={"essential": True},
                roles={"essential": True},
            ).validate(decoded.claims)
            subject = decoded.claims["sub"]
            tenant_id = decoded.claims["tenant_id"]
            roles = decoded.claims["roles"]
            token_id = decoded.claims["jti"]
            if not isinstance(subject, str) or not subject:
                raise AuthenticationError("invalid subject claim")
            if not isinstance(tenant_id, str) or not tenant_id:
                raise AuthenticationError("invalid tenant claim")
            if (
                not isinstance(roles, list)
                or not roles
                or any(not isinstance(role, str) or not role for role in roles)
            ):
                raise AuthenticationError("invalid roles claim")
            if not isinstance(token_id, str) or not token_id:
                raise AuthenticationError("invalid token identifier claim")
            return Principal(
                subject=subject,
                tenant_id=tenant_id,
                roles=frozenset(roles),
                token_id=token_id,
            )
        except AuthenticationError:
            raise
        except (JoseError, KeyError, TypeError, ValueError) as error:
            raise AuthenticationError("token validation failed") from error


class BearerAuthMiddleware:
    """Authenticate v2 public and internal routes before dispatch."""

    def __init__(self, app: ASGIApp, *, token_verifier: TokenVerifier) -> None:
        self._app = app
        self._token_verifier = token_verifier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        request_id = state.setdefault("request_id", str(uuid4()))
        path = scope.get("path", "")
        if path.startswith(("/api/v2/", "/internal/v2/")):
            token = _bearer_token(scope)
            if token is None:
                await _send_unauthenticated(send, request_id)
                return
            try:
                state["principal"] = self._token_verifier.verify(token)
            except AuthenticationError:
                await _send_unauthenticated(send, request_id)
                return

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    item
                    for item in message.get("headers", [])
                    if item[0].lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, send_with_request_id)


def current_principal(request: Request) -> Principal:
    principal: Any = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise AuthenticationError("request has no authenticated principal")
    return principal


def _bearer_token(scope: Scope) -> str | None:
    values = [
        value.decode("latin-1")
        for name, value in scope.get("headers", [])
        if name.lower() == b"authorization"
    ]
    if len(values) != 1:
        return None
    scheme, separator, token = values[0].partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or " " in token:
        return None
    return token


async def _send_unauthenticated(send: Send, request_id: str) -> None:
    import json

    body = json.dumps(
        {
            "code": "UNAUTHENTICATED",
            "message": "A valid bearer token is required.",
            "request_id": request_id,
            "retryable": False,
            "details": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"x-request-id", request_id.encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
