"""Hosted Worker entry point; process/Supervisor assembly belongs to P10."""

import asyncio
import json

import httpx

from wuji_core.contracts.admission import ToolSettlementRequest
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_maf_worker.runtime import MafRuntime


TOOL_CALLS_PATH = "/internal/v2/tool-calls"
SETTLEMENT_PATH = "/internal/v2/tool-settlement"
CLOSE_TIMEOUT_SECONDS = 5.0


def settlement_url(tool_gate_url):
    """Address the settlement route that is a sibling of the tool-calls route.

    The deployed worker is given the full tool-calls URL, never a base URL, so
    the only accepted input is that frozen route; anything else is refused
    instead of guessing an origin to publish a settlement to.
    """

    base, separator, tail = tool_gate_url.rpartition(TOOL_CALLS_PATH)
    if not separator or tail:
        raise ValueError("the configured tool gate URL must name the tool-calls route")
    return base + SETTLEMENT_PATH


async def close_operation_set(*, tool_gate_url, run_credential, ssl_context=None):
    """Tell the gate this Run will start no further operation.

    The Run states only that it is finished; the gate recomputes the status from
    durable platform records. Bounded and best-effort on purpose: a refused
    close leaves the operations unsettled, where the platform already treats
    them as unknown, and it must never change the Run's own outcome.
    """

    body = canonical_json_bytes(ToolSettlementRequest.model_validate(
        {}).model_dump(mode="python"))
    try:
        async with asyncio.timeout(CLOSE_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=0, verify=ssl_context or True),
                trust_env=False, follow_redirects=False,
                timeout=httpx.Timeout(CLOSE_TIMEOUT_SECONDS),
                headers={"Authorization": "Bearer " + run_credential,
                         "Content-Type": "application/json", "Accept": "application/json",
                         "Accept-Encoding": "identity"},
            ) as client:
                response = await client.post(settlement_url(tool_gate_url), content=body)
    except Exception:
        return None
    if response.status_code != 200:
        # Bounded operator signal: the status is stable, the body stays private.
        print(json.dumps({"event": "worker_operation_set_unsettled",
                          "status": response.status_code}, sort_keys=True), flush=True)
        return None
    return strict_json_loads(response.content)


async def run_assignment(assignment, *, host, context, run_credential,
                         token_verifier, model_gate_url, tool_gate_url,
                         ssl_context=None):
    """Consume internal worker events to completion without a UI connection."""
    runtime = MafRuntime(
        host=host, context=context, run_credential=run_credential,
        token_verifier=token_verifier,
        model_gate_url=model_gate_url, tool_gate_url=tool_gate_url,
        ssl_context=ssl_context,
    )
    try:
        async for _event in runtime.execute(assignment):
            pass  # The Host has persisted either the result or the native input receipt.
        await runtime.aclose()
        return runtime.input_receipt if runtime.input_receipt is not None else runtime.result
    finally:
        # One Run owns one operation set. Closing it on every exit path is what
        # lets the platform settle a Run that made no tool call at all, instead
        # of pinning its Work item at `operations_unsettled` forever.
        await close_operation_set(
            tool_gate_url=tool_gate_url, run_credential=run_credential,
            ssl_context=ssl_context,
        )
