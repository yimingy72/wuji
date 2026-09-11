"""Async auth and project authority access through separate database roles."""

from __future__ import annotations

import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from wuji_api.database_admin import USER_LOCK_SEED
from wuji_api.scope_policy import evaluate_scope
from wuji_api.security import (
    CursorPosition,
    ScopeCursorPosition,
    TaskCursorPosition,
    opaque_token,
    token_hash,
)
from wuji_api.settings import Settings

EXPECTED_REVISION = "20260911_0005"


class AuthorityUnavailable(RuntimeError):
    pass


class HandshakeInProgress(RuntimeError):
    pass


class HandshakeCompletionInvalid(RuntimeError):
    """The claimed handshake is no longer eligible to create a session."""


class PreviewForbidden(RuntimeError):
    pass


class CommandForbidden(RuntimeError):
    pass


class FreshAuthorityInvalid(RuntimeError):
    pass


class ResourceNotFound(RuntimeError):
    pass


class PreviewExpired(RuntimeError):
    pass


class VersionConflict(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class InvalidTransition(RuntimeError):
    pass


class ScopeDenied(RuntimeError):
    pass


class CommandValidationFailed(RuntimeError):
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
    role: str


@dataclass(frozen=True)
class ScopeRecord:
    policy_id: UUID
    version: int
    tenant_id: UUID
    project_id: UUID
    authorization_id: UUID
    policy_hash: str
    scope: dict[str, Any]
    valid_from: datetime
    valid_until: datetime
    revoked_at: datetime | None
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

    async def fail_handshake(self, handshake_id: UUID, *, reason: str) -> bool:
        try:
            async with self.auth.begin() as connection:
                failed = await connection.scalar(
                    text(
                        "UPDATE oidc_handshakes SET status = 'failed', consumed_at = clock_timestamp() "
                        "WHERE id = :id AND status IN ('pending', 'exchanging') "
                        "AND expires_at > clock_timestamp() RETURNING id"
                    ),
                    {"id": handshake_id},
                )
                if failed is None:
                    return False
                await connection.execute(
                    text(
                        "INSERT INTO identity_audit (user_id, action, actor, details) "
                        "VALUES (NULL, 'oidc.failed', 'oidc-callback', "
                        "jsonb_build_object('reason', CAST(:reason AS text)))"
                    ),
                    {"reason": reason},
                )
            return True
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
                    failed = await connection.scalar(
                        text(
                            "UPDATE oidc_handshakes SET status = 'failed', consumed_at = clock_timestamp() "
                            "WHERE id = :id AND status = 'exchanging' "
                            "AND expires_at > clock_timestamp() RETURNING id"
                        ),
                        {"id": handshake_id},
                    )
                    if failed is None:
                        raise HandshakeCompletionInvalid
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
                consumed = await connection.scalar(
                    text(
                        "UPDATE oidc_handshakes SET status = 'consumed', "
                        "consumed_at = clock_timestamp() "
                        "WHERE id = :id AND status = 'exchanging' "
                        "AND expires_at > clock_timestamp() RETURNING id"
                    ),
                    {"id": handshake_id},
                )
                if consumed is None:
                    raise HandshakeCompletionInvalid
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
                        "UPDATE sessions AS s SET last_seen_at = clock_timestamp() "
                        "FROM users AS u WHERE s.id = :id AND u.id = s.user_id "
                        "AND s.revoked_at IS NULL AND u.enabled "
                        "AND clock_timestamp() < s.absolute_expires_at "
                        "AND clock_timestamp() < s.last_seen_at + interval '30 minutes' "
                        "RETURNING s.last_seen_at"
                    ),
                    {"id": row["session_id"]},
                )
                if last_seen_at is None:
                    return None
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

    @asynccontextmanager
    async def _fresh_user_lock(
        self, user_id: UUID
    ) -> AsyncIterator[int]:
        """Hold the management-coordinated user lock across one project write."""

        try:
            async with self.auth.begin() as connection:
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, :seed))"),
                    {"user_id": str(user_id), "seed": USER_LOCK_SEED},
                )
                row = (
                    await connection.execute(
                        text("SELECT enabled, permissions_version FROM users WHERE id = :user_id"),
                        {"user_id": user_id},
                    )
                ).mappings().one_or_none()
                if row is None or not row["enabled"]:
                    raise FreshAuthorityInvalid
                yield int(row["permissions_version"])
        except FreshAuthorityInvalid:
            raise
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def _authorize_project_connection(
        self, connection: Any, *, user_id: UUID, project_id: UUID
    ) -> ProjectRecord | None:
        await self._set_user_context(connection, user_id)
        row = (
            await connection.execute(
                text(
                    "SELECT p.id, p.tenant_id, p.name, p.created_at, "
                    "CASE WHEN tm.role = 'operator' AND pm.role = 'operator' "
                    "THEN 'operator' ELSE 'viewer' END AS role "
                    "FROM projects p "
                    "JOIN project_memberships pm ON pm.tenant_id = p.tenant_id "
                    "AND pm.project_id = p.id AND pm.user_id = :user_id AND pm.enabled "
                    "JOIN tenant_memberships tm ON tm.tenant_id = p.tenant_id "
                    "AND tm.user_id = pm.user_id AND tm.enabled "
                    "WHERE p.id = :project_id"
                ),
                {"user_id": user_id, "project_id": project_id},
            )
        ).mappings().one_or_none()
        if row is None:
            return None
        await connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": str(row["tenant_id"])},
        )
        await connection.execute(
            text("SELECT set_config('app.project_id', :project_id, true)"),
            {"project_id": str(project_id)},
        )
        return ProjectRecord(**row)

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
                    after = "WHERE (p.created_at, p.id) < (:created_at, :project_id)"
                    params.update(
                        {"created_at": position.created_at, "project_id": position.project_id}
                    )
                rows = (
                    await connection.execute(
                        text(
                            "SELECT p.id, p.tenant_id, p.name, p.created_at, "
                            "CASE WHEN tm.role = 'operator' AND pm.role = 'operator' "
                            "THEN 'operator' ELSE 'viewer' END AS role "
                            "FROM projects p "
                            "JOIN project_memberships pm ON pm.tenant_id = p.tenant_id "
                            "AND pm.project_id = p.id AND pm.user_id = "
                            "NULLIF(current_setting('app.user_id', true), '')::uuid AND pm.enabled "
                            "JOIN tenant_memberships tm ON tm.tenant_id = p.tenant_id "
                            "AND tm.user_id = pm.user_id AND tm.enabled "
                            f"{after} ORDER BY p.created_at DESC, p.id DESC LIMIT :limit"
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
                            "SELECT p.id, p.tenant_id, p.name, p.created_at, "
                            "CASE WHEN tm.role = 'operator' AND pm.role = 'operator' "
                            "THEN 'operator' ELSE 'viewer' END AS role "
                            "FROM projects p "
                            "JOIN project_memberships pm ON pm.tenant_id = p.tenant_id "
                            "AND pm.project_id = p.id AND pm.user_id = "
                            "NULLIF(current_setting('app.user_id', true), '')::uuid AND pm.enabled "
                            "JOIN tenant_memberships tm ON tm.tenant_id = p.tenant_id "
                            "AND tm.user_id = pm.user_id AND tm.enabled "
                            "WHERE p.id = :project_id AND p.tenant_id = :tenant_id"
                        ),
                        {"project_id": project_id, "tenant_id": tenant_id},
                    )
                ).mappings().one_or_none()
            return None if row is None else ProjectRecord(**row)
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def list_scopes(
        self,
        *,
        user_id: UUID,
        project: ProjectRecord,
        limit: int,
        position: ScopeCursorPosition | None,
    ) -> list[ScopeRecord] | None:
        try:
            async with self.project.begin() as connection:
                await self._set_user_context(connection, user_id)
                await connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(project.tenant_id)},
                )
                await connection.execute(
                    text("SELECT set_config('app.project_id', :project_id, true)"),
                    {"project_id": str(project.id)},
                )
                still_visible = await connection.scalar(
                    text(
                        "SELECT id FROM projects WHERE tenant_id = :tenant_id "
                        "AND id = :project_id"
                    ),
                    {"tenant_id": project.tenant_id, "project_id": project.id},
                )
                if still_visible is None:
                    return None
                params: dict[str, Any] = {
                    "tenant_id": project.tenant_id,
                    "project_id": project.id,
                    "limit": limit + 1,
                }
                after = ""
                if position is not None:
                    after = (
                        "AND (sp.created_at, sp.policy_id, sp.version) "
                        "< (:created_at, :policy_id, :version)"
                    )
                    params.update(
                        {
                            "created_at": position.created_at,
                            "policy_id": position.policy_id,
                            "version": position.version,
                        }
                    )
                rows = (
                    await connection.execute(
                        text(
                            "SELECT sp.policy_id, sp.version, sp.tenant_id, sp.project_id, "
                            "sp.authorization_id, sp.policy_hash, sp.scope, sp.created_at, "
                            "a.valid_from, a.valid_until, a.revoked_at "
                            "FROM scope_policy_versions sp "
                            "JOIN authorization_records a ON a.tenant_id = sp.tenant_id "
                            "AND a.project_id = sp.project_id AND a.id = sp.authorization_id "
                            "WHERE sp.tenant_id = :tenant_id AND sp.project_id = :project_id "
                            "AND a.valid_from <= clock_timestamp() "
                            "AND a.valid_until > clock_timestamp() AND a.revoked_at IS NULL "
                            f"{after} ORDER BY sp.created_at DESC, sp.policy_id DESC, "
                            "sp.version DESC LIMIT :limit"
                        ),
                        params,
                    )
                ).mappings().all()
            return [ScopeRecord(**row) for row in rows]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def create_task_preview(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        normalized_draft: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            async with self.project.begin() as connection:
                await self._set_user_context(connection, user_id)
                project_row = (
                    await connection.execute(
                        text(
                            "SELECT p.id, p.tenant_id, "
                            "CASE WHEN tm.role = 'operator' AND pm.role = 'operator' "
                            "THEN 'operator' ELSE 'viewer' END AS role "
                            "FROM projects p "
                            "JOIN project_memberships pm ON pm.tenant_id = p.tenant_id "
                            "AND pm.project_id = p.id AND pm.user_id = :user_id AND pm.enabled "
                            "JOIN tenant_memberships tm ON tm.tenant_id = p.tenant_id "
                            "AND tm.user_id = pm.user_id AND tm.enabled "
                            "WHERE p.id = :project_id"
                        ),
                        {"user_id": user_id, "project_id": project_id},
                    )
                ).mappings().one_or_none()
                if project_row is None:
                    return None
                if project_row["role"] != "operator":
                    raise PreviewForbidden
                tenant_id = project_row["tenant_id"]
                await connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                await connection.execute(
                    text("SELECT set_config('app.project_id', :project_id, true)"),
                    {"project_id": str(project_id)},
                )
                scope_row = (
                    await connection.execute(
                        text(
                            "SELECT sp.policy_id, sp.version, sp.policy_hash, sp.scope, "
                            "a.valid_from, a.valid_until, a.revoked_at "
                            "FROM scope_policy_versions sp "
                            "JOIN authorization_records a ON a.tenant_id = sp.tenant_id "
                            "AND a.project_id = sp.project_id AND a.id = sp.authorization_id "
                            "WHERE sp.tenant_id = :tenant_id AND sp.project_id = :project_id "
                            "AND sp.policy_id = :policy_id AND sp.version = :version"
                        ),
                        {
                            "tenant_id": tenant_id,
                            "project_id": project_id,
                            "policy_id": UUID(normalized_draft["scope"]["policy_id"]),
                            "version": normalized_draft["scope"]["version"],
                        },
                    )
                ).mappings().one_or_none()
                if scope_row is None:
                    return None
                evaluated = evaluate_scope(
                    normalized_draft,
                    scope_row["scope"],
                    {
                        "valid_from": scope_row["valid_from"],
                        "valid_until": scope_row["valid_until"],
                        "revoked_at": scope_row["revoked_at"],
                    },
                    now=await connection.scalar(text("SELECT clock_timestamp()")),
                )
                preview_id = uuid4()
                await connection.execute(
                    text(
                        "INSERT INTO task_previews "
                        "(id, tenant_id, project_id, user_id, permissions_version, draft, "
                        "input_digest, policy_id, policy_version, policy_hash, effective_scope, "
                        "can_create, blockers, expires_at) VALUES "
                        "(:id, :tenant_id, :project_id, :user_id, :permissions_version, "
                        "CAST(:draft AS jsonb), :input_digest, :policy_id, :policy_version, "
                        ":policy_hash, CAST(:effective_scope AS jsonb), :can_create, "
                        "CAST(:blockers AS jsonb), :expires_at)"
                    ),
                    {
                        "id": preview_id,
                        "tenant_id": tenant_id,
                        "project_id": project_id,
                        "user_id": user_id,
                        "permissions_version": permissions_version,
                        "draft": json.dumps(evaluated["draft"], separators=(",", ":")),
                        "input_digest": evaluated["input_digest"],
                        "policy_id": scope_row["policy_id"],
                        "policy_version": scope_row["version"],
                        "policy_hash": scope_row["policy_hash"],
                        "effective_scope": json.dumps(
                            evaluated["effective_scope"], separators=(",", ":")
                        ),
                        "can_create": evaluated["can_create"],
                        "blockers": json.dumps(evaluated["blockers"], separators=(",", ":")),
                        "expires_at": evaluated["expires_at"],
                    },
                )
            return {"preview_id": preview_id, "project_id": project_id, **evaluated}
        except PreviewForbidden:
            raise
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    @staticmethod
    def _task_select() -> str:
        return (
            "t.id, t.tenant_id, t.project_id, t.draft, t.policy_id, t.policy_version, "
            "t.version, t.state, t.cleanup_state, t.active_calls, t.unknown_calls, "
            "t.egress_state, t.assessment_outcome, t.stop_reason, t.event_sequence, "
            "t.created_at, t.updated_at"
        )

    @staticmethod
    def _receipt_select() -> str:
        return (
            "r.id AS command_id, r.idempotency_key, r.kind, r.disposition, "
            "r.project_id, r.task_id, r.accepted_at, r.accepted_task_version, "
            "r.request_digest"
        )

    async def list_tasks(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        limit: int,
        position: TaskCursorPosition | None,
    ) -> tuple[ProjectRecord, list[dict[str, Any]]] | None:
        try:
            async with self.project.begin() as connection:
                project = await self._authorize_project_connection(
                    connection, user_id=user_id, project_id=project_id
                )
                if project is None:
                    return None
                params: dict[str, Any] = {
                    "tenant_id": project.tenant_id,
                    "project_id": project.id,
                    "limit": limit + 1,
                }
                after = ""
                if position is not None:
                    after = "AND (t.created_at, t.id) < (:created_at, :task_id)"
                    params.update(
                        {"created_at": position.created_at, "task_id": position.task_id}
                    )
                rows = (
                    await connection.execute(
                        text(
                            f"SELECT {self._task_select()} FROM tasks t "
                            "WHERE t.tenant_id = :tenant_id AND t.project_id = :project_id "
                            f"{after} ORDER BY t.created_at DESC, t.id DESC LIMIT :limit"
                        ),
                        params,
                    )
                ).mappings().all()
                return project, [dict(row) for row in rows]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def get_task_snapshot(
        self, *, user_id: UUID, project_id: UUID, task_id: UUID
    ) -> tuple[ProjectRecord, dict[str, Any]] | None:
        try:
            async with self.project.begin() as connection:
                project = await self._authorize_project_connection(
                    connection, user_id=user_id, project_id=project_id
                )
                if project is None:
                    return None
                row = (
                    await connection.execute(
                        text(
                            f"SELECT {self._task_select()} FROM tasks t "
                            "WHERE t.tenant_id = :tenant_id AND t.project_id = :project_id "
                            "AND t.id = :task_id"
                        ),
                        {
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "task_id": task_id,
                        },
                    )
                ).mappings().one_or_none()
                return None if row is None else (project, dict(row))
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def get_command_receipt(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        command_id: UUID | None = None,
        idempotency_key: UUID | None = None,
    ) -> dict[str, Any] | None:
        if (command_id is None) == (idempotency_key is None):
            raise ValueError("exactly one receipt locator is required")
        try:
            async with self.project.begin() as connection:
                project = await self._authorize_project_connection(
                    connection, user_id=user_id, project_id=project_id
                )
                if project is None:
                    return None
                locator = "r.id = :locator" if command_id is not None else "r.idempotency_key = :locator"
                row = (
                    await connection.execute(
                        text(
                            f"SELECT {self._receipt_select()} FROM command_receipts r "
                            "WHERE r.tenant_id = :tenant_id AND r.project_id = :project_id "
                            f"AND r.user_id = :user_id AND {locator}"
                        ),
                        {
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "user_id": user_id,
                            "locator": command_id if command_id is not None else idempotency_key,
                        },
                    )
                ).mappings().one_or_none()
                return None if row is None else dict(row)
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def list_task_events(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> list[dict[str, Any]] | None:
        try:
            async with self.project.begin() as connection:
                project = await self._authorize_project_connection(
                    connection, user_id=user_id, project_id=project_id
                )
                if project is None:
                    return None
                visible_task = await connection.scalar(
                    text(
                        "SELECT id FROM tasks WHERE tenant_id = :tenant_id "
                        "AND project_id = :project_id AND id = :task_id"
                    ),
                    {
                        "tenant_id": project.tenant_id,
                        "project_id": project.id,
                        "task_id": task_id,
                    },
                )
                if visible_task is None:
                    return None
                rows = (
                    await connection.execute(
                        text(
                            "SELECT event_id, tenant_id, project_id, task_id, sequence, "
                            "aggregate_version, event_type, occurred_at, trace_id, summary "
                            "FROM task_events WHERE tenant_id = :tenant_id "
                            "AND project_id = :project_id AND task_id = :task_id "
                            "AND sequence > :after_sequence ORDER BY sequence ASC LIMIT :limit"
                        ),
                        {
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "task_id": task_id,
                            "after_sequence": after_sequence,
                            "limit": limit + 1,
                        },
                    )
                ).mappings().all()
                return [dict(row) for row in rows]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def _existing_receipt(
        self,
        connection: Any,
        *,
        tenant_id: UUID,
        project_id: UUID,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> dict[str, Any] | None:
        row = (
            await connection.execute(
                text(
                    f"SELECT {self._receipt_select()} FROM command_receipts r "
                    "WHERE r.tenant_id = :tenant_id AND r.project_id = :project_id "
                    "AND r.user_id = :user_id AND r.idempotency_key = :idempotency_key"
                ),
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "user_id": user_id,
                    "idempotency_key": idempotency_key,
                },
            )
        ).mappings().one_or_none()
        return None if row is None else dict(row)

    async def create_task_command(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        idempotency_key: UUID,
        preview_id: UUID,
        supplied_input_digest: str,
        normalized_draft: dict[str, Any],
        request_digest: str,
        trace_id: UUID,
    ) -> dict[str, Any]:
        try:
            async with self._fresh_user_lock(user_id) as fresh_permissions_version:
                async with self.project.begin() as connection:
                    project = await self._authorize_project_connection(
                        connection, user_id=user_id, project_id=project_id
                    )
                    if project is None:
                        raise ResourceNotFound
                    if project.role != "operator":
                        raise CommandForbidden
                    existing = await self._existing_receipt(
                        connection,
                        tenant_id=project.tenant_id,
                        project_id=project.id,
                        user_id=user_id,
                        idempotency_key=idempotency_key,
                    )
                    if existing is not None:
                        if existing["request_digest"] != request_digest:
                            raise IdempotencyConflict
                        return existing
                    if fresh_permissions_version != permissions_version:
                        raise VersionConflict
                    preview = (
                        await connection.execute(
                            text(
                                "SELECT tp.id, tp.permissions_version, tp.draft, tp.input_digest, "
                                "tp.policy_id, tp.policy_version, tp.policy_hash, tp.effective_scope, "
                                "tp.can_create, tp.blockers, tp.expires_at, sp.scope, "
                                "a.valid_from, a.valid_until, a.revoked_at "
                                "FROM task_previews tp "
                                "JOIN scope_policy_versions sp ON sp.tenant_id = tp.tenant_id "
                                "AND sp.project_id = tp.project_id AND sp.policy_id = tp.policy_id "
                                "AND sp.version = tp.policy_version AND sp.policy_hash = tp.policy_hash "
                                "JOIN authorization_records a ON a.tenant_id = sp.tenant_id "
                                "AND a.project_id = sp.project_id AND a.id = sp.authorization_id "
                                "WHERE tp.tenant_id = :tenant_id AND tp.project_id = :project_id "
                                "AND tp.user_id = :user_id AND tp.id = :preview_id"
                            ),
                            {
                                "tenant_id": project.tenant_id,
                                "project_id": project.id,
                                "user_id": user_id,
                                "preview_id": preview_id,
                            },
                        )
                    ).mappings().one_or_none()
                    if preview is None:
                        raise ResourceNotFound
                    now = await connection.scalar(text("SELECT clock_timestamp()"))
                    if preview["expires_at"] <= now:
                        raise PreviewExpired
                    if not preview["can_create"]:
                        blocker_codes = {
                            blocker.get("code")
                            for blocker in preview["blockers"]
                            if isinstance(blocker, dict)
                        }
                        if "CREATION_UNAVAILABLE" in blocker_codes:
                            raise VersionConflict
                        raise ScopeDenied
                    if preview["permissions_version"] != fresh_permissions_version:
                        raise VersionConflict
                    if (
                        preview["draft"] != normalized_draft
                        or preview["input_digest"] != supplied_input_digest
                    ):
                        raise CommandValidationFailed
                    evaluated = evaluate_scope(
                        normalized_draft,
                        preview["scope"],
                        {
                            "valid_from": preview["valid_from"],
                            "valid_until": preview["valid_until"],
                            "revoked_at": preview["revoked_at"],
                        },
                        now=now,
                    )
                    if (
                        not evaluated["can_create"]
                        or evaluated["input_digest"] != supplied_input_digest
                        or evaluated["effective_scope"] != preview["effective_scope"]
                    ):
                        raise ScopeDenied

                    task_id = uuid4()
                    command_id = uuid4()
                    event_id = uuid4()
                    await connection.execute(
                        text(
                            "INSERT INTO tasks (id, tenant_id, project_id, user_id, draft, "
                            "input_digest, policy_id, policy_version, policy_hash, effective_scope, "
                            "version, state, cleanup_state, active_calls, unknown_calls, "
                            "egress_state, assessment_outcome, stop_reason, event_sequence) VALUES "
                            "(:id, :tenant_id, :project_id, :user_id, CAST(:draft AS jsonb), "
                            ":input_digest, :policy_id, :policy_version, :policy_hash, "
                            "CAST(:effective_scope AS jsonb), 1, 'queued', 'not_required', 0, 0, "
                            "'not_granted', 'not_assessed', NULL, 1)"
                        ),
                        {
                            "id": task_id,
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "user_id": user_id,
                            "draft": json.dumps(normalized_draft, separators=(",", ":")),
                            "input_digest": supplied_input_digest,
                            "policy_id": preview["policy_id"],
                            "policy_version": preview["policy_version"],
                            "policy_hash": preview["policy_hash"],
                            "effective_scope": json.dumps(
                                preview["effective_scope"], separators=(",", ":")
                            ),
                        },
                    )
                    receipt = (
                        await connection.execute(
                            text(
                                "INSERT INTO command_receipts (id, tenant_id, project_id, user_id, "
                                "idempotency_key, kind, task_id, request_digest, disposition, "
                                "accepted_task_version) VALUES (:id, :tenant_id, :project_id, "
                                ":user_id, :idempotency_key, 'create', :task_id, :request_digest, "
                                "'accepted', 1) RETURNING id AS command_id, idempotency_key, kind, "
                                "disposition, project_id, task_id, accepted_at, "
                                "accepted_task_version, request_digest"
                            ),
                            {
                                "id": command_id,
                                "tenant_id": project.tenant_id,
                                "project_id": project.id,
                                "user_id": user_id,
                                "idempotency_key": idempotency_key,
                                "task_id": task_id,
                                "request_digest": request_digest,
                            },
                        )
                    ).mappings().one()
                    await connection.execute(
                        text(
                            "INSERT INTO task_events (event_id, tenant_id, project_id, task_id, "
                            "sequence, aggregate_version, event_type, trace_id, summary) VALUES "
                            "(:event_id, :tenant_id, :project_id, :task_id, 1, 1, "
                            "'task.changed', :trace_id, '任务已创建，等待执行')"
                        ),
                        {
                            "event_id": event_id,
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "task_id": task_id,
                            "trace_id": trace_id,
                        },
                    )
                    return dict(receipt)
        except (
            CommandForbidden,
            CommandValidationFailed,
            FreshAuthorityInvalid,
            IdempotencyConflict,
            PreviewExpired,
            ResourceNotFound,
            ScopeDenied,
            VersionConflict,
        ):
            raise
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def control_task_command(
        self,
        *,
        user_id: UUID,
        permissions_version: int,
        project_id: UUID,
        task_id: UUID,
        idempotency_key: UUID,
        action: str,
        expected_version: int,
        request_digest: str,
        trace_id: UUID,
    ) -> dict[str, Any]:
        try:
            async with self._fresh_user_lock(user_id) as fresh_permissions_version:
                async with self.project.begin() as connection:
                    project = await self._authorize_project_connection(
                        connection, user_id=user_id, project_id=project_id
                    )
                    if project is None:
                        raise ResourceNotFound
                    if project.role != "operator":
                        raise CommandForbidden
                    existing = await self._existing_receipt(
                        connection,
                        tenant_id=project.tenant_id,
                        project_id=project.id,
                        user_id=user_id,
                        idempotency_key=idempotency_key,
                    )
                    if existing is not None:
                        if existing["request_digest"] != request_digest:
                            raise IdempotencyConflict
                        return existing
                    if fresh_permissions_version != permissions_version:
                        raise VersionConflict
                    task = (
                        await connection.execute(
                            text(
                                "SELECT id, version, state, event_sequence FROM tasks "
                                "WHERE tenant_id = :tenant_id AND project_id = :project_id "
                                "AND id = :task_id FOR UPDATE"
                            ),
                            {
                                "tenant_id": project.tenant_id,
                                "project_id": project.id,
                                "task_id": task_id,
                            },
                        )
                    ).mappings().one_or_none()
                    if task is None:
                        raise ResourceNotFound
                    if task["version"] != expected_version:
                        raise VersionConflict
                    if task["state"] != "queued" or action != "cancel":
                        raise InvalidTransition
                    new_version = int(task["version"]) + 1
                    new_sequence = int(task["event_sequence"]) + 1
                    await connection.execute(
                        text(
                            "UPDATE tasks SET state = 'cancelled', version = :version, "
                            "stop_reason = 'user_cancelled', event_sequence = :event_sequence, "
                            "updated_at = clock_timestamp() WHERE tenant_id = :tenant_id "
                            "AND project_id = :project_id AND id = :task_id"
                        ),
                        {
                            "version": new_version,
                            "event_sequence": new_sequence,
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "task_id": task_id,
                        },
                    )
                    receipt = (
                        await connection.execute(
                            text(
                                "INSERT INTO command_receipts (id, tenant_id, project_id, user_id, "
                                "idempotency_key, kind, task_id, request_digest, disposition, "
                                "accepted_task_version) VALUES (:id, :tenant_id, :project_id, "
                                ":user_id, :idempotency_key, 'cancel', :task_id, :request_digest, "
                                "'accepted', :accepted_task_version) RETURNING id AS command_id, "
                                "idempotency_key, kind, disposition, project_id, task_id, accepted_at, "
                                "accepted_task_version, request_digest"
                            ),
                            {
                                "id": uuid4(),
                                "tenant_id": project.tenant_id,
                                "project_id": project.id,
                                "user_id": user_id,
                                "idempotency_key": idempotency_key,
                                "task_id": task_id,
                                "request_digest": request_digest,
                                "accepted_task_version": new_version,
                            },
                        )
                    ).mappings().one()
                    await connection.execute(
                        text(
                            "INSERT INTO task_events (event_id, tenant_id, project_id, task_id, "
                            "sequence, aggregate_version, event_type, trace_id, summary) VALUES "
                            "(:event_id, :tenant_id, :project_id, :task_id, :sequence, :version, "
                            "'task.changed', :trace_id, '用户已取消任务')"
                        ),
                        {
                            "event_id": uuid4(),
                            "tenant_id": project.tenant_id,
                            "project_id": project.id,
                            "task_id": task_id,
                            "sequence": new_sequence,
                            "version": new_version,
                            "trace_id": trace_id,
                        },
                    )
                    return dict(receipt)
        except (
            CommandForbidden,
            FreshAuthorityInvalid,
            IdempotencyConflict,
            InvalidTransition,
            ResourceNotFound,
            VersionConflict,
        ):
            raise
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error
