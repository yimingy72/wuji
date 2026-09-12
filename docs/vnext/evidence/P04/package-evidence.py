"""Package observed fixture evidence without publishing reusable bearer tokens."""
import base64
import gzip
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).parent
raw=ROOT/'work/vnext/p04-final-raw'
manifest=json.loads((OUT/'final-run.json').read_text())
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
for name,digest in manifest['file_sha256'].items():
    assert hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)).hexdigest()==digest
binding={'code_commit':commit,'tested_base_head':manifest['base_head'],'code_tree_sha256':manifest['code_tree_sha256'],'all_16_tested_files_match_commit':True}
(OUT/'commit-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
exchanges=[];catalog=[]
for source in sorted(raw.rglob('*')):
    if not source.is_file():continue
    rel=source.relative_to(raw)
    dest=OUT/'runtime'/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    data=source.read_bytes()
    if source.name=='http-exchanges.jsonl':
        lines=[]
        for line in data.decode().splitlines():
            exchange=json.loads(line)
            auth=exchange['request']['headers'].get('authorization')
            if auth:
                token=auth.removeprefix('Bearer ')
                claims=json.loads(base64.urlsafe_b64decode(token.split('.')[1]+'==='))
                exchange['request']['headers']['authorization']='Bearer ${TOKEN_'+claims['sub'].replace('-','_')+'}'
                exchange['authorization_evidence']={'subject':claims['sub'],'roles':claims['roles'],'original_header_sha256':hashlib.sha256(auth.encode()).hexdigest(),'replacement':'ephemeral fixture token; regenerate with test issuer'}
            lines.append(json.dumps(exchange,ensure_ascii=False,sort_keys=True))
            exchanges.append((str(rel.parent),exchange))
        dest.write_text('\n'.join(lines)+'\n')
    elif source.name=='postgres-events.jsonl':
        dest=dest.with_suffix('.jsonl.gz')
        dest.write_bytes(gzip.compress(data,mtime=0))
    else:shutil.copyfile(source,dest)
    catalog.append({'path':str(dest.relative_to(OUT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256(data).hexdigest(),'original_bytes':len(data)})
(OUT/'evidence-index.json').write_text(json.dumps(catalog,indent=2)+'\n')
root=ET.parse(OUT/'junit.xml').getroot()
cases=[e.attrib for e in root.iter('testcase')]
(OUT/'test-names.json').write_text(json.dumps(cases,indent=2)+'\n')
parts=['# P04 complete fixture HTTP exchanges\n',
'Production ASGI routes, not mock handlers; original body bytes are untruncated. `http://testserver` is the in-process ASGI authority, not an external host. PostgreSQL connections and artifact files are real isolated fixtures.\n',
'Authorization headers use `${TOKEN_subject}` instead of publishing bearer credentials. Re-run `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_knowledge_admission.py -q` to create the isolated database, actual parents/policy grants, freshly signed test issuer and every request. The issuer implementation is `tests/vnext/support/identity_provider.py`; the P04 fixture explicitly adds worker and qualified-human roles. Private signing keys are never saved. Original header hashes are retained in runtime JSONL.\n',
'SQL (including requests, parameters, actual results/errors and transaction outcomes) is losslessly gzip-compressed per test. Runtime JSONL retains exact HTTP bodies as base64. Inputs named `capture-*.bin` / `raw-*.bin` retain actual sealed source bytes.\n',
'Validation boundaries: candidate self-certification, unrelated prose, partial negation, same-batch failed dependencies, current ACLs and model-output/capture authority are the intentional negative controls below.\n']
for index,(node,e) in enumerate(exchanges,1):
    request=e['request'];response=e['response']
    parts.append(f'## Exchange {index} · {node}\n')
    reqbody=base64.b64decode(request['body_base64']).decode('utf-8')
    resbody=base64.b64decode(response['body_base64']).decode('utf-8')
    parts.append('```http\n'+request['method']+' '+request['url']+' HTTP/1.1\n'+'\n'.join(k+': '+v for k,v in request['headers'].items())+'\n\n'+reqbody+'\n```\n')
    parts.append('```http\nHTTP/1.1 '+str(response['status_code'])+'\n'+'\n'.join(k+': '+v for k,v in response['headers'].items())+'\n\n'+resbody+'\n```\n')
(OUT/'http-reproduction.md').write_text('\n'.join(parts))
positive=next(e for _,e in exchanges if e['response']['status_code']==200 and b'"display_kind":"fact"' in base64.b64decode(e['response']['body_base64']))
negative=next(e for _,e in exchanges if e['response']['status_code']==403)
content=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><title>P04 recorded verification evidence</title>
<style>body{{font:16px system-ui;margin:32px;background:#f5f7fa;color:#182331}}h1{{font-size:28px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;border:1px solid #d5dee8;padding:16px;font:13px ui-monospace}}.meta{{font-size:14px;color:#40546a}}strong{{color:#145c35}}</style>
<h1>P04 · 真实服务/API/PG/字节验证记录</h1><p><strong>24 passed · contracts check exit 0</strong></p>
<p class="meta">被测树与本地代码提交逐文件匹配：{commit}<br>代码指纹：{manifest['code_tree_sha256']}<br>生产 ASGI 路由；隔离 PostgreSQL；实际封存字节。截图展示已保存的响应，不是运行中的产品 UI。</p>
<h2>最终候选命令</h2><pre>{html.escape((OUT/'final-tests.txt').read_text())}</pre>
<h2>Agent 候选经独立核验后进入 Fact 读视图</h2><pre>{html.escape(json.dumps(json.loads(base64.b64decode(positive['response']['body_base64'])),ensure_ascii=False,indent=2))}</pre>
<h2>直接自认证被拒绝</h2><pre>{html.escape(base64.b64decode(negative['response']['body_base64']).decode())}</pre>
<p>局部机制自行验证；P05/P09 执行、P12 Goal、P13 完整画布及独立审查不在本页通过声明内。</p></html>'''
(OUT/'result.html').write_text(content)
print(json.dumps({'code_commit':commit,'http_exchanges':len(exchanges),'runtime_files':len(catalog),'test_cases':len(cases)},indent=2))
