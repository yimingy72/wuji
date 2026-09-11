"""Explicit start and bounded execution observations in the original command space."""
import hashlib
import json
from datetime import timedelta
from uuid import uuid4
from urllib.parse import urlsplit
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from wuji_api.database import (AuthorityUnavailable, CommandForbidden, IdempotencyConflict,
    InvalidTransition, ResourceNotFound, VersionConflict)
from wuji_api.draft_store import DraftStore
from wuji_api.model_selection import model_version_lock
from wuji_api.scope_policy import normalize_origin

PAGE_COLUMNS = {
    "agent_runs": "id,phase,intent_id,worker_profile_id,state,result_state,outcome,created_at,updated_at",
    "tool_calls": "id,agent_run_id,tool,state,args,result,cancel_requested,created_at,updated_at",
    "task_artifacts": "id,tool_call_id,kind,name,mime,size,sha256,state,created_at",
}

class ExecutionStore:
    def __init__(self, authority):
        self.authority = authority

    async def _task(self, connection, *, user_id, project_id, task_id, locked=False):
        project = await DraftStore(self.authority)._authorize(connection, user_id, project_id)
        params = dict(tenant_id=project.tenant_id,project_id=project_id,task_id=task_id,user_id=user_id)
        task = (await connection.execute(text("SELECT id,task_kind,state,version,execution_epoch,event_sequence,creation_config,creation_config_snapshot_id "
            "FROM tasks WHERE tenant_id=:tenant_id AND project_id=:project_id AND id=:task_id" + (" FOR UPDATE" if locked else "")),params)).mappings().one_or_none()
        if task is None: raise ResourceNotFound
        return project, task, params

    async def start_command(self, *, user_id, permissions_version, project_id, task_id, idempotency_key,
                            expected_version, request_digest, trace_id):
        try:
            async with self.authority._fresh_user_lock(user_id) as current:
                async with self.authority.project.begin() as connection:
                    project = await DraftStore(self.authority)._authorize(connection,user_id,project_id)
                    if project.role != "operator": raise CommandForbidden
                    params = dict(tenant_id=project.tenant_id,project_id=project_id,user_id=user_id,idempotency_key=idempotency_key)
                    existing = await self.authority._existing_receipt(connection,**params)
                    if existing:
                        if existing["request_digest"] != request_digest: raise IdempotencyConflict
                        return existing
                    if current != permissions_version: raise VersionConflict
                    _, task, task_params = await self._task(connection,user_id=user_id,project_id=project_id,task_id=task_id,locked=True)
                    params.update(task_params)
                    if task["version"] != expected_version: raise VersionConflict
                    if task["task_kind"] != "web_assessment" or task["state"] != "ready": raise InvalidTransition
                    now = await connection.scalar(text("SELECT clock_timestamp()"))
                    service = (await connection.execute(text("SELECT instance_id,config,heartbeat_at FROM execution_services WHERE id='core'"))).mappings().one_or_none()
                    if service is None or not now-timedelta(seconds=15) < service["heartbeat_at"] <= now: raise InvalidTransition
                    config, creation = service["config"], task["creation_config"]
                    if config.get("ready") is not True or not isinstance(config.get("profile_id"),str): raise InvalidTransition
                    model_id = creation["model"]["id"]
                    if config.get("model_profile_version_id") != model_id: raise InvalidTransition
                    parsed = urlsplit(creation["actual_input"]["entry_url"])
                    entry = normalize_origin(f"{parsed.scheme}://{parsed.netloc}/")
                    if entry not in config.get("fixture_origins",[]): raise InvalidTransition
                    await model_version_lock(connection,project.tenant_id,model_id)
                    available = await connection.scalar(text("SELECT id FROM model_versions WHERE tenant_id=:tenant_id AND id=:model_id AND kind='profile' AND state IN ('published','retired') AND sync_state='synced'"),dict(params,model_id=model_id))
                    if available is None: raise InvalidTransition
                    now = await connection.scalar(text("SELECT clock_timestamp()"))
                    current_service = (await connection.execute(text("SELECT instance_id,config,heartbeat_at FROM execution_services WHERE id='core'"))).mappings().one_or_none()
                    if (current_service is None or current_service["instance_id"] != service["instance_id"]
                            or current_service["config"] != config
                            or not now-timedelta(seconds=15) < current_service["heartbeat_at"] <= now):
                        raise InvalidTransition
                    authorization = await connection.scalar(text("SELECT valid_until FROM task_authorizations WHERE tenant_id=:tenant_id AND project_id=:project_id AND task_id=:task_id AND id=:id"),dict(params,id=creation["authorization_id"]))
                    if authorization is None or authorization <= now: raise InvalidTransition
                    snapshot = dict(id=str(uuid4()),creation_config_id=str(task["creation_config_snapshot_id"]),profile_id=config["profile_id"],config={key:config[key] for key in ("profile_id","ready","namespace","agent_image","kali_image","fixture_origins","model_profile_version_id","model_base_url","control_url","max_agents","max_task_seconds","max_agent_turns","max_tool_calls") if key in config})
                    snapshot["config_digest"] = hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
                    params.update(command_id=uuid4(),request_digest=request_digest,version=expected_version+1,
                        execution_id=uuid4(),epoch=task["execution_epoch"]+1,instance_id=service["instance_id"],snapshot=json.dumps(snapshot),
                        event_id=uuid4(),sequence=task["event_sequence"]+1,trace_id=trace_id)
                    receipt = (await connection.execute(text("INSERT INTO command_receipts (id,tenant_id,project_id,user_id,idempotency_key,kind,task_id,request_digest,disposition,accepted_task_version) "
                        "VALUES (:command_id,:tenant_id,:project_id,:user_id,:idempotency_key,'start',:task_id,:request_digest,'accepted',:version) "
                        "RETURNING id AS command_id,idempotency_key,kind,disposition,project_id,task_id,accepted_at,accepted_task_version,request_digest"),params)).mappings().one()
                    await connection.execute(text("INSERT INTO task_executions(id,tenant_id,project_id,task_id,start_command_id,epoch,state,service_instance_id,execution_snapshot) "
                        "VALUES(:execution_id,:tenant_id,:project_id,:task_id,:command_id,:epoch,'pending',:instance_id,CAST(:snapshot AS jsonb))"),params)
                    await connection.execute(text("UPDATE tasks SET state='provisioning',version=:version,execution_epoch=:epoch,event_sequence=:sequence,updated_at=clock_timestamp() "
                        "WHERE id=:task_id AND tenant_id=:tenant_id AND project_id=:project_id"),params)
                    await connection.execute(text("INSERT INTO task_events(event_id,tenant_id,project_id,task_id,sequence,aggregate_version,event_type,trace_id,summary) "
                        "VALUES(:event_id,:tenant_id,:project_id,:task_id,:sequence,:version,'task.changed',:trace_id,'任务已启动，准备执行环境')"),params)
                    return dict(receipt)
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def page(self, *, user_id, project_id, task_id, table, limit, position=None, filter_value=None):
        if table not in PAGE_COLUMNS or type(limit) is not int or not 1 <= limit <= 100: raise ValueError("invalid execution page")
        try:
            async with self.authority.project.begin() as connection:
                _, _, params = await self._task(connection,user_id=user_id,project_id=project_id,task_id=task_id)
                params["limit"] = limit+1
                after = ""
                if filter_value is not None:
                    column={"agent_runs":"intent_id","tool_calls":"agent_run_id","task_artifacts":"tool_call_id"}[table]
                    after=f" AND {column}=:filter_value"
                    params["filter_value"]=filter_value
                if position:
                    after += " AND (created_at,id)<(:created_at,:after_id)"
                    params.update(created_at=position.created_at,after_id=position.task_id)
                rows = (await connection.execute(text(f"SELECT {PAGE_COLUMNS[table]} FROM {table} WHERE tenant_id=:tenant_id AND project_id=:project_id AND task_id=:task_id{after} ORDER BY created_at DESC,id DESC LIMIT :limit"),params)).mappings().all()
                return [dict(row) for row in rows]
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def blackboard(self, *, user_id, project_id, task_id):
        try:
            async with self.authority.project.begin() as connection:
                _, _, params = await self._task(connection,user_id=user_id,project_id=project_id,task_id=task_id)
                row = (await connection.execute(text("SELECT native_project_id,graph,digest,created_at FROM task_graph_snapshots WHERE tenant_id=:tenant_id AND project_id=:project_id AND task_id=:task_id ORDER BY created_at DESC,id DESC LIMIT 1"),params)).mappings().one_or_none()
                if row is None: return dict(state="pending",native_project_id=None,graph=None,captured_at=None,digest=None)
                return dict(state="available",native_project_id=row["native_project_id"],graph=row["graph"],captured_at=row["created_at"],digest=row["digest"])
        except SQLAlchemyError as error: raise AuthorityUnavailable from error

    async def result(self, *, user_id, project_id, task_id):
        try:
            async with self.authority.project.begin() as connection:
                _, _, params = await self._task(connection,user_id=user_id,project_id=project_id,task_id=task_id)
                row = (await connection.execute(text("SELECT result,model_spend,cost_state FROM task_executions WHERE tenant_id=:tenant_id AND project_id=:project_id AND task_id=:task_id"),params)).mappings().one_or_none()
                result = {} if row is None or row["result"] is None else row["result"]
                return dict(state="available" if result else "pending",goal_status=result.get("goal_status","unknown"),summary=result.get("summary",""),limitations=result.get("limitations",[]),artifact_ids=result.get("artifact_ids",[]),
                    model_spend=None if row is None or row["model_spend"] is None else str(row["model_spend"]),cost_state="unknown" if row is None else row["cost_state"])
        except SQLAlchemyError as error: raise AuthorityUnavailable from error
