"""Atomic saved-draft creation in the original user command key space."""
from datetime import timedelta
import json
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from wuji_api.database import (AuthorityUnavailable, CommandForbidden, CommandValidationFailed,
    IdempotencyConflict, PreviewExpired, ResourceNotFound, VersionConflict)
from wuji_api.draft_store import DraftStore
from wuji_api.model_selection import ModelUnavailable, model_version_lock, selectable_model
from wuji_api.task_creation import CreationBlocked, CreationConfigSnapshot, evaluate_creation, preview_digest

class CreationStore:
    def __init__(self, authority, preview_ttl_seconds=300):
        self.authority=authority
        self.preview_ttl_seconds=preview_ttl_seconds

    async def _draft(self, connection, params):
        row=(await connection.execute(text("SELECT * FROM task_drafts WHERE id=:draft_id AND tenant_id=:tenant_id AND project_id=:project_id AND user_id=:user_id FOR UPDATE"),params)).mappings().one_or_none()
        if row is None: raise ResourceNotFound
        return row

    async def preview(self, *, user_id, permissions_version, project_id, draft_id, draft_version):
        try:
            async with self.authority._fresh_user_lock(user_id) as current:
                async with self.authority.project.begin() as connection:
                    project=await DraftStore(self.authority)._authorize(connection,user_id,project_id)
                    if project.role != 'operator': raise CommandForbidden
                    if current != permissions_version: raise VersionConflict
                    params=dict(user_id=user_id,project_id=project_id,tenant_id=project.tenant_id,draft_id=draft_id)
                    draft=await self._draft(connection,params)
                    if draft['version'] != draft_version: raise VersionConflict
                    content=draft['content']; model_id=content.get('model_profile_version_id'); model=None
                    if model_id:
                        await model_version_lock(connection,project.tenant_id,model_id)
                        try: model=await selectable_model(connection,project.tenant_id,model_id)
                        except ModelUnavailable: pass
                    now=await connection.scalar(text('SELECT clock_timestamp()'))
                    blockers,auth_digest=evaluate_creation(content,model,now)
                    input_digest=preview_digest(dict(content=content,model=model,permissions_version=current,user_id=str(user_id),project_id=str(project_id)))
                    params.update(id=uuid4(),draft_version=draft_version,draft_digest=draft['content_digest'],permissions_version=current,
                        normalized_content=json.dumps(content),model_snapshot=json.dumps(model),input_digest=input_digest,
                        authorization_digest=auth_digest,can_create=not blockers,blockers=json.dumps(blockers),created_at=now,expires_at=now+timedelta(seconds=self.preview_ttl_seconds))
                    await connection.execute(text('''INSERT INTO task_creation_previews
                        (id,tenant_id,project_id,user_id,draft_id,draft_version,draft_digest,permissions_version,normalized_content,model_snapshot,input_digest,authorization_digest,can_create,blockers,created_at,expires_at)
                        VALUES (:id,:tenant_id,:project_id,:user_id,:draft_id,:draft_version,:draft_digest,:permissions_version,CAST(:normalized_content AS jsonb),CAST(:model_snapshot AS jsonb),:input_digest,:authorization_digest,:can_create,CAST(:blockers AS jsonb),:created_at,:expires_at)'''),params)
                    return dict(preview_id=params['id'],project_id=project_id,start_available=False,draft_id=draft_id,draft_version=draft_version,normalized_content=content,model_snapshot=model,
                        input_digest=input_digest,authorization_digest=auth_digest,can_create=not blockers,blockers=blockers,created_at=now,expires_at=params['expires_at'])
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def create_command(self, *, user_id, permissions_version, project_id, idempotency_key, body, request_digest, trace_id):
        try:
            async with self.authority._fresh_user_lock(user_id) as current:
                async with self.authority.project.begin() as connection:
                    project=await DraftStore(self.authority)._authorize(connection,user_id,project_id)
                    if project.role != 'operator': raise CommandForbidden
                    params=dict(user_id=user_id,project_id=project_id,tenant_id=project.tenant_id,idempotency_key=idempotency_key)
                    existing=await self.authority._existing_receipt(connection,**params)
                    if existing:
                        if existing['request_digest'] != request_digest: raise IdempotencyConflict
                        return existing
                    if current != permissions_version: raise VersionConflict
                    params.update(draft_id=body.draft_id,preview_id=body.preview_id)
                    draft=await self._draft(connection,params)
                    preview=(await connection.execute(text('SELECT * FROM task_creation_previews WHERE id=:preview_id AND tenant_id=:tenant_id AND project_id=:project_id AND user_id=:user_id'),params)).mappings().one_or_none()
                    if preview is None: raise ResourceNotFound
                    now=await connection.scalar(text('SELECT clock_timestamp()'))
                    if preview['expires_at'] <= now: raise PreviewExpired
                    if preview['permissions_version'] != current or draft['version'] != body.draft_version or preview['draft_version'] != draft['version']: raise VersionConflict
                    if preview['draft_id'] != body.draft_id or preview['draft_digest'] != draft['content_digest'] or preview['normalized_content'] != draft['content']: raise VersionConflict
                    if body.input_digest != preview['input_digest'] or body.scope_confirmation.authorization_digest != preview['authorization_digest']: raise CommandValidationFailed
                    content=draft['content']; model_id=content.get('model_profile_version_id')
                    if not model_id: raise ModelUnavailable
                    await model_version_lock(connection,project.tenant_id,model_id)
                    now=await connection.scalar(text('SELECT clock_timestamp()'))
                    if preview['expires_at'] <= now: raise PreviewExpired
                    model=await selectable_model(connection,project.tenant_id,model_id)
                    if model != preview['model_snapshot']: raise VersionConflict
                    blockers,auth_digest=evaluate_creation(content,model,now)
                    if blockers or not preview['can_create']: raise CreationBlocked
                    if auth_digest != preview['authorization_digest']: raise CommandValidationFailed
                    task_id,auth_id,snapshot_id=uuid4(),uuid4(),uuid4()
                    snapshot=dict(schema_version='1.0',id=str(snapshot_id),scenario=content['scenario'],goal_template=content['goal_template'],
                        objective=content['objective'],completion_criteria=content['completion_criteria'],supplemental_hints=content['supplemental_hints'],
                        actual_input=content,authorization=content['authorization'],authorization_id=str(auth_id),authorization_digest=auth_digest,
                        model=model,budget_usd=content['budget_usd'],created_by=str(user_id),created_at=now.isoformat())
                    snapshot['digest']=preview_digest(snapshot)
                    snapshot=CreationConfigSnapshot.model_validate(snapshot).model_dump(mode='json')
                    snapshot['digest']=preview_digest({key:value for key,value in snapshot.items() if key != 'digest'})
                    params.update(task_id=task_id,auth_id=auth_id,snapshot_id=snapshot_id,draft=json.dumps(dict(content,target_url=content['entry_url'])),
                        scope=json.dumps(content['authorization']),scope_hash=auth_digest,input_digest=preview['input_digest'],snapshot=json.dumps(snapshot),
                        valid_until=content['authorization']['valid_until'],now=now,permissions_version=current,request_digest=request_digest,command_id=uuid4(),event_id=uuid4(),trace_id=trace_id)
                    await connection.execute(text('''INSERT INTO tasks
                        (id,tenant_id,project_id,user_id,draft,input_digest,effective_scope,version,state,cleanup_state,active_calls,unknown_calls,egress_state,assessment_outcome,stop_reason,event_sequence,task_kind,task_authorization_id,creation_config_snapshot_id,creation_config)
                        VALUES (:task_id,:tenant_id,:project_id,:user_id,CAST(:draft AS jsonb),:input_digest,CAST(:scope AS jsonb),1,'ready','not_required',0,0,'not_granted','not_assessed',NULL,1,'web_assessment',:auth_id,:snapshot_id,CAST(:snapshot AS jsonb))'''),params)
                    await connection.execute(text('''INSERT INTO task_authorizations
                        (id,tenant_id,project_id,task_id,version,scope,scope_hash,valid_from,valid_until,confirmed_by,permissions_version,confirmation_text_version,confirmed_at)
                        VALUES (:auth_id,:tenant_id,:project_id,:task_id,1,CAST(:scope AS jsonb),:scope_hash,:now,CAST(:valid_until AS timestamptz),:user_id,:permissions_version,'1.0',:now)'''),params)
                    receipt=(await connection.execute(text('''INSERT INTO command_receipts
                        (id,tenant_id,project_id,user_id,idempotency_key,kind,task_id,request_digest,disposition,accepted_task_version)
                        VALUES (:command_id,:tenant_id,:project_id,:user_id,:idempotency_key,'create',:task_id,:request_digest,'accepted',1)
                        RETURNING id AS command_id,idempotency_key,kind,disposition,project_id,task_id,accepted_at,accepted_task_version,request_digest'''),params)).mappings().one()
                    await connection.execute(text("INSERT INTO task_events(event_id,tenant_id,project_id,task_id,sequence,aggregate_version,event_type,trace_id,summary) VALUES(:event_id,:tenant_id,:project_id,:task_id,1,1,'task.changed',:trace_id,'任务已创建，等待启动')"),params)
                    await connection.execute(text('UPDATE task_drafts SET last_created_task_id=:task_id WHERE id=:draft_id AND tenant_id=:tenant_id AND project_id=:project_id AND user_id=:user_id'),params)
                    return dict(receipt)
        except SQLAlchemyError as error: raise AuthorityUnavailable from error
