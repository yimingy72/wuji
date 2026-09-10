# Wuji v0.4 评估、知识与交付模型

- **日期**：2026-09-09
- **状态**：待实现业务契约；示例不是已部署 API 或已通过验收的能力
- **上层约束**：[平台架构](architecture.md)
- **验证方式**：[架构验收清单](architecture-acceptance.md)

本文件补充“为什么执行、验证了什么、覆盖到哪里、怎样交付”。所有主动操作继续服从平台架构中的身份、ScopePolicy、预算、租约、出口和取消约束。业务模型不能自行授权目标访问。

## 1. 对象职责与关系

| 对象 | 负责表达 | 不应承担 |
| --- | --- | --- |
| Task | 一次有授权、预算和配置快照的评估工作 | 永久复用的无限授权会话 |
| ConfigSnapshot | 本次使用的场景、角色、知识、资料、规则及环境版本 | 指向随时变化的 latest |
| CoveragePlanVersion / CoverageItem | 已定义测试范围、维度、身份及完成判据 | 扩大 Scope 或声称系统全覆盖 |
| Intent | 准备推进的探索问题与依赖 | 已成立的漏洞结论 |
| Hint | 带作者与来源的人工提示或 Agent 态势判断 | Fact、授权扩展或直接恢复/停止命令 |
| AgentRun | 执行者的一次上下文、调度、用量和租约 | 验证结果本身 |
| VerificationRun | 固定主张、方法、前提、身份、证据和结论的一次核实 | 单个 shell 命令或“又一个 Agent” |
| ToolCall / ToolAttempt | 逻辑工具请求与实际执行尝试 | 证明目标安全或业务判据满足 |
| Observation / Artifact | 原始观察及其受限存储内容 | 自动成为可信指令或已确认结论 |
| EvidenceLink | 观察如何支持、反驳或限制一个主张 | 复制一段无来源的模型总结 |
| Fact / Hypothesis | 有来源的事实或待验证假设 | 直接获得目标访问权限 |
| Asset / AssetRelation | 项目内对象及带来源、时间的关系 | 所发现资产都已授权 |
| Finding / FindingRevision | 稳定发现身份及不可覆盖的结论版本 | 混合所有状态的 verified 布尔值 |
| ReportCommit / ExportArtifact | 固定内容清单及具体格式的交付产物 | 会随 live 数据变动的公开报告 |

Task 绑定一个 ConfigSnapshot，并引用多个顺序演进的 CoveragePlanVersion。CoverageItem 可产生多个 Intent 和 VerificationRun；一个 VerificationRun 可由多个顺序交接的 AgentRun 完成，各自保留执行归属。探索 ToolCall 可以尚无 VerificationRun，但必须关联 Task、Intent、AgentRun；Phase 1 的人工受控调用记录操作者主体，不伪造 AgentRun。

EvidenceLink 连接不可变 Observation/Artifact 版本与 Fact、VerificationRun 或 FindingRevision。Finding 可引用多个验证结果，一个验证结果也可支持多个不同主张，但每个关联须写明适用部分，不能将一份证据的强度扩展到未验证的影响。

所有对象和关联使用 tenant/project 复合归属约束；任务内执行对象额外检查 task_id。复用历史证据通过显式引用保留 source_task_id 和原身份/时间，不能复制后声称是本次新验证。授权判断从当前 Task 策略派生，不从资产关联、历史证据或报告内容派生。

## 2. 场景、角色、知识和资料

### 2.1 配置契约

