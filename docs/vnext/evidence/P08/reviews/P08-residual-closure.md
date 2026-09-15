# P08 四项残留（F2–F5）现状核对 — 2026-09-15

- 状态：**source + 运行证据核对完成**；四项残留均已在当前源码中关闭，并有直接测试。
- 被核对的复审：[P08 平台定向复审](P08-platform-rereview.md)（固定源码 `f4c3b761f4c829cd0bd28cc71425ec000a798c31`，结论 F2/F3/F4 = P1、F5 = P2）。
- 本轮核对源码：`cc65fef` 工作树（`codex/vnext-maf`）。
- 运行证据：真实隔离 PostgreSQL 的 `tests/vnext/test_session_approval.py`、
  `test_session_permissions.py`、`test_maf_runtime.py`、`test_maf_child_transport.py`；
  本轮完整可运行集合 **405 passed / 0 failed**（原始输出 `work/vnext/p08s/related-suite-final3.txt`）。
- 范围：只关闭该复审的四项残留与本次顺带修掉的两个缺陷。**不**宣称完整 P08 验收；固定记忆、原生
  compaction 的真实 child 验证（A3）与 GC/半发布等更宽边界仍按原状态另行处理。

## F2 — 冷恢复后拒绝决定与前沿绑定（P1）

原问题：`stage_objects` 对旧 model response / native_arguments 重新 `save`，产生新 `BlobRef` UUID；
随后又把 `rejected_calls.call_binding` 换成 enriched 版本，而 `_frontier` 要求它与持久
`input_delivery.decisions[].call_binding`、`approval_request.binding_json` 完全相等，于是正常冷恢复
稳定报 `SESSION_FRONTIER_MISMATCH`。

现状（已修）：

- `packages/wuji-core/src/wuji_core/execution/sessions.py:574` — `if entry.response_ref is not None:`
  直接复用已发布祖先的 `response_ref`（并记录进 `reused_refs`），不再重建 UUID；`native_arguments`
  同理使用 `call.arguments_ref`（`sessions.py:600` 起）。
- `sessions.py:637` — `if not equal(enriched, entry.call_binding): raise DomainError("SESSION_FRONTIER_MISMATCH", 409)`，
  即 enriched 绑定必须与持久拒绝决定逐字节一致，任何"新 refs"都会被拒绝而不是静默写入。

覆盖：`tests/vnext/test_session_approval.py`（20 passed，含 `test_restored_approved_callback_uses_original_lineage_attempt_and_approval_ref`、
拒绝结果接纳与前沿测试）；`tests/vnext/test_session_permissions.py::test_publish_rechecks_source_access_after_real_stage`
用真实 `load_published` + `stage_objects` 走重复用路径。

## F3 — 批准资格必须绑定到该 publication 实际选中的 capability（P1）

原问题：资格来源只按 `tenant + profile_digest + qualifications_json` 匹配，同 profile 不同
client/runtime（approver 集合不同）的合法 A/B 能力会互相串用，B 专属 operator 可越过 A 资格。

现状（已修）：

- `packages/wuji-core/src/wuji_core/execution/session_schema_draft.sql:148` `guard_approval_intake_insert()`：
  `session_manifest` 按 `(session_id, revision, work_item_id, manifest_ref)` 精确定位后，
  `session_schema_draft.sql:178` 起要求
  `vnext.session_capability.ref = manifest.capability_ref AND digest = manifest.capability_digest AND profile_digest = NEW.profile_digest AND document_json->>'profile_digest' = NEW.profile_digest AND document_json->'approver_subjects' = NEW.qualifications_json::jsonb`，
  即钉到该 publication 实际选中的完整 capability 身份/摘要与 approver 集合。
- 可信来源仍由 `check_approval_intake_source()`（`session_schema_draft.sql:207`）以同一
  `(input_request_id, manifest_ref)` 的 `input_source.receipt_json.approval_refs` 延迟约束。

