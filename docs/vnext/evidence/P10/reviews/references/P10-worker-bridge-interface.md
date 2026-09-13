# P10 same-Worker bridge: source interface for Dirac

2026-09-13. Implementation handoff, not test evidence. M1 baseline is
`5cfd581`; preserve its TokenVerifier, native wire and complete raw binding.
Core owns only new files:

- `packages/wuji-core/src/wuji_core/execution/worker_bridge.py`
- `packages/wuji-core/src/wuji_core/http/worker_host.py`
- `packages/maf-worker/src/wuji_maf_worker/remote_host.py`
- `packages/maf-worker/src/wuji_maf_worker/child_entrypoint.py`
- `services/maf-supervisor/controller-adapter.mjs`

No edits to existing Node/bootstrap/dispatch/runtime/host, P09, schema, snapshots,
P13/UI or locks. Any subsequently necessary existing-file change goes to main.
Dirac owns OpenAPI additions/generated types, first RED, all checks/fixes and
evidence. First RED may simply import missing `WorkerHostBridge` (no DB).
After that RED core starts these owned files without another main gate.

## Python assembly

`WorkerHostBridge(uow, registry, credentials, receiver_access, host_factory,
context_builder, ledger, child_config, spool_directory)` lives controller-side.
`receiver_access(assignment)` returns a deployment-owned registered receiver
AccessContext, never an actor-supplied principal. `host_factory(access)` returns
the actual PlatformWorkerHost for the authenticated Worker. `context_builder`
is the existing pure `build_context_bundle`, wrapped by deployment to accept
`records, read_set, snapshot_id, max_records, max_bytes, relations` (plain refs
and relation dictionaries); it introduces no MAF type import into Core.
Bridge loads every record itself through actual SnapshotRepository and the
existing ledger RecordView reader, and supplies frozen profile limits. No
caller-provided context or empty-context substitute.

`create_worker_host_router(bridge)` uses the existing create_app/TokenVerifier
and strict JSON boundary. `bridge.await_start(access, assignment)` is a bounded
single read returning wait/ready/revoked. It authenticates the same Run binding,
re-reads actual P09 registration and current P05 Task/Work/Run plus the stored
execution_observation source; ready requires exact actual birth and persisted
started/running observation. It never records observations or starts execution.

`RemoteWorkerHost(origin, run_credential, token_verifier, receiver,
spool_directory, timeout=10, max_transport_bytes=...)` provides existing
resolve/archive_sdk/submit_result, plus async `await_start(assignment,
timeout=..., poll_interval=...)`, `load_context(assignment)` and sync
`replay(assignment)`. Polling is bounded/cancellable and only the permission
read is repeated. Result/archive request bytes are durably retained before
HTTP; uncertain submission never re-enters the SDK. Replay sends the exact
saved request, returning the real P04 ResultReceipt. HTTP is HTTPS or loopback,
fixed origin, no proxy/redirect/retry, explicit byte and time bounds.

Registered launch is `python -m wuji_maf_worker.child_entrypoint`, with only
Node's existing assignment/bootstrap directory environment variables plus an
explicit deployment environment allowlist. The child reads `bridge.json`
(Run bearer, public verification PEM/issuer/audience, fixed Gate/Host URLs,
receiver identity and bounded transport/wait configuration). It validates
assignment/digest/receiver, constructs actual TokenVerifier, awaits admission,
loads authorized context, and calls existing `run_assignment` once. No DB,
Task key, arbitrary factory/command or signing/decryption key enters child.

`ControllerAdapter({origin, authorization, receiver, timeoutMs,
maxResponseBytes})` exports `authorize` and `bootstrap` callbacks accepted by
the unchanged NodeSupervisor. It retrieves real bootstrap over receiver
authenticated HTTP, matches complete assignment/digest/receiver, and writes
0600 `bridge.json` durably in Node's existing worker directory. `mafProfile`
helper creates only the registered Python module argv from deployment inputs.

## Minimal OpenAPI v2 intent (SOL owns generation)

