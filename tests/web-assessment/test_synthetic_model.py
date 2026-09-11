"""Synthetic protocol/compaction probes prove mechanics, not model reasoning quality."""
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4
from cairn.dispatcher.contracts import validate_bootstrap_execute_payload,validate_reason_payload

root=Path(__file__).parents[2]/'services/core-fixtures'
sys.path.insert(0,str(root))
import web_assessment_model as model
spec=importlib.util.spec_from_file_location('w1_model_server',root/'server.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)


def request(phase='reason',feedback=None):
    assignment={'origin':'http://web.test/entry','intent_id':'i1','completion_feedback':feedback}
    return {'messages':[{'role':'system','content':'Wuji stage contract: '+json.dumps({'profile_id':model.PROFILE,'phase':phase,'origin':assignment['origin']})}]},assignment


def observed(req,name,value):
    call='call_'+uuid4().hex
    req['messages'] += [{'role':'assistant','tool_calls':[{'id':call,'function':{'name':name,'arguments':'{}'}}]},
                        {'role':'tool','tool_call_id':call,'content':json.dumps(value)}]


def tool_message(message):
    call=message['tool_calls'][0]['function']
    return call['name'],json.loads(call['arguments'])


def test_reason_platform_feedback_and_actual_verification_flow():
    req,assignment=request()
    assert tool_message(server.model_response(req))[0]=='task_read'
    observed(req,'task_read',assignment)
    assessment={'assessment':{'items':[{'state':'pending','target_url':'http://web.test/unpredictable-resource'}]},'observations':[]}
    observed(req,'assessment_read',assessment)
    graph={'graph':{'facts':[{'id':'origin','description':'entry'}],'intents':[]}}
    observed(req,'graph_read',graph)
    assert 'complete' in json.loads(server.model_response(req)['content'])['data']
    observed(req,'task_read',dict(assignment,completion_feedback={'missing':['pending item']}))
    intent=json.loads(server.model_response(req)['content'])['data']['intents'][0]
    assert json.loads(intent['description'])['target_url']=='http://web.test/unpredictable-resource'
    explore,assignment=request('explore');observed(explore,'task_read',assignment)
    first_id=str(uuid4())
    assessment['observations']=[{'target_url':'http://web.test/unpredictable-resource','method':'GET','request_headers':{'origin':model.PROBES[0]},'response_status':200,'tool_call_id':first_id,'artifact_id':str(uuid4())}]
    observed(explore,'assessment_read',assessment)
    graph['graph']['intents']=[dict(intent,id='i1')];observed(explore,'graph_read',graph)
    name,args=tool_message(server.model_response(explore))
    assert name=='http_request' and args['headers']=={'Origin':model.PROBES[1]}
    second_id=str(uuid4())
    observed(explore,'http_request',{'id':second_id,'state':'exited','result':{'ok':True,'observation_id':str(uuid4()),'artifact_id':str(uuid4()),'exchange':{'url':args['url'],'method':'GET','request_headers':{'origin':model.PROBES[1]},'status':200}}})
    name,args=tool_message(server.model_response(explore))
    assert name=='verification_submit' and args['tool_call_ids']==[first_id,second_id]
    authoritative={'verification_run_id':str(uuid4()),'result_id':str(uuid4()),'verdict':'inconclusive','reason':'actual incomplete evidence','assessment_revision':2}
    observed(explore,'verification_submit',{'result':authoritative})
    fact=json.loads(server.model_response(explore)['content'])['data']['description']
    assert authoritative['result_id'] in fact and authoritative['reason'] in fact


def test_bootstrap_and_anonymous_block_use_observations():
    req,assignment=request('bootstrap');observed(req,'task_read',assignment)
    assert tool_message(server.model_response(req))==('http_request',{'url':assignment['origin'],'method':'GET'})
    observed(req,'http_request',{'result':{'ok':True,'observation_id':str(uuid4()),'artifact_id':str(uuid4()),'body_excerpt':'Actual page'}})
    data=json.loads(server.model_response(req)['content'])['data']
    assert 'fact' in data and 'complete' in data
    kind,validated=validate_bootstrap_execute_payload({'accepted':True,'data':data})
    assert kind=='complete' and '后续有限评估由平台决定' in validated['complete_description']
    req,assignment=request('explore');observed(req,'task_read',assignment)
    call=str(uuid4());target='http://web.test/any-resource'
    observed(req,'assessment_read',{'assessment':{},'observations':[{'target_url':target,'method':'GET','response_status':403,'tool_call_id':call}]})
    observed(req,'graph_read',{'graph':{'facts':[{'id':'origin'}],'intents':[{'id':'i1','description':json.dumps({'target_url':target,'method':'Compare origins'})}]}})
    assert tool_message(server.model_response(req))==('verification_submit',{'rule_id':'cors-reflection-v1','tool_call_ids':[call]})


def test_compaction_probe_does_not_consume_healthcheck_or_change_legacy(monkeypatch):
    monkeypatch.setenv('WUJI_W1_COMPACTION_PROBE','1');monkeypatch.setattr(model,'_probe_used',False);monkeypatch.setattr(model,'_probe_responses',0)
    health={'messages':[{'role':'user','content':'health'}]}
    assert model.prompt_tokens(health)==100 and not model._probe_used
    assert server.model_response(health)['content']=='fixture connection ok'
    legacy={'messages':[{'role':'system','content':'Wuji stage contract: '+json.dumps({'phase':'bootstrap','origin':server.TARGET_ORIGIN+'/'})}]}
    assert tool_message(server.model_response(legacy))[0]=='fixture_http'
    assert model.prompt_tokens(legacy)==100 and not model._probe_used
    req,_=request('bootstrap')
    assert model.prompt_tokens(req)==100 and not model._probe_used
    assert model.prompt_tokens(health)==100 and model._probe_responses==1
    assert model.prompt_tokens(legacy)==100 and model._probe_responses==1
    assert model.prompt_tokens(req)==20000
    assert model.prompt_tokens(req)==100
    summary={'messages':[{'role':'system','content':model.SUMMARY_PREFIX+'\n\nDo NOT continue the conversation.'},{'role':'user','content':model.PROFILE}]}
    reply=server.model_response(summary)
    assert 'tool_calls' not in reply and 'assessment_read' in reply['content']
    assert model.prompt_tokens(summary)==100


def test_reason_does_not_duplicate_open_target_intents():
    req,assignment=request('reason',feedback={'missing':['resources']})
    observed(req,'task_read',assignment)
    targets=['http://web.test/one','http://web.test/two']
    observed(req,'assessment_read',{'assessment':{'items':[{'state':'pending','target_url':target} for target in targets]},'observations':[]})
    graph={'graph':{'facts':[{'id':'origin'}],'intents':[{'id':'i1','to':None,'description':json.dumps({'target_url':targets[0]})}]}}
    observed(req,'graph_read',graph)
    payload=json.loads(server.model_response(req)['content'])
    assert len(payload['data']['intents'])==1
    assert json.loads(payload['data']['intents'][0]['description'])['target_url']==targets[1]
    graph['graph']['intents'].append({'id':'i2','to':None,'description':json.dumps({'target_url':targets[1]})})
    observed(req,'graph_read',graph)
    payload=json.loads(server.model_response(req)['content'])
    assert payload['data']=={'intents':[]}
    assert validate_reason_payload(payload,open_intents_empty=False,max_intents=2)==('noop',None)
