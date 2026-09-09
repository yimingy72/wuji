from datetime import UTC, datetime
from uuid import uuid4

import pytest
from joserfc.errors import InvalidClaimError, MissingClaimError
from pydantic import ValidationError

from wuji_api.oidc import StrictCodeIDToken
from wuji_api.security import (
    CursorCodec,
    CursorPosition,
    ExpiredCursor,
    InvalidCursor,
    InvalidReturnPath,
    normalize_return_path,
)
from wuji_api.settings import Settings


def settings(**overrides) -> Settings:
    values = {
        "profile": "local-test",
        "auth_database_url": "postgresql+psycopg://auth:secret@127.0.0.1:5432/wuji",
        "project_database_url": "postgresql+psycopg://project:secret@127.0.0.1:5432/wuji",
        "public_origin": "http://127.0.0.1:4182",
        "oidc_issuer": "http://127.0.0.1:18083",
        "oidc_client_id": "wuji-platform",
        "oidc_client_secret": "fixture-secret",
        "cursor_signing_key": "a" * 32,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
def test_return_path_is_limited_to_canonical_project_routes() -> None:
    assert normalize_return_path("/projects/") == "/projects"
    assert (
        normalize_return_path("/projects/018f6f3a-5f8a-7cc0-9a2e-21cb26083762/")
        == "/projects/018f6f3a-5f8a-7cc0-9a2e-21cb26083762"
    )
    for unsafe in (
        "//example.invalid/projects",
        "/projects/../login",
        "/projects\\other",
        "/projects/not-a-uuid",
        "/projects/00000000-0000-0000-0000-000000000001?next=/",
    ):
        with pytest.raises(InvalidReturnPath):
            normalize_return_path(unsafe)


@pytest.mark.unit
def test_cursor_is_signed_bound_and_expires_with_default_lifetime() -> None:
    user_id = uuid4()
    position = CursorPosition(
        created_at=datetime(2026, 9, 9, 10, 0, tzinfo=UTC), project_id=uuid4()
    )
    codec = CursorCodec("k" * 32)
    cursor = codec.encode(
        user_id=user_id, permissions_version=3, limit=50, position=position, now=1000
    )
    assert codec.decode(
        cursor, user_id=user_id, permissions_version=3, limit=50, now=1899
    ) == position
    with pytest.raises(InvalidCursor):
        codec.decode(cursor + "x", user_id=user_id, permissions_version=3, limit=50, now=1001)
    with pytest.raises(InvalidCursor):
        codec.decode(cursor, user_id=uuid4(), permissions_version=3, limit=50, now=1001)
    with pytest.raises(InvalidCursor):
        codec.decode(cursor, user_id=user_id, permissions_version=3, limit=25, now=1001)
    with pytest.raises(ExpiredCursor):
        codec.decode(cursor, user_id=user_id, permissions_version=4, limit=50, now=1001)
    with pytest.raises(ExpiredCursor):
        codec.decode(cursor, user_id=user_id, permissions_version=3, limit=50, now=1900)


@pytest.mark.unit
def test_profiles_reject_insecure_production_and_nonstandard_dev_cursor_ttl() -> None:
    assert settings(cursor_ttl_seconds=1).cursor_ttl_seconds == 1
    with pytest.raises(ValidationError):
        settings(profile="local-dev", cursor_ttl_seconds=1)
    with pytest.raises(ValidationError):
        settings(profile="production")
    production = settings(
        profile="production",
        public_origin="https://wuji.example",
        oidc_issuer="https://identity.example/realms/wuji",
    )
    assert production.secure_cookies


def strict_claims(payload: dict) -> StrictCodeIDToken:
    return StrictCodeIDToken(
        payload,
        {"alg": "RS256"},
        {
            "iss": {"essential": True, "value": "https://issuer.example"},
            "aud": {"essential": True, "value": "wuji"},
            "nonce": {"essential": True, "value": "expected"},
        },
        {"client_id": "wuji", "nonce": "expected"},
    )


@pytest.mark.unit
def test_authlib_claims_keep_nonce_and_audience_strict() -> None:
    valid = {
        "iss": "https://issuer.example",
        "sub": "subject",
        "aud": "wuji",
        "exp": 200,
        "iat": 100,
        "nonce": "expected",
        "nonce_supported": False,
    }
    strict_claims(valid).validate(now=100, leeway=0)

    missing_nonce = valid | {"nonce_supported": False}
    missing_nonce.pop("nonce")
    with pytest.raises(MissingClaimError):
        strict_claims(missing_nonce).validate(now=100, leeway=0)

    with pytest.raises(InvalidClaimError):
        strict_claims(valid | {"nonce": "wrong", "nonce_supported": False}).validate(
            now=100, leeway=0
        )
    with pytest.raises(InvalidClaimError):
        strict_claims(valid | {"aud": "other", "azp": "wuji"}).validate(now=100, leeway=0)
