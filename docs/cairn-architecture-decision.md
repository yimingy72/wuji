# 架构替代决策：Cairn 调度、平台侧 Agent 与共享 Kali

- 日期：2026-09-10；状态：accepted / 用户已批准的目标架构，implementation pending。
- 依据：用户批准《Wuji 架构复审修订版：Cairn 调度、平台侧 Agent 与共享 Kali》；用户明确Agent不运行在Kali中，整体架构由主代理独立设计。
- 后续澄清：Task业务主体、每Task一个Agent Pod与核心不改边界见[修订记录](stages/cairn-architecture-baseline/clarification.md)；以下为修订后的现行决定。
- 文档实施基准：codex/phase-1c-prep@6ee84b5268a5012c69ba4567d78eb18727b41ee1。
- 本批范围：[Spec](stages/cairn-architecture-baseline/spec.md)、[Plan](stages/cairn-architecture-baseline/plan.md)、[文档验收](stages/cairn-architecture-baseline/acceptance.md)。公开API仍0.4.0，本文不是已发布接口或已验证部署的声明。

## 1. 替代哪些旧决定

| 旧设计 | 本次决定 | 保留的事实 |
| --- | --- | --- |
| LangGraph必选，优先Deep Agents | 直接复用Cairn Server/Dispatcher，首个Harness采用Pi coding-agent；LangGraph/LangChain/Deep Agents不再是目标执行链必选项 | P0实验代码、依赖锁和原验收保留，不把它改写为Pi/Cairn证据 |
| Cairn仅作概念参考，Fact/Intent/Hint全部在Wuji PostgreSQL自建 | Cairn Server维护唯一可写探索图；首版单Server、单Dispatcher、持久化SQLite | Wuji仍维护Task、AgentRun、工具账本、证据和验证/报告 |
| 自建Wuji模型网关，P0 Provider/IPC进入生产 | LiteLLM承担网关和原生金额预算；模型协议与Harness继续复用成熟实现 | P0私有文件、IPC与次数账本只作实验资产 |
| 首批模型预算用Token上限 | Task金额预算USD；组织模型配置不设置Task预算；全部Agent及辅助调用共享预算 | Token保留为统计与上下文容量指标，历史计数不改写 |
| Cairn Agent与工具同住Kali | 每Task一个Pod，多个Agent运行于其中agent容器；多个Agent经受控工具接口共用一个Kali Runtime | 用户要求的是共享目标执行环境，而非把Harness迁入Kali |
| 强制SOL开发、Luna独立验收及固定并发/worktree | 当前会话连续完成；允许按需子代理，本次gpt-6-astra/low；架构由主代理独立设计 | 历史报告仍记录当时实际模型；测试预算与Git约束继续有效 |

旧权威文档基准可从 `git show 6ee84b5:<path>` 追溯。旧0.5草案标为superseded，不得从其中复制过时设计进入实施。

## 2. 部署与唯一所有权

Task是Wuji完整业务主体：统筹场景、目标/起点/终点、授权范围、模型和金额预算、平台/目标工具、约束以及执行控制；Cairn Project是其中的探索上下文。保留Wuji Task及其现有标识，不把Task删成Cairn Project的简单别名，也不向用户提供两套独立任务创建/编辑流程。

```text
Wuji Project -> 多个Task
一个Task -> 目标、工具、约束、模型与外部执行控制
        -> 一个Cairn Project / 原生共享黑板
        -> 一个Task Pod
           -> agent容器 / 多个AgentRun与Harness会话
           -> kali容器 / MCP、工具与共享工作区
各Agent -> Tool Router -> Runtime Supervisor / MCP
                         -> 同一个Kali容器 / 当前获准Runtime attempt
各Agent -> LiteLLM -> 组织已发布模型的上游服务
```

| 组件 | 职责与所有权 |
| --- | --- |
| Platform API | 用户权限、Task命令、授权、配置、执行准入、验证与产物访问 |
| Cairn Bridge | API内部适配模块，核对Task归属、登记平台操作、调用原生接口并核对结果；不选择下一探索方向 |
| Cairn Server | 原生Project、Fact/Intent/Hint、探索关系与读写协议；不增改核心 |
| Cairn Dispatcher | Bootstrap/Reason/Explore、Worker能力匹配与并发；通过平台准入后才派发 |
| Agent Worker后端 | agent容器内Harness进程、会话与进程回执；不创建/删除Pod |
| Tool Router | 真实调用身份、工具权限、调用账本、有效epoch与Kali attempt路由 |
| Runtime Controller | 整个Task Pod创建、重建、停止核对和回收；Cairn经执行后端启动Harness进程 |
| Runtime Supervisor/MCP | Kali内工具进程、执行句柄、取消、产物上报 |
| LiteLLM | 模型接入、原生凭据、费用和Task金额预算；不维护Agent会话 |
| Assessment/Artifact | 平台内的验证、覆盖、结果、证据与报告模块 |

