# Wuji 自动化渗透平台架构

- **版本**：Cairn 架构修订（公开 API 仍为0.4.0）
- **日期**：2026-09-10
- **状态**：目标架构基线；身份/项目、范围预览、B2/B3任务管理与事件同步已实现并通过最小验证，完整执行闭环尚未实现
- **适用范围**：已获授权的非破坏性安全验证；禁止目标数据破坏、目标持久化和越权扩散
- **验收依据**：[架构验收清单](architecture-acceptance.md)
- **评估业务契约**：[评估、知识与交付模型](assessment-model.md)
- **前端实施设计**：[前端架构与技术选型](frontend-architecture.md)
- **Agent 执行层**：[Harness 职责与选型建议](agent-harness-decision.md)、[模型网关实测](model-gateway-validation.md)
- **本次复审**：[已批准架构替代决策](cairn-architecture-decision.md)；[原v0.4复审](architecture-review.md)保留为历史
- **参考复核补充（2026-09-10）**：[元刃后端复核](metablade-backend-review.md)、[已确认产品交互](product-interaction-proposal.md)；目标设计补充，公开 API 0.4.0 尚未升级
- **黑板明确要求（2026-09-10）**：[Cairn 黑板适配设计](cairn-blackboard-design.md)；直接复用Cairn Server/Dispatcher，目标协议尚未实现
- **开工准备**：[依赖与交付顺序](predevelopment-plan.md)、[Phase 1 API 契约](phase1-api-contract.md)

本次按用户批准的[架构复审修订](cairn-architecture-decision.md)更新目标设计：Cairn负责共享图和探索调度，Pi负责平台侧Agent循环与上下文，LiteLLM负责模型接入及Task金额预算。Wuji负责任务、执行准入、工具、证据和停止核对。LangGraph/LangChain/Deep Agents不再是该链路必选依赖；原P0实验与验收保留。本文不代表业务已实现；实际仍以[Phase1A](stages/phase-1a/acceptance.md)、[B1](stages/phase-1b/acceptance.md)、[B2/B3](stages/phase-1b/b23-acceptance.md)及[P0](stages/phase-1c-prep-p0/acceptance.md)记录为准。

2026-09-10 场景与流量补充设计见 [场景、执行边界与流量工作台](scenario-execution-design.md)。任务场景与 HTTP/Agent 实现能力分离；新增阶段授权、受管代理/MCP 出网资格与请求级流量视图的拟议契约。最新补充：Web 默认不配账号，成果凭据通过黑板受限引用共享；已批准阶段自动推进。外域页面资源可正常加载但不可主动测试，目标测试、依赖加载和候选核验采用不同执行许可。流量证据细化见 [Kali 流量方案](traffic-evidence-design.md)。该修订为待评审设计，不代表当前 0.4.0 已实现。

## 1. 目标与架构原则

Wuji 在 Kubernetes 中管理独立任务执行环境，由 Platform 中的 Agent 规划验证步骤，通过受控工具收集证据并生成可追溯报告。

必须满足以下约束：

1. 授权范围是服务端执行策略，不能由 Prompt、Agent 或目标返回内容扩大。
2. 每次执行同时满足身份权限、目标范围、操作类型、预算和有效租约约束。
3. 一个 Task 同时最多有一个获准执行的 Runtime attempt；故障重建可以产生新 attempt。
4. 工具执行、网络出口和模型访问都有独立于模型判断的控制点。
5. 暂停、取消、失联、恢复和结果不明是明确状态，不能用“停止推理”代替“停止执行”。
6. 外部请求不承诺 exactly-once；通过去重、执行账本和结果核对控制重复，结果不明时不盲目重试。
7. 多租户身份、资源配额和审计从首版建立；先以合成工具验证多Agent归属与共享Runtime，真实目标执行另需出口和停止证据。

“禁止持久化”指禁止在测试目标建立驻留、后门或其他持续访问机制。平台按保留策略保存任务、检查点和证据；这不授予在目标上写入数据的权限。非破坏性也不等于 HTTP GET 或工具名称含有“read”：仍须审查目标业务语义及请求负载。

## 2. 已确定的架构决策

