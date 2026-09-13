# P08 平台原六项问题定向复审 — SOURCE_ONLY

归档日期：2026-09-13。类型：`derived-static-rereview`；固定源码 `sourceSHA=f4c3b761f4c829cd0bd28cc71425ec000a798c31`。源文档：`.superpowers/sdd/vnext-v2/P08-platform-rereview.md`，源字节 SHA-256：`f254b5e55f14b62760fa93cdff0d5bc5cb285db795b58b690e6d60c2de607e5a`。永久副本保留原文结论，仅增加本来源说明并调整相对链接；下文“本轮”指原源码复审，归档另行 docs-only 提交，没有新增运行验证。

2026-09-13。**源码结论：CHANGES REQUIRED。原 F1、F6 的具体缺口 source-addressed；原 F2、F3、F4、F5 未关闭，残留 P1 × 3、P2 × 1。实际验收：pending。**不增加原六项以外的审查范围，不将本次判断写成完整 P08、G2 或 SDK/数据库通过。

原源码：`a75584777af917d269480f48af97a696ecb0a821`。原审永久归档提交：`47c278140c8129da8b9db3a67ceb139e11688293`，见[原六项报告](P08-platform-review.md)。本次修复源码固定为 **`f4c3b761f4c829cd0bd28cc71425ec000a798c31`**。以下源码行号全部对应此固定提交，不对应后续 dirty 文件。

角色为直接受派的独立 P08 reviewer；未创建子代理。只读取上述固定提交、相关既有合同、源码消费者及保存的证据。未运行 pytest、sourcechecks、DB/DDL、SDK、HTTP、浏览器、截图、formatter 或其他新验证命令；未修改生产、测试、Git index 或提交。本文为本轮唯一写入。

收口时 main 已明确采纳 F2/F3/F4/F5 四项残留并交 Dewey。M2 窗口解冻只影响修复排期，不改变本文固定 `f4c3b76` 的结论；本报告不审查或继承 M2 onecase 的运行结果。

## 六项状态

| 原问题 | 本次源码判断 | 实际证据状态 |
| --- | --- | --- |
| F1 / P1：0009 拒绝批准转换 | source-addressed：0014 已增加精确 `approval_admit` 边，原有转换保留 | 仅已有源码字符串检查；真实 trigger/RLS/事务回滚与唯一 Attempt/Outbox 待测 |
| F2 / P1：拒绝结果可冒充成功 | 部分处理但未关闭：canonical 内容、持久决定与 delivery 核对已加；重新封存改变原 binding 引用，合法拒绝边界失败 | 既有 noDB 类型/内容检查不覆盖 `stage_objects → _frontier`；真实 SDK/DB 待测 |
| F3 / P1：INSERT 伪初态和资格来源 | 初始 pending/version 1/空决定字段 source-addressed；完整 capability/资格来源仍未绑定 | 既有 DDL 源码检查不证明非 owner INSERT/资格负例通过 |
| F4 / P1：高权限 receiver 代源 Worker 读图 | stage 已增加源 Worker 图校验；publish 未重验源当前 ACL，未关闭 | F4 无真实图/ACL 验证；DB/RLS 待测 |
| F5 / P2：后继请求因果链可伪造 | 保存了真实 P06 request messages；校验仍是部分位置映射与跨请求并集，未关闭 | 既有 helper 正负数据读取不覆盖整个 `_frontier` 的逐请求因果合同 |
| F6 / P2：同 Run 嵌套对象无来源证明 | 原“无 session_object/role/JTI 直接放行”旁路 source-addressed；已发布同 Session 祖先仍允许旧 JTI 失效 | F6 无真实图/JTI 负例；不是整个 graph SOURCE_PASS，F4 仍开放 |

## 残留

### F2 · P1：重新生成 response/arguments 引用与持久原决定 binding 冲突

**文件/函数：**`packages/wuji-core/src/wuji_core/execution/sessions.py::stage_objects()` 415–462、`_frontier()` 619–665；直接消费者 `packages/maf-worker/src/wuji_maf_worker/sessions.py::_rejected_entry()` / `NativeSessionAdapter._frontier()`、`runtime.py` 289–350。

**已处理部分：**`contracts/sessions.py` 21–41 固定 core 1.18.0 的原生拒绝 Content：包括 `result`、`items` 和 `additional_properties`，而不是对任意内容自算 hash。已保存 P01 `capability-record.json` 中 `raw_sdk_and_http.cases.reject.processes[1].result.session_after.state.in_memory.messages` 的 tool Content 与此形状一致；本轮只读取这段公开拒绝结果，没有执行 SDK。新增 rejection frontier 保存 approval_ref、decision_version、call_binding、result_position/content/digest；平台还核对持久 approval、resolved input、delivered delivery 和 receiving holder。

