"""The complete P0 validation tool surface."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def wuji_synthetic_check() -> str:
    """Return the fixed, local P0 tool result. It performs no I/O."""

    return "WUJI_SYNTHETIC_RESULT"


PROBE_TOOLS = (wuji_synthetic_check,)
EXPECTED_TOOL_NAMES = ("wuji_synthetic_check",)
