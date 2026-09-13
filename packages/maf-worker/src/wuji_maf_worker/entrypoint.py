"""Hosted Worker entry point; process/Supervisor assembly belongs to P10."""

from wuji_maf_worker.runtime import MafRuntime


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
    async for _event in runtime.execute(assignment):
        pass  # The Host has persisted either the result or the native input receipt.
    await runtime.aclose()
    return runtime.input_receipt if runtime.input_receipt is not None else runtime.result
