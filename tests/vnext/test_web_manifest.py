from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "vnext" / "kubernetes"))
from web import LOCAL_ACCESS_COMMAND, NAMESPACE, build_web_manifests, render_json_documents

IMAGE = "registry.local/wuji-web@sha256:" + "a" * 64


def _by_kind(manifests):
    return {item["kind"]: item for item in manifests}


def test_web_manifest_isolated_arm64_non_root_read_only_and_port_forward_access():
    manifests = build_web_manifests(
        IMAGE,
        api_base_url="https://api.example.test",
        auth_entrypoint="https://auth.example.test/login",
    )
    assert [item["kind"] for item in manifests] == ["ConfigMap", "Deployment", "Service"]
    assert all(item["metadata"]["namespace"] == NAMESPACE for item in manifests)

    deployment = _by_kind(manifests)["Deployment"]
    pod = deployment["spec"]["template"]
    container = pod["spec"]["containers"][0]
    assert pod["spec"]["nodeSelector"] == {"kubernetes.io/arch": "arm64"}
    assert pod["spec"]["automountServiceAccountToken"] is False
    assert pod["spec"]["securityContext"]["runAsNonRoot"] is True
    assert container["image"] == IMAGE
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert {mount["mountPath"] for mount in container["volumeMounts"]} == {
        "/tmp",
        "/usr/share/nginx/html/config.js",
    }

    service = _by_kind(manifests)["Service"]
    assert service["spec"]["ports"] == [{"name": "http", "port": 80, "targetPort": "http"}]
    assert service["metadata"]["annotations"]["wuji.dev/local-access"] == LOCAL_ACCESS_COMMAND


def test_web_manifest_exposes_only_explicit_runtime_configuration():
    config = _by_kind(build_web_manifests(IMAGE, api_base_url="", auth_entrypoint=""))["ConfigMap"]
    script = config["data"]["config.js"]
    assert json.loads(script.removeprefix("window.__WUJI_CONFIG__ = ").rstrip(";\n")) == {
        "apiBaseUrl": "",
        "authEntrypoint": "",
    }


def test_web_manifest_rejects_mutable_images():
    with pytest.raises(ValueError, match="immutable"):
        build_web_manifests("registry.local/wuji-web:latest")


def test_web_manifest_cli_output_is_multi_document_json():
    output = render_json_documents(build_web_manifests(IMAGE))
    documents = [json.loads(document) for document in output.strip().split("\n---\n")]
    assert [document["kind"] for document in documents] == ["ConfigMap", "Deployment", "Service"]
