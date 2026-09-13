# P06 模型与工具准入接口收口

日期：2026-09-13；主控制器负责。依据已批准 Spec S05—S09/S13/S14 和 P06 Plan。P06 仍需最终 P05 handoff、迁移头及明确 START。

## 所有权与身份

P06 复用 P05 控制/容量 UoW 和真实父记录，追加 ModelCall 及同一 ToolCall/ToolAttempt 的准入与结算字段；不得另存 Task/Work/Run 可执行状态或金额计价表。所有前置 pool 锁按 P05 顺序取得，再锁 Task/Work/Session/资源。

Run 请求先验签，再以 Principal.subject/token_id 查询服务端 Run credential binding，检查当前撤销、期限、Task/Work/Run/receiver/runtime/环境和固定配置；请求里的 identity 只能作一致性校验。允许扩展当前 run_writer 关联为有明确用途的 Run credential binding，但结果写、模型、工具、采集能力分别赋权，不因持有某种 Run 凭据自动获得全部权限。普通旧 Run 凭据不得用于停止后的新请求；内部 settlement 主体有单独的受限资格。

P05 的 control/observe/admit 权限面向人类或可信控制服务，不直接授予 Agent。P06 可在同一 UoW 增加 `model_request` / `tool_request` 的限定用途入口：先核对真实 Run binding，再进入同样的前置锁顺序，只给对应账本/计数/操作所需的数据库权限。不能伪造 controller Principal 或给 Run 增加 can_control/can_admit 来绕过限制。

所有规则读取冻结的 TaskDefinition/Profile refs 和当前控制事实。缺少 P05 依赖、恢复/环境证明或已发布能力则阻断；不能以 caller booleans 补齐事实。

## 模型路由与私有 Key

生产端口 `TaskModelRouteResolver.resolve(task_id, model_profile_ref)` 提供冻结的模型别名、已验证协议、网关地址、Key secret ref 和受限转发配置；`TaskGatewayKeyResolver` 仅在 Gate 内解析秘密。Assignment/Session/Worker/Kali/普通日志均不含 Task Key；上游管理 Key 仍只在 LiteLLM。

可复用经确认无 Cairn 依赖的既有 LiteLLM 管理适配；新核心默认缺配置即 CAPABILITY_UNAVAILABLE，不回落为测试 Key。首版用部署注册、版本/摘要固定的模型与 Runtime Profile，发布状态和已验证能力必须明确；管理 UI 的完整衔接另由对应集成任务完成。测试 resolver 只提供明确的合成配置/Key，不能伪装 LiteLLM 计费结果。

协议采用已验证的 Chat Completions。原生 tool_calls、content omission、created/usage integer 和成功响应/流保持协议形状；Wuji 自己的计数/修订字符串不改变供应商字段。不支持的托管工具、远程 Agent 或协议能力明确拒绝，不静默丢字段。上游地址/模型由配置选取，不能来自模型/MCP 参数。

## 请求身份与累计口径

`X-Wuji-Request-ID` 是 Worker 提供的每次逻辑模型请求关联 ID，不是授权凭据。Gate 派生真实 Run 并生成 model_attempt_id；可靠关联时保存 logical_request_id，否则 grouping_unknown。request.state.request_id 仅作这次 HTTP 跟踪。

同 Run/请求 ID/完整请求摘要重复到达不得再次发起推理。已完成且保留完整响应时可返回原始协议响应并注明 replay；在途、部分或响应不明时返回明确状态/核对入口，不补造回复。新的请求 ID 即使同文本也是新的推理尝试。提供受权 `GET /internal/v2/model-attempts/{id}` 回执/响应状态查询，只读不计新推理；结果内容按当前数据权限限制。

max_model_requests 计入每个已提交准入的实际尝试，包括之后失败/未收到响应及显式重试；明确的准入拒绝不算新执行。保守的已用调用额度不因客户端失联、服务重启、换 Session/Run 或换环境返还。发送/响应/费用另有各自状态，因此次数消耗不等于已经产生上游费用。全部 Reason/Explore/report/摘要/压缩/repair 使用同一 Task 累计。

max_tool_calls 计入每个获准执行的 ToolAttempt（包含显式重试），不能让一个逻辑 ToolCall 的多次尝试免费。等待审批的逻辑提议尚非执行尝试，但受配置中的待处理操作数量上限限制。身份/策略拒绝记录审计，不伪造为目标执行。模型与工具输出共用 Task 累计输出额度；具体类别计数可另展示。

P05 的 AgentRun 预留已经占用相应 global/model/tenant 池，模型请求不能再次预留同一 Run 池而造成自我阻塞。首版每 Run 同时最多一个实际在途模型请求，使用持久约束并在退出/响应核对后解除；额外请求可明确等待/拒绝，不假称已执行。需要更多并发时另加明确的调用池策略，不把 Agent 槽位重复计数。工具并发使用独立的 RuntimeProfile 操作上限和资源锁，仍不释放或重复预留 Agent 槽位。

