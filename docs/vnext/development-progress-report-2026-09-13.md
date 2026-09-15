# Wuji 当前开发进度与开发方向完整汇报

> 汇报日期：2026-09-13  
> 当前阶段：vNext MAF v2 核心重构  
> 活跃分支：`codex/vnext-maf`  
> 汇报状态：实施中，不是发布或生产切换结论

## 1. 执行摘要

Wuji 已完成 W1 封闭机制基线，并正式进入 vNext MAF v2 重构。新架构不再以 Cairn Server、Cairn Dispatcher、Cairn Blackboard 或 Pi CLI 作为新运行内核，改为 Wuji 自有 Blackboard、持久 Scheduler、Python MAF Worker、模型/工具准入和受权 React Flow 工作台。

截至本报告生成时：

- P00—P05 已按各自限定范围 accepted。
- P06 已有核心实现和首个 13/13 候选，但独立审查发现 3 个 P1、4 个 P2 问题；当前未提交修复工作树的聚焦测试为 21/21 通过，尚未完成固定提交、复审和最终证据收口，因此仍未 accepted。
- P07 仅完成 ContextBundle 纯函数切片，完整 MAF SDK Runtime 尚未启动。
- P13 仅完成纯图投影 builder，持久快照、权限、分页、历史和 API 尚未启动。
- P08—P12、P14—P20 尚未完成完整任务切片。
- 21 个计划任务中有 6 个任务切片 accepted；任务规模不同，该数字不是线性产品完成百分比。
- 原始 75 项统一产品验收没有整体标记通过；局部测试证据不能替代最终端到端验收。
- 未执行收费模型效果试验、真实外部目标、生产部署、旧系统停机切换或旧数据删除。

权威设计与计划：

- [vNext Spec](SPEC.md)
- [vNext Plan](PLAN.md)
- [vNext 阶段验收状态](../stages/vnext-maf/acceptance.md)
- [实施决定记录](decision-register.md)

## 2. Git、工作树与交付状态

| 对象 | 当前状态 | 含义 |
| --- | --- | --- |
| 远端 W1 交付入口 | `codex/github-upload@1d73a76` | 与 `origin/codex/github-upload` 一致，保存 W1 源码与交接文档 |
| 活跃 vNext 分支 | `codex/vnext-maf@e3e5cfd` | 相对 W1 基线有 41 个本地提交 |
| vNext 远端状态 | 无 upstream | 尚未推送、合并或部署 |
| `master` | `28fcd44` | 仍保留早期阶段基线 |
| 主工作区 | 7 份架构文档修改及 `docs/stages/wuji-maf-architecture/` 未提交 | 上一轮草案保留，不覆盖活动 vNext 实施 |
| vNext 工作区 | P06 修复代码、迁移、测试和证据尚未提交 | 当前最需要保护和收口的工作内容 |
| CodeGraph | 两个工作树均无 `.codegraph/` | 本轮按仓库规则回退 Git、`rg` 和源码直接读取 |

vNext 相对 W1 增加约 865 个文件，其中 722 个位于 `docs/vnext/evidence/`。这些文件主要是按证据要求保存的 HTTP、SQL、身份、截图、测试结果和摘要清单；文件数量不能作为产品完成度指标。

当前新代码主要位于：

- `packages/wuji-core/src/wuji_core/`
- `packages/maf-worker/src/wuji_maf_worker/`
- `packages/contracts/openapi-v2.yaml`
- `tests/vnext/`
- `scripts/vnext/`
- `ops/vnext/`

## 3. W1 已交付基线

旧线仍是当前已交付、可追溯的运行机制基线：

- Phase 1A 已集成身份、项目、数据库、生命周期与五套主题；完整验收仍为 partial，保留 3 项真实回调待测。
- Phase 1B 已实现 Scope、预览、任务创建、查询、取消、幂等回执和事件同步的最小闭环。
- Phase 1C 已在封闭夹具中完成 Task 创建、显式启动、Cairn/Pi/LiteLLM、双容器 Task Pod、共享 Kali、证据、结果和停止闭环。
- W1 已完成有限 Web 评估机制、三类结果、关系视图和 Pi 原生压缩验证。

