"""Provision native LiteLLM Task keys without resetting existing spend.

The protocol follows the existing execution-control/model_budget.py adapter.
Only the private launch process gets management authority. Gates read limited
Task keys; Worker and Kali never receive these keys or the provider key.
"""

from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import math
import re
import secrets

import httpx


class TaskBudgetUnavailable(RuntimeError):
    code = "CAPABILITY_UNAVAILABLE"


def task_key_filename(tenant_id: str, task_id: str) -> str:
    for value in (tenant_id, task_id):
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or "\x00" in value:
            raise ValueError("bounded Task identity required")
    return "task-" + sha256((tenant_id + "\x00" + task_id).encode()).hexdigest() + ".key"


class KubernetesTaskKeyStore:
    """CAS-protected stable secrets; conflicts never replace another key."""

    def __init__(self, core, *, namespace="wuji-vnext-test", secret_name="task-model-keys"):
        if namespace != "wuji-vnext-test" or secret_name != "task-model-keys":
            raise ValueError("the isolated Task key store is required")
        self.core, self.namespace, self.secret_name = core, namespace, secret_name

    def get_or_create(self, tenant_id, task_id):
        name = task_key_filename(tenant_id, task_id)
        for _ in range(4):
            try:
                document = self.core.read_namespaced_secret(
                    self.secret_name, self.namespace, _request_timeout=(5, 5),
                )
            except Exception as error:
                if getattr(error, "status", None) != 404:
                    raise TaskBudgetUnavailable("task_key_store_unavailable") from None
                body = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
                        "metadata": {"name": self.secret_name, "namespace": self.namespace,
                                     "labels": {"wuji.dev/credential-owner": "first-use-launch-v1"}},
                        "data": {}}
                try:
                    self.core.create_namespaced_secret(
                        self.namespace, body, _request_timeout=(5, 5),
                    )
                except Exception as failure:
                    if getattr(failure, "status", None) != 409:
                        raise TaskBudgetUnavailable("task_key_store_unavailable") from None
                continue
            if (document.metadata.labels or {}).get("wuji.dev/credential-owner") != "first-use-launch-v1":
                raise TaskBudgetUnavailable("task_key_store_owner_conflict")
            data = dict(document.data or {})
            if name in data:
                try:
                    key = base64.b64decode(data[name], validate=True).decode("ascii")
                except (ValueError, UnicodeError):
                    raise TaskBudgetUnavailable("task_key_invalid") from None
                if not re.fullmatch(r"sk-[A-Za-z0-9_-]{32,256}", key):
                    raise TaskBudgetUnavailable("task_key_invalid")
                return key
            if len(data) >= 1024:
                raise TaskBudgetUnavailable("task_key_store_full")
            key = "sk-" + secrets.token_urlsafe(32)
            data[name] = base64.b64encode(key.encode()).decode()
            body = {"metadata": {"resourceVersion": document.metadata.resource_version}, "data": data}
            try:
                self.core.patch_namespaced_secret(
                    self.secret_name, self.namespace, body, _request_timeout=(5, 5),
                )
                return key
            except Exception as error:
                if getattr(error, "status", None) != 409:
                    # A lost response is recovered by reading the same Secret,
                    # never by assuming a different newly generated key won.
                    raise TaskBudgetUnavailable("task_key_write_unknown") from None
        raise TaskBudgetUnavailable("task_key_write_conflict")


class ReadOnlyKubernetesTaskKeys:
    """Gate-only GET access avoids asynchronous Secret-volume projection lag."""

    def __init__(self, core):
        self.core = core

    def resolve(self, tenant_id, task_id):
        try:
            document = self.core.read_namespaced_secret(
                "task-model-keys", "wuji-vnext-test", _request_timeout=(5, 5),
            )
            if (document.metadata.labels or {}).get("wuji.dev/credential-owner") != "first-use-launch-v1":
                raise ValueError
            encoded = (document.data or {})[task_key_filename(tenant_id, task_id)]
            if not isinstance(encoded, str) or len(encoded) > 1024:
                raise ValueError
            key = base64.b64decode(encoded, validate=True).decode("ascii")
            if not re.fullmatch(r"sk-[A-Za-z0-9_-]{32,256}", key):
                raise ValueError
            return key
        except Exception:
            raise TaskBudgetUnavailable("task_key_unavailable") from None


class NativeTaskBudget:
    def __init__(self, store, client: httpx.Client):
        self.store, self.client = store, client

    def _request(self, method, path, *, body=None, params=None, missing=False):
        try:
            with self.client.stream(method, path, json=body, params=params) as response:
                if missing and response.status_code == 404:
                    return None
                if not 200 <= response.status_code < 300:
                    raise TaskBudgetUnavailable("gateway_budget_rejected")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > 65_536:
                        raise TaskBudgetUnavailable("gateway_budget_response_limit")
                    raw.extend(chunk)
            from wuji_core.http import strict_json_loads
            result = strict_json_loads(bytes(raw))
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (httpx.HTTPError, OSError, ValueError):
            raise TaskBudgetUnavailable("gateway_budget_unknown") from None

    def ensure(self, *, task_id, tenant_id, model_alias, budget_usd):
        if not isinstance(model_alias, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}", model_alias):
            raise ValueError("a published model alias is required")
        try:
            amount = Decimal(budget_usd)
            if not amount.is_finite() or amount <= 0 or not math.isfinite(float(amount)):
                raise ValueError
        except (InvalidOperation, TypeError, ValueError, OverflowError):
            raise ValueError("a positive finite Task budget is required") from None
        key = self.store.get_or_create(tenant_id, task_id)
        key_hash = sha256(key.encode()).hexdigest()
        metadata = {"wuji_task_id": task_id, "wuji_tenant_id": tenant_id}
        result = self._request("GET", "/key/info", params={"key": key_hash}, missing=True)
        if result is None:
            self._request("POST", "/key/generate", body={
                "key": key, "models": [model_alias], "max_budget": float(amount),
                "metadata": metadata,
            })
            result = self._request("GET", "/key/info", params={"key": key_hash})
        info = result.get("info", result)
        if not isinstance(info, dict):
            raise TaskBudgetUnavailable("gateway_budget_unknown")
        recorded_metadata = info.get("metadata")
        if (
            not isinstance(recorded_metadata, dict)
            or any(recorded_metadata.get(k) != v for k, v in metadata.items())
            or info.get("models") != [model_alias]
            or isinstance(info.get("max_budget"), bool)
            or str(info.get("max_budget")) in {"None", "nan", "inf"}
            or Decimal(str(info["max_budget"])) != amount
            or info.get("blocked") is True
        ):
            raise TaskBudgetUnavailable("gateway_budget_binding_conflict")
        return {"task_id": task_id, "key_hash": key_hash, "model_alias": model_alias,
                "budget_usd": str(amount), "credential_file": task_key_filename(tenant_id, task_id)}