| 主题 | 当前决定 | 边界 |
| --- | --- | --- |
| 任务映射 | 一个Wuji Project包含多个Task，一个Task对应一个Cairn Project | 草稿无Project；正式创建幂等绑定停止态Project，历史queued不自动执行 |
| Agent | 平台侧Worker Pod中运行多个独立Pi Harness进程 | 每Task首版一个Worker Pod；Agent不运行在Kali |
| 探索 | 复用Cairn Bootstrap/Reason/Explore及Worker选择 | Cairn状态不是许可；派发前经Wuji准入，不加第二个探索调度器 |
| 上下文 | Pi coding-agent独占会话、压缩和工作记忆 | 不自研循环/压缩/模型协议；候选版本未集成验收 |
| 黑板 | Cairn Server唯一可写Fact/Intent/Hint与探索图 | 首版单Server、单Dispatcher、持久化SQLite；Wuji只保存引用/投影与原始提交 |
| 目标环境 | 同Task多个Agent共用一个Kali容器，一个获准Runtime attempt | Runtime Controller独占Kali；Worker后端只管理Agent资源 |
| 工具 | 受信Pi扩展、Tool Router、Runtime MCP/受管能力 | 快照/工作记忆/业务/目标工具分权；默认本地执行工具关闭 |
| 模型与预算 | LiteLLM；组织发布模型方案，Task设置USD金额预算 | 全部辅助调用共用，不周期重置；未知价格不按零，禁止自动付费探活 |
| 执行恢复 | PostgreSQL执行记录、原结果、进程回执和幂等操作 | 先核对再恢复；同步失败只重投结果，不重跑探索 |
| 评估 | VerificationRun、CoveragePlan、Finding与报告版本 | 结构校验不等于漏洞确认；Cairn complete先作为提案 |
| 事件 | 各权威数据源本地事务事件，跨库凭回执同步 | 不假定跨库原子事务；投影不回写权威图 |
| 前端 | React/TypeScript/Vite/Ant Design，五主题 | Task是入口；公开API仍0.4.0，业务页面按已实现能力开放 |

## 3. 逻辑链路与部署边界

### 3.1 主要链路

```text
Console -> Platform API -> PostgreSQL（Task / 权限 / 配置 / 执行账本）
Platform API内Cairn Bridge <-> Cairn Server（SQLite探索图）
Cairn Dispatcher -> Wuji执行准入 -> AgentRun -> 平台侧Worker后端 -> Pi Harness
Pi -> 受限快照/工作记忆，或鉴权平台查询
Pi -> Tool Router -> Runtime Supervisor/MCP -> 一个共享Kali容器 -> 受控出口
Pi -> LiteLLM -> 已发布方案的上游模型
Kali产物 -> Artifact -> 对象存储；元数据/验证/报告 -> PostgreSQL
Agent原始结果 -> Wuji持久提交 -> Bridge幂等同步 -> Cairn图与回执
```

### 3.2 组件与资源所有权

| 组件 | 唯一职责 | 部署边界 |
| --- | --- | --- |
| Platform API | 身份/任务/配置/准入/验证/产物访问 | 现有FastAPI；Policy、Assessment、Artifact等先作为模块 |
| Cairn Bridge | Task归属、持久操作、控制/结果同步及完成提案 | API内部模块；不决定探索方向 |
| Cairn Server | 探索图、版本、事件和写入回执 | 独立服务、SQLite持久卷；无公开管理入口 |
| Cairn Dispatcher | 探索工作、Worker选择与并发 | 首版单实例；内存Future不是持久账本 |
| Agent Worker后端 | 平台Worker Pod、Harness进程/会话/回执 | 每Task首版一个Worker Pod，多AgentRun；只清理Agent资源 |
| Tool Router | 工具权限、真实身份、调用账本、当前attempt路由 | 独立受信服务；无模型循环 |
| Runtime Controller | Kali Runtime创建/重建/停止核对/回收 | 独立ServiceAccount；不启动Harness |
| Runtime Supervisor/MCP | 许可、工具执行、进程句柄、证据上报 | TaskRuntime受信控制容器，面向共享Kali工具容器 |
| LiteLLM | 模型、凭据、原生费用和Task金额限制 | 独立网关和数据库；上游Key不进入Agent/Kali |
| Egress | 目标与操作出口约束、流量归属和停止 | 平台独立执行边界；具体方案待后续设计/验证 |

平台Worker Pod和Kali Pod不共享文件卷、进程空间或凭据。Cairn的ExecutionBackend只适配平台Worker环境，其配置选择、执行上下文和cleanup需同步修改；不把原生Docker接口称为已支持Kubernetes。Agent不直接访问测试目标，Kali不持有平台数据库、Cairn管理或模型凭据。

详细边界见[架构决策](cairn-architecture-decision.md)、[Harness](agent-harness-decision.md)与[黑板](cairn-blackboard-design.md)。新增服务均为目标设计，本批不部署。

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
      allowedMethods: [GET, HEAD]
      operationClasses: [http-observe]
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

