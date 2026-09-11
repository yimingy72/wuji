"""Bounded read projections of immutable task assessment and evidence records."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from wuji_api.database import AuthorityUnavailable, ResourceNotFound
from wuji_api.execution_store import ExecutionStore
from wuji_api.assessments import AssessmentView, Observation, VerificationRun, VerificationResult, EvidenceLink

OWNED = 'tenant_id=:tenant_id AND project_id=:project_id AND task_id=:task_id'
RUN_COLUMNS = 'id,coverage_item_id,target_url,rule_id,claim,agent_run_id,intent_id,created_at'
RESULT_COLUMNS = 'id,verification_run_id,revision,verdict,reason,limitations,supersedes_result_id,created_at'
LINK_COLUMNS = 'id,verification_result_id,observation_id,artifact_id,relation,selector'


def public(model, row):
    return {key:row[key] for key in model.model_fields if key in row}


class AssessmentStore:
    def __init__(self, authority):
        self.authority = authority

    async def _params(self, connection, user_id, project_id, task_id):
        _, _, params = await ExecutionStore(self.authority)._task(connection,
            user_id=user_id, project_id=project_id, task_id=task_id)
        return params

    async def assessment(self, *, user_id, project_id, task_id):
        try:
            async with self.authority.project.begin() as connection:
                params = await self._params(connection,user_id,project_id,task_id)
                row = (await connection.execute(text(f'SELECT id,revision,progress_digest,snapshot FROM assessment_plans WHERE {OWNED} ORDER BY revision DESC LIMIT 1'),params)).mappings().one_or_none()
                if row is None: return AssessmentView(state='not_assessed').model_dump(mode='json')
                return public(AssessmentView,dict(row['snapshot'],state='available',plan_id=row['id'],revision=row['revision'],progress_digest=row['progress_digest']))
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def _latest(self, connection, params, run):
        result = (await connection.execute(text(f'SELECT {RESULT_COLUMNS} FROM verification_result_revisions WHERE {OWNED} AND verification_run_id=:verification_id ORDER BY revision DESC LIMIT 1'),dict(params,verification_id=run['id']))).mappings().one_or_none()
        return dict(public(VerificationRun,run),latest_result=None if result is None else public(VerificationResult,result))

    async def page(self, *, user_id, project_id, task_id, kind, limit, position=None, coverage_item_id=None, observation_id=None):
        if kind not in {'observations','verifications'} or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid assessment page')
        try:
            async with self.authority.project.begin() as connection:
                params = await self._params(connection,user_id,project_id,task_id)
                params['limit'] = limit + 1
                after = ''
                if position:
                    after += ' AND (created_at,id)<(:created_at,:after_id)'
                    params.update(created_at=position.created_at,after_id=position.task_id)
                if kind == 'verifications' and coverage_item_id is not None:
                    after += ' AND coverage_item_id=:coverage_item_id'
                    params['coverage_item_id'] = coverage_item_id
                if kind == 'observations' and observation_id is not None:
                    after += ' AND id=:observation_id'
                    params['observation_id'] = observation_id
                table = 'observations' if kind == 'observations' else 'verification_runs'
                columns = 'id,tool_call_id,agent_run_id,artifact_id,body_artifact_id,created_at,metadata' if kind == 'observations' else RUN_COLUMNS
                rows = (await connection.execute(text(f'SELECT {columns} FROM {table} WHERE {OWNED}{after} ORDER BY created_at DESC,id DESC LIMIT :limit'),params)).mappings().all()
                if kind == 'observations':
                    return [public(Observation,dict(row['metadata'],**{key:row[key] for key in ('id','tool_call_id','agent_run_id','artifact_id','body_artifact_id','created_at')},
                        target_url=row['metadata']['url'],response_status=row['metadata']['status'])) for row in rows]
                return [await self._latest(connection,params,row) for row in rows]
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def verification(self, *, user_id, project_id, task_id, verification_id):
        try:
            async with self.authority.project.begin() as connection:
                params = await self._params(connection,user_id,project_id,task_id)
                params['verification_id'] = verification_id
                row = (await connection.execute(text(f'SELECT {RUN_COLUMNS} FROM verification_runs WHERE {OWNED} AND id=:verification_id'),params)).mappings().one_or_none()
                if row is None: raise ResourceNotFound
                results = (await connection.execute(text(f'SELECT {RESULT_COLUMNS} FROM verification_result_revisions WHERE {OWNED} AND verification_run_id=:verification_id ORDER BY revision DESC LIMIT 100'),params)).mappings().all()
                # Include only evidence belonging to the same task and visible revision window.
                evidence = (await connection.execute(text(f'SELECT {LINK_COLUMNS} FROM evidence_links WHERE {OWNED} AND verification_result_id IN '
                    f'(SELECT id FROM verification_result_revisions WHERE {OWNED} AND verification_run_id=:verification_id ORDER BY revision DESC LIMIT 100) '
                    'ORDER BY created_at DESC,id DESC LIMIT 200'),params)).mappings().all()
                return dict(verification=await self._latest(connection,params,row),
                    results=[public(VerificationResult,item) for item in results],evidence=[public(EvidenceLink,item) for item in evidence])
        except SQLAlchemyError as error: raise AuthorityUnavailable from error
