# P08 candidate and 0014 source preparation

状态：SOURCE_ONLY 局部无 DB checks 已执行；candidate 实际 owner 登记/消费、0014 DDL/RLS、Session publish/CAS、审批原子事务和完整 P08 均为 `not_run/未验证`。代码提交为 `c021be3`。

本切片落实显式 `mechanism_candidate|verified`：candidate 允许空证据但必须短期绑定固定 synthetic Task/receiver/runtime/Pod/profile/model/tool/executor；verified 必须用新不可变 ref 并带非空真实证据。`SessionCompatibility` 保留 validation status，不能把 candidate 展示为 verified。0014 聚合链明确位于 Dirac `vnext_0013_receiver_results` 之后。

执行过的无 DB 节点：

- SessionRepository 参数入口：1 passed / 2.05s。
- SessionManifest JSON datetime 与 provider SSE/raw call：2 passed / 1.04s。
- Candidate 新合同 RED：缺 validation/binding/digest 字段，1 failed / 1.01s。
- Candidate RunIdentity RED→GREEN：真实 `RevisionString` 与 wire 字符串直接比较会恒不相等；加入 JSON-mode exact identity 匹配后 1 passed / 1.19s。
- Verified 非空 evidence/new-ref 合同：1 passed / 0.71s。
- 0014 module RED→GREEN：缺 migration module 后，最终 parser/head guard 为 1 passed / 0.83s。

完整 stdout、stderr、exit code、HEAD 与文件摘要均先保存在 `work/p08/<run-id>/` ignored 受限目录。本目录不复制或手工重建 raw，只发布来源摘要：[binding.json](binding.json)。所有 stderr 均为真实空文件；stdout 中保留固定 SDK `AgentFileStore` experimental warning。

本轮没有连接 PostgreSQL、执行 DDL、发送 HTTP、运行真实 SDK 模型/ToolGate、启动 child/Host 或发布 capability；没有相关 HTTP 包或截图。实际机制候选必须等 Bacon/Dirac consumer 固定并由 main 安排串行 PG/HTTP。