| 配置 | 必要字段 | 发布与运行规则 |
| --- | --- | --- |
| ScenarioProfileVersion | 场景目标、起手维度、required_inputs、推荐角色、完成判据、预算建议 | 场景只是计划模板；用户选择后再求交 Scope 和实际能力 |
| AgentProfileVersion | 角色说明、逻辑 Model Profile、工具/Skill 子集、输入输出 Schema、并发/层级建议 | 所有主/子 Agent 均装配平台约束；配置权限不能超过 Task |
| SkillPackageVersion | manifest、版本、内容摘要、发布者、信任级别、依赖、适用 Adapter/规则、文件清单 | 审核后发布，固定依赖版本；方法文本不授予新权限 |
| ReferenceVersion | source_type、来源、内容摘要、大小、MIME、采集时间、访问级别、源 commit（适用时） | 用户文档、源码和历史报告默认为不可信数据 |
| ValidationRuleVersion | 输入证据 Schema、前提、可接受结论、检查条件、复核要求 | 校验结论能否被接受，不自行发送目标请求 |
| VerificationTemplateVersion | 声明式步骤、Adapter 版本、目标变量、前提、期望观察和规则引用 | 通过 Tool 注册表和 Scope 预检后才可执行，不是任意代码入口 |

平台预置配置也有发布版本。增加 ConfigPublisher、FindingReviewer、ReportPublisher 等权限点，由 TenantAdmin 在允许范围内分配；这些权限不自动包含 ScopeManager 或敏感证据导出权限。Agent 没有发布平台知识、修改规则和扩大工具权限的权限。

ConfigSnapshot 保存上述版本 ID、内容摘要、initial_scope_version、RuntimeProfile、Prompt/Graph/Tool Schema、Harness/客户端版本及 ContextPolicy。Task 另存当前有效 Scope 绑定及其变更历史；后续合法 Scope 切换不改写初始配置快照，每次验证、调用和覆盖计划记录实际使用的 Scope 版本。绑定的旧配置版本被安全撤销时停止新派发，暂停受影响任务并按取消契约处理在途操作；普通更新不影响已运行任务。迁移到新知识、资料或方法配置创建关联新 Task，避免同一次评估悄悄改变依据；Scope 调整使用平台架构定义的版本切换链路。

### 2.2 起步场景与角色

产品任务类型已按用户要求调整为 CTF、Web 单点渗透、综合渗透、攻防演练、代码审计，详见 [场景修订](scenario-execution-design.md)。下文 web-observation 是早期能力配置，不作为顶层产品场景。TaskStage/StageGate 与独立资产授权对象待具体阶段契约冻结。

首个场景 `web-observation` 只组合已验收 HTTP 观察能力，起手维度包括入口可达性、响应配置和公开内容观察。登录、访问控制、源码和协议分析在相应输入与 Adapter 可用后增加；缺失维度记录 blocked 或 not_run，不直接隐藏。

采用用户明确要求的 [Cairn 风格黑板](cairn-blackboard-design.md)，由 Fact/Intent/Hint 的当前态势产生下一步工作，不固定 Planner→Explorer→Verifier 流水线。角色模板只表达模型、工具、方法和输出能力：Phase 2 用一个通用 Agent 读取黑板、规划和推进必要验证；Phase 3 才按可执行 Intent 与能力匹配分派 Worker。CodeAuditor 等专用配置在需要时匹配；Reporter 先为生成草稿的逻辑能力，不必启动常驻 Agent。模型能力、工具集合和网络操作始终受平台交集策略约束。

### 2.3 按需知识加载

Orchestrator 根据已固定场景和 AgentProfile 提供可用 Skill 目录，模型可请求加载允许的文件。Knowledge 模块验证版本、摘要、路径和可见范围，拒绝 `../`、符号链接越界及未列入 manifest 的内容。加载日志关联 Task、AgentRun、模型调用和内容摘要，并限制文件数、体积和上下文 Token。

发布的 Skill 方法作为有明确来源的参考内容进入上下文，最高优先级规则仍由平台装配；用户上传的 SKILL.md、AUTHORIZATION.md 或提示词不自动成为配置。Reference 中出现的“调用工具”“修改规则”等文本只作为待分析内容。检索缓存和摘要缓存至少按租户、项目、内容版本、访问级别及模型数据策略隔离；摘要不能将来源可信度升级。

