"""Synthetic W1 protocol probe, not autonomous-model or memory-quality evidence.

Uses actual tool observations only. No target answer map or outbound client exists.
Pi 0.73.0 summary identification follows src/core/compaction/utils.ts at that tag.
"""
import json
import os
import threading
import uuid

PROFILE = 'closed-web-assessment-v1'
PROBES = ('https://probe-a.invalid','https://probe-b.invalid')
SUMMARY_PREFIX = 'You are a context summarization assistant. Your task is to read a conversation between a user and an AI coding assistant, then produce a structured summary following the exact format specified.'
_probe_lock = threading.Lock()
_probe_used = False
_probe_responses = 0


def content(value):
    if isinstance(value,list): return '\n'.join(x.get('text','') for x in value if isinstance(x,dict))
    return value if isinstance(value,str) else ''


def contract(request):
    for message in request.get('messages',[]):
        if message.get('role') != 'system': continue
        text=content(message.get('content'))
        marker='Wuji stage contract: '
        if marker in text:
            try:
                value,_=json.JSONDecoder().raw_decode(text.split(marker,1)[1])
                if value.get('profile_id')==PROFILE and value.get('phase') in {'bootstrap','reason','explore'}:return value
            except (ValueError,TypeError,AttributeError):pass
    return None


def is_summary(request):
    return any(m.get('role')=='system' and content(m.get('content')).startswith(SUMMARY_PREFIX)
               for m in request.get('messages',[]))


def prompt_tokens(request):
    global _probe_used, _probe_responses
    if os.environ.get('WUJI_W1_COMPACTION_PROBE')=='1' and contract(request) and not is_summary(request):
        with _probe_lock:
            if not _probe_used:
                _probe_responses += 1
                if _probe_responses == 2:
                    _probe_used=True
                    return 20000
    return 100


def tool(name,args):
    return {'role':'assistant','content':None,'tool_calls':[{'id':'call_'+uuid.uuid4().hex,'type':'function',
            'function':{'name':name,'arguments':json.dumps(args)}}]}


def answer(data):return {'role':'assistant','content':json.dumps({'accepted':True,'data':data},ensure_ascii=False)}
def reject():return {'role':'assistant','content':json.dumps({'accepted':False})}


def observations(request):
    names={};results=[]
    for message in request.get('messages',[]):
        for call in message.get('tool_calls',[]): names[call['id']]=call['function']['name']
        if message.get('role')=='tool':
            try:value=json.loads(content(message.get('content')))
            except (ValueError,TypeError):continue
            results.append((names.get(message.get('tool_call_id')),value))
    return results


def unwrap(value):return value.get('result',value) if isinstance(value,dict) else value


