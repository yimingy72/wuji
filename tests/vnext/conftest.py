from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import APIRouter, Request

from wuji_core.contracts.knowledge import ClaimProposal
from wuji_core.http.app import create_app
from wuji_core.http.auth import TokenVerifier, current_principal

from support.http_capture import RecordedTestClient
from support.identity_provider import TestIdentityProvider, TestTokens
from support.postgres import RecordedDbConnection, isolated_database


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def audit_directory(request, tmp_path) -> Path:
    durable_root = os.environ.get("WUJI_TEST_EVIDENCE_DIR")
    if durable_root:
        node_digest = hashlib.sha256(request.node.nodeid.encode("utf-8")).hexdigest()[:12]
        directory = Path(durable_root) / node_digest
    else:
        directory = tmp_path
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.fixture
def test_tokens(audit_directory: Path) -> TestTokens:
    provider = TestIdentityProvider(
        audit_path=audit_directory / "identity-events.jsonl"
    )
    return provider.tokens()


@pytest.fixture
def api_client(
    audit_directory: Path, test_tokens: TestTokens
) -> Iterator[RecordedTestClient]:
    router = APIRouter()

    @router.post("/api/v2/test/identity")
    async def identity_probe(request: Request) -> dict[str, object]:
        principal = current_principal(request)
        return {
            "subject": principal.subject,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "payload": await request.json(),
        }

    @router.post("/api/v2/test/claim")
    async def contract_probe(payload: ClaimProposal) -> dict[str, object]:
        return payload.model_dump(mode="json")

    verifier = TokenVerifier(
        public_key_pem=test_tokens.public_key_pem,
        issuer=test_tokens.issuer,
        audience=test_tokens.audience,
    )
    client = RecordedTestClient(
        create_app(token_verifier=verifier, routers=[router]),
        audit_path=audit_directory / "http-exchanges.jsonl",
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def db_conn(audit_directory: Path) -> Iterator[RecordedDbConnection]:
    with isolated_database(
        manifest_path=REPOSITORY_ROOT / "work" / "vnext" / "postgres-fixture.json",
        audit_path=audit_directory / "postgres-events.jsonl",
    ) as connection:
        yield connection
