from __future__ import annotations

import base64
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from starlette.types import ASGIApp


@dataclass(frozen=True, slots=True)
class CapturedRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedExchange:
    request: CapturedRequest
    response: CapturedResponse


class RecordedTestClient:
    """Drive a real ASGI app and retain complete synthetic HTTP exchanges."""

    def __init__(self, app: ASGIApp, *, audit_path: Path) -> None:
        self._app = app
        self._audit_path = audit_path
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.exchanges: list[CapturedExchange] = []

    def close(self) -> None:
        return None

    def request(self, method: str, url: str, **kwargs: Any):
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self._app),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        response = asyncio.run(send())
        request = response.request
        exchange = CapturedExchange(
            request=CapturedRequest(
                method=request.method,
                url=str(request.url),
                headers={key.lower(): value for key, value in request.headers.items()},
                body=request.content,
            ),
            response=CapturedResponse(
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.content,
            ),
        )
        self.exchanges.append(exchange)
        with self._audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(_serializable(exchange), sort_keys=True) + "\n")
        return response

    def get(self, url: str, **kwargs: Any):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any):
        return self.request("PUT", url, **kwargs)


def _serializable(exchange: CapturedExchange) -> dict[str, object]:
    return {
        "request": {
            "method": exchange.request.method,
            "url": exchange.request.url,
            "headers": exchange.request.headers,
            "body_base64": base64.b64encode(exchange.request.body).decode("ascii"),
        },
        "response": {
            "status_code": exchange.response.status_code,
            "headers": exchange.response.headers,
            "body_base64": base64.b64encode(exchange.response.body).decode("ascii"),
        },
    }
