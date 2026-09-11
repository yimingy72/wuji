# D3-B 正式创建、任务授权与配置快照 Spec

- 状态：**approved / in-progress**；2026-09-11。用户已批准完整核心闭环计划；本Spec为M1实施基础，最新执行顺序与对接字段见[实施合同](execution-contracts.md)，不代表已经实现或通过验收。
- 起点：`codex/phase-1c-creation-prototype@276b6a8`，沿用 phase-1c-prep 工作树；已纳入同树尚未提交的架构交接，保留其来源与候选状态。
- 当前应用为 Default 模式。按根 AGENTS 可准备下一阶段草案；没有自行切换 Plan 模式，没有把 D3-A 标成用户已确认。
- 背景：[项目索引](../../project-context.md)、[D3-A Spec](../phase-1c-creation-prototype/spec.md)/[评审](../phase-1c-creation-prototype/acceptance.md)、[D1](../phase-1c-control-plane/spec.md)、[D2](../phase-1c-model-config/spec.md)、[安全场景交接](../../cairn-security-specialization-handoff.md)、[架构决策](../../cairn-architecture-decision.md)、[评估模型](../../assessment-model.md)。
- 配套：[核心闭环总计划](core-loop-plan.md)、[本里程碑Plan](plan.md)、[Goal 模板正文](goal-templates.md)、[调度衔接提案](execution-handoff.md)、[验收状态](acceptance.md)。

## 1. 交付目标

最新优先级：用户明确要求尽快完成整个任务测试核心。本Spec定义核心总计划的M1，ready不是最终交付；M1之后连续推进权威执行账本、Cairn/Pi/共享Kali、结果与停止，不再把每个小切片包装成新的产品终点。创建入口反馈已在D3-A定向补丁落实，不要求用户重复描述同一问题。

真实链路为：组织管理员维护模型 → 操作员选择场景与目标 → 保存/恢复个人草稿 → 预览范围与配置 → 本人确认范围 → 创建 ready Task → 原键核对/刷新详情 → 取消未执行 Task。

本批只允许 Web 单点正式创建，五类场景均提供默认 Goal/完成条件并支持草稿。用户确认的是“提供模板且允许自定义”；模板具体正文与下述字段属于本次待评审方案。其他四类创建返回明确阻断，不因为有模板而开放执行。

不新增 start，pause/resume 继续拒绝；不创建 Pod、AgentRun、Cairn Project、网关 Task Key、工具调用、覆盖率或报告。不触发模型检查、代码下载、DNS 解析和目标请求。模型配置页只有管理员显式检查动作可以请求网关，测试只使用合成上游。

本批 ready 表示“创建信息已固定、等待启动”，不是“执行条件均已就绪”。详情显示启动未开放原因，不显示虚构运行环境或消耗。创建快照与后续执行配置分开，见第 6 节。

## 2. 用户场景与界面

保持 D3-A 四步和五主题。正式路由保留项目归属，不直接搬用原型无项目路由。

1. 场景与目标：普通模式切换不弹窗；Web只填一个“测试地址（URL）”，其他模式填写题目/源码等对应内容。默认带出可编辑的“任务目标与完成条件”。名称按地址建议、可展开修改；一个“补充线索（可选）”入口承载已知信息/已有尝试/关注功能，不要求区分Origin/Hint。匿名Web不提供账号/Cookie，固定禁止项不要求抄写。
2. 对象与范围：包含/排除规则、协议端口、明确授权截止时间；入口可含路径，路径不成为 ACL。截止时间与预算不自动填值。
3. 模型与预算：从组织发布的可用版本中选择，单一版本可以预选；金额为正数 USD 十进制字符串。没有方案或原方案失效仍可保存草稿，不自动替换原选择。
4. 确认并创建：服务端返回规范化 Goal/完成条件、范围、期限、模型版本、公司价格与金额上限；用户确认范围后提交。目标、规则、期限改变清除范围确认；其他输入改变使旧预览失效。

完成条件在第一步直接可见，不只放在隐藏高级区域。模板来源显示“Web 单点 · V1”；编辑后显示“已自定义”，不让用户输入原生 Cairn JSON、Fact ID 或调度参数。选择其他场景先保留各场景在当前会话内的未保存输入；不得用新模板静默覆盖自定义内容。恢复默认需要明确点击，只覆盖目标和完成条件。

