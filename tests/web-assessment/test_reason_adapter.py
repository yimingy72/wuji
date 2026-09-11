"""Only explicit platform decisions bypass native completion failure handling."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock
import pytest
import requests

path = Path(__file__).parents[2] / 'services/cairn-dispatcher/main.py'
spec = importlib.util.spec_from_file_location('wuji_reason_adapter', path)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def controlled(body):
    client = object.__new__(adapter.ControlledClient)
    client.control = SimpleNamespace(request=Mock(return_value=body))
    return client


@pytest.mark.parametrize('phase', ['reason', 'bootstrap'])
@pytest.mark.parametrize('kind', ['needs_followup', 'stop_with_results'])
def test_native_finally_before_handled_scheduler_result(monkeypatch, phase, kind):
    calls = []
    client = controlled({'status_code':409,'data':None,'text':'proposal reviewed',
        'platform_decision':{'kind':kind,'review_id':str(uuid4())}})
    original_request = client.control.request
    def request(method, path, body):
        if path.endswith('/release_reason'):
            calls.append('release')
            return {'status_code':200,'data':None,'text':''}
        return original_request(method,path,body)
    client.control.request = request
    lease = SimpleNamespace(start=lambda:calls.append('start'),stop=lambda:calls.append('stop'))
    native = adapter.reason if phase == 'reason' else adapter.bootstrap
    monkeypatch.setattr(native,'get_driver',lambda *args:object())
    monkeypatch.setattr(native,'HeartbeatLease',SimpleNamespace(
        for_reason=lambda *args:lease,for_intent=lambda *args:lease))
    def execute(_project):
        client.complete('p1',['origin'],'proposal','run-worker')
        raise AssertionError('a platform decision must never become native success')
    manager = SimpleNamespace(ensure_running=execute)
    config = SimpleNamespace(runtime=SimpleNamespace(execution='local',interval=5,healthcheck_timeout=2))
    project = SimpleNamespace(project=SimpleNamespace(id='p1'))
    worker = SimpleNamespace(type='pi',name='run-worker')
    middle = '' if phase == 'reason' else SimpleNamespace(id='i1')
    assert getattr(adapter,'run_'+phase)(config,client,manager,project,middle,worker,None) == 'success'
    assert calls == (['start','stop','release'] if phase == 'reason' else ['start','stop'])


def test_native_failure_and_unknown_are_not_business_success(monkeypatch):
    for code in (409,0,503):
        result = controlled({'status_code':code,'data':None,'text':'unconfirmed'}).complete('p1',[],'proposal','worker')
        assert result.status_code == code
    with pytest.raises(ValueError):
        controlled({'status_code':200,'platform_decision':{'kind':'needs_followup','review_id':'invalid'}}).complete('p1')
    for phase in ('reason','bootstrap'):
        monkeypatch.setattr(adapter,'_native_run_'+phase,lambda:'failed')
        assert getattr(adapter,'run_'+phase)() == 'failed'
        def unavailable(): raise requests.ConnectionError('unavailable')
        monkeypatch.setattr(adapter,'_native_run_'+phase,unavailable)
        with pytest.raises(requests.ConnectionError): getattr(adapter,'run_'+phase)()


def test_pending_reason_request_only_supplements_absent_native_trigger(monkeypatch):
    dispatcher = object.__new__(adapter.WujiDispatcher)
    review = str(uuid4())
    dispatcher.control = SimpleNamespace(request=Mock(return_value={'pending':True,'review_id':review}))
    project = SimpleNamespace(project=SimpleNamespace(id='p1'))
    monkeypatch.setattr(adapter.DispatcherLoop,'_reason_trigger',lambda *args:None)
    assert dispatcher._reason_trigger(project) == 'wuji-assessment:'+review
    dispatcher.control.request.assert_called_once_with('GET','/internal/v1/dispatch/reason-requests/p1')
    dispatcher.control.request.reset_mock()
    monkeypatch.setattr(adapter.DispatcherLoop,'_reason_trigger',lambda *args:'facts:2->3')
    assert dispatcher._reason_trigger(project) == 'facts:2->3'
    dispatcher.control.request.assert_not_called()
