# 核心任务闭环：统一终点与连续实施计划

状态：**approved / in-progress**；2026-09-11。用户在Plan模式确认封闭夹具闭环、Reason主动补证交Explore，并以PLEASE IMPLEMENT THIS PLAN批准完整核心计划。当前已切回Default执行模式。以下历史草案由用户批准版及[实施合同](execution-contracts.md)具体化：交付wuji-test/4182，开发专用Artifact持久卷，原生框架不替换；M1—M4连续实施，不再重复索要小切片批准。

本文件是后续计划的总入口。[D3-B Spec](spec.md)/[Plan](plan.md)是其中 M1 的详细任务书，[调度合同](execution-handoff.md)是 M2/M3 的设计输入。ready 是内部开发里程碑；后续按依赖连续实施，不在每个小提交后重新发起同内容的方案审批或扩大测试。

## 1. 最终交付

先交付一条可重复、可追溯的核心执行链路：

**真实任务与配置 → 显式启动 → Cairn调度 → Pi受控工具 → 同Task共享Kali → 原生Fact与可读取证据 → 明确结果 → 已核对的停止。**

首条验收使用自建 HTTP 夹具与确定性模型协议上游，经真实 LiteLLM、Pi、Cairn 与 Kubernetes 路径运行。合成上游只替代推理服务，不在前端假造 Agent/Fact/Task 完成。这能证明平台集成链路，不能证明真实模型渗透效果或完整覆盖能力。

同时覆盖用户取消：先撤执行许可，再停止/核对 Harness 与 Kali 后台工具，停止确认后显示已取消；未确认则 reconciling。单纯 ready、API 202、Pod 删除已接受或 Cairn complete 均不能满足最终交付。

五场景保留模板和草稿，本轮只开放 Web 核心。真实模型费用和真实外部目标仍受既有授权；先不追加付费请求，不把“加快开发”当新额度。

## 2. 内部里程碑与依赖

| 里程碑 | 实际交付 | 结束判据 | 紧接工作 |
| --- | --- | --- | --- |
| M1 创建基础（D3-B） | 精简创建页、真实草稿/授权、Goal及配置快照、ready；D2模型页面只补核心必需功能 | 用户输入能持久恢复，原键不会重复创建，快照/权限/范围一致 | M2，无需再次为ready做一轮产品设计 |
| M2 执行控制 | start消费者、epoch/AgentRun/ToolCall/attempt、Cairn绑定、LiteLLM任务受限预算、运行配置绑定 | 未启动/旧queued拒绝派发，start有持久消费者，取消先关闭许可 | M3 |
| M3 调度与共享执行 | 原生Cairn阶段、Pi明确工具表、Task Pod双容器、共享文件/HTTP夹具、持久结果和原生写回 | 真实工具→观察→Fact/文件，结果同步失败不重新探索 | M4 |
| M4 观察和结束 | 最小任务执行页、Agent状态/调用/证据、完成依据/未完成项、停止核对 | 一条正常闭环及同一路径取消检查有证据，历史可只读查看 | 核心交付，不转入新一轮表单打磨 |

架构由主代理负责，公共契约、迁移及锁文件唯一负责人；可选子代理仅实施冻结范围。每个里程碑可以提交代码和记录必要检查，不要求一次大提交或等所有模块完成才发现集成阻塞。批准整体方案后持续推进；发生实质新设计才更新方案，不以分支/文件拆分重置测试或请求批准。

## 3. M2 的控制契约

公开创建/查询/事件复用 M1。start 只在当前候选具备实际消费者且运行配置有效时加入既有 task commands：
- 请求 action=start、expected_version，使用与create/cancel相同用户/项目/UUID幂等键空间；先鉴权和查原回执，再处理新启动前提。
- 仅新 web_assessment ready 可首次启动；历史queued明确拒绝。start持久写入命令、执行记录和epoch后返回202；没有消费者时不注册/不接受。
- Task状态按现行架构 ready→queued/provisioning→running→completing→completed；取消进入cancelling，执行未知reconciling，已确认停止才cancelled。首个闭环不顺带开放pause/resume或自动重启恢复。
- completed只说明执行闭环已结束，assessment/Goal结果另外表达。没有漏洞不等于安全，预算结束不等于Goal达成。

权威记录由 Wuji PostgreSQL 保存并提供真实 PermitSource/ControlSource，替换现有基础库的协议占位：
- TaskExecution：task、start_command、epoch、创建/执行快照、当前attempt与许可/停止原因。
- AgentRun：独立run/session、phase、worker_profile、原生intent（适用）、epoch/attempt、进程回执、执行状态、result_sync_state。
- ToolCall/ToolAttempt：稳定调用/尝试ID、归属、规范参数摘要、允许工具/目标、发送与执行回执、结果/停止/unknown状态。
- TaskRuntime：attempt、Pod/容器引用、UID、配置版本、准备/停止/回收状态。
- AgentResult/BridgeOperation：先保存原始结果和校验状态，后调用原生Core；存在待同步结果不重新派发同一Intent。

每次派发与工具调用读取当前许可，runtime_attempt与execution_epoch同时匹配；取消用递增epoch拒绝迟到许可。lease/原生claim过期不证明旧进程已停，未知实例禁止重派。ToolAttempt重试须有明确分类与新记录，不能让“重试”抹掉原结果不明。

具体迁移接0006继续顺序追加，不放松旧Task的执行保护；RLS/复合归属、写入单一控制主体、锁顺序与原生操作恢复在业务实现前纳入本计划附录，不让开发代理自行决定。

## 4. 模型和配置绑定

创建快照固定用户Goal/授权/模型/价格/金额；执行快照固定真实运行镜像、工具/Prompt/Pi版本及当前平台策略，不能填占位UUID。允许用户核对后启动，不把其理解为重新创建另一种Task。