2026-09-10 用户删除路径级强制范围要求：目标策略只约束域名/子域、协议、端口及明确批准资产，不再包含路径白名单/黑名单。Schema 须明确域名规范化、子域匹配、IP 字面量和 IPv6 规则；路径可用于测试重点及流量查看，不构成权限。非破坏性约束仍通过已批准操作类别与受信 Adapter 实现，不能仅靠 GET/HEAD 名称判断。当前 0.4.0 的存量路径授权保持历史含义，正式迁移不得自动扩大旧授权。

主动测试权限为平台允许集合、租户策略、项目授权、Task Scope、RuntimeProfile、Worker 授权和 Tool Adapter 能力的交集；平台禁止项和其他拒绝规则优先。正常页面依赖按受管加载上下文获得独立、有限的访问许可；它不是测试权限，也不将外域加入 Task 测试 Scope。候选核验与平台服务亦独立按用途校验，不能使用一个目标白名单概括全部出网。

新增目标、延长授权或放宽操作须经有权限的操作者创建新版本；Agent 只能提交请求。现有授权可复用且仍有效时，不重复索要确认。版本切换先阻止新派发并停止或排空受影响调用；Router、Runtime、出口完成新版本绑定后才能恢复。撤销策略、授权过期和禁止项命中不得自动降级放行。

### 4.2 三个执行检查点

以下保留平台执行要求；具体HTTP转发、DNS/CNI及流量采集方案仍属后续设计，不构成本轮已选实现或已通过验收。

1. **Router**：校验可信身份、任务状态、策略版本、结构化参数、工具版本、操作用途、预算及租约，保存 ToolCall 后签发有限许可。
2. **Runtime**：验证许可与本机 Task/attempt 匹配，检查参数摘要、截止时间、去重记录、可用 Adapter 和进程配额；不接受 Agent 直接构造的权限字段。
3. **Egress Gateway**：独立验证工作负载与活动任务绑定、策略版本、执行有效期，检查实际目的地及累计请求量；拒绝 Runtime 直连互联网或平台内网。

Router 同时签发接收方为出口的调用许可，绑定 call/attempt、Worker 的目标子集、操作类型和请求额度；Supervisor 使用它发起出口请求。后续 CLI 只能获得该次调用的受限出口句柄，不获得任务通用控制凭据。网关逐请求校验许可并累计用量，Task 级网络可达不代表获得整个 Task 的操作权限。

原HTTP切片候选为受控 HTTP 请求转发，由网关解析并规范化 origin、方法、路径、请求头和重定向，不提供任意 CONNECT 隧道。TLS 在网关作为 HTTP 客户端连接目标并验证证书，返回受限响应。保留受控转发用于域名/工具操作检查及请求证据；不执行路径级范围校验。浏览器 HTTPS 内容可见性另行选型，不能仅凭 L4 日志声称已取得明文请求/响应。

解析 DNS 后检查全部候选地址，只连接本次验证过的地址；每次重试、重定向和新连接重新检查，防止校验和连接使用不同目的地。网关拒绝平台 Service/Pod/Node 网段、API Server、元数据服务和保留地址；客户内网目标只能通过显式批准且与平台基础设施隔离的出口配置接入，不能笼统放行所有私网。

发现新域名、子域名或关联资产只记录为候选事实，不自动纳入范围。跨 origin 不转发 Authorization/Cookie。限定到 Host 的授权不能因共用 IP 扩展为整台服务器授权。

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

Task 和 Worker 必须配置最大运行时间、工具调用数、Agent 并发/深度和产物大小；模型接入后还须配置Task金额上限（USD），Token用于统计和上下文容量。子级截止时间和配额不能超过父级；到期执行取消链路，预算耗尽停止新派发并按策略进入暂停或停止流程。

当前0.4.0不开放目标执行。原HTTP观察切片使用 `http_observe` 的设想保留为候选；新增Kali工具按后续Spec和出口能力逐项开放。后续 `browser_observe`、`network_probe` 只有在各自出口约束通过验收后才能启用；浏览器子请求、WebSocket、下载和后台请求同样受控，不支持的通道拒绝。

HTTP 观察是第一个可验收切片，不是长期产品能力上限。后续可并行建设离线源码审计、浏览器与协议分析 Profile；源码审计优先使用只读输入快照和离线解析 Adapter。需要构建或执行输入代码时必须单独设计沙箱和验证契约，不能借“代码审计”默认获得任意代码执行或网络权限。

目标命令/脚本和Kali文件操作由受管工具能力提供，不能在平台侧直接使用任意Bash或本机文件工具。参数、工作目录、代理及可执行能力由服务端限定；不通过shell字符串拼接构造平台控制命令。Artifact接口使用受限句柄，Kali路径不等于证据引用；交互终端/远程桌面另行按权限与出口能力开放。

### 5.2 Base MCP

