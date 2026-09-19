"""Explicit isolated first-use release actions; default is a read-only plan.

No target/model calls, no old Task rewrites, no data deletion. Secret values go
only through subprocess stdin and are not included in ordinary output/errors.
Run catalog first, inspect the Job, then rollout with the same fixed image set.
"""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys

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
BASE = ["kubectl", "--context", "docker-desktop", "--namespace", render.NAMESPACE]


def kube(args, *, document=None):
    result = subprocess.run([*BASE, *args], input=None if document is None else json.dumps(document),
                            capture_output=True, text=True, timeout=40, check=False)
    if result.returncode:
        # Kubernetes error bodies can echo Secret fields. Never print them.
        raise RuntimeError("cluster_operation_failed:" + args[0])
    return result.stdout


def get(kind, name):
    raw = kube(["get", kind, name, "--ignore-not-found", "-o", "json"])
    return json.loads(raw) if raw.strip() else None


def private_secret(name, data):
    current = get("secret", name)
    encoded = {key: base64.b64encode(value.encode()).decode() for key, value in data.items()}
    if current:
        if current["metadata"].get("labels", {}).get("wuji.dev/first-use-owner") != "first-use-release-v1":
            raise RuntimeError("private_secret_owner_conflict")
        if current.get("data") != encoded:
            raise RuntimeError("private_secret_content_conflict")
        return "reused"
    document = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque", "metadata": render.metadata(name), "data": encoded}
    kube(["create", "-f", "-"], document=document)
    return "created"


def apply_owned(document):
    name, kind = document["metadata"]["name"], document["kind"]
    current = get(kind, name)
    if current and current["metadata"].get("labels", {}).get("wuji.dev/first-use-owner") != "first-use-release-v1":
        raise RuntimeError("resource_owner_conflict:" + name)
    # These contain public code/config only; never call this with a Secret.
    if kind == "Secret":
        raise ValueError("Secrets must use the private stdin create path")
    kube(["apply", "-f", "-"], document=document)


def source_config():
    raw = get("secret", "e08-r7-input")
    if raw is None:
        raise RuntimeError("trusted_template_missing")
    config = json.loads(base64.b64decode(raw["data"]["config.json"]))
    if config["database"]["dbname"] != "wuji_vnext_ui_20260915":
        raise RuntimeError("isolated_database_binding_changed")
    return config


def assert_quiescent(config):
    counts = live_counts("docker-desktop", render.NAMESPACE, {
        "database": config["database"], "migration_password": config["roles"]["wuji_migration"],
    })
    guard_live_attempts(counts)
    pods = json.loads(kube(["get", "pods", "-l", "app.kubernetes.io/managed-by=wuji-task-runtime-controller", "-o", "json"]))
    if any(item.get("status", {}).get("phase") == "Running" for item in pods["items"]):
        raise RuntimeError("running_task_pod_requires_reconciliation")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["catalog", "rollout"])
    parser.add_argument("--mode", choices=["mechanism_synthetic", "real_model"], required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--web-image")
    parser.add_argument("--evidence-ref", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    inventory = json.loads(args.images.read_bytes())
    revisions = {inventory[role]["source_revision"] for role in ("platform", "agent", "kali")}
    if len(revisions) != 1:
        raise ValueError("image source revisions disagree")
    revision = revisions.pop()
    images = {role: render.image_ref(inventory[role]["reference"]) for role in ("platform", "agent", "kali")}
    source = source_config()
    counts = assert_quiescent(source)
    config = owner_template(source, mode=args.mode, lock_digest=shipped_worker_lock_digest())
    public = get("configmap", "api-config")["data"]
    suffix = render.suffix_for(args.mode)
    launch = render.launch_manifests(images=images, mode=args.mode, source_revision=revision,
        evidence_ref=args.evidence_ref, public_data=public)
    job_name = "first-use-catalog-" + suffix + "-" + revision[:10]
    catalog = render.catalog_job(platform_image=images["platform"], mode=args.mode, job_name=job_name,
        public_data=public, program=(ROOT / "ops/vnext/first_use_catalog.py").read_text())
    report = {"action": args.action, "mode": args.mode, "execute": args.execute,
              "source_revision": revision, "live_counts": counts, "catalog_job": job_name}
    if not args.execute:
        print(json.dumps(report, sort_keys=True))
        return
    if args.action == "catalog":
        report["owner_secret"] = private_secret(f"first-use-{suffix}-owner", {"config.json": json.dumps(config, sort_keys=True)})
        for document in catalog:
            apply_owned(document)
    else:
        if not args.web_image:
            raise ValueError("fixed web image required for release rollout")
        render.image_ref(args.web_image)
        job = get("job", job_name)
        if not job or job.get("status", {}).get("succeeded") != 1:
            raise RuntimeError("catalog_job_not_successful")
        # Explicit release rollout only. Future Task starts update trusted
        # bindings in place, never use this operator command.
        for document in render.rbac_manifests():
            apply_owned(document)
        gate_config = get("configmap", "gates-config")
        gate_settings = json.loads(gate_config["data"]["deployment.json"])
        if args.mode == "real_model":
            gate_settings.update(task_model_key_ref="first-use-task-model-key", task_model_keys_secret="task-model-keys")
        kube(["patch", "configmap", "gates-config", "--type", "merge", "--patch-file", "/dev/stdin"],
             document={"data": {"deployment.json": json.dumps(gate_settings, sort_keys=True)}})
        kube(["patch", "deployment", "gates", "--type", "merge", "--patch-file", "/dev/stdin"],
             document={"spec": {"template": {"spec": {"serviceAccountName": "first-use-gates", "automountServiceAccountToken": True}}}})
        for name in ("api", "runtime", "scheduler", "gates"):
            deployment = get("deployment", name)
            updates = [container["name"] + "=" + images["platform"] for container in deployment["spec"]["template"]["spec"]["containers"]]
            kube(["set", "image", "deployment/" + name, *updates])
        credentials = get("secret", "wuji-web-gateway-credentials")
        if "access.token" not in credentials["data"]:
            kube(["patch", "secret", "wuji-web-gateway-credentials", "--type", "merge", "--patch-file", "/dev/stdin"],
                 document={"data": {"access.token": base64.b64encode(secrets.token_urlsafe(32).encode()).decode()}})
        web_documents = web.build_web_manifests(args.web_image, auth_entrypoint="/auth/login", gateway_image=images["platform"],
            gateway_api_base_url="https://api.wuji-vnext-test.svc:8443", identity_issuer=source["identity"]["issuer"],
            identity_audience=source["identity"]["audience"], tenant_id=source["owner"][0], project_id=source["owner"][1],
            display_name="本地测试操作者", allowed_origins=("http://localhost:44180", "http://127.0.0.1:44180"))
        for document in web_documents:
            existing = get(document["kind"], document["metadata"]["name"])
            if existing and existing["metadata"].get("labels", {}).get("app.kubernetes.io/managed-by") != "wuji-vnext-deployment":
                raise RuntimeError("web_resource_owner_conflict")
            kube(["apply", "-f", "-"], document=document)
        for document in launch:
            apply_owned(document)
        for document in render.fixture_manifests(platform_image=images["platform"],
                program=(ROOT / "tests/first_use/f1_f2_fixture.py").read_text()):
            apply_owned(document)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # No raw subprocess/SQL/config exception text in ordinary logs.
        print(json.dumps({"event": "first_use_release_failed", "error": type(error).__name__}))
        raise SystemExit(1) from None
