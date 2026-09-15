"""P04 integration: real signed HTTP, nonowner PostgreSQL and sealed bytes.

Prerequisite SQL supplies identities/policy/run bindings, never knowledge outcomes.
Tests catch self-certification, reference laundering, stale CAS, partial publication,
and model-output authority accidentally opening capture mutations.
"""

from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from support.p03 import access, seed
from support.http_capture import RecordedTestClient
from support.identity_provider import TestIdentityProvider as IdentityProvider
from wuji_core.contracts.knowledge import ClaimProposal, AssessmentCommand
from wuji_core.contracts.envelopes import ResultEnvelope
from wuji_core.http import create_app, canonical_json_bytes
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.schema import migrate
from wuji_core.persistence.uow import UnitOfWork, DomainError
from wuji_core.evidence.artifacts import ArtifactStore
from wuji_core.evidence.observations import EvidenceService
from wuji_core.persistence.snapshots import SnapshotRepository

TASK = "task-fixture"
OWNER = ("tenant-fixture", "project-fixture", TASK)
BASE = "/api/v2/tasks/task-fixture"
IDENTITY = dict(
    tenant_id=OWNER[0],
    project_id=OWNER[1],
    task_id=TASK,
    work_item_id="work-fixture",
    agent_run_id="run-fixture",
    receiver_id="receiver-fixture",
    execution_epoch="1",
    run_epoch="1",
    runtime_attempt="1",
)


def production(name):
    try:
        return import_module("wuji_core." + name)
    except ModuleNotFoundError as error:
        pytest.fail(f"P04 production entrypoint absent: {error.name}")


def proposal(text="A freely shared hypothesis", *, kind="hypothesis", basis=(), **kw):
    return dict(
        client_ref="c",
        kind=kind,
        assertion_role="candidate_fact",
        text=text,
        basis_refs=list(basis),
        limitations=["isolated fixture"],
        **kw,
    )


def test_revision_and_raw_first_wire_contract():
    revised = proposal(revises={"entity_type": "claim", "id": "c", "revision": "1"})
    try:
        parsed = ClaimProposal.model_validate(revised)
    except ValidationError:
        pytest.fail("ClaimProposal must accept a fixed revises reference")
    assert parsed.revises.id == "c"
    raw = dict(
        schema_version="wuji.result-envelope.v2",
        submission_id="s",
        identity=IDENTITY,
        snapshot_id="snap",
        read_set=[],
        raw_output_ref={"id": "a", "version": "1", "sha256": "a" * 64},
        raw_output_digest="a" * 64,
        payload="not an AgentPayload",
        producer_version="fixture-v1",
    )
    assert ResultEnvelope.model_validate(raw).payload == "not an AgentPayload"


@contextmanager
def case(env, tmp_path, audit):
    # Imports deliberately occur here: RED is a clear missing production assertion.
    claims_mod = production("blackboard.claims")
    assess_mod = production("blackboard.assessments")
    view_mod = production("blackboard.fact_view")
    commit_mod = production("blackboard.committer")
    with env.migration_connection() as m:
        migrate(m, application_role=env.application_role)
        seed(m)
        seed(m, project="project-other", task="task-sibling")
        for task, project in [(TASK, OWNER[1]), ("task-sibling", "project-other")]:
            own = (OWNER[0], project, task)
            m.execute(
                "INSERT INTO vnext.task_assessment_policy(tenant_id,project_id,task_id,policy_version) VALUES (%s,%s,%s,'assessment-policy-v1')",
                own,
            )
            for subject, kind, qualified in [
                ("agent-fixture", "agent", False),
                ("reader-fixture", "human", False),
                ("assessor-fixture", "human", True),
            ]:
                m.execute(
                    "INSERT INTO vnext.knowledge_actor(tenant_id,project_id,task_id,subject,producer_kind,qualified_human) VALUES (%s,%s,%s,%s,%s,%s)",
                    (*own, subject, kind, qualified),
                )
        m.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_settle,can_model_output,clearance) VALUES (%s,%s,%s,'worker-fixture',true,true,true,true,1)",
            OWNER,
        )
        m.execute(
            "INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,can_settle) VALUES (%s,%s,%s,'run-fixture','worker-fixture','agent-fixture',true)",
            OWNER,
        )
    uow = UnitOfWork(env.additional_app_connection)
    store = ArtifactStore(uow, tmp_path / "objects")
    claims = claims_mod.ClaimService(uow)
    assessments = assess_mod.AssessmentService(uow, store)
    view = view_mod.FactLedger(uow)
    committer = commit_mod.ResultCommitter(uow, store, claims)
    provider = IdentityProvider(audit_path=audit / "identity-events.jsonl")
    tokens = provider.tokens()
    worker = provider.issue(
        subject="worker-fixture", tenant_id=OWNER[0], roles=["worker"]
    )
    human = provider.issue(
        subject="assessor-fixture", tenant_id=OWNER[0], roles=["human", "assessor"]
    )
    verifier = TokenVerifier(
        public_key_pem=tokens.public_key_pem,
        issuer=tokens.issuer,
        audience=tokens.audience,
    )
    routers = [
        production("http.knowledge").create_knowledge_router(
            claims, assessments, committer
        ),
        production("http.records").create_records_router(view),
        production("http.evidence").create_evidence_router(EvidenceService(uow, store)),
    ]
    client = RecordedTestClient(
        create_app(token_verifier=verifier, routers=routers),
        audit_path=audit / "http-exchanges.jsonl",
    )
    yield SimpleNamespace(**locals())
    client.close()


