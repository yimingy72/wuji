# P08 会话、原生审批与恢复实施合同

2026-09-13，主代理设计。状态：implementation-ready，尚无 P08 运行验收。依据已批准 Spec S08–S10、P08 Plan/AC-023/035/038–043/066、P05/P06/P07 实施合同与 D11。这里补齐已批准功能的生产接口，不修改导入源包或增加验收编号。

## 交付路径与归属

同一个已验证 MAF Worker 返回真实待批调用 → 固定完整 Session 边界并发布 → P05 收到真实输入和进程退出事实 → 人工决定持久化 → P09 为同 Work/Session 派发新 Run → 从已发布边界恢复原调用 → P06 当前准入、批准消费、原 ToolCall/新 ToolAttempt 与 Outbox 同事务 → 实际工具/证据 → 原生 SDK 后续响应。普通问题、拒绝、hold/pause/cancel 与未知状态保持各自语义。

核心实现可用 GPT-6/xhigh；首 RED、实际 SDK/数据库/进程测试、常规修复和复核均由 SOL/xhigh。核心先交精确接口，再等 SOL 首 RED 后写生产。当前 PG/平台 HTTP 窗口归 M2 Dirac；P08 不自行占用。共享迁移由主代理编号和分配，核心只准备无编号 schema draft。核心不能改正在由 Dirac 收口的 Worker bridge/transport 或 OpenAPI。

P08 核心目标文件为原 Plan 的 worker `sessions.py/history.py/approvals.py` 和 core `execution/inputs.py/approvals.py`；增加 core `execution/sessions.py`、内部 `contracts/sessions.py` 及无编号 `execution/session_schema_draft.sql`。必要的既有 runtime/factory/tools、P05/P06/P09 接缝逐项列入 handoff 后由主代理分配，不能靠测试夹具补齐生产缺口。最终必须在实际 hosted/child Worker 消费这些能力，不停在独立仓库 helper。

当前实施分为平台核心与原生 Worker 两个不重叠源码 lane：平台核心拥有内部合同、持久服务与 P05/P06/P09/Host 接缝；Worker 核心拥有原生适配及 runtime/factory/tools/entrypoint。迁移/UoW 与测试由指定 SOL 集成。2026-09-13 原预留但未执行的 P08 0013 顺延为 `vnext_0014_p08_session_approval`；0013 分配给 M2 `vnext_0013_receiver_results` 的受限补交修复，实际当前 head 仍以迁移运行证据为准。M2 bridge/Node 的修复归其原 SOL owner，共享端口通过主代理协调，不能并发改同一文件。

## 完整发布与单写者

沿用冻结的 `SessionManifest` wire 形状以及 P05 的 `session_manifest`、Work 当前 Session 引用。内部服务 `SessionRepository(uow, *, artifacts, registry)` 提供：

```python
publish(access, assignment, manifest, *, expected_revision) -> SessionReceipt
load_published(access, task_id, session_id, *, revision=None) -> PublishedSession
validate_recovery_in_transaction(tx, work, *, assignment=None) -> RecoveryCheck
```

`access` 来自真实签名身份；manifest、assignment 都不能提升权限。`expected_revision=0` 只用于首次发布，返回值至少含精确 manifest 引用、checkpoint revision、内容摘要与真实发布状态；内部类型不重复定义 OpenAPI DTO。`revision=None` 只在解析一次当前发布指针时使用，随后的对象加载始终按该固定版本。

先用 P03 真实 Run writer 保存不可变字节，再通过短事务检查身份、对象摘要、封存状态、同 Task 所有权和完整递归引用，最后 CAS 发布。固定顺序遵循现有容量池 → Task → Work/Session → 对象/资源顺序。所有被引用的 history/provider state/memory 对象与嵌套对象在同一 publication 中被 pin，提交租约沿用 P03；不伪造 ToolAttempt 或把框架状态标成目标 capture。未发布字节不构成恢复点，也不能通过 latest memory/path 渗入旧边界。

