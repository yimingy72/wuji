# Cairn 黑板与 Wuji 任务的接入设计

2026-09-12：Wuji 自有黑板与持久 Scheduler 的后继设计见 [整体草案](stages/wuji-maf-architecture/spec.md)。当前尚未重构；本页的 Cairn 唯一可写图约束继续适用于 legacy 链路，新方案按 Task 固定后端且禁止双写/双调度。

- 日期：2026-09-10；状态：架构已确认；2026-09-11核心闭环与W1已完成封闭夹具集成，生产扩展仍待验证。
- 权威取舍：[架构替代决策](cairn-architecture-decision.md)；本页负责共享图与生命周期，Worker/工具边界见[Harness设计](agent-harness-decision.md)。
- 旧6ee84b5中“仅借鉴Cairn领域模型、PostgreSQL自建黑板、LangGraph持久编排”的方案已被替代。当前0.5.0已有任务黑板只读接口与关系导航，见[核心验收](stages/phase-1c-task-creation/acceptance.md)；旧task_events本身不构成黑板实现证明。

## 1. 直接复用及唯一图来源

Task是Wuji完整业务主体：统筹场景、目标/起点/终点、授权范围、模型和金额预算、平台/目标工具、约束以及执行控制；Cairn Project是其中的探索上下文。保留Wuji Task及其现有标识，不把Task删成Cairn Project的简单别名，也不向用户提供两套独立任务创建/编辑流程。

复用Cairn Server和Dispatcher。一个Wuji Task对应一个Cairn Project及一块黑板；Wuji Project是多任务分组，不能直接与Cairn Project映射。角色用于能力匹配，探索通过Bootstrap/Reason/Explore动态产生，不固化为角色流水线。

| 对象 | 语义与界限 |
| --- | --- |
| Origin | 冻结的起始条件及来源；用户输入不自动成为已验证结论 |
| Goal | 目标锚点及完成条件，存在该节点不表示目标已经达成 |
| Fact | 有来源的共享发现；不直接等于已确认漏洞或执行许可 |
| Intent | 从已有依据出发的探索方向，可引用多个输入Fact |
| Hint | 人工/Agent建议与态势说明，不是事实、授权或控制命令 |
| Artifact/Observation | 原始产物与观察，由Wuji维护受限存储和证据关系 |
| VerificationRun/Finding | Wuji核对主张、证据与结论，不由Cairn图结构校验代替 |

原生Fact主要为描述文本，结构校验不验证真实性；原生worker字段及心跳也不等于平台身份/执行代次。[固定协议](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/docs/specs/server-protocol.md)

2026-09-11原生行为复核：Reason标准返回complete/intents/noop，没有新增Fact写回分支，也没有固定逐Fact复核Worker。后续的补证、追加纠错、覆盖与共享文件规范见[执行衔接提案](stages/phase-1c-task-creation/execution-handoff.md)，已按核心与[W1实施合同](stages/phase-2-web-assessment/implementation-contracts.md)落实有限范围；Wuji保存完成缺口并通过普通Reason/Intent补证，不增加Core协议或由提示词承担真实性校验。

Cairn SQLite是探索图唯一可写来源，首版单Server、单Dispatcher、持久卷。Wuji PostgreSQL保存Task/AgentRun/ToolCall、权限、验证和图引用/只读投影；原始Agent提交是交接证据，不能成为另一份可独立编辑的Fact。

## 2. Bridge与必要增量

Cairn Bridge作为Platform API内部模块，负责Task映射、真实调用归属、持久操作、结果及控制同步。它不生成探索方向，不形成第二个调度器。用户不直连原生Cairn写接口，Worker不拥有数据库或跨任务管理能力。

保持Cairn Server、数据库结构、Fact/Intent/Hint模型和黑板读写/complete/reopen协议原样。改造集中在Dispatcher的调度接入、Worker后端、模型/工具适配，以及Wuji侧业务控制；不再给Cairn增加外部Task字段、原子停止态创建、操作回执或事务事件。

Wuji先保存原始Agent结果和本地操作记录，再通过原生Cairn API提交，成功后记录返回的原生ID及观察结果。请求失败需区分明确未发送与可能已提交；响应丢失按已知Project/Intent及原生读接口核对，能确认已提交则记录完成，不能确认则保持待核对。不得宣称原生API提供新增幂等回执、图版本或事务事件；不盲目重投写入，更不能重跑模型或目标。 具体平台接口/DTO见0.5.0契约和核心实施合同，不要求改Cairn数据库。

## 3. 创建、启动与派发

草稿不创建Cairn Project。Task正式创建时由Wuji记录目标、授权及模型/金额快照，保持ready；显式start接受后固定执行配置、准备受限模型凭据并核验Task Pod，再调用原生Cairn创建并保存关联；原生Project可以是active，但所有未显式启动、未关联或许可不完整的Project均被改造后的Dispatcher拒绝派发。Task业务状态与Cairn探索状态分开，不要求核心支持ready或原子停止态创建。创建响应丢失则先核对；无法确认时保留结果不明，不按名称/时间猜关联，也不盲目再次创建。