def headers(c, role="agent", key=None):
    token = (
        c.worker
        if role == "worker"
        else c.human if role == "human" else getattr(c.tokens, role)
    )
    return {"Authorization": "Bearer " + token, "Idempotency-Key": key or str(uuid4())}


def post_claim(c, body, *, role="agent", key=None):
    return c.client.post(
        BASE + "/claims/proposals", json=body, headers=headers(c, role, key)
    )


def get_claim(c, ref, *, snapshot=None, role="agent"):
    params = {"revision": ref["revision"]}
    if snapshot:
        params["snapshot_id"] = snapshot
    return c.client.get(
        BASE + "/records/claim/" + ref["id"], params=params, headers=headers(c, role)
    )


def captured(c, *, body=b'{"version":17}', completeness="complete", access_level=0):
    ref = c.store.stage(
        access(),
        TASK,
        "attempt-fixture",
        body,
        "application/json",
        completeness=completeness,
        access_level=access_level,
    )
    c.store.seal(access(), TASK, ref)
    c.audit.joinpath("capture-" + ref.id + ".bin").write_bytes(body)
    envelope = dict(
        schema_version="wuji.capture.v2",
        capture_id=str(uuid4()),
        identity=IDENTITY,
        tool_call_id="tool-fixture",
        tool_attempt_id="attempt-fixture",
        artifact_refs=[ref.model_dump(mode="json")],
        capture_layer="fixture_file_bytes",
        observed_at="2026-09-13T00:00:00Z",
        received_at="2026-09-13T00:00:01Z",
        evidence_origin="fixture_capture",
        conditions=[],
        completeness=completeness,
    )
    response = c.client.post(
        "/internal/v2/evidence",
        json=envelope,
        headers=headers(c, "collector", envelope["capture_id"]),
    )
    assert response.status_code == 202, response.text
    return ref, response.json()["observation_ref"]


def exact(ref, obs, *, value=17, text=None, absent=False):
    method = "json-pointer-absent-v1" if absent else "json-pointer-equals-v1"
    pointer = "/missing" if absent else "/version"
    assertion = dict(
        predicate=method, artifact_ref=ref.model_dump(mode="json"), pointer=pointer
    )
    if not absent:
        assertion["expected"] = value
    # Independently written specification template; never call the checker renderer.
    wording = (
        f"完整捕获内容 {ref.id}@1 中不存在 /missing。"
        if absent
        else f"已捕获内容 {ref.id}@1 的 /version 字段等于 {value}。"
    )
    return proposal(
        text or wording,
        kind="observation-summary",
        basis=[obs],
        structured_assertion=assertion,
    )


def assess(
    c,
    ref,
    inputs,
    *,
    method="json-pointer-equals-v1",
    kind="deterministic",
    state="supported",
    role="assessor",
    supersedes=(),
):
    body = dict(
        schema_version="wuji.api.v2",
        expected_version=ref["revision"],
        assessment=dict(
            assessment_id=str(uuid4()),
            claim_ref=ref,
            input_refs=inputs,
            grounding_state="content_checked",
            evidence_state=state,
            applicability_state="current",
            method_kind=kind,
            method_version=method,
            reviewer_ref="assessor-fixture",
            conditions=["isolated fixture"],
            reason="Read fixed evidence and assertion",
        ),
        supersedes_assessment_ids=list(supersedes),
        supersedes_reason="Correct prior assessment" if supersedes else None,
    )
    return c.client.post(BASE + "/assessments", json=body, headers=headers(c, role))


