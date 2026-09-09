"""Authlib-backed OIDC discovery, authorization, token exchange, and strict claims validation."""

from __future__ import annotations

import logging
from typing import Any

from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import CodeIDToken

from wuji_api.security import pkce_challenge
from wuji_api.settings import Settings

security_logger = logging.getLogger("wuji.security")


class OIDCProtocolError(RuntimeError):
    pass


class OIDCDependencyError(RuntimeError):
    """The configured provider could not complete a required network exchange."""


class StrictCodeIDToken(CodeIDToken):
    """Keep Authlib's nonce validation enabled even for a hostile compatibility claim."""

    def get(self, key: str, default: Any = None) -> Any:
        if key == "nonce_supported":
            return None
        return super().get(key, default)


class OIDCClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        oauth = OAuth()
        self.remote = oauth.register(
            name="wuji",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret.get_secret_value(),
            server_metadata_url=f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email"},
        )

    async def metadata(self) -> dict[str, Any]:
        try:
            metadata = await self.remote.load_server_metadata()
        except Exception as error:
            raise OIDCDependencyError from error
        if metadata.get("issuer") != self.settings.oidc_issuer:
            raise OIDCProtocolError("discovery issuer mismatch")
        algorithms = metadata.get("id_token_signing_alg_values_supported", [])
        if "RS256" not in algorithms:
            raise OIDCProtocolError("issuer does not advertise RS256")
        # parse_id_token consumes this list when creating Authlib's JWS registry.
        metadata["id_token_signing_alg_values_supported"] = ["RS256"]
        return metadata

    async def authorization_url(
        self, *, state: str, nonce: str, code_verifier: str
    ) -> str:
        await self.metadata()
        try:
            result = await self.remote.create_authorization_url(
                redirect_uri=self.settings.redirect_uri,
                state=state,
                nonce=nonce,
                code_challenge=pkce_challenge(code_verifier),
                code_challenge_method="S256",
                response_mode="query",
            )
            return result["url"]
        except Exception as error:
            raise OIDCProtocolError from error

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> dict[str, Any]:
        metadata = await self.metadata()
        token_endpoint = metadata.get("token_endpoint")
        if not token_endpoint:
            raise OIDCProtocolError("issuer metadata has no token endpoint")
        try:
            token = await self.remote.fetch_access_token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=self.settings.redirect_uri,
                code_verifier=code_verifier,
            )
        except Exception as error:
            security_logger.warning(
                "oidc_exchange_unavailable error_type=%s cause_type=%s",
                error.__class__.__name__,
                error.__cause__.__class__.__name__ if error.__cause__ is not None else "none",
            )
            raise OIDCDependencyError from error
        if "id_token" not in token:
            raise OIDCProtocolError("token response has no ID Token")
        try:
            claims_options = {
                "iss": {
                    "essential": True,
                    "value": self.settings.oidc_issuer,
                },
                "aud": {
                    "essential": True,
                    "value": self.settings.oidc_client_id,
                },
                "nonce": {
                    "essential": True,
                    "value": nonce,
                },
            }
            user_info = await self.remote.parse_id_token(
                token,
                nonce=nonce,
                claims_options=claims_options,
                claims_cls=StrictCodeIDToken,
                leeway=0,
            )
            if user_info.get("iss") != self.settings.oidc_issuer:
                raise OIDCProtocolError("validated issuer mismatch")
            if not isinstance(user_info.get("sub"), str) or not user_info["sub"]:
                raise OIDCProtocolError("validated ID token has no subject")
            return dict(user_info)
        except OIDCProtocolError:
            raise
        except Exception as error:
            security_logger.warning(
                "oidc_exchange_rejected error_type=%s cause_type=%s",
                error.__class__.__name__,
                error.__cause__.__class__.__name__ if error.__cause__ is not None else "none",
            )
            raise OIDCProtocolError from error
