"""Async auth and project authority access through separate database roles."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from wuji_api.database_admin import USER_LOCK_SEED
from wuji_api.security import CursorPosition, opaque_token, token_hash
from wuji_api.settings import Settings

EXPECTED_REVISION = "20260909_0001"


class AuthorityUnavailable(RuntimeError):
    pass


class HandshakeInProgress(RuntimeError):
    pass


@dataclass(frozen=True)
class ClaimedHandshake:
    id: UUID
    nonce: str
    code_verifier: str
    return_to: str


@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: UUID
    user_id: UUID
    display_name: str
    csrf_token: str
    expires_at: datetime
    permissions_version: int


@dataclass(frozen=True)
class CreatedSession:
    token: str
    session: AuthenticatedSession


@dataclass(frozen=True)
class ProjectRecord:
    id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime


class DatabaseAuthority:
    def __init__(self, settings: Settings):
        engine_options = {
            "pool_pre_ping": True,
            "pool_reset_on_return": "rollback",
            "hide_parameters": True,
        }
        self.auth: AsyncEngine = create_async_engine(
            settings.auth_database_url.get_secret_value(), **engine_options
        )
        self.project: AsyncEngine = create_async_engine(
            settings.project_database_url.get_secret_value(), **engine_options
        )

    async def close(self) -> None:
        await self.auth.dispose()
        await self.project.dispose()

    async def ready(self) -> bool:
        try:
            for engine in (self.auth, self.project):
                async with engine.connect() as connection:
                    revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
                    if revision != EXPECTED_REVISION:
                        return False
            return True
        except SQLAlchemyError:
            return False

    async def begin_handshake(
        self,
        *,
        existing_binding_hash: str | None,
        handshake_id: UUID,
        state_hash_value: str,
        binding_hash: str,
        nonce: str,
        code_verifier: str,
        return_to: str,
    ) -> None:
        try:
            async with self.auth.begin() as connection:
                if existing_binding_hash is not None:
                    status = await connection.scalar(
                        text(
                            "SELECT status FROM oidc_handshakes "
                            "WHERE binding_hash = :binding_hash AND expires_at > clock_timestamp() "
                            "ORDER BY created_at DESC LIMIT 1 FOR UPDATE"
                        ),
                        {"binding_hash": existing_binding_hash},
                    )
                    if status == "exchanging":
                        raise HandshakeInProgress
                    await connection.execute(
                        text(
                            "UPDATE oidc_handshakes SET status = 'replaced', consumed_at = clock_timestamp() "
                            "WHERE binding_hash = :binding_hash AND status = 'pending'"
                        ),
                        {"binding_hash": existing_binding_hash},
                    )
                await connection.execute(
                    text(
                        "INSERT INTO oidc_handshakes "
                        "(id, state_hash, binding_hash, nonce, code_verifier, return_to, expires_at) "
                        "VALUES (:id, :state_hash, :binding_hash, :nonce, :code_verifier, :return_to, "
                        "clock_timestamp() + interval '5 minutes')"
                    ),
                    {
                        "id": handshake_id,
                        "state_hash": state_hash_value,
                        "binding_hash": binding_hash,
                        "nonce": nonce,
                        "code_verifier": code_verifier,
                        "return_to": return_to,
                    },
                )
        except HandshakeInProgress:
            raise
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def claim_handshake(self, *, state_hash_value: str, binding_hash: str) -> ClaimedHandshake | None:
        try:
            async with self.auth.begin() as connection:
                row = (
                    await connection.execute(
                        text(
                            "UPDATE oidc_handshakes "
                            "SET status = 'exchanging', claimed_at = clock_timestamp() "
                            "WHERE state_hash = :state_hash AND binding_hash = :binding_hash "
                            "AND status = 'pending' AND expires_at > clock_timestamp() "
                            "RETURNING id, nonce, code_verifier, return_to"
                        ),
                        {"state_hash": state_hash_value, "binding_hash": binding_hash},
                    )
                ).mappings().one_or_none()
            if row is None:
                return None
            return ClaimedHandshake(
                id=row["id"],
                nonce=row["nonce"],
                code_verifier=row["code_verifier"],
                return_to=row["return_to"],
            )
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def fail_handshake(self, handshake_id: UUID, *, reason: str) -> None:
        try:
            async with self.auth.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE oidc_handshakes SET status = 'failed', consumed_at = clock_timestamp() "
                        "WHERE id = :id AND status = 'exchanging'"
                    ),
                    {"id": handshake_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO identity_audit (user_id, action, actor, details) "
                        "VALUES (NULL, 'oidc.failed', 'oidc-callback', "
                        "jsonb_build_object('reason', CAST(:reason AS text)))"
                    ),
                    {"reason": reason},
                )
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def complete_login(
        self,
        *,
        handshake_id: UUID,
        issuer: str,
        subject: str,
        old_session_token: str | None,
    ) -> CreatedSession | None:
        raw_token = opaque_token()
        csrf_token = opaque_token()
        try:
            async with self.auth.begin() as connection:
                user_id = await connection.scalar(
                    text(
                        "SELECT user_id FROM external_identities "
                        "WHERE issuer = :issuer AND subject = :subject"
                    ),
                    {"issuer": issuer, "subject": subject},
                )
                if user_id is None:
                    await connection.execute(
                        text(
                            "UPDATE oidc_handshakes SET status = 'failed', consumed_at = clock_timestamp() "
                            "WHERE id = :id AND status = 'exchanging'"
                        ),
                        {"id": handshake_id},
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO identity_audit (user_id, action, actor, details) "
                            "VALUES (NULL, 'oidc.forbidden', 'oidc-callback', "
                            "jsonb_build_object('reason', 'identity_not_provisioned'))"
                        )
                    )
                    return None
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, :seed))"),
                    {"user_id": str(user_id), "seed": USER_LOCK_SEED},
                )
                user = (
                    await connection.execute(
                        text(
                            "SELECT id, display_name, permissions_version FROM users "
                            "WHERE id = :id AND enabled"
                        ),
                        {"id": user_id},
                    )
                ).mappings().one_or_none()
                if user is None:
                    await connection.execute(
                        text(
                            "UPDATE oidc_handshakes SET status = 'failed', consumed_at = clock_timestamp() "
                            "WHERE id = :id AND status = 'exchanging'"
                        ),
                        {"id": handshake_id},
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO identity_audit (user_id, action, actor, details) "
                            "VALUES (:user_id, 'oidc.forbidden', 'oidc-callback', "
                            "jsonb_build_object('reason', 'user_disabled'))"
                        ),
                        {"user_id": user_id},
                    )
                    return None
                if old_session_token:
                    await connection.execute(
                        text(
                            "UPDATE sessions SET revoked_at = clock_timestamp() "
                            "WHERE token_hash = :token_hash AND revoked_at IS NULL"
                        ),
                        {"token_hash": token_hash(old_session_token)},
                    )
                session_id = uuid4()
                session_row = (
                    await connection.execute(
                        text(
                            "INSERT INTO sessions "
                            "(id, token_hash, user_id, csrf_token, absolute_expires_at) "
                            "VALUES (:id, :token_hash, :user_id, :csrf_token, "
                            "clock_timestamp() + interval '8 hours') "
                            "RETURNING created_at, last_seen_at, absolute_expires_at"
                        ),
                        {
                            "id": session_id,
                            "token_hash": token_hash(raw_token),
                            "user_id": user_id,
                            "csrf_token": csrf_token,
                        },
                    )
                ).mappings().one()
                await connection.execute(
                    text(
                        "UPDATE oidc_handshakes SET status = 'consumed', consumed_at = clock_timestamp() "
                        "WHERE id = :id AND status = 'exchanging'"
                    ),
                    {"id": handshake_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO identity_audit (user_id, action, actor, details) "
                        "VALUES (:user_id, 'session.created', 'oidc-callback', '{}'::jsonb)"
                    ),
                    {"user_id": user_id},
                )
                expires_at = min(
                    session_row["absolute_expires_at"],
                    session_row["last_seen_at"] + timedelta(minutes=30),
                )
                return CreatedSession(
                    token=raw_token,
                    session=AuthenticatedSession(
                        session_id=session_id,
                        user_id=user["id"],
                        display_name=user["display_name"],
                        csrf_token=csrf_token,
                        expires_at=expires_at,
                        permissions_version=int(user["permissions_version"]),
                    ),
                )
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def authenticate(self, raw_token: str) -> AuthenticatedSession | None:
        try:
            async with self.auth.begin() as connection:
                row = (
                    await connection.execute(
                        text(
                            "SELECT s.id AS session_id, s.user_id, s.csrf_token, s.absolute_expires_at, "
                            "u.display_name, u.permissions_version "
                            "FROM sessions s JOIN users u ON u.id = s.user_id "
                            "WHERE s.token_hash = :token_hash AND s.revoked_at IS NULL AND u.enabled "
                            "AND clock_timestamp() < s.absolute_expires_at "
                            "AND clock_timestamp() < s.last_seen_at + interval '30 minutes' "
                            "FOR UPDATE OF s"
                        ),
                        {"token_hash": token_hash(raw_token)},
                    )
                ).mappings().one_or_none()
                if row is None:
                    return None
                last_seen_at = await connection.scalar(
                    text(
                        "UPDATE sessions SET last_seen_at = clock_timestamp() "
                        "WHERE id = :id RETURNING last_seen_at"
                    ),
                    {"id": row["session_id"]},
                )
                expires_at = min(
                    row["absolute_expires_at"],
                    last_seen_at + timedelta(minutes=30),
                )
                return AuthenticatedSession(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    display_name=row["display_name"],
                    csrf_token=row["csrf_token"],
                    expires_at=expires_at,
                    permissions_version=int(row["permissions_version"]),
                )
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def revoke_session(self, raw_token: str, csrf_token: str) -> str:
        """Return revoked, unauthenticated, or forbidden after a committed transaction."""

        try:
            async with self.auth.begin() as connection:
                row = (
                    await connection.execute(
                        text(
                            "SELECT s.id, s.user_id, s.csrf_token FROM sessions s "
                            "JOIN users u ON u.id = s.user_id "
                            "WHERE s.token_hash = :token_hash AND s.revoked_at IS NULL AND u.enabled "
                            "AND clock_timestamp() < s.absolute_expires_at "
                            "AND clock_timestamp() < s.last_seen_at + interval '30 minutes' "
                            "FOR UPDATE OF s"
                        ),
                        {"token_hash": token_hash(raw_token)},
                    )
                ).mappings().one_or_none()
                if row is None:
                    return "unauthenticated"
                if not hmac.compare_digest(row["csrf_token"], csrf_token):
                    return "forbidden"
                await connection.execute(
                    text("UPDATE sessions SET revoked_at = clock_timestamp() WHERE id = :id"),
                    {"id": row["id"]},
                )
                await connection.execute(
                    text(
                        "INSERT INTO identity_audit (user_id, action, actor, details) "
                        "VALUES (:user_id, 'session.revoked', 'browser-logout', '{}'::jsonb)"
                    ),
                    {"user_id": row["user_id"]},
                )
            return "revoked"
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    @staticmethod
    async def _set_user_context(connection: Any, user_id: UUID) -> None:
        await connection.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )

    async def list_projects(
        self,
        *,
        user_id: UUID,
        limit: int,
        position: CursorPosition | None,
    ) -> list[ProjectRecord]:
        try:
            async with self.project.begin() as connection:
                await self._set_user_context(connection, user_id)
                params: dict[str, Any] = {"limit": limit + 1}
                after = ""
                if position is not None:
                    after = "WHERE (created_at, id) < (:created_at, :project_id)"
                    params.update(
                        {"created_at": position.created_at, "project_id": position.project_id}
                    )
                rows = (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, name, created_at FROM projects "
                            f"{after} ORDER BY created_at DESC, id DESC LIMIT :limit"
                        ),
                        params,
                    )
                ).mappings().all()
            return [ProjectRecord(**row) for row in rows]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def get_project(self, *, user_id: UUID, project_id: UUID) -> ProjectRecord | None:
        try:
            async with self.project.begin() as connection:
                await self._set_user_context(connection, user_id)
                tenant_id = await connection.scalar(
                    text("SELECT tenant_id FROM projects WHERE id = :project_id"),
                    {"project_id": project_id},
                )
                if tenant_id is None:
                    return None
                await connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                await connection.execute(
                    text("SELECT set_config('app.project_id', :project_id, true)"),
                    {"project_id": str(project_id)},
                )
                row = (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, name, created_at FROM projects "
                            "WHERE id = :project_id AND tenant_id = :tenant_id"
                        ),
                        {"project_id": project_id, "tenant_id": tenant_id},
                    )
                ).mappings().one_or_none()
            return None if row is None else ProjectRecord(**row)
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error
