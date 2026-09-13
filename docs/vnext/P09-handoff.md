# P09 已验证切片公共交接

2026-09-13。实现/验证基线 `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c`；定向修复 `e0a10b586905ed705b0d7f520bda6f6f96b26cac` 已由 Dalton SOL/xhigh 独立复审 PASS。范围与原始输出见[永久证据](evidence/P09/README.md)，缺失 SQL 运行日志已明确登记。

P09 已测迁移链为 `vnext_0010_p09_scheduler` → `vnext_0011_p09_dispatch_fairness`。这表示 P09 的历史边界，不声明当前集成工作树 HEAD；P13 的后续 0012 由其负责人集成。0010 未被 0011 改写。0011 添加每 Work `consideration_round` 和 receiver `pod_uid`，无可信 UID 的旧 receiver 禁用，须由受信环境生产者重新登记。

公共 Python 端口保持在以下模块；这些是直接服务调用，不是对外 HTTP 或 Supervisor 已运行的证明：

- `scheduling.policy`：`Candidate(..., eligible=True, consideration_round=0)`；`SchedulerPolicy.select(SchedulingSnapshot)` 返回 proposal；`WorkKey.digest`；`ProgressSummary.made_progress`。
- `scheduling.claims`：`Scheduler.tick(now=None, limit=16)`；`SchedulerOwnership.acquire/assert_owned/borrow/close`；`WorkRepository.register(tx, key, kind, priority)`；`DispatchRepository.read(tx, operation_id)`。
- `scheduling.triggers`：`TriggerRepository(artifacts=...).start/read/record/begin_reason/consume/fail`；`scheduling.waiters`：`WaiterRepository.from_result/register/scan` 与版本化 `WaitPredicate`。
- `scheduling.credentials`：真实 `RunCredentialIssuer.prepare/bind_admitted_run/retrieve`，部署提供签名/加密/公钥 resolver；`retrieve` 是注册 receiver 的 observe 管理端口。
- `persistence.snapshots`：`create_in_transaction(tx, query=None, reader_clearance=None)`，原 `create/get/page/read_ref` 仍保留。

Snapshot 跨主体读取只允许实际 Assignment/Run 对应的 signed subject/JTI、有效未撤销 credential、当前 Task/Work/Run 身份与 epoch、ACL/clearance 及 run_writer；固定 Intent/basis 缺失在 Run/credential/reservation/dispatch Outbox 创建前阻断。原创建者 access_digest 规则保留。凭据密文及引用在同准入事务提交；管理阶段读取凭据不构成模型/工具执行许可。

`pod_uid` 从固定 receiver/runtime/environment 原样复制到 AgentRun。已测值是显式 synthetic fixture UID，P10 实际 Pod 路径必须使用真实 Kubernetes `metadata.uid`；本交接没有真实 spawn/start/exit 结论。

原 31+4+容量竞态1 与修复 3+升级1+UID1 分属两组版本和运行，不汇总成完整 P09 accepted。真实 M2、P08 非知识生产事件、真实退出 failure/retry 闭环与恢复仍 partial。归档时 P09 无运行中的 DB/HTTP 命令，生产/shared 源及 PG 窗口已不归本归档任务；本次只提交 docs/证据，不修改迁移 README。
