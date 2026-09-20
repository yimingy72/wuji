"""Offline release guard checks; no cluster, provider, model, or target access."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vnext"))
SPEC = importlib.util.spec_from_file_location(
    "first_use_release_guards", ROOT / "scripts/vnext/first_use_platform.py"
)
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)

PLATFORM_IMAGE = "127.0.0.1:55529/wuji-vnext-platform@sha256:" + "a" * 64
MODEL_IMAGE = "127.0.0.1:55529/wuji-first-use-litellm@sha256:" + "b" * 64
WEB_IMAGE = "127.0.0.1:55529/wuji-web@" + release.REUSABLE_WEB_DIGEST
BASELINE = "aeef6956028f8bf07f0319a8366f4dabed5cc1f5"


def _deployment(name, images, *, namespace=release.render.NAMESPACE, ready=True):
    labels = {**release.MANAGER_LABELS, "wuji.dev/service": name}
    generation = 4
    desired = 1
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "generation": generation,
            "labels": dict(release.MANAGER_LABELS),
        },
        "spec": {
            "replicas": desired,
            "selector": {"matchLabels": {"wuji.dev/service": name}},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [
                        {"name": role, "image": image}
                        for role, image in images.items()
                    ]
                },
            },
        },
        "status": {
            "observedGeneration": generation,
            "updatedReplicas": desired,
            "readyReplicas": desired if ready else 0,
            "availableReplicas": desired if ready else 0,
            "replicas": desired,
        },
    }


def _pod(name, images, *, ready=True):
    return {
        "metadata": {"name": name},
        "spec": {
            "containers": [
                {"name": role, "image": image}
                for role, image in images.items()
            ]
        },
        "status": {
            "containerStatuses": [
                {
                    "name": role,
                    "ready": ready,
                    "imageID": "docker-pullable://" + image,
                }
                for role, image in images.items()
            ]
        },
    }


def test_not_ready_model_gateway_cannot_be_reported_successful(monkeypatch):
    images = {"litellm": MODEL_IMAGE}
    deployment = _deployment(
        "first-use-litellm", images, namespace=release.MODEL_NAMESPACE, ready=False
    )
    reads = []

    def fake_get(kind, name, *, namespace=release.render.NAMESPACE):
        reads.append((namespace, kind, name))
        return deployment

    def fake_pods(value, namespace):
        reads.append((namespace, "pods", value["metadata"]["name"]))
        return [_pod("first-use-litellm-fixture", images, ready=False)]

    monkeypatch.setattr(release, "get", fake_get)
    monkeypatch.setattr(release, "_pod_list", fake_pods)
    with pytest.raises(release.ReleaseError) as caught:
        release.wait_for_rollouts(
            [(release.MODEL_NAMESPACE, "first-use-litellm", images)], timeout_seconds=0
        )
    assert caught.value.code == (
        "rollout_not_ready:wuji-first-use-model/first-use-litellm:ready_replicas"
    )
    assert reads[0] == (
        "wuji-first-use-model", "deployment", "first-use-litellm"
    )


def test_owner_mismatch_stops_rollout_before_any_write(monkeypatch, tmp_path):
    inventory = {
        role: {"source_revision": BASELINE, "reference": PLATFORM_IMAGE}
        for role in ("platform", "agent", "kali")
    }
    inventory_path = tmp_path / "images.json"
    inventory_path.write_text(json.dumps(inventory))
    source = {
        "identity": {"issuer": "https://identity.invalid", "audience": "deployment"},
        "owner": ["tenant", "project", "task"],
    }
    job = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": "filled-by-read",
            "namespace": release.render.NAMESPACE,
            "labels": dict(release.render.OWNER_LABEL),
        },
        "spec": {"template": {"spec": {"containers": [
            {"name": "catalog", "image": PLATFORM_IMAGE}
        ]}}},
        "status": {"succeeded": 1},
    }
    foreign_gates = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "gates-config",
            "namespace": release.render.NAMESPACE,
            "labels": {
                "app.kubernetes.io/managed-by": "foreign-owner",
                "wuji.dev/environment": "local-test",
            },
        },
        "data": {"deployment.json": json.dumps({
            "schema_version": "wuji.deployment.v1", "role": "gates"
        })},
    }
    objects = {
        ("configmap", "api-config"): {"data": {"ca.crt": "CA", "identity.pub": "PUB"}},
        ("configmap", "gates-config"): foreign_gates,
    }
    writes = []

    def fake_get(kind, name, *, namespace=release.render.NAMESPACE):
        if kind.lower() == "job":
            value = dict(job)
            value["metadata"] = {**job["metadata"], "name": name}
            return value
        return objects.get((kind.lower(), name))

    def record_write(*args, **kwargs):
        writes.append((args, kwargs))
        pytest.fail("owner preflight allowed a cluster write")

    monkeypatch.setattr(release, "get", fake_get)
    monkeypatch.setattr(release, "kube", record_write)
    monkeypatch.setattr(release, "source_config", lambda: source)
    monkeypatch.setattr(release, "assert_quiescent", lambda value: {})
    monkeypatch.setattr(release, "owner_template", lambda *args, **kwargs: {})
    monkeypatch.setattr(release, "shipped_worker_lock_digest", lambda: "c" * 64)
    monkeypatch.setattr(sys, "argv", [
        "first_use_platform.py", "rollout",
        "--mode", "mechanism_synthetic",
        "--images", str(inventory_path),
        "--web-image", WEB_IMAGE,
        "--web-source-revision", release.REUSABLE_WEB_REVISION,
        "--evidence-ref", "offline-owner-guard",
        "--execute",
    ])

    with pytest.raises(release.ReleaseError) as caught:
        release.main()
    assert caught.value.code == "platform_resource_owner:configmap/gates-config"
    assert writes == []


def test_reviewed_old_web_is_reusable_but_digest_or_source_mismatch_is_rejected():
    assert release.validate_web_source(
        "127.0.0.1:55529/wuji-web@" + release.SELECTION_WEB_DIGEST,
        release.SELECTION_WEB_REVISION, BASELINE,
    ) == "reviewed_ui_selection_fix"
    assert release.validate_web_source(
        WEB_IMAGE, release.REUSABLE_WEB_REVISION, BASELINE
    ) == "reviewed_unchanged_reuse"

    wrong_digest = "127.0.0.1:55529/wuji-web@sha256:" + "d" * 64
    with pytest.raises(release.ReleaseError, match="web_reusable_digest_mismatch"):
        release.validate_web_source(
            wrong_digest, release.REUSABLE_WEB_REVISION, BASELINE
        )
    with pytest.raises(release.ReleaseError, match="web_source_revision_mismatch"):
        release.validate_web_source(WEB_IMAGE, "e" * 40, BASELINE)


def test_new_web_config_names_preserve_unlabelled_legacy_objects():
    documents = [
        {"kind": "ConfigMap", "metadata": {"name": "wuji-web-config"}},
        {"kind": "ConfigMap", "metadata": {"name": "wuji-web-gateway-config"}},
        {"kind": "Deployment", "spec": {"template": {"spec": {"volumes": [
            {"configMap": {"name": "wuji-web-config"}},
            {"configMap": {"name": "wuji-web-gateway-config"}},
            {"configMap": {"name": "api-config"}},
        ]}}}},
    ]
    actual = release.version_web_configmaps(documents)
    assert [item["metadata"]["name"] for item in actual[:2]] == [
        "first-use-web-config-v2", "first-use-web-gateway-config-v2"]
    assert [v["configMap"]["name"] for v in actual[2]["spec"]["template"]["spec"]["volumes"]] == [
        "first-use-web-config-v2", "first-use-web-gateway-config-v2", "api-config"]
