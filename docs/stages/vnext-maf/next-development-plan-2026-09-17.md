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

> 进度：E00 完成（本文 §1）；E01/E02 已交付 `5a94986`；E03-A 已交付 `8812239`；E03-B 已交付 `0f66d08`；E06 已交付 `83ffb65`；E01 收口项（worker lock 复锁）已交付 `36f8771`；**M1 已在本地集群实跑通过**（见 §5）。

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

### M1（已实测）：正式入口 → 真实 MAF/工具 → 独立证据

- 2026-09-17 在 `wuji-vnext-test` 用镜像 `source_revision=36f8771` 实测：`POST /api/v2/tasks` 新建 Task `45d4ee2f…` →
  owner 命令四阶段（prepare/activate/wire/capability）全绿 → Task Pod `pod_uid=835445c0…` ready →
  `reason`/`explore` 两个 work item 均 `done`，两个 Run `exited/accepted`，8 份 sealed artifact（含工作区读取捕获与 MAF SDK 归档）、2 条候选 Claim 被接纳。
- 发布的三份 Session Profile 正文已包含该 Task 的 Goal/判据/授权范围/预算/硬上限/角色职责（E03-A 在集群内生效）。
- 证据包：[M1 mechanism loop](../vnext/evidence/E08/m1-mechanism-loop-20260917/README.md)（含创建请求/响应、四阶段结果、数据库回读、截图与原始日志）。

### M1 暴露并已修复的部署缺陷

1. **worker lock 变更 → 新 Task prepare 永久失败**：已加 `preflight.worker_lock` + owner `--phase relock`（本次发布 `k8s-runtime-v1` rev4）。
2. **共享 runtime ConfigMap 混入两个 Worker lock → runtime 启动即失败**：`wire` 现在按 lock 退休旧条目（`replace_runtime_profiles`，`pruned:N`），不再让两种 lock 共存。
3. **每 Task Service 证书缺本 Task DNS 名 → runtime 到 supervisor 的 HTTPS 投递 `URLError`**：现场把模板 Task secret 更新为带 `*.wuji-vnext-test.svc` 的证书后新建 Task 一次成功；`rotate-task-certs` 现在可在同一命令里把重签后的叶子证书推送到模板 Task secret（`--task-secrets <name>,<name>`），见下。

### E04-A（部分交付）：结果结算后驱动下一步

- `tests/vnext/test_exploration_loop.py`（2 项，真实 PostgreSQL + 生产 Scheduler）：
  1. Run 提交结果、关闭自己的操作集、平台观察到退出 → work 才结算为 `done`；Committer 接纳 Reason 提出的**新问题**（`accepted_shared`），Scheduler 记录 `scheduler_decision=accepted` 并把该 Intent 物化成新的 Explore work（`max_work_items` 足够时不再被上限挡住）。
  2. Explore 的候选 Claim 被接纳并持久化（`claim_revision` 行、work `done`、run `exited/accepted`）。
- 未完成：**新 Claim 进入下一次 Reason read_set** 尚未通过；`scheduler_progress` 本轮实测没有 material 行，需要单独核对 `_progress` 的触发条件（下一项最小工作）。

### E03-C（已交付）：冻结的 Task/Work/Run/评估状态进入模型输入

- 集群实测发现：交付给模型的上下文只有 1 条记录（那次的 Intent），`snapshot_manifest.states`（work_items/agent_runs/claim_assessments/task）**从未进入模型输入**——模型看不到"已经做过什么"、哪条 Claim 已经是 Fact、以及 Task 的冻结状态。
- 现在 `build_context_bundle(..., states=...)` 把这份已冻结、已校验的映射放进同一份上下文文档（仍受 `max_context_bytes` 约束），`WorkerHostBridge.resolve` 传入 `manifest.states`，runtime 的 `build_context` 转发；没有 states 的旧调用方行为不变。
- 证据：`tests/vnext/test_maf_child_transport.py::test_delivered_child_context_carries_the_authorized_evidence_body` 断言真实子进程收到的 spool 文档里 `states.work_items`/`agent_runs`/`claim_assessments` 都在且带 state/revision。

### E04-A 收口（已交付）：材料进展与下一次 read_set

- `TriggerRepository._progress` 之前只认 `evidence_ingested`，正常工具结果提交（`result_committed`）**不产生任何 material 进展**——无进展收敛会失去依据。
- 现在被接纳的非 Reason 结果按**已接受组件的 canonical refs** 生成一条 `material` 进展行：指纹不含 ToolAttempt ID/UUID/接收时间，重放同一事件既不新增进展也不新增工作；Reason 自己的决策不计入材料。
- 证据：`tests/vnext/test_exploration_loop.py` 3 项，其中第三项实测"新 Claim 进入下一次 Reason 的 read_set"（新 Reason Run 的 snapshot read set 含该 Claim），第二项实测材料行唯一且重放无副作用。

