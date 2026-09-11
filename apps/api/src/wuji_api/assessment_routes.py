"""Authenticated read-only W1 task assessment endpoints."""
import hashlib
from uuid import UUID
from fastapi import Query, Request
from wuji_api.assessment_store import AssessmentStore
from wuji_api.assessments import AssessmentView, ObservationPage, VerificationPage, VerificationDetail
from wuji_api.database import AuthorityUnavailable, ResourceNotFound
from wuji_api.security import ExpiredCursor, InvalidCursor, TaskCursorPosition


def register_assessment_routes(application):
    from wuji_api.main import ApiProblem, ErrorResponse, _authenticated, _command_problem, _runtime
    errors = {code:{'model':ErrorResponse} for code in (401,403,404,410,422,500,503)}
    base = '/api/v1/projects/{project_id}/tasks/{task_id}'

    async def invoke(awaitable):
        try: return await awaitable
        except ResourceNotFound as error: raise _command_problem(error) from error
        except AuthorityUnavailable as error: raise ApiProblem(503,'SERVICE_UNAVAILABLE') from error

    @application.get(base+'/assessment',response_model=AssessmentView,responses=errors,tags=['Assessments'])
    async def assessment(request:Request,project_id:UUID,task_id:UUID):
        runtime = _runtime(request); session = await _authenticated(request,runtime)
        return AssessmentView.model_validate(await invoke(AssessmentStore(runtime.authority).assessment(
            user_id=session.user_id,project_id=project_id,task_id=task_id)))

    async def page(request, project_id, task_id, kind, limit, cursor, coverage_item_id=None, observation_id=None):
        runtime = _runtime(request); session = await _authenticated(request,runtime)
        purpose = f'assessment:{kind}:{task_id}:{coverage_item_id or "all"}:{observation_id or "all"}'
        endpoint = 'wa_' + hashlib.sha256(purpose.encode()).hexdigest()[:32]
        args = dict(user_id=session.user_id,permissions_version=session.permissions_version,
                    project_id=project_id,limit=limit,endpoint=endpoint)
        position = None
        if cursor:
            try: position = runtime.cursors.decode_task(cursor,**args)
            except ExpiredCursor as error: raise ApiProblem(410,'CURSOR_EXPIRED') from error
            except InvalidCursor as error: raise ApiProblem(422,'VALIDATION_FAILED') from error
        rows = await invoke(AssessmentStore(runtime.authority).page(user_id=session.user_id,
            project_id=project_id,task_id=task_id,kind=kind,limit=limit,position=position,coverage_item_id=coverage_item_id,observation_id=observation_id))
        visible, next_cursor = rows[:limit], None
        if len(rows)>limit:
            last = visible[-1]
            next_cursor = runtime.cursors.encode_task(**args,position=TaskCursorPosition(last['created_at'],last['id']))
        response_model = ObservationPage if kind == 'observations' else VerificationPage
        return response_model(items=visible,next_cursor=next_cursor)

    @application.get(base+'/observations',response_model=ObservationPage,responses=errors,tags=['Assessments'])
    async def observations(request:Request,project_id:UUID,task_id:UUID,
            limit:int=Query(50,ge=1,le=100),cursor:str|None=Query(None,min_length=1,max_length=512),observation_id:UUID|None=None):
        return await page(request,project_id,task_id,'observations',limit,cursor,observation_id=observation_id)

    @application.get(base+'/verifications',response_model=VerificationPage,responses=errors,tags=['Assessments'])
    async def verifications(request:Request,project_id:UUID,task_id:UUID,
            limit:int=Query(50,ge=1,le=100),cursor:str|None=Query(None,min_length=1,max_length=512),coverage_item_id:UUID|None=None):
        return await page(request,project_id,task_id,'verifications',limit,cursor,coverage_item_id)

    @application.get(base+'/verifications/{verification_id}',response_model=VerificationDetail,responses=errors,tags=['Assessments'])
    async def verification(request:Request,project_id:UUID,task_id:UUID,verification_id:UUID):
        runtime = _runtime(request); session = await _authenticated(request,runtime)
        return VerificationDetail.model_validate(await invoke(AssessmentStore(runtime.authority).verification(
            user_id=session.user_id,project_id=project_id,task_id=task_id,verification_id=verification_id)))
