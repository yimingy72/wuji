"""Public evidence reads use current ACLs and never expose capture writes."""

from fastapi.testclient import TestClient

from support.p03 import capture_case
from wuji_core.http import create_app
from wuji_core.http.auth import TokenVerifier
from wuji_core.http.evidence import create_artifact_router


def test_public_artifact_router_reads_sealed_bytes_but_has_no_capture_producer(
    db_environment, tmp_path, audit_directory, test_tokens,
):
    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        captured = case.client.post(
            "/internal/v2/evidence", json=case.envelope, headers=case.headers,
        )
        assert captured.status_code == 202
        verifier = TokenVerifier(
            public_key_pem=test_tokens.public_key_pem,
            issuer=test_tokens.issuer, audience=test_tokens.audience,
        )
        ref = case.refs[0]
        path = f'/api/v2/artifacts/{ref["id"]}/content?version=1'
        headers = {"Authorization": "Bearer " + test_tokens.reader}
        app = create_app(token_verifier=verifier, routers=[create_artifact_router(case.store)])
        with TestClient(app) as client:
            response = client.get(path, headers=headers)
            assert response.status_code == 200
            assert response.content == case.data[0]
            assert response.headers["content-disposition"] == "attachment"
            assert response.headers["content-security-policy"] == "default-src 'none'"
            assert client.get(path).status_code == 401
            assert client.post(
                "/internal/v2/evidence", json=case.envelope, headers=case.headers,
            ).status_code == 404
        bounded = create_app(
            token_verifier=verifier,
            routers=[create_artifact_router(case.store, max_content_bytes=1)],
        )
        with TestClient(bounded) as client:
            assert client.get(path, headers=headers).status_code == 404


def test_public_material_preview_is_exact_and_rechecks_current_permissions(
    db_environment, tmp_path, audit_directory, test_tokens,
):
    from hashlib import sha256
    from support.p03 import access
    from test_model_material_v2 import exchange
    from wuji_core.evidence.material import ArtifactMaterialService
    from wuji_core.http.material import create_material_router

    with capture_case(db_environment, tmp_path, audit_directory, test_tokens) as case:
        raw = exchange("公开证据正文 fixture-only".encode())
        ref = case.store.stage(
            access(), "task-fixture", "attempt-fixture", raw,
            "application/vnd.wuji.http-exchange+json",
            completeness="complete", conditions=case.envelope["conditions"],
        )
        case.store.seal(access(), "task-fixture", ref)
        envelope = {**case.envelope, "artifact_refs": [ref.model_dump(mode="json")]}
        captured = case.client.post("/internal/v2/evidence", json=envelope, headers=case.headers)
        assert captured.status_code == 202, captured.text
        verifier = TokenVerifier(public_key_pem=test_tokens.public_key_pem,
                                 issuer=test_tokens.issuer, audience=test_tokens.audience)
        app = create_app(token_verifier=verifier, routers=[
            create_material_router(ArtifactMaterialService(case.store)),
        ])
        path = f"/api/v2/tasks/task-fixture/artifacts/{ref.id}/material?version=1"
        headers = {"Authorization": "Bearer " + test_tokens.reader}
        with TestClient(app) as client:
            response = client.get(path, headers=headers)
            assert response.status_code == 200, response.text
            packet = response.json()
            assert packet["status"] == "delivered"
            assert packet["source"]["artifact_sha256"] == sha256(raw).hexdigest()
            assert "公开证据正文" in packet["representation"]["text"]
            assert client.get(path.replace("task-fixture", "task-other"), headers=headers).status_code == 404
            with db_environment.migration_connection() as connection:
                connection.execute("UPDATE vnext.task_access SET can_read=false WHERE subject='reader-fixture'")
            assert client.get(path, headers=headers).status_code == 404
