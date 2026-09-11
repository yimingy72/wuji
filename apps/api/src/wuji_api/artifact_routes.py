"""Authenticated development Artifact download through a purpose-limited grant."""
from datetime import datetime,timezone
from uuid import UUID
import base64,hashlib,hmac,json,time
import httpx
from fastapi import Request
from fastapi.responses import Response
from sqlalchemy import text
from wuji_api.execution_store import ExecutionStore
from wuji_api.database import ResourceNotFound,AuthorityUnavailable

def grant(key,task_id,artifact_id):
    value={"role":"artifact","task_id":str(task_id),"artifact_id":str(artifact_id),"exp":int(time.time())+30}
    body=base64.urlsafe_b64encode(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).rstrip(b"=").decode()
    sig=base64.urlsafe_b64encode(hmac.new(key.encode(),("wuji-core-v1."+body).encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
    return body+"."+sig

def register_artifact_routes(app):
    from wuji_api.main import _runtime,_authenticated,_command_problem,ApiProblem,NO_STORE,ErrorResponse
    @app.get("/api/v1/projects/{project_id}/tasks/{task_id}/artifacts/{artifact_id}/content",tags=["Artifacts"],
             responses={c:{"model":ErrorResponse} for c in (401,403,404,409,500,503)})
    async def download(request:Request,project_id:UUID,task_id:UUID,artifact_id:UUID):
        runtime=_runtime(request);session=await _authenticated(request,runtime)
        try:
            async with runtime.authority.project.begin() as c:
                await ExecutionStore(runtime.authority)._task(c,user_id=session.user_id,project_id=project_id,task_id=task_id)
                row=(await c.execute(text("SELECT mime,size,sha256 FROM task_artifacts WHERE id=:id AND task_id=:task "
                    "AND project_id=:project AND state='available'"),{"id":artifact_id,"task":task_id,"project":project_id})).mappings().one_or_none()
                service=await c.scalar(text("SELECT config FROM execution_services WHERE id='core'"))
                if row is None:raise ResourceNotFound
        except (ResourceNotFound,AuthorityUnavailable) as error:raise _command_problem(error) from error
        url=(service or {}).get("public_control_url")
        if url!="http://127.0.0.1:18502":raise ApiProblem(503,"SERVICE_UNAVAILABLE")
        token=grant(runtime.settings.cursor_signing_key.get_secret_value(),task_id,artifact_id)
        try:
            async with httpx.AsyncClient(timeout=10,trust_env=False,transport=httpx.AsyncHTTPTransport(retries=0)) as client:
                response=await client.get(url+"/internal/v1/artifacts/"+str(artifact_id)+"/content",headers={"Authorization":"Bearer "+token})
                if response.status_code!=200:raise ApiProblem(503,"SERVICE_UNAVAILABLE")
                data=response.content
                if len(data)>1_048_576 or len(data)!=row["size"] or hashlib.sha256(data).hexdigest()!=row["sha256"]:
                    raise ApiProblem(409,"VERSION_CONFLICT")
        except httpx.HTTPError as error:raise ApiProblem(503,"SERVICE_UNAVAILABLE") from error
        return Response(data,media_type=row["mime"],headers={**NO_STORE,"X-Content-Type-Options":"nosniff",
            "Content-Disposition":'attachment; filename="'+str(artifact_id)+'.json"'})