草稿显式保存。返回/主题切换不丢当前输入；离开含未保存修改的页面提示保存或放弃。真实刷新只恢复最后一次服务端保存内容，页面不承诺恢复未保存正文。进入确认页前先完成草稿保存，存储冲突保留本地输入，由用户决定重新载入或复制为新草稿，不覆盖远端。

正式任务列表按已存在的游标方式读取，增加任务/个人草稿切换并分别保持分页。列表不显示尚未实现的全局总量。创建成功进入详情，原草稿保留并显示最近创建任务的入口；不自动删除草稿。再次创建是新的显式操作，不靠修改回执复用已有 Task。

## 3. 草稿和模板版本

继续使用 SavedTaskDraft 身份、私有归属、expected_version 和紧邻同输入重放。新增 content.schema_version=`2.0`；`1.0` 仍可读取/保存，不批量改写原内容/摘要。

新版本复用五类 scenario、name、objective、model_profile_version_id、budget_usd 及各场景输入。1.0的starting_point/constraints保持兼容；2.0不再让用户填写同名框架字段，新增：

| 字段 | 意义 |
| --- | --- |
| goal_template | 可空的 {id, version, digest} 来源；引用平台内置不可变版本，不接受任意模板地址 |
| completion_criteria | 最多 20 条可编辑完成条件文本，每条最多 1000 字符；保存允许空，创建要求至少一条非空 |
| supplemental_hints | 最多8000字符的可选补充线索；供后续装配Hint，不是强制执行限制或已验证Fact |
| authorization（Web） | 可空；包含 includes、excludes、valid_until，schema_version=1.0 |
| include rule | host、include_subdomains、endpoint:{scheme:http/https,port:1..65535} |
| exclude rule | host、include_subdomains、endpoints: all_included 或明确协议端口对列表 |

已有文本长度、引用/资产上限、正金额与 64KiB 规范化内容上限继续有效。草稿允许缺项或业务上无效（如已过期/全排除），但填写字段必须格式有效。没有 Reference/Runtime 发布服务时，只保留旧草稿引用，不伪造资源；Web 创建若仍带未支持的引用，应显示不支持且阻止创建，不静默丢弃。

读取旧 Web 草稿不授权转换：编辑器可把入口与 additional_origins 显示为候选包含项，按旧 include_subdomains 只对应入口主机；明确提示检查新范围。升级保存显式写 2.0，截止时间和完成条件缺失需补充，确认记录重新取得。旧 1.0 草稿不直接用于新版创建，返回需要升级并确认。

旧starting_point可以显示为待核对补充线索；旧constraints非空则保留原字段/旧版本并显示待处理限制，不静默合并成软性Hint或在升级时丢弃。暂不支持强制实施的限制不能承诺生效；用户明确处理后再保存新版。新Origin由结构化URL、匿名起点和实际输入引用装配；自定义Goal或Hint不覆盖平台禁令。未来真正的额外限制需有受支持的高级选项和执行器，本批不放空控件。

模板首版随服务发布的资源提供，不增加模板管理后台、租户模板 CRUD 或新配置角色。模板 ID/版本/digest 及完整文本固定进创建快照；已有草稿不自动跟随新默认版升级。自定义不允许改变平台 Scope、禁止项、权限或金额限制，模板也不证明“已测试”或“目标达成”。

草稿响应增加可选的服务端 model_selection 摘要：version_id、已观察过的名称/版本、available/unavailable/unresolved。保存时只从当前用户可选择的方案取得摘要；同引用失效后保留原摘要，不把另一个租户或未经可见性核验的 UUID 解析成可读模型信息。不让浏览器提供可信模型名称/价格。旧草稿无摘要则显示“原模型版本不可用”，不绕过 D2 RLS 查询未发布配置。

## 4. Task 自有授权

新授权仅供本 Task，创建者确认记录不等于平台已验证资产权属。沿用 Operator 的 task.create 权限，不赋予组织管理员、ScopeManager 或其他项目访问权。

