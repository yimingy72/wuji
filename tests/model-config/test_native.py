"""One real pinned LiteLLM instance; all provider responses are synthetic."""
import asyncio
from uuid import UUID, uuid4

import httpx

from wuji_api.database_admin import set_tenant_admin
from wuji_api.model_gateway import ModelGateway
from native_fixture import native_gateway

# Capture before D1's per-test guard; the only HTTP destination here is the owned proxy.
_REAL_HTTP = httpx.AsyncHTTPTransport.handle_async_request


def test_native_protocols_publish_and_restart(draft_case, monkeypatch):
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _REAL_HTTP)
    set_tenant_admin(database_url_value=draft_case.database.admin_url, user_id=draft_case.users["owner"],
                     tenant_id=draft_case.tenant, enabled=True, actor="D2 native fixture")
    with native_gateway() as gateway:
        async def scenario():
            async with draft_case.client() as (client, app):
                app.state.runtime.settings.model_gateway_allowed_bases = gateway.upstream_bases
                app.state.runtime.model_gateway = ModelGateway(gateway.url, gateway.master_key, gateway.instance_id)
                prefix = f"/api/v1/tenants/{draft_case.tenant}"
                async def post(path, body):
                    response = await client.post(prefix+path, json=body, headers={"Idempotency-Key": str(uuid4())})
                    assert response.status_code == 200, response.text
                    result = response.json()
                    assert result["state"] == "succeeded", result
                    return result
                profiles = []
                assert gateway.request_count() == 0
                for protocol, base in zip(("openai", "anthropic"), gateway.upstream_bases):
                    service = await post('/model-services', {"name": protocol, "config": {"protocol": protocol, "base_url": base}, "api_key": "synthetic-native-credential"})
                    model = 'synthetic-chat' if protocol == 'openai' else 'claude-sonnet-4-20250514'
                    profile = await post('/model-profiles', {"name": protocol, "config": {
                        "service_version_id": service['version_id'], "model_id": model, "context_window": 4096,
                        "max_output_tokens": 256, "pricing": {"source": "synthetic tariff", "input_per_million": "1",
                        "output_per_million": "2", "cache_mode": "standard_input"}}})
                    assert gateway.request_count() == len(profiles)
                    await post(f"/model-profile-versions/{profile['version_id']}/checks", {})
                    assert gateway.request_count() == len(profiles)+1
                    await post(f"/model-profile-versions/{profile['version_id']}/commands", {"action": "publish", "expected_version": 1})
                    profiles.append(profile['version_id'])
                gateway.restart()
                assert gateway.request_count() == 2
                for version_id in profiles:
                    await post(f"/model-profile-versions/{version_id}/checks", {})
                assert gateway.request_count() == 4
                response = await client.get(f"/api/v1/projects/{draft_case.project}/model-profiles")
                assert response.status_code == 200
                assert {row['id'] for row in response.json()['items']} == set(profiles)
        asyncio.run(scenario())