### E05（已交付）：完成提案有真实消费者，缺口回到 Reason

- 事实核对：`reason.completion_requested` 在 vNext 里**此前没有任何消费者**（唯一命中在遗留 `services/execution-control/core.py`，那条是 v1 老链路），事件只进 outbox 没人处理。
- 现在 `Scheduler` 注入 `CompletionService`：在已持有 Task 锁、且刚消费该请求事件的同一事务里调用 `review_in_transaction`，把评审写成一份带来源与依据版本的 `completion.reviewed` 事件（review_id、decision、reasons、coverage、open_work、unsettled_runs、basis={请求事件序号, work item, processing_generation, control_version, board_revision}、review_digest）。同一请求事件重复投递不会再生成第二份评审，也**从不**由评审本身关闭 Task。
- 缺口反馈闭环：`completion.reviewed` 在 decision 为 `wait`/`blocked` 时是"相关事件"（唤醒下一代 Reason），并且最新评审会随 `snapshot_manifest.states.completion_review` 进入下一次 Reason 的冻结输入；`ready` 不触发新一轮 Reason，等待操作者走既有 quiesce 决策。
- 判据侧沿用既有 P12 协议（未改动）：`test_completion_protocol.py` 已覆盖"只有 current 的 met 判定支持 Goal""没有必需判据永远不算满足""判定必须引用封存证据""必需工作未完成不得提前静默""只有评估身份能写判定"，以及迟到反证标记 disputed。
- 证据：`tests/vnext/test_exploration_loop.py::test_a_completion_request_is_answered_once_with_a_durable_review`（一次请求一份评审、basis/digest、不关闭 Task、重复事件不新增、评审进入下一次 Reason 输入）。

### 部署工具收口：证书轮换同时更新模板 Task secret

- 根因：`rotate-task-certs` 只重签 `work/vnext/k8s/tls/` 里的状态文件，模板 Task 的 secret 仍是旧 SAN 证书，新建 Task 复制到旧证书后 runtime→supervisor 的 HTTPS 调用报 `URLError`，Run 永远停在 `registered`。
- 现在 `scripts/vnext/k8s.py rotate-task-certs --task-secrets <agent-auth>,<kali-auth>` 把 `task-agent.*`/`task-kali.*` 叶子证书按后缀映射写入对应 secret（`--type merge`，只改 `tls.crt`/`tls.key`），未识别的 secret 名直接拒绝而不是静默跳过。
- 证据：`tests/vnext/test_configure_refresh.py::test_rotating_the_task_leaves_also_republishes_the_template_secrets`。

### E07（快照模式已交付）：R04/R05 未关闭前不启用实时订阅

- `apps/web/src/features/topology/TopologyContainer.tsx` 新增 `LIVE_VIEW_ENABLED = false`：R04（视图 revision 与 snapshot 未原子绑定）与 R05（重连不证明从已见基线真正续传）未关闭前，SSE 订阅不建立，图/详情/引用全部来自同一份受权快照。
- 界面显式显示"快照模式：实时订阅未启用，图为当前受权快照"，并提供"刷新快照"按钮（重新读取 `requestRevision`）；原来的实时状态文案保留在开关打开后的分支，供 X04 修好后恢复。
- 验证：`pnpm --filter @wuji/web typecheck` 通过；本项不宣称 P15 完成，也不把实时模式标为可用。

### M2（已实测）：真实观察 → 非预写 Intent → 正式执行 → 新证据改变判断

- 2026-09-17 在 `wuji-vnext-test` 用镜像 `source_revision=4047e12b919811c69190f8d850b41e113f848197` 实测 CASE-A（`E06` 夹具，答案与变体标签都在 `grader/` 之外）：
  公开入口 `POST /api/v2/tasks` 新建 Task `ff045b32-68f6-4faa-b74c-482af7f0c148` → owner 四阶段全绿 →
  7 个 work_item 全部 `done`、7 个 AgentRun 全部 `exited/accepted`、2 个 Intent、2 条 Claim、2 条 Observation、
  1 次 `reason.completion_requested` 与 1 份 `completion.reviewed`，最终 `blocked_reason=reason_operator_review`。
