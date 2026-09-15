# vNext 当前开发任务与下一项执行计划

- 状态：approved；队列第 1 项 P15-L、第 2 项 P08-S、第 3 项 P11-C 创建入口已交付
- 整理日期：2026-09-15
- 实施工作树：`work/worktrees/vnext-maf`
- 分支：`codex/vnext-maf`
- 审核基线：`38ecc530de34b82049c9d4414ee14b5bd8270f07`
- 权威来源：[Spec](../../vnext/SPEC.md)、[P00–P20 Plan](../../vnext/PLAN.md)、[Acceptance](acceptance.md)、[实施决定](../../vnext/decision-register.md)

本文取代 2026-09-13 的近期执行排序；旧[下一批开发执行单](next-batch-plan.md)保留其 A1/A2/B1/C0–C2 当时计划与已发生结果，不再作为下一项开发入口。

## 1. 当前交付面

| 工作面 | 已完成或可复用 | 当前缺口 | 状态 |
| --- | --- | --- | --- |
| P00–P06 平台基础 | 身份、证据、知识接纳、控制状态、模型/工具准入与累计账本已有各自范围验收 | 完整下游集成、真实模型效果和外部目标不继承局部结论 | 已验收基础，继续复用 |
| P07/P09/P10 执行链 | hosted M1、限定 M2，以及本地 K8s fresh6 的 Scheduler→Task Pod→MAF→Gate→Kali→P03/P04→退出已实测 | 完整 Session、全部 work kind、完整故障矩阵和 Task 完成仍缺 | 局部通过 |
| P08 Session/审批 | 两代 child approve/reject、拒绝结果接纳、退出撤销守卫已有局部实测 | 固定 memory、原生 compaction、单写/CAS、半发布、旧批准和 GC 等完整边界未收口 | in-progress |
| P11 控制与正式入口 | Approval、Task/Work command 路由已有局部 PG/HTTP 结果；本地浏览器机制身份可读 | 正式 Task/Project 创建、生产身份、完整 hold/pause/resume/cancel 与实际进程恢复未完成 | partial |
| P12 可信完成 | 合同和前置领域能力已冻结 | precheck、quiescing、settlement、报告冻结和迟到反证尚未实现 | not implemented |
| P13 投影/API | 受权快照、历史目录、RecordView 和独立 K8s API 已实测 | Layout、ViewStream、P12 后续节点类型和规模目标 | partial |
| P14/P15 工作台 | 真实 K8s 浏览器会话、拓扑画布/列表、记录详情、历史快照选择已实测 | 布局持久化、实时流、Artifact 预览、正式身份和性能目标 | partial |
| P16–P20 | 已有 Spec/Plan 和前置模块 | 治理、完整端到端、离线归档、发布物与离线评测工具 | not run |

当前活跃 K8s 切片的 `api`、`runtime`、`scheduler`、`gates`、`wuji-web` 可运行。`8e0f30e` 已将 `44180` 改为 Docker Desktop Kubernetes 管理的 `LoadBalancer` Service，不再依赖 `kubectl port-forward`。旧 `c2-*` 验证 Deployment 的凭据已过期并处于 CrashLoop，后续只做可逆缩容，不删除其数据库或证据。

## 2. 后续开发队列

