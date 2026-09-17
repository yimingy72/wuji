# vNext 当前任务队列 — 2026-09-17（信息驱动探索：E00–E08）

- 状态：approved；用户已下发执行单 `WUJI-EXPLORATION-9891989-20260917-R1` 并要求按 E00–E08 增量实施
- 基线检查点：`9891989da00f74b298da223a9d81ce61d3ab0723`（本工作树干净、已推送）
- 权威来源：用户下发的执行单 `WUJI-EXPLORATION-9891989-20260917-R1`（EXECUTION_PLAN / TRIAL_PROTOCOL / AGENT_HANDOFF，不随仓库分发）；仓库内以本文 + [Spec](../../vnext/SPEC.md) + [Plan](../../vnext/PLAN.md) + [实施决定](../../vnext/decision-register.md) 为准
- 取代：[2026-09-16 计划](next-development-plan-2026-09-16.md) 的队列顺序（该文 T1–T8 交付事实继续有效）

## 1. E00 基线状态表（只读核对，2026-09-17）

| 项目 | 实际状态 | 依据 |
| --- | --- | --- |
| 当前提交 | `9891989`，`codex/vnext-maf` 与 origin 同步，工作树干净 | `git status --short --branch` |
| 迁移头 | `vnext_0027_p16_artifact_purge`（2026-09-17 04:42:49Z 应用） | 集群 `wuji_vnext_ui_20260915` |
| 框架锁 | `agent_framework_core 1.18.0` / `agent_framework_openai 1.14.3`；Worker `uv.lock` 摘要随 `runtime_profile.lock_digest` 冻结 | `ops/vnext/task_launch.py::FRAMEWORK_SNAPSHOT` |
| R01 完成审核版本竞态 | 已修复 `c35153f`（Task 写锁内重算并持久化真实依据） | 提交 + P10-M2 定向复审 |
| R02 候选发现不隔离 | 已修复 `4ea77c0`（逐 Task 隔离，坏候选不再取消其他派发） | 同上 |
| R03 共用游标饥饿 | 已修复 `4ea77c0`（派发/核对各自独立、按 Task ID 续扫） | 同上 |
| R04 视图/详情 snapshot 错配 | **未修复**（X04 未动） | `packages/wuji-core/src/wuji_core/projection/snapshots.py` 只返回单个 snapshot；前端仍独立刷新详情 |
| R05 SSE cursor 未真正恢复基线 | **未修复**（X04 未动） | `apps/web/src/features/topology/stream.ts` 仍以浏览器本地游标重连 |
| R06 CI 未实际执行 | 已修复 `f4e46f2` + `9891989`；run [35195579930](https://github.com/yimingy72/wuji/actions/runs/35195579930) 两 job 全绿（后端 562 passed） | GitHub Actions |
| X04（R04+R05） | 未开始；按执行单由 E07 快照模式先行，未修复前关闭不可靠 live 订阅 | 本文件 §3 |
| 已授权操作 | 本地提交、推送 origin、本地 docker-desktop 集群 `wuji-vnext-test` 部署与只读验证 | 历史会话授权，继续沿用 |
| 未授权操作 | 付费真实模型调用（无网关/Key/额度）、真实靶场目标访问、生产切换、数据删除 | 缺配置，按 `blocked_configuration` 记录 |
| 当前可用 Profile | `harness.{reason,explore,report}.deployment.v2`，全部由部署 `bootstrap-config.json` 的 `definition.worker_profiles` 派生；三者的 `tool_definition_refs` 均为 `workspace-read-v1` | 集群 Task 定义回读 |
| 当前已发布工具 | 仅 `workspace-read-v1`（kind=`workspace_read`，executor `kali-workspace-v1`，`evidence_origin=fixture_capture`） | `vnext.tool_definition` 全表 1 行 |
| `http_target` 能力 | 代码已实现并单测通过（`eb90941`：范围校验 + Kali `HttpTargetExecutor`），但**未发布**、Scheduler 仍拒收（`claims.py::_profile` 只允许 `workspace_read`） | 源码 + 租户表 |
| 真实模型 | 不可用：部署模型是 loopback 合成模型（`http://127.0.0.1:8081/v1/chat/completions`，`capability_ref=synthetic-chat-completions-v1`），无真实网关/Key/额度 | `bootstrap-config.json` |
| 旧模式是否仍固定夹具 | **是**：`finalise_definition` 强制 `evaluation_mode=mechanism_synthetic`；`admit_initial_intent` 固定读 `workspace:version.txt` | `ops/vnext/task_launch.py:297,503` |

### 1.1 逻辑信息 → 现有字段/事件映射（E00 交付）

| 逻辑信息 | 现有表达 | 结论 |
| --- | --- | --- |
| Goal / Origin | `definition.task.goal`（`TaskCreate`：`text` + `criteria[]`）、`definition.start_points` | 已足够，不需要新表 |
| 模式（机制/真实） | `definition.evaluation_mode`（当前只有 `mechanism_synthetic`） | 需扩为显式可信配置，E01 |
| 角色能力 | `definition.worker_profiles[kind].body.tool_definition_refs` + `runtime_profile.allowed_tool_refs` + `executor_registration.allowed_tool_refs` | 交叉规则重复，E02 收敛 |
| Intent 理由 | `intent_revision.question` / `basis_refs` / `expected_output`（无“为什么值得做”字段） | 本轮不做合同增量；理由由 `question` 承载，评测侧记录 |
| 证据正文 | Artifact/Observation 原生字节 + `read_set`/`ContextBundle` 引用 | 已足够，E03 只需保证真正注入 |
| 重复关联 | `WorkKey`（`intent:{id}:{revision}:{profile}:{digest}:{basis}:{env}:{output}`） | 已足够，E04-A 复用它做精确重复关联 |
| 进展 | `scheduler_trigger.generation` + `reason_lease` + 预算计数器 | 已足够，E04-B 只加有限收敛判定 |
| 完成反馈 | `reason.completion_requested` → `completion/*`（消费者已存在，R01 修复后按锁复核） | E05 复核消费者与缺口反馈路径 |

## 2. 里程碑与最短路径

| 里程碑 | 内容 | 依赖 |
| --- | --- | --- |
| M1 | 正式 Task 入口 + 实际 MAF/工具完成一个工作，真实证据独立保存（无真实模型授权时用明确标注的合成模式） | E01/E02/E03/E06 |
| M2 | 真实观察触发非预写 Intent → 正式调度执行 → 新证据改变后续判断 | M1 + E04-A/E05 |
| M3 | 材料变体改变后续问题；有限去重/无进展收敛；封闭实例有限现场观察 | M2 + E04-B/E07/E08 |

## 3. 队列（对应 P 任务）

1. **E01 真实任务配置与机制夹具分离（P02/P07/P11/P18）** — 模式来自可信部署配置；真实模式默认 Reason-first，不回落 `version.txt`；显式 seed 策略才产生种子读取；preflight 不触达目标/付费模型。
2. **E02 接通完整能力链（P06/P07/P09/P10）** — 发布→Profile→Task 许可→Scheduler→Worker→Gate→Executor 同一张兼容表；Reason 无目标能力；`http_target` 进入正式调度前必须有部署发布与真实负控。
3. **E03 让模型看到真实任务与材料（P07/P08/P04）** — Goal/Origin/范围/能力/限制 + 固定问题 + 证据正文 + 反证 + 已做尝试。
4. **E04-A 真实观察触发 Reason（P04/P05/P09）** — 事件→generation→Reason→Intent 接纳；Reason 自触发不自启；重复事件不重复工作。
5. **E05 完成提案的持久消费者与可信判据（P04/P05/P12/P16）** — 缺口反馈可回到 Reason；规则比较失败不得写 met。
6. **E06 盲测夹具与验收器（P17/P18）** — 变体材料与模型隔离、独立评分、可追溯关系。
7. **E07 最小工作台解释能力 + X04 收口（P13/P14/P15）** — 先快照模式；live 订阅按 R04/R05 收口。
8. **E08 固定候选闭环验收与有限试测（P17/P18）** — 机制闭环 → 真实模型案例 → 变体 → 单实例有限观察。

## 4. 本轮立即执行顺序

1. E00（本文）。
2. E01 + E02 打通“真实任务配置 → 正确角色能力 → 正式 Scheduler”。
3. E03 + E06 并行。
4. 立即跑 M1，不等全部 UI/P20 完成。
