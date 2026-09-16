# Two-Task runtime host · live attempt and what it still needs (2026-09-16)

- Revisions: `f16fa69` (multi-Task host), `b9e3e88`-series (image/module fix), `2d9a4c5`-series (gates merge),
  `e0c5a0f`-series (per-Task gate executors); the last roll used platform
  `127.0.0.1:56615/wuji-vnext-platform@sha256:5b037d5b…`, agent `…agent@sha256:6e134574…`,
  kali `…kali@sha256:05aa1b15…`.
- Tasks: A `86a2a7f2-1c60-4fc7-82d1-748a26fcd6e4`, B `3aa77fba-c264-4f79-8223-a656ffd53a37`
  (B was created and deliberately left un-started).
- Fixture: fixed synthetic model, harmless read-only `workspace-read-v1` tool.

## 1. What the live run proved

| Claim | Evidence |
| --- | --- |
| the runtime host serves a bounded Task *list* | `runtime-config.json` carries `task_ids: [60e7bd1b…, 86a2a7f2…]` and `pod_runtime.tasks` with both entries; the legacy `task_config`/`receiver` keys are gone |
| one Task's not-ready environment no longer stops the loop | `runtime-environment.txt`: every cycle logs one `runtime_pod_environment` line **per Task** (`task_id`, `state=stopped`, `reason=permit_revoked`) and then still runs `runtime_dispatch_cycle` |
| the gate host serves several Tasks | `gates-config.json` carries two executor entries with distinct Task identity and the deployment's own `collector_subject`/`gate_subject`; `pods.txt` shows `gates` **2/2 Running** |
| the launcher merges instead of replacing | `runtime-config.json`/`gates-config.json` keep the earlier Task's entry while adding this one; a second identical run reports `unchanged` |

## 2. Defects the live run found, and their fixes

1. **The platform image did not ship the new parser.** `ops/vnext/images/Dockerfile` copies `ops/vnext` files
   explicitly, so `pod_task_config.py` was missing and `runtime` crash-looped with `ModuleNotFoundError`.
   Fixed by adding it to the image.
2. **A new gate executor entry invented the deployment binding.** Appending the second Task built its binding
   from the launch identifiers alone, so `collector_subject`/`gate_subject` were absent and `gates` crash-looped
   (`ExecutorDeploymentBinding.__init__() missing 2 required keyword-only arguments`). A new entry now clones the
   deployment's own binding, a missing field is repaired from the entries that have it, and entries that disagree
   are refused as `INPUT_DIGEST_CONFLICT` (`merge_gates_executors`, covered by `tests/vnext/test_task_launch.py`).
3. **Two Tasks share one `executor_ref`.** The gate host keyed executors by `executor_ref` alone and refused the
   second Task (`duplicate deployment executor`). It now keys both the remote executor and its collector access by
   `(tenant, project, task, executor_ref)` for invoke/query/cancel/capture; fixtures follow
   (`test_remote_workspace.py` + `test_run_admission.py`, 43 passed).

```text
ERROR:    Error loading ASGI app factory: ExecutorDeploymentBinding.__init__() missing 2 required keyword-only arguments: 'collector_subject' and 'gate_subject'
ValueError: duplicate deployment executor
```

## 3. The two-Task run, and cancelling one without stopping the other (2026-09-16 07:26–07:31 UTC)

Task A's attempt had already spent its window, so the run was repeated with two **fresh** Tasks:
B `3aa77fba…` and C `6ffd59cd…`, launched back to back through the same owner command
(`raw/launch-B.log`, `raw/launch-C.log`, both `SuccessCriteriaMet|1|`).

```http
POST /api/v2/tasks/{task_id}/commands HTTP/1.1
Host: 127.0.0.1:18455 (kubectl -n wuji-vnext-test port-forward svc/runtime 18455:8443)
Authorization: Bearer <operator JWT>
Idempotency-Key: cancel-6ffd59cd-2f11-49ad-a0bc-60328fd1e538-two-task-C
Content-Type: application/json

{"command":"cancel","expected_version":"2","reason":"stage B branch 3: cancel while work is in flight","schema_version":"wuji.api.v2"}
```

```http
HTTP/1.1 202
{"command_id":"cancel-6ffd59cd-…-two-task-C","disposition":"accepted","resource_ref":{"entity_type":"task","id":"6ffd59cd-…","revision":"3"},"resource_version":"3","request_id":"66e61886-861b-46a0-a752-05db1315ab78","code":null}
```

Before the cancel both Task Pods were running **at the same time**:

```text
wuji-task-v-2749e0c5bdd0fb10bb8e78e3b7a0c061-a1   2/2   Running   0     12m     # Task B
wuji-task-v-46cb40c00cc4ee69af35b1036ae21390-a1   2/2   Running   0     4m41s   # Task C
```

After it (`raw/after-cancel-pods.txt`, `raw/after-cancel-tasks.txt`, `raw/after-cancel-capacity.txt`):

