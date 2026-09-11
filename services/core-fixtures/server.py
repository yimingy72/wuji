"""Closed HTTP target and deterministic OpenAI-compatible model fixture.

No outbound HTTP, model SDK or inference occurs in this fixture process.
"""
from __future__ import annotations
import json
import os
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import yaml
import web_assessment_model

TARGET_ORIGIN = os.environ.get('WUJI_FIXTURE_ORIGIN', 'http://wuji-core-fixtures:8000').rstrip('/')
SHARED_PATH = '/workspace/shared/handoff.txt'
PROOF = 'wuji-shared-handoff-v1'

def decode_content(value):
    if isinstance(value,list): value = '\n'.join(x.get('text','') for x in value if isinstance(x,dict))
    if isinstance(value,str):
        try: return json.loads(value)
        except (ValueError, TypeError): return value
    return value

def tool_observations(messages):
    names = {}
    observations = []
    for message in messages:
        for call in message.get('tool_calls',[]):
            names[call['id']] = call['function']['name']
        if message.get('role') == 'tool':
            observations.append((names.get(message.get('tool_call_id')), decode_content(message.get('content',''))))
    return observations

def unwrap(value):
    if isinstance(value,dict) and 'result' in value: return value['result']
    return value

def tool(name,args):
    return {'role':'assistant','content':None,'tool_calls':[{'id':'call_'+uuid.uuid4().hex,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}

def answer(data):
    return {'role':'assistant','content':json.dumps({'accepted':True,'data':data},ensure_ascii=False)}

def model_response(request):
    w1=web_assessment_model.model_response(request)
    if w1 is not None:return w1
    messages=request.get('messages',[])
    text='\n'.join(str(m.get('content','')) for m in messages if m.get('role') in ('system','user'))
    phase_match=re.search(r'"phase"\s*:\s*"(bootstrap|reason|explore)"',text)
    if not phase_match:
        # Native LiteLLM's explicit connection check has no Wuji Agent assignment.
        return {'role':'assistant','content':'fixture connection ok'}
    phase=phase_match.group(1)
    observations=tool_observations(messages)
    seen={name:unwrap(value) for name,value in observations}
    if phase=='bootstrap':
        target=TARGET_ORIGIN+'/'
        marker='Wuji stage contract: '
        if marker in text:
            try:
                contract,_=json.JSONDecoder().raw_decode(text.split(marker,1)[1])
                supplied=urlparse(contract.get('origin',''))
                allowed=urlparse(TARGET_ORIGIN)
                if supplied.scheme==allowed.scheme and supplied.netloc==allowed.netloc:
                    target=contract['origin']
            except (ValueError,TypeError):pass
        if 'fixture_http' not in seen: return tool('fixture_http',{'url':target})
        result=seen['fixture_http']
        if not isinstance(result,dict) or not result.get('ok') or 'WUJI_HTTP_FIXTURE_V1' not in result.get('body',''):
            return {'role':'assistant','content':json.dumps({'accepted':False})}
        return answer({'fact':{'description':'HTTP_OBSERVED '+json.dumps(result,ensure_ascii=False)},'complete':{'description':'HTTP observed; shared-file producer and consumer evidence still required.'}})
    if 'graph_read' not in seen: return tool('graph_read',{})
    graph=seen['graph_read']
    if isinstance(graph,str): graph=yaml.safe_load(graph)
    if not isinstance(graph,dict): raise ValueError('graph_snapshot_invalid')
    facts=graph.get('facts',[])
    if isinstance(facts,dict): facts=[dict(v,id=k) if isinstance(v,dict) else {'id':k,'description':v} for k,v in facts.items()]
    producer=[f for f in facts if 'HANDOFF_WRITTEN' in str(f.get('description',''))]
    consumer=[f for f in facts if 'HANDOFF_READ' in str(f.get('description',''))]
    if phase=='reason':
        if not producer:
            return answer({'intents':[{'from':['origin'],'description':'WUJI_PRODUCER: write a shared handoff file and report the actual receipt.'}]})
        if not consumer:
            return answer({'intents':[{'from':[producer[-1]['id']],'description':'WUJI_CONSUMER: read the existing shared handoff file and verify its content from the actual tool result.'}]})
        return answer({'complete':{'from':[consumer[-1]['id']],'description':'Fixture HTTP observation and shared-file handoff were verified by actual controlled tool results. External targets and vulnerability effectiveness were not tested.'}})
    # Explore prompt's current Intent section selects the role; existing graph mentions do not.
    current_text='\n'.join(str(m.get('content','')) for m in messages if m.get('role')=='user')
    consumer_role='WUJI_CONSUMER:' in current_text
    if consumer_role:
        if 'workspace_read' not in seen: return tool('workspace_read',{'path':SHARED_PATH})
        result=seen['workspace_read']
        if not isinstance(result,dict) or not result.get('ok') or result.get('content')!=PROOF:
            return {'role':'assistant','content':json.dumps({'accepted':False})}
        return answer({'description':'HANDOFF_READ '+json.dumps(result,ensure_ascii=False)})
    if 'workspace_write' not in seen: return tool('workspace_write',{'path':SHARED_PATH,'content':PROOF})
    result=seen['workspace_write']
    if not isinstance(result,dict) or not result.get('ok') or result.get('bytes')!=len(PROOF):
        return {'role':'assistant','content':json.dumps({'accepted':False})}
    return answer({'description':'HANDOFF_WRITTEN '+json.dumps(result,ensure_ascii=False)})

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send_json(self,status,body):
        payload=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=='/delay': time.sleep(min(60,max(0,float(parse_qs(parsed.query).get('seconds',['30'])[0]))))
        if parsed.path in ('/','/api/marker','/delay'):
            return self.send_json(200,{'marker':'WUJI_HTTP_FIXTURE_V1','path':parsed.path,'synthetic':True})
        if parsed.path in ('/v1/models','/models'):
            return self.send_json(200,{'object':'list','data':[{'id':'wuji-fixture','object':'model','owned_by':'wuji'}]})
        self.send_json(404,{'error':'not_found'})
    def do_POST(self):
        if self.path not in ('/v1/chat/completions','/chat/completions'):return self.send_json(404,{'error':'not_found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>2097152: return self.send_json(413,{'error':'too_large'})
            request=json.loads(self.rfile.read(size))
            message=model_response(request)
        except Exception:return self.send_json(422,{'error':{'message':'fixture_request_invalid','type':'invalid_request_error'}})
        identity='chatcmpl-'+uuid.uuid4().hex
        base={'id':identity,'created':int(time.time()),'model':request.get('model','wuji-fixture')}
        finish='tool_calls' if message.get('tool_calls') else 'stop'
        prompt_tokens=web_assessment_model.prompt_tokens(request)
        usage={'prompt_tokens':prompt_tokens,'completion_tokens':50,'total_tokens':prompt_tokens+50}
        if not request.get('stream'):
            return self.send_json(200,{**base,'object':'chat.completion','choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':usage})
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-cache');self.end_headers()
        delta=dict(message)
        if delta.get('tool_calls'):delta['tool_calls']=[dict(call,index=i) for i,call in enumerate(delta['tool_calls'])]
        chunks=[{**base,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]},
                {**base,'object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':usage},
                {**base,'object':'chat.completion.chunk','choices':[],'usage':usage}]
        for chunk in chunks:self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
        self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8000'))),Handler).serve_forever()
