"""Closed fixture capability boundary; no model, target or cluster calls."""
from copy import deepcopy
import pytest
from wuji_core.admission.registry import _mechanism_candidate_tool_allowed as allowed
from wuji_core.admission.mechanism_fixture import FIRST_USE_FIXTURE_ORIGIN


def definition():
    return {"evaluation_mode": "mechanism_synthetic",
        "mechanism_http_origins": [FIRST_USE_FIXTURE_ORIGIN],
        "task": {"authorization_scope": [{"protocol": "http", "port": 8080,
            "host": "first-use-fixture.wuji-vnext-test.svc"}]}}


def test_closed_fixture_allows_explore_http_and_stored_workspace_reads():
    assert allowed(definition(), "explore", ["http_target"], "live_capture")
    assert allowed(definition(), "reason", ["workspace_read"], "live_capture")
    assert not allowed(definition(), "reason", ["http_target"], "live_capture")
    assert not allowed(definition(), "report", ["http_target"], "live_capture")
    assert not allowed(definition(), "explore", ["http_target"], "imported_unverified")


def test_legacy_mechanism_keeps_the_fixture_workspace_only_boundary():
    d={"evaluation_mode": "mechanism_synthetic"}
    assert allowed(d, "explore", ["workspace_read"], "fixture_capture")
    assert not allowed(d, "explore", ["workspace_read"], "live_capture")
    assert not allowed(d, "explore", ["http_target"], "fixture_capture")
    d=definition();d["evaluation_mode"]="real_model"
    assert not allowed(d, "explore", ["http_target"], "live_capture")


@pytest.mark.parametrize("change", ["scope", "origin"])
def test_owner_fixture_cannot_expand_to_another_origin(change):
    d=deepcopy(definition())
    if change=="scope":d["task"]["authorization_scope"][0]["host"]="unapproved.invalid"
    else:d["mechanism_http_origins"]=["http://unapproved.invalid:8080"]
    with pytest.raises(ValueError):allowed(d, "explore", ["http_target"], "live_capture")
