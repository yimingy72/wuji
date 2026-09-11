"""Owned wuji-test core services; never starts the API, gateway or a model request."""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import stat
from urllib.parse import quote, urlsplit
from uuid import UUID
import psycopg
from psycopg import sql
import yaml
from wuji_api.database_admin import execution_role_name
from common import (KUBECTL_CONTEXT, OWNER_LABEL, REPOSITORY_ROOT, LifecycleError,
    assert_run_ownership, atomic_write_json, exclusive_lock, json_output, load_manifest,
    minimal_environment, preflight_ports, record_is_owned, require_context,
    require_owned_resource, run_command, safe_error_payload, spawn_registered,
    terminate_record, update_process, wait_port)

LABEL = 'wuji.dev/core-run'
NAMES = ['wuji-core-control', 'wuji-core-cairn', 'wuji-core-fixtures', 'wuji-core-dispatcher']

def side_path(path, run): return path.with_name('core-' + run['run_id'] + '.json')

def validate_run(path):
    if not path.is_absolute(): raise LifecycleError('--run-file must be absolute')
    run = load_manifest(path)
    assert_run_ownership(run)
    if run['namespace'] != 'wuji-test' or run['profile'] != 'test':
        raise LifecycleError('core lifecycle only supports wuji-test')
    return run

def load_core(path, run):
    side = side_path(path, run)
    info=side.stat()
    if side.is_symlink() or not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.getuid(): raise LifecycleError('core file must be private and owned')
    core = json.loads(side.read_text())
    for key in ('run_id', 'source_sha', 'repository_root'):
        if core.get(key) != run[key]: raise LifecycleError('core identity mismatch')
    return core

def metadata(run, name):
    return {'name':name,'namespace':'wuji-test','labels':{'wuji.dev/owner':OWNER_LABEL,LABEL:run['run_id'],'app.kubernetes.io/part-of':'wuji'}}

def owned(run, kind, name, core=None):
    value = require_owned_resource(kind, name, namespace='wuji-test')
    if value:
        if value['metadata'].get('labels',{}).get(LABEL) != run['run_id']:
            raise LifecycleError('core resource belongs to another run')
        expected = (core or {}).get('resources',{}).get(kind+'/'+name)
        if expected and expected != value['metadata']['uid']:
            raise LifecycleError('core resource UID changed')
    return value

def write(run, core, value):
    kind,name=value['kind'],value['metadata']['name']
    previous=owned(run,kind,name,core)
    if previous:
        if kind in ('Secret','PersistentVolumeClaim'):
            core['resources'][kind+'/'+name]=previous['metadata']['uid']
            return previous
        if kind=='Service':
            for field in ('clusterIP','clusterIPs','ipFamilies','ipFamilyPolicy'):
                if field in previous.get('spec',{}):value['spec'][field]=previous['spec'][field]
        value['metadata'].update({key:previous['metadata'][key] for key in ('uid','resourceVersion')})
    run_command(['kubectl','--context',KUBECTL_CONTEXT,'-n','wuji-test','replace' if previous else 'create','-f','-'],input_text=json.dumps(value))
    current=owned(run,kind,name)
    if not current:raise LifecycleError('resource write not confirmed')
    core['resources'][kind+'/'+name]=current['metadata']['uid']
    return current

def image_reference(name):
    result=json.loads(run_command(['docker','image','inspect',name],timeout=30).stdout)[0]
    references=result.get('RepoDigests',[])
    if not references:raise LifecycleError('core image has no real RepoDigest; build candidate first')
    repository=name.split('@')[0].rsplit(':',1)[0]
    matching=[r for r in references if r.split('@')[0].endswith(repository)]
    if not matching:raise LifecycleError('image digest repository mismatch')
    return matching[0]

