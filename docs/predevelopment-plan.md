# Wuji 实现进度与后续交付

更新：2026-09-11。当前业务来源为W1记录提交40472c6，文档与GitHub入口为codex/github-upload。以下区分已交付机制与待授权/待验证能力，不将路线图作为新业务开发指令。

## 1. 当前实际基线

| 范围 | 当前结论 | 依据 |
| --- | --- | --- |
| 平台基础 | 身份/项目/五主题与任务管理已集成；Phase1A完整验收partial | [Phase1A](stages/phase-1a/acceptance.md) |
| 模型与创建 | 管理员模型配置、同版本检查/发布、五场景草稿、Web正式创建、快照与ready/start已交付 | [核心验收](stages/phase-1c-task-creation/acceptance.md) |
| 执行核心 | Cairn/Pi/LiteLLM、单Task双容器、多个AgentRun、账本、证据和停止核对通过封闭夹具验收 | [核心验收](stages/phase-1c-task-creation/acceptance.md) |
| W1评估 | 有限HTTP、验证/覆盖、双Artifact、Reason补证反馈与Pi原生压缩机制通过 | [W1验收](stages/phase-2-web-assessment/acceptance.md) |
| API与数据库 | OpenAPI 0.5.0，迁移头0008；旧Scope/queued保留历史语义 | [API说明](phase1-api-contract.md) |
| 运行边界 | 自建站点、合成上游；真实模型自主效果、外部目标和生产出口未验收 | [背景索引](project-context.md) |

## 2. 后续方向与前置条件

| 方向 | 前置条件 / 范围 |
| --- | --- |
| W1真实模型效果 | 明确已发布模型版本、公司单价与新增USD授权；机制通过不能代替效果层 |
| 生产出口与外部目标 | 独立Spec/Plan，验证授权、DNS/重定向、撤销和停止边界后逐项开放工具 |
| 关系画布 | 评审React Flow与当前数据关系；现有真实黑板/时间线/工作区继续保留 |
| 完整评估交付 | 通用Goal映射、Finding/报告/资料和更多场景分别冻结契约；不重建探索调度器 |
| 既有延期 | [Phase1A待测](stages/phase-1a/deferred-tests.md)及W1验收限制按需集中安排，不因文档更新全量重测 |

D1/D2/D3-B、执行账本与Cairn/Pi接入不再列为未开工任务。原架构草案与P0保留历史，不能覆盖后续accepted记录。后续新阶段仍先在应用Plan模式完成具体规划；草案不自动授权实施。

## 3. 依赖基线及选择依据

| 依赖 | 固定版本 | 选择说明 |
| --- | --- | --- |
| Node / pnpm | 24.20.0 / 10.32.1 | 使用 Node 24 工具链；pnpm workspace 同时固定执行版本 |
| React / React DOM | 19.2.8 / 19.2.8 | 对齐 React DOM 的 peer dependency |
| Ant Design / icons | 6.6.3 / 6.3.4 | 与 React 19 同组构建验证 |
| Inter Variable / IBM Plex Mono 字体包 | 5.3.0 / 5.3.0 | 本地打包拉丁字形；中文沿用系统字体，OFL-1.1 |
| TypeScript | 5.9.3 | openapi-typescript 7.13.0 声明 TypeScript 5 peer 约束；本轮未采用 TypeScript 7 |
| Vite / React plugin | 8.2.2 / 6.1.1 | 插件和 Vite 主版本对齐 |
| React Router DOM | 7.18.3 | Data Mode，页面懒加载 |
| TanStack Query | 5.102.8 | 查询缓存与路由 loader 共用同一定义 |
| openapi-typescript / Redocly CLI | 7.13.0 / 2.51.2 | 生成和校验 OpenAPI 3.1 契约 |
| Ajv / ajv-formats / YAML | 8.20.0 / 3.0.1 / 2.9.0 | JSON Schema 2020 校验、格式和文档解析 |
| Vitest / Playwright | 5.0.0 / 1.63.0 | 本地契约与浏览器验证 |

精确元数据以 npm registry 和锁文件为依据，开启严格 peer dependency 检查；所列不是“全部最新版”承诺。Node 24 的发布维护状态见 [Node 发布计划](https://nodejs.org/en/about/previous-releases)，类型生成器的 peer 要求见 [openapi-typescript 7.13.0 元数据](https://registry.npmjs.org/openapi-typescript/7.13.0)。上述前端依赖的登记许可证为 MIT、Apache-2.0、ISC 或 OFL-1.1；Cairn另保留AGPL-3.0及上游来源，见[架构决策](cairn-architecture-decision.md)；完整传递依赖清单、漏洞审计及组织许可要求需在生产依赖冻结前完成。

以后升级依赖必须同时检查 peer、类型生成差异、构建和浏览器测试，不通过简单修改“最新版本”说明完成升级。

## 4. 开发与交付约束

沿用[AGENTS](../AGENTS.md)及[协作流程](development-workflow.md)：当前会话连续开发，主代理负责架构，按需使用指定子代理。按影响选择最小检查，不设置累计检查时间预算；通过即停，未覆盖如实记录。

已有运行工作树和master保持其历史SHA。新运行按[本地工作台](local-development.md)正常生成run-file，不手改记录绕过版本核验。GitHub当前版本见[仓库交接](repository-handoff.md)；后续推送仍依用户授权，不因已配置远端自动发布每次工作。

本次仅文档同步，不修改锁文件、依赖、代码或验收SHA，不运行模型或目标请求；真实模型的历史已用额度不能因整理文档重置。
