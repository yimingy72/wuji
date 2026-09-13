# vnext migration head

Current head: `vnext_0006_p05_control`, following the accepted P04 head
`vnext_0005_p04_input_freshness`. P05 owns `persistence/control_schema.py`, the
control extension of `UnitOfWork`, and `blackboard/result_state.py` plus the two
publication-transaction calls in P04 ResultCommitter. Original submission and
receipt rows remain authoritative; the migration reconstructs their Run
projection without inventing Task activation. Populated legacy generic criterion
references require an explicit mapping; the migration does not guess one.

P05 service ports (no Task/Work HTTP routes until P11):

- `ControlService(uow, artifacts=store).apply(ControlCommandContext(access,
  task_id, operation_id, command, work_item_id=None)) -> CommandReceipt` uses
  independent Task control_version / Work revision CAS and command namespaces.
- `record_observation(access, ExecutionObservation)` validates the complete
  stored-source receipt/digest, fixed RunIdentity, receiver/operation/environment/
  pod identity and process birth/exit fields. Observer ACL and controller/reconciler
  role are required; ordinary control and knowledge-write authority cannot submit
  these observations. P10 supplies actual Supervisor observations later.
- `reconcile(access, task_id, work_item_id)` and `refresh(...)` consume stored
  execution or input/dependency changes. `dispatchable(...)` is an informational
  read, never a permit. P09 repeats `can_dispatch(tx, work_row)` inside admission,
  including its Scope/Profile/limits checks and atomic Run/Outbox registration.
- `UnitOfWork.transaction(..., capability='control'|'observe'|'admit')` locks
  frozen task_capacity_pool refs in global/model key order, then tenant pools,
  before Task. ACLs are `can_control/can_observe/can_admit`; roles respectively
  operator/controller, controller/reconciler, scheduler/controller; Agent is
  excluded. New control writes must not reuse a Task-first knowledge transaction.
- `CapacityService.reserve(tx, run_id)` requires the registered current Run and
  rechecks Task/Work epochs, hold and reservation state. Stored observations drive
  release; `run_operation_settlement` and resource_reservation retain independent
  side-effect uncertainty. Pool limits and task definition/profile snapshots must
  be explicitly provisioned, with no guessed defaults.
- `DependencyService.add(access, task_id, work_id, WorkDependency)` reuses the
  Task-locked DAG. `criterion_ref` now uses `GoalCriterionRef(criterion_id,
  revision)`, with a real same-Task goal_criterion FK, never a knowledge alias.
- `project_submission(tx, run_id, submission_id)` is called only by P04's actual
  receive/reconcile transactions. `mark_missing_output(tx, run_id)` uses database
  CAS, no submission, trusted final stop/operation settlement and final_output
  expectation. Input boundaries remain separate. Application roles cannot update
  agent_run.result_state directly; receipt replay cannot regress accepted.
- SessionManifest/InputRequest/criterion judgment/completion decision tables are
  minimal canonical producer headers. P08/P12 extend these same tables and their
  publication/verification permissions; P05 provides no client write API or SDK
  recovery claim. Session recovery checks sealed objects, exact published pins,
  current access, Run/Work/version/lock identity and pending operations. Missing
  headers/objects block execution. `apply_completion(access, task_id, receipt_id)`
  requires controller + can_control and a P12-owned decision with exact control/
  board versions; it cannot manufacture a Goal judgment or a report.

P05 evidence and integration limitations are recorded in
`docs/vnext/evidence/P05/report.md`. The following describes the preserved P04/P03
foundation and its original evidence.

The fifth migration adds
`claim_input_current`, a scope/ACL-checked SECURITY DEFINER boolean over full
Claim version state. It requires the referenced fixed revision to be readable,
returns stale even when a newer revision is private, and never returns hidden
revision numbers, IDs or counts. Both Fact aggregation (Repeatable Read) and
ResultCommitter read_set admission (the existing Task-locked write transaction)
consume this shared boundary. No history or original reference is rewritten.

