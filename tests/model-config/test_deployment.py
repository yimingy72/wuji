"""Focused lifecycle checks with no cluster access."""
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/platform'))
import gateway


def run_record():
    instance = uuid4()
    suffix = instance.hex
    return {'namespace': 'wuji-test', 'profile': 'test', 'processes': {}, 'model_gateway': {
        'instance_id': str(instance), 'url': 'http://127.0.0.1:18402',
        'database_name': 'wuji_gateway_'+suffix, 'database_role': 'wg_'+suffix,
        'master_key': 'sk-synthetic-management-only',
        **{f'{kind}_secret_name': f'wg-{suffix}-{kind}' for kind in ('master','salt','database')},
    }}


def test_fixed_gateway_template_and_optional_v1_extension():
    run = run_record()
    items = gateway.resources(run)
    deployment = items[-1]
    pod = deployment['spec']['template']['spec']
    assert deployment['spec']['replicas'] == 1
    assert pod['automountServiceAccountToken'] is False
    container = pod['containers'][0]
    assert container['image'] == gateway.IMAGE
    assert container['readinessProbe']['httpGet']['path'] == '/health/readiness'
    assert container['livenessProbe']['httpGet']['path'] == '/health/liveliness'
    assert run['model_gateway']['master_key'] not in json.dumps(items)
    env = {item['name']: item for item in container['env']}
    assert env['LITELLM_MASTER_KEY']['valueFrom'] != env['LITELLM_SALT_KEY']['valueFrom']
    schema = json.loads((ROOT/'scripts/platform/run-file.schema.json').read_text())
    assert schema['properties']['schema_version']['const'] == 1
    assert 'model_gateway' not in schema['required']
    model_schema = {**schema['properties']['model_gateway'], '$defs': schema['$defs']}
    jsonschema.Draft202012Validator(model_schema, format_checker=jsonschema.FormatChecker()).validate(run['model_gateway'])
    credential_schema = schema['$defs']['processRecord']['properties']['credential_scopes']
    for scopes in (['auth_dsn','project_dsn','oidc_client'], ['auth_dsn','project_dsn','oidc_client','model_gateway_management']):
        jsonschema.validate(scopes, credential_schema)


def test_gateway_delete_acceptance_is_not_stopped(monkeypatch):
    run = run_record()
    writes = []
    monkeypatch.setattr(gateway, 'load_manifest', lambda path: run)
    monkeypatch.setattr(gateway, 'owned', lambda *args: {'metadata': {'uid': 'own-uid', 'resourceVersion': '17'}})
    monkeypatch.setattr(gateway, 'record_is_owned', lambda record: False)
    monkeypatch.setattr(gateway, 'run_command', lambda command, **kwargs: writes.append((command,kwargs)))
    outcome = gateway.down(Path('/unused-fixture'))
    assert outcome['state'] == 'stopping' and outcome['persistent_data_retained'] is True
    assert len(writes) == 1
    payload = json.loads(writes[0][1]['input_text'])
    assert payload['preconditions'] == {'uid':'own-uid','resourceVersion':'17'}
    assert '/deployments/' in ' '.join(writes[0][0])
