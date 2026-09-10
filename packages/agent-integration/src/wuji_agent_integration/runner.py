"""Probe orchestration kept outside the production API."""

from __future__ import annotations

import json
import multiprocessing
import os
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, message_to_dict, messages_from_dict
from langchain_core.utils.function_calling import convert_to_openai_tool

from .config import Protocol, fixed_probe_configs
from .harness import assert_restricted_tool_surface, build_restricted_harness
from .ipc_model import DelayedProviderSession, IpcChatModel, ProviderFailure, ProviderSession
from .isolation import scrub_harness_environment, secret_environment_is_clear
from .ledger import CallLedger
from .tools import PROBE_TOOLS, wuji_synthetic_check


def _message_summary(message: AIMessage) -> dict[str, Any]:
    metadata = message.response_metadata or {}
    usage = message.usage_metadata or {}
    return {
        "actual_model": metadata.get("model_name", metadata.get("model", "unknown")),
        "finish_reason": metadata.get("finish_reason", metadata.get("stop_reason", "unknown")),
        "usage": {
            "input_tokens": usage.get("input_tokens", "unknown"),
            "output_tokens": usage.get("output_tokens", "unknown"),
            "total_tokens": usage.get("total_tokens", "unknown"),
        },
        "tool_call_ids": [call.get("id", "unknown") for call in message.tool_calls],
    }


def run_openai_harness(session: ProviderSession) -> dict[str, Any]:
    model = IpcChatModel(session)
    agent = build_restricted_harness(model)
    tool_names = assert_restricted_tool_surface(agent)
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Perform the approved synthetic check. Use the one available tool, then report completion."
                )
            ]
        }
    )
    messages = result["messages"]
    ai_messages = [message for message in messages if isinstance(message, AIMessage)]
    tool_messages = [message for message in messages if isinstance(message, ToolMessage)]
    if len(ai_messages) != 2 or len(tool_messages) != 1:
        raise RuntimeError("OpenAI harness did not complete exactly one two-request tool round trip")
    call_ids = [call.get("id") for call in ai_messages[0].tool_calls]
    if call_ids != [tool_messages[0].tool_call_id]:
        raise RuntimeError("OpenAI harness tool-call ID did not match its tool result")
    return {
        "adapter": "deepagents",
        "tool_names": list(tool_names),
        "tool_call_id": call_ids[0],
        "calls": [_message_summary(message) for message in ai_messages],
        "final_text": str(ai_messages[-1].content),
    }


def run_anthropic_native(session: ProviderSession) -> dict[str, Any]:
    tools = [convert_to_openai_tool(tool) for tool in PROBE_TOOLS]
    first_payload = session.invoke(
        [message_to_dict(HumanMessage(content="Call wuji_synthetic_check once for the approved connection check."))],
        tools,
    )
    first = messages_from_dict([first_payload["message"]])[0]
    if not isinstance(first, AIMessage) or len(first.tool_calls) != 1:
        raise RuntimeError("Anthropic native client did not request exactly one synthetic tool")
    call = first.tool_calls[0]
    if call.get("name") != "wuji_synthetic_check" or not call.get("id"):
        raise RuntimeError("Anthropic native client returned an invalid tool call")
    tool_result = wuji_synthetic_check.invoke(call.get("args") or {})
    second_payload = session.invoke(
        [
            message_to_dict(HumanMessage(content="Call wuji_synthetic_check once for the approved connection check.")),
            message_to_dict(first),
            message_to_dict(ToolMessage(content=tool_result, tool_call_id=call["id"])),
        ],
        tools,
    )
    second = messages_from_dict([second_payload["message"]])[0]
    if not isinstance(second, AIMessage) or second.tool_calls:
        raise RuntimeError("Anthropic native client did not complete the tool round trip")
    return {
        "adapter": "langchain-anthropic",
        "tool_names": ["wuji_synthetic_check"],
        "tool_call_id": call["id"],
        "calls": [_message_summary(first), _message_summary(second)],
        "final_text": str(second.content),
    }


