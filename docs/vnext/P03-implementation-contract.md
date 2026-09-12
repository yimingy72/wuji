# P03 实施接口收口

日期：2026-09-13。负责人：主控制器。依据已批准 v2 Spec S03/S04/S08/S10/S13/S14 与 P03 Plan；这是进入 P03 前的实现合同，P02 正在范围复审，本文不标记任何产品验证通过。

## 所有权与入口

P03 允许新增 `wuji_core.http.evidence` 的真实路由工厂，提供现有合同的 `POST /internal/v2/evidence` 与 `GET /api/v2/artifacts/{artifact_id}/content`。使用最终 P02 的 VNextAPIRouter、TokenVerifier/current_principal、DecimalJSONResponse/StreamingResponse；测试不在 fixture 内实现业务逻辑。

ArtifactStore 的 stage/seal 是内部生产端口，接收有范围的可信主体、实际 bytes、媒体类型和采集信息；本阶段不增加未经定义的 HTTP 上传接口。调用者不能提供任意本机路径或外部 URL。对象路径由服务生成，BlobRef 只解析到受权登记对象。封存后核对实际摘要与长度，正文/元数据不以 Agent 声明替代。

生产 `wuji-core` 直接声明 `psycopg[binary]==3.3.5`，同步新 worker lock；不得依赖测试 dev 环境偶然提供驱动。只调整新核心和新锁，不改旧依赖。验证命令使用 `./scripts/vnext/uv.sh run --frozen ...`，不使用旧根包装。

## Capture 与 Observation

**一个 capture_id 对应一个逻辑 Observation，包含该次观察的全部 artifact_refs。** HTTP 交换的元数据与正文等产物属于同一观察；不能因产物拆文件而增加独立证据数量。Artifact 保持各自不可变身份和摘要。

P03 获准在单一 OpenAPI v2 中修订 P02 新增而尚未被业务使用的返回类型并重新生成：

- ObservationRecord 增加 `observation_id`、`revision`、`task_id`，将单个 `artifact_ref` 改为 `artifact_refs`（非空、有界、有序）。保留 capture/attempt、采集主体、层次、环境、条件、时间、完整性和来源字段。
- EvidenceReceipt 增加 `observation_ref: KnowledgeRef | null`。accepted/historical_only 必须引用该唯一 Observation；pending/rejected 为 null。引用类型必须为 observation。
- Observation 初版 revision 为 1；同 capture 的同输入重投返回原 Observation 和原回执，不重新创建。更正另建 capture 并追加关系，不覆盖原字节/观察。
- 只修改这些相关类型和 evidence 路由 header；新增直接针对多产物/稳定观察引用的合同用例，运行生成一致性检查，不重跑未变 SDK。

这是对已有多 artifact CaptureEnvelope 与 P02 单 artifact 返回形状之间缺口的收口，不改变用户原始包字节。原包与 P02 历史验收仍按各自版本解释。

## 身份、操作与幂等

`CaptureEnvelope.tool_call_id` 是平台逻辑 ToolCall 的 ID；供应商不透明 call ID、Session lineage、原消息身份、ToolDefinitionVersion 保存在该 ToolCall 的独立字段，不以新 run_id 换操作键。`tool_attempt_id` 是其实际尝试 ID。

P03 可建立最小的规范 Task/WorkItem/AgentRun/ToolCall/ToolAttempt 父记录及可信采集绑定，供所有权、receiver、execution_epoch/run_epoch/runtime_attempt 和实际回执关联使用。P05/P06 扩展同一套表。入口绝不为不存在的身份补造父记录。测试用真实 SQL 建立明确的前提夹具，并如实标为前提，不称为已完成 Supervisor 集成。

AccessContext 从签名 Principal 加服务器端项目/任务权限、采集绑定与已登记 ToolAttempt 派生。JWT 有效、role=collector 或 envelope 自填 tenant/task 不单独授予该 capture 的写入权。匹配父记录、collector subject、receiver 和各代次；跨任务/项目/租户关系由复合外键和服务校验共同拒绝。

HTTP evidence 写入要求 `Idempotency-Key`，其值必须等于 capture_id，避免两个可独立变化的操作身份。OpenAPI 在 P03 一并补充该必需 header。内部服务仍以 `(tenant_id, task_id, evidence_ingest, capture_id)` 和规范化完整 envelope 摘要去重；Python stage/seal 端口不伪装成 HTTP。请求跟踪 request_id 来自可信 HTTP/UoW 上下文，与操作幂等身份分开。

同键同输入返回原回执前重验当前访问权；同键不同输入 409/INPUT_DIGEST_CONFLICT。字符串内容、数组顺序和数值不得有损改变。已有 CaptureEnvelope 示例只是 body，不因新增 HTTP header 改写原示例。

## 时间与迟到证据

不可变接收记录保留整个原 envelope，包括采集端 reported received_at；Observation.received_at 采用平台实际接收时间，observed_at 保留可信采集方报告并明确来源，不能用其时间延长执行许可。环境和 collector_ref 来自真实父记录/绑定，不采信模型或 payload 改写。

有效当前执行与许可下的 capture 可以 accepted。已登记且有可信开始记录的旧 ToolAttempt，在任务停止/代次撤销后由仍获准进行结算的采集主体补交时，只能 historical_only；不得产生新工作、许可或重启任务。任意未登记、绑定不符或没有相应结算权限的写入仍拒绝。普通过期 Run 凭据不能借此写入；范围收窄不等于放弃保存已发生操作的内部证据。

结果不明不补写零执行；已有 partial 字节与完整性原因保留。model_mode 与 evidence_origin 分开存；model_output、imported_unverified 不能经此入口改标为 live_capture。来源值须与受信 staging/ToolAttempt 环境信息相符。

## 快照、引用与事务

内部 `SnapshotRepository.create(task_id, access, *, query=None)` 保留 Plan 的默认调用形式；query 是有界、类型化的内部查询范围。持久 SnapshotManifest 保存所有权、query/access 摘要、时间/期限、固定有序引用、当时状态与关系，以及 Artifact pin。后续分页从已提交 manifest 读取，重新鉴权，不再读取 latest 拼历史。

新增 registry/domain 在同一事务提交。Registry 不存第二份断言正文；类型化引用不能仅指向一个没有真实领域记录的 registry key。用明确的受约束关系/延迟校验保证最终提交时域记录存在且归属一致。未实施的实体不能通过空 registry 行伪造支持。

同 Task 语义提交连同适用 revision、内部事件序号与 Outbox 原子完成；遵守既定锁序。WorkDependency 的数据库基础可先实现无环约束与存储，业务接纳/满足条件分别归属 P04/P05/P09，不维护第二份 Intent DAG。

发布租约和不可变 publication refs 是通用持久接口，Snapshot 先成为真实消费者；普通 GC 同时检查租约和已发布引用并在同一协调协议内操作。P08/P16 复用它们，不由 P03提前模拟完整 Session/Report 或用户数据 purge。

## 验证与后续

P03 按准备文档中的实际 API、真实双连接 PostgreSQL、非 owner RLS、字节完整性、重投/冲突、固定快照及发布/GC 路径实施。关联 AC 的评估、完整运行和前端部分保留后续状态，不用 P03 通过替代。所有新增字段和路由返回先经过直接合同测试与生成检查。
