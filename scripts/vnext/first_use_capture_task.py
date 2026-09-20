"""Read-only complete redacted HTTP captures for one UUID Task in local K8s."""
import argparse
import json
from pathlib import Path
import subprocess
from uuid import UUID

PROBE = r'''
import httpx,json,ssl,sys
from pathlib import Path
task_id=sys.argv[1]
token=Path('/run/wuji/credentials/service.token').read_text().strip()
with httpx.Client(base_url='https://api.wuji-vnext-test.svc:8443',
                 verify=ssl.create_default_context(cafile='/config/ca.crt'),
                 headers={'Authorization':'Bearer '+token},trust_env=False,
                 follow_redirects=False,timeout=15) as client:
    records=[]
    for suffix in ('','/launch','/readiness'):
        response=client.get('/api/v2/tasks/'+task_id+suffix)
        request=response.request
        headers=dict(request.headers);headers['authorization']='Bearer <operator SecretRef>'
        records.append({'request':{'method':request.method,'url':str(request.url),
            'headers':headers,'body':request.content.decode()},
            'response':{'status':response.status_code,'headers':dict(response.headers),
                'body':response.text.replace(token,'<redacted>')}})
    print(json.dumps(records,ensure_ascii=False))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task-id',type=UUID,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise ValueError('refusing to replace prior capture')
    command=['kubectl','--context','docker-desktop','-n','wuji-vnext-test',
             'exec','-i','deployment/api','--','python','-',str(a.task_id)]
    result=subprocess.run(command,input=PROBE,text=True,capture_output=True,timeout=55)
    if result.returncode:
        print(json.dumps({'error':'capture_failed','exit_code':result.returncode}))
        return 1
    records=json.loads(result.stdout)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:
        json.dump({'task_id':str(a.task_id),'observer':'A0',
          'method':'real public API HTTP from API Pod; not browser wire capture',
          'inference_or_target_requests':False,'exchanges':records},f,ensure_ascii=False,indent=2)
    print(json.dumps({'output':str(a.output),'statuses':[r['response']['status'] for r in records]}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
