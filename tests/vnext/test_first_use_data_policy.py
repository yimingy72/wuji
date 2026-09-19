"""Frozen external-material consent is enforced before any model send."""

from hashlib import sha256

from support.p06 import NATIVE_MODEL_REQUEST, TASK, fresh_ledger, model_case, model_headers
from wuji_core.http import canonical_json_bytes, strict_json_loads


def test_real_model_admission_requires_persisted_creator_consent(
    db_environment, tmp_path, audit_directory,
):
    # The upstream is synthetic; only policy admission is under test here.
    with model_case(db_environment, tmp_path, audit_directory) as case:
        def consent(value):
            with db_environment.migration_connection() as connection:
                source = connection.execute("SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)).fetchone()[0]
                definition = strict_json_loads(source)
                definition["evaluation_mode"] = "real_model"
                definition["task"]["external_analysis_approved"] = value
                raw = canonical_json_bytes(definition)
                connection.execute("UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
                                   (raw.decode(), sha256(raw).hexdigest(), TASK))
        consent(False)
        rejected = case.client.post("/internal/v2/model/chat/completions",
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST), headers=model_headers(case, "policy-missing"))
        assert rejected.status_code == 503, rejected.text
        assert case.upstream.exchanges == []
        assert fresh_ledger(case).snapshot(case.access, TASK).model_attempts == 0
        consent(True)
        accepted = case.client.post("/internal/v2/model/chat/completions",
            content=canonical_json_bytes(NATIVE_MODEL_REQUEST), headers=model_headers(case, "policy-confirmed"))
        assert accepted.status_code == 200, accepted.text
        assert len(case.upstream.exchanges) == 1
