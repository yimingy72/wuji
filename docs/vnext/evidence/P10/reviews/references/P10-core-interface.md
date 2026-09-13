# P10 core assembly for Ptolemy SOL

2026-09-13. Interface handoff, not verification evidence. Owned implementation: new `services/maf-supervisor/{main,inbox,guardian,protocol}.mjs`, `execution/{dispatch_outbox,reconcile}.py`. No M1/P09/shared schema/wire/lock edits. First RED may import the missing `NodeSupervisor` below; after that RED core implementation is already authorized.

```js
import { NodeSupervisor } from './services/maf-supervisor/main.mjs';
const supervisor = await NodeSupervisor.open({
  inboxDir, // private durable directory; one OS SQLite-lock owner, no PID lease
  receiver: { receiver_id, runtime_attempt, environment_ref, pod_uid },
  profiles: {
    [profile_id]: { command, args, env, cwd, workKinds: ['explore'] },
  }, // deployment-only, fixed absolute command/cwd; env is an allowlist
  authorize: async ({ action, assignment, assignment_digest, receiver,
                      control_operation_id, auth }) => grant,
  // Optional trusted deployment hooks, never derived from HTTP input:
  bootstrap: async ({ assignment, directory }) => {},
  fault: async (window, { operation_id }) => {},
});
await supervisor.start({ start_operation_id, assignment, profile_id }, auth);
await supervisor.query(start_operation_id, auth);
await supervisor.control(start_operation_id, {
  control_operation_id, action: 'stop', identity: assignment.identity,
}, auth);
const server = supervisor.createServer({ authenticate: async (request) => auth });
server.listen(0, '127.0.0.1');
await supervisor.close(); // releases inbox owner only; does not assert Worker exit
```

`assignment` is the complete existing WorkerAssignment JSON; `start_operation_id === assignment.operation_id`, `profile_id` must occur in frozen `assignment.profile_refs`. No executable/path/env comes from Actor parameters. Receiver includes exact stable pod UID, even for a local harmless fixture environment. SQLite uses Node 24.20.0 built-in `node:sqlite`; no dependency/lock edits.

`grant` must be an object containing `identity` (exact assignment RunIdentity), `assignment_digest`, `receiver` (all four exact receiver fields), `action` (query/start/stop/stop_after_current), `subject` (authenticated service principal), `execution_allowed` (boolean), and `valid_until` (UTC timestamp). New start requires true execution permit; historical query/replay requires fresh read authorization, not permission to spawn. A bare boolean is rejected. The adapter is a trusted controller port, not a model-provided permission assertion. Production adapter must re-read real P09/P05 current rows; its absence blocks production dispatch. Grant checks repeat after bootstrap and immediately before irreversible spawn. Stop requires current controller authority for this historical Run; the controller adapter must distinguish current control authority from revoked Worker credentials.

HTTP (private transport, not generated product wire): `PUT /operations/{id}` accepts `{assignment,profile_id}`; `GET /operations/{id}`; `POST /operations/{id}/control` accepts the control object above. All routes authenticate before lookup/replay. Responses are private process receipts with `operation_id, identity, receiver, assignment_digest, profile_id, state, observation`. `state` is prepared/running/exited/not_started/unknown. `observation` is the **existing P05 ExecutionObservation** with full source bytes and digest; prepared has none. No result receipt/raw output/token appears in these replies. Unknown operation returns 404; absence is not proof of never started and Python must never turn query-404 after ambiguous delivery into another PUT.

Durability: commit prepared before OS spawn, keep immutable random launch identity and restricted per-launch guardian authentication key. An independent trusted Node guardian owns the actual ChildProcess handle, writes authenticated durable actual birth/exit records, and accepts authenticated control over a Unix socket. Restart never probes or kills a PID as identity proof; it challenges the same guardian or reads its signed exit record. Missing birth/guardian/exit proof becomes unknown, never another spawn. Bounded stdout/stderr files are private artifacts, not result receipts. Deployment must isolate guardian inbox/key from Worker filesystem access; local same-UID fixture is not proof of production sandboxing.

Fault hooks (core does not execute them): `before_prepared`, `after_prepared_before_spawn`, `after_spawn_before_running_receipt`, `after_running_before_response`. Third hook follows actual observed OS birth and precedes inbox running commit. Harness kills the independent Supervisor, restarts with the same receiver/inbox, queries and redelivers the original operation, counts actual fixture starts independently, and records actual exit. Second/third windows cannot be released merely because no PID is visible. `stop` stores intent before signaling; accepted never means exited. `stop_after_current` is explicitly rejected until real MAF cooperative control exists.

