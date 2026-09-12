"""Record the one final P04 candidate run; no business logic in this harness."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).parent
paths=[
 'packages/contracts/openapi-v2.yaml','packages/contracts/src/v2/generated.ts',
 'packages/wuji-core/src/wuji_core/contracts/generated.py',
 'packages/wuji-core/src/wuji_core/evidence/artifacts.py',
 'packages/wuji-core/src/wuji_core/persistence/schema.py',
 'packages/wuji-core/src/wuji_core/persistence/knowledge_schema.py',
 'packages/wuji-core/src/wuji_core/persistence/uow.py',
 'packages/wuji-core/src/wuji_core/persistence/snapshots.py',
 'packages/wuji-core/src/wuji_core/http/knowledge.py',
 'packages/wuji-core/src/wuji_core/http/records.py',
 'tests/vnext/test_knowledge_admission.py',
 *[f'packages/wuji-core/src/wuji_core/blackboard/{name}.py' for name in ('claims','assessments','fact_view','relations','committer')],
]
files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
fingerprint=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
manifest={'base_head':head,'code_tree_sha256':fingerprint,'file_sha256':files,'commands':[]}
raw=ROOT/'work/vnext/p04-final-raw'
env={**os.environ,'WUJI_TEST_EVIDENCE_DIR':str(raw)}
commands=[['./scripts/vnext/uv.sh','run','--frozen','pytest','tests/vnext/test_knowledge_admission.py','-q','--junitxml='+str(OUT/'junit.xml')],
          ['work/toolchain/bin/pnpm','contracts:check:v2']]
for index,command in enumerate(commands):
    path=OUT/('final-tests.txt' if index==0 else 'contracts-check.txt')
    started=time.time()
    with path.open('w') as out: result=subprocess.run(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
    manifest['commands'].append({'argv':command,'exit_code':result.returncode,'elapsed_seconds':round(time.time()-started,3),'output':path.name})
    (OUT/'final-run.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(path.name,result.returncode,path.read_text()[-4000:])
    if result.returncode:raise SystemExit(result.returncode)
assert files=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},'code changed during evidence run'