用户最终确认：每Task一个Pod，固定agent与kali两个容器；agent容器动态运行多个Harness进程，kali容器承载工具/MCP及共享目录。各容器独立镜像、工作卷、凭据挂载和进程空间；它们共享Pod网络，不承诺按容器分配不同NetworkPolicy。Kali同任务目录/浏览器Context划分用于避免污染，不宣称隔离相互恶意的执行者。

Cairn ExecutionBackend定位已获准的Task Pod及agent容器，适配动态进程执行；后端选择、执行上下文和cleanup调用均需改造，不是已有Kubernetes支持。[上游接口](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/runtime/backend.py)

## 3. 数据权威和跨库一致性

- Wuji PostgreSQL：Task/权限/配置快照、AgentRun及原始结构化提交、Runtime/ToolCall、证据元数据、验证和报告、待同步操作与只读投影。
- Cairn SQLite：唯一可写Fact/Intent/Hint及探索关系；首版单实例及持久卷。
- LiteLLM独立数据库：网关原生模型配置、凭据、用量与费用；其迁移不得作用于Wuji表。
- 对象存储：产物、原始证据、受限日志及会话归档。

原始Agent提交是不可变交接证据，不是第二套可写Fact。Wuji查询投影不得反向覆盖Cairn。数据库RLS只保护Wuji表；Cairn通过Bridge和受限服务入口核对Task/租户归属，不把SQLite或内部网络当作多租户鉴权。

保持Cairn Server、数据库结构、Fact/Intent/Hint模型和黑板读写/complete/reopen协议原样。改造集中在Dispatcher的调度接入、Worker后端、模型/工具适配，以及Wuji侧业务控制；不再给Cairn增加外部Task字段、原子停止态创建、操作回执或事务事件。 Wuji先保存原始Agent结果和本地操作记录，再通过原生Cairn API提交，成功后记录返回的原生ID及观察结果。请求失败需区分明确未发送与可能已提交；响应丢失按已知Project/Intent及原生读接口核对，能确认已提交则记录完成，不能确认则保持待核对。不得宣称原生API提供新增幂等回执、图版本或事务事件；不盲目重投写入，更不能重跑模型或目标。

## 4. 任务、派发与结果

草稿不创建Cairn Project。Task正式创建时由Wuji记录创建命令与执行配置，再调用原生Cairn创建并保存关联；原生Project可以是active，但所有未显式启动、未关联或许可不完整的Project均被改造后的Dispatcher拒绝派发。Task业务状态与Cairn探索状态分开，不要求核心支持ready或原子停止态创建。创建响应丢失则先核对；无法确认时保留结果不明，不按名称/时间猜关联，也不盲目再次创建。显式start接受后，只有配置、授权、预算、Worker和Kali Runtime均满足条件才允许调度。旧queued没有启动记录，永远不能被新执行器自动接管。

Dispatcher选择Worker配置后先申请AgentRun，再启动进程。worker_profile_id表达能力和容量；agent_run_id表达真实执行、认领、会话、日志与结果；execution_epoch和runtime_attempt限定当前许可。Intent仍有运行、停止核对或结果同步中的AgentRun时拒绝重复派发。Cairn的active/stopped及内存Future均不是执行许可或持久恢复依据。[上游调度状态](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/scheduler/loop.py)

Wuji先保存原始Agent结果和本地操作记录，再通过原生Cairn API提交，成功后记录返回的原生ID及观察结果。请求失败需区分明确未发送与可能已提交；响应丢失按已知Project/Intent及原生读接口核对，能确认已提交则记录完成，不能确认则保持待核对。不得宣称原生API提供新增幂等回执、图版本或事务事件；不盲目重投写入，更不能重跑模型或目标。取消前已接受结果可补入历史；取消后新提案不触发执行。旧回执读取不等于新执行许可。

## 5. 完成、取消与恢复