当前 Work 的实际 Run/run_epoch 是唯一可写者；CAS 校验 Session lineage、Work、前一 revision、固定 Profile/client/framework lock 与原生状态完整性。旧 Run、同 Session 第二写者、不同内容重放、跨 Work 引用都拒绝。已发布版本不可修改。受信 receiver 可保留撤销后的原始状态字节作历史，但不能将其安装为新可执行恢复点。读取和恢复均重验当前 ACL/clearance，公开报告不得暴露原始 prompt/私有推理/密钥。

## 原生对象与操作前沿

Worker 只使用已安装 MAF 的公开 Session/history/memory/approval/compaction 接口，不复制循环、压缩算法或 SDK 私有对象转换。P01 已证明 approval Content 的 `id` 等于嵌套 function_call 的 occurrence `id`，provider `call_id` 是另一身份；两者及完整 Content 都保存，不能只存 Session JSON 或一个 approve 布尔值。

三个根对象必须携带完整可验证边界：固定 history/message_end；公开 SDK Session/provider state、全部待批原生 Content、原消息与调用身份映射；版本化 memory manifest 及全部实际文件/状态引用。关闭文件记忆的 Profile 保存真实空 manifest；开启时使用公开存储接口，写入不可变版本，不读本机 home 或任意路径。嵌套引用与大小限制显式有界。Profile/client/framework 的实际快照与 lock 摘要纳入根对象，不能只按包名认兼容。

操作前沿保存在这些受 pin 的根对象中，不为字段名称扩展外部 SessionManifest：列出实际纳入原生 history 的 model_attempt、ToolCall/ToolAttempt/EvidenceReceipt 和原消息位置/摘要；待批未执行调用另行列出。平台用持久准入/结果账本核对，不能只检查 `pending_operation_refs` 为空。检查点之后存在未纳入消息的已完成动作、未知请求、缺失回执或无法证明配对时，阻断原生恢复，不自动重跑。显式新上下文/新工作由后续控制流程表达，不能悄悄将不兼容恢复变成 fresh run。

Worker 的待封存输入记录真实 model_attempt、原生消息位置/摘要和原调用数据；Gate 规范请求/完整响应摘要由 `stage_session` 的受信平台服务从实际账本核对补齐。输入观察与最终严格根对象分别表达，缺失摘要不能填占位值。只有原调用和原生消息对应得到核对后才封存最终完整根；SDK 的公开序列化字典保持原样，不能把平台补充元数据写成伪造 SDK 字段。

仅开放通过真实 SDK 检查的 settled_boundary、approval_boundary；任意流中断/未完整发布/不兼容版本为 non_resumable。原生压缩只改变工作历史，保留原始资料、回执与历史归档；压缩后恢复检查候选标签、反证及工具请求/结果配对。仅有 compaction 事件不构成通过。

M1 已发布 Profile 的关闭能力和摘要保持不变。新增恢复、记忆或压缩组合使用显式新 Profile 版本/摘要，并在 Task 激活前固定；不得让原版本的 `restoration=false` 因代码升级自动变为可恢复。新组合的能力状态按 SOL 实际验证结果发布。

机制验收可装配固定的候选组合完成首次真实检查，不伪造其此前已通过的证明，也不要求先有本次 PASS 才允许执行本次验证。运行端只信任部署固定的版本/组合配置，不接受请求中的 passed 布尔值；正式发布与本轮验收结论由实际证据收口。

## 输入和批准

InputService 只接受受信 Worker Host 观察到的真实原生待批 Content，或已登记的人类问题。服务核对归属、固定 checkpoint、实际模型请求/原消息与工具定义/原始参数映射；模型生成 `input_required` 或猜一个 call ID 不能登记平台等待。登记 input、approval 与真实源引用同事务，发布边界先完成。P05 只根据原 input receipt 和 Supervisor 进程事实进入 waiting_input/释放容量，Worker 不能自报 exited。

