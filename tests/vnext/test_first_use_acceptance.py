from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _driver():
    path = ROOT / "scripts/vnext/first_use_acceptance.py"
    spec = importlib.util.spec_from_file_location("wuji_first_use_acceptance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_read_chain() -> dict:
    return {
        "task_id": "task-fixture",
        "run_id": "run-fixture",
        "tool_call_id": "call-fixture",
        "artifact_ref": {"id": "artifact-fixture", "revision": "1"},
        "read_set": [{"entity_type": "artifact", "id": "artifact-fixture", "revision": "1"}],
        "model_attempt_ids": ["attempt-1", "attempt-2"],
        "material": {
            "status": "delivered",
            "source": {
                "artifact_ref": {"id": "artifact-fixture", "revision": "1"},
                "artifact_sha256": "a" * 64,
            },
            "representation": {
                "encoding": "utf-8",
                "text": "中文 fixture marker",
                "representation_sha256": "b" * 64,
            },
        },
    }


def test_read_chain_requires_content_and_exact_source_reference():
    module = _driver()
    result = module.validate_read_chain(valid_read_chain())
    assert result == {"valid": True, "errors": []}

    broken = valid_read_chain()
    broken["material"]["source"]["artifact_ref"] = {"id": "other", "revision": "1"}
    result = module.validate_read_chain(broken)
    assert not result["valid"]
    assert any("artifact_ref" in error for error in result["errors"])


def test_driver_command_payload_is_explicit_and_never_starts_implicitly():
    module = _driver()
    assert module.command_payload("start", "7", "A8 first-use start") == {
        "schema_version": "wuji.api.v2",
        "command": "start",
        "expected_version": "7",
        "reason": "A8 first-use start",
    }
    try:
        module.command_payload("resume", "7", "not in this bounded driver")
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("driver unexpectedly accepted an unbounded command")


def test_driver_refuses_non_local_base_url_and_sensitive_route():
    module = _driver()
    try:
        module._local_base_url("https://example.invalid")
    except module.DriverBlocked:
        pass
    else:
        raise AssertionError("driver must not contact an external target")
    assert not module._allowed_path("/internal/v2/model/chat/completions")
    assert module._allowed_path("/api/v2/tasks/task-fixture/readiness")