def run_probe(
    *,
    credential_path: str,
    ledger_path: str,
    report_path: str,
    run_id: str | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Run the single approved two-protocol probe and write a redacted report."""

    scrub_harness_environment()
    if not secret_environment_is_clear():
        raise RuntimeError("harness environment still contains provider credentials")
    run_id = run_id or str(uuid4())
    deadline_epoch = time.time() + timeout_seconds
    openai_config, anthropic_config = fixed_probe_configs(timeout_seconds)
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "started",
        "run_id": run_id,
        "purpose": "organization_model_configuration_check",
        "requested_model": "qwen-flash",
        "limits": {"shared_attempts": 4, "attempts_per_protocol": 2, "sdk_retries": 0, "max_output_tokens": 256},
        "environment": {"provider_secrets_present_in_harness": False, "external_tracing_enabled": False},
        "openai": {"status": "skipped"},
        "anthropic": {"status": "skipped"},
        "cleanup": {},
    }
    openai_session = ProviderSession(
        openai_config,
        credential_path=credential_path,
        ledger_path=ledger_path,
        run_id=run_id,
        deadline_epoch=deadline_epoch,
    )
    anthropic_session: ProviderSession | None = None
    pending_error: BaseException | None = None
    try:
        report[Protocol.OPENAI.value] = {"status": "running"}
        with openai_session as session:
            report[Protocol.OPENAI.value] = {"status": "completed", **run_openai_harness(session)}
        report["cleanup"]["openai_provider_process_cleaned"] = not openai_session.is_alive
        anthropic_session = ProviderSession(
            anthropic_config,
            credential_path=credential_path,
            ledger_path=ledger_path,
            run_id=run_id,
            deadline_epoch=deadline_epoch,
        )
        report[Protocol.ANTHROPIC.value] = {"status": "running"}
        with anthropic_session as session:
            report[Protocol.ANTHROPIC.value] = {"status": "completed", **run_anthropic_native(session)}
        report["cleanup"]["anthropic_provider_process_cleaned"] = not anthropic_session.is_alive
        report["status"] = "completed"
    except BaseException as exc:
        pending_error = exc
        report["status"] = "failed"
        report["error"] = {
            "stage": getattr(exc, "stage", "probe"),
            "code": getattr(exc, "code", type(exc).__name__),
        }
        for protocol in (Protocol.OPENAI.value, Protocol.ANTHROPIC.value):
            if report[protocol]["status"] == "running":
                report[protocol] = {"status": "failed", "error": dict(report["error"])}
    finally:
        openai_session.close()
        report["cleanup"]["openai_provider_process_cleaned"] = not openai_session.is_alive
        if anthropic_session is not None:
            anthropic_session.close()
            report["cleanup"]["anthropic_provider_process_cleaned"] = not anthropic_session.is_alive
        else:
            report["cleanup"]["anthropic_provider_process_cleaned"] = True
        try:
            report["attempts"] = CallLedger(ledger_path).snapshot_for_run(run_id)
        except BaseException as exc:
            report["attempts"] = "unavailable"
            report["ledger_error"] = {"code": type(exc).__name__}
        report["skipped"] = [
            protocol for protocol in (Protocol.OPENAI.value, Protocol.ANTHROPIC.value) if report[protocol]["status"] == "skipped"
        ]
        report["limits_not_validated"] = [
            "production process isolation",
            "Runtime stop confirmation",
            "long-context summarization",
            "persistent recovery",
            "multi-agent execution",
            "complete streaming protocol compatibility",
        ]
        _write_report(report_path, report)
    if pending_error is not None:
        raise pending_error
    return report


def run_cancellation_fixture(*, delay_seconds: float = 5.0, cancel_after_seconds: float = 0.05) -> dict[str, Any]:
    """Cancel ProviderSession._receive and prove its delayed child is gone."""

    scrub_harness_environment()
    cancel_event = threading.Event()
    session = DelayedProviderSession(
        delay_seconds=delay_seconds,
        deadline_epoch=time.time() + max(delay_seconds + 2.0, 3.0),
        cancel_event=cancel_event,
    )
    started = time.monotonic()
    result: dict[str, Any] = {}

    def wait_for_provider() -> None:
        try:
            session.invoke([], [])
            result["wait_result"] = "unexpected_response"
        except ProviderFailure as exc:
            result["wait_result"] = exc.code

    with session:
        provider_pid = session.process_id
        waiter = threading.Thread(target=wait_for_provider, name="wuji-provider-wait-fixture")
        waiter.start()
        time.sleep(cancel_after_seconds)
        cancel_event.set()
        waiter.join(timeout=1.0)
        wait_ended = not waiter.is_alive()
    pid_still_active = any(child.pid == provider_pid for child in multiprocessing.active_children())
    return {
        "cancelled": result.get("wait_result") == "Cancelled",
        "adapter_wait_ended": wait_ended,
        "provider_process_cleaned": not session.is_alive and not pid_still_active,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }


def _write_report(path: str, report: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, target)