All new DTOs are generated in existing `contracts.generated`, extra fields
forbidden. Existing references retain their published constraints. No new
token purpose, ACL, DDL, public start or execution-bypass endpoint.

Routes (all POST under `/internal/v2/worker-host/`, no public route):

| Suffix | Request schema | Response |
|---|---|---|
| await-start | WorkerBridgeRequest | WorkerStartPermission |
| resolve | WorkerBridgeRequest | WorkerResolvedContext |
| archive-sdk | WorkerArchiveRequest | existing BlobRef |
| submit-result | WorkerSubmitRequest | existing ResultReceipt |
| replay | WorkerSubmitRequest | existing ResultReceipt (same exact payload) |
| receiver-authorize | ReceiverBridgeRequest | ReceiverBridgeGrant |
| receiver-bootstrap | WorkerBridgeRequest | WorkerBootstrap |

Schema fields (required unless stated nullable; all strings bounded):

- `WorkerBridgeRequest`: `assignment: WorkerAssignment`.
- `WorkerReceiver`: receiver_id (1..256), runtime_attempt (existing Revision),
  environment_ref (1..256), pod_uid (1..256).
- `WorkerStartPermission`: status enum wait/ready/revoked; identity RunIdentity;
  start_operation_id (1..256); assignment_digest SHA256; receiver WorkerReceiver;
  birth_id nullable (1..1024); observation_id nullable (1..256);
  source_digest nullable SHA256; valid_until RFC3339. Ready requires nonnull
  birth/observation/source. It is a read observation, never caller authority.
- `WorkerContext`: snapshot_id (1..256), read_set and record_refs arrays of
  KnowledgeRef (max 5000), text (max 16777216 chars), input_digest SHA256.
- `WorkerResolvedContext`: context WorkerContext; resolved object (the current
  internal PlatformWorkerHost resolve document, existing published profile,
  client_model, ExecutionLimits, request_timeout_seconds, tools and
  session_lineage; no extra deployment/secret fields); assignment_digest SHA256.
- `WorkerArchiveRequest`: assignment WorkerAssignment, sdk_output_base64
  (max 22369624 chars), sdk_digest SHA256.
- `WorkerSubmitRequest`: assignment WorkerAssignment, context WorkerContext,
  raw_output_base64 and sdk_output_base64 (each max 22369624 chars), raw_digest
  and sdk_digest SHA256, tool_receipts array of existing ToolCallReceipt
  (max 10000). Decoded byte limits additionally use the frozen Assignment.
- `ReceiverBridgeRequest`: assignment WorkerAssignment, assignment_digest
  SHA256, receiver WorkerReceiver, action enum query/start/stop/stop_after_current,
  control_operation_id nullable (1..256).
- `ReceiverBridgeGrant`: identity RunIdentity, assignment_digest SHA256,
  receiver WorkerReceiver, action same enum, subject (1..256),
  execution_allowed boolean, valid_until RFC3339. Produced only by actual
  ReceiverAuthorizer under authenticated registered receiver access.
- `WorkerBootstrap`: assignment WorkerAssignment, assignment_digest SHA256,
  receiver WorkerReceiver, run_credential (1..16384, sensitive/writeOnly where
  appropriate), public_key_pem (1..16384), issuer and audience (1..2048),
  host_origin/model_gate_url/tool_gate_url (1..2048 each),
  wait_timeout_seconds (integer 1..300), transport_timeout_seconds
  (integer 1..60), max_transport_bytes (integer 1..67108864).

Use bounded explicit resolved nested schema or current published DTO references
where already available; do not create an independent Pydantic wire copy.
Raw base64/digests preserve exact bytes. Controller retains exact authenticated
requests before P03/P04 processing; replay never fabricates successful receipts.
Late receipt reconciliation is receiver-only and must preserve original Worker
writer identity through existing authorized settlement ports; if that requires
an unavailable shared port, report it to main instead of elevating a Worker.

No tests/services/DB/formatters/generated checks run by core. Source commit is
CORE_WRITTEN_UNVERIFIED and transfers these source files to Dirac for checks
and subsequent fixes; M2 acceptance remains SOL's actual same-child evidence.

## Source transfer — 6e90a97

