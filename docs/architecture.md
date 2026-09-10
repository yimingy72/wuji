# Wuji 自动化渗透平台架构

- **版本**：v0.4
- **日期**：2026-09-09
- **状态**：目标架构基线；平台身份/项目与B1范围预览已实现，B2/B3实施中，完整执行闭环尚未验收
- **适用范围**：已获授权的非破坏性安全验证；禁止目标数据破坏、目标持久化和越权扩散
- **验收依据**：[架构验收清单](architecture-acceptance.md)
- **评估业务契约**：[评估、知识与交付模型](assessment-model.md)
- **前端实施设计**：[前端架构与技术选型](frontend-architecture.md)
- **Agent 执行层**：[Harness 职责与选型建议](agent-harness-decision.md)、[模型网关实测](model-gateway-validation.md)
- **本次复审**：[问题、修正与验证缺口](architecture-review.md)
- **开工准备**：[依赖与交付顺序](predevelopment-plan.md)、[Phase 1 API 契约](phase1-api-contract.md)

v0.4 保留既有执行控制、评估与交付模型，修正框架复用边界：上下文管理、压缩和 Agent 循环复用 Harness，持久执行复用 LangGraph，多模型协议复用现成适配器。Wuji 实现领域策略与集成契约，不另建通用 Agent 框架；具体依赖仍待集成验证。本文描述目标能力，不把设计接口当成实现；实际进度以[Phase 1A验收](stages/phase-1a/acceptance.md)、[B1验收](stages/phase-1b/acceptance.md)和[B2/B3验收](stages/phase-1b/b23-acceptance.md)为准。

## 1. 目标与架构原则

Wuji 在 Kubernetes 中管理独立任务执行环境，由 Platform 中的 Agent 规划验证步骤，通过受控工具收集证据并生成可追溯报告。

必须满足以下约束：

1. 授权范围是服务端执行策略，不能由 Prompt、Agent 或目标返回内容扩大。
2. 每次执行同时满足身份权限、目标范围、操作类型、预算和有效租约约束。
3. 一个 Task 同时最多有一个获准执行的 Runtime attempt；故障重建可以产生新 attempt。
4. 工具执行、网络出口和模型访问都有独立于模型判断的控制点。
5. 暂停、取消、失联、恢复和结果不明是明确状态，不能用“停止推理”代替“停止执行”。
6. 外部请求不承诺 exactly-once；通过去重、执行账本和结果核对控制重复，结果不明时不盲目重试。
7. 多租户身份、资源配额和审计从首版建立；多 Agent 在单 Agent 安全闭环通过验收后接入。

“禁止持久化”指禁止在测试目标建立驻留、后门或其他持续访问机制。平台按保留策略保存任务、检查点和证据；这不授予在目标上写入数据的权限。非破坏性也不等于 HTTP GET 或工具名称含有“read”：仍须审查目标业务语义及请求负载。

## 2. 已确定的架构决策

| 主题 | v0.4 决策 | 演进边界 |
| --- | --- | --- |
| 执行环境 | 一个 Task 一个活动 TaskRuntime；HTTP 切片使用最小镜像，Kali 工具按 RuntimeProfile 接入 | Pod 按 attempt 重建；ExternalRuntime 以后通过相同运行契约接入 |
| Runner | 不作为业务概念；Worker Node/Node Pool 属于基础设施 | 不让任务依赖节点名称或 Pod IP |
| Agent | 运行在 Platform 的 Orchestrator，通过 MCP Router 请求工具 | 不持有 Kubernetes、Runtime 或 Provider 凭据 |
| Agent Harness | 通过薄 AgentDriver 复用模型/工具循环与上下文管理；优先验证 Deep Agents | LangGraph 管外层任务；具体 Harness 和版本待受控集成验证，一个 AgentRun 绑定一种实现 |
| 上下文 | Harness 独占会话历史、压缩和工作记忆；平台提供版本化输入与证据引用 | 不另建压缩服务；摘要不是事实或授权来源，辅助模型调用同样计费 |
| 协作 | LangGraph 编排；Blackboard 共享事实；Dispatcher 管理 Worker | Worker 无权扩大范围、权限和任务总预算 |
| 评估单元 | VerificationRun 独立于 AgentRun，固定主张、方法、身份和证据 | 单 Agent 即可执行；独立复核不等于模型多数投票 |
| 覆盖与停止 | 版本化 CoveragePlan，区分有效评估、未复现、阻断和未执行 | 计划内覆盖率不是整个目标系统的安全覆盖率 |
| 能力配置 | ScenarioProfile、AgentProfile、SkillPackage、ReferenceVersion 各自版本化 | 配置与知识不能替代 ScopePolicy 授权 |
| 资产与交付 | PostgreSQL 资产关系、证据引用、FindingRevision、ReportCommit | 图可视化与导出格式是同一事实模型的投影 |
| 工具 | 版本化、结构化 Tool Adapter；首版仅受限 HTTP 观察 | 通用 bash、任意代码、任意插件不进入当前工具契约 |
| Runtime MCP | 内网 Streamable HTTP，固定并验证协商的协议版本 | MCP session ID 不承担认证或执行去重 |
| 任务状态 | PostgreSQL 是业务期望状态和执行账本的权威来源 | Kubernetes 提供资源实况；缓存和事件不能反向覆盖业务决策 |
| Kubernetes 接入 | 首版 Runtime Controller 直接调用 API | CRD 不是最小闭环前提，未来只增加单向投影 |
| 事件 | PostgreSQL 事务 Outbox + 可重放事件记录 | Redis 可作缓存/唤醒；量化瓶颈出现后再引入 JetStream |
| 模型接入 | 复用模型客户端与已有网关；Wuji Gateway 统一策略、路由、重试和预算 | 不重写各厂商协议；不在网关二次编排/压缩会话，不默认增加代理链 |
| 前端 | React + TypeScript + Vite + Ant Design；REST 命令 + SSE 事件 | 统一查询缓存和同源会话；浏览器交互以后通过受控会话代理接入 |
| 部署 | 按权限边界分进程，业务模块先合并部署 | 不把每个逻辑模块都拆成微服务 |

## 3. 逻辑链路与部署边界

### 3.1 主要链路

```text
任务控制：Console -> Platform API -> PostgreSQL（Task / Policy / Outbox）
资源协调：Runtime Controller -> Kubernetes API -> TaskRuntime Pod
任务编排：Orchestrator -> Blackboard / Dispatcher -> Worker
Agent 执行：Orchestrator（LangGraph）-> AgentDriver -> Agent Harness
工作记忆：Agent Harness -> 按 AgentRun 隔离的框架存储后端
业务工具：Agent Harness -> 已鉴权的平台模块（Blackboard / Knowledge / Assessment）
目标工具：Agent Harness -> Tool Bridge -> MCP Router -> Runtime MCP / Supervisor -> Tool Adapter
目标访问：Tool Adapter -> Egress Gateway -> 授权测试目标
模型调用：Agent Harness -> Model Bridge -> Model Gateway -> Provider Adapter -> 已有网关 / Model Providers
证据保存：Runtime Supervisor -> Artifact API -> S3；元数据 -> PostgreSQL
评估闭环：CoverageItem -> Intent -> VerificationRun -> Observation/Evidence -> FindingRevision
交付闭环：CoveragePlan 快照 + FindingRevision + 证据清单 -> ReportCommit -> ExportArtifact
```

Blackboard 不直接调用 Runtime；所有目标操作经 MCP Router。框架工作记忆工具仅操作限定的 AgentRun 状态；业务工具使用项目鉴权接口，两者不提供目标网络或通用代码执行。Runtime 向 Router 返回状态和受限大小的结果，证据上传走 Artifact 接口。控制流、执行流、模型流量分开鉴权。

