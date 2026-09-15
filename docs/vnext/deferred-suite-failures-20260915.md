# vNext suite failures outside the current task — 2026-09-15

Status: **both classes fixed**; the runnable vNext set is green (405 passed). Both failures
pre-dated the P08-S work and were reproduced at `e97eab8` with the working-tree changes stashed, so
they were neither caused by the P15-L layout slice nor by the approval-identity fix.

Command actually run (real isolated PostgreSQL per test, no cluster required):

```text
./scripts/vnext/uv.sh run --frozen pytest \
  tests/vnext/test_capture_transactions.py tests/vnext/test_context_bundle.py \
  tests/vnext/test_dependency_probe.py tests/vnext/test_http_record_rendering.py \
  tests/vnext/test_knowledge_admission.py tests/vnext/test_layouts.py \
  tests/vnext/test_p03_contracts.py tests/vnext/test_contract_shapes.py \
  tests/vnext/test_projection_builder.py tests/vnext/test_remote_workspace.py \
  tests/vnext/test_rls.py tests/vnext/test_run_admission.py \
  tests/vnext/test_scheduler_generations.py tests/vnext/test_work_state_guards.py \
  tests/vnext/test_web_gateway.py tests/vnext/test_web_manifest.py \
  tests/vnext/test_session_approval.py tests/vnext/test_session_permissions.py \
  tests/vnext/test_session_transport.py tests/vnext/test_session_writer_exit_migration.py \
  tests/vnext/test_maf_runtime.py tests/vnext/test_maf_child_transport.py \
  tests/vnext/test_p05_fix_round1.py tests/vnext/test_control_integration.py \
  tests/vnext/test_view_snapshots.py tests/vnext/test_p03_fix_round1.py \
  tests/vnext/test_contract_fix_round1.py tests/vnext/test_contract_fix_round2.py -q
# at e97eab8 + P08-S fixes: 4 failed, 401 passed
# after the class-1 fix:       2 failed, 403 passed in 367.78s
# after the class-2 fix:       0 failed, 405 passed in 372.85s
#   (raw output: work/vnext/p08s/related-suite-final3.txt)
```

Two suites cannot even be collected in this environment (`test_configure_refresh.py`,
`test_k8s_runtime.py`, `test_pod_runtime.py` need the `kubernetes` package that is only installed
for the deployment runtime), so they are out of scope for this record.

## 1. `work_dependency` insert is control-plane state but two P03-era tests write it as a domain write — FIXED

Fixed by adding `control_access()`, `seed_control_actor()` and `seed_capacity()` to
`tests/vnext/support/p03.py` and moving the two dependency inserts into a `capability="control"`
transaction with an operator principal. `seed_control_actor` stays out of the shared `seed()` because
that helper also runs against pre-0006 schemas in upgrade tests, where `task_access.can_control`
does not exist yet. Re-run of the two files plus the upgrade guard: 46 passed.

Failing tests (before the fix):

```text
tests/vnext/test_rls.py::test_two_connections_cannot_commit_dependency_cycle
tests/vnext/test_capture_transactions.py::test_snapshot_pins_revisions_states_relations_after_connection_close
```

Observed error (both, at `tx.add_dependency(...)`):

```text
psycopg.errors.InsufficientPrivilege: new row violates row-level security policy for table "work_dependency"
```

Root cause: migration `vnext_0006_p05_control` replaced the P03 `scoped_insert` policy:

```text
DROP POLICY scoped_insert ON vnext.work_dependency
CREATE POLICY control_insert ON vnext.work_dependency FOR INSERT
  WITH CHECK (vnext.in_scope(...) AND current_setting('wuji.control',true)='true')
```

`wuji.control` is set only for `capability="control"`, which also requires an operator/controller
role and `task_access.can_control`. Both tests still open the transaction with
`capability="write"` and the `collector` fixture principal, so the insert is correctly rejected and
the tests fail before their real assertion.

Minimal fix direction: extend `tests/vnext/support/p03.py` with a control-capable subject
(`can_control=true`, roles `{operator}`) and a `control_access()` helper, then let the two tests
insert dependencies in a `capability="control"` transaction. The cycle guard itself
(`check_dependency`) is unchanged and still exercised.

## 2. Exit/reconcile cannot restore a published pending input because the fixture has no SessionRepository — FIXED

Failing tests (before the fix):

```text
tests/vnext/test_p05_fix_round1.py::test_f2_settlement_after_exit_restores_published_pending_input
tests/vnext/test_work_state_guards.py::test_waiting_input_survives_pause_and_published_resume
```

Observed assertion:

```text
E  - waiting_input
E  + reconciling
```

Root cause, verified with a temporary instrumented `ControlService._settle` (debug patch reverted):

```text
DEBUG settle state running     stop_kind exited settled False result_accepted False
      waiting ('pending','input-fixture') session session-fixture fresh False resumable None
DEBUG settle state reconciling stop_kind exited settled True  result_accepted False
      waiting ('pending','input-fixture') session session-fixture fresh False resumable None
```

`_known_fresh(tx, work)` is false for any run with `stop_kind != 'not_started'`, so the
waiting-input restore needs `self.sessions.validate_recovery_in_transaction(...)`, and the P05-era
fixture built `ControlService` without a `SessionRepository`.

Fixed by mirroring production wiring and the P08-owned boundaries:

- `control_case` now builds a real `SessionRepository(c.uow, artifacts=c.store,
  registry=AdmissionRegistry(c.uow))` and passes it to `ControlService` exactly like
  `ops/vnext/deployment_common.py` does.
- `resumable_session(monkeypatch, c)` pins only `validate_recovery_in_transaction` (returning a
  resumable `RecoveryCheck`) and documents that session-graph validation — real stage, publish,
  permission re-checks — is P08's own coverage in `test_session_permissions.py`.
- `seed_session` writes the publication block (`manifest_ref`, digests, lineage, capability) through
  the migration owner so the persisted `input_delivery` row can reference a real manifest, and the
  test resolves the waiting input through the production `inputs.save_delivery` helper inside a
  `capability="control"` transaction, which is exactly what the 0014 `guard_input_revoke` trigger
  demands ("P08 persisted decision required for resolution").

Result: both tests pass, and the same production-shaped resolution path is exercised instead of a
raw `UPDATE ... SET status='resolved'`.

## Relationship to the current work

- `b465238` (P15-L layout CAS) introduced migration `vnext_0018_p15_layout` and expects exact head
  lists in two old tests; those stale expectations were updated in the P08-S commit together with
  the tests above (`tests/vnext/test_session_approval.py`,
  `tests/vnext/test_session_writer_exit_migration.py`).
- The P08-S commit also fixes the restore-time approval identity check
  (`packages/maf-worker/src/wuji_maf_worker/tools.py`) and three further stale expectations that were
  failing before it (`tests/vnext/test_knowledge_admission.py`, `tests/vnext/test_contract_shapes.py`).
- Both classes are closed; the raw runs above keep the before/after numbers and the exact
  commands used.
