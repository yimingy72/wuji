# Phase 1B Spec：真实任务管理

- 状态：B1 approved；已在 Plan 模式完成最终规划，用户明确批准实施。B2/B3 在进入对应批次前继续细化。
- 日期：2026-09-09。
- 设计输入：[现有架构](../../architecture.md)、[Phase 1 契约](../../phase1-api-contract.md)、[Phase 1A 验收](../phase-1a/acceptance.md)。
- 当前 Phase 1A 功能已集成，三个真实 Keycloak 回调用例延期；本草案不把上一阶段改记为通过，也不授权目标执行。
- 本次[评审记录](review.md)固定首批行为；B1 实施以 [Spec](b1-spec.md) / [Plan](b1-plan.md) 为准。

## 1. 可交付结果

用户登录并选择项目后，可以选择已有批准范围、填写 HTTP 观察任务、查看服务端范围预览并提交。任务、命令回执及事件保存在 PostgreSQL；刷新后仍可查询，重复提交不会创建第二个任务。Viewer 只读，Operator 可以创建和取消有权访问项目的任务。

本阶段交付任务管理，不启动 Runtime、DNS 查询、目标 HTTP 请求或模型调用。任务列表和详情清楚显示“排队中”，尚无执行器时不显示运行进度、证据或成功结果。五套主题及现有身份、项目隔离继续复用。

## 2. 分批范围

| 批次 | 用户可见交付 | 依赖 |
| --- | --- | --- |
| B1：范围与预览 | 当前项目的已批准 Scope；任务表单；服务端预览、范围拒绝与过期提示 | Phase 1A 身份与项目；本阶段方案评审 |
| B2：任务与命令 | 创建、列表、详情、取消；幂等回执查询；刷新后保留任务 | B1 的规范化与预览绑定 |
| B3：事件与前端收口 | 任务快照与事件补页；命令结果不明时按原键核对；切换项目后的旧请求隔离 | B2 的同事务写入 |

批次各自记录交付，未实现按钮不伪装为可用。Scope 发布管理 UI、pause/resume、运行调用账本及证据 API 留给后续批次；本阶段先实现命令账本和事务事件，避免预建无人使用的运行表。

## 3. 范围与预览

- Scope 由受信管理入口预置不可变版本，关联项目、授权依据、批准者、起止时间和策略摘要；普通任务表单不能扩张授权或发布策略。
- 公开沿用 `GET /projects/{project_id}/scopes`、`POST /projects/{project_id}/task-previews` 和既有 DTO；B1 将契约升至0.3.0，增加 task.preview、CREATION_UNAVAILABLE、not_granted 及明确的错误/回跳声明。找不到或无权访问项目返回404。
- HTTP(S) 输入规范化只做本地计算：拒绝用户信息、控制字符和歧义编码；规范化 origin、默认端口和路径，按路径段匹配允许范围，排除规则优先。查询参数保留参与摘要；禁止携带 URL fragment。具体算法和有限输入向量已固定在 B1 Spec §3，不能只使用字符串前缀。
- 预览绑定当前用户、项目、权限版本、完整规范化 draft、Scope 版本与摘要，有效期为5分钟且不超过授权截止时间。改变表单立即废弃旧预览。B1没有创建入口时返回CREATION_UNAVAILABLE，不把范围通过等同于任务可以提交。
- 限额为 draft、Scope 和平台上限的交集，沿用首版 200 请求、2 请求/秒、并发 2、单次 10 秒、响应 1 MiB、任务 600 秒的最大值。预览不进行网络访问。
- 输入不合法返回 422；可解析但范围不允许或授权过期时返回有明确 blocker 的预览。Scope 本身不存在或不可见时返回 404，不能拼造 effective_scope。

## 4. 创建、控制与权限

创建复核当前权限、preview 绑定、摘要、有效期和 Scope；同事务写入 Task、CommandReceipt 与初始 `task.changed` 事件。初始 Task 为 queued、version=1、active_calls=0、unknown_calls=0、egress_state=not_granted、cleanup_state=not_required、assessment_outcome=not_assessed，允许动作仅cancel。Runtime未部署或离线不影响已授权请求进入队列；创建不是执行许可。

