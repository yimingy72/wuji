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
task_entries = pod_task_config.task_entries
entry_has_endpoint = pod_task_config.entry_has_endpoint
entry_service_names = pod_task_config.entry_service_names
task_supervisor_url = pod_task_config.task_supervisor_url
DEFAULT_NAMES = {"agent": "task-agent", "kali": "task-kali"}


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


def test_an_explicit_empty_task_list_is_the_empty_platform_state():
    assert pod_task_config.task_entries({"tasks": []}) == []


@pytest.mark.parametrize(
    "config",
    [
        {},
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


def test_a_task_may_publish_its_own_service_names_and_supervisor_origin():
    """Two live Task Pods must not share one Service name."""

    config = {
        "tasks": [
            {
                "task_config": {"task_id": "task-a"},
                "receiver": {},
                "service_names": {"agent": "task-agent-a", "kali": "task-kali-a"},
                "supervisor_url": "https://task-agent-a.wuji-vnext-test.svc:8443",
            },
            {"task_config": {"task_id": "task-b"}, "receiver": {}},
        ]
    }

    assert [entry[0] for entry in task_entries(config)] == ["task-a", "task-b"]
    assert entry_has_endpoint(config, "task-a") is True
    assert entry_has_endpoint(config, "task-b") is False
    assert entry_service_names(config["tasks"][0], DEFAULT_NAMES) == {
        "agent": "task-agent-a",
        "kali": "task-kali-a",
    }
    assert entry_service_names(config["tasks"][1], DEFAULT_NAMES) == DEFAULT_NAMES
    assert task_supervisor_url(config["tasks"][0]).startswith("https://task-agent-a.")
    assert task_supervisor_url(config["tasks"][1]) is None


@pytest.mark.parametrize(
    "names",
    [
        {"agent": "Task-Agent-A", "kali": "task-kali-a"},
        {"agent": "task-agent-a", "kali": "task-kali-a-"},
        {"agent": "task agent", "kali": "task-kali-a"},
        {"agent": "a" * 64, "kali": "task-kali-a"},
        {"agent": "task-agent-a"},
    ],
)
def test_a_per_task_service_pair_must_be_dns_labels(names):
    with pytest.raises(ValueError):
        entry_service_names(
            {"service_names": names, "task_config": {}, "receiver": {}}, DEFAULT_NAMES
        )


def test_a_per_task_supervisor_origin_must_be_bounded_https():
    with pytest.raises(ValueError):
        task_supervisor_url({"supervisor_url": "http://task-agent-a.svc:8443"})
    with pytest.raises(ValueError):
        task_supervisor_url({"supervisor_url": "https://" + "a" * 300})


def test_an_unknown_entry_key_is_still_refused():
    with pytest.raises(ValueError):
        task_entries(
            {
                "tasks": [
                    {"task_config": {"task_id": "task-a"}, "receiver": {}, "extra": True}
                ]
            }
        )
