"""Bounded provider usage consumption for model responses.

Usage is response data, not a billing decision.  The provider may put the
same logical usage record on the terminal content chunk or on a separate
usage-only chunk.  This module validates the stable token counters and keeps
the source position so the production ledger can retain an auditable,
redacted record without treating a missing value as zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class UsageSchemaError(ValueError):
    """The provider supplied a malformed usage object."""


_COUNTERS = ("prompt_tokens", "completion_tokens", "total_tokens")


def parse_usage(value: Any) -> dict[str, int] | None:
    """Validate and retain only the stable, non-sensitive usage counters.

    Provider-specific detail fields (for example cache or reasoning
    breakdowns) are deliberately not copied into the Wuji ledger until a
    published contract names them.  A missing/null usage value remains
    ``None`` and is later recorded as ``unknown``.
    """

    if value is None:
        return None
    if not isinstance(value, dict):
        raise UsageSchemaError("usage must be an object or null")
    result: dict[str, int] = {}
    for name in _COUNTERS:
        counter = value.get(name)
        if isinstance(counter, bool) or not isinstance(counter, int) or counter < 0:
            raise UsageSchemaError(f"usage.{name} must be a non-negative integer")
        result[name] = counter
    return result


@dataclass
class UsageAccumulator:
    """Consume usage from either accepted SSE position exactly once."""

    usage: dict[str, int] | None = None
    locations: list[str] = field(default_factory=list)

    def observe(self, chunk: dict[str, Any]) -> None:
        if "usage" not in chunk or chunk["usage"] is None:
            return
        parsed = parse_usage(chunk["usage"])
        if parsed is None:  # defensive; the branch above already excludes it
            return
        choices = chunk.get("choices")
        location = (
            "standalone_usage_chunk"
            if isinstance(choices, list) and not choices
            else "terminal_content_chunk"
        )
        if self.usage is not None and self.usage != parsed:
            raise UsageSchemaError("conflicting non-null usage chunks")
        self.usage = parsed
        if location not in self.locations:
            self.locations.append(location)

    @property
    def source(self) -> str | None:
        if not self.locations:
            return None
        return "+".join(self.locations)

    def snapshot(self) -> tuple[dict[str, int] | None, str | None]:
        return self.usage, self.source


def usage_from_completion(value: dict[str, Any]) -> tuple[dict[str, int], str]:
    """Consume usage from a non-streaming completion response."""

    parsed = parse_usage(value.get("usage"))
    if parsed is None:
        raise UsageSchemaError("completion response has unknown usage")
    return parsed, "completion_response"


__all__ = [
    "UsageAccumulator",
    "UsageSchemaError",
    "parse_usage",
    "usage_from_completion",
]
