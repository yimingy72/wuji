# P07 M1 接口与资产验证状态

绑定代码 SHA：`bcc64ffa67ea3b910f62b065853108cdb7d67614`。

该表是首轮 hosted 闭环的历史清单。独立审查后的当前状态绑定
`5cfd581129c7991deaddaad9bfdaf8b4ee34b140`，见
[review-fixes/interface-inventory.md](review-fixes/interface-inventory.md)。

| 接口/资产 | 验证状态 | 本切片证据 |
| --- | --- | --- |
| `MafRuntime.execute(WorkerAssignment)` / native `ResponseStream` | 已利用 | 实际 MAF SDK 发起 2 次 native SSE 请求；事件消费者取消后后台任务仍完成 |
| `POST /internal/v2/model/chat/completions` / `ModelGate` | 已利用 | 2 次不同 `X-Wuji-Request-ID`，响应带真实 `X-Wuji-Model-Attempt-ID` |
| `POST /internal/v2/tool-calls` / `ToolGate` | 已利用 | 非空 provider call ID 与 SDK occurrence ID，实际执行 1 次 `workspace_read` |
| `WorkspaceReadExecutor` / `version.txt` | 已利用 | 返回 `fixture-version=17\n`，产出 sealed Artifact |
| P03 Observation / EvidenceReceipt | 已利用 | EvidenceReceipt 为 accepted；Observation 与 Artifact 持久化并可读 |
| `PlatformWorkerHost.submit_result` / P04 `ResultCommitter` | 已利用 | 原始最终字节先封存，候选 Claim accepted_shared，重放不新增 revision 或网络调用 |
| Claim assessment | 已利用 | producer=`agent`，producer_ref=`run-fixture`，无 FactAssessment，显示为 `claim` |
| Run credential revocation | 已利用 | 新模型请求和新工具请求均返回 409 `STALE_EXECUTION`，计数不变 |
| Scheduler / Supervisor / Pod / Task completion | 未利用 | 属于 M2/P09/P10 后续；本 hosted M1 不提供这些证明 |
| Session restoration / native approval / MCP | 未利用 | 超出 M1 范围，未声称支持 |
