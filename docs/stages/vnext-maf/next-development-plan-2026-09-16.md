# vNext 当前任务队列 — 2026-09-16（attempt 凭据与孤儿 Run 收口）

- 状态：approved；队列第 1–5 项为本次诊断直接得出的修复项
- 整理日期：2026-09-16；实施工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`
- 基线：`89f7e0d`（本次证据提交）；队列开始前的最后代码提交 `34b7802`
- 权威来源：[Spec](../../vnext/SPEC.md)、[P00–P20 Plan](../../vnext/PLAN.md)、[验收状态](acceptance.md)、[实施决定](../../vnext/decision-register.md)
- 取代：[2026-09-15 计划](next-development-plan-2026-09-15.md) 的队列顺序（该文的 P15-L/P08-S/P11-C 交付事实继续有效）

## 1. 触发本次队列的实测结论

Task A attempt 2 的第三个 Run（`9e574eb0`）从未被投递成功：receiver bearer 在
`2026-09-16T09:29:23Z` 到期，而该 attempt 于 09:11 才启动并直接复制了这份 bearer；三次 `401` 用尽
`MAX_DELIVERY_SENDS` 后，Run 停在 `registered`、work item 停在 `leased`。attempt 窗口到期删除 Pod 后，
`roll_runtime_attempt` 又以 `attempt_has_unsettled_run` 拒绝滚动，Task A 进入硬死锁。

完整时间线、注册声明、投递日志与数据库事实见
[证据包](../../vnext/evidence/P11/attempt-credential-expiry-20260916/README.md)。该证据只描述失败，不构成通过。

## 2. 队列

1. **T1 attempt 凭据期限守卫。已交付（`9366098`）。** `ops/vnext/task_launch.py` 在 `prepare`（激活前）
   与 `wire` 两处解析挂载 bearer 的 `exp`，要求覆盖 attempt 窗口加 900 秒固定余量，否则以
   `receiver_bearer_expires_before_attempt_window` 拒绝；不可解析的 bearer 报 `receiver_bearer_unreadable`。
   真实 PostgreSQL 的 `tests/vnext/test_task_launch.py` 13 项通过（含新增用例）。
2. **T2 凭据刷新入库、可复现。未开始。** 把目前只存在于被忽略目录（`work/vnext/p11c/refresh-tokens.py`）的
   24h 重签变成仓库内命令：固定 TTL 上界、明确目标 Secret 清单、存在活跃 attempt 时拒绝执行，并写进运维
   文档。否则每次到期都要靠人工脚本，且脚本没有前置守卫。
3. **T3 supervisor 错误码有界化。已交付（`9366098`）。** 平台侧 `SupervisorHttpTransport` 不再把 401
   折叠为 `STALE_EXECUTION`：无标签的 401 报 `UNAUTHENTICATED`，maf-supervisor 自己的有界码
   （`UNAUTHENTICATED`/`CONTROLLER_REQUEST_REJECTED`）原样透出，其余未白名单码仍保守回落。
4. **T4 权威拒绝不消耗投递预算。已交付（`9366098`）。** `DispatchJournal.release_send` 让被接收方明确
   拒绝的发送归还预算（保留 `attempted` 单调标记），结果未知的发送仍受三次上限约束；
   `tests/vnext/test_maf_child_transport.py` 20 项通过（含两个新增用例）。
5. **T5 孤儿 Run 结算。已交付并实测（`3307a14`）。** 迁移 `vnext_0021_p05_environment_settlement` 让结果
   投影在"最后观察为 `environment_stopped` 且没有任何执行证据"时有界地写入 `incomplete`；
   `ControlService._settle` 对同一情形解除 `operations_unsettled` 保持并以
   `terminal_reason=environment_stopped_before_observation` 收口；runtime 只在 Pod 对象确认不存在时
   上报该证据。真实集群：attempt 2 的 `9e574eb0` 收口，Task 成功滚动到 attempt 3，随后新 Run 真实投递并
   执行（见[证据包](../../vnext/evidence/P11/attempt3-recovery-20260916/README.md)）。
6. **T6 会话边界导出超限。已交付并实测（`1ffb8a3` + `7ff1281`）。** Session 对象/总界限改为由准入限额派生
   （32 KiB / 128 KiB，仍封顶 64 KiB / 256 KiB），以新身份 `harness.<kind>.deployment.v2` 发布（runtime host
   与共享 ConfigMap 都拒绝同 ref 不同字节，已激活 Task 继续钉 v1）；越界错误点名 root 与两个字节数。真实 K8s：
   通过公开创建入口新建的 Task `083f6134-…` 首次 attempt 的 `reason` run `c3e30b1f` `exit_code=0`、无私有失败
   文件、结果回执 `accepted`、work `done`；同窗口 0 次 401/URLError。见
   [证据包](../../vnext/evidence/P11/history-bound-fix-20260916/README.md)。
7. **T7 并发只读。已交付并实测（`427882b`）。** 在途工具限额改为每 Run 计数；声明只读的工作区工具按 Run
   共享路径（`…:read:<run>`），只与裸路径独占者冲突，写者仍用裸键并排除读者。真实 K8s：新建 Task
   `fc2ff1b0-…` 的 reason 与 explore 两个 Run 同时读同一路径，均 `exit_code=0`、结果均 `accepted`、work item
   均 `done`。见[证据包](../../vnext/evidence/P11/concurrent-read-fix-20260916/README.md)。
8. **T2 凭据刷新入库。仍未开始。** 目前仍靠仓库外脚本，且 runtime 重启时过期 bearer 会直接拒绝启动。
9. **T8 写入路径与更广并发。未开始。** 写者键的"排除读者"分支只有单元语义；多 Task 并发、长会话压缩/记忆
   与 P12 完成面仍未验证。

### T5 已核对的接口事实（实现前不再猜）

- **触发证据是充分的**：`wuji_task_runtime` 的 `RuntimeObservation.state` 只有在 Pod 对象已不存在
  （或删除未被接受）时才返回 `stopped`；`stopping` 只表示删除已受理。运行中的 runtime 循环已经拿到
  这份观察并逐 Task 上报，因此"环境已终结"不需要新的 k8s 探测，也不该用 `error` 状态代替。
- **观察可以直接构造**：`ExecutionObservation` 的 `environment_stopped` 允许 `process=None`，但
  `source_receipt` 必须与观察自身字段的规范化 JSON 完全一致（`control.py` 的 `source_matches`），
  `receipt_id`/`observed_at` 由平台生成，`environment_ref`/`pod_uid` 只能取自 Run 行。
- **结算是缺的那一环**：`project_run_result` 的观察分支只接受 `process_state='exited'` 且
  `stop_kind IN ('exited','environment_stopped')` **且存在 `run_operation_settlement(status='settled')`**。
  迁移 `vnext_0020_p06_run_settlement_close` 已经支持"空操作集"发布 `settled`，但守卫只允许
  `wuji.request_purpose IN ('tool_request','tool_settle')`，即 Run 自己的凭据用途；从未启动的 Run
  没有凭据，因此今天没有合法发布者。这正是 Task A 无法滚动的原因。
- 因此 T5 的最小实现必须在两条路里选一条，并同步记录到决定登记：
  - **(a) 平台侧空操作集收口**：新增顺序迁移（`vnext_0021_...`）让受权 reconciler 能以新的有界用途为
    空操作集发布 `settled`，之后沿用既有 `project_run_result` → `_settle` 路径，Run 落到 `incomplete`、
    Work 落到 `failed`。范围：迁移 + `uow` 用途 + reconciler 端口 + 真实库测试。
  - **(b) `_settle` 直接分支**：识别"最后观察为 `environment_stopped` 且无任何执行证据"时，直接写
    `result_state='incomplete'` 并以新的有界 `terminal_reason`（例如
    `environment_stopped_before_observation`）收口 Work。改动更小，但绕过了结果投影函数，
    需要说明为何不违反 P05/P06 的单一投影权威。
- 未决点（实现前需确认）：从未执行的 Work 应该**重投**还是**终态失败**。今天 `_known_fresh` +
  `_restore` 只对 `not_started` 的 Run 成立，而"环境消失"无法证明进程从未启动，所以保守做法是终态
  失败并保留有界原因；若产品希望自动重投，需要新增"未观测即未执行"的判定与其容量/预算语义。

## 3. 每项的验证入口（通过即停）

- T1：`tests/vnext/test_task_launch.py` 新增"bearer 早于 deadline 到期"用例，真实 PostgreSQL；
  另在真实集群用一份短期 bearer 复现拒绝，不进入 wire。
- T2：刷新命令对两个 Secret 生效并回读 sha256；存在活跃 attempt 时返回有界拒绝。
- T3：`node --test tests/task-workers/*.test.mjs` 相应用例 + 真实 401 运行时日志显示新码。
- T4：`tests/vnext/test_dispatch_outbox.py`（或等价）证明三次权威拒绝后仍可投递，且未知结果仍受
  `MAX_DELIVERY_SENDS` 约束。
- T5：真实 PostgreSQL 用例 + 真实集群上让 Task A 的孤儿 Run 收口，随后 `--roll-attempt` 成功并派发新 Run。

完成后更新本文件、[验收状态](acceptance.md) 与对应证据包；未验证项保持显式未完成。
