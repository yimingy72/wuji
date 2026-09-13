"""Hosted Worker entry point; process/Supervisor assembly belongs to P10."""

from wuji_maf_worker.runtime import MafRuntime


async def run_assignment(assignment, *, host, context, run_credential,
                         token_verifier, model_gate_url, tool_gate_url):
    """Consume internal worker events to completion without a UI connection."""
    runtime = MafRuntime(
        host=host, context=context, run_credential=run_credential,
        token_verifier=token_verifier,
        model_gate_url=model_gate_url, tool_gate_url=tool_gate_url,
    )
    async for _event in runtime.execute(assignment):
        pass  # Raw output and result receipt were already persisted by the host.
    await runtime.aclose()
    return runtime.result
