"""The deployment bearer refresh is bounded, planned and guarded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import util as importlib_util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib_util.spec_from_file_location(
    "vnext_refresh_credentials", ROOT / "scripts/vnext/refresh_credentials.py"
)
assert SPEC is not None and SPEC.loader is not None
refresh = importlib_util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


def test_the_plan_covers_every_consumer_with_one_fixed_subject():
    assert set(refresh.PLAN) == {
        "runtime-credentials",
        "scheduler-credentials",
        "gates-credentials",
        "api-credentials",
    }
    flattened = {
        (secret, field): value
        for secret, fields in refresh.PLAN.items()
        for field, value in fields.items()
    }
    assert flattened == {
        ("runtime-credentials", "receiver.token"): ("receiver", ["controller"]),
        ("runtime-credentials", "service.token"): ("pod-controller", ["controller"]),
        ("scheduler-credentials", "service.token"): ("scheduler", ["scheduler"]),
        ("gates-credentials", "collector.token"): ("collector", ["collector"]),
        ("gates-credentials", "service.token"): ("gate", ["gate"]),
        ("api-credentials", "service.token"): ("operator", ["operator"]),
    }
    # No deployment bearer is minted for a human operator: owner actions mint
    # their own bounded bearer per command.
    assert all(
        subject != "operator" or [roles] == [["operator"]]
        for subject, roles in flattened.values()
    )
    assert set(refresh.CONSUMER_DEPLOYMENTS) == {"api", "runtime", "scheduler", "gates"}


@pytest.mark.parametrize("value", [0, 0.5, 72.5, 100, -1, "24", True])
def test_a_ttl_outside_the_published_window_is_refused(value):
    with pytest.raises(ValueError, match="ttl_hours"):
        refresh.parse_ttl_hours(value)


@pytest.mark.parametrize("value", [1, 4, 24, 72])
def test_a_ttl_inside_the_published_window_is_accepted(value):
    assert refresh.parse_ttl_hours(value) == float(value)


def test_a_minted_bearer_carries_the_deployment_claims_and_a_bounded_lifetime():
    import base64
    import json

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    moment = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    claims = refresh.claims_for(
        "receiver",
        ["controller"],
        tenant_id="tenant-fixture",
        issuer="https://identity.fixture.invalid",
        audience="wuji-fixture",
        ttl_seconds=3600,
        moment=moment,
    )
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["nbf"] == claims["iat"] - refresh.BACKDATE_SECONDS
    assert claims["jti"]

    token = refresh.mint(claims, signing_key_pem=pem)
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    decoded = json.loads(base64.urlsafe_b64decode(payload))
    assert decoded["sub"] == "receiver"
    assert decoded["roles"] == ["controller"]
    assert decoded["tenant_id"] == "tenant-fixture"
    assert decoded["iss"] == "https://identity.fixture.invalid"
    assert decoded["aud"] == "wuji-fixture"
    assert decoded["exp"] == claims["exp"]

    # The printed summary never carries token bytes.
    material, summary = refresh.refresh_plan(
        tenant_id="tenant-fixture",
        issuer="https://identity.fixture.invalid",
        audience="wuji-fixture",
        ttl_seconds=3600,
        signing_key_pem=pem,
        moment=moment,
    )
    body = json.dumps({"material": material, "summary": summary})
    assert token not in body
    assert set(material) == set(refresh.PLAN)
    assert all(item["ttl_seconds"] == 3600 for item in summary)


def test_a_live_attempt_refuses_the_rotation_unless_explicitly_allowed():
    live = {"tasks_in_window": 1, "enabled_receivers": 0, "unexited_runs": 3}
    with pytest.raises(RuntimeError, match="tasks_in_window=1"):
        refresh.guard_live_attempts(live)
    assert refresh.guard_live_attempts(live, allow=True) == live

    receiver_only = {"tasks_in_window": 0, "enabled_receivers": 1, "unexited_runs": 0}
    with pytest.raises(RuntimeError, match="enabled_receivers=1"):
        refresh.guard_live_attempts(receiver_only)

    # Stale Runs from finished Tasks never block a rotation.
    assert refresh.guard_live_attempts(
        {"tasks_in_window": 0, "enabled_receivers": 0, "unexited_runs": 6}
    ) == {"tasks_in_window": 0, "enabled_receivers": 0, "unexited_runs": 6}


def test_the_live_query_counts_only_an_open_window_and_an_enabled_receiver():
    sql = " ".join(refresh.LIVE_WINDOW_SQL.split())
    assert "t.activated_at IS NOT NULL" in sql
    assert "make_interval(secs => GREATEST(1," in sql
    assert "max_elapsed_seconds" in sql
    assert "scheduler_receiver" in sql
    assert "process_state <> 'exited'" in sql
