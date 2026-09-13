# P07 MAF Worker 实施接口收口

日期：2026-09-13。主代理设计；依据已批准 Spec S08/S09/S10 与 P07 Plan。此文为 P06 执行期间的依赖准备，P07 生产实现须等最终 P06 公共交接和明确 START。测试、验证及常规修复由 SOL/xhigh，核心生产实现可用 GPT-6/xhigh。

## 工厂与调用权威

只在 `wuji_maf_worker` 适配包引用 MAF 类型。采用 P01 固定发行物和公开 `create_harness_agent`/`Agent.run`、Session、HistoryProvider、FunctionMiddleware、原生压缩策略；不复制 Agent 循环、不调用或补丁私有函数、不导入探针脚本作为生产运行时。Reason/Explore/Report 由固定 Profile 选择组件和指令，执行资格始终来自平台。

WorkerAssignment 只含运行引用，不能兼任发布配置。通过内部配置读取端口解析并校验固定版本、摘要、lock、已发布能力与 Run 身份；缺失即阻断。Worker 仅持 Run 限定凭据；模型地址指向 P06 Gate，Task Gateway Key 不进入 Worker。SDK HTTP 重试显式关闭。每次实际 HTTP 推理产生独立逻辑请求 ID，通过可信传输层交给 P06；不能按文本相等复用。Reason、摘要、压缩等模型请求都走同一 Gate。

P06 的 RuntimeProfile 负责执行准入参数；P07 的 HarnessProfile 独立固定各 work_kind 的组件/指令/压缩/上下文上限。部署在 Task 首次激活前，将已发布 HarnessProfile 引用、版本与正文摘要一并写入不可变 TaskDefinition 的 `worker_profiles` 快照，并纳入 definition_digest；WorkerAssignment.profile_refs 使用既有有界字符串引用。不能给已经发布的 RuntimeProfile 同版本偷偷增加 Harness 行为，或在执行时按名称读取最新 Profile。缺少 worker_profiles 的旧任务不会自动得到 MAF 执行资格。P09/P11 后续装配新 Task/Work 时消费该绑定；P07 前提夹具明确预注册，不声称正式创建 API 已接通。

首个受控 Profile 使用非空显式工具清单。Mode、默认 Shell/WebSearch/文件访问、自动审批、后台子 Agent、外层循环和自动 Skills 发现关闭。可选 Todo 默认关闭；需要开放时必须登记实际原生工具名和状态版本，不能仅因为 SDK 默认提供就发布。文件记忆通过版本固定的存储适配与后续 P08 manifest 衔接，不给 MAF 本机 home、环境变量或任意路径。受控工具、原生审批和受支持会话恢复是核心，不能以缩减 Profile 无限延期。

## 上下文与原始记录

`build_context_bundle(records, read_set)` 为内部纯构建函数，调用者是经过当前授权检查的快照/资料服务适配；不能从模型参数或任意前端记录直接注入。ContextBundle 是内部类型，不为此发明外部 API；如确需外部 DTO，仍由单一 OpenAPI 生成。

每条资料保留精确引用、版本、来源、Claim epistemic 状态、支持与反对证据、适用条件、失败尝试和未覆盖原因。只对正文做清晰的数据边界包装，不把资料内指令变成系统/工具权限。事实标签只能使用 P04 当前受权聚合结果，不能在 Worker 自行评估或把没有评估的候选写为 Fact。相同预算下取舍资料须保留相关反证或明确缺失原因，不能只筛支持当前假设的项。

新的独立 Reason 使用新 Session；同 WorkItem 输入/审批续接需平台提供已发布可恢复 manifest。ContextBundle 固定 snapshot_id/read_set；刷新建立新快照和明确增量，不替换旧输入。每次真实资料读取重新授权，固定版本不冻结旧权限。read_set 来自实际引用记录，连同原始结果封存后交 P04 接纳。

## 工具调用身份与 MCP

工具名、描述、参数 schema 和版本从受信发布配置生成；实际广告表必须与其一致。MAF 负责调用已注册函数；函数适配只转发到 P06 同一 ToolAdmission。注册服务从可信 Run 身份推导授权，不采信模型参数里的 Task/Run/URL。

平台资料读取应作为明确注册的工具能力。P06 首片的 workspace_read 不能冒充按当前 ACL 读取黑板记录。P07 可窄增 `platform_record` 工具目标类型及 RecordReadExecutor：参数为精确 KnowledgeRef，服务端限定同 Task 与已发布实体类型，沿真实请求主体当前数据权限调用已有 P04 FactLedger/受限 Artifact 读取端口；不将平台地址加入目标 Scope、不接受任意 URL，也不把 Agent 改成 collector/controller 主体读取。首版 read_record 可明确限于已有正式读取端口支持的 claim/intent，Artifact 用单独受控读取；Observation 等扩展复用 P13 后续统一映射，缺适配即不可发布。此增量在 P06 最终共享文件交接后实施，普通函数/MCP仍走同一准入、次数与回执；固定复制资料文件或内存读取不能替代当前权限重验。

