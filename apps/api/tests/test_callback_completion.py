import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from wuji_api.database import ClaimedHandshake, HandshakeCompletionInvalid
from wuji_api.main import create_app
from wuji_api.settings import Settings


def _settings() -> Settings:
    return Settings(
        profile="local-test",
        auth_database_url="postgresql+psycopg://auth:secret@127.0.0.1:5432/wuji",
        project_database_url="postgresql+psycopg://project:secret@127.0.0.1:5432/wuji",
        public_origin="http://127.0.0.1:4182",
        oidc_issuer="http://127.0.0.1:18083",
        oidc_client_id="wuji-test",
        oidc_client_secret="fixture-secret",
        cursor_signing_key="k" * 32,
    )


class LateCompletionAuthority:
    old_session_token: str | None = None

    async def claim_handshake(self, **_arguments) -> ClaimedHandshake:
        return ClaimedHandshake(
            id=uuid4(), nonce="nonce", code_verifier="verifier", return_to="/projects"
        )

    async def complete_login(self, *, old_session_token: str | None, **_arguments):
        self.old_session_token = old_session_token
        raise HandshakeCompletionInvalid


class ValidOIDC:
    async def exchange(self, **_arguments):
        return {"iss": "http://127.0.0.1:18083", "sub": "subject"}


@pytest.mark.unit
def test_late_completion_does_not_modify_browser_cookies() -> None:
    settings = _settings()
    authority = LateCompletionAuthority()
    app = create_app(settings=settings)
    original_runtime = app.state.runtime
    app.state.runtime = SimpleNamespace(
        settings=settings,
        authority=authority,
        oidc=ValidOIDC(),
        cursors=None,
    )
    async def request_callback() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:4182",
            follow_redirects=False,
            cookies={"wuji_oidc_handshake": "new-binding", "wuji_session": "old-session"},
        ) as client:
            return await client.get(
                "/api/v1/auth/callback", params={"state": "old-state", "code": "old-code"}
            )

    try:
        response = asyncio.run(request_callback())
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login?error=UNAUTHENTICATED&trace_id=")
        assert response.headers.get_list("set-cookie") == []
        assert authority.old_session_token == "old-session"
    finally:
        asyncio.run(original_runtime.close())
