"""Create one isolated deployment's configuration/identity material, not execution facts."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey

from wuji_core.contracts.execution import TaskCreate
from wuji_core.admission.registry import TaskAdmissionConfig
from wuji_core.http import canonical_json_bytes
from wuji_maf_worker.factory import HarnessProfile
from wuji_task_runtime.manifest import build_task_pod
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig

from render import NAMESPACE, LABELS, metadata, secret, service, platform, task_storage


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open("xb") as f:
        path.chmod(0o600);f.write(data)



_IMAGE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
_TASK_CONFIG_FILE = re.compile(r"task-config(?:-[A-Za-z0-9_-]+)?\.json$")


def _published_image_ref(value, role):
    reference = value.get("reference") if isinstance(value, dict) else value
    if not isinstance(reference, str) or not _IMAGE_REFERENCE.fullmatch(reference):
        raise ValueError(f"{role} image must be an immutable published digest reference")
    return reference


def _published_image_set(images):
    if not isinstance(images, dict):
        raise ValueError("published image set must be an object")
    refs = {
        role: _published_image_ref(images.get(role), role)
        for role in ("agent", "kali", "platform")
    }
    revisions = {
        value.get("source_revision")
        for value in images.values()
        if isinstance(value, dict) and value.get("source_revision")
    }
    if len(revisions) > 1:
        raise ValueError("published image set mixes source revisions")
    return refs, next(iter(revisions), None)


def _task_runtime_config(values):
    normalized = deepcopy(values)
    for role in ("agent", "kali"):
        normalized[role + "_resources"] = ContainerResources(
            **normalized[role + "_resources"]
        )
    return TaskRuntimeConfig(**normalized)


def _read_json(path):
    try:
        return json.loads(Path(path).read_bytes())
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(f"invalid configuration JSON: {path.name}") from error


def _without_images(value):
    result = deepcopy(value)
    result.pop("agent_image", None)
    result.pop("kali_image", None)
    return result


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _refresh_backup(state, paths):
    backup_root = Path(state) / "refresh-backups"
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_root / stamp
    suffix = 0
    while backup.exists():
        suffix += 1
        backup = backup_root / f"{stamp}-{suffix}"
    backup.mkdir(mode=0o700)
    for path in paths:
        path = Path(path)
        if path.exists():
            shutil.copy2(path, backup / path.name)
    return backup


def refresh_images(root, state, images):
    """Refresh non-secret deployment bindings for an existing Task attempt.

    This function never creates owner/Task/credentials and never reads full
    platform Secret/PVC objects. It consumes the safe sidecars emitted by
    ``configure`` and atomically refreshes only image-bearing bindings.
    """
    root = Path(root).resolve()
    state = Path(state).resolve()
    configuration = state / "configuration"
    if not root.is_dir() or not configuration.is_dir():
        raise ValueError("existing deployment configuration is required")
    refs, source_revision = _published_image_set(images)

    task_files = sorted(
        path for path in configuration.iterdir()
        if path.is_file() and _TASK_CONFIG_FILE.fullmatch(path.name)
    )
    if not task_files:
        raise ValueError("existing task-config JSON is required")
    task_documents = [_read_json(path) for path in task_files]
    base = deepcopy(task_documents[0])
    if any(_without_images(document) != _without_images(base) for document in task_documents[1:]):
        raise ValueError("task-config files disagree outside image references")

    public_path = configuration / "public.json"
    public = _read_json(public_path)
    owner = public.get("owner")
    if not isinstance(owner, list) or len(owner) != 3:
        raise ValueError("existing owner binding is required")
    if public.get("definition_digest") != base.get("config_digest"):
        raise ValueError("Task definition digest binding changed")
    if str(base.get("tenant_id")) != str(owner[0]) or str(base.get("task_id")) != str(owner[2]):
        raise ValueError("Task owner binding changed")
    runtime_path = configuration / "runtime-deployment.json"
    runtime = _read_json(runtime_path)
    runtime_task = ((runtime.get("pod_runtime") or {}).get("task_config"))
    if not isinstance(runtime_task, dict) or _without_images(runtime_task) != _without_images(base):
        raise ValueError("runtime deployment task-config binding differs")

    updated_task = deepcopy(base)
    updated_task.update(agent_image=refs["agent"], kali_image=refs["kali"])
    task_config = _task_runtime_config(updated_task)
    updated_task = deepcopy(updated_task)
    runtime["pod_runtime"]["task_config"] = deepcopy(updated_task)

    runtime_manifest_path = configuration / "runtime-deployment-manifest.json"
    runtime_manifest = _read_json(runtime_manifest_path)
    if runtime_manifest.get("kind") != "Deployment":
        raise ValueError("runtime deployment manifest kind is invalid")
    runtime_containers = (((runtime_manifest.get("spec") or {}).get("template") or {})
                          .get("spec", {}).get("containers", []))
    runtime_matches = [item for item in runtime_containers if item.get("name") == "runtime"]
    if len(runtime_matches) != 1:
        raise ValueError("runtime deployment manifest must have one runtime container")
    runtime_matches[0]["image"] = refs["platform"]

    runtime_configmap_path = configuration / "runtime-configmap.json"
    runtime_configmap = _read_json(runtime_configmap_path)
    if runtime_configmap.get("kind") != "ConfigMap":
        raise ValueError("runtime ConfigMap manifest kind is invalid")
    runtime_data = runtime_configmap.get("data")
    if not isinstance(runtime_data, dict) or "deployment.json" not in runtime_data:
        raise ValueError("runtime ConfigMap deployment.json is required")
    old_runtime_config = json.loads(runtime_data["deployment.json"])
    old_runtime_task = ((old_runtime_config.get("pod_runtime") or {}).get("task_config"))
    if not isinstance(old_runtime_task, dict) or _without_images(old_runtime_task) != _without_images(base):
        raise ValueError("runtime ConfigMap task-config binding differs")
    runtime_data["deployment.json"] = canonical_json_bytes(runtime).decode()

    # ``platform.json`` is the actual apply bundle.  The sidecar manifests above
    # are useful for inspection, but refreshing only those files leaves the live
    # runtime ConfigMap on the old image pair and recreates the exact
    # Controller/template mismatch this command is meant to repair.  Update the
    # existing owned bundle in place, changing only published image references
    # and the runtime deployment payload; credentials, PVCs, and Task-owned
    # resources remain byte-for-byte untouched.
    platform_path = configuration / "platform.json"
    platform_manifest = _read_json(platform_path)
    if platform_manifest.get("kind") != "List" or not isinstance(platform_manifest.get("items"), list):
        raise ValueError("platform deployment manifest is invalid")
    platform_items = platform_manifest["items"]
    runtime_cm_matches = [
        item for item in platform_items
        if item.get("kind") == "ConfigMap"
        and (item.get("metadata") or {}).get("name") == runtime_configmap.get("metadata", {}).get("name")
    ]
    if len(runtime_cm_matches) != 1:
        raise ValueError("platform bundle must have one runtime ConfigMap")
    platform_runtime_cm = runtime_cm_matches[0]
    platform_runtime_data = platform_runtime_cm.get("data")
    if not isinstance(platform_runtime_data, dict) or "deployment.json" not in platform_runtime_data:
        raise ValueError("platform runtime ConfigMap deployment.json is required")
    platform_runtime_config = json.loads(platform_runtime_data["deployment.json"])
    platform_runtime_task = ((platform_runtime_config.get("pod_runtime") or {}).get("task_config"))
    if not isinstance(platform_runtime_task, dict) or _without_images(platform_runtime_task) != _without_images(base):
        raise ValueError("platform runtime ConfigMap task-config binding differs")
    platform_runtime_data["deployment.json"] = canonical_json_bytes(runtime).decode()

    for deployment_name in ("runtime", "scheduler", "gates"):
        matches = [
            item for item in platform_items
            if item.get("kind") == "Deployment"
            and (item.get("metadata") or {}).get("name") == deployment_name
        ]
        if len(matches) != 1:
            raise ValueError(f"platform bundle must have one {deployment_name} Deployment")
        containers = ((matches[0].get("spec") or {}).get("template") or {}).get("spec", {}).get("containers")
        if not isinstance(containers, list) or not containers:
            raise ValueError(f"{deployment_name} Deployment containers are required")
        for container in containers:
            if not isinstance(container, dict) or not isinstance(container.get("image"), str):
                raise ValueError(f"{deployment_name} Deployment image binding is invalid")
            container["image"] = refs["platform"]

    task_configmaps_path = configuration / "task-configmaps.json"
    task_configmaps = _read_json(task_configmaps_path)
    if task_configmaps.get("kind") != "List" or not isinstance(task_configmaps.get("items"), list):
        raise ValueError("Task-owned ConfigMap manifest is invalid")
    expected_labels = {
        "app.kubernetes.io/managed-by": "wuji-task-runtime-controller",
        "wuji.dev/task-id": str(owner[2]),
        "wuji.dev/tenant-id": str(owner[0]),
    }
    for item in task_configmaps["items"]:
        metadata = item.get("metadata") or {}
        labels = metadata.get("labels") or {}
        if item.get("kind") != "ConfigMap" or metadata.get("namespace") != base.get("namespace"):
            raise ValueError("Task-owned ConfigMap namespace/kind binding differs")
        if any(labels.get(key) != value for key, value in expected_labels.items()):
            raise ValueError("Task-owned ConfigMap ownership binding differs")

    task_pod = build_task_pod(task_config)
    if task_pod["metadata"]["annotations"].get("wuji.dev/template-digest") != task_config.template_digest:
        raise ValueError("Pod template digest generation is inconsistent")
    if [item["image"] for item in task_pod["spec"]["containers"]] != [refs["agent"], refs["kali"]]:
        raise ValueError("Pod image binding is inconsistent")

    image_set = {
        "agent": refs["agent"],
        "kali": refs["kali"],
        "platform": refs["platform"],
    }
    image_set_document = {
        "images": image_set,
        "source_revision": source_revision,
    }
    refresh_document = {
        "owner": owner,
        "definition_digest": public["definition_digest"],
        "task_id": str(task_config.task_id),
        "tenant_id": str(task_config.tenant_id),
        "namespace": task_config.namespace,
        "execution_epoch": task_config.execution_epoch,
        "runtime_attempt": task_config.runtime_attempt,
        "config_digest": task_config.config_digest,
        "scope_digest": task_config.scope_digest,
        "template_digest": task_config.template_digest,
        "images": image_set,
        "credentials_preserved": True,
        "secret_and_pvc_manifests_untouched": True,
    }

    touched = [*task_files, runtime_path, runtime_manifest_path,
               runtime_configmap_path, platform_path, task_configmaps_path,
               configuration / "task-pod.json", configuration / "image-set.json",
               configuration / "refresh-manifest.json"]
    backup = _refresh_backup(state, touched)
    payloads = {
        path: canonical_json_bytes(document)
        for path, document in (
            [(path, updated_task) for path in task_files]
            + [(runtime_path, runtime),
               (runtime_manifest_path, runtime_manifest),
               (runtime_configmap_path, runtime_configmap),
               (platform_path, platform_manifest),
               (task_configmaps_path, task_configmaps),
               (configuration / "task-pod.json", task_pod),
               (configuration / "image-set.json", image_set_document),
               (configuration / "refresh-manifest.json", refresh_document)]
        )
    }
    for path, data in payloads.items():
        _atomic_write(path, data)
    return {
        "configuration": str(configuration),
        "backup": str(backup),
        "task_config_files": [path.name for path in task_files],
        "task_id": str(task_config.task_id),
        "tenant_id": str(task_config.tenant_id),
        "execution_epoch": task_config.execution_epoch,
        "runtime_attempt": task_config.runtime_attempt,
        "config_digest": task_config.config_digest,
        "template_digest": task_config.template_digest,
        "images": image_set,
    }


def configure(root, state, images):
    bundle=state/"configuration"
    if bundle.exists():raise ValueError("configuration already exists; preserve its Task/credentials")
    bundle.mkdir(mode=0o700)
    tenant,project,task=owner=tuple(str(uuid4()) for _ in range(3))
    now=datetime.now(timezone.utc);published=now.isoformat().replace("+00:00","Z")
    issuer="https://identity.wuji-vnext-test.invalid";audience="wuji-vnext-deployment"
    key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    encryption=secrets.token_bytes(32)
    tokens={}
    for subject,roles in {"operator":["operator"],"scheduler":["scheduler"],"receiver":["controller"],
                          "pod-controller":["controller"],"collector":["collector"],"gate":["gate"]}.items():
        tokens[subject]=jwt.encode({"alg":"RS256","kid":"deployment-key"},{
            "iss":issuer,"aud":audience,"sub":subject,"tenant_id":tenant,"roles":roles,
            "iat":int(now.timestamp()),"nbf":int(now.timestamp())-1,
            "exp":int((now+timedelta(hours=4)).timestamp()),"jti":str(uuid4())},RSAKey.import_key(private),algorithms=["RS256"]).encode()
    db={"host":f"postgres.{NAMESPACE}.svc","port":5432,"dbname":"wuji_vnext"}
    passwords={name:secrets.token_urlsafe(36) for name in ("wuji_migration","wuji_app","wuji_pod")}
    receiver="task-"+task+"-a1";environment="pod-environment-"+task
    executor_ref="kali-workspace-v1";tool_ref="workspace-read-v1"
    binding=dict(tenant_id=tenant,project_id=project,task_id=task,executor_ref=executor_ref,
        receiver_id=receiver,environment_ref=environment,collector_subject="collector",gate_subject="gate")
    lock=sha256((root/"packages/maf-worker/uv.lock").read_bytes()).hexdigest()
    profiles={kind:HarnessProfile(ref=f"harness.{kind}.c2.v1",revision="1",work_kind=kind,
        instructions="Read version.txt once using the registered workspace tool and cite the returned evidence.",
        tool_definition_refs=(tool_ref,),lock_digest=lock,max_context_records=128,max_context_bytes=65536,
        max_output_tokens=2048).snapshot() for kind in ("explore","reason","report")}
    admission=TaskAdmissionConfig.model_validate({
        "model":{"ref":"synthetic-model-v1","revision":"1","published_at":published,
            "capability_ref":"synthetic-chat-completions-v1","protocol":"chat_completions",
            "client_model":"synthetic-model","upstream_model":"synthetic-model",
            "gateway_url":"http://127.0.0.1:8081/v1/chat/completions","task_key_ref":"model-key","max_retries":0},
        "runtime":{"ref":"k8s-runtime-v1","revision":"1","published_at":published,"lock_digest":lock,
            "limits":{"max_work_items":4,"max_reason_runs":2,"max_model_requests":8,"max_tool_calls":8,
                "max_single_output_bytes":32768,"max_total_output_bytes":131072,"max_elapsed_seconds":1800,
                "max_attempts_per_work":2,"repair_attempts":0},"chunk_bytes":512,"buffer_bytes":4096,
            "idle_timeout_seconds":15.0,"total_timeout_seconds":60.0,"max_pending_operations":4,
            "max_inflight_tools":1,"max_inflight_model_requests":1,"allowed_tool_refs":[tool_ref]},
        "allowed_tool_refs":[tool_ref]}).model_dump(mode="json")
    task_body=TaskCreate.model_validate({"schema_version":"wuji.api.v2","project_id":project,
        "name":"C2 isolated Kali workspace read","scenario":"web_single",
        "goal":{"text":"Read the isolated namespace's version.txt without external target traffic.","criteria":[{
            "criterion_id":"version-read","object":"isolated Kali fixture file","condition":"durable read evidence",
            "evidence_requirements":["sealed bytes"],"allowed_methods":["deterministic"],
            "responsible_party":"deployment-test","required":True}]},
        "authorization_scope":[{"host":"fixture.invalid","protocol":"https","port":443}],
        "authorization_expires_at":(now+timedelta(hours=4)).isoformat(),
        "model_profile_ref":"synthetic-model-v1","runtime_profile_ref":"k8s-runtime-v1",
        "budget":{"amount":"1","currency":"USD"}}).model_dump(mode="json")
    definition={"task":task_body,"start_points":["workspace:version.txt"],"model_profile":admission["model"],
        "runtime_profile":admission["runtime"],"worker_profiles":profiles,"lock_digest":lock,"evaluation_mode":"mechanism_synthetic"}
    definition_digest=sha256(canonical_json_bytes(definition)).hexdigest()
    image_refs, image_source_revision = _published_image_set(images)
    config_values={"tenant_id":tenant,"task_id":task,"namespace":NAMESPACE,"runtime_attempt":1,"execution_epoch":2,
        "scope_digest":sha256(canonical_json_bytes(task_body["authorization_scope"])).hexdigest(),"config_digest":definition_digest,
        "agent_image":image_refs["agent"],"kali_image":image_refs["kali"],
        "agent_resources":{"cpu_request":"100m","memory_request":"128Mi","cpu_limit":"1","memory_limit":"512Mi"},
        "kali_resources":{"cpu_request":"100m","memory_request":"128Mi","cpu_limit":"1","memory_limit":"512Mi"},
        "tmp_size_limit":"128Mi","pod_deadline_seconds":1800,"expose_pod_identity":True,"kali_receipts_enabled":True}
    config=TaskRuntimeConfig(**{**config_values,**{k:ContainerResources(**config_values[k]) for k in ("agent_resources","kali_resources")}})
    tls={p.name:p.read_bytes() for p in (state/"tls").iterdir() if p.suffix in {".key",".crt"} and p.name!="ca.key"}
    bootstrap={"database":{**db,"user":"bootstrap","password":(state/"credentials/bootstrap.password").read_text()},
        "roles":passwords,"ca_file":"/config/ca.crt","owner":owner,"definition":definition,"admission":admission,
        "operator_subject":"operator","pod_controller_subject":"pod-controller", "identity":{"issuer":issuer,"audience":audience},
        "public_key_file":"/config/identity.pub","operator_token_file":"/run/wuji/bootstrap/operator.token",
        "task_access":{"operator":{"write":True,"control":True},"scheduler":{"admit":True},
            "pod-controller":{"control":True,"observe":True,"admit":True},"receiver":{"observe":True,"settle":True},
            "collector":{"capture":True,"settle":True},"gate":{}},
        "tool":{"ref":tool_ref,"revision":"1","published_at":published,"name":"read_workspace",
            "input_schema":{"type":"object","additionalProperties":False,"required":["path"],"properties":{"path":{"type":"string"}}},
            "executor_ref":executor_ref,"approval_required":False,"allowed_target_kinds":["workspace_read"]},
        "executor":{"ref":executor_ref,"receiver_id":receiver,"environment_ref":environment,
            "collector_subject":"collector","evidence_origin":"fixture_capture","capture_layer":"fixture_file_bytes","allowed_tool_refs":[tool_ref]}}
    objects=task_storage(config)
    runtime_settings = None
    runtime_manifest = None
    runtime_configmap = None
    task_configmaps = []
    def configmap(name,data,task_owned=False):
        obj={"apiVersion":"v1","kind":"ConfigMap","metadata":metadata(name),"data":data}
        if task_owned:obj["metadata"].update(labels=config.identity_labels,annotations=config.ownership_annotations)
        return obj
    base={"schema_version":"wuji.deployment.v1","database_file":"/run/wuji/credentials/database.json",
        "public_key_file":"/config/identity.pub","issuer":issuer,"audience":audience,
        "service_token_file":"/run/wuji/credentials/service.token","ca_file":"/config/ca.crt","profiles_file":"/config/profiles.json"}
    for name,subject,dbuser in (("runtime","pod-controller","wuji_pod"),("scheduler","scheduler","wuji_app"),("gates","gate","wuji_app")):
        settings={**base,"role":name}
        credentials={"service.token":tokens[subject],"database.json":canonical_json_bytes({**db,"user":dbuser,"password":passwords[dbuser]})}
        if name!="scheduler":credentials.update({"tls.crt":tls[name+".crt"],"tls.key":tls[name+".key"]})
        if name in {"runtime","scheduler"}:
            credentials.update({"signing.key":private,"encryption.key":encryption})
            settings["secret_refs"]={"signing-key":"/run/wuji/credentials/signing.key","encryption-key":"/run/wuji/credentials/encryption.key"}
        if name=="runtime":
            credentials["receiver.token"]=tokens["receiver"]
            settings.update(task_ids=[task],work_kinds=["reason","explore","report"],receiver_token_file="/run/wuji/credentials/receiver.token",
                supervisor_url=f"https://task-agent.{NAMESPACE}.svc:8443",host_origin=f"https://runtime.{NAMESPACE}.svc:8443",
                model_gate_url=f"https://gates.{NAMESPACE}.svc:8443/internal/v2/model",tool_gate_url=f"https://gates.{NAMESPACE}.svc:8443/internal/v2/tool-calls",
                public_commands=True,public_approvals=True,journal_path="/var/lib/wuji/platform/state/dispatch.sqlite3",
                spool_directory="/var/lib/wuji/platform/state/intake",
                pod_runtime={"task_config":config_values,"receiver":{"receiver_id":receiver,"receiver_subject":"receiver",
                    "environment_ref":environment,"credential_template_ref":"deployment-worker-v1","model_mode":"synthetic"},
                    "kubernetes_url":"https://kubernetes.default.svc","kubernetes_ca_file":"/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                    "kubernetes_token_file":"/var/run/secrets/kubernetes.io/serviceaccount/token"})
        if name=="gates":
            credentials.update({"collector.token":tokens["collector"],"model.key":b"synthetic-local-only"})
            settings.update(secret_refs={"model-key":"/run/wuji/credentials/model.key"},executors=[{
                "binding":binding,"base_url":f"https://task-kali.{NAMESPACE}.svc:8444",
                "gate_token_file":"/run/wuji/credentials/service.token","collector_token_file":"/run/wuji/credentials/collector.token"}])
        platform_configmap = configmap(name+"-config",{"deployment.json":canonical_json_bytes(settings).decode(),
            "profiles.json":canonical_json_bytes(list(profiles.values())).decode(),"identity.pub":public.decode(),"ca.crt":tls["ca.crt"].decode()})
        objects += [platform_configmap,secret(name+"-credentials",credentials)]
        if name == "runtime":
            runtime_settings = deepcopy(settings)
            runtime_configmap = deepcopy(platform_configmap)
        command=(["python",f"/opt/wuji/services/wuji-{name}/main.py","--factory",f"deployment:build_{name}"] if name in {"runtime","scheduler"} else
            ["python","-m","uvicorn","gate_deployment:build_gates","--factory","--host","0.0.0.0"])
        if name!="scheduler":command += ["--port","8443","--ssl-certfile","/run/wuji/credentials/tls.crt","--ssl-keyfile","/run/wuji/credentials/tls.key"]
        platform_manifest = platform(name,image_refs["platform"],command,synthetic_model_image=image_refs["platform"] if name=="gates" else None)
        objects.append(platform_manifest)
        if name == "runtime":
            runtime_manifest = deepcopy(platform_manifest)
        if name!="scheduler":objects.append(service(name,8443))
    agent_config={"schema_version":"wuji.supervisor.deployment.v1","controller_origin":f"https://runtime.{NAMESPACE}.svc:8443",
        "receiver":{"receiver_id":receiver,"runtime_attempt":"1","environment_ref":environment},"receiver_token_file":"/run/wuji/credentials/receiver.token",
        "profiles":{p["ref"]:[kind] for kind,p in profiles.items()},"inbox_dir":"/var/lib/wuji/agent/inbox",
        "ca_file":"/config/ca.crt","certificate_file":"/run/wuji/credentials/tls.crt","private_key_file":"/run/wuji/credentials/tls.key","port":8443}
    kali_config={"schema_version":"wuji.kali.deployment.v1","binding":binding,"platform_url":f"https://gates.{NAMESPACE}.svc:8443",
        "ca_file":"/config/ca.crt","collector_token_file":"/run/wuji/credentials/collector.token",
        "public_key_file":"/config/identity.pub","issuer":issuer,"audience":audience,"root":"/workspace","receipt_root":"/var/lib/wuji/kali-receipts"}
    for role,cfg,bearer_name,bearer_subject in (("agent",agent_config,"receiver.token","receiver"),("kali",kali_config,"collector.token","collector")):
        task_configmap = configmap(config.resource_names[role+"_config"],{"supervisor.json" if role=="agent" else "kali.json":canonical_json_bytes(cfg).decode(),"ca.crt":tls["ca.crt"].decode(),"identity.pub":public.decode()},True)
        task_configmaps.append(deepcopy(task_configmap))
        objects.append(task_configmap)
        obj=secret(config.resource_names[role+"_auth"],{bearer_name:tokens[bearer_subject],"tls.crt":tls["task-"+role+".crt"],"tls.key":tls["task-"+role+".key"]})
        obj["metadata"].update(labels=config.identity_labels,annotations=config.ownership_annotations);objects.append(obj)
        svc=service("task-"+role,8443 if role=="agent" else 8444);svc["spec"]["selector"]=config.identity_labels;objects.append(svc)
    # Populate only the synthetic mechanism fixture through a Kubernetes Job.
    # The production ToolGate still authorizes and records the subsequent read.
    initializer_name = config.task_prefix + "-workspace-init"
    initializer_meta = metadata(initializer_name)
    initializer_meta["labels"].update(config.identity_labels)
    initializer_meta["annotations"] = config.ownership_annotations
    objects.append({"apiVersion":"batch/v1","kind":"Job","metadata":initializer_meta,
        "spec":{"backoffLimit":0,"activeDeadlineSeconds":120,"template":{
            "metadata":{"labels":dict(initializer_meta["labels"]),"annotations":dict(initializer_meta["annotations"])},
            "spec":{"automountServiceAccountToken":False,"nodeSelector":{"kubernetes.io/arch":"arm64"},
                "restartPolicy":"Never","securityContext":{"runAsNonRoot":True,"fsGroup":10000,
                    "seccompProfile":{"type":"RuntimeDefault"}},
                "containers":[{"name":"workspace-init","image":image_refs["kali"],
                    "command":["sh","-c","umask 077; printf 'wuji-c2-fixture-v1\n' > /workspace/version.txt"],
                    "securityContext":{"runAsUser":10002,"runAsGroup":10000,"runAsNonRoot":True,
                        "allowPrivilegeEscalation":False,"readOnlyRootFilesystem":True,
                        "capabilities":{"drop":["ALL"]}},
                    "volumeMounts":[{"name":"kali-work","mountPath":"/workspace"},
                        {"name":"tmp","mountPath":"/tmp"}],
                    "resources":{"requests":{"cpu":"25m","memory":"32Mi"},
                        "limits":{"cpu":"250m","memory":"128Mi"}}}],
                "volumes":[{"name":"kali-work","persistentVolumeClaim":{"claimName":config.resource_names["kali_work"]}},
                    {"name":"tmp","emptyDir":{"sizeLimit":"16Mi"}}]}}}})
    objects += [{"apiVersion":"v1","kind":"ServiceAccount","metadata":metadata("runtime")},
        {"apiVersion":"rbac.authorization.k8s.io/v1","kind":"Role","metadata":metadata("runtime"),"rules":[
            {"apiGroups":[""],"resources":["pods"],"verbs":["get","list","create","delete"]},
            {"apiGroups":[""],"resources":["configmaps","secrets","persistentvolumeclaims","services"],"verbs":["get"]},
            {"apiGroups":["discovery.k8s.io"],"resources":["endpointslices"],"verbs":["list"]}]},
        {"apiVersion":"rbac.authorization.k8s.io/v1","kind":"RoleBinding","metadata":metadata("runtime"),
         "roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"Role","name":"runtime"},
         "subjects":[{"kind":"ServiceAccount","name":"runtime","namespace":NAMESPACE}]}]
    if runtime_settings is None or runtime_manifest is None or runtime_configmap is None:
        raise ValueError("runtime deployment configuration was not assembled")
    write(bundle/"platform.json",json.dumps({"apiVersion":"v1","kind":"List","items":objects}).encode())
    write(bundle/"bootstrap.json",canonical_json_bytes(bootstrap));write(bundle/"operator.token",tokens["operator"])
    write(bundle/"identity.pub",public);write(bundle/"task-config.json",canonical_json_bytes(config_values))
    write(bundle/"public.json",canonical_json_bytes({"owner":owner,"receiver_id":receiver,"definition_digest":definition_digest}))
    write(bundle/"runtime-deployment.json",canonical_json_bytes(runtime_settings))
    write(bundle/"runtime-deployment-manifest.json",canonical_json_bytes(runtime_manifest))
    write(bundle/"runtime-configmap.json",canonical_json_bytes(runtime_configmap))
    write(bundle/"task-configmaps.json",canonical_json_bytes({"apiVersion":"v1","kind":"List","items":task_configmaps}))
    write(bundle/"task-pod.json",canonical_json_bytes(build_task_pod(config)))
    write(bundle/"image-set.json",canonical_json_bytes({"images":image_refs,"source_revision":image_source_revision}))
    return bundle
