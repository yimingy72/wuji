# P07 M1 hosted Worker 独立审查

- 日期：2026-09-13
- 审查范围：M1 归属的 `factory.py`、`runtime.py`、`tools.py`、`entrypoint.py`、`worker_host.py`，以及 `bcc64ff` 对 P06 `admission/tools.py` 的窄序列化修复
- 初始核心：`a014904085108b27cce78f3ffdc30d6d60ad03ef`
- 最终被测代码：`bcc64ffa67ea3b910f62b065853108cdb7d67614`
- 复用证据提交：`d81f6cf65b2a3c3aad6e13cdd05020f9b18f876f`
- 结论：**CHANGES_REQUIRED（2 个 P1、1 个 P2）**。已有证据真实证明了当前同源夹具下的 hosted M1 正向闭环，但下面问题阻止把该实现视为身份闭合、保持 SDK 语义且持久可核对的 M1 结果。此结论不把 M1 提升为完整 P07。

本次只读检查使用提交定点读取和 `bcc64ff` 的相关路径 diff，没有使用会混入 P14/D11 的跨提交全分支 diff；未启动新测试、PostgreSQL、服务、子代理或反例运行。工作树原有未跟踪 P06/P09 内容保持不动。

## Findings

### P1 · Host/Assignment 身份与实际 Gate bearer 可以被拼接成两个不同 Run

位置：

- `packages/maf-worker/src/wuji_maf_worker/runtime.py:38-47,109,153-156`
- `packages/wuji-core/src/wuji_core/worker_host.py:27-30,40-44`
- `packages/wuji-core/src/wuji_core/http/model_gate.py:27-31`

触发：`MafRuntime` 独立接收 `host` 和原始 `run_credential`。`PlatformWorkerHost.resolve()` 只证明 `host.access` 的绑定与 `assignment.identity` 相等；随后模型与工具 HTTP 使用另一个未经同源核对的 bearer。ModelGate 请求体没有 RunIdentity，服务端只从 bearer 推导当前 Run。因此，若装配层把 Run A 的 `host/context/assignment` 与 Run B 的有效 token 组合，且两边使用相同的共享模型/工具 Profile，B 的 ModelGate 会接受并把 A 的 Context 发往 B 的上游。即使后续工具回执在 A 的 sink 被拒绝，A 的资料已出站且请求被记到 B；模型若直接返回无工具结果或只引用 A 的原始 read_set，A 的 ResultCommitter 还可以接纳结果。

影响：这是跨 Run 的数据与计量身份混淆。两个 HTTP Gate 本身仍被调用，但它们授权的是 bearer 对应的 Run，而 hosted Worker 的输入和结果属于另一个 Run，因而不能称为组合层的两 Gate 身份闭环。

最小复现（静态确定；依用户要求未新建 DB 反例）：准备两个使用同一 `client_model` 和工具 schema 的当前 Run；以 `host_A/context_A/assignment_A` 调用 `MafRuntime(..., run_credential=token_B)`。现有构造函数和 `resolve()` 没有任何比较会在首次模型 HTTP 前拒绝该组合。当前测试夹具在 `tests/vnext/support/m1.py:505,561-563,658-665` 恰好从同一个 `credential` 同时构造两侧，因此没有覆盖错配。

最小修复：让可信装配点从同一个已验证 credential 一次性产生 Host access 与 Gate transport，或向 Worker 提供服务端签发、可校验的绑定对象，使 `subject/token_id/RunIdentity` 在首个模型请求前与 assignment 一致；不要在 Worker 内仅解析未验证 JWT claims。

### P1 · bcc 请求适配删除了有语义的 SDK 字段，冻结的串行工具行为没有到达上游

位置：

- `packages/maf-worker/src/wuji_maf_worker/tools.py:23-45`
- `packages/maf-worker/src/wuji_maf_worker/factory.py:89-111`
- `packages/wuji-core/src/wuji_core/admission/models.py:48-91`