Python ports: `DispatchOutbox(uow, *, access, credentials, transport, profiles)` reads the real P09 DispatchRepository and opaque credential ref. `.deliver(task_id, operation_id)` first queries that operation, sends only on its initial absent receiver record, uses the original registered assignment, and queries after uncertain PUT without replacing the operation. `SupervisorHttpTransport` is the bounded authenticated private HTTP client. `.inspect(task_id,operation_id)` is query-only. `Reconciler(uow, *, access, control, transport, persist_results)` exposes `.inspect(run)->ObservedExecution` and `.reconcile(run)`; run carries exact registered identity/environment/pod/start_operation. Existing P05 observation source is validated and checked against the actual registered assignment digest. `persist_results` must durably reconcile existing M1 results before handing any observation to P05; callback does not supply process truth.

SOL owns all checks, routine fixes, screenshots/HTTP/process evidence. No core tests/formatting/DB/browser/K8s. Node-only checks may use private temp files/ports after CORE_READY. Actual P09/MAF/P05/Pod integration waits for main's shared window and is required for M2, not implied by harmless child success.

## Concrete source handoff

Node source-only commit `72d26a02308ab54db2c7c56b52f9861b8acdda82` is CORE_WRITTEN_UNVERIFIED and now owned by Ptolemy for checks/routine fixes. The four Node files are implemented as above. `profiles[id].env` is a fixed string-to-string object (no inherited parent environment); `workKinds` is required. Core adds only `WUJI_WORKER_ASSIGNMENT_FILE` and `WUJI_WORKER_BOOTSTRAP_DIRECTORY`. `fault` exceptions propagate from direct calls; HTTP maps non-domain failures to a generic 503. Guardian logs are bounded per stream (default 1 MiB) but always drained. Guardian private launch files/socket must not be mounted into production Worker; same-UID fixture does not establish this boundary.

Python final public assembly (overrides the shorthand constructor above):

```python
from wuji_core.execution.dispatch_outbox import (
    DispatchOutbox, DispatchJournal, FileBootstrapStore,
    SupervisorHttpTransport, ReceiverAuthorizer,
)
from wuji_core.execution.reconcile import Reconciler, RegisteredRun, ObservedExecution

transport = SupervisorHttpTransport(
    receiver_origin, authorization=receiver_service_bearer_resolver,
    timeout=10, max_response_bytes=65536,
)
sender = DispatchOutbox(
    uow, access=actual_receiver_access, credentials=actual_p09_issuer,
    transport=transport, profiles={'explore': frozen_harness_ref},
    journal_path=private_durable_sender_journal,
    bootstrap_store=FileBootstrapStore(private_receiver_bootstrap_spool),
)
observed = sender.deliver(task_id, original_operation_id)
reconciler = Reconciler(
    uow, access=actual_receiver_access, control=actual_p05_control,
    transport=transport, persist_results=reconcile_existing_actual_m1_output,
)
run = reconciler.registered(task_id=task_id, operation_id=original_operation_id)
observed = reconciler.reconcile(run)
sender.close()
```

`DispatchJournal` is private SQLite durability, not a new shared schema or execution fact source. It commits attempted BEFORE PUT; a crash before sending may therefore leave a conservative unresolved operation. On restart, only original-operation GET is allowed once attempted, including receiver 404. A fresh query timeout also forbids PUT. There is no reset flag, synthetic never-started receipt or replacement operation. Preserve this journal with the receiver inbox. Independent receiver idempotency still prevents duplicate spawn across sender instances. `FileBootstrapStore.stage` atomically stores exact identity/digest/real P09 Run bearer in a 0600 file keyed by SHA256(canonical identity); deployment bootstrap verifies it and writes the one Worker-readable credential. The returned file path never enters Outbox, argv or public receipt. Core supplies no default keys or auto-cleanup policy.

`ReceiverAuthorizer(uow).authorize(access=..., action=..., assignment=..., assignment_digest=..., receiver=..., control_operation_id=None)` is the real P09/P05 row consumer behind the Node callback. It rechecks the actual receiver subject, frozen assignment, environment/pod, current start epochs/Work/Task/hold/dependency/expiry/capacity. Historical query requires present observe authority; stop additionally requires P05 already durably revoked the Run. It does not install an HTTP router or grant an ACL. Main/SOL still owns private auth transport and receiver/pod producer.

`RegisteredRun` contains `identity`, `start_operation_id`, `environment_ref`, `pod_uid`, `assignment_digest`; `Reconciler.registered` reads it through actual P09 observe permission. `inspect(run)` reloads actual registration before network. `ObservedExecution` contains `run`, `state`, `observation`, `reason`, `source_receipt`. A network/404 unknown has observation=None; it does not invent a P05 receiver source or release capacity. A receiver's signed-process-derived unknown has a valid P05 source and may be recorded. Reconcile invokes actual existing-result persistence before P05 `record_observation` and `reconcile`; result status never supplies process state. No P05/P09 field or shared migration is changed.

Python core is source only, not executed. Missing `agent_run.pod_uid` explicitly raises `RECEIVER_ENVIRONMENT_UNBOUND`; existing P09 registration currently does not set it. Also actual child launcher must await P05 running admission before any MAF/model/tool request. These are main-owned M2 integration requirements, not code paths to satisfy with fabricated fixture flags.
