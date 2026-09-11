"""One temporary PostgreSQL start/read path, with stale consumer and old-task refusal."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from uuid import UUID,uuid4
import pytest
from wuji_api.database import InvalidTransition, ResourceNotFound
from wuji_api.execution_store import ExecutionStore
from wuji_api.execution_routes import register_execution_routes

spec=importlib.util.spec_from_file_location('execution_owned_pg',Path(__file__).parents[1]/'control-plane'/'conftest.py')
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
draft_database=module.draft_database
draft_case=module.draft_case


def test_start_receipt_and_permission_filtered_observations(draft_case):
    case=draft_case
    task,auth,model,service,definition,service_definition,old,old_auth,policy=[uuid4() for _ in range(9)]
    config={'service_version_id':str(service),'model_id':'fixture','context_window':4096,'max_output_tokens':512,'timeout_seconds':30,'pricing':{'source':'fixture','input_per_million':'1','output_per_million':'2','cache_mode':'standard_input'}}
    with case.database.connect() as c:
        for did,vid,kind,conf,sv in [(service_definition,service,'service',{'protocol':'openai','base_url':'http://fixture.invalid'},None),(definition,model,'profile',config,service)]:
            c.execute('INSERT INTO model_definitions(id,tenant_id,kind,name) VALUES(%s,%s,%s,%s)',(did,case.tenant,kind,'Fixture'))
            c.execute("INSERT INTO model_versions(id,tenant_id,kind,definition_id,number,name,config,service_version_id,gateway_instance_id,native_id,request_digest,state,sync_state) VALUES(%s,%s,%s,%s,1,'Fixture',%s,%s,%s,%s,%s,'published','synced')",(vid,case.tenant,kind,did,json.dumps(conf),sv,uuid4(),str(vid),'a'*64))
        creation={'model':{'id':str(model)},'actual_input':{'entry_url':'http://fixture.invalid/path'},'authorization_id':str(auth)}
        c.execute("INSERT INTO tasks(id,tenant_id,project_id,user_id,draft,input_digest,effective_scope,task_kind,state,task_authorization_id,creation_config_snapshot_id,creation_config,event_sequence) VALUES(%s,%s,%s,%s,'{}',%s,'{}','web_assessment','ready',%s,%s,%s,1)",(task,case.tenant,case.project,case.users['owner'],'a'*64,auth,uuid4(),json.dumps(creation)))
        c.execute("INSERT INTO task_authorizations(id,tenant_id,project_id,task_id,scope,scope_hash,valid_from,valid_until,confirmed_by,permissions_version,confirmation_text_version,confirmed_at) VALUES(%s,%s,%s,%s,'{}',%s,clock_timestamp(),clock_timestamp()+interval '1 hour',%s,1,'1.0',clock_timestamp())",(auth,case.tenant,case.project,task,'a'*64,case.users['owner']))
        c.execute("INSERT INTO authorization_records(id,tenant_id,project_id,subject,basis,approved_by,valid_from,valid_until) VALUES(%s,%s,%s,'fixture','fixture','fixture',clock_timestamp(),clock_timestamp()+interval '1 hour')",(old_auth,case.tenant,case.project))
        c.execute("INSERT INTO scope_policy_versions(policy_id,version,tenant_id,project_id,authorization_id,scope,policy_hash) VALUES(%s,1,%s,%s,%s,'{}',%s)",(policy,case.tenant,case.project,old_auth,'b'*64))
        c.execute("INSERT INTO tasks(id,tenant_id,project_id,user_id,draft,input_digest,policy_id,policy_version,policy_hash,effective_scope) VALUES(%s,%s,%s,%s,'{}',%s,%s,1,%s,'{}')",(old,case.tenant,case.project,case.users['owner'],'b'*64,policy,'b'*64))
    async def run():
        async with case.client() as (client,app):
            if not any(getattr(route,'path','').endswith('/agent-runs') for route in app.routes): register_execution_routes(app)
            store=ExecutionStore(app.state.runtime.authority)
            args=dict(user_id=UUID(case.users['owner']),permissions_version=1,project_id=UUID(case.project),task_id=task,idempotency_key=uuid4(),expected_version=1,request_digest='c'*64,trace_id=uuid4())
            with pytest.raises(InvalidTransition): await store.start_command(**args)
            with pytest.raises(InvalidTransition): await store.start_command(**dict(args,task_id=old,idempotency_key=uuid4()))
            service_config={'ready':True,'profile_id':'closed-fixture-v1','fixture_origins':['http://fixture.invalid'],'model_profile_version_id':str(model),'unexpected_secret':'never snapshot'}
            with case.database.connect() as c:
                c.execute("INSERT INTO execution_services(id,instance_id,config) VALUES('core',%s,%s)",(uuid4(),json.dumps(service_config)))
                c.execute("UPDATE model_versions SET state='retired' WHERE id=%s",(model,))
            receipt=await store.start_command(**args)
            assert receipt['kind']=='start' and receipt['accepted_task_version']==2
            with case.database.connect() as c:
                c.execute("UPDATE execution_services SET heartbeat_at=clock_timestamp()-interval '1 hour'")
                row=c.execute('SELECT execution_snapshot FROM task_executions WHERE task_id=%s',(task,)).fetchone()[0]
                assert 'unexpected_secret' not in row['config']
                assert c.execute('SELECT state,execution_epoch FROM tasks WHERE id=%s',(task,)).fetchone()==('provisioning',1)
            assert await store.start_command(**args)==receipt
            prefix=f'/api/v1/projects/{case.project}/tasks/{task}'
            for suffix in ('agent-runs','tool-calls','artifacts'):
                response=await client.get(prefix+'/'+suffix)
                assert response.status_code==200,response.text
                assert response.json()=={'items':[],'next_cursor':None}
            response=await client.get(prefix+'/blackboard')
            assert response.status_code==200,response.text
            assert response.json()['state']=='pending' and response.json()['graph'] is None
            response=await client.get(prefix+'/result')
            assert response.status_code==200,response.text
            assert response.json()['model_spend'] is None
            with pytest.raises(ResourceNotFound): await store.result(user_id=UUID(case.users['outsider']),project_id=UUID(case.project),task_id=task)
    asyncio.run(run())
