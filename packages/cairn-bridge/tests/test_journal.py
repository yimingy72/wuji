from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from wuji_cairn_bridge.errors import BindingConflict, OperationConflict
from wuji_cairn_bridge.journal import SQLAlchemyJournal, metadata
from wuji_cairn_bridge.models import AgentResult, TaskKey


def test_durable_claim_and_identity(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'journal.sqlite'}")
    metadata.create_all(engine)
    journal = SQLAlchemyJournal(engine)
    key = TaskKey(uuid4(), uuid4(), uuid4())
    server = uuid4()
    journal.prepare_binding(key, server, "a" * 64)
    assert journal.claim_binding(key)
    assert not SQLAlchemyJournal(engine).claim_binding(key)
    journal.finish_binding(key, "project-one")
    assert SQLAlchemyJournal(engine).get_binding(key).project_id == "project-one"
    alien = replace(key, tenant_id=uuid4())
    assert journal.get_binding(alien) is None
    with pytest.raises(BindingConflict):
        journal.prepare_binding(alien, server, "a" * 64)
    with pytest.raises(BindingConflict):
        journal.prepare_binding(key, server, "b" * 64)
    result = AgentResult(key, uuid4(), uuid4(), "intent-one", "conclusion", 1, 1, "a" * 64, "b" * 64)
    digest = result.request_digest(server, "project-one")
    journal.prepare_result(result, server, "project-one", digest)
    assert journal.claim_result(key, result.operation_id)
    assert not SQLAlchemyJournal(engine).claim_result(key, result.operation_id)
    journal.set_result_state(key, result.operation_id, "unknown")
    recovered = SQLAlchemyJournal(engine)
    assert recovered.get_result(key, result.operation_id).result == result
    assert recovered.get_result(alien, result.operation_id) is None
    assert not recovered.claim_result(key, result.operation_id)
    recovered.finish_result(key, result.operation_id, "fact-one")
    assert recovered.prepare_result(result, server, "project-one", digest).fact_id == "fact-one"
    with pytest.raises(OperationConflict):
        recovered.finish_result(key, result.operation_id, "fact-other")
    changed = replace(result, description="other")
    with pytest.raises(OperationConflict):
        recovered.prepare_result(changed, server, "project-one", changed.request_digest(server, "project-one"))
    engine.dispose()


def test_binding_unknown_and_native_uniqueness(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bindings.sqlite'}")
    metadata.create_all(engine)
    journal = SQLAlchemyJournal(engine)
    server = uuid4()
    first = TaskKey(uuid4(), uuid4(), uuid4())
    second = replace(first, task_id=uuid4())
    for key in (first, second):
        journal.prepare_binding(key, server, "a" * 64)
        assert journal.claim_binding(key)
    journal.finish_binding(first, "native-one")
    with pytest.raises(BindingConflict):
        journal.finish_binding(second, "native-one")
    journal.set_binding_state(second, "unknown")
    recovered = SQLAlchemyJournal(engine)
    assert recovered.prepare_binding(second, server, "a" * 64).state == "unknown"
    assert not recovered.claim_binding(second)
    with pytest.raises(BindingConflict):
        recovered.finish_binding(second, "native-guessed")
    engine.dispose()
