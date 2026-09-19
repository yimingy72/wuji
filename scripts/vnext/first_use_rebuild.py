#!/usr/bin/env python3
"""Rebuild the first-use source layer on the fixed 5cdbd17 images.

This is deliberately not a general image builder.  It accepts only the known
first-use delta, proves that the dependency-producing inputs are byte-identical
to the old source revision, verifies the fixed local base image IDs and their
OCI revision labels, and then overlays changed files from ``git archive HEAD``.
No dependency installation command is run.

The resulting ``images.json`` has the same per-target fields consumed by
``scripts/vnext/k8s.py publish``.  Publishing remains a separate operation; this
script never contacts a registry and has no registry-port setting.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "work/vnext/k8s"
TARGETS = ("agent", "platform", "kali")
EXPECTED_BASE_REVISION = "5cdbd170939f1d2e410868ab591381331f5cdba9"
EXPECTED_BASE_IMAGES = {
    "agent": "sha256:491542e99755ca381f432aa4d8fdf8450a86f9f9ab93fb7459d1f46ae6649a78",
    "platform": "sha256:eed223946fd0394c7e33b90a5f78df3643d378d467405c3ddd31fdf8792229db",
    "kali": "sha256:cab422446dfab53ec22839f0bd3f1ae1262846ac60ccb0bad211735b539b759b",
}
EXPECTED_BASE_TAGS = {target: f"wuji-vnext-{target}:c1" for target in TARGETS}
IMAGE_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")

# These are every input used by ops/vnext/images/Dockerfile to choose or install
# platform/agent/kali dependencies.  Other Dockerfiles (notably LiteLLM) build a
# separate image and are reported outside this three-image recovery operation.
REUSED_DEPENDENCY_INPUTS = (
    "ops/vnext/images/Dockerfile",
    "ops/vnext/pyproject.toml",
    "ops/vnext/uv.lock",
    "packages/maf-worker/pyproject.toml",
    "packages/maf-worker/uv.lock",
    "packages/task-runtime/pyproject.toml",
    "packages/wuji-core/pyproject.toml",
)
SUPPORTED_DOCKERFILE_SHA256 = "b4a56d2f67f3d783a9df5a5e4465329493d8510a947f4619b96f207bccaff524"

# The exact image-resident source delta between 5cdbd17 and the first-use
# candidate.  Expanding this set requires a fresh review of COPY coverage and
# dependency semantics; an unknown path must not be silently omitted.
EXPECTED_IMAGE_SOURCE_DELTA = frozenset(
    {
        "ops/vnext/launch_adapter.py",
        "ops/vnext/synthetic_model.py",
        "ops/vnext/task_launch.py",
        "ops/vnext/task_model_keys.py",
        "packages/wuji-core/src/wuji_core/admission/mechanism_fixture.py",
        "packages/wuji-core/src/wuji_core/admission/tools.py",
        "packages/wuji-core/src/wuji_core/execution/launch.py",
        "packages/wuji-core/src/wuji_core/scheduling/claims.py",
    }
)

# These first-use files execute on the deployment host, belong to the separate
# LiteLLM image, or implement this recovery tool.  They are included in the
# proof as non-embedded changes rather than being described as ignored.
ALLOWED_NON_IMAGE_FILES = frozenset(
    {
        "AGENTS.md",
        "apps/web/Dockerfile",
        "ops/vnext/images/Dockerfile.web-permissions",
        "ops/vnext/first_use_catalog.py",
        "ops/vnext/images/Dockerfile.litellm",
        "ops/vnext/images/Dockerfile.litellm-prisma-compat",
        "ops/vnext/images/litellm-freeze-20260919-r2.json",
        "ops/vnext/images/litellm-freeze-20260919.json",
        "ops/vnext/images/litellm-prisma.toml",
        "ops/vnext/kubernetes/first_use.py",
        "scripts/vnext/first_use_gateway.py",
        "scripts/vnext/first_use_platform.py",
        "scripts/vnext/first_use_rebuild.py",
    }
)
ALLOWED_NON_IMAGE_PREFIXES = ("docs/", "tests/")


class RebuildError(RuntimeError):
    """The fixed source-overlay contract was not satisfied."""


@dataclass(frozen=True, slots=True)
class CopyRule:
    source: str
    destination: str
    targets: frozenset[str]
    directory: bool = False


@dataclass(frozen=True, slots=True)
class Change:
    status: str
    path: str


@dataclass(frozen=True, slots=True)
class Overlay:
    source: str
    destination: str
    targets: tuple[str, ...]
    git_mode: str


ALL_TARGETS = frozenset(TARGETS)
PLATFORM_TARGETS = frozenset(("platform", "kali"))
COPY_RULES = (
    CopyRule("packages/wuji-core", "/opt/wuji/packages/wuji-core", ALL_TARGETS, True),
    CopyRule("packages/maf-worker", "/opt/wuji/packages/maf-worker", ALL_TARGETS, True),
    CopyRule("packages/task-runtime", "/opt/wuji/packages/task-runtime", ALL_TARGETS, True),
    CopyRule("services/maf-supervisor", "/opt/wuji/services/maf-supervisor", ALL_TARGETS, True),
    CopyRule("ops/vnext/pyproject.toml", "/opt/wuji/ops/vnext/pyproject.toml", PLATFORM_TARGETS),
    CopyRule("ops/vnext/uv.lock", "/opt/wuji/ops/vnext/uv.lock", PLATFORM_TARGETS),
    CopyRule("services/wuji-runtime", "/opt/wuji/services/wuji-runtime", PLATFORM_TARGETS, True),
    CopyRule("services/wuji-launch", "/opt/wuji/services/wuji-launch", PLATFORM_TARGETS, True),
    CopyRule("services/wuji-api", "/opt/wuji/services/wuji-api", PLATFORM_TARGETS, True),
    CopyRule("services/wuji-web-gateway", "/opt/wuji/services/wuji-web-gateway", PLATFORM_TARGETS, True),
    CopyRule("services/wuji-scheduler", "/opt/wuji/services/wuji-scheduler", PLATFORM_TARGETS, True),
    CopyRule("ops/vnext/deployment_common.py", "/opt/wuji/ops/vnext/deployment_common.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/gate_deployment.py", "/opt/wuji/ops/vnext/gate_deployment.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/kali_deployment.py", "/opt/wuji/ops/vnext/kali_deployment.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/pod_deployment.py", "/opt/wuji/ops/vnext/pod_deployment.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/pod_task_config.py", "/opt/wuji/ops/vnext/pod_task_config.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/launch_adapter.py", "/opt/wuji/ops/vnext/launch_adapter.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/task_model_keys.py", "/opt/wuji/ops/vnext/task_model_keys.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/bootstrap.py", "/opt/wuji/ops/vnext/bootstrap.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/synthetic_model.py", "/opt/wuji/ops/vnext/synthetic_model.py", PLATFORM_TARGETS),
    CopyRule("ops/vnext/task_launch.py", "/opt/wuji/ops/vnext/task_launch.py", PLATFORM_TARGETS),
    CopyRule(
        "ops/vnext/kubernetes/task-owner-rbac.json",
        "/opt/wuji/ops/vnext/kubernetes/task-owner-rbac.json",
        PLATFORM_TARGETS,
    ),
    CopyRule("services/wuji-kali-executor", "/opt/wuji/services/wuji-kali-executor", PLATFORM_TARGETS, True),
)


def _run(
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    input_bytes: bytes | None = None,
    timeout: int = 120,
) -> bytes:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RebuildError(f"command failed ({result.returncode}): {' '.join(command)}: {detail}")
    return result.stdout


def _git(root: Path, *arguments: str, timeout: int = 120) -> bytes:
    return _run(("git", *arguments), cwd=root, timeout=timeout)


def current_revision(root: Path) -> str:
    revision = _git(root, "rev-parse", "HEAD").decode().strip()
    if not COMMIT.fullmatch(revision):
        raise RebuildError("HEAD did not resolve to a full commit SHA")
    return revision


def load_base_inventory(path: Path) -> dict[str, dict[str, str]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RebuildError(f"cannot read base image inventory: {error}") from error
    if not isinstance(document, dict) or set(document) != set(TARGETS):
        raise RebuildError("base inventory must contain exactly agent, platform, and kali")
    result: dict[str, dict[str, str]] = {}
    for target in TARGETS:
        value = document[target]
        if not isinstance(value, dict):
            raise RebuildError(f"base inventory entry {target} is not an object")
        required = {"id", "exporter_digest", "source_revision", "tag"}
        if not required.issubset(value):
            raise RebuildError(f"base inventory entry {target} lacks required fields")
        entry = {key: str(value[key]) for key in required}
        if entry["source_revision"] != EXPECTED_BASE_REVISION:
            raise RebuildError(f"{target} does not use the fixed 5cdbd17 source revision")
        if entry["id"] != EXPECTED_BASE_IMAGES[target]:
            raise RebuildError(f"{target} image ID differs from the reviewed fixed image")
        if entry["exporter_digest"] != EXPECTED_BASE_IMAGES[target]:
            raise RebuildError(f"{target} exporter digest differs from the reviewed fixed image")
        if entry["tag"] != EXPECTED_BASE_TAGS[target]:
            raise RebuildError(f"{target} tag differs from the reviewed local base tag")
        result[target] = entry
    return result


def _git_file(root: Path, revision: str, path: str) -> bytes:
    try:
        return _git(root, "show", f"{revision}:{path}")
    except RebuildError as error:
        raise RebuildError(f"required dependency input is missing at {revision[:12]}: {path}") from error


def verify_ancestry(root: Path, base_revision: str, revision: str) -> None:
    if base_revision == revision:
        raise RebuildError("the old source revision and current revision are identical")
    result = subprocess.run(
        ("git", "merge-base", "--is-ancestor", base_revision, revision),
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RebuildError("old source_revision is not an ancestor of the fixed current commit")


def verify_dependency_inputs(root: Path, base_revision: str, revision: str) -> dict[str, dict[str, Any]]:
    proof: dict[str, dict[str, Any]] = {}
    for path in REUSED_DEPENDENCY_INPUTS:
        old = _git_file(root, base_revision, path)
        current = _git_file(root, revision, path)
        if old != current:
            raise RebuildError(f"dependency-producing input changed since the base image: {path}")
        digest = sha256(current).hexdigest()
        proof[path] = {
            "base_sha256": digest,
            "current_sha256": digest,
            "byte_identical": True,
        }
    dockerfile_digest = proof["ops/vnext/images/Dockerfile"]["current_sha256"]
    if dockerfile_digest != SUPPORTED_DOCKERFILE_SHA256:
        raise RebuildError("the Dockerfile is identical to base but not the reviewed COPY contract")
    return proof


def changed_files(root: Path, base_revision: str, revision: str) -> list[Change]:
    raw = _git(
        root,
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        f"{base_revision}..{revision}",
    )
    fields = raw.decode("utf-8", errors="strict").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    if len(fields) % 2:
        raise RebuildError("unexpected git name-status output")
    return [Change(fields[index], fields[index + 1]) for index in range(0, len(fields), 2)]


def _copy_rule(path: str) -> CopyRule | None:
    matches = []
    for rule in COPY_RULES:
        if path == rule.source or (rule.directory and path.startswith(rule.source + "/")):
            matches.append(rule)
    if len(matches) > 1:
        raise RebuildError(f"ambiguous reviewed COPY mapping for {path}")
    return matches[0] if matches else None


def _destination(rule: CopyRule, path: str) -> str:
    if not rule.directory:
        return rule.destination
    relative = PurePosixPath(path).relative_to(PurePosixPath(rule.source))
    return str(PurePosixPath(rule.destination) / relative)


def _git_mode(root: Path, revision: str, path: str) -> str:
    line = _git(root, "ls-tree", revision, "--", path).decode().strip()
    parts = line.split(None, 3)
    if len(parts) != 4 or parts[3] != path:
        raise RebuildError(f"cannot resolve changed path in fixed commit: {path}")
    mode, object_type = parts[0], parts[1]
    if object_type != "blob" or mode not in {"100644", "100755"}:
        raise RebuildError(f"changed image source is not a regular tracked file: {path}")
    return mode


def classify_changes(root: Path, revision: str, changes: Iterable[Change]) -> tuple[list[Overlay], list[dict[str, str]]]:
    overlays: list[Overlay] = []
    outside: list[dict[str, str]] = []
    for change in changes:
        if change.status not in {"A", "M"}:
            raise RebuildError(
                f"source-overlay recovery refuses deletion, rename, type, or unresolved changes: "
                f"{change.status} {change.path}"
            )
        rule = _copy_rule(change.path)
        if rule is not None:
            overlays.append(
                Overlay(
                    source=change.path,
                    destination=_destination(rule, change.path),
                    targets=tuple(target for target in TARGETS if target in rule.targets),
                    git_mode=_git_mode(root, revision, change.path),
                )
            )
            continue
        if change.path in ALLOWED_NON_IMAGE_FILES:
            category = "separate_image_or_deployment_host"
        elif change.path.startswith(ALLOWED_NON_IMAGE_PREFIXES):
            category = "documentation_or_test_evidence"
        else:
            raise RebuildError(f"changed path is outside every reviewed image/non-image scope: {change.path}")
        outside.append({"path": change.path, "status": change.status, "classification": category})

    actual = {overlay.source for overlay in overlays}
    if actual != EXPECTED_IMAGE_SOURCE_DELTA:
        missing = sorted(EXPECTED_IMAGE_SOURCE_DELTA - actual)
        extra = sorted(actual - EXPECTED_IMAGE_SOURCE_DELTA)
        raise RebuildError(f"first-use image source delta differs from the reviewed set; missing={missing}, extra={extra}")
    return sorted(overlays, key=lambda item: item.source), sorted(outside, key=lambda item: item["path"])


def make_plan(root: Path, inventory: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    revisions = {str(entry["source_revision"]) for entry in inventory.values()}
    if revisions != {EXPECTED_BASE_REVISION}:
        raise RebuildError("the three base images do not share the fixed source revision")
    revision = current_revision(root)
    verify_ancestry(root, EXPECTED_BASE_REVISION, revision)
    dependencies = verify_dependency_inputs(root, EXPECTED_BASE_REVISION, revision)
    overlays, outside = classify_changes(
        root,
        revision,
        changed_files(root, EXPECTED_BASE_REVISION, revision),
    )
    by_target = {
        target: [
            {
                "source": overlay.source,
                "destination": overlay.destination,
                "git_mode": overlay.git_mode,
            }
            for overlay in overlays
            if target in overlay.targets
        ]
        for target in TARGETS
    }
    if any(not entries for entries in by_target.values()):
        raise RebuildError("every fixed image must receive at least one reviewed source overlay")
    return {
        "schema": "wuji.first-use-source-overlay-plan.v1",
        "base_source_revision": EXPECTED_BASE_REVISION,
        "current_source_revision": revision,
        "ancestry_verified": True,
        "dependency_inputs": dependencies,
        "overlays": by_target,
        "outside_overlay_changes": outside,
        "dependency_install_commands": [],
        "context_export": {"command": ["git", "archive", revision], "fixed_commit": True},
        "docker_validation": "required_at_build",
    }


def overlay_dockerfile(target: str, base_tag: str, overlays: Sequence[Mapping[str, str]]) -> str:
    if target not in TARGETS or base_tag != EXPECTED_BASE_TAGS[target]:
        raise RebuildError("unreviewed overlay base")
    if not overlays:
        raise RebuildError(f"no overlay files selected for {target}")
    lines = [f"FROM {base_tag}"]
    for item in overlays:
        source = str(item["source"])
        destination = str(item["destination"])
        if source not in EXPECTED_IMAGE_SOURCE_DELTA or not destination.startswith("/opt/wuji/"):
            raise RebuildError(f"unreviewed COPY instruction for {target}: {source}")
        mode = str(item["git_mode"])
        if mode not in {"100644", "100755"}:
            raise RebuildError(f"unreviewed file mode: {source}")
        # Archive extraction runs under a private umask. Image source files
        # must instead keep their tracked readable mode for the non-root UID.
        lines.append("COPY --chmod=" + mode[-3:] + " " + json.dumps([source, destination], separators=(",", ":")))
    return "\n".join(lines) + "\n"


def docker_build_command(
    *,
    dockerfile: Path,
    context: Path,
    metadata: Path,
    tag: str,
    revision: str,
    base_revision: str,
) -> list[str]:
    return [
        "docker",
        "build",
        "--pull=false",
        "--network=none",
        "--platform",
        "linux/arm64",
        "--metadata-file",
        str(metadata),
        "--label",
        "org.opencontainers.image.revision=" + revision,
        "--label",
        "wuji.dev.source-overlay.base-revision=" + base_revision,
        "--label",
        "wuji.dev.source-overlay.dependencies=reused",
        "--progress=plain",
        "-t",
        tag,
        "-f",
        str(dockerfile),
        str(context),
    ]


def _save_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def _run_logged(command: Sequence[str], raw: Path, name: str, *, timeout: int = 1800) -> bytes:
    stdout = raw / f"{name}.stdout"
    stderr = raw / f"{name}.stderr"
    with stdout.open("xb") as out, stderr.open("xb") as err:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            stdout=out,
            stderr=err,
            timeout=timeout,
            check=False,
        )
    _save_exclusive(raw / f"{name}.exit", str(result.returncode).encode())
    if result.returncode:
        raise RebuildError(f"{name} failed; inspect {raw}")
    return stdout.read_bytes()


def _inspect_local_base(target: str, entry: Mapping[str, str], raw: Path) -> dict[str, Any]:
    data = _run_logged(("docker", "image", "inspect", entry["tag"]), raw, f"base-{target}-inspect", timeout=30)
    try:
        documents = json.loads(data)
        image = documents[0]
    except (json.JSONDecodeError, IndexError, KeyError, TypeError) as error:
        raise RebuildError(f"cannot parse local {target} base image inspection") from error
    labels = image.get("Config", {}).get("Labels", {}) or {}
    if image.get("Id") != entry["id"]:
        raise RebuildError(f"local {target} tag does not resolve to the fixed image ID")
    if labels.get("org.opencontainers.image.revision") != EXPECTED_BASE_REVISION:
        raise RebuildError(f"local {target} image lacks the exact old revision label")
    if (image.get("Os"), image.get("Architecture")) != ("linux", "arm64"):
        raise RebuildError(f"local {target} image is not linux/arm64")
    return {
        "tag": entry["tag"],
        "expected_id": entry["id"],
        "actual_id": image["Id"],
        "revision_label": labels["org.opencontainers.image.revision"],
        "platform": "linux/arm64",
        "verified": True,
    }


def _export_context(root: Path, revision: str, destination: Path, raw: Path) -> None:
    destination.mkdir(mode=0o700)
    archive_stderr = raw / "git-archive.stderr"
    extract_stderr = raw / "context-extract.stderr"
    with archive_stderr.open("xb") as archive_error, extract_stderr.open("xb") as extract_error:
        archive = subprocess.Popen(
            ("git", "archive", "--format=tar", revision),
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=archive_error,
        )
        assert archive.stdout is not None
        extract = subprocess.run(
            ("tar", "-x", "-C", str(destination)),
            stdin=archive.stdout,
            stdout=subprocess.DEVNULL,
            stderr=extract_error,
            timeout=300,
            check=False,
        )
        archive.stdout.close()
        archive_status = archive.wait(timeout=30)
    _save_exclusive(raw / "git-archive.exit", str(archive_status).encode())
    _save_exclusive(raw / "context-extract.exit", str(extract.returncode).encode())
    if archive_status or extract.returncode:
        raise RebuildError("fixed-commit git archive export failed")


def _new_output_directory(state: Path) -> Path:
    resolved = state.resolve()
    allowed = STATE.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise RebuildError("state directory must remain under the ignored work/vnext/k8s directory")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    return Path(tempfile.mkdtemp(prefix="first-use-rebuild-", dir=resolved))


def build(root: Path, inventory: Mapping[str, Mapping[str, str]], plan: Mapping[str, Any], raw: Path) -> dict[str, Any]:
    revision = str(plan["current_source_revision"])
    _save_exclusive(raw / "rebuild-plan.json", json.dumps(plan, sort_keys=True, indent=2).encode())
    _save_exclusive(raw / "source-commit.txt", revision.encode())

    base_checks = {
        target: _inspect_local_base(target, inventory[target], raw)
        for target in TARGETS
    }
    context = raw / "context"
    _export_context(root, revision, context, raw)

    images: dict[str, dict[str, str]] = {}
    build_records: dict[str, dict[str, Any]] = {}
    for target in TARGETS:
        dockerfile = raw / f"Dockerfile.{target}.source-overlay"
        text = overlay_dockerfile(target, inventory[target]["tag"], plan["overlays"][target])
        _save_exclusive(dockerfile, text.encode())
        metadata = raw / f"{target}.metadata.json"
        tag = f"wuji-vnext-{target}:first-use-{revision[:12]}"
        command = docker_build_command(
            dockerfile=dockerfile,
            context=context,
            metadata=metadata,
            tag=tag,
            revision=revision,
            base_revision=EXPECTED_BASE_REVISION,
        )
        _run_logged(command, raw, f"build-{target}")
        inspection = json.loads(
            _run_logged(("docker", "image", "inspect", tag), raw, f"image-{target}", timeout=30)
        )[0]
        labels = inspection.get("Config", {}).get("Labels", {}) or {}
        if (inspection.get("Os"), inspection.get("Architecture")) != ("linux", "arm64"):
            raise RebuildError(f"rebuilt {target} image has the wrong platform")
        if labels.get("org.opencontainers.image.revision") != revision:
            raise RebuildError(f"rebuilt {target} image has the wrong source revision label")
        if labels.get("wuji.dev.source-overlay.base-revision") != EXPECTED_BASE_REVISION:
            raise RebuildError(f"rebuilt {target} image lost the dependency reuse label")
        image_id = str(inspection.get("Id", ""))
        if not IMAGE_DIGEST.fullmatch(image_id):
            raise RebuildError(f"rebuilt {target} image has no fixed image ID")
        try:
            exporter_digest = str(json.loads(metadata.read_text(encoding="utf-8"))["containerimage.digest"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise RebuildError(f"rebuilt {target} metadata lacks containerimage.digest") from error
        if not IMAGE_DIGEST.fullmatch(exporter_digest):
            raise RebuildError(f"rebuilt {target} exporter digest is invalid")
        images[target] = {
            "tag": tag,
            "id": image_id,
            "exporter_digest": exporter_digest,
            "source_revision": revision,
        }
        build_records[target] = {
            "base_id": inventory[target]["id"],
            "output_id": image_id,
            "exporter_digest": exporter_digest,
            "overlay_files": [item["source"] for item in plan["overlays"][target]],
            "dependency_install_ran": False,
            "pull_allowed": False,
            "build_network": "none",
        }

    images_bytes = json.dumps(images, sort_keys=True, indent=2).encode()
    _save_exclusive(raw / "images.json", images_bytes)
    proof = {
        "schema": "wuji.first-use-dependency-reuse-proof.v1",
        "base_source_revision": EXPECTED_BASE_REVISION,
        "current_source_revision": revision,
        "ancestry_verified": True,
        "dependency_inputs": plan["dependency_inputs"],
        "base_images": base_checks,
        "builds": build_records,
        "outside_overlay_changes": plan["outside_overlay_changes"],
        "context_export": plan["context_export"],
        "images_inventory_sha256": sha256(images_bytes).hexdigest(),
        "publish_compatibility": {
            "consumer": "scripts/vnext/k8s.py publish",
            "required_fields": ["tag", "id", "exporter_digest", "source_revision"],
            "registry_contacted": False,
            "registry_port": None,
        },
    }
    _save_exclusive(raw / "dependency-reuse-proof.json", json.dumps(proof, sort_keys=True, indent=2).encode())
    return {"raw_directory": str(raw), "images": str(raw / "images.json"), "proof": str(raw / "dependency-reuse-proof.json")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "build"))
    parser.add_argument("--base-inventory", type=Path, required=True)
    parser.add_argument("--state-directory", type=Path, default=STATE)
    args = parser.parse_args()
    inventory = load_base_inventory(args.base_inventory.resolve())
    plan = make_plan(ROOT, inventory)
    if args.command == "plan":
        print(json.dumps(plan, sort_keys=True, indent=2))
        return
    os.umask(0o077)
    raw = _new_output_directory(args.state_directory)
    result = build(ROOT, inventory, plan, raw)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
