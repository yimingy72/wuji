# P06 validation report

Candidate `f32678d5662965f44b32863e8ecdf306db676ffd` implements migration head
`vnext_0007_p06_admission`. The focused P06 suite passed 13/13 against isolated
PostgreSQL, signed inbound ASGI, a real localhost model HTTP peer, and the
production `WorkspaceReadExecutor`. No paid model, external target, old service,
deployment switch, or remote publish was used.

![P06 final verification](screenshots/final-verification.png)

## Commands and results

```sh
WUJI_TEST_EVIDENCE_DIR=$PWD/docs/vnext/evidence/P06/full-candidate-1/raw \
  ./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_run_admission.py -q
# 13 passed in 13.50s; exit 0

work/toolchain/bin/pnpm contracts:check:v2
# generated Python/TypeScript match OpenAPI; OpenAPI valid; exit 0
```

The contract check retained one existing warning for the unused `AgentPayload`
component. It did not report generated-file drift or an invalid API description.

## Covered behavior

| Test | Result | Boundary |
| --- | --- | --- |
| `test_current_run_model_gate_forwards_native_and_records_attempt` | pass | Current signed Run, private key resolution, native response, durable receipt and no duplicate P05 pool reservation |
| `test_revoked_run_cannot_request_model` | pass | Deployment credential revocation rejects before secret resolution/upstream/attempt |
| `test_p05_pause_makes_bound_run_identity_stale` | pass | P05 control state and epoch authority override a still-valid token |
| `test_model_request_replay_conflict_and_new_id_have_distinct_attempts` | pass | Same ID/digest replay, changed digest conflict, new ID new inference |
| `test_two_runs_cannot_both_take_the_last_task_model_request` | pass | Real multi-connection race admits one final Task request |
| `test_partial_stream_releases_local_inflight_without_settling_billing` | pass | Missing `[DONE]` remains partial; local end, inflight and billing remain separate |
| `test_workspace_read_returns_only_after_persisting_evidence` | pass | Real file read, receiver inbox, Artifact seal, EvidenceReceipt, then return; GET does not execute again |
| `test_revoked_run_cannot_dispatch_workspace_tool` | pass | Revoked Run produces no receiver receipt or ToolAttempt |
| `test_task_output_limit_is_cumulative_across_model_attempts` | pass | Second response observes Task total output limit; overflow is received but not retained/forwarded |
| `test_approval_required_tool_does_not_create_an_execution_attempt` | pass | Unbound approval remains pending with zero execution attempt/evidence |
| `test_tool_operation_replay_conflict_and_new_call_id_control_execution` | pass | Canonical ToolCall replay/conflict/new provider call identity |
| `test_missing_mcp_type_and_revoked_function_adapter_do_not_execute` | pass | Missing official MCP package fails closed; function adapter observes server tool revocation |
| `test_started_tool_can_settle_after_revocation_but_new_work_is_rejected` | pass | Trusted settlement preserves an already-started result after revocation; new work remains denied |

Every HTTP-backed row has its complete method, URL, headers, request body,
status, response headers and response body in
[the reproduction packet](http-reproduction.md). Original inbound/outbound HTTP,
identity and PostgreSQL event JSONL files remain under `raw/<test-node-hash>/`.
The direct function/MCP row has no HTTP route and is marked accordingly rather
than receiving a fabricated packet.

## Acceptance interpretation

- AC-032 P06 model/tool portions pass. Session persistence remains owned by
  P08/P11.
- AC-044 P06 partial-stream behavior passes; no completion frame or assistant
  result was fabricated.
- AC-045 P06 cumulative request/output, multi-Run contention and durable ledger
  portions pass. P17 restart/fault end-to-end remains not run.
- AC-025 admission rejection passes; P09 still owns the pure scheduling-policy
  portion.
- AC-036 function-adapter revocation and missing-MCP fail-closed behavior pass.
  Official MCP normalization and full MCP transport remain not run because
  `mcp.types` is not installed; P07 owns that integration.
- AC-068 P06 durable audit/billing-state separation is exercised by the real
  ledger. P16's complete trace/metric policy remains not run.

Other explicit not-run boundaries are P08 durable approval consumption,
Supervisor/Kali remote execution, real LiteLLM pricing/billing reconciliation,
external targets, production cutover, downstream SDK/MAF integration, and P17's
tool cancel/reconcile/retry and restart fault matrix.