Skill 脚本和二进制依赖不能通过“加载知识”执行；确需执行的依赖必须进入已验收 Adapter 镜像和 Schema。知识更新、下载资料和启用工具是三个不同操作。

按需加载复用 Harness 的机制，Knowledge 模块提供限定版本的只读后端。框架维护的待办、记忆与压缩摘要属于 AgentRun 工作状态，不能直接修改 CoveragePlan、发布知识或形成 verified Fact。可信规则、原始证据和执行账本各有独立权威；上下文压缩不删除这些记录，也不改变来源可信度。摘要等辅助调用纳入同一 Task 模型预算。

### 2.4 资料导入

Phase 2 支持已上传且完成校验的文件快照；后续 Git、URL 和压缩包导入使用独立受限作业。下载来源由资料导入策略授权，不把资料 URL 加入测试 Scope，也不借资料下载绕过网络限制。Git 固定 commit，默认不执行 hook、构建脚本、子模块或 LFS 外联；这些依赖如确需获取须分别批准来源并留版本记录。

解析在低权限离线进程进行，限制文件数、解压后体积、嵌套深度和时间，拒绝路径逃逸；源凭据不进入模型或任务共享目录。引用 ID 先经项目权限校验，下载链接不能替代 ReferenceVersion 归属。分析输出保留源文件/commit/位置，资料更新不会覆盖旧版本。

## 3. VerificationRun：验证与执行分离

### 3.1 最小记录

```yaml
verificationRun:
  id: vr-001
  taskId: task-001
  coverageItemId: cov-001
  configSnapshotId: cfg-001
  scopeVersion: 1
  claim: "指定公开端点的响应包含已定义的安全响应头"
  targetRef: asset-app-001
  identityRef: anonymous
  methodRef: response-header-observation@1
  validationRuleRef: header-presence@1
  preconditions: [approved-origin, reachable-response]
  executionStatus: queued
  verdict: unassessed
  evidenceRefs: []
  limitations: []
  supersedesVerificationRunId: null
```

示例是字段形状；实际 Schema 还必须携带 tenant/project、创建主体、截止时间、版本、预算绑定及 attempt 关联。主张应当能在给定身份与方法下被核实，不能写成“目标绝对安全”。创建请求固定主张与方法；改变主张、身份、方法或重新复测必须创建新 Run。

### 3.2 状态与结论

执行状态使用 `queued / running / waiting_review / completed / blocked / cancelled / failed / reconciling`。结论独立使用：

| verdict | 含义 | 接受条件 |
| --- | --- | --- |
| `unassessed` | 尚未形成可接受判断 | 未执行，或关键前提未满足 |
| `confirmed` | 给定主张在本次条件下获得证据支持 | ValidationRuleVersion 要求的证据和前提满足 |
| `not_reproduced` | 按本次方法执行后未观察到预期现象 | 方法已完整执行，必要对照有效，观察未缺失；不是“证明不存在” |
| `inconclusive` | 已获得部分观察但不足以接受确定结论 | 记录证据缺口、相互冲突或测量限制 |

`confirmed` 指主张被支持，不必然意味着存在漏洞：示例“响应头存在”成立也可 confirmed。是否构成 Finding 由主张类型、影响证据和研判决定。界面不能把所有 confirmed 验证都计成漏洞。

blocked/failed/cancelled 不自动产生 not_reproduced；已完成的子观察保留，整体结论为 unassessed 或有依据的 inconclusive。ToolCall unknown 会使相关验证进入 reconciling，禁止新的目标尝试；执行核对解决后才能结算。自动任务重试只按平台 Router 规则处理，验证层不额外重试一次目标操作。

### 3.3 复核、交接和恢复

