# Cairn 黑板与 Wuji 任务的接入设计

- 日期：2026-09-10；状态：目标架构已确认，implementation pending。
- 权威取舍：[架构替代决策](cairn-architecture-decision.md)；本页负责共享图与生命周期，Worker/工具边界见[Harness设计](agent-harness-decision.md)。
- 旧6ee84b5中“仅借鉴Cairn领域模型、PostgreSQL自建黑板、LangGraph持久编排”的方案已被替代。公开API0.4.0尚无黑板，task_events不能当成Fact/Intent/Hint实现证明。

## 1. 直接复用及唯一图来源

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

Cairn SQLite是探索图唯一可写来源，首版单Server、单Dispatcher、持久卷。Wuji PostgreSQL保存Task/AgentRun/ToolCall、权限、验证和图引用/只读投影；原始Agent提交是交接证据，不能成为另一份可独立编辑的Fact。

## 2. Bridge与必要增量

Cairn Bridge作为Platform API内部模块，负责Task映射、真实调用归属、持久操作、结果及控制同步。它不生成探索方向，不形成第二个调度器。用户不直连原生Cairn写接口，Worker不拥有数据库或跨任务管理能力。

需要给Cairn增加：外部Task标识唯一、创建时stopped、操作ID与完整请求摘要、幂等回执查询，以及图变更/版本/事件/回执同事务写入。现有API只能提供部分能力，这些增量不能标为已实现。

跨库使用Wuji持久操作/Outbox、Cairn本地事务及原回执核对；不假定两库原子提交。按Task顺序同步控制与结果；同ID异输入拒绝，响应丢失查询原操作，投影落后不覆盖权威图。具体HTTP/DTO和迁移由后续控制面Spec冻结。

## 3. 创建、启动与派发

草稿不创建Project。Task正式创建后按稳定Task标识幂等创建stopped Project；映射尚未同步就显示待同步，不伪造已就绪。禁止创建active后再补停止，因为Dispatcher可能抢先派发。

只有显式start、有效配置/授权/预算、Worker及Kali Runtime就绪后才允许调度。Cairn active只是探索状态，Wuji仍在每次派发/工具调用检查许可。旧queued没有start记录，不得自动接管。

Dispatcher选Worker配置后先申请AgentRun。worker_profile_id用于能力/容量，agent_run_id用于认领/会话/结果，execution_epoch和runtime_attempt限定当前执行。Intent已有运行、停止核对或结果同步中AgentRun时拒绝重复派发；原生心跳过期不能单独触发重跑。

## 4. 结果写入与恢复

固定顺序：

1. 在Wuji保存原始结构化结果、执行状态和Artifact引用。
2. 校验真实Task/AgentRun、代次、证据归属和结构。
3. 保存具有稳定操作ID的黑板提交。
4. Cairn幂等写入并返回原生Fact/Intent ID与版本。
5. Wuji登记同步完成并发布只读展示事件。

黑板不可用时保持结果待同步，只重投已保存结果。取消前接受的结果可补入历史；取消后新提案不能触发执行。已完成探索的结果丢失通知，不构成重新跑模型/目标的理由。

原生Cairn从现有图重建时间线，并非完整不可变事件日志；所需事务事件是Wuji接入增量。快照版本和事件位置保持一致，整批校验通过再推进游标；各数据源保留自己的版本，不用一次全局序列假装跨库一致快照。

## 5. 完成、停止与重新验证

Dispatcher的complete改为向Bridge提交完成提案。平台核对目标/覆盖/证据；缺少必需项且允许继续时反馈具体缺项。接受结束后停止新派发，分别核对Agent与Kali活动调用。目标达成才提交Cairn完成边；预算、环境或用户决定导致部分结束时保持stopped，不写假goal边。

取消/暂停先改变平台执行许可，再传播Cairn状态和Harness/Runtime停止。执行仍否继续未知时保持reconciling；已确认停止但结果缺失可部分结束，保留未知结果和证据缺口，不转成未复现。

首次集成重启后先冻结派发并核对持久回执/会话/账本，不承诺无缝恢复。Cairn内存Future仅作运行时缓存。终态复测创建关联新Task，引用历史依据并重新授权，不调用reopen改写已交付图历史。上游reopen会删除原完成边，这种行为不直接用于Wuji。[上游实现](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/server/routers/projects.py)

## 6. 共享成果与人工输入

多个Agent通过同一Task图间接协作。每次执行读入绑定的不可变快照，后续读图取得新Fact/Hint；不声称更新会立即推送到所有在途Agent。完整会话与压缩状态仍属于各自Harness，不能把黑板当作共享聊天历史。

Kali本地文件路径只用于现场定位，上传/登记Artifact后才能形成可追溯证据引用；未上传标为待收集或缺失。凭据实体受限保存，图只登记来源、适用对象、受限credential_ref及证据。共享引用不能扩大Scope，也不改写初始ConfigSnapshot。

Hint、回答问题和控制/授权命令分别处理：Hint保留作者/来源、供后续规划参考；回答绑定具体问题和AgentRun；范围/预算/启动/取消使用对应权限化命令。发现新资产只产生候选及申请，不自动授权。

跨Task引用必须显式保留来源任务、时间、身份并重新鉴权；不在Wuji Project中自动传播成可执行事实。反证与纠错保留原发现及来源，不覆盖已交付报告；关联和证据接纳规则由后续领域契约固定。

## 7. 工作台、依赖和验收

任务详情关联黑板、AgentRun、共享环境、工具记录、证据和结果。点Fact查看其受限证据，点Intent查看依据、认领及结果，Hint显示作者和生效上下文。页面只读权威记录/投影，不直接修改Cairn或通过原生界面绕过Wuji权限。

先完成0.5控制面必要契约与持久记录，再接入调度和合成工具，随后共享Kali及正式产品页面。真实目标开放以出口和停止证据为前提；详细流量控制仍待后续设计。

本次只改文档，不启动Cairn、不调用模型；旧P0预算及事实保持。后续最小场景为一个Fact→Intent→结果链、结果重投不重跑、两个独立AgentRun共用一个Runtime、未启动/失权不派发和取消边界。完整图、长断线、压力与模型矩阵不成为本轮检查要求。