覆盖：`tests/vnext/test_session_permissions.py::test_receiver_cannot_apply_other_capability_qualifications_to_published_session`
断言同 profile_digest 的 B 资格被 `guard_approval_intake_insert` 以 `42501` 拒绝（并检查 `diag.context`），
而 A 资格路径通过；同时断言批准行与 publication 状态未被改动。

## F4 — publish 必须重验**当前**源 Worker ACL/JTI 与完整 stage 证明（P1）

原问题：stage 成功后若源 Worker 的 `can_read`/clearance 被撤销或降低，receiver 仍可仅凭自身权限
pin 并发布源已无读权的全图；失败 stage 留下的根也没有 published 端必需的 stage 证明。

现状（已修）：`session_schema_draft.sql:269` `check_session_stage_for_publish()` 在发布事务内 JOIN
**当前** `task_access`（`source_acl.can_read` 且 `clearance >= stage.graph_access_level`）、**当前**
`run_credential`（未撤销、未过期）与 `run_writer`（未撤销），并要求已注册且 enabled 的 receiver 与
精确 `session_stage` 全字段匹配；`record_session_stage()`（同文件 219 起）在建 stage 时同样要求
当前 credential/writer/ACL 与三根对象。

覆盖：`test_session_permissions.py::test_publish_rechecks_source_access_after_real_stage[revoke_read|lower_clearance]`
——真实 stage 提交后撤销/降低源权限，`publish` 被拒且 publication 状态不变；恢复 ACL 后同一请求成功。

## F5 — 每个 model attempt 必须绑定它自己的有序 request 前驱（P2）

原问题：只收集 request 中实际出现的 tool_calls/tool 消息位置，并用后续请求的并集覆盖，导致某个
attempt 的 request 缺少应见结果也能通过。

现状（已修）：`sessions.py:126` `request_predecessor_positions()` 对**每个** request 消息逐条解析期望
（assistant tool_calls / tool result / text），在 history 中要求唯一匹配；`sessions.py:202`
`if len(matches) != 1: raise DomainError("SESSION_FRONTIER_MISMATCH", 409)`，不再用全局并集兜底。
工具结果还会回查其原生 position（`result_position.message_index < len(history.messages) - 1`）。

覆盖：`tests/vnext/test_session_approval.py::test_p06_request_messages_bind_tool_result_to_earlier_native_position`
使用 P01 capability record 的真实 restore HTTP 请求：正确 instructions 下映射到 `text/function_call/function_result`；
缺少 instructions 或 instructions 字节不符时 fail closed；去掉 tool 消息后不再产生 `function_result` 位置。

## 本轮同时修复的两个缺陷

1. **恢复的批准回调无法证明原始批准身份**（`packages/maf-worker/src/wuji_maf_worker/tools.py`）：
   Host 恢复路径不带 SDK 私有的 `_approval_request_id`，导致所有恢复后的 approve 直接失败。现在私有键
   存在时必须等于 `pending.id`，缺失时回落到公开原生批准 id 且同样必须相等；伪造私有键仍以
   `approval_request_id` 失败（`cc65fef` 之前的 `93f2fc6`）。
2. **等待输入恢复在无 SessionRepository 的 fixture 中恒为 reconciling**：P05 fixture 未按生产装配
   `SessionRepository`，`_recoverable()` 恒假。现在 fixture 按 `ops/vnext/deployment_common.py` 接线，
   并用生产 `inputs.save_delivery` 在 `capability="control"` 事务内解析等待输入（满足 0014
   `guard_input_revoke` 的"persisted decision"要求）。见 `docs/vnext/deferred-suite-failures-20260915.md`。

## 未覆盖

- 固定记忆与原生 compaction 的真实 child 往返（A3）仍按原记录另行验证。
- GC、跨进程半发布、Pod 级 stop/restart 与其余 work kind 不在本次核对范围；P08 仍非完整 accepted。
