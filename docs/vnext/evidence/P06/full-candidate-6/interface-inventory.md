# P06 interface inventory

Validated code ends at `78095e617c0be14932937fb8a052fb9a256b0f56`;
migration head is `vnext_0009_p06_request_write_guards`.

![P06 verification](screenshots/final-verification.png)

| Interface | Purpose | Validation status |
| --- | --- | --- |
| `POST /internal/v2/model/chat/completions` | Signed native Chat Completions Gate | validated with localhost upstream, replay, limits, null tools and capability assembly |
| `GET /internal/v2/model-attempts/{id}` | Durable model receipt | validated; no new inference |
| `ModelGate.reconcile` / `AdmissionLedger.reconcile_not_sent` | End proven not-sent slot without refund/resend | validated with rebuilt services and send fence |
| `POST /internal/v2/tool-calls` | Canonical ToolCall admission/execution | validated with production `workspace_read`, approval, replay and partial evidence |
| `GET /internal/v2/tool-calls/{id}` | Durable tool receipt | validated; no re-execution |
| `POST /internal/v2/tool-calls/{id}/cancel` | Idempotent cancel intent | delivery replay validated; remote matrix remains P17 |
| `ToolGate.invoke_function` | Function normalization | validated against server revocation |
| `ToolGate.invoke_mcp` | Official MCP normalization | fail-closed validated; official package/full path not run |
| `ToolCapabilityResolver(tool_gate)` | Require actual executor/collector assembly before advertisement | missing and assembled paths validated |
| `ToolAdmission.retry` | Retry confirmed stopped attempt | registered retry/replay validated; unknown/complete/nonterminal reopen denied |
| deployment registry functions | Freeze/revoke config, definitions, executors and Run bindings | validated through owner connection |
| `AdmissionLedger.snapshot/model_attempt/tool_call` | Durable cumulative counters/receipts | validated with rebuilt services and PostgreSQL |
| 0009 request-write matrix | Separate four purposes across authority tables | validated for INSERT/UPDATE, exact transitions and safe retry |
| earliest 0008 → 0009 upgrade | Normalize every update function and trigger | validated using exact 67a migration code then current public `migrate()` |

`http_target` remains unavailable until a redirect-aware Scope adapter exists.
Run credentials do not receive Task keys or controller/admit/capture/observe
permissions. Complete HTTP packets are in
[http-reproduction.md](http-reproduction.md).
