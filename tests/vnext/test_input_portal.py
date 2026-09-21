from support.http_capture import RecordedTestClient
from support.identity_provider import TestIdentityProvider as IdentityProvider
from wuji_core.contracts.generated import TaskInputListV1
from wuji_core.http import create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.inputs import create_input_router


def test_public_input_portal_lists_and_answers_only_the_fixed_request(audit_directory):
    provider = IdentityProvider(audit_path=audit_directory / "identity.jsonl")
    tokens = provider.tokens()
    token = provider.issue(
        subject="operator", tenant_id="tenant", roles=["operator"]
    )

    class Inputs:
        def list_pending(self, access, task_id):
            assert access.principal.subject == "operator" and task_id == "task-1"
            return TaskInputListV1.model_validate({
                "schema_version": "wuji.task-inputs.v1", "task_id": task_id,
                "items": [{"input_request_id": "input-1", "work_item_id": "work-1",
                    "kind": "question", "status": "pending", "prompt": "Which version?",
                    "manifest_ref": "session-checkpoint:1"}],
            })

        def answer_question(self, access, input_request_id, *, text, idempotency_key):
            assert access.principal.subject == "operator"
            assert (input_request_id, text, idempotency_key) == (
                "input-1", "Version 2", "answer-once",
            )
            return "delivery-1"

    app = create_app(
        token_verifier=TokenVerifier(
            public_key_pem=tokens.public_key_pem,
            issuer=tokens.issuer,
            audience=tokens.audience,
        ),
        routers=[create_input_router(Inputs())],
    )
    client = RecordedTestClient(app, audit_path=audit_directory / "http.jsonl")
    try:
        headers = {"Authorization": "Bearer " + token}
        listed = client.get("/api/v2/tasks/task-1/inputs", headers=headers)
        answered = client.post(
            "/api/v2/inputs/input-1/answers",
            headers={**headers, "Idempotency-Key": "answer-once"},
            json={"schema_version": "wuji.api.v2", "text": "Version 2"},
        )
    finally:
        client.close()
    assert listed.status_code == 200 and listed.json()["items"][0]["prompt"] == "Which version?"
    assert answered.status_code == 200 and answered.json() == {
        "schema_version": "wuji.input-answer.v1",
        "input_request_id": "input-1", "delivery_id": "delivery-1",
        "status": "resolved",
    }
