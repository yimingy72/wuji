# P05 执行控制与容量接口收口

日期：2026-09-13；主控制器负责。依据已批准 v2 S04—S07、S09/S11/S13 和 P05 Plan。P05 仅准备，需等待共享迁移交接及 START。

## 所有权与迁移顺序

P05 在最终 P04 迁移头之后追加独立控制迁移，扩展同一 Task/WorkItem/AgentRun/ToolCall/ToolAttempt、UoW 和 Outbox；不重建父表或结果账本。允许新增执行 states/control/dependencies/capacity 模块、内部控制输入/观察类型、必要公开 DTO 修订及生成物。正式 Task/Work/审批 HTTP 路由由 P11 接线；P05 的服务是生产实现，测试通过实际服务与数据库调用，不提供假业务路由。

“全局暂停”在本阶段指 Task 整体 pause 与单 Work hold 的区别，不增加平台级运营开关。

## 状态与版本

Task 增加独立 control_version、desired/observed、activated_at、close_trigger/result_outcome、关闭尝试引用及不可变执行定义/配置引用。TaskView.version 对应 control_version，不借用 board_revision。迁移已有行不填造 activated_at；仅 execution_allowed=true、旧 Run 或历史 queued 不成为显式 start 证明。派发资格必须同时检查 activated_at、Task desired/observed、当前许可和配置。

WorkItem 扩展 kind、desired_state、revision、run_epoch、当前 Run、固定 IntentRevision、阻断/终止原因，以及带来源标识的 suspension_causes/wait/session 引用。Work.revision 作为控制/执行状态 CAS，不因无关黑板追加改变。保持所有固定状态/转移；known never-started 可 fresh start，registered/lease 过期/缺回执不构成 known not-started。

AgentRun 的 process_state 与 result_state 分开。P04 结果服务是 received/accepted/rejected/historical_only 的写入者；P05 不凭退出把结果改成 accepted。需要结算缺失输出时，通过共享结果状态入口以 CAS 仅将尚无提交的结果标 incomplete，不能覆盖在途已接纳结果。迟到结果仍由 P04 根据当前资格接纳或 historical_only。Work.done 同时需要已接纳有效结果、真实进程退出和相关操作结算。

## 命令上下文与初始化

`ControlService.apply` 接收内部 `ControlCommandContext`：可信 AccessContext、task_id、可选 work_item_id、operation_id，以及已验证 TaskCommand/WorkCommand DTO。目标来自路由或可信调用，不由 DTO 自授归属。Task 命令 CAS 对 Task.control_version，Work 命令对 Work.revision。

通用控制回执键分别采用 `(tenant, task, task_command, operation_id)` / `(tenant, task, work_command, operation_id)`，完整摘要包含目标、command、expected_version、reason；同键不同命令也冲突。同键查询先检查当前读权限；新写另查控制权限。回执、状态/代次及控制 Outbox 同事务，不复用 evidence_ingest/result_submit 命名空间。

新增 can_control/can_observe 等任务 ACL 和 UoW 能力，不能把 can_write 知识权限或 Agent 角色当成执行控制资格。人类 Operator 的控制与受信 Controller 的观察登记分别校验，Agent 无权通过普通候选/结果接口调用这些写入。

Task.start 是首次激活的幂等事务：核对已保存的完整目标/起点/授权/模型与 Runtime Profile 快照及有效期，记录 activated_at 和新许可，发出持久 task.started/Reason 初始化触发。无需模型或伪 Bootstrap Run。P09 消费触发并创建/领取唯一 Reason 工作，不由 P05启动 Agent。用户创建 Task 的 HTTP 接口和完整输入接线归 P11；P05测试使用明确的保存定义前提，不能根据 Scope 第一个 Host 猜入口或补造输入。

pause/hold/cancel 先撤销相应 epoch，再写停止 Outbox。Task.pause 仅增加 task_pause；Task.resume 只解除它。Work.hold 增加 user_hold 并保持 desired=hold，ResumeWork 只解除自己的 hold。按 `(cause_kind,cause_ref)` 保存原因，completion_epoch 关联具体 ID。解除一种原因不能解除其他原因或未答 wait_ref。