### 3.2 逻辑职责与首版部署

| 逻辑组件 | 职责 | 首版部署单元 |
| --- | --- | --- |
| Platform API | 身份、租户、项目、Task、ScopePolicy、配置版本、产物授权、SSE | `platform-api` |
| Policy 模块 | 编译不可变策略版本、权限求交、操作分类 | API 内管理；执行端使用版本化策略快照 |
| Blackboard / Base MCP | Observation、Fact、Intent、验证请求及 Worker 请求 | API 内模块，内部接口独立鉴权 |
| Assessment 模块 | 覆盖计划、VerificationRun、规则校验、FindingRevision 和研判 | API 内模块；模型只能提案，模块控制状态转换 |
| Knowledge / Reference 模块 | 发布知识版本、资料导入、摘要和引用、加载审计 | API 内模块；耗时解析使用有限权限后台作业 |
| Asset / Report 模块 | 资产关系、证据引用、报告快照和导出 | API 内模块；异步渲染与目标执行解耦 |
| Orchestrator / Dispatcher | LangGraph、Worker 调度、检查点、任务推进 | `agent-orchestrator` |
| AgentDriver / Harness | 单 AgentRun 的模型/工具循环、上下文与框架事件适配 | 默认内嵌 Orchestrator；以后接入独立 SDK Worker 时使用相同限定身份与调用边界 |
| MCP Router / Execution Broker | 身份派生、策略校验、调用账本、执行许可、结果接收 | `mcp-router` |
| Runtime Controller | Pod 生命周期、工作负载身份、租约协调、资源回收 | `runtime-controller`，独立 ServiceAccount |
| Model Gateway | 请求策略检查、路由、预算和每次尝试审计；复用协议客户端 | `model-gateway`，Provider Key 只在此边界内；不管理 Agent 会话历史 |
| Egress Gateway | Task 出口身份、目标检查、请求限流、租约到期断流 | 独立受信进程，部署在 Runtime Pod 之外 |
| Runtime Supervisor | 许可验证、工具调度、进程管理、状态与证据收集 | 每个 TaskRuntime 内的受信控制容器 |

这些部署边界用于限制凭据和故障影响。Blackboard、Policy、Assessment、Knowledge、Asset、Artifact 和 Report 先作为模块维护，不额外增加网络服务。资料解析和报告渲染复用后台作业基础设施，但使用独立低权限进程/沙箱，不在 API 进程里执行不可信内容。首版数据基础设施为 PostgreSQL 和 S3 兼容对象存储。

## 4. 授权范围与操作策略

### 4.1 ScopePolicy

任务绑定不可变 `scope_policy_id + version + hash` 和授权记录。授权记录包含授权主体、项目、目标控制权或委托依据、起止时间及策略批准者；用户输入一个 URL 不等于平台已完成授权校验。

以下为设计示例，不是当前已实现的 API Schema：

```yaml
scopePolicy:
  id: scope-001
  version: 1
  authorizationRef: authz-001
  validFrom: "2026-09-09T01:00:00Z"
  validUntil: "2026-09-09T02:00:00Z"
  targets:
    - origin: https://authorized-target.example:443
      allowedPathPrefixes: [/public/]
      allowedMethods: [GET, HEAD]
      operationClasses: [http-observe]
  excludedPathPrefixes: [/public/logout, /public/admin]
  redirects: revalidate-every-hop
  dnsPolicy: resolve-validate-connect
  credentialPolicy: same-approved-origin-only
  limits:
    taskRequestsPerSecond: 2
    burst: 2
    maxConcurrentRequests: 2
    maxTotalRequests: 200
    requestTimeoutSeconds: 10
    maxResponseBytes: 1048576
  prohibitions: [destructive-action, target-persistence, lateral-movement]
```

Schema 必须明确 URL 规范化、路径段边界匹配、编码处理、IP 字面量和 IPv6 规则；前缀 `/public/` 不能误匹配 `/publicity/`。GET/HEAD 只是约束之一，已知会改变业务状态的端点仍必须排除。

实际权限为平台允许集合、租户策略、项目授权、Task Scope、RuntimeProfile、Worker 授权和 Tool Adapter 能力的交集；平台禁止项和其他拒绝规则优先。

新增目标、延长授权或放宽操作须经有权限的操作者创建新版本；Agent 只能提交请求。现有授权可复用且仍有效时，不重复索要确认。版本切换先阻止新派发并停止或排空受影响调用；Router、Runtime、出口完成新版本绑定后才能恢复。撤销策略、授权过期和禁止项命中不得自动降级放行。

### 4.2 三个执行检查点

1. **Router**：校验可信身份、任务状态、策略版本、结构化参数、工具版本、预算及租约，保存 ToolCall 后签发有限许可。
2. **Runtime**：验证许可与本机 Task/attempt 匹配，检查参数摘要、截止时间、去重记录、可用 Adapter 和进程配额；不接受 Agent 直接构造的权限字段。
3. **Egress Gateway**：独立验证工作负载与活动任务绑定、策略版本、执行有效期，检查实际目的地及累计请求量；拒绝 Runtime 直连互联网或平台内网。

Router 同时签发接收方为出口的调用许可，绑定 call/attempt、Worker 的目标子集、操作类型和请求额度；Supervisor 使用它发起出口请求。后续 CLI 只能获得该次调用的受限出口句柄，不获得任务通用控制凭据。网关逐请求校验许可并累计用量，Task 级网络可达不代表获得整个 Task 的操作权限。

首版出口提供受控 HTTP 请求转发，由网关解析并规范化 origin、方法、路径、请求头和重定向，不提供任意 CONNECT 隧道。TLS 在网关作为 HTTP 客户端连接目标并验证证书，返回受限响应。普通 L4 白名单无法实现方法/路径约束。

解析 DNS 后检查全部候选地址，只连接本次验证过的地址；每次重试、重定向和新连接重新检查，防止校验和连接使用不同目的地。网关拒绝平台 Service/Pod/Node 网段、API Server、元数据服务和保留地址；客户内网目标只能通过显式批准且与平台基础设施隔离的出口配置接入，不能笼统放行所有私网。

发现新域名、子域名或关联资产只记录为候选事实，不自动纳入范围。跨 origin 不转发 Authorization/Cookie。目标路径限定到 Host 的授权不能因共用 IP 扩展为整台服务器授权。

## 5. 工具契约与 MCP

本节 Runtime 注册表约束目标操作；Base MCP 是平台业务接口。Harness 自带的待办和工作记忆工具是第三类：仅可使用已审查、无目标网络和任意代码执行能力的受限后端，记录调用与存储配额，不为它们创建 Kali 执行环境。工具类别由服务端注册，不能由模型或第三方插件自行声明。工作记忆中的待办不能直接修改 CoveragePlan、Task 或 Finding。

### 5.1 工具注册表

| 字段 | 要求 |
| --- | --- |
| `name / version / image_digest` | 固定工具及运行镜像版本，不在线安装未知插件 |
| `input_schema / output_schema` | 严格结构化；限制输出大小；未知字段拒绝 |
| `operation_class` | 由平台审查注册，不采用模型自报的风险等级 |
| `scope_resolver` | 从参数解析所有目标；不能解析的调用拒绝 |
| `timeout / resource_limits` | 有限执行时间、进程数、内存和产物配额 |
| `retry_class` | `safe-read`、`idempotent-with-key` 或 `never-auto-retry` |
| `cancel_handler / evidence_schema` | 停止机制、状态反馈、证据关联方式 |

