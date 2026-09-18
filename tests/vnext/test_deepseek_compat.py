"""A6 DeepSeek request and SSE usage contract checks.

The ModelGate integration assertion lives in ``test_maf_runtime``.  These
small checks cover the two provider usage positions and the fail-closed
provider mapping without contacting a real model.
"""

from __future__ import annotations

import pytest

from wuji_core.admission.models import _SSEObserver
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError


def _chunk(*, choices, usage=None) -> bytes:
    body = {
        "id": "fixture",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "deepseek-flash",
        "choices": choices,
    }
    if usage is not None:
        body["usage"] = usage
    return b"data: " + canonical_json_bytes(body) + b"\n\n"


def test_sse_usage_from_terminal_content_chunk_is_consumed():
    observer = _SSEObserver(4096)
    observer.feed(
        _chunk(
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        )
        + b"data: [DONE]\n\n"
    )

    assert observer.usage.snapshot() == (
        {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        "terminal_content_chunk",
    )


def test_sse_usage_only_chunk_is_consumed_for_compatibility():
    observer = _SSEObserver(4096)
    observer.feed(
        _chunk(choices=[], usage={"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5})
        + b"data: [DONE]\n\n"
    )

    assert observer.usage.snapshot() == (
        {"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
        "standalone_usage_chunk",
    )


def test_sse_conflicting_usage_is_not_silently_merged():
    observer = _SSEObserver(4096)
    observer.feed(
        _chunk(
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        )
    )
    with pytest.raises(DomainError) as error:
        observer.feed(
            _chunk(
                choices=[],
                usage={"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            )
        )
    assert error.value.code == "INVALID_SCHEMA"
