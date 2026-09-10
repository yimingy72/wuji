# 架构替代决策：Cairn 调度、平台侧 Agent 与共享 Kali

- 日期：2026-09-10；状态：accepted / 用户已批准的目标架构，implementation pending。
- 依据：用户批准《Wuji 架构复审修订版：Cairn 调度、平台侧 Agent 与共享 Kali》；用户明确Agent不运行在Kali中，整体架构由主代理独立设计。
- 文档实施基准：codex/phase-1c-prep@6ee84b5268a5012c69ba4567d78eb18727b41ee1。
- 本批范围：[Spec](stages/cairn-architecture-baseline/spec.md)、[Plan](stages/cairn-architecture-baseline/plan.md)、[文档验收](stages/cairn-architecture-baseline/acceptance.md)。公开API仍0.4.0，本文不是已发布接口或已验证部署的声明。

## 1. 替代哪些旧决定

| 旧设计 | 本次决定 | 保留的事实 |
| --- | --- | --- |
| LangGraph必选，优先Deep Agents | 直接复用Cairn Server/Dispatcher，首个Harness采用Pi coding-agent；LangGraph/LangChain/Deep Agents不再是目标执行链必选项 | P0实验代码、依赖锁和原验收保留，不把它改写为Pi/Cairn证据 |
| Cairn仅作概念参考，Fact/Intent/Hint全部在Wuji PostgreSQL自建 | Cairn Server维护唯一可写探索图；首版单Server、单Dispatcher、持久化SQLite | Wuji仍维护Task、AgentRun、工具账本、证据和验证/报告 |
| 自建Wuji模型网关，P0 Provider/IPC进入生产 | LiteLLM承担网关和原生金额预算；模型协议与Harness继续复用成熟实现 | P0私有文件、IPC与次数账本只作实验资产 |
| 首批模型预算用Token上限 | Task金额预算USD；组织模型配置不设置Task预算；全部Agent及辅助调用共享预算 | Token保留为统计与上下文容量指标，历史计数不改写 |
| Cairn Agent与工具同住Kali | Agent运行于平台侧Worker Pod；多个Agent经受控工具接口共用一个Kali Runtime | 用户要求的是共享目标执行环境，而非把Harness迁入Kali |
| 强制SOL开发、Luna独立验收及固定并发/worktree | 当前会话连续完成；允许按需子代理，本次gpt-6-astra/low；架构由主代理独立设计 | 历史报告仍记录当时实际模型；测试预算与Git约束继续有效 |

旧权威文档基准可从 `git show 6ee84b5:<path>` 追溯。旧0.5草案标为superseded，不得从其中复制过时设计进入实施。

## 2. 部署与唯一所有权

```text
Wuji Project -> 多个Task
一个Task -> 一个Cairn Project -> 一块共享黑板
                            -> 一个平台侧Agent Worker Pod
                               -> 多个独立AgentRun / Harness会话
各Agent -> Tool Router -> Runtime Supervisor / MCP
                         -> 同一个Kali容器 / 当前获准Runtime attempt
各Agent -> LiteLLM -> 组织已发布模型的上游服务
```

| 组件 | 职责与所有权 |
| --- | --- |
| Platform API | 用户权限、Task命令、授权、配置、执行准入、验证与产物访问 |
| Cairn Bridge | API内部适配模块，核对归属、登记幂等操作、同步控制和结果；不选择下一探索方向 |
| Cairn Server | Fact/Intent/Hint、探索关系、黑板版本、事件和写入回执 |
| Cairn Dispatcher | Bootstrap/Reason/Explore、Worker能力匹配与并发；通过平台准入后才派发 |
| Agent Worker后端 | 平台侧Worker Pod、Harness进程、会话与进程回执；只清理Agent资源 |
| Tool Router | 真实调用身份、工具权限、调用账本、有效epoch与Kali attempt路由 |
| Runtime Controller | Kali Runtime创建、重建、停止核对和回收；不启动Harness |
| Runtime Supervisor/MCP | Kali内工具进程、执行句柄、取消、产物上报 |
| LiteLLM | 模型接入、原生凭据、费用和Task金额预算；不维护Agent会话 |
| Assessment/Artifact | 平台内的验证、覆盖、结果、证据与报告模块 |

每Task首版一个平台侧Worker Pod容纳多个Harness进程，另一个TaskRuntime Pod容纳一个共享Kali工具容器及所需受信控制Sidecar。两类Pod不共用文件卷、进程空间或凭据。Kali同任务目录/浏览器Context划分用于避免污染，不宣称隔离相互恶意的执行者。

Cairn ExecutionBackend适配平台Worker环境；后端选择、执行上下文和cleanup调用均需改造，不是已有Kubernetes支持。[上游接口](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/runtime/backend.py)

## 3. 数据权威和跨库一致性

- Wuji PostgreSQL：Task/权限/配置快照、AgentRun及原始结构化提交、Runtime/ToolCall、证据元数据、验证和报告、待同步操作与只读投影。
- Cairn SQLite：唯一可写Fact/Intent/Hint及探索关系；首版单实例及持久卷。
- LiteLLM独立数据库：网关原生模型配置、凭据、用量与费用；其迁移不得作用于Wuji表。
- 对象存储：产物、原始证据、受限日志及会话归档。

原始Agent提交是不可变交接证据，不是第二套可写Fact。Wuji查询投影不得反向覆盖Cairn。数据库RLS只保护Wuji表；Cairn通过Bridge和受限服务入口核对Task/租户归属，不把SQLite或内部网络当作多租户鉴权。