Core source-only commit: `6e90a97fa507717e4f8b06229ca1d2fc5e1593c4`.
Status **CORE_WRITTEN_UNVERIFIED**. Exactly the five listed new source files are
committed. Dirac now owns their code writes, all checks and routine fixes. Core
ran no test, import/compile probe, formatter, generated check, DB, HTTP/Node
service, SDK, K8s or paid model. Git hooks were disabled for the source commit
to avoid implicit checks. This is an assembly note, not a verification report.

Consume Dirac's generated `WorkerResolvedHost`/nested profile/tool DTOs and the
main-approved `receiver-replay`/`receiver-archive` routes. Existing Node's
`persistResults` hook is Dirac's separate change. It calls the adapter's bound
`persistResults({assignment,directory})`, where directory is the fixed worker
subdirectory. No pending-file result is `null`; rejected/unknown HTTP throws.
Result intake files are passed byte-for-byte through Node, without canonical
JS conversion of raw SDK/tool receipt numbers. Actual P03/P04 performs replay.

Deployment supplies the current pure context builder as a narrow adapter:

```python
from wuji_maf_worker.context import (
    ContextLimits, ContextRelation, build_context_bundle,
)
from wuji_core.contracts.knowledge import KnowledgeRef

def context_builder(*, records, read_set, snapshot_id, max_records, max_bytes,
                    relations):
    return build_context_bundle(
        records, read_set, snapshot_id=snapshot_id,
        limits=ContextLimits(max_records=max_records, max_bytes=max_bytes),
        relations=tuple(ContextRelation(
            source=KnowledgeRef.model_validate(item['source']),
            target=KnowledgeRef.model_validate(item['target']),
            relation=item['relation'],
        ) for item in relations),
    )
```

`ledger` is the actual `FactLedger` for Claim/Intent views. The bridge reads
Artifact/Observation rows using the actual authorized SnapshotRepository and
constructs the existing RecordView DTOs. It renders every frozen reference,
including relation endpoints; configured limits reject instead of truncating.
Core imports no MAF package. `host_factory(access)` must return the actual
PlatformWorkerHost with that exact Principal and controller-held services.
`receiver_access(value)` selects the trusted receiver by `value.identity` and
accepts either a WorkerAssignment or a RegisteredRun (the latter is used by
`bridge.reconcile_results`, the existing P10 Reconciler callback).

Create the private router with the existing create_app/TokenVerifier; configure
its existing `JsonBoundaryLimits.max_body_bytes` to the deployment's bounded
transport size when larger archives are required (the default remains 1 MiB).
Worker/Node/controller default/configured bounds are finite, at most 64 MiB
transport and 16 MiB decoded per raw/SDK object, further reduced by Assignment.

Node deployment composes `ControllerAdapter` and `mafProfile`, then passes its
bound `authorize`, `bootstrap`, `persistResults` to the existing Supervisor.
Its provided `authenticate` recognizes the configured actual service bearer;
the controller still performs real TokenVerifier and P09 receiver authorization.
Direct Node calls pass that bearer string as auth. `mafProfile` fixes argv to
`-m wuji_maf_worker.child_entrypoint` and restricts deployment environment keys;
it never copies the process environment. Bootstrap retains only the Run bearer
and public verification/config in 0600 Worker files. Controller intake retains
the verified Principal metadata, context and exact output requests, no bearer.

The actual child durably marks one entry to that Worker directory, waits on
server-derived permission, loads context and invokes the unchanged
`run_assignment`. HTTP has no retries/redirects/proxies and total deadlines.
Child error logs are generic; its original raw output stays in private files.
Receiver settlement derives its writer from controller's saved verified intake
and reuses existing run_writer/P03/P04 authorization. Revocation does not grant
new work; rejection at any existing settlement guard remains a real failure.

Production must isolate Worker directories from controller intake, other Runs
and guardian private launch data. The existing same-UID local Supervisor layout
does not prove that Pod filesystem boundary. Actual process/Scheduler/PG/SDK
and Pod integration remain SOL/main's checks; no M2 acceptance is asserted here.
