# Agent Harness 与平台侧 Worker 接入

- 日期：2026-09-10；2026-09-11状态更新：核心Cairn/Pi/LiteLLM/双容器Task已通过封闭夹具验收，见[记录](stages/phase-1c-task-creation/acceptance.md)。W1已通过真实Pi原生压缩及压缩后持久记录读取，见[W1验收](stages/phase-2-web-assessment/acceptance.md)；长期记忆质量与真实模型效果仍待验收。
- 权威取舍：[架构替代决策](cairn-architecture-decision.md)；完整部署见[主架构](architecture.md)，共享图协议见[黑板设计](cairn-blackboard-design.md)。
- 历史：6ee84b5中的LangGraph/Deep Agents首选方案已被替代。[P0验收](stages/phase-1c-prep-p0/acceptance.md)仍只证明原受限Deep Agents/客户端实验，不证明Pi、Cairn或LiteLLM已可用。

## 1. 复用边界

目标链路使用Cairn Dispatcher + Pi coding-agent + LiteLLM。Pi提供模型客户端、Agent循环、上下文控制、会话和摘要；Cairn提供探索调度，Wuji补执行准入、工具接入、身份、持久交接与停止核对。LangGraph/LangChain/Deep Agents不再是必选依赖，不运行第二套探索调度器。

首个Harness以Pi 0.73.0为固定集成基线，复用Cairn现有Pi CLI驱动及JSON事件模式，不同时接入Claude/Codex/Pi多套实现。一个AgentRun绑定一个Harness版本及会话。未来更换SDK属于Worker适配变化，不能借此重写模型协议或压缩算法。

2026-09-11复审续接：原生阶段输入可能经Pi压缩成为摘要，不能靠初始提示保证合同无损；[阶段合同/记忆/成果交接提案](stages/phase-1c-task-creation/execution-handoff.md)的持久配置、调用记录和受限扩展已按核心/W1合同落实；graph_refresh、assessment_read和evidence_read读取受鉴权记录。不能宣称仅放置镜像AGENTS文件就会被禁用自动加载的Pi驱动读取。

