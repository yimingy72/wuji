"""User-owned, non-executable task draft persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wuji_api.database import (
    AuthorityUnavailable,
    CommandForbidden,
    CommandValidationFailed,
    DatabaseAuthority,
    ResourceNotFound,
    VersionConflict,
)
from wuji_api.security import TaskCursorPosition

_COLUMNS = "id, tenant_id, project_id, user_id, version, content, created_at, updated_at"
_WHERE = "id = :id AND tenant_id = :tenant_id AND project_id = :project_id AND user_id = :user_id"


class DraftStore:
    def __init__(self, authority: DatabaseAuthority) -> None:
        self.authority = authority

    async def _authorize(self, connection: Any, user_id: UUID, project_id: UUID) -> Any:
        project = await self.authority._authorize_project_connection(
            connection, user_id=user_id, project_id=project_id
        )
        if project is None:
            raise ResourceNotFound
        # Existing authority sets context; drafts also require an enabled tenant.
        enabled = await connection.scalar(
            text("SELECT 1 FROM projects p JOIN tenants t ON t.id = p.tenant_id "
                 "WHERE p.id = :project_id AND p.tenant_id = :tenant_id "
                 "AND p.enabled AND t.enabled"),
            {"project_id": project_id, "tenant_id": project.tenant_id},
        )
        if enabled is None:
            raise ResourceNotFound
        return project

    async def save(
        self, *, user_id: UUID, permissions_version: int, project_id: UUID,
        draft_id: UUID, expected_version: int, content: dict[str, Any], content_digest: str,
    ) -> dict[str, Any]:
        try:
            canonical = json.dumps(
                content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as error:
            raise CommandValidationFailed from error
        digest = hashlib.sha256(b"wuji-draft-v1\n" + canonical).hexdigest()
        if (not isinstance(content, dict) or len(canonical) > 65536
                or not isinstance(content_digest, str)
                or not content_digest.isascii()
                or not hmac.compare_digest(digest, content_digest)
                or type(expected_version) is not int or expected_version < 0):
            raise CommandValidationFailed
        try:
            async with self.authority._fresh_user_lock(user_id) as current_permissions:
                async with self.authority.project.begin() as connection:
                    project = await self._authorize(connection, user_id, project_id)
                    if project.role != "operator":
                        raise CommandForbidden
                    if current_permissions != permissions_version:
                        raise VersionConflict
                    params = {
                        "id": draft_id, "tenant_id": project.tenant_id,
                        "project_id": project_id, "user_id": user_id,
                        "content": canonical.decode("utf-8"), "content_digest": digest,
                    }
                    if expected_version == 0:
                        row = (await connection.execute(text(
                            "INSERT INTO task_drafts "
                            "(id, tenant_id, project_id, user_id, content, content_digest, version) "
                            "VALUES (:id, :tenant_id, :project_id, :user_id, "
                            "CAST(:content AS jsonb), :content_digest, 1) "
                            f"ON CONFLICT (id) DO NOTHING RETURNING {_COLUMNS}"
                        ), params)).mappings().one_or_none()
                        if row is not None:
                            return dict(row)
                    row = (await connection.execute(text(
                        f"SELECT {_COLUMNS}, content_digest FROM task_drafts "
                        f"WHERE {_WHERE} FOR UPDATE"
                    ), params)).mappings().one_or_none()
                    if row is None:
                        raise ResourceNotFound
                    if row["version"] == expected_version + 1 and hmac.compare_digest(
                        row["content_digest"], digest
                    ):
                        return {key: value for key, value in row.items() if key != "content_digest"}
                    if row["version"] != expected_version:
                        raise VersionConflict
                    updated = (await connection.execute(text(
                        "UPDATE task_drafts SET content = CAST(:content AS jsonb), "
                        "content_digest = :content_digest, version = version + 1, "
                        "updated_at = clock_timestamp() "
                        f"WHERE {_WHERE} RETURNING {_COLUMNS}"
                    ), params)).mappings().one()
                    return dict(updated)
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def get(
        self, *, user_id: UUID, project_id: UUID, draft_id: UUID,
    ) -> dict[str, Any]:
        try:
            async with self.authority.project.begin() as connection:
                project = await self._authorize(connection, user_id, project_id)
                row = (await connection.execute(text(
                    f"SELECT {_COLUMNS} FROM task_drafts WHERE {_WHERE}"
                ), {"id": draft_id, "tenant_id": project.tenant_id,
                    "project_id": project_id, "user_id": user_id})).mappings().one_or_none()
                if row is None:
                    raise ResourceNotFound
                return dict(row)
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    async def list(
        self, *, user_id: UUID, project_id: UUID, limit: int,
        position: TaskCursorPosition | None,
    ) -> list[dict[str, Any]]:
        try:
            async with self.authority.project.begin() as connection:
                project = await self._authorize(connection, user_id, project_id)
                params: dict[str, Any] = {
                    "tenant_id": project.tenant_id, "project_id": project_id,
                    "user_id": user_id, "limit": limit + 1,
                }
                after = ""
                if position is not None:
                    after = "AND (created_at, id) < (:created_at, :id) "
                    params.update(created_at=position.created_at, id=position.task_id)
                rows = (await connection.execute(text(
                    f"SELECT {_COLUMNS} FROM task_drafts "
                    "WHERE tenant_id = :tenant_id AND project_id = :project_id "
                    f"AND user_id = :user_id {after}"
                    "ORDER BY created_at DESC, id DESC LIMIT :limit"
                ), params)).mappings().all()
                return [dict(row) for row in rows]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error
