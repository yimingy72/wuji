# P10/M2 Bridge independent read-only review

**Verdict: FAIL for the stated Scheduler → Outbox → real Child path. Four Important/P2 findings; no Critical/P1 finding in the assigned scope.**

Reviewed target: core `6e90a97fa507717e4f8b06229ca1d2fc5e1593c4`, effective candidate `e40e7e2100cf528bf7eba797176b9bd033be48c3`. `87e1304` was read only to understand the later ControllerAdapter callback contract; its Node settlement/main behavior remains Epicurus-owned and its child rerun remains Dirac-owned. This reviewer ran no test, PostgreSQL, HTTP, process, browser, formatter, generation or build command.

Assigned source read completely: `execution/{dispatch_outbox,reconcile,worker_bridge}.py`, `maf-worker/{remote_host,child_entrypoint}.py`, `http/worker_host.py`, `services/maf-supervisor/controller-adapter.mjs`, bridge OpenAPI/generated DTOs, `tests/vnext/{test_maf_child_transport.py,support/m2.py}`, and the submitted M2 result/interface records. Excluded as directed: Node `main.mjs` settlement P1, P08, P13, P14/P15 and later unrelated current-HEAD changes.

## Findings

### 1. Important/P2 — actual child test bypasses DispatchOutbox and no production consumer exists

`tests/vnext/test_maf_child_transport.py:110-112@e40e7e2` obtains a P09 Assignment and calls the test helper `case.node.start()` directly. `tests/vnext/support/m2.py:513-524` constructs `SupervisorHttpTransport` only for Reconciler query; it never constructs `DispatchOutbox` or calls `deliver`. `git grep` at the fixed candidate finds no `DispatchOutbox` construction or `.deliver()` consumer, and finds complete `WorkerHostBridge`/router/ControllerAdapter/Reconciler assembly only under test support.

`FileBootstrapStore` is also a dead end: `DispatchOutbox.deliver` writes it at `dispatch_outbox.py:248-256`, but no source reads it. The tested Node callback instead retrieves the Run bearer independently through `WorkerHostBridge.receiver_bootstrap`. Enabling both leaves a redundant plaintext Run credential; using only the tested path bypasses the journal/query-before-PUT contract.

Impact: the one real child run proves Node → Child → Gate → result recovery. It does not prove Scheduler → durable Outbox → Supervisor, one-attempt journal semantics, or an installed product service.

Required closure: add the production runtime dispatcher/consumer, use exactly one restricted bootstrap path, drive the child scenario through `DispatchOutbox.deliver`, and prove query-before-PUT, one operation/launch and unknown-without-resend.

### 2. Important/P2 — process receipts do not bind the exact canonical harness profile

`execution/reconcile.py:65-99@e40e7e2` binds operation, RunIdentity, receiver, Assignment digest and process observation, but line 83 only checks `profile_id` is a string. It does not compare with the exact TaskDefinition `worker_profiles[assignment.work_kind]` ref/digest. Accepting any `assignment.profile_refs` member would also be wrong because model/runtime refs share that tuple.

The profile is not part of the P05 `ExecutionObservation` subsequently recorded, so a mismatched profile can disappear from authoritative process state. The actual test always supplies `assignment.profile_refs[0]` (`support/m2.py:293-296,363-367`) and has no mutation negative.

Required closure: derive the exact harness ref/digest from canonical TaskDefinition plus work kind, retain it in the registered-run binding, reject any different receipt profile before P05 observation, and add one mismatch negative.

### 3. Important/P2 — revoked trusted historical replay only replays an already accepted receipt

The test first calls `case.reconciler.reconcile(registered)` at `test_maf_child_transport.py:158`, storing the accepted P04 result. It revokes the Worker credential only at lines 225-231, then replays the already-final submission. It does not test retained output whose first controller intake occurs after Run/epoch revocation.

The source has no distinct settlement path. `WorkerHostBridge._original_writer` reconstructs the original Worker principal; `receiver_replay -> _submit -> PlatformWorkerHost.submit_result` uses ordinary `model_output`. P09 Worker ACL lacks `can_settle`, while P04 `run_disposition` requires settlement permission for a stale Run to become `historical_only`. A genuinely stale first intake is rejected; granting the Worker settlement permission would violate the boundary.

Normal Worker intake also has a revocation race: `_ready` checks the Run credential, then `_submit/_archive` writes through `model_output` without rechecking that credential at the write point.

Required closure: use a distinct registered-receiver settlement authority that binds exact retained bytes and yields `historical_only` without reopening execution. Test both normal Worker ready→revoke→write denial and receiver first intake after Run/epoch revocation. Do not broaden Worker ACL or weaken P04 disposition.

### 4. Important/P2 — start grant omits current receiver Pod UID

`ReceiverAuthorizer.authorize` builds expected receiver data and queries current `scheduler_receiver` at `dispatch_outbox.py:291-308@e40e7e2`. Start authorization checks row existence, environment and enabled state, but omits `registered_receiver.pod_uid == run.pod_uid`.

`WorkerHostBridge.await_start` checks this only later at `worker_bridge.py:254-260`, after Node start can already spawn the inert child. The actual test always uses the same synthetic UID.

Required closure: bind current receiver ID/runtime/subject/environment/Pod UID before issuing the start grant and add a mismatch negative proving no launch.

## Actual evidence coverage

The submitted `1 passed in 8.91s` genuinely exercises a P09-produced Assignment, real Node-spawned Python child, persisted P05 started barrier, two native model requests, one ToolGate workspace read, P03 evidence, P04 accepted result, 503-before-controller-intake retained bytes, later receiver replay and one process launch. The recorded Task remains running; result and process state are not presented as Task completion.

Source confirms Assignment/digest/Run identity are re-read, Worker waits for persisted start before importing MAF, Reconciler orders result persistence before process observation, unknown transport does not invent exit or resend, child env has no DB/Task signing key, and private request files are bounded/no-follow/immutable.

The single test does not cover the four findings, all receiver/credential mutations, first historical intake, stop settlement, all work kinds, Pod/Kubernetes, P08, full P10/P07 or production deployment. Its test listener, receiver credential issuer, receiver-access resolver, host factory and service assembly are fixtures and are not product capabilities.

## Focused re-review

Main accepted all four findings and assigned substantive fixes. Re-review should inspect their real production callers and one fixed candidate after Dirac's minimal affected integration; no old ten/P06 full rerun is required. Evidence must preserve `e40e7e2` history, distinguish product callers from fixtures, and retain full HTTP/PG/process observations.
