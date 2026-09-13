# P07 M1 三项定向复审

- 日期：2026-09-13
- 复审模型：`gpt-5.6-sol / xhigh`
- 原审查：[P07-M1-review.md](P07-M1-review.md)
- 原审查被测代码：`bcc64ffa67ea3b910f62b065853108cdb7d67614`
- 修复代码：`5cfd581129c7991deaddaad9bfdaf8b4ee34b140`
- 修复提交父项：`fd66d2b86582bc012516cbcd6c4eb62226ff07f0`
- 证据提交：`57ec12ea2ada7acf7fe6a0ac7ac98b40e7c66012`，其父项即上述修复代码
- 结论：**PASS**。原审查的 2 个 P1、1 个 P2 均为 **closed**；本 source bound 内无 remaining finding。

## Source bound 与方法

本次只读取原报告、vNext 阶段入口、P07 实施合同、[修复证据 README](../../../docs/vnext/evidence/P07/M1/review-fixes/README.md)、`5cfd581^..5cfd581` 的 M1/OpenAPI/P06 窄改，以及 `57ec12e` 中已有的真实 HTTP、SQL、结果摘要和截图。修复提交只改 10 个 M1/合同/直接消费者文件，不含 migration、schema、Grant、角色或权限策略文件。

当前工作树 HEAD 为 `fd9c474ab2be9d32aeabda2690a120cb2c003343`，工作树还含 P09/P10 等未提交内容；它们以及 P13/P14、Supervisor、全分支 diff 均未纳入判定。`57ec12e..HEAD` 未修改本次定点读取的 M1 修复路径和 `review-fixes` 证据，但本报告仍只对 `5cfd581` 代码与 `57ec12e` 证据负责，不把结论自动扩展到后续 HEAD。该工作树没有 `.codegraph/`，因此按仓库约定回退到 Git 提交定点源码读取。

本次没有运行测试、PostgreSQL、SDK、浏览器或服务，也没有改动业务代码。下文的 `5 passed`、`2 passed`、HTTP 和 SQL 均是证据提交已有结果，本次只读复核，不能称为本复审执行。

## 1. P1 Host、bearer 与完整 Run 身份拼接

状态：**PASS / closed**。

`5cfd581:packages/maf-worker/src/wuji_maf_worker/runtime.py:114-122` 在创建 HTTP client、构造 SDK agent 和进入 `agent.run` 之前，以部署注入的真实 `TokenVerifier` 验签实际 bearer。`TokenVerifier.verify` 使用 RS256 并校验 issuer、audience、subject、有效期、JTI、tenant 和 roles；返回的 Principal 固定 `subject/tenant_id/roles/token_id`。

随后 `PlatformWorkerHost.resolve` 先要求该 verified Principal 与 `Host.access.principal` 完全相同，再由 Host access 的 tenant/subject/JTI 定位唯一 run credential binding，并要求 binding 的完整 `RunIdentity` 与 Assignment 相等。完整身份包含 tenant、project、task、work item、agent run、execution epoch、run epoch、runtime attempt 和 receiver；`model_request` transaction 还沿既有 P06 current-run/revocation/expiry 路径复核当前资格。首次可能携带 ContextBundle 的模型 HTTP 位于上述检查之后，因此 Run A 的 Host/Context/Assignment 不能再与 Run B 的有效 bearer 拼接出站。

既有错配负控使用同一真实 issuer 签发的两个有效 Run 凭据。两个 Principal 的 subject/JTI 不同；证据目录没有生成 Gate 或 upstream HTTP 文件，SQL 最终 `model_call` 计数为 0。该证据与静态调用顺序一致。

- 签发身份：[p06-identity-events.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/4a33faf6a572/p06-identity-events.jsonl)
- 完整 SQL：[postgres-events.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/4a33faf6a572/postgres-events.jsonl)
- 零 HTTP 说明：[修复证据 README](../../../docs/vnext/evidence/P07/M1/review-fixes/README.md)

Remaining：无。

## 2. P1 SDK 请求字段与 token 方言

状态：**PASS / closed**。

OpenAPI v2 与生成的 Python/TypeScript DTO 现在都保留 `parallel_tool_calls`、`stream_options.include_usage`、`max_tokens` 和 `max_completion_tokens`；公开边界禁止两个 token-limit 字段同时出现。M1 的 `ModelCallIdentity.request` 只校验冻结行为和广告表，并设置请求 ID，不再 `pop` 字段、重命名 token 方言或重写 request body。

P06 `ModelAdmission.authorize` 从完整原始 JSON 建立 source，校验 DTO 后复制 source，仅把已发布的 client model 替换成 upstream model，再将其入账和转发。因此串行工具约束、usage opt-in 和 SDK 选择的 token 方言由请求显式携带，不依赖上游默认值。

既有同源实际 SDK 正例的两次完整 Gate 请求和两次完整 upstream 请求均为：`parallel_tool_calls=false`、`stream_options={"include_usage":true}`、`max_completion_tokens=2048`，没有 `max_tokens`；两侧仅 model 名按发布配置变化。原 P06 `max_tokens=64` 方言的两个直接消费者记录为通过，说明此次 DTO 扩展没有删除旧方言。该通过记录为既有证据，本复审未重跑。

