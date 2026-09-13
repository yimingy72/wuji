# P09 directed rereview — A/B/C and receiver Pod UID seam

Date: 2026-09-13
Decision: **PASS — the three findings in `P09-review.md` and the directly related receiver `pod_uid` upgrade seam are closed in `e0a10b586905ed705b0d7f520bda6f6f96b26cac`.**

Gate effect: this fix may serve as the P09 migration gate for the next P13 persistence migration. This is not a claim that P09 is fully accepted or that P10/M2, process restoration, or a real Pod path is complete.

## Review identity and method

- Reviewer: Dalton, an independent rereview agent directly delegated by the main agent with `model=gpt-5.6-sol` and `reasoning_effort=xhigh`.
- Dalton personally performed the bounded static rereview against immutable Git objects and the existing execution transcript. Dalton is independent of implementer Archimedes; no lower-level reviewer was required or used.
- The executed RED/GREEN evidence below was produced by the completed Archimedes SOL/xhigh implementation lane and was reused without rerunning it.
- No DB, HTTP, compile, formatter, service, browser, Kubernetes, or other validation was rerun for this rereview.
- The worktree has no `.codegraph/`; review used the exact commit diff, direct line-numbered source reads, and the existing execution transcript.

## Exact boundary

- Original tested P09 code: `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c`.
- Fix under review: `e0a10b586905ed705b0d7f520bda6f6f96b26cac`.
- Code review used only the single-commit diff `e0a10b5^..e0a10b5`. Its seven paths are the new 0011 migration, `schema.py`, P09 `claims.py` / `policy.py` / `triggers.py`, and the two P09 test files.
- The current worktree HEAD contains later P10 work. No `a3f7a95..HEAD` branch diff, M1, P13, P10 implementation, or UI change contributed to this decision. The seven reviewed paths have no later overlap between `e0a10b5` and the current HEAD.
- The original `.superpowers/sdd/vnext-v2/P09-review.md` and the old `packages/wuji-core/src/wuji_core/persistence/scheduler_schema.py` / `vnext_0010_p09_scheduler` source were not modified.

## Finding A — receiver authority before receiver-dependent writes

**Closed.**

`dispatch_fairness_schema.py:48-69` adds a narrow `SECURITY DEFINER` predicate that checks the fixed same-Task/runtime receiver, enabled identity template, scheduler caller `can_read + can_admit`, receiver subject's current `can_read + can_observe`, and a present registered `pod_uid`. This avoids the self-only `task_access` RLS problem without granting the scheduler general ACL visibility.

`claims.py:314-329` uses that predicate. `_prepare` performs the receiver check at `claims.py:419-424`, before accepted Intent materialization and `WorkRepository.register`. `_admit` repeats it at `claims.py:555-566`, before blocked-Work reopening, Snapshot creation, AgentRun, capacity reservation, credential binding, Assignment, Outbox, or snapshot-reader binding. It does not add or repair receiver permissions.

The existing focused test revokes `can_observe`, receives `receiver_unavailable`, and observes zero Scheduler Work, Assignment, credential, reservation, and dispatch Outbox rows. Trigger accumulation is independent durable bookkeeping and was not part of the original undeliverable-Run defect.

## Finding B — authoritative generation consumption

**Closed.**

`triggers.py:304-416` still advances `consumed_generation` only after `_apply_decision` succeeds. For `propose_intents`, `triggers.py:421-444` now requires a non-empty set of receipt components that are `accepted_shared`, have no component error, carry a canonical Intent ref, and resolve to an `intent_revision` owned by the current Reason AgentRun in the same Task.

An empty component set, no accepted canonical Intent, or an all-rejected receipt makes `not accepted` true, records Scheduler decision `rejected/reason_intent_not_accepted`, leaves the inflight Reason and previous `consumed_generation` intact, and returns `False`. An accepted canonical Intent from a different producer cannot satisfy the AgentRun binding. P04 raw output, component receipts, accepted Claims, and canonical Intent records are not rewritten.

The reused RED/GREEN node exercises the real P04 all-rejected receipt. Empty-result behavior follows the same explicit `not accepted` branch; no additional matrix was run for this rereview.

## Finding C — bounded Work consideration across rejection and reconstruction

**Closed.**

