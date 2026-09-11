"""Stop receipt and late-cancel checks without database, Kubernetes, or network."""
import asyncio
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock,Mock
import pytest

root=Path(__file__).parents[2]
sys.path.insert(0,str(root/'services'/'execution-control'))
from core import Core,GatewayUnknown,utcnow
import core as core_module

class Result:
    def __init__(self,value=None):self.value=value
    def mappings(self):return self
    def one(self):return self.value
    def scalar_one(self):return self.value

class FakeStore:
    def __init__(self,run=None,rt=None,current=None):
        self.run=run;self.rt=rt;self.current=current;self.writes=[];self.events=[];self.pending=False
    @contextmanager
    def tx(self):yield self
    def execute(self,query,params=None):
        query=str(query);self.writes.append((query,params or {}))
        if query.startswith('SELECT state,stop_reason,execution_epoch FROM tasks'):return Result(self.current)
        return Result()
    def one(self,query,params=None):
        if 'FROM agent_runs WHERE id=' in query:return self.run
        if 'FROM core_operations' in query:return self.pending
        if 'FROM runtime_attempts' in query:return self.rt
        return None
    def rows(self,*args):return []
    def event(self,c,task_id,summary,updates=None):self.events.append(updates or {})
    def stop_requested(self,*args):pass


def test_finish_requires_exit_receipt_and_separates_result_state():
    core=object.__new__(Core);rid=uuid4()
    base={'id':rid,'task_id':uuid4(),'outcome':None,'output':None,'receipt':None}
    for outcome,receipt,pending,expected in [
        ('unknown',None,False,('unknown','unknown')),
        ('rejected',None,False,('not_started','rejected')),
        ('success',{'id':str(uuid4()),'state':'exited'},False,('unknown','synced')),
        ('success',{'id':str(rid),'state':'exited'},True,('exited','unknown')),
    ]:
        store=FakeStore(dict(base,receipt=receipt,output='raw' if outcome=='success' else None))
        store.pending=pending;core.store=store
        result=core.finish_run(rid,outcome)
        assert (result['state'],result['result_state'])==expected


def test_unknown_key_block_cannot_announce_revocation():
    core=object.__new__(Core);core.store=FakeStore()
    core.gateway=SimpleNamespace(block=AsyncMock(side_effect=GatewayUnknown()),lookup=AsyncMock(return_value={'blocked':False}))
    task={'id':uuid4(),'state':'cancelling','updated_at':utcnow(),'stop_reason':'user_cancelled'}
    ex={'id':uuid4(),'task_id':task['id'],'key_hash':'a'*64,'model_state':'ready'}
    asyncio.run(core.stop(ex,task))
    assert core.store.events[-1]['state']=='reconciling'
    assert core.store.events[-1]['egress_state']=='unknown'
    assert not any("state='stopped',result=" in query for query,_ in core.store.writes)
    assert any(params.get('state')=='block_unknown' for _,params in core.store.writes)


def test_missing_uid_reconciles_before_final_current_cancel(monkeypatch):
    core=object.__new__(Core);task_id=uuid4();runtime_id=uuid4()
    task={'id':task_id,'state':'completing','updated_at':utcnow(),'stop_reason':'exploration_completed'}
    ex={'id':uuid4(),'task_id':task_id,'model_state':'pending','key_hash':None}
    cfg={'tenant_id':str(uuid4()),'task_id':str(task_id),'agent_resources':{},'kali_resources':{},'namespace':'wuji-test','pod_name':'frozen-pod'}
    core.store=FakeStore(rt={'id':runtime_id,'config':cfg,'pod_uid':None},current={'state':'cancelling','stop_reason':'user_cancelled','execution_epoch':2})
    monkeypatch.setattr(core_module,'ContainerResources',lambda **kw:kw)
    monkeypatch.setattr(core_module,'TaskRuntimeConfig',lambda **kw:SimpleNamespace(**kw))
    verify=Mock();monkeypatch.setattr(core_module,'verify_pod_ownership',verify)
    core.pods=SimpleNamespace(read_pod=Mock(return_value={'metadata':{'uid':'actual-uid'}}))
    core.controller=SimpleNamespace(stop=Mock(return_value=SimpleNamespace(state='stopped')))
    core.evidence_complete=Mock(return_value=False);core.graph_snapshot=AsyncMock()
    asyncio.run(core.stop(ex,task))
    core.pods.read_pod.assert_called_once_with('wuji-test','frozen-pod')
    verify.assert_called_once()
    assert core.controller.stop.call_args.args[1]=='actual-uid'
    assert any(params.get('uid')=='actual-uid' for _,params in core.store.writes)
    assert core.store.events[-1]['state']=='cancelled'
