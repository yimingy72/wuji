# P08 平台授权、恢复与原子性独立静态审查

归档日期：2026-09-13（Asia/Shanghai）。归档类型：`derived-static-review`。源审查文档 SHA-256：`c129742c4633e945eb3b183ac950a82c102de745683c7ce5c809303f6a72c7cd`；固定源码 `sourceSHA`：`a75584777af917d269480f48af97a696ecb0a821`。

**结论：CHANGES REQUIRED，P1 × 4、P2 × 2。**六项均已通知负责集成的线程并获采纳，交由 Dewey 在 `vnext_0014_p08_session_approval` 集成时精确修复。本归档只调整永久位置、相对文档链接和来源标记，没有改变原审查结论。

本审查者是直接派出的独立 SOL/xhigh reviewer，不是主代理或当前控制器；没有创建子代理。审查仅使用源码和既有文档/证据，不运行 pytest、数据库、HTTP、SDK、formatter 或 browser。既有 4+1 Worker unit 由 Dewey 执行，不是本审查者的测试，也不能证明平台 publication、PG trigger、跨进程恢复或审批事务通过。

## 固定范围与依据

- 平台核心固定为 `a75584777af917d269480f48af97a696ecb0a821`。主审文件为 `contracts/sessions.py`、`execution/{sessions,inputs,approvals}.py`、`execution/session_schema_draft.sql`，并定向读取该提交的 `control.py::_recoverable`、`admission/{tools,ledger}.py` P08 变更及 P09 `session_holder`/lineage 消费者。
- `069b242` 的 M2 receiver/results 接缝与 `750277c` 的 model-output credential/JTI 锁只用于理解相邻真实原语；没有把它们冒充 a755 的运行证据，也没有建议削弱其 receiver settlement、historical-only 或精确 credential 约束。
- 权威依据为 [P08 实施合同](../../../P08-implementation-contract.md)、[vNext Spec S09](../../../SPEC.md#S09)、[vNext Plan P08](../../../PLAN.md)、[验收 AC-023/035/038–043/066](../../../ACCEPTANCE.md)、[阶段 Spec](../../../../stages/vnext-maf/spec.md)、[阶段 Plan](../../../../stages/vnext-maf/plan.md)、[阶段 Acceptance](../../../../stages/vnext-maf/acceptance.md)及 [P08 evidence index](../README.md)。工作树无 `.codegraph/`，审查使用固定提交的 `git show`、`git diff`、`git grep` 与 `rg`。
- D12/candidate、B2、0014 在途或当前 dirty 字节均未进入固定结论。以下均为**静态可触发路径推断，未做数据库或 SDK 实测**。

## Findings

### F1 · P1：批准消费所需状态转换被 0009 trigger 拒绝，批准执行路径不可达

**文件/函数：**`execution/approvals.py::ApprovalService.bind_operation_in_transaction()`（a755 约 137–167 行）；`admission/tools.py::ToolAdmission.authorize()` / `authorize_in_transaction()` / `_new_attempt()`（约 136–149、196–242 行）；`persistence/admission_request_guard_schema.py::guard_tool_call_purpose()`（约 367–419 行）。

**触发：**合法 approval 已为 `decided/approve`，恢复 Run 持有精确 holder，并以原 approval_ref 调用 ToolAdmission。bind 先执行 `tool_call: pending_approval -> admitted`，此时 `latest_attempt_id` 仍为 NULL；0009 trigger 没有允许这条批准转换，因而抛出 `tool request transition is not registered`。

**影响：**事务在唯一 ToolAttempt、资源占用、Outbox 和 approval consumed 前回滚；真实批准不能进入一次工具执行，AC-040/041 正向闭环不可达。

**最小修复方向：**0014 只增加严格的批准转换：同事务必须存在固定 `decided/approve` approval，且原 ToolCall、参数和 Session holder 绑定成立；保留 0009 其他 purpose、字段和状态限制。继续用 deferred constraint 保证 Approval、唯一 Attempt 与对应 Outbox 同一提交。尚无 DB 实测关闭证据。

### F2 · P1：拒绝后的 `function_result` 只按 call_id 认定，任意成功内容可冒充原生拒绝

**文件/函数：**`execution/sessions.py::SessionRepository._frontier()`（a755 约 468–504 行）；相关根合同为 `contracts/sessions.py::OperationFrontier` / `NativeCallBinding`。

**触发：**approval 已真实决定 `reject`，ToolCall 无 ToolAttempt。边界生产者在 history 放入任意 `type=function_result` 且 `call_id` 等于原 provider call_id 的内容，并让 provider Session state 使用同一 history。当前分支不检查结果正文、位置摘要、approval_ref、decision_version 或实际原生拒绝响应。

**影响：**未执行工具可在可恢复 Session 中呈现为成功或任意结果，后继模型也可接收该伪结果；P06 账本虽无 ToolAttempt，Session/frontier 却错误承认拒绝语义完成。

**最小修复方向：**受 pin 根固定 rejection 的 approval_ref、decision_version、原 call binding、唯一结果位置和摘要；`_frontier()` 对照持久 approval/input_delivery 与真实 SDK 验证过的原生拒绝序列化。不得接受 arbitrary-success self-hash，也不得为拒绝伪造 ToolAttempt/EvidenceReceipt。尚无 SDK/DB 实测关闭证据。

### F3 · P1：observe authority 可在 INSERT 时伪造 resolved/approved 初始状态并绕过 approver

**文件/函数：**`execution/session_schema_draft.sql` 的 `input_request`/`approval_request` 定义、`guard_approval_update()`、`guard_input_revoke()` 与 INSERT policy/grant（约 220–245 行）；消费点为 `execution/approvals.py::bind_operation_in_transaction()`（a755 约 137–167 行）。

**触发：**若 draft 原样集成，持有 application role、`can_observe` 和 controller/reconciler observe 身份的 receiver 可整行 INSERT。UPDATE trigger 不处理 INSERT，表 CHECK 也不要求初始 pending/version 1/空决定字段；该 authority 可直接插入 `input_request.status='resolved'` 与 `approval_request.decision_status='decided', decision='approve'`，并自选 qualifications/decided_by。后续合法 Worker 会把它视为可消费批准。

**影响：**receiver 的可信 intake 权限升级为决定权限，绕过 control capability、真实 approver 资格和原生决策来源，可产生实际 ToolAttempt。缺陷属于 draft 已写出的授权策略；“0014 尚未执行”本身不是 Finding，也未被描述成已部署漏洞。

**最小修复方向：**加入不可绕过的数据库初始状态和来源守卫：input 只能初始 pending；approval 只能 version 1/pending，decision、decided_*、consumed_* 必须为空；qualifications、call/参数/tool/scope/profile/session 绑定已发布 frontier 与部署 capability。可采用列级 INSERT/default、严格 BEFORE INSERT 或受限 intake 函数，不能只依赖 Python。保留 receiver 生成可信 source receipt 的权限。尚无 DB 实测关闭证据。

### F4 · P1：完整引用图只在高权限 receiver 下读取，形成 source Worker ACL confused deputy

**文件/函数：**`execution/sessions.py::stage_objects()`、`_graph()`、`publish()`（a755 约 263–380、510–563、629–702 行）；caller 引用合同为 `contracts/sessions.py::SessionRoot`、`BoundaryObject`、`MemoryFile` / `MemoryManifestRoot`。

**触发：**`stage_objects()` 在源 Worker 权限下核对 ledger、archives 和本次生成对象，却没有按 Worker 当前 ACL 遍历全部 caller-supplied history/provider/memory refs、MemoryFile.ref/state_refs 与 BoundaryObject.object_refs。完整 `_graph()` 到 receiver 的 observe publish 事务才执行。若 receiver clearance 更高，Worker 掌握一个当前不可读的高等级 BlobRef 后，可借 receiver 读取并 pin 入 Session publication。

**影响：**最终 publication level 取最大值避免立即降级返回字节，但不能证明源 Worker 有读权；未经源权限授权的对象已被错误关联并保留。安全性不能依赖 ref/sha 不可猜。

**最小修复方向：**stage 完整图时先在源 Worker 当前 ACL/JTI 下遍历并固定每个新引用的可读性、摘要、来源、role 与 access level；receiver CAS publication 再重验同一固定图。`max(access_level)` 只能防降级，不能替代源读权。已发布同 Session 祖先继续按不可变 publication 和当前 holder 处理。尚无 DB 实测关闭证据。

### F5 · P2：后继 model request 未与实际 history 前缀绑定，可拼接错误因果链

**文件/函数：**`contracts/sessions.py::ModelFrontierEntry`（a755 约 75–80 行）；`execution/sessions.py::_model()` / `_frontier()`（约 159–182、402–467 行）。

**触发：**工具完成后，model attempt B 的真实 P06 `request_json` 遗漏或替换该 ToolReceipt；边界生产者另构造含真实 ToolReceipt 与 B 响应的 history/provider state。`_model()` 只验证 request_json 自身摘要，`_frontier()` 只证明 B 响应位于 history、ToolReceipt 位于某个 function_result，没有证明 B 的真实请求 messages 等于对应 history 前缀并包含前驱结果。

**影响：**publication 可错误宣称后继模型实际见过某项操作结果，恢复后的上下文来源和动作顺序不真实；它不单独绕过 P06 当前 Scope/额度准入，因此定为 P2。

**最小修复方向：**以 P06 保存的 request_json 为权威，为每个 model attempt 固定并校验原生请求消息映射/前缀摘要和前驱 operation positions，验证顺序与唯一配对；不能接受 Worker 自报同值 self-hash。可放入受 pin 内部根，无需扩外部 SessionManifest。尚无 SDK/DB 实测关闭证据。

### F6 · P2：同 Run 嵌套 model-output 不要求 `session_object`/source JTI/role，来源边界可被替换

**文件/函数：**`execution/sessions.py::_graph()` / `publish()` / `require_current_root_writer()`（a755 约 510–563、620–688 行）；`execution/session_schema_draft.sql::guard_session_object()`（约 107–119 行）；相邻原语为 `750277c` 的 `UnitOfWork._model_output_binding()` 与 M2 retained-result receiver writer。

**触发：**顶层三根在 publish 时匹配 `session_object`、credential 和 run_writer；但 `_graph()` 对 `record.agent_run_id == owner_run_id` 的嵌套引用直接放行，不要求匹配 `session_object` 元数据、允许 role 或 writer_token_id。同一 AgentRun 下其他合法 writer（包括 M2 receiver settlement writer）产生的可见 model-output 可被引用并作为新 Session 状态依赖 pin 入。

**影响：**`750277c` 保证 Worker 自身新增 model-output 使用精确当前 JTI，却没有证明安装到 Session 图中的全部新 model-output 都来自该 Session 源 writer。F4 检查 visibility；F6 检查可见对象的 producer/JTI/role provenance。

**最小修复方向：**图遍历按用途分类。本次新增 Session model-output 必须匹配 `session_object`、允许 role、owner Run 和发布时仍有效的源 writer JTI；P03 ToolAttempt evidence 继续按真实 receipt 证明。已发布同 Session 祖先在旧 Run 退出、旧 JTI 撤销后，依靠不可变 publication、摘要和当前新 holder 授权恢复，**不得要求旧 JTI 永久有效，也不得禁止跨进程恢复**。保留 M2 receiver historical-only/受限补交原语，但其字节不能未经 Session 来源证明安装成新恢复状态。尚无 DB 实测关闭证据。

## 其余定向判断

| 关注点 | 固定源码静态结论 |
| --- | --- |
| publication、root 与 nested pins | 三根及 `session_object.refs_json` 递归图由 `_graph()` 有界遍历；publish 把到达对象写入 `publication_ref`，load 要求每个到达对象有同 publication pin。publication、pins、manifest 与 Work 指针同事务。完整性受 F4/F6 限制。 |
| CAS 与单写者 | publish 锁 Work，核对存储 Assignment、当前 Run/run_epoch、Task execution/runtime epoch、process truth、前一 revision 与 manifest digest；同 revision 同内容仅返回旧 receipt，不同内容、旧 writer 或第二 writer 被拒绝。未发现 root-only/CAS 旁路。 |
| operation frontier 与 unknown | `_frontier()` 对比同 Work 全部 model_call、tool_attempt、tool_call；model response 必须 complete，ToolAttempt 必须 complete 且有 accepted EvidenceReceipt，未结算/unknown/漏项阻断。P06 异步 billing pending 是既定独立费用轴。F2/F5 是剩余内容和因果缺口。 |
| approval 来源与原子性 | pending Content、SDK occurrence id、provider call_id、model attempt、消息位置、arguments bytes/digest、ToolDefinition、ToolCall、Session/Work/checkpoint 均交叉核对；决定和消费重验当前权限。应用层把 bind、Attempt/资源、Outbox 与 consumed 放在同一事务，deferred constraint 再检查；F1 使正向路径当前不可达，不能宣称 AC-041 通过。 |
| hold / pause / cancel / scope revoke | `current_run()`、Approval `_current()`、Control `_restore()` 与 scheduler `can_dispatch()` 重验 Task/Work desired state、suspension causes、epoch、input、授权期限和依赖。Task resume 只移除 task_pause，Work resume 只移除自身 user_hold；取消、scope revoke 或 pending input 不自动复活。未发现新的 P1/P2。 |
| current ACL 与 P09 lineage | load/recovery 按当前 task access、clearance、capability revocation、artifact level 和 pin 重读；P09 在同一锁定事务读取精确 Session、插 holder，并为新 Run 签发独立 subject/JTI/epoch credential，同时继承原 lineage。恢复不复用旧 Worker token。除 F4 外未发现新 P1/P2。 |
| M2 receiver 补交 | `069b242`/`750277c` 的 receiver-bound retained result 与 source credential 锁保持原边界；撤销后字节仍可 historical-only 保存。F6 只限制未经证明安装为新 Session 状态。 |

## 已知但不计为新缺陷

- `vnext_0014_p08_session_approval` 尚未执行/集成，完整 PostgreSQL、SDK、HTTP 与进程验收未运行；这些是既知状态，不重复列为 bug。
- B2 transport/OpenAPI 正由 Bacon 实施；未来路由齐备度不进入固定 a755 结论。
- D12 首次 `mechanism_candidate` bootstrap 由 Dewey 实现。候选不是 prior PASS，首次证据可为空；不要求新增用户 approval，也不纳入当前 dirty 字节。
- 记忆采用已裁定的固定 ContextProvider/AgentFileStore 输入且 Harness FileMemoryProvider 关闭，不自动学习；这不是缺失。
- Worker 原生适配由 Dewey 做真实测试；本审查没有扩成完整 native SDK review，也没有把其 4+1 unit 冒称本轮执行。
- 未重复评审 P03/P04 全库，也未建议削弱 P03 immutable artifact/publication、P06 purpose/ledger、P09 holder/credential 或 M2 receiver 原语。

## 证据与验收边界

本轮没有运行测试、数据库、HTTP、SDK 或浏览器，因此没有新的运行截图或完整 HTTP 请求包可附；伪造截图或报文会违反 source-only 约束。[P08 evidence index](../README.md)同样明确：现有内容不证明 Session publication、CAS、跨进程恢复、approval consumption、ToolGate 或 PG trigger。六项 Finding 需在修复后生成独立 RED/GREEN 与 0014 数据库证据；本报告不能把源码存在性升级为 P08、G2、SDK 或数据库验收通过。

**最终固定判断：CHANGES REQUIRED（P1 × 4，P2 × 2）。**除六项与上述既有未集成边界外，本次限定的 authority 源码切面没有发现新的 P1/P2；这是 `sourceSHA=a75584777af917d269480f48af97a696ecb0a821` 的静态结论，不是 P08 或完整 M3 验收。
