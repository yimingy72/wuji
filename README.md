# Wuji 自动化渗透平台

Wuji 是一个 Kubernetes 原生、AI 驱动的授权安全验证平台，仅面向非破坏性测试，禁止目标数据破坏、目标持久化和越权扩散。

Phase 1A 的身份、项目、数据库、本地生命周期及五主题正式前端已集成。Phase 1B / B1 已实现批准范围与任务预览，最小功能验证通过，公开契约升级为 OpenAPI 0.3.0。完整验收当前为 partial：最近一次独立检查中 API 73/73、生命周期 6/6、Chrome 12/15 通过，3 个真实 Keycloak 回调场景留待集中测试。Runtime 和 Agent 尚未实现。

v0.4 架构基线：

- Agent 在 Platform 编排，一个 Task 同时最多有一个获准执行的 Runtime attempt；首版 HTTP 使用最小镜像，Kali 工具按 Profile 接入。
- ScopePolicy 在 MCP Router、Runtime 和独立网络出口执行，目标内容和 Agent 无权扩大范围。
- 首版使用结构化 HTTP 观察工具；浏览器和网络探测按 Adapter 验收后接入。
- LangGraph 负责工作流，Blackboard 共享证据与事实，Dispatcher 管理有限权限和预算的 Worker。
- Agent Harness 复用上下文控制、压缩、模型/工具循环和打断，经薄 AgentDriver 接入；优先验证 Deep Agents，尚未集成。
- VerificationRun 独立记录验证主张、条件和结论；CoveragePlan 区分已评估、未复现、阻断与未执行。
- 场景、角色、知识包和资料按版本绑定到任务配置快照，加载知识不会扩大授权。
- 资产关系与协议无关证据支持完整追溯；Finding 分维度管理状态，ReportCommit 固定交付版本。
- PostgreSQL 保存任务权威状态、执行账本、检查点和事务 Outbox，明确结果不明、恢复与回放语义。
- Model Gateway 统一数据策略、模型路由、重试和预算；外部内容与可信系统指令分开。
- QuotaGroup 统一共享上游配额，多个模型别名和 fallback 不重复领取容量。
- Runtime 通过租约、出口断流和进程管理实现停止；浏览器身份、工作目录及凭据按 Worker/调用限定。
- 前端采用 React + TypeScript + Vite + Ant Design，统一路由、查询缓存、同源会话和任务事件恢复。
- 先交付租户权限、受控工具、执行限额、取消和清理闭环，再接入单 Agent 与多 Agent。

文档：

- [开发协作流程](docs/development-workflow.md)：主代理规划/验收、SOL 子代理开发、Luna 集中测试、CodeGraph 与 Git 分工。
- [本地工作台启动与停止](docs/local-development.md)：Docker Desktop Kubernetes、正式入口、开发账号读取及按影响选择的检查入口。
- [开发基线验收](docs/stages/development-baseline/acceptance.md)：B01–B08 通过，21 项契约测试和 12 项浏览器用例通过；Phase 1A 功能已按 [Spec](docs/stages/phase-1a/spec.md) / [Plan](docs/stages/phase-1a/plan.md) 集成，[完整验收](docs/stages/phase-1a/acceptance.md)仍为 partial，剩余 3 项见[集中测试清单](docs/stages/phase-1a/deferred-tests.md)。
- [Phase 1A 方案评审](docs/stages/phase-1a/review.md)：设计已完成复核；实际开发批次、提交与检查状态见[执行记录](docs/stages/phase-1a/execution.md)。
- [Phase 1B Spec](docs/stages/phase-1b/spec.md) / [Plan](docs/stages/phase-1b/plan.md)：B1 批准范围与任务预览已获准实施；B2/B3 的真实任务、命令和事件尚未进入开发。
- [架构设计 v0.4](docs/architecture.md)：组件职责、执行契约、安全边界、状态机和开发阶段。
- [整体架构复审](docs/architecture-review.md)：十项设计缺口、已修正边界、框架复用清单与剩余验证。
- [Agent 执行框架决策](docs/agent-harness-decision.md)：LangGraph、Deep Agents、pi、Claude/Codex SDK 与 DeepSeek Harness 的分工和接入顺序。
- [模型网关实测](docs/model-gateway-validation.md)：两个协议的工具往返、Responses 结果及尚未验证的 SDK 能力。
- [评估、知识与交付模型](docs/assessment-model.md)：验证单元、覆盖指标、配置知识版本、资产证据、Finding 与报告契约。
- [前端架构与技术选型](docs/frontend-architecture.md)：框架取舍、状态与权限、REST/SSE、页面阶段、部署和工程初始化门槛。
- [开工准备与交付顺序](docs/predevelopment-plan.md)：精确依赖、当前产物、后端/身份/数据库/执行环境的后续任务。
- [Phase 1 API 契约](docs/phase1-api-contract.md)：0.3.0 共21个设计操作、生成类型/校验器、身份增量、幂等命令与事件约定；接口定义和实际实现状态分别记录。
- [页面线框与交互](docs/phase1-wireframes.md)：三栏工作台、创建与证据详情、异常场景和接口映射。
- [工作台视觉基线](DESIGN.md)：五套明暗配色、紧凑组件、字体、响应布局与页面文案规则。
- [Phase 0 验证记录](docs/phase0-validation.md)：本地测试、截图、构建及未覆盖项。
- [架构验收清单](docs/architecture-acceptance.md)：80 个阶段验收场景，包含新增上下文/打断/恢复与模型适配检查；当前均未完成整体验收。

本地原型：

```sh
pnpm install --frozen-lockfile
pnpm dev
```

访问 `http://127.0.0.1:4173`。原型只使用内存示例数据，不连接平台或测试目标。`pnpm check` 校验契约、夹具及类型，`pnpm build` 构建原型；浏览器检查方式见开工准备文档。
