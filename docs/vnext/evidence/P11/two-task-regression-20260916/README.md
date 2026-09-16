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

## 3. What is still missing (next defect, with its evidence)

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

- No two-Pod concurrency, no cancel of one Task while the other runs, and no new-start dispatch for a second Task
  are demonstrated here; the unit tests cover the restriction logic, not the live pair.
- 43 vNext tests (remote workspace + run admission) plus 35 earlier ones cover the code changed here; the failing
  live attempt above is kept rather than retried away.
