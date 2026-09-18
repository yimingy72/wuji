from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from vnext.assert_release_inventory import (
    ReleaseInventoryError,
    assert_release_inventory,
    build_release_inventory,
)


def test_release_inventory_collects_real_inputs_and_hashes(tmp_path):
    (tmp_path / "ops" / "vnext").mkdir(parents=True)
    (tmp_path / "ops" / "vnext" / "pyproject.toml").write_text(
        '[project]\nname="release"\ndependencies=["fastapi==1.0"]\n', encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "1.0.0"}}), encoding="utf-8"
    )
    (tmp_path / "ops" / "vnext" / "images").mkdir()
    dockerfile = tmp_path / "ops" / "vnext" / "images" / "Dockerfile"
    dockerfile.write_text("FROM python:3.13\nENTRYPOINT [\"python\", \"-m\", \"release\"]\n", encoding="utf-8")

    inventory = build_release_inventory(tmp_path)
    assert "fastapi" in inventory.python_distributions
    assert "react" in inventory.npm_packages
    assert inventory.source_artifact_hashes["ops/vnext/images/Dockerfile"]
    assert_release_inventory(inventory)


@pytest.mark.parametrize(
    ("filename", "body"),
    [
        ("package-lock.json", {"packages": {"node_modules/@mariozechner/pi-coding-agent": {}}}),
        ("Dockerfile", "FROM base\nENTRYPOINT [\"cairn\"]\n"),
    ],
)
def test_release_inventory_rejects_legacy_execution(tmp_path, filename, body):
    path = tmp_path / filename
    if isinstance(body, dict):
        path.write_text(json.dumps(body), encoding="utf-8")
    else:
        path.write_text(body, encoding="utf-8")
    inventory = build_release_inventory(tmp_path)
    with pytest.raises(ReleaseInventoryError):
        assert_release_inventory(inventory)


def test_repository_release_inventory_is_nonempty_and_clean():
    root = Path(__file__).resolve().parents[2]
    inventory = build_release_inventory(root)
    assert inventory.source_artifact_hashes
    assert_release_inventory(inventory)
