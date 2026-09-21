from support.p13 import BASE, headers, projection_case, revise_claim, supported_claim


def _exploration(case, **params):
    return case.client.get(
        BASE + "/exploration",
        params={"mode": "live", "node_limit": 300, **params},
        headers=headers(case),
    )


def test_existing_task_projects_readable_problem_claim_and_fixed_snapshot(
    db_environment, tmp_path, audit_directory
):
    with projection_case(db_environment, tmp_path, audit_directory) as case:
        claim = supported_claim(case)
        accepted = case.knowledge.client.post(
            BASE + "/intents/proposals",
            json={
                "client_ref": "problem-view",
                "question": "当前材料是否支持已捕获的版本结论？",
                "basis_refs": [claim.ref],
                "expected_output": "给出有依据的结论和限制",
            },
            headers=headers(case),
        )
        assert accepted.status_code == 202, accepted.text

        first_response = _exploration(case)
        assert first_response.status_code == 200, first_response.text
        first = first_response.json()
        assert first["schema_version"] == "wuji.exploration-view.v1"
        assert first["problems"][0]["question"] == "当前材料是否支持已捕获的版本结论？"
        assert first["problems"][0]["public_rationale"] is None
        assert first["problems"][0]["basis_refs"] == [claim.ref]
        assert "public_rationale" in first["missing_fields"]
        assert any(item["text"] == claim.body["text"] for item in first["insights"])

        revise_claim(case, claim, text="A later claim revision")
        current = _exploration(case).json()
        historical = case.client.get(
            BASE + "/exploration",
            params={
                "mode": "history",
                "snapshot_id": first["snapshot_id"],
                "node_limit": 300,
            },
            headers=headers(case),
        )
        assert historical.status_code == 200, historical.text
        assert historical.json()["snapshot_id"] == first["snapshot_id"]
        assert not any(item["text"] == "A later claim revision" for item in historical.json()["insights"])
        assert any(item["text"] == "A later claim revision" for item in current["insights"])
