# P06 final validation report

P06 base `f32678d5662965f44b32863e8ecdf306db676ffd` was hardened through
`67a8030`, `a9a768c`, `8a3a44d`, and
`76d593468881a4cc2fed0de71142895e3d08a9ac`. The migration head is
`vnext_0009_p06_request_write_guards`, which upgrades existing 0008 and 0007
databases rather than rewriting their recorded heads.

![P06 final verification](screenshots/final-verification.png)

## Results

```sh
WUJI_TEST_EVIDENCE_DIR=$PWD/docs/vnext/evidence/P06/full-candidate-5/raw \
  ./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_run_admission.py -q
# 33 passed in 42.12s; exit 0

work/toolchain/bin/pnpm contracts:check:v2
# generated Python/TypeScript match OpenAPI; API valid; exit 0
```

The contract check was run after the OpenAPI response-header change and reused
for migration-only follow-ups because OpenAPI/generated hashes did not change.
One existing warning remains for unused `AgentPayload`.

Four review cycles produced 7, 2, 3 and 5 meaningful RED failures. Targeted
GREEN runs passed 8, 2, 3 and 8 checks before the final 33-item run.

## Verified boundaries

- Run binding rechecks current Task/Work/Run identity, process, reservations and
  revocation without granting control/admit/capture authority.
- Model admission preserves native JSON/SSE and private keys, handles
  `tools:null`, requires actual tool assembly, persists cumulative limits, and
  reconciles proven not-sent attempts without refund/resend or old-Gate revival.
- Tool admission preserves canonical operation identity, approval pending,
  cancellation replay, receiver permit CAS, explicit stopped retry, late
  settlement and evidence-before-return.
- Workspace output limits retain an actual prefix with partial EvidenceReceipt
  and `LIMIT_BLOCKED`; replay compares original digest/length without recounting.
- 0009 records the four-purpose INSERT/UPDATE matrix. Requests can create only
  zero/initial authority rows and exact send/attach/dispatch/cancel/retry
  transitions. Settlement cannot create execution, ToolCall, ToolAttempt,
  resource claim or reservation. Failed/cancelled retries require a stopped
  prior receipt and an already-registered new attempt; complete, unknown,
  running and evidence-pending calls cannot reopen.

Complete HTTP packets are in [http-reproduction.md](http-reproduction.md); raw
HTTP, identity and PostgreSQL logs are under `raw/<test-node-hash>/`. Direct
service/RLS/OpenAPI checks are marked non-HTTP. The route and service inventory
is [interface-inventory.md](interface-inventory.md).

## Limits

P06 portions of AC-032, AC-044 and AC-045 pass. AC-025 still depends on P09;
AC-036 on P07's official MCP transport; AC-068 on P16 telemetry. P08 durable
approval consumption, P10 Supervisor/Kali execution, real LiteLLM billing,
P17 remote fault matrix, external targets and production cutover remain not run.

Independent static review status: pending final narrow review of 0009.