- 完整 Gate 请求/响应：[platform-gate-http.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/0b3a90d78c4d/platform-gate-http.jsonl)
- 完整 upstream 请求/响应：[model-upstream-http.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/0b3a90d78c4d/model-upstream-http.jsonl)
- 既有命令输出：[final-verification.txt](../../../docs/vnext/evidence/P07/M1/review-fixes/final-verification.txt)

Remaining：无。

## 3. P2 SDK archive、完整 replay 与结果权威

状态：**PASS / closed**。

`PlatformWorkerHost.archive_sdk` 以完整 Assignment identity 与 operation 派生稳定的 `maf-sdk:<digest>` publication。写入复用既有 `model_output` 能力和既有 `publication/publication_ref`，要求 artifact 已 sealed、provenance 为 `model_output`、agent run 与完整 RunIdentity 相同、writer subject 与当前 Host access 相同，并继承实际 access level。既有 `artifact_retained()` 把任何 publication ref 视为持久保留依据，因此 SDK NDJSON 不再只依赖五分钟 staging lease。

结果 publication `result:<submission_id>` 由原 P04 `ResultCommitter.receive` 先固定 raw artifact，再追加同一 SDK ref 和 canonical binding ref。既有 SQL 显示该 publication 恰有三项 sealed ref：`text/plain` raw、`application/x-ndjson` SDK archive、`application/vnd.wuji.maf-result-binding+json` binding，均属于 `run-fixture/run-worker-fixture` 且 access level 为 1。

Canonical binding 覆盖 submission/operation、完整 RunIdentity、raw ref/digest/size、SDK ref/digest/size，以及 ContextBundle 的 snapshot、input digest、完整 text digest、read set、record refs 和 relations digest；工具部分重新从 P06 ledger 读取真实 receipt，要求 complete、同 Run、无重复，并固定 ToolCall/operation/attempt、receipt digest、Observation、artifact refs 和 result ref。已有 submission 的 replay 在 P04 lookup 前比较原 envelope、SDK bytes 和完整 canonical binding；SDK、tool receipts 或 ContextBundle 任一变化都会 `INPUT_DIGEST_CONFLICT`。

Binding 只承担输入等价检查。首次结果仍依次调用 P04 `receive` 与 `reconcile`，相同 replay 返回 P04 `lookup` 的原 receipt；最终 Claim/Intent 接纳、result receipt 和幂等权威仍是 P04，没有第二套结果写入或第二结果权威。既有摘要显示 replay 后仍只有 1 个 result submission、1 个 result receipt、1 个 Claim revision 和 1 个 Observation；2 次模型请求及 1 次业务工具请求未增加。

- 完整 SQL：[postgres-events.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/0b3a90d78c4d/postgres-events.jsonl)
- 结果与 replay 计数：[m1-result-summary.json](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/0b3a90d78c4d/m1-result-summary.json)
- 接口与资产状态：[interface-inventory.md](../../../docs/vnext/evidence/P07/M1/review-fixes/interface-inventory.md)

Remaining：无。

## 修复直接影响

正常同源实际 SDK 正例没有被削弱：已有实物仍包含两次真实模型 Gate/upstream 往返、一次真实函数 ToolGate 调用、固定文件字节形成的 Observation/EvidenceReceipt、Agent Claim 和 P04 accepted result。撤销路径仍为模型与工具 409 `STALE_EXECUTION`，且不会新增 upstream/model/tool attempt；本复审只读取该既有请求包，没有重跑。

P10 的真实 Host transport 可以依赖本报告关闭的 M1 最终接口；这只确认上述接口前提，不把 P10、Supervisor 或完整 P07 纳入本次通过范围。

修复没有修改旧 migration/schema，也没有增加 Grant、角色或 capability。新增持久关联复用既有 publication、artifact retention 与 `model_output` 权限路径。未发现新资产或接口；现有资产状态已记录在上述 interface inventory，无需另行扩大资产清单。

- 撤销完整 Gate 请求/响应：[platform-gate-http.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/f0b4d1a67bd8/platform-gate-http.jsonl)
- 撤销完整 upstream 记录：[model-upstream-http.jsonl](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/f0b4d1a67bd8/model-upstream-http.jsonl)
- 撤销摘要：[m1-revocation-summary.json](../../../docs/vnext/evidence/P07/M1/review-fixes/final-code-sha/raw/f0b4d1a67bd8/m1-revocation-summary.json)

## 证据截图

![P07 M1 review fixes](../../../docs/vnext/evidence/P07/M1/review-fixes/screenshots/m1-review-fixes.png)

## 范围边界

恢复、MCP、Supervisor/process truth、Scheduler、持久 delivery、Task completion、Kubernetes/Pod、完整 P07 及真实收费模型效果均不在本次 scope。本 PASS 只关闭原报告的三项 finding，不提升完整 P07 或其他里程碑状态。
