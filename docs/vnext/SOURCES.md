# 来源、依据与证据边界

**检查日期：2026-09-13。** 这份复审的基础是本次对话已有文件；外部官方文档只用于核对框架/数据库/画布性质，没有替代原文。文件摘要见 [source_manifest.json](source_manifest.json)。

## 来源分类

| 标签 | 来源 | 用途与限制 |
|---|---|---|
| U1 | 用户本轮与前序明确要求 | 全面复审三文档、允许 Agent 提炼事实、自有黑板/调度、Python MAF、React Flow、退出 Cairn；不等于批准停机、收费或删除 |
| O1 | [原始草案](source/ORIGINAL_DRAFT.md) | 保留原术语、场景、责任、范围与限制；其中本地路径/验收/公司价格是草案陈述，本轮未复测 |
| O2 | [上一版 Spec](source/V1_SPEC.md) | 本轮直接审计对象；不能因它是上一轮助手生成就视为可靠基线 |
| O3 | [上一版 Plan](source/V1_PLAN.md) | 核对任务、依赖、接口、测试和阶段出口 |
| O4 | [上一版 Review](source/V1_REVIEW.md) | 审查先前“问题→修复”是否准确、是否混入未经解释的新偏好 |
| D | 本版建议、规范与测试目标 | 明确是设计决定；不是原稿事实，也不是 MAF 原生 API 或已完成代码 |
| E1–E7 | 下列本轮读取的官方网页 | 只支持列出的外部事实；不证明 Wuji 集成成功 |

原件比对：上一轮独立上传的 SPEC/PLAN/REVIEW 与 ZIP 中对应副本逐字节相同；本包 source 未修改原件。原稿与 v1 的版本/时间声明保留，不混写为本轮版本。

## 本轮外部核查

| ID | 官方来源 | 实际支持的内容 | 不应推出的结论 |
|---|---|---|---|
| E1 | [MAF Harness](https://learn.microsoft.com/en-us/agent-framework/concepts/harness) | Harness 组合既有 Agent/客户端/Provider/中间件，Python工厂返回普通Agent；部分可选功能仍实验性 | 不证明已安装wheel含所有源码能力、不证明生产适配完成 |
| E2 | [MAF Session](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/conversations/session) | Session含本地/服务会话标识和state；Harness默认内存history；有序列化/恢复接口且配置兼容重要 | 不证明任意崩溃点完整恢复、不把服务ID当用户授权 |
| E3 | [MAF Tool Approval](https://learn.microsoft.com/en-us/agent-framework/agents/tools/tool-approval) | 需输入时run返回请求；应用负责收集决定并继续调用，函数可标记审批 | 不证明Wuji的审批库、跨进程恢复或审批消费事务已存在 |
| E4 | [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) | Read Committed与Repeatable Read的事务可见性不同 | 不把一次读事务当跨HTTP的永久快照 |
| E5 | [PostgreSQL Row Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | owner、超级用户及BYPASSRLS对策略适用有例外 | 不以owner连接测试通过证明应用租户隔离 |
| E6 | [React Flow component](https://reactflow.dev/api-reference/react-flow) | 支持受控nodes/edges、自定义类型与交互回调 | 不提供Wuji业务真相、权限、完整历史或持久事件流 |
| E7 | [MAF Observability](https://learn.microsoft.com/en-us/agent-framework/agents/observability) | OTel traces/logs/metrics与导出配置；敏感数据记录有风险 | 不将Trace当费用/审计权威、不声称启用后端即已部署 |

网页可能继续变化；P01必须用实际发行包、lock、模型网关组合和观测证明目标能力，而不是仅按网页文字执行。

## 没有重新证明的内容

本轮没有读取用户本机仓库、当前集群或数据库；原稿中的 `codex/github-upload@1d73a...` 只是历史基线。没有重新运行 W1、MAF SDK、React Flow 构建、PostgreSQL 并发测试、生产出口或真实题目效果测试。

旧文档的公司价格、运行费用、验收截图与路径不复制成新的实测结果。Plan路径标为新目标路径；`TopologyFlowCanvas` 是否已在用户本地存在由P00核对。README和VALIDATION_REPORT中的通过仅指本包真实执行的文档校验。

## 外部事实与设计建议的对应

S08/S09引用E1–E3；S04引用E4/E5；S12引用E6；S14引用E7。其余生命周期、Fact视图、ViewStream、完成收敛等是本版[D]，不是声称官方提供了这些同名模块。复审项原文可在 source 按行找到，定位索引见 AUDIT_COVERAGE。
