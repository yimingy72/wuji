# Agent 执行框架与 LangGraph 的职责划分

> 2026-09-10 P0增量：[受限适配验收](stages/phase-1c-prep-p0/acceptance.md)已通过：Deep Agents 0.7.13的单工具往返及OpenAI/Anthropic原生客户端接入。本页此前“尚未集成验证”描述适用于当时；正式Agent、长上下文、持久恢复与完整流式能力仍未验收。

> 2026-09-10 阶段更新：下一步已包含基础模型配置与待细化的显式连接检查，详见 [Phase 1C 前置草案](stages/phase-1c-prep/spec.md)。本文“Phase 1 无模型闭环”指目标执行不依赖 Agent 推理，不排除已前移的配置能力；Harness 候选验证仍按后续独立切片进行。

- **日期**：2026-09-09
- **状态**：v0.4 复用边界已修订；具体候选与版本尚未集成验证
- **关联**：[主架构](architecture.md)、[模型网关实测](model-gateway-validation.md)、[开工计划](predevelopment-plan.md)

## 1. 决策

Wuji 应复用成熟的 Agent 执行框架。此前仅写“LangGraph 编排”没有覆盖完整的 Agent 执行层，本补充明确这一缺口。

确定职责边界：LangGraph 管任务流程与恢复，Agent Harness 管一次 AgentRun 内的模型与工具循环，平台控制授权、执行、证据和预算。增加薄的 `AgentDriver` 适配接口，使业务对象不依赖某个框架的会话格式。它不实现另一套通用 Agent 循环。

**首选验证 LangGraph + Deep Agents**，先验证单 Agent、受控 HTTP 工具和固定预算的最小配置。若默认工具、子代理或状态管理无法按边界收敛，首版采用 LangChain `create_agent` + 现成 SummarizationMiddleware，仍然复用上下文压缩。pi 保留为候选；Claude Agent SDK、Codex SDK 按专用 Worker 需求再接入；DeepSeek Harness 先做候选验证。一个 AgentRun 只绑定一种 Harness，不同时叠加多套循环，也不把“候选不通过”变成自研通用 Harness 的理由。

这是基于 Wuji 已选 LangGraph、需要恢复和平台工具控制的工程建议，并非所有候选的实测排名。Orchestrator 语言与框架版本仍须在 P0-02/P0-10 固定；前端采用 TypeScript 不代表后端必须同语言。

### 1.1 明确复用到什么程度

| 用户关心的能力 | 复用实现 | Wuji 自己实现的部分 |
| --- | --- | --- |
| 完整 Agent 循环 | Harness 的模型调用、工具分发和结果回传 | 工具绑定、领域输入输出及业务调用 ID |
| 上下文控制与压缩 | Harness 的历史、Token 估计、裁剪、摘要和结果卸载；精简方案用现成摘要中间件 | ContextPolicy 配置、证据引用、来源与保留权限；不写压缩算法或另一套历史管理器 |
| 打断与继续 | Harness / LangGraph 的中断、取消信号、恢复和事件 API | 将用户命令映射到 epoch、停止确认和重新授权，不自研协程/会话运行时 |
| 多模型接入 | 成熟 Provider 客户端与现有网关的协议实现 | 允许模型/能力配置、业务预算、路由规则和审计，不重写各厂商 SDK |
| 状态持久化 | 框架维护的 checkpointer/store 和序列化 | 租户归属、执行账本对账、版本与删除策略 |
| Skills 与工作记忆 | Harness 的加载机制及受限后端接口 | 发布版本、只读知识快照和 AgentRun 存储隔离 |