`dispatch_fairness_schema.py:8-37` adds persisted `scheduler_work.consideration_round` and an admit-only column update policy/grant. `claims.py:799-829` reads the value into every eligible candidate. At `claims.py:850-909`, each selected Work increments its round in the outer Scheduler transaction before entering the admission savepoint, so an admission rejection rolls back its provisional admission writes but not its consideration progress.

`policy.py:140-175` orders by `consideration_round` before the existing bounded priority/age/control score. Therefore a fixed set of more-than-`limit` high-ranked machine-recheck blocks can each occupy a batch only at its current round; an unconsidered runnable Work remains at the lower round and reaches `_admit`. Rank and aging still decide order inside one round. The value is stored in PostgreSQL and reloaded when a Scheduler object is reconstructed, so process-local state cannot reset the progression.

The focused test uses more blocked candidates than the tick limit, persists two first-round considerations, adds another blocked candidate, reconstructs `Scheduler`, and observes the lower-ranked runnable Work admitted within the next two bounded ticks. This proves the P09 persistence/reconstruction seam; it is not a P10 process-restart test.

## Receiver Pod UID and 0010 → 0011 upgrade

**Closed for the P09/P10 registration seam.**

`vnext_0011_p09_dispatch_fairness` is a new incremental migration. It adds nullable `scheduler_receiver.pod_uid`, disables every enabled 0010 receiver whose newly added UID is null or blank, and then prevents an enabled receiver from lacking a bounded non-empty UID. It never fabricates a value. Deployment must republish the receiver from trusted runtime metadata before it can be used again.

The receiver table remains deployment/migration controlled: the application role receives no INSERT or UPDATE producer for `scheduler_receiver`. `claims.py:674-690` copies the selected registered receiver's exact `pod_uid` into the new AgentRun in the same admission transaction. The focused main-flow node uses an explicitly synthetic fixture UID and verifies that exact value in the registered Run; it does not claim Kubernetes metadata or process start truth.

`schema.py` appends 0011 after `SCHEDULER_HEAD` in both upgrade and fresh-install paths. A direct `a3f7a95..e0a10b5` path check confirms `scheduler_schema.py` and the old 0010 migration source are unchanged.

## Reused execution evidence

These commands were read from the completed Archimedes SOL/xhigh task transcript. They were not rerun here:

1. A/B/C focused nodes:

   `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_scheduler_generations.py::test_scheduler_rejects_receiver_without_current_observe_permission_before_dispatch tests/vnext/test_scheduler_generations.py::test_rejected_reason_intents_do_not_consume_processing_generation tests/vnext/test_scheduler_generations.py::test_persisted_work_cursor_advances_past_more_than_limit_blocked_candidates -q`

   - RED: exit 1, `3 failed in 5.04s` — unauthorized receiver still produced two Assignments; rejected Intent receipt returned `consume=True`; fairness persistence was absent.
   - GREEN: exit 0, `3 passed in 5.00s`.

2. Incremental migration node:

   `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_scheduler_generations.py::test_p09_fairness_migration_upgrades_0010_and_reapplies_once -q`

   - exit 0, `1 passed in 1.22s`.

3. Receiver UID copy node:

   `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_scheduler_generations.py::test_scheduler_main_flow_uses_real_pg_and_minimal_signed_run_identity -q`

   - exit 0, `1 passed in 2.49s`.

The GREEN, upgrade, and UID checks ran before the commit on the same seven-path worktree bytes later committed as `e0a10b5`; the lane then staged only those seven paths. There was no post-commit DB rerun. The task transcript is the existing evidence source; no permanent P09 stdout/JUnit/screenshot/HTTP package was created. This static rereview is not a new test-result artifact and does not fabricate those missing delivery media.

## Explicit non-claims

- P10's real receiver producer, authenticated transport assembly, prepared/spawn/running/exit truth, crash windows, and full Outbox delivery remain outside this rereview.
- Full M2 and complete P09 acceptance remain pending their actual downstream integration criteria.
- M1/Session restoration remains unsupported; previously executed Work continues to block rather than inventing a recovery point.
- No real Kubernetes Pod UID, actual process start, P08 public producer matrix, HTTP API, UI, paid model, or external target was reviewed or executed here.
- The decision is only that A/B/C and the directly required 0010→0011/receiver-UID seam have no remaining direct code risk in the reviewed patch.
