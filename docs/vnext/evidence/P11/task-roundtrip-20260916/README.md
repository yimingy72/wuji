# P11-C: a Task created through the product entry reaches a real MAF round trip — 2026-09-16

Status: **verified for the isolated local slice.** A Task created by `POST /api/v2/tasks` was taken
by the owner command through `prepare → activate → wire → capability`, the scheduler admitted its
`reason` work, the Task Pod ran the real MAF child against the model and tool gates, and the run
submitted a result the platform accepted. The `explore` work of the same attempt hit the deployed
tool-call limit and is left `reconciling / operations_unsettled`; that is an open defect, not a pass.

Scope: local Docker Desktop Kubernetes (`wuji-vnext-test`), real isolated PostgreSQL
(`wuji_vnext_ui_20260915`), synthetic loopback model, one Task at a time. This package does **not**
accept P11, P12, Pod/K8s hardening, multi-Task concurrency or production identity.

- tested code: `9eb1a8a` (`codex/vnext-maf`), platform image
  `127.0.0.1:56615/wuji-vnext-platform@sha256:0b73edf628211da7940bb99002957492143241d4d5f5366277d6f43c764e502d`,
  agent `…wuji-vnext-agent@sha256:7878cfba…`, kali `…wuji-vnext-kali@sha256:97a5189b…`
- Task `ea03c0f8-0f77-4f50-88d4-7225d31b0a2a`, attempt 1, execution epoch 2, definition digest
  `765a5ff9d8729fed958831843b3cb3a5deaad8315e140cd1a7c13a3d68240468`
- Task Pod `wuji-task-v-b2a80dafb0b1f257f1603abb1fdc632b-a1` uid
  `41e5d0af-fd13-4e2a-94ee-c4b9ce513fc6`

![created Task, launch phases, PostgreSQL state, gate traffic and child launches](screenshots/p11c-roundtrip.png)

## 1. What the run proves

| Step | Observed evidence |
| --- | --- |
| product creation entry | `POST /api/v2/tasks` → `201`, revision 1, `desired=pause`, `observed=ready` (`raw/create.headers`, `raw/create.response.json`) |
| owner command | four phases in one idempotent run; `wire` wrote `runtime-config` (`task_ids`, `session_transport=true`), `profiles.json`, `gates-config` and the Task-owned objects (`raw/launch.log`) |
| runtime host | the child's `worker-host/await-start` and `worker-host/resolve` were answered from the frozen definition and the attempt's published Session profiles; the child reached `run_assignment` (`raw/child-launches.txt`) |
| scheduler | `reason` and `explore` work admitted for the created Task (`raw/work-items.txt`) |
| real MAF child | `reason` run `e500c775-…`: 2 model calls, 1 tool call, exited at `03:10:35.963` (`raw/agent-runs.txt`, `raw/model-calls.txt`, `raw/tool-calls.txt`) |
| gates | `POST /internal/v2/model/chat/completions 200`, `POST /internal/v2/executors/kali-workspace-v1/permits/check 200`, `POST /internal/v2/tool-calls 200` (`raw/gates-access.txt`) |
| accepted result | result submission `maf-m1:374b32d9…` state `received`, run `result_state=accepted`, work item `reason` → `done` (`raw/result-submissions.txt`, `raw/work-items.txt`) |

## 2. Complete reproduction packet

### 2.1 Create the Task (operator bearer minted from the deployment identity)

```http
POST /api/v2/tasks HTTP/1.1
Host: 127.0.0.1:18454 (kubectl port-forward svc/api 18454:8443)
Authorization: Bearer <operator JWT: iss=https://identity.wuji-vnext-test.invalid,
  aud=wuji-vnext-deployment, sub=operator, roles=[operator], tenant=1fc6b1f3-…, ttl 900s>
Idempotency-Key: operator|p11c-roundtrip-20260916|<random>
Content-Type: application/json
```

```json
{"authorization_expires_at":"2099-01-01T00:00:00Z","authorization_scope":[{"host":"fixture.invalid","port":443,"protocol":"https"}],"budget":{"amount":"1","currency":"USD"},"goal":{"criteria":[{"allowed_methods":["deterministic"],"condition":"version captured","criterion_id":"version","evidence_requirements":["sealed bytes"],"object":"fixture bytes","required":true,"responsible_party":"fixture-checker"}],"text":"Read the isolated workspace version file"},"model_profile_ref":"k8s-model-v1","name":"P11-C round trip probe 2026-09-16","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","runtime_profile_ref":"k8s-runtime-v1","scenario":"web_single","schema_version":"wuji.api.v2"}
```

```http
HTTP/1.1 201
date: Wed, 16 Sep 2026 03:09:16 GMT
server: uvicorn
content-length: 409
content-type: application/json
x-request-id: 66ca629e-8764-4976-8708-c9f2f64e0942
```