```text
wuji-task-v-2749e0c5bdd0fb10bb8e78e3b7a0c061-a1   2/2   Running   0     23m     # Task B, untouched
wuji-task-v-46cb40c00cc4ee69af35b1036ae21390-a1   (deleted)                      # Task C's Pod

3aa77fba|run|running|t|            # Task B: still runnable
6ffd59cd|cancel|quiescing|f|user_cancel

3aa77fba|released|6                # Task B capacity, released exactly once
6ffd59cd|released|6                # Task C capacity, released exactly once
```

The runtime loop kept cycling while reporting the stopped Tasks one by one, and never reported Task B:

```text
{"event": "runtime_pod_environment", "pod_name": "…b9070a1a…", "reason": "permit_revoked", "state": "stopped", "task_id": "60e7bd1b-…"}
{"event": "runtime_pod_environment", "pod_name": "…46cb40c0…", "reason": "permit_revoked", "state": "stopped", "task_id": "6ffd59cd-…"}
{"event": "runtime_pod_environment", "pod_name": "…98ce2d5e…", "reason": "permit_revoked", "state": "stopped", "task_id": "86a2a7f2-…"}
```

Both Tasks did their work before the cancel (`raw/two-task-work-items.txt`, `raw/two-task-runs.txt`): each shows
`reason|done` with an accepted result written by its own Run, and `explore|failed|process_failure` settling
through the platform's closed-operation-set basis.

## 4. The attempt-window hazard behind that (still open)

Task A's retry could never create a Pod:

```text
SELECT activated_at, now()-activated_at: 2026-09-16 06:09:13+00 | 00:58:32
runtime limits max_elapsed_seconds: 1800
```

The permit's `expires_at` is `min(authorization_expires_at, activated_at + max_elapsed_seconds)`, so once a
launch has been activated and then fails after `wire`, the attempt's 30-minute window keeps running and the retry
is refused by an expired permit — `permit_revoked`, hence `POD_NOT_READY` forever. The definition digest and the
persisted `task.started` event still match, so this is purely the elapsed window. A launch retry therefore needs
to roll to a **new runtime attempt** (fresh activation and binding), which the owner command does not do yet;
that is the next fix. It is unrelated to multi-Task hosting, and the run above avoided it by using fresh Tasks.

### 4.1 The refusal now names its predicate (commit `7194df2`, live)

`PermitDenied` carries a bounded lowercase code, the runtime keeps it on the observation, and the loop logs it
beside `reason=permit_revoked`. After rolling the image, the four Tasks in this cluster reported:

```text
60e7bd1b|stopped|permit_revoked|permit_expired      # window closed
86a2a7f2|stopped|permit_revoked|permit_expired      # the retry that could never start
3aa77fba|stopped|permit_revoked|permit_expired      # finished its work, window closed after
6ffd59cd|stopped|permit_revoked|task_not_runnable    # cancelled by the operator
```

(raw: `raw/runtime-permit-codes.txt`; the loop kept cycling in the same tail.) An operator can now tell an
expired attempt window from a cancelled Task or a binding mismatch without reading the database, and messages
stay internal (only the code and the fixed `reason` vocabulary are printed).

## 5. What is still missing

The two Task *Pods* never ran side by side. Task A's attempt is stuck:

```text
86a2a7f2-1c60-4fc7-82d1-748a26fcd6e4|run|running|2|t          # task: runnable
86a2a7f2-1c60-4fc7-82d1-748a26fcd6e4|1|task-86a2a7f2-…-a1|f    # its receiver row: enabled=false
{"event": "runtime_pod_environment", "pod_name": "wuji-task-v-98ce2d5e…-a1", "reason": "permit_revoked", "state": "stopped", "task_id": "86a2a7f2-1c60-4fc7-82d1-748a26fcd6e4"}
DomainError: POD_NOT_READY
```

The first launch attempt failed *after* `wire` (gates rollout wait). That left the attempt's
`scheduler_receiver.enabled=false` and no Task Pod. A launch retry then waits for a Pod that the runtime will not
create, because the revoked permit is what denies it — a launch-retry hazard independent of the multi-Task work.
The fix belongs in the attempt lifecycle (re-publishing the receiver before the Pod wait, or letting the runtime
recreate the Pod for the current attempt when the platform re-enables the receiver), not in the Task list.
Task B stays `pause/ready` with no receiver row, so nothing was fabricated for it.

## 4. Limits

- Two-Pod concurrency and the cancel of one Task while the other keeps its Pod are demonstrated in §3. A *new
  start* delivered to a second Task while the first is stopped is not: both fixtures finish their work within
  seconds of the Pod becoming ready, so the restriction is covered by unit tests rather than by a live dispatch.
- 43 vNext tests (remote workspace + run admission) plus 35 earlier ones cover the code changed here; the failing
  live attempt above is kept rather than retried away.