def test_agent_candidate_real_check_and_only_one_body(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        artifact, obs = captured(c)
        body = exact(artifact, obs)
        accepted = post_claim(c, body, key="candidate")
        assert accepted.status_code == 202, accepted.text
        ref = accepted.json()["canonical_ref"]
        before = get_claim(c, ref).json()
        assert before["assessment"]["evidence_state"] == "unassessed"
        assert before["assessment"]["eligible"] is False
        checked = assess(c, ref, [obs])
        assert checked.status_code == 202, checked.text
        after = get_claim(c, ref).json()
        assert after["display_kind"] == "fact"
        assert after["record"]["producer_kind"] == "agent"
        assert after["record"]["text"] == body["text"]
        with c.uow.transaction(access("agent-fixture", role="agent"), TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.claim_revision"
                ).fetchone()[0]
                == 1
            )
            assert (
                tx.connection.execute("SELECT to_regclass('vnext.fact')").fetchone()[0]
                is None
            )
        assert post_claim(c, body, key="candidate").json() == accepted.json()
        assert (
            post_claim(
                c, {**body, "text": body["text"] + " "}, key="candidate"
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    "variant,want",
    [
        ("wrong-value", "contradicted"),
        ("unrelated-prose", "unassessed"),
        ("partial-negative", "inconclusive"),
    ],
)
def test_precise_checker_does_not_launder_evidence(
    db_environment, tmp_path, audit_directory, variant, want
):
    with case(db_environment, tmp_path, audit_directory) as c:
        artifact, obs = captured(
            c, completeness="partial" if variant == "partial-negative" else "complete"
        )
        body = exact(
            artifact,
            obs,
            value=18 if variant == "wrong-value" else 17,
            text="系统安全" if variant == "unrelated-prose" else None,
            absent=variant == "partial-negative",
        )
        ref = post_claim(c, body).json()["canonical_ref"]
        response = assess(
            c,
            ref,
            [obs],
            method=(
                "json-pointer-absent-v1"
                if variant == "partial-negative"
                else "json-pointer-equals-v1"
            ),
        )
        assert response.status_code == 202, response.text
        view = get_claim(c, ref).json()["assessment"]
        assert view["evidence_state"] == want
        assert not view["eligible"]


def test_free_candidates_and_model_opinions_do_not_self_certify(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        artifact, obs = captured(c)
        for body in [
            proposal(),
            proposal(
                "tool says system healthy", kind="observation-summary", basis=[obs]
            ),
        ]:
            response = post_claim(c, body)
            assert response.json()["status"] == "accepted_shared"
            ref = response.json()["canonical_ref"]
            assert not get_claim(c, ref).json()["assessment"]["eligible"]
        assert (
            post_claim(c, {**proposal(), "evidence_state": "supported"}).status_code
            == 422
        )
        assert assess(c, ref, [obs], role="agent").status_code == 403
        assert (
            assess(
                c, ref, [obs], kind="model_review", method="model-review-v1"
            ).status_code
            == 422
        )
        opinion = assess(
            c,
            ref,
            [obs],
            kind="model_review",
            method="model-review-v1",
            state="inconclusive",
        )
        assert opinion.status_code == 202, opinion.text
        assert not get_claim(c, ref).json()["assessment"]["eligible"]


def test_revision_conflict_aggregation_and_frozen_snapshot(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        artifact, obs = captured(c)
        body = exact(artifact, obs)
        v1 = post_claim(c, body).json()["canonical_ref"]
        support = assess(c, v1, [obs]).json()["assessment_id"]
        snap = SnapshotRepository(c.uow).create(
            TASK, access("agent-fixture", role="agent")
        )
        contradiction = assess(
            c,
            v1,
            [obs],
            kind="human_attestation",
            method="human-attestation-v1",
            state="contradicted",
            role="human",
        )
        assert contradiction.status_code == 202, contradiction.text
        assert (
            get_claim(c, v1).json()["assessment"]["applicability_state"] == "disputed"
        )
        assert (
            get_claim(c, v1, snapshot=snap.snapshot_id).json()["assessment"]["eligible"]
            is True
        )
        assert assess(c, v1, [obs]).status_code == 202
        assert not get_claim(c, v1).json()["assessment"][
            "eligible"
        ]  # not last writer wins
        v2 = post_claim(c, {**body, "revises": v1}).json()["canonical_ref"]
        assert v2["id"] == v1["id"] and v2["revision"] == "2"
        assert get_claim(c, v2).json()["assessment"]["evidence_state"] == "unassessed"
        assert post_claim(c, {**body, "revises": v1}).status_code == 409
        assert get_claim(c, v1).json()["record"]["supersedes"] is None
        assert get_claim(c, v2).json()["record"]["supersedes"] == v1
        assert support in get_claim(c, v1).json()["assessment"]["assessment_ids"]


def result(c, payload, *, submission=None, snapshot=None, raw=None, read_set=()):
    raw = canonical_json_bytes(payload) if raw is None else raw
    ref = c.store.stage_model_output(
        access("worker-fixture", role="worker"),
        TASK,
        "run-fixture",
        raw,
        "application/json",
    )
    c.store.seal(access("worker-fixture", role="worker"), TASK, ref)
    c.audit.joinpath("raw-" + ref.id + ".bin").write_bytes(raw)
    snap = (
        snapshot
        or SnapshotRepository(c.uow)
        .create(TASK, access("worker-fixture", role="worker"))
        .snapshot_id
    )
    return dict(
        schema_version="wuji.result-envelope.v2",
        submission_id=submission or str(uuid4()),
        identity=IDENTITY,
        snapshot_id=snap,
        read_set=list(read_set),
        raw_output_ref=ref.model_dump(mode="json"),
        raw_output_digest=ref.sha256.root,
        payload=payload,
        producer_version="fixture-v1",
    )


def payload(claims=(), intents=()):
    return dict(
        schema_version="wuji.agent-payload.v2",
        claims=list(claims),
        intent_proposals=list(intents),
        limitations=[],
    )


def submit(c, envelope):
    return c.client.post(
        "/internal/v2/results",
        json=envelope,
        headers=headers(c, "worker", envelope["submission_id"]),
    )


def test_raw_first_rejection_and_model_output_has_no_capture_power(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        env = result(c, None, raw=b"not JSON: final model reply")
        response = submit(c, env)
        assert response.status_code == 202, response.text
        assert (
            response.json()["status"] == "rejected"
            and response.json()["code"] == "INVALID_SCHEMA"
        )
        with c.uow.transaction(access("worker-fixture", role="worker"), TASK) as tx:
            rows = tx.connection.execute(
                "SELECT status FROM vnext.result_submission"
            ).fetchall()
            assert rows == [("received",)]
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.observation"
                ).fetchone()[0]
                == 0
            )
            a = tx.connection.execute(
                "SELECT tool_attempt_id,agent_run_id,provenance FROM vnext.artifact WHERE entity_id=%s",
                (env["raw_output_ref"]["id"],),
            ).fetchone()
            assert a == (None, "run-fixture", "model_output")
        with pytest.raises(DomainError):
            c.store.stage(
                access("worker-fixture", role="worker"),
                TASK,
                "attempt-fixture",
                b"bad",
                "text/plain",
            )
        assert (
            c.committer.reconcile(
                access("worker-fixture", role="worker"), TASK, env["submission_id"]
            ).model_dump(mode="json")
            == response.json()
        )
        assert submit(c, env).json() == response.json()


def test_same_batch_topology_failure_has_no_phantom_records(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        a = {**proposal("A"), "client_ref": "a", "basis_refs": [{"client_ref": "b"}]}
        b = {
            **proposal("B"),
            "client_ref": "b",
            "basis_refs": [{"client_ref": "missing"}],
        }
        intent = dict(
            client_ref="i",
            question="Check hypothesis",
            basis_refs=[{"client_ref": "a"}],
            expected_output="Evidence",
        )
        env = result(
            c,
            payload([a, b, {**proposal("independent"), "client_ref": "ok"}], [intent]),
        )
        response = submit(c, env)
        assert response.status_code == 202, response.text
        components = {r["local_ref"]: r for r in response.json()["components"]}
        assert components["ok"]["status"] == "accepted_shared"
        for local in ["a", "b", "i"]:
            assert (
                components[local]["status"] == "rejected"
                and components[local]["canonical_ref"] is None
            )
        with c.uow.transaction(access("worker-fixture", role="worker"), TASK) as tx:
            assert tx.connection.execute(
                "SELECT text FROM vnext.claim_revision"
            ).fetchall() == [("independent",)]
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.intent_revision"
                ).fetchone()[0]
                == 0
            )
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.entity_revision_registry WHERE entity_type IN ('claim','intent')"
                ).fetchone()[0]
                == 1
            )
        good = result(c, payload([a, {**proposal("B"), "client_ref": "b"}], [intent]))
        assert all(
            r["status"] == "accepted_shared"
            for r in submit(c, good).json()["components"]
        )