字节口径区分 received/retained/forwarded。Task 的输出 hard limit 约束应用接受/保留/向下游交付的字节，准入/分块计量在真实锁事务内防止重复分配；到限停止新增接收/转发并保留部分原因。底层 socket 预读不宣称为已验证的零字节超限。RuntimeProfile 明确单 chunk/buffer、单响应、总输出、idle/总时限、待处理操作数；生产缺项不可发布，测试数值只属于夹具。

金额累计、价格和上游费用由 LiteLLM 原生实现；平台只保存 gateway usage/spend refs 和独立 billing state，不推算另一套金额预占/结算。异步账单未到不被解释为免费，也不自动阻塞已确定结束的纯本地执行。

## 工具操作、审批与执行端口

ToolOperation 在本阶段就是规范 ToolCall 的逻辑执行身份，operation_id 复用 tool_call_id，避免第二套可独立变化的操作记录。它的唯一业务键为 Session lineage/原消息身份/provider call_id/ToolDefinitionVersion；SDK content/approval ID 另行保留。ToolAttempt 表示实际尝试与当前运行持有者。相同键不同参数冲突；新 call ID 同参数仍是新操作。

新增受限 HTTP `POST /internal/v2/tool-calls`、`GET /internal/v2/tool-calls/{id}` 和 `POST /internal/v2/tool-calls/{id}/cancel`，在单一 OpenAPI 中固定调用/回执 DTO。调用体包含固定工具版本、上述逻辑标识、参数及可选 approval_ref，不含自授身份。取消仅提交意图，实际状态仍由回执核对。查旧回执先核对当前权限。

函数和 MCP 适配都进入同一 ToolAdmission 服务。P06 可提供生产规范化适配端口及官方 MCP 请求类型转换，不能自行编造一套 MCP 协议；完整 MAF/MCP transport 接线属于 P07。报告只声称实际验证的适配层，不以两个同名函数冒充传输协议测试。任意 MCP URL、自动下载工具、任意 Shell 都不开放。

真实执行通过 `ToolExecutorPort.dispatch/query/cancel`：使用注册接收者、短期许可、当前 epoch/attempt/receiver、工具版本、参数摘要、期限和资源 key。P06 的隔离外部工具夹具必须真正执行无害文件读取等操作，不能模拟准入/账本。正式 Kali/Supervisor 接线由 P10/后续 Runtime 集成完成，P06 不把本地夹具称为生产出网能力。

Task/Run/工具版本和当前许可通过后，先持久 ToolAttempt/dispatch 记录再发网络；请求不明只查原 operation，不换 ID 重跑。外部调用不在长数据库事务内。执行端回执和独立采集产生真实字节/Observation/EvidenceReceipt 后才向 Agent交付结果；缺 FactExtractor 不阻塞。直接复用 P03 采集绑定，不能伪造 ToolAttempt 来满足 FK。

需要审批时，P06 暴露可在已有事务中组合的 prepare/authorize/bind 端口。P08 在同一许可事务把已批准请求消费到唯一 ToolOperation/Attempt 和 outbox；未实现批准绑定的工具保持 approval-required/blocked，不接受 client approved=true。批准不解除 Task.pause/Work.hold。恢复只转移合法持有者并复用原逻辑操作。

## 转发、错误与结算

普通 JSON 在发送前完成准入，使用精确 JSON 字节转发，不经过有损浮点再编码。SSE 保留真实流字节，仅做必要的有界帧/完成标记观察；不自建 Agent 循环或拼造完整 assistant 消息。EOF、协议终止标记、截断和客户端断开分开记载。

流开始前可返回既定安全错误；开始后不能改 HTTP 状态或追加普通 JSON 当成功结尾，也不补 `[DONE]`。停止流并记录 partial/unknown，供回执查询。已发上游请求可能继续计费，不承诺远端撤销/退款。

代理不透出 Key、内部配置或完整敏感上游错误。内部 HTTP 错误语义与 native 成功协议分开，必要新增错误/回执接口由 P06 主名单声明。旧许可下的结算由受信身份更新已登记尝试，不授予新模型/工具执行权。

## 实施与验证

START 后采用 P05 最终公共控制/容量/回执接口与 migration head；本合同授权上述 narrow DTO/路由/配置、secret resolver、同一账本和执行适配。先完成真实签名 Run → Gate → 合成上游/无害外部工具 → 原生记录主流程，再检查撤销、并发最后额度、服务重建累计、同操作重取/冲突、新 ID 新尝试、部分流和证据先交付。只在各实际边界声称通过；LiteLLM 真部署、MCP transport、Supervisor、P08审批原子消费和效果试验未接入部分保留后续状态。
