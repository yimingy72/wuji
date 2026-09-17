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
8. **T2 凭据刷新入库。已交付并实测（本项提交）。** `scripts/vnext/refresh_credentials.py` 固定六个目标字段、
   TTL 限 1..72 小时、在 `tasks_in_window>0` 或 `enabled_receivers>0` 时拒绝（陈旧未退出 Run 不阻断），只打印
   有界元数据，并可 `--restart` 滚动 api/runtime/scheduler/gates。实测：守卫放行（窗口=0、receiver=0、
   unexited_runs=6）→ patch 四个 Secret → 四个 Deployment rollout 成功 → 新 bearer 24 小时有效，
   T1 守卫在 1800 秒窗口下 remaining=86342s 通过。见
   [证据包](../../vnext/evidence/P11/credential-refresh-20260916/README.md)。
   **仍缺**：拒绝分支只有单元覆盖；bearer 仍是部署级共享，按 attempt 独立签发未设计。
9. **T8 每 Task 独立 supervisor 端点。已交付并实测（`425a187`）。** launcher 为每个 attempt 创建
   `task-agent-<prefix>`/`task-kali-<prefix>` Service 并把 `service_names`+`supervisor_url` 写进该 Task 的 runtime 条目；
   gates 的 executor 同样按 Task 指向自己的 Kali；runtime 用 `TaskSupervisorTransport` 按 Task 路由
   `query/start/control`；两个 task Service 叶证书新增一层通配 SAN（`k8s.py rotate-task-certs` 复用既有 CA 只重签这两张）。
   真实 K8s：两个 Task Pod 同时 Running，各自 Service 只指向自己的 Pod，两侧各 2 个 Run 全部
   `exited|accepted|settled`，且每个 Pod 的 supervisor 收件箱只持有自己 Task 的两个 assignment。检查 53 passed。
   见[证据包](../../vnext/evidence/P11/multi-task-endpoints-20260917/README.md)。**仍缺**：写入路径"排除读者"分支的实机验证、
   长会话压缩/记忆、旧条目仍回落固定名、多 Task 长时间公平性与 per-attempt 证书签发。
10. **P12-A 完成 precheck 生产者。已交付并实测（`3d2b55c`）。** 迁移 `vnext_0022_p12_completion` 提供
    SECURITY DEFINER 的 quiescing 决定生产者；`completion.criteria` 只认已持久化判定（缺失/unknown/
    not_applicable/非 current 均未满足，空 required 永不满足），`CompletionService.precheck` 不绑定提出者
    Run，`propose` 仅在 ready 时写入决定并交给 P05 消费。真实集群 7 个 Task 全部 `wait/criteria_unmet`，
    包括两个 Run 均已接纳、work 均 `done` 的 `fc2ff1b0-…`。见
    [证据包](../../vnext/evidence/P12/completion-precheck-20260916/README.md)。
11. **P12-B 判定生产与关闭决定。部分交付并实测（`267f720` + `91a22b5`）。** 迁移 `vnext_0023_p12_judgments`
    提供 `record_criterion_judgment`（冻结 revision、幂等、迟到反证只记录不改当前）与
    `prepare_completion_close`（trigger/outcome 独立、必须匹配当前 epoch）；`completion.judgments` 要求
    assessor + `can_assess` 且只接受**已封存**证据（回执记录实际校验的引用与 digest）；`CompletionService.close`
    写关闭决定。真实集群：Task `fc2ff1b0-…` 用真实封存 artifact 写入 `met/current` 判定后 precheck 由
    `wait/criteria_unmet` 变为 `ready`，写入 quiescing 决定并 apply 成功（`observed_state=quiescing`、
    `execution_allowed=false`、epoch 已设）。同一 key 用不同回执重放被生产者拒绝。见
    [证据包](../../vnext/evidence/P12/completion-judgment-20260916/README.md)。
    **仍缺**：判定的生产来源（谁/按什么规则自动判定）、真正 close（P05 要求全部 Run 已结算）、AC-049 冻结期
    结算、AC-053 ReportCommit 冻结与迟到反证追加。

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

12. **P12-C 冻结期结算与强制关闭。已交付并实测（`3c0b3b4`）。** 新增测试证明冻结期拒绝新动作但继续接受在飞
    Run 的退出观测、结果提交与 accepted 投影（AC-049）；`CompletionService.close` 只在 `goal_satisfied` 时要求
    完整评审，强制关闭（budget/time/no_progress/operator）允许有未完成工作并由 P05 取消它们，trigger 与 outcome
    始终分离（AC-052）。真实 Task `fc2ff1b0-…` 从 `quiescing` 走到 `observed_state=closed`
    （trigger=goal_satisfied、outcome=complete、control_version=4）。见
    [证据包](../../vnext/evidence/P12/completion-close-20260917/README.md)。
13. **P12-D ReportCommit 冻结与迟到反证。未开始。** 关闭目前只固化 Task 状态与两份决定，尚未冻结报告正文、
    也未把迟到反证追加成补充/争议记录（AC-053）；关闭的产品入口（工作台/API）与报告投递同样未接线。

