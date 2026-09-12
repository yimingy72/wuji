from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from wuji_core.contracts import generated
from wuji_core.contracts.envelopes import (
    AgentPayload,
    CaptureEnvelope,
    ResultEnvelope,
    RunIdentity,
    WorkerAssignment,
)
from wuji_core.contracts.execution import SessionManifest, WorkState, can_transition_work
from wuji_core.contracts.knowledge import AssessmentCommand, ClaimProposal, FactAssessment
from wuji_core.contracts.views import (
    TopologySnapshot,
    ViewEventBatch,
    ViewReset,
)
from wuji_core.http.json_boundary import (
    InvalidJsonDocument,
    canonical_json_bytes,
    strict_json_loads,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIRECTORY = REPOSITORY_ROOT / "docs" / "vnext" / "examples"


def _example(name: str) -> object:
    return json.loads((EXAMPLE_DIRECTORY / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("claim_candidate.json", ClaimProposal),
        ("claim_hypothesis.json", ClaimProposal),
        ("assessment_supported.json", FactAssessment),
        ("agent_payload.json", AgentPayload),
        ("result_envelope.json", ResultEnvelope),
        ("capture_envelope.json", CaptureEnvelope),
        ("session_manifest.json", SessionManifest),
        ("worker_assignment.json", WorkerAssignment),
        ("topology_snapshot.json", TopologySnapshot),
        ("view_event_batch.json", ViewEventBatch),
        ("view_reset.json", ViewReset),
    ],
)
def test_approved_examples_validate(filename: str, model: type) -> None:
    model.model_validate(_example(filename))


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("reject_self_certified_claim.json", ClaimProposal),
        ("reject_model_only_support.json", FactAssessment),
        ("reject_global_sequence_leak.json", ViewEventBatch),
    ],
)
def test_negative_examples_are_rejected(filename: str, model: type) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(_example(filename))


def test_assessment_command_cannot_wrap_model_only_supported_assessment() -> None:
    with pytest.raises(ValidationError):
        AssessmentCommand.model_validate(
            {
                "schema_version": "wuji.api.v2",
                "expected_version": "1",
                "assessment": _example("reject_model_only_support.json"),
            }
        )


@pytest.mark.parametrize(
    "protected_field",
    [
        "collector_id",
        "evidence_state",
        "grounding_state",
        "applicability_state",
        "fact_assessment",
        "task_state",
        "run_epoch",
    ],
)
def test_candidate_cannot_supply_protected_authority(protected_field: str) -> None:
    payload = {
        "client_ref": "c1",
        "kind": "observation-summary",
        "assertion_role": "candidate_fact",
        "text": "  version 为 17\n原样保留  ",
        "basis_refs": [],
        "limitations": [],
        protected_field: "forged",
    }

    with pytest.raises(ValidationError):
        ClaimProposal.model_validate(payload)


def test_unstructured_candidate_text_preserves_whitespace() -> None:
    text = "  任意候选文本 {\"predicate\": false}\n第二行  "
    claim = ClaimProposal.model_validate(
        {
            "client_ref": "c1",
            "kind": "observation-summary",
            "assertion_role": "candidate_fact",
            "text": text,
            "structured_assertion": {"source_value": 17, "present": True},
            "basis_refs": [],
            "limitations": [],
        }
    )

    assert claim.text == text
    assert claim.structured_assertion == {"source_value": 17, "present": True}


def test_intent_can_reference_a_claim_from_the_same_payload() -> None:
    payload = AgentPayload.model_validate(
        {
            "schema_version": "wuji.agent-payload.v2",
            "claims": [
                {
                    "client_ref": "claim-local",
                    "kind": "hypothesis",
                    "assertion_role": "hypothesis",
                    "text": "需要进一步核对。",
                    "basis_refs": [],
                    "limitations": [],
                }
            ],
            "intent_proposals": [
                {
                    "client_ref": "intent-local",
                    "question": "核对版本来源",
                    "basis_refs": [{"client_ref": "claim-local"}],
                    "expected_output": "固定版本记录",
                }
            ],
            "limitations": [],
        }
    )

    assert payload.intent_proposals[0].basis_refs[0].root.client_ref == "claim-local"


def test_proposal_local_reference_cannot_impersonate_a_canonical_reference() -> None:
    payload = _example("agent_payload.json")
    payload["intent_proposals"] = [
        {
            "client_ref": "i1",
            "question": "核对来源",
            "basis_refs": [
                {
                    "client_ref": "candidate-17",
                    "entity_type": "claim",
                    "id": "forged-id",
                    "revision": "1",
                }
            ],
            "expected_output": "来源",
        }
    ]

    with pytest.raises(ValidationError):
        AgentPayload.model_validate(payload)


