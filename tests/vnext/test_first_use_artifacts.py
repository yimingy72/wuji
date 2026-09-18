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