Task 和 Worker 必须配置最大运行时间、工具调用数、Agent 并发/深度和产物大小；模型接入后还须配置 Token/费用上限。子级截止时间和配额不能超过父级；到期执行取消链路，预算耗尽停止新派发并按策略进入暂停或停止流程。

首版只开放 `http_observe`，使用第 4 节的受控 HTTP 转发。后续 `browser_observe`、`network_probe` 只有在各自出口约束通过验收后才能启用；浏览器子请求、WebSocket、下载和后台请求同样受控，不支持的通道拒绝。

HTTP 观察是第一个可验收切片，不是长期产品能力上限。后续可并行建设离线源码审计、浏览器与协议分析 Profile；源码审计优先使用只读输入快照和离线解析 Adapter。需要构建或执行输入代码时必须单独设计沙箱和验证契约，不能借“代码审计”默认获得任意代码执行或网络权限。

CLI Adapter 使用固定可执行文件和校验后的参数数组，不经 shell 拼接，不开放脚本、插件加载、任意代理和任意输出路径参数。`read_artifact`/`save_artifact` 使用服务端句柄，不暴露任意宿主文件路径。MVP 不提供通用 bash、任意文件读写、Kali 交互终端或可任意导航的远程桌面。

### 5.2 Base MCP

```text
get_task / get_blackboard
get_coverage / get_asset_context / load_skill / read_reference
write_observation / propose_fact / propose_finding
submit_intent / request_worker / request_verification / submit_verification_result
save_artifact / request_report_draft
```

上述是按阶段开放的逻辑工具目录，不是当前已实现接口。Worker 请求由 Dispatcher 再检查权限和剩余预算，不能直接创建自由运行的子 Agent。模型只能提交候选事实、验证结果及 Finding；Assessment 模块根据证据和 ValidationRuleVersion 决定可接受的结论。Fact 可标记 verified，Finding 使用分离的证据/研判/修复/发布状态，避免一个 verified 布尔值混淆多个含义。规则不满足时保留不确定状态。

知识发布、范围批准、人工研判、修复关闭和报告发布是 Platform API 的受权限保护命令，不作为普通 Agent 工具开放。`request_report_draft` 只生成草稿，不自动发布或向外部发送报告。

### 5.3 身份与执行许可

工作负载间使用双向 TLS 或等价的可验证工作负载身份；Runtime 的 MCP 入口同时认证 Router 调用方。localhost、ClusterIP、MCP session ID 都不是授权依据。按选定的 Streamable HTTP 协议版本处理 Origin 校验和会话生命周期。[MCP 传输规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)

Router 从已认证调用身份及服务端 AgentRun 映射派生上下文，拒绝参数覆盖：

```text
tenant_id / project_id / task_id / runtime_id / runtime_attempt
agent_run_id / tool_call_id / policy_version / policy_hash
tool_version / args_digest / execution_epoch / expires_at / trace_id
```

验证调用还关联 `verification_run_id / coverage_item_id / config_snapshot_id`；探索调用允许尚无验证单元，但必须关联 Intent 和来源。各 ID 的租户、项目和任务归属在服务端校验，不能通过挂接其他任务的验证 ID 获得权限。

Runtime 使用专门签发给本接收方的短期凭据及逐次执行许可，校验发行者、接收方、有效期、epoch 和工具集合。任务取消或重建会使旧许可失效；不把用户登录 Token 原样转发给下游。凭据接收方验证遵循 [MCP 安全要求](https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices)。

模型只看到工具逻辑名、脱敏参数和结果，不接触内部路由地址、签名密钥、执行许可或 Runtime Token。

## 6. Runtime 与 Kubernetes 隔离

### 6.1 Pod 与进程边界

```text
Task -> TaskRuntime -> attempt-N Pod
                       ├── runtime-control：MCP / Supervisor / 凭据
                       └── kali-tools：受限 Adapter 子进程 / Browser（后续）
```

HTTP MVP 可只运行受信 Supervisor 和内置 HTTP Adapter；增加 Kali 工具进程时必须采用独立控制容器和工具容器，不能让通用工具与凭据同权限共存。两者使用不同非 root UID、不共享 PID namespace、不共享凭据卷。受限本地调度接口只接受 Router 已授权的操作，所有网络监听端口都鉴权，不能信任请求来自同一 Pod。