- 包含域名默认自身；勾选子域后匹配自身及所有后代。IP 只匹配自身，不支持网段/CIDR、通配符字符串或 DNS 自动关联。
- 域名小写、移除结尾点、按标签边界匹配，沿用现有 URL 标准化的 IDNA 规则；IP 使用标准地址解析，IPv6 用规范形式，禁止 zone ID。入口含凭据/fragment 拒绝。
- 协议与端口为成对条件，HTTP/HTTPS 默认端口仅从入口解析；不隐式扩到其他端口。裸 host 字段不能含 scheme/path/query/port。
- 排除优先；域名排除默认含下级，IP 排除仅自身；all_included 仅指本任务包含的协议端口，不能产生新授权。
- 入口被排除、入口不在包含集合或整个有效范围为空，can_create=false；仍允许保存草稿。
- 不枚举真实子域；有限排除不能被猜成已穷举无限子域集合。整项为空只在规则集合能证明全部包含被覆盖排除时成立。
- 授权时间使用服务端创建时间作 valid_from，用户提供带时区 valid_until，提交时必须仍在将来。不给默认 24 小时或永久期限。
- 确认正文版本、规范化规则摘要、确认者、permissions_version、时间均由服务端保存。客户端只回传预览摘要及 accepted=true，不能声明确认者或确认时间。

旧 scope_policy_versions、authorization_records 和路径字段不删除、不复制成全域。新版授权不列入旧 GET /scopes，旧 HTTP 创建也不能引用它。父域、兄弟域、IP 与域名不通过“看起来相关”互相授权。模型撤销/授权到期不重写初始快照；后续执行准入另外检查当前状态。

## 5. 公开契约提案

沿用 OpenAPI 0.5.0 开发候选与现有 /api/v1；正式主工作区仍为 0.4.0。新请求和返回必须生成类型/校验器，禁止手改生成物。

下表相对前缀为 /projects/{project_id}：

| 接口 | 增量及返回 |
| --- | --- |
| GET /scenario-profiles | 有项目读取权限返回 5 个内置 ScenarioProfileVersion，包含默认 Goal/完成条件、digest、can_create 与阻断原因；固定有界集合，无模型请求 |
| PUT/GET /task-drafts/{draft_id}，GET /task-drafts | 兼容 1.0 与 2.0 内容；保留 D1 路径和版本机制，增加 model_selection 与最近创建任务摘要（仅可见时） |
| POST /task-creation-previews | 新版专用预览；请求 {draft_id,draft_version}；返回 200 TaskCreationPreview，业务缺项返回 blockers，不创建 Task |
| POST /tasks | 原请求完整保留；新增 creation_kind=saved_web_draft 的互斥请求分支；成功仍返回 202 CommandReceipt |
| GET /tasks、GET /tasks/{task_id} | 混合旧/新类型读取；旧 Task 响应字段不变，新 WebTask 明确 task_kind=web_assessment 和 ready/cancelled |
| POST /tasks/{task_id}/commands | 原 cancel/version/回执语义扩展到未执行 ready；pause/resume 仍 409，start 不纳入请求枚举 |
| GET /commands/{command_id}、GET /command-keys/{key}、GET /tasks/{task_id}/events | 不改原键归属、回执不可变及快照游标规则 |

TaskCreationPreview 包括 preview_id、draft_id/version、input_digest、authorization_digest、normalized_content、model_snapshot（可空）、expires_at、can_create、blockers、start_available=false。只保存当前用户可见输入；不可见草稿 404。有效期复用已有预览配置，不增加产品默认授权期；模型缺失/范围无效也能返回受阻预览。

创建新版请求：
```json
{
  "creation_kind": "saved_web_draft",
  "draft_id": "<uuid>",
  "draft_version": 2,
  "preview_id": "<uuid>",
  "input_digest": "<sha256>",
  "scope_confirmation": {
    "accepted": true,
    "authorization_digest": "<sha256>"
  }
}
```
Idempotency-Key 仍在原请求头；新分支不重复提交整个草稿正文，服务端读取版本固定内容。摘要覆盖场景、目标/完成条件、起始条件、约束、入口、范围、期限、模型版本/内容、公司价格、金额以及权限版本。预览不把摘要当鉴权；确认和创建仍复核当前权限。

