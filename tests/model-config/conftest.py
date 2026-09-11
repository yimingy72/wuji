"""D2 reuses the owned D1 PostgreSQL/session fixture; gateway HTTP is synthetic."""
from contextlib import asynccontextmanager
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

import httpx
import pytest

from wuji_api.database_admin import set_tenant_admin
from wuji_api.model_gateway import ModelGateway

_source = Path(__file__).resolve().parents[1] / "control-plane" / "conftest.py"
_spec = importlib.util.spec_from_file_location("wuji_d2_draft_fixtures", _source)
_drafts = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _drafts
_spec.loader.exec_module(_drafts)
draft_database = _drafts.draft_database
draft_case = _drafts.draft_case

BASE = "https://synthetic-model.example/v1"


class NativeHTTPFixture:
    """Native endpoint shapes, not evidence of a running LiteLLM integration."""
    def __init__(self):
        self.instance_id = uuid4()
        self.credentials = {}
        self.models = {}
        self.calls = []
        self.lose_create = False
        self.lose_health = False
        self.reject_block = False

    def count(self, method, path):
        return self.calls.count((method, path))

    def handle(self, request):
        path = request.url.path
        self.calls.append((request.method, path))
        body = json.loads(request.content) if request.content else None
        if request.method == "POST" and path == "/credentials":
            # Never retain the synthetic credential body in the fixture's ledger.
            self.credentials[body["credential_name"]] = {
                "credential_name": body["credential_name"], "credential_info": body["credential_info"]}
            if self.lose_create:
                self.lose_create = False
                raise httpx.ReadTimeout("synthetic lost create response", request=request)
            return httpx.Response(200, json={"status": "success"})
        if request.method == "GET" and path.startswith("/credentials/by_name/"):
            row = self.credentials.get(path.rsplit("/", 1)[1])
            return httpx.Response(200 if row else 404, json=row or {})
        if request.method == "POST" and path == "/model/new":
            self.models[body["model_info"]["id"]] = body
            return httpx.Response(200, json=body)
        if request.method == "GET" and path == "/model/info":
            return httpx.Response(200, json={"data": list(self.models.values())})
        if request.method == "GET" and path == "/health":
            if self.lose_health:
                raise httpx.ReadTimeout("synthetic lost health response", request=request)
            model_id = request.url.params["model_id"]
            assert model_id in self.models
            return httpx.Response(200, json={"healthy_count": 1,
                "healthy_endpoints": [{"model_id": model_id}], "unhealthy_endpoints": []})
        if request.method == "POST" and path == "/model/block":
            assert body["model_id"] in self.models
            return httpx.Response(400 if self.reject_block else 200, json={"status": "success"})
        raise AssertionError(f"unexpected native HTTP endpoint: {request.method} {path}")


class ModelCase:
    def __init__(self, draft):
        self.draft = draft
        self.native = NativeHTTPFixture()

    def grant(self, user="owner", enabled=True):
        return set_tenant_admin(database_url_value=self.draft.database.admin_url,
            user_id=self.draft.users[user], tenant_id=(self.draft.other_tenant if user == "outsider" else self.draft.tenant),
            enabled=enabled, actor="D2 synthetic test")

    def path(self, suffix, tenant=None):
        return f"/api/v1/tenants/{tenant or self.draft.tenant}/{suffix}"

    @asynccontextmanager
    async def client(self, user="owner"):
        async with self.draft.client(user) as (client, app):
            app.state.runtime.settings.model_gateway_allowed_bases = [BASE]
            app.state.runtime.model_gateway = ModelGateway("https://synthetic-litellm.example",
                "synthetic-management-key", self.native.instance_id,
                transport=httpx.MockTransport(self.native.handle))
            yield client, app


@pytest.fixture
def model_case(draft_case):
    return ModelCase(draft_case)