def prepare(path, model_version, image):
    run=validate_run(path)
    if side_path(path,run).exists():
        core=load_core(path,run)
        if model_version and core['config']['model_profile_version_id'] != str(UUID(model_version)):
            raise LifecycleError('prepared core model snapshot differs; use its original run')
        return core
    if not model_version:raise LifecycleError('prepare requires --model-profile-version-id')
    model_version=str(UUID(model_version))
    if require_owned_resource('namespace','wuji-test') is None:raise LifecycleError('owned test namespace absent')
    gateway=run.get('model_gateway')
    if not gateway:raise LifecycleError('prepare existing model gateway first')
    suffix=run['run_id'].replace('-','')
    core={key:run[key] for key in ('run_id','source_sha','repository_root')}
    core.update(resources={},secret_name='wuji-core-'+suffix,artifact_pvc='wuji-artifacts-'+suffix,cairn_pvc='wuji-cairn-'+suffix,image=image_reference(image))
    gateway_name='wg-'+gateway['instance_id'].replace('-','')
    core['config']={'namespace':'wuji-test','control_url':'http://wuji-core-control:8000','public_control_url':'http://127.0.0.1:18502',
        'cairn_url':'http://wuji-core-cairn:8000','model_base_url':f'http://{gateway_name}:4000/v1','gateway_url':f'http://{gateway_name}:4000',
        'agent_image':image_reference('wuji-task-agent:core-loop'),'kali_image':image_reference('wuji-task-kali:core-loop'),
        'fixture_origins':['http://wuji-core-fixtures:8000'],'artifact_root':'/artifacts','model_profile_version_id':model_version,'profile_id':'fixture-web-v1'}
    existing=owned(run,'Secret',core['secret_name'])
    role=execution_role_name(run['database']['roles']['project'])
    if existing:
        values={key:base64.b64decode(value,validate=True).decode() for key,value in existing['data'].items()}
        password=urlsplit(values['execution_dsn']).password
        from urllib.parse import unquote
        password=unquote(password)
    else:
        password=secrets.token_urlsafe(48)
        values={name:secrets.token_urlsafe(48) for name in ('service_token','cairn_token','runtime_signing_key')}
        values.update(execution_dsn=f"postgresql+psycopg://{quote(role,safe='')}:{quote(password,safe='')}@postgres.wuji-test.svc:5432/{run['database']['name']}",
            gateway_management_key=gateway['master_key'],artifact_signing_key=run['credentials']['app']['cursor_signing_key'])
    admin=run['credentials']['database']['admin_dsn'].replace('postgresql+psycopg://','postgresql://',1)
    with psycopg.connect(admin,connect_timeout=10) as connection:
        row=connection.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
        if row != (False,False,False,False,False):raise LifecycleError('execution role missing or unexpected privileges')
        member=connection.execute('SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)',(role,)).fetchone()
        if member:raise LifecycleError('execution role has unexpected memberships')
        connection.execute(sql.SQL('ALTER ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
    secret=write(run,core,{'apiVersion':'v1','kind':'Secret','metadata':metadata(run,core['secret_name']),'type':'Opaque','immutable':True,'stringData':values})
    core['resources']['Secret/'+core['secret_name']]=secret['metadata']['uid']
    atomic_write_json(side_path(path,run),core)
    return core

def resources(run, core):
    config=core['config']
    output=[]
    for value in yaml.safe_load_all((REPOSITORY_ROOT/'infra/kubernetes/core/rbac.yaml').read_text()):
        value['metadata']=metadata(run,value['metadata']['name']);output.append(value)
    for pvc in (core['artifact_pvc'],core['cairn_pvc']):
        output.append({'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':metadata(run,pvc),'spec':{'accessModes':['ReadWriteOnce'],'resources':{'requests':{'storage':'1Gi'}}}})
    dispatch=yaml.safe_load((REPOSITORY_ROOT/'services/cairn-dispatcher/example.yaml').read_text());dispatch['server']=config['cairn_url']
    output.append({'apiVersion':'v1','kind':'ConfigMap','metadata':metadata(run,'wuji-core-config'),'data':{'control.json':json.dumps(config),'dispatcher.yaml':yaml.safe_dump(dispatch)}})
    commands={NAMES[0]:['python','services/execution-control/main.py'],NAMES[1]:['uvicorn','cairn_server:app','--app-dir','services/execution-control','--host','0.0.0.0','--port','8000'],NAMES[2]:['python','services/core-fixtures/server.py'],NAMES[3]:['python','services/cairn-dispatcher/main.py','--config','/config/dispatcher.yaml']}
    for name in NAMES:
        labels=metadata(run,name)['labels']|{'app':name}
        volumes=[{'name':'config','configMap':{'name':'wuji-core-config'}}]
        mounts=[{'name':'config','mountPath':'/config','readOnly':True}]
        env={'PYTHONDONTWRITEBYTECODE':'1'}
        keys=[]
        if name==NAMES[0]:
            keys=['execution_dsn','service_token','cairn_token','gateway_management_key','runtime_signing_key','artifact_signing_key']
            env.update(WUJI_CORE_CONFIG='/config/control.json',WUJI_CORE_CREDENTIALS='/run/wuji/credentials')
            volumes.append({'name':'artifacts','persistentVolumeClaim':{'claimName':core['artifact_pvc']}});mounts.append({'name':'artifacts','mountPath':'/artifacts'})
        elif name==NAMES[1]:
            keys=['cairn_token'];env.update(HOME='/var/lib/wuji',WUJI_CORE_CREDENTIALS='/run/wuji/credentials')
            volumes.append({'name':'cairn-data','persistentVolumeClaim':{'claimName':core['cairn_pvc']}});mounts.append({'name':'cairn-data','mountPath':'/var/lib/wuji/.local/share/cairn'})
        elif name==NAMES[3]:
            keys=['service_token','cairn_token'];env.update(WUJI_CONTROL_URL=config['control_url'],WUJI_SERVICE_TOKEN_FILE='/run/wuji/credentials/service_token',WUJI_CAIRN_TOKEN_FILE='/run/wuji/credentials/cairn_token')
        else:env.update(WUJI_FIXTURE_ORIGIN=config['fixture_origins'][0],PORT='8000')
        if keys:
            volumes.append({'name':'credentials','secret':{'secretName':core['secret_name'],'defaultMode':0o400,'items':[{'key':key,'path':key} for key in keys]}})
            mounts.append({'name':'credentials','mountPath':'/run/wuji/credentials','readOnly':True})
        container={'name':'service','image':core['image'],'imagePullPolicy':'IfNotPresent','command':commands[name],'env':[{'name':k,'value':v} for k,v in env.items()],'volumeMounts':mounts,'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1','memory':'512Mi'}}}
        if name!=NAMES[3]:container.update(ports=[{'containerPort':8000}],readinessProbe={'tcpSocket':{'port':8000},'initialDelaySeconds':2,'periodSeconds':3})
        pod={'containers':[container],'volumes':volumes,'automountServiceAccountToken':name==NAMES[0],'terminationGracePeriodSeconds':30}
        if name==NAMES[0]:pod['serviceAccountName']='wuji-core-control'
        output.append({'apiVersion':'apps/v1','kind':'Deployment','metadata':metadata(run,name),'spec':{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':name}},'template':{'metadata':{'labels':labels},'spec':pod}}})
        if name!=NAMES[3]:output.append({'apiVersion':'v1','kind':'Service','metadata':metadata(run,name),'spec':{'selector':{'app':name},'ports':[{'port':8000,'targetPort':8000}]}})
    return output

def up(path):
    run=validate_run(path);core=load_core(path,run)
    if owned(run,'Secret',core['secret_name'],core) is None:raise LifecycleError('retained core credential Secret missing')
    desired=resources(run,core)
    for value in desired:owned(run,value['kind'],value['metadata']['name'],core)
    existing=run['processes'].get('core_forward',{})
    if not record_is_owned(existing):preflight_ports([18502])
    for value in desired:
        write(run,core,value);atomic_write_json(side_path(path,run),core)
    for name in NAMES:
        run_command(['kubectl','--context',KUBECTL_CONTEXT,'-n','wuji-test','rollout','status','deployment/'+name,'--timeout=180s'],timeout=190)
    if not record_is_owned(existing):
        command=['kubectl','--context',KUBECTL_CONTEXT,'-n','wuji-test','port-forward','--address','127.0.0.1','service/wuji-core-control','18502:8000']
        process,record=spawn_registered(path,'core_forward',command,log_path=Path(run['artifacts_dir'])/'core-forward.log',command_marker='kubectl port-forward service/wuji-core-control',env=minimal_environment())
        try:wait_port(18502,timeout=30)
        except BaseException:
            terminate_record(record,process=process)
            update_process(path,'core_forward',{'lifecycle_state':'exited','exit_code':1})
            raise
    return status(path)

def status(path):
    run=validate_run(path)
    if not side_path(path,run).exists():return {'configured':False}
    core=load_core(path,run)
    deployments={}
    for name in NAMES:
        value=owned(run,'Deployment',name,core)
        deployments[name]={'present':value is not None,'ready_replicas':(value or {}).get('status',{}).get('readyReplicas',0)}
    return {'configured':True,'run_id':run['run_id'],'source_sha':run['source_sha'],'url':core['config']['public_control_url'],'deployments':deployments,'forward_owned':record_is_owned(run['processes'].get('core_forward',{})),'persistent_data_retained':True}

def down(path):
    run=validate_run(path);core=load_core(path,run)
    record=run['processes'].get('core_forward',{})
    if record_is_owned(record):terminate_record(record);update_process(path,'core_forward',{'lifecycle_state':'stopped'})
    endpoints={'Deployment':'/apis/apps/v1/namespaces/wuji-test/deployments/','Service':'/api/v1/namespaces/wuji-test/services/','ConfigMap':'/api/v1/namespaces/wuji-test/configmaps/','Role':'/apis/rbac.authorization.k8s.io/v1/namespaces/wuji-test/roles/','RoleBinding':'/apis/rbac.authorization.k8s.io/v1/namespaces/wuji-test/rolebindings/','ServiceAccount':'/api/v1/namespaces/wuji-test/serviceaccounts/'}
    for key in reversed(list(core['resources'])):
        kind,name=key.split('/',1)
        if kind not in endpoints:continue
        value=owned(run,kind,name,core)
        if value:
            run_command(['kubectl','--context',KUBECTL_CONTEXT,'delete','--raw',endpoints[kind]+name,'-f','-'],input_text=json.dumps({'apiVersion':'v1','kind':'DeleteOptions','propagationPolicy':'Foreground','preconditions':{'uid':value['metadata']['uid'],'resourceVersion':value['metadata']['resourceVersion']}}))
        core['resources'].pop(key,None)
        atomic_write_json(side_path(path,run),core)
    return status(path)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','up','status','down']);parser.add_argument('--run-file',type=Path,required=True)
    parser.add_argument('--model-profile-version-id');parser.add_argument('--image',default='wuji-core:core-loop')
    args=parser.parse_args()
    try:
        validate_run(args.run_file)
        with exclusive_lock(args.run_file.with_name('.'+args.run_file.name+'.core.lock')):
            require_context()
            if args.action=='prepare':
                core=prepare(args.run_file,args.model_profile_version_id,args.image);result={'prepared':True,'run_id':core['run_id'],'core_file':str(side_path(args.run_file,core))}
            else:result=globals()[args.action](args.run_file)
        print(json_output(result));return 0
    except Exception as error:
        print(json.dumps(safe_error_payload(run_id=None,error=error)));return 1

if __name__=='__main__':raise SystemExit(main())
