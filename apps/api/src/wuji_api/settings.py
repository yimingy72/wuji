"""Validated API runtime configuration with explicit local and production profiles."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WUJI_", extra="ignore")

    profile: Literal["local-dev", "local-test", "production"]
    auth_database_url: SecretStr
    project_database_url: SecretStr
    public_origin: str
    oidc_issuer: str
    oidc_client_id: str = Field(min_length=1, max_length=255)
    oidc_client_secret: SecretStr
    cursor_signing_key: SecretStr
    cursor_ttl_seconds: int = Field(default=900, ge=1, le=900)

    @model_validator(mode="after")
    def validate_security_profile(self) -> "Settings":
        public = urlsplit(self.public_origin)
        issuer = urlsplit(self.oidc_issuer)
        auth_database = urlsplit(self.auth_database_url.get_secret_value())
        project_database = urlsplit(self.project_database_url.get_secret_value())
        if public.path not in {"", "/"} or public.query or public.fragment:
            raise ValueError("public origin must not contain a path, query, or fragment")
        if public.username or public.password or issuer.username or issuer.password:
            raise ValueError("configured URLs must not contain credentials")
        if not public.hostname or not issuer.hostname:
            raise ValueError("configured URLs require an explicit hostname")
        for database in (auth_database, project_database):
            if (
                database.scheme != "postgresql+psycopg"
                or not database.hostname
                or not database.username
                or database.password is None
                or database.path in {"", "/"}
            ):
                raise ValueError("runtime database URLs must use authenticated psycopg connections")
        if auth_database.username == project_database.username:
            raise ValueError("auth and project database roles must be distinct")

        loopback_hosts = {"127.0.0.1", "::1"}
        if self.profile == "production":
            if public.scheme != "https" or issuer.scheme != "https":
                raise ValueError("production public origin and issuer must use HTTPS")
            if self.cursor_ttl_seconds != 900:
                raise ValueError("production cursor lifetime is fixed at 900 seconds")
        else:
            if public.scheme not in {"http", "https"} or issuer.scheme not in {"http", "https"}:
                raise ValueError("local URLs must use HTTP or HTTPS")
            if public.hostname not in loopback_hosts or issuer.hostname not in loopback_hosts:
                raise ValueError("local profile URLs must use a loopback hostname")
            if self.profile == "local-dev" and self.cursor_ttl_seconds != 900:
                raise ValueError("development cursor lifetime is fixed at 900 seconds")

        if len(self.cursor_signing_key.get_secret_value()) < 32:
            raise ValueError("cursor signing key must contain at least 32 characters")
        return self

    @property
    def redirect_uri(self) -> str:
        return f"{self.public_origin.rstrip('/')}/api/v1/auth/callback"

    @property
    def secure_cookies(self) -> bool:
        return self.profile == "production" or urlsplit(self.public_origin).scheme == "https"


def optional_settings() -> Settings | None:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError:
        return None
