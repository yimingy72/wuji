"""Explicit isolated first-use release actions; default is a read-only plan.

No target/model calls, no old Task rewrites, no data deletion. Secret values go
only through subprocess stdin and are not included in ordinary output/errors.
Run catalog first, inspect the Job, then rollout with the same fixed image set.
"""
import argparse
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))
from first_use_catalog import owner_template
from task_launch import shipped_worker_lock_digest
from refresh_credentials import guard_live_attempts, live_counts


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


render = load("first_use_render", "ops/vnext/kubernetes/first_use.py")
web = load("first_use_web", "ops/vnext/kubernetes/web.py")
BASE = ["kubectl", "--context", "docker-desktop"]
MODEL_NAMESPACE = "wuji-first-use-model"
MANAGER_LABELS = {
    "app.kubernetes.io/managed-by": "wuji-vnext-deployment",
    "wuji.dev/environment": "local-test",
}
CORE_CONTAINERS = {
    "api": ("api",),
    "runtime": ("runtime",),
    "scheduler": ("scheduler",),
    # The rendered core deployment retains the loopback model alongside gates.
    "gates": ("gates", "synthetic-model"),
}
REUSABLE_WEB_REVISION = "a28c887d82660c9e0e66fc563d37e785c48f10be"
# Same 5cdbd17 compiled assets; reviewed nginx Host/port and permission overlay.
REUSABLE_WEB_DIGEST = "sha256:e84b4f467ea1ce5f12c1f761e0662844fe6b8e2021be8ec98f3b25242cd02925"
WEB_SOURCE_PATHS = ("apps/web", "packages/contracts")
# Reviewed settled-cancel copy and directory synchronization Web build.
SELECTION_WEB_REVISION = "0d73f2de7162f43b34d1082f64b59bde450c39ea"
SELECTION_WEB_DIGEST = "sha256:a8b8f8f96f590cd8e9dbeca04afb3883f18f81b286816d3278ff6ec69f95268a"
FIRST_USE_WORKER_TRANSPORT_BYTES = 8_388_608


