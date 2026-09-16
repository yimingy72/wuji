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

1. **T1 attempt 凭据期限守卫（fail closed）。** owner 工具在 `prepare/activate` 前解析 receiver bearer 的
   `exp`，要求不早于 `activated_at + max_elapsed_seconds` 加固定余量；否则以有界码拒绝启动，而不是把
   一个注定 401 的 attempt 交给 runtime。范围：`ops/vnext/task_launch.py` + 单测。
2. **T2 凭据刷新入库、可复现。** 把目前只在被忽略目录里的 24h 重签脚本变成仓库内命令，明确 TTL 上界、
   目标 Secret 清单与前置条件（存在活跃 attempt 时拒绝执行），并记录到运维文档。
3. **T3 supervisor 错误码有界化。** `services/maf-supervisor` 的错误响应带 `code`，使 401/拒绝类失败
   在平台侧显示为 `UNAUTHENTICATED`/`CONTROLLER_REQUEST_REJECTED`，不再折叠成 `STALE_EXECUTION`。
4. **T4 权威拒绝不消耗投递预算。** 只有"已发出但结果未知"的发送才计入 `MAX_DELIVERY_SENDS`；被接收方
   明确拒绝（401/403/409/422、404 OPERATION_NOT_FOUND）不递增发送计数，保留静默期节奏。凭据修好后
   同一 operation 必须能重新投递，而不是永久停留在 `previous_delivery_unresolved_no_replay`。
5. **T5 孤儿 Run 结算。** attempt 已终结（permit 撤销且 Pod 已确认删除）而 Run 从未被观测时，由受权
   reconciler 记录 `environment_stopped` 观测并走既有 `_settle`，使 `roll_runtime_attempt` 不再被卡；
   结算只依据平台自身的 attempt/Pod 事实，不伪造进程退出或结果。

T1–T4 是小型、可单元测试的改动；T5 触及 P05 观察语义，先落最小实现与真实库测试，再回到 P12 完成面。

## 3. 每项的验证入口（通过即停）

- T1：`tests/vnext/test_task_launch.py` 新增"bearer 早于 deadline 到期"用例，真实 PostgreSQL；
  另在真实集群用一份短期 bearer 复现拒绝，不进入 wire。
- T2：刷新命令对两个 Secret 生效并回读 sha256；存在活跃 attempt 时返回有界拒绝。
- T3：`node --test tests/task-workers/*.test.mjs` 相应用例 + 真实 401 运行时日志显示新码。
- T4：`tests/vnext/test_dispatch_outbox.py`（或等价）证明三次权威拒绝后仍可投递，且未知结果仍受
  `MAX_DELIVERY_SENDS` 约束。
- T5：真实 PostgreSQL 用例 + 真实集群上让 Task A 的孤儿 Run 收口，随后 `--roll-attempt` 成功并派发新 Run。

完成后更新本文件、[验收状态](acceptance.md) 与对应证据包；未验证项保持显式未完成。
