# Wuji 开工准备与交付顺序

- **日期**：2026-09-09
- **阶段**：Phase 1实施中；本文保留开工依赖，实际结果以阶段验收记录为准
- **原则**：每项有产物、依赖和通过证据；架构描述、原型演示、集成验收分开记录

## 1. 首个可开发切片

以一个测试租户、一个项目、已批准 HTTP Scope 和一个受控 HTTP 观察任务为首个纵向切片：选择范围 → 服务端预览 → 幂等创建 → Runtime 就绪 → 一次非破坏性观察 → 证据保存 → 取消/完成 → 出口停止与清理。

先在自建 HTTP/DNS 夹具上跑通；模型、多 Agent、浏览器、资料导入和复杂配置中心随后接入。所有阶段保持主架构的授权、限额和隔离要求。

## 2. 本轮交付和状态

| 产物 | 位置 | 状态与实际边界 |
| --- | --- | --- |
| 前端精确依赖及工具链 | package.json、pnpm-lock.yaml、.node-version | 已固定，兼容性验证见第 3 节；不是生产容量验证 |
| 21 个设计 API 操作及业务 Schema | packages/contracts/openapi.yaml | 身份/项目/范围/预览/任务命令/事件已实现，证据仍为设计；设计操作不等于全部已注册 |
| 正反例夹具与契约检查 | packages/contracts/fixtures、tests/contracts.test.mjs | 校验字段、条件状态和契约声明；不能验证后端实际执法 |
| 四页流程原型 | spikes/frontend | 使用本地内存夹具，按路由拆包；不接平台或测试目标 |
| 最小 CI | .github/workflows/phase0.yml | 定义冻结安装、契约/类型/构建和浏览器检查；尚未在远端 CI 执行 |
| 页面交互与主题 | docs/phase1-wireframes.md、DESIGN.md | 五主题、范围预览及真实任务页面已实现；完整配置页面按后续阶段交付 |
| Agent 执行框架决策 | [Harness 职责与选型](agent-harness-decision.md) | 补齐 LangGraph 与 Harness 分工；优先验证 Deep Agents，具体依赖尚未安装或集成 |
| 模型网关基础验证 | [实际测试记录](model-gateway-validation.md) | 两个协议的模拟工具往返及 Responses 短文本通过；不代表完整 SDK 兼容或生产计量验收 |
| 架构复审 v0.4 | [问题与修正](architecture-review.md) | 修正框架复用、上下文、辅助计费、恢复与事件边界；新增 H01–H10，均待集成验证 |
| 分阶段协作与 Git 基线 | [协作流程](development-workflow.md)、[基线验收](stages/development-baseline/acceptance.md) | B01–B08已通过；SOL/xhigh开发，后续Luna/xhigh测试，全体共享10分钟最小验证预算 |
| Phase 1A | [验收](stages/phase-1a/acceptance.md) | 正式工程/身份/项目/数据库已实现；3个真实回调场景延期，完整验收partial |
| Phase 1B | [B1验收](stages/phase-1b/acceptance.md)、[B2/B3验收](stages/phase-1b/b23-acceptance.md) | B1、B2/B3最小验收通过，扩展验证待集中执行；Runtime及Agent尚未接入 |

上述完成项不代表整个 Phase 0 完成，也不代表 80 个架构验收场景已通过。验证结果和未覆盖项记录在 [Phase 0 验证记录](phase0-validation.md)。

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

