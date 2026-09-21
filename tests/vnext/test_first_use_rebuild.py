from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vnext" / "first_use_rebuild.py"
SPEC = importlib.util.spec_from_file_location("first_use_rebuild", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)
BASE_REVISION = "e06fee4816741d42f456192d2ea42b94fb485244"


def base_inventory() -> dict[str, dict[str, str]]:
    return {
        target: {
            "tag": module.EXPECTED_BASE_TAGS[target],
            "id": "sha256:" + {"agent": "1", "platform": "2", "kali": "3"}[target] * 64,
            "exporter_digest": "sha256:" + {"agent": "1", "platform": "2", "kali": "3"}[target] * 64,
            "source_revision": BASE_REVISION,
        }
        for target in module.TARGETS
    }


def test_repository_plan_is_fixed_to_reviewed_base_and_copy_ranges(tmp_path):
    inventory_path = tmp_path / "images.json"
    inventory_path.write_text(json.dumps(base_inventory()), encoding="utf-8")

    inventory = module.load_base_inventory(inventory_path)
    plan = module.make_plan(ROOT, inventory)

    assert plan["base_source_revision"] == BASE_REVISION
    assert plan["current_source_revision"] != BASE_REVISION
    assert plan["ancestry_verified"] is True
    assert set(plan["dependency_inputs"]) == set(module.REUSED_DEPENDENCY_INPUTS)
    assert all(value["byte_identical"] for value in plan["dependency_inputs"].values())
    assert all(module._copy_rule(item["source"]) is not None for item in plan["overlays"]["agent"])
    assert all(module._copy_rule(item["source"]) is not None for item in plan["overlays"]["platform"])
    assert all(module._copy_rule(item["source"]) is not None for item in plan["overlays"]["kali"])
    assert any(
        item["path"].startswith("apps/web/")
        and item["classification"] == "separate_image_or_deployment_host"
        for item in plan["outside_overlay_changes"]
    )


def test_inventory_rejects_a_nonimmutable_base_image(tmp_path):
    inventory = base_inventory()
    inventory["platform"]["id"] = "not-an-image-id"
    path = tmp_path / "images.json"
    path.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(module.RebuildError, match="immutable"):
        module.load_base_inventory(path)


@pytest.mark.parametrize(
    "change",
    [
        module.Change("D", "packages/wuji-core/src/wuji_core/admission/tools.py"),
        module.Change("A", "ops/vnext/unreviewed_runtime.py"),
    ],
)
def test_change_classification_fails_closed_for_deletion_and_unknown_path(change):
    with pytest.raises(module.RebuildError):
        module.classify_changes(ROOT, module.current_revision(ROOT), [change])


def test_overlay_dockerfile_and_build_command_cannot_install_or_pull():
    plan = module.make_plan(ROOT, base_inventory())
    target = "platform"
    dockerfile = module.overlay_dockerfile(
        target,
        module.EXPECTED_BASE_TAGS[target],
        plan["overlays"][target],
    )
    assert dockerfile.startswith("FROM wuji-vnext-platform:c1\n")
    assert "RUN " not in dockerfile
    assert "ADD " not in dockerfile
    assert dockerfile.count("COPY ") == len(plan["overlays"][target])

    command = module.docker_build_command(
        dockerfile=Path("Dockerfile.overlay"),
        context=Path("context"),
        metadata=Path("metadata.json"),
        tag="wuji-vnext-platform:first-use-deadbeef",
        revision="1" * 40,
        base_revision=BASE_REVISION,
    )
    assert "--pull=false" in command
    assert command[command.index("--network=none") + 1] == "--platform"
    assert "linux/arm64" in command


def test_dependency_input_drift_is_rejected(monkeypatch):
    original = module._git_file

    def changed(root, revision, path):
        value = original(root, revision, path)
        if revision != BASE_REVISION and path == "ops/vnext/uv.lock":
            return value + b"\nchanged"
        return value

    monkeypatch.setattr(module, "_git_file", changed)
    with pytest.raises(module.RebuildError, match="dependency-producing input changed"):
        module.verify_dependency_inputs(
            ROOT,
            BASE_REVISION,
            module.current_revision(ROOT),
        )