The preceding `vnext_0004_p04_assessment_visibility` follows P04 knowledge
head `vnext_0003_p04_knowledge` and both P03 heads below. The fourth migration
adds a fixed-search-path, scope/ACL-checked SECURITY DEFINER visibility guard.
It returns only whether all related assessments/actions/inputs are visible;
partial views uniformly return CAPABILITY_UNAVAILABLE. Fact reads use one
Repeatable Read transaction for this guard and aggregation; historical reads
also guard against exposing a misleading subset. No hidden row data is returned.
The same `migrate(connection, application_role=...)` advances only recognized
head sets and rejects unknown heads. P04 adds canonical knowledge actors,
Run writer bindings, explicit Task assessment-policy bindings, immutable
assessment actions, IntentRevision, and raw/final result receipts. Existing
P03 rows and evidence-authority mutation guards remain in place.

P04 service ports:

- `ClaimService(uow).propose(access, task_id, proposal, *, idempotency_key)` and
  `propose_intent(...)` return a `ComponentReceipt`.
- `AssessmentService(uow, store).record(access, task_id, command, *, idempotency_key)`
  returns an `AssessmentReceipt`; `invalidate(..., assessment_id, *, kind,
  reason, idempotency_key)` appends stale/retracted/disputed decisions.
- `FactLedger(uow).read(access, task_id, KnowledgeRef, *, snapshot_id=None)`
  returns the validated RecordView. Claim snapshots freeze policy/outcome and
  close over actual assessment inputs; current permissions are rechecked.
- `ResultCommitter(uow, store, claims).receive(access, envelope)` publishes raw
  receipt only; `.reconcile(access, task_id, submission_id)` completes local
  admission; `.lookup(...)` reads the current receipt; `.submit(...)` combines
  receive/reconcile. None reruns a model/tool.
- `ArtifactStore.stage_model_output(access, task_id, agent_run_id, bytes,
  media_type, *, access_level=0)` uses the same sealing, leases and publication
  pins as captures. It needs stored `run_writer` + `can_model_output` and a
  signed worker/supervisor identity, without granting capture. It accepts a Run
  with zero ToolAttempts; `seal` selects the correct mutation authority.
- Compose `create_knowledge_router(claims, assessments, committer)` and
  `create_records_router(ledger)` through P02 `create_app`. Results additionally
  require `Idempotency-Key == submission_id`.

Deployment must register actual actors/writers and explicitly bind each Task to
published `assessment-policy-v1`; application credentials cannot grant these
permissions. P05/P09 own WorkItem creation and lifecycle invalidation triggers;
P12/P13 own Goal/Topology integration. No seeded test parents prove those flows.

The following describes the preserved P03 foundation and its original checks.

`vnext_0002_p03_evidence_authority` advances the independent `vnext_0001_p03` base through
`wuji_core.persistence.schema.migrate(connection, application_role=...)`.
It does not import legacy migrations, start services, or migrate user data.
The schema owner must be a separate non-superuser, non-BYPASSRLS migration role;
the application role has scoped DML and no ownership/DDL/ACL-management rights.

The existing real fixture provides both required connection hooks:

```python
from wuji_core.persistence.schema import migrate

with db_environment.migration_connection() as migration:
    # The wrapper has already executed SET ROLE <isolated migration owner>.
    migrate(migration, application_role=db_environment.application_role)

# Each call opens a distinct nonowner connection and records SQL/results.
uow = UnitOfWork(db_environment.additional_app_connection)
```

Reapplying the same head is a no-op; an unknown head is rejected. The authority
upgrade adds only mutation guards and retains the base migration record. Artifact
sealing and lease writes require an evidence execution context plus a nonrevoked
stored collector binding. Actual-mutation triggers preserve the UPDATE visibility
needed for snapshot publication row locks. Deployment
must supply its own connection factory and configured storage root. This task
verifies local PostgreSQL 16.2, not a production image or production cutover.

