"""Real connection/identity/byte fixtures; no business implementation.

Parent rows and tool-start receipts below are explicit prerequisites, not proof
that Supervisor/admission ran. Only newly generated isolated databases are used.
"""

from contextlib import contextmanager
from importlib import import_module

from wuji_core.http.auth import Principal


def module(name):
    try:
        return import_module("wuji_core." + name)
    except ModuleNotFoundError as error:
        assert False, f"P03 production module absent: {error.name}"


def principal(subject="collector-fixture", tenant="tenant-fixture", role="collector"):
    return Principal(subject, tenant, frozenset({role}), "fixture-token-id")


def access(subject="collector-fixture", tenant="tenant-fixture", role="collector"):
    return module("persistence.uow").AccessContext(
        principal(subject, tenant, role), "fixture-request"
    )


def seed(
    connection,
    *,
    tenant="tenant-fixture",
    project="project-fixture",
    task="task-fixture",
):
    owner = (tenant, project, task)
    connection.execute(
        "INSERT INTO vnext.tenant(tenant_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (tenant,),
    )
    connection.execute(
        "INSERT INTO vnext.project(tenant_id,project_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (tenant, project),
    )
    connection.execute(
        "INSERT INTO vnext.task(tenant_id,project_id,task_id) VALUES (%s,%s,%s)", owner
    )
    for subject in [
        "collector-fixture",
        "agent-fixture",
        "reader-fixture",
        "assessor-fixture",
    ]:
        connection.execute(
            "INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,can_read,can_write,can_capture,can_settle,can_gc,can_assess,clearance) VALUES (%s,%s,%s,%s,true,true,%s,%s,%s,%s,1)",
            (
                *owner,
                subject,
                subject == "collector-fixture",
                subject == "collector-fixture",
                subject == "collector-fixture",
                subject == "assessor-fixture",
            ),
        )
    for work in ["work-fixture", "work-b"]:
        connection.execute(
            "INSERT INTO vnext.work_item(tenant_id,project_id,task_id,work_item_id) VALUES (%s,%s,%s,%s)",
            (*owner, work),
        )
    connection.execute(
        "INSERT INTO vnext.agent_run(tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,environment_ref,model_mode) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            *owner,
            "run-fixture",
            "work-fixture",
            "receiver-fixture",
            "environment-fixture",
            "synthetic",
        ),
    )
    connection.execute(
        "INSERT INTO vnext.tool_call(tenant_id,project_id,task_id,tool_call_id,session_lineage,message_id,provider_call_id,tool_definition_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            *owner,
            "tool-fixture",
            "lineage-fixture",
            "message-fixture",
            "provider-opaque-call",
            "fixture-reader-v1",
        ),
    )
    connection.execute(
        "INSERT INTO vnext.tool_attempt(tenant_id,project_id,task_id,tool_attempt_id,tool_call_id,agent_run_id,started_at,evidence_origin,capture_layer,receipt_json) VALUES (%s,%s,%s,%s,%s,%s,'2026-09-13T00:00:00Z','fixture_capture','fixture_file_bytes',%s)",
        (
            *owner,
            "attempt-fixture",
            "tool-fixture",
            "run-fixture",
            '{"fixture_prerequisite":true,"exit_code":0}',
        ),
    )
    connection.execute(
        "INSERT INTO vnext.collector_binding(tenant_id,project_id,task_id,tool_attempt_id,subject,can_settle) VALUES (%s,%s,%s,%s,%s,true)",
        (*owner, "attempt-fixture", "collector-fixture"),
    )


@contextmanager
def prepared(environment):
    schema = module("persistence.schema")
    uow = module("persistence.uow")
    with environment.migration_connection() as migration:
        schema.migrate(migration, application_role=environment.application_role)
        seed(migration)
        seed(
            migration, tenant="tenant-other", project="project-other", task="task-other"
        )
        seed(migration, project="project-other", task="task-sibling")
    yield uow.UnitOfWork(environment.additional_app_connection)


def claim(tx, entity_id="claim-1", revision=1, text="  captured value\n", *, level=0):
    tx.connection.execute(
        "INSERT INTO vnext.claim_revision(tenant_id,project_id,task_id,entity_id,revision,kind,assertion_role,text,producer_kind,producer_ref,access_level) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            *tx.owner,
            entity_id,
            revision,
            "observation-summary",
            "candidate_fact",
            text,
            "agent",
            "agent-fixture",
            level,
        ),
    )


@contextmanager
def capture_case(
    environment,
    tmp_path,
    audit_directory,
    tokens,
    *,
    completeness="complete",
    provenance="capture",
):
    from types import SimpleNamespace
    from wuji_core.http import create_app
    from wuji_core.http.auth import TokenVerifier
    from support.http_capture import RecordedTestClient

    with prepared(environment) as uow:
        store = module("evidence.artifacts").ArtifactStore(uow, tmp_path / "objects")
        service = module("evidence.observations").EvidenceService(uow, store)
        router = module("http.evidence").create_evidence_router(service)
        verifier = TokenVerifier(
            public_key_pem=tokens.public_key_pem,
            issuer=tokens.issuer,
            audience=tokens.audience,
        )
        client = RecordedTestClient(
            create_app(token_verifier=verifier, routers=[router]),
            audit_path=audit_directory / "http-exchanges.jsonl",
        )
        data = [
            b'  {"version":17,"message":"system healthy"}\n',
            b'{"fixture_prerequisite":true,"exit_code":0}\n',
        ]
        refs = []
        for ordinal, body in enumerate(data):
            (audit_directory / f"capture-input-{ordinal}.bin").write_bytes(body)
            ref = store.stage(
                access(),
                "task-fixture",
                "attempt-fixture",
                body,
                "application/json",
                completeness=completeness,
                conditions=(
                    ["fixture bytes; remainder unavailable"]
                    if completeness == "partial"
                    else ["fixture bytes"]
                ),
                provenance=provenance,
            )
            store.seal(access(), "task-fixture", ref)
            refs.append(ref.model_dump(mode="json"))
        envelope = {
            "schema_version": "wuji.capture.v2",
            "capture_id": "capture-fixture",
            "identity": {
                "tenant_id": "tenant-fixture",
                "project_id": "project-fixture",
                "task_id": "task-fixture",
                "work_item_id": "work-fixture",
                "agent_run_id": "run-fixture",
                "receiver_id": "receiver-fixture",
                "execution_epoch": "1",
                "run_epoch": "1",
                "runtime_attempt": "1",
            },
            "tool_call_id": "tool-fixture",
            "tool_attempt_id": "attempt-fixture",
            "artifact_refs": refs,
            "capture_layer": "fixture_file_bytes",
            "observed_at": "2026-09-13T00:00:00Z",
            "received_at": "2026-09-13T00:00:01Z",
            "evidence_origin": "fixture_capture",
            "conditions": (
                ["fixture bytes; remainder unavailable"]
                if completeness == "partial"
                else ["fixture bytes"]
            ),
            "completeness": completeness,
        }
        yield SimpleNamespace(
            uow=uow,
            store=store,
            service=service,
            client=client,
            envelope=envelope,
            data=data,
            refs=refs,
            headers={
                "Authorization": "Bearer " + tokens.collector,
                "Idempotency-Key": "capture-fixture",
            },
        )
        client.close()
