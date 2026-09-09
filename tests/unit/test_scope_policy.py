"""Independent, bounded vectors for B1 policy normalization and path matching."""
from datetime import UTC, datetime, timedelta

import pytest

from wuji_api.scope_policy import ScopePolicyError, evaluate_scope, normalize_task_draft, normalize_url

pytestmark = pytest.mark.unit


def _path_allowed(path: str) -> bool:
    limits = {
        "max_total_requests": 20, "requests_per_second": 1,
        "max_concurrent_requests": 1, "request_timeout_seconds": 5,
        "max_response_bytes": 1024, "max_runtime_seconds": 60,
    }
    scope = {
        "label": "Independent policy vector", "origins": ["https://example.com"],
        "allowed_path_prefixes": ["/public"], "excluded_path_prefixes": ["/public/logout"],
        "allowed_methods": ["GET", "HEAD"], "limits": limits,
    }
    draft = normalize_task_draft({
        "name": "Independent vector", "scope": {"policy_id": "00000000-0000-4000-8000-000000000001", "version": 1},
        "target_url": f"https://example.com{path}", "tool": "http_observe", "method": "GET", "limits": limits,
    })
    now = datetime(2026, 9, 9, tzinfo=UTC)
    preview = evaluate_scope(draft, scope, {
        "valid_from": now - timedelta(hours=1), "valid_until": now + timedelta(hours=1), "revoked_at": None,
    }, now=now)
    return all(blocker["code"] != "SCOPE_DENIED" for blocker in preview["blockers"])


def test_default_ports_and_host_case_are_canonicalized_without_network_access() -> None:
    assert normalize_url("HTTPS://Example.COM:443/public/a") == "https://example.com/public/a"
    assert normalize_url("http://Example.COM:80/public/a") == "http://example.com/public/a"


def test_scope_prefix_matching_accepts_child_and_rejects_sibling_and_exclusion() -> None:
    assert _path_allowed("/public/a") is True
    assert _path_allowed("/publicity") is False
    assert _path_allowed("/public/logout") is False


@pytest.mark.parametrize("url", [
    "https://example.com/public/%2e%2e/admin",
    "https://example.com/public/%2E%2E/admin",
    "https://example.com/public/%2fadmin",
    "https://example.com/public/%2Fadmin",
])
def test_encoded_dot_segments_and_slashes_are_rejected(url: str) -> None:
    with pytest.raises(ScopePolicyError):
        normalize_url(url)
