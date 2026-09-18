#!/usr/bin/env python3
"""Inspect the vNext release inputs and reject legacy execution dependencies."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

FORBIDDEN_TOKENS = ("cairn", "pi-coding-agent", "claude-code", "claude-cli")
_PACKAGE_SPLIT = re.compile(r"[<>=!~\[; ]")


def _normalise_package(value: object) -> str:
    raw = str(value).strip().lower()
    return _PACKAGE_SPLIT.split(raw, maxsplit=1)[0].replace("_", "-")


def _contains_forbidden(value: object) -> bool:
    text = str(value).lower()
    return any(token in text for token in FORBIDDEN_TOKENS)


@dataclass(frozen=True, slots=True)
class ReleaseInventory:
    python_distributions: tuple[str, ...]
    npm_packages: tuple[str, ...]
    legacy_runtime_entrypoints: tuple[str, ...]
    cairn_service_dependencies: tuple[str, ...]
    source_artifact_hashes: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "python_distributions": list(self.python_distributions),
            "npm_packages": list(self.npm_packages),
            "legacy_runtime_entrypoints": list(self.legacy_runtime_entrypoints),
            "cairn_service_dependencies": list(self.cairn_service_dependencies),
            "source_artifact_hashes": dict(sorted(self.source_artifact_hashes.items())),
        }

    # A model-like spelling makes the inventory convenient for tests and
    # callers that already consume the other vNext contract objects.
    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        del mode
        return self.as_dict()


class ReleaseInventoryError(RuntimeError):
    """The release contains a legacy execution dependency or no source hash."""


def _read_toml(path: Path) -> Mapping[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _direct_python_dependencies(path: Path) -> set[str]:
    document = _read_toml(path)
    project = document.get("project", {})
    dependencies = project.get("dependencies", []) if isinstance(project, Mapping) else []
    if not isinstance(dependencies, list):
        return set()
    return {_normalise_package(item) for item in dependencies if isinstance(item, str)}


def _lock_packages(path: Path) -> dict[str, Mapping[str, Any]]:
    document = _read_toml(path)
    packages = document.get("package", [])
    if not isinstance(packages, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for item in packages:
        if isinstance(item, Mapping) and isinstance(item.get("name"), str):
            result[_normalise_package(item["name"])] = item
    return result


def _dependency_names(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        yield from (_normalise_package(key) for key in value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield _normalise_package(item)
            elif isinstance(item, Mapping) and isinstance(item.get("name"), str):
                yield _normalise_package(item["name"])


def _python_inventory(root: Path) -> set[str]:
    manifests = [
        root / "ops" / "vnext" / "pyproject.toml",
        root / "apps" / "api" / "pyproject.toml",
        root / "packages" / "wuji-core" / "pyproject.toml",
        root / "packages" / "maf-worker" / "pyproject.toml",
        root / "packages" / "task-runtime" / "pyproject.toml",
    ]
    direct: set[str] = set()
    for path in manifests:
        if path.is_file():
            direct.update(_direct_python_dependencies(path))

    inventory = set(direct)
    for lock_path in (
        root / "ops" / "vnext" / "uv.lock",
        root / "packages" / "maf-worker" / "uv.lock",
    ):
        if not lock_path.is_file():
            continue
        packages = _lock_packages(lock_path)
        pending = [name for name in direct if name in packages]
        visited: set[str] = set()
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            inventory.add(name)
            package = packages.get(name, {})
            for dependency in _dependency_names(package.get("dependencies", [])):
                inventory.add(dependency)
                if dependency in packages and dependency not in visited:
                    pending.append(dependency)
    return inventory


def _package_json_dependencies(path: Path) -> set[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    result: set[str] = set()
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = document.get(section, {})
        if isinstance(values, Mapping):
            result.update(str(key).lower() for key in values)
    return result


def _npm_inventory(root: Path) -> set[str]:
    inventory: set[str] = set()
    for path in (root / "package.json", root / "apps" / "web" / "package.json"):
        if path.is_file():
            inventory.update(_package_json_dependencies(path))

    package_lock = root / "package-lock.json"
    if package_lock.is_file():
        try:
            document = json.loads(package_lock.read_text(encoding="utf-8"))
            packages = document.get("packages", {})
            if isinstance(packages, Mapping):
                for key in packages:
                    if isinstance(key, str) and key.startswith("node_modules/"):
                        inventory.add(key.removeprefix("node_modules/").lower())
        except (OSError, json.JSONDecodeError):
            pass

    # pnpm's lockfile is YAML, but the package keys are stable enough to read
    # without making YAML a runtime requirement for this release check.
    for lock_path in (root / "pnpm-lock.yaml", root / "apps" / "web" / "pnpm-lock.yaml"):
        if not lock_path.is_file():
            continue
        try:
            text = lock_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in re.finditer(r"^\s{2,}/?((?:@[^/\s]+/)?[^/\s@]+)(?:@[^\s:]+)?:", text, re.MULTILINE):
            inventory.add(match.group(1).lower())
    return inventory


def _release_files(root: Path) -> list[Path]:
    candidates: set[Path] = set()
    explicit = (
        root / "package.json",
        root / "package-lock.json",
        root / "pnpm-lock.yaml",
        root / "ops" / "vnext" / "pyproject.toml",
        root / "ops" / "vnext" / "uv.lock",
        root / "apps" / "api" / "pyproject.toml",
        root / "packages" / "wuji-core" / "pyproject.toml",
        root / "packages" / "maf-worker" / "pyproject.toml",
        root / "packages" / "maf-worker" / "uv.lock",
        root / "apps" / "web" / "package.json",
        root / "apps" / "web" / "package-lock.json",
        root / "apps" / "web" / "pnpm-lock.yaml",
    )
    candidates.update(path for path in explicit if path.is_file())
    for directory in (
        root / "ops" / "vnext" / "images",
        root / "ops" / "vnext" / "kubernetes",
        root / "apps" / "api" / "src",
        root / "packages" / "wuji-core" / "src",
        root / "scripts" / "vnext",
    ):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or any(part in {".venv", "node_modules", "__pycache__"} for part in path.parts):
                continue
            if path.suffix.lower() in {".py", ".mjs", ".js", ".json", ".yaml", ".yml", ".toml", ".lock"} or path.name.startswith("Dockerfile"):
                candidates.add(path)
    return sorted(candidates)


def _python_legacy_entries(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return []
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            values = [node.module or ""]
        else:
            continue
        if any(_contains_forbidden(value) for value in values):
            hits.append(f"{path}:{getattr(node, 'lineno', 1)}")
    return hits


def _line_hits(path: Path, *, service_scan: bool) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    hits: list[str] = []
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        if _contains_forbidden(line):
            if service_scan or re.search(r"ENTRYPOINT|CMD|command|args|image|mount|exec|service|health", line, re.I):
                hits.append(f"{path}:{number}")
    return hits


def build_release_inventory(root: str | Path) -> ReleaseInventory:
    root_path = Path(root).resolve()
    files = _release_files(root_path)
    python_distributions = tuple(sorted(_python_inventory(root_path)))
    npm_packages = tuple(sorted(_npm_inventory(root_path)))
    entrypoints: list[str] = []
    service_dependencies: list[str] = []
    for path in files:
        relative = path.relative_to(root_path)
        if path.suffix == ".py" and (
            "ops/vnext" in relative.as_posix()
            or "apps/api/src" in relative.as_posix()
            or "wuji-core/src" in relative.as_posix()
        ):
            entrypoints.extend(_python_legacy_entries(path))
        if path.suffix.lower() in {".yaml", ".yml", ".json"} or path.name.startswith("Dockerfile"):
            entrypoints.extend(_line_hits(path, service_scan=False))
            service_dependencies.extend(_line_hits(path, service_scan=True))

    hashes = {
        path.relative_to(root_path).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    return ReleaseInventory(
        python_distributions=python_distributions,
        npm_packages=npm_packages,
        legacy_runtime_entrypoints=tuple(sorted(set(entrypoints))),
        cairn_service_dependencies=tuple(sorted(set(service_dependencies))),
        source_artifact_hashes=hashes,
    )


def assert_release_inventory(inventory: ReleaseInventory) -> None:
    violations: list[str] = []
    for field_name in ("python_distributions", "npm_packages"):
        values = getattr(inventory, field_name)
        violations.extend(f"{field_name}: {value}" for value in values if _contains_forbidden(value))
    violations.extend(f"legacy_runtime_entrypoints: {value}" for value in inventory.legacy_runtime_entrypoints)
    violations.extend(f"cairn_service_dependencies: {value}" for value in inventory.cairn_service_dependencies)
    if not inventory.source_artifact_hashes:
        violations.append("source_artifact_hashes: no release files were hashed")
    if violations:
        raise ReleaseInventoryError("legacy release inventory violation:\n- " + "\n- ".join(violations))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        inventory = build_release_inventory(args.root)
        assert_release_inventory(inventory)
    except (OSError, ReleaseInventoryError) as error:
        print(error, file=sys.stderr)
        return 1
    document = json.dumps(inventory.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding="utf-8")
    else:
        print(document, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
