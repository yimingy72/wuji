"""Short-transaction model configuration persistence; no gateway I/O or secrets."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4
import hmac
import json

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wuji_api.database import (AuthorityUnavailable, CommandForbidden, DatabaseAuthority,
                               IdempotencyConflict, InvalidTransition, ResourceNotFound,
                               VersionConflict)
from wuji_api.security import TaskCursorPosition
from wuji_api.model_selection import model_version_lock


@dataclass(frozen=True)
class Actor:
    user_id: UUID
    tenant_id: UUID


class ModelStore:
    def __init__(self, authority: DatabaseAuthority) -> None:
        self.authority = authority

    @asynccontextmanager
    async def _transaction(self, actor: Actor):
        try:
            async with self.authority.project.begin() as connection:
                await self.authority._set_user_context(connection, actor.user_id)
                await connection.execute(text("SELECT set_config('app.tenant_id',:tenant,true), "
                                              "set_config('app.project_id','',true)"),
                                         {"tenant": str(actor.tenant_id)})
                yield connection
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error

    @asynccontextmanager
    async def actor(self, user_id: UUID, tenant_id: UUID, permissions_version: int):
        async with self.authority._fresh_user_lock(user_id) as current:
            async with self._transaction(Actor(user_id, tenant_id)) as connection:
                allowed = await connection.scalar(text(
                    "SELECT 1 FROM tenants t JOIN tenant_memberships tm ON tm.tenant_id=t.id "
                    "JOIN tenant_admin_grants g ON g.tenant_id=tm.tenant_id AND g.user_id=tm.user_id "
                    "WHERE t.id=:tenant AND tm.user_id=:user AND t.enabled AND tm.enabled AND g.enabled"
                ), {"tenant": tenant_id, "user": user_id})
                if allowed is None:
                    raise CommandForbidden
                if current != permissions_version:
                    raise VersionConflict
            yield Actor(user_id, tenant_id)

    @staticmethod
    def _page(limit: int, position: TaskCursorPosition | None, prefix: str = ""):
        params = {"limit": limit + 1}
        after = ""
        if position is not None:
            after = f" AND ({prefix}created_at,{prefix}id)<(:created_at,:page_id)"
            params.update(created_at=position.created_at, page_id=position.task_id)
        return after, params

    async def list_tenants(self, user_id, limit, position):
        async with self._transaction(Actor(user_id, UUID(int=0))) as connection:
            await connection.execute(text("SELECT set_config('app.tenant_id','',true)"))
            after, params = self._page(limit, position, "t.")
            params["user"] = user_id
            rows = await connection.execute(text(
                "SELECT t.id,t.name,t.created_at,EXISTS(SELECT 1 FROM tenant_admin_grants g "
                "WHERE g.tenant_id=t.id AND g.user_id=:user AND g.enabled) AS is_admin "
                "FROM tenants t JOIN tenant_memberships tm ON tm.tenant_id=t.id "
                f"WHERE tm.user_id=:user AND t.enabled AND tm.enabled {after} "
                "ORDER BY t.created_at DESC,t.id DESC LIMIT :limit"), params)
            return [dict(row) for row in rows.mappings()]

    async def list_definitions(self, actor, kind, limit, position):
        async with self._transaction(actor) as connection:
            after, params = self._page(limit, position)
            params.update(tenant=actor.tenant_id, kind=kind)
            rows = await connection.execute(text("SELECT * FROM model_definitions "
                f"WHERE tenant_id=:tenant AND kind=:kind {after} "
                "ORDER BY created_at DESC,id DESC LIMIT :limit"), params)
            return [dict(row) for row in rows.mappings()]

    async def list_versions(self, actor, kind, definition_id, limit, position):
        async with self._transaction(actor) as connection:
            params = {"tenant": actor.tenant_id, "kind": kind, "definition": definition_id}
            if await connection.scalar(text("SELECT id FROM model_definitions WHERE tenant_id=:tenant "
                "AND kind=:kind AND id=:definition"), params) is None:
                raise ResourceNotFound
            after, page = self._page(limit, position)
            params.update(page)
            rows = await connection.execute(text("SELECT * FROM model_versions WHERE tenant_id=:tenant "
                f"AND kind=:kind AND definition_id=:definition {after} "
                "ORDER BY created_at DESC,id DESC LIMIT :limit"), params)
            return [dict(row) for row in rows.mappings()]

    async def _version(self, connection, actor, version_id, kind=None, lock=False):
        row = (await connection.execute(text("SELECT * FROM model_versions "
            "WHERE tenant_id=:tenant AND id=:id" + (" AND kind=:kind" if kind else "") +
            (" FOR UPDATE" if lock else "")),
            {"tenant": actor.tenant_id, "id": version_id, "kind": kind})).mappings().one_or_none()
        if row is None:
            raise ResourceNotFound
        return dict(row)

    async def get_version(self, actor, version_id, kind=None):
        async with self._transaction(actor) as connection:
            return await self._version(connection, actor, version_id, kind)

    async def _replay(self, connection, actor, key, digest, kind):
        row = (await connection.execute(text("SELECT * FROM model_operations "
            "WHERE tenant_id=:tenant AND user_id=:user AND idempotency_key=:key"),
            {"tenant": actor.tenant_id, "user": actor.user_id, "key": key})).mappings().one_or_none()
        if row is not None:
            if row["kind"] != kind or not hmac.compare_digest(row["request_digest"], digest):
                raise IdempotencyConflict
            return await self._operation(connection, actor, row["id"])
        return None

    async def _insert_operation(self, connection, actor, key, digest, kind, version_id, state="prepared"):
        return dict((await connection.execute(text(
            "INSERT INTO model_operations(id,tenant_id,user_id,idempotency_key,kind,version_id,request_digest,state) "
            "VALUES(:id,:tenant,:user,:key,:kind,:version,:digest,:state) RETURNING *"),
            {"id": uuid4(), "tenant": actor.tenant_id, "user": actor.user_id, "key": key,
             "kind": kind, "version": version_id, "digest": digest, "state": state})).mappings().one())

    async def prepare_version(self, actor, key, request_digest, kind, name, config,
                              definition_id, gateway_instance_id):
        async with self._transaction(actor) as connection:
            operation = await self._replay(connection, actor, key, request_digest, "create_" + kind)
            if operation is not None:
                return operation, await self._version(connection, actor, operation["version_id"])
            if kind not in {"service", "profile"}:
                raise ResourceNotFound
            service_id = None
            if kind == "profile":
                service_id = UUID(str(config["service_version_id"]))
                service = await self._version(connection, actor, service_id, "service", True)
                if service["sync_state"] != "synced" or service["gateway_instance_id"] != gateway_instance_id:
                    raise InvalidTransition
            if definition_id is None:
                definition_id = uuid4()
                await connection.execute(text("INSERT INTO model_definitions(id,tenant_id,kind,name) "
                    "VALUES(:id,:tenant,:kind,:name)"),
                    {"id": definition_id, "tenant": actor.tenant_id, "kind": kind, "name": name})
            else:
                # Serialize numbering across different administrators without config UPDATE rights.
                await connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 1465207371))"),
                                         {"id": str(definition_id)})
                if await connection.scalar(text("SELECT id FROM model_definitions WHERE id=:id "
                    "AND tenant_id=:tenant AND kind=:kind"),
                    {"id": definition_id, "tenant": actor.tenant_id, "kind": kind}) is None:
                    raise ResourceNotFound
            number = await connection.scalar(text("SELECT COALESCE(MAX(number),0)+1 FROM model_versions "
                "WHERE definition_id=:id AND tenant_id=:tenant"), {"id": definition_id, "tenant": actor.tenant_id})
            version_id = uuid4()
            native = (f"wuji_{gateway_instance_id.hex}_{actor.tenant_id.hex}_{version_id.hex}"
                      if kind == "service" else str(version_id))
            version = dict((await connection.execute(text(
                "INSERT INTO model_versions(id,tenant_id,kind,definition_id,number,name,config,"
                "service_version_id,gateway_instance_id,native_id,request_digest) VALUES"
                "(:id,:tenant,:kind,:definition,:number,:name,CAST(:config AS jsonb),:service,:gateway,:native,:digest) RETURNING *"),
                {"id": version_id, "tenant": actor.tenant_id, "kind": kind, "definition": definition_id,
                 "number": number, "name": name, "config": json.dumps(config), "service": service_id,
                 "gateway": gateway_instance_id, "native": native, "digest": request_digest})).mappings().one())
            operation = await self._insert_operation(connection, actor, key, request_digest, "create_" + kind, version_id)
            return operation, version

    async def prepare_action(self, actor, key, request_digest, version_id, kind, expected_version=None):
        async with self._transaction(actor) as connection:
            operation = await self._replay(connection, actor, key, request_digest, kind)
            if operation is not None:
                return operation, await self._version(connection, actor, operation["version_id"])
            await model_version_lock(connection, actor.tenant_id, version_id)
            version = await self._version(connection, actor, version_id, "profile", True)
            if kind == "check":
                if version["sync_state"] != "synced" or version["state"] == "revoked":
                    raise InvalidTransition
            else:
                if version["state_revision"] != expected_version:
                    raise VersionConflict
                if kind == "publish":
                    latest = (await connection.execute(text("SELECT state FROM model_operations "
                        "WHERE tenant_id=:tenant AND version_id=:version AND kind='check' "
                        "ORDER BY created_at DESC,id DESC LIMIT 1"),
                        {"tenant": actor.tenant_id, "version": version_id})).scalar_one_or_none()
                    config = version["config"]
                    if (version["state"] not in {"draft", "retired"} or version["sync_state"] != "synced"
                        or latest != "succeeded" or not config.get("pricing")
                        or not config.get("context_window") or not config.get("max_output_tokens")
                        or config["max_output_tokens"] > config["context_window"]):
                        raise InvalidTransition
                    target = "published"
                elif kind == "retire" and version["state"] == "published":
                    target = "retired"
                elif kind == "revoke" and (version["state"] != "revoked" or version["sync_state"] != "synced"):
                    target = "revoked"
                else:
                    raise InvalidTransition
                version = dict((await connection.execute(text("UPDATE model_versions SET state=:state, "
                    "state_revision=state_revision+1" + (", sync_state='pending'" if kind == "revoke" else "") +
                    " WHERE id=:id AND tenant_id=:tenant RETURNING *"),
                    {"state": target, "id": version_id, "tenant": actor.tenant_id})).mappings().one())
            operation = await self._insert_operation(connection, actor, key, request_digest, kind, version_id,
                                                     "succeeded" if kind in {"publish", "retire"} else "prepared")
            return operation, version

    async def claim(self, actor, operation_id):
        async with self._transaction(actor) as connection:
            return await connection.scalar(text("UPDATE model_operations SET state='sent',sent_at=clock_timestamp(),"
                "updated_at=clock_timestamp() WHERE id=:id AND tenant_id=:tenant AND user_id=:user "
                "AND state='prepared' RETURNING id"),
                {"id": operation_id, "tenant": actor.tenant_id, "user": actor.user_id}) is not None

    async def _operation(self, connection, actor, operation_id):
        await connection.execute(text("UPDATE model_operations SET state='unknown',updated_at=clock_timestamp() "
            "WHERE id=:id AND tenant_id=:tenant AND user_id=:user AND state='sent' "
            "AND sent_at < clock_timestamp()-interval '45 seconds'"),
            {"id": operation_id, "tenant": actor.tenant_id, "user": actor.user_id})
        row = (await connection.execute(text("SELECT * FROM model_operations WHERE id=:id "
            "AND tenant_id=:tenant"), {"id": operation_id, "tenant": actor.tenant_id})).mappings().one_or_none()
        if row is None:
            raise ResourceNotFound
        return dict(row)

    async def get_operation(self, actor, operation_id):
        async with self._transaction(actor) as connection:
            return await self._operation(connection, actor, operation_id)

    async def get_operation_by_key(self, actor, key):
        async with self._transaction(actor) as connection:
            operation_id = await connection.scalar(text(
                "SELECT id FROM model_operations WHERE tenant_id=:tenant "
                "AND user_id=:user AND idempotency_key=:key"),
                {"tenant": actor.tenant_id, "user": actor.user_id, "key": key})
            if operation_id is None:
                raise ResourceNotFound
            return await self._operation(connection, actor, operation_id)

    async def finish(self, actor, operation_id, state, result=None):
        if state not in {"succeeded", "failed", "unknown"}:
            raise InvalidTransition
        safe_result = {key: (result or {}).get(key) for key in ("error_code", "usage", "cost_usd")}
        async with self._transaction(actor) as connection:
            operation = (await connection.execute(text("UPDATE model_operations SET state=:state,"
                "result=CAST(:result AS jsonb),updated_at=clock_timestamp() WHERE id=:id AND tenant_id=:tenant "
                "AND user_id=:user AND state IN ('sent','unknown') RETURNING *"),
                {"id": operation_id, "tenant": actor.tenant_id, "user": actor.user_id,
                 "state": state, "result": json.dumps(safe_result)})).mappings().one_or_none()
            if operation is None:
                return await self._operation(connection, actor, operation_id)
            if operation["kind"] in {"create_service", "create_profile", "revoke"}:
                sync = "synced" if state == "succeeded" else (
                    "unknown" if state == "unknown" or operation["kind"] == "revoke" else "failed")
                await connection.execute(text("UPDATE model_versions SET sync_state=:sync "
                    "WHERE id=:id AND tenant_id=:tenant " +
                    ("" if operation["kind"] == "revoke" else "AND state != 'revoked'")),
                    {"sync": sync, "id": operation["version_id"], "tenant": actor.tenant_id})
            return dict(operation)

    async def project_profiles(self, user_id, project_id, limit, position):
        try:
            async with self.authority.project.begin() as connection:
                project = await self.authority._authorize_project_connection(connection, user_id=user_id, project_id=project_id)
                if project is None:
                    raise ResourceNotFound
                after, params = self._page(limit, position)
                params["tenant"] = project.tenant_id
                rows = await connection.execute(text("SELECT * FROM model_versions WHERE tenant_id=:tenant "
                    f"AND kind='profile' AND state='published' AND sync_state='synced' {after} "
                    "ORDER BY created_at DESC,id DESC LIMIT :limit"), params)
                return [dict(row) for row in rows.mappings()]
        except SQLAlchemyError as error:
            raise AuthorityUnavailable from error
