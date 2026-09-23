"""The empty Core CTF renderer is complete without touching a cluster."""

import base64
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from cryptography import x509


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "wuji_core_ctf_platform", ROOT / "scripts/vnext/core_ctf_platform.py"
)
platform = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = platform
SPEC.loader.exec_module(platform)


def _items(path):
    return json.loads(path.read_bytes())["items"]


def _named(items, kind, name):
    return next(
        item for item in items
        if item["kind"] == kind and item["metadata"]["name"] == name
    )


def test_renderer_builds_an_independent_empty_arm64_platform(tmp_path, monkeypatch):
    password_cli = platform._load(
        "core_ctf_password_cli", "scripts/vnext/set_web_password.py"
    )
    credential = tmp_path / "password.json"
    password_cli.write_credential(
        credential, password_cli.credential_document("operator", "renderer-fixture-only")
    )
    monkeypatch.setattr(platform, "ROOT", tmp_path)
    digest = "a" * 64
    images = {
        role: {
            "reference": f"registry.invalid/wuji-{role}@sha256:{digest}",
            "source_revision": "a" * 40,
        }
        for role in platform.ROLES
    }

    output = platform.render(
        tmp_path / "work/core-platform",
        images,
        namespace="core-fixture",
        architecture="arm64",
        password_credential=credential,
        web_port=44181,
        explore_limit=4,
        pool_capacity=5,
    )

    public = json.loads((output / "public.json").read_bytes())
    image_manifest = json.loads((output / "images.json").read_bytes())
    assert image_manifest["source_revision"] == "a" * 40
    assert image_manifest["image_source_revisions"] == {
        role: "a" * 40 for role in platform.BUSINESS_ROLES
    }
    assert public["task_count"] == 0
    assert public["web_url"] == "http://127.0.0.1:44181/"
    assert public["apply_order"] == [
        "foundation.json", "bootstrap-job.json", "catalog-job.json", "platform.json"
    ]

    foundation = _items(output / "foundation.json")
    assert _named(foundation, "Namespace", "core-fixture")["metadata"]["name"] == "core-fixture"
    postgres = _named(foundation, "Deployment", "postgres")
    assert postgres["spec"]["template"]["spec"]["nodeSelector"] == {
        "kubernetes.io/arch": "arm64"
    }
    postgres_tls = _named(foundation, "Secret", "postgres-tls")
    certificate = x509.load_pem_x509_certificate(
        base64.b64decode(postgres_tls["data"]["tls.crt"])
    )
    sans = certificate.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName)
    assert "postgres.core-fixture.svc" in sans

    for filename in ("bootstrap-job.json", "catalog-job.json"):
        pod = _items(output / filename)[0]["spec"]["template"]["spec"]
        assert pod["nodeSelector"] == {"kubernetes.io/arch": "arm64"}
        assert pod["automountServiceAccountToken"] is False

    objects = _items(output / "platform.json")
    runtime_config = _named(objects, "ConfigMap", "runtime-config")
    runtime = json.loads(runtime_config["data"]["deployment.json"])
    assert runtime["task_ids"] == []
    assert runtime["pod_runtime"]["tasks"] == []
    assert runtime_config["data"]["profiles.json"] == "[]"
    assert runtime["worker_lock_digest"] == platform.shipped_worker_lock_digest()
    assert runtime["max_transport_bytes"] == 8_388_608
    gates = json.loads(
        _named(objects, "ConfigMap", "gates-config")["data"]["deployment.json"]
    )
    assert gates["executors"] == []
    for role in ("runtime", "api", "scheduler", "gates"):
        settings = json.loads(
            _named(objects, "ConfigMap", role + "-config")["data"]["deployment.json"]
        )
        assert settings["artifact_max_bytes"] == 67_108_864
        deployment = _named(objects, "Deployment", role)
        assert deployment["metadata"]["labels"] == platform.LABELS
        assert deployment["spec"]["template"]["spec"]["nodeSelector"] == {
            "kubernetes.io/arch": "arm64"
        }
    assert "max_transport_bytes" not in json.loads(
        _named(objects, "ConfigMap", "api-config")["data"]["deployment.json"]
    )
    assert base64.b64decode(
        _named(objects, "Secret", "runtime-credentials")["data"]["encryption.key"]
    ) == base64.b64decode(
        _named(objects, "Secret", "scheduler-credentials")["data"]["encryption.key"]
    )
    assert {
        container["name"]
        for container in _named(objects, "Deployment", "gates")["spec"]["template"]["spec"]["containers"]
    } == {"gates", "synthetic-model"}
    assert _named(objects, "Deployment", "core-target")["spec"]["template"]["spec"][
        "nodeSelector"
    ] == {"kubernetes.io/arch": "arm64"}

    launch = _named(objects, "Deployment", "core-launch")
    launch_settings = json.loads(
        _named(objects, "ConfigMap", "core-launch-config")["data"]["launch.json"]
    )
    assert launch_settings["capture_ca_cert_file"] == (
        runtime["pod_runtime"]["capture_client"]["ca_file"]
    )
    mounts = {
        item["name"]
        for item in launch["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
    }
    assert {
        "owner", "deployment", "agent-auth", "gates-auth", "capture-ca",
        "capture-runtime",
    } <= mounts
    launch_credentials = _named(objects, "Secret", "core-launch-credentials")
    assert set(launch_credentials["data"]) == {
        "service.token", "signing.key", "receiver.token"
    }
    assert "capture-ca" not in {
        item["name"]
        for role in ("runtime", "api", "scheduler", "gates")
        for item in _named(objects, "Deployment", role)["spec"]["template"]["spec"]["volumes"]
    }
    assert all(item["metadata"]["namespace"] == "core-fixture" for item in objects)
    web = _named(objects, "Deployment", "core-web")["spec"]["template"]["spec"]
    assert web["nodeSelector"] == {"kubernetes.io/arch": "arm64"}
    assert {item["name"] for item in web["containers"]} == {"web", "gateway"}
    assert _named(objects, "Service", "core-web")["spec"]["ports"][0]["port"] == 44181
    _named(objects, "PersistentVolumeClaim", "core-web-sessions")
    settings = platform.gateway.GatewaySettings.model_validate(json.loads(
        _named(objects, "ConfigMap", "core-web-gateway-config")["data"]["web-gateway.json"]
    ))
    assert settings.mode == "local_password"
    assert settings.api_base_url == "https://api.core-fixture.svc:8443"
    assert settings.project_id == public["project_id"]
    assert settings.session_db_file == "/var/lib/wuji/web/sessions.sqlite3"
    assert settings.secure_cookie is False
    credential_data = _named(objects, "Secret", "core-web-credentials")["data"]
    assert base64.b64decode(credential_data["password.json"]) == credential.read_bytes()
    assert set(credential_data) == {"identity.key", "session.key", "password.json"}


def test_role_image_sources_allow_mixed_sha_and_reject_missing_or_conflicting_map(tmp_path):
    runner = platform._load("core_ctf_run_config_check", "tests/vnext/run_core_ctf.py")
    sources = {
        role: format(index + 1, "x") * 40
        for index, role in enumerate(platform.BUSINESS_ROLES)
    }
    inventory = {
        role: {
            "reference": f"registry.invalid/{role}@sha256:{'a' * 64}",
            "source_revision": sources[role],
        }
        for role in platform.BUSINESS_ROLES
    }
    inventory["postgres"] = {"reference": f"registry.invalid/postgres@sha256:{'b' * 64}"}
    assert platform._image_source_revisions(inventory) == sources
    with pytest.raises(ValueError, match="source SHA"):
        platform._image_source_revisions({**inventory, "capture": inventory["capture"]["reference"]})

    directory = tmp_path / "configuration"
    directory.mkdir()
    (directory / "public.json").write_text(json.dumps({
        "mode": "mechanism_synthetic", "task_count": 0,
        "project_id": "project", "web_url": "http://127.0.0.1:44181/",
        "start_url": "http://target.invalid/answer.json",
    }))
    manifest = {
        "images": {role: item["reference"] for role, item in inventory.items()},
        "source_revision": sources["platform"],
        "image_source_revisions": sources,
    }
    path = directory / "images.json"
    config = {"configuration_directory": directory, "expected_source_revision": sources["platform"]}
    path.write_text(json.dumps(manifest))
    assert runner.prepared_configuration(config)[1]["image_source_revisions"] == sources
    path.write_text(json.dumps({key: value for key, value in manifest.items() if key != "image_source_revisions"}))
    assert runner.prepared_configuration(config)[1]["image_source_revisions"] == {
        role: sources["platform"] for role in platform.BUSINESS_ROLES
    }
    for invalid in (
        {**sources, "platform": "f" * 40},
        {role: source for role, source in sources.items() if role != "capture"},
    ):
        path.write_text(json.dumps({**manifest, "image_source_revisions": invalid}))
        with pytest.raises(ValueError, match="source revisions are inconsistent"):
            runner.prepared_configuration(config)
