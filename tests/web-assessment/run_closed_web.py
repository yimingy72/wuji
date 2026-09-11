#!/usr/bin/env python3
"""One explicit synthetic W1 acceptance run; re-entry reconciles original IDs only.

--task-id is read-only continuation: it never creates or starts a task. The 0600
record is written before command transmission. Preserve it after interruptions;
404/unknown command outcomes never authorize a replacement key. HTTP observations
come from the real controlled Task; expected paths/verdicts stay in this acceptance
script and are never sent to the model. No gateway configuration or check occurs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from datetime import datetime,timedelta,timezone
from uuid import UUID,uuid4

import httpx
import psycopg
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/platform'))
from common import atomic_write_json,exclusive_lock,load_manifest,assert_run_ownership
spec=importlib.util.spec_from_file_location('closed_web_setup',ROOT/'scripts/platform/core-fixture-setup.py')
setup_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup_module)
TARGET='http://wuji-web-assessment-lab:8000/'
PROFILE='closed-web-assessment-v1'

class CheckFailed(RuntimeError):pass

def require(condition,message):
    if not condition:raise CheckFailed(message)

def uuid(value):return str(UUID(str(value)))

def compaction_counts(outputs):
    """Inspect native JSONL locally; never return prompts, summaries or tool bodies."""
    ended=after=0
    tables=[]
    for output in outputs:
        compacted=False
        for line in (output or '').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if not isinstance(event,dict):continue
            if event.get('type')=='compaction_end' and event.get('result') and not event.get('aborted',False):
                ended+=1;compacted=True
            if event.get('type')=='message_end' and event.get('message',{}).get('customType')=='wuji_tool_table_verified':
                details=event['message'].get('details',{})
                if details.get('stage')=='after_compaction':tables.append(details.get('tool_names',[]))
            if compacted and event.get('type') in {'tool_execution_start','tool_execution_end'} and event.get('toolName') in {'task_read','assessment_read','graph_read'}:
                after+=1
    required={'task_read','assessment_read','evidence_read','graph_read'}
    forbidden={'bash','read','write','edit'}
    require(bool(tables),'post-compaction tool table audit missing')
    require(all(isinstance(names,list) and required<=set(names) and not forbidden.intersection(names) for names in tables),'post-compaction tool table differs or exposes default local tools')
    return {'successful_compactions':ended,'read_tool_events_after_compaction':after,
            'post_compaction_tool_audits':len(tables),'post_compaction_tools':sorted({name for names in tables for name in names})}


class Acceptance:
    def __init__(self,args):
        self.args=args;self.run=load_manifest(args.run_file);assert_run_ownership(self.run)
        require(self.run['profile']=='test' and self.run['namespace']=='wuji-test','only owned test/wuji-test is allowed')
        self.identity={k:self.run[k] for k in ('run_id','source_sha','repository_root')}
        self.identity.update(mode='synthetic',profile_id=PROFILE)
        setup_path=args.run_file.with_name('core-fixture-setup-'+self.run['run_id']+'.json')
        setup=setup_module.private_record(setup_path)
        require(setup.get('complete') is True and setup.get('published') is True,'published setup record required')
        require(setup.get('profile_id')==PROFILE and setup.get('compaction_probe') is True,'W1 compaction probe setup required')
        require(all(setup.get(k)==self.run[k] for k in ('run_id','source_sha','repository_root')),'setup ownership mismatch')
        self.model=uuid(setup['model_profile_version_id'])
        self.tenant=uuid(setup['tenant_id']);self.project=uuid(setup['project_id'])
        self.base=f'/api/v1/projects/{self.project}'
        if args.record_out.exists() or args.record_out.is_symlink():
            self.record=setup_module.private_record(args.record_out)
            require(all(self.record.get(k)==v for k,v in self.identity.items()),'acceptance record ownership mismatch')
        else:
            self.record={**self.identity,'stages':{}}
            self.save()
        if args.task_id:
            require(not self.record.get('task_id') or self.record['task_id']==str(args.task_id),'existing task ID differs')
            self.record['task_id']=str(args.task_id);self.save()
        self.readonly=bool(args.task_id or self.record.get('task_id') or 'create' in self.record['stages'])
        self.setup=setup_module.Setup(args.run_file,PROFILE,True)
        self.setup.login()
        model=self.get(f'/api/v1/tenants/{self.tenant}/model-profile-versions/{self.model}')
        require(model['state']=='published' and model['sync_state']=='synced','synthetic model is not published/synced')
        price=model['config']['pricing']
        require(model['config']['model_id']=='wuji-fixture' and price['input_per_million']=='1' and price['output_per_million']=='2' and price['cache_mode']=='standard_input','synthetic model configuration differs')
        service=self.get(f"/api/v1/tenants/{self.tenant}/model-service-versions/{model['config']['service_version_id']}")
        require(service['config']['base_url']=='http://wuji-core-fixtures:8000/v1','synthetic upstream differs')

    def save(self):atomic_write_json(self.args.record_out,self.record)
    def request(self,method,path,**kwargs):
        try:response=self.setup.client.request(method,self.setup.base+path,**kwargs)
        except httpx.HTTPError:raise CheckFailed('HTTP transport outcome unknown; retain original record and keys') from None
        require(response.status_code in {200,202},f'{method} {path.split("?")[0]} HTTP {response.status_code}')
        return response
    def get(self,path,**kwargs):return self.request('GET',path,**kwargs).json()
    def page(self,path,**params):
        output=[];cursor=None
        for _ in range(20):
            page=self.get(path,params=dict(params,limit=100,**({'cursor':cursor} if cursor else {})))
            output+=page['items'];cursor=page['next_cursor']
            if not cursor:return output
        raise CheckFailed('bounded pagination exceeded')
    def command(self,stage,path,body):
        saved=self.record['stages'].get(stage)
        if saved:
            receipt=self.get(self.base+'/command-keys/'+saved['key'])
        else:
            saved={'key':str(uuid4()),'state':'sent'}
            self.record['stages'][stage]=saved;self.save()
            receipt=self.request('POST',path,json=body,headers={'Idempotency-Key':saved['key']}).json()
        require(receipt['idempotency_key']==saved['key'] and receipt['kind']==stage,'command receipt binding mismatch')
        require(receipt['project_id']==self.project,'command project mismatch')
        saved.update(state='accepted',command_id=receipt['command_id'],task_id=receipt['task_id'])
        self.record['task_id']=receipt['task_id'];self.save()
        return receipt
    def create_start(self):
        if self.readonly:
            if not self.record.get('task_id'):
                self.command('create',self.base+'/tasks',None)
            return
        if not self.record.get('task_id'):
            if 'create' in self.record['stages']:
                self.command('create',self.base+'/tasks',None)
            else:
                if 'draft' not in self.record:
                    self.record['draft']={'id':str(uuid4()),'content':{'schema_version':'2.0','scenario':'web_single',
                        'name':'Closed Web assessment acceptance','objective':'评估授权实验站点可发现资源的匿名HTTP响应配置，保留条件与限制。',
                        'goal_template':None,'completion_criteria':['记录有限资源的实际观察、验证结论及未完成原因。'],
                        'supplemental_hints':'','entry_url':TARGET,'model_profile_version_id':self.model,'budget_usd':'1',
                        'authorization':{'schema_version':'1.0','includes':[{'host':'wuji-web-assessment-lab','include_subdomains':False,'endpoint':{'scheme':'http','port':8000}}],
                            'excludes':[],'valid_until':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}}}
                    self.save()
                draft=self.record['draft']
                saved=self.request('PUT',self.base+'/task-drafts/'+draft['id'],json={'expected_version':0,'content':draft['content']}).json()
                preview=self.request('POST',self.base+'/task-creation-previews',json={'draft_id':draft['id'],'draft_version':saved['version']}).json()
                require(preview['can_create'] is True,'creation preview blocked')
                self.command('create',self.base+'/tasks',{'creation_kind':'saved_web_draft','draft_id':draft['id'],'draft_version':saved['version'],
                    'preview_id':preview['preview_id'],'input_digest':preview['input_digest'],'scope_confirmation':{'accepted':True,'authorization_digest':preview['authorization_digest']}})
        task=self.get(self.task_path())['task']
        if 'start' in self.record['stages']:
            self.command('start',self.task_path()+'/commands',None)
        elif task['state']=='ready':
            self.command('start',self.task_path()+'/commands',{'action':'start','expected_version':task['version']})
        else:require(task['state'] in {'provisioning','running','completing','completed','reconciling','cancelling','cancelled'},'unexpected resumed task state')
    def task_path(self):return self.base+'/tasks/'+uuid(self.record['task_id'])

    def verify(self):
        self.create_start();path=self.task_path();deadline=time.monotonic()+180
        while True:
            remaining=deadline-time.monotonic()
            require(remaining>0,'task did not reach terminal state within 180 seconds; continue with original Task ID')
            task=self.get(path,timeout=min(10,remaining))['task']
            require(not self.readonly or task['state']!='ready','existing Task is ready; continuation is read-only and will not start it')
            require(task['target_url']==TARGET,'existing Task target differs from the fixed lab')
            if task['state'] in {'completed','cancelled'}:break
            require(time.monotonic()<deadline,'task did not reach terminal state within 180 seconds; continue with original Task ID')
            time.sleep(1)
        require(task['creation_config']['model']['id']==self.model and task['creation_config']['budget_usd']=='1','Task model/budget snapshot differs')
        require(task['state']=='completed' and task['cleanup_state']=='completed','task execution/cleanup did not complete')
        require(task['stop_reason']!='agent_result_incomplete','platform review was incorrectly treated as Agent failure')
        result=self.get(path+'/result');assessment=self.get(path+'/assessment')
        require(result['goal_status']=='unknown','custom Goal must remain unknown')
        require(assessment['outcome']=='partial' and task['assessment_outcome']=='partial','finite assessment must disclose partial outcome')
        expected={'/':('not_reproduced','evaluated'),'/catalog/a':('confirmed','evaluated'),'/catalog/b':('not_reproduced','evaluated'),'/account/view':('unassessed','blocked')}
        actual={item['target_url'].removeprefix(TARGET.rstrip('/')):(item['verdict'],item['state']) for item in assessment['items']}
        require(actual==expected,'finite resource verdict/state mapping differs')
        runs=self.page(path+'/agent-runs')
        require({'bootstrap','reason','explore'} <= {r['phase'] for r in runs},'missing native stage')
        graph=self.get(path+'/blackboard')
        require(graph['state']=='available' and graph['graph']['project']['status']=='stopped','native graph must be stopped, not completed')
        require(len(graph['graph']['facts'])>2,'native observed Facts missing')
        artifacts={a['id']:a for a in self.page(path+'/artifacts')};checked=set();links=0
        for verification in self.page(path+'/verifications'):
            detail=self.get(path+'/verifications/'+verification['id'])
            for evidence in detail['evidence']:
                links+=1
                observations=self.get(path+'/observations',params={'observation_id':evidence['observation_id']})['items']
                require(len(observations)==1,'evidence observation lookup did not resolve exactly once')
                observation=observations[0]
                require(evidence['artifact_id']==observation['artifact_id'],'evidence metadata Artifact binding differs')
                contents={}
                for aid in (observation['artifact_id'],observation['body_artifact_id']):
                    require(aid in artifacts,'observation Artifact absent from Task list')
                    data=self.request('GET',path+'/artifacts/'+aid+'/content').content
                    require(len(data)==artifacts[aid]['size'] and hashlib.sha256(data).hexdigest()==artifacts[aid]['sha256'],'Artifact hash/size mismatch')
                    contents[aid]=data;checked.add(aid)
                envelope=json.loads(contents[observation['artifact_id']])
                require(envelope['body_artifact_id']==observation['body_artifact_id'] and envelope['tool_call_id']==observation['tool_call_id'],'HTTP exchange Artifact binding mismatch')
                body=contents[observation['body_artifact_id']]
                require(hashlib.sha256(body).hexdigest()==observation['body_sha256'] and len(body)==observation['body_bytes'],'HTTP body does not match captured exchange')
        require(links>0,'verification EvidenceLinks missing')
        # Explicit database name prevents accidentally inspecting the management DB.
        dsn=self.run['credentials']['database']['admin_dsn'].replace('postgresql+psycopg://','postgresql://',1)
        with psycopg.connect(dsn,dbname=self.run['database']['name'],row_factory=dict_row) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            params=(self.tenant,self.project,self.record['task_id'])
            where='tenant_id=%s AND project_id=%s AND task_id=%s'
            reviews=connection.execute('SELECT decision,reason FROM completion_reviews WHERE '+where,params).fetchall()
            attempts=connection.execute('SELECT attempt FROM runtime_attempts WHERE '+where,params).fetchall()
            outputs=connection.execute('SELECT output FROM agent_runs WHERE '+where,params).fetchall()
            failures=connection.execute("SELECT count(*) AS n FROM task_events WHERE "+where+" AND summary LIKE %s",params+('%agent_result_incomplete%',)).fetchone()['n']
        require(len(attempts)==1 and attempts[0]['attempt']==1,'Task must use exactly one runtime attempt')
        require(any(r['decision']=='needs_followup' for r in reviews),'persistent needs_followup review missing')
        require(failures==0,'unexpected Agent incomplete event')
        counts=compaction_counts([row['output'] for row in outputs])
        require(counts['successful_compactions']>=1,'native compaction_end result missing or aborted')
        require(counts['read_tool_events_after_compaction']>=1,'no actual persisted-record read tool after compaction')
        return {'ok':True,'source_sha':self.run['source_sha'],'run_id':self.run['run_id'],'task_id':self.record['task_id'],
            'task_url':self.setup.base+f'/projects/{self.project}/tasks/{self.record["task_id"]}','exit_code':0,
            'resources':len(actual),'agent_runs':len(runs),'runtime_attempts':len(attempts),'completion_reviews':len(reviews),
            'evidence_links':links,'verified_artifacts':len(checked),**counts,
            'limitations':['Synthetic protocol and real native compaction mechanics only; not real-model memory or penetration effectiveness.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-file',type=Path,required=True)
    parser.add_argument('--record-out',type=Path,required=True)
    parser.add_argument('--mode',choices=['synthetic'],required=True)
    parser.add_argument('--task-id',type=UUID)
    args=parser.parse_args()
    if not args.run_file.is_absolute() or not args.record_out.is_absolute():parser.error('paths must be absolute')
    acceptance=None
    try:
        with exclusive_lock(args.record_out.with_name('.'+args.record_out.name+'.lock')):
            acceptance=Acceptance(args);report=acceptance.verify()
            acceptance.record['report']=report;acceptance.save()
            atomic_write_json(args.record_out.with_name(args.record_out.stem+'.report.json'),report)
            print(json.dumps(report,ensure_ascii=False))
        return 0
    except Exception as error:
        message=str(error) if isinstance(error,CheckFailed) else 'acceptance failed; private diagnostic withheld, retain original task/command record'
        print(json.dumps({'ok':False,'exit_code':1,'error':message}),file=sys.stderr)
        return 1
    finally:
        if acceptance is not None:acceptance.setup.client.close()

if __name__=='__main__':raise SystemExit(main())