错误分类：
- 401 未登录/失效；403 当前写权限拒绝；不可见草稿、项目、任务或他人回执 404。
- 409 VERSION_CONFLICT（草稿/权限版本变化）、PREVIEW_EXPIRED、IDEMPOTENCY_CONFLICT、MODEL_UNAVAILABLE 或 CREATION_BLOCKED；客户端重新预览或调整输入，不静默换模型。
- 422 格式不合法/摘要或确认内容不匹配；原 start 非法动作仍按现有请求校验拒绝，不返回无消费者的 202。
- 503 数据库不可用/结果可能不明；网络错误、响应校验失败、未知 5xx 与查键 404 均不能等价为“未创建”。
- 受阻预览 code 明确映射字段：MISSING_INPUT、DRAFT_UPGRADE_REQUIRED、SCENARIO_UNAVAILABLE、INVALID_SCOPE、ENTRY_OUT_OF_SCOPE、ENTRY_EXCLUDED、EMPTY_SCOPE、AUTHORIZATION_EXPIRED、MODEL_UNAVAILABLE、UNSUPPORTED_CONFIGURATION。

## 6. 快照与状态

创建同一事务固定 CreationConfigSnapshot：
- scenario、模板来源与完整默认正文、用户实际Goal/完成条件、补充线索；结构化入口/匿名起点与平台策略引用分别保存；
- draft ID/version/digest、入口、授权 ID/version/hash 与确认正文；
- 模型方案/服务版本引用、实际 model ID、容量、输出/超时和公司计价来源/缓存模式/单价；
- USD 金额上限、snapshot ID/schema/digest、创建者与时间。

不包含 API Key、网关管理 Key、内部凭据、假的 Runtime/Prompt/Tool/Harness 发布版本。D2 管理模型中的路由与原生 ID 只进入后端内部字段，普通任务响应不公开管理连接信息。

本批 Task 绑定 creation_config_snapshot_id；execution_config_snapshot_id 未建立，不提前添加可写空快照表。后续启动前才能从已发布运行能力生成 ExecutionConfigSnapshot，并引用创建快照，固定镜像、工具、Prompt、Pi 及控制策略实际版本。显式绑定时展示新增运行配置；不得悄悄改变已有目标/范围/模型/价格/金额。架构中完整 ConfigSnapshot 在正式执行前必须具备，D3-B 不宣称完成该部分。

新 Task 初始 ready/version=1/event_sequence=1；active_calls=unknown_calls=0、egress=not_granted、cleanup=not_required、assessment=not_assessed、stop_reason=null。取消原子转 cancelled/version=2/sequence=2。旧 queued/cancelled 及回执保持原意，旧 Task 没有创建快照不能补造 Goal/价格/授权。

新 WebTask 列表返回名称、入口、状态、创建/更新时间、task_kind、task scope binding、version、allowed_actions 和现有执行摘要；详情快照在该任务对象中增加固定 creation_config，event_cursor 仍从同次任务读取的 event_sequence 生成。模型的当前可用性是单独的实时提示，不回写快照或降低已有事件版本。

Task/Cairn 绑定在后续唯一控制消费者上线时接入；D3-B 没有实际调用就不生成“已绑定”标记、孤立 Outbox 或空转 start。后续可给本批 ready 补建探索上下文，但必须由权威许可拒绝未启动派发；不自动接管旧 queued。这是分批交付边界，完整目标仍为一个 Task 一个原生 Cairn Project。

## 7. 创建事务、幂等与恢复

1. 会话、Origin、CSRF 检查后，取得当前用户事务锁；重新确认项目/租户有效与 Operator 身份。
2. 先按原用户/项目/UUID 键查回执，规范化完整命令摘要相同则返回原回执；不同返回 409。已有回执不重新检查过期预览、旧草稿版本或当前模型发布状态。
3. 新命令复核 permissions_version，锁定个人草稿行，对照 preview_id/归属/版本/内容摘要。预览不可见为 404，过期为 409。
4. 获取与 D2 publish/retire/revoke 共用的模型版本协调锁；在锁后重新查询 published/synced、容量和完整价格。检查本次授权有效期、模板及确认摘要。
5. 同一 PostgreSQL 事务写 Task、任务自有授权、创建快照、原命令回执、首个事件及草稿最近创建引用。任一失败整体回滚。事务内不调用 LiteLLM/Cairn 或其他外部服务。
6. 202 后客户端核对回执并读取 Task 实态；读取失败保持核对/重试入口，不把原创建当普通失败。