**触发：**从批准边界恢复并真实拒绝，原 approval/delivery 保存的 binding 引用 response 对象 R1 和 arguments 对象 A1。新 `stage_objects()` 为旧 model response 再次 `save`（422 行），为原参数再次 `save`（437 行），产生 R2/A2；445–462 行将 rejection 的 call_binding 替换为 enriched binding。随后 `_frontier()` 658–659 行又要求该 binding 与原 delivery 中的 binding、`approval_request.binding_json` 全部相等。R2/A2 与 R1/A1 的 BlobRef id 不同，即使原始字节、call 身份、结果完全正确也无法相等。

**影响：**合法拒绝后的 Session 无法再次 stage/publish；普通跨 Run 拒绝闭环被源码层的引用替换阻断。新 canonical 检查不应移除，但此候选不能把 F2 关闭。

**最小方向：**将原批准 checkpoint 的 immutable binding/ref 与当前 history 中重定位的调用/结果位置分开；保留原批准引用或通过同 Session 已发布祖先证明复用。继续对照持久 decision/delivery，不改写旧 approval，不删完整来源比较，不伪造 ToolAttempt。main 已确认该残留并交 Dewey。

### F3 · P1：qualifications 可以取自同 profile 的另一完整 capability

**文件/函数：**`packages/wuji-core/src/wuji_core/execution/session_schema_draft.sql::guard_approval_intake_insert()` 154–177、`check_approval_intake_source()` 182–192；消费点 `execution/approvals.py::_current()` 44–55、`decide()` 83–85；配置读取对照 `admission/registry.py::session_capability()` 436–495。

**已处理部分：**`guard_input_intake_insert()` 108–122 和 `guard_approval_intake_insert()` 124–138 在非 owner INSERT 时强制 pending，approval version=1 且决定/消费字段为空，原直接插入 decided/resolved 的漏洞在源码层已封。deferred guard 要求提交时存在同 input/manifest 的 source receipt 并列出 approval_ref。

**触发：**同 tenant 有两份合法 capability A/B，使用相同 Harness profile，但 client/runtime 组合及 approver_subjects 不同；当前 Task/Session 固定选择 A。SQL 154–157 只按 tenant、NEW.profile_digest 与 NEW.qualifications_json 匹配 capability，不核对已发布 Session 根固定的 capability_ref/digest、client/runtime。observe intake 可沿用真实原 call、binding、scope、同一 profile_digest，却填入 B 的资格列表，并插入列出此 approval_ref 的 source receipt。具备该 Task read/control、属于 B 而不属于 A 资格列表的 operator 随后执行正常 `decide()`；`_current()` 核对的是原 manifest/profile/tool/binding，`decide()` 只查已存 qualifications，因此不能排除这一替换。

**影响：**初始状态守卫不再允许直接伪造 approve，但 receiver 仍能改变这次调用允许谁审批，原 F3 的资格来源边界未闭合。此例不要求创建虚假的 capability，也不涉及 D12 首次 bootstrap。

**最小方向：**在数据库 intake/source guard 中把资格唯一派生到该 publication 实际选中的完整 capability identity/digest/client/runtime 与原 frontier。source receipt 仅列出 approval_ref 不足以证明选择了正确 capability。不得以任意同 profile 的其他 record 替代；保留初态与 deferred 同事务约束。main 已确认该残留并交 Dewey。

### F4 · P1：stage 后源 ACL 失效，receiver 仍可发布该图

**文件/函数：**`packages/wuji-core/src/wuji_core/execution/sessions.py::stage_objects()` 488–505、`publish()` 880–929、`_graph()` 715–804。

**已处理部分：**stage 491–502 现在以真实 Worker `tool_request` 事务遍历三根递归图，传入源 subject/token_id，使用源 clearance；原“只在 receiver 下第一次检查图”已部分改进。

**触发：**stage 成功后、publish 前，源 Worker 的 can_read 被撤销或 clearance 被降低；其 Run credential/JTI 与 run_writer 尚未撤销，receiver 当前权限仍高。已持有固定 manifest 的发布调用进入 receiver observe 事务：publish 只核对 receiver、当前 Work/Run 及 writer/JTI，909–910 的 `_graph()` 未传源 subject/token_id，也没有读取源 `task_access`。对象读取和最终 max(level) 继续使用 receiver 权限，因此源当前已无读权的图仍可被 pin/发布。

根与 session_object 元数据还在 stage 最后图校验之前分事务落盘；publish 没有必须消费的、绑定该完整图的 stage 成功证明。因此新增一次 stage 校验本身不是 publication authority 的充分条件。上述 ACL 撤销例以一次成功 stage 为前提，不依赖从失败响应猜出新 UUID。

**影响：**F4 的源 current ACL 与 receiver confused-deputy 边界仍未关闭；publication level 取最大值只能防止降级读出，不能替代源授权。

**最小方向：**在 publication 事务内通过受限平台原语重验精确源 Worker 当前 ACL/JTI 及固定图；若采用 stage receipt，需绑定根、递归引用、源身份并在 publish 再验当前权限，而不是把旧 receipt 当永久许可。源新增写/发布需当前授权；已发布同 Session 祖先的旧 JTI 无需一直存活，恢复依靠不可变 publication 与当前新 holder。该残留已同时发送 main 与 Dewey。