```text
get_task / get_blackboard
get_coverage / get_asset_context / load_skill / read_reference
write_observation / propose_fact / propose_finding
submit_intent / request_worker / request_verification / submit_verification_result
save_artifact / request_report_draft
```

上述是按阶段开放的逻辑工具目录，不是当前已实现接口。Worker 请求由 Dispatcher 再检查权限和剩余预算，不能直接创建自由运行的子 Agent。模型只能提交候选事实、验证结果及 Finding；Assessment 模块根据证据和 ValidationRuleVersion 决定可接受的结论。Cairn Fact记录共享发现，真实性由Wuji验证记录和证据关系表达；Finding使用分离的证据/研判/修复/发布状态，避免一个 verified 布尔值混淆多个含义。规则不满足时保留不确定状态。

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

本节仅描述Kali目标执行Pod，Agent Harness运行在另一个平台侧Worker Pod。Agent会话/模型凭据不进入本节工具环境；两类资源生命周期分别归属Worker后端和Runtime Controller。

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
| Cairn Dispatcher / Worker后端 | API准入/Bridge、受限Worker执行控制 | 服务身份限定的调度与Agent资源操作 |
| 平台Agent Worker | LiteLLM、Tool Router、受限快照/证据接口 | 当前Task/AgentRun限定能力；无目标直连 |
| Router | 绑定的 Runtime MCP | mTLS + 有限执行许可；禁止任意用户指定 URL |
| Runtime Supervisor | Router、Artifact 接口、Egress Gateway | 身份绑定的心跳/结果、受限上传、授权目标请求 |
| Kali 工具容器 | Egress Gateway、受限本地 Adapter 通道 | 仅接受逐调用出口许可；无权访问平台业务 API |
| Egress Gateway | 已验证目标、获准页面依赖/候选核验目的地、受控 DNS | 按用途许可与活动租约检查连接；辅助访问不变为测试权，拒绝平台网段 |
| Model Gateway | 租户允许的 Provider/适配层 | 数据策略允许的模型请求 |
| Runtime Controller | Kubernetes API、任务存储、出口管理接口 | 资源协调、执行租约及撤销 |

Pod 级策略无法区分同 Pod 容器，因此表中控制容器专有的平台接口还必须认证其独享凭据，工具容器即使网络可达也无权限。Runtime 不需要任意 DNS，目标解析由出口执行；必要的内部服务解析使用受控解析器，禁止借 DNS 外发任意数据。

Namespace 按租户划分，Task 使用服务端不可由工具修改的标签和 Pod UID 绑定；每 Task 一个 Namespace 可作为管理选择，但不能替代上述控制。Egress 身份绑定到已注册工作负载及有效 attempt，不采用客户端自报 task header，也不能仅凭可复用的 Pod IP 认证。

### 6.3 Controller 调谐

Controller 根据 PostgreSQL 中的 Task 期望状态反复调谐，使用任务版本、唯一活动 attempt 约束和协调租约避免多副本重复创建。资源使用确定名称及 task/attempt/Pod UID 标签；策略就绪、身份签发、出口注册和 MCP readiness 全部完成才进入 ready。

Controller 的集群权限限定在预置 Runtime Namespace 内的必要资源，不能创建 RoleBinding、任意特权 Pod 或修改平台资源。Namespace 和配额由部署管理流程预置。Pod 创建成功但 DB 回写失败时按资源标签核对，不重复建立第二个可执行环境。

重建前撤销旧 attempt 出口权限并确认撤销或等待其租约失效，再激活新 attempt。临时浏览器会话和进程不承诺恢复；Pod重建先冻结派发并核对旧调用；不能因为新Pod就重新Bootstrap或重跑结果不明的操作。

回收覆盖 Pod、Service、临时 Secret、工作卷和出口授权。保存独立 `cleanup_status`，定期清扫带有效所有权标记的孤儿资源；清扫器不得按模糊名称删除不属于本平台的资源。

## 7. 生命周期、恢复与事件一致性

### 7.1 状态权威

Wuji PostgreSQL维护Task期望状态、授权、执行代次、AgentRun、Runtime/工具账本及原始结果。Cairn维护探索图，LiteLLM维护原生模型计量；Kubernetes提供资源实况。界面和事件投影不是独立写入源。

草稿不创建Cairn Project，正式Task幂等绑定初始stopped Project。需要Cairn原子停止态创建和外部Task标识唯一能力，不能先active再停止。跨库以稳定操作ID、摘要、回执和按Task排序的持久操作同步；每个数据源只保证其本地事务，不声称跨库原子完成。

### 7.2 Task与执行许可