@pytest.mark.parametrize("invalid_revision", [1, -1, "-1", "01", "1.0", " 1"])
def test_run_identity_revisions_are_canonical_decimal_strings(
    invalid_revision: object,
) -> None:
    identity = {
        "tenant_id": "tenant-fixture",
        "project_id": "project-fixture",
        "task_id": "task-fixture",
        "work_item_id": "work-fixture",
        "agent_run_id": "run-fixture",
        "execution_epoch": invalid_revision,
        "run_epoch": "1",
        "runtime_attempt": "1",
        "receiver_id": "receiver-fixture",
    }

    with pytest.raises(ValidationError):
        RunIdentity.model_validate(identity)


def test_result_envelope_rejects_trusted_fields_inside_agent_payload() -> None:
    envelope = _example("result_envelope.json")
    envelope["payload"]["identity"] = envelope["identity"]

    with pytest.raises(ValidationError):
        ResultEnvelope.model_validate(envelope)


def test_work_state_contains_no_superseded_value() -> None:
    assert "superseded" not in {state.value for state in WorkState}
    with pytest.raises(ValueError):
        WorkState("superseded")


def test_fact_is_not_a_canonical_knowledge_entity_type() -> None:
    with pytest.raises(ValidationError):
        generated.KnowledgeRef.model_validate(
            {"entity_type": "fact", "id": "legacy-fact", "revision": "1"}
        )


def test_contract_allows_every_published_work_transition() -> None:
    allowed = {
        ("ready", "leased"),
        ("leased", "running"),
        ("leased", "reconciling"),
        ("leased", "stopping"),
        ("running", "waiting_input"),
        ("running", "done"),
        ("running", "failed"),
        ("running", "stopping"),
        ("running", "reconciling"),
        ("ready", "blocked"),
        ("blocked", "ready"),
        ("ready", "cancelled"),
        ("blocked", "cancelled"),
        ("waiting_input", "cancelled"),
        ("suspended", "cancelled"),
        ("waiting_input", "ready"),
        ("suspended", "ready"),
        ("stopping", "suspended"),
        ("stopping", "cancelled"),
        ("stopping", "reconciling"),
        ("reconciling", "done"),
        ("reconciling", "failed"),
        ("reconciling", "suspended"),
        ("reconciling", "cancelled"),
        ("ready", "suspended"),
        ("blocked", "suspended"),
        ("waiting_input", "suspended"),
        ("suspended", "waiting_input"),
        ("suspended", "blocked"),
    }

    observed = {
        (source.value, target.value)
        for source in WorkState
        for target in WorkState
        if can_transition_work(source, target)
    }
    assert observed == allowed


@pytest.mark.parametrize("terminal", [WorkState.done, WorkState.failed, WorkState.cancelled])
def test_terminal_work_cannot_return_to_ready(terminal: WorkState) -> None:
    assert not can_transition_work(terminal, WorkState.ready)


def test_openapi_contains_every_machine_contract_enum_and_required_shape() -> None:
    machine_contract = json.loads(
        (REPOSITORY_ROOT / "docs" / "vnext" / "contracts.json").read_text(
            encoding="utf-8"
        )
    )
    openapi = yaml.safe_load(
        (REPOSITORY_ROOT / "packages" / "contracts" / "openapi-v2.yaml").read_text(
            encoding="utf-8"
        )
    )
    schemas = openapi["components"]["schemas"]
    enum_schema_names = {
        "claim_kind": "ClaimKind",
        "assertion_role": "AssertionRole",
        "producer_kind": "ProducerKind",
        "grounding_state": "GroundingState",
        "evidence_state": "EvidenceState",
        "applicability_state": "ApplicabilityState",
        "assessment_method": "AssessmentMethod",
        "work_kind": "WorkKind",
        "intent_acceptance": "IntentAcceptance",
        "work_desired": "WorkDesired",
        "work_state": "WorkState",
        "run_process": "RunProcessState",
        "run_result": "RunResultState",
        "task_desired": "TaskDesired",
        "task_observed": "TaskObserved",
        "close_trigger": "CloseTrigger",
        "result_outcome": "ResultOutcome",
        "goal_status": "GoalStatus",
        "dependency_condition": "DependencyCondition",
        "recovery_class": "RecoveryClass",
        "result_receipt_status": "ResultReceiptStatus",
        "component_receipt_status": "ComponentReceiptStatus",
        "evidence_receipt_status": "EvidenceReceiptStatus",
        "artifact_state": "ArtifactState",
        "evidence_origin": "EvidenceOrigin",
        "model_mode": "ModelMode",
        "node_entity_type": "NodeEntityType",
        "reason_decision": "ReasonDecision",
        "test_result": "TestResult",
        "suspension_cause": "SuspensionCause",
        "report_delivery": "ReportDeliveryState",
    }

    assert {
        key: schemas[schema_name]["enum"]
        for key, schema_name in enum_schema_names.items()
    } == machine_contract["enums"]
    assert {
        name: schemas[name]["required"]
        for name in machine_contract["wire_required_fields"]
    } == machine_contract["wire_required_fields"]


