"""Provider child process: the only code path that reads an upstream key."""

from __future__ import annotations

import time
from multiprocessing.connection import Connection
from typing import Any

from pydantic import SecretStr

from .config import ModelConfig, Protocol
from .credentials import load_api_key
from .ledger import CallLedger


def create_native_model(config: ModelConfig, api_key: SecretStr) -> Any:
    """Create the approved native LangChain client with SDK retries disabled."""

    if config.protocol is Protocol.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model_id,
            base_url=config.base_url,
            api_key=api_key,
            timeout=config.timeout_seconds,
            max_completion_tokens=config.max_output_tokens,
            max_retries=0,
            use_responses_api=False,
            streaming=False,
        )
    if config.protocol is Protocol.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=config.model_id,
            base_url=config.base_url,
            api_key=api_key,
            timeout=config.timeout_seconds,
            max_tokens_to_sample=config.max_output_tokens,
            max_retries=0,
            streaming=False,
        )
    raise ValueError("unsupported protocol")


def _usage(message: Any) -> dict[str, int | str]:
    usage = getattr(message, "usage_metadata", None) or {}
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    if not isinstance(usage, dict):
        usage = {}
    return {
        "input_tokens": usage.get("input_tokens", "unknown"),
        "output_tokens": usage.get("output_tokens", "unknown"),
        "total_tokens": usage.get("total_tokens", "unknown"),
    }


def summarize_message(message: Any) -> dict[str, Any]:
    metadata = getattr(message, "response_metadata", None) or {}
    tool_calls = getattr(message, "tool_calls", None) or []
    return {
        "actual_model": metadata.get("model_name", metadata.get("model", "unknown")),
        "finish_reason": metadata.get("finish_reason", metadata.get("stop_reason", "unknown")),
        "usage": _usage(message),
        "tool_call_ids": [item.get("id", "unknown") for item in tool_calls],
    }


def provider_process_main(
    connection: Connection,
    credential_path: str,
    ledger_path: str,
    run_id: str,
    config_payload: dict[str, Any],
) -> None:
    """Serve serialized model calls until stopped; never return exception text."""

    try:
        from langchain_core.messages import message_to_dict, messages_from_dict

        config = ModelConfig.from_payload(config_payload)
        api_key = SecretStr(load_api_key(credential_path))
        model = create_native_model(config, api_key)
        ledger = CallLedger(ledger_path)
        sequence = 0
        connection.send({"ok": True, "event": "ready"})
        while True:
            command = connection.recv()
            if command.get("op") == "stop":
                return
            if command.get("op") != "invoke":
                connection.send({"ok": False, "error": {"stage": "ipc", "code": "InvalidOperation"}})
                continue
            deadline = float(command["deadline_epoch"])
            if time.time() >= deadline:
                connection.send({"ok": False, "error": {"stage": "deadline", "code": "DeadlineExceeded"}})
                continue
            sequence += 1
            attempt_id = ledger.reserve(
                run_id=run_id,
                protocol=config.protocol.value,
                requested_model=config.model_id,
                sequence=sequence,
            )
            try:
                messages = messages_from_dict(command["messages"])
                bound_model = model.bind_tools(command["tools"])
                result = bound_model.invoke(messages)
                summary = summarize_message(result)
                ledger.complete(attempt_id, summary)
                connection.send(
                    {
                        "ok": True,
                        "message": message_to_dict(result),
                        "attempt_id": attempt_id,
                        "summary": summary,
                    }
                )
            except BaseException as exc:
                code = type(exc).__name__
                ledger.mark_unknown(attempt_id, code)
                connection.send({"ok": False, "error": {"stage": "upstream", "code": code}})
    except BaseException as exc:
        try:
            connection.send({"ok": False, "error": {"stage": "startup", "code": type(exc).__name__}})
        except BaseException:
            pass
    finally:
        connection.close()