Worker 提交候选结果与证据 ID，Assessment 模块先验证归属、内容摘要、方法前提、执行记录及规则条件。需要人工复核的类别进入 waiting_review；Reviewer 通过权限化命令确认或驳回，并记录理由。不能仅凭另一个模型同意、置信分数高或 exit code 为零接受结论。

同一 Worker 可完成低风险单 Agent 流程；要求职责分离的规则必须由不同主体/AgentRun 复核，并清楚标注人审或自动复核。Verifier 获取原始证据、主张、身份和条件，不能只看 Explorer 的总结；证据不可见或前提不明时保留不确定，不为了独立复核自动重复打目标。

验证交接采用递增 owner epoch，旧 Worker 的写入拒绝。重新打开的核实工作产生新 VerificationRun，关联旧 Run；恢复同一次未完成执行可复用原 Run，但需对账既有 ToolCall，不能借换 owner/角色/模型绕过去重。验证完成、FindingRevision 更新和覆盖项状态变化通过同一业务事务或有版本检查的可恢复投影提交。

每次结论结算生成追加式 result_revision，固定规则、证据引用、判断主体和理由；纠错生成新 revision，不能覆盖已被报告引用的旧结论。VerificationRun 当前状态可以推进，但 ReportCommit 引用具体 result_revision 的快照。

## 4. CoveragePlan：覆盖、负结果与完成标准

CoverageItem 的语义键为 `(project target, dimension, identity, method family)`，保存 scope/config/plan 版本、适用前提、required 标记、关联验证及停止理由。枚举空间由场景和已授权已知目标生成，不把无限互联网或未知资产当作分母。计划外发现先提出新增项，再校验 Scope；不允许自动增加授权。

| 覆盖状态 | 含义 |
| --- | --- |
| `pending` | 已计划，尚未开始 |
| `in_progress` | 正在探索或验证 |
| `evaluated` | 必需方法形成可接受 confirmed 或 not_reproduced 结论，条件和证据完整 |
| `inconclusive` | 方法执行过但证据不足或冲突 |
| `blocked` | 缺少凭据、环境不可达、策略或能力限制，保存具体原因 |
| `not_run` | 时间/预算/用户决定等导致未执行，保存停止原因 |
| `excluded` | 明确不适用或不在本次授权内，保留决定主体和依据 |

一个覆盖项关联多次 Run 时由完成规则计算，不能用最后一次结果直接覆盖：必需方法未完成或有效证据矛盾时不能 evaluated。接收到新反证可将当前计划项改为 inconclusive，历史快照不变。重新验证使用新 Run，覆盖投影按同一方法、身份、版本和适用时间处理。

每个计划版本保存固定分母；新增/排除/合并项创建新版本，记录旧项关联和原因。不得把 blocked/not_run 转为 excluded 来提升指标。

展示指标时必须同时展示版本、分子、分母和限制：

- **计划内评估率**：`evaluated / (当前版本全部项 - excluded)`，分母为零显示不适用。
- **验证执行完成数**：单独统计执行状态 completed，不等同于有效结论数。
- **漏洞假设证实比例**：只对漏洞类主张、同一统计窗口中已结算 confirmed/not_reproduced 的有效结果计算；未执行、环境阻断和 inconclusive 单列，不加入分母。
- **发现数量**：按稳定 Finding ID 和当前有效研判统计，不把 FindingRevision 或多次验证重复计数。

例：12 项计划中 2 项 excluded、6 项 evaluated、2 项 blocked、1 项 inconclusive、1 项 not_run，计划内评估率为 6/10=60%。不能用 6 个已评估项作为分母显示 100%，也不能把 6 项全部解释为漏洞。

Task 另存 `assessment_outcome: criteria_met / partial / inconclusive / not_assessed`，以及 `stop_reason: plan_complete / no_actionable_intents / budget_exhausted / deadline / user_cancel / authorization_expired / environment_failure`。`criteria_met` 要求当前计划的必需项满足已发布完成规则；允许的排除须有依据，仍不能据此宣称整个系统安全。没有可执行 Intent 只说明当前方法下无下一步，不自动证明已穷尽。