W1 不证明真实模型自主效果、真实外部目标、生产出口、完整流量采集或生产可用性。详细边界见 [W1 验收记录](../stages/phase-2-web-assessment/acceptance.md)。

vNext 不继承旧线的产品通过状态。旧实现和证据继续保留为历史来源，但新运行、查询和新发布物不得依赖 Cairn/Pi 执行内核。

## 4. vNext P00—P20 实际进度

| 任务 | 状态 | 已完成或待完成内容 |
| --- | --- | --- |
| P00 基线与来源 | accepted | 完成工作树、源码、设计来源、授权和环境边界核对 |
| P01 MAF SDK 探针 | accepted（局部能力） | 验证真实发行包、公开 API、工具往返、审批和 Session 恢复可行性 |
| P02 合同与测试底座 | accepted | 建立 OpenAPI v2、生成 DTO、严格 JSON、认证、RLS、ASGI 和真实 PostgreSQL 测试底座 |
| P03 持久化与证据 | accepted | 建立 Artifact、Observation、快照、发布租约、RLS 和原始字节边界 |
| P04 知识接纳与评估 | accepted | 建立 ClaimRevision、Fact 读视图、版本化评估、反证、可见性和新鲜度规则 |
| P05 控制与容量 | accepted | 建立 Task/Work/Run 状态、暂停叠加、依赖、容量及结果/进程分离 |
| P06 模型/工具准入 | under review fixes | 当前工作树 21 项聚焦测试通过；待提交、复审和最终证据包 |
| P07 MAF Worker | partial | ContextBundle 纯函数 8 项通过；SDK、工具、压缩、恢复未完成 |
| P08 Session 与审批 | not_run | 完整 SessionManifest、指定调用审批和原子消费未实现 |
| P09 持久 Scheduler | not_run | generation、waiter、公平策略和事务派发未实现 |
| P10 Supervisor | not_run | 新 Supervisor、Outbox 和 prepared/spawn 故障窗口未实现 |
| P11 控制与恢复联调 | not_run | 暂停、恢复、取消、审批和失败域未贯通 |
| P12 完成与报告协议 | not_run | Goal precheck、quiescing、ReportCommit 和迟到反证未实现 |
| P13 图投影 | partial | 纯 builder 9 项通过；持久快照、分页、历史、权限和 API 未实现 |
| P14 React Flow 画布 | not_run | 正式 `TopologyFlowCanvas` 尚未实现 |
| P15 ViewStream | not_run | SSE、重连、权限变化、历史模式和浏览器验证未实现 |
| P16 数据治理 | not_run | GC、purge、脱敏派生、审计、观测和交付策略未实现 |
| P17 核心端到端 | not_run | 75 项统一产品验收与故障矩阵未执行 |
| P18 效果评测 | not_run | 离线评测器未实现；真实模型试验另需 USD 授权 |
| P19 历史归档 | not_run | Cairn/Pi 历史只读导出、导入和切换演练未实现 |
| P20 发布与切换 | not_run | 新发布物、依赖清单、统一检查和生产切换未执行 |

## 5. 已完成切片及验证证据

### 5.1 P01：真实 MAF 公开能力

- 真实 `agent-framework-core 1.18.0` 和 `agent-framework-openai 1.14.3` 已锁定并核对发行物。
- 实际执行 `create_harness_agent → ChatClient → localhost 合成模型 → MAF 原生函数 → 第二次模型请求`。
- 验证 Session 序列化、跨进程恢复、审批批准/拒绝、未知工具、无隐式 HTTP 重试和默认工具裁剪。
- 证据：[P01 报告](P01-report.md)、[截图](evidence/P01/screenshots/test-results.jpg)、[完整 HTTP 包](evidence/P01/http-reproduction.md)。

### 5.2 P02：v2 合同和可信测试底座

- OpenAPI v2 成为外部 wire schema 单一来源。
- Python/TypeScript DTO 从同一合同生成。
- 严格拒绝重复 JSON key、非有限数字、非法控制字段和越界值。
- 建立真实签名身份、实际 ASGI、非 owner PostgreSQL 和 RLS 测试底座。
- 证据：[P02 报告](evidence/P02/report.md)、[截图](evidence/P02/screenshots/http-boundary.jpg)、[完整 HTTP 包](evidence/P02/http-reproduction.md)。

