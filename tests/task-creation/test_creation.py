import asyncio
import json
from datetime import UTC,datetime,timedelta
from uuid import UUID,uuid4
import pytest
from wuji_api.drafts import SaveDraftRequest
from wuji_api.task_authorization import TaskAuthorization,permits_url
from wuji_api.task_creation_store import CreationStore
from wuji_api.task_creation import NewCreateTaskRequest
from wuji_api.tasks import command_request_digest
from wuji_api.database import IdempotencyConflict, ResourceNotFound

def test_legacy_and_authorization():
    old=SaveDraftRequest.model_validate({'expected_version':0,'content':{'scenario':'web_single','constraints':'do not leave /old'}}).content.model_dump(mode='json')
    assert old['constraints']=='do not leave /old' and 'authorization' not in old and 'completion_criteria' not in old
    scope=TaskAuthorization.model_validate({'includes':[{'host':'EXAMPLE.COM','include_subdomains':True,'endpoint':{'scheme':'https','port':443}}], 'excludes':[{'host':'excluded.example.com','endpoints':'all_included'}]}).model_dump(mode='json')
    assert permits_url(scope,'https://example.com/any/path')
    assert not permits_url(scope,'https://excluded.example.com/')
    assert not permits_url(scope,'http://example.com/')
    for host in ('example.com:80','example.com/path','user@example.com'):
        with pytest.raises(ValueError): TaskAuthorization.model_validate({'includes':[{'host':host,'endpoint':{'scheme':'http','port':80}}]})

def test_real_creation_replay_snapshot_and_owner(draft_case):
    case=draft_case
    sid,pid,sd,pd=uuid4(),uuid4(),uuid4(),uuid4()
    config={'service_version_id':str(sid),'model_id':'fixture','context_window':4096,'max_output_tokens':512,'timeout_seconds':30,'pricing':{'source':'fixture company tariff','input_per_million':'1','output_per_million':'2','cache_mode':'standard_input'}}
    with case.database.connect() as c:
        for did,vid,kind,conf,service in [(sd,sid,'service',{'protocol':'openai','base_url':'http://fixture.invalid'},None),(pd,pid,'profile',config,sid)]:
            c.execute('INSERT INTO model_definitions(id,tenant_id,kind,name) VALUES(%s,%s,%s,%s)',(did,case.tenant,kind,'Fixture'))
            c.execute("INSERT INTO model_versions(id,tenant_id,kind,definition_id,number,name,config,service_version_id,gateway_instance_id,native_id,request_digest,state,sync_state) VALUES(%s,%s,%s,%s,1,'Fixture',%s,%s,%s,%s,%s,'published','synced')",(vid,case.tenant,kind,did,json.dumps(conf),service,uuid4(),str(vid),'a'*64))
    async def run():
        async with case.client() as (client,app):
            draft_id=uuid4(); user=UUID(case.users['owner']); project=UUID(case.project)
            body={'expected_version':0,'content':{'schema_version':'2.0','scenario':'web_single','name':'Fixture','objective':'Observe fixture','completion_criteria':['Record response'],'entry_url':'http://fixture.invalid/test','model_profile_version_id':str(pid),'budget_usd':'1','authorization':{'includes':[{'host':'fixture.invalid','endpoint':{'scheme':'http','port':80}}],'valid_until':(datetime.now(UTC)+timedelta(hours=1)).isoformat()}}}
            response=await client.put(case.path(draft_id),json=body)
            assert response.status_code==200,response.text
            assert response.json()['selected_model_summary']['id']==str(pid)
            store=CreationStore(app.state.runtime.authority)
            preview=await store.preview(user_id=user,permissions_version=1,project_id=project,draft_id=draft_id,draft_version=1)
            assert preview['can_create'],preview['blockers']
            request=NewCreateTaskRequest(creation_kind='saved_web_draft',draft_id=draft_id,draft_version=1,preview_id=preview['preview_id'],input_digest=preview['input_digest'],scope_confirmation={'accepted':True,'authorization_digest':preview['authorization_digest']})
            digest=command_request_digest(kind='create',project_id=project,task_id=None,request=request.model_dump(mode='json'))
            args=dict(user_id=user,permissions_version=1,project_id=project,idempotency_key=uuid4(),body=request,request_digest=digest,trace_id=uuid4())
            first,second=await asyncio.gather(store.create_command(**args),store.create_command(**args))
            assert first==second
            with case.database.connect() as c:
                row=c.execute('SELECT state,creation_config FROM tasks WHERE id=%s',(first['task_id'],)).fetchone()
                assert row[0]=='ready' and row[1]['model']['config']['pricing']['source']=='fixture company tariff'
                c.execute("UPDATE model_versions SET state='revoked' WHERE id=%s",(pid,))
                c.execute("UPDATE task_creation_previews SET expires_at=created_at+interval '1 microsecond' WHERE id=%s",(preview['preview_id'],))
            assert await store.create_command(**args)==first
            with pytest.raises(IdempotencyConflict): await store.create_command(**dict(args,request_digest='b'*64))
            with pytest.raises(ResourceNotFound): await store.preview(user_id=UUID(case.users['peer']),permissions_version=1,project_id=project,draft_id=draft_id,draft_version=1)
            with case.database.connect() as c:
                assert c.execute('SELECT count(*) FROM tasks WHERE project_id=%s',(project,)).fetchone()[0]==1
                assert c.execute('SELECT count(*) FROM task_events WHERE task_id=%s',(first['task_id'],)).fetchone()[0]==1
    asyncio.run(run())