def test_old_snapshot_append_and_current_auth_recheck(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        snap = (
            SnapshotRepository(c.uow)
            .create(TASK, access("worker-fixture", role="worker"))
            .snapshot_id
        )
        one = result(c, payload([proposal("first")]), snapshot=snap)
        two = result(c, payload([proposal("second")]), snapshot=snap)
        assert submit(c, one).json()["status"] == "accepted"
        assert submit(c, two).json()["status"] == "accepted"
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE task_id=%s AND subject='worker-fixture'",
                (TASK,),
            )
        assert submit(c, one).status_code in (403, 404)


def test_claim_cross_owner_refs_and_agent_revision_authority(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        human = post_claim(c, proposal("human text"), role="reader").json()[
            "canonical_ref"
        ]
        assert (
            post_claim(c, {**proposal("rewrite"), "revises": human}).status_code == 404
        )
        sibling = c.client.post(
            "/api/v2/tasks/task-sibling/claims/proposals",
            json=proposal("sibling"),
            headers=headers(c),
        ).json()["canonical_ref"]
        rejected = post_claim(c, proposal(basis=[sibling]))
        assert rejected.status_code == 202, rejected.text
        assert rejected.json()["status"] == "rejected"
        assert rejected.json()["canonical_ref"] is None


def test_assessment_actions_are_append_only_and_qualified(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        artifact, obs = captured(c)
        ref = post_claim(c, exact(artifact, obs)).json()["canonical_ref"]
        supported = assess(c, ref, [obs]).json()["assessment_id"]
        opposed = assess(
            c,
            ref,
            [obs],
            kind="human_attestation",
            method="human-attestation-v1",
            state="contradicted",
            role="human",
        ).json()["assessment_id"]
        replacing = assess(c, ref, [obs], supersedes=[opposed])
        assert replacing.status_code == 202, replacing.text
        assert get_claim(c, ref).json()["assessment"]["eligible"] is True
        with pytest.raises(DomainError):
            c.assessments.invalidate(
                access("agent-fixture", role="agent"),
                TASK,
                supported,
                kind="retracted",
                reason="model says so",
                idempotency_key="bad",
            )
        for aid in [supported, replacing.json()["assessment_id"]]:
            c.assessments.invalidate(
                access("assessor-fixture", role="assessor"),
                TASK,
                aid,
                kind="stale",
                reason="environment reset",
                idempotency_key="stale-" + aid,
            )
        current = get_claim(c, ref).json()["assessment"]
        assert not current["eligible"] and current["applicability_state"] == "stale"
        with c.uow.transaction(access("assessor-fixture", role="assessor"), TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.assessment"
                ).fetchone()[0]
                == 3
            )
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.assessment_action"
                ).fetchone()[0]
                == 3
            )


