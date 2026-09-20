"""Non-secret manifests for the isolated first-use release.

Only the private catalog Job and launch consumer mount owner authority. No
manifest here creates a Task, starts a Run or makes a model/target request.
"""
import json
import re

NAMESPACE = "wuji-vnext-test"
OWNER_LABEL = {"wuji.dev/first-use-owner": "first-use-release-v1"}


def metadata(name):
    return {"name": name, "namespace": NAMESPACE, "labels": dict(OWNER_LABEL)}


def image_ref(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}", value):
        raise ValueError("immutable published image reference required")
    return value


def suffix_for(mode):
    if mode not in {"real_model", "mechanism_synthetic"}:
        raise ValueError("explicit first-use mode required")
    return "deepseek" if mode == "real_model" else "mechanism"


def owner_secret_name(mode):
    # v7 freezes the evidence-driven v4 role instructions and wider Worker wire.
    # Keep older private templates for historical failed launches.
    return f"first-use-{suffix_for(mode)}-owner-v7"


def rbac_manifests():
    result = []
    rules = {
        "first-use-launch": [
            {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]},
            {"apiGroups": [""], "resources": ["configmaps", "persistentvolumeclaims", "services"],
             "verbs": ["get", "list", "create", "update", "patch"]},
            {"apiGroups": [""], "resources": ["secrets"], "verbs": ["get", "create", "patch"]},
            {"apiGroups": ["batch"], "resources": ["jobs"], "verbs": ["get", "list", "create"]},
            {"apiGroups": ["batch"], "resources": ["jobs/status"], "verbs": ["get"]},
        ],
        "first-use-gates": [
            {"apiGroups": [""], "resources": ["secrets"], "resourceNames": ["task-model-keys"], "verbs": ["get"]},
        ],
    }
    for name, grants in rules.items():
        result += [
            {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": metadata(name)},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": metadata(name), "rules": grants},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": metadata(name),
             "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": name},
             "subjects": [{"kind": "ServiceAccount", "name": name, "namespace": NAMESPACE}]},
        ]
    return result


def launch_manifests(*, images, mode, source_revision, evidence_ref, public_data):
    suffix = suffix_for(mode)
    if not re.fullmatch(r"[a-f0-9]{40}", source_revision):
        raise ValueError("fixed source revision required")
    if not isinstance(evidence_ref, str) or not 1 <= len(evidence_ref) <= 256:
        raise ValueError("reviewed capability evidence reference required")
    for role in ("agent", "kali", "platform"):
        image_ref(images[role])
    settings = {
        "schema_version": "wuji.launch-deployment.v1",
        "owner_config_file": "/run/wuji/bootstrap/config.json",
        "service_token_file": "/run/wuji/deployment-signing/service.token",
        "namespace": NAMESPACE, "agent_image": images["agent"], "kali_image": images["kali"],
        "runtime_origin": "https://runtime.wuji-vnext-test.svc:8443",
        "gate_url": "https://gates.wuji-vnext-test.svc:8443", "evidence_ref": evidence_ref,
    }
    if mode == "real_model":
        settings.update(gateway_url="https://first-use-litellm.wuji-first-use-model.svc:4000",
                        gateway_management_key_file="/run/wuji/gateway/master.key",
                        gateway_ca_file="/config/ca.crt")
    config = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": metadata("first-use-launch-config"),
              "data": {**{key: public_data[key] for key in ("ca.crt", "identity.pub")},
                       "launch.json": json.dumps(settings, sort_keys=True)}}
    secrets = {"input": (owner_secret_name(mode), "/run/wuji/bootstrap"),
               "agent-auth": ("task-agent-auth", "/run/wuji/task-agent-auth"),
               "kali-auth": ("task-kali-auth", "/run/wuji/task-kali-auth"),
               "signing-key": ("runtime-credentials", "/run/wuji/deployment-signing"),
               "gates-auth": ("gates-credentials", "/run/wuji/gates-credentials")}
    mounts = [{"name": name, "mountPath": path, "readOnly": True} for name, (_, path) in secrets.items()]
    volumes = [{"name": name, "secret": {"secretName": secret, "defaultMode": 0o440}}
               for name, (secret, _) in secrets.items()]
    if mode == "real_model":
        mounts.append({"name": "gateway", "mountPath": "/run/wuji/gateway", "readOnly": True})
        # Project only management authority, not the provider credential or DB URL.
        volumes.append({"name": "gateway", "secret": {"secretName": "first-use-litellm-private",
                        "defaultMode": 0o440, "items": [{"key": "master.key", "path": "master.key"}]}})
    mounts += [{"name": "public", "mountPath": "/config", "readOnly": True}, {"name": "tmp", "mountPath": "/tmp"}]
    volumes += [{"name": "public", "configMap": {"name": "first-use-launch-config"}},
                {"name": "tmp", "emptyDir": {"sizeLimit": "64Mi"}}]
    labels = {**OWNER_LABEL, "wuji.dev/service": "first-use-launch"}
    deployment = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": metadata("first-use-launch"),
        "spec": {"replicas": 1, "strategy": {"type": "Recreate"}, "selector": {"matchLabels": labels},
            "template": {"metadata": {"labels": labels, "annotations": {"wuji.dev/source-revision": source_revision}},
                "spec": {"serviceAccountName": "first-use-launch", "nodeSelector": {"kubernetes.io/arch": "arm64"},
                    "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10000,
                                        "fsGroup": 10000, "seccompProfile": {"type": "RuntimeDefault"}},
                    "containers": [{"name": "launch", "image": images["platform"], "imagePullPolicy": "IfNotPresent",
                        "command": ["python", "/opt/wuji/services/wuji-launch/main.py", "--batch-limit", "1"],
                        "env": [{"name": "POD_UID", "valueFrom": {"fieldRef": {"fieldPath": "metadata.uid"}}}],
                        "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                                            "capabilities": {"drop": ["ALL"]}},
                        "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
                        "volumeMounts": mounts}], "volumes": volumes}}}}
    return [config, deployment]


