from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey


@dataclass(frozen=True, slots=True)
class TestTokens:
    agent: str
    collector: str
    assessor: str
    reader: str
    tampered: str
    wrong_issuer: str
    wrong_audience: str
    expired: str
    public_key_pem: bytes
    issuer: str
    audience: str
    public_key_sha256: str


class TestIdentityProvider:
    """Independent synthetic issuer whose private key never leaves this object."""

    def __init__(self, *, audit_path: Path) -> None:
        self.issuer = "https://identity.fixture.invalid"
        self.audience = "wuji-vnext-tests"
        self._audit_path = audit_path
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._signing_key = RSAKey.import_key(self._private_key)
        self.public_key_pem = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        public_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.public_key_sha256 = hashlib.sha256(public_der).hexdigest()

    def issue(
        self,
        *,
        subject: str,
        tenant_id: str,
        roles: list[str],
        issuer: str | None = None,
        audience: str | None = None,
        expires_in: int = 300,
    ) -> str:
        now = int(time.time())
        token_id = str(uuid4())
        effective_issuer = issuer or self.issuer
        effective_audience = audience or self.audience
        claims = {
            "iss": effective_issuer,
            "aud": effective_audience,
            "sub": subject,
            "tenant_id": tenant_id,
            "roles": roles,
            "iat": now,
            "nbf": now - 1,
            "exp": now + expires_in,
            "jti": token_id,
        }
        token = jwt.encode(
            {"alg": "RS256", "kid": self.public_key_sha256[:16]},
            claims,
            self._signing_key,
            algorithms=["RS256"],
        )
        with self._audit_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "issuer": effective_issuer,
                        "audience": effective_audience,
                        "subject": subject,
                        "tenant_id": tenant_id,
                        "roles": roles,
                        "token_id": token_id,
                        "public_key_sha256": self.public_key_sha256,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
        return token

    def tokens(self) -> TestTokens:
        agent = self.issue(
            subject="agent-fixture", tenant_id="tenant-fixture", roles=["agent"]
        )
        collector = self.issue(
            subject="collector-fixture",
            tenant_id="tenant-fixture",
            roles=["collector"],
        )
        assessor = self.issue(
            subject="assessor-fixture",
            tenant_id="tenant-fixture",
            roles=["assessor"],
        )
        reader = self.issue(
            subject="reader-fixture", tenant_id="tenant-fixture", roles=["reader"]
        )
        parts = agent.split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        wrong_issuer = self.issue(
            subject="wrong-issuer-fixture",
            tenant_id="tenant-fixture",
            roles=["agent"],
            issuer="https://other.fixture.invalid",
        )
        wrong_audience = self.issue(
            subject="wrong-audience-fixture",
            tenant_id="tenant-fixture",
            roles=["agent"],
            audience="another-service",
        )
        expired = self.issue(
            subject="expired-fixture",
            tenant_id="tenant-fixture",
            roles=["agent"],
            expires_in=-30,
        )
        return TestTokens(
            agent=agent,
            collector=collector,
            assessor=assessor,
            reader=reader,
            tampered=".".join(parts),
            wrong_issuer=wrong_issuer,
            wrong_audience=wrong_audience,
            expired=expired,
            public_key_pem=self.public_key_pem,
            issuer=self.issuer,
            audience=self.audience,
            public_key_sha256=self.public_key_sha256,
        )