### F5 · P2：任意后继请求见过结果即可补齐全局 coverage，逐请求因果仍可错配

**文件/函数：**`packages/wuji-core/src/wuji_core/execution/sessions.py::request_predecessor_positions()` 102–162、`_frontier()` 537–548、666–687；`contracts/sessions.py::ModelFrontierEntry` 97–105。

**已处理部分：**`_model()` 返回真实 P06 request_json；stage 424–434 将其 messages 与摘要纳入固定根；恢复时再次与账本请求逐字结构比较。工具调用和工具结果在该请求中存在时，helper 会核对对应内容及位置，且位置必须早于该模型响应。

**触发：**保存的 history 顺序为 `Q → A(call) → R(tool result) → B(text) → C(text)`。实际 B 的 P06 请求只有 Q，遗漏 R；实际 C 的请求含 Q/A/R。helper 只处理请求中已经存在的 `assistant.tool_calls` 和 role=tool 内容，B 的 predecessor_positions 为空，可以通过；C 提供 R 的位置。666–687 行把全部模型的 predecessor_positions 取并集，R 已在 C 中出现，故全局检查通过。于是原反例中“B 被放到 R 后，但 B 实际未见 R”仍能发布。

helper 也不映射普通 user/system/assistant 文本，并把匹配位置存成字典后排序；这并没有证明每次真实请求等于其对应的有序原生 history 前缀。

**影响：**已保存真实 request 并不自动意味着恢复 history 因果正确；一条更晚请求可掩盖较早请求遗漏前驱结果。保留原 F5 的 P2 级别，不推断其能绕过 P06 Scope/额度准入。

**最小方向：**以每个 model attempt 为单位，核对真实有序 request messages 与该次 history 前缀或已证明的原生 approval/compaction 映射；应见的前驱结果必须进入对应那次请求，不能靠任意后继请求并集补齐。避免实现另一套 SDK 历史算法，使用固定公开序列化的来源映射。该残留已同时发送 main 与 Dewey。

## F1 / F6 的限定 source-addressed 依据

F1：0014 draft 251–350 现在保留原 0009 的 attach、dispatched、cancel_intent、safe_retry 及 tool_settle 分支，新增的 approval_admit 只允许 pending_approval、无 Attempt 到 admitted、仍无 Attempt，并要求除 status 外整行不变；同时核对 approve/decided、期限、原 call/参数/SDK 身份、holder、当前 Run/epoch 和未撤销 credential。原缺失状态边已补齐；352–374 的 deferred Approval/ToolCall/Attempt/Outbox 约束仍存在。此结论只关闭原 F1 的源码缺边，F3 的来源残留和实际 DB trigger/RLS/原子性仍需分别处理。

F6：`_graph()` 750–794 不再因 artifact.agent_run_id 等于当前 Run 就跳过验证。除已发布同 Session/Work 祖先与同 Work ToolAttempt evidence 外，新 model-output 必须存在 session_object，匹配 owner Run、允许 role、access level，以及未撤销、未过期的 credential/run_writer；Worker stage 还显式传入精确源 subject/JTI。原“缺 session_object 或只有 receiver 结果 writer 也可作为新 Session 依赖”的具体旁路已封。祖先分支先核对同 Session publication pin，不对其旧 writer JTI 要求永久有效；load 的 publication 分支仍逐对象查 pin。此为来源缺口的局部源码处理结论，不替代 F4 的发布时源 ACL，也不证明真实 GC/RLS/JTI 竞态已通过。

## 已有证据与后续终判

已读取 [Dewey SOURCE_ONLY 修复说明](../review-fixes/README.md)及 [binding.json](../review-fixes/binding.json)。其中记录 F1/F2/F3/F5 既有 noDB source batch 为 `3 passed in 0.80s`，包含 DDL 源码字符串检查、拒绝 Content/类型路径与 P06 请求 helper。它不是本审查者执行，也不验证实际 PostgreSQL trigger/RLS、`stage_objects → publish`、完整 SDK 或跨进程链。F4/F6 没有真实 graph/ACL/JTI 检查；上述运行项保持 pending/not_run，不制造截图或 HTTP 报文。

本轮按 `f4c3b76` 八个 owned 文件及必要原消费者追踪，未将 M2 `worker_host.py`、0013 current-intake 的独立修复或后续 dirty 变更纳入结论；没有重复评审 P03/P04 或扩展 native SDK。D12 初次候选、B2 集成、只读 memory 裁定与既知未测试状态均不另计 Finding。

后续固定修复候选只复审 F2/F3/F4/F5 变化及直接受影响接口；F1/F6 未变源码复用本轮 source-addressed 依据。待固定真实 DB/SDK/跨进程证据齐备后，再按实际结果更新验收终判，不重复未改源码，也不因已有 sourcechecks 自动关闭运行验收。