```text
草稿 -> 正式创建ready（Cairn stopped）
ready --显式start--> queued / provisioning -> running（Cairn active且Wuji准入通过）
running -> pausing -> paused
非终态 -> cancelling -> cancelled
完成提案被接受 -> completing -> completed（目标达成或明确partial结果）
执行仍否继续未知 -> reconciling（禁止重新派发）
```

这是目标状态机，不是当前0.4.0 DTO。现有迁移限定queued/cancelled、活动调用恒零；ready/start、执行状态、代次和账本须随0.5契约及迁移同步实现。旧queued没有启动记录，不能自动接管，也不能伪造曾经ready/start的历史。

每次Agent派发和工具请求重新检查Task、真实身份、当前epoch、有效授权/配置、预算及runtime_attempt。Cairn active/stopped不能代替执行许可。worker_profile_id表达能力和容量，agent_run_id表达本次真实执行/认领/会话；Intent有运行、停止核对或结果同步中AgentRun时拒绝重复派发。

### 7.3 持久交接与失败

Agent启动前登记AgentRun，保存进程归属及后续回执。结果先持久化原始结构化提交/产物引用，再校验并登记稳定黑板操作；Cairn写入后返回原生ID和回执，Wuji登记同步完成。黑板不可用时保持结果待同步，只重投结果，不重新询问模型或访问目标。

取消前接受的结果可以补入历史；取消后产生的新提案不触发执行。读取旧回执和申请新许可分别处理。通知或流连接丢失不代表任务未执行；Cairn内存Future不是恢复账本。

工具保留逻辑tool_call_id与实际attempt，派发前保存参数摘要和许可，Runtime接受/启动/退出分别有记录。相同ID不同输入拒绝；可能已执行的工具不能因超时、换Pod或新会话ID直接重发。明确重试也重新检查授权和剩余限额。

### 7.4 完成、暂停、取消与重启

Dispatcher complete先交Bridge作为完成提案，不立即触发Cairn默认完成清理。平台核对目标、覆盖和证据；仍缺必需项且允许继续时反馈缺项。接受结束后停止新派发，分别核对Agent及Kali活动执行，再定终态。达成目标才写Cairn完成边；预算/环境/用户决定导致部分结束时保持stopped，不伪造goal达成。

暂停和取消先改变平台执行许可，再传播到Dispatcher、Harness、Tool Router、Runtime与出口。Worker后端只停止/清理Agent资源，Runtime Controller独占Kali。SDK abort和Pod删除请求都不是停止证明，不承诺撤回或回滚已发送的目标请求。

执行是否仍在继续未知时保持reconciling；已确认执行/出口停止但结果缺失时保留未知结果和证据缺口，可按partial结束，不能转成成功或未复现。停止与资源清理状态分开，清理失败保留待处理状态。

首次集成在Dispatcher/Worker重启后先冻结相关派发，核对持久AgentRun、进程回执、会话和ToolCall，再决定显式恢复；不承诺无缝续接，不因租约超时直接换Worker重跑。终态复测创建关联新Task，不用Cairn reopen改写历史。

## 8. Agent与共享黑板

### 8.1 框架和数据

Cairn Server是Fact/Intent/Hint及探索关系的唯一可写来源，首版单Server/单Dispatcher/SQLite持久卷。Cairn Dispatcher复用Bootstrap/Reason/Explore及Worker匹配；Pi coding-agent复用模型客户端、循环、会话和压缩。LangGraph/LangChain/Deep Agents不再必选，P0实验及证据保留。

Bridge负责平台归属、操作和结果同步，不选择下一Intent。原始Agent提交、Wuji图引用与只读投影不能成为第二套可写Fact。共享图、Agent完整会话和Kali共享文件是不同资源；一块黑板只绑定一个Task，跨Task引用须显式保留来源并重新鉴权。

### 8.2 工具和上下文

Pi关闭自动发现和默认本地执行工具，只加载受信扩展/版本化知识。快照工具只读取本AgentRun绑定的不可变黑板快照，不能接收任意平台路径；工作记忆只作用于限定AgentRun存储。Cairn原生图文件交付必须同步改造，不能只删除read工具。

目标命令、文件和浏览器操作经Tool Router/MCP在共享Kali中执行。工具白名单同时在Harness与服务端检查；MCP session、模型自报ID、提示词或工具名字都不能授予权限。当前Scope/epoch从平台装配，不依赖摘要保存授权。

同Task共享Kali工具环境，AgentRun/ToolCall分目录，浏览器Context按执行/身份区分，共享端口/代理等可变资源由工具服务协调。目录不是同容器恶意执行者的强隔离。Kali路径只用于现场定位，登记Artifact后才作为可追溯引用；缺失产物明确标注。凭据以受限引用共享，不广播明文。

