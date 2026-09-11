"""Durable control-plane orchestration around native gateway operations."""
from __future__ import annotations

import hmac
import json
from uuid import UUID

from wuji_api.database import AuthorityUnavailable, CommandValidationFailed, InvalidTransition, ResourceNotFound
from wuji_api.model_gateway import GatewayRejected, GatewayUnknown
from wuji_api.model_store import ModelStore


class ModelWorkflow:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = ModelStore(runtime.authority)
        self.gateway = runtime.model_gateway

    def digest(self, kind, target, content, secret=None):
        payload = json.dumps({"kind": kind, "target": str(target) if target else None,
                              "content": content, "secret": secret}, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        return hmac.digest(self.runtime.settings.cursor_signing_key.get_secret_value().encode(),
                           b"wuji-model-operation-v1\n" + payload, "sha256").hex()

    def configured(self):
        if self.gateway is None:
            raise AuthorityUnavailable

    async def save(self, session, tenant_id, key, kind, body, definition_id=None):
        self.configured()
        config = body.config.model_dump(mode="json")
        secret = body.api_key.get_secret_value() if kind == "service" else None
        if kind == "service" and config["base_url"] not in self.runtime.settings.model_gateway_allowed_bases:
            raise CommandValidationFailed
        digest = self.digest(f"create_{kind}", definition_id, {"name": body.name, "config": config}, secret)
        async with self.store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
            operation, version = await self.store.prepare_version(actor, key, digest, kind,
                body.name, config, definition_id, self.gateway.instance_id)
            return await self._execute(actor, operation, version, secret)

    async def action(self, session, tenant_id, key, version_id, action, expected_version=None):
        self.configured()
        digest = self.digest(action, version_id, {"expected_version": expected_version})
        async with self.store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
            try:
                await self.store.get_operation_by_key(actor, key)
            except ResourceNotFound:
                version = await self.store.get_version(actor, version_id, "profile")
                if action in {"publish", "check"}:
                    if version["gateway_instance_id"] != self.gateway.instance_id:
                        raise InvalidTransition
                    if action == "publish":
                        try:
                            matches = await self.gateway.reconcile(version)
                        except (GatewayRejected, GatewayUnknown):
                            raise AuthorityUnavailable from None
                        if not matches:
                            raise InvalidTransition
            operation, version = await self.store.prepare_action(actor, key, digest, version_id, action, expected_version)
            return await self._execute(actor, operation, version)

    async def _execute(self, actor, operation, version, secret=None):
        state = operation["state"]
        if state in {"succeeded", "failed"}:
            return operation
        if state in {"sent", "unknown"}:
            return await self._reconcile(actor, operation, version)
        if version["gateway_instance_id"] != self.gateway.instance_id:
            raise InvalidTransition
        service = None
        if operation["kind"] == "create_profile":
            service = await self.store.get_version(actor, UUID(version["config"]["service_version_id"]), "service")
            if service["sync_state"] != "synced" or service["gateway_instance_id"] != self.gateway.instance_id:
                raise InvalidTransition
        if not await self.store.claim(actor, operation["id"]):
            return await self.store.get_operation(actor, operation["id"])
        try:
            if operation["kind"] == "create_service":
                await self.gateway.create_service(version, secret)
                if not await self.gateway.reconcile(version):
                    raise GatewayUnknown
            elif operation["kind"] == "create_profile":
                await self.gateway.create_profile(version, service)
                if not await self.gateway.reconcile(version):
                    raise GatewayUnknown
            elif operation["kind"] == "check":
                if not await self.gateway.check(version):
                    return await self.store.finish(actor, operation["id"], "failed", {"error_code": "CONNECTION_FAILED"})
            elif operation["kind"] == "revoke":
                await self.gateway.block(version)
            else:
                raise InvalidTransition
        except GatewayRejected:
            return await self.store.finish(actor, operation["id"], "failed", {"error_code": "GATEWAY_REJECTED"})
        except GatewayUnknown:
            return await self.store.finish(actor, operation["id"], "unknown", {"error_code": "GATEWAY_UNCONFIRMED"})
        return await self.store.finish(actor, operation["id"], "succeeded", {})

    async def _reconcile(self, actor, operation, version):
        # In particular, a connection check is never repeated to fill missing evidence.
        if operation["kind"] not in {"create_service", "create_profile"}:
            return await self.store.get_operation(actor, operation["id"])
        try:
            if await self.gateway.reconcile(version):
                return await self.store.finish(actor, operation["id"], "succeeded", {})
        except (GatewayRejected, GatewayUnknown):
            pass
        return await self.store.get_operation(actor, operation["id"])

    async def operation(self, session, tenant_id, operation_id):
        async with self.store.actor(session.user_id, tenant_id, session.permissions_version) as actor:
            operation = await self.store.get_operation(actor, operation_id)
            if self.gateway is not None and operation["state"] in {"sent", "unknown"}:
                version = await self.store.get_version(actor, operation["version_id"])
                return await self._reconcile(actor, operation, version)
            return operation