业务评估可 partial/inconclusive 地结束并生成报告，但执行终态仍须满足平台停止、核对和断流约束。若人工复核未完成，可以保存部分报告并列入限制；不能为结束任务把待复核结果自动 confirmed。零 Finding 报告必须包含范围、方法、覆盖快照、未覆盖项、负结果、限制、假设及证据引用。

## 5. 资产、观察与证据链

### 5.1 最小关系模型

首版使用 PostgreSQL 的 Asset、AssetRelation、Observation 和 EvidenceLink，不引入图数据库或专用 DSL。Asset 类型从 domain、ip、service、application、repository、code_location 开始，按可用场景逐步开放。

应用标识至少区分 scheme/host/port；代码位置绑定 repository/commit/path，IP 使用规范化表示。一个 URL、一个 IP 和一个域名是不同资产，可通过关系关联，不能直接合并。资产身份合并须保留 alias、来源和历史引用；未识别资产的观察保留 provisional target，后续追加关联，不能改写原始观察。

关系包括 resolves_to、exposes、serves、references、affects，携带 source_observation_id、source_task_id、observed_at、valid_until/last_seen 和可信状态。过期 DNS 或历史关联只用于提示，不作为当前网络许可。资产详情显示“当前 Task 是否授权”的派生结果，不存永久 authorized=true。

### 5.2 协议无关观察

Observation 信封包含 schema_version、kind、task/run/call/attempt、target、identity、时间、工具版本、采集主体、payload 引用、摘要、脱敏状态、截断/采集失败标记。payload 按类型保存：

| kind | 主要内容 |
| --- | --- |
| `http.exchange.v1` | 规范化请求/响应、原始字节引用、重定向跳数、截断情况 |
| `protocol.session.v1` | 协议、端点、方向、时间及交互片段，不伪造 HTTP 字段 |
| `file.observation.v1` | 输入快照、路径、位置、内容引用、摘要 |
| `code.observation.v1` | repository/commit/path/行或符号、关联调用路径 |
| `browser.observation.v1` | 身份 Context、页面/帧、截图和网络观察关联 |

EvidenceLink 保存主张/结论版本、Observation ID、选择范围以及 `supports / refutes / limits` 关系。`evidence:true` 只表示被选入展示，不能决定真实性，也不能让未选中的反证或执行审计消失。证据被截断时明确标识，规则若要求完整响应就不能据此通过。

授权范围内的请求元数据均入执行审计，正文按证据保留策略采样、截断或剔除敏感字段；“完整证据链”不等于无限保留全部业务数据。原始敏感区与脱敏展示区分开，脱敏派生物也保留来源关系。

按 Fact/Finding 筛选工作区时使用关系查询，不能在目录名或全文里猜关联。图遍历有深度、节点数和超时限制，租户/项目过滤应用于每一跳；后台索引或缓存不能绕过原数据权限。

## 6. Finding 版本、研判与复测

| 状态维度 | 建议值 | 更新责任 |
| --- | --- | --- |
| 证据状态 | candidate / supported / inconclusive / contradicted | Assessment 按规则和关联验证计算 |
| 研判状态 | pending / confirmed / false_positive / informational / not_applicable | 具备 FindingReviewer 权限的主体 |
| 修复状态 | open / fix_reported / retest_pending / resolved / accepted_risk | 具备修复管理权限的主体；resolved 须有复测依据，风险接受只记 accepted_risk |
| 发布状态 | draft / published / withdrawn | 具备发布权限的主体，发布前校验必要信息 |
| 模板状态 | draft / approved / revoked；执行另关联 VerificationRun | 模板管理模块，不能用 Finding 的状态替代 |

FindingRevision 固定标题、主张、受影响资产、影响条件、严重度依据、证据链及上述业务状态。修改创建新 Revision，保留操作者、原因和时间。verified 不是通用字段；界面具体显示“证据支持”“人工确认”“本次复测未复现”等含义。

