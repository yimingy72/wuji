"""Native Chat Completions forwarding behind durable Run admission."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from starlette.concurrency import run_in_threadpool
from starlette.responses import Response, StreamingResponse

from wuji_core.contracts.execution import ChatCompletionRequest, ChatCompletionResponse
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, row, json_text
from wuji_core.admission.registry import TaskAdmissionConfig
from wuji_core.admission.common import audit, consume_attempt, current_run, digest


class AdmissionError(DomainError):
    def __init__(self, code, status, *, details=None):
        super().__init__(code, status)
        self.details = details or {}


@dataclass(frozen=True)
class ModelPermit:
    identity: RunIdentity
    model_attempt_id: str
    config: TaskAdmissionConfig
    request_body: bytes = field(repr=False)
    settlement_token: str = field(repr=False)
    replay: bool = False


class TaskGatewayKeyResolver(Protocol):
    def resolve(self, secret_ref: str) -> str: ...


class ToolCapabilityResolverPort(Protocol):
    def require_available(self, access, tools) -> None: ...


class ModelAdmission:
    def __init__(self, uow, *, registry, ledger):
        self.uow, self.registry, self.ledger = uow, registry, ledger

    def authorize(self, access, request, *, request_id, original_json=None):
        request = ChatCompletionRequest.model_validate(request)
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 256:
            raise DomainError("INVALID_SCHEMA", 422)
        source = strict_json_loads(original_json) if original_json is not None else request.model_dump(mode="python", exclude_unset=True)
        if ChatCompletionRequest.model_validate(source) != request:
            raise DomainError("INVALID_SCHEMA", 422)
        if "temperature" in source and not 0 <= source["temperature"] <= 2:
            raise DomainError("INVALID_SCHEMA", 422)
        binding = self.registry.binding(access)
        try:
            with self.uow.transaction(access, binding.identity.task_id, capability="model_request") as tx:
                config = self.registry.config(tx)
                run, work = current_run(tx, config)
                if source["model"] != config.model.client_model:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                allowed = set(config.allowed_tool_refs) & set(config.runtime.allowed_tool_refs) & set(tx.run_binding.allowed_tool_refs)
                definitions = {self.registry.tool(tx, ref).name: self.registry.tool(tx, ref) for ref in allowed}
                if len(definitions) != len(allowed):
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                for tool in source.get("tools") or []:
                    proposed = tool["function"]
                    registered = definitions.get(proposed["name"])
                    if not registered or digest(proposed["parameters"]) != digest(registered.input_schema):
                        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                old = row(tx.connection.execute("SELECT * FROM vnext.model_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND logical_request_id=%s", (*tx.owner, run["agent_run_id"], request_id)))
                request_digest = digest(source)
                if old:
                    if old["input_digest"] != request_digest:
                        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    if not old["response_available"] or old["response_state"] != "complete":
                        raise AdmissionError("OPERATION_UNKNOWN", 409, details={"model_attempt_id": old["model_attempt_id"], "receipt_url": "/internal/v2/model-attempts/" + old["model_attempt_id"]})
                    return ModelPermit(binding.identity, old["model_attempt_id"], config, old["request_json"].encode(), old["settlement_token"], True)
                busy = tx.connection.execute("SELECT 1 FROM vnext.model_call WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND inflight", (*tx.owner, run["agent_run_id"])).fetchone()
                if busy:
                    raise DomainError("LIMIT_BLOCKED", 429)
                consume_attempt(tx, model=True, maximum=config.runtime.limits.max_model_requests)
                attempt_id, token = str(uuid4()), str(uuid4())
                native = dict(source)
                native["model"] = config.model.upstream_model
                native_bytes = canonical_json_bytes(native)
                tx.connection.execute("INSERT INTO vnext.model_call(tenant_id,project_id,task_id,model_attempt_id,agent_run_id,subject,token_id,logical_request_id,input_digest,request_json,profile_json,settlement_token,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (*tx.owner, attempt_id, run["agent_run_id"], access.principal.subject, access.principal.token_id, request_id, request_digest, native_bytes.decode(), json_text(config.model_dump(mode="json")), token, tx.permissions["clearance"]))
                audit(tx, "model.admitted", {"model_attempt_id": attempt_id, "agent_run_id": run["agent_run_id"]})
                return ModelPermit(binding.identity, attempt_id, config, native_bytes, token)
        except DomainError as exc:
            self.ledger.rejected(access, binding.identity.task_id, "model_request", exc.code)
            raise

    def begin_send(self, access, permit):
        with self.uow.transaction(access, permit.identity.task_id, capability="model_request") as tx:
            current_run(tx, self.registry.config(tx))
            record = self.ledger._permit_row(tx, permit)
            if (
                permit.replay
                or record["send_state"] != "not_sent"
                or record["local_state"] != "inflight"
                or not record["inflight"]
            ):
                raise DomainError("OPERATION_UNKNOWN", 409)
            updated = tx.connection.execute(
                "UPDATE vnext.model_call SET send_state='sending' WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND model_attempt_id=%s AND send_state='not_sent' AND local_state='inflight' AND inflight RETURNING model_attempt_id",
                (*tx.owner, permit.model_attempt_id),
            ).fetchone()
            if not updated:
                raise DomainError("OPERATION_UNKNOWN", 409)
            audit(tx, "model.sending", {"model_attempt_id": permit.model_attempt_id})


class HttpxModelTransport:
    """The client is injected; no implicit retry, redirect or environment policy."""
    def __init__(self, client):
        self.client = client

    @asynccontextmanager
    async def open(self, *, url, headers, body, timeout):
        try:
            async with self.client.stream("POST", url, headers=headers, content=body, timeout=timeout, follow_redirects=False) as response:
                yield response
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503) from exc


class _SSEObserver:
    def __init__(self, maximum):
        self.buffer, self.maximum, self.done = bytearray(), maximum, False

    def feed(self, data):
        self.buffer.extend(data)
        if len(self.buffer) > self.maximum:
            raise DomainError("LIMIT_BLOCKED", 429)
        while True:
            candidates = [i for i in (self.buffer.find(b"\n\n"), self.buffer.find(b"\r\n\r\n")) if i >= 0]
            if not candidates:
                return
            end = min(candidates)
            length = 4 if self.buffer[end:end+4] == b"\r\n\r\n" else 2
            frame = bytes(self.buffer[:end])
            del self.buffer[:end+length]
            fields = [line[5:].lstrip(b" ") for line in frame.splitlines() if line.startswith(b"data:")]
            if not fields:
                continue
            payload = b"\n".join(fields)
            if self.done:
                raise DomainError("INVALID_SCHEMA", 422)
            if payload == b"[DONE]":
                self.done = True
            else:
                value = strict_json_loads(payload)
                if not isinstance(value, dict) or "error" in value or value.get("object") != "chat.completion.chunk":
                    raise DomainError("INVALID_SCHEMA", 422)


class _ModelStream:
    def __init__(self, gate, access, permit):
        self.gate, self.access, self.permit = gate, access, permit
        self.context = None
        self.response = None
        self.finished = False
        self.seen = 0
        self.closed = False
        self.started = asyncio.get_running_loop().time()

    async def open(self):
        runtime = self.permit.config.runtime
        try:
            await run_in_threadpool(self.gate.admission.begin_send, self.access, self.permit)
            task_resolver = getattr(self.gate.key_resolver, "resolve_for_task", None)
            if callable(task_resolver):
                key = await run_in_threadpool(
                    task_resolver, self.permit.config.model.task_key_ref,
                    tenant_id=self.permit.identity.tenant_id,
                    task_id=self.permit.identity.task_id,
                )
            else:
                key = await run_in_threadpool(self.gate.key_resolver.resolve, self.permit.config.model.task_key_ref)
            if not isinstance(key, str) or not key or "\r" in key or "\n" in key:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            self.context = self.gate.transport.open(url=self.permit.config.model.gateway_url, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "text/event-stream" if strict_json_loads(self.permit.request_body)["stream"] else "application/json", "X-Wuji-Model-Attempt-ID": self.permit.model_attempt_id}, body=self.permit.request_body, timeout=runtime.idle_timeout_seconds)
            self.response = await asyncio.wait_for(self.context.__aenter__(), timeout=runtime.total_timeout_seconds)
            status = self.response.status_code
            content_type = self.response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            reference = lambda name: (v if isinstance(v := self.response.headers.get(name), str) and 0 < len(v) <= 256 and "\n" not in v and "\r" not in v else None)
            await run_in_threadpool(self.gate.ledger.response_started, self.access, self.permit, status=status, content_type=content_type, usage_ref=reference("x-litellm-call-id"), spend_ref=reference("x-wuji-gateway-spend-ref"))
            expected = "text/event-stream" if strict_json_loads(self.permit.request_body)["stream"] else "application/json"
            if status != 200 or content_type != expected:
                raise DomainError("LIMIT_BLOCKED" if status == 429 else "CAPABILITY_UNAVAILABLE", 429 if status == 429 else 503)
        except BaseException:
            await self.close()
            raise

    async def chunks(self):
        runtime = self.permit.config.runtime
        iterator = self.response.aiter_bytes(chunk_size=runtime.chunk_bytes).__aiter__()
        while True:
            remaining = runtime.total_timeout_seconds - (asyncio.get_running_loop().time() - self.started)
            if remaining <= 0:
                raise TimeoutError("model request deadline")
            try:
                data = await asyncio.wait_for(anext(iterator), timeout=min(runtime.idle_timeout_seconds, remaining))
            except StopAsyncIteration:
                return
            if not data:
                continue
            if len(data) > runtime.chunk_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            self.seen += len(data)
            if not await run_in_threadpool(self.gate.ledger.retain, self.access, self.permit, data):
                raise DomainError("LIMIT_BLOCKED", 429)
            yield data

    async def close(self):
        if self.closed:
            return
        self.closed = True
        ended = True
        if self.context is not None:
            try:
                await asyncio.wait_for(self.context.__aexit__(None, None, None), timeout=self.permit.config.runtime.idle_timeout_seconds)
            except BaseException:
                ended = False
        await run_in_threadpool(self.gate.ledger.settle_local, self.access, self.permit, response_state="complete" if self.finished else "partial" if self.seen else "unknown", local_ended=ended, reason="transport_closed" if ended else "transport_close_unknown")


class _FinalizingStreamResponse(StreamingResponse):
    def __init__(self, *args, finalizer, timeout_seconds, **kwargs):
        super().__init__(*args, **kwargs)
        self.finalizer = finalizer
        self.timeout_seconds = timeout_seconds

    async def __call__(self, scope, receive, send):
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await super().__call__(scope, receive, send)
        except TimeoutError:
            # A started response terminates without inventing a completion frame.
            pass
        finally:
            await asyncio.shield(self.finalizer())


class ModelGate:
    def __init__(
        self,
        admission,
        *,
        registry,
        ledger,
        key_resolver,
        transport,
        tool_capabilities: ToolCapabilityResolverPort | None = None,
    ):
        self.admission, self.registry, self.ledger = admission, registry, ledger
        self.key_resolver, self.transport = key_resolver, transport
        self.tool_capabilities = tool_capabilities

    async def request(self, access, request, *, request_id, original_json=None):
        if request.tools:
            if self.tool_capabilities is None:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            await run_in_threadpool(
                self.tool_capabilities.require_available, access, request.tools
            )
        permit = await run_in_threadpool(self.admission.authorize, access, request, request_id=request_id, original_json=original_json)
        headers = {"X-Wuji-Model-Attempt-ID": permit.model_attempt_id, "X-Wuji-Replayed": str(permit.replay).lower(), "Cache-Control": "no-store"}
        if permit.replay:
            if request.stream:
                async def replay():
                    # A fresh scoped transaction reads each bounded persisted chunk.
                    chunks = self.ledger.response_chunks(access, permit)
                    sentinel = object()
                    while (part := await run_in_threadpool(next, chunks, sentinel)) is not sentinel:
                        await run_in_threadpool(self.ledger.forwarded, access, permit, len(part))
                        yield part
                async def replay_closed():
                    return None
                return _FinalizingStreamResponse(replay(), finalizer=replay_closed, timeout_seconds=permit.config.runtime.total_timeout_seconds, media_type="text/event-stream", headers=headers)
            parts = await run_in_threadpool(lambda: list(self.ledger.response_chunks(access, permit)))
            data = b"".join(parts)
            await run_in_threadpool(self.ledger.forwarded, access, permit, len(data))
            return Response(data, media_type="application/json", headers=headers)
        stream = _ModelStream(self, access, permit)
        await stream.open()
        if request.stream:
            async def forward():
                observer = _SSEObserver(permit.config.runtime.buffer_bytes)
                try:
                    async for chunk in stream.chunks():
                        observer.feed(chunk)
                        await run_in_threadpool(self.ledger.forwarded, access, permit, len(chunk))
                        yield chunk
                        if observer.done and not observer.buffer.strip():
                            break
                    stream.finished = observer.done and not observer.buffer.strip()
                except (Exception, asyncio.CancelledError):
                    # Never turn a midstream error into a made-up native message.
                    return
                finally:
                    await asyncio.shield(stream.close())
            return _FinalizingStreamResponse(forward(), finalizer=stream.close, timeout_seconds=permit.config.runtime.total_timeout_seconds, media_type="text/event-stream", headers=headers)
        try:
            data = bytearray()
            async for chunk in stream.chunks():
                if len(data) + len(chunk) > permit.config.runtime.buffer_bytes:
                    raise DomainError("LIMIT_BLOCKED", 429)
                data.extend(chunk)
            parsed = strict_json_loads(data)
            ChatCompletionResponse.model_validate(parsed)
            stream.finished = True
            await run_in_threadpool(self.ledger.forwarded, access, permit, len(data))
            return Response(bytes(data), media_type="application/json", headers=headers)
        finally:
            await asyncio.shield(stream.close())

    async def reconcile(self, access, model_attempt_id):
        # Persisted transport receipts only. No caller boolean can release a slot.
        return await run_in_threadpool(
            self.ledger.reconcile_not_sent, access, model_attempt_id
        )
