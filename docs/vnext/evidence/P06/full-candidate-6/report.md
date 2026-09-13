# P06 final validation report

P06 base `f32678d5662965f44b32863e8ecdf306db676ffd` was hardened through
`67a8030`, `a9a768c`, `8a3a44d`, `76d5934`, and
`78095e617c0be14932937fb8a052fb9a256b0f56`. The migration head is
`vnext_0009_p06_request_write_guards`.

![P06 final verification](screenshots/final-verification.png)

## Results

```sh
WUJI_TEST_EVIDENCE_DIR=$PWD/docs/vnext/evidence/P06/full-candidate-6/raw \
  ./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_run_admission.py -q
# 35 passed in 38.49s; exit 0

work/toolchain/bin/pnpm contracts:check:v2
# generated Python/TypeScript match OpenAPI; API valid; exit 0
```

The contract result is reused for migration-only follow-ups because the OpenAPI
and generated TypeScript hashes did not change. One existing warning remains
for unused `AgentPayload`.

The final upgrade check loaded the exact `67a8030` historical schema and 0008
migration, created a real v8 PostgreSQL database, then applied current public
`migrate()` to 0009. It verified all model/tool update triggers and reran the
non-owner request/settlement forgery checks: 2 passed.

## Verified boundaries

- Run binding rechecks Task/Work/Run identity, process, reservations and
  revocation without granting control/admit/capture authority.
- Model admission preserves native JSON/SSE and private keys, requires actual
  tool assembly, persists cumulative limits, and reconciles proven not-sent
  attempts without refund/resend or old-Gate revival.
- Tool admission preserves operation identity, approval pending, cancellation
  replay, permit CAS, stopped retry, late settlement and evidence-before-return.
- Workspace limits retain a real prefix with partial EvidenceReceipt and
  `LIMIT_BLOCKED`; replay compares original digest/length without recounting.
- 0009 owns a self-contained four-purpose INSERT/UPDATE matrix. It creates or
  replaces every counter/model/tool update function and reinstalls every
  trigger, so the earliest 67a v8 variant and later v8 variants converge.
  Requests can create only zero/initial rows and exact send/attach/dispatch/
  cancel/retry transitions; settlement cannot create execution. Complete,
  unknown, running and evidence-pending calls cannot reopen.

Complete synthetic HTTP packets are in
[http-reproduction.md](http-reproduction.md). Raw HTTP, identity and PostgreSQL
logs remain in the restricted local `raw/<test-node-hash>/` paths and are
indexed by [sha256.json](sha256.json), but are not staged into Git. Direct
service/RLS/OpenAPI checks are marked non-HTTP. The interface inventory is
[interface-inventory.md](interface-inventory.md).

## Limits

P06 portions of AC-032, AC-044 and AC-045 pass. AC-025 still depends on P09;
AC-036 on P07 official MCP transport; AC-068 on P16 telemetry. P08 durable
approval consumption, P10 Supervisor/Kali execution, real LiteLLM billing,
P17 remote fault matrix, external targets and production cutover remain not run.

The selected adjacent P04 consumer
`test_assessment_actions_are_append_only_and_qualified` also passed (1/1),
confirming the shared UoW/migration changes did not widen assessment writers.
P02 identity/RLS, P03 capture/evidence and P05 revocation/capacity were already
directly exercised by named P06 tests and were not rerun.

Independent static review status: **PASS**. Maxwell reviewed fixed
`f32678d`, each narrow fix, the four-purpose matrix, and the exact earliest-v8
upgrade path without rerunning DB/HTTP. See
[independent-review.md](independent-review.md).
