"""Trusted LiteLLM Proxy hook for the frozen DeepSeek route.

This module is loaded by LiteLLM's public ``CustomLogger`` callback API.  It
is deliberately scoped to one published Wuji alias; no general provider
parameter rewriting or retry behavior lives here.
"""

from __future__ import annotations

from typing import Any

from litellm.integrations.custom_logger import CustomLogger


HOOK_VERSION = "wuji-deepseek-params-v1"
ROUTE_ALIAS = "wuji-deepseek-observe-v1"
MAX_OUTPUT_TOKENS = 4096


def _bounded_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if not 0 < value <= MAX_OUTPUT_TOKENS:
        raise ValueError(f"{field} must be between 1 and {MAX_OUTPUT_TOKENS}")
    return value


class DeepSeekParameterHook(CustomLogger):
    """Rewrite only the fixed DeepSeek route at the gateway boundary."""

    hook_version = HOOK_VERSION

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict[str, Any],
        call_type: str,
    ) -> dict[str, Any] | None:
        del user_api_key_dict, cache, call_type
        if data.get("model") != ROUTE_ALIAS:
            return data

        has_completion = "max_completion_tokens" in data
        has_provider_max = "max_tokens" in data
        if has_completion and has_provider_max:
            raise ValueError(
                "max_completion_tokens and max_tokens cannot both be set for the DeepSeek route"
            )

        if has_completion:
            data["max_tokens"] = _bounded_integer(
                data.pop("max_completion_tokens"), "max_completion_tokens"
            )
        elif has_provider_max:
            data["max_tokens"] = _bounded_integer(data["max_tokens"], "max_tokens")
        else:
            raise ValueError("DeepSeek route requires a bounded output token limit")

        if "thinking" in data and data["thinking"] != {"type": "disabled"}:
            raise ValueError("DeepSeek non-thinking route does not allow thinking overrides")
        if "reasoning_effort" in data:
            raise ValueError("DeepSeek non-thinking route does not allow reasoning_effort")
        data["thinking"] = {"type": "disabled"}
        return data


proxy_handler_instance = DeepSeekParameterHook()


__all__ = [
    "DeepSeekParameterHook",
    "HOOK_VERSION",
    "ROUTE_ALIAS",
    "proxy_handler_instance",
]