### 5.3 P03：规范持久化和原始证据

- 实现可信 Capture、Artifact staged/sealed、Observation、EvidenceReceipt、固定快照、发布租约和 GC 边界。
- 原候选执行 53 项检查，审查修复执行 6 项定向检查。
- 证据：[P03 报告](evidence/P03/report.md)、[截图](evidence/P03/screenshots/overview.jpg)、[完整 HTTP 包](evidence/P03/http-reproduction.md)。

### 5.4 P04：候选知识、Fact 视图和评估

- Agent 可以提出候选事实、摘要和假设，但不能写 FactAssessment 或伪造采集身份。
- ClaimRevision 为断言正文唯一来源；Fact 是符合评估策略的读视图。
- 支持版本化评估、反证冲突、旧版本失效、隐藏反证可见性和 read-set 新鲜度。
- 证据：[P04 报告](evidence/P04/report.md)、[截图](evidence/P04/screenshots/knowledge-and-visibility.jpg)、[完整 HTTP 包](evidence/P04/http-reproduction.md)。

### 5.5 P05：执行控制、状态和容量

- Task、WorkItem、AgentRun、结果、进程和外部操作分别维护状态。
- Task pause 与 Work hold 分别保存；恢复 Task 不解除用户 hold。
- 结果 accepted 不释放仍可能运行的进程容量。
- 原候选 28 项通过，复审修复 3 项通过。
- 证据：[P05 报告](evidence/P05/report.md)、[截图](evidence/P05/screenshots/control-verification.jpg)、[完整 HTTP 包](evidence/P05/http-reproduction.md)。

### 5.6 P06：模型/工具准入当前状态

P06 初始候选 `f32678d` 已实现：

- Run 限定模型和工具准入；
- Task 网关 Key 仅由 Gate 解析；
- 模型发送、响应、费用、本地状态分轴记账；
- 累计模型请求、工具调用和输出字节限制；
- 稳定 ToolCall、ToolAttempt 和逻辑请求身份；
- `workspace_read` 无害真实执行；
- 证据先持久化再向 Agent 返回；
- 请求重放、冲突、查询和部分流处理。

初始候选 13/13 通过，但独立审查发现：

1. 模型发送前崩溃可能永久锁住 inflight；
2. 取消登记后崩溃可能导致取消不再投递；
3. 模型和工具数据库写权限没有按 purpose 严格隔离；
4. 合法 `tools: null` 可能触发内部异常；
5. 模型可能宣告尚未实际装配的工具；
6. 输出达到限额时可能丢失已获得的部分结果；
7. OpenAPI 缺少模型重放响应头。

当前未提交修复已加入相应实现、迁移和测试。本报告生成前重新执行：

```text
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_run_admission.py -q

21 passed in 22.86s
```

合同检查：

```text
work/toolchain/bin/pnpm contracts:check:v2

exit 0
Generated Python and TypeScript v2 contracts match OpenAPI.
packages/contracts/openapi-v2.yaml: validated
```

保留一个既存警告：`AgentPayload` 组件当前未被其他 OpenAPI schema 引用。

该 21 项结果只是当前未提交工作树的状态核验，不是新的正式验收成果。修复候选尚未形成固定 SHA、复审结论、最终截图和完整请求包，因此 P06 保持未 accepted。

初始候选证据：[报告](evidence/P06/full-candidate-1/report.md)、[截图](evidence/P06/full-candidate-1/screenshots/final-verification.png)、[完整 HTTP 包](evidence/P06/full-candidate-1/http-reproduction.md)。这些材料绑定修复前 `f32678d`，不能替代当前修复候选的最终证据。

### 5.7 P07 与 P13 提前完成的纯函数切片

- P07 ContextBundle：8 项通过，仅证明受限上下文纯构建与直接输入边界；真实 SDK、模型、工具、压缩、Session 和恢复均未执行。
- P13 projection builder：9 项通过，仅证明节点身份、Fact/Claim 展示、关系端点、冲突拒绝和公开字段白名单；数据库、HTTP、权限、快照和历史均未执行。
- P13 证据：[纯投影报告](evidence/P13/pure-green/report.md)。

