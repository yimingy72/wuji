"""Private control API. Browser traffic stays behind the authenticated Platform API."""
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from uuid import UUID
import asyncio,json,os,hmac
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,Response
import uvicorn
from core import Core,Denied
from store import utcnow
from grants import verify

@asynccontextmanager
async def lifespan(app):
    config=json.loads(Path(os.environ["WUJI_CORE_CONFIG"]).read_text())
    core=Core(config,os.environ["WUJI_CORE_CREDENTIALS"]);app.state.core=core
    stop=asyncio.Event()
    async def consume():
        while not stop.is_set():
            try:await core.tick()
            except Exception as error:
                # No upstream body, configuration or credentials in ordinary logs.
                print(json.dumps({"component":"execution-control","error":type(error).__name__}),flush=True)
            try:await asyncio.wait_for(stop.wait(),timeout=1)
            except TimeoutError:pass
    worker=asyncio.create_task(consume())
    try:yield
    finally:
        stop.set()
        await worker
        core.store.execute("UPDATE execution_services SET config=jsonb_set(config,'{ready}','false'::jsonb) WHERE id='core' AND instance_id=:id",
                           {"id":core.instance})
        await core.http.aclose();await core.gateway.close();core.store.engine.dispose()

app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
def token(request):return request.headers.get("authorization","").removeprefix("Bearer ")
def core(request):return request.app.state.core
def service(request):
    value=core(request)
    if not hmac.compare_digest(token(request),value.creds["service_token"]):raise HTTPException(403,"service identity required")
    return value
async def body(request):
    data=await request.body()
    if len(data)>4_300_000:raise HTTPException(413,"request too large")
    return json.loads(data)

@app.exception_handler(Denied)
async def denied(request,error):return JSONResponse({"error":"execution_denied"},status_code=409)
@app.exception_handler(ValueError)
async def invalid(request,error):return JSONResponse({"error":"invalid_request"},status_code=422)

@app.get("/health")
async def health():return {"status":"live"}

@app.get("/internal/v1/runtime/lease")
async def lease(request:Request,task_id:UUID,runtime_attempt:int,execution_epoch:int):
    c=core(request)
    claims=verify(c.creds["runtime_signing_key"],token(request),"runtime")
    allowed=(claims["task_id"]==str(task_id) and claims["epoch"]==execution_epoch and claims["attempt"]==runtime_attempt
             and c.store.permitted(task_id,execution_epoch,runtime_attempt,provisioning=True))
    return {"allowed":bool(allowed),"expires_at":(utcnow()+timedelta(seconds=15)).isoformat()}

@app.get("/internal/v1/dispatch/projects")
async def projects(request:Request):
    c=service(request)
    rows=c.store.rows("SELECT ex.* FROM task_executions ex JOIN tasks t ON t.id=ex.task_id "
        "WHERE t.state='running' AND ex.binding_state='bound' AND ex.state='running'")
    return {"items":[{k:str(row[k]) for k in ("native_project_id","task_id","tenant_id","project_id")}
                     for row in rows if c.store.permitted(row["task_id"],row["epoch"],1)]}

@app.post("/internal/v1/dispatch/admit")
async def admit(request:Request):return await service(request).admit(await body(request))

@app.get("/internal/v1/dispatch/runs/{run_id}")
async def get_run(request:Request,run_id:UUID):
    c=service(request);run=c.store.one("SELECT * FROM agent_runs WHERE id=:id",{"id":run_id})
    if not run or not c.store.permitted(run["task_id"],run["execution_epoch"],run["runtime_attempt"]):raise Denied("run is not admitted")
    return {"agent_run_id":str(run_id),"state":run["state"],"task_id":str(run["task_id"])}

@app.post("/internal/v1/dispatch/runs/{run_id}/output")
async def run_output(request:Request,run_id:UUID):return service(request).save_output(run_id,await body(request))

@app.post("/internal/v1/dispatch/runs/{run_id}/finish")
async def run_finish(request:Request,run_id:UUID):
    value=await body(request)
    if value.get("outcome") not in {"success","failed","cancelled","rejected","unhealthy","unknown"}:raise Denied("outcome invalid")
    return service(request).finish_run(run_id,value["outcome"])

@app.post("/internal/v1/cairn/{project}/{action}")
async def cairn_action(request:Request,project:str,action:str):
    c=service(request);value=await body(request)
    if not isinstance(value.get("args"),list):raise Denied("invalid native input")
    return await c.core_action(project,action,value["args"])

@app.post("/internal/v1/agent-runs/{run_id}/tool-calls")
async def tool_create(request:Request,run_id:UUID):
    c=core(request);claims,run=c.agent_context(token(request),run_id)
    return await c.create_call(claims,run,await body(request))

@app.get("/internal/v1/tool-calls/{call_id}")
async def tool_read(request:Request,call_id:UUID):
    c=core(request);claims,run=c.agent_context(token(request))
    call=c.store.one("SELECT * FROM tool_calls WHERE id=:id AND agent_run_id=:run AND task_id=:task",
                    {"id":call_id,"run":run["id"],"task":run["task_id"]})
    if not call:raise HTTPException(404,"call not found")
    return await c.poll_call(call)

@app.post("/internal/v1/tool-calls/{call_id}/cancel")
async def tool_cancel(request:Request,call_id:UUID):
    c=core(request);claims,run=c.agent_context(token(request))
    call=c.store.one("SELECT * FROM tool_calls WHERE id=:id AND agent_run_id=:run AND task_id=:task",
                    {"id":call_id,"run":run["id"],"task":run["task_id"]})
    if not call:raise HTTPException(404,"call not found")
    return await c.cancel_call(call)

@app.get("/internal/v1/artifacts/{artifact_id}/content")
async def artifact(request:Request,artifact_id:UUID):
    c=core(request);claims=verify(c.creds["artifact_signing_key"],token(request),"artifact")
    if claims.get("artifact_id")!=str(artifact_id):raise HTTPException(403,"artifact binding")
    row=c.store.one("SELECT * FROM task_artifacts WHERE id=:id AND task_id=:task AND state='available'",
                   {"id":artifact_id,"task":claims["task_id"]})
    if not row:raise HTTPException(404,"artifact unavailable")
    data=c.artifacts.read(row["storage_key"])
    import hashlib
    if len(data)!=row["size"] or hashlib.sha256(data).hexdigest()!=row["sha256"]:raise HTTPException(409,"artifact integrity")
    return Response(data,media_type=row["mime"],headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff",
                     "Content-Disposition":'attachment; filename="'+str(artifact_id)+'.json"'})

if __name__=="__main__":uvicorn.run(app,host="0.0.0.0",port=8000,access_log=False)
