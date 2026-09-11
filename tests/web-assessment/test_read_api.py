"""One owned PostgreSQL HTTP read path; no target or model requests."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

spec=importlib.util.spec_from_file_location('assessment_owned_pg',Path(__file__).parents[1]/'control-plane'/'conftest.py')
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
draft_database=module.draft_database
draft_case=module.draft_case


def test_owned_read_api_and_bound_cursor(draft_case):
    case=draft_case
    task,auth,execution,command,run,call,artifact,body_artifact,plan,coverage,verification,result=[uuid4() for _ in range(12)]
    tenant,project,user=case.tenant,case.project,case.users['owner']
    with case.database.connect() as c:
        c.execute("INSERT INTO tasks(id,tenant_id,project_id,user_id,draft,input_digest,effective_scope,task_kind,state,task_authorization_id,creation_config_snapshot_id,creation_config) VALUES(%s,%s,%s,%s,'{}',%s,'{}','web_assessment','ready',%s,%s,'{}')",(task,tenant,project,user,'a'*64,auth,uuid4()))
        c.execute("INSERT INTO task_authorizations(id,tenant_id,project_id,task_id,scope,scope_hash,valid_from,valid_until,confirmed_by,permissions_version,confirmation_text_version,confirmed_at) VALUES(%s,%s,%s,%s,'{}',%s,clock_timestamp(),clock_timestamp()+interval '1 hour',%s,1,'1.0',clock_timestamp())",(auth,tenant,project,task,'a'*64,user))
        c.execute("INSERT INTO command_receipts(id,tenant_id,project_id,user_id,idempotency_key,kind,task_id,request_digest,disposition,accepted_task_version) VALUES(%s,%s,%s,%s,%s,'create',%s,%s,'accepted',1)",(command,tenant,project,user,uuid4(),task,'a'*64))
        c.execute("INSERT INTO task_executions(id,tenant_id,project_id,task_id,start_command_id,epoch,service_instance_id,execution_snapshot) VALUES(%s,%s,%s,%s,%s,1,%s,'{}')",(execution,tenant,project,task,command,uuid4()))
        c.execute("INSERT INTO runtime_attempts(id,tenant_id,project_id,task_id,execution_id,attempt,namespace,pod_name,config) VALUES(%s,%s,%s,%s,%s,1,'test','fixture','{}')",(uuid4(),tenant,project,task,execution))
        c.execute("INSERT INTO agent_runs(id,tenant_id,project_id,task_id,execution_id,runtime_attempt,execution_epoch,phase,worker_profile_id,worker_name,assignment) VALUES(%s,%s,%s,%s,%s,1,1,'explore','fixture',%s,'{}')",(run,tenant,project,task,execution,str(run)))
        c.execute("INSERT INTO tool_calls(id,tenant_id,project_id,task_id,agent_run_id,request_id,request_digest,runtime_attempt,execution_epoch,tool,args) VALUES(%s,%s,%s,%s,%s,'fixture',%s,1,1,'http_request','{}')",(call,tenant,project,task,run,'a'*64))
        for aid in (artifact,body_artifact):
            c.execute("INSERT INTO task_artifacts(id,tenant_id,project_id,task_id,tool_call_id,kind,name,mime,size,sha256,storage_key) VALUES(%s,%s,%s,%s,%s,'observation','fixture','application/json',0,%s,'private-storage')",(aid,tenant,project,task,call,'a'*64))
        exchange={'schema_version':'http.exchange.v1','url':'http://fixture.invalid/resource','method':'OPTIONS','request_headers':{'origin':'https://probe.invalid'},'status':200,'response_headers':{},'body_bytes':0,'body_sha256':'a'*64,'body_encoding':'client-decoded','complete':True,'termination':'complete','redacted_headers':[],'started_at':'2026-09-11T00:00:00Z','finished_at':'2026-09-11T00:00:01Z'}
        observation=uuid4()
        c.execute("INSERT INTO observations(id,tenant_id,project_id,task_id,tool_call_id,agent_run_id,runtime_attempt,artifact_id,body_artifact_id,target_url,method,metadata) VALUES(%s,%s,%s,%s,%s,%s,1,%s,%s,%s,'OPTIONS',%s)",(observation,tenant,project,task,call,run,artifact,body_artifact,exchange['url'],json.dumps(exchange)))
        for vid,submission in ((verification,call),(uuid4(),uuid4())):
            if submission!=call:
                c.execute("INSERT INTO tool_calls(id,tenant_id,project_id,task_id,agent_run_id,request_id,request_digest,runtime_attempt,execution_epoch,tool,args) VALUES(%s,%s,%s,%s,%s,'other',%s,1,1,'verification_submit','{}')",(submission,tenant,project,task,run,'b'*64))
            c.execute("INSERT INTO verification_runs(id,tenant_id,project_id,task_id,coverage_item_id,target_url,rule_id,claim,agent_run_id,submission_call_id) VALUES(%s,%s,%s,%s,%s,%s,'cors-reflection-v1','Bounded claim',%s,%s)",(vid,tenant,project,task,coverage,exchange['url'],run,submission))
        c.execute("INSERT INTO verification_result_revisions(id,tenant_id,project_id,task_id,verification_run_id,revision,verdict,reason,limitations) VALUES(%s,%s,%s,%s,%s,1,'inconclusive','One observation','[]')",(result,tenant,project,task,verification))
        c.execute("INSERT INTO evidence_links(id,tenant_id,project_id,task_id,verification_result_id,observation_id,artifact_id,relation,selector) VALUES(%s,%s,%s,%s,%s,%s,%s,'limits','{}')",(uuid4(),tenant,project,task,result,observation,artifact))
    async def check():
        base=f'/api/v1/projects/{project}/tasks/{task}'
        async with case.client() as (client,_):
            r=await client.get(base+'/assessment');assert r.status_code==200,r.text
            assert r.json()['state']=='not_assessed'
            with case.database.connect() as c:
                c.execute("INSERT INTO assessment_plans(id,tenant_id,project_id,task_id,revision,progress_digest,snapshot) VALUES(%s,%s,%s,%s,1,%s,%s)",(plan,tenant,project,task,'c'*64,json.dumps({'profile_id':'closed-web-assessment-v1','outcome':'partial','items':[]})))
            value=(await client.get(base+'/assessment')).json()
            assert value['plan_id']==str(plan) and value['revision']==1
            r=await client.get(base+'/observations');assert r.status_code==200,r.text
            obs=r.json()['items'][0]
            assert obs['method']=='OPTIONS' and obs['response_status']==200 and obs['body_artifact_id']==str(body_artifact)
            assert 'metadata' not in obs and 'body_base64' not in obs and 'storage_key' not in obs
            selected=await client.get(base+'/observations',params={'observation_id':str(observation)})
            assert selected.status_code==200 and selected.json()['items']==[obs]
            missing=await client.get(base+'/observations',params={'observation_id':str(uuid4())})
            assert missing.status_code==200 and missing.json()=={'items':[],'next_cursor':None}
            r=await client.get(base+'/verifications',params={'limit':1,'coverage_item_id':str(coverage)});assert r.status_code==200,r.text
            cursor=r.json()['next_cursor'];assert cursor
            assert (await client.get(base+'/verifications',params={'limit':1,'cursor':cursor})).status_code==422
            assert (await client.get(base+'/verifications',params={'limit':1,'coverage_item_id':str(coverage),'cursor':cursor})).status_code==200
            r=await client.get(base+'/verifications/'+str(verification));assert r.status_code==200,r.text
            assert r.json()['verification']['latest_result']['id']==str(result)
            assert len(r.json()['evidence'])==1
            assert (await client.get(base+'/verifications/'+str(uuid4()))).status_code==404
        async with case.client('outsider') as (client,_):
            assert (await client.get(base+'/assessment')).status_code==404
            assert (await client.get(base+'/verifications/'+str(verification))).status_code==404
    asyncio.run(check())