`bcc64ff` 先确认 SDK 发出 `parallel_tool_calls=false` 和 `stream_options={"include_usage":true}`，随后用 `pop()` 删除两者，并把 SDK 的 `max_completion_tokens` 改写回 `max_tokens`。P06 随后只改模型名并原样转发，所以这些字段不会在 Gate 后恢复。这不是只确认默认值：

- `parallel_tool_calls=false` 是 factory 通过 `allow_multiple_tool_calls=False` 固定的执行约束。删除后由上游采用自己的默认值；若返回多个调用，固定 SDK 的 FunctionInvocationLayer 会并发执行该批调用。
- `stream_options.include_usage=true` 是固定 SDK 为 streaming 请求显式加入的 usage 能力；删除会使上游不再收到 usage opt-in。
- `max_completion_tokens -> max_tokens` 改变了公开 OpenAI Chat Completions 方言；只接受新字段的模型会在 Gate 后失败。

已安装公开 SDK 实物也证明这些字段不是私有探针：`agent_framework_openai/_chat_completion_client.py:247-248,635` 分别定义 token 字段翻译并为 stream 加入 usage；`agent_framework/_tools.py:1896-2037` 明确并发执行一个函数调用批次。

现有完整 HTTP 包已经是最小复现。解码主闭环第一条 Gate 与 upstream 请求，实际结果均为：

```json
{
  "max_tokens": 2048,
  "max_completion_tokens": null,
  "parallel_tool_calls": null,
  "stream_options": null,
  "tool_count": 1
}
```

当前 synthetic endpoint 接受 `max_tokens` 且只返回一个工具调用，所以 3 项 M1 检查不会暴露该问题。最小修复应在 P06/M1 边界保留这些字段，或由 Gate 明确执行等价约束并按已发布模型能力选择 token 方言；不能通过删除字段把受控行为交还给上游默认值。

### P2 · SDK archive 没有持久所有者，replay 也没有核对 SDK/tool 输入身份

位置：

- `packages/wuji-core/src/wuji_core/worker_host.py:102-103,126-155`
- `packages/maf-worker/src/wuji_maf_worker/runtime.py:132-137,172-186`
- `packages/wuji-core/src/wuji_core/persistence/schema.py:238-247`

成功路径在 `_stage()` 后丢弃 `archive_sdk()` 返回的 BlobRef；失败路径同样丢弃。ResultSubmission 只发布 515 字节的最终文本 Artifact，SDK NDJSON 没有 publication/ref、Observation、Snapshot 或其他持久引用。实际 SQL 在 `postgres-events.jsonl:7956` 保存了 12126 字节 `application/x-ndjson` Artifact `6a2d12f2-...`，但唯一关联是五分钟 staging lease；结果 publication 只引用最终文本 Artifact `b44a9f42-...`。按 `artifact_retained()`，lease 过期后该 SDK archive 可被 GC。

同一缺口也出现在 replay：`submit_result()` 的已有提交分支只比较 writer、RunIdentity、raw digest、snapshot_id 和 read_set，然后在第 150 行直接返回；不同的 `sdk_output`、`tool_receipts`、`context.input_digest` 或 `record_refs` 不会产生 `INPUT_DIGEST_CONFLICT`，也不会再次经过 `_tool_basis()`。因此“没有重执行”已被证明，但“同一完整输入才是 replay”尚未成立。

影响：进程退出后可能失去 Session/SDK message/identity mapping 的受限原始档案；调用方还能把不同 SDK/tool 来源冒充为原提交的 replay。现有 Claim→Observation→ToolAttempt 业务来源仍然存在，本问题不否定本轮 P03/P04 Claim 结果，也不等同于要求 P08 恢复。

最小修复：把 SDK archive ref 及稳定的 tool receipt/context digest 绑定到受限的 Run/result 持久记录并纳入保留规则；已有提交返回前比较这些持久摘要。完整 SessionManifest/恢复仍留给 P08。

## 已核对通过的 M1 范围