1. **P15-L：Layout CAS 垂直切片。已交付。** `b465238` 完成个人布局读、写、`If-Match` 冲突、K8s 浏览器刷新与真实 409 验证，并在实测中发现、修复 409 后自动回写缺陷。见 [P15-L 证据](../../vnext/evidence/P15/layout-cas-20260915/README.md) 与[验收记录](acceptance.md)。范围限本地机制身份与两个知识视图。
2. **P08-S：Session/操作前沿收口。已交付（范围限操作前沿与批准边界）。** `93f2fc6`/`2366969`/`cc65fef` 清零 P08 红色基线、修复恢复后批准身份判定与按 attempt 前驱绑定，并核对 F2/F3/F4/F5 四项残留已关闭；真实隔离 PostgreSQL 完整可运行集合 405 passed / 0 failed。见 [P08 残留现状核对](../../vnext/evidence/P08/reviews/P08-residual-closure.md) 与[延期记录](../../vnext/deferred-suite-failures-20260915.md)。固定记忆、原生 compaction 的真实 child 与 GC/半发布边界仍按原计划另行验证。
3. **P11-C：正式创建与控制闭环。创建入口已交付，控制闭环进行中。** `d0204db` 增加 `POST /api/v2/tasks`：0019 迁移的 `published_profile` 目录与 `vnext.create_task` SECURITY DEFINER 函数、`TaskService`、路由与 K8s 实测（201/幂等重放/409/匿名 401/浏览器入口不转发）；见[P11-C 创建入口证据](../../vnext/evidence/P11/task-creation-20260915/README.md)与[决定 D18](../../vnext/decision-register.md)。owner 侧 admission/容量/调度身份发布已由 `8d6c972` 交付（真实 PostgreSQL 2 项 + K8s 对已创建 Task 发布后 start/pause/cancel 202 与控制事件；该 Task `agent_run=0`，不作进程停止结论，见[证据](../../vnext/evidence/P11/task-admission-control-20260915/README.md)）。2026-09-15 追加：Pod 级停止观察已在真实 K8s 完成——`cancel` 受理后 5 秒内删除运行中的 Task Pod，Task 保持 reconciling 且不伪造退出，见[证据](../../vnext/evidence/P11/pod-stop-20260915/README.md)；同时完成全平面镜像按 `8d6c972` 重建滚动与过期凭据重签。**未关闭**：Pod 运行期间 runtime 持续 `runtime_dispatch_error`(DomainError)、worker 未启动（agent 无日志、run 停 registered），以及从部署配置自动推导 admission 行的 owner 工具；诊断已明确：receiver 在 Pod 停止后被禁用、runtime 固定 `execution_epoch=2` 而任务代次已推进（PermitDenied 正确拒绝）、租户尚无 `session_capability`；错误码与 pod-environment 状态日志已由 `56ba97d`/`b5cc4ca` 补齐。二次跟进确认：同代次原地重跑会被持久 inbox 以 `RECEIVER_IDENTITY_CONFLICT` 正确拒绝。下一步用**新 runtime attempt**（任务+runtime 配置同步渲染，并给每次尝试独立的 agent 状态卷或归档旧 inbox）验证 assignment 到达 supervisor，同时发布 tenant session capability，再补干净退出观测。
4. **P12-T：可信完成。** 实现 precheck、quiescing、有限结算、ReportCommit/Delivery、迟到反证和 abort-close。
5. **P15-S：ViewStream。** 在 P08/P11/P12 的事件和完成类型稳定后实现受权 view revision、opaque cursor、SSE、duplicate/gap/reset 和权限变化关流。
6. **P15-A/P16：Artifact 预览与治理。** 受权内容流、访问审计、保留/GC/purge 和衍生权限。
7. **P17/P19/P20：集中机制验收、离线归档和独立发布物。** P18 只准备离线工具；真实收费模型试验和生产切换仍需单独授权。

这个顺序先关闭当前可见工作台最小缺口，再回到决定产品是否可信的 Session→控制→完成主链。ViewStream 不先于核心事件生产者收口，避免为随后新增的 Goal、CompletionReview、Report 和控制事件重复修改流合同。

2026-09-15 交付记录：队列第 1 项已按 §3 完成并实测（本地 K8s、真实 PostgreSQL、真实浏览器），证据包为
[`docs/vnext/evidence/P15/layout-cas-20260915/`](../../vnext/evidence/P15/layout-cas-20260915/README.md)。
当前队列下一项固定为 **P08-S：Session/compaction 收口**，其后依次为 P11-C、P12-T、P15-S、P15-A/P16、P17/P19/P20。

## 3. 下一项：P15-L Layout CAS

### 3.1 用户结果

同一受权用户在 live 或 history 视图拖动节点、平移或缩放后，刷新页面仍取得对应个人布局。两个标签页从同一 revision 修改时，后提交的旧 revision 返回 409，不能覆盖先提交的布局。布局写入不修改 Task、Fact/Claim、Intent、Artifact、WorkItem、Run、快照或领域 Outbox。

### 3.2 先修正合同

当前 OpenAPI 只有 `PUT /api/v2/tasks/{task_id}/layouts/{view_name}`，`LayoutPatch` 也没有客户端已经维护的 viewport；仅实现现状无法完成“刷新后保留布局”。本任务在单一合同源 `packages/contracts/openapi-v2.yaml` 中完成以下收口并重新生成 Python/TypeScript DTO：