### 8.3 验证、覆盖和人工介入

Origin是起始依据，Goal是未达成目标，Fact为共享发现而非已确认漏洞。VerificationRun表达主张、方法、证据与结论，AgentRun表达一次执行；Finding/Report按明确规则生成并保留版本。CoveragePlan不能扩大Scope，缺项/阻断/未知不改成未复现。

Hint为建议、回答绑定具体问题、控制/授权变更走权限化命令；三者不可混用。范围扩展由人决定，已授权阶段按策略推进，不把全部工具调用改为人审。五场景由版本化输入/阶段/完成条件驱动同一调度引擎，不开发固定角色流水线。

会话、压缩和工作记忆由Pi维护，网关不二次编排历史，黑板不合并所有聊天。证据/摘要保留来源数据身份，不升级成系统规则。恢复已删除会话时明确不可恢复，不依赖模型猜测。

### 8.4 界面与事件

Agent原始事件转成受限领域事件后才对外提供，展示运行状态、工具调用、产物、结果和限制；不公开隐藏推理。黑板变更、版本、事务事件与回执是所需Cairn增量，不能把现有重建时间线称为完整不可变事件日志。

Wuji查询投影按来源ID/版本/游标去重，只在校验成功后推进；快照按各来源版本标注，不假装跨库全局原子快照。历史回放只读已有数据，不调用模型/目标。详细职责见[Harness](agent-harness-decision.md)和[黑板](cairn-blackboard-design.md)。

## 9. LiteLLM与任务预算

### 9.1 配置与模型接入

Model Gateway采用LiteLLM Proxy，候选v1.100.0。组织共享模型配置由TenantAdmin维护，Task选择已发布版本；平台模型配置不设置Task预算。发布要求管理员显式触发的同版本连接检查成功，保存配置不隐式请求模型。无可用方案时只能保存草稿。

Pi原生模型客户端接LiteLLM，再路由到已配置上游。上游Key只在网关；平台侧Agent仅使用Task限定凭据，无管理权限，Kali不接收模型凭据。LiteLLM使用独立数据库与原生迁移，密钥保存/运行镜像和实际兼容性由后续Spec固定验证；P0的私有文件/ProviderSession/IPC/次数账本不作为生产网关。

### 9.2 金额与辅助调用

Task金额预算按USD计量，全部Agent/Reason/Bootstrap/收尾/摘要/重试共用LiteLLM原生预算，不周期重置，不因换Worker、模型或重建Runtime创建新预算。Token作为上下文容量和用量指标；价格未知不按零，也不宣称金额限制可用。

达到预算后停止新增模型请求及继续派发；已在途请求可能继续结算，不承诺未经验证的并发零超支。预算耗尽不额外请求模型写总结。平台保存预算配置、归属、费用引用及耗尽后的控制状态，不再自建另一套模型金额预占/结算引擎。

共享上游容量关系必须有依据，不能按别名/URL猜测；确需QuotaGroup元数据时仅表达已确认关联，不能让子Agent分别领取完整Task预算。原生网关不能满足的能力须明确记录缺口，不静默重建通用网关。

### 9.3 重试、健康与停止

关闭Cairn自动付费探活；普通readiness/liveness不请求模型。无效配置、权限拒绝、不支持工具等错误不能按短周期重启Worker。结果不明先核对，不自动更换模型/幂等键追加付费调用。收尾最多按既定单次流程且仍受Task预算限制。

网关、SDK及Harness隐式重试/fallback必须显式收敛；模型主动纠错是有预算的新回合，目标工具重试仍由Tool Router账本控制。原生网关取消不代表上游费用回滚；迟到用量继续关联原Task。

### 9.4 数据策略

发送模型前按任务分类限制数据，原始敏感证据和凭据不默认进入上下文；System/Developer规则与用户/目标/工具数据分开。未知模型能力、容量、价格不从名字猜测，协议连通不代表工具/流式/Harness通过。

会话/摘要/工具日志按保留策略保存，第三方遥测默认关闭。LiteLLM不重排或压缩Harness历史，也不覆盖Task、Scope或黑板的状态权威。完整模型/网关兼容和恢复矩阵不属于本轮文档验收。

## 10. 多租户数据、证据和审计

### 10.1 PostgreSQL

以下为Wuji PostgreSQL目标实体；Cairn图表和LiteLLM原生表不放入此数据库：

