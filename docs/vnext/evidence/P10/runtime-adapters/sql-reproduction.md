# C0 runtime adapters · 完整脱敏 PostgreSQL 事件流

以下文件由实际测试记录的 `postgres-events.jsonl` 派生。解压后保留完整有序的连接、事务、SQL、参数、结果和异常事件；只递归替换凭据值。每个本地原件及归档文件的 SHA-256、字节数和脱敏计数见[index.json](index.json)。

## Remote Workspace

- [主链及撤销后旧 receipt](raw/sql/remote-main-revocation.postgres-events.jsonl.gz)
- [callback 提交后 ACK 丢失](raw/sql/remote-callback-lost-ack.postgres-events.jsonl.gz)
- [callback 提交后 5xx](raw/sql/remote-callback-503.postgres-events.jsonl.gz)
- [callback 提交后坏 ACK](raw/sql/remote-callback-bad-ack.postgres-events.jsonl.gz)
- [dispatch 不明且 query 为 not_registered](raw/sql/remote-dispatch-not-registered.postgres-events.jsonl.gz)
- [permit 篡改、错误 executor 与错误 Gate 主体](raw/sql/remote-tamper-and-identity.postgres-events.jsonl.gz)

这些流对应真实 `bound_attempt`、Task ACL/call clearance、`executor_registration`、DB 原 permit、`ToolAdmission.check_execution` / `validate_receipt_permit` 及 P03 evidence 持久化。没有把测试侧 allow 布尔量写成权限结果。

## Task Pod receiver

- [当前 P05 permit、session lease、已核对 Pod UID 与 0017 receiver 登记](raw/sql/pod-current-permit-lease-registration.postgres-events.jsonl.gz)
- [错误 Pod owner 拒绝且不登记 receiver](raw/sql/pod-foreign-owner-rejected.postgres-events.jsonl.gz)

第一条还包含第二连接无法取得 Task-wide advisory lease、close 精确 disable receiver、同 attempt 不同 Pod UID 拒绝。Pod API 来自记录型 PodClient，因此这些 SQL 只证明 P05/0017 与受信 API 输入的组合，不证明 Kubernetes API/Pod 实际运行。

读取示例：

```bash
gzip -dc docs/vnext/evidence/P10/runtime-adapters/raw/sql/pod-current-permit-lease-registration.postgres-events.jsonl.gz
```

原始数据库连接信息、JWT、execution token、私钥或可用凭据不进入 Git；占位符带原值 SHA-256，仅用于对照本地原件，不能授权或重放。