模型锁按 tenant/version 派生独立命名空间的 PostgreSQL advisory transaction lock；D2 本地状态变更和新创建均遵守，远端阻断在锁外。先撤销成功则创建拒绝；先创建提交则快照保留，但撤销阻止后续启动。用户锁不能协调不同用户，这里不复用用户锁冒充跨用户互斥，也不扩大普通项目成员模型写权限。

相同原键并发使用现有用户事务锁和回执唯一约束，只能产生一份 Task/事件/回执。同草稿不同键属于不同操作，后端不按相似内容合并；界面需要先放弃旧核对才允许发起新操作。

客户端继续 sessionStorage 最小标记 + 内存冻结请求；存标记失败不提交。同项目一个待确认命令，包含已接受但尚未成功读取 Task 的情况。刷新只按原键读回执，不从当前草稿拼装旧请求。404 保持待确认；查看列表再明确放弃只清核对，不取消潜在任务。身份/项目/权限变化中止请求并校验上下文代次和原键，迟到结果不能覆盖新状态。

## 8. 模型配置正式前端

复用 D2 全部管理能力，不建新模型 SDK/模型管理协议。TenantAdmin 与项目角色独立：管理员无项目权限仍可进入组织模型设置，Operator 无管理权没有编辑入口。

组织设置路径 /settings/tenants/{tenant_id}/models，任务路径保持 /projects/{project_id}/tasks 及 drafts/{draft_id}。前后端登录回跳白名单同步扩展，只允许已知路径和有限 step/cursor/tab 参数，禁止任意 redirect。

服务新版本必须重输 Key；成功清除临时 Key，请求/响应不能进入普通日志或持久缓存。结果不明按 D2 原操作键查询，不重新保存；服务无连接检查和发布动作。方案名称、版本、容量、超时、pricing=null、价格来源和显式缓存模式完整对应 D2。

检查只在显式点击发生，结果未知只读核对；保存/选择/发布/页面探针绝不暗中请求模型。撤销展示平台状态与网关阻断分别表达；创建预览和提交均重新检查，不能只靠前端禁用按钮。

## 9. 最小验收与延期

固定候选执行以下 6 组，不扩张压力/完整主题矩阵：
- C1：五模板与自定义/草稿恢复；Web 完整创建、刷新详情和取消，确认快照不被模板/模型/草稿后续变更覆盖。
- C2：包含/排除优先、入口拒绝与空范围可保存不可创建；截止过期、旧草稿升级需确认；旧路径 Scope 和 queued 语义保持。
- C3：同键重放及一次双请求并发只写一任务/事件；改摘要冲突；旧回执先于新前提检查。
- C4：Viewer、他人草稿、跨项目/租户与撤权拒绝；模型撤销和创建用一个确定性同步点验证排序。
- C5：一条真实浏览器丢创建响应→刷新原键恢复→查看配置→取消；保留创建四态和分页，检查迟到结果隔离。
- C6：模型配置页真实 API 表单与 D2 错误映射；缺价/未选缓存模式/Key 重输/撤销提示。需要连接检查时仅合成上游，复用 D2 原生网关证据，不再跑网关重启。

一次契约检查、API 包及正式前端构建、改动范围 AntD 检查；后台核心用自有临时 PostgreSQL/ASGI，浏览器用隔离测试服务。无累计时间预算，通过即停，文档修改只校对 diff/链接。详细命令见 Plan。

未覆盖：真实目标/模型、金额耗尽、多 Agent/长任务压缩、Kubernetes/LiteLLM 故障矩阵、Cairn Core 集成、完整报告/覆盖。Phase 1A partial 不因本批通过改写。交付仍保留主工作区服务/数据库/master；正式切换必须使用正常启动流程，不修改绑定 SHA 绕过验证。