```text
Tenant / Project / Membership / Authorization / ScopePolicy
Task / TaskRuntime / AgentRun / CairnTaskBinding / GraphOperation / GraphProjection
ConfigSnapshot / ScenarioProfileVersion / AgentProfileVersion / SkillPackageVersion
Reference / ReferenceVersion / CoveragePlanVersion / CoverageItem
VerificationRun / ValidationRuleVersion / VerificationTemplateVersion
Asset / AssetRelation / Observation / EvidenceLink / CairnFactRef / Hypothesis
Finding / FindingRevision / Artifact / ReportCommit / ExportArtifact
ToolCall / ToolAttempt / ModelUsageRef / TaskBudgetConfig
QuotaGroup（已确认关系）/ ToolBudgetLedger / AuditEvent / OutboxEvent
```

所有业务记录携带 tenant_id，项目级记录携带 project_id；父子关系使用包含租户/项目维度的复合约束，阻止跨租户关联。服务端从身份和资源归属建立上下文，禁止只凭客户端 tenant_id 查询。

采用 PostgreSQL RLS 作为纵深隔离，应用角色非 superuser、无 BYPASSRLS、不是表 owner，必要时 FORCE ROW LEVEL SECURITY；迁移角色与运行角色分开。租户上下文按事务设置，连接池复用后不得残留。RLS 依赖可信服务正确建立上下文，不声称能防御任意被攻陷的共享数据库客户端。