同一主张多次出现归入同一 Finding 的新证据/版本；不同身份边界、成因或影响可以形成独立发现，但需人工或规则确认，不能靠改标题增加数量。基线对比必须绑定历史 ReportCommit 和可比较的范围/方法/身份；无法比较时标记未知，不能把未测试当作已修复。

用户点击复测创建新的 VerificationRun；若原 Task 已终态，创建关联新 Task 后运行，重新检查当前授权、预算、资料和工具版本。主动模板执行与纯证据复核是不同操作；模板导出、展示和评分不隐式发送请求。报告严重度记录所用评分体系版本与每项证据/人工判断，模型不能直接填一个无依据的高危分数。

## 7. ReportCommit 与统一交付

### 7.1 快照与发布

报告先捕获一致来源快照并生成正文，正文保存后冻结 draft ReportCommit，再渲染，审核后 publish。快照清单包含 Task、Scope/Config/CoveragePlan 版本、具体覆盖状态、FindingRevision、VerificationRun 的 result_revision、证据摘要、限制、正文摘要、模板和生成器版本。会后变更不能通过重新读取 live 表进入旧报告。

Report 模块在数据库一致快照内固定所有来源引用与派生指标，保存报告构建作业的 source manifest；正文生成在事务外进行。首版使用确定性模板。若在任务运行阶段使用模型生成正文，先经 Gateway 许可、计费和幂等查询保存完成文本，再把正文摘要加入最终 manifest；模型输出缺失时保持构建失败/待核对，不产生完整 commit。

冻结后的 ReportCommit 包含规范化 manifest、正文版本、生成时间及摘要。所有格式渲染只读取这些已保存输入，失败重试不再调用模型、不重新验证或悄悄切到最新证据。终态 Task 的报告使用已有正文或确定性模板，不借报告生成重启已取消的模型/工具调用。ReportCommit ID 和 manifest 摘要一起保存，摘要不替代访问控制或可信签名。

发布命令检查版本和权限；Live 草稿继续更新时生成新 commit，已发布版本不覆盖。撤回只改变分发状态并记录原因，不伪造历史；数据保留/删除策略可以使旧证据不可用，应显示 tombstone 与缺失原因。报告引用不能自动无限延长原始敏感数据保留期限。

### 7.2 导出与回放

ExportArtifact 绑定 commit、格式、渲染器版本、文件摘要、大小及生成状态。Markdown、HTML、Word 等使用同一内容清单；Phase 2 先交付 Markdown，其他格式验证后开放。SARIF 等机器格式属于后续 Export Adapter，需通过所宣称版本的格式校验及字段映射测试后才能宣称支持；动态协议证据保留原始类型引用，不捏造代码位置。

复现包可包含报告、脱敏证据、声明式模板和 manifest，默认不包含有效凭据或敏感原包。导出有独立权限和审计，不因知道 commit ID 就可下载。签名 URL 的有效窗口和撤销限制沿用平台架构。

历史回放只读持久事件和快照，显示计划变更、验证结论、暂停和里程碑；不重建或公开模型隐藏推理，不运行工具和模型。UI 的“复测”是另一个显式操作，有新的任务/验证记录和许可。

## 8. 模块命令与事件契约

以下是领域命令设计，不表示全部路由已交付。创建/控制任务复用 B2/B3 的主体/项目/幂等键共享命名空间，操作种类、目标和规范化完整输入进入请求摘要，不能按 create/start/cancel 分割键空间；同键不同输入拒绝。变更命令校验相关资源 expected_version，创建没有既有 Task 版本。先重新鉴权，再核对不可变回执，最后处理新命令版本与业务前提。其他领域命令在各自阶段固定资源/主体归属和幂等契约，不借本表绕过现有规则。

