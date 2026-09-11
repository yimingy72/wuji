"""Draft HTTP entrypoints reuse the established session and project authority."""
from uuid import UUID

from fastapi import Header, Query, Request

from wuji_api.database import AuthorityUnavailable, CommandForbidden, CommandValidationFailed, FreshAuthorityInvalid, ResourceNotFound, VersionConflict
from wuji_api.draft_store import DraftStore
from wuji_api.drafts import SaveDraftRequest, TaskDraftPageResponse, TaskDraftResponse, content_digest
from wuji_api.security import ExpiredCursor, InvalidCursor, TaskCursorPosition


def register_draft_routes(application):
    # Late binding avoids a second copy of authentication and error handling.
    from wuji_api.main import ApiProblem, ErrorResponse, _authenticated, _command_problem, _require_write, _runtime

    errors = {code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 410, 422, 500, 503)}

    @application.put("/api/v1/projects/{project_id}/task-drafts/{draft_id}", tags=["Drafts"], response_model=TaskDraftResponse, responses=errors)
    async def save_draft(request: Request, project_id: UUID, draft_id: UUID, body: SaveDraftRequest,
                         csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")):
        current = _runtime(request)
        session = await _authenticated(request, current)
        _require_write(request, current, session, csrf_token)
        content = body.content.model_dump(mode="json")
        try:
            row = await DraftStore(current.authority).save(user_id=session.user_id,
                permissions_version=session.permissions_version, project_id=project_id, draft_id=draft_id,
                expected_version=body.expected_version, content=content, content_digest=content_digest(content))
        except (CommandForbidden, CommandValidationFailed, FreshAuthorityInvalid, ResourceNotFound, VersionConflict) as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        return TaskDraftResponse.model_validate(row)

    @application.get("/api/v1/projects/{project_id}/task-drafts/{draft_id}", tags=["Drafts"], response_model=TaskDraftResponse, responses=errors)
    async def get_draft(request: Request, project_id: UUID, draft_id: UUID):
        current = _runtime(request)
        session = await _authenticated(request, current)
        try:
            row = await DraftStore(current.authority).get(user_id=session.user_id, project_id=project_id, draft_id=draft_id)
        except ResourceNotFound as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        return TaskDraftResponse.model_validate(row)

    @application.get("/api/v1/projects/{project_id}/task-drafts", tags=["Drafts"], response_model=TaskDraftPageResponse, responses=errors)
    async def list_drafts(request: Request, project_id: UUID, limit: int = Query(default=50, ge=1, le=100),
                          cursor: str | None = Query(default=None, min_length=1, max_length=512)):
        current = _runtime(request)
        session = await _authenticated(request, current)
        position = None
        if cursor is not None:
            try:
                position = current.cursors.decode_task(cursor, user_id=session.user_id,
                    permissions_version=session.permissions_version, project_id=project_id, limit=limit, endpoint="task_drafts")
            except ExpiredCursor as error:
                raise ApiProblem(410, "CURSOR_EXPIRED") from error
            except InvalidCursor as error:
                raise ApiProblem(422, "VALIDATION_FAILED") from error
        try:
            rows = await DraftStore(current.authority).list(user_id=session.user_id, project_id=project_id,
                                                           limit=limit, position=position)
        except ResourceNotFound as error:
            raise _command_problem(error) from error
        except AuthorityUnavailable as error:
            raise ApiProblem(503, "SERVICE_UNAVAILABLE") from error
        visible = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            last = visible[-1]
            next_cursor = current.cursors.encode_task(user_id=session.user_id, permissions_version=session.permissions_version,
                project_id=project_id, limit=limit, position=TaskCursorPosition(last["created_at"], last["id"]), endpoint="task_drafts")
        return TaskDraftPageResponse(items=[TaskDraftResponse.model_validate(row) for row in visible], next_cursor=next_cursor)
