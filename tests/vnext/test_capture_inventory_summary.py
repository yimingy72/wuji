"""Capture inventory keeps one bounded summary per HTTP exchange."""

import base64

from wuji_capture.control import CaptureItemStore
from wuji_capture.writer import DurableWriter


def test_http_exchange_has_a_bounded_inventory_summary_and_original_parts(tmp_path):
    writer = DurableWriter(
        tmp_path / "http", maximum_request_body_bytes=1024,
        maximum_response_body_bytes=1024, maximum_session_bytes=1024 * 1024,
        maximum_items=10,
    )
    empty = base64.b64encode(b"").decode()
    writer.handle({
        "op": "record", "exchange_id": "exchange-1", "stage": "request",
        "metadata": {"method": "GET", "url": "https://example.test/" + "a" * 3000},
        "body_base64": empty,
    })
    writer.handle({
        "op": "record", "exchange_id": "exchange-1", "stage": "response",
        "metadata": {"status_code": 200}, "body_base64": empty,
    })
    store = CaptureItemStore(
        tmp_path, maximum_items=10, maximum_session_bytes=1024 * 1024,
        maximum_chunk_bytes=1024,
    )
    store.refresh(sealed=False, pcap_stats=None)
    item = store.page(after=0, limit=10)["items"][0]

    assert item["kind"] == "http_exchange"
    assert item["metadata"] == {
        "exchange_id": "exchange-1", "method": "GET", "status_code": 200,
        "url": ("https://example.test/" + "a" * 3000)[:2048],
    }
    assert {part["part"] for part in item["parts"]} == {
        "request_metadata", "request_body", "response_metadata", "response_body",
    }
