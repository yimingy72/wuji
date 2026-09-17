"""Pure configuration refresh checks; no Kubernetes, database or Secret reads."""

import base64
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for package in ("packages/wuji-core/src", "packages/task-runtime/src", "packages/maf-worker/src"):
    sys.path.insert(0, str(ROOT / package))
sys.path.insert(0, str(ROOT / "ops/vnext/kubernetes"))

from wuji_task_runtime.manifest import build_task_pod


_spec = importlib.util.spec_from_file_location(
    "vnext_configure", ROOT / "ops/vnext/kubernetes/configure.py"
)
configure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(configure)


OLD_AGENT = "registry.local/wuji-agent@sha256:" + "1" * 64
OLD_KALI = "registry.local/wuji-kali@sha256:" + "2" * 64
OLD_PLATFORM = "registry.local/wuji-platform@sha256:" + "3" * 64
NEW_AGENT = "registry.local/wuji-agent@sha256:" + "4" * 64
NEW_KALI = "registry.local/wuji-kali@sha256:" + "5" * 64
NEW_PLATFORM = "registry.local/wuji-platform@sha256:" + "6" * 64
TENANT = "tenant-fixture"
PROJECT = "project-fixture"
TASK = "task-fixture"
NAMESPACE = "wuji-vnext-test"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _task_config(agent=OLD_AGENT, kali=OLD_KALI):
    return {
        "tenant_id": TENANT,
        "task_id": TASK,
        "namespace": NAMESPACE,
        "runtime_attempt": 1,
        "execution_epoch": 2,
        "scope_digest": "a" * 64,
        "config_digest": "b" * 64,
        "agent_image": agent,
        "kali_image": kali,
        "agent_resources": {
            "cpu_request": "100m",
            "memory_request": "128Mi",
            "cpu_limit": "1",
            "memory_limit": "512Mi",
        },
        "kali_resources": {
            "cpu_request": "100m",
            "memory_request": "128Mi",
            "cpu_limit": "1",
            "memory_limit": "512Mi",
        },
        "tmp_size_limit": "128Mi",
        "pod_deadline_seconds": 1800,
        "expose_pod_identity": True,
        "kali_receipts_enabled": True,
    }


def _task_configmaps():
    labels = {
        "app.kubernetes.io/managed-by": "wuji-task-runtime-controller",
        "wuji.dev/task-id": TASK,
        "wuji.dev/tenant-id": TENANT,
        "wuji.dev/runtime-attempt": "1",
    }
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": TASK + "-agent-config",
                    "namespace": NAMESPACE,
                    "labels": labels,
                    "annotations": {"wuji.dev/task-id": TASK, "wuji.dev/tenant-id": TENANT},
                },
                "data": {"supervisor.json": "{}", "ca.crt": "CA", "identity.pub": "PUB"},
            },
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": TASK + "-kali-config",
                    "namespace": NAMESPACE,
                    "labels": labels,
                    "annotations": {"wuji.dev/task-id": TASK, "wuji.dev/tenant-id": TENANT},
                },
                "data": {"kali.json": "{}", "ca.crt": "CA", "identity.pub": "PUB"},
            },
        ],
    }


def _platform_manifest(runtime, platform_image=OLD_PLATFORM):
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "runtime-config", "namespace": NAMESPACE},
                "data": {
                    "deployment.json": json.dumps(runtime, sort_keys=True, separators=(",", ":")),
                    "profiles.json": "[]",
                },
            },
            *[
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": name, "namespace": NAMESPACE},
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {"name": name, "image": platform_image},
                                    *([{"name": "synthetic-model", "image": platform_image}] if name == "gates" else []),
                                ]
                            }
                        }
                    },
                }
                for name in ("runtime", "scheduler", "gates")
            ],
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "runtime-credentials", "namespace": NAMESPACE},
                "data": {"opaque": "preserve-me"},
            },
            {
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "metadata": {"name": "runtime-state", "namespace": NAMESPACE},
                "spec": {"resources": {"requests": {"storage": "1Gi"}}},
            },
        ],
    }