- 五次 Reason 决定构成闭环：`wait`（尚无材料）→ `propose_intents`（问题来自只在被观察字节里出现的 `{"pointer": "materials/registry-oct.json"}`）→
  `wait`（该问题已在执行，等待其结果而不是重复提问）→ `propose_completion`（指向的文件已读、正文带答案）→ `blocked`（评审仍缺判据，交操作者）。
- 独立评分：`verdict=pass`（答案链 `entry.json → registry-oct.json`、答案 `4.2.0`、诱饵 `4.3.1` 未被读取）。
- 证据包：[M2 mechanism loop](../vnext/evidence/E08/m2-mechanism-loop-20260917/README.md)（含创建报文、四阶段原文、五次决定、数据库回读、工作台截图与评分）。

### M2 触发并修复的四项缺陷

1. **工具结果正文不交付**：模型只拿到 receipt。新增 `/internal/v2/tool-calls/{id}/material`，在同一 Run 内把该次调用的封存文本结果交给模型（受发布输出上限约束、固定省略原因），receipt 本体不变；会话重放时只有校验正文等于封存 Artifact 才接受（`e8f15e0`）。
2. **机制 peer 用 Artifact 做问题依据**：被 Committer 正确拒绝而耗尽该代 Reason；改为最新 Claim/退到 Observation，且已有同路径问题时改为 `wait`（`8208934`）。
3. **Session profile 身份只哈希部分 body**：限值不同而 ref 相同 → `wire` 阶段 `INPUT_DIGEST_CONFLICT`；改为身份覆盖整个已发布 body（`fa94f4c`）。
4. **Run 私有产物回流成黑板材料**：快照默认选入每个 sealed Artifact，上下文逐代增长，最终在会话边界以 `LIMIT_BLOCKED` 拒绝 Run。新 Run 的快照只冻结 claim/intent/observation 及其证据闭包（`4047e12`）。

### 下一步（M3 之前）

1. E04-B：有限去重（不同 Intent ID 的同一规范问题建立可核验重复关联）与无进展收敛（发布窗口、达到后只发一次完成/停止请求、真实 wait/blocked 不按 tick 计无进展）。
2. E08：在同一 Goal/能力/预算下运行 CASE-B 两个变体，核对"改变的是问题与依据"；CASE-C 走 insufficient 分支。
3. X04（R04/R05）修好后再打开实时订阅；在此之前工作台保持快照模式。
4. 真实模型试测仍为 `blocked_configuration`（无网关/Key/额度）。

### E04-B（已交付）：精确去重 + 有限无进展收敛

- **精确去重**：工作身份不再只由 Intent ID 决定。Scheduler 重算 (冻结问句, 依据 refs, 方法/能力版本, Profile 摘要, 环境, 输出合同) 的 canonical digest，命中既有 Work 时只写一条 `intent.deduplicated`（同时点名 Intent 与既有 Work），不创建第二个 Explore；新依据或新环境得到不同 digest，仍是合法延续。
- **有限无进展收敛**：运行时限新增可选 `max_no_progress_rounds`。一轮"已结算且没有新材料"的 Reason 只有在没有其它排队/运行中 Work、没有未满足 waiter、也没有更新输入在等时才计数；达到窗口发出一份 `reason.completion_requested`（`reason=no_progress_window`）交给 E05，并置 `blocked_reason='no_progress_window'`，在**新知识**到来前不再生成 Reason（失败重试与操作者阻断不会被新材料解除）。
- **附带修正**：Work 通常在自己的退出观察被消费时才结算完成，此前 waiter 只在"相关事件"重扫，导致条件已满足的等待可能不醒；现在每条已记录事件都重读谓词。
- 证据：`tests/vnext/test_exploration_loop.py` 4 项定向用例 + 集群复核（窗口=3 的 CASE-A 重跑，`no_progress_count=0`、无重复问题、循环闭合到 `reason_operator_review`）见 [E04-B 证据包](../vnext/evidence/E08/e04b-bounded-loop-20260918/README.md)。

### 现在的位置（2026-09-18）

M1、M2 与 E04-B 均已实测；距离"可开展 M3 限定试测"只差：

1. **E08 变体对照**：同一 Goal/能力/预算下运行 CASE-B 两个变体（一致/冲突），核对"改变的是问题与依据"；CASE-C 走信息不足分支。
2. **真实模型**：仍为 `blocked_configuration`（无网关/Key/额度）。机制模式只能证明平台路径，不能替代模型质量结论。
3. **X04（R04/R05）**：视图 revision 与 snapshot 原子绑定、丢批次回放/reset 未做；工作台维持快照模式，修好后才能打开实时订阅。
