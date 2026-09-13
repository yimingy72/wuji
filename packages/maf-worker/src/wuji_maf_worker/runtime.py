"""One hosted Worker assignment, independently consuming MAF's native stream."""

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from typing import AsyncIterator, Protocol
from urllib.parse import urlsplit

import httpx

from wuji_core.contracts.envelopes import RunIdentity, WorkerAssignment
from wuji_core.http import canonical_json_bytes
from wuji_maf_worker.context import ContextBundle
from wuji_maf_worker.factory import HarnessProfile, build_agent
from wuji_maf_worker.tools import GateFunctions, ModelCallIdentity


@dataclass(frozen=True)
class WorkerEvent:
    kind: str
    agent_run_id: str
    data: dict


class AgentRuntimePort(Protocol):
    def execute(self, assignment: WorkerAssignment) -> AsyncIterator[WorkerEvent]: ...
    async def cancel(self, identity: RunIdentity, reason: str): ...
    async def deliver_input(self, identity: RunIdentity, human_input): ...


class WorkerHostPort(Protocol):
    def resolve(self, assignment, context): ...
    def archive_sdk(self, assignment, body: bytes): ...
    def submit_result(self, assignment, *, raw_output, context, tool_receipts, sdk_output): ...


class MafRuntime:
    def __init__(self, *, host: WorkerHostPort, context: ContextBundle,
                 run_credential: str, model_gate_url: str, tool_gate_url: str):
        for url, suffix in ((model_gate_url, "/internal/v2/model"), (tool_gate_url, "/internal/v2/tool-calls")):
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip("/") != suffix:
                raise ValueError("a deployment-owned Wuji Gate endpoint is required")
        if not run_credential or "\n" in run_credential or "\r" in run_credential:
            raise ValueError("a Run credential is required")
        self._host, self._context, self._credential = host, context, run_credential
        self._model_url, self._tool_url = model_gate_url, tool_gate_url
        self._assignment = None
        self._task = None
        self.result = None
        self.raw_output = b""
        self.sdk_output = b""
        self.tool_receipts = []
        self.identity_mapping = []

    async def execute(self, assignment):
        assignment = WorkerAssignment.model_validate(assignment).model_copy(deep=True)
        if self._assignment is not None and self._assignment != assignment:
            raise ValueError("one runtime instance owns one immutable assignment")
        if self._task is None:
            self._assignment = assignment
            # Only this task owns SDK iteration. Closing an event consumer does not
            # inject cancellation into the SDK, tool request or result commit.
            self._task = asyncio.create_task(self._run(assignment))
        receipt = await asyncio.shield(self._task)
        yield WorkerEvent(
            "result_receipt", assignment.identity.agent_run_id,
            receipt.model_dump(mode="json"),
        )

    async def wait(self, identity):
        self._require_identity(identity)
        return await asyncio.shield(self._task)

    def _require_identity(self, identity):
        if self._assignment is None or RunIdentity.model_validate(identity) != self._assignment.identity:
            raise ValueError("no local task for that complete Run identity")

    async def cancel(self, identity, reason):
        self._require_identity(identity)
        if not isinstance(reason, str) or not 1 <= len(reason) <= 8192:
            raise ValueError("a bounded cancellation reason is required")
        if self._task.done():
            state = "local_task_finished"
        else:
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5)
                state = "local_task_finished"
            except asyncio.CancelledError:
                state = "local_task_cancelled"
            except TimeoutError:
                state = "local_cancel_requested"
            except Exception:
                state = "local_task_failed"
        return {"source": "worker_adapter", "state": state, "remote_state": "unknown"}

    async def deliver_input(self, identity, human_input):
        self._require_identity(identity)
        raise NotImplementedError("M1 has no published persistent delivery/approval boundary")

    async def aclose(self):
        if self._task is not None:
            await asyncio.shield(self._task)

    async def _run(self, assignment):
        if assignment.session_manifest_ref is not None or assignment.resume_reason is not None:
            raise NotImplementedError("M1 only executes fresh work; manifest restoration is unavailable")
        resolved = await asyncio.to_thread(self._host.resolve, assignment, self._context)
        profile = HarnessProfile.from_snapshot(resolved["profile"])
        if (
            self._context.snapshot_id != assignment.snapshot_id
            or sha256(self._context.text.encode()).hexdigest() != self._context.input_digest
            or len(self._context.record_refs) > profile.max_context_records
            or len(self._context.text.encode()) > profile.max_context_bytes
        ):
            raise ValueError("context does not match the frozen input/profile")
        limits = resolved["limits"]
        identity = ModelCallIdentity(resolved["tools"], max_bytes=limits["max_single_output_bytes"])
        self.identity_mapping = identity.mapping
        timeout = httpx.Timeout(resolved["request_timeout_seconds"])
        sdk_lines = []
        retained = 0

        def retain(body):
            nonlocal retained
            retained += len(body) + 1
            if retained > limits["max_total_output_bytes"]:
                raise ValueError("SDK archive exceeds the published output limit")
            sdk_lines.append(body)

        def archive_bytes():
            return b"\n".join(sdk_lines + [canonical_json_bytes({
                "source": "wuji_worker_adapter", "identity_mapping": identity.mapping,
                "tool_receipts": [r.model_dump(mode="python") for r in self.tool_receipts],
                "snapshot_id": self._context.snapshot_id, "input_digest": self._context.input_digest,
            })]) + b"\n"

        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(retries=0), trust_env=False,
            follow_redirects=False, timeout=timeout,
            event_hooks={"request": [identity.request], "response": [identity.response]},
        ) as model_http, httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(retries=0), trust_env=False,
            follow_redirects=False, timeout=timeout,
            headers={"Authorization": "Bearer " + self._credential, "Content-Type": "application/json"},
        ) as tool_http:
            functions = GateFunctions(
                definitions=resolved["tools"], identity=identity,
                lineage=resolved["session_lineage"], client=tool_http, url=self._tool_url,
            )
            self.tool_receipts = functions.receipts
            agent, native = build_agent(
                resolved=resolved, profile=profile, model_http=model_http,
                model_gate_url=self._model_url, run_credential=self._credential,
                tools=functions.registered_tools(), middleware=functions,
                response_parser=identity.parse_response,
            )
            try:
                async with asyncio.timeout(limits["max_elapsed_seconds"]):
                    session = agent.create_session()
                    stream = agent.run(self._context.text, session=session, stream=True)
                    async for update in stream:
                        retain(update.to_json().encode())
                    final = await stream.get_final_response()
                    retain(final.to_json().encode())
                    retain(canonical_json_bytes({"session": session.to_dict()}))
                    messages = [m for m in final.messages if m.role == "assistant"]
                    if not messages or not messages[-1].text or any(c.type in {"function_call", "function_approval_request"} for c in messages[-1].contents) or final.continuation_token is not None:
                        raise ValueError("SDK has no settled final assistant text")
                    self.raw_output = messages[-1].text.encode("utf-8")
                    self.sdk_output = archive_bytes()
                    if len(self.raw_output) > limits["max_single_output_bytes"] or len(self.sdk_output) > limits["max_total_output_bytes"]:
                        raise ValueError("final SDK output exceeds published limits")
                    self.result = await asyncio.to_thread(
                        self._host.submit_result, assignment,
                        raw_output=self.raw_output, context=self._context,
                        tool_receipts=tuple(self.tool_receipts), sdk_output=self.sdk_output,
                    )
                    return self.result
            except BaseException:
                self.sdk_output = archive_bytes()
                # Preserve the actual partial SDK observations if the result sink
                # did not finish. A persistence error propagates, never success.
                if sdk_lines:
                    await asyncio.to_thread(self._host.archive_sdk, assignment, self.sdk_output)
                raise
            finally:
                await native.close()