Pi当前提供CLI、RPC与SDK入口，以及内置工具关闭、显式白名单和扩展能力。[固定版本文档](https://github.com/earendil-works/pi/blob/v0.73.0/packages/coding-agent/README.md) 这些是静态能力依据；Wuji已验收受限工具往返、取消核对及原生压缩机制，通用MCP/浏览器、多模型与完整恢复矩阵不在该证据范围。

## 2. Worker与Kali分别管理

每Task一个Pod，包含agent与kali两个容器。多个Harness进程在agent容器内运行并分别绑定AgentRun，不嵌入API/Dispatcher或放入kali。Cairn执行后端管理agent进程；Task Runtime Controller唯一管理Pod创建、重建和回收。一个有效attempt供同任务所有Agent和Kali工具共享。

Cairn ExecutionBackend接已就绪Task Pod中的agent容器；新增后端必须同时接入配置选择、执行上下文、进程回执和cleanup调用。不能只新增一个类就声称Kubernetes适配已完成。[上游接口](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/runtime/backend.py)

两个容器分别挂载工作卷/凭据，不共享PID空间；网络边界以整个Task Pod为单位。目标操作经工具接口，不能把Pod级NetworkPolicy当成容器间隔离。Kubernetes管理权限不交给Harness或Kali，Kali不持有Provider、Cairn管理或平台数据库凭据。

## 3. 明确工具表面

关闭本机扩展、Skill、模板和上下文文件自动发现；只显式装载平台发布的受信扩展和版本化知识。关闭默认本地执行工具，在Harness与服务端同时校验允许工具集合。Pi支持`--no-builtin-tools`、`--tools`，以及`--no-extensions`配合显式`-e`；参数组合须在候选版本验证，不以提示词禁令替代能力限制。

| 类别 | 实现边界 |
| --- | --- |
| 快照读取 | 只读取本AgentRun分配的原生查询快照（由Wuji保存采集内容），不接收任意平台路径 |
| 工作记忆 | 每AgentRun限定存储；不具备目标访问或平台业务写权限 |
| 黑板/证据读取 | 通过平台鉴权接口，核对Task、版本和引用权限 |
| Kali命令/文件/浏览器 | 通过Tool Router/MCP，在同Task当前Kali attempt执行 |
| 人工介入 | 提交Hint、具体问题、范围扩展申请；不能直接修改授权或控制状态 |

Cairn原生要求Agent读取其写入的graph.yaml；删除Pi的本地read工具时必须同步提供快照读取能力并调整模板。[原生交付点](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/tasks/common.py) 不把快照文件路径误当成Kali路径。

远程命令、文件操作和浏览器工具不改变运行分层；Kali脚本仍可工作，但必须通过受管工具能力。工具名、模型自报任务ID和MCP session均不能承担鉴权。长命令通过稳定执行句柄等待/停止，不依赖模型忙轮询。

## 4. 输入、输出与结果持久化

WorkerAssignment由平台从配置快照及当前许可装配，包含Task/Intent、worker_profile_id、agent_run_id、execution_epoch、runtime_attempt、允许模型/工具、快照和证据引用、截止时间及输出要求。Worker配置用于能力/容量；实际执行身份用于认领、会话和结果，不能混用。

模型不能提交任意归属字段以切换Task。Cairn原生accepted/data业务JSON保留，平台适配外围登记真实执行、证据和限制。结构校验通过不表示漏洞真实或授权充分。

Wuji先保存原始Agent结果和本地操作记录，再通过原生Cairn API提交，成功后记录返回的原生ID及观察结果。请求失败需区分明确未发送与可能已提交；响应丢失按已知Project/Intent及原生读接口核对，能确认已提交则记录完成，不能确认则保持待核对。不得宣称原生API提供新增幂等回执、图版本或事务事件；不盲目重投写入，更不能重跑模型或目标。

执行中的文件直接在共享Kali内交接：/workspace/agents/<agent_run_id>/保存各Agent工作文件，/workspace/shared/保存明确共享成果，/workspace/inputs/保存任务输入。Agent经MCP读写这些目录，黑板可记录发现及工作文件路径；协作不必先上传对象存储。正式证据、报告或长期归档再登记Artifact、内容摘要和版本，临时路径不冒充已归档证据。成果凭据以受限引用共享，不广播明文。

## 5. 模型访问与上下文

Pi原生客户端连接LiteLLM，组织已发布模型的上游Key只在网关。平台侧Worker只能使用Task限定的模型凭据，不拥有管理权限；Kali不接收模型凭据。默认配置不复用开发者真实主目录、模型登录态或P0私有凭据文件。

组织模型配置无Task预算项；Task金额预算USD由LiteLLM原生执行，全部Agent/Reason/Bootstrap/收尾/摘要共用，不周期重置，不因重建环境重置。上下文容量和Token统计独立于金额限制；未知模型容量/价格不猜测，未知价格不按零。

Cairn自动付费健康检查关闭，发布要求管理员显式触发同版本连接检查；普通readiness不调用模型。配置错误、权限拒绝或工具不支持不能以短周期重启Worker解决。网关/客户端/Harness的自动重试须显式收敛，结果不明先核对；不得静默增加付费尝试或切换模型。

上下文历史、裁剪、摘要和大结果卸载只由Pi负责。Gateway不二次编排会话，黑板不保存完整聊天历史。当前Scope/epoch从平台取得，不依赖摘要记住授权；来源内容保留数据身份，不升级成系统规则。摘要/收尾同样计入Task预算，预算耗尽不额外调用模型总结。

## 6. 停止与恢复

取消先改变平台执行许可，随后停止新模型/工具派发，并分别核对Harness和Kali后台工具。请求abort或删除Pod不等于已经停止；停止进程不承诺回滚目标效果。停止已确认但结果缺失时保留未知结果；是否仍执行未知时禁止重派并进入reconciling。

Dispatcher/Worker重启后先冻结相关派发，核对持久AgentRun、进程回执、会话与ToolCall；首次集成不承诺无缝恢复。不通过重新问模型猜原动作，不让新会话ID绕过已有调用记录。会话已删除时明确不可恢复。

会话/日志/快照按Task数据分类保存；原始事件不直接作为公开Task事件，不公开隐藏推理。首版执行观察可显示Agent状态、工具调用、产物和最终结果；完整逐Token流和协议矩阵不属于本批文档验收。

## 7. 当前证据与后续边界

- [核心验收](stages/phase-1c-task-creation/acceptance.md)：真实Cairn/Pi/LiteLLM、双容器Task、跨Agent文件交接、结果核对、取消及原生金额拒绝；被测候选及复用证据分别记录。
- [W1验收](stages/phase-2-web-assessment/acceptance.md)：被测f12a46f，真实Pi compaction_end及压缩后受限持久记录读取；使用合成上游，不证明自主推理或长期记忆质量。
- [P0验收](stages/phase-1c-prep-p0/acceptance.md)：原Deep Agents实验及4次真实调用的历史事实，不能作为Pi验收。

本次文档不重跑业务验证。完整流式/恢复、多模型、长上下文质量与生产运行按[后续清单](predevelopment-plan.md)另行安排；真实模型效果须有明确新增USD授权。