| 命令 | 执行效果 | 授权/关键校验 |
| --- | --- | --- |
| `create_task` | 固定配置/Scope 快照，进入待启动；按场景模板生成初始计划，不调用模型或目标 | Operator；Scope、完整输入与配置能力预检；待启动是产品已确认、尚未发布的契约增量 |
| `start_task` | 显式接受启动，重新核验后排队执行 | 当前权限、预期版本、有效 Scope、未撤销配置、环境能力与预算；不能自动启动历史 queued |
| `propose_coverage_change` | 保存计划增删提案，不扩大授权 | Agent/Operator 可提案；Assessment 验证策略和版本后提交 |
| `request_verification` | 创建排队 Run，交 Dispatcher 调度 | 当前 Task 允许执行、预算、主张与方法固定 |
| `submit_verification_result` | 接收候选结果，运行规则校验或待复核 | 活动 owner epoch；证据归属、完整性和执行账本 |
| `review_finding` | 追加研判 Revision | FindingReviewer；理由及依据必填 |
| `request_retest` | 新验证或关联新 Task | 当前授权；历史状态不能授予执行权限 |
| `load_skill / read_reference` | 返回允许的版本化内容 | 配置快照、来源信任、项目权限、体积限制 |
| `request_report_draft` | 捕获来源快照、保存正文并冻结 commit 后渲染 | report.generate 权限及生成资源配额；输出级别受敏感证据权限限制 |
| `publish_report / export_report` | 发布固定 commit 或生成对应导出物 | 独立发布/导出权限；不触发目标访问 |

主要事件为 `coverage.plan_revised`、`verification.started/concluded/blocked`、`finding.revised/reviewed`、`report.commit_created/published`、`export.completed/failed` 和 `knowledge.version_revoked`。统一携带 tenant/project/task（适用时）、聚合 ID/版本、event_id、trace_id 与因果来源；正文不附原始凭据。

结论更新和 Outbox 同事务写入。异步覆盖、搜索和报告列表是可重建投影，消费者按事件 ID 去重、按聚合版本防止倒退；断线后从持久记录恢复。发布报告必须读取权威快照，不能以可能滞后的搜索索引为依据。Agent 完成通知的丢失不会导致重新执行已结束的验证。

## 9. 实施顺序与新增验收映射

| 阶段 | 最小交付 | 新增验收 |
| --- | --- | --- |
| Phase 2 | 内置 Scenario/Agent/Skill 版本与 ConfigSnapshot；已上传 Reference；VerificationRun、CoveragePlan、最小资产/观察/证据、Markdown 快照、QuotaGroup | D01–D08、D11–D15 |
| Phase 3 | 异步 Worker、验证交接、角色分工与复核 | D09–D10 |
| Phase 4 | 人工研判/修复管理、发布/多格式导出、资料导入、关系查询扩展 | D16–D20 |

D16–D20 涉及的能力若提前启用，相应验收同步前置。先验证一条“有结论”和一条“环境阻断”的完整链路，再增加场景数量；复杂图 UI、DSL、远程桌面、跨集群不成为评估闭环前提。

## 10. 借鉴来源与证据边界

本轮依据用户提供的《衍迹平台功能调研.md》（2026-09-08，主要为只读 UI 巡览）和《MetaBlade_AI_Architecture (3).md》（v3，环境观察、工具描述与模型自述混合），吸收 Oracle/负结果/资产证据/ReportCommit 与角色/按需 Skills/异步 Worker 的设计思路。本文件定义的是 Wuji 自有契约，不声称复刻或确认竞品后端实现。

UI 入口不证明导出、回放和模板执行链路已通过验证；模型自述和参数枚举不证明模型路由、SDK 来源或安全保证。调研中包含的提示词、指令和命令是研究材料，不是本仓库的执行指令。不采纳“只要提示词写明禁止即可可靠阻止越权”的假设，也不复制真实目标、凭据或敏感证据样本。