只有显式start、有效配置/授权/预算、Worker及Kali Runtime就绪后才允许调度。Cairn active只是探索状态，Wuji仍在每次派发/工具调用检查许可。旧queued没有start记录，不得自动接管。

Dispatcher选Worker配置后先申请AgentRun。worker_profile_id用于能力/容量，agent_run_id用于认领/会话/结果，execution_epoch和runtime_attempt限定当前执行。Intent已有运行、停止核对或结果同步中AgentRun时拒绝重复派发；原生心跳过期不能单独触发重跑。

## 4. 结果写入与恢复

Wuji先保存原始Agent结果和本地操作记录，再通过原生Cairn API提交，成功后记录返回的原生ID及观察结果。请求失败需区分明确未发送与可能已提交；响应丢失按已知Project/Intent及原生读接口核对，能确认已提交则记录完成，不能确认则保持待核对。不得宣称原生API提供新增幂等回执、图版本或事务事件；不盲目重投写入，更不能重跑模型或目标。

原生Cairn时间线由现有图重建，不是新增的不可变事件日志。Wuji可以保存自己的操作审计和观察快照，标明采集时间/摘要；本地采集编号不是Cairn原生事务版本，也不承诺完整捕获每个中间变化。取消前接受的结果保留历史，取消后新提案不得获准执行。

## 5. 完成、停止与重新验证

Cairn按原生语义记录探索完成，Wuji独立维护任务执行、停止、评估和报告状态。Core completed不直接等于全部进程已停或漏洞已确认；平台核对Agent/Kali活动执行、覆盖、证据和限制后形成自己的结论，可为partial。平台预算/取消通过外部执行许可和原生停止操作终止继续派发，不修改黑板核心完成语义；不自动reopen已交付任务，复测创建关联新Task。

取消/暂停先改变平台执行许可，再传播Cairn状态和Harness/Runtime停止。执行仍否继续未知时保持reconciling；已确认停止但结果缺失可部分结束，保留未知结果和证据缺口，不转成未复现。

首次集成重启后先冻结派发并核对持久回执/会话/账本，不承诺无缝恢复。Cairn内存Future仅作运行时缓存。终态复测创建关联新Task，引用历史依据并重新授权，不调用reopen改写已交付图历史。上游reopen会删除原完成边，这种行为不直接用于Wuji。[上游实现](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/server/routers/projects.py)

## 6. 共享成果与人工输入

多个Agent通过同一Task图间接协作。每次执行读入Wuji保存的本次原生查询快照，后续读图取得新Fact/Hint；不声称更新会立即推送到所有在途Agent。完整会话与压缩状态仍属于各自Harness，不能把黑板当作共享聊天历史。

执行中的文件直接在共享Kali内交接：/workspace/agents/<agent_run_id>/保存各Agent工作文件，/workspace/shared/保存明确共享成果，/workspace/inputs/保存任务输入。Agent经MCP读写这些目录，黑板可记录发现及工作文件路径；协作不必先上传对象存储。正式证据、报告或长期归档再登记Artifact、内容摘要和版本，临时路径不冒充已归档证据。凭据实体受限保存，图只登记来源、适用对象、受限credential_ref及证据。共享引用不能扩大Scope，也不改写初始ConfigSnapshot。

Hint、回答问题和控制/授权命令分别处理：Hint保留作者/来源、供后续规划参考；回答绑定具体问题和AgentRun；范围/预算/启动/取消使用对应权限化命令。发现新资产只产生候选及申请，不自动授权。

跨Task引用必须显式保留来源任务、时间、身份并重新鉴权；不在Wuji Project中自动传播成可执行事实。反证与纠错保留原发现及来源，不覆盖已交付报告；关联和证据接纳规则由后续领域契约固定。

## 7. 工作台、依赖和验收

任务详情关联黑板、AgentRun、共享环境、工具记录、证据和结果。点Fact查看其受限证据，点Intent查看依据、认领及结果，Hint显示作者和生效上下文。页面只读权威记录/投影，不直接修改Cairn或通过原生界面绕过Wuji权限。

0.5控制面、调度、共享Kali、正式关系视图已通过[核心验收](stages/phase-1c-task-creation/acceptance.md)；W1完成缺口反馈、评估与证据刷新见[W1验收](stages/phase-2-web-assessment/acceptance.md)。真实目标开放仍以生产出口和停止边界证据为前提。

本次只同步文档，不启动Cairn或模型。完整图布局、长断线、压力与模型矩阵保持后续范围；本机历史证据与业务被测SHA不因文档提交变化。