创建和取消都要求会话、CSRF、Origin 与 UUID Idempotency-Key。键空间为当前用户和项目，绑定命令种类、目标及规范化完整请求。相同键和输入重投返回原回执；内容不同返回 409 IDEMPOTENCY_CONFLICT。已存在回执的重投先重新鉴权，再返回原结果，不重新检查旧 expected_version 或已经到期的 preview。

角色为当前有效租户/项目成员角色的最小权限；能力再与已实现接口求交。B1 Operator只开放project.read/task.preview，Viewer只开放project.read；B2 Operator追加task.read/create/control，Viewer追加task.read。控制仍受服务端allowed_actions约束。Receipt的accepted_task_version固定接受时版本，前端另查Task获取当前状态。最少保留24小时的幂等记录，本阶段不增加自动清理任务。

取消仅面向从未分配执行资源/许可的queued任务：鉴权、幂等串行核对、锁Task、版本检查、核实未执行、更新为cancelled/version+1、写不可变回执与递增task.changed/Outbox均在同一事务完成，提交后202。accepted_task_version取取消后的版本；不存在持久化cancelling中间态或后台补偿任务。cleanup_state=not_required、egress_state=not_granted、stop_reason=user_cancelled，不伪造revoked证据。Phase 1C开放执行时必须将真实attempt/许可核对及实际停止协调接入取消路径；B2不替已分配资源确认停止。pause/resume返回409 INVALID_TRANSITION，页面不展示对应按钮。

## 5. 存储与事件

新增授权记录、Scope 版本、TaskPreview、Task、CommandReceipt、任务事件/Outbox。所有业务关联带 tenant_id/project_id 复合外键；沿用真实运行角色和事务级用户上下文。项目角色获得必要业务表权限，但不获得认证写权限、DDL、TEMP、BYPASSRLS 或管理凭据。

每个任务的写事务锁定同一 Task 行，并在同事务内分配递增的任务内事件序号；不使用全局 sequence 的最大值推断已经全部提交。快照及游标从同一数据库快照读取。事件本身作为持久事实通知，Outbox 发布状态不得决定业务事务是否已提交；首版 HTTP 轮询直接读已提交事件，不新增消息队列或 SSE。

事件游标绑定用户、权限版本、项目、任务和位置；跨上下文 422，过期或权限版本变化 410。空页保留位置，每页重新鉴权。任务列表沿用 `(created_at,id)` 降序、默认 50/最多 100 的有界分页，不增加未经契约定义的搜索或总页数。

## 6. 前端与失败行为

完整路由为 `/projects/:projectId/tasks`、`/projects/:projectId/tasks/new`、`/projects/:projectId/tasks/:taskId`；B1只注册tasks/new，B2再加列表与详情。后端/前端/契约的登录回跳白名单按已实现路由同步扩展。复用现有AppShell、Query、响应校验和身份/项目代次，不引入原型Mock。

创建响应丢失后，保留原键及原始请求，只按原键核对或重送相同输入；查键 404 不等于没有执行。409 版本冲突刷新快照并交用户重新操作；401/项目404清理失效上下文；503不显示假成功。新输入产生新预览，不能在旧命令结果不明时自动以新键创建重复任务。事件只用于刷新视图，不触发目标操作。

## 7. 最小验收与评审事项

每批次只做主流程、直接受影响错误路径和一项必要权限边界；全体代理共享 10 分钟预算，受影响项通过即停止，未测项进清单。计划中的场景见 [Plan](plan.md)，不能把列表本身作为执行证据。

本次评审已决定保留Phase 1A三项延期，不以此反复启动旧回归；采用独立阶段分支推进，master保持原已验收基线。B1创建不可用、B2可以排队、Phase 1C才能授权执行的语义已分开写明。MISSING_ADAPTER在当前固定http_observe配置下没有实际失败来源时不发出。

本阶段已在Plan模式完成B1最终规划并获得用户明确实施批准；仅B1进入业务实现，后续批次不自动扩大范围。
