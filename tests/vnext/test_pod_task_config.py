"""The runtime host's Task list is parsed and bounded without Kubernetes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _load_module():
    """Load by path: the deployment-only Kubernetes client stays out of this test."""

    path = REPOSITORY_ROOT / "ops" / "vnext" / "pod_task_config.py"
    spec = importlib.util.spec_from_file_location("wuji_pod_task_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pod_task_config = _load_module()


def test_each_task_keeps_its_own_config_and_receiver():
    config = {
        "tasks": [
            {"task_config": {"task_id": "a"}, "receiver": {"receiver_id": "ra"}},
            {"task_config": {"task_id": "b"}, "receiver": {"receiver_id": "rb"}},
        ]
    }

    entries = pod_task_config.task_entries(config)

    assert [entry[0] for entry in entries] == ["a", "b"]
    assert [entry[2]["receiver_id"] for entry in entries] == ["ra", "rb"]


def test_the_single_task_shape_stays_readable():
    config = {"task_config": {"task_id": "only"}, "receiver": {"receiver_id": "r"}}

    assert [entry[0] for entry in pod_task_config.task_entries(config)] == ["only"]


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"tasks": []},
        {"tasks": [{"task_config": {"task_id": "a"}, "receiver": {}}] * 65},
        {"tasks": [{"task_config": {"task_id": "a"}, "receiver": {}}, {"task_config": {"task_id": "a"}, "receiver": {}}]},
        {"tasks": [{"task_config": {"task_id": "a"}, "receiver": {}, "extra": 1}]},
        {"tasks": [{"task_config": {}, "receiver": {}}]},
        {"tasks": [{"task_config": {"task_id": "a"}, "receiver": "not-a-mapping"}]},
        {"task_config": {"task_id": "a"}},
    ],
)
def test_an_incomplete_or_duplicated_task_list_is_refused(config):
    with pytest.raises(ValueError):
        pod_task_config.task_entries(config)


def test_only_a_ready_task_is_eligible_for_new_starts():
    class Observation:
        def __init__(self, state):
            self.state = state

    assert pod_task_config.start_eligible_task_ids(
        {
            "b": Observation("not_ready"),
            "a": Observation("ready"),
            "c": "error",
        }
    ) == ("a",)
    assert pod_task_config.start_eligible_task_ids({}) == ()
    with pytest.raises(ValueError):
        pod_task_config.start_eligible_task_ids(())
