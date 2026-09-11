#!/usr/bin/env python3
"""Explicit synthetic D2/core fixture setup for one existing owned test run.

Prerequisites (performed separately by the operator): gateway up, API restarted
with issuer_fixture, single_a TenantAdmin granted, candidate core images built.
Run with the repository .venv Python and --run-file /absolute/private/run.json.
No real model upstream is configurable. Invoking this script explicitly requests
one connection check of the fixed synthetic model, followed by publication.

The private adjacent setup record contains public IDs and original operation keys
only. A sent/unknown HTTP operation is read back by its original key/operation ID;
it is never POSTed again. A 404 after interruption requires manual reconciliation,
not removal of this record. A failed/unknown connection check is never repeated.
Core prepare/up reuse their existing owned lifecycle and retained resources.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from urllib.parse import urljoin, urlsplit
from uuid import UUID, uuid4

import httpx
from common import (REPOSITORY_ROOT, LifecycleError, assert_run_ownership,
                    atomic_write_json, exclusive_lock, load_manifest)

UPSTREAM = 'http://wuji-core-fixtures:8000/v1'
MODEL = 'wuji-fixture'
PRICE = {'source':'Synthetic fixture tariff','input_per_million':'1',
         'output_per_million':'2','cache_mode':'standard_input'}


def origin(value):
    parsed = urlsplit(value)
    return parsed.scheme + '://' + parsed.netloc


def private_record(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise LifecycleError('setup record must be an owned regular 0600 file')
    return json.loads(path.read_text())


class Setup:
    def __init__(self, path, profile="fixture-web-v1", compaction_probe=False):
        self.profile=profile
        self.compaction_probe=compaction_probe
        self.path = path
        self.run = load_manifest(path)
        assert_run_ownership(self.run)
        if self.run['profile'] != 'test' or self.run['namespace'] != 'wuji-test':
            raise LifecycleError('setup is restricted to the existing wuji-test run')
        if not self.run.get('model_gateway'):
            raise LifecycleError('operator must prepare and start the gateway first')
        self.record_path = path.with_name('core-fixture-setup-' + self.run['run_id'] + '.json')
        self.owner = {k:self.run[k] for k in ('run_id','source_sha','repository_root')}
        self.owner.update(profile_id=profile,compaction_probe=compaction_probe)
        if self.record_path.exists() or self.record_path.is_symlink():
            self.record = private_record(self.record_path)
            if any(self.record.get(k) != v for k,v in self.owner.items()):
                raise LifecycleError('setup record belongs to a different run or candidate')
        else:
            self.record = {**self.owner,'schema_version':1,'stages':{},'complete':False}
            self.save()
        user = self.run['seed_users']['single_a']
        self.user_id = str(UUID(user['id']))
        self.tenant = str(UUID(user['tenant_ids'][0]))
        self.project = str(UUID(user['project_ids'][0]))
        self.base = self.run['urls']['web'].rstrip('/')
        self.client = httpx.Client(timeout=40,follow_redirects=False,trust_env=False,
                                  transport=httpx.HTTPTransport(retries=0))

    def save(self):
        atomic_write_json(self.record_path,self.record)

    def request(self, method, path, **kwargs):
        try:
            response = self.client.request(method,urljoin(self.base,path),**kwargs)
        except httpx.HTTPError:
            raise LifecycleError('HTTP outcome unavailable; rerun only to reconcile original operation') from None
        return response

    def json(self, response):
        if response.status_code != 200:
            raise LifecycleError('fixture API request did not succeed; response body withheld')
        try:
            value = response.json()
            if not isinstance(value,dict): raise ValueError
            return value
        except ValueError:
            raise LifecycleError('fixture API response was invalid') from None

    def login(self):
        fixture = self.run['urls']['issuer_fixture'].rstrip('/')
        response = self.request('POST',fixture+'/_control',json={'scenario':'valid','user':'single_a'},
            headers={'Authorization':'Bearer '+self.run['credentials']['oidc_fixture']['control_token']})
        self.json(response)
        response = self.request('GET','/api/v1/auth/login',params={'return_to':'/projects'})
        allowed = {origin(self.base),origin(self.run['urls']['api']),origin(fixture)}
        seen_fixture = False
        for _ in range(8):
            if response.status_code not in (302,303,307,308): break
            destination = urljoin(str(response.url),response.headers.get('location',''))
            if origin(destination) not in allowed:
                raise LifecycleError('login redirect is outside the owned fixture endpoints')
            if origin(destination) == origin(fixture): seen_fixture = True
            response = self.request('GET',destination)
        if not seen_fixture:
            raise LifecycleError('API must first be restarted with issuer_fixture')
        session = self.json(self.request('GET','/api/v1/session'))
        if session['user_id'] != self.user_id:
            raise LifecycleError('fixture session is not single_a')
        self.client.headers.update({'Origin':self.base,'X-CSRF-Token':session['csrf_token']})
        # This read requires the pre-existing TenantAdmin grant; never grant here.
        self.json(self.request('GET',f'/api/v1/tenants/{self.tenant}/model-services'))

    def operation(self, stage, path, body):
        saved = self.record['stages'].get(stage)
        first = saved is None
        if first:
            saved = {'key':str(uuid4()),'state':'sent'}
            self.record['stages'][stage] = saved
            self.save()  # Before the one permitted POST, including connection check.
            response = self.request('POST',path,json=body,headers={'Idempotency-Key':saved['key']})
        else:
            route = (f"model-operations/{saved['operation_id']}" if saved.get('operation_id')
                     else f"model-operation-keys/{saved['key']}")
            response = self.request('GET',f'/api/v1/tenants/{self.tenant}/'+route)
        if response.status_code == 404:
            raise LifecycleError('original operation not found; no replacement operation was sent')
        value = self.json(response)
        for _ in range(30):
            saved.update(operation_id=str(UUID(value['id'])),version_id=str(UUID(value['version_id'])),state=value['state'])
            self.save()
            if value['state'] == 'succeeded': return saved['version_id']
            if value['state'] == 'failed':
                raise LifecycleError('original fixture operation failed; no automatic replacement')
            time.sleep(1)
            value = self.json(self.request('GET',f"/api/v1/tenants/{self.tenant}/model-operations/{saved['operation_id']}"))
        raise LifecycleError('original operation remains unresolved; no check or write was repeated')

    def lifecycle(self, action, model_version):
        stage = 'core_' + action
        if self.record['stages'].get(stage,{}).get('state') == 'succeeded': return
        self.record['stages'][stage] = {'state':'sent'}
        self.save()
        arguments = [sys.executable,str(REPOSITORY_ROOT/'scripts/platform/core.py'),action,
                     '--run-file',str(self.path)]
        if action == 'prepare':
            arguments += ['--model-profile-version-id',model_version,'--profile',self.profile]
            if self.compaction_probe:arguments += ['--compaction-probe']
        result = subprocess.run(arguments,cwd=REPOSITORY_ROOT,stdin=subprocess.DEVNULL,
                                capture_output=True,text=True,timeout=850,check=False)
        if result.returncode:
            raise LifecycleError('owned core lifecycle failed; diagnostic output withheld')
        self.record['stages'][stage] = {'state':'succeeded'}
        self.save()

    def run_setup(self):
        self.login()
        prefix = f'/api/v1/tenants/{self.tenant}'
        if self.record.get('complete'):
            model = self.record['model_profile_version_id']
            version = self.json(self.request('GET',prefix+f'/model-profile-versions/{model}'))
            if version['state'] != 'published' or version['sync_state'] != 'synced':
                raise LifecycleError('completed setup model is no longer published; no check was repeated')
            return
        service = self.operation('create_service',prefix+'/model-services',{
            'name':'Core synthetic fixture','config':{'protocol':'openai','base_url':UPSTREAM},
            'api_key':'wuji-synthetic-fixture-only'})
        model = self.operation('create_profile',prefix+'/model-profiles',{
            'name':'Core synthetic fixture','config':{'service_version_id':service,'model_id':MODEL,
                'context_window':32768,'max_output_tokens':1024,'timeout_seconds':30,'pricing':PRICE}})
        self.record.update(service_version_id=service,model_profile_version_id=model,
                           tenant_id=self.tenant,project_id=self.project)
        self.save()
        self.lifecycle('prepare',model)
        self.lifecycle('up',model)
        self.operation('check',prefix+f'/model-profile-versions/{model}/checks',{})
        version = self.json(self.request('GET',prefix+f'/model-profile-versions/{model}'))
        self.operation('publish',prefix+f'/model-profile-versions/{model}/commands',
                       {'action':'publish','expected_version':version['state_revision']})
        version = self.json(self.request('GET',prefix+f'/model-profile-versions/{model}'))
        if version['state'] != 'published' or version['sync_state'] != 'synced':
            raise LifecycleError('fixture publication was not confirmed')
        self.record.update(complete=True,published=True)
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-file',type=Path,required=True)
    parser.add_argument('--profile',choices=['fixture-web-v1','closed-web-assessment-v1'],default='fixture-web-v1')
    parser.add_argument('--compaction-probe',action='store_true')
    arguments = parser.parse_args()
    if not arguments.run_file.is_absolute():
        parser.error('--run-file must be absolute')
    setup = None
    try:
        with exclusive_lock(arguments.run_file.with_name('.'+arguments.run_file.name+'.fixture-setup.lock')):
            setup = Setup(arguments.run_file,arguments.profile,arguments.compaction_probe)
            setup.run_setup()
            print(json.dumps({'ok':True,'run_id':setup.run['run_id'],
                              'model_profile_version_id':setup.record['model_profile_version_id'],'published':True}))
        return 0
    except Exception as error:
        # Never format HTTP exceptions, subprocess output, private run data or Keys.
        message = 'fixture setup stopped; reconcile the private setup record and original operation before proceeding'
        print(json.dumps({'ok':False,'error':message}),file=sys.stderr)
        return 1
    finally:
        if setup is not None: setup.client.close()


if __name__ == '__main__':
    raise SystemExit(main())