def test_raw_reconcile_after_received_and_late_settlement(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        env = result(c, payload([proposal("received, then publish")]))
        first = c.committer.receive(access("worker-fixture", role="worker"), env)
        assert first.status.value == "received"
        assert (
            c.committer.lookup(
                access("worker-fixture", role="worker"), TASK, env["submission_id"]
            ).status.value
            == "received"
        )
        assert submit(c, env).json()["status"] == "accepted"
        mismatch = result(
            c,
            payload([proposal("client alternate")]),
            raw=canonical_json_bytes(payload([proposal("sealed original")])),
        )
        assert submit(c, mismatch).json()["code"] == "INVALID_SCHEMA"
        late = result(c, payload([proposal("historical only")]))
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task SET execution_allowed=false,execution_epoch=execution_epoch+1 WHERE task_id=%s",
                (TASK,),
            )
        response = submit(c, late)
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "historical_only"
        assert response.json()["components"] == []
        with c.uow.transaction(access("worker-fixture", role="worker"), TASK) as tx:
            assert tx.connection.execute(
                "SELECT text FROM vnext.claim_revision"
            ).fetchall() == [("received, then publish",)]
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.tool_attempt"
                ).fetchone()[0]
                == 1
            )


def test_model_output_capability_cannot_seal_capture_or_change_lease(
    db_environment, tmp_path, audit_directory
):
    import psycopg

    with case(db_environment, tmp_path, audit_directory) as c:
        ref = c.store.stage(
            access(), TASK, "attempt-fixture", b"capture pending", "text/plain"
        )
        worker = access("worker-fixture", role="worker")
        for statement, params in [
            ("UPDATE vnext.artifact SET state='sealed' WHERE entity_id=%s", (ref.id,)),
            (
                "UPDATE vnext.artifact_lease SET expires_at=clock_timestamp()+interval '1 hour' WHERE artifact_id=%s",
                (ref.id,),
            ),
            ("DELETE FROM vnext.artifact_lease WHERE artifact_id=%s", (ref.id,)),
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with c.uow.transaction(worker, TASK, capability="model_output") as tx:
                    tx.connection.execute(statement, params)
        with pytest.raises(DomainError):
            c.store.stage_model_output(
                access("agent-fixture", role="agent"),
                TASK,
                "run-fixture",
                b"agent forged writer",
                "text/plain",
            )
        good = c.store.stage_model_output(
            worker, TASK, "run-fixture", b"actual model final", "text/plain"
        )
        c.store.seal(worker, TASK, good)
        c.store.acquire_lease(worker, TASK, good, lease_owner="settlement")
        c.store.release_lease(worker, TASK, good, lease_owner="settlement")
        c.store.seal(access(), TASK, ref)
        assert c.store.read(worker, ref.id, "1")[0] == b"capture pending"


@pytest.mark.parametrize(
    "values",
    [
        {"cycle": True},
        {"duplicate": True},
        {"revision": True},
    ],
)
def test_batch_invalid_graph_preserves_independent_claim(
    db_environment, tmp_path, audit_directory, values
):
    with case(db_environment, tmp_path, audit_directory) as c:
        one = {**proposal("one"), "client_ref": "a"}
        two = {**proposal("two"), "client_ref": "b"}
        if values.get("cycle"):
            one["basis_refs"] = [{"client_ref": "b"}]
            two["basis_refs"] = [{"client_ref": "a"}]
        elif values.get("duplicate"):
            two["client_ref"] = "a"
        else:
            ref = post_claim(c, proposal("initial")).json()["canonical_ref"]
            one["revises"] = ref
            two["revises"] = ref
        response = submit(
            c,
            result(
                c, payload([one, two, {**proposal("unrelated"), "client_ref": "ok"}])
            ),
        )
        assert response.status_code == 202, response.text
        assert [r["status"] for r in response.json()["components"]] == [
            "rejected",
            "rejected",
            "accepted_shared",
        ]


def test_stale_readset_has_persistent_limit_not_execution_failure(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        original = post_claim(c, proposal("original")).json()["canonical_ref"]
        snap = SnapshotRepository(c.uow).create(
            TASK, access("worker-fixture", role="worker")
        )
        assert post_claim(c, proposal("revision", revises=original)).status_code == 202
        response = submit(
            c,
            result(
                c,
                payload([proposal("old analysis", basis=[original])]),
                snapshot=snap.snapshot_id,
                read_set=[original],
            ),
        )
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "accepted"
        item = response.json()["components"][0]
        assert item["code"] == "STALE_INPUT"
        assert any(
            "stale_input" in text
            for text in get_claim(c, item["canonical_ref"]).json()["record"][
                "limitations"
            ]
        )


def test_fixed_snapshot_includes_assessment_inputs_and_checks_current_access(
    db_environment, tmp_path, audit_directory
):
    from wuji_core.persistence.snapshots import SnapshotQuery

    with case(db_environment, tmp_path, audit_directory) as c:
        a, obs = captured(c)
        ref = post_claim(
            c, proposal("Reviewed prose", kind="observation-summary")
        ).json()["canonical_ref"]
        assert (
            assess(
                c,
                ref,
                [obs],
                kind="human_attestation",
                method="human-attestation-v1",
                role="human",
            ).status_code
            == 202
        )
        snap = SnapshotRepository(c.uow).create(
            TASK,
            access("agent-fixture", role="agent"),
            query=SnapshotQuery(entity_types=("claim",)),
        )
        refs = [r.model_dump(mode="json") for r in snap.refs]
        assert obs in refs
        assert {"entity_type": "artifact", "id": a.id, "revision": "1"} in refs
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE task_id=%s AND subject='agent-fixture'",
                (TASK,),
            )
        assert get_claim(c, ref, snapshot=snap.snapshot_id).status_code == 404


def test_migration_preserves_heads_and_rejects_unknown(db_environment):
    with db_environment.migration_connection() as m:
        migrate(m, application_role=db_environment.application_role)
        migrate(m, application_role=db_environment.application_role)
        heads = {
            row[0]
            for row in m.execute("SELECT head FROM vnext.schema_migration").fetchall()
        }
        # Later migrations extend the same chain; the P03/P04 heads must remain
        # recorded and re-running the migration must not duplicate them.
        assert {
            "vnext_0001_p03",
            "vnext_0002_p03_evidence_authority",
            "vnext_0003_p04_knowledge",
            "vnext_0004_p04_assessment_visibility",
            "vnext_0005_p04_input_freshness",
        } <= heads
        m.execute("INSERT INTO vnext.schema_migration(head) VALUES('unknown')")
        with pytest.raises(ValueError, match="unrecognized"):
            migrate(m, application_role=db_environment.application_role)


def test_generic_scalar_checks_keep_precision_and_partial_scope(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        for raw, expected, wording, want in [
            (b'{"version":"healthy"}', "healthy", '"healthy"', True),
            (b'{"version":false}', 0, "0", False),
            (
                b'{"version":9007199254740993}',
                9007199254740993,
                "9007199254740993",
                True,
            ),
            (b'{"version":null}', None, "null", True),
        ]:
            a, obs = captured(c, body=raw, completeness="partial")
            body = exact(
                a,
                obs,
                value=expected,
                text=f"已捕获内容 {a.id}@1 的 /version 字段等于 {wording}。",
            )
            ref = post_claim(c, body).json()["canonical_ref"]
            assert assess(c, ref, [obs]).status_code == 202
            assert get_claim(c, ref).json()["assessment"]["eligible"] is want
        a, obs = captured(c)
        ref = post_claim(c, exact(a, obs, absent=True)).json()["canonical_ref"]
        assert assess(c, ref, [obs], method="json-pointer-absent-v1").status_code == 202
        assert get_claim(c, ref).json()["assessment"]["eligible"] is True


def test_model_final_output_for_run_without_any_tool_attempt(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        with c.env.migration_connection() as m:
            m.execute(
                "INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,environment_ref,model_mode) VALUES(%s,%s,%s,'zero-tool-run','work-b','zero-receiver','environment-fixture','synthetic')",
                OWNER,
            )
            m.execute(
                "INSERT INTO vnext.run_writer(tenant_id,project_id,task_id,agent_run_id,subject,agent_subject,can_settle) VALUES(%s,%s,%s,'zero-tool-run','worker-fixture','agent-fixture',true)",
                OWNER,
            )
        worker = access("worker-fixture", role="worker")
        raw = canonical_json_bytes(payload([proposal("analysis without tools")]))
        ref = c.store.stage_model_output(
            worker, TASK, "zero-tool-run", raw, "application/json"
        )
        c.store.seal(worker, TASK, ref)
        snap = SnapshotRepository(c.uow).create(TASK, worker)
        env = dict(
            schema_version="wuji.result-envelope.v2",
            submission_id="zero-tool-result",
            identity={
                **IDENTITY,
                "agent_run_id": "zero-tool-run",
                "work_item_id": "work-b",
                "receiver_id": "zero-receiver",
            },
            snapshot_id=snap.snapshot_id,
            read_set=[],
            raw_output_ref=ref.model_dump(mode="json"),
            raw_output_digest=ref.sha256.root,
            payload=None,
            producer_version="fixture-v1",
        )
        response = submit(c, env)
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "accepted"
        with c.uow.transaction(worker, TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.tool_attempt WHERE agent_run_id='zero-tool-run'"
                ).fetchone()[0]
                == 0
            )


def test_assessment_request_keeps_actor_foreign_key(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        a, obs = captured(c)
        ref = post_claim(c, exact(a, obs)).json()["canonical_ref"]
        assert assess(c, ref, [obs]).status_code == 202
        with c.uow.transaction(access("assessor-fixture", role="assessor"), TASK) as tx:
            # to_jsonb permits a semantic missing-field assertion on the pre-extension table.
            stored = tx.connection.execute(
                "SELECT to_jsonb(a)->>'actor_subject' FROM vnext.assessment a"
            ).fetchone()[0]
            assert stored == "assessor-fixture"


def test_unverified_intent_is_readable_but_not_in_older_snapshot(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        claim = post_claim(c, proposal()).json()["canonical_ref"]
        snap = SnapshotRepository(c.uow).create(
            TASK, access("agent-fixture", role="agent")
        )
        body = dict(
            client_ref="i",
            question="Check hypothesis",
            basis_refs=[claim],
            expected_output="actual evidence",
        )
        accepted = c.client.post(
            BASE + "/intents/proposals", json=body, headers=headers(c)
        )
        assert accepted.status_code == 202, accepted.text
        ref = accepted.json()["canonical_ref"]
        path = BASE + "/records/intent/" + ref["id"]
        read = c.client.get(path, params={"revision": "1"}, headers=headers(c))
        assert read.status_code == 200, read.text
        assert read.json()["record"]["acceptance_state"] == "admitted"
        assert (
            c.client.get(
                path,
                params={"revision": "1", "snapshot_id": snap.snapshot_id},
                headers=headers(c),
            ).status_code
            == 422
        )
        with c.uow.transaction(access("agent-fixture", role="agent"), TASK) as tx:
            assert (
                tx.connection.execute(
                    "SELECT count(*) FROM vnext.work_item"
                ).fetchone()[0]
                == 2
            )  # only seeded prerequisites


def test_hidden_counterevidence_cannot_turn_public_claim_into_fact(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        public, public_obs = captured(c)
        ref = post_claim(c, exact(public, public_obs)).json()["canonical_ref"]
        assert assess(c, ref, [public_obs]).status_code == 202
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET clearance=0 WHERE task_id=%s AND subject='reader-fixture'",
                (TASK,),
            )
        assert get_claim(c, ref, role="reader").json()["assessment"]["eligible"] is True
        old_snapshot = SnapshotRepository(c.uow).create(
            TASK, access("reader-fixture", role="reader")
        )
        private, private_obs = captured(
            c, body=b'{"private_counterexample":true}', access_level=1
        )
        opposed = assess(
            c,
            ref,
            [private_obs],
            kind="human_attestation",
            method="human-attestation-v1",
            state="contradicted",
            role="human",
        )
        assert opposed.status_code == 202, opposed.text
        high = get_claim(c, ref)
        assert high.status_code == 200, high.text
        assert high.json()["assessment"]["applicability_state"] == "disputed"
        assert high.json()["assessment"]["eligible"] is False
        for snapshot in (None, old_snapshot.snapshot_id):
            low = get_claim(c, ref, role="reader", snapshot=snapshot)
            assert low.status_code == 503, low.text
            assert low.json()["code"] == "CAPABILITY_UNAVAILABLE"
            assert low.json()["details"] == {}
            assert set(low.json()) == {
                "code",
                "message",
                "request_id",
                "retryable",
                "details",
            }
            for hidden in (
                opposed.json()["assessment_id"],
                private.id,
                private_obs["id"],
                "isolated fixture",
            ):
                assert hidden not in low.text
        with pytest.raises(DomainError) as unavailable:
            SnapshotRepository(c.uow).create(
                TASK, access("reader-fixture", role="reader")
            )
        assert unavailable.value.code == "CAPABILITY_UNAVAILABLE"


def test_private_new_premise_revision_invalidates_low_reader_fact(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET clearance=0 WHERE task_id=%s AND subject='reader-fixture'",
                (TASK,),
            )
        premise = post_claim(
            c, proposal("Public premise v1", kind="observation-summary")
        ).json()["canonical_ref"]
        derived = post_claim(
            c,
            proposal(
                "Conclusion supported by premise",
                kind="derived-conclusion",
                basis=[premise],
            ),
        ).json()["canonical_ref"]
        assert (
            assess(
                c,
                derived,
                [premise],
                kind="human_attestation",
                method="human-attestation-v1",
                role="human",
            ).status_code
            == 202
        )
        assert (
            get_claim(c, derived, role="reader").json()["assessment"]["eligible"]
            is True
        )
        private, private_obs = captured(
            c, body=b'{"updated_premise":false}', access_level=1
        )
        changed = post_claim(
            c,
            proposal(
                "Revised private premise v2",
                kind="observation-summary",
                basis=[private_obs],
                revises=premise,
            ),
        )
        assert (
            changed.status_code == 202
            and changed.json()["canonical_ref"]["revision"] == "2"
        )
        high = get_claim(c, derived, role="agent")
        low = get_claim(c, derived, role="reader")
        assert high.status_code == low.status_code == 200
        assert high.json()["assessment"]["applicability_state"] == "stale"
        assert low.json()["assessment"]["applicability_state"] == "stale", low.text
        assert not low.json()["assessment"]["eligible"]
        assert low.json()["assessment"]["assessment_ids"] == []
        assert low.json()["assessment"]["conditions"] == []
        assert low.json()["record"]["basis_refs"] == [premise]
        for hidden in (
            private.id,
            private_obs["id"],
            "Revised private premise v2",
            "updated_premise",
        ):
            assert hidden not in low.text
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET can_read=false WHERE task_id=%s AND subject='reader-fixture'",
                (TASK,),
            )
        assert get_claim(c, derived, role="reader").status_code == 404


def test_result_readset_uses_authoritative_freshness_for_private_new_version(
    db_environment, tmp_path, audit_directory
):
    with case(db_environment, tmp_path, audit_directory) as c:
        with c.env.migration_connection() as m:
            m.execute(
                "UPDATE vnext.task_access SET clearance=0 WHERE task_id=%s AND subject='worker-fixture'",
                (TASK,),
            )
        premise = post_claim(c, proposal("Public premise")).json()["canonical_ref"]
        snapshot = SnapshotRepository(c.uow).create(
            TASK, access("worker-fixture", role="worker")
        )
        private, private_obs = captured(
            c, body=b'{"private_update":true}', access_level=1
        )
        changed = post_claim(
            c, proposal("Private successor", basis=[private_obs], revises=premise)
        )
        assert (
            changed.status_code == 202
            and changed.json()["canonical_ref"]["revision"] == "2"
        )
        envelope = result(
            c,
            payload([proposal("Old snapshot analysis", basis=[premise])]),
            snapshot=snapshot.snapshot_id,
            read_set=[premise],
        )
        response = submit(c, envelope)
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "accepted"
        component = response.json()["components"][0]
        assert component["code"] == "STALE_INPUT", response.text
        read = get_claim(c, component["canonical_ref"])
        assert any(
            "stale_input" in text for text in read.json()["record"]["limitations"]
        )
        for hidden in (private.id, private_obs["id"], "Private successor"):
            assert hidden not in response.text and hidden not in read.text