def catalog_job(*, platform_image, mode, job_name, public_data, program):
    suffix = suffix_for(mode)
    image_ref(platform_image)
    if not re.fullmatch(r"first-use-catalog-[a-z0-9-]{1,40}", job_name):
        raise ValueError("bounded catalog Job name required")
    config_name = job_name + "-code"
    config = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": metadata(config_name),
              "data": {"catalog.py": program, **{k: public_data[k] for k in ("ca.crt", "identity.pub")}}}
    job = {"apiVersion": "batch/v1", "kind": "Job", "metadata": metadata(job_name),
           "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 120,
                    "template": {"metadata": {"labels": dict(OWNER_LABEL)}, "spec": {
                        "restartPolicy": "Never", "automountServiceAccountToken": False,
                        "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10000,
                                            "fsGroup": 10000, "seccompProfile": {"type": "RuntimeDefault"}},
                        "containers": [{"name": "catalog", "image": platform_image,
                            "command": ["python", "/config/catalog.py"],
                            "env": [{"name": "WUJI_FIRST_USE_OWNER_CONFIG", "value": "/run/wuji/bootstrap/config.json"}],
                            "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                                                "capabilities": {"drop": ["ALL"]}},
                            "volumeMounts": [{"name": "public", "mountPath": "/config", "readOnly": True},
                                             {"name": "input", "mountPath": "/run/wuji/bootstrap", "readOnly": True},
                                             {"name": "tmp", "mountPath": "/tmp"}]}],
                        "volumes": [{"name": "public", "configMap": {"name": config_name}},
                                    {"name": "input", "secret": {"secretName": owner_secret_name(mode), "defaultMode": 0o440}},
                                    {"name": "tmp", "emptyDir": {"sizeLimit": "32Mi"}}]}}}}
    return [config, job]


def fixture_manifests(*, platform_image, program):
    """The only non-loopback mechanism target; never mounts any credential."""
    image_ref(platform_image)
    labels = {**OWNER_LABEL, "wuji.dev/service": "first-use-fixture"}
    return [
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": metadata("first-use-fixture-code"),
         "data": {"fixture.py": program}},
        {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": metadata("first-use-fixture"),
         "spec": {"replicas": 1, "strategy": {"type": "Recreate"}, "selector": {"matchLabels": labels},
          "template": {"metadata": {"labels": labels}, "spec": {
            "automountServiceAccountToken": False,
            "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10000,
                                "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": [{"name": "fixture", "image": platform_image,
                "command": ["python", "/fixture/fixture.py", "--host", "0.0.0.0", "--port", "8080"],
                "ports": [{"name": "http", "containerPort": 8080}],
                "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                                    "capabilities": {"drop": ["ALL"]}},
                "resources": {"requests": {"cpu": "25m", "memory": "32Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}},
                "volumeMounts": [{"name": "code", "mountPath": "/fixture", "readOnly": True}],
                "readinessProbe": {"tcpSocket": {"port": "http"}, "periodSeconds": 5}}],
            "volumes": [{"name": "code", "configMap": {"name": "first-use-fixture-code"}}]}}}},
        {"apiVersion": "v1", "kind": "Service", "metadata": metadata("first-use-fixture"),
         "spec": {"type": "ClusterIP", "selector": labels, "ports": [{"name": "http", "port": 8080, "targetPort": "http"}]}},
        {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": metadata("first-use-fixture-no-egress"),
         "spec": {"podSelector": {"matchLabels": labels}, "policyTypes": ["Egress"], "egress": []}},
    ]
