# Wuji 黑板架构：参考 Cairn 的领域适配

日期：2026-09-10。状态：**用户已明确要求采用黑板架构；本文为待阶段 Spec 固定的适配设计**。不表示当前 0.4.0 API 已实现黑板。

明确参考 [oritera/Cairn](https://github.com/oritera/Cairn)。其官方[协作探索协议](https://github.com/oritera/Cairn/blob/main/docs/specs/server-protocol.md)直接使用“衍迹（Cairn）”名称；这能确认参考项目的关联，不能据此证明用户调研到的商业界面与公开仓库版本完全相同。

## 1. 设计决定

Wuji 的 Agent 协作以**共享黑板驱动探索**。Worker 基于已记录的事实、未完成方向和提示提出下一步工作，结构化结果回到黑板，再触发后续判断。角色是能力/方法配置，不是必须逐个经过的 Planner → Explorer → Verifier 固定流水线。

元刃参考用于平台/Runtime 分层、成熟 Harness、角色配置和产物交付；Cairn 参考用于共享知识与协作协议；衍迹 UI 调研用于黑板、时间线、证据和结果的联动。三者各自解决不同问题，不把三个完整引擎叠加部署。

```text
用户目标 / 授权对象 / 冻结配置
                ↓
Task Blackboard：Origin、Goal、Fact、Intent、Hint
        ↓ 读取同一版本的态势                 ↑ 原子记录结果与事件
Orchestrator + Dispatcher ── 派发 ──→ AgentDriver / Harness
        │                                  │
        │                                  ├─ 模型 → Model Gateway
        │                                  └─ 目标工具 → Router → Runtime → Egress
        └─ 校验执行归属、候选结果、证据 → Blackboard / Assessment
```

LangGraph 仍管理持久生命周期、等待和恢复；Dispatcher 根据黑板和预算分派工作；Harness 管一次 AgentRun 的模型/工具循环和上下文。**Blackboard 是共享领域状态，不是另一份聊天历史、另一套调度器或一个必需的图数据库。**

## 2. 参考的核心及证据范围

Cairn README 描述 Fact/Intent/Hint、无固定角色的 Worker、通过共享图间接协作，以及 Dispatcher 统一写入探索结果。[README](https://github.com/oritera/Cairn#how-it-works)

协议把 Fact 定为追加记录，Intent 连接一个或多个起点与探索结果，Hint 是图外提示；认领/心跳用于协作，完成/重开是显式动作。[协议](https://github.com/oritera/Cairn/blob/main/docs/specs/server-protocol.md)

这些是借鉴的协作抽象，不直接继承它的项目状态、身份字段、超时参数或“文本结论即事实”接受方式。Wuji 要承接既有任务账本、Scope、验证及报告契约，具体适配如下。

## 3. 作用域与对象

**一个 Wuji Task 对应一块任务黑板。** Cairn 的 Project 表示一个问题实例，不能机械映射成 Wuji 的项目：Wuji 一个项目含多个授权、身份、预算和时间不同的 Task，不能共用一张可自由写入的执行黑板。

| 对象 | Wuji 含义 | 不能混同 |
| --- | --- | --- |
| Origin | 冻结的起始对象、已知输入及其来源，引用 ConfigSnapshot | 用户输入的断言不自动成为已验证事实 |
| Goal | 有版本的目标和完成标准，引用 Scenario/CoveragePlan | 目标尚未达成，不能作为“已经为真”的普通 Fact |
| Fact | 有来源、适用对象/身份/时间、证据关系的事实记录 | 模型印象、用户 Hint、已确认漏洞或执行许可 |
| Intent | 基于若干已知依据准备探索的问题、方法和完成标准 | 已执行的工具调用、固定 Agent 职位或授权扩展 |
| Hint | 人或 Agent 提交的建议、关注点和态势判断，保留作者与来源 | 更高优先级系统指令、Scope 更新、停止/恢复命令 |
| Observation / Artifact | 原始观察与证据内容 | Fact 自述文本；文件路径本身不代替有权限的证据引用 |
| VerificationRun | 对主张、方法和证据进行核实的领域单元 | 必须另启动一个“验证者 Agent”；单 Agent 也能推进验证 |

现有 Fact/Intent/Observation/EvidenceLink 等对象继续使用，不为“黑板”再复制一套平行事实表。新增 Hint 和黑板版本/关系投影等必要契约。跨 Task 参考必须显式记录来源任务/时间/身份，重新检查当前权限，不能在项目级自动传播成新任务事实。

## 4. 因果关系与冲突

- 一个 Intent 可以由多个 Fact/Observation 引用共同支持；保存全部输入关系，不能只保留一个父节点。结果关联可引用多个事实及证据。
- Fact 内容追加而不覆盖。新证据与旧记录矛盾时追加反驳/替代关系，界面显示“存在冲突/已被后续记录修正”；不删除旧事实来让图变得整齐。
- 探索因果边只引用已有输入，再产生新结果，形成可追溯的无环因果图。反驳、适用范围和相似性是独立类型的关系，不假装都是时间上的因果边。
- Intent 可以受阻、取消或无有效证据；这种执行结果如实记录，不能为了画出一条 Fact 边伪造“未发现漏洞”。
- 模型提交的是候选内容。Blackboard/Assessment 校验来源、归属、输出 Schema 与规则，不能由 Worker 任意设置“已确认漏洞”；不把结构校验通过宣传为已证明业务结论正确。

## 5. 统一写入口与原子操作

采用一个**逻辑写入口**：API 内的 Blackboard 领域服务。模型/Worker 无直接数据库写权限；Dispatcher 提交 Agent 结果，用户 Hint 经鉴权 API 提交，两者都经过同一领域约束。不是所有请求必须由一个全局 Python 进程串行处理。

| 操作 | 必须同事务完成的内容 |
| --- | --- |
| 提出方向 | 当前任务状态/权限检查，来源引用、方法与去重检查，Intent 及其输入边，黑板版本与事件 |
| 认领 | Task/Intent 版本检查、唯一 owner、递增 fencing token、预算/租约关联、事件 |
| 提交结果 | 当前 owner/epoch、调用账本和证据归属校验，结果记录及关系、Intent 结论、黑板版本与事件 |
| 添加提示 | 服务端派生作者/权限、Hint 内容与来源、版本与事件；不派发目标调用 |
| 判定完成 | 验证目标/覆盖/限制，确认无活动或未知调用、出口隔离；Task 完成与原因单独记录 |

“单写入口”是约束集中，不是把所有状态交给模型或靠一把全局锁。Task 控制、Assessment 和黑板仍在同一 PostgreSQL 权威边界协调。历史事件和完成通知都是结果的投影；通知丢失后读取结果，不能从头重跑已提交探索。

## 6. 动态探索、角色与 Harness

起步可以做一条明确的观察，也可以基于当前信息提出多个 Intent；不要求每个任务先调用一遍所有角色。可选的“分析态势/探索方向/检查完成”是调度工作类型，不是需要各自启动常驻服务的角色。

AgentProfile 保留模型、工具、Skill、输出 Schema 和能力限制。默认以通用 Worker 从当前可执行 Intent 取任务；需要专门 Adapter、身份或审核职责时才匹配专用配置。验证的可靠性来自 VerificationRun 的方法与证据，不来自角色名字或多个模型投票。

外层 LangGraph 执行既有领域操作，例如读取态势、请求一次 AgentRun、等待结果、提交结果、处理控制命令；不再把“规划 Agent → 探索 Agent → 验证 Agent”写死为必须经过的业务图。内层 Harness 的自动子代理首版继续关闭，Phase 3 分派全部走 Dispatcher。

续约过期仅说明所有权失效，不证明外部调用已停止。旧 Worker 的迟到写入由 fencing 拒绝；存在未知调用时先核对账本和隔离旧执行，不立刻把同一意图重新发给新 Worker 重试。

## 7. Hint 与人工介入

详情中的“补充提示”可挂到整个任务或某个 Intent，保存作者、时间、来源与可见范围。示例：“重点解释当前响应头的影响；没有证据的项目请标明未检查。”提示只是建议；后续规划记录读取了哪个黑板版本和哪些提示，不声称提交后立即改变在途调用。

区分三种动作：

1. **Hint**：非阻塞的关注点/解释，供下一次决策参考。
2. **回答问题**：回应具体问题 ID，检查问题版本和允许回答者，安全边界消费一次。
3. **控制/授权变更**：启动、暂停、取消、Scope 或预算变更，必须使用对应受控命令，不能用 Hint 实现。

用户提示和 Agent 态势总结均有明确来源。派发上下文时不能把摘要中的 Hint 升级成可信事实或平台规则。添加新资料/身份/方法仍按已确认产品设计创建关联任务。

终态任务允许按权限添加复盘备注或下一次复测建议，但不恢复执行、不改已冻结报告。Wuji 不直接复制 Cairn 的 completed → reopen 执行语义；需要继续时建立关联新 Task，并显式引用原黑板中的历史依据。

## 8. 读取、上下文与前端

黑板快照与事件位置保持一致，提交通过后再推进版本。关键参数来源为 Task 和配置记录，不能从图布局反推授权或实际执行状态。

小图可以读取完整逻辑快照；图变大后按当前 Intent 的祖先依据、有关提示和增量记录提供受限上下文包，包含 board_version、选取依据、截断/省略说明及可按权限展开的引用。所有 Worker 可在其任务权限内查询共享依据，但不必每次向模型重新发送全部原始证据。不得用摘要冒充原始完整图。

上下文压缩仍由 Harness 负责。Blackboard 保留可查询的领域记录，不替代 Harness 历史，也不允许 Harness 的 Todo/记忆文件直接修改黑板事实或 CoveragePlan。

前端提供“黑板 / 时间线 / 结果”关联视图：点 Fact 看证据，点 Intent 看依据、认领和结果，Hint 显示作者与处理上下文。先提供紧凑关系卡/列表与局部关系，再增加完整图操作；不能只有一个漂亮关系图而没有写入/认领/恢复协议。首批 HTTP 仍以观察记录为主，完整 Agent 原型展示黑板交互。

## 9. 分阶段落地与既有进度

| 阶段 | 黑板范围 |
| --- | --- |
| 当前交互原型 | 合成 Fact/Intent/Hint、关联证据与提示输入；清楚标为规划体验 |
| Phase 1C/D | 为后续黑板建立真实 Task/ToolCall/Artifact 依据；不虚构 Agent 或补做完整多 Agent |
| Phase 2 | 最小黑板领域协议：Fact/Intent/Hint、输入/结果关系、版本与事件、单 Agent 读写闭环和人工提示；与 Harness 选择一起确定具体 Spec |
| Phase 3 | 多 Worker 动态认领、fencing、共享事实、去重与依赖交接；沿用 Phase 2 黑板和验证对象 |
| Phase 4 | 完整关系查询、冲突研判、历史回放及报告冻结引用；不是到此时才第一次实现黑板 |

当前 B2/B3 的 task_events 是任务管理事件，不是已经实现了 Fact/Intent/Hint 黑板。原“共享事实”的宽泛描述需要以本文件的最小领域协议补齐。新增 Hint 与图关系、动态调度策略是设计增量，进入实现前更新对应阶段契约和迁移；本轮不修改 OpenAPI 或数据表。

## 10. 最小检查范围

本次只读参考资料与代码，不运行 Cairn、不安装它的执行环境、不增加模型调用或测试。后续测试并入对应阶段已有预算：一个事实→意图→结果链、一个人工 Hint、重复认领/迟到结果拒绝、停止后不续作即可；不为黑板另建无上限的全图/全模型/长时间故障矩阵。

参考是架构语义，不在本轮把 Cairn 作为运行依赖，也不复制其执行代码。实际源码固定版本与协议差异由独立静态核查附记记录。

## 11. LangGraph 已有共享能力与复用方式

2026-09-10 核对官方文档：LangGraph 提供共享 State/reducer 和动态 Send/Command；子图既可使用共享状态键，也可保留各自上下文并通过输入输出交接。它不是只能表达固定流程的工具。[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[子图](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)

checkpoint 保存 thread 的执行状态；Store 支持跨 thread 共享数据。仅有 checkpointer 不会自动形成跨 thread 共享存储。[持久化](https://docs.langchain.com/oss/python/langgraph/persistence)

| 需求 | 复用 LangGraph | Wuji 的领域补充 |
| --- | --- | --- |
| 多 Agent 看见共同结果 | State/子图接口；跨 thread 使用受控 Store 或领域查询 | 黑板版本、证据引用、用户/项目/任务权限及 Hint 来源 |
| 合并并发输出 | 为状态键定义 reducer | 幂等记录 ID、结论版本和矛盾关系；合并列表不等于判定哪个结论真实 |
| 动态派发/交接 | Send/Command/条件边与子图 | 只派发已认领并具备预算/执行许可的 Intent；不建立第二个框架调度器 |
| 中断/恢复 | checkpoint 与 interrupt/resume | 人工问题归属、停止核实、重鉴权及账本核对 |
| 共享长期材料 | Store 的 namespace/key 与查询接口 | 访问控制、分类和保留；namespace 不是天然租户隔离证明 |

小型演示可以将事实列表放进共享 State；Wuji 的正式方案选择让 PostgreSQL 领域表保存 Fact/Intent/Hint 与元数据，对象存储保存原始证据，LangGraph 状态保存记录 ID、board_version、当前工作位置和必要缓存。节点通过薄领域适配器读取/提交黑板，不把两份可写事实分别放在 State/Store 与业务数据库。

这是为了复用现有领域事务与权限，**不是 LangGraph 无法保存事实数据**。需要框架 Store 的工作记忆与跨会话内容继续复用其接口，但不能作为第二个证据/结论权威。Reducer 的结构合并也不能代替 VerificationRun 的结论接受规则。

还需区分两种“图”：LangGraph 图的节点是计算步骤/Agent，边表示控制流；黑板图的内容是依据、探索和结果，关系表达因果。前者负责怎样执行，后者提供当前为什么执行这一步及得到什么。Wuji 让执行节点读取黑板并作出下一次分派，而不是运行两个互不一致的工作流引擎。

## 12. 固定源码核查附记

独立 SOL/xhigh 静态核查采用 Cairn 提交 [`e0ef2f850e5805f824815ee38f049e066deeb7d1`](https://github.com/oritera/Cairn/tree/e0ef2f850e5805f824815ee38f049e066deeb7d1)，不是对商业衍迹版本的确认。主代理另行复核 WorkerDriver、WorkerConfig 和 reopen 协议；未执行仓库代码。

| 核查 | 证据与采用方式 |
| --- | --- |
| 无固定角色仍有能力配置 | `WorkerConfig` 含 task_types、容量、优先级；Wuji 保留能力匹配，不强制所有 Worker 配置完全相同。[源码](https://github.com/oritera/Cairn/blob/e0ef2f850e5805f824815ee38f049e066deeb7d1/cairn/src/cairn/dispatcher/config.py#L157-L163) |
| Harness 适配是薄接口 | WorkerDriver 构造执行/收尾命令并维护 session；这支持沿用 Wuji AgentDriver 分工，不证明任一 SDK 在 Wuji 网关上已兼容。[源码](https://github.com/oritera/Cairn/blob/e0ef2f850e5805f824815ee38f049e066deeb7d1/cairn/src/cairn/dispatcher/workers/base.py#L17-L43) |
| 调度与结果回写集中 | Dispatcher 按图态派发；Wuji 映射到现有 Orchestrator/Dispatcher，不运行第二套 Cairn 调度器。[调度循环](https://github.com/oritera/Cairn/blob/e0ef2f850e5805f824815ee38f049e066deeb7d1/cairn/src/cairn/dispatcher/scheduler/loop.py#L66-L81) |
| 完成后重新打开有不同历史语义 | 所核查协议的 reopen 删除原完成边；Wuji 保留历史并创建关联新任务，不直接复制此行为。[协议](https://github.com/oritera/Cairn/blob/e0ef2f850e5805f824815ee38f049e066deeb7d1/docs/specs/server-protocol.md#L555-L570) |

Wuji 已设计的 ToolCall/AgentRun 账本、租约 fencing、VerificationRun 和报告版本仍保留；黑板是协作知识的权威记录，通过受控关系引用执行与验证记录，不覆盖它们的状态职责。


## 13. 用户补充：运行成果与凭据共享

2026-09-10：Web 单点创建不预置账号。当前授权方法内获得的账号、会话和其他成果作为运行记录进入黑板；其他同任务 Agent 可通过受限引用使用。凭据实体加密保存，黑板记录来源、适用对象/权限、有效状态、credential_ref 和证据；不把明文 Secret 广播到所有模型上下文。运行成果追加不改变初始配置快照，也不要求为每份成果重建任务；目标范围和工具权限独立检查。详细契约留在后续 Agent 协作 Spec。
