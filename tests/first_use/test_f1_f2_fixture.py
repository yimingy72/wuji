from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .f1_f2_fixture import F1_MESSAGE, F2_MESSAGE, FixtureServer


def _get(url: str) -> tuple[int, dict]:
    with urlopen(url, timeout=3) as response:
        return response.status, json.loads(response.read())


def _post(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=3) as response:
        return response.status, json.loads(response.read())


def test_f1_records_marker_and_material_for_a_second_model_request():
    with FixtureServer() as fixture:
        status, entry = _get(fixture.base_url + "/f1/entry")
        assert status == 200
        assert entry["marker"].startswith("f1-")
        assert F1_MESSAGE in entry["message"]

        status, source = _get(fixture.base_url + entry["source_path"])
        assert status == 200
        material = json.dumps(source, ensure_ascii=False, sort_keys=True)
        assert entry["marker"] in material
        assert "4.2.0" in material

        first_prompt = "请开始读取批准的 F1 入口，不要预置 marker。"
        second_prompt = f"marker={entry['marker']} source={material}"
        assert entry["marker"] not in first_prompt
        assert _post(
            fixture.base_url + "/model/requests", {"role": "first", "content": first_prompt}
        )[0] == 201
        assert _post(
            fixture.base_url + "/model/requests", {"role": "second", "content": second_prompt}
        )[0] == 201

        exchanges = fixture.exchanges
        model = [item for item in exchanges if item["path"] == "/model/requests"]
        assert len(model) == 2
        assert entry["marker"] not in model[0]["request_body"]
        assert entry["marker"] in model[1]["request_body"]
        assert "4.2.0" in model[1]["request_body"]
        assert all("request_http" in item and "response_http" in item for item in exchanges)


def test_f2_variants_publish_different_next_paths_and_reject_the_other_path():
    with FixtureServer() as fixture:
        status, variant_a = _get(fixture.base_url + "/f2/a/entry")
        assert status == 200
        assert variant_a["message"] == F2_MESSAGE
        assert variant_a["guide_path"] == "/f2/a/guide-a"
        assert _get(fixture.base_url + variant_a["guide_path"])[0] == 200
        try:
            _get(fixture.base_url + "/f2/a/guide-b")
        except Exception as exc:  # urllib raises HTTPError for the intentional 404.
            assert getattr(exc, "code", None) == 404
        else:
            raise AssertionError("the unapproved F2 A path unexpectedly succeeded")

        status, variant_b = _get(fixture.base_url + "/f2/b/entry")
        assert status == 200
        assert variant_b["guide_path"] == "/f2/b/guide-b"
        document = _get(fixture.base_url + variant_b["guide_path"])[1]["document"]
        assert document["mode"] == "observe-b"
        assert document["version"] == "4.3.1"

        events = _get(fixture.base_url + "/events")[1]
        assert events["f2_success_count"] == 2
        assert any(
            item["path"] == "/f2/a/guide-b" and item["response_status"] == 404
            for item in events["exchanges"]
        )
