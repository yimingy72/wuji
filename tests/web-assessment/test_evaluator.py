"""Real SQL/rules over explicitly simulated runtime/HTTP receipts, not a network test."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event
from wuji_api.database_admin import execution_role_name

root=Path(__file__).parents[2]
sys.path.insert(0,str(root/'services/execution-control'))
from assessment import WebAssessment, AssessmentError
from assessment_rules import PROFILE_ID,RULE_ID
from artifacts import ArtifactFileStore
from store import Store

spec=importlib.util.spec_from_file_location('evaluator_owned_pg',root/'tests/control-plane/conftest.py')
fixtures=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixtures;spec.loader.exec_module(fixtures)
draft_database=fixtures.draft_database
draft_case=fixtures.draft_case


class SimulatedRuntime:
    """Seed only controlled ledger prerequisites; no subprocess or HTTP execution."""
    def __init__(self,case):self.case=case;self.tasks={}
    def task(self):
        task,auth,command,execution=uuid4(),uuid4(),uuid4(),uuid4()
        case=self.case
        scope={'schema_version':'1.0','includes':[{'host':'fixture.invalid','include_subdomains':False,'endpoint':{'scheme':'http','port':80}}],'excludes':[],'valid_until':'2099-01-01T00:00:00Z'}
        creation={'actual_input':{'entry_url':'http://fixture.invalid/'},'authorization':scope}
        with case.database.connect() as c:
            c.execute("INSERT INTO tasks(id,tenant_id,project_id,user_id,draft,input_digest,effective_scope,task_kind,state,execution_epoch,task_authorization_id,creation_config_snapshot_id,creation_config) VALUES(%s,%s,%s,%s,'{}',%s,'{}','web_assessment','running',1,%s,%s,%s)",(task,case.tenant,case.project,case.users['owner'],'a'*64,auth,uuid4(),json.dumps(creation)))
            c.execute("INSERT INTO task_authorizations(id,tenant_id,project_id,task_id,scope,scope_hash,valid_from,valid_until,confirmed_by,permissions_version,confirmation_text_version,confirmed_at) VALUES(%s,%s,%s,%s,%s,%s,clock_timestamp(),'2099-01-01',%s,1,'1.0',clock_timestamp())",(auth,case.tenant,case.project,task,json.dumps(scope),'a'*64,case.users['owner']))
            c.execute("INSERT INTO command_receipts(id,tenant_id,project_id,user_id,idempotency_key,kind,task_id,request_digest,disposition,accepted_task_version) VALUES(%s,%s,%s,%s,%s,'start',%s,%s,'accepted',1)",(command,case.tenant,case.project,case.users['owner'],uuid4(),task,'a'*64))
            c.execute("INSERT INTO task_executions(id,tenant_id,project_id,task_id,start_command_id,epoch,service_instance_id,execution_snapshot) VALUES(%s,%s,%s,%s,%s,1,%s,%s)",(execution,case.tenant,case.project,task,command,uuid4(),json.dumps({'profile_id':PROFILE_ID})))
            c.execute("INSERT INTO runtime_attempts(id,tenant_id,project_id,task_id,execution_id,attempt,namespace,pod_name,config) VALUES(%s,%s,%s,%s,%s,1,'simulated','not-a-pod','{}')",(uuid4(),case.tenant,case.project,task,execution))
        self.tasks[task]=execution
        return task
    def run(self,task,phase='explore',state='exited'):
        rid=uuid4();case=self.case
        with case.database.connect() as c:
            c.execute("INSERT INTO agent_runs(id,tenant_id,project_id,task_id,execution_id,runtime_attempt,execution_epoch,phase,worker_profile_id,worker_name,state,result_state,assignment,output) VALUES(%s,%s,%s,%s,%s,1,1,%s,'simulated',%s,%s,'synced','{}','SIMULATED persisted proposal')",(rid,case.tenant,case.project,task,self.tasks[task],phase,str(rid),state))
        return {'id':rid,'tenant_id':case.tenant,'project_id':case.project,'task_id':task,'execution_epoch':1,'intent_id':None,'output':'SIMULATED persisted proposal'}
    def call(self,run,tool,args,state='exited'):
        call=dict(run,id=uuid4(),agent_run_id=run['id'],runtime_attempt=1,tool=tool,args=args)
        with self.case.database.connect() as c:
            c.execute("INSERT INTO tool_calls(id,tenant_id,project_id,task_id,agent_run_id,request_id,request_digest,runtime_attempt,execution_epoch,tool,args,state) VALUES(%s,%s,%s,%s,%s,%s,%s,1,1,%s,%s,%s)",(call['id'],run['tenant_id'],run['project_id'],run['task_id'],run['id'],str(call['id']),'a'*64,tool,json.dumps(args),state))
        return call


def exchange(url,body=b'fixture',origin=None,status=200,reflect=False,html=False):
    headers={'content-type':'text/html' if html else 'text/plain'}
    if reflect:headers.update({'access-control-allow-origin':origin,'access-control-allow-credentials':'true'})
    return {'exchange':{'schema_version':'http.exchange.v1','url':url,'method':'GET','request_headers':{'origin':origin} if origin else {},'status':status,'response_headers':headers,'body_base64':base64.b64encode(body).decode(),'body_bytes':len(body),'body_sha256':hashlib.sha256(body).hexdigest(),'body_encoding':'client-decoded','started_at':'2026-09-11T00:00:00Z','finished_at':'2026-09-11T00:00:01Z','complete':True,'termination':'complete','redacted_headers':[]}}


def test_real_evaluator_and_completion_review_ledger(draft_case,tmp_path):
    simulated=SimulatedRuntime(draft_case)
    store=Store(draft_case.database.admin_url)
    # All evaluator queries execute with the actual constrained execution role.
    @event.listens_for(store.engine,'connect')
    def role(dbapi_connection,_record):
        previous=dbapi_connection.autocommit
        dbapi_connection.autocommit=True
        try:
            with dbapi_connection.cursor() as c:c.execute('SET ROLE "'+execution_role_name('draft_project')+'"')
        finally:dbapi_connection.autocommit=previous
    evaluator=WebAssessment(SimpleNamespace(store=store,artifacts=ArtifactFileStore(tmp_path/'artifacts')))
    try:
        assert store.one('SELECT current_user AS role')['role']==execution_role_name('draft_project')
        task=simulated.task();run=simulated.run(task)
        def capture(url,**kw):
            payload=exchange(url,**kw)
            args={'url':url,'method':'GET','headers':payload['exchange']['request_headers']}
            call=simulated.call(run,'http_request',args)
            result=evaluator.capture(call,payload)
            return call,result
        entry,_=capture('http://fixture.invalid/',body=b'<a href="/positive">one</a><a href="/control">two</a><a href="/protected">three</a>',html=True)
        view=evaluator.view(task)
        assert len(view['items'])==4 and len(view['items'])<=11 and view['discovery_state']=='complete'
        captures={}
        for resource,reflect in [('positive',True),('control',False)]:
            captures[resource]=[capture('http://fixture.invalid/'+resource,origin=origin,reflect=reflect)[0] for origin in ('https://probe-a.invalid','https://probe-b.invalid')]
        captures['protected']=[capture('http://fixture.invalid/protected',status=401)[0]]
        def submit(calls,**extra):
            args={'rule_id':RULE_ID,'tool_call_ids':[str(c['id']) for c in calls],**extra}
            call=simulated.call(run,'verification_submit',args)
            return call,args,evaluator.submit(call,run,args)
        results={}
        for target,expected in [('positive','confirmed'),('control','not_reproduced'),('protected','unassessed')]:
            call,args,result=submit(captures[target]);results[target]=result
            assert result['verdict']==expected
            assert evaluator.submit(call,run,args)==result
        assert next(i for i in evaluator.view(task)['items'] if i['target_url'].endswith('/protected'))['state']=='blocked'
        observation=store.one('SELECT * FROM observations WHERE tool_call_id=:id',{'id':entry['id']})
        with store.tx() as c:
            metadata,body=evaluator.checked_observation(c,observation)
        assert hashlib.sha256(body).hexdigest()==metadata['body_sha256']
        for aid in (observation['artifact_id'],observation['body_artifact_id']):
            artifact=store.one('SELECT * FROM task_artifacts WHERE id=:id',{'id':aid})
            raw=evaluator.artifacts.read(artifact['storage_key'])
            assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and len(raw)==artifact['size']
        _,_,correction=submit(captures['positive'],supersedes_result_id=results['positive']['result_id'])
        old=store.one('SELECT * FROM verification_result_revisions WHERE id=:id',{'id':results['positive']['result_id']})
        new=store.one('SELECT * FROM verification_result_revisions WHERE id=:id',{'id':correction['result_id']})
        assert old['verdict']=='confirmed' and old['supersedes_result_id'] is None
        assert str(new['supersedes_result_id'])==results['positive']['result_id'] and old['id']!=new['id']
        foreign=simulated.run(simulated.task())
        bad=simulated.call(foreign,'verification_submit',{})
        with pytest.raises(AssessmentError,match='outside task'):
            evaluator.submit(bad,foreign,{'rule_id':RULE_ID,'tool_call_ids':[str(entry['id'])]})
        ex=store.execution(task);proposal=[['origin'],'review finite evidence','simulated worker']
        first=evaluator.review(ex,simulated.run(task,'reason'),proposal)
        assert (first['decision'],first['attempt_number'])==('needs_followup',1)
        replay_run=store.one('SELECT * FROM agent_runs WHERE id=:id',{'id':first['agent_run_id']})
        assert evaluator.review(ex,replay_run,proposal)['id']==first['id']
        second=evaluator.review(ex,simulated.run(task,'reason'),proposal)
        assert (second['decision'],second['reason'])==('stop_with_results','no_progress')
        capture('http://fixture.invalid/positive',origin='https://new-progress.invalid',reflect=True)
        third=evaluator.review(ex,simulated.run(task,'reason'),proposal)
        assert third['progress_digest']!=first['progress_digest']
        assert (third['decision'],third['attempt_number'])==('needs_followup',1)
        pending=simulated.call(run,'http_request',{'url':'http://fixture.invalid/positive'},state='unknown')
        waiting=evaluator.review(ex,simulated.run(task,'reason'),proposal)
        assert (waiting['decision'],waiting['reason'],waiting['attempt_number'])==('needs_followup','waiting_execution',0)
    finally:
        store.engine.dispose()