def model_response(request):
    stage=contract(request)
    if is_summary(request):
        # The serialized W1 conversation may be discarded by Pi. Persisted records
        # are recovered through tools, never reconstructed from invented verdicts.
        serialized=json.dumps(request.get('messages',[]))
        if PROFILE not in serialized and not _probe_used:return None
        return {'role':'assistant','content':'## Goal\nContinue the assigned bounded Web assessment.\n## Progress\nConversation compacted; no verdict is asserted by this summary.\n## Next Steps\nCall task_read, assessment_read and graph_read to recover the current assignment, feedback and persisted observations. Reuse tool_call_ids from assessment_read before collecting evidence. Follow the current stage contract.'}
    if stage is None:return None
    history=observations(request)
    seen={name:unwrap(value) for name,value in history}
    phase=stage['phase']
    if 'task_read' not in seen:return tool('task_read',{})
    assignment=seen['task_read']
    if not isinstance(assignment,dict):return reject()
    if phase=='bootstrap':
        exchanges=[unwrap(value) for name,value in history if name=='http_request']
        if not exchanges:return tool('http_request',{'url':assignment.get('origin',stage.get('origin')),'method':'GET'})
        observed=exchanges[-1]
        if not isinstance(observed,dict) or not observed.get('observation_id'):return reject()
        return answer({'fact':{'description':'Actual entry observation: '+json.dumps(observed,ensure_ascii=False)},
                       'complete':{'description':'初始观察已提交，后续有限评估由平台决定。'}})
    if 'assessment_read' not in seen:return tool('assessment_read',{})
    assessment_read=seen['assessment_read']
    if not isinstance(assessment_read,dict):return reject()
    assessment=assessment_read.get('assessment',{})
    if 'graph_read' not in seen:return tool('graph_read',{})
    graph=seen['graph_read']
    if not isinstance(graph,dict) or not isinstance(graph.get('graph'),dict):return reject()
    graph=graph['graph']
    sources=assignment.get('allowed_fact_ids',[fact['id'] for fact in graph.get('facts',[]) if fact['id']!='goal'])
    if not sources:return reject()
    pending=[item for item in assessment.get('items',[]) if item.get('state') in {'pending','not_run'}]
    if phase=='reason':
        open_targets=set()
        for intent in graph.get('intents',[]):
            if intent.get('to') is not None:continue
            try:
                target=json.loads(intent.get('description','')).get('target_url')
                if isinstance(target,str):open_targets.add(target)
            except (ValueError,TypeError,AttributeError):pass
        actionable=[item for item in pending if item['target_url'] not in open_targets]
        if pending and not actionable:return answer({'intents':[]})
        if pending and not assignment.get('completion_feedback'):
            return answer({'complete':{'from':sources,'description':'Request a platform review of the current persisted assessment and remaining work.'}})
        if pending:
            return answer({'intents':[{'from':sources,'description':json.dumps({'method':'Compare two distinct Origin request headers using GET; submit actual observation references for cors-reflection-v1.','target_url':item['target_url']},ensure_ascii=False)} for item in actionable[:2]]})
        return answer({'complete':{'from':sources,'description':'Review persisted assessment results and disclosed blocked or untested conditions; stop according to platform policy.'}})
    current=next((item for item in graph.get('intents',[]) if item.get('id')==assignment.get('intent_id')),None)
    if current is None:return reject()
    try:target=json.loads(current['description'])['target_url']
    except (ValueError,TypeError,KeyError):return reject()
    if 'verification_submit' in seen:
        result=seen['verification_submit']
        if not isinstance(result,dict) or not result.get('verification_run_id'):return reject()
        receipts=[unwrap(value) for name,value in history if name=='http_request']
        artifacts=[row.get('artifact_id') for row in receipts if isinstance(row,dict) and row.get('artifact_id')]
        artifacts += [row['artifact_id'] for row in assessment_read.get('observations',[]) if row.get('target_url')==target and row.get('artifact_id')]
        return answer({'description':'Authoritative verification result: '+json.dumps(result,ensure_ascii=False)+'; actual Artifact references: '+json.dumps(list(dict.fromkeys(artifacts)))})
    existing=[row for row in assessment_read.get('observations',[]) if row.get('target_url')==target and row.get('method')=='GET']
    for name,value in history:
        if name!='http_request' or not isinstance(value,dict):continue
        result=unwrap(value)
        exchange=result.get('exchange',{}) if isinstance(result,dict) else {}
        if exchange.get('url')==target and exchange.get('method')=='GET' and value.get('id'):
            existing.append(dict(exchange,tool_call_id=value['id'],response_status=exchange.get('status')))
    blocked=next((row for row in existing if row.get('response_status') in (401,403)),None)
    if blocked:return tool('verification_submit',{'rule_id':'cors-reflection-v1','tool_call_ids':[blocked['tool_call_id']]})
    chosen=[]
    for probe in PROBES:
        match=next((row for row in reversed(existing) if row.get('request_headers',{}).get('origin')==probe),None)
        if match is None:return tool('http_request',{'url':target,'method':'GET','headers':{'Origin':probe}})
        chosen.append(match['tool_call_id'])
    return tool('verification_submit',{'rule_id':'cors-reflection-v1','tool_call_ids':chosen})
