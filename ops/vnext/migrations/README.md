# vnext migration head

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
