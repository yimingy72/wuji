# P12 evidence index

- [Completion precheck](completion-precheck-20260916/README.md): 迁移 `vnext_0022_p12_completion` 加完成期生产者；
  precheck 只认已持久化判定，真实集群 7 个 Task 全部 `wait/criteria_unmet`。
- [Completion judgment and epoch](completion-judgment-20260916/README.md): 迁移 `vnext_0023_p12_judgments` 加判定与
  关闭决定生产者；真实 Task `fc2ff1b0-…` 用一份已封存 artifact 写入 `met/current` 判定后 precheck 变为 `ready`，
  写入 quiescing 决定并 `apply` 成功进入完成期（`observed_state=quiescing`、`execution_allowed=false`）。
- [Completion close](completion-close-20260917/README.md): AC-049 冻结期继续收回执 + AC-052 强制关闭取消未完成工作；
  真实 Task `fc2ff1b0-…` 从 `quiescing` 走到 **`observed_state=closed`**（trigger=goal_satisfied、outcome=complete、
  execution_allowed=false、control_version=4），两份决定与判定事实一并记录。
- [Report freeze and late counter-evidence](report-freeze-20260917/README.md): `vnext_0024_p12_reports` 冻结报告
  正文（服务端 digest）并把迟到反证追加为争议记录；真实关闭的 Task 上实测：正文与 digest 不变、dispute 变
  `disputed`、Task 仍 `closed`、无 ready work（AC-053）。