精确元数据以 npm registry 和锁文件为依据，开启严格 peer dependency 检查；所列不是“全部最新版”承诺。Node 24 的发布维护状态见 [Node 发布计划](https://nodejs.org/en/about/previous-releases)，类型生成器的 peer 要求见 [openapi-typescript 7.13.0 元数据](https://registry.npmjs.org/openapi-typescript/7.13.0)。直接依赖的登记许可证为 MIT、Apache-2.0、ISC 或 OFL-1.1；完整传递依赖清单、漏洞审计及组织许可要求需在生产依赖冻结前完成。

以后升级依赖必须同时检查 peer、类型生成差异、构建和浏览器测试，不通过简单修改“最新版本”说明完成升级。

## 4. 后续开工任务

责任列表示承担该任务的职能，不代表已向某个人指派或发送任务。

| 编号 | 任务 / 责任 | 必须产物与通过条件 | 依赖 / 状态 |
| --- | --- | --- | --- |
| P0-01 | 第一切片契约 / 前后端 | 完成当前 API 基线的实现评审，补充正式身份端点、错误和容量配置策略 | 身份/项目/范围及B2/B3任务事件已有实现和最小验证证据 |
| P0-02 | 后端语言与框架 / 后端 | 记录 API、Router、Controller、Orchestrator 的语言/SDK 组合及职责；区分 LangGraph 与 Agent Harness，明确默认执行层候选及适配边界 | Python/FastAPI已实现并验证，Harness仍按P0-10验证 |
| P0-03 | 身份接入 / 后端与部署 | 选定首个提供方，完成会话、CSRF、登录回跳、退出、过期/撤销验证 | Keycloak OIDC + Authlib已实现，主流程通过，3个真实回调专项延期 |
| P0-04 | 数据库初始迁移 / 后端 | Tenant/Project/Membership、授权策略、Task/命令/ToolCall、Artifact、Audit/Outbox 的约束和迁移 | 依赖 P0-01/02；测试跨租户关联、连接池上下文与唯一约束 |
| P0-05 | 出口与 CNI 小验证 / 基础设施 | 选定实现组合；实测 DNS/IPv6/重定向、直连阻断、限速、撤销窗口 | Phase 1 执行开放前必须完成 |
| P0-06 | Runtime 生命周期小验证 / 后端与基础设施 | 受限镜像启动、租约过期断流、取消与孤儿资源回收；双副本/失联时最多一个有效 attempt | 依赖 P0-05；记录实测停止窗口 |
| P0-07 | 幂等命令与事件小验证 / 后端 | 请求丢失、并发创建/取消、事务乱序、Outbox 补发和一致游标的数据库集成测试 | 依赖 P0-04；不能以当前 Schema 测试替代 |
| P0-08 | 开发/测试环境 / 全栈与基础设施 | 自建 HTTP/DNS 夹具、数据库/存储启动、测试身份、初始化和重置脚本；CI 可复现 | Docker Desktop Kubernetes上PostgreSQL/Keycloak及PVC已部署；本地生命周期已验证，任务出口隔离与远端CI未验收 |
| P0-09 | 正式前端基础层 / 前端 | 会话、权限、运行时响应校验、命令客户端、缓存代次隔离、加载/错误状态、服务端分页 | 复用已验证依赖和线框，不能直接把原型 Mock 发布上线 |
| P0-10 | SSE/模型工作流预验证 / 后端与前端 | 快照交接/补发/撤权；一个默认 Harness 实际压缩与回查证据、辅助调用计费、打断/恢复与账本去重、受控工具与模型协议；覆盖 H01–H10 | 基础协议已实测；候选小验证可在框架冻结前开展，不阻塞 Phase 1 无模型切片；完整集成在 Phase 2 开放前完成 |

## 5. 实施顺序

正式FastAPI后端和`apps/web`已交付身份、项目、范围预览、任务管理及事件同步；下一阶段先规划Phase 1C受控执行。当前Docker Desktop数据库/身份部署不代表已具备任务Runtime或出口隔离。

先完成 P0-01 至 P0-04，使身份、字段、事务和数据库约束可执行；同时开展 P0-05/P0-06 的隔离环境验证。P0-07/P0-08 为恢复和集成测试提供基础，P0-09 根据真实接口接入页面。

### 5.1 接下来按可运行结果交付

| 批次 | 实现内容 | 可审查结果 | 依赖 |
| --- | --- | --- | --- |
| A：正式工程与平台基础 | 确定后端语言/框架、首个身份提供方及本地/集群开发方式；建立 API、数据库迁移、开发启动和正式 `apps/web`；迁入已确认主题和布局 | 可启动的前后端与数据库；迁移可重复执行；真实会话和项目查询；五套主题可切换。此时执行入口尚未开放 | P0-01/02/03/04/08/09 |
| B：真实任务管理 | 项目权限、Scope读取与预览、幂等创建/取消、任务查询、命令回执和事务事件/Outbox；工具调用账本留C | 浏览器创建的任务持久保存在数据库；刷新可查询；重复提交、版本冲突和无权限有实际集成检查 | A、P0-07 |
| C：受控执行与证据 | 接入 Controller、Runtime、Router、HTTP Adapter、受控出口、限额、证据存储和资源回收 | 在自建测试服务完成观察并查看证据；取消必须等待实际停止确认；失联断流、范围拒绝和清理均有执行证据 | B；P0-05/06 验证通过后开放执行 |
| D：Phase 1 联调验收 | 将正式任务/证据页面与真实接口联调；验证权限撤销、结果不明、取消中与清理等待；提供最小部署与复现说明 | 完成首个纵向切片及其适用验收项；明确剩余缺口后进入单 Agent 阶段 | C |

第一批明确产物是正式工程、身份/项目和数据库 API 基础。执行隔离验证可以与 A/B 同期开展。单 Agent、模型网关、多 Agent、浏览器 Adapter、知识配置中心和复杂图谱按既定后续阶段接入。

Phase 1 只有在服务端鉴权、受控出口、限额、取消和清理有实际证据后才开放测试执行。Phase 2 再完成 P0-10 和单 Agent 评估；页面、后台模块和验收用例按同一阶段发布。

## 6. 本地检查入口

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
pnpm dev
```

修改 API 后先执行 `pnpm contracts:generate`，并保留生成物与源文件的一致变化。CI 文件是 GitHub Actions 的实现模板；若最终采用其他 CI，复用相同脚本和锁文件，不改变验收口径。当前没有部署、发布或远端提交动作。

本机已有 Chrome 时，可用 `WUJI_BROWSER_CHANNEL=chrome pnpm test:e2e` 进行本地验证；记录实际浏览器版本。CI 继续使用安装的 Playwright 配套 Chromium，本地 Chrome 结果不能代替 CI 环境结果。
