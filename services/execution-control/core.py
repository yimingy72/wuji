"""One trusted consumer for Task runtime and native framework coordination."""
from __future__ import annotations
import asyncio,base64,hashlib,hmac,json,secrets,time
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import UUID,uuid4,uuid5,NAMESPACE_URL
import httpx
from kubernetes import client,config
from kubernetes.client.exceptions import ApiException
from sqlalchemy import text
from wuji_task_runtime import TaskRuntimeConfig,ContainerResources,ExecutionPermit
from wuji_task_runtime.controller import TaskRuntimeController
from wuji_task_runtime.kubernetes_client import KubernetesPodClient
from wuji_task_runtime.manifest import verify_resource_ownership,verify_pod_ownership
from wuji_task_runtime.errors import TaskRuntimeError
from wuji_api.task_authorization import permits_url
from artifacts import ArtifactFileStore
from model_budget import TaskModelGateway,GatewayUnknown,GatewayRejected
from store import Store,dump,utcnow
from grants import issue,verify

def digest(value):return hashlib.sha256(dump(value).encode()).hexdigest()
def parse_time(value):return datetime.fromisoformat(value.replace("Z","+00:00")) if isinstance(value,str) else value
def identity(task):return {k:task[k] for k in ("tenant_id","project_id","task_id")} if "task_id" in task else {
    "tenant_id":task["tenant_id"],"project_id":task["project_id"],"task_id":task["id"]}

class Denied(Exception): pass

