"""Owned Kubernetes resource construction; no workflow/permit/receiver state."""

import base64

NAMESPACE = "wuji-vnext-test"
LABELS = {"app.kubernetes.io/managed-by":"wuji-vnext-deployment", "wuji.dev/environment":"local-test"}


def metadata(name, *, namespace=NAMESPACE, **labels):
    return {"name":name, "namespace":namespace, "labels":{**LABELS, **labels}}


def pvc(name, size="1Gi", *, labels=None, annotations=None, namespace=NAMESPACE):
    meta = metadata(name, namespace=namespace)
    if labels is not None:
        meta["labels"] = labels
    if annotations is not None:
        meta["annotations"] = annotations
    return {"apiVersion":"v1", "kind":"PersistentVolumeClaim", "metadata":meta,
        "spec":{"accessModes":["ReadWriteOnce"], "resources":{"requests":{"storage":size}}}}


def secret(name, data, *, namespace=NAMESPACE):
    return {"apiVersion":"v1", "kind":"Secret", "metadata":metadata(name, namespace=namespace),
        "type":"Opaque", "data":{key:base64.b64encode(value).decode() for key,value in data.items()}}


def service(name, port, *, namespace=NAMESPACE):
    return {"apiVersion":"v1", "kind":"Service", "metadata":metadata(name, namespace=namespace),
        "spec":{"selector":{"wuji.dev/service":name}, "ports":[{"port":port,"targetPort":port,"name":"tls"}]}}


def security(uid, group=10000):
    return {"runAsUser":uid, "runAsGroup":group, "runAsNonRoot":True,
        "allowPrivilegeEscalation":False, "readOnlyRootFilesystem":True,
        "capabilities":{"drop":["ALL"]}}


def postgres(image, tls, password, *, namespace=NAMESPACE, architecture="arm64"):
    name = "postgres"
    container = {"name":"postgres", "image":image,
        "args":["postgres", "-c", "ssl=on", "-c", "ssl_cert_file=/run/wuji/tls/tls.crt",
                "-c", "ssl_key_file=/run/wuji/tls/tls.key"],
        "securityContext":security(999,999),
        "env":[{"name":"PGDATA","value":"/var/lib/postgresql/data/pgdata"},
            {"name":"POSTGRES_DB","value":"wuji_vnext"},
            {"name":"POSTGRES_USER","value":"bootstrap"},
            {"name":"POSTGRES_PASSWORD","valueFrom":{"secretKeyRef":{"name":"postgres-bootstrap","key":"password"}}}],
        "resources":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"1","memory":"512Mi"}},
        "volumeMounts":[{"name":"data","mountPath":"/var/lib/postgresql/data"},
            {"name":"tls","mountPath":"/run/wuji/tls","readOnly":True},
            {"name":"tmp","mountPath":"/tmp"}, {"name":"socket","mountPath":"/var/run/postgresql"}],
        "readinessProbe":{"exec":{"command":["pg_isready","-U","bootstrap","-d","wuji_vnext"]},
            "periodSeconds":5,"timeoutSeconds":3}}
    deploy = {"apiVersion":"apps/v1", "kind":"Deployment", "metadata":metadata(name, namespace=namespace),
        "spec":{"replicas":1,"strategy":{"type":"Recreate"},"selector":{"matchLabels":{"wuji.dev/service":name}},
            "template":{"metadata":{"labels":{**LABELS,"wuji.dev/service":name}},"spec":{
                "nodeSelector":{"kubernetes.io/arch":architecture},"automountServiceAccountToken":False,
                "securityContext":{"runAsNonRoot":True,"fsGroup":999,"seccompProfile":{"type":"RuntimeDefault"}},
                "containers":[container],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"postgres-data"}},
                    {"name":"tls","secret":{"secretName":"postgres-tls","defaultMode":288}},
                    {"name":"tmp","emptyDir":{"sizeLimit":"128Mi"}},
                    {"name":"socket","emptyDir":{"sizeLimit":"16Mi"}}]}}}}
    return [pvc("postgres-data", namespace=namespace),
        secret("postgres-bootstrap", {"password":password}, namespace=namespace),
        secret("postgres-tls", {"tls.crt":tls["postgres.crt"],"tls.key":tls["postgres.key"]}, namespace=namespace),
        service("postgres",5432, namespace=namespace), deploy]


def platform_storage(*, namespace=NAMESPACE):
    return [pvc(name, namespace=namespace) for name in ("platform-artifacts", "runtime-state")]


def task_storage(config):
    return [pvc(config.resource_names[key], labels=config.identity_labels,
                annotations=config.ownership_annotations, namespace=config.namespace)
            for key in ("agent_state", "kali_work", "kali_receipts")]


def platform(
    name, image, command, *, synthetic_model_image=None,
    namespace=NAMESPACE, architecture="arm64",
):
    if name not in {"runtime", "api", "scheduler", "gates"}:
        raise ValueError("fixed platform role required")
    mounts = [{"name":"config","mountPath":"/config","readOnly":True},
        {"name":"credentials","mountPath":"/run/wuji/credentials","readOnly":True},
        {"name":"tmp","mountPath":"/tmp"}]
    volumes = [{"name":"config","configMap":{"name":name+"-config"}},
        {"name":"credentials","secret":{"secretName":name+"-credentials","defaultMode":288}},
        {"name":"tmp","emptyDir":{"sizeLimit":"128Mi"}}]
    # Every platform role that serves or removes artifact bytes needs the same
    # store; a role-local root would tombstone rows while the bytes survive
    # somewhere else (or make authorized reads fail).
    mounts.insert(2, {"name":"artifacts","mountPath":"/var/lib/wuji/platform/artifacts"})
    volumes.insert(2, {"name":"artifacts","persistentVolumeClaim":{"claimName":"platform-artifacts"}})
    if name == "runtime":
        volumes.append({"name":"state","persistentVolumeClaim":{"claimName":"runtime-state"}})
        mounts.append({"name":"state","mountPath":"/var/lib/wuji/platform/state"})
    container = {"name":name,"image":image,"command":command,"securityContext":security(10001),
        "resources":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"1","memory":"768Mi"}},
        "volumeMounts":mounts}
    if name != "scheduler":
        container["readinessProbe"] = {"tcpSocket":{"port":8443},"periodSeconds":5}
    containers = [container]
    if synthetic_model_image is not None:
        if name != "gates":
            raise ValueError("D12 synthetic model belongs in the calling Gate Pod")
        containers.append({"name":"synthetic-model","image":synthetic_model_image,
            "command":["python","/opt/wuji/ops/vnext/synthetic_model.py","--host","127.0.0.1","--port","8081"],
            "securityContext":security(10001),"volumeMounts":[{"name":"tmp","mountPath":"/tmp"}],
            "resources":{"requests":{"cpu":"25m","memory":"32Mi"},"limits":{"cpu":"250m","memory":"128Mi"}}})
    return {"apiVersion":"apps/v1","kind":"Deployment","metadata":metadata(name, namespace=namespace),
        "spec":{"replicas":1,"strategy":{"type":"Recreate"},"selector":{"matchLabels":{"wuji.dev/service":name}},
            "template":{"metadata":{"labels":{**LABELS,"wuji.dev/service":name}},"spec":{
                "nodeSelector":{"kubernetes.io/arch":architecture},"securityContext":{"runAsNonRoot":True,
                    "fsGroup":10000,"seccompProfile":{"type":"RuntimeDefault"}},
                "automountServiceAccountToken":name=="runtime", "serviceAccountName":"runtime" if name=="runtime" else "default",
                "containers":containers,"volumes":volumes}}}}
