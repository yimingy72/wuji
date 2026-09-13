# P09/M2 Scheduler independent review

Date: 2026-09-13  
Requested lane: SOL/xhigh; independent read-only review  
Decision: **NEEDS FIX — P09 is not ready to act as the shared persistence/API gate**

Coordination status: main accepted all three findings and assigned the bounded repair direction to Archimedes. Archimedes independently re-read the cited paths, agreed that all three are real P09 defects, and did not run PostgreSQL or pytest. The next review is limited to these three fixes and their direct regression checks; the existing `31 + 4 + 1` results remain the baseline and are not to be rerun merely because ownership changed.

## Reviewed boundary

- Core source commit: `5c6217b5aaf159a3946f823f3d1fe0a67321a16d`.
- Final verification/fix commit: `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c`.
- The review used the union of the two commits' P09-owned changes: `scheduling/*`, `persistence/scheduler_schema.py`, the necessary `persistence/schema.py` and `persistence/snapshots.py` integration, `services/wuji-scheduler/main.py`, `tests/vnext/test_scheduler_generations.py`, and `tests/vnext/support/p09.py`.
- Intermediate P13, P07/M1 and P14/UI commits and the current shared-tree changes after `a3f7a95` were excluded. The current worktree was at `592bed2d1bbb59e4bda720039fa3940c405d66c9`; its unrelated dirty files were not read as P09 final code and were not modified.
- Required sources read: root `AGENTS.md`, project context, Spec S04/S06/S07, Plan P09/P10 boundary, `P09-brief.md`, `P09-parallel-brief.md`, `P09-implementation-contract.md`, `P09-core-interface.md`, `P09-shared-decisions.md`, `P09-core-handoff.md`, and `P09-shared-handoff.md`. This worktree has no `.codegraph/`, so review fell back to immutable Git objects, `rg`, and direct line-by-line reads.

## Findings

### [P1] Admission can publish a Run to a receiver that has no receive/decrypt authority

`packages/wuji-core/src/wuji_core/scheduling/claims.py:314-326` accepts an enabled `scheduler_receiver` and enabled identity template without checking the referenced `receiver_subject` still has `can_read` and `can_observe`. The DDL at `packages/wuji-core/src/wuji_core/persistence/scheduler_schema.py:145-152` only gives `receiver_subject` a foreign key to `task_access`; it does not constrain those permissions.

Minimal counterexample: register an enabled receiver whose existing `task_access` row has `can_observe=false`, then tick an otherwise runnable Task. `_receiver` succeeds, so `_admit` can commit the AgentRun, capacity reservations, credential, Assignment and Outbox. `DispatchRepository.read` and `read_scheduler_credential` later require an observe transaction and reject that same subject. The Run is durably undeliverable while its reservations remain held. This violates the contract that a missing or unauthorized receiver blocks before Run/Outbox creation.

Fix the admission-side receiver lookup so it joins the current same-Task ACL and requires the receiver's database authority before Snapshot/Run creation. Keep the existing receiver-side checks as defense in depth. The current positive test fixture always installs a valid observer, so `tests/vnext/test_scheduler_generations.py:304-370` does not exercise this path.

### [P1] A rejected `propose_intents` result can consume the authoritative trigger generation

`packages/wuji-core/src/wuji_core/scheduling/triggers.py:338-416` accepts the P04 overall receipt, calls `_apply_decision`, records the Scheduler decision as accepted and advances `consumed_generation`. At `triggers.py:418-447`, `_apply_decision` has checks for wait, blocked and completion but no `propose_intents` check.

P04 can legitimately produce `ResultReceipt.status=accepted` while every Intent component is rejected: overall receipt status describes the accepted submission envelope, and component receipts carry independent rejection codes. With raw `reason_decision=propose_intents`, P09 currently performs no canonical action, records the decision as accepted, clears the inflight Reason and consumes through `processing_generation`. No admitted Intent/Work exists and the trigger is lost. This is receipt/watermark corruption, not a P10 producer limitation.

Require `propose_intents` to bind at least one accepted canonical Intent component from the actual P04 receipt. When no such component exists, record a rejected Scheduler decision and leave the generation unconsumed for the existing terminal-settlement/bounded-failure path. The 31-item P09 file contains no production `TriggerRepository.consume` case; the recorded late-generation test at `tests/vnext/test_scheduler_generations.py:507-535` exercises `record/read` only.

