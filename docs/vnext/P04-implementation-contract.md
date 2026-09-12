# P04 知识接纳与评估接口收口

日期：2026-09-13；主控制器负责。依据已批准 v2 Spec S03/S04/S09/S10/S13 和 P04 Plan。P04 仍需等待 P03 验收和明确 START；本文固定准备阶段发现的接口缺口，不表示已经实现。

## 范围与所有权

P04 实现 ClaimService、AssessmentService、FactLedger 读视图、受约束关系和 ResultCommitter，复用 P03 的实际 UoW、父记录、registry、操作回执、字节读取和快照。允许新增生产 `wuji_core.http.knowledge` 路由工厂和必要的 `http.records` 读路由，提供现有 claims/intents/assessments/results/records API；不得在测试 fixture 内实现业务结果。

P04 可串行修改下文明确的 OpenAPI v2 输入/返回形状及生成产物，追加实际 schema 迁移和必要依赖；先读 P03 最终 handoff，不建立第二套父记录、事务框架或业务图。所有 JSON 路由/响应采用最终 P02 安全入口，assessment/evidence 输入采用公开 policy wrappers。

## Claim 创建与修订

ClaimProposal 增加可选 `revises: KnowledgeRef | null`。无 revises 创建新 claim；有 revises 时必须为当前可写的同 Task claim 版本，作为该 claim 的 expected revision。CAS 成功后沿用 claim_id、追加 revision、保存 supersedes 指向旧版；不要求整体 board_revision 未变。

Agent 默认只能修订自己产生或被明确分配可修订权限的 claim；人类操作者按当前项目权限处理。不同 Agent 可以提交引用旧 claim 的新候选/反证，不因此获得改写它的权限。同批不得对同一 claim 产生两个竞争修订。无解析器文本、空依据假设仍可 accepted_shared/unassessed；revises 不是新增授权入口。

独立 propose 没有跨请求 client_ref 命名空间。批内 ProposalLocalRef 仅在同一 ResultSubmission 内解析；外部请求不能把它当数据库 ID。全批先检查 client_ref 唯一，再按依赖解析，缺失/循环/拒绝依赖传播到受影响组件，合法无关组件仍可接纳，失败组件不留下领域/registry/关系残行。

## 评估事件、政策与责任

FactAssessment 是不可变评估事件，assessment_id 为逻辑事件 ID，领域 revision 初版固定 1；created_at、责任主体和选用 policy 由服务赋值。原事件不更新。AssessmentCommand 的 expected_version 绑定 `assessment.claim_ref.revision`，不锁死整个 Task 的评估水位；对旧 claim 版本的合法评估可以保存，但不自动作用到新正文。

AssessmentCommand 可增加 `supersedes_assessment_ids` 和显式理由，用新事件替代同一固定 ClaimRevision 的旧判断。仅有相应评估/纠错资格的主体可以替代；普通 Agent 不能借该字段撤回检查结果。撤回同样保存追加的决定及其依据，不删除原事件。方法失效/环境变化产生可审计失效记录。

首版发布一个固定 `assessment-policy-v1`，版本、文档摘要与允许方法集合由部署注册；Task 明确绑定该版本，不默认追 latest。只聚合匹配 claim revision、输入和环境条件且未被合法替代/撤回的判断：有效支持与反证并存为 disputed/inconclusive；仅模型意见不贡献 supported；没有适用判断为 unassessed。新 ClaimRevision 不继承旧 supported。

human_attestation 要求真实 qualified human 身份、固定被审正文/输入范围和非空理由；reviewer_ref 必须与服务端主体相符。model_review 只存意见。其他 method_kind 必须对应已发布实现，不能把文件字段检查标为已经发生的目标复现。

## 首批确定性方法

允许的候选内容不受固定模板限制；以下模板只限定这两个自动检查方法能认证的精确范围，不能匹配时仍保留共享候选。它们是通用方法，不写入任何靶场答案。

- `json-pointer-equals-v1`：structured_assertion 固定 predicate、artifact_ref、RFC6901 pointer、JSON scalar expected。artifact_ref 必须与合法 basis 对应。服务重新读取封存字节、核对摘要/长度，用严格 JSON 解析及精确数值比较核对该字段。能认证的完整正文模板为 `已捕获内容 {artifact_id}@{version} 的 {pointer} 字段等于 {expected_json}。`，expected_json 按精确规范 JSON 编码。通过只支持已捕获内容中的该命题；有效局部材料可支持局部值，无法解析/缺必要范围则 inconclusive。
- `json-pointer-absent-v1`：同样固定 artifact/pointer，仅在该输入的完整性足以支持完整 JSON 文档判断时使用；正文模板为 `完整捕获内容 {artifact_id}@{version} 中不存在 {pointer}。`。partial/缺失不能支持否定判断，记录 inconclusive；存在该字段构成反证。