需要对Cairn增加稳定外部Task标识、停止态创建、操作ID/摘要/回执，以及图变更/版本/事件/回执同事务写入。跨库通过按Task排序的持久操作和回执核对，不宣称分布式事务原子性。响应丢失查询原操作；黑板不可用时只重投已保存结果，不重跑模型或目标。

## 4. 任务、派发与结果

草稿不创建Cairn Project。正式Task以稳定Task标识幂等创建stopped Project，不能先active再停止。显式start接受后，只有配置、授权、预算、Worker和Kali Runtime均满足条件才允许调度。旧queued没有启动记录，永远不能被新执行器自动接管。

Dispatcher选择Worker配置后先申请AgentRun，再启动进程。worker_profile_id表达能力和容量；agent_run_id表达真实执行、认领、会话、日志与结果；execution_epoch和runtime_attempt限定当前许可。Intent仍有运行、停止核对或结果同步中的AgentRun时拒绝重复派发。Cairn的active/stopped及内存Future均不是执行许可或持久恢复依据。[上游调度状态](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/scheduler/loop.py)

固定结果顺序：持久化原始结果/执行状态/产物引用 → 核对身份、代次、证据及结构 → 登记稳定黑板操作 → Cairn幂等写入并返回原生ID → Wuji登记同步完成/发布投影事件。同步失败显示结果待同步；不得把它当作探索失败。取消前已接受结果可补入历史；取消后新提案不触发执行。旧回执读取不等于新执行许可。

## 5. 完成、取消与恢复

Dispatcher的complete先由Bridge接为完成提案，不直接触发Cairn默认完成清理。平台核对目标条件、覆盖、证据；仍缺必需项且允许继续时反馈缺项。接受结束后停止新派发，分别核对Agent与Kali活动执行，再确定终态。目标确已达成才写Cairn完成边；预算/环境/用户决定导致部分结束时保持stopped，不伪造goal达成。终态复测创建关联新Task，不使用reopen改写已交付历史。

暂停/取消先改变平台执行许可，再传播到Dispatcher、Harness、Tool Router、Runtime与出口。SDK abort和Pod删除请求均不是停止证明；不得假设能回滚已发往目标的请求。

执行是否仍在继续未知时保持reconciling并禁止新派发；已确认停止但结果缺失时保留结果未知和证据缺口，可部分结束，不写成成功或未复现。首次集成重启后先冻结派发并核对进程回执、会话及工具账本，不承诺无缝续接，不重新询问模型猜测原动作。

## 6. Harness、模型与成果

首个接入使用Pi coding-agent现成客户端、循环、会话、摘要与JSON事件；保留Cairn CLI适配方向，不同时接入多套Harness。关闭自动发现和默认本地执行工具，只加载受信扩展。提供绑定本次AgentRun的不可变快照读取、限定工作记忆、鉴权的黑板/证据查询；目标命令和文件操作走Tool Router/MCP，在Kali执行。禁用read后必须同时改造Cairn原来的文件快照交付。[快照实现](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/tasks/common.py)

组织模型配置由TenantAdmin维护，发布前要求同版本显式连接检查成功；无可用模型时只能保存草稿。Task设置USD金额预算，全部Agent、Reason、收尾、摘要和重试共用LiteLLM预算，不周期重置、不因换Agent或重建Runtime重置。上游Key只在LiteLLM；受限任务凭据只用于平台侧模型请求，不进入Kali。未知价格不按零计费，不承诺未验证的并发零超支。

关闭Cairn自动付费探活；readiness不请求模型。无效配置、权限拒绝、不支持工具等错误不按短周期重启Worker。结果不明先核对；收尾最多按既定单次流程且必须仍有预算，耗尽后不额外请求模型生成总结。

Kali本地路径只用于现场定位；产物先登记Artifact再通过引用进入黑板。上传未完成标记待收集/缺失。凭据通过受限引用共享，原文不广播。Fact表达共享发现，VerificationRun/Finding规则决定可接受结论。保留五场景、五主题、匿名Web、域名/子域授权；流量具体实现仍待设计，真实目标执行前必须有出口和停止边界证据。

## 7. 版本、实施依赖和验收边界

| 依赖 | 候选集成基线 | 状态 |
| --- | --- | --- |
| Cairn | 8e7e0ea67552383851dfcabfba0c4e9c8d007878 | 静态核对，所需适配/增量未实现；保留AGPL-3.0许可及上游来源 |
| Pi coding-agent | 0.73.0 | 首个Harness接入方向，未在Wuji验收 |
| LiteLLM Proxy | v1.100.0 | 网关选型已确认，未部署、未固定运行镜像digest或完成集成 |

必要补丁和平台适配保留明确归属，不重写Cairn搜索调度、厂商协议或Pi上下文机制。候选失败报告具体原因，不静默换框架。

后续依赖顺序：控制面基础（0.5契约、配置快照、ready/start、epoch、AgentRun/工具账本、Task绑定）→调度适配（先合成工具）→共享Runtime→原型评审后的正式产品接入→真实目标开放。具体API、迁移和验证入口由对应Spec/Plan冻结；旧0.5草案不能直接施工。

本批只更新文档，Phase1A保持partial，P0验收限定原实验，业务仍0.4.0。原共享检查预算已用426/600秒、剩174秒，真实4次额度已用完，不按重拆批次重置。文档仅diff/链接检查；后续最小场景为未启动不派发、两个独立AgentRun共用一个Runtime、结果重投不重跑、工具越权拒绝、取消与迟到派发、旧queued不执行；不足则待测，不预先标集成通过。
