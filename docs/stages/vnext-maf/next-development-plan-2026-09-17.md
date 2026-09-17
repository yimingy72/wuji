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

> 进度：E00 完成（本文 §1）；E01/E02 已交付 `5a94986`；E03-A 已交付 `8812239`；E03-B 已交付 `0f66d08`；E06 已交付 `83ffb65`；E01 收口项（worker lock 复锁）已交付（见 §5）。

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

## 5. 增量进展

### E03-A（已交付）：模型真正拿到冻结的 Task 上下文

- 每个角色的 Session Profile 正文 = 部署发布的角色指令 + 一份由 Task 定义渲染出的**冻结 Task 上下文**：Goal 原文、每条判据（对象/条件/证据要求/允许方法/责任方）、授权范围与到期、金额预算、已发布硬上限、起点、评估模式、角色职责，以及"未实际读到的材料必须标为未读"的材料规则。
- Profile 身份改为 Task 级 `harness.<role>.task.<digest16>`：正文不同必然 ref 不同，两个 Task 不会用同一个 key 发布不同字节；同一 Task 重复 prepare 仍然逐字节一致（幂等）。
- 模型输入对应关系：`build_agent(agent_instructions=profile.instructions)`，已用捕获参数的方式实测；材料正文（Artifact 字节）仍按权限走工具/上下文，不在本项伪造。
- 证据：`tests/vnext/test_task_launch.py::test_e03_the_model_instructions_carry_the_frozen_task_context`（Goal/范围/预算/上限/角色职责进入正文；Goal 变化即输入变化且 ref 变化，工具集合不变）、`::test_e03_the_harness_receives_the_composed_instructions`（Harness 收到的就是这份正文）。
- 残留（E03-B）：平台封存的 Artifact 正文目前只能在同一 Run 的工具结果里看到，跨 Run 的 Reason 只能看到元数据；需要把受权读集中的文本证据正文有界地放进上下文，并对未放入的部分显式标注。

### E03-B（已交付）：受权证据正文进入跨 Run 上下文

- 平台在构建交付上下文时，对**已授权快照读集**中的 Artifact 做有界内联：只取 `state=sealed`、`media_type` 为 `text/*`、字节数不超过 `min(max_single_output_bytes, max_context_bytes/4)` 的正文，整组正文不超过 `max_context_bytes/2`，其余留给记录元数据。
- 正文要么**整份**进入上下文（`material: {encoding, byte_length, text}`，与按引用一致），要么在记录上显式标注固定原因：`not_sealed` / `not_text_media` / `over_inline_limit` / `unreadable` / `not_utf8` / `context_byte_limit` / `not_delivered`。**不截断、不静默丢弃、不改写原始字节**（存储字节与摘要仍由 `ArtifactStore.checked_bytes` 逐字节校验）。
- 未配置 artifact 端口的宿主保持原行为：上下文只有精确引用，记录不出现 `material`/`material_omitted`，也不假装正文已交付。
- 证据：`tests/vnext/test_evidence_in_context.py`（6 项：投递与逐项省略原因、预算边界不截断、无 artifact 端口时行为不变、上下文渲染、超限时改名、纯元数据模式不变）与 `tests/vnext/test_maf_child_transport.py::test_delivered_child_context_carries_the_authorized_evidence_body`（真实 M2 子进程链路上，spool 出的交付上下文确实带 P09 夹具正文）。

### E06（已交付）：封闭试测夹具、独立评分与可复跑入口

- `scripts/vnext/exploration_trials.py` 提供 `fixtures / preflight / case-config / run / inspect / summarize / stop`：`fixtures` 生成 CASE-A（运行时引用）、CASE-B 两个同 Goal 变体（一致/冲突）、CASE-C（信息不足）；`preflight` 只读本地材料与评分文档，检查"评分文档在材料根之外、材料字节未被改动、非答案文件不含答案、Goal 不含答案、变体标签不外泄"；`run` 委托现有 owner 命令，不新增第二套启动路径；`stop` 发真实 `cancel` 命令并回读数据库状态，不把 202 当成已停止。
- `ops/vnext/task_launch.py` 支持部署/场景发布的有界 `materials`（≤16 项、每项 ≤4096 字节、路径受限）：attempt 初始化 Job 以 `umask 077` 写入 Kali 工作区，文本一律 base64 传输并 shell-quote，材料文本不进入命令行字面量；未发布材料时保持原 `version.txt` 夹具。
- 证据：`tests/vnext/test_exploration_trials.py`（4 项：生成与预检、篡改材料被拒、案例运行配置只发布本案例材料、变体标签/诱饵答案不外泄）与 `tests/vnext/test_task_launch.py::test_e06_published_materials_seed_the_workspace_without_shell_interpretation`。
- 未覆盖：真实集群上的 `run`/`stop` 尚未执行（等待新镜像滚动完成）；评分器（grading.json）需要根据真实试次记录写回，本轮只固定其输入契约。

### E01 收口（已交付）：worker lock 变更后新 Task 无法 prepare

- 真实集群实测发现：`198` 之后的提交 `62c232c` 改了 `packages/maf-worker/uv.lock`，但部署在 2026-09-15 发布的 `k8s-runtime-v1` 仍写着旧摘要 `b6d8a78d…`；`create_task` 把该旧 profile 冻结进新 Task 定义，`finalise_definition` 与 `shipped_worker_lock_digest()` 不一致，prepare 以 `INPUT_DIGEST_CONFLICT` 拒绝。这是正确的 fail-closed，但当时没有 owner 复核/修复路径。
- 现在：`preflight` 新增 `worker_lock` 检查，直接点名"定义里的摘要 vs 本次构建实际 ship 的摘要"并给出修复动作；新增 owner 阶段 `--phase relock`，把部署文档里的运行时 profile 发布为**下一个不可变 revision**（不原地改写旧行），重复执行幂等。
- 证据：`tests/vnext/test_task_launch.py::test_e01_a_stale_worker_lock_is_named_and_relock_publishes_a_new_revision`（stale 定义被 preflight 拦下 → relock 发布 rev3 → 再执行不重复发布 → 旧定义的 Task 仍被点名，必须重建）。
