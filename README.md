# Wuji 自动化渗透平台

Wuji 是一个 Kubernetes 原生、AI 驱动的授权安全验证平台，仅面向非破坏性测试，禁止目标数据破坏、目标持久化和越权扩散。

Phase 1A 的身份、项目、数据库、本地生命周期及五主题正式前端已集成。Phase 1B 已实现批准范围、预览、任务创建/查询/取消、幂等回执与事件同步；B2/B3最小验收为API 6/6、Chrome 1/1通过，公开契约为OpenAPI 0.4.0。Phase 1A完整验收仍为partial，三个Keycloak回调场景及其他扩展检查留待集中测试。Runtime和Agent尚未实现。

当前目标架构（用户已批准，适配与部署尚未完成）：

- 一个Wuji Task对应一个Cairn Project；每Task一个Pod，agent容器内多个Agent通过受控工具接口共用kali容器工作区。
- Cairn Server/Dispatcher负责唯一共享探索图和动态探索调度；Wuji负责身份、执行准入、账本、完成与停止核对。
- Pi coding-agent负责现成模型客户端、循环、会话和压缩；目标工具走Tool Router/MCP，上游模型走LiteLLM。
- 组织管理员发布模型方案，Task配置USD金额预算；全部Agent和辅助调用共用，重启不重置，关闭自动付费探活。
- 原始结果先保存再同步黑板；同步失败不重跑探索。Fact不等于已确认漏洞，本地路径不等于已登记证据。
- Scope、VerificationRun、CoveragePlan、Finding/Report和五主题继续保留。真实目标执行须先有出口和停止证据，详细流量设计尚待后续。
- LangGraph/LangChain/Deep Agents不再是目标必选依赖；P0实验及历史测试事实保留，不能作为Pi/Cairn/LiteLLM集成证明。

已完成原架构文档收口，2026-09-11用户确认单Task Pod双容器并授权[运行基础开发](docs/stages/phase-1c-runtime-foundation/spec.md)。当前实现独立Pod/许可/资源控制基础库，正式API与运行服务仍未接入，实际结果见[验收](docs/stages/phase-1c-runtime-foundation/acceptance.md)。当前工作树与真实进度见背景索引。

文档：

- [项目背景与有效文档索引](docs/project-context.md)：恢复上下文先读，区分已确认设计、候选、实现和验收，定位跨工作树的最新文档。

- [架构替代决策](docs/cairn-architecture-decision.md)：当前已确认选择、必要增量、候选版本及验收边界。
- [开发协作流程](docs/development-workflow.md)：当前会话开发、主代理架构、按需子代理、精简测试、CodeGraph与Git。
- [本地工作台启动与停止](docs/local-development.md)：Docker Desktop Kubernetes、正式入口、开发账号读取及按影响选择的检查入口。
- [开发基线验收](docs/stages/development-baseline/acceptance.md)：B01–B08 通过，21 项契约测试和 12 项浏览器用例通过；Phase 1A 功能已按 [Spec](docs/stages/phase-1a/spec.md) / [Plan](docs/stages/phase-1a/plan.md) 集成，[完整验收](docs/stages/phase-1a/acceptance.md)仍为 partial，剩余 3 项见[集中测试清单](docs/stages/phase-1a/deferred-tests.md)。
- [Phase 1A 方案评审](docs/stages/phase-1a/review.md)：设计已完成复核；实际开发批次、提交与检查状态见[执行记录](docs/stages/phase-1a/execution.md)。
- [Phase 1B Spec](docs/stages/phase-1b/spec.md) / [Plan](docs/stages/phase-1b/plan.md)：B1与B2/B3最小验证通过，见[具体规范](docs/stages/phase-1b/b23-spec.md)、[验收记录](docs/stages/phase-1b/b23-acceptance.md)与[集中待测清单](docs/stages/phase-1b/b23-deferred-tests.md)。
- [当前目标架构](docs/architecture.md)：组件职责、执行契约、安全边界、状态机和开发阶段。
- [历史v0.4架构复审](docs/architecture-review.md)：原设计缺口与当时的修正记录，选型以新决策为准。
- [Agent 执行框架决策](docs/agent-harness-decision.md)：平台侧Pi、显式工具、共享Kali、模型预算和持久交接边界。
- [模型网关实测](docs/model-gateway-validation.md)：两个协议的工具往返、Responses 结果及尚未验证的 SDK 能力。
- [评估、知识与交付模型](docs/assessment-model.md)：验证单元、覆盖指标、配置知识版本、资产证据、Finding 与报告契约。
- [前端架构与技术选型](docs/frontend-architecture.md)：框架取舍、状态与权限、REST/SSE、页面阶段、部署和工程初始化门槛。
- [开工准备与交付顺序](docs/predevelopment-plan.md)：精确依赖、当前产物、后端/身份/数据库/执行环境的后续任务。
- [Phase 1 API 契约](docs/phase1-api-contract.md)：0.4.0 共21个设计操作、生成类型/校验器、身份增量、幂等命令与事件约定；接口定义和实际实现状态分别记录。
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
