"""Thin native LiteLLM management adapter; no model SDK or inference loop."""
from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

import httpx


class GatewayUnknown(RuntimeError):
    pass


class GatewayRejected(RuntimeError):
    pass


class ModelGateway:
    def __init__(self, url: str, key: str, instance_id: UUID, *, transport=None):
        self.instance_id = instance_id
        self.client = httpx.AsyncClient(base_url=url.rstrip("/"), headers={"Authorization": f"Bearer {key}"},
            timeout=10, follow_redirects=False, trust_env=False, transport=transport)

    async def close(self):
        await self.client.aclose()

    async def request(self, method, path, *, body=None, timeout=10):
        try:
            response = await self.client.request(method, path, json=body, timeout=timeout)
        except (httpx.HTTPError, OSError):
            raise GatewayUnknown("gateway response unavailable") from None
        if response.status_code in (400, 401, 403, 404, 422):
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

    def marker(self, version):
        if version["gateway_instance_id"] != self.instance_id:
            raise GatewayRejected("gateway instance differs")
        return {"wuji_instance_id": str(self.instance_id), "wuji_tenant_id": str(version["tenant_id"]),
                "wuji_version_id": str(version["id"]), "wuji_request_digest": version["request_digest"]}

    def alias(self, version):
        return f"wuji_{version['tenant_id'].hex}_{version['id'].hex}"

    async def create_service(self, version, api_key):
        await self.request("POST", "/credentials", body={"credential_name": version["native_id"],
            "credential_values": {"api_key": api_key},
            "credential_info": {**self.marker(version), "custom_llm_provider": version["config"]["protocol"]}})

    async def create_profile(self, version, service):
        config = version["config"]
        native = {"model": f"{service['config']['protocol']}/{config['model_id']}",
            "api_base": service["config"]["base_url"], "litellm_credential_name": service["native_id"],
            "timeout": config["timeout_seconds"], "max_retries": 0}
        info = {**self.marker(version), "id": version["native_id"], "mode": "chat",
                "health_check_max_tokens": 256, "health_check_timeout": 20}
        if config.get("context_window") is not None:
            info["max_input_tokens"] = config["context_window"]
        if config.get("max_output_tokens") is not None:
            info["max_output_tokens"] = config["max_output_tokens"]
        prices = config.get("pricing")
        if prices:
            def cost(name):
                return float(Decimal(prices[name]) / Decimal(1_000_000))
            info.update(input_cost_per_token=cost("input_per_million"), output_cost_per_token=cost("output_per_million"),
                cache_read_input_token_cost=cost("cache_read_per_million" if prices["cache_mode"] == "separate" else "input_per_million"),
                cache_creation_input_token_cost=cost("cache_creation_per_million" if prices["cache_mode"] == "separate" else "input_per_million"))
        await self.request("POST", "/model/new", body={"model_name": self.alias(version), "litellm_params": native, "model_info": info})

    async def reconcile(self, version):
        marker = self.marker(version)
        if version["kind"] == "service":
            data = await self.request("GET", f"/credentials/by_name/{version['native_id']}")
            info = data.get("credential_info", {})
            return data.get("credential_name") == version["native_id"] and all(info.get(k) == v for k, v in marker.items())
        data = await self.request("GET", "/model/info")
        rows = data.get("data")
        if not isinstance(rows, list):
            raise GatewayUnknown("invalid model list")
        for row in rows:
            info = row.get("model_info", {})
            if info.get("id") == version["native_id"]:
                return row.get("model_name") == self.alias(version) and all(info.get(k) == v for k, v in marker.items())
        return False

    async def check(self, version):
        self.marker(version)
        data = await self.request("GET", f"/health?model_id={version['native_id']}", timeout=25)
        healthy = data.get("healthy_endpoints", [])
        return data.get("healthy_count") == 1 and len(healthy) == 1 and healthy[0].get("model_id") == version["native_id"]

    async def block(self, version):
        self.marker(version)
        await self.request("POST", "/model/block", body={"model_id": version["native_id"]})
