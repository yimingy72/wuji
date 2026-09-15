"""Bounded docker-desktop deployment operations for the isolated vNext namespace."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from ipaddress import ip_address
import os
import re
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = "docker-desktop"
NAMESPACE = "wuji-vnext-test"
MANAGER = "wuji-vnext-deployment"
LABELS = {"app.kubernetes.io/managed-by": MANAGER, "wuji.dev/environment": "local-test"}
STATE = ROOT / "work/vnext/k8s"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        raise FileExistsError(f"refusing to replace existing deployment material: {path.name}")
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def run(command, raw, name, *, input_bytes=None, missing_ok=False, timeout=1800):
    stdout = raw / (name + ".stdout")
    stderr = raw / (name + ".stderr")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        result = subprocess.run(command, cwd=ROOT, input=input_bytes, stdout=out,
            stderr=err, timeout=timeout, check=False)
    save(raw / (name + ".exit"), str(result.returncode).encode())
    if result.returncode and not missing_ok:
        raise RuntimeError(f"{name} failed; raw output: {raw}")
    return result.returncode, stdout.read_bytes()


def kubectl(*args):
    return ["kubectl", "--context", CONTEXT, "--namespace", NAMESPACE, *args]


def owned(resource):
    metadata = resource.get("metadata", {})
    labels = metadata.get("labels", {})
    platform_owned = all(labels.get(key) == value for key, value in LABELS.items())
    task_owned = resource.get("kind") in {"ConfigMap", "Secret", "PersistentVolumeClaim"} and (
        labels.get("app.kubernetes.io/managed-by") == "wuji-task-runtime-controller"
        and bool(labels.get("wuji.dev/task-id")) and bool(labels.get("wuji.dev/tenant-id"))
        and metadata.get("namespace") == NAMESPACE
        and metadata.get("name", "").startswith("wuji-task-"))
    return platform_owned or task_owned


def namespace(raw, *, create=False):
    _, data = run(kubectl("get", "namespace", NAMESPACE, "--ignore-not-found", "-o", "json"),
        raw, "namespace-read", timeout=30)
    if data.strip():
        value = json.loads(data)
        if not owned(value):
            raise ValueError("namespace exists without this deployment's ownership labels")
        return value
    if not create:
        raise ValueError("managed namespace is absent")
    run(kubectl("auth", "can-i", "create", "namespaces"), raw, "namespace-permission", timeout=30)
    _, data = run(kubectl("create", "-f", str(ROOT / "ops/vnext/kubernetes/namespace.yaml"), "-o", "json"),
        raw, "namespace-create", timeout=30)
    return json.loads(data)


def certificates(directory):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    if directory.exists():
        raise ValueError("CA already exists; keep it and reuse the prepared state")
    directory.mkdir(parents=True, mode=0o700)
    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Wuji isolated vNext test CA")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=7))
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False,
            key_cert_sign=True, crl_sign=True, content_commitment=False, data_encipherment=False,
            key_agreement=False, encipher_only=None, decipher_only=None), critical=True)
        .sign(key, hashes.SHA256()))
    save(directory / "ca.key", key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    save(directory / "ca.crt", ca.public_bytes(serialization.Encoding.PEM))
    for service in ("runtime", "api", "gates", "postgres", "task-agent", "task-kali"):
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        dns = [service, f"{service}.{NAMESPACE}", f"{service}.{NAMESPACE}.svc",
               f"{service}.{NAMESPACE}.svc.cluster.local"]
        leaf = (x509.CertificateBuilder().subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, dns[2])]))
            .issuer_name(ca.subject).public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=7))
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=True,
                key_cert_sign=False, crl_sign=False, content_commitment=False, data_encipherment=False,
                key_agreement=False, encipher_only=None, decipher_only=None), critical=True)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([*[x509.DNSName(d) for d in dns],
                x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
        save(directory / f"{service}.key", leaf_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        save(directory / f"{service}.crt", leaf.public_bytes(serialization.Encoding.PEM))


def build_images(raw):
    images = {}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    snapshot = raw / "context"
    snapshot.mkdir()
    archive = subprocess.Popen(["git", "archive", revision], cwd=ROOT, stdout=subprocess.PIPE)
    extracted = subprocess.run(["tar", "-x", "-C", str(snapshot)], stdin=archive.stdout, check=False)
    archive.stdout.close()
    if extracted.returncode or archive.wait():
        raise RuntimeError("fixed-commit build context export failed")
    save(raw / "source-commit.txt", revision.encode())
    for target in ("agent", "platform", "kali"):
        tag = f"wuji-vnext-{target}:c1"
        build_metadata = raw / (target + ".metadata.json")
        run(["docker", "build", "--platform", "linux/arm64", "--target", target,
            "--metadata-file", str(build_metadata),
            "--label", "org.opencontainers.image.revision=" + revision,
            "--progress=plain", "-t", tag, "-f", str(snapshot / "ops/vnext/images/Dockerfile"), str(snapshot)],
            raw, "build-" + target)
        _, data = run(["docker", "image", "inspect", tag], raw, "image-" + target, timeout=30)
        image = json.loads(data)[0]
        if (image["Os"], image["Architecture"]) != ("linux", "arm64"):
            raise ValueError("unexpected built image platform")
        digest = json.loads(build_metadata.read_bytes())["containerimage.digest"]
        images[target] = {"tag": tag, "id": image["Id"], "exporter_digest": digest,
            "source_revision": revision}
    save(raw / "images.json", json.dumps(images, sort_keys=True, indent=2).encode())
    return images


def publish_images(images_path, raw):
    _, data = run(["docker","inspect","wuji-vnext-build-registry"],raw,"registry-inspect",timeout=30)
    registry = json.loads(data)[0]
    if registry["Config"].get("Labels",{}).get("app.kubernetes.io/managed-by") != MANAGER:
        raise ValueError("local build registry is not owned")
    if registry["HostConfig"]["NetworkMode"] != "host" or "REGISTRY_HTTP_ADDR=127.0.0.1:0" not in registry["Config"]["Env"]:
        raise ValueError("build registry must bind only the Docker VM loopback")
    run(["docker","logs","wuji-vnext-build-registry"],raw,"registry-log",timeout=30)
    logs=(raw/"registry-log.stdout").read_text()+(raw/"registry-log.stderr").read_text()
    ports=re.findall(r'listening on 127\.0\.0\.1:([0-9]+)',logs)
    if not ports:
        raise ValueError("registry has no observed loopback listener")
    origin = "127.0.0.1:" + ports[-1]
    published = {}
    for target, image in json.loads(images_path.read_bytes()).items():
        if target not in {"agent","platform","kali"}:
            raise ValueError("unsupported deployment image")
        repository = origin + "/wuji-vnext-" + target
        tag = repository + ":" + image["source_revision"][:12]
        run(["docker","tag",image["id"],tag],raw,"tag-"+target,timeout=30)
        run(["docker","push",tag],raw,"push-"+target)
        _, data = run(["docker","image","inspect",tag],raw,"published-"+target,timeout=30)
        actual = json.loads(data)[0]
        refs = [ref for ref in actual["RepoDigests"] if ref.startswith(repository+"@sha256:")]
        if actual["Id"] != image["id"] or len(refs) != 1:
            raise ValueError("published repository digest does not resolve the built image")
        published[target] = {"id":image["id"],"reference":refs[0],"source_revision":image["source_revision"]}
    save(raw/"images-published.json",json.dumps(published,sort_keys=True,indent=2).encode())


def secret_manifest(name, files):
    # Caller-selected files are trusted deployment inputs. Never emit their bytes
    # to stdout or include the private CA key in any resource.
    if any(Path(path).name == "ca.key" for path in files.values()):
        raise ValueError("CA signing key must never enter Kubernetes")
    return {"apiVersion": "v1", "kind": "Secret",
        "metadata": {"name": name, "namespace": NAMESPACE, "labels": LABELS},
        "type": "Opaque", "data": {key: base64.b64encode(Path(path).read_bytes()).decode()
                                      for key, path in files.items()}}


def manifest_objects(path):
    bundle = json.loads(path.read_bytes())
    objects = bundle["items"] if bundle.get("kind") == "List" else [bundle]
    allowed = {"Service", "Deployment", "ConfigMap", "Secret", "PersistentVolumeClaim",
               "ServiceAccount", "Role", "RoleBinding", "NetworkPolicy", "Job"}
    for obj in objects:
        if obj.get("kind") not in allowed or obj.get("metadata", {}).get("namespace") != NAMESPACE or not owned(obj):
            raise ValueError("deployment bundle must contain only owned namespace resources")
    return objects


def deploy(path, raw):
    namespace(raw)
    objects = manifest_objects(path)
    # Refuse taking over a colliding named object; apply only this exact bundle.
    for index, obj in enumerate(objects):
        kind, name = obj["kind"], obj["metadata"]["name"]
        _, data = run(kubectl("get", kind, name, "--ignore-not-found", "-o", "json"), raw,
            f"ownership-{index}", timeout=30)
        if data.strip() and not owned(json.loads(data)):
            raise ValueError("refusing to overwrite a foreign deployment resource")
    run(kubectl("apply", "-f", str(path)), raw, "apply", timeout=120)
    inventory = []
    for index, obj in enumerate(objects):
        _, data = run(kubectl("get", obj["kind"], obj["metadata"]["name"], "-o", "json"),
            raw, f"applied-{index}", timeout=30)
        actual = json.loads(data)
        inventory.append({"kind": obj["kind"], "name": obj["metadata"]["name"],
            "uid": actual["metadata"]["uid"]})
    save(raw / "inventory.json", json.dumps(inventory, indent=2).encode())


def cleanup(inventory_path, raw):
    namespace(raw)
    for index, item in enumerate(json.loads(inventory_path.read_bytes())):
        if item["kind"] in {"PersistentVolumeClaim", "Secret"}:
            continue  # Evidence/data and their credentials are retained by default.
        if item["kind"] not in {"Service", "Deployment", "ConfigMap", "ServiceAccount", "Role", "RoleBinding", "NetworkPolicy", "Job"}:
            raise ValueError("unsupported cleanup resource")
        _, data = run(kubectl("get", item["kind"], item["name"], "--ignore-not-found", "-o", "json"),
            raw, f"cleanup-read-{index}", timeout=30)
        if not data.strip():
            continue
        actual = json.loads(data)
        if not owned(actual) or actual["metadata"]["uid"] != item["uid"]:
            raise ValueError("cleanup ownership/UID changed")
        # Kubernetes delete receives the observed UID precondition in the object.
        api = actual["apiVersion"]
        resource = {"Service":"services", "Deployment":"deployments", "ConfigMap":"configmaps",
            "ServiceAccount":"serviceaccounts", "Role":"roles", "RoleBinding":"rolebindings",
            "NetworkPolicy":"networkpolicies", "Job":"jobs"}[item["kind"]]
        prefix = "/api/v1" if api == "v1" else "/apis/" + api
        url = f"{prefix}/namespaces/{NAMESPACE}/{resource}/{item['name']}"
        body = json.dumps({"apiVersion":"v1", "kind":"DeleteOptions",
            "preconditions":{"uid":item["uid"]}, "propagationPolicy":"Foreground"}).encode()
        run(kubectl("delete", "--raw", url, "-f", "-"), raw, f"delete-{index}", input_bytes=body, timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "build", "publish", "deploy", "test", "status", "cleanup"))
    parser.add_argument("--state-directory", type=Path, default=STATE)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--images", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    state = args.state_directory.resolve()
    if state != STATE and STATE not in state.parents:
        raise ValueError("state must remain in the ignored vNext deployment directory")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    raw = Path(tempfile.mkdtemp(prefix=args.command + "-", dir=state))
    if args.command == "prepare":
        namespace(raw, create=True)
        if not (state / "tls").exists():
            certificates(state / "tls")
        ca = (state / "tls/ca.crt").read_bytes()
        save(raw / "public-binding.json", json.dumps({"context": CONTEXT,
            "namespace": NAMESPACE, "ca_sha256": sha256(ca).hexdigest()}).encode())
    elif args.command == "build":
        build_images(raw)
    elif args.command == "publish":
        if args.images is None:
            parser.error("publish requires the exact fixed-build inventory")
        publish_images(args.images.resolve(), raw)
    elif args.command == "deploy":
        if args.manifest is None:
            parser.error("deploy requires an explicit prepared bundle")
        deploy(args.manifest.resolve(), raw)
    elif args.command == "cleanup":
        if args.inventory is None:
            parser.error("cleanup requires the exact deployment inventory")
        cleanup(args.inventory.resolve(), raw)
    elif args.command == "test":
        run([str(ROOT / "scripts/vnext/uv.sh"), "run", "--frozen", "pytest",
            "tests/vnext/test_k8s_runtime.py", "-q"], raw, "pytest")
    else:
        namespace(raw)
        run(kubectl("get", "pods,deployments,services,pvc", "-l",
            "app.kubernetes.io/managed-by=" + MANAGER, "-o", "json"), raw, "status", timeout=30)
    print(json.dumps({"operation": args.command, "raw_directory": str(raw)}))


if __name__ == "__main__":
    main()