LangChain 的摘要中间件支持配置触发阈值、保留窗口和摘要模型；模型容量未知时不能盲用基于窗口比例的默认值。[中间件文档](https://docs.langchain.com/oss/python/langchain/middleware/built-in) 默认模型适配候选复用其现有 OpenAI 集成，具体网关特性必须实测。[模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/openai)

## 2. 四层职责

| 层次 | 负责 | Wuji 中的边界 |
| --- | --- | --- |
| 业务控制 | 租户、授权、Task、VerificationRun、账本、证据、预算、取消和回收 | 平台模块及 Router / Runtime / Egress 执行；模型只能提案 |
| 编排运行时 | 阶段推进、等待事件、中断、检查点、恢复 | LangGraph + Orchestrator / Dispatcher；持有单一任务执行租约 |
| Agent Harness | 模型调用循环、工具结果回传、上下文整理、可选规划与技能加载 | 每个 AgentRun 一个执行实例；经适配接口使用平台服务 |
| 模型接入 | API 协议、模型路由、用量与请求生命周期 | Wuji Model Gateway 接现有上游网关；上游 Key 留在后端边界 |

LangGraph 官方把自己定位为低层、有状态 Agent 编排运行时；LangChain 提供常用 Agent 抽象，Deep Agents 在其上提供规划、上下文管理、子代理等 Harness 能力。因此“使用 LangGraph”不等于自动获得完整的执行框架。[LangGraph 官方说明](https://docs.langchain.com/oss/python/langgraph/overview)

```text
Console -> Platform API -> Task / Scope / Ledger / Evidence
                              |
                  Orchestrator（LangGraph）
                              |
                    AgentDriver -> Harness
                         |              |
                 Model Bridge       Tool Bridge
                         |              |
                Wuji Model Gateway  MCP Router
                         |              |
                 已有模型网关       Runtime -> Egress -> 授权目标
```

## 3. 候选方案

| 方案 | 已提供的能力 | Wuji 的取舍 |
| --- | --- | --- |
| LangChain `create_agent` | 模型与工具的执行循环，基于 LangGraph 运行 | 最小单 Agent 切片配现成摘要中间件；平台只补策略与集成。[官方文档](https://docs.langchain.com/oss/python/langchain/agents) |
| Deep Agents | 基于 LangGraph 的 Harness，含上下文整理、文件系统抽象、规划及子代理能力 | 优先做受限配置验证，复用执行能力；默认工具和子代理须逐项收敛。[官方文档](https://docs.langchain.com/oss/python/deepagents/overview) |
| pi agent core | 可嵌入的 Agent 状态、工具、流式事件与上下文转换接口 | 适合希望精简控制层或选择 TypeScript Orchestrator 的方案；仍需接平台恢复和账本。[官方仓库](https://github.com/earendil-works/pi/blob/main/packages/agent/README.md) |
| pi coding-agent SDK | 在核心循环之上提供会话、压缩和可嵌入的 Harness | 如果选 pi 来复用完整上下文能力，应评估这一层，不能只引入 agent core 后再自写压缩；默认 read/write/edit/bash 须收敛到平台允许能力。[官方文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md) |
| Claude Agent SDK | Claude Code 的执行循环、工具、上下文管理及会话能力，提供 Python / TypeScript SDK | 可作为专用 Worker；需实测网关、模型与完整 SDK 行为，Messages 接口通不代表 SDK 已兼容。[官方文档](https://code.claude.com/docs/en/agent-sdk/overview) |
| Codex SDK / Codex Harness | SDK 控制 Codex Agent 的启动、线程续接与运行；底层运行时提供执行能力 | SDK 与 Harness 是控制接口和运行时的关系；作为一个适配方案评估，不拆成两套必选框架。[官方文档](https://learn.chatgpt.com/docs/codex-sdk) |
| DeepSeek Harness | 基于 Cordis 插件体系组织工具、模型、会话和运行能力 | 借鉴插件边界与生命周期；仓库目前标为开发预览，预期有破坏性变更，须先验证再考虑成为核心依赖。[官方仓库](https://github.com/deepseek-ai/deepseek-harness) |

这些框架主要解决“Agent 如何运行”。它们不会自动实现 Wuji 的 ScopePolicy、执行许可、目标出口、VerificationRun、证据可信度或取消后的资源回收。

## 4. 适配与恢复约束

`AgentDriver` 首版只需表达以下概念，具体语言签名和 Schema 在实现时固定：

- 输入：平台派生的租户/任务/AgentRun 身份、配置快照、已限定的工具与模型句柄、剩余预算、截止时间和取消信号。
- 操作：启动、订阅规范化事件、读取可恢复位置、请求停止；不支持恢复的适配器必须明确报告能力。
- 输出：结构化结论、证据引用、后续 Intent 提案、框架版本与会话引用。费用与实际执行用量以平台账本为准。

LangGraph 外层拥有 Task 阶段和主编排租约；Harness 内层拥有当前 AgentRun 的循环位置。使用同属 LangGraph 的框架时按受控子图或子调用集成，避免两个独立调度器同时推进任务。嵌套图的中断传播与恢复语义须实测，不能仅凭框架名称推断。

框架会话 ID 映射到租户限定的 AgentRun，不向用户直接暴露可跨任务续接的底层句柄。每次工具调用在派发前固定业务调用 ID；恢复先查 Router 账本，不能因为内层重新生成 tool call ID 就重复访问目标。检查点与业务账本不假定同事务提交。

全部模型调用经过 Wuji Gateway；目标工具经过 Router，业务工具访问已鉴权的平台模块，待办/工作记忆工具使用限定后端。第三类不能获得目标网络、任意代码执行或改写业务结论的能力，其内部状态仍受配额与审计约束。默认 shell、任意宿主文件写入、外部网页访问、自动发现 MCP/插件等能力必须禁用或改接受控接口；不能挂载开发者真实工作目录。Agent 不获得上游 Key；独立 SDK Worker 若要求 API 凭据，使用只能访问 Wuji Gateway 的短期限定凭据。

Deep Agents 不能仅传入自定义工具就视为已移除默认工具；实际工具清单、文件系统后端及子代理配置均需核验。其自带文件系统权限不等同于任意代码执行的隔离边界。首个配置不允许 Harness 自行创建 Worker；后续子代理须经 Dispatcher 分配身份与预算。[Deep Agents 配置说明](https://docs.langchain.com/oss/python/deepagents/overview)

停止 Harness 仅停止推理请求。平台取消仍须撤销新派发许可、处理在途调用、等待出口断流并回收资源；不能用 SDK 的 abort 返回值宣告 Task 已完成取消。

框架压缩、工具选择与自动评估可能使用辅助模型，必须显式注入同一受控模型客户端并登记 `purpose`，统一预占、结算和取消。模型调用上限覆盖这些内部请求。框架 transport retry 与模型主动纠错分开：前者服从 Gateway，后者是有预算上限的新回合；工具结果 unknown 不能作为可自由重试的普通错误反馈给循环。

上下文只由 Harness 维护；Gateway 不二次整理历史。平台策略从服务端装配，来源摘要保持数据身份，原始证据另存。框架默认记忆文件、检查点与 trace 继承任务数据策略，底层库表的租户隔离必须单独验证，不能假设业务 RLS 自动覆盖。

## 5. 模型网关的接入方式

用户提供的 Baizhi 网关可作为 Provider Adapter 的上游，不需要再默认串联 LiteLLM、Bifrost 等额外代理。Wuji Gateway 首先实现平台需要的策略、用量、预算、请求幂等和审计；协议转换优先复用已有客户端。

两个 base URL 分别提供 OpenAI 与 Anthropic 兼容协议，不代表两个独立模型供应商，也不证明两份配额。当前返回列表一致且未列出 `claude-*` ID；模型别名、真实模型、账户配额关系和收费规则须由上游信息确认。开发时可以先施加共享的保守总限额，但不能把这一限额当作已经确认的真实 QuotaGroup 映射。

本轮已验证 `qwen-flash` 的 Chat Completions / Messages 工具往返和 Responses 非流式文本请求。Codex 的自定义 Provider 配置涉及 base URL、认证与 wire API；仍需独立验证 SDK 使用的流式事件和模型能力，不能从普通 Responses 成功直接推导 Codex SDK 完整可用。[Codex 配置说明](https://learn.chatgpt.com/docs/config-file/config-advanced)

## 6. 验证与交付顺序

Phase 1 继续实现无模型的受控 HTTP 闭环；本决策不把所有候选接入变成开工前提。P0-10 在 Phase 2 前完成一个候选的最小集成验证，失败再按原因切换候选：

| 验证 | 必须保留的证据 |
| --- | --- |
| 实际依赖与工具表面 | 锁定版本、真实工具清单；未开放 shell、任意网络或自动加载本机技能 |
| 模型与工具往返 | 流式文本/工具事件、工具 ID 对应、非法参数处理、用量结算；不能只验证连通 |
| 单 Agent 业务闭环 | 受控夹具观察 → Router 调用记录 → 证据 ID → 结构化验证提案 |
| 恢复与结果不明 | 工具执行后故障、检查点落后、进程重启；凭账本不重复访问目标 |
| 取消与预算 | 取消后停止新增请求；超时保留未知用量；记录 SDK 和上游的重试行为 |
| 不可信输入 | 目标文本诱导使用未授权工具、扩大范围或读取本地凭据时，执行端仍拒绝 |

通过后只固定这一套默认 Harness。新增专用 Worker 的 SDK 必须通过同一适配契约；不将 SDK 返回的自然语言直接写成已确认漏洞。

完整验收以 [H01–H10](architecture-acceptance.md) 为准，含真实触发压缩、压缩后核对原证据、辅助调用预算、打断恢复与持久/临时事件区分。当前接口 ping 结果不能替代这些验证。

## 7. 元刃参考复核（2026-09-10）

[元刃后端复核](metablade-backend-review.md)确认继续借鉴平台侧 Agent/容器工具分离、角色任务书、按需知识与后台完成交接。用户提供的原文混有环境观察、工具定义和模型自述；Claude Code 风格提示词、工具名称及模型枚举不能证明其使用某个 SDK，也不能确认其上下文压缩、检查点和取消机制。

因此保留上述复用决策，不因相似性改选 SDK，也不自研通用 Harness。Wuji 补充 WorkerAssignment、AgentRunResult 和问题/回答领域归属，映射到既有 AgentDriver 与框架中断/恢复接口；不维护另一份可写会话或循环。框架是否真正具备受限工具、预算和恢复能力仍由 Phase 2 的单候选集成验证决定，本次静态复核不追加测试矩阵。

LangGraph 同时具备共享 State/reducer、子图输入输出、跨 thread Store、动态 Send/Command；不能把本文件的“领域数据由平台管理”误解为框架没有共享能力。Wuji 复用这些机制，黑板只补 Fact/Intent/Hint、证据关系和结论接受等领域规则；共享状态以领域记录引用为主，避免与 PostgreSQL 维护两份可写事实。详见 [LangGraph 与黑板复用边界](cairn-blackboard-design.md#11-langgraph-已有共享能力与复用方式)。
