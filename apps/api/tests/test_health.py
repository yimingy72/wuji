import asyncio
from uuid import UUID

import httpx
import pytest
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters

from wuji_api import create_app


class ContractRequest:
    host_url = "http://test"
    method = "get"
    body = None
    content_type = "application/octet-stream"

    def __init__(self, path: str):
        self.path = path
        self.parameters = RequestParameters()


class ContractResponse:
    def __init__(self, response: httpx.Response):
        self.status_code = response.status_code
        self.content_type = response.headers.get("content-type", "")
        self.headers = response.headers
        self.data = response.content


async def request(path: str, *, ready: bool = False) -> httpx.Response:
    async def probe() -> bool:
        return ready

    transport = httpx.ASGITransport(app=create_app(probe))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.unit
def test_health_is_public_and_readiness_fails_closed() -> None:
    live = asyncio.run(request("/health/live"))
    assert live.status_code == 200
    assert live.json() == {"status": "live"}
    assert live.headers["cache-control"] == "no-store"

    ready = asyncio.run(request("/health/ready"))
    assert ready.status_code == 503
    assert ready.json()["code"] == "SERVICE_UNAVAILABLE"
    UUID(ready.json()["trace_id"])
    assert ready.headers["cache-control"] == "no-store"


@pytest.mark.unit
def test_ready_probe_and_unregistered_business_routes_are_truthful() -> None:
    ready = asyncio.run(request("/health/ready", ready=True))
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}

    session = asyncio.run(request("/api/v1/session"))
    assert session.status_code == 404
    assert session.json()["code"] == "NOT_FOUND"


@pytest.mark.unit
def test_runtime_health_responses_follow_the_authoritative_openapi() -> None:
    contract = OpenAPI.from_file_path("packages/contracts/openapi.yaml")
    for path in ("/health/live", "/health/ready"):
        response = asyncio.run(request(path))
        contract.validate_response(ContractRequest(path), ContractResponse(response))

    runtime = create_app().openapi()
    assert set(runtime["paths"]) == {"/health/live", "/health/ready"}
    for path in runtime["paths"].values():
        assert path["get"]["security"] == []
        assert path["get"]["servers"] == [{"url": "/"}]
