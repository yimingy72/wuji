"""A rejected private knowledge read logs only bounded diagnostic fields."""

import asyncio
from contextlib import redirect_stdout
import io
import json
from types import SimpleNamespace

from starlette.requests import Request

from wuji_core.http import worker_host
from wuji_core.persistence.uow import DomainError


def test_knowledge_read_refusal_emits_bounded_code(monkeypatch):
    class Bridge:
        def knowledge_read(self, _access, _payload):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN", 404)

    monkeypatch.setattr(worker_host, "current_principal", lambda _request: SimpleNamespace(
        subject="worker", tenant_id="tenant", roles=frozenset({"worker"}), token_id="token"
    ))
    router = worker_host.create_worker_host_router(Bridge())
    route = next(item for item in router.routes if item.path.endswith("/knowledge-read"))
    request = Request({
        "type": "http", "method": "POST", "path": route.path,
        "headers": [], "state": {"request_id": "request-fixed"},
    })
    payload = SimpleNamespace(assignment=SimpleNamespace(identity=SimpleNamespace(task_id="task-fixed")))
    output = io.StringIO()
    with redirect_stdout(output):
        response = asyncio.run(route.endpoint(request, payload))
    assert response.status_code == 404
    assert json.loads(output.getvalue()) == {
        "code": "NOT_FOUND_OR_FORBIDDEN",
        "event": "worker_knowledge_read_refused",
        "exception": "DomainError",
        "request_id": "request-fixed",
        "status": 404,
        "task_id": "task-fixed",
    }