def test_refresh_images_preserves_binding_and_aligns_template(tmp_path):
    state = tmp_path / "state"
    bundle = state / "configuration"
    base = _task_config()
    owner = [TENANT, PROJECT, TASK]
    runtime = {
        "schema_version": "wuji.deployment.v1",
        "role": "runtime",
        "task_ids": [TASK],
        "secret_refs": {"signing-key": "/credentials/signing.key"},
        "receiver_token_file": "/credentials/receiver.token",
        "pod_runtime": {
            "task_config": dict(base),
            "receiver": {
                "receiver_id": "receiver-fixture",
                "receiver_subject": "receiver",
                "environment_ref": "pod-fixture",
                "credential_template_ref": "deployment-worker-v1",
                "model_mode": "synthetic",
            },
        },
    }
    runtime_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "runtime", "namespace": NAMESPACE},
        "spec": {
            "template": {
                "spec": {
                    "containers": [{"name": "runtime", "image": OLD_PLATFORM}],
                    "volumes": [{"name": "credentials", "secret": {"secretName": "runtime-credentials"}}],
                }
            }
        },
    }
    runtime_configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "runtime-config", "namespace": NAMESPACE},
        "data": {
            "deployment.json": json.dumps(runtime, sort_keys=True, separators=(",", ":")),
            "profiles.json": "[]",
            "identity.pub": "PUB",
            "ca.crt": "CA",
        },
    }
    _write(bundle / "task-config.json", base)
    _write(bundle / "task-config-r2.json", _task_config("registry.local/old-agent@sha256:" + "7" * 64, OLD_KALI))
    _write(bundle / "public.json", {"owner": owner, "receiver_id": "receiver-fixture", "definition_digest": base["config_digest"]})
    _write(bundle / "runtime-deployment.json", runtime)
    _write(bundle / "runtime-deployment-manifest.json", runtime_manifest)
    _write(bundle / "runtime-configmap.json", runtime_configmap)
    _write(bundle / "platform.json", _platform_manifest(runtime))
    _write(bundle / "task-configmaps.json", _task_configmaps())

    result = configure.refresh_images(
        ROOT,
        state,
        {
            "agent": {"reference": NEW_AGENT, "source_revision": "cdda7f4"},
            "kali": {"reference": NEW_KALI, "source_revision": "cdda7f4"},
            "platform": {"reference": NEW_PLATFORM, "source_revision": "cdda7f4"},
        },
    )

    assert result["task_id"] == TASK
    assert result["execution_epoch"] == 2
    assert result["runtime_attempt"] == 1
    assert result["config_digest"] == base["config_digest"]
    assert Path(result["backup"]).is_dir()
    assert json.loads((Path(result["backup"]) / "task-config.json").read_bytes()) == base

    refreshed = json.loads((bundle / "task-config.json").read_bytes())
    refreshed_r2 = json.loads((bundle / "task-config-r2.json").read_bytes())
    assert refreshed["agent_image"] == NEW_AGENT
    assert refreshed["kali_image"] == NEW_KALI
    assert configure._without_images(refreshed) == configure._without_images(refreshed_r2)
    assert refreshed["config_digest"] == base["config_digest"]
    task_runtime = configure._task_runtime_config(refreshed)
    pod = json.loads((bundle / "task-pod.json").read_bytes())
    assert pod["metadata"]["annotations"]["wuji.dev/template-digest"] == task_runtime.template_digest
    assert [item["image"] for item in pod["spec"]["containers"]] == [NEW_AGENT, NEW_KALI]
    assert pod["metadata"]["labels"]["wuji.dev/task-id"] == TASK

    deployment = json.loads((bundle / "runtime-deployment.json").read_bytes())
    # The refresh keeps the published list shape: the bootstrap Task is the only
    # entry this command owns, and its images are the ones that changed.
    refreshed_entry = configure._runtime_task_entry(deployment)
    assert deployment["pod_runtime"]["tasks"] == [refreshed_entry]
    assert refreshed_entry["task_config"]["agent_image"] == NEW_AGENT
    assert refreshed_entry["task_config"]["kali_image"] == NEW_KALI
    assert configure._task_runtime_config(refreshed_entry["task_config"]).template_digest == task_runtime.template_digest
    runtime_cm = json.loads((bundle / "runtime-configmap.json").read_bytes())
    cm_deployment = json.loads(runtime_cm["data"]["deployment.json"])
    assert configure._runtime_task_entry(cm_deployment)["task_config"] == refreshed_entry["task_config"]
    assert runtime_cm["data"]["profiles.json"] == "[]"
    assert json.loads((bundle / "runtime-deployment-manifest.json").read_bytes())["spec"]["template"]["spec"]["containers"][0]["image"] == NEW_PLATFORM
    applied = json.loads((bundle / "platform.json").read_bytes())
    applied_runtime_cm = next(item for item in applied["items"] if item["kind"] == "ConfigMap" and item["metadata"]["name"] == "runtime-config")
    applied_entry = configure._runtime_task_entry(
        json.loads(applied_runtime_cm["data"]["deployment.json"])
    )
    assert applied_entry["task_config"] == refreshed_entry["task_config"]
    for name in ("runtime", "scheduler", "gates"):
        applied_deployment = next(item for item in applied["items"] if item["kind"] == "Deployment" and item["metadata"]["name"] == name)
        assert {container["image"] for container in applied_deployment["spec"]["template"]["spec"]["containers"]} == {NEW_PLATFORM}
    assert next(item for item in applied["items"] if item["kind"] == "Secret")["data"] == {"opaque": "preserve-me"}
    assert next(item for item in applied["items"] if item["kind"] == "PersistentVolumeClaim")["spec"] == {"resources": {"requests": {"storage": "1Gi"}}}
    assert json.loads((bundle / "public.json").read_bytes())["owner"] == owner
    assert json.loads((bundle / "task-configmaps.json").read_bytes()) == _task_configmaps()
    assert build_task_pod(task_runtime)["metadata"]["annotations"]["wuji.dev/template-digest"] == task_runtime.template_digest