```json
{"task_id":"ea03c0f8-0f77-4f50-88d4-7225d31b0a2a","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","version":"1","name":"P11-C round trip probe 2026-09-16","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

The verbatim pair is in [`raw/create.headers`](raw/create.headers) and
[`raw/create.response.json`](raw/create.response.json); the request body, the idempotency key and the
task id are in [`raw/create.request.json`](raw/create.request.json),
[`raw/idempotency-key.txt`](raw/idempotency-key.txt) and [`raw/task-id.txt`](raw/task-id.txt).

### 2.2 One owner command takes the Task to a running attempt

```bash
scripts/vnext/uv.sh run --frozen python ops/vnext/task_launch.py --submit \
  --task ea03c0f8-0f77-4f50-88d4-7225d31b0a2a \
  --image 127.0.0.1:56615/wuji-vnext-platform@sha256:0b73edf6… \
  --agent-image 127.0.0.1:56615/wuji-vnext-agent@sha256:7878cfba… \
  --kali-image 127.0.0.1:56615/wuji-vnext-kali@sha256:97a5189b…
# TASK_LAUNCH_JOB_STATUS SuccessCriteriaMet|1|
```

The complete four-phase JSON and the persisted binding are in [`raw/launch.log`](raw/launch.log).
The attempt's deployment binding that `wire` wrote is in [`raw/runtime-config.txt`](raw/runtime-config.txt)
and [`raw/runtime-profiles.txt`](raw/runtime-profiles.txt).

## 3. Defects found and closed while making this work

Every one of these surfaced only in the live slice; the source reviews could not see them.

| # | Symptom observed in the run | Cause | Fix |
| --- | --- | --- | --- |
| 1 | child stopped at `step=load_context`, `code=CAPABILITY_UNAVAILABLE` | the Task definition froze `wuji.harness.session.v1` profiles but `wire` only refreshed `deployment.json`; the runtime host still held the older published profile set, and `session_transport` was never enabled | `wire` publishes the attempt's exact Session profile snapshots and requires `session_transport: true` (`adb4a4c`) |
| 2 | child stopped at `step=run_assignment` with no reason at all | the bounded stderr line named the phase but not the failure, and raw text could not be logged | the line now carries the exception class, and the exact traceback goes to an owner-only `child-error.txt` inside the Task Pod (`a3068ae`) |
| 3 | `installed MAF release/lock does not match published profile` | the Task was created from a published runtime profile naming a lock the shipped worker does not have; only the child could notice, after the model gate had accepted the attempt | the command measures `packages/maf-worker/uv.lock` from its own build and refuses with `INPUT_DIGEST_CONFLICT` before activation (`4357959`); the isolated catalogue was re-published as `k8s-runtime-v1` revision 2 with the shipped digest |
| 4 | `ChatClientException(APIConnectionError)` on the first model call, gate accepted nothing | `wire` rolled `runtime` before `gates`, and `wait_for_rollout` returned on the Deployment status that still described the previous ReplicaSet, so the child called a gate whose Pod did not exist yet | the gate is rolled first, and the wait now requires the observed generation, no remaining old Pod and the desired available replicas (`33dea4b`, `9eb1a8a`) |
| 5 | a launch failed permanently with `CAPABILITY_UNAVAILABLE` in `publish_capabilities` | the capability phase demanded that the attempt had registered its receiver, but registration follows the controller cycle that creates the Pod | bounded 120 s retry while the code is `CAPABILITY_UNAVAILABLE`; every other refusal still fails immediately (`33dea4b`) |

A sixth, smaller change belongs to the same diagnostic theme: `WorkerHostBridge.resolve` now emits
`{"event": "worker_resolve_refused", "step": …, "code": …}` (its `CAPABILITY_UNAVAILABLE` can come
from three different predicates), which is what turned defect 1 from a guess into a fact (`a921fdc`).

## 4. Open defects (not closed here)

1. **A refused tool call does not settle the work.** The `explore` run's tool call was answered
   `429 Too Many Requests`; the harness raised, the child exited, and the work item is left
   `reconciling / operations_unsettled` with no terminal reason (`raw/work-items.txt`,
   `raw/gates-access.txt`). A run that ends without any settlement must still reach a bounded
   terminal reason so the Scheduler can re-admit or fail it.
2. **A run that makes no tool call never settles** (carried from the previous package): the
   operation settlement row is written by the tool-admission path only.
3. **Single-Task slice.** `task-agent`/`task-kali`, the runtime `pod_runtime` and the gates executor
   binding still serve one Task at a time; multi-Task concurrency is unchanged.
4. **Capacity sizing.** The three pools were raised to capacity 4 for this harness because earlier
   probe Tasks cannot release their reservations without a real exit observation.
5. **Catalogue discipline.** The isolated catalogue had to be re-published by hand after the worker
   lock changed. A deployment should publish its runtime profile in the same step that builds the
   worker image, otherwise every Task created in between is unusable.

## 5. Validation performed

```text
tests/vnext/test_task_launch.py        6 passed  (245.06s)   on 33dea4b
tests/vnext/test_maf_child_transport.py 12 passed (41.47s)   on a3068ae
tests/vnext/test_task_creation.py + test_task_launch.py 10 passed (7.64s) on 4357959
```

The live run above is the verification for the deployment-side changes; no unit test can observe a
ReplicaSet that does not exist yet.

## 6. Raw material

`raw/create.request.json`, `raw/create.headers`, `raw/create.response.json`, `raw/idempotency-key.txt`,
`raw/task-id.txt`, `raw/launch.log`, `raw/work-items.txt`, `raw/agent-runs.txt`, `raw/model-calls.txt`,
`raw/tool-calls.txt`, `raw/result-submissions.txt`, `raw/gates-access.txt`, `raw/runtime-config.txt`,
`raw/runtime-profiles.txt`, `raw/task-pod.txt`, `raw/child-launches.txt`.