- 公开 SDK 与唯一循环：生产代码使用公开 `create_harness_agent`、`Agent.run(stream=True)`、`ResponseStream`、`FunctionMiddleware` 和 `FunctionInvocationContext`；没有第二套模型/工具循环或私有 SDK patch。
- Profile 与广告实物：固定 SDK 在两次模型请求中均广告且只广告一个 `read_fixture`，schema 与发布 ToolDefinition 相同；Todo、Mode、文件记忆/访问、Skills、Shell、WebSearch、后台 Agent、外层循环、自动审批、compaction、restore 和 MCP 在 M1 snapshot/factory 中关闭。
- 实际调用身份：首个 ModelGate attempt header 被组成 message identity；provider call ID=`call-m1-read`，SDK occurrence ID=`af-call-...`，P06 的 bcc RootModel 序列化修复在实际 ToolCallRequest 中保留为非空字符串。模型参数不能提供 Task/Run/URL。
- 两 Gate 当前同源路径：2 次模型请求和 1 次函数工具请求都经过真实 HTTP Gate；撤销后直接模型/工具请求均为 409 `STALE_EXECUTION`，上游/model_attempt/tool_attempt 计数不增。上述 P1 身份拼接仍需修复。
- Task Key 与私有输出：Worker 只持 Run token，Task Key 由 ModelGate 私有 resolver 获取；提交证据中未发现明文 Task Key、JWT、私钥或环境 Key。公开 WorkerEvent 只有 ResultReceipt，不含 prompt、最终原文、SDK message 或 provider metadata。
- 消费者断开：事件 consumer 在首个模型响应前取消后，受 shield 保护的 Worker task 继续完成工具、第二模型请求和 P04 提交。
- P03/P04：实际文件字节 `fixture-version=17\n` 形成 sealed Artifact、Observation 和 accepted EvidenceReceipt；最终候选由 P04 记录为 `producer_kind=agent`、`producer_ref=run-fixture`、basis 为该 Observation、无 FactAssessment，展示为 Claim。
- 相同实参 replay：已有证据中的同一 `raw_output/context/tool_receipts/sdk_output` 重放没有新网络请求，也没有新增 Claim revision、Observation、model attempt、tool attempt 或 result row。更严格的完整输入等价见 P2。

## 明确未覆盖，非本次 scope 缺陷

MCP transport、原生 approval、compaction、Session restore、Supervisor/process truth、Scheduler、持久 delivery、Task completion、Kubernetes/Pod、真实收费模型效果均未覆盖。完整 AC-036/AC-037/AC-043 和完整 P07 保持未通过；本报告也不把 M1 的 hosted 结果扩写成 G2、M2、M4 或全 P07。

现有 3 个 M1 用例没有单独运行“未登记函数”或“不执行 callback”的正式负控；当前正向实物能证明实际文件读取/证据入账，但不能替代完整 AC-003/AC-037 的负控。依用户指令本轮未增加或运行这些测试。

## 复用证据

- 既有命令记录：[`docs/vnext/evidence/P07/M1/final-verification.txt`](../../../docs/vnext/evidence/P07/M1/final-verification.txt)，记录 `3 passed in 9.13s` 与直接受影响 P06 consumers `2 passed in 5.70s`；本审查未重跑。
- 完整 Gate HTTP：[`platform-gate-http.jsonl`](../../../docs/vnext/evidence/P07/M1/final-verified/raw/0b3a90d78c4d/platform-gate-http.jsonl)
- 完整 upstream HTTP：[`model-upstream-http.jsonl`](../../../docs/vnext/evidence/P07/M1/final-verified/raw/0b3a90d78c4d/model-upstream-http.jsonl)
- 完整 SQL：[`postgres-events.jsonl`](../../../docs/vnext/evidence/P07/M1/final-verified/raw/0b3a90d78c4d/postgres-events.jsonl)
- 撤销请求包：[`platform-gate-http.jsonl`](../../../docs/vnext/evidence/P07/M1/final-verified/raw/f0b4d1a67bd8/platform-gate-http.jsonl)
- 截图证据：![P07 M1 final verification](../../../docs/vnext/evidence/P07/M1/screenshots/m1-final-verification.png)

