# P09 Scheduler 实施收口（依赖准备）

日期：2026-09-13。主代理设计，依据批准的 Plan P09 与 Spec S04/S06/S07。P06 尚未交出最终迁移；本文不提前启动 P09 生产实现。测试、验证、复核与常规修复使用 SOL/xhigh。

## 单活动与事务准入

首版一个活动 Scheduler。使用数据库持有的明确服务所有权，不能仅靠定时器、自报 alive 或过期时间认定旧调度者停止。可采用专用 PostgreSQL session advisory lock，并让所有准入事务只使用持有该锁的同一会话；连接失效后不得换普通连接继续派发，必须重新取得所有权。不是自行设计多活动调度协议。纯策略函数不拿锁、不写 DB、不发网络；调度快照中的权限提示不是 permit。

按已授权服务主体及 Task ACL 枚举候选；不能给 Scheduler 一个绕开租户 RLS 的业务读角色。每次实际领取使用 P05 `can_dispatch(tx, work)`、容量池前置锁序和 P06 已发布模型/Runtime 配置及累计限额。全局/模型池→租户池→Task→Work→Session→排序资源，重复核对当前依赖、Scope、暂停、期限和注册 receiver/runtime。Task 未 start 不创建执行尝试。

同一事务创建真实 AgentRun、run_epoch、稳定 start_operation_id、完整冻结 WorkerAssignment、容量 reservation、Run 限定凭据 binding 与 Outbox，再提交。Outbox 中引用受限凭据，不向普通事件/图/审计输出明文。不能以调度 tick 的成功或 Outbox 写成当作进程已启动；实际 Supervisor/运行观察仍归 P10。P06 一个 Run 的模型请求不能再占一份 Agent 槽位。

配置缺失、未发布的 Worker/HarnessProfile、缺接收者、不可恢复 Session 或必要引用无权必须留下明确 blocked/解除条件，不能生成一个永远无法运行的假 Assignment。P07 TaskDefinition.worker_profiles 的绑定在正式集成时必须核对；P09 未接实际 SDK 的局部前提不得称完整运行验收。

## 公平选择与精确去重

SchedulerPolicy.select 消费已固定的 SchedulingSnapshot、逻辑时钟和轮转位置，输出有界 SelectionProposal。租户与 Task 轮转，同 Task 使用有界人工优先级与等待老化，并给予已就绪 Reason/控制工作有限机会；不能让不断到来的新 Intent 永久排挤旧可执行工作。轮转位置与真实决策持久化，进程重建不总从排序第一项开始。SOL 用确定输入序列验证公平边界，不做大规模性能矩阵。

Work 的 exact key 绑定规范问题/Intent 身份、方法/Profile 版本、精确依据版本、执行环境和预期输出合同。相同 Intent 的重复消费不能产生第二 Work；新 Intent 不因标题相似被自动合并。运行尝试和外部工具逻辑身份不拿该工作 key 代替。自然语言相似度不授予执行或证明已做过。

max_work_items 以真实已登记 Work 的累计口径约束，max_reason_runs 以已准入 Reason Run 约束；尝试失败/服务重建不返还次数。Task 模型/工具/输出累计仍由 P06 同一账本负责，不在 Scheduler 再维护价格或第二套财务预占。

## 独立 generation 与 Reason 结果消费

TriggerAccumulator 保存 trigger_generation、consumed_generation、reason 集合、inflight_reason_work_id。消费 actual domain Outbox 事件有持久去重键；事件即使 board_revision 未变也能产生新的 trigger generation。Task.start 初始触发是程序登记，不伪造 Bootstrap Run。

领取 Reason 时冻结 processing_generation、读取用 SnapshotManifest 和 Work 身份；结果只消费到该 processing_generation，执行期间新来的 generation 保留。失败按发布的有限次数和退避处理，超过上限保留 blocked、责任角色与解除条件。心跳、Token、无效提案、布局或 Reason 自己新建 Intent 不立即反向触发 Reason；使用实际生产者/提交因果关系识别，不能按模型自报 role 判断。

P04 保留 raw-first 和原 ComponentReceipt 权威。P09 为已注册 reason Work 的 `reason_decision` 增加同 Task 事务内的规范消费端口，绑定真实 submission、原始 payload/receipt、已接纳的 local-ref 映射和 processing_generation。可在 P04 接纳事务组合一个服务端口，不允许分离为“先消费 generation 后登记等待”。Explore 提交的文字 `reason_decision` 不因此拥有 Reason 调度角色。

若需要把 ReasonDecision 的接纳结果纳入 ResultReceipt，做窄的组件回执扩展并从 OpenAPI 生成，不能改写历史原始提交或将一个无效决定假装执行成功。Reason 控制部分拒收时，合法知识组件仍保留；触发失败/blocked 的记录与知识接纳状态分别表达，不能仅用 Work.done 推断 Reason 决定已生效。

## Wait 与 blocked

只接受发布的有版本谓词和真实同 Task 引用。模型提供的 predicate 字符串不是可执行代码、SQL、URL 或权限。wait 必须有可核对的引用；其 local refs 只能解析到本批真实接纳对象。登记 waiter 与读取谓词当前状态在同一锁事务内：已满足则登记后续触发，未满足才持久等待。相关事件与唤醒标志原子提交；重启扫描未处理 waiter。

blocked 的 reason_code、责任角色和解除条件由平台规则形成，模型的 reason 文本只作资料。无可靠机器解除条件时明确交给 Task operator 审查，不靠 tick 自动清空。纯输入等待可在实际 Run 退出、边界保存及操作结算后释放容量，不能只因模型选择 wait 就释放。

## 可测进展与未知执行

ProgressSummary 只用可观察规则：实际新增有效材料（以内容/来源/适用条件作明确去重）、可信判据/阻断已解决、发布规则能确认的新增问题类别。新 Claim/Intent UUID、改标题、Claim/Fact 数量增长或模型 novelty 分数不能单独清零无进展计数；自由问题没有可靠类别时标 unknown。固定总工作、Reason、调用/字节、时间及失败上限仍有效。

未知工具只阻断相关 Work、资源与依赖；租约过期不证明旧写者已停止。未知响应费用不占工具资源；旧模型请求的本地执行是否结束按 P06 实际结算判断。Task cancel/finish 的全局风险收敛继续交 P11/P12，不由 Scheduler 自行宣布 Goal 完成。

## 最小交接与验证

最终 P06/P07 公共接口固定后再落具体 migration/head、注册字段及方法签名；不猜内部表来通过测试。SOL 用真实 PostgreSQL 与生产 Scheduler/Trigger/Waiter，覆盖同 board_revision 新触发、在途新 generation、wait 事件先到与后到、失败上限、精确去重、确定公平序列和最后共享容量竞态。只外部 receiver/真实进程前提可作隔离夹具；不得在测试里实现被测计数/触发/策略。完整 Outbox→Supervisor→MAF 运行在 P10/P17 汇合验收，局部 SQL 通过不冒称其完成。
