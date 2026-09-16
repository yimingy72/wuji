# P12 evidence index

- [Completion precheck](completion-precheck-20260916/README.md): 迁移 `vnext_0022_p12_completion` 加完成期生产者；
  precheck 只认已持久化判定，真实集群 7 个 Task 全部 `wait/criteria_unmet`。
- [Completion judgment and epoch](completion-judgment-20260916/README.md): 迁移 `vnext_0023_p12_judgments` 加判定与
  关闭决定生产者；真实 Task `fc2ff1b0-…` 用一份已封存 artifact 写入 `met/current` 判定后 precheck 变为 `ready`，
  写入 quiescing 决定并 `apply` 成功进入完成期（`observed_state=quiescing`、`execution_allowed=false`）。