class ReleaseError(RuntimeError):
    """A bounded release failure whose code is safe for operator output."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def rollout_runtime_settings(settings):
    result = dict(settings)
    result.update(
        session_transport=True,
        max_transport_bytes=FIRST_USE_WORKER_TRANSPORT_BYTES,
    )
    return result


def kube(args, *, document=None, namespace=render.NAMESPACE):
    command = [*BASE, "--namespace", namespace, *args]
    result = subprocess.run(command, input=None if document is None else json.dumps(document),
                            capture_output=True, text=True, timeout=40, check=False)
    if result.returncode:
        # Kubernetes error bodies can echo Secret fields. Never print them.
        raise ReleaseError("cluster_operation_failed:" + args[0])
    return result.stdout


def get(kind, name, *, namespace=render.NAMESPACE):
    raw = kube(["get", kind, name, "--ignore-not-found", "-o", "json"], namespace=namespace)
    return json.loads(raw) if raw.strip() else None


def _labels(resource):
    return resource.get("metadata", {}).get("labels", {})


def _require_labels(resource, expected, code):
    labels = _labels(resource)
    if any(labels.get(key) != value for key, value in expected.items()):
        raise ReleaseError(code)


def _container_images(deployment, expected_names, code):
    if deployment.get("apiVersion") != "apps/v1" or deployment.get("kind") != "Deployment":
        raise ReleaseError(code + ":schema")
    containers = (
        deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers")
    )
    if not isinstance(containers, list):
        raise ReleaseError(code + ":containers")
    result = {}
    for container in containers:
        if not isinstance(container, dict) or not isinstance(container.get("name"), str):
            raise ReleaseError(code + ":containers")
        if container["name"] in result or not isinstance(container.get("image"), str):
            raise ReleaseError(code + ":containers")
        result[container["name"]] = container["image"]
    if set(result) != set(expected_names):
        raise ReleaseError(code + ":containers")
    return result


def _require_platform_object(resource, kind, name):
    if resource is None:
        raise ReleaseError("platform_resource_missing:" + kind + "/" + name)
    if resource.get("kind", "").lower() != kind.lower():
        raise ReleaseError("platform_resource_schema:" + kind + "/" + name)
    if resource.get("metadata", {}).get("namespace") != render.NAMESPACE:
        raise ReleaseError("platform_resource_namespace:" + kind + "/" + name)
    _require_labels(resource, MANAGER_LABELS, "platform_resource_owner:" + kind + "/" + name)


def _require_existing_document(current, desired):
    """Check an apply target against the labels and shape its renderer owns."""

    kind = desired["kind"]
    name = desired["metadata"]["name"]
    code = "release_resource_conflict:" + kind + "/" + name
    if current.get("apiVersion") != desired.get("apiVersion") or current.get("kind") != kind:
        raise ReleaseError(code + ":schema")
    if current.get("metadata", {}).get("namespace") != render.NAMESPACE:
        raise ReleaseError(code + ":namespace")
    _require_labels(current, desired["metadata"].get("labels", {}), code + ":owner")
    if kind == "Deployment":
        desired_names = [
            item["name"]
            for item in desired["spec"]["template"]["spec"]["containers"]
        ]
        _container_images(current, desired_names, code)


def validate_web_source(web_image, web_source_revision, release_revision):
    """Bind the Web digest to its source, allowing the reviewed unchanged build."""

    render.image_ref(web_image)
    if web_source_revision == release_revision:
        return "release_revision"
    if web_source_revision == SELECTION_WEB_REVISION:
        if web_image.rsplit("@", 1)[-1] != SELECTION_WEB_DIGEST:
            raise ReleaseError("web_reusable_digest_mismatch")
        difference = subprocess.run(
            ["git", "diff", "--name-only", release_revision, web_source_revision, "--", *WEB_SOURCE_PATHS],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        if difference.returncode or not set(difference.stdout.splitlines()) <= {
            "apps/web/src/features/first-use/FirstUseWorkbench.tsx",
            "apps/web/src/features/first-use/workbenchState.ts",
            "packages/contracts/openapi-v2.yaml",
            "packages/contracts/src/v2/generated.ts",
        }:
            raise ReleaseError("web_source_changed_since_reviewed_selection_fix")
        return "reviewed_ui_selection_fix"
    if web_source_revision != REUSABLE_WEB_REVISION:
        raise ReleaseError("web_source_revision_mismatch")
    if web_image.rsplit("@", 1)[-1] != REUSABLE_WEB_DIGEST:
        raise ReleaseError("web_reusable_digest_mismatch")
    result = subprocess.run(
        ["git", "diff", "--quiet", web_source_revision, release_revision, "--", *WEB_SOURCE_PATHS],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    if result.returncode == 1:
        raise ReleaseError("web_source_changed_since_reusable_revision")
    if result.returncode != 0:
        raise ReleaseError("web_source_comparison_failed")
    return "reviewed_unchanged_reuse"


def _preflight_catalog(secret_name, secret_data, documents):
    current = get("secret", secret_name)
    encoded = {key: base64.b64encode(value.encode()).decode() for key, value in secret_data.items()}
    if current:
        _require_labels(current, render.OWNER_LABEL, "private_secret_owner_conflict")
        if current.get("type") != "Opaque" or current.get("data") != encoded:
            raise ReleaseError("private_secret_content_conflict")
    for document in documents:
        existing = get(document["kind"], document["metadata"]["name"])
        if existing:
            _require_existing_document(existing, document)


def _preflight_rollout(*, job_name, platform_image, documents):
    """Read every existing rollout target before the first write."""

    job = get("job", job_name)
    if not job or job.get("status", {}).get("succeeded") != 1:
        raise ReleaseError("catalog_job_not_successful")
    _require_labels(job, render.OWNER_LABEL, "catalog_job_owner_conflict")
    pod_containers = job.get("spec", {}).get("template", {}).get("spec", {}).get("containers")
    if (
        job.get("apiVersion") != "batch/v1"
        or job.get("kind") != "Job"
        or not isinstance(pod_containers, list)
        or [(item.get("name"), item.get("image")) for item in pod_containers]
        != [("catalog", platform_image)]
    ):
        raise ReleaseError("catalog_job_invalid")

    gates_config = get("configmap", "gates-config")
    _require_platform_object(gates_config, "configmap", "gates-config")
    data = gates_config.get("data")
    try:
        gate_settings = json.loads(data["deployment.json"])
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ReleaseError("gates_config_schema_invalid") from None
    if (
        not isinstance(gate_settings, dict)
        or gate_settings.get("schema_version") != "wuji.deployment.v1"
        or gate_settings.get("role") != "gates"
    ):
        raise ReleaseError("gates_config_schema_invalid")

    runtime_config = get("configmap", "runtime-config")
    _require_platform_object(runtime_config, "configmap", "runtime-config")
    runtime_data = runtime_config.get("data")
    try:
        runtime_settings = json.loads(runtime_data["deployment.json"])
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ReleaseError("runtime_config_schema_invalid") from None
    if (
        not isinstance(runtime_settings, dict)
        or runtime_settings.get("schema_version") != "wuji.deployment.v1"
        or runtime_settings.get("role") != "runtime"
    ):
        raise ReleaseError("runtime_config_schema_invalid")

    deployments = {}
    for name, roles in CORE_CONTAINERS.items():
        deployment = get("deployment", name)
        _require_platform_object(deployment, "deployment", name)
        _container_images(deployment, roles, "core_deployment_invalid:" + name)
        deployments[name] = deployment

    credentials = get("secret", "wuji-web-gateway-credentials")
    _require_platform_object(credentials, "secret", "wuji-web-gateway-credentials")
    if credentials.get("type") != "Opaque" or not isinstance(credentials.get("data"), dict):
        raise ReleaseError("web_credentials_schema_invalid")
    if not {"identity.key", "session.key"}.issubset(credentials["data"]):
        raise ReleaseError("web_credentials_schema_invalid")

    seen = set()
    for document in documents:
        identity = (document["kind"], document["metadata"]["name"])
        if identity in seen:
            raise ReleaseError("duplicate_release_resource:" + "/".join(identity))
        seen.add(identity)
        existing = get(*identity)
        if existing:
            _require_existing_document(existing, document)
    return {
        "gate_settings": gate_settings,
        "runtime_settings": runtime_settings,
        "deployments": deployments,
        "credentials": credentials,
    }


def _pod_list(deployment, namespace):
    selector = deployment.get("spec", {}).get("selector", {}).get("matchLabels")
    if not isinstance(selector, dict) or not selector:
        raise ReleaseError("rollout_selector_invalid:" + deployment["metadata"]["name"])
    value = ",".join(key + "=" + selector[key] for key in sorted(selector))
    raw = kube(["get", "pods", "-l", value, "-o", "json"], namespace=namespace)
    result = json.loads(raw)
    if not isinstance(result.get("items"), list):
        raise ReleaseError("rollout_pod_list_invalid:" + deployment["metadata"]["name"])
    return [item for item in result["items"] if not item.get("metadata", {}).get("deletionTimestamp")]


def _rollout_observation(deployment, pods, expected_images):
    """Return a short pending reason, or None only for exact ready image state."""

    name = deployment.get("metadata", {}).get("name", "unknown")
    actual_images = _container_images(deployment, tuple(expected_images), "rollout_invalid:" + name)
    if actual_images != expected_images:
        raise ReleaseError("rollout_deployment_image_mismatch:" + name)
    desired = deployment.get("spec", {}).get("replicas")
    generation = deployment.get("metadata", {}).get("generation")
    if not isinstance(desired, int) or desired < 1 or not isinstance(generation, int):
        raise ReleaseError("rollout_invalid:" + name + ":replicas")
    status = deployment.get("status", {})
    checks = (
        (status.get("observedGeneration", 0) >= generation, "observed_generation"),
        (status.get("updatedReplicas", 0) == desired, "updated_replicas"),
        (status.get("readyReplicas", 0) == desired, "ready_replicas"),
        (status.get("availableReplicas", 0) == desired, "available_replicas"),
        (status.get("replicas", 0) == desired, "replicas"),
    )
    for passed, reason in checks:
        if not passed:
            return reason
    if len(pods) != desired:
        return "pod_count"
    for pod in pods:
        containers = pod.get("spec", {}).get("containers")
        if not isinstance(containers, list):
            return "pod_containers"
        pod_images = {item.get("name"): item.get("image") for item in containers}
        if pod_images != expected_images:
            raise ReleaseError("rollout_pod_image_mismatch:" + name)
        statuses = pod.get("status", {}).get("containerStatuses")
        if not isinstance(statuses, list):
            return "pod_status"
        by_name = {item.get("name"): item for item in statuses}
        if set(by_name) != set(expected_images) or any(not by_name[key].get("ready") for key in by_name):
            return "pod_ready"
        for role, reference in expected_images.items():
            digest = reference.rsplit("@", 1)[-1]
            if not str(by_name[role].get("imageID", "")).endswith("@" + digest):
                raise ReleaseError("rollout_pod_digest_mismatch:" + name + "/" + role)
    return None


def wait_for_rollouts(workloads, *, timeout_seconds=300):
    """Wait for all release Deployments against one bounded shared deadline."""

    deadline = time.monotonic() + timeout_seconds
    while True:
        pending = []
        for namespace, name, expected_images in workloads:
            deployment = get("deployment", name, namespace=namespace)
            if deployment is None:
                pending.append(namespace + "/" + name + ":missing")
                continue
            reason = _rollout_observation(
                deployment, _pod_list(deployment, namespace), expected_images
            )
            if reason:
                pending.append(namespace + "/" + name + ":" + reason)
        if not pending:
            return [namespace + "/" + name for namespace, name, _ in workloads]
        if time.monotonic() >= deadline:
            raise ReleaseError("rollout_not_ready:" + ",".join(pending))
        time.sleep(2)


def private_secret(name, data):
    current = get("secret", name)
    encoded = {key: base64.b64encode(value.encode()).decode() for key, value in data.items()}
    if current:
        if current["metadata"].get("labels", {}).get("wuji.dev/first-use-owner") != "first-use-release-v1":
            raise ReleaseError("private_secret_owner_conflict")
        if current.get("data") != encoded:
            raise ReleaseError("private_secret_content_conflict")
        return "reused"
    document = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque", "metadata": render.metadata(name), "data": encoded}
    kube(["create", "-f", "-"], document=document)
    return "created"


def apply_owned(document):
    name, kind = document["metadata"]["name"], document["kind"]
    current = get(kind, name)
    if current and current["metadata"].get("labels", {}).get("wuji.dev/first-use-owner") != "first-use-release-v1":
        raise ReleaseError("resource_owner_conflict:" + name)
    # These contain public code/config only; never call this with a Secret.
    if kind == "Secret":
        raise ValueError("Secrets must use the private stdin create path")
    kube(["apply", "-f", "-"], document=document)


def source_config():
    raw = get("secret", "e08-r7-input")
    if raw is None:
        raise ReleaseError("trusted_template_missing")
    config = json.loads(base64.b64decode(raw["data"]["config.json"]))
    if config["database"]["dbname"] != "wuji_vnext_ui_20260915":
        raise ReleaseError("isolated_database_binding_changed")
    return config


def assert_quiescent(config):
    counts = live_counts("docker-desktop", render.NAMESPACE, {
        "database": config["database"], "migration_password": config["roles"]["wuji_migration"],
    })
    guard_live_attempts(counts)
    pods = json.loads(kube(["get", "pods", "-l", "app.kubernetes.io/managed-by=wuji-task-runtime-controller", "-o", "json"]))
    if any(item.get("status", {}).get("phase") == "Running" for item in pods["items"]):
        raise ReleaseError("running_task_pod_requires_reconciliation")
    return counts


def _model_gateway_expectation():
    """Read the independently owned provider gateway without mutating it."""

    deployment = get("deployment", "first-use-litellm", namespace=MODEL_NAMESPACE)
    if deployment is None:
        raise ReleaseError("model_gateway_missing:" + MODEL_NAMESPACE + "/first-use-litellm")
    images = _container_images(
        deployment, ("litellm",), "model_gateway_invalid:first-use-litellm"
    )
    try:
        render.image_ref(images["litellm"])
    except ValueError:
        raise ReleaseError("model_gateway_image_not_immutable") from None
    return MODEL_NAMESPACE, "first-use-litellm", images


def version_web_configmaps(documents):
    """Keep legacy unlabelled config objects untouched during the release."""
    names = {"wuji-web-config": "first-use-web-config-v2",
             "wuji-web-gateway-config": "first-use-web-gateway-config-v2"}
    seen = set()
    for document in documents:
        if document["kind"] == "ConfigMap" and document["metadata"]["name"] in names:
            old = document["metadata"]["name"]
            seen.add(old)
            document["metadata"]["name"] = names[old]
        if document["kind"] == "Deployment":
            for volume in document["spec"]["template"]["spec"].get("volumes", []):
                reference = volume.get("configMap", {})
                if reference.get("name") in names:
                    reference["name"] = names[reference["name"]]
    if seen != set(names):
        raise ReleaseError("web_config_renderer_changed")
    return documents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["catalog", "rollout"])
    parser.add_argument("--mode", choices=["mechanism_synthetic", "real_model"], required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--web-image")
    parser.add_argument("--web-source-revision",
                        help="source revision recorded by the reviewed Web image inventory")
    parser.add_argument("--evidence-ref", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    inventory = json.loads(args.images.read_bytes())
    revisions = {inventory[role]["source_revision"] for role in ("platform", "agent", "kali")}
    if len(revisions) != 1:
        raise ValueError("image source revisions disagree")
    revision = revisions.pop()
    images = {role: render.image_ref(inventory[role]["reference"]) for role in ("platform", "agent", "kali")}
    web_provenance = None
    if args.action == "rollout":
        if not args.web_image or not args.web_source_revision:
            raise ValueError("fixed web image and source revision required for release rollout")
        web_provenance = validate_web_source(
            args.web_image, args.web_source_revision, revision
        )
    source = source_config()
    counts = assert_quiescent(source)
    config = owner_template(source, mode=args.mode, lock_digest=shipped_worker_lock_digest())
    public = get("configmap", "api-config")["data"]
    suffix = render.suffix_for(args.mode)
    launch = render.launch_manifests(images=images, mode=args.mode, source_revision=revision,
        evidence_ref=args.evidence_ref, public_data=public)
    catalog_program = (ROOT / "ops/vnext/first_use_catalog.py").read_text()
    catalog_program_digest = sha256(catalog_program.encode()).hexdigest()
    job_name = (
        "first-use-catalog-" + suffix + "-" + revision[:8]
        + "-" + catalog_program_digest[:8]
    )
    catalog = render.catalog_job(platform_image=images["platform"], mode=args.mode, job_name=job_name,
        public_data=public, program=catalog_program)
    fixture = render.fixture_manifests(platform_image=images["platform"],
        program=(ROOT / "tests/first_use/f1_f2_fixture.py").read_text())
    report = {"action": args.action, "mode": args.mode, "execute": args.execute,
              "image_source_revision": revision, "live_counts": counts, "catalog_job": job_name,
              "catalog_program_sha256": catalog_program_digest}
    if args.action == "catalog":
        report["catalog_state"] = "submission_planned"
    if web_provenance:
        report.update(web_source_revision=args.web_source_revision,
                      web_provenance=web_provenance)
    if not args.execute:
        print(json.dumps(report, sort_keys=True))
        return
    if args.action == "catalog":
        owner_name = render.owner_secret_name(args.mode)
        owner_data = {"config.json": json.dumps(config, sort_keys=True)}
        _preflight_catalog(owner_name, owner_data, catalog)
        report["owner_secret"] = private_secret(owner_name, owner_data)
        for document in catalog:
            apply_owned(document)
        # Applying the Job submits it. Only a later rollout that observes
        # status.succeeded=1 may treat the catalog operation as complete.
        report["catalog_state"] = "submitted_not_completed"
    else:
        rbac = render.rbac_manifests()
        web_documents = web.build_web_manifests(args.web_image, auth_entrypoint="/auth/login", gateway_image=images["platform"],
            gateway_api_base_url="https://api.wuji-vnext-test.svc:8443", identity_issuer=source["identity"]["issuer"],
            identity_audience=source["identity"]["audience"], tenant_id=source["owner"][0], project_id=source["owner"][1],
            display_name="本地测试操作者", allowed_origins=("http://localhost:44180", "http://127.0.0.1:44180"))
        web_documents = version_web_configmaps(web_documents)
        documents = [*rbac, *web_documents, *launch, *fixture]
        preflight = _preflight_rollout(
            job_name=job_name, platform_image=images["platform"], documents=documents
        )
        model_gateway = _model_gateway_expectation() if args.mode == "real_model" else None

        # Explicit release rollout only. Future Task starts update trusted
        # bindings in place, never use this operator command.
        for document in rbac:
            apply_owned(document)
        runtime_settings = rollout_runtime_settings(preflight["runtime_settings"])
        kube(["patch", "configmap", "runtime-config", "--type", "merge", "--patch-file", "/dev/stdin"],
             document={"data": {"deployment.json": json.dumps(runtime_settings, sort_keys=True)}})
        gate_settings = dict(preflight["gate_settings"])
        if args.mode == "real_model":
            gate_settings.update(task_model_key_ref="first-use-task-model-key", task_model_keys_secret="task-model-keys")
        kube(["patch", "configmap", "gates-config", "--type", "merge", "--patch-file", "/dev/stdin"],
             document={"data": {"deployment.json": json.dumps(gate_settings, sort_keys=True)}})
        kube(["patch", "deployment", "gates", "--type", "merge", "--patch-file", "/dev/stdin"],
             document={"spec": {"template": {"spec": {"serviceAccountName": "first-use-gates", "automountServiceAccountToken": True}}}})
        for name, roles in CORE_CONTAINERS.items():
            updates = [role + "=" + images["platform"] for role in roles]
            kube(["set", "image", "deployment/" + name, *updates])
            kube(["patch", "deployment", name, "--type", "merge", "--patch-file", "/dev/stdin"],
                 document={"spec": {"template": {"metadata": {"annotations": {
                     "wuji.dev/release-revision": revision,
                 }}}}})
        credentials = preflight["credentials"]
        if "access.token" not in credentials["data"]:
            kube(["patch", "secret", "wuji-web-gateway-credentials", "--type", "merge", "--patch-file", "/dev/stdin"],
                 document={"data": {"access.token": base64.b64encode(secrets.token_urlsafe(32).encode()).decode()}})
        for document in web_documents:
            kube(["apply", "-f", "-"], document=document)
        for document in launch:
            apply_owned(document)
        for document in fixture:
            apply_owned(document)
        workloads = [
            (render.NAMESPACE, name, {role: images["platform"] for role in roles})
            for name, roles in CORE_CONTAINERS.items()
        ]
        for document in [*web_documents, *launch, *fixture]:
            if document["kind"] != "Deployment":
                continue
            expected = {
                item["name"]: item["image"]
                for item in document["spec"]["template"]["spec"]["containers"]
            }
            workloads.append((render.NAMESPACE, document["metadata"]["name"], expected))
        if model_gateway:
            workloads.append(model_gateway)
        report["ready_deployments"] = wait_for_rollouts(workloads)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # No raw subprocess/SQL/config exception text in ordinary logs.
        code = error.code if isinstance(error, ReleaseError) else type(error).__name__
        print(json.dumps({"event": "first_use_release_failed", "error": code}))
        raise SystemExit(1) from None
