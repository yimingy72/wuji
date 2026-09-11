import importlib.util
from pathlib import Path
from cairn.dispatcher.contracts import validate_bootstrap_execute_payload, validate_reason_payload, validate_explore_payload
spec=importlib.util.spec_from_file_location('fixture_server',Path(__file__).with_name('server.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import json

def request(phase,observations=(),prompt=''):
    messages=[{'role':'system','content':json.dumps({'phase':phase})},{'role':'user','content':prompt}]
    for i,(name,result) in enumerate(observations):
        messages.extend([{'role':'assistant','tool_calls':[{'id':str(i),'function':{'name':name}}]}, {'role':'tool','tool_call_id':str(i),'content':json.dumps(result)}])
    return m.model_response({'messages':messages})
assert request('bootstrap')['tool_calls'][0]['function']['name']=='fixture_http'
bootstrap=request('bootstrap',[('fixture_http',{'result':{'ok':True,'body':'WUJI_HTTP_FIXTURE_V1','status':200}})])
assert validate_bootstrap_execute_payload(json.loads(bootstrap['content']))[0]=='complete'
graph={'facts':[{'id':'origin','description':'fixture'}]}
r=request('reason',[('graph_read',graph)])
assert validate_reason_payload(json.loads(r['content']),True,2)[0]=='intents'
r=request('explore',[('graph_read',graph),('workspace_write',{'result':{'ok':True,'bytes':len(m.PROOF)}})],'WUJI_PRODUCER:')
assert 'HANDOFF_WRITTEN' in validate_explore_payload(json.loads(r['content']))[1]
graph['facts'].append({'id':'fact-produced','description':'HANDOFF_WRITTEN actual tool result'})
r=request('reason',[('graph_read',graph)])
assert json.loads(r['content'])['data']['intents'][0]['from']==['fact-produced']
r=request('explore',[('graph_read',graph),('workspace_read',{'result':{'ok':True,'content':m.PROOF}})],'WUJI_CONSUMER:')
assert 'HANDOFF_READ' in validate_explore_payload(json.loads(r['content']))[1]
graph['facts'].append({'id':'fact-consumed','description':'HANDOFF_READ actual tool result'})
r=request('reason',[('graph_read',graph)])
assert json.loads(r['content'])['data']['complete']['from']==['fact-consumed']
assert json.loads(request('bootstrap',[('fixture_http',{'result':{'ok':False}})])['content'])['accepted'] is False
print('fixture native contracts and observed-result gates passed')
