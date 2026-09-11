"""Native LiteLLM task keys. The caller persists the stable secret before generate."""
from __future__ import annotations

import hashlib
import math
import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

import httpx


class GatewayUnknown(RuntimeError):
    """The operation may have happened; reconcile the same key before proceeding."""


class GatewayRejected(RuntimeError):
    """An explicit response confirms rejection of the operation."""


def _hash(value):
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("a SHA-256 key hash is required")
    return value


def _safe(data, key_hash):
    info = data.get("info", data)
    if not isinstance(info, dict):
        raise GatewayUnknown("invalid key information")
    metadata = info.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    # Do not relay arbitrary gateway metadata, credentials, or raw response fields.
    safe_metadata = {}
    for name in ("wuji_task_id", "wuji_tenant_id"):
        if name in metadata:
            try:
                safe_metadata[name] = str(UUID(str(metadata[name])))
            except (ValueError, TypeError, AttributeError):
                raise GatewayUnknown("invalid key metadata") from None
    def amount(name):
        value = info.get(name)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise GatewayUnknown("invalid key accounting information")
        return value
    models = info.get("models")
    if models is not None and (not isinstance(models, list) or any(not isinstance(m, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,255}", m) is None for m in models)):
        raise GatewayUnknown("invalid key model configuration")
    blocked = info.get("blocked")
    if blocked is not None and type(blocked) is not bool:
        raise GatewayUnknown("invalid key block state")
    return {"key_hash": key_hash, "models": models, "max_budget": amount("max_budget"),
            "spend": amount("spend"), "blocked": blocked, "metadata": safe_metadata}


class TaskModelGateway:
    def __init__(self, base_url, management_key, timeout=10):
        self.client = httpx.AsyncClient(base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {management_key}"}, timeout=timeout,
            follow_redirects=False, trust_env=False, transport=httpx.AsyncHTTPTransport(retries=0))

    async def close(self):
        await self.client.aclose()

    async def _request(self, method, path, *, body=None, params=None, missing=False):
        try:
            response = await self.client.request(method, path, json=body, params=params)
        except (httpx.HTTPError, OSError):
            raise GatewayUnknown("gateway response unavailable") from None
        if response.status_code == 404 and missing:
            return None
        if response.status_code in (400, 401, 403, 404, 405, 422):
            raise GatewayRejected("gateway rejected operation")
        if not 200 <= response.status_code < 300:
            raise GatewayUnknown("gateway result not confirmed")
        if len(response.content) > 2_097_152:
            raise GatewayUnknown("gateway response exceeds limit")
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (ValueError, TypeError):
            raise GatewayUnknown("invalid gateway response") from None

    async def generate(self, *, key, model_alias, budget_usd, task_id, tenant_id):
        if not isinstance(key, str) or not key.startswith("sk-") or len(key) > 4096 or any(ord(c) < 33 for c in key):
            raise ValueError("a stable task credential is required")
        if not isinstance(model_alias, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}", model_alias) is None:
            raise ValueError("a concrete model alias is required")
        try:
            budget = Decimal(budget_usd)
            if not budget.is_finite() or budget <= 0 or not math.isfinite(float(budget)):
                raise ValueError
        except (InvalidOperation, TypeError, ValueError, OverflowError):
            raise ValueError("positive USD budget required") from None
        metadata = {"wuji_task_id": str(UUID(str(task_id))), "wuji_tenant_id": str(UUID(str(tenant_id)))}
        data = await self._request("POST", "/key/generate", body={"key": key, "models": [model_alias],
            "max_budget": float(budget), "metadata": metadata})
        result = _safe(data, hashlib.sha256(key.encode()).hexdigest())
        if (data.get("key") != key or result["models"] != [model_alias]
                or result["max_budget"] != float(budget) or result["metadata"] != metadata):
            raise GatewayUnknown("generated key configuration not confirmed")
        return result

    async def lookup(self, key_hash):
        key_hash = _hash(key_hash)
        data = await self._request("GET", "/key/info", params={"key": key_hash}, missing=True)
        return None if data is None else _safe(data, key_hash)

    async def block(self, key_hash):
        key_hash = _hash(key_hash)
        data = await self._request("POST", "/key/block", body={"key": key_hash})
        result = _safe(data, key_hash)
        # Native block acknowledgement establishes block state, not in-flight cancellation.
        result["blocked"] = True
        return result