平台记录读取的捕获要标明是已有记录/资料的派生读取及来源引用，保留继承的数据级别，不伪装成一次新目标验证。工具返回依据实际受权读取和保存的 EvidenceReceipt，不依赖可选 FactExtractor。后续进展规则不能仅因为重复读取产生新 Artifact ID 就认定发现新材料。

使用公开 FunctionMiddleware/FunctionInvocationContext 读取 SDK 实际调用元数据，保留 provider call_id 与 framework occurrence/content ID。原消息身份由实际 Message/History 观察建立并持久化映射；不能用参数摘要、新 Run ID 或模型自报标识替代。恢复沿用已发布映射。当前固定发行物会在函数 middleware metadata 提供 `call_id` 和 `function_call_occurrence_id`；实际消息映射时序须由 SOL 的真实 SDK 往返验证，不能仅凭源码阅读认定。缺少可证明身份的调用阻断，不猜 ID。

函数 HTTP 与 MCP 传输都携带同一规范调用身份到 P06。MCP 使用官方客户端/服务端类型和真实 transport，允许以 MAF 注册函数包装官方 ClientSession 调用；不要求使用会自动发现附加能力的包装器。首版只连部署登记的受控 MCP 适配服务，不接受模型提供的地址/命令，也不默认启用 prompts、sampling、elicitation、roots 或动态 tools/list 扩权。远端广告与固定 ToolDefinition 必须一致才发布。

运行凭据从传输闭包或受控上下文提供，不放进通用 `function_invocation_kwargs`、模型参数或可被 MCP schema 声明读取的字典。模型可提供的 `_meta` 不能覆盖平台身份。MCP 请求 ID 只是协议关联，不替代逻辑 ToolCall。transport 断开后沿原操作查询，不能借重连新建执行；无重试开关的组件仍须由 P06 稳定操作身份避免副作用重放，实际行为如实验证。

## 执行、事件、保存和取消

`AgentRuntimePort.execute(WorkerAssignment)` 的 AsyncIterator 属于 Supervisor/Worker 内部。Worker 主入口在自身任务内持续消费 SDK stream 和保存接收记录，不能把底层 SDK iterator 直接绑到浏览器连接。UI 订阅之后消费平台持久事件；UI 断开不取消执行。Worker sink 失败必须暴露错误/不明边界，不能继续丢弃唯一原始输出后报告成功。

事件只映射实际观察的 SDK 消息/工具/审批或适配器事实，内部类型明确来源，不捏造原生 checkpoint/停机成功事件。保留原始 SDK 输出和最终原始文本，可信 envelope 由 Worker 生成后走 P04 raw-first 提交；非法 AgentPayload 保留原文并返回真实拒收状态，不由 Worker 偷修成成功结论。

原始 SDK/模型响应按对应敏感级别受限封存，公开 WorkerEvent、UI 和 Trace 只使用明确字段白名单；不能因为保存了原始响应就默认导出私有推理、完整 Prompt、凭据或任意 Provider metadata。工具原始参数若有 SDK 转换前的精确 JSON 表达，应保留该原生调用数据并在 Gate 严格解析，不能让经过浮点转换的参数悄悄替代原逻辑调用摘要；实际可用时序与精度由 P07 的公开 SDK 接口测试确认。

`cancel(identity, reason)` 在本进程发出取消并等待受限本地退出，返回仅表示实际观察到的本地事实；当前许可撤销及最终资源结算归 P05/P10/P11，远端模型或工具未知不可写 stopped。`deliver_input` 只接平台已登记的 delivery，真实原生审批响应必须与保存的原调用配对；持久去重/消费归 P08/P11。任意运行中聊天注入未证明则明确不可用。P07 提供组合端口及原生转换，不能把内存 ack 当持久 delivery 或审批已执行。

P08 拥有不可变对象、单写者 CAS、manifest 发布与审批原子消费；P07 提供公开 SDK Session 序列化/恢复和 boundary export/import。settled_boundary 与 approval_boundary 必须同时保存所需 Session、完整原生待批 Content、消息身份映射、Provider/history/memory 状态。没有已发布边界时不启动恢复；单独一个 Session JSON 不够。

## 压缩与验证分工

压缩复用真实 MAF 的公开策略和 factory 参数，Profile 固定策略及上限，禁止自研摘要/压缩算法。原始资料、回执和已发布对象不被压缩改写。每轮独立注入的 ContextBundle 保留证据与 epistemic 状态；压缩历史后的摘要不得将假设升级。只在已结算边界或真实审批边界使用经过验证的组合，运行中任意崩溃恢复仍关闭。

SOL 负责首个有意义 RED、实际 SDK→P06 Gate→合成模型→真实工具→第二模型请求的验证，并检查非空广告表、未登记工具不执行、当前撤销在函数/MCP真实transport一致生效。必须真正触发原生压缩，检查恢复后的历史、工具消息配对、资料状态及原始证据字节；只观察 compaction 事件不足。P08 完成持久发布前，不把 P07 序列化结果标为完整 AC-043/G2 通过。测试夹具只扮演外部模型/无害工具和数据库前提，不实现产品准入/结果账本。实际命令使用既有 `scripts/vnext/uv.sh`，不重跑无变化探针或旧核心。