### [P2] Recheckable blocked Work can permanently starve runnable Work in the same Task

`packages/wuji-core/src/wuji_core/scheduling/claims.py:795-825` includes every machine-recheck block in each candidate snapshot. `claims.py:851-891` advances only the Task selection position when admission fails, while `packages/wuji-core/src/wuji_core/scheduling/policy.py:134-161` deterministically ranks Work inside that Task from unchanged priority/age/work ID. There is no persisted Work cursor, failed-proposal continuation beyond the fixed tick limit, or retry eligibility time on `scheduler_block`.

Minimal counterexample: place at least `tick.limit` older/high-priority Works in `required_snapshot_input_unavailable` (a machine-recheck code) and one lower-ranked runnable Work in the same Task. Every tick proposes the same blocked prefix, every admission fails, and the runnable Work never reaches `_admit`. Age does not repair this because all existing candidates age at the same rate and keep their score differences. This violates P09's bounded fairness guarantee.

Persist a Work-level continuation/backoff/recheck condition, or continue selection after failed proposals with a bounded mechanism that cannot repeatedly spend the full proposal window on the same unchanged failures. The current fairness tests cover pure age and tenant/Task cursors but do not combine repeated admission rejection with a lower-ranked runnable Work.

## Confirmed scope and existing evidence

Read-only inspection found no additional same-or-higher-severity defect in these implemented paths: dedicated non-owner advisory-lock session ownership; reuse of that exact session for P05 pool-to-Task admission; atomic Run/run_epoch/stable operation/Reservation/credential/Assignment/Outbox commit; minimal per-Run JWT identity with encrypted credential reference; SQL denial of identity creation when `wuji.admit` is false or request/settlement purpose is set; Snapshot reader binding to current subject/JTI/credential/Run/epochs/revocation/ACL/clearance; required-input failure before Run creation; exact Work key; late generation retention; and waiter condition-first/condition-later handling. This is a static review statement bounded by the recorded tests below, not a fresh execution claim.

Archimedes reported these already executed results for final commit `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c`; this review did not rerun them:

- `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_scheduler_generations.py -q` — exit 0, `31 passed in 16.57s`. Mixed pure checks and real isolated PostgreSQL through the non-owner application role. The owner connection was limited to migration and deployment prerequisites.
- `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_capture_transactions.py::test_snapshot_query_scope_current_access_and_expiration tests/vnext/test_capture_transactions.py::test_read_only_member_can_create_a_snapshot_without_domain_write tests/vnext/test_knowledge_admission.py::test_fixed_snapshot_includes_assessment_inputs_and_checks_current_access tests/vnext/test_run_admission.py::test_run_credential_does_not_grant_control_admit_or_capture -q` — exit 0, `4 passed in 3.53s` on real isolated PostgreSQL/non-owner consumer paths.
- `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_work_state_guards.py::test_shared_global_pool_serializes_two_tenants -q` — exit 0, `1 passed in 0.74s`; two tenants and two independent non-owner connections raced the last shared global slot. This is a reused P05 capacity test at the P09 migration head, not a new P09-specific concurrency implementation.

The original task records contain the command outputs. No permanent stdout/JUnit/screenshot/HTTP package was created for this offline slice. The committed tests are reviewable, but they are not a substitute for those missing durable run artifacts.

## Explicitly unverified or outside this slice

- P10 receiver producer, prepared/spawn/running/exit truth and full Outbox delivery are absent. Assignment registration does not prove spawn or M2 completion.
- M1 does not implement restoration; P09 deliberately blocks previously executed Work. No complete Session restore is claimed.
- P08 public typed Work/Input/GoalCriterion WaitRef production and a real same-revision non-knowledge event producer are not verified.
- Full P04 ReasonDecision consumption and trusted terminal finite-failure/retry flow were not executed; the receipt-consumption defect above must be fixed before that closure can pass.
- No actual scheduler service process, paid model, external target, HTTP flow, UI, Kubernetes path or P13 persistence DDL was reviewed or run here.