运行角色不授予 TRUNCATE、DDL 或任意角色切换权限；使用行级策略时仍需独立限制表级权限。[PostgreSQL RLS 说明](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

基础角色按项目分配：Viewer 查看被授权的脱敏结果；Operator 在已批准 Scope 内创建和控制任务；ScopeManager 管理授权与策略版本；TenantAdmin 管理本租户成员和配置。角色可组合，但租户管理员不能越过平台禁止项。原始敏感证据下载和数据导出是独立权限，不随普通查看权限自动授予。

后台执行同样限定Task归属，Controller只持有所需资源/状态权限。Cairn SQLite和LiteLLM独立数据库不自动继承Wuji RLS，各自通过受信服务入口和任务映射控制权限。

Pi会话ID映射到真实AgentRun，用户不能凭底层session读取其他任务内容。会话格式使用Harness原生实现，不新建LangGraph检查点作为目标必选项；平台账本保存恢复与结果核对依据。

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

创建页先选可用场景，再补齐目标与可选资料；Web 单点默认匿名且不提供账号配置，运行中取得的身份作为受限任务成果管理；显示有效目标、授权期限、排除项、允许操作、请求上限、模型数据策略和出口位置。服务端保存配置及策略快照；用户看到的范围与执行策略使用同一版本。缺少 Adapter 或凭据的测试维度显示阻断原因，不伪装为可启动的完整场景。

状态展示区分暂停中、已暂停、取消中、已取消、结果核对中、清理待完成；API 接受取消请求后不能立即显示“已停止”。写命令使用幂等键，超时先核对原命令；不自动换键再次提交。事件带游标，快照与订阅之间提供一致交接；SSE 断线后从持久事件补发，客户端去重并校验资源版本，游标失效时重新同步快照。

MVP 只查看工具日志、截图和证据。后续浏览器交互仍通过 Platform API、项目权限和执行许可；人工请求使用相同的 Scope/预算控制，不提供绕过 Router 的终端或直连 Pod 通道。

工作区允许按 CoverageItem、VerificationRun、Fact、Finding 筛选资产、流量、工具调用和文件，均使用服务端关系查询与同一授权。总览优先呈现需要介入的阻断、证据冲突、未知执行和预算等待；执行进度、计划内评估率、发现证实比例分别展示并标注分母。

先实现时间线与单条 Finding 的证据链，再增加全图、里程碑回放和全局搜索。回放使用已存事件，不向目标发送流量；Agent 展示简短决策摘要、依据和计划变更，不依赖保存或公开模型隐藏推理过程。

Phase 1 先交付登录/项目、任务列表、基本范围预览、任务详情和受控证据查看，可用有界只读轮询同步状态；Phase 2 再接入场景/知识配置快照、评估页面和 SSE。配置中心、全图和发布工作流随对应后端能力开放。页面权限、证据预览和缓存隔离从首版验收，不能等待 Phase 4 才建立。

## 12. 部署与演进

目标部署按平台服务、Agent Worker和Kali Runtime分权；生产数据服务可外置。两类任务Pod分别由各自所有者管理，不为每Task建立独立Helm release；本批不部署。

第3节是目标边界，实际业务仍0.4.0。后续依赖改为控制面基础→调度适配→共享Runtime→产品接入→真实目标开放；配置/账本不能放到真实调度之后。未实现能力不注册为可执行工具。

控制台由独立 web 容器提供静态文件，与 API 共用浏览器访问入口；SSE 关闭代理缓冲并配置连接超时。SPA fallback 不接管 API、证据和事件响应。入口 HTML/公开运行配置与带摘要静态资源分别配置缓存，业务数据不进入共享静态缓存。构建产物不包含凭据，详情见前端设计第 8 节。

建议目录（尚未实现）：

```text
apps/web/
apps/api/                    # 已有，后续含 Cairn Bridge / Policy / Assessment / Artifact
services/cairn-server/        # 候选部署配置，不在本批实现
services/cairn-dispatcher/
services/agent-worker/
services/mcp-router/
deploy/litellm/              # 使用上游原生网关
services/runtime-controller/
services/egress-gateway/
packages/contracts/          # API / policy / event / tool schema
runtime/control/
runtime/adapters/
deploy/helm/wuji-platform/
docs/
```

升级固定镜像 digest、工具 Schema、Cairn/Pi/Prompt 和策略版本；保留活动任务的兼容执行版本，无法兼容的检查点暂停并显式迁移，不能用新图静默重放旧操作。配置和 Schema 变更有迁移策略，平台启动不得因依赖未就绪而绕过鉴权或策略检查。

| 演进项 | 启用条件 |
| --- | --- |
| Redis | 已测得缓存或协调需求；不能成为唯一业务账本 |
| NATS JetStream | Outbox 延迟、吞吐或消费者数量达到记录过的容量阈值；通过重投/乱序测试 |
| CRD | 存在 GitOps 或外部 Kubernetes 消费需求；先确定唯一写入方向 |
| Cairn容量/高可用演进 | 首版已是独立单实例服务；有量化需求后再设计迁移/高可用，不能直接横向复制SQLite写实例 |
| ExternalRuntime / 多集群 | 能验证身份、策略、出口、租约、取消和证据契约，先通过同一验收清单 |
| Browser / 网络探测 | 专用 Adapter 与所有流量通道通过范围、限速、取消验收 |

未来可引入 `TaskRuntime` CRD 作为 PostgreSQL 期望状态的单向资源投影：业务字段只由 Controller 写入，Kubernetes status 回传资源实况。不同时允许 API 与用户直接修改两份 Task 期望状态；原 v0.1 的 `PenTestTask` CRD 示例不作为首版契约。

## 13. 开发依赖与准入门槛

本批只做[架构文档收口](stages/cairn-architecture-baseline/spec.md)，实际开发进度见[背景索引](project-context.md)。Phase1A保持partial，B1/B2/B3原证据及P0实验不改写。

| 后续批次 | 必须交付 |
| --- | --- |
| 控制面基础 | 0.5契约、必要配置快照、ready/start、执行代次、AgentRun/工具账本、Task与Cairn绑定 |
| 调度适配 | 派发准入、平台Worker后端、Pi受限工具、持久结果回写；先合成工具夹具 |
| 共享Runtime | 多Agent对接一个Kali、产物登记、取消和停止核对 |
| 产品接入 | 原型评审后接正式创建与执行观察页面，复用已冻结接口和五主题 |
| 真实目标开放 | 出口和停止边界有证据后启用，详细流量设计仍需单独收口 |
| 后续平台完善 | VerificationRun/覆盖、Finding、报告、资料、图查询按对应业务Spec推进，不重新开发调度引擎 |

每批先冻结具体Spec/Plan、API与迁移、归属及最小验证入口；上述依赖表不是已批准业务任务书。旧0.5草案superseded，不直接施工。配置和框架不能满足所需能力时记录阻断，不能悄悄换框架或扩大测试。

后续最小验证只覆盖未启动不派发、独立AgentRun共用Runtime、结果重投不重跑、工具越权拒绝、取消与迟到派发、历史queued不执行。原共享检查预算426/600秒已用，剩174秒，真实4次额度已用完，不按重拆批次重置；预算不足则待测。架构验收目录是历史场景参考，不是每次全量执行清单。

## 14. 待实现验证的选型

以下选型不改变前述契约，也不代表已有可用实现：

1. Egress Gateway 实现及 CNI 组合：验证规范化、DNS、IPv6、TLS、长连接撤销和聚合限流。
2. Cairn 8e7e0ea、Pi 0.73.0、LiteLLM v1.100.0为候选集成基线；适配、实际工具表、金额计量与停止待验证，未验证不称可用，不静默换框架。
3. Runtime 镜像与沙箱：验证 Kali 工具在 Restricted 配置下可运行；不兼容工具先不提供。
4. 容量参数：后续集中容量验证再确定，不能借本次文档修改启动压测。

本版验收前提是平台控制组件、集群管理员及策略签发链可信。针对这些主体被攻陷的防护需要额外威胁模型；不能以本架构宣称已经解决所有宿主机或供应链风险。
