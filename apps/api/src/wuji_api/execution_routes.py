"""Read-only task execution HTTP routes reuse session, project, and cursor authority."""
from uuid import UUID
import hashlib
from fastapi import Query, Request
from wuji_api.database import AuthorityUnavailable, ResourceNotFound
from wuji_api.execution_store import ExecutionStore
from wuji_api.executions import AgentRunPage, ToolCallPage, ArtifactPage, BlackBoardSnapshot, TaskResult
from wuji_api.security import ExpiredCursor, InvalidCursor, TaskCursorPosition


def register_execution_routes(application):
    from wuji_api.main import ApiProblem, ErrorResponse, _authenticated, _command_problem, _runtime
    errors = {code: {"model": ErrorResponse} for code in (401,403,404,409,410,422,500,503)}

    def register_page(suffix, table, response_model):
        async def page(request: Request, project_id: UUID, task_id: UUID,
                       limit: int = Query(default=50,ge=1,le=100),
                       cursor: str | None = Query(default=None,min_length=1,max_length=512),
                       intent_id: str | None = Query(default=None,max_length=128,pattern=r"^[A-Za-z0-9_-]+$"),
                       agent_run_id: UUID | None = None, tool_call_id: UUID | None = None):
            current = _runtime(request)
            session = await _authenticated(request,current)
            endpoint = f"{table}:{task_id}"
            allowed_filter={"agent_runs":intent_id,"tool_calls":agent_run_id,"task_artifacts":tool_call_id}[table]
            supplied=[v for v in (intent_id,agent_run_id,tool_call_id) if v is not None]
            if len(supplied)>1 or (supplied and allowed_filter is None):raise ApiProblem(422,"VALIDATION_FAILED")
            if allowed_filter is not None:
                endpoint=f"{table}:"+hashlib.sha256(f"{task_id}:{allowed_filter}".encode()).hexdigest()[:24]
            position = None
            if cursor:
                try:
                    position = current.cursors.decode_task(cursor,user_id=session.user_id,
                        permissions_version=session.permissions_version,project_id=project_id,limit=limit,endpoint=endpoint)
                except ExpiredCursor as error: raise ApiProblem(410,"CURSOR_EXPIRED") from error
                except InvalidCursor as error: raise ApiProblem(422,"VALIDATION_FAILED") from error
            try:
                rows = await ExecutionStore(current.authority).page(user_id=session.user_id,project_id=project_id,
                    task_id=task_id,table=table,limit=limit,position=position,filter_value=allowed_filter)
            except ResourceNotFound as error: raise _command_problem(error) from error
            except AuthorityUnavailable as error: raise ApiProblem(503,"SERVICE_UNAVAILABLE") from error
            visible, next_cursor = rows[:limit], None
            if len(rows)>limit:
                last = visible[-1]
                next_cursor = current.cursors.encode_task(user_id=session.user_id,
                    permissions_version=session.permissions_version,project_id=project_id,limit=limit,
                    position=TaskCursorPosition(last["created_at"],last["id"]),endpoint=endpoint)
            return response_model(items=visible,next_cursor=next_cursor)
        application.get(f"/api/v1/projects/{{project_id}}/tasks/{{task_id}}/{suffix}",
            tags=["Executions"],response_model=response_model,responses=errors,name=f"get_{table}")(page)

    register_page("agent-runs","agent_runs",AgentRunPage)
    register_page("tool-calls","tool_calls",ToolCallPage)
    register_page("artifacts","task_artifacts",ArtifactPage)

    @application.get("/api/v1/projects/{project_id}/tasks/{task_id}/blackboard",tags=["Executions"],response_model=BlackBoardSnapshot,responses=errors)
    async def blackboard(request: Request, project_id: UUID, task_id: UUID):
        current = _runtime(request)
        session = await _authenticated(request,current)
        try:
            return BlackBoardSnapshot.model_validate(await ExecutionStore(current.authority).blackboard(
                user_id=session.user_id,project_id=project_id,task_id=task_id))
        except ResourceNotFound as error: raise _command_problem(error) from error
        except AuthorityUnavailable as error: raise ApiProblem(503,"SERVICE_UNAVAILABLE") from error

    @application.get("/api/v1/projects/{project_id}/tasks/{task_id}/result",tags=["Executions"],response_model=TaskResult,responses=errors)
    async def result(request: Request, project_id: UUID, task_id: UUID):
        current = _runtime(request)
        session = await _authenticated(request,current)
        try:
            return TaskResult.model_validate(await ExecutionStore(current.authority).result(
                user_id=session.user_id,project_id=project_id,task_id=task_id))
        except ResourceNotFound as error: raise _command_problem(error) from error
        except AuthorityUnavailable as error: raise ApiProblem(503,"SERVICE_UNAVAILABLE") from error