## Canonical boundaries

- Task/WorkItem/AgentRun/ToolCall/ToolAttempt and collector bindings are the
  canonical parents. P05/P06 extend these tables. Capture never creates a
  missing parent. ToolCall preserves its provider call ID, lineage, message and
  definition-version key independently of a Run.
- ClaimRevision owns assertion text. The registry contains identity, revision
  and visibility only. Domain inserts register their revision in the same
  transaction; a deferred domain-existence check rejects phantom registry rows.
  The currently implemented registry kinds are artifact/observation/claim;
  other kinds require actual domain tables in a later migration.
- Assessment and typed input/relation tables preserve revision and composite
  tenant/project/task FKs. P04 owns assessment policy aggregation/Fact read
  views and business acceptance; this head does not expose a writable Fact.
- UnitOfWork resolves ACLs from signed server Principal context. Transaction-local
  settings isolate scope and capabilities; JWT roles alone do not grant Task
  access. Same-Task writes take Task before artifact/resource locks. Revision,
  counters, evidence receipt and Outbox commit atomically. Dependency insertion
  checks cycles under the Task lock. Future capacity locks must precede Task.
- `AccessContext(principal, request_id)` is an internal authenticated context,
  not a client DTO. A shared DB credential is trusted server infrastructure;
  tenant clients never receive it or supply SQL/GUC values.

## Bytes, manifests and retention

`ArtifactStore.stage` reserves a DB object and commit lease before writing actual
bounded bytes to a server-generated UUID path. `seal` checks digest and length.
Original capture envelopes remain immutable; Observation uses server receipt
time and includes every ordered ArtifactRef. `EvidenceReceipt` is the public
policy wrapper in `contracts.envelopes`; its generated base alone does not apply
OpenAPI's conditional status/reference constraint.

`SnapshotRepository.create(task_id, access, *, query=None)` commits fixed refs,
state, relationships, query/access digests and pins in a short Repeatable Read
transaction. Later pages reauthorize and read this manifest. `read_ref` returns
an internal domain row; P13 must validate its public RecordView and never expose
storage keys or raw internal rows. Expiration is `DomainError` with
410/SNAPSHOT_EXPIRED; public topology pagination remains P13.

Snapshots and observations are actual publication consumers. Common publication
refs and artifact leases protect bytes. GC additionally checks typed evidence
references; a fixed-search-path, scope-checked SECURITY DEFINER function sees
private pins that a lower-clearance maintainer cannot otherwise read. GC first
commits a tombstone, then unlinks/fsyncs and records body removal; interruptions
can retry cleanup. Tombstones retain identity/digest. No user-data purge or
production retention period is implemented. P08/P16 must reuse these interfaces
for Session/Report publication and approved retention.

## HTTP composition and focused validation

Compose `create_evidence_router(EvidenceService(uow, store))` through the existing
`create_app(token_verifier=..., routers=[...])`. This registers the production
capture route and authorized byte stream route. Capture requires a signed
collector plus stored attempt binding; `Idempotency-Key` must equal capture_id.
A started old attempt can produce historical_only only with settlement authority.
The async capture route reads the original request body, then offloads the entire
synchronous ingestion transaction through Starlette run_in_threadpool; connection
creation, use and commit stay together. The response is validated before
DecimalJSONResponse; content uses
StreamingResponse with Digest, attachment, no-store and nosniff headers.

```sh
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_p03_contracts.py tests/vnext/test_rls.py tests/vnext/test_capture_transactions.py -q
work/toolchain/bin/pnpm contracts:check:v2
```

The fixtures seed explicit SQL prerequisites and use real temporary bytes,
signed test tokens, production services/routes and isolated PostgreSQL. Seeded
Run/start receipts are not evidence of Supervisor/admission integration. Full
assessment, SDK/import, topology HTTP and Session restoration AC portions remain
with their owning tasks. See `docs/vnext/evidence/P03/report.md` for actual results.
