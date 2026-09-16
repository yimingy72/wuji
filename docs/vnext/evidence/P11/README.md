# P11 evidence index

- [Task creation entry](task-creation-20260915/README.md): `POST /api/v2/tasks`, migration
  `vnext_0019_p11_task_creation`, published-profile catalog, real K8s 201/idempotent replay/409 and the
  created Task rows.
- [Task admission and control commands](task-admission-control-20260915/README.md): owner-side
  `publish_task_admission`, the same Task accepting `start`/`pause`/`cancel` through the runtime control
  API, with `runs=0` explicitly stated (no process-stop claim).

- [Pod-level cancel stop](pod-stop-20260915/README.md): the real Task Pod (new agent/kali digests)
  deleted within 5 s of an accepted `cancel`, with `reconciling` kept and no fabricated exit
  observation; also records the expired-token/image-roll environment work and the open
  worker-assignment dispatch finding.

- [Stage B branch 1 round trip](stage-b-roundtrip-20260916/README.md): a Task created through the
  public route reaching an accepted result and a real exit on the fixed `9e5bfb6` images, including the
  refused tool call whose bounded code the child now names, and the buffered-response defect that the
  first run of the branch exposed.

- [Two-Task runtime host](two-task-regression-20260916/README.md): the runtime host serving a bounded Task
  list, per-Task gate executors and per-Task environment reporting, plus the three defects the live attempt
  found and the launch-retry hazard that still blocks two concurrent Task Pods.

- [Attempt credential expiry](attempt-credential-expiry-20260916/README.md): Task A attempt 2 的第三个 Run 在
  receiver bearer 到期（`2026-09-16T09:29:23Z`）之后派发，三次 401 用尽投递预算后停在 `registered`，
  并因 `attempt_has_unsettled_run` 锁死滚动；含 bearer 注册声明、投递日志与数据库事实。

- [attempt 3 recovery](attempt3-recovery-20260916/README.md): attempt 2 的孤儿 Run 按平台环境证据结算
  （`environment_stopped`），刷新凭据并滚动到 attempt 3 后，新 Run 真实投递（`PUT 200`）、执行并退出，
  窗口内 0 次 401/URLError；同一 Run 的 child 仍以 `native root exceeds the fixed object bound` 失败，
  作为下一个缺陷保留。

- [History bound fix](history-bound-fix-20260916/README.md): 发布 `harness.*.deployment.v2` 把 Session 对象上限
  从固定 16 KiB 改为由准入限额派生（32 KiB / 128 KiB），并让越界错误点名 root 与字节数；新 Task 的 `reason`
  路径因此产出 **accepted** 结果并 `done`，`explore` 仍保留已知的 `LIMIT_BLOCKED` 失败。

Still open: owner tooling that derives admission rows from deployment configuration, a runtime attempt
that carries no worker-assignment dispatch finding, Stage B branches 2 and 3 on their own fixtures, and
the multi-Task runtime host that would prove one Task is not stopped with another.