可信 source receipt 在实际平台 intake 事务内生成并持久化，按已发布 manifest 与完整原生内容摘要去重。Worker 只提交真实观察及固定引用，不能用自己生成的 UUID 自授“可信回执”身份。

ApprovalService 提供 `decide(access, approval_id, decision, *, idempotency_key)` 与 `bind_operation_in_transaction(tx, prepared, approval_ref)`。决定绑定固定原 call、参数摘要、ToolDefinition/Scope/Profile、Session/Work/checkpoint、有效期及有资格的主体；决定版本 CAS、幂等冲突及当前读权限先于返回旧回执。公共 API 沿用冻结 ApprovalDecision → CommandReceipt，不另设含 approved=true 的执行端点。

批准只是保存决定。P06 在真实 `tool_request` 准入事务中重验当前 Task/Work/Run/Scope、恢复持有者、工具配置和额度，然后绑定原规范 ToolCall（即 ToolOperation），登记唯一 ToolAttempt/资源占用/Outbox 并消费批准。任一步失败全部回滚；重复恢复返回同一 operation/attempt 或当前真实状态，不再获得一份 allowance。原键不同参数冲突，新 call ID 同参数仍是新操作。拒绝用保存 Content 的原生 approval response 恢复，无真实工具执行；不能伪造成功工具结果。

delivery_id 由平台持久登记，pending/delivered 表示传输接收状态，重复交付去重；不表示模型理解。回答不解除 Work hold、Task pause 或取消；取消/Scope 撤销后的旧批准不使任务复活。若当前版本允许保存一个决定但不能执行，决定状态与执行阻断分别返回，不用批准成功冒充已执行。

## 既有接缝必须收口

- P05 `_recoverable` 当前只查根对象及 pending refs，须消费上述完整 frontier/发布校验；不能保留浅层检查作为旁路。
- P09 当前 credential lineage 为 `run:<id>`，Assignment 固定 fresh。恢复必须读取被锁定 Work 的精确 Session 引用，将原 session lineage 绑定到新 Run；新 Run 凭据/epoch 仍独立，不能继续用旧 Worker token。新独立 Reason 保持新会话策略。
- P06 现有 prepare/authorize 未装批准 consumer；只在主代理分配后接入上述同事务 port，保持现有四 purpose 的数据库约束，不授予 Worker 控制/审批权限。原 ToolCall 所属 Work 与合法持有者移交必须核对，不能凭任意相同 lineage 读取旧操作。
- Worker ModelCallIdentity 当前只支持 fresh response；恢复须从已发布原生映射恢复原模型请求/call/occurrence，不能把新 Run 或新模型请求 ID 填到原待批动作上。新的模型请求继续独立记账。
- M2 bridge 完成并释放源文件后，安装真实 publish/load/input/delivery Host transport；保持 await-start 屏障、Run token 验证和原结果补交。HTTP DTO 只能从主代理分配的 OpenAPI 来源生成。

## 最小验收与停止条件

SOL 首项 RED 绑定真实缺失接口；之后围绕一条真实 Worker 审批闭环检查：原生批准一次执行/拒绝零执行且跨进程；半发布/固定记忆/真实 GC pins；同 Session 两写者及不兼容 lock；批准与 ToolAttempt+Outbox 原子回滚和幂等；暂停未答输入/hold/cancel/Scope 撤销；检查点后真实完成但未纳入 history 的工具动作不能重做；实际原生压缩和恢复配对。共享 P05/P06/P09 仅复测直接受影响消费者，不重跑全套旧证据。

HTTP 路径保存完整实际请求/响应和一张结果截图；SDK/SQL/进程事件按实际媒介保存。每次记录代码 SHA 或 dirty diff 的真实绑定、命令/退出码、原始输入/输出与未覆盖项。付费模型、目标外网、生产切换仍不在授权内。P08 与完整 M3 只有实际消费者/证据齐备后才能验收。