上述纯函数切片没有符合完整 HTTP/UI 成果要求的截图和请求包，因此只作为前置切片记录，不作为 P07 或 P13 完整交付验收。

## 6. 已冻结的开发方向

### 6.1 新执行内核

```text
Wuji API / Control
        ↓
Wuji Blackboard
        ↓
Wuji Scheduler
        ↓
MAF Supervisor
        ↓
Python MAF Worker
        ↓
Model Gate / Tool Gate
        ↓
LiteLLM / 受控工具 / Evidence Capture
```

MAF 只负责单个 Agent 的模型—工具循环；Wuji 负责全局任务、调度、授权、预算、证据接纳、控制和完成判断。

### 6.2 知识和证据

- `ClaimRevision` 是断言正文唯一来源。
- Fact 是 `ClaimRevision + 有效 FactAssessment` 的受权读视图。
- Agent 可以提出 candidate fact、解释和假设，但不能自行认证为 Fact。
- 未验证假设可以驱动受控探索，但不能扩大 Scope、授权或直接满足 Goal。
- Artifact、Observation 和工具回执独立于 Agent 最终输出持久化。
- 评估同时区分 grounding、evidence、applicability 和 producer，不采用“最后写入者获胜”。

### 6.3 生命周期和控制

```text
Task
  └─ IntentRevision
       └─ WorkItem
            └─ AgentRun
                 └─ Session
```

以下状态独立表达：

- 结果是否接纳；
- 进程是否退出；
- 工具操作是否结算；
- 模型响应是否完整；
- 模型费用是否核对；
- Task 是否关闭；
- Goal 是否满足。

Task pause 与 Work hold 分别保存。旧凭据、旧 epoch 和旧 runtime attempt 不得产生新动作，但撤销身份不能假装已经停止外部操作。

### 6.4 Scheduler

- 首版采用单活动持久 Scheduler。
- 策略选择是纯函数，不直接生成执行许可。
- 派发事务重新检查 Scope、Profile、依赖、容量、预算、deadline 和运行身份。
- `trigger_generation` 独立于 Blackboard revision，避免丢失依赖、输入和反证事件。
- waiter 登记和条件检查在同一事务完成。
- Reason 自己产生 Intent 不立即反向触发下一轮 Reason。
- 工作数、Reason 次数、模型请求、工具调用、输出字节和失败重试均受累计上限约束。

### 6.5 MAF Worker

- 使用真实 Python MAF 公开接口，不修改 SDK 私有实现。
- 不实现第二套 Agent 循环。
- 默认关闭 Shell、WebSearch、任意文件访问、后台 Agent 和动态 Skills。
- 工具清单只来自已发布 Profile。
- 模型请求全部经过 P06 Model Gate。
- 函数和 MCP 工具经过同一 ToolAdmission。
- Worker 不持 Task 网关 Key。
- Worker 独立消费 SDK 流，前端 SSE 断开不能取消执行。

### 6.6 Session 与审批

- SessionManifest 固定 history、memory、provider state 和 pending operation。
- 不可变对象完整保存后，以 CAS 发布 manifest。
- 半提交对象不能作为恢复点。
- 审批绑定原始 ToolCall 和参数摘要。
- 批准消费与唯一 ToolOperation 原子提交。
- 重启和重放不能把同一批准变成第二次执行。
- 批准不解除 Task pause 或 Work hold。

### 6.7 完成协议

任务结束采用两阶段协议：

1. `precheck`：检查必要工作、Goal 判据、证据、反证和未决审批；
2. `quiescing`：冻结新动作，仅允许已登记操作、证据、结果和退出回执结算。

最终分别保存关闭触发原因、结果完整度、Goal 状态、ReportCommit、ReportDelivery、费用待核对状态和环境清理状态。

### 6.8 前端受权图

- 使用 `@xyflow/react` 实现正式 `TopologyFlowCanvas`。
- 图是领域投影，不是数据库或执行队列。
- Fact/Claim 显示变化不复制正文节点。
- 节点身份包含 revision，旧关系不自动迁移到新 revision。
- 拖动只更新个人 LayoutPreference。
- 禁止自由连线创建业务关系，禁止从画布删除证据。
- ViewStream 使用受权视图版本和不透明 cursor，不暴露内部全局事件序号。
- 保留五套主题、键盘操作和列表替代视图。

