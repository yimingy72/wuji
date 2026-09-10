# B2/B3 Spec：任务管理与事件同步

- 状态：accepted（最小验收）；用户已在 Plan 模式审阅并明确要求实施，基准60f6544。实际证据及未覆盖项见[b23-acceptance.md](b23-acceptance.md)。
- B2/B3连续开发，共用一个候选和600秒最小验收；Phase1A partial继续保留。

## 交付

预览→创建→查询→取消→刷新恢复；Task只生成queued/cancelled。B2完成任务、幂等命令、快照与事件原子写入，B3完成事件读取和页面同步。本批不访问目标、不接入Runtime/Agent/模型、不实现pause/resume、证据或消息发布进程。

## API与存储

平台/契约0.4.0。现有 `/api/v1/projects/{project_id}` 下启用GET/POST tasks、GET tasks/{task_id}、POST tasks/{task_id}/commands、GET commands/{command_id}、GET command-keys/{idempotency_key}、GET tasks/{task_id}/events；复用已有DTO，导出Task/TaskPage/TaskSnapshot/CommandReceipt/EventPage校验器，同步JS与d.ts。新路由、登录回跳模式及明确错误响应同步契约、API与web。

唯一迁移20260910_0003接0002，新增tasks、command_receipts、task_events（兼作Outbox）。Task保存完整规范化draft、effective_scope、policy_hash；所有关联使用tenant/project复合FK。Task行保存事件序号，事件唯一键(task_id,sequence)。RLS及列权限保持最小；普通角色不获得认证写入、DDL、TEMP、管理凭据。任务/事件按当前项目读取，回执限当前仍有项目读取权限的原提交者。

预览的数据库CHECK和Pydantic一起支持can_create=true且blockers=[]；false必须有blocker。有效预览不再追加CREATION_UNAVAILABLE；现有B1预览保持false，不能直接创建。新请求须当前权限、有效期、绑定用户/项目/权限版本、完整规范化draft/input_digest与现行授权一致。不得仅凭前端按钮开放创建。

Operator追加task.read/create/control，Viewer追加task.read，保留现有权限。allowed_actions取任务状态和当前权限交集。列表默认50/最多100，(created_at,id)降序；不增加搜索或虚假总量。

## 事务及失败语义

写操作会话+Origin+CSRF+UUID Idempotency-Key。沿用USER_LOCK_SEED用户事务锁与现有管理撤权协调；锁内重新读取当前用户enabled/permissions_version及双层角色，业务写入只用project engine。不得通过给project角色开放users全表来绕过边界。锁顺序为用户→Task。

键唯一范围(user_id,project_id,key)，绑定命令kind、目标和规范化完整请求摘要。先鉴权、再查回执、最后新命令校验；同键同输入原样返回旧回执，同键不同输入409 IDEMPOTENCY_CONFLICT。已接受重投不再因预览到期/旧expected_version失败。回执至少保留24小时，本批不自动删除；回滚与明确拒绝无成功回执。

创建POST提交preview_id/input_digest/draft，同事务创建queued/version=1 Task、回执、sequence=1 task.changed，提交后202。执行计数0，egress=not_granted，cleanup=not_required，assessment=not_assessed，stop_reason=null。新B1 blocked预览返回409 VERSION_CONFLICT要求重预览；过期409 PREVIEW_EXPIRED；绑定资源不可见404；权限版本变化409 VERSION_CONFLICT；输入摘要不符422 VALIDATION_FAILED；当前范围拒绝403 SCOPE_DENIED。不得改写旧预览为可创建。

取消锁Task，检查expected_version与从未执行，原子queued→cancelled/version+1、user_cancelled、回执和递增task.changed；提交后202，accepted_task_version取新版本。无持久cancelling中间态。新请求版本错409 VERSION_CONFLICT；终态新控制或pause/resume返回409 INVALID_TRANSITION。原已接受命令重投先返回回执。

缺会话401，CSRF/Origin或操作权限拒绝403，不可见项目/任务/回执404，非法输入422，数据库异常503。未知错误500脱敏。读写no-store，公开错误包含trace_id。错误不能显示为成功/空列表。

## 快照与事件

快照Task与event_cursor来自同一Task行的同一次读取，不能使用全局sequence最大值。写事件与Task更新同事务，取消先锁Task再递增序号。TaskEvent只提供归属、版本、时间、trace和短摘要，不包含凭据/原始证据。

事件after排他；首次省略after时从任务sequence=0开始读取有界历史，为详情状态变更记录提供入口。签名游标绑定用户、权限版本、项目、任务、位置，有效900秒。跨上下文422，过期或权限版本变化410 CURSOR_EXPIRED。默认50/最多100，空页保留原游标（首次空页签发位置0），has_more判断额外一条；每页重新鉴权。快照游标不绑定分页limit。事件可重复读取但不触发操作。

## 页面与恢复

新增 `/projects/:projectId/tasks` 和 `/projects/:projectId/tasks/:taskId`；保留new路由并开放有效预览的“创建任务”。真实列表、详情、取消、原键核对和状态变更记录；沿用Ant Design五主题、生成响应校验器和身份/项目代次。详情只显示真实queued/cancelled及scope版本等DTO字段，不显示执行进度或证据占位。

命令客户端：一次操作一个UUID，内存冻结原请求；202后查Task实际状态。当前标签页sessionStorage只保存用户/项目/幂等键/kind/必要资源ID/时间，不保存URL、请求正文、凭据。每项目一个未确认命令，记录保存成功才发送；存储失败显示可重试错误并不提交。现页未知结果允许查键/显式原键原请求重送，禁止自动换键。刷新后仅恢复只读核对；404保持“提交结果待确认”，不得推断失败或重构原请求重送。允许查看列表后明确确认放弃旧核对再新操作。确认放弃只是本地记录操作，不代表服务端已取消。

注销/身份变化清除记录；项目切换中止旧请求、归属隔离。权限变化重新鉴权，不把权限版本本身作为键丢失理由。回执查到后清除pending并进入实际任务；迟到响应/错误必须验证代次和项目。列表操作后或focus刷新，保持分页位置。

可见详情5秒读事件，单请求串行、每轮最多5页，整页校验处理成功才推进。事件触发权威快照刷新、不拼装状态；快照按version防倒退。瞬态错误10/20秒退避，连续3次后手动重试。隐藏暂停，重新可见重同步，终态停止周期轮询。410重新快照；401/项目404清理视图。轮询不自动重发写操作。

## 最小验收

1. 合法新预览创建→列表/快照→取消，验证状态/回执/事件。
2. 同键重放与两请求并发只创建一个Task；变更请求409。
3. 过期/旧B1预览、输入不一致、Viewer写入和跨项目拒绝。
4. 新版本冲突与已接受命令重放顺序；回执仅原提交者可见。
5. 快照后取消可补事件，小页补页及空页保持位置。
6. 一条真实Chrome流程：服务端创建已提交但响应被丢弃，刷新按原键恢复→查询→取消。

所有代理共用600秒（构建、等待、脚本排查、复跑），同类helper最多两轮，必要检查通过即停。未变pure函数与Phase1A证据复用，旧B1仅更新直接变化预期。压力、长断线、全主题、旧回调专项延期。验收绑定SHA/run_id/命令/退出码/证据和实际执行者。