使用LiteLLM原生Task限定凭据与max budget能力，全部Bootstrap/Reason/Explore/收尾/压缩共用，不周期重置；受限凭据只进agent容器。网关管理及上游Key在网关/控制服务，Kali无模型凭据。原生创建凭据结果未知先核对，不能重建预算清空花费。

启动前需核对固定LiteLLM版本的实际凭据创建/查回/阻断与预算执行字段、并发和计费限制；不自建金额引擎填补不支持能力。合成模型以明确用量返回和合成公司价格验证累计，费用缺失标未知；不能用D2连通/发布证据代替预算证据。

不做付费探活或自动fallback；普通探针不调用模型。真正的预算耗尽停止新请求并核对在途调用；不为补总结额外调用模型。若固定版本能力/许可证不足，作为这条核心链路的具体阻塞报告，不静默换组件。

## 5. Cairn与Pi的实现边界

只改Dispatcher接入与执行后端/模型/工具适配；Cairn Core与原生图协议原样。Task创建只保存本库状态；唯一绑定消费者按已知引用接原生create/查询核对。未绑定、未启动或无许可的Project全部拒绝派发，即便原生active。

原生阶段继续Bootstrap/Reason/Explore并发语义，不设计固定安全角色流水线。首批建议Reason将主动补证提交普通Intent给Explore；持久覆盖/尝试及已有证据可读。若需要Reason内补证，按execution-handoff列出的完整身份/Intent/conclude路径处理，不仅放开一个data.fact字段。

Pi关闭自动发现与默认平台本地执行工具，仅显式加载可信扩展。只允许：
- 绑定本AgentRun的图/任务/结果快照读取；
- 受限工作记忆和本Task文件/证据查询；
- 已授权的工具执行及稳定句柄等待/停止；
- 提交受控结果或问题，不直接修改授权/Task状态。

阶段提示从持久合同装配；压缩复用Pi，工具账本与成果独立持久。收尾合规与原生业务结构分别校验；解析失败保留原始输出，不自动重跑工具。每阶段结果先保存，再写Core/查核；Cairn图采集摘要不冒称跨接口事务版本。

## 6. 共享Task Pod与受控夹具

复用task-runtime包的官方Kubernetes SDK、UID/归属核对和单Pod双容器manifest；Controller管理Pod，worker后端只管agent容器进程。两个AgentRun通过各自会话和调用身份共用一个Kali attempt；分别目录，共享成果使用/workspace/shared，不能靠目录名代替权限。

Supervisor必须提供实际调用与进程句柄、等待、停止、文件状态/摘要；返回命令完成不等于HTTP验证结论成立。一个合成HTTP适配器用于首条fixture路径，工具以结构化参数指定已批准夹具URL；不开放任意宿主机Shell或绕过范围的代理地址。

夹具运行在隔离测试环境，通过明确配置的受管出口访问。先验证集群策略实际可执行，不能因Docker Desktop中有Kubernetes就宣称NetworkPolicy生效。工具层目标校验加Task网络边界共同约束；平台Service/元数据及未批准目的地拒绝。暂不设计完整外域依赖/代理池/HTTPS流量矩阵。

若现有CNI不能实现所需限制，不假装真实目标可用：本批可继续无目标合成工具接入，但HTTP/网络边界保留未通过，不标核心完整验收。真实外部目标开放需要后续已确认的完整出口方案，不能用本夹具唯一地址硬编码当产品策略。

关键文件先核实路径、状态、来源和摘要，同Task可直接交接；正式证据登记Artifact并保存可访问内容。首版文件对象存储使用已选架构接口；若服务未部署，先实现受限持久存储适配，不把Kali临时路径冒称已归档。Core Fact只引用内容和来源，不保存明文凭据。

## 7. 最小执行观察页面

沿用现有Task详情和五主题，只增加支撑闭环的信息：
- 当前状态与原因、启动/取消命令核对；
- 本次执行的AgentRun状态、阶段与工具调用，区分运行/待同步/未知；
- 目标/完成条件、Fact增量、证据及共享成果引用；
- 已测试、未测试/阻断与明确结束原因；
- 停止核对及清理状态。

前端通过Wuji鉴权API/事件读取，不直连Cairn/Kubernetes/MCP/LiteLLM；图不是主页面必须完成的可视化大屏。只展示实际证据，不以假数填预算、覆盖率或漏洞。无完整报告引擎时交付确定性结果摘要，不追加模型总结请求。

## 8. 统一验收和停止条件

只维护一个核心验收清单，不累加每个历史阶段的完整测试：
1. M1必要权限/范围/幂等/快照检查一次。
2. 合成上游经真实网关与Pi，产生一个工具请求及真实返回；记录实际AgentRun/ToolCall、模型用量来源。
3. 同Task两个AgentRun共享一个Kali attempt，交接一个文件；无越权工具，身份与目录可追溯。
4. 正常结果先持久化，写原生Fact并在详情读到证据/结论；一次写回未知核对不产生新探索。
5. 通过同启动路径取消正在等待的工具，旧epoch派发被拒绝，Harness与Kali句柄停止有回执；未知保持unknown。
6. 未启动/旧queued不派发；Task金额统一累计且不因Agent/attempt重置；没有真实付费调用。

同一固定候选完成一次核心联合验收；前置模块仅做直接必要检查。通过后不扩张长压缩/故障/主题/压力矩阵，不为增加信心重复测试。真实模型能力、复杂漏洞效果和流量覆盖明确延期。

交付记录绑定SHA、run_id、启动/结束对象、真实命令/退出码、实际请求次数及未覆盖项。M1完成可记录代码交付，但只有M4必要链路有证据才能说“核心闭环已完成”。