## 容量事务

复用 UoW 增加受权 control/admission 事务入口，在锁 Task 之前读取该 Task 冻结配置的 capacity pool refs 并按固定顺序锁定：平台及共享模型池（稳定 key 排序）→租户池→Task→Work→Session→排序资源。不得先进入原 Task 写事务，再补取全局/租户容量锁。

池上限由已发布配置给出，生产缺少配置则阻断，不从模型名称或用户提案猜容量。P05测试显式给出小型夹具上限，不新增永久默认数。预留关联真实 AgentRun 与池，状态 reserved/running_or_unknown/released；P09在同一准入事务调用预留端口，P10/P11的真实观察驱动占用/释放。未知仍按可能在运行占用；本地退出可释放 Agent 进程容量，但未知工具副作用继续占其冲突资源。费用 pending 不冒充进程仍活跃。

## 可信执行观察

P05 定义并保存内部 `ExecutionObservation`：稳定 observation/receipt ID、固定 RunIdentity、receiver/runtime/环境身份、原生 operation ID、完整进程出生/退出身份（适用时）、kind=not_started/started/exited/environment_stopped/unknown、来源回执及摘要、采集时间。观察登记仅由授权 controller/reconciler 调用；不能由 TaskCommand 内的 exited=true 等字段产生。

ControlService 从已登记回执核对状态，cancel_ack 只表示接收；没有正确接收者/代次/出生身份或停止依据保持 reconciling。P10把实际 Supervisor GET/退出回执归一到该入口，不增另一个进程状态权威。P05的预置观察在测试中明确为前提夹具，真实进程证明留 P10/P11。

## 输入、Session、判据与完成的交界

P05 允许定义最小的规范 input_request、session_manifest、goal_criterion/judgment 元数据和当前引用，以便控制服务读取真实持久前提；写入内容、完整发布/审批协议和实际核验分别由 P08、P12实现并扩展同一表。P05不提供“自报可恢复/判据满足”的客户端入口。

Session 元数据采用已有 SessionManifest 形状，发布标识、完整 refs/pins、锁摘要与恢复类必须明确。控制恢复检查已发布状态、当前访问、Run/Work归属、固定版本、所有对象可用及 pending operations；缺少已实施发布/校验适配时 executed 工作 blocked，不能把临时 JSON 当合法恢复点。测试可用实际封存字节与明确发布前提检验控制守卫，但不称为 SDK 恢复验证。

InputRequest 保留原 wait_ref 和 pending/resolved/revoked 状态；P08负责真实问题/审批、内容与决定的写入。P05取消可撤销可执行等待并保留审计；恢复仅移除暂停原因，未答问题仍 waiting_input。

WorkDependency 增加专用 `GoalCriterionRef(criterion_id, revision)`，不以 KnowledgeRef(goal/claim) 假充判据。P05在真实规范行上检查固定版本的当前 judgment；仅有合法、适用的判定才 criterion_satisfied。判据实际方法/证据判定由 P12拥有；fixture judgment 只证明依赖守卫，不是已验证 Goal。settled 与 accepted_result 分别按真实前驱结算和有效结果检查，前驱失败/取消只满足 settled。

finish/cancel 记录结束意图和 close trigger，进入有界停止/等待结算，P05不生成报告、不判断 Goal.met、也不立即写 closed。P12的 CompletionEpoch/precheck/finalize 是关闭权威，通过内部受权控制入口应用 quiescing、精确解除某个 completion_epoch 原因及最后关闭。`abort-close` 是P12内部命令，不塞入普通用户 TaskCommand 作为无条件恢复。

## 测试与交接

按固定 Spec 和 P05准备中的主流程、失败/权限边界运行真实数据库/服务检查。复用未改的P03 DAG证据；更改DAG路径才定向复测。收到结果但未退出、单项hold叠加Taskpause、未答输入、never-started与已执行恢复、容量保留/释放、三类依赖、命令幂等和独立控制权限必须有具体结果。P08/P10/P11/P12/P09实际联调部分如实保留后续状态。
