"""Wuji adapters around the unchanged Cairn 0.2.1 scheduler and task runners."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
from uuid import UUID
from urllib.parse import quote
import requests
from cairn.dispatcher.scheduler.loop import DispatcherLoop
from cairn.dispatcher.scheduler import loop as scheduler_loop
from cairn.dispatcher.protocol.client import CairnClient, ApiResult
from cairn.dispatcher.runtime.process import ProcessResult
from cairn.dispatcher.workers.adapters.pi import PiDriver
from cairn.dispatcher.workers.base import DriverResult
from cairn.dispatcher.workers import registry
from cairn.dispatcher.tasks import bootstrap, common, explore, reason

PIN = '8e7e0ea67552383851dfcabfba0c4e9c8d007878'

# Bootstrap catches Exception internally. This private control signal bypasses that
# failure branch while still unwinding the native runner's finally/lease cleanup.
class CompletionHandled(BaseException):
    def __init__(self, decision):
        if (not isinstance(decision, dict) or decision.get('kind') not in
                {'needs_followup', 'stop_with_results'} or not isinstance(decision.get('review_id'), str)):
            raise ValueError('invalid platform completion decision')
        self.kind = decision['kind']
        self.review_id = str(UUID(decision['review_id']))
        super().__init__('platform completion proposal handled')


_native_run_reason = reason.run_reason_task
_native_run_bootstrap = bootstrap.run_bootstrap_task


def run_reason(*args, **kwargs):
    try:
        return _native_run_reason(*args, **kwargs)
    except CompletionHandled:
        # Scheduler stage handling only; the native graph was not completed here.
        return 'success'


def run_bootstrap(*args, **kwargs):
    try:
        return _native_run_bootstrap(*args, **kwargs)
    except CompletionHandled:
        return 'success'

def verify_upstream():
    dist = importlib.metadata.distribution('cairn')
    direct = json.loads(dist.read_text('direct_url.json') or '{}')
    if dist.version != '0.2.1' or direct.get('vcs_info', {}).get('commit_id') != PIN:
        raise RuntimeError('Cairn upstream pin mismatch')
    manifest = json.loads(Path(__file__).with_name('upstream-hashes.json').read_text())
    for relative, expected in manifest.items():
        if hashlib.sha256(Path(dist.locate_file(relative)).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Cairn source changed: ' + relative)

class Control:
    def __init__(self):
        self.url = os.environ['WUJI_CONTROL_URL'].rstrip('/')
        self.token = Path(os.environ['WUJI_SERVICE_TOKEN_FILE']).read_text().strip()
    def request(self, method, route, body=None):
        response = requests.request(method, self.url + route, json=body,
            headers={'Authorization': 'Bearer ' + self.token}, timeout=20)
        response.raise_for_status()
        return response.json()

class ControlledClient(CairnClient):
    WRITES = {'create_intent', 'heartbeat', 'release', 'claim_reason', 'reason_heartbeat',
              'release_reason', 'conclude', 'complete', 'stop'}
    def __init__(self, base_url, control):
        super().__init__(base_url)
        self.control = control
        self.token = Path(os.environ['WUJI_CAIRN_TOKEN_FILE']).read_text().strip()
    def _session(self):
        session = super()._session()
        session.headers['Authorization'] = 'Bearer ' + self.token
        return session
    def list_projects(self):
        allowed = {item['native_project_id'] for item in self.control.request('GET', '/internal/v1/dispatch/projects')['items']}
        return [project for project in super().list_projects() if project.id in allowed]
    def __getattribute__(self, name):
        if name in object.__getattribute__(self, 'WRITES'):
            def write(project_id, *args):
                body = self.control.request('POST', f'/internal/v1/cairn/{project_id}/{name}', {'args': list(args)})
                if 'platform_decision' in body:
                    raise CompletionHandled(body['platform_decision'])
                return ApiResult(status_code=body['status_code'], data=body.get('data'), text=body.get('text', ''))
            return write
        return super().__getattribute__(name)

class ManagedPi(PiDriver):
    def build_execute(self, worker, prompt, session):
        return DriverResult(['wuji-managed-pi', worker.name, prompt], session=worker.name)
    def supports_conclude(self):
        # Invalid/unknown output is retained for reconciliation, never another model run.
        return False
    def build_conclude(self, worker, prompt, session):
        raise RuntimeError('Conclude fallback disabled: reconcile original output')

def graph_reference(backend, container_name, graph_yaml, *, phase):
    return 'Read the entire immutable graph snapshot using the graph_read controlled tool. It is supplied in this AgentRun assignment; no local graph file exists.'

class RemoteProcess:
    def __init__(self, admission, prompt, control):
        self.a, self.prompt, self.control = admission, prompt, control
        self.cancel_reason = None
        self.started = False
    def agent(self, method, suffix='', body=None):
        response = requests.request(method, self.a['agent_url'].rstrip('/') + '/runs/' + self.a['agent_run_id'] + suffix,
            json=body, headers={'Authorization': 'Bearer ' + self.a['backend_token']}, timeout=20)
        response.raise_for_status()
        return response.json()
    def start(self):
        body = {key:self.a[key] for key in ['phase','assignment','model','tool_names','deadline','operation_id','tool_token']}
        body['prompt'] = self.prompt
        try:
            self.agent('PUT', body=body)
        except requests.RequestException:
            # Read back the same ID only. No replacement key or new execution.
            self.agent('GET')
        self.started = True
    def communicate(self, timeout):
        deadline = time.monotonic() + (timeout or 95)
        while True:
            receipt = self.agent('GET')
            if receipt['state'] == 'exited':
                output = self.agent('GET', '/output')['output']
                self.control.request('POST', '/internal/v1/dispatch/runs/' + self.a['agent_run_id'] + '/output',
                    {'output':output, 'returncode':receipt['returncode'], 'receipt':receipt})
                return ProcessResult(receipt['returncode'], output, '', cancelled=self.cancel_reason is not None, cancel_reason=self.cancel_reason)
            if receipt['state'] == 'unknown':
                raise RuntimeError('Agent execution unknown; reconciliation required')
            if time.monotonic() > deadline:
                self.cancel('deadline')
                raise RuntimeError('Agent stop not yet confirmed; reconciliation required')
            time.sleep(.25)
    def kill(self):
        self.cancel('killed')
    def cancel(self, reason):
        self.cancel_reason = reason
        self.agent('POST', '/cancel')

class RemoteBackend:
    def __init__(self, control):
        self.control = control
        self.admissions = {}
        self.processes = []
    def container_name(self, project_id):
        return project_id
    def ensure_running(self, project_id):
        candidates = [a for a in self.admissions.values() if a['native_project_id'] == project_id]
        if not candidates:
            raise RuntimeError('No approved ready attempt')
        # Admission is issued only after the controller verifies the existing Pod.
        self.control.request('GET', '/internal/v1/dispatch/runs/' + candidates[-1]['agent_run_id'])
        return project_id
    def build_exec_process(self, container_name, env, command, timeout_seconds=None, kill_after_seconds=5):
        if len(command) != 3 or command[0] != 'wuji-managed-pi':
            raise RuntimeError('Arbitrary command rejected')
        a = self.admissions[command[1]]
        if a['native_project_id'] != container_name:
            raise RuntimeError('Project binding mismatch')
        process = RemoteProcess(a, command[2], self.control)
        self.processes.append(process)
        return process
    def write_text_file(self, *args):
        raise RuntimeError('Use immutable assignment graph_snapshot')
    def needs_completed_cleanup(self, project_id): return False
    def needs_stopped_cleanup(self, project_id): return False
    def cleanup_completed(self, project_id): return False
    def cleanup_stopped(self, project_id): return False
    def close(self): pass

class WujiDispatcher(DispatcherLoop):
    def __init__(self, config_path):
        verify_upstream()
        super().__init__(config_path)
        if self.config.runtime.execution != 'local' or any(w.type != 'pi' for w in self.config.workers):
            raise RuntimeError('Only managed Pi local construction is supported')
        self.config.runtime.worker_healthcheck = 'disabled'
        self.container_manager.close()
        self.client.close()
        self.control = Control()
        self.client = ControlledClient(self.config.server, self.control)
        self.container_manager = RemoteBackend(self.control)
        self.profiles = {}
        self.blocked_admits = set()
        self.dispatch_context = None
        scheduler_loop.run_reason_task = run_reason
        scheduler_loop.run_bootstrap_task = run_bootstrap
        registry.LOCAL_DRIVERS['pi'] = ManagedPi(local=True)
        common.write_graph_snapshot_reference = graph_reference
        explore.write_graph_snapshot_reference = graph_reference
        reason.write_graph_snapshot_reference = graph_reference
    def run_startup_healthchecks(self, **kwargs):
        self._startup_healthchecks_checked = True
    def _worker_counts(self):
        counts = {}
        for task in self.futures.values():
            profile = self.profiles.get(task.worker_name, task.worker_name)
            counts[profile] = counts.get(profile, 0) + 1
        return counts
    def _select_worker(self, project_id, task_type):
        selection = super()._select_worker(project_id, task_type)
        if selection.worker is None:
            return selection
        intent_id = self.dispatch_context
        key = (project_id, task_type, intent_id)
        if key in self.blocked_admits:
            selection.worker = None
            return selection
        profile = selection.worker
        self.blocked_admits.add(key)
        try:
            a = self.control.request('POST', '/internal/v1/dispatch/admit',
                {'native_project_id':project_id,'phase':task_type,'intent_id':intent_id,'worker_profile_id':profile.name,
                 'allowed_fact_ids':[fact.id for fact in self.dispatch_project.facts if fact.id!='goal']})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (403,409):
                self.blocked_admits.discard(key)
                selection.worker = None
                return selection
            raise
        a.update(native_project_id=project_id, phase=task_type)
        self.container_manager.admissions[a['worker_name']] = a
        self.profiles[a['worker_name']] = profile.name
        selection.worker = profile.model_copy(update={'name':a['worker_name'],'env':{}})
        self.current_admission = (key, a)
        return selection
    def _dispatch(self, parent, project, intent_id, *args):
        self.dispatch_context = intent_id
        self.dispatch_project = project
        self.current_admission = None
        result = parent(project, *args)
        if self.current_admission and not result:
            key, a = self.current_admission
            self.control.request('POST', f"/internal/v1/dispatch/runs/{a['agent_run_id']}/finish", {'outcome':'rejected'})
            self.blocked_admits.discard(key)
        return result
    def _dispatch_bootstrap(self, project, intent):
        return self._dispatch(super()._dispatch_bootstrap, project, intent.id, intent)
    def _dispatch_explore(self, project, export_yaml, intent):
        return self._dispatch(super()._dispatch_explore, project, intent.id, export_yaml, intent)
    def _dispatch_reason(self, project, export_yaml, trigger):
        return self._dispatch(super()._dispatch_reason, project, None, export_yaml, trigger)
    def _reason_trigger(self, project):
        trigger = super()._reason_trigger(project)
        if trigger is not None:
            return trigger
        native_id = quote(project.project.id, safe='')
        request = self.control.request('GET', '/internal/v1/dispatch/reason-requests/' + native_id)
        if request.get('pending') is True:
            review_id = request.get('review_id')
            if not isinstance(review_id, str):
                raise ValueError('pending assessment review identity required')
            return 'wuji-assessment:' + str(UUID(review_id))
        if request.get('pending') is not False:
            raise ValueError('invalid assessment reason request')
        return None

    def _reap_futures(self):
        for future, task in list(self.futures.items()):
            if not future.done(): continue
            a = self.container_manager.admissions[task.worker_name]
            try: outcome = future.result()
            except Exception: outcome = 'unknown'
            self.control.request('POST', f"/internal/v1/dispatch/runs/{a['agent_run_id']}/finish", {'outcome':outcome})
            if outcome == 'success':
                self.blocked_admits.discard((task.project_id,task.task_type,task.intent_id))
        super()._reap_futures()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    options = parser.parse_args()
    WujiDispatcher(options.config).run(once=options.once)