- 同一路径增加 `GET`，返回新的 `LayoutPreference`。
- 新增 `LayoutViewport {x,y,zoom}`；x/y 必须有限且在固定范围内，zoom 限定为 React Flow 当前允许的 `0.2..2.0`。
- `LayoutPatch` 必须包含 `schema_version`、`selection_mode`、`entries`、`viewport`，未知字段继续拒绝。
- `LayoutPreference` 返回 `schema_version`、`view_name`、`layout_revision`、`selection_mode`、`entries`、`viewport`。
- 不存在持久记录时 GET 返回 revision `0` 的服务端默认值；首次 PUT 必须 `If-Match: 0`，成功后返回 revision `1`。后续 revision 为严格递增十进制字符串。
- 首个产品切片只允许 `knowledge-live` 和 `knowledge-history` 两个 view name，分别默认 `follow_latest` 与 `explicit_revision`，避免历史选择改变 live 偏好。

### 3.3 数据与权限

新增顺序迁移 `vnext_0018_p15_layout`，表的唯一键为 `(tenant_id, project_id, task_id, subject, view_name, layout_schema)`。持久字段只包含 revision、selection mode、entries、viewport 和更新时间。

- 身份从当前 bearer 派生，客户端不能提交 subject、tenant、project 或 task owner 字段。
- 保存个人布局只要求当前 Task `can_read`；它不使用领域 `can_write`，也不产生语义事件。
- RLS 同时约束当前 tenant、Task ACL、subject 与 clearance；撤销读取后 GET/PUT 均返回不区分存在性的 404。
- PUT 在一个事务中锁定个人布局行并比较 `If-Match`。revision 不一致返回 409；不得自动 last-write-wins。
- 坐标、zoom、条目数、重复 anchor 和 JSON 大小全部有界；NaN/Infinity 和未知字段在 HTTP 边界拒绝。
- 新增或改变的 anchor 必须能映射到当前用户受权投影中的稳定节点身份。逻辑 anchor 至少匹配一个同类型同 ID 的受权 revision；精确 anchor 必须匹配精确 revision。未知或已失权节点不得借布局表建立影子记录。

### 3.4 代码切片

- 合同：`packages/contracts/openapi-v2.yaml`、生成的 Python/TypeScript DTO、直接合同检查。
- 持久化：新增 `wuji_core/persistence/layout_schema.py` 和 `wuji_core/projection/layouts.py`。
- HTTP：新增独立 `wuji_core/http/layouts.py`，装入 `services/wuji-api/deployment.py`；兼容 Runtime 入口只复用同一 router，不导入旧应用。
- BFF：`services/wuji-web-gateway/main.py` 只新增固定 Task 的 layout GET/PUT。PUT 必须校验精确 Origin、Content-Type、If-Match 和请求体上限，只转发固定头，不开放其他写路由。
- Web：`VNextWorkbench` 持有受控 LayoutPreference；进入视图时读取，节点拖动与 viewport 变化串行保存。409 显示冲突并重新读取服务器 revision，不自动覆盖。
- K8s：只重建受影响的 API、gateway、web 镜像并升级隔离数据库到 0018；不重启无关 runtime/gates/scheduler，不延长现有 Task 授权。

### 3.5 最小验证与停止条件

只执行以下直接路径，通过即停止：

1. 合同生成/check，确认 GET、viewport、严格字段和生成 DTO 一致。
2. 真实 PostgreSQL：默认 revision 0、首次创建、顺序更新、stale 409、跨 subject 隔离、撤销读取、未知 node、重复 anchor、非有限数拒绝，以及领域 revision/outbox 不变。
3. BFF：未登录 401、跨 Task 404、缺/错 Origin 拒绝、有效 GET/PUT、If-Match 和 409 原样保留；不开放 Task command。
4. Web 定向测试：加载持久布局、拖动/viewport 保存、409 后不覆盖、live/history 隔离。
5. typecheck 和 production build。
6. 当前本地 K8s：登录→GET revision 0/已有 revision→拖动并保存→刷新后位置和 viewport 保留；第二个旧 revision 请求得到 409；浏览器控制台无新增错误。

成果包按项目约定保存至少一张浏览器或终端截图，并附完整、未截断且凭据脱敏的 HTTP 请求/响应。记录代码 SHA、镜像摘要、数据库 migration head、Pod UID 和未覆盖项。该成果只提升 Layout CAS，不提升 ViewStream、生产 OIDC、P11 控制或 P12 完成状态。
