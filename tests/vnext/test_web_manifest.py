from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "vnext" / "kubernetes"))
from web import LOCAL_ACCESS_URL, NAMESPACE, build_web_manifests, render_json_documents

IMAGE = "registry.local/wuji-web@sha256:" + "a" * 64
GATEWAY_IMAGE = "registry.local/wuji-vnext-platform@sha256:" + "b" * 64


def _by_kind(manifests):
    return {item["kind"]: item for item in manifests}


def test_web_manifest_isolated_arm64_non_root_read_only_and_load_balancer_access():
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
    assert service["spec"]["type"] == "LoadBalancer"
    assert service["spec"]["ports"] == [{"name": "http", "port": 44180, "targetPort": "http"}]
    assert service["metadata"]["annotations"]["wuji.dev/local-access"] == LOCAL_ACCESS_URL


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


def test_web_manifest_can_attach_the_local_browser_session_gateway():
    manifests = build_web_manifests(
        IMAGE,
        auth_entrypoint="/auth/login",
        gateway_image=GATEWAY_IMAGE,
        gateway_api_base_url="https://api.wuji-vnext-test.svc:8443",
        identity_issuer="https://identity.wuji-vnext-test.invalid",
        identity_audience="wuji-vnext-deployment",
        tenant_id="tenant-fixture",
        project_id="project-fixture",
        task_id="task-fixture",
        allowed_origins=("http://127.0.0.1:44180",),
    )
    assert [item["kind"] for item in manifests] == [
        "ConfigMap", "ConfigMap", "Deployment", "Service"
    ]
    config_maps = {item["metadata"]["name"]: item for item in manifests if item["kind"] == "ConfigMap"}
    browser = json.loads(
        config_maps["wuji-web-config"]["data"]["config.js"]
        .removeprefix("window.__WUJI_CONFIG__ = ").rstrip(";\n")
    )
    assert browser == {
        "apiBaseUrl": "",
        "authEntrypoint": "/auth/login",
        "mode": "vnext-readonly",
        "tenantId": "tenant-fixture",
        "projectId": "project-fixture",
        "taskId": "task-fixture",
    }
    gateway = json.loads(config_maps["wuji-web-gateway-config"]["data"]["web-gateway.json"])
    assert gateway["api_base_url"] == "https://api.wuji-vnext-test.svc:8443"
    assert gateway["signing_key_file"] == "/run/wuji/web/identity.key"
    deployment = next(item for item in manifests if item["kind"] == "Deployment")
    assert deployment["spec"]["template"]["spec"]["securityContext"]["fsGroup"] == 10000
    containers = {item["name"]: item for item in deployment["spec"]["template"]["spec"]["containers"]}
    assert containers["web"]["securityContext"]["runAsGroup"] == 10000
    assert containers["gateway"]["image"] == GATEWAY_IMAGE
    assert containers["gateway"]["command"][-1] == "8090"
    volumes = {item["name"]: item for item in deployment["spec"]["template"]["spec"]["volumes"]}
    assert volumes["gateway-credentials"]["secret"]["secretName"] == "wuji-web-gateway-credentials"
    assert not any(item["kind"] == "Secret" for item in manifests)
