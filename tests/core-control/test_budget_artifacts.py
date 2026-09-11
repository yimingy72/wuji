import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).parents[2] / 'services' / 'execution-control'
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
budget, artifacts = load('model_budget'), load('artifacts')


def test_native_key_body_hash_reconciliation_and_no_retry():
    async def run():
        key = 'sk-' + 'x' * 40
        digest = hashlib.sha256(key.encode()).hexdigest()
        task, tenant = uuid4(), uuid4()
        requests = []
        status = 200
        def handle(request):
            requests.append(request)
            if status != 200: return httpx.Response(status, json={'key':key})
            if request.url.path == '/key/generate':
                body = json.loads(request.content)
                assert body == {'key':key,'models':['fixture_alias'],'max_budget':1.25,
                    'metadata':{'wuji_task_id':str(task),'wuji_tenant_id':str(tenant)}}
                return httpx.Response(200,json=dict(body,key_name=key,spend=None,blocked=False))
            if request.url.path == '/key/info':
                assert request.url.params['key'] == digest and key not in str(request.url)
                return httpx.Response(200,json={'key':key,'info':{'models':['fixture_alias'],'spend':0.25,'blocked':True}})
            assert json.loads(request.content) == {'key':digest}
            return httpx.Response(200,json={'key':key})
        gateway = budget.TaskModelGateway('http://gateway.invalid','management-secret')
        await gateway.client.aclose()
        gateway.client = httpx.AsyncClient(base_url='http://gateway.invalid', transport=httpx.MockTransport(handle))
        try:
            result = await gateway.generate(key=key,model_alias='fixture_alias',budget_usd='1.25',task_id=task,tenant_id=tenant)
            assert key not in json.dumps(result) and result['spend'] is None and result['key_hash'] == digest
            assert (await gateway.lookup(digest))['spend'] == 0.25
            assert (await gateway.block(digest))['blocked'] is True
            status = 404
            assert await gateway.lookup(digest) is None
            status = 403
            with pytest.raises(budget.GatewayRejected): await gateway.block(digest)
            status = 503
            before = len(requests)
            with pytest.raises(budget.GatewayUnknown): await gateway.generate(key=key,model_alias='fixture_alias',budget_usd='1.25',task_id=task,tenant_id=tenant)
            assert len(requests) == before + 1
            with pytest.raises(ValueError): await gateway.lookup(key)
        finally: await gateway.close()
    asyncio.run(run())


def test_artifact_atomic_identity_bounds_and_symlinks(tmp_path):
    store = artifacts.ArtifactFileStore(tmp_path / 'evidence')
    task, artifact = uuid4(), uuid4()
    result = store.write(task, artifact, b'evidence', 'text/plain')
    assert result['sha256'] == hashlib.sha256(b'evidence').hexdigest()
    assert store.read(result['storage_key']) == b'evidence'
    assert store.write(task, artifact, b'evidence', 'text/plain') == result
    assert (store.root.stat().st_mode & 0o777) == 0o700
    assert ((store.root/result['storage_key']).stat().st_mode & 0o777) == 0o600
    with pytest.raises(artifacts.ArtifactConflict): store.write(task,artifact,b'changed','text/plain')
    with pytest.raises(artifacts.ArtifactError): store.write(task,uuid4(),b'x'*(artifacts.MAX_BYTES+1),'text/plain')
    with pytest.raises(artifacts.ArtifactUnsafe): store.read('../../outside')
    missing = uuid4()
    with pytest.raises(artifacts.ArtifactMissing): store.read(f'{task}/{missing}.blob')
    (store.root/str(task)/f'{missing}.pending-test').write_bytes(b'partial')
    with pytest.raises(artifacts.ArtifactIncomplete): store.read(f'{task}/{missing}.blob')
    outside = tmp_path/'outside'
    outside.write_bytes(b'private')
    (store.root/str(task)/f'{missing}.blob').symlink_to(outside)
    with pytest.raises(artifacts.ArtifactUnsafe): store.read(f'{task}/{missing}.blob')