其他正文、解释或更大推论不能仅因 structured_assertion 检查成功而变成 Fact。例如字段正确但正文是“系统安全”，结果只能保留候选/不确定，不能认证整个 Claim。合资格人审及未来方法可以支持其他自然语言，P04 不要求通用解析器。方法说明和模板可由受控只读目录提供给 Agent；测试正例使用独立固定文字和真实字节，不从待测函数生成预期答案。

## 关系与读视图

KnowledgeRef 保持规范知识/节点引用，Fact 仍引用 ClaimRevision。P03 的知识关系用于 cites/input_to/supersedes/proposes 等合法 registry 端点；assessment→claim、observation→ToolAttempt、human producer 等使用真实领域外键和主体记录，不伪造 KnowledgeRef 或空 registry 父记录。

P04 的 Claim read 返回唯一 ClaimRecord 及有界的 aggregate assessment/Fact eligibility 信息，明确 policy version、条件、限制和有效评估引用。可在现有 RecordView 中追加专用 ClaimAssessmentView，不能复制一份可写 Fact 正文。当前视图从当前有效评估计算；指定已保存 snapshot 的历史读取使用其冻结的 claim/assessment/policy 状态并重新核对当前访问权。完整 Topology 和 GoalCriterion 展示/关系由 P13/P12 接线，其尚缺的 typed criterion ref 不由 P04 假造为 goal 节点。

合法 Intent 提案先持久接纳为 IntentRevision；P04 不自行启动 Agent 或创建第二个调度器。WorkItem 建立和执行条件由 P05/P09 消费同一已接纳提案，未验证假设可用作依据，执行权限另验。

## 原始输出先保存

结果入口先认证真实 Run/Worker 绑定并验证可信 envelope 字段及已封存 model_output Artifact 的归属/摘要，再持久保存原始 submission 与 received 回执。模型输出的结构检查在这之后进行。

为支持该顺序，外层 ResultEnvelope.payload 放宽为有界 JSON value 或 null；强 AgentPayload 仍是独立的第二阶段 schema。可信 Worker 对非 JSON 回复传 payload=null，原文保存在 raw_output_ref。服务重新读取并解析原始 UTF-8 最终回复，若传了 payload 则核对其与原文的规范内容一致；不相信客户端“解析成功”标志。无法解析或 AgentPayload 不合法时返回 rejected/INVALID_SCHEMA，原材料和 received 记录保留，不自动重问模型。外层 envelope 本身不合法的请求不伪造为已接收的合法 Run 结果。

P03 的 capture staging 绑定 ToolAttempt，不能用它为零工具调用的模型最终回复伪造一个工具父记录。P04 获准在同一 ArtifactStore 增加 `stage_model_output` 及对应来源约束：绑定真实 AgentRun/受信 writer，provenance 固定 model_output，允许没有 tool_attempt_id；capture 来源仍必须绑定实际 ToolAttempt。复用相同字节路径、seal、租约、pin 和 GC，不建立第二个产物存储。必要的 run-writer subject 映射作为真实 AgentRun 的权限关联保存，不另存一份执行状态。该专用写能力不能同时开启 Observation/capture 写权限，数据库策略也必须区分两类来源。

HTTP `Idempotency-Key` 必须等于 submission_id；服务键为 `(tenant, task, result_submit, submission_id)`，同键不同原始内容冲突。提供按该 ID 查询/恢复已接收提交的内部服务端口，只重做本地接纳，不运行 Agent/工具。结果阶段二和领域/组件回执/Outbox 同事务；原始字节不在大事务里读写。

stale_input 是持久的接纳限制及组件 code，可用新的受约束 ComponentReceipt.code 值表达；无关旧快照追加仍可接纳，失效依据不能驱动新控制决定。仅 API/当前执行确实不再允许操作时使用 STALE_EXECUTION，避免把知识过时误写成进程失效。撤销后的可信结果依现有资格 historical_only，不创建 ready 工作或恢复 Task。

## 实施与验证

START 前接收 P03 最终公开端口、迁移头与被测 SHA。上述 narrow wire/schema 扩展由 P04 明确列清单并做直接合同检查；不覆盖用户原始 Spec 包。正向候选→独立检查→Fact 读视图、无解析器候选、反证聚合、追加修订、批内拒绝传播、旧快照追加、原文结构失败留存和幂等恢复均使用真实服务/API/SQL/字节验证。尚未联通的调度、Goal 和完整画布不提前标通过。