class Core:
    def __init__(self,cfg,credentials):
        self.cfg=cfg
        self.creds={p.name:p.read_text().strip() for p in Path(credentials).iterdir() if p.is_file()}
        self.store=Store(self.creds["execution_dsn"])
        self.artifacts=ArtifactFileStore(cfg["artifact_root"])
        self.http=httpx.AsyncClient(timeout=10,transport=httpx.AsyncHTTPTransport(retries=0),trust_env=False)
        self.gateway=TaskModelGateway(cfg["gateway_url"],self.creds["gateway_management_key"])
        configuration=client.Configuration()
        config.load_incluster_config(client_configuration=configuration)
        configuration.retries=0
        self.kube=client.CoreV1Api(client.ApiClient(configuration))
        self.pods=KubernetesPodClient(self.kube)
        self.controller=TaskRuntimeController(self.pods,self)
        self.instance=uuid4()
        self.busy=set()
        self.cairn_lock=asyncio.Lock()
        self.agent_locks={}
        self.tasks=set()
        self.service_config={k:v for k,v in cfg.items() if k in
            {"profile_id","namespace","agent_image","kali_image","fixture_origins","model_profile_version_id","model_base_url","control_url","public_control_url"}}
        self.service_config.update(max_agents=2,max_task_seconds=900,max_agent_turns=12,max_tool_calls=64,ready=False)

    async def native(self,method,path,body=None):
        try:
            r=await self.http.request(method,self.cfg["cairn_url"]+path,json=body,
                headers={"Authorization":"Bearer "+self.creds["cairn_token"]})
            data=r.json() if r.content else None
            return {"status_code":r.status_code,"data":data,"text":""}
        except (httpx.HTTPError,ValueError):
            return {"status_code":0,"data":None,"text":"native response unknown"}

    def current(self,task_id):
        ex=self.store.execution(task_id)
        rt=self.store.one("SELECT * FROM runtime_attempts WHERE task_id=:id ORDER BY attempt DESC LIMIT 1",{"id":task_id})
        if not ex or not rt or not self.store.permitted(task_id,ex["epoch"],rt["attempt"],provisioning=True):return None
        t=self.store.task(task_id)
        return ExecutionPermit(UUID(str(t["tenant_id"])),UUID(str(task_id)),rt["attempt"],ex["epoch"],
            t["creation_config"]["authorization_digest"],ex["execution_snapshot"]["config_digest"],
            UUID(str(ex["start_command_id"])),utcnow()+timedelta(seconds=15))

    def runtime_config(self,t,ex,attempt=1):
        runtime=ex["execution_snapshot"]["config"]
        deadline=min(900,max(1,int((parse_time(t["creation_config"]["authorization"]["valid_until"])-utcnow()).total_seconds())))
        return TaskRuntimeConfig(UUID(str(t["tenant_id"])),UUID(str(t["id"])),runtime["namespace"],attempt,ex["epoch"],
            t["creation_config"]["authorization_digest"],ex["execution_snapshot"]["config_digest"],
            runtime["agent_image"],runtime["kali_image"],ContainerResources("100m","128Mi","1","1Gi"),
            ContainerResources("100m","128Mi","1","512Mi"),"128Mi",deadline)

    def secret(self,rc,role):
        obj=self.kube.read_namespaced_secret(rc.resource_names[role+"_auth"],rc.namespace,_request_timeout=10)
        metadata=self.kube.api_client.sanitize_for_serialization(obj.metadata)
        verify_resource_ownership({"metadata":metadata},rc)
        return {k:base64.b64decode(v,validate=True).decode() for k,v in obj.data.items()}

    def ensure_resource(self,rc,kind,name,payload):
        reads={"Secret":self.kube.read_namespaced_secret,"ConfigMap":self.kube.read_namespaced_config_map,
               "PersistentVolumeClaim":self.kube.read_namespaced_persistent_volume_claim}
        creates={"Secret":self.kube.create_namespaced_secret,"ConfigMap":self.kube.create_namespaced_config_map,
                 "PersistentVolumeClaim":self.kube.create_namespaced_persistent_volume_claim}
        try:
            obj=reads[kind](name,rc.namespace,_request_timeout=10)
            verify_resource_ownership({"metadata":self.kube.api_client.sanitize_for_serialization(obj.metadata)},rc)
            return obj
        except ApiException as err:
            if err.status!=404:raise
        body={"apiVersion":"v1","kind":kind,"metadata":{"name":name,"namespace":rc.namespace,
              "labels":rc.identity_labels},**payload}
        return creates[kind](rc.namespace,body,_request_timeout=10)

    async def provision(self,ex):
        task_id=ex["task_id"];t=self.store.task(task_id)
        if t["state"]!="provisioning":return
        rc=self.runtime_config(t,ex)
        rt=self.store.one("SELECT * FROM runtime_attempts WHERE task_id=:id AND attempt=1",{"id":task_id})
        if not rt:
            self.store.execute("INSERT INTO runtime_attempts(id,tenant_id,project_id,task_id,execution_id,attempt,namespace,pod_name,config)"
                " VALUES(:id,:tenant_id,:project_id,:task_id,:ex,1,:namespace,:pod,CAST(:config AS jsonb))",
                {**identity(t),"id":uuid4(),"ex":ex["id"],"namespace":rc.namespace,"pod":rc.pod_name,"config":dump(asdict(rc))})
        else:
            values=rt["config"].copy()
            for k in ("tenant_id","task_id"):values[k]=UUID(values[k])
            for k in ("agent_resources","kali_resources"):values[k]=ContainerResources(**values[k])
            rc=TaskRuntimeConfig(**values)
        if not self.current(task_id):
            self.store.stop_requested(task_id,"authorization_or_model_unavailable");return
        runtime=ex["execution_snapshot"]["config"]
        expiry=min(parse_time(t["creation_config"]["authorization"]["valid_until"]).timestamp(),time.time()+900)
        lease=issue(self.creds["runtime_signing_key"],{"role":"runtime","task_id":str(task_id),
                    "epoch":ex["epoch"],"attempt":1},expiry)
        agent_creds={"backend_token":secrets.token_urlsafe(32),"lease_token":lease,"model_key":"sk-"+secrets.token_hex(32)}
        kali_creds={"router_token":secrets.token_urlsafe(32),"lease_token":lease}
        for role,values in (("agent",agent_creds),("kali",kali_creds)):
            self.ensure_resource(rc,"Secret",rc.resource_names[role+"_auth"],{"type":"Opaque","stringData":values})
        agent_creds=self.secret(rc,"agent")
        key=agent_creds["model_key"];key_hash=hashlib.sha256(key.encode()).hexdigest()
        alias="wuji_"+UUID(str(t["tenant_id"])).hex+"_"+UUID(t["creation_config"]["model"]["id"]).hex
        if ex["model_state"]!="ready":
            if ex["model_state"]=="pending":
                self.store.execute("UPDATE task_executions SET model_state='sent',key_hash=:hash,secret_name=:secret WHERE id=:id",
                    {"id":ex["id"],"hash":key_hash,"secret":rc.resource_names["agent_auth"]})
                try:
                    await self.gateway.generate(key=key,model_alias=alias,budget_usd=t["creation_config"]["budget_usd"],
                                                task_id=task_id,tenant_id=t["tenant_id"])
                except GatewayUnknown:
                    self.store.execute("UPDATE task_executions SET model_state='unknown' WHERE id=:id",{"id":ex["id"]})
                    return
                except GatewayRejected:
                    self.store.stop_requested(task_id,"model_key_rejected");return
            else:
                info=await self.gateway.lookup(key_hash)
                if not info:return
                if (info["models"]!=[alias] or info["metadata"]!={"wuji_task_id":str(task_id),"wuji_tenant_id":str(t["tenant_id"])}
                    or info["max_budget"]!=float(t["creation_config"]["budget_usd"])):
                    self.store.stop_requested(task_id,"model_key_conflict");return
            self.store.execute("UPDATE task_executions SET model_state='ready' WHERE id=:id",{"id":ex["id"]})
        binding={**{k:str(t[k]) for k in ("tenant_id","project_id")},"task_id":str(task_id),
                 "runtime_attempt":1,"execution_epoch":ex["epoch"],"control_url":self.cfg["control_url"],
                 "fixture_origins":runtime["fixture_origins"]}
        for role in ("agent","kali"):
            self.ensure_resource(rc,"ConfigMap",rc.resource_names[role+"_config"],{"data":{"binding.json":dump(binding)}})
            self.ensure_resource(rc,"PersistentVolumeClaim",rc.resource_names["agent_state" if role=="agent" else "kali_work"],
                {"spec":{"accessModes":["ReadWriteOnce"],"resources":{"requests":{"storage":"1Gi"}}}})
        observed=self.controller.ensure(rc)
        self.store.execute("UPDATE runtime_attempts SET state=:state,pod_uid=:uid,updated_at=clock_timestamp() WHERE task_id=:id AND attempt=1",
                           {"state":observed.state,"uid":observed.pod_uid,"id":task_id})
        if observed.state!="ready":return
        if ex["binding_state"]=="pending":
            self.store.execute("UPDATE task_executions SET binding_state='sent' WHERE id=:id",{"id":ex["id"]})
            creation=t["creation_config"]
            origin=dump({"entry_url":creation["actual_input"]["entry_url"],"identity":"anonymous","scope":creation["authorization"]})
            response=await self.native("POST","/projects",{"title":t["draft"]["name"],"origin":origin,
                "goal":creation["objective"]+"\n完成条件：\n"+"\n".join(creation["completion_criteria"]),
                "bootstrap_enabled":True,"hints":[{"content":creation["supplemental_hints"],"creator":"wuji.user"}] if creation["supplemental_hints"] else []})
            if response["status_code"]!=201:
                self.store.execute("UPDATE task_executions SET binding_state='unknown' WHERE id=:id",{"id":ex["id"]})
                return
            native_id=response["data"]["project"]["id"]
            self.store.execute("UPDATE task_executions SET native_project_id=:native,binding_state='bound' WHERE id=:id",
                               {"native":native_id,"id":ex["id"]})
        elif ex["binding_state"]!="bound":return
        with self.store.tx() as c:
            row=c.execute(text("SELECT state FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).scalar_one()
            if row!="provisioning":return
            c.execute(text("UPDATE task_executions SET state='running',updated_at=clock_timestamp() WHERE id=:id"),{"id":ex["id"]})
            self.store.event(c,task_id,"执行环境已就绪，开始探索",{"state":"running","egress_state":"fixture_only"})

    def worker_endpoints(self,task_id):
        ex=self.store.execution(task_id);t=self.store.task(task_id)
        rt=self.store.one("SELECT * FROM runtime_attempts WHERE task_id=:id ORDER BY attempt DESC LIMIT 1",{"id":task_id})
        if not rt or not rt["pod_uid"]:raise Denied("runtime unavailable")
        values=rt["config"].copy()
        for k in ("tenant_id","task_id"):values[k]=UUID(values[k])
        for k in ("agent_resources","kali_resources"):values[k]=ContainerResources(**values[k])
        rc=TaskRuntimeConfig(**values)
        pod=self.pods.read_pod(rc.namespace,rc.pod_name)
        if not pod or pod["metadata"]["uid"]!=rt["pod_uid"]:raise Denied("runtime identity changed")
        ip=pod.get("status",{}).get("podIP")
        if not ip:raise Denied("runtime address unknown")
        host="["+ip+"]" if ":" in ip else ip
        return rc,"http://"+host+":8001","http://"+host+":8003",self.secret(rc,"agent"),self.secret(rc,"kali")

    async def admit(self,body):
        ex=self.store.one("SELECT * FROM task_executions WHERE native_project_id=:id",{"id":body["native_project_id"]})
        if not ex:raise Denied("unknown exploration")
        task_id=ex["task_id"];phase=body["phase"];intent=body.get("intent_id")
        if phase not in {"bootstrap","reason","explore"} or (phase!="reason" and not intent):raise Denied("invalid phase")
        t=self.store.task(task_id)
        if not self.store.permitted(task_id,ex["epoch"],1):raise Denied("execution denied")
        graph=await self.native("GET","/projects/"+ex["native_project_id"])
        if graph["status_code"]!=200:raise Denied("graph unavailable")
        rc,agent_url,_,agent_secret,_=self.worker_endpoints(task_id)
        run_id=uuid4();deadline=min(utcnow()+timedelta(seconds=90),parse_time(t["creation_config"]["authorization"]["valid_until"]))
        creation=t["creation_config"];profile=creation["model"]["config"]
        model={"base_url":self.cfg["model_base_url"],"model_id":"wuji_"+UUID(str(t["tenant_id"])).hex+"_"+UUID(creation["model"]["id"]).hex,
               "context_window":profile["context_window"],"max_output_tokens":profile["max_output_tokens"],
               "timeout_seconds":profile["timeout_seconds"],"pricing":profile["pricing"]}
        assignment={**{k:str(v) for k,v in identity(t).items()},"agent_run_id":str(run_id),
          "execution_epoch":ex["epoch"],"runtime_attempt":1,"phase":phase,"intent_id":intent,
          "goal":creation["objective"],"objective":creation["objective"],"completion_criteria":creation["completion_criteria"],
          "origin":creation["actual_input"]["entry_url"],"supplemental_hints":creation["supplemental_hints"],
          "graph_snapshot":graph["data"]}
        with self.store.tx() as c:
            current=c.execute(text("SELECT state,execution_epoch FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
            if current["state"]!="running" or current["execution_epoch"]!=ex["epoch"]:raise Denied("execution changed")
            active=c.execute(text("SELECT count(*) FROM agent_runs WHERE task_id=:id AND"
                  " (state IN ('registered','running','unknown') OR result_state IN ('pending','unknown'))"),{"id":task_id}).scalar_one()
            if active>=2:raise Denied("worker capacity")
            duplicate=c.execute(text("SELECT 1 FROM agent_runs WHERE task_id=:id AND phase=:phase AND "
                  "COALESCE(intent_id,'')=COALESCE(:intent,'') AND (state IN ('registered','running','unknown')"
                  " OR result_state IN ('pending','unknown'))"),{"id":task_id,"phase":phase,"intent":intent}).first()
            if duplicate:raise Denied("run requires reconciliation")
            c.execute(text("INSERT INTO agent_runs(id,tenant_id,project_id,task_id,execution_id,runtime_attempt,execution_epoch,"
                "phase,intent_id,worker_profile_id,worker_name,state,assignment) VALUES(:id,:tenant_id,:project_id,:task_id,"
                ":execution,1,:epoch,:phase,:intent,:profile,:worker,'running',CAST(:assignment AS jsonb))"),
                {**identity(t),"id":run_id,"execution":ex["id"],"epoch":ex["epoch"],"phase":phase,"intent":intent,
                 "profile":body["worker_profile_id"],"worker":"run-"+str(run_id),"assignment":dump(assignment)})
            self.store.event(c,task_id,"Agent已获准执行")
        token=issue(self.creds["runtime_signing_key"],{"role":"agent","task_id":str(task_id),"run_id":str(run_id),
                    "epoch":ex["epoch"],"attempt":1},deadline.timestamp())
        tools=["task_read","graph_read","workspace_read","workspace_list"]
        if phase!="reason":tools+=["fixture_http","workspace_write","fixture_wait","tool_wait","tool_cancel"]
        return {"agent_run_id":str(run_id),"worker_name":"run-"+str(run_id),"task_id":str(task_id),
                "tenant_id":str(t["tenant_id"]),"project_id":str(t["project_id"]),"native_project_id":ex["native_project_id"],
                "assignment":assignment,"model":model,"tool_names":tools,"deadline":deadline.isoformat(),
                "operation_id":str(run_id),"tool_token":token,"agent_url":agent_url,"backend_token":agent_secret["backend_token"]}

    def agent_context(self,token,run_id=None):
        claims=verify(self.creds["runtime_signing_key"],token,"agent")
        if run_id and claims["run_id"]!=str(run_id):raise Denied("run identity")
        row=self.store.one("SELECT * FROM agent_runs WHERE id=:id AND task_id=:task",{"id":claims["run_id"],"task":claims["task_id"]})
        if not row:raise Denied("run unavailable")
        return claims,row

    async def create_call(self,claims,run,body):
        task_id=run["task_id"];tool=body["tool"];args=body.get("args",{});request_id=body["request_id"]
        if tool not in {"fixture_http","workspace_read","workspace_write","workspace_list","fixture_wait"}:raise Denied("tool not registered")
        if run["phase"]=="reason" and tool not in {"workspace_read","workspace_list"}:raise Denied("reason cannot actively collect")
        if not isinstance(args,dict) or len(dump(args).encode())>1_060_000 or not isinstance(request_id,str) or len(request_id)>200:raise Denied("tool input")
        if not self.store.permitted(task_id,claims["epoch"],claims["attempt"]):raise Denied("execution denied")
        task=self.store.task(task_id)
        if tool=="fixture_http":
            url=args.get("url")
            if not isinstance(url,str) or not permits_url(task["creation_config"]["authorization"],url):raise Denied("scope denied")
            from urllib.parse import urlsplit
            u=urlsplit(url)
            if (u.scheme+"://"+u.netloc) not in self.cfg["fixture_origins"] or u.username or u.password:raise Denied("fixture destination denied")
        call_id=uuid5(UUID(str(run["id"])),request_id)
        request_hash=digest({"tool":tool,"args":args})
        with self.store.tx() as c:
            current=c.execute(text("SELECT state,execution_epoch FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
            if current["state"]!="running" or current["execution_epoch"]!=claims["epoch"]:raise Denied("execution changed")
            old=c.execute(text("SELECT * FROM tool_calls WHERE id=:id"),{"id":call_id}).mappings().one_or_none()
            if old:
                if old["request_digest"]!=request_hash:raise Denied("tool request conflict")
                return self.call_public(dict(old))
            admitted=c.execute(text("SELECT state,execution_epoch,runtime_attempt FROM agent_runs WHERE id=:run AND task_id=:task FOR UPDATE"),
                               {"run":run["id"],"task":task_id}).mappings().one_or_none()
            if (not admitted or admitted["state"]!="running" or admitted["execution_epoch"]!=claims["epoch"]
                or admitted["runtime_attempt"]!=claims["attempt"] or claims["attempt"]!=1):
                raise Denied("agent execution changed")
            total=c.execute(text("SELECT count(*) FROM tool_calls WHERE task_id=:id"),{"id":task_id}).scalar_one()
            if total>=64:raise Denied("tool quota exceeded")
            c.execute(text("INSERT INTO tool_calls(id,tenant_id,project_id,task_id,agent_run_id,request_id,request_digest,"
                 "runtime_attempt,execution_epoch,tool,args) VALUES(:id,:tenant_id,:project_id,:task_id,:run,:request,"
                 ":digest,1,:epoch,:tool,CAST(:args AS jsonb))"),
                 {**identity(task),"id":call_id,"run":run["id"],"request":request_id,"digest":request_hash,
                  "epoch":claims["epoch"],"tool":tool,"args":dump(args)})
            payload={"operation_id":str(call_id),"agent_run_id":str(run["id"]),"task_id":str(task_id),
                     "execution_epoch":claims["epoch"],"runtime_attempt":1,"tool":tool,"args":args,
                     "expires_at":min(utcnow()+timedelta(seconds=60),parse_time(task["creation_config"]["authorization"]["valid_until"])).isoformat()}
            c.execute(text("INSERT INTO tool_attempts(id,tenant_id,project_id,task_id,tool_call_id,request,state)"
                " VALUES(:id,:tenant_id,:project_id,:task_id,:call,CAST(:request AS jsonb),'sent')"),
                {**identity(task),"id":uuid4(),"call":call_id,"request":dump(payload)})
            self.store.event(c,task_id,"工具调用已登记",{"active_calls":self._active_count(c,task_id)})
        try:
            _,_,kali_url,_,credentials=self.worker_endpoints(task_id)
            r=await self.http.put(kali_url+"/calls/"+str(call_id),json=payload,
                                headers={"Authorization":"Bearer "+credentials["router_token"]})
            if r.status_code!=200:raise Denied("tool acceptance unknown")
            self.store.execute("UPDATE tool_calls SET state='running',receipt=CAST(:receipt AS jsonb),updated_at=clock_timestamp() WHERE id=:id",
                               {"id":call_id,"receipt":dump(r.json())})
        except (httpx.HTTPError,Denied,ValueError):
            with self.store.tx() as c:
                c.execute(text("SELECT id FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id})
                c.execute(text("UPDATE tool_calls SET state='unknown',updated_at=clock_timestamp() WHERE id=:id AND state<>'exited'"),{"id":call_id})
                c.execute(text("UPDATE tool_attempts SET state='unknown',updated_at=clock_timestamp() WHERE tool_call_id=:id AND state<>'exited'"),{"id":call_id})
                unknown=c.execute(text("SELECT count(*) FROM tool_calls WHERE task_id=:task AND state='unknown'"),{"task":task_id}).scalar_one()
                self.store.event(c,task_id,"工具启动结果待核对",{"active_calls":self._active_count(c,task_id),"unknown_calls":unknown})
        return self.call_public(self.store.one("SELECT * FROM tool_calls WHERE id=:id",{"id":call_id}))

    @staticmethod
    def _active_count(c,task_id):
        return c.execute(text("SELECT count(*) FROM tool_calls WHERE task_id=:id AND state IN ('registered','running')"),
                         {"id":task_id}).scalar_one()

    @staticmethod
    def call_public(call):
        return {k:call[k] for k in ("id","state","tool","result","cancel_requested")}

    async def poll_call(self,call):
        if call["state"]=="exited":return self.call_public(call)
        try:
            _,_,url,_,creds=self.worker_endpoints(call["task_id"])
            response=await self.http.get(url+"/calls/"+str(call["id"]),headers={"Authorization":"Bearer "+creds["router_token"]})
            if response.status_code!=200:return self.call_public(call)
            receipt=response.json()
        except (httpx.HTTPError,Denied):return self.call_public(call)
        if receipt.get("state")!="exited":return self.call_public(call)
        result=receipt.get("result") or {"ok":False,"error":"result_missing"}
        if result.get("ok") is True and call["tool"] in {"fixture_http","workspace_write","workspace_read"}:
            data=dump({"tool_call_id":str(call["id"]),"tool":call["tool"],"args":call["args"],"result":result}).encode()
            artifact_id=uuid5(UUID(str(call["id"])),"observation")
            if len(data)<=1_048_576:
                info=self.artifacts.write(call["task_id"],artifact_id,data,"application/json")
                self.store.execute("INSERT INTO task_artifacts(id,tenant_id,project_id,task_id,tool_call_id,kind,name,mime,size,sha256,storage_key)"
                   " VALUES(:id,:tenant_id,:project_id,:task_id,:call,'observation',:name,'application/json',:size,:sha,:key) ON CONFLICT(id) DO NOTHING",
                   {**identity(call),"id":artifact_id,"call":call["id"],"name":call["tool"]+" observation",
                    "size":info["size"],"sha":info["sha256"],"key":info["storage_key"]})
                result={**result,"artifact_id":str(artifact_id)}
            for field in ("body","content"):
                if isinstance(result.get(field),str) and len(result[field])>8192:
                    result[field]=result[field][:8192];result["truncated"]=True
        with self.store.tx() as c:
            row=c.execute(text("SELECT state FROM tool_calls WHERE id=:id FOR UPDATE"),{"id":call["id"]}).scalar_one()
            if row=="exited":return self.call_public(self.store.one("SELECT * FROM tool_calls WHERE id=:id",{"id":call["id"]}))
            c.execute(text("UPDATE tool_calls SET state='exited',result=CAST(:result AS jsonb),receipt=CAST(:receipt AS jsonb),"
                           "updated_at=clock_timestamp() WHERE id=:id"),{"id":call["id"],"result":dump(result),"receipt":dump(receipt)})
            c.execute(text("UPDATE tool_attempts SET state='exited',receipt=CAST(:receipt AS jsonb),updated_at=clock_timestamp() WHERE tool_call_id=:id"),
                      {"id":call["id"],"receipt":dump(receipt)})
            unknown=c.execute(text("SELECT count(*) FROM tool_calls WHERE task_id=:task AND state='unknown'"),{"task":call["task_id"]}).scalar_one()
            self.store.event(c,call["task_id"],"工具执行已结束",{"active_calls":self._active_count(c,call["task_id"]),"unknown_calls":unknown})
        return self.call_public(self.store.one("SELECT * FROM tool_calls WHERE id=:id",{"id":call["id"]}))

    async def cancel_call(self,call):
        self.store.execute("UPDATE tool_calls SET cancel_requested=true WHERE id=:id",{"id":call["id"]})
        try:
            _,_,url,_,creds=self.worker_endpoints(call["task_id"])
            await self.http.post(url+"/calls/"+str(call["id"])+"/cancel",headers={"Authorization":"Bearer "+creds["router_token"]})
        except (Denied,httpx.HTTPError):pass
        return await self.poll_call(call)

    def evidence_complete(self,task_id):
        calls=self.store.rows("SELECT * FROM tool_calls WHERE task_id=:id AND state='exited'",{"id":task_id})
        http=any(c["tool"]=="fixture_http" and (c["result"] or {}).get("ok") is True
                 and "WUJI_HTTP_FIXTURE_V1" in (c["result"] or {}).get("body","")
                 and (c["result"] or {}).get("artifact_id") for c in calls)
        writes=[c for c in calls if c["tool"]=="workspace_write" and (c["result"] or {}).get("ok") is True]
        reads=[c for c in calls if c["tool"]=="workspace_read" and (c["result"] or {}).get("ok") is True]
        shared=any(w["agent_run_id"]!=r["agent_run_id"] and w["args"].get("path")==r["args"].get("path")
            and w["args"].get("content")==r["result"].get("content")
            and str(w["args"].get("path","")).startswith("/workspace/shared/")
            and w["result"].get("artifact_id") and r["result"].get("artifact_id")
            for w in writes for r in reads)
        return bool(http and shared)

    async def graph_snapshot(self,ex):
        if not ex.get("native_project_id"):return
        response=await self.native("GET","/projects/"+ex["native_project_id"])
        if response["status_code"]!=200:return
        value=response["data"];hashed=digest(value)
        old=self.store.one("SELECT digest FROM task_graph_snapshots WHERE task_id=:id ORDER BY created_at DESC LIMIT 1",{"id":ex["task_id"]})
        if old and old["digest"]==hashed:return
        with self.store.tx() as c:
            c.execute(text("INSERT INTO task_graph_snapshots(id,tenant_id,project_id,task_id,native_project_id,graph,digest)"
                " VALUES(:id,:tenant_id,:project_id,:task_id,:native,CAST(:graph AS jsonb),:digest)"),
                {**identity(ex),"id":uuid4(),"native":ex["native_project_id"],"graph":dump(value),"digest":hashed})
            self.store.event(c,ex["task_id"],"黑板观察已更新")

    async def core_action(self,native_id,action,args):
        if action not in {"create_intent","heartbeat","release","claim_reason","reason_heartbeat","release_reason","conclude","complete","stop"}:
            raise Denied("native action denied")
        ex=self.store.one("SELECT * FROM task_executions WHERE native_project_id=:id",{"id":native_id})
        if not ex:raise Denied("unbound graph")
        task_id=ex["task_id"];run=None
        actor_index={"create_intent":2,"heartbeat":1,"release":1,"claim_reason":0,"reason_heartbeat":0,
                     "release_reason":0,"conclude":1,"complete":2}.get(action)
        actor=args[actor_index] if actor_index is not None and len(args)>actor_index else ""
        if isinstance(actor,str) and actor.startswith("run-"):
            run=self.store.one("SELECT * FROM agent_runs WHERE worker_name=:worker AND task_id=:task",
                              {"worker":actor,"task":task_id})
            if not run:raise Denied("native worker identity")
        elif not (action=="create_intent" and actor=="dispatcher.bootstrap") and action!="stop":
            raise Denied("unknown native worker")
        if action not in {"release","release_reason","stop"} and not self.store.permitted(task_id,ex["epoch"],1):
            return {"status_code":403,"data":None,"text":"execution permission closed"}
        if action in {"conclude","complete","create_intent"} and run and run["output"] is None:
            raise Denied("persisted result required")
        if action=="complete" and not self.evidence_complete(task_id):
            return {"status_code":409,"data":None,"text":"fixture evidence incomplete"}
        if run and action in {"heartbeat","release","conclude"} and args[0]!=run["intent_id"]:
            raise Denied("native intent identity")
        prefix="/projects/"+native_id
        routes={
          "create_intent":lambda:("POST",prefix+"/intents",{"from":args[0],"description":args[1],"creator":args[2],"worker":None}),
          "heartbeat":lambda:("POST",prefix+"/intents/"+args[0]+"/heartbeat",{"worker":args[1]}),
          "release":lambda:("POST",prefix+"/intents/"+args[0]+"/release",{"worker":args[1]}),
          "claim_reason":lambda:("POST",prefix+"/reason/claim",{"worker":args[0],"trigger":args[1]}),
          "reason_heartbeat":lambda:("POST",prefix+"/reason/heartbeat",{"worker":args[0]}),
          "release_reason":lambda:("POST",prefix+"/reason/release",{"worker":args[0]}),
          "conclude":lambda:("POST",prefix+"/intents/"+args[0]+"/conclude",{"worker":args[1],"description":args[2]}),
          "complete":lambda:("POST",prefix+"/complete",{"from":args[0],"description":args[1],"worker":args[2]}),
          "stop":lambda:("PUT",prefix+"/status",{"status":"stopped"}),
        }
        method,url,body=routes[action]()
        if action in {"heartbeat","release","claim_reason","reason_heartbeat","release_reason","stop"}:
            return await self.native(method,url,body)
        operation_id=uuid5(UUID(str(ex["id"])),action+":"+digest(args))
        async with self.cairn_lock:
            old=self.store.one("SELECT * FROM core_operations WHERE id=:id",{"id":operation_id})
            if old:
                if old["state"] in {"succeeded","rejected"}:return old["response"]
                return await self.reconcile_native(old,ex,action,args)
            with self.store.tx() as c:
                task=c.execute(text("SELECT state,execution_epoch FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
                if task["state"]!="running" or task["execution_epoch"]!=ex["epoch"]:raise Denied("execution changed")
                c.execute(text("INSERT INTO core_operations(id,tenant_id,project_id,task_id,agent_run_id,kind,request_digest,request,state)"
                    " VALUES(:id,:tenant_id,:project_id,:task_id,:run,:kind,:digest,CAST(:request AS jsonb),'sent')"),
                    {**identity(ex),"id":operation_id,"run":run["id"] if run else None,"kind":action,
                     "digest":digest(args),"request":dump({"args":args,"method":method,"path":url,"body":body})})
            response=await self.native(method,url,body)
            status="succeeded" if 200<=response["status_code"]<300 else "rejected" if response["status_code"] in {400,403,404,409,422} else "unknown"
            self.store.execute("UPDATE core_operations SET state=:state,response=CAST(:response AS jsonb),updated_at=clock_timestamp() WHERE id=:id",
                               {"id":operation_id,"state":status,"response":dump(response)})
            if status=="unknown":
                if run:self.store.execute("UPDATE agent_runs SET result_state='unknown' WHERE id=:id",{"id":run["id"]})
                self.store.stop_requested(task_id,"result_sync_unknown")
            if status=="succeeded":
                await self.graph_snapshot(ex)
                if action=="complete":self.store.stop_requested(task_id,"exploration_completed")
            return response

    async def reconcile_native(self,op,ex,action,args):
        response=await self.native("GET","/projects/"+ex["native_project_id"])
        if response["status_code"]==200 and action in {"conclude","complete"}:
            graph=response["data"];result=None
            if action=="conclude":
                intent=next((i for i in graph["intents"] if i["id"]==args[0] and i.get("to")),None)
                fact=next((f for f in graph["facts"] if intent and f["id"]==intent["to"] and f["description"]==args[2]),None)
                if fact:result={"fact":fact,"intent":intent}
            elif graph["project"]["status"]=="completed":
                result=next((i for i in graph["intents"] if i.get("to")=="goal" and i.get("from")==args[0]
                             and i.get("description")==args[1]),None)
            if result:
                value={"status_code":200,"data":result,"text":""}
                self.store.execute("UPDATE core_operations SET state='succeeded',response=CAST(:response AS jsonb) WHERE id=:id",
                                   {"id":op["id"],"response":dump(value)})
                return value
        return {"status_code":0,"data":None,"text":"native operation requires reconciliation"}

    def save_output(self,run_id,body):
        output=body.get("output")
        if not isinstance(output,str) or len(output.encode())>4_194_304:raise Denied("invalid run output")
        receipt=body.get("receipt") or {}
        if receipt.get("id")!=str(run_id) or receipt.get("state")!="exited":
            raise Denied("output requires the matching exited process receipt")
        old=self.store.one("SELECT * FROM agent_runs WHERE id=:id",{"id":run_id})
        if not old:raise Denied("run not found")
        if old["output"] is not None:
            if old["output"]!=output:raise Denied("result changed")
            return {"saved":True}
        self.store.execute("UPDATE agent_runs SET output=:output,receipt=CAST(:receipt AS jsonb),"
            "updated_at=clock_timestamp() WHERE id=:id AND output IS NULL",
            {"id":run_id,"output":output,"receipt":dump(body.get("receipt") or {})})
        return {"saved":True}

    def finish_run(self,run_id,outcome):
        run=self.store.one("SELECT * FROM agent_runs WHERE id=:id",{"id":run_id})
        if not run:raise Denied("unknown run")
        if run["outcome"] is not None:
            return {"state":run["state"],"result_state":run["result_state"]}
        pending=self.store.one("SELECT 1 FROM core_operations WHERE agent_run_id=:id AND state IN ('sent','unknown')",{"id":run_id})
        receipt=run.get("receipt") or {}
        exited=receipt.get("state")=="exited" and receipt.get("id")==str(run_id)
        not_started=outcome=="rejected" and run["output"] is None and not receipt
        state="exited" if exited else "not_started" if not_started else "unknown"
        result_state="unknown" if pending or outcome=="unknown" or (outcome=="success" and run["output"] is None) else "synced" if outcome=="success" else "rejected"
        with self.store.tx() as c:
            c.execute(text("UPDATE agent_runs SET state=:state,result_state=:result,outcome=:outcome,updated_at=clock_timestamp() WHERE id=:id"),
                      {"id":run_id,"state":state,"result":result_state,"outcome":outcome})
            self.store.event(c,run["task_id"],"Agent运行已核对")
        if state=="unknown" or outcome not in {"success","cancelled"} or pending:self.store.stop_requested(run["task_id"],"agent_result_incomplete")
        return {"state":state,"result_state":result_state}

    async def stop(self,ex,task):
        task_id=task["id"]
        model_blocked=not ex.get("key_hash") and ex["model_state"]=="pending"
        if ex.get("key_hash"):
            model_state="blocked" if ex["model_state"]=="blocked" else "block_unknown"
            if model_state!="blocked":
                try:
                    response=await self.gateway.block(ex["key_hash"])
                    model_state="blocked" if response.get("blocked") is True else "block_unknown"
                except GatewayUnknown: model_state="block_unknown"
                except GatewayRejected: model_state="block_rejected"
                if model_state!="blocked":
                    try:
                        info=await self.gateway.lookup(ex["key_hash"])
                        if info and info.get("blocked") is True:model_state="blocked"
                    except (GatewayUnknown,GatewayRejected):pass
            self.store.execute("UPDATE task_executions SET model_state=:state WHERE id=:id",{"id":ex["id"],"state":model_state})
            model_blocked=model_state=="blocked"
        rt=self.store.one("SELECT * FROM runtime_attempts WHERE task_id=:id ORDER BY attempt DESC LIMIT 1",{"id":task_id})
        rc=None;pod_absent=False
        if rt:
            values=rt["config"].copy()
            for k in ("tenant_id","task_id"):values[k]=UUID(values[k])
            for k in ("agent_resources","kali_resources"):values[k]=ContainerResources(**values[k])
            rc=TaskRuntimeConfig(**values)
            if not rt["pod_uid"]:
                try:
                    pod=self.pods.read_pod(rc.namespace,rc.pod_name)
                    if pod is None:pod_absent=True
                    else:
                        verify_pod_ownership(pod,rc)
                        uid=pod["metadata"].get("uid")
                        if not isinstance(uid,str) or not uid:raise Denied("runtime identity unknown")
                        rt["pod_uid"]=uid
                        self.store.execute("UPDATE runtime_attempts SET pod_uid=:uid WHERE id=:id",{"id":rt["id"],"uid":uid})
                except (TaskRuntimeError,ApiException,Denied):
                    self.store.execute("UPDATE runtime_attempts SET state='unknown' WHERE id=:id",{"id":rt["id"]})
                    with self.store.tx() as c:self.store.event(c,task_id,"执行环境仍待核对",{"state":"reconciling","cleanup_state":"unknown"})
                    return
        calls=self.store.rows("SELECT * FROM tool_calls WHERE task_id=:id AND state<>'exited'",{"id":task_id})
        for call in calls:await self.cancel_call(call)
        runs=self.store.rows("SELECT * FROM agent_runs WHERE task_id=:id AND state NOT IN ('exited','not_started')",{"id":task_id})
        for run in runs:
            try:
                _,url,_,secret,_=self.worker_endpoints(task_id)
                await self.http.post(url+"/runs/"+str(run["id"])+"/cancel",headers={"Authorization":"Bearer "+secret["backend_token"]})
                r=await self.http.get(url+"/runs/"+str(run["id"]),headers={"Authorization":"Bearer "+secret["backend_token"]})
                if r.status_code==200 and r.json().get("state")=="exited" and r.json().get("id")==str(run["id"]):
                    self.store.execute("UPDATE agent_runs SET state='exited',receipt=CAST(:receipt AS jsonb),"
                        "result_state=CASE WHEN result_state='pending' THEN 'rejected' ELSE result_state END,"
                        "outcome=COALESCE(outcome,'cancelled'),updated_at=clock_timestamp() WHERE id=:id",
                        {"id":run["id"],"receipt":dump(r.json())})
            except (Denied,httpx.HTTPError):pass
        if ex.get("native_project_id"):await self.native("PUT","/projects/"+ex["native_project_id"]+"/status",{"status":"stopped"})
        pending=self.store.one("SELECT 1 FROM agent_runs WHERE task_id=:id AND state NOT IN ('exited','not_started') UNION ALL "
            "SELECT 1 FROM tool_calls WHERE task_id=:id AND state<>'exited' LIMIT 1",{"id":task_id})
        if pending:
            if (utcnow()-task["updated_at"]).total_seconds()>20 and task["state"]!="reconciling":
                with self.store.tx() as c:self.store.event(c,task_id,"执行停止尚待核对",{"state":"reconciling","unknown_calls":len(calls)})
            return
        cleanup="not_required"
        if rt and rt["pod_uid"]:
            observed=self.controller.stop(rc,rt["pod_uid"])
            self.store.execute("UPDATE runtime_attempts SET state=:state WHERE id=:id",{"id":rt["id"],"state":observed.state})
            cleanup="completed" if observed.state=="stopped" else "pending"
        elif rt and pod_absent:
            self.store.execute("UPDATE runtime_attempts SET state='stopped' WHERE id=:id",{"id":rt["id"]})
        if not model_blocked:
            with self.store.tx() as c:self.store.event(c,task_id,"模型凭据阻断仍待核对",{"state":"reconciling","egress_state":"unknown","cleanup_state":cleanup})
            return
        met=self.evidence_complete(task_id)
        artifacts=self.store.rows("SELECT id FROM task_artifacts WHERE task_id=:id ORDER BY created_at",{"id":task_id})
        result={"goal_status":"unknown","summary":"已核对夹具HTTP观察与共享文件交接。" if met else "任务已停止，保留已取得的观察。",
                "limitations":["本次使用合成模型与固定夹具，不代表真实渗透能力或任意自定义目标已完成。"],
                "artifact_ids":[str(a["id"]) for a in artifacts]}
        if cleanup=="pending":return
        pending_results=self.store.rows("SELECT * FROM core_operations WHERE task_id=:id AND state IN ('sent','unknown')",
                                        {"id":task_id})
        for operation in pending_results:
            if operation["kind"] in {"conclude","complete"}:
                await self.reconcile_native(operation,ex,operation["kind"],operation["request"]["args"])
        if self.store.one("SELECT 1 FROM core_operations WHERE task_id=:id AND state IN ('sent','unknown')",{"id":task_id}):
            result["limitations"].append("部分黑板写回尚待核对；原始结果已保留，没有重新执行探索。")
        await self.graph_snapshot(ex)
        with self.store.tx() as c:
            current=c.execute(text("SELECT state,stop_reason,execution_epoch FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
            if current["state"] in {"completed","cancelled"}:return
            if current["state"] not in {"cancelling","completing","reconciling"}:raise Denied("stop state changed")
            if current["stop_reason"]!="exploration_completed":result["limitations"].append("结束原因："+str(current["stop_reason"]))
            c.execute(text("UPDATE task_executions SET state='stopped',result=CAST(:result AS jsonb),updated_at=clock_timestamp() WHERE id=:id"),
                      {"id":ex["id"],"result":dump(result)})
            final="cancelled" if current["stop_reason"]=="user_cancelled" or current["state"]=="cancelling" else "completed"
            self.store.event(c,task_id,"任务执行已停止并完成核对",{"state":final,"active_calls":0,"unknown_calls":0,
                  "egress_state":"revoked","cleanup_state":cleanup,"assessment_outcome":"complete" if met else "partial"})

    async def tick(self):
        ready=False
        try:
            native=await self.native("GET","/settings")
            gateway=await self.http.get(self.cfg["gateway_url"]+"/health/readiness")
            ready=native["status_code"]==200 and gateway.status_code==200
        except httpx.HTTPError:pass
        self.service_config["ready"]=ready
        self.store.execute("INSERT INTO execution_services(id,instance_id,config,heartbeat_at) VALUES('core',:id,CAST(:config AS jsonb),clock_timestamp())"
            " ON CONFLICT(id) DO UPDATE SET instance_id=excluded.instance_id,config=excluded.config,heartbeat_at=excluded.heartbeat_at",
            {"id":self.instance,"config":dump(self.service_config)})
        for ex in self.store.rows("SELECT * FROM task_executions WHERE state<>'stopped' ORDER BY created_at"):
            task=self.store.task(ex["task_id"])
            try:
                if ex["service_instance_id"]!=self.instance:
                    self.store.stop_requested(task["id"],"controller_restarted")
                    self.store.execute("UPDATE task_executions SET service_instance_id=:instance WHERE id=:id",
                                       {"id":ex["id"],"instance":self.instance})
                    task=self.store.task(task["id"])
                if (utcnow()-ex["created_at"]).total_seconds()>900:self.store.stop_requested(task["id"],"runtime_deadline")
                task=self.store.task(task["id"])
                if task["state"]=="provisioning":await self.provision(ex)
                elif task["state"]=="running":
                    if not self.current(task["id"]):self.store.stop_requested(task["id"],"authorization_or_model_unavailable")
                    for call in self.store.rows("SELECT * FROM tool_calls WHERE task_id=:id AND state<>'exited'",{"id":task["id"]}):
                        await self.poll_call(call)
                elif task["state"] in {"cancelling","completing","reconciling"}:await self.stop(ex,task)
            except Exception as error:
                self.store.execute("UPDATE task_executions SET failure_reason=:reason,updated_at=clock_timestamp() WHERE id=:id",
                                   {"id":ex["id"],"reason":type(error).__name__})
        for ex in self.store.rows("SELECT id,key_hash FROM task_executions WHERE key_hash IS NOT NULL"):
            try:
                info=await self.gateway.lookup(ex["key_hash"])
                if info is not None:self.store.execute("UPDATE task_executions SET model_spend=:spend,cost_state=:state WHERE id=:id",
                    {"id":ex["id"],"spend":info["spend"],"state":"reported" if info["spend"] is not None else "unknown"})
            except (GatewayUnknown,GatewayRejected):pass
