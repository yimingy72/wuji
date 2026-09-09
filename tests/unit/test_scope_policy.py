"""Minimal B1 URL and scope-policy vectors.

These tests deliberately exercise the public pure-policy exports only.  The
small adapter below keeps the vectors readable while B1-A1 finalizes the
export names; it must be removed or narrowed before the first B1 run.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

import pytest


def _policy_module():
    try:
        return import_module("wuji_api.scope_policy")
    except ModuleNotFoundError as error:  # pragma: no cover - pre-B1 baseline
        pytest.fail(f"B1 pure policy module is missing: {error}")


def _export(*names: str) -> Callable[..., Any]:
    module = _policy_module()
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    pytest.fail(f"B1 pure policy export not found; tried {', '.join(names)}")


def _normalized_url(value: str) -> str:
    result = _export("normalize_target_url", "normalize_url")(value)
    # A small value object is acceptable, but the policy must expose its
    # canonical URL without requiring a network or resolver.
    if isinstance(result, str):
        return result
    for attribute in ("url", "target_url", "canonical"):
        canonical = getattr(result, attribute, None)
        if isinstance(canonical, str):
            return canonical
    pytest.fail(f"pure URL normalizer returned no canonical URL: {result!r}")


def _path_allowed(path: str) -> bool:
    checker = _export("path_is_allowed", "is_path_allowed", "matches_scope_path")
    try:
        return bool(
            checker(
                path,
                allowed_path_prefixes=["/public"],
                excluded_path_prefixes=["/public/logout"],
            )
        )
    except TypeError:
        # Accommodate the positional form while keeping the policy inputs
        # explicit and independent from any API/database fixture.
        return bool(checker(path, ["/public"], ["/public/logout"]))


def test_default_ports_and_host_case_are_canonicalized_without_network_access() -> None:
    assert _normalized_url("HTTPS://Example.COM:443/public/a") == "https://example.com/public/a"
    assert _normalized_url("http://Example.COM:80/public/a") == "http://example.com/public/a"


def test_scope_prefix_matching_accepts_child_and_rejects_sibling_and_exclusion() -> None:
    assert _path_allowed("/public/a") is True
    assert _path_allowed("/publicity") is False
    assert _path_allowed("/public/logout") is False


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/public/%2e%2e/admin",
        "https://example.com/public/%2E%2E/admin",
        "https://example.com/public/%2fadmin",
        "https://example.com/public/%2Fadmin",
    ],
)
def test_encoded_dot_segments_and_slashes_are_rejected(url: str) -> None:
    normalizer = _export("normalize_target_url", "normalize_url")
    with pytest.raises((ValueError, TypeError)):
        normalizer(url)
