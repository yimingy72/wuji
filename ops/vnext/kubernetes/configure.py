"""Create one isolated deployment's configuration/identity material, not execution facts."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey

from wuji_core.contracts.execution import TaskCreate
from wuji_core.admission.registry import TaskAdmissionConfig
from wuji_core.http import canonical_json_bytes
from wuji_maf_worker.factory import HarnessProfile
from wuji_task_runtime.models import ContainerResources, TaskRuntimeConfig

from render import NAMESPACE, LABELS, metadata, secret, service, platform, task_storage


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open("xb") as f:
        path.chmod(0o600);f.write(data)


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
            "gateway_url":"http://127.0.0.1:8081/v1","task_key_ref":"model-key","max_retries":0},
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
    config_values={"tenant_id":tenant,"task_id":task,"namespace":NAMESPACE,"runtime_attempt":1,"execution_epoch":2,
        "scope_digest":sha256(canonical_json_bytes(task_body["authorization_scope"])).hexdigest(),"config_digest":definition_digest,
        "agent_image":images["agent"],"kali_image":images["kali"],
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
            "pod-controller":{"control":True,"observe":True},"receiver":{"observe":True,"settle":True},
            "collector":{"capture":True,"settle":True},"gate":{}},
        "tool":{"ref":tool_ref,"revision":"1","published_at":published,"name":"read_workspace",
            "input_schema":{"type":"object","additionalProperties":False,"required":["path"],"properties":{"path":{"type":"string"}}},
            "executor_ref":executor_ref,"approval_required":False,"allowed_target_kinds":["workspace_read"]},
        "executor":{"ref":executor_ref,"receiver_id":receiver,"environment_ref":environment,
            "collector_subject":"collector","evidence_origin":"fixture_capture","capture_layer":"fixture_file_bytes","allowed_tool_refs":[tool_ref]}}
    objects=task_storage(config)
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
            settings.update(task_ids=[task],receiver_token_file="/run/wuji/credentials/receiver.token",
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
        objects += [configmap(name+"-config",{"deployment.json":canonical_json_bytes(settings).decode(),
            "profiles.json":canonical_json_bytes(list(profiles.values())).decode(),"identity.pub":public.decode(),"ca.crt":tls["ca.crt"].decode()}),secret(name+"-credentials",credentials)]
        command=(["python",f"/opt/wuji/services/wuji-{name}/main.py","--factory",f"deployment:build_{name}"] if name in {"runtime","scheduler"} else
            ["python","-m","uvicorn","gate_deployment:build_gates","--factory","--host","0.0.0.0"])
        if name!="scheduler":command += ["--port","8443","--ssl-certfile","/run/wuji/credentials/tls.crt","--ssl-keyfile","/run/wuji/credentials/tls.key"]
        objects += [platform(name,images["platform"],command,synthetic_model_image=images["platform"] if name=="gates" else None)]
        if name!="scheduler":objects.append(service(name,8443))
    agent_config={"schema_version":"wuji.supervisor.deployment.v1","controller_origin":f"https://runtime.{NAMESPACE}.svc:8443",
        "receiver":{"receiver_id":receiver,"runtime_attempt":"1","environment_ref":environment},"receiver_token_file":"/run/wuji/credentials/receiver.token",
        "profiles":{p["ref"]:[kind] for kind,p in profiles.items()},"inbox_dir":"/var/lib/wuji/agent/inbox",
        "ca_file":"/config/ca.crt","certificate_file":"/run/wuji/credentials/tls.crt","private_key_file":"/run/wuji/credentials/tls.key","port":8443}
    kali_config={"schema_version":"wuji.kali.deployment.v1","binding":binding,"platform_url":f"https://gates.{NAMESPACE}.svc:8443",
        "ca_file":"/config/ca.crt","collector_token_file":"/run/wuji/credentials/collector.token",
        "public_key_file":"/config/identity.pub","issuer":issuer,"audience":audience,"root":"/workspace","receipt_root":"/var/lib/wuji/kali-receipts"}
    for role,cfg,bearer_name,bearer_subject in (("agent",agent_config,"receiver.token","receiver"),("kali",kali_config,"collector.token","collector")):
        objects.append(configmap(config.resource_names[role+"_config"],{("supervisor.json" if role=="agent" else "kali.json"):canonical_json_bytes(cfg).decode(),"ca.crt":tls["ca.crt"].decode(),"identity.pub":public.decode()},True))
        obj=secret(config.resource_names[role+"_auth"],{bearer_name:tokens[bearer_subject],"tls.crt":tls["task-"+role+".crt"],"tls.key":tls["task-"+role+".key"]})
        obj["metadata"].update(labels=config.identity_labels,annotations=config.ownership_annotations);objects.append(obj)
        svc=service("task-"+role,8443 if role=="agent" else 8444);svc["spec"]["selector"]=config.identity_labels;objects.append(svc)
    objects += [{"apiVersion":"v1","kind":"ServiceAccount","metadata":metadata("runtime")},
        {"apiVersion":"rbac.authorization.k8s.io/v1","kind":"Role","metadata":metadata("runtime"),"rules":[
            {"apiGroups":[""],"resources":["pods"],"verbs":["get","list","create","delete"]},
            {"apiGroups":[""],"resources":["configmaps","secrets","persistentvolumeclaims","services"],"verbs":["get"]},
            {"apiGroups":["discovery.k8s.io"],"resources":["endpointslices"],"verbs":["list"]}]},
        {"apiVersion":"rbac.authorization.k8s.io/v1","kind":"RoleBinding","metadata":metadata("runtime"),
         "roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"Role","name":"runtime"},
         "subjects":[{"kind":"ServiceAccount","name":"runtime","namespace":NAMESPACE}]}]
    write(bundle/"platform.json",json.dumps({"apiVersion":"v1","kind":"List","items":objects}).encode())
    write(bundle/"bootstrap.json",canonical_json_bytes(bootstrap));write(bundle/"operator.token",tokens["operator"])
    write(bundle/"identity.pub",public);write(bundle/"task-config.json",canonical_json_bytes(config_values))
    write(bundle/"public.json",canonical_json_bytes({"owner":owner,"receiver_id":receiver,"definition_digest":definition_digest}))
    return bundle