Sidecar 共享 Pod 网络，不能靠 Kubernetes NetworkPolicy 隔离同 Pod 的不同容器；它用于进程和凭据分离。工具容器不挂载控制凭据、签名材料、数据库或 Provider Key。Egress Gateway 在 Pod 外强制限制目标；拆 Sidecar 本身不是网络安全边界。[NetworkPolicy 的能力与限制](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

Runtime 默认配置：

- `automountServiceAccountToken: false`；禁止 hostNetwork、hostPID、hostIPC、hostPath 和 privileged。
- 非 root、`allowPrivilegeEscalation: false`、drop ALL capabilities、`seccompProfile: RuntimeDefault`、只读根文件系统，写入限定的临时卷。
- 设置 CPU、内存、临时存储 requests/limits、进程上限和租户 ResourceQuota；工具不兼容时更换 Adapter，不自动放宽限制。
- Runtime 与 Platform 使用独立节点池；对恶意工具或不受信代码的强隔离需求，先验证沙箱运行时/虚机方案，当前契约不声称普通 Pod 是该类安全边界。

准入控制拒绝违反 RuntimeProfile 的 Pod，而不是只依赖应用生成正确 YAML。基线参照 [Kubernetes Restricted Pod Security Standard](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

### 6.2 网络允许矩阵

所有未列出的 Runtime 入站和出站默认拒绝；选用能实际执行 NetworkPolicy 的 CNI，并验收 IPv4、IPv6 和节点访问路径。

| 发起方 | 接收方 | 允许内容 |
| --- | --- | --- |
| Console | Platform API | 已认证 HTTPS / SSE |
| Orchestrator | API 内部模块、Router、Model Gateway、PostgreSQL | 各自角色允许的业务与检查点操作 |
| Router | 绑定的 Runtime MCP | mTLS + 有限执行许可；禁止任意用户指定 URL |
| Runtime Supervisor | Router、Artifact 接口、Egress Gateway | 身份绑定的心跳/结果、受限上传、授权目标请求 |
| Kali 工具容器 | Egress Gateway、受限本地 Adapter 通道 | 仅接受逐调用出口许可；无权访问平台业务 API |
| Egress Gateway | 已验证目标、受控 DNS | 策略与活动租约内的连接；拒绝平台网段 |
| Model Gateway | 租户允许的 Provider/适配层 | 数据策略允许的模型请求 |
| Runtime Controller | Kubernetes API、任务存储、出口管理接口 | 资源协调、执行租约及撤销 |

Pod 级策略无法区分同 Pod 容器，因此表中控制容器专有的平台接口还必须认证其独享凭据，工具容器即使网络可达也无权限。Runtime 不需要任意 DNS，目标解析由出口执行；必要的内部服务解析使用受控解析器，禁止借 DNS 外发任意数据。

Namespace 按租户划分，Task 使用服务端不可由工具修改的标签和 Pod UID 绑定；每 Task 一个 Namespace 可作为管理选择，但不能替代上述控制。Egress 身份绑定到已注册工作负载及有效 attempt，不采用客户端自报 task header，也不能仅凭可复用的 Pod IP 认证。

### 6.3 Controller 调谐

Controller 根据 PostgreSQL 中的 Task 期望状态反复调谐，使用任务版本、唯一活动 attempt 约束和协调租约避免多副本重复创建。资源使用确定名称及 task/attempt/Pod UID 标签；策略就绪、身份签发、出口注册和 MCP readiness 全部完成才进入 ready。

Controller 的集群权限限定在预置 Runtime Namespace 内的必要资源，不能创建 RoleBinding、任意特权 Pod 或修改平台资源。Namespace 和配额由部署管理流程预置。Pod 创建成功但 DB 回写失败时按资源标签核对，不重复建立第二个可执行环境。

重建前撤销旧 attempt 出口权限并确认撤销或等待其租约失效，再激活新 attempt。临时浏览器会话和进程不承诺恢复；Pod 重建后重新 Bootstrap，结果不明的调用进入核对流程。

回收覆盖 Pod、Service、临时 Secret、工作卷和出口授权。保存独立 `cleanup_status`，定期清扫带有效所有权标记的孤儿资源；清扫器不得按模糊名称删除不属于本平台的资源。

## 7. 生命周期、恢复与事件一致性

### 7.1 状态权威与写入责任

| 状态 | 权威来源 / 写入责任 |
| --- | --- |
| Task 期望状态、ScopePolicy | PostgreSQL；API 授权变更 |
| Task 执行进度、AgentRun | PostgreSQL；Orchestrator 通过版本条件更新 |
| TaskRuntime 实况 | Controller 观察 Kubernetes 后记录，不能撤销用户的取消决定 |
| ToolCall / ToolAttempt | Router 执行账本；Runtime 回执作为证据输入 |
| Graph 检查点 | PostgreSQL checkpointer；Orchestrator 单一活动执行租约 |
| Blackboard / Finding | PostgreSQL；模块接口维护版本和证据关联 |
| CoveragePlan / VerificationRun | PostgreSQL；Assessment 模块校验提案并提交，模型不能直接改结论 |
| Profile / Skill / Reference 版本 | PostgreSQL 元数据 + 对象存储内容；配置/资料模块发布不可变版本 |
| Asset / EvidenceLink | PostgreSQL；资产与证据模块维护来源、时间和版本 |
| ReportCommit / ExportArtifact | PostgreSQL 快照清单 + 对象存储渲染产物；Report 模块管理发布 |
| 预算 | PostgreSQL reservation/ledger；Gateway、Router 按预算类型预占和结算 |
| 事件和 UI | 事务 Outbox 发布、持久化事件投影；不作为独立事实源 |

Task API 的创建、暂停、恢复、取消接受幂等请求键和资源版本，区分“命令已接受”与“状态已达成”。事件带 `event_id / tenant_id / task_id / aggregate_version / trace_id`。投递按至少一次设计，消费者去重并检查版本；乱序事件不能让终态任务重新运行。

取消提交、执行许可签发和租约续期都按同一 Task 版本/epoch 做数据库条件更新，避免检查后又被取消的竞争。取消提交后不再签发新许可；此前已签发且在途的操作通过出口撤销与租约上限停止，不能宣称分布式撤销无传播延迟。数据库不可用时拒绝新授权和续约。

### 7.2 Task 与 ToolCall 状态

```text
Task:
queued -> provisioning -> running -> completing -> completed
running -> pausing -> paused -> provisioning/running
任意非终态 -> cancelling -> cancelled
运行异常 -> reconciling -> paused / running / cancelling / failed

ToolCall:
proposed -> authorized -> dispatched -> running -> succeeded / failed
proposed -> rejected
authorized/dispatched/running -> cancelling -> cancelled
dispatched/running -> unknown -> reconciling -> 已核实结果 / 保持 unknown
```

只有授权有效、预算允许、旧 epoch 已隔离且未取消的任务才可从 reconciling 恢复 running。未知结果不会直接转为成功，也不会因为换了 Pod 就变成“未执行”。完成任务前必须确认没有活动执行和待核对调用，证据元数据已落库，出口权限已撤销；清理进度单独显示。

这里的“待核对调用”指可能仍执行或目标副作用未知的 ToolCall，不等同于业务结论 inconclusive。Task 达到执行终态时另外保存 `assessment_outcome` 和 `stop_reason`：允许结论不完整的任务在明确披露限制后结束，不允许把 unknown 执行改成业务“未复现”来绕过核对。完成判据和覆盖计算见评估业务契约。

Phase 1 的工具任务由 API 与 Router/Controller 协调上述状态；接入 Orchestrator 后由其推进工作流，禁止两者同时拥有同一 Task 的执行推进权。任何 failed 终态同样要求先隔离出口并停止活动执行；无法确认时保留 reconciling。

Phase 1 的状态转换、派发、核对和停止实现为可复用业务操作，由持久任务协调循环调用；不把长任务放在 HTTP 请求线程或仅内存后台回调中。Phase 2 的 Graph 节点调用这些既有操作，只接替调度职责，不重新实现另一套 Task / ToolCall 状态机。

### 7.3 暂停、取消和失联

- **暂停**：先停止新 Worker、模型尝试和工具派发，进入 pausing；允许已批准调用在有限 drain deadline 内结束，超时则停止。没有活动调用且出口已冻结后才标记 paused。恢复时重新验证授权、预算、策略和 Runtime 健康。
- **取消**：API 提交取消意图并增加 execution epoch；Router/Gateway 拒绝旧 epoch 的新操作，出口撤销活动授权并关闭连接；Supervisor 停止工具进程组、浏览器 Context 和后台任务。已发往目标的请求无法撤回，取消不声称回滚目标效果。
- **失联**：Supervisor 和 Egress Gateway 使用可到期执行租约，续约失败时停止执行/转发，不能无限使用缓存策略。无法确认进程停止时保留 cancelling/reconciling，不因 Pod 删除请求成功就宣告结束。
- **确认**：收到可信停止回执，或已证实运行环境终止，且出口被隔离，才完成取消；清理失败保留 `cleanup_pending` 并告警。下游模型响应可能稍后返回，只记账，不再触发工具。

建议初始参数为租约 30 秒、续约周期 10 秒、额外时钟/调度容差 5 秒，暂停 drain deadline 15 秒；这些是待验收配置，不是已实测 SLA。最坏失联断流目标为最后一次有效续约后 35 秒内。出口检查覆盖已建立的长连接和流式转发，旧续约消息不能延长撤销后的租约。

租约同时受授权到期、Task/Worker 截止时间和调用截止时间约束，取最早者；时钟容差不能延长业务授权。调度使用单调计时，并检验签名期限和时钟偏差；偏差超限停止续约。

### 7.4 执行账本与重试

每次逻辑操作有稳定 `tool_call_id`，每次实际尝试有 `attempt_id`；相同 ID 但不同参数摘要必须拒绝。记录 authorized、dispatch intent、Runtime accepted、started、exit/result、证据摘要和终态。Runtime 在启动工具前保存接收/去重记录，Router 保存持久账本；Runtime 临时盘丢失后结合 Router 记录核对，不能假设从未执行。

Runtime 以 `(tool_call_id, attempt_id)` 去重投递；只有 Router 能经状态核对与预算预占后创建新的 attempt。HTTP 客户端、Adapter 和出口禁用不可观测的自动重试；网关处理的重定向逐跳留痕、计数并验证 Scope，不隐藏在一次调用统计中。

故障恢复先查询已有执行状态和证据，再决定重试。`safe-read` 也须重新获得预算和 Scope 许可；`idempotent-with-key` 要求目标接口或 Adapter 真正支持幂等，不以数据库唯一键替代目标幂等。无法判断是否已产生目标效果的调用不自动再次发送。

LangGraph 的外部操作封装为可记录结果的 task/node，并使用数据库检查点；图节点恢复时通过业务调用 ID 读取既有结果。框架恢复仍要求应用处理副作用和幂等性。[LangGraph 官方说明](https://docs.langchain.com/oss/python/langgraph/functional-api)

Graph 检查点与业务账本不假定在同一事务提交；Orchestrator 恢复时按 AgentRun、调用 ID 和版本对账。DB 状态变更与 Outbox 在同一事务写入，发布失败可补发。MCP 重连、HTTP 超时和消息重投都不构成重发工具的授权。

工具执行前先持久化模型产出的动作及其业务调用 ID，再派发。恢复身份绑定 `agent_run_id + checkpoint/step + emission_index` 等稳定位置，并核对参数摘要；具体字段由适配契约固定，不能只用目标/参数去重而误吞合法的新观察。若框架无法稳定恢复位置，停在核对状态，不重新询问模型来猜测原动作。模型调用同样保存逻辑请求 ID、已返回结果与用量；Graph 重放不直接生成第二个付费请求。

审计回放只重放已存储事件、输入摘要和结果，不调用模型或目标。重新验证应创建新执行请求并重新检查范围和剩余预算。

## 8. Agent 与 Blackboard

LangGraph 提供编排与持久执行机制，不自动包含完整 Agent Harness。Wuji 复用成熟执行框架，平台保留任务、授权、账本和证据的状态权威；框架取舍见 [Agent 执行层决策](agent-harness-decision.md)。

### 8.1 编排

```text
Bootstrap -> Reason -> Submit Intent -> Dispatch -> Wait Workers
    ^                                                |
    +---------------- Reduce Results <---------------+
                         |
                  Continue / Pause / Finish
```

Dispatcher 原子认领 Intent，记录 owner、租约和递增 fencing token；过期 Worker 的写入拒绝。Intent 使用任务、目标、验证方法、身份和阶段生成去重键，重复观察更新现有探索项。每个 Task 只有一个持有有效租约的主编排实例。

Worker 绑定服务端创建的 `agent_run_id / intent_id / scope_version / runtime_attempt / credential_handle / budget_reservation`。模型输入只包含必要描述和逻辑句柄，不包含授权凭据。Worker 可提交后续 Intent，创建权和预算分配留在 Dispatcher。

独立工作可后台执行，依赖结果的步骤等待持久化完成事件；恢复后从 AgentRun/事件游标取结果，不靠模型循环轮询。Worker 回传结构化结论、证据 ID、限制、新 Intent 和平台计量的 usage。前台/后台只是调度方式，共用相同许可、取消、租约和预算约束；AgentRun 续接须重新检查任务状态，不允许旧 Worker 在取消后被消息唤醒继续执行。

### 8.2 共享与隔离

| 资源 | 策略 |
| --- | --- |
| Task Pod、出口、基础工具镜像 | Task 级共享；同一 Task 是共同的运行信任域 |
| 浏览器 | 按 Worker 与验证身份建立独立 Context、Cookie jar、下载目录；不共享登录状态 |
| 工作目录 | `/workspace/<agent_run_id>/<tool_call_id>/`；Adapter 限定路径并拒绝符号链接逃逸 |
| 代理配置 | 策略由平台管理；共享资源变更使用租约锁，Worker 不自由修改 |
| 凭据 | 项目/任务/目标/身份限定的句柄，按调用注入受信 Adapter；不进入模型上下文 |
| 事实与证据 | Blackboard 显式共享，携带来源、时间、工具版本、验证身份及可信度 |

目录和 Context 隔离用于防止会话污染与误操作，不声明对同 Pod 内任意恶意代码提供强隔离。需要相互不信任的执行者时拆分 Task/运行环境，不能仅增加目录。

Observation 为原始观察索引；Fact 保留来源和有效期；Hypothesis 为待验证假设；Finding 必须引用证据、适用目标/身份、验证规则版本和置信状态。模型总结不能自行提升来源可信度。冲突事实并存并标记待核对，不采用最后写入覆盖。

### 8.3 验证单元与覆盖计划

VerificationRun 固定“核实什么、在什么身份和条件下、依据什么证据”，AgentRun 表示“谁在执行”。一个验证单元可有多个顺序交接的 AgentRun 和多个 ToolCall；交接遵守 fencing，不并发写同一执行所有权。重新验证创建新 VerificationRun 并关联旧结果，不覆盖原记录。

VerificationRun 的执行状态与结论分开：完成一次工作不自动得到 confirmed；模型未找到问题不自动得到 not_reproduced。未满足方法前提、被环境阻断、输出被截断或关键证据缺失时保存原因和 inconclusive/unassessed。

CoveragePlan 是当前已定义计划，CoverageItem 以授权目标、测试维度和验证身份组织；ScopePolicy 决定允许范围，CoveragePlan 不签发权限。计划增删形成新版本，保留原分母和改动原因；不允许为了提高覆盖率删除未完成项。首版用列表/矩阵展示，后续图视图是同一数据投影。

### 8.4 场景、角色、知识与资料

ScenarioProfile 定义起手维度、所需资料和完成判据；AgentProfile 定义角色、逻辑模型、工具子集和输出 Schema；SkillPackage 提供版本化方法与工具用法；ReferenceVersion 固定源码/文档等任务输入。RuntimeProfile 管理实际环境能力，ScopePolicy 管理权限，任何一项配置不能越过其他限制。

Task 创建 ConfigSnapshot 固定所引用版本及摘要；按需加载知识有上下文大小限制、来源记录和逐次加载审计。管理员发布的知识与用户/目标资料区分信任级别，仓库中的同名 SKILL.md 不自动成为平台知识。配置、资料更新不会静默改变运行中任务；详细配置和变更契约见 [评估、知识与交付模型](assessment-model.md)。

### 8.5 Harness 接入与恢复

外层 LangGraph 推进 Task / Intent，内层 Harness 运行当前 AgentRun；通过 AgentDriver 适配模型、工具、事件与恢复位置，不另写一套通用模型循环。优先验证 Deep Agents 的受限配置；若默认能力无法收敛，最小切片采用 LangChain `create_agent` 与现成 SummarizationMiddleware。pi、Claude Agent SDK、Codex SDK 和 DeepSeek Harness 按需求评估，不同时堆叠进首版。

Harness 的目标工具只能通过 Router 执行，模型请求只能通过 Wuji Gateway；工作记忆和平台业务工具按第 5 节分流。默认 shell、任意网络/宿主文件写入和本机插件发现必须关闭或改接受控服务；框架的权限提示不能替代 Scope 与网络隔离。子代理创建必须经 Dispatcher 取得身份、预算和租约，首版单 Agent 配置关闭自动派生。

每个 AgentRun 固定 Harness 类型、版本、配置摘要与租户限定会话引用。外层拥有任务执行租约，内层检查点不直接覆盖 Task 状态；恢复先对账已有模型/工具调用，不能仅凭重新生成的框架调用 ID 重发操作。停止推理后，仍由平台完成在途执行停止、断流和清理。

### 8.6 上下文与压缩的唯一责任方

Harness 管理消息历史、Token 估计、上下文裁剪、摘要与大结果卸载；优先配置其现成机制，不在 Orchestrator、Blackboard 或 Gateway 再维护另一份可写会话。Deep Agents 已提供压缩/卸载机制，LangChain 也有可配置的摘要中间件。[上下文机制](https://docs.langchain.com/oss/python/deepagents/context-engineering)、[内置中间件](https://docs.langchain.com/oss/python/langchain/middleware/built-in)

平台提供 ContextPolicy 配置与受限存储适配：输入上限、保留最近消息、压缩触发条件、摘要模型、最大压缩次数、脱敏及保留策略随 ConfigSnapshot 固定。未知模型别名不能套用猜测的上下文窗口；设置经验证的 Model Profile，开发探测可使用显式保守输入上限。Token 估计用于预留空间，不能冒充 Provider 实际计费用量。

可信规则与当前 Scope/epoch 从服务端装配，恢复时重新读取；不依赖压缩摘要记住授权。工具输入保留必要证据引用、来源和截断标记，大正文存对象存储并按需读取。工作记忆、模型摘要与候选结论不能直接提升为 Blackboard 已验证事实，也不能覆盖原始证据。

框架虚拟文件系统只挂载当前 AgentRun 工作区及允许读取的知识快照；发布知识和规则只读，框架不自动加载开发者目录或其他项目的记忆。摘要、工具选择、自动评估和未来子 Agent 的模型调用全部经过相同 Gateway 身份与预算，不能让辅助模型沿默认客户端直连上游。压缩失败或预算不足时有界停止，不无限压缩/重试。

### 8.7 打断与流式事件

复用 Harness / LangGraph 的中断、恢复、取消信号与事件 API，Wuji 只映射业务命令。等待用户决策使用已保存的中断位置；用户补充指令在下一个安全边界入队处理，不另起并行主循环。Phase 1 只有 pause/resume/cancel，后续 steering 或审核交互扩展契约后再开放。

框架中断不自动代表 Task 已 paused；必须满足第 7 节排空与出口冻结条件。取消先提交平台 epoch，再传播框架 abort 与工具停止，迟到结果只入账；恢复检查授权和活动租约，不能通过直接 resume 底层会话绕过业务命令。

框架事件转换为领域事件后才进入持久 Outbox。任务状态、工具动作、证据引用、压缩发生及用量需要留痕；逐 Token 文本不是 Task 版本更新，不逐片写 Outbox。后续如展示实时文本，采用有界临时流并保留最终可见摘要；断线恢复依据持久事件与快照，不承诺逐 Token 回放。框架 thread ID、内部控制事件和隐藏推理不直接开放给前端。

## 9. Model Gateway 与资源预算

### 9.1 模型与数据策略

逻辑模型使用 `reasoning / fast / vision / long-context`；`private` 作为数据处理策略而非可被 fallback 绕过的模型别名。

每次调用先求交租户、项目与 Task 的允许 Provider、部署区域、数据类别、留存要求、工具调用和结构化输出能力，再从候选路由选择模型。fallback 只能选择满足全部硬约束的候选；无合格模型则失败。私有数据策略不能回退到公网模型。

Wuji Gateway 是模型重试与 fallback 的唯一责任层。接入 LiteLLM/Bifrost 时通过配置和契约测试确认关闭内置自动重试/fallback；无法关闭或无法观察每次实际尝试的模式不接入。Orchestrator 对 Gateway 超时先用幂等请求键查询状态，不自行生成第二次付费调用。

复用模型客户端完成协议序列化、工具调用与流式解析；默认候选使用 LangChain 的 Provider 集成，业务层不手写每家模型协议。SDK、Harness 重试中间件和 HTTP 客户端的传输重试/fallback 必须与 Gateway 协调，目标工具重试则由 Router 决定。模型纠正无效参数属于有预算上限的新推理回合，不能与网络重投或 unknown 工具重试混为一谈。

已有企业模型网关可直接作为上游；Wuji 首先补齐业务策略与账本，不默认串联额外代理。2026-09-09 已验证用户提供网关的两种协议工具往返及 Responses 基础文本，具体见 [实测记录](model-gateway-validation.md)。该结果不代表 Harness 兼容、全部模型可用或上游重试/计费已满足本节要求；开发接入和生产验收分别记录。

### 9.2 消息与不可信数据

```text
System/Developer：平台可信规则 + 管理员策略 + Agent 角色 + 结构化 Scope 摘要
User：用户目标及补充信息
Tool/Data：网页、HTTP 响应、文件内容、Blackboard 事实与摘要
```

Blackboard 摘要和检索结果保留来源标记，不拼入系统指令。不同 Provider 的消息映射必须维持信任层级，不支持的映射拒绝；输出工具调用仍经 Router 校验。角色分离降低注入影响，不保证模型不会被诱导，也不替代执行授权。

发往 Provider 前进行凭据剔除、敏感字段处理和大小限制；原始 HAR、Cookie、Authorization 和完整目标响应默认不自动发送给外部模型。Prompt Profile、工具 Schema 和策略版本随调用记录，模型不得修改。

业务输入在进入 Harness 前完成分类和脱敏；Harness 管理会话，Gateway 在出口检查策略，不再次排序历史、压缩消息或重写工具对应关系。协议中的不透明续接状态由已验证客户端原样维护，并继承数据分类与路由绑定；无法按数据策略处理的形式拒绝接入，不在网关猜测其含义或任意改写。

AgentRun 绑定模型路由与会话兼容信息。fallback 除数据/预算约束外，还检查协议、工具 Schema、上下文容量及续接状态；不能把原 Provider 的会话 ID 或专属内容直接传给另一模型。需要切换不兼容模型时，先完成在途调用核对，在安全边界从平台证据和可迁移摘要建立新的会话段并记录切换，禁止重复执行已提交动作。模型清单、实测能力和暂时健康分别维护。

### 9.3 预算与限流

预算分为模型 Token/费用、工具尝试、目标请求/带宽/并发、Runtime 资源和产物存储，均有 Task 总上限；Worker 获得总预算内的分配，不能各自领取完整 Task 配额。

Gateway 在调用前原子预占输入及最大输出成本，设置输出上限，结束后按实际用量结算并释放剩余。请求发送后结果不明时保留预占并等待对账，不能超时即退款。所有 fallback、重试和取消后返回的用量都记录；未知用量先按预占上限保守处理。

Router 为每个工具 attempt 预占调用配额；出口以实际请求计数，重定向和重试也消耗额度。Task、租户及指向同一目标的并发任务服从聚合速率上限，防止多 Task 叠加负载。跨副本计数或配额租约必须原子协调；计数服务失联时停止新增请求，不回退到不限流。

记录 `model_call_id / attempt_id / actual_model / route_policy_version / prompt_version / input_tokens / output_tokens / reserved_cost / actual_cost / latency / trace_id`，价格配置版本一并保存。限制不可观测收费的 Provider 模式，不能承诺无法计量的硬成本上限。

### 9.4 上游共享配额与计量

增加 QuotaGroup 描述一个真实上游账户/配额池的并发、RPM、TPM 和可用容量；多个 Provider 配置、模型别名或路由可引用同一组。组映射由管理员确认，不能只按显示名或 URL 猜测。切换模型、Key 或 fallback 不重新获得一份共享额度。

Gateway 同时获得租户/任务预算预占和 QuotaGroup 容量许可；任一条件失败则排队或拒绝，排队有截止时间和公平调度。结果不明的 Provider 尝试按已知最大执行期限和核对策略处理，不能仅凭本地连接超时立即释放全部上游并发许可。容量协调不可用时不放行。

用量保留 Provider 原始字段及规范化输入/输出、缓存读/写、其他计费项和计费规则版本。未知字段标记未知，不按零计费；缓存 Token 与输入 Token 的包含关系按 Provider 映射，不能直接相加造成重复统计。按 Task、Worker、VerificationRun、模型和 QuotaGroup 汇总，计量数据来自 Gateway/执行器，不信任模型自报。

## 10. 多租户数据、证据和审计

### 10.1 PostgreSQL

核心实体为：

```text
Tenant / Project / Membership / Authorization / ScopePolicy
Task / TaskRuntime / AgentRun / Intent / GraphCheckpoint
ConfigSnapshot / ScenarioProfileVersion / AgentProfileVersion / SkillPackageVersion
Reference / ReferenceVersion / CoveragePlanVersion / CoverageItem
VerificationRun / ValidationRuleVersion / VerificationTemplateVersion
Asset / AssetRelation / Observation / EvidenceLink / Fact / Hypothesis
Finding / FindingRevision / Artifact / ReportCommit / ExportArtifact
ToolCall / ToolAttempt / ModelCall / ModelAttempt
QuotaGroup / BudgetReservation / BudgetLedger / AuditEvent / OutboxEvent
```

所有业务记录携带 tenant_id，项目级记录携带 project_id；父子关系使用包含租户/项目维度的复合约束，阻止跨租户关联。服务端从身份和资源归属建立上下文，禁止只凭客户端 tenant_id 查询。

采用 PostgreSQL RLS 作为纵深隔离，应用角色非 superuser、无 BYPASSRLS、不是表 owner，必要时 FORCE ROW LEVEL SECURITY；迁移角色与运行角色分开。租户上下文按事务设置，连接池复用后不得残留。RLS 依赖可信服务正确建立上下文，不声称能防御任意被攻陷的共享数据库客户端。

运行角色不授予 TRUNCATE、DDL 或任意角色切换权限；使用行级策略时仍需独立限制表级权限。[PostgreSQL RLS 说明](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

基础角色按项目分配：Viewer 查看被授权的脱敏结果；Operator 在已批准 Scope 内创建和控制任务；ScopeManager 管理授权与策略版本；TenantAdmin 管理本租户成员和配置。角色可组合，但租户管理员不能越过平台禁止项。原始敏感证据下载和数据导出是独立权限，不随普通查看权限自动授予。

后台 Worker 同样以 Task 归属限定事务；Controller 跨租户权限只允许其所需任务/Runtime 字段，不授予读取所有证据内容的通用角色。Graph checkpoint 的 thread ID 由服务端映射至 tenant/task/run，不允许用户通过任意 thread ID 读取状态。

复用框架维护的 checkpointer/store 与序列化格式，Wuji 保存租户归属映射并控制访问入口。框架自建表不自动拥有业务表的 tenant_id/RLS，接入时单独验证 schema、数据库角色、命名空间授权与清理接口，不能把 ID 前缀当作隔离证明。仅受信 Orchestrator 的检查点角色访问框架表；API、Runtime 和模型无通用读取权限。

上下文卸载文件、摘要、检查点和框架 trace 也属于任务数据，继承分类、加密、保留与删除策略；第三方 tracing 默认关闭，启用前纳入允许的数据出口。恢复所需对象已删除时明确不可恢复，不静默回退到模型猜测。

### 10.2 对象存储与产物

对象键由 Artifact 模块生成，使用 tenant/project/task/artifact 层级；路径前缀本身不是授权。Runtime 使用限定对象、大小、类型和短期有效期的上传授权，不持有 Bucket 通用凭据。上传完成后校验摘要、实际大小和元数据再发布 Artifact。

下载默认经 API 重新鉴权，服务端代理访问；明确允许的短时签名 URL 在失效前有残余访问窗口，不能宣称即时撤销。SSE 重连及事件补发同样重新检查项目权限，事件 payload 不包含原始凭据。

持续订阅按成员权限版本及撤销通知重新鉴权，并设置有界复查间隔；权限撤销后关闭连接、停止补发。复查间隔及签名 URL 最长有效期是需配置和实测的权限撤销窗口。

截图、HAR、原始响应、工具输出和报告设定数据分类、静态加密、访问审计及租户保留期限；凭据脱敏后进入普通日志，确有证据价值的原始敏感内容只进入受限证据区。平台删除任务按保留策略清理产物、检查点及备份生命周期，不在被测目标执行清理命令。

目标 HTML/SVG/报告中的外部内容在预览中转义或通过独立 origin 的受限沙箱呈现，禁用主动脚本和外联；文件下载采用受控 Content-Type/Disposition，避免证据查看页面执行目标内容。

### 10.3 审计与可观测性

审计包含策略批准/变更/撤销、授权拒绝、执行许可、每次实际尝试、停止回执、数据导出、模型路由及预算结算。关联 tenant/project/task/agent/call/attempt/trace，保留参数摘要、策略版本、工具镜像摘要、目标、时间和证据哈希。

普通业务角色不可修改/删除审计记录；按保留策略将审计批次导出到独立权限的存储。证据哈希用于校验内容一致性，不单独声称能抵抗数据库管理员篡改。

监控 unknown 调用、取消耗时、租约过期断流、孤儿 Runtime、Outbox 积压、预算未结算、策略拒绝和证据上传失败。提供确定错误码，例如 `SCOPE_DENIED`、`LEASE_EXPIRED`、`BUDGET_EXHAUSTED`、`EXECUTION_UNKNOWN`，日志默认脱敏。

### 10.4 资产、证据和交付版本

资产以项目内规范化标识管理，关系保留来源和有效时间；同 IP、同标题或同内容不自动合并不同应用。观察使用协议无关信封及类型化 payload，EvidenceLink 明确支持/反驳/限制哪个主张。HTTP 原包、代码位置和非 HTTP 协议记录不强行套用同一字段。

Finding 使用稳定 ID + 追加式 FindingRevision，分别管理证据结论、人工研判、修复状态和发布状态；模板的执行/验证状态单独关联 VerificationRun。报告先固定来源快照、生成并保存正文，再冻结 ReportCommit，引用 Scope、CoveragePlan、FindingRevision、验证结果 revision、证据清单、正文摘要、限制和生成版本。格式渲染只读取冻结输入；Live 草稿与已发布版本明确区分。

生成报告、展示历史回放、导出模板都不访问目标。执行模板、修复复测和任务续作必须建立新的受控验证请求；终态 Task 的续作创建关联新 Task，复用资料和历史证据引用但重新验证当前授权，原报告不被改写。证据保留期到期时显示不可用及原因，不伪造快照仍可完整复现。

## 11. 前端与操作体验

### 11.1 技术栈与访问边界

采用 React + TypeScript strict + Vite 构建独立 SPA，Ant Design 提供基础组件，React Router Data Mode 管理路由，TanStack Query 统一服务端数据缓存。URL 保存非敏感筛选和导航状态，局部状态保存未提交交互；不在浏览器另建任务权威状态。主版本候选、精确版本锁定方式和工程初始化门槛见 [前端架构与技术选型](frontend-architecture.md)。

静态前端和 Platform API 经同源入口提供服务，登录使用服务端会话及 CSRF 防护。前端只调用 Platform API，不直接访问 Runtime、MCP Router、Model Provider 或 Kubernetes。路由/按钮权限仅用于交互，API、文件和持续订阅独立鉴权；项目切换或权限失效时关闭订阅、中止请求、清理缓存，并拒绝旧上下文的迟到响应回填。

### 11.2 页面与操作语义

前端按“作业”和“配置”组织：作业包括总览、任务、资产、验证、漏洞、报告和资料；配置包括场景/角色/知识版本、RuntimeProfile、模型/QuotaGroup 和租户权限。Task 详情包含覆盖、时间线、工作区和 Agent 执行记录。

创建页先选可用场景，再补齐目标、资料和验证身份；显示有效目标、授权期限、排除项、允许操作、请求上限、模型数据策略和出口位置。服务端保存配置及策略快照；用户看到的范围与执行策略使用同一版本。缺少 Adapter 或凭据的测试维度显示阻断原因，不伪装为可启动的完整场景。

状态展示区分暂停中、已暂停、取消中、已取消、结果核对中、清理待完成；API 接受取消请求后不能立即显示“已停止”。写命令使用幂等键，超时先核对原命令；不自动换键再次提交。事件带游标，快照与订阅之间提供一致交接；SSE 断线后从持久事件补发，客户端去重并校验资源版本，游标失效时重新同步快照。

MVP 只查看工具日志、截图和证据。后续浏览器交互仍通过 Platform API、项目权限和执行许可；人工请求使用相同的 Scope/预算控制，不提供绕过 Router 的终端或直连 Pod 通道。

工作区允许按 CoverageItem、VerificationRun、Fact、Finding 筛选资产、流量、工具调用和文件，均使用服务端关系查询与同一授权。总览优先呈现需要介入的阻断、证据冲突、未知执行和预算等待；执行进度、计划内评估率、发现证实比例分别展示并标注分母。

先实现时间线与单条 Finding 的证据链，再增加全图、里程碑回放和全局搜索。回放使用已存事件，不向目标发送流量；Agent 展示简短决策摘要、依据和计划变更，不依赖保存或公开模型隐藏推理过程。

Phase 1 先交付登录/项目、任务列表、基本范围预览、任务详情和受控证据查看，可用有界只读轮询同步状态；Phase 2 再接入场景/知识配置快照、评估页面和 SSE。配置中心、全图和发布工作流随对应后端能力开放。页面权限、证据预览和缓存隔离从首版验收，不能等待 Phase 4 才建立。

## 12. 部署与演进

Helm 安装 Platform、出口组件、Runtime 基础策略及可选开发数据依赖；生产数据库和对象存储可以外置。Task Pod 由 Controller 动态管理，每个 Task 不单独执行 Helm release。

第 3 节列出的是完整 MVP 部署边界；Phase 1 仅启用 API、Router、Controller、出口与数据依赖，Phase 2 再启用 Orchestrator 和 Model Gateway。未实现工具和模块默认不注册，不能暴露占位接口执行实际操作。

控制台由独立 web 容器提供静态文件，与 API 共用浏览器访问入口；SSE 关闭代理缓冲并配置连接超时。SPA fallback 不接管 API、证据和事件响应。入口 HTML/公开运行配置与带摘要静态资源分别配置缓存，业务数据不进入共享静态缓存。构建产物不包含凭据，详情见前端设计第 8 节。

建议目录（尚未实现）：

```text
apps/web/
services/platform-api/        # 含 Policy / Assessment / Knowledge / Asset / Report 等模块
services/agent-orchestrator/
services/mcp-router/
services/model-gateway/
services/runtime-controller/
services/egress-gateway/
packages/contracts/          # API / policy / event / tool schema
runtime/control/
runtime/adapters/
deploy/helm/wuji-platform/
docs/
```

升级固定镜像 digest、工具 Schema、Graph/Prompt 和策略版本；保留活动任务的兼容执行版本，无法兼容的检查点暂停并显式迁移，不能用新图静默重放旧操作。配置和 Schema 变更有迁移策略，平台启动不得因依赖未就绪而绕过鉴权或策略检查。

| 演进项 | 启用条件 |
| --- | --- |
| Redis | 已测得缓存或协调需求；不能成为唯一业务账本 |
| NATS JetStream | Outbox 延迟、吞吐或消费者数量达到记录过的容量阈值；通过重投/乱序测试 |
| CRD | 存在 GitOps 或外部 Kubernetes 消费需求；先确定唯一写入方向 |
| 独立 Blackboard 服务 | 有独立扩容、权限或性能需求；保持原接口契约 |
| ExternalRuntime / 多集群 | 能验证身份、策略、出口、租约、取消和证据契约，先通过同一验收清单 |
| Browser / 网络探测 | 专用 Adapter 与所有流量通道通过范围、限速、取消验收 |

未来可引入 `TaskRuntime` CRD 作为 PostgreSQL 期望状态的单向资源投影：业务字段只由 Controller 写入，Kubernetes status 回传资源实况。不同时允许 API 与用户直接修改两份 Task 期望状态；原 v0.1 的 `PenTestTask` CRD 示例不作为首版契约。

## 13. 开发阶段与准入门槛

| 阶段 | 交付内容 | 进入下一阶段的条件 |
| --- | --- | --- |
| Phase 1：受控工具闭环 | Task API、基础租户/RBAC、ScopePolicy、Controller、MCP Router、HTTP Adapter、出口、调用账本/Outbox、事件查询、配额、取消、清理、最小 Helm；控制台登录/项目、任务和证据页面 | 无模型介入，在自建服务验证越界拒绝、非破坏性、跨租户隔离、限额、失联断流和资源回收；前端状态与执行结果一致 |
| Phase 2：单 Agent 评估 | Model Gateway/QuotaGroup、LangGraph + 一个已验证 Harness、框架上下文管理、配置快照、一个 HTTP 场景及知识包、CoveragePlan、VerificationRun、最小资产/证据模型、SSE、恢复、Markdown 报告快照及评估页面 | 上下文压缩/打断/恢复/辅助计费通过 H01–H10；提示注入不能扩大工具权限；恢复不盲目重复操作；阻断不算未复现；断线补发不造成状态回退 |
| Phase 3：多 Agent | Blackboard 扩展、Intent 租约、Dispatcher、角色模板、异步 Worker、独立身份/目录、验证交接与复核 | 重复认领、过期 Worker、状态冲突和并发预算通过验收；有 Browser 时先通过 Context 隔离验收 |
| Phase 4：平台完善 | Finding 研判/修复工作流、报告发布和多格式导出、资料导入、资产关系查询、租户管理、保留策略和容量演练 | 结论状态不混淆，报告版本固定，权限撤销及备份恢复可验证；未实现格式不声明支持 |
| Phase 5：按需扩展 | 额外 Adapter、CRD、JetStream、多集群/ExternalRuntime | 有量化需求，并通过原有边界与新能力的增量验收 |

各阶段场景与证据要求见 [架构验收清单](architecture-acceptance.md)。测试只针对自建服务、测试租户和隔离 Runtime；不为验证平台控制而访问未授权第三方或修改真实目标数据。

业务实现前增加 Phase 0：固定接口和依赖，验证身份、数据库约束、受控出口、Runtime 生命周期和恢复。当前已有 API 契约及独立前端原型；本地工程测试与平台验收分别记录，详见开工准备文档。

Phase 2 先实现内置配置、已上传资料引用和只读 HTTP 评估闭环；配置管理 UI、Git 导入和更多场景按需后续开放。评估模型中的对象先确定契约，未交付的能力不对外注册。跨阶段依赖和新增验收编号见评估业务契约第 9 节。

## 14. 待实现验证的选型

以下选型不改变前述契约，也不代表已有可用实现：

1. Egress Gateway 实现及 CNI 组合：验证规范化、DNS、IPv6、TLS、长连接撤销和聚合限流。
2. Agent Harness 与模型接入：优先验证 Deep Agents + 现成模型客户端接已有网关；固定上下文、取消、恢复和数据/计费能力后锁定版本。不以增加代理层补偿未知的上游行为。
3. Runtime 镜像与沙箱：验证 Kali 工具在 Restricted 配置下可运行；不兼容工具先不提供。
4. 容量参数：通过压测确定租户并发、Pod 资源、证据大小、Outbox 吞吐和数据库连接池配置。

本版验收前提是平台控制组件、集群管理员及策略签发链可信。针对这些主体被攻陷的防护需要额外威胁模型；不能以本架构宣称已经解决所有宿主机或供应链风险。
