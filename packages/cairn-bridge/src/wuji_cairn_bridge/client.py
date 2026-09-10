from __future__ import annotations

import math
from urllib.parse import urlsplit
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from cairn.dispatcher.protocol.client import ApiResult, CairnClient
from cairn.server.models import CreateProjectRequest

from .errors import InvalidBridgeInput
from .models import require_uuid


class _BoundedSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs["allow_redirects"] = False
        return super().request(method, url, **kwargs)


class CairnPlatformClient(CairnClient):
    """Uses Cairn's native protocol; only adds project creation and session policy."""

    def __init__(self, server_id: UUID, base_url: str, timeout: float = 10):
        require_uuid(server_id, "server_id")
        try:
            parts = urlsplit(base_url)
            valid = (
                parts.scheme in {"http", "https"} and parts.hostname and
                parts.username is None and parts.password is None and
                not parts.query and not parts.fragment and not any(c.isspace() for c in base_url)
            )
            _ = parts.port
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise InvalidBridgeInput("Cairn URL must be explicit, without credentials, query or fragment")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise InvalidBridgeInput("Cairn timeout must be positive and finite")
        self.server_id = server_id
        super().__init__(base_url, timeout=timeout)

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = _BoundedSession()
            session.trust_env = False
            adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=0)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            self._local.session = session
            with self._sessions_lock:
                self._sessions[id(session)] = session
        return session

    def create_project(self, request: CreateProjectRequest) -> ApiResult:
        return self._request_json("POST", "/projects", json=request.model_dump(mode="json", exclude_none=True))
