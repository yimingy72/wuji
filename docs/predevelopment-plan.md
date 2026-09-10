# Wuji 后续开发依赖与交付顺序

- 日期：2026-09-10；状态：目标开发依赖已确认，具体业务Spec/Plan尚未批准。
- 当前入口：[背景索引](project-context.md)、[架构替代决策](cairn-architecture-decision.md)、[本批文档Spec](stages/cairn-architecture-baseline/spec.md)。
- 本页替代6ee84b5中的旧HTTP优先/后置模型网关开发顺序；原Phase1A/B及P0验收保留，不能据此将后续能力标为完成。

## 1. 当前实际基线

| 对象 | 状态 |
| --- | --- |
| 主业务381ae3a | 正式FastAPI/前端/身份/项目/范围预览/任务创建查询取消/幂等回执/事件，API0.4.0 |
| Phase1A | 完整验收partial，三个真实回调场景仍延期 |
| B1/B2/B3 | 最小验证有效；现有Task只有queued/cancelled，执行调用数恒零 |
| P0 a84716c | 原受限Deep Agents/原生客户端工具往返及取消等待实验通过；不是Pi/Cairn/LiteLLM证据 |
| 新架构 | Cairn Server/Dispatcher、平台侧Pi、多Agent共享一个Kali、LiteLLM Task金额预算已确认，尚未集成 |
| 本批 | 只更新架构、规则、索引和旧草案适用状态；不改业务/契约/依赖/迁移/运行记录 |

## 2. 后续按依赖实施

| 批次 | 必须交付 | 前置和边界 |
| --- | --- | --- |
| 控制面基础 | 0.5契约、必要配置快照、ready/start、执行代次、AgentRun/工具账本、Task-Cairn绑定 | 先冻结Spec/Plan和迁移；组织模型配置/Task金额预算的必要后端不能后置到真实调度之后；旧queued不自动执行 |
| 调度适配 | Wuji派发准入、平台Worker后端、Pi受限工具、持久结果及黑板幂等回写 | 先合成工具夹具；Cairn active/stopped不代替许可，同步失败不重跑探索 |
| 共享Runtime | 多Agent对接一个Kali、产物登记、命令句柄、取消与停止核对 | Worker后端不管理Kali；一个有效attempt；Agent与Kali分离 |
| 产品接入 | 原型评审后接正式创建与执行观察页面 | 复用上述契约、现有会话/权限/命令恢复及五主题；没有模型只能存草稿 |
| 真实目标开放 | 启用已验证工具与场景 | 先有受控出口、授权与停止证据；详细流量方案仍待独立设计 |
| 后续业务完善 | 覆盖/验证/资产/报告、资料导入、图查询和更多场景 | 按对应领域Spec逐批开放，不再建一套探索调度器 |

任务创建、范围确认、模型配置等产品交互仍需先评审原型，再接正式前后端；隔离的调度适配可先用夹具，不能绕过交互确认发布新创建流程。

每批计划必须固定具体接口、迁移、变更范围、错误/恢复行为及最小验证入口。旧phase-1c-prep草案superseded，不能直接派发实施。本次不清理或删除P0包，不升级框架依赖。

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

## 4. 下一份控制面Spec必须落实

- 组织TenantAdmin模型配置与同版本显式连接检查，LiteLLM原生管理边界；禁止隐式付费探活。
- 独立草稿、创建者范围确认、版本化ConfigSnapshot、Task USD金额预算和无模型行为；不从P0复制测试限额作为产品默认。
- 0.5 DTO、生成校验器、数据库约束及迁移；Task/回执/事件兼容，历史queued不自动执行。
- Task-Cairn映射、停止态幂等创建、原操作回执、每次派发真实AgentRun身份与执行代次。
- 原始结果先保存再同步；原生Fact ID、结果待同步和只读投影；跨库不假定原子事务。
- 完成提案、资源所有权、未知执行与未知结果区分；明确本批实际开放的命令，不能只有202入口而无消费者。

## 5. Git、验证与交付

继续使用当前会话和已有phase-1c-prep工作树，架构由主代理独立设计；可选子代理按根AGENTS的最新gpt-6-astra/low设置执行明确任务，不强制独立worktree或独立测试者。

文档提交不移动主业务HEAD或master，不修改私有运行文件绕过SHA检查。业务交付时才按[本地启动流程](local-development.md)切换服务、增量迁移/seed并保留数据；代码集成后再同步CodeGraph。

本批只检查diff、相对链接与文档一致性，不运行安装、构建、浏览器或Kubernetes检查。业务检查预算仍已用426/600秒、剩174秒，真实4次模型额度已耗尽，不因上述拆批重置。预算不足如实待测，不把代码或文档交付冒充完整验收。

后续最小场景仅为未启动不派发、两个独立AgentRun共用一个Runtime、结果重投不重跑、工具越权拒绝、取消与迟到派发、旧queued不执行。长上下文、长时间断线、压力和完整协议矩阵保留到明确安排的集中验证；通过即停止。