def _default_artifact_root():
    """The platform default the api inherits for its artifact store."""

    spec = importlib.util.spec_from_file_location(
        "vnext_deployment_common", ROOT / "ops/vnext/deployment_common.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Settings.model_fields["artifact_root"].default


def test_fresh_configuration_includes_isolated_public_api(tmp_path):
    operations_spec = importlib.util.spec_from_file_location(
        "vnext_k8s_operations_for_config", ROOT / "scripts/vnext/k8s.py"
    )
    operations = importlib.util.module_from_spec(operations_spec)
    operations_spec.loader.exec_module(operations)

    state = tmp_path / "state"
    operations.certificates(state / "tls")
    credentials = state / "credentials"
    credentials.mkdir(mode=0o700)
    (credentials / "bootstrap.password").write_text("bootstrap-fixture-password")
    bundle = configure.configure(
        ROOT,
        state,
        {
            "agent": {"reference": NEW_AGENT, "source_revision": "api-source"},
            "kali": {"reference": NEW_KALI, "source_revision": "api-source"},
            "platform": {"reference": NEW_PLATFORM, "source_revision": "api-source"},
        },
    )

    platform = json.loads((bundle / "platform.json").read_bytes())
    api_config = next(
        item for item in platform["items"]
        if item["kind"] == "ConfigMap" and item["metadata"]["name"] == "api-config"
    )
    settings = json.loads(api_config["data"]["deployment.json"])
    assert settings["role"] == "api"
    # The api serves and purges artifact bytes, so it must mount the same store
    # the runtime and gates use; a role-local root would tombstone rows while
    # the bytes survive elsewhere. It inherits the shared default root instead
    # of carrying a role-local override.
    assert "artifact_root" not in settings
    assert _default_artifact_root() == "/var/lib/wuji/platform/artifacts"

    api_secret = next(
        item for item in platform["items"]
        if item["kind"] == "Secret" and item["metadata"]["name"] == "api-credentials"
    )
    database = json.loads(base64.b64decode(api_secret["data"]["database.json"]))
    assert database["user"] == "wuji_app"
    assert {"service.token", "tls.crt", "tls.key"} <= set(api_secret["data"])

    api_deployment = next(
        item for item in platform["items"]
        if item["kind"] == "Deployment" and item["metadata"]["name"] == "api"
    )
    pod = api_deployment["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False
    assert "artifacts" in {item["name"] for item in pod["volumes"]}
    assert {
        "name": "artifacts",
        "mountPath": "/var/lib/wuji/platform/artifacts",
    } in pod["containers"][0]["volumeMounts"]
    assert next(
        item for item in platform["items"]
        if item["kind"] == "Service" and item["metadata"]["name"] == "api"
    )["spec"]["ports"] == [{"port": 8443, "targetPort": 8443, "name": "tls"}]


def test_rotating_the_task_leaves_also_republishes_the_template_secrets(tmp_path):
    """A rotated leaf has to reach the secret a new Task copies from."""

    import importlib.util as _importlib

    spec = _importlib.spec_from_file_location(
        "vnext_k8s", ROOT / "scripts/vnext/k8s.py"
    )
    k8s = _importlib.module_from_spec(spec)
    spec.loader.exec_module(k8s)

    tls = tmp_path / "tls"
    tls.mkdir()
    (tls / "task-agent.crt").write_bytes(b"rotated agent certificate")
    (tls / "task-agent.key").write_bytes(b"rotated agent key")
    (tls / "task-kali.crt").write_bytes(b"rotated kali certificate")
    (tls / "task-kali.key").write_bytes(b"rotated kali key")

    agent = k8s.task_certificate_patch(tls, "wuji-task-v-abc-agent-auth")
    assert agent["kind"] == "agent"
    import base64 as _base64

    assert _base64.b64decode(agent["patch"]["data"]["tls.crt"]) == b"rotated agent certificate"
    assert _base64.b64decode(agent["patch"]["data"]["tls.key"]) == b"rotated agent key"
    assert set(agent["patch"]["data"]) == {"tls.crt", "tls.key"}

    kali = k8s.task_certificate_patch(tls, "wuji-task-v-abc-kali-auth")
    assert kali["kind"] == "kali"
    assert _base64.b64decode(kali["patch"]["data"]["tls.crt"]) == b"rotated kali certificate"

    # An unrelated or missing secret is refused instead of silently ignored.
    for bad in ("wuji-task-v-abc-runtime-auth", "wuji-task-v-abc"):
        try:
            k8s.task_certificate_patch(tls, bad)
        except ValueError as error:
            assert "unknown Task secret" in str(error)
        else:
            raise AssertionError("an unknown Task secret must be refused")
