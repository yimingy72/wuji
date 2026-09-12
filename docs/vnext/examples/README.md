# 文档示例（不是运行回执）

这些 JSON 是设计合同的测试数据，所有ID、摘要和时间均为示意，未对应真实业务执行。`reject_` 前缀是必须被示例 schema 拒绝的反例，不可送生产执行。

`checks/example.schema.json` 只覆盖本包示例 profile 的闭合结构；完整业务路由、Reason payload 扩展、身份授权、数据库并发及已安装 MAF 行为由 Plan P02 与后续任务验证。结构通过不证明内容真实。

ClaimProposal 正向示例允许 Agent 提出候选事实；FactAssessment 示例代表可信检查服务的输出，Agent 主体即使构造相同 JSON 也必须被服务端拒绝。两条不同主体路径不能仅凭 schema 合法而合并。

ViewEventBatch 示例不含全局 Task 序号；cursor 仅示意服务端不透明 handle，示例字符串不提供加密或认证。
