"""Creation preview and built-in scenario HTTP endpoints."""
from uuid import UUID
from fastapi import Header, Request
from wuji_api.database import AuthorityUnavailable, CommandForbidden, FreshAuthorityInvalid, ResourceNotFound, VersionConflict
from wuji_api.draft_store import DraftStore
from wuji_api.task_creation import CreationPreviewRequest, TaskCreationPreview
from wuji_api.task_creation_store import CreationStore
from wuji_api.scenario_profiles import ScenarioProfilePage, scenario_profiles

def register_creation_routes(application):
    from wuji_api.main import ApiProblem, ErrorResponse, _authenticated, _command_problem, _require_write, _runtime
    errors={code:{'model':ErrorResponse} for code in (401,403,404,409,422,500,503)}
    @application.get('/api/v1/projects/{project_id}/scenario-profiles',tags=['Drafts'],response_model=ScenarioProfilePage,responses=errors)
    async def get_profiles(request:Request,project_id:UUID):
        current=_runtime(request);session=await _authenticated(request,current)
        try:
            async with current.authority.project.begin() as connection:
                await DraftStore(current.authority)._authorize(connection,session.user_id,project_id)
        except ResourceNotFound as error: raise _command_problem(error) from error
        return scenario_profiles()
    @application.post('/api/v1/projects/{project_id}/task-creation-previews',tags=['Drafts'],response_model=TaskCreationPreview,responses=errors)
    async def preview(request:Request,project_id:UUID,body:CreationPreviewRequest,csrf_token:str|None=Header(default=None,alias='X-CSRF-Token')):
        current=_runtime(request);session=await _authenticated(request,current);_require_write(request,current,session,csrf_token)
        try:
            row=await CreationStore(current.authority).preview(user_id=session.user_id,permissions_version=session.permissions_version,project_id=project_id,draft_id=body.draft_id,draft_version=body.draft_version)
        except (CommandForbidden,FreshAuthorityInvalid,ResourceNotFound,VersionConflict) as error: raise _command_problem(error) from error
        except AuthorityUnavailable as error: raise ApiProblem(503,'SERVICE_UNAVAILABLE') from error
        return TaskCreationPreview.model_validate(row)
