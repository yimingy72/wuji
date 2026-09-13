# P13 图投影与持久视图实施收口

日期：2026-09-13，主代理设计。依据已批准 P13 Plan 与 Spec S12/S14，P03/P04/P05 已完成本项验收。P06 仍独占共享迁移、UoW、OpenAPI/生成 DTO；当前 P13 仅并行纯 builder，持久化和 API 改动须在 P06 最终交接后开始。所有测试、验证、复核和常规修复由 SOL/xhigh。

## 纯映射切片

`projection/builder.py` 消费已经过服务端授权的 RecordView 和精确引用关系；不读数据库、不评估证据、不授予命令。`node_id(ref)` 固定 `entity_type:id@revision`；`project_record` 校验 payload 与 ref 的类型、ID、修订匹配，并只映射公开展示字段。Claim 是否显示 fact 只用 P04 规范 ClaimAssessmentView.eligible，单独的 display_kind 提示不能提升知识等级。

`build_projection` 对相同精确节点去重，遇到冲突正文/状态拒绝，不选择其中较新或较有利的一份。关系只连接两个实际存在的精确端点，缺失端点即不输出该边及其标签；旧关系不重连到新 revision。边 ID 由固定关系身份、精确端点和类型形成，标签/布局变化不改变它。返回有序 tuples，不修改输入记录。

Task Origin 使用 TaskView.version，Work 使用 WorkItemView.revision，Artifact 使用 BlobRef.version，其余正文采用真实 revision。AgentRun 的唯一 ID 对应一次不可变注册身份，首版正文引用固定 @1；process/result 状态改变更新投影，不拿 run_epoch 充当正文修订。标签可按 DTO 展示上限加明确省略号，完整原文不改写。任何内部序号、原始来源路径、密钥、私有结构化字段或隐藏计数均不从记录任意复制到节点。

纯函数检查只证明映射边界，不能代替受权资料读取、真实 PostgreSQL、持久分页、历史或 API 验收。当前纯切片入口为 `tests/vnext/test_projection_builder.py`。

## 一个稳定事务与一个已保存版本

后续 ProjectionRepository 在同一受权 Repeatable Read 短事务内固定知识引用、评估显示、Task/Work/Run 可见状态、关系、完整 RecordView 展示副本及内部事件消费起点。不能先生成知识快照、再开启第二事务读取最新执行状态拼装同一快照。

优先将 P03 SnapshotRepository 的既有创建逻辑提取为可在现有事务调用的入口，外部 create 继续复用它；P04 FactLedger 也可增加同事务受权读取入口。保留原 RLS、评估完整性/新鲜度检查、Artifact pin、发布租约及当前权限校验。不要复制第二套知识评估逻辑或引入 Agent 权限提升。

图的 materialized nodes/edges/RecordView 是不可变派生视图，可保存于与同一 SnapshotManifest/publication 关联的图投影记录；其写入须同事务完成。规范领域表仍为业务来源。Task/Work/Run 的可变状态必须保存实际当时值，后续页面与侧栏从该副本读取，不在分页时补最新值。尚无正式生产记录的 Goal/Verification/Completion/Report 类型不得伪造；相应 P12 等生产者注册后补接实际来源，最终节点类型完整覆盖仍在后续集成验收。

源码衔接待定向验证项：P05 WorkDependency 已使用 GoalCriterionRef，但 P03 SnapshotRepository 的 dependencies 构建仍调用 KnowledgeRef 的 `_ref`。SOL 应在共享迁移交接后以真实 criterion dependency + snapshot 复现，改为专用引用并保留真实 FK；不得为通过而把 goal_criterion 加进知识实体枚举。GoalRecord 的旧 criterion_refs wire 也要在 P12 正式 Goal 来源接线时统一改为正确引用，不能靠虚构 goal 节点绕过。

## 身份、当前权限与分页

每个 view 绑定 principal、tenant/project/task、规范 query_digest、access_scope_digest、projection_version 和有效期。view_id 是新生成身份；初始 view_revision 为自己的版本，不取内部 board_revision/task_event_seq。查询、历史选择、展开或访问条件改变后创建新 view，旧流不能混入。内部事件起点单独持久保存供 P15 catch-up，不返回浏览器。

现有 ViewQuery 足够先固定 live/history、节点/边限额及 snapshot/cursor。前端搜索只能查已获授权的展示内容，展开可重新获取新 view 后调整折叠；若后来确需服务器过滤字段，再在 P13 所有权下做明确的窄 OpenAPI 增量，不自行增加通用查询 DSL。

2026-09-13 独立复核后的主代理裁定：公共 `mode=live` 必须不带 `snapshot_id`；`mode=history` 必须带实际保存的 `snapshot_id`。非法组合返回 `422/INVALID_SCHEMA`，不能把历史内容持久化为 live 查询身份。续页仍绑定原 mode/snapshot/query。records 与 snapshots 的实际过期路径统一在单一 OpenAPI 声明 `410`，保留 typed 历史不可用/游标过期恢复语义；这两项修复按新的定向证据记录，不追改原 12 项结果。

Cursor 使用随机 opaque handle，服务端保存分页位置及上述绑定/期限；不能把内部序号 JSON Base64 后仅签名。分页读取完整已保存 materialization，原节点 revision/评估/关系不变。分页可以输出增量片段，但边端点必须已在当前或此前同 view 页内交付；客户端按精确 ID 合并，不能把不同 view 或 query 的页拼接。节点/边各自限额均实际约束每页，未交付完时给 continuation 和明确 truncated，不回传隐藏总数。

每次图页、历史、记录或内容读取先核对当前 ACL、全部实际依据可读性和派生权限。权限变化使旧 view 失效；不以部分已隐藏依据继续展示一个看似完整的 Fact/摘要。原隐藏端点对应的边、标签、摘要和计数也不输出。纯 builder 的端点过滤只是一层保护，不替代该读取边界。allowed_actions 仅为重验后的提示，history 一律空动作。

## 历史、保留与后续消费

历史列表只列当前主体可访问且实际保存的 manifest；不存在/已不保留的时间点返回 HISTORY_UNAVAILABLE，不用 latest 替代。交互快照过期按合同返回 410，保留期限来自明确配置；后续 ReportCommit/RetentionProfile 的更长保留按 P12/P16 接入，不虚构永久保留。历史读取不触发模型/工具/任务执行。

P15 在 P13 view 的真实消费起点上建立 stream，只有可见投影改变才递增 view_revision；这一步尚未由 P13 纯映射证明。P14 的正式工作台容器消费真实 topology API，精确记录接口同样读取受权保存版本，不只搭临时原型路由。

## 最小验证与所有权

SOL 负责纯片 RED/GREEN 及必要定向修复。待 P06 交出 migration head 后，再用真实签名 HTTP 与隔离非 owner PostgreSQL，覆盖第一页后并发新 revision、固定第二页/侧栏、权限降低、隐藏依据/边、未知历史、游标绑定及清晰过期；沿用未改 P03/P04/P05 证据，不重跑全套。API 结果须完整请求响应与实际截图，纯函数初始记录不伪装 HTTP。

本文件授权为上述行为增加必要的派生存储/同事务组合接口，具体新增迁移号由最终 P06 交接决定。纯映射先完成不代表 P13 全项 accepted，后续阶段状态以实际命令和完整依赖证据更新。
