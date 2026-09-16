"""The Task permit names the predicate that refused it, bounded.

`wuji_task_runtime` imports the deployment-only Kubernetes client, so this test
loads `errors.py` and `models.py` directly with that one dependency stubbed. The
classification itself is production code, not a copy.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY_ROOT / "packages" / "task-runtime" / "src" / "wuji_task_runtime"


def _load():
    kubernetes = types.ModuleType("kubernetes")
    utils = types.ModuleType("kubernetes.utils")
    quantity = types.ModuleType("kubernetes.utils.quantity")
    # Only the shape of a quantity matters here: the validator under test is the
    # permit binding, not Kubernetes quantity parsing.
    quantity.parse_quantity = lambda value: Decimal("1")
    sys.modules.setdefault("kubernetes", kubernetes)
    sys.modules.setdefault("kubernetes.utils", utils)
    sys.modules.setdefault("kubernetes.utils.quantity", quantity)
    package = types.ModuleType("wuji_task_runtime")
    package.__path__ = [str(SOURCE)]
    sys.modules["wuji_task_runtime"] = package
    for name in ("errors", "models"):
        spec = importlib.util.spec_from_file_location(
            f"wuji_task_runtime.{name}", SOURCE / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"wuji_task_runtime.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules["wuji_task_runtime.errors"], sys.modules["wuji_task_runtime.models"]


errors, models = _load()


def permit(**overrides):
    now = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
    values = {
        "tenant_id": "tenant-fixture",
        "task_id": "task-fixture",
        "runtime_attempt": 1,
        "execution_epoch": 2,
        "scope_digest": "a" * 64,
        "config_digest": "b" * 64,
        "start_command_id": "start-command-fixture",
        "expires_at": now + timedelta(minutes=5),
    }
    values.update(overrides)
    return models.ExecutionPermit(**values)


def config(**overrides):
    values = {
        "tenant_id": "tenant-fixture",
        "task_id": "task-fixture",
        "namespace": "wuji-vnext-test",
        "runtime_attempt": 1,
        "execution_epoch": 2,
        "scope_digest": "a" * 64,
        "config_digest": "b" * 64,
        "agent_image": "127.0.0.1:5000/wuji-agent@sha256:" + "c" * 64,
        "kali_image": "127.0.0.1:5000/wuji-kali@sha256:" + "d" * 64,
        "agent_resources": models.ContainerResources(cpu_request="100m", cpu_limit="1", memory_request="128Mi", memory_limit="512Mi"),
        "kali_resources": models.ContainerResources(cpu_request="100m", cpu_limit="1", memory_request="128Mi", memory_limit="512Mi"),
        "tmp_size_limit": "128Mi",
        "pod_deadline_seconds": 600,
        "expose_pod_identity": True,
        "kali_receipts_enabled": True,
    }
    values.update(overrides)
    return models.TaskRuntimeConfig(**values)


def deny_code(permit_value, config_value, now):
    with pytest.raises(errors.PermitDenied) as denied:
        models.validate_execution_permit(config_value, permit_value, now)
    return denied.value.code


def test_an_expired_attempt_window_is_not_the_same_as_a_missing_permit():
    now = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)

    assert deny_code(None, config(), now) == "permit_missing"
    assert deny_code(permit(expires_at=now - timedelta(seconds=1)), config(), now) == "permit_expired"
    # A permit that still binds this attempt passes unchanged.
    assert models.validate_execution_permit(config(), permit(), now) == permit()


def test_a_permit_that_binds_another_attempt_is_named_as_a_binding_mismatch():
    now = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)

    assert deny_code(permit(runtime_attempt=2), config(), now) == "permit_binding_mismatch"
    assert deny_code(permit(), config(execution_epoch=3), now) == "permit_binding_mismatch"


def test_permit_codes_stay_bounded_lowercase_identifiers():
    with pytest.raises(ValueError):
        errors.PermitDenied("message", code="Permit Expired")
    with pytest.raises(ValueError):
        errors.PermitDenied("message", code="A" * 65)
    assert errors.PermitDenied("message").code is None