Cairn按原生语义记录探索完成，Wuji独立维护任务执行、停止、评估和报告状态。Core completed不直接等于全部进程已停或漏洞已确认；平台核对Agent/Kali活动执行、覆盖、证据和限制后形成自己的结论，可为partial。平台预算/取消通过外部执行许可和原生停止操作终止继续派发，不修改黑板核心完成语义；不自动reopen已交付任务，复测创建关联新Task。

暂停/取消先改变平台执行许可，再传播到Dispatcher、Harness、Tool Router、Runtime与出口。SDK abort和Pod删除请求均不是停止证明；不得假设能回滚已发往目标的请求。

执行是否仍在继续未知时保持reconciling并禁止新派发；已确认停止但结果缺失时保留结果未知和证据缺口，可部分结束，不写成成功或未复现。首次集成重启后先冻结派发并核对进程回执、会话及工具账本，不承诺无缝续接，不重新询问模型猜测原动作。

## 6. Harness、模型与成果

首个接入使用Pi coding-agent现成客户端、循环、会话、摘要与JSON事件；保留Cairn CLI适配方向，不同时接入多套Harness。关闭自动发现和默认本地执行工具，只加载受信扩展。提供绑定本次AgentRun的不可变快照读取、限定工作记忆、鉴权的黑板/证据查询；目标命令和文件操作走Tool Router/MCP，在Kali执行。禁用read后必须同时改造Cairn原来的文件快照交付。[快照实现](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/tasks/common.py)

组织模型配置由TenantAdmin维护，发布前要求同版本显式连接检查成功；无可用模型时只能保存草稿。Task设置USD金额预算，全部Agent、Reason、收尾、摘要和重试共用LiteLLM预算，不周期重置、不因换Agent或重建Runtime重置。上游Key只在LiteLLM；受限任务凭据只用于平台侧模型请求，不进入Kali。未知价格不按零计费，不承诺未验证的并发零超支。

关闭Cairn自动付费探活；readiness不请求模型。无效配置、权限拒绝、不支持工具等错误不按短周期重启Worker。结果不明先核对；收尾最多按既定单次流程且必须仍有预算，耗尽后不额外请求模型生成总结。

执行中的文件直接在共享Kali内交接：/workspace/agents/<agent_run_id>/保存各Agent工作文件，/workspace/shared/保存明确共享成果，/workspace/inputs/保存任务输入。Agent经MCP读写这些目录，黑板可记录发现及工作文件路径；协作不必先上传对象存储。正式证据、报告或长期归档再登记Artifact、内容摘要和版本，临时路径不冒充已归档证据。凭据通过受限引用共享，原文不广播。Fact表达共享发现，VerificationRun/Finding规则决定可接受结论。保留五场景、五主题、匿名Web、域名/子域授权；流量具体实现仍待设计，真实目标执行前必须有出口和停止边界证据。

## 7. 版本、实施依赖和验收边界

| 依赖 | 候选集成基线 | 状态 |
| --- | --- | --- |
| Cairn | 8e7e0ea67552383851dfcabfba0c4e9c8d007878 | 静态核对，所需适配/增量未实现；保留AGPL-3.0许可及上游来源 |
| Pi coding-agent | 0.73.0 | 首个Harness接入方向，未在Wuji验收 |
| LiteLLM Proxy | v1.100.0 | 网关选型已确认，未部署、未固定运行镜像digest或完成集成 |

Dispatcher/执行后端的必要适配保留明确归属，Cairn黑板核心不打补丁，不重写搜索策略、厂商协议或Pi上下文机制。候选失败报告具体原因，不静默换框架。

后续依赖顺序：控制面基础（0.5契约、配置快照、ready/start、epoch、AgentRun/工具账本、Task绑定）→调度适配（先合成工具）→共享Runtime→原型评审后的正式产品接入→真实目标开放。具体API、迁移和验证入口由对应Spec/Plan冻结；旧0.5草案不能直接施工。

原架构收口只更新文档；2026-09-11用户授权并完成[运行基础库离线验收](stages/phase-1c-runtime-foundation/acceptance.md)，完整执行尚未接入。Phase1A保持partial，P0仅限原实验，业务仍0.4.0。共享预算累计508/600秒、剩92秒，真实4次额度已用完，不按重拆批次重置。文档仅diff/链接检查；后续最小场景为未启动不派发、同一Task Pod的agent容器内两个AgentRun共用kali容器、结果核对不重跑、工具越权拒绝、取消与迟到派发、旧queued不执行；不足则待测，不预先标集成通过。