def test_openapi_publishes_the_complete_s13_route_set() -> None:
    openapi = yaml.safe_load(
        (REPOSITORY_ROOT / "packages" / "contracts" / "openapi-v2.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert set(openapi["paths"]) == {
        "/api/v2/tasks",
        "/api/v2/tasks/{task_id}/commands",
        "/api/v2/tasks/{task_id}/claims/proposals",
        "/api/v2/tasks/{task_id}/intents/proposals",
        "/api/v2/work-items/{work_item_id}/commands",
        "/api/v2/approvals/{approval_id}/decisions",
        "/api/v2/tasks/{task_id}/assessments",
        "/api/v2/tasks/{task_id}/topology",
        "/api/v2/views/{view_id}/events",
        "/api/v2/tasks/{task_id}/snapshots",
        "/api/v2/tasks/{task_id}/records/{record_type}/{record_id}",
        "/api/v2/tasks/{task_id}/layouts/{view_name}",
        "/api/v2/artifacts/{artifact_id}/content",
        "/api/v2/archives/{archive_id}",
        "/internal/v2/model/chat/completions",
        "/internal/v2/evidence",
        "/internal/v2/results",
        "/internal/v2/dispatch/claims",
        "/internal/v2/runs/{run_id}",
        "/internal/v2/runs/{run_id}/control",
    }


def test_view_query_is_typed_without_internal_watermarks() -> None:
    query = generated.ViewQuery.model_validate(
        {
            "mode": "live",
            "snapshot_id": None,
            "cursor": None,
            "node_limit": 300,
            "edge_limit": 600,
        }
    )
    assert query.node_limit == 300

    with pytest.raises(ValidationError):
        generated.ViewQuery.model_validate(
            {
                "mode": "live",
                "snapshot_id": None,
                "cursor": None,
                "node_limit": 300,
                "edge_limit": 600,
                "board_revision": "857",
            }
        )


def test_numeric_limits_remain_integers_while_revisions_are_strings() -> None:
    assignment = _example("worker_assignment.json")
    assignment["limits"]["max_work_items"] = "24"
    with pytest.raises(ValidationError):
        WorkerAssignment.model_validate(assignment)


def test_finite_integer_coordinates_are_valid_json_numbers() -> None:
    entry = generated.LayoutEntry.model_validate(
        {
            "anchor": {"entity_type": "claim", "id": "claim-1", "revision": "1"},
            "x": 1,
            "y": -2,
            "pinned": True,
        }
    )

    assert entry.x == 1.0
    assert entry.y == -2.0


def test_duplicate_json_keys_are_rejected_before_model_validation() -> None:
    with pytest.raises(InvalidJsonDocument, match="duplicate object key: authority"):
        strict_json_loads(b'{"authority":"agent","authority":"collector"}')


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonfinite_json_numbers_are_rejected(constant: bytes) -> None:
    with pytest.raises(InvalidJsonDocument, match="non-finite JSON number"):
        strict_json_loads(b'{"coordinate":' + constant + b"}")


def test_canonical_json_preserves_strings_and_array_order() -> None:
    source = b'{ "z": [" second ", "first"], "a": {"text": " x\\n"} }'

    assert canonical_json_bytes(source) == (
        b'{"a":{"text":" x\\n"},"z":[" second ","first"]}'
    )


def test_canonical_json_ignores_only_object_key_order_and_outer_spacing() -> None:
    left = b'{"message":" x ","items":[2,1]}'
    right = b'  { "items" : [2, 1], "message" : " x " }  '

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(b'{"message":"x","items":[2,1]}') != canonical_json_bytes(
        left
    )
    assert canonical_json_bytes(b'{"message":" x ","items":[1,2]}') != canonical_json_bytes(
        left
    )


def test_protected_asgi_route_requires_a_bearer_token(api_client) -> None:
    response = api_client.post("/api/v2/test/identity", json={"probe": "missing"})

    assert response.status_code == 401
    assert response.json() == {
        "code": "UNAUTHENTICATED",
        "message": "A valid bearer token is required.",
        "request_id": response.headers["x-request-id"],
        "retryable": False,
        "details": {},
    }


def test_protected_asgi_route_rejects_a_tampered_issuer_token(
    api_client, test_tokens
) -> None:
    response = api_client.post(
        "/api/v2/test/identity",
        json={"probe": "tampered"},
        headers={"Authorization": f"Bearer {test_tokens.tampered}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("token_name", ["wrong_issuer", "wrong_audience", "expired"])
def test_protected_asgi_route_rejects_invalid_registered_claims(
    api_client, test_tokens, token_name: str
) -> None:
    response = api_client.post(
        "/api/v2/test/identity",
        json={"probe": token_name},
        headers={"Authorization": f"Bearer {getattr(test_tokens, token_name)}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_issuer_signed_identity_reaches_the_real_asgi_route(
    api_client, test_tokens
) -> None:
    response = api_client.post(
        "/api/v2/test/identity",
        json={"probe": "signed"},
        headers={"Authorization": f"Bearer {test_tokens.agent}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "subject": "agent-fixture",
        "tenant_id": "tenant-fixture",
        "roles": ["agent"],
        "payload": {"probe": "signed"},
    }
    exchange = api_client.exchanges[-1]
    assert exchange.request.method == "POST"
    assert exchange.request.url == "http://testserver/api/v2/test/identity"
    assert exchange.request.headers["authorization"] == f"Bearer {test_tokens.agent}"
    assert exchange.request.body == b'{"probe":"signed"}'
    assert exchange.response.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        b'{"authority":"agent","authority":"collector"}',
        b'{"coordinate":NaN}',
    ],
)
def test_asgi_boundary_rejects_unsafe_json_before_route_dispatch(
    api_client, test_tokens, body: bytes
) -> None:
    response = api_client.post(
        "/api/v2/test/identity",
        content=body,
        headers={
            "Authorization": f"Bearer {test_tokens.agent}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA"
    assert response.json()["retryable"] is False


def test_asgi_model_validation_uses_the_versioned_error_envelope(
    api_client, test_tokens
) -> None:
    response = api_client.post(
        "/api/v2/test/claim",
        json={
            "client_ref": "claim-1",
            "kind": "SENSITIVE-INVALID-KIND",
            "assertion_role": "candidate_fact",
            "text": "SENSITIVE-CANDIDATE-CONTENT version 为 17",
            "basis_refs": [],
            "limitations": [],
        },
        headers={"Authorization": f"Bearer {test_tokens.agent}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SCHEMA"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert response.json()["retryable"] is False
    public_error = response.json()["details"]["errors"][0]
    assert public_error["type"] == "enum"
    assert set(public_error) == {"type", "loc", "msg"}
    assert "SENSITIVE-INVALID-KIND" not in response.text
    assert "SENSITIVE-CANDIDATE-CONTENT" not in response.text
    assert "detail" not in response.json()


def test_db_conn_is_real_postgres_in_an_isolated_nonowner_database(db_conn) -> None:
    row = db_conn.execute(
        """
        SELECT
            current_setting('server_version_num'),
            current_database(),
            current_user,
            owner.rolname,
            app.rolsuper,
            app.rolbypassrls,
            has_database_privilege(current_user, current_database(), 'CREATE')
        FROM pg_database AS database
        JOIN pg_roles AS owner ON owner.oid = database.datdba
        JOIN pg_roles AS app ON app.rolname = current_user
        WHERE database.datname = current_database()
        """
    ).fetchone()

    assert row is not None
    (
        version_number,
        database_name,
        current_user,
        owner_name,
        is_superuser,
        bypasses_rls,
        can_create_database_objects,
    ) = row
    assert version_number == "160002"
    assert database_name.startswith("wuji_p02_")
    assert current_user.startswith("wuji_app_")
    assert owner_name.startswith("wuji_migration_")
    assert owner_name != current_user
    assert is_superuser is False
    assert bypasses_rls is False
    assert can_create_database_objects is False
    assert db_conn.audit_path.is_file()
