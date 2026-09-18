"""Native gateway management semantics; no provider inference or real keys."""

import importlib.util
from pathlib import Path

import httpx
import pytest


spec = importlib.util.spec_from_file_location(
    "first_use_task_keys", Path(__file__).resolve().parents[2] / "ops/vnext/task_model_keys.py",
)
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)


class StableStore:
    def get_or_create(self, tenant_id, task_id):
        return "sk-fixture-" + keys.task_key_filename(tenant_id, task_id)[5:45]


def test_existing_task_budget_is_reconciled_without_resetting_spend():
    requests = []

    def gateway(request):
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"info": {
            "models": ["wuji-deepseek-observe-v1"], "max_budget": 1.0, "spend": 0.37,
            "metadata": {"wuji_task_id": "task-one", "wuji_tenant_id": "tenant-one"},
        }})

    with httpx.Client(base_url="https://gateway.invalid", transport=httpx.MockTransport(gateway)) as client:
        budget = keys.NativeTaskBudget(StableStore(), client)
        args = dict(task_id="task-one", tenant_id="tenant-one", model_alias="wuji-deepseek-observe-v1", budget_usd="1.00")
        first = budget.ensure(**args)
        assert budget.ensure(**args) == first
        with pytest.raises(keys.TaskBudgetUnavailable):
            budget.ensure(**{**args, "budget_usd": "2.00"})
    assert requests == [("GET", "/key/info")] * 3


def test_lost_generate_response_recovers_same_key_by_lookup():
    attempts = []
    persisted = False

    def gateway(request):
        nonlocal persisted
        attempts.append((request.method, request.url.path))
        if request.method == "POST":
            persisted = True
            raise httpx.ReadTimeout("synthetic response loss", request=request)
        if not persisted:
            return httpx.Response(404)
        return httpx.Response(200, json={"info": {
            "models": ["model-fixture"], "max_budget": 1,
            "metadata": {"wuji_task_id": "task", "wuji_tenant_id": "tenant"},
        }})

    with httpx.Client(base_url="https://gateway.invalid", transport=httpx.MockTransport(gateway)) as client:
        budget = keys.NativeTaskBudget(StableStore(), client)
        args = dict(task_id="task", tenant_id="tenant", model_alias="model-fixture", budget_usd="1")
        with pytest.raises(keys.TaskBudgetUnavailable, match="gateway_budget_unknown"):
            budget.ensure(**args)
        receipt = budget.ensure(**args)
    assert len(receipt["key_hash"]) == 64
    assert attempts == [("GET", "/key/info"), ("POST", "/key/generate"), ("GET", "/key/info")]
    assert "key" not in receipt
    assert keys.task_key_filename("tenant", "task") != keys.task_key_filename("other", "task")


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "0", "-1"])
def test_invalid_budget_never_contacts_gateway(amount):
    def forbidden(request):
        pytest.fail("invalid Task budget contacted gateway")

    with httpx.Client(base_url="https://gateway.invalid", transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(ValueError):
            keys.NativeTaskBudget(StableStore(), client).ensure(
                task_id="task", tenant_id="tenant", model_alias="model", budget_usd=amount,
            )
