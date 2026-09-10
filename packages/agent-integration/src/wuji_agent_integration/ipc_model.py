"""Thin BaseChatModel bridge; the Agent process never receives a provider key."""

from __future__ import annotations

import multiprocessing
import threading
import time
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, PrivateAttr

from .config import ModelConfig
from .provider import provider_process_main


class ProviderFailure(RuntimeError):
    def __init__(self, stage: str, code: str) -> None:
        super().__init__(f"provider failure at {stage}: {code}")
        self.stage = stage
        self.code = code


class ProviderSession:
    """Own one Provider child and guarantee it is reaped on every exit path."""

    def __init__(
        self,
        config: ModelConfig,
        *,
        credential_path: str,
        ledger_path: str,
        run_id: str,
        deadline_epoch: float,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.config = config
        self.credential_path = credential_path
        self.ledger_path = ledger_path
        self.run_id = run_id
        self.deadline_epoch = deadline_epoch
        self.cancel_event = cancel_event
        self._connection: Connection | None = None
        self._process: multiprocessing.Process | None = None

    @property
    def process_id(self) -> int | None:
        return self._process.pid if self._process else None

    @property
    def is_alive(self) -> bool:
        return bool(self._process and self._process.is_alive())

    def __enter__(self) -> ProviderSession:
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=True)
        process = context.Process(
            target=provider_process_main,
            args=(child, self.credential_path, self.ledger_path, self.run_id, self.config.to_payload()),
            name=f"wuji-provider-{self.config.protocol.value}",
        )
        process.start()
        child.close()
        self._connection = parent
        self._process = process
        try:
            ready = self._receive()
            if ready.get("event") != "ready":
                self._raise_failure(ready)
        except BaseException:
            self.close()
            raise
        return self

    def invoke(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self._connection is None:
            raise RuntimeError("provider session is not started")
        self._connection.send(
            {
                "op": "invoke",
                "messages": messages,
                "tools": tools,
                "deadline_epoch": self.deadline_epoch,
            }
        )
        response = self._receive()
        if not response.get("ok"):
            self._raise_failure(response)
        return response

    def _receive(self) -> dict[str, Any]:
        if self._connection is None:
            raise RuntimeError("provider session is not started")
        while True:
            if self.cancel_event is not None and self.cancel_event.is_set():
                raise ProviderFailure("cancel", "Cancelled")
            remaining = self.deadline_epoch - time.time()
            if remaining <= 0:
                raise ProviderFailure("deadline", "DeadlineExceeded")
            if self._connection.poll(min(remaining, 0.05)):
                break
        try:
            response = self._connection.recv()
        except EOFError as exc:
            raise ProviderFailure("ipc", "ProviderExited") from exc
        if not isinstance(response, dict):
            raise ProviderFailure("ipc", "InvalidResponse")
        return response

    @staticmethod
    def _raise_failure(response: dict[str, Any]) -> None:
        error = response.get("error") or {}
        raise ProviderFailure(str(error.get("stage", "unknown")), str(error.get("code", "ProviderFailure")))

    def close(self) -> None:
        process, connection = self._process, self._connection
        if connection is not None and process is not None and process.is_alive():
            try:
                connection.send({"op": "stop"})
            except (BrokenPipeError, EOFError, OSError):
                pass
        if process is not None:
            process.join(timeout=0.5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=1.0)
        if connection is not None:
            connection.close()
        self._process = None
        self._connection = None

    def __exit__(self, *_: object) -> None:
        self.close()


def delayed_provider_process_main(connection: Connection, delay_seconds: float) -> None:
    """Local-only child used to exercise ProviderSession cancellation."""

    try:
        connection.send({"ok": True, "event": "ready"})
        command = connection.recv()
        if command.get("op") == "invoke":
            time.sleep(delay_seconds)
            connection.send({"ok": True, "message": {}, "summary": {}})
    finally:
        connection.close()


class DelayedProviderSession(ProviderSession):
    """ProviderSession variant whose child deliberately delays its IPC reply."""

    def __init__(self, *, delay_seconds: float, deadline_epoch: float, cancel_event: threading.Event) -> None:
        from .config import OPENAI_BASE_URL, PROBE_MODEL_ID, Protocol

        super().__init__(
            ModelConfig(Protocol.OPENAI, OPENAI_BASE_URL, PROBE_MODEL_ID, 1.0, 1),
            credential_path="unused-by-local-fixture",
            ledger_path="unused-by-local-fixture",
            run_id="local-cancellation-fixture",
            deadline_epoch=deadline_epoch,
            cancel_event=cancel_event,
        )
        self.delay_seconds = delay_seconds

    def __enter__(self) -> DelayedProviderSession:
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=True)
        process = context.Process(
            target=delayed_provider_process_main,
            args=(child, self.delay_seconds),
            name="wuji-provider-delay-fixture",
        )
        process.start()
        child.close()
        self._connection = parent
        self._process = process
        try:
            ready = self._receive()
            if ready.get("event") != "ready":
                self._raise_failure(ready)
        except BaseException:
            self.close()
            raise
        return self


class IpcChatModel(BaseChatModel):
    """A native BaseChatModel facade over the private Provider process."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    model_name: str
    protocol: str
    _session: ProviderSession = PrivateAttr()

    def __init__(self, session: ProviderSession) -> None:
        super().__init__(model_name=session.config.model_id, protocol=session.config.protocol.value)
        self._session = session

    @property
    def _llm_type(self) -> str:
        return "wuji-ipc"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.model_name, "protocol": self.protocol}

    def _get_ls_params(self, **_: Any) -> dict[str, Any]:
        return {"ls_provider": "wuji-ipc", "ls_model_name": self.model_name, "ls_model_type": "chat"}

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | BaseTool | Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Any:
        formatted = [convert_to_openai_tool(tool) for tool in tools]
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return self.bind(tools=formatted, **kwargs)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager
        response = self._session.invoke(
            [message_to_dict(message) for message in messages],
            list(kwargs.get("tools", [])),
        )
        message = messages_from_dict([response["message"]])[0]
        return ChatResult(generations=[ChatGeneration(message=message)])