### 6.9 新旧系统切换

- 新 schema、新 Worker、新 Supervisor 和新发布物独立构建。
- 开发阶段不修改旧生产 Supervisor 的启动逻辑。
- 历史只读归档可以解析旧 SQLite/JSON，但新运行服务不能调用 Cairn。
- 生产切换前必须停止并核对旧执行、校验归档、保留产物和权限映射。
- 无法确定旧操作状态时阻断切换，不删卷。
- 生产切换、旧数据删除和重新开启旧部署分别需要明确授权。

## 7. 后续实施顺序

### 7.1 当前第一优先级

```text
P06 修复代码与迁移固定提交
  → 7 项问题定向复审
  → 固定被测 SHA
  → 生成截图、完整 HTTP 包和摘要清单
  → P06 accepted
```

### 7.2 核心运行路径

```text
P06
  → P07 完整 MAF Worker
  → P08 Session/审批
  → P09 持久 Scheduler
  → P10 Supervisor
  → P11 控制与恢复联调
  → P12 完成和报告
  → P17 核心端到端与故障矩阵
```

P09 只依赖 P04、P05、P06，因此在 P06 交接后可以与 P07 的部分实现并行；P10 需要 P07 与 P09 都完成后才能正式汇合。

### 7.3 图与前端路径

```text
P06 交出迁移与共享接口所有权
  → P13 持久投影、快照和 API
  → P14 React Flow 工作台
  → P15 ViewStream、历史和浏览器验证
  → P16 数据治理、交付和观测
```

### 7.4 归档、发布与效果评测

```text
P12 + P13
  → P19 历史只读归档和切换演练

P17 + P19
  → P20 新发布物和显式切换

P07 + P09 + P17
  → P18 离线效果评测工具
  → 经单独授权后运行真实模型试验
```

## 8. 当前风险、限制和待处理事项

1. **P06 工作树尚未提交。** 当前修复、测试、迁移和证据不能清理或覆盖。
2. **P06 尚未复审。** 21/21 只能说明当前聚焦测试绿色，不能说明 7 项审查发现已正式关闭。
3. **修复证据包尚未完成。** 当前 raw 记录已经产生，但仍需固定 SHA、报告、截图、完整 HTTP 包和摘要清单。
4. **主工作区上下文落后。** 主工作区旧草案仍写“仅设计”，活动 vNext 索引已明确进入实施；集成时需要同步权威索引。
5. **vNext 没有远端分支。** 当前成果仅在本机 Git 对象和工作树中。
6. **完整 MCP transport 未验证。** 当前环境没有 `mcp.types`；P06 仅验证缺失时 fail closed，正式 transport 属于 P07。
7. **正式 MAF Worker 和 Scheduler 未贯通。** 目前还不能完成真实任务循环。
8. **正式前端未开始。** P13 只有纯 builder，P14/P15 尚未执行。
9. **统一产品验收未完成。** 75 项 AC 仍需 P17 汇总真实运行证据。
10. **Docker/Kubernetes 环境待恢复。** P00 核对时 Docker daemon 不可用；当前隔离 PostgreSQL 可用，但后续 Supervisor/Kubernetes 集成需要重新确认环境。
11. **真实模型和真实目标未授权。** 未运行真实 LiteLLM 计费核对、付费模型、外部目标或生产出口。
12. **生产操作未授权。** 未执行推送、部署、停机、切换、旧数据删除或持久卷清理。

## 9. 总体判断

当前架构路线已经稳定，后端领域核心已完成基线、合同、证据、知识和控制五层基础。项目尚未进入完整用户运行闭环，关键原因是 P06 仍处于修复复审门禁，P07/P09/P13 的后续持久集成均受该门禁影响。

下一阶段不需要重新讨论总体架构，首要工作是固定 P06 修复候选并完成合规证据与复审。P06 accepted 后，项目将进入 MAF Worker、持久 Scheduler、Supervisor 和 React Flow 工作台的并行贯通阶段。