14. **P12-D 报告冻结与迟到反证。已交付并实测（`9bddbcc`）。** 迁移 `vnext_0024_p12_reports` 提供
    `freeze_report_commit`（仅该 epoch 已关闭的 Task、服务端 digest、同 key 不同字节或自相矛盾的行都拒绝）与
    `amend_report_commit`（追加争议记录并标 `disputed`，永不改正文）；`completion.reports` 从持久事实组装正文并
    校验反证引用的封存证据。真实集群：已关闭 Task 的报告 684 字节冻结（digest `4445bc13…`），追加一条引用
    封存 artifact 的反证后正文与 digest 不变、`dispute_state=disputed`、Task 仍 `closed`、`ready_work=0`。见
    [证据包](../../vnext/evidence/P12/report-freeze-20260917/README.md)。
15. **P12-E 关闭与报告的产品入口。已交付并实测（`6148154`）。** 新增
    `GET/POST /api/v2/tasks/{task_id}/completion` 与 `GET /api/v2/tasks/{task_id}/reports/{report_id}`：
    审核、epoch 与关闭决定仍由平台生产，调用者只表达意图（关闭原因 + 结果）且必须持有该 Task 的 `can_control`
    （agent 一律排除）；同源 BFF 只转发这三条固定路由，工作台新增“任务完成”面板（判据表、开始收尾、
    完成关闭并冻结报告、冻结正文与“有争议”标签）。真实浏览器在固定 Task `083f6134-…` 上完成
    `ready → quiescing → closed`，报告 701 字节冻结（digest `4f1b3e37…`），幂等重放返回同一份 commit，
    `ready_work=0`。测试：`test_completion_portal.py` 6 passed（真实 PostgreSQL + 签名 HTTP）、相邻
    `test_completion_protocol.py` 16 passed；web build / contracts check exit 0。见
    [证据包](../../vnext/evidence/P12/product-entry-20260917/README.md)。
16. **P15 ViewStream 与工作台实时视图。已交付并实测（`32311a4` + `94a1122`）。** 迁移
    `vnext_0025_p15_view_stream` 允许同一投影视图推进（subject 绑定的 UPDATE 策略、`stream` 游标、
    `vnext.task_for_view` 只按当前 tenant+subject 解析 Task）；`ProjectionRepository.stream_step` 在视图上
    写出新 materialization 并产出最多 2000 条 node/edge patch（无变化不发空批次），
    `GET /api/v2/views/{view_id}/events` 以 SSE 输出批次，权限撤销/过期/变更过大时发 `ViewReset`；
    同源 BFF 只转发该 Task 拓扑刚发布过的 view id，工作台对 live 视图应用 patch，无法应用或 reset 时显式重读。
    真实 K8s：`curl -N` 收到 keepalive 与 16 条 patch 的批次（`pause` 命令 202 触发）；浏览器无需刷新，
    画布节点从 `origin:2abfdd57…@4` 变为 `@5`。检查：pytest 29 passed、topology vitest 29 passed、web build exit 0。
    见[证据包](../../vnext/evidence/P15/view-stream-20260917/README.md)。
17. **P16-A 报告交付（ReportDelivery）。已交付并实测（`6cfa411`，修复 `3843311`）。** 迁移
    `vnext_0026_p16_report_delivery` 提供只读交付账本与 `SECURITY DEFINER` 生产者（control 权限、当前 scope、
    已关闭 Task 同一 epoch、必须引用冻结正文 digest、服务端计算摘要）；`wuji_core.audit.delivery` 按显式声明的
    profile 核对冻结正文与已密封产物，缺失必需材料记为 `incomplete` 而不编造“不适用”；数据库拒绝
    “缺必需材料却写 ready”、离线交付携带 HTTP 交换、http ready 无交换回执与同 key 改写。产品面有
    `GET/POST /api/v2/tasks/{id}/reports/{rid}/deliveries`（含单条与列表）、同源 BFF 白名单与工作台“报告交付”面板。
    真实 K8s：离线文档 profile `ready`、截图 profile `incomplete`、同 key 重放同一记录、离线带交换/缺幂等键 422、
    `reader` 与其他 Task 404；真实浏览器从 UI 生成记录并列出 3 条。检查：交付 9 passed、P12 相邻全绿、
    BFF 6 passed、合同 check 与 web build exit 0。**同轮修复**了 P12/P16 拒绝路径在 HTTP 边界退化为 500 的
    封闭错误码问题（`3843311`，本集群镜像待重建）。见
    [证据包](../../vnext/evidence/P16/report-delivery-20260917/README.md)。
18. **仍未完成。** P16 的保留/GC/purge 与 tombstone（AC-066/067）、审计/观测/费用分离（AC-068）、
    HTTP 交付适配器与外部媒介投递、历史交付分页；判定自动生产来源；真正在 run 执行中投递取消、
    写入路径语义与长会话压缩；工作台当前仍是每个 web 部署绑定一个 Task。ViewStream 的跨 BFF 重启、
    多标签长连接与规模 p95 也未验证。
