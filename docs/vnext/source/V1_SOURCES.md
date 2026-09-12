# 依据与核查边界

核查日期：2026-09-12。本文档包只交付审查、设计与实施计划；没有修改远端仓库、启动 Wuji/MAF、调用收费模型、执行目标工具或运行产品测试。

## 证据等级

- **U**：本轮用户明确要求；作为目标需求。
- **D**：上传草案中的陈述；作为评审对象，不自动认定为已实现事实或用户已经批准。
- **R**：本轮读取的仓库源码或元数据；只证明所读提交的静态内容。
- **E**：官方文档；只证明其描述的框架接口/行为，不证明 Wuji 已完成适配。
- **P**：本次提出的设计决策；以 SPEC.md 为准，仍待实施批准。

## U1 — 本轮明确目标

不使用 Cairn Server、Dispatcher 或原生黑板作为新系统运行依赖；使用 MAF 重构 Agent 执行；自行完善调度；区分模型主张与真实调用证据；画布使用 `@xyflow/react`，组件名 `TopologyFlowCanvas`；交付 Spec 和 Plan。

## D1 — 上传草案

[原始草案，保持原文](INPUT_SPEC.md)。评审中的行号按此文件计算。草案提及的其他本地文档、历史测试结果、价格授权及本地未提交代码，没有在本轮全部重新核验。不能将这些陈述变成本次测试证据。

## R1 — Wuji 仓库基线

- 仓库：<https://github.com/yimingy72/wuji>
- 本轮复核基线：`1d73a767599732d9a53f81ad2cc553f4bf11d84e`，分支 `codex/github-upload`。
- [根 package.json](https://github.com/yimingy72/wuji/blob/1d73a767599732d9a53f81ad2cc553f4bf11d84e/package.json)：现有 pnpm 脚本、Node 24.x、pnpm 10.32.1；根 typecheck/build 默认仍指向 frontend spike，新计划显式使用正式 web 脚本。
- [根 pyproject.toml](https://github.com/yimingy72/wuji/blob/1d73a767599732d9a53f81ad2cc553f4bf11d84e/pyproject.toml)：Python 3.13.15、uv workspace、Cairn git 来源与 bridge 分组、pytest 当前 testpaths。
- [apps/web/package.json](https://github.com/yimingy72/wuji/blob/1d73a767599732d9a53f81ad2cc553f4bf11d84e/apps/web/package.json)：正式前端 React/Ant Design/React Query，未列出 `@xyflow/react`。
- [递归文件树](https://api.github.com/repos/yimingy72/wuji/git/trees/1d73a767599732d9a53f81ad2cc553f4bf11d84e?recursive=1)：用于确认 apps/api、apps/web、迁移和包目录。
- 本轮代码搜索未检索到 `TopologyFlowCanvas`；不能据此断言用户本地不存在该组件。计划将其视为**明确的目标组件名**，在实施基线核对时决定是迁入本地已有组件还是按同名新建。

## R2 — MAF 源码参考

- [Harness 工厂](https://github.com/microsoft/agent-framework/blob/3c670707766a8455da6491a9049cc9d575e019f0/python/packages/core/agent_framework/_harness/_agent.py)：核对公开参数、返回普通 Agent、默认历史/文件记忆、可选后台 Agent/文件访问/循环、自动工具审批与 Web Search 等行为。
- 参考提交：`3c670707766a8455da6491a9049cc9d575e019f0`。**这不是已经安装或验证的发布包锁。** P01 必须通过已发布 wheel、完整 lock 与隔离环境检查收口，不能将仓库 HEAD 的版本字符串等同于对应 wheel 的内容。

## E1 — MAF Harness

<https://learn.microsoft.com/en-us/agent-framework/concepts/harness>

用于核对 Harness 是组件组合，不是独立的黑板/调度服务；工厂与实验特性成熟度分别处理。

## E2 — MAF 会话与持久化

- <https://learn.microsoft.com/en-us/agent-framework/hosting/self-hosting>
- <https://learn.microsoft.com/en-us/agent-framework/agents/conversations/storage>

用于核对完整 Session 与 HistoryProvider 是不同持久化职责；默认内存历史不是可靠数据库；应用负责认证、授权及存储。本文提出的事务式会话提交协议不是官方现成功能。

## E3 — MAF 工具审批

<https://learn.microsoft.com/en-us/agent-framework/agents/tools/tool-approval>

用于核对函数工具审批、返回待输入请求及随后继续运行。审批数据库、有效期、身份绑定、跨 Run 移交由 Wuji 实现。

## E4 — MAF 观测

<https://learn.microsoft.com/en-us/agent-framework/agents/observability>

用于核对 OpenTelemetry 与敏感数据风险；观测系统不是业务账本或计费权威。

## E5 — React Flow 组件与受控状态

- <https://reactflow.dev/api-reference/react-flow>
- <https://reactflow.dev/api-reference/hooks/use-nodes-state>
- <https://reactflow.dev/examples/interaction/save-and-restore>

用于核对 `nodes/edges`、自定义节点/边、交互回调及布局保存。它是前端画布，不是黑板数据库或任务执行引擎。`TopologyFlowCanvas` 不是官方内置组件。

## E6 — React Flow 布局与性能

- <https://reactflow.dev/learn/layouting/layouting>
- <https://reactflow.dev/learn/advanced-use/performance>

布局由应用选择；本方案建议 ELK 仅作为候选布局器，由 P13 验证后固定依赖，不把布局结果解释为业务因果或执行顺序。

## E7 — PostgreSQL 一致性

- <https://www.postgresql.org/docs/current/transaction-iso.html>
- <https://www.postgresql.org/docs/current/sql-select.html>

Read Committed 的不同语句不保证看到同一快照；Repeatable Read 和显式锁需要按操作正确使用。`SKIP LOCKED` 适用于领取竞争，不能取代容量、授权或结果结算条件。文档指向 current；实际数据库版本沿用已核实部署并在 P01 固定。

## 未完成的验证

未运行 MAF wheel、真实压缩/审批续接、跨进程会话恢复、React Flow 画布、PostgreSQL 并发测试、Runtime 停止、模型网关计费、生产出口或性能测试。对应验证被写入 Plan 和验收矩阵，不能将“计划检查”记录成“已经通过”。
