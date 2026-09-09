# Phase 1 API 契约说明

- **契约版本**：0.2.0；OpenAPI 3.1.1
- **状态**：可校验的接口基线；CORE 已实现两个健康端点，身份与项目接口在 SERVER 批次实现，任务/证据接口仍为后续阶段设计
- **权威文件**：[openapi.yaml](../packages/contracts/openapi.yaml)
- **生成类型**：[api.d.ts](../packages/contracts/generated/api.d.ts)
- **响应校验器**：[@wuji/contracts/validators](../packages/contracts/generated/validators.js)，从同一 Schema 生成的 standalone ESM
- **共享夹具**：[phase1.json](../packages/contracts/fixtures/phase1.json)
- **Phase 1A 夹具**：[phase1a.json](../packages/contracts/fixtures/phase1a.json)，与原型含未实现权限的夹具分开

## 1. 首版范围

本契约覆盖21个设计操作。0.2.0 在原15个操作上增加登录/回调/退出、项目详情和两个健康端点。Phase 1 暂不暴露通用工具执行接口、模型调用、配置发布、SSE、Finding 工作流或报告发布。后续能力必须扩充契约及验收后接入。

统一同源前缀为 `/api/v1`。项目 ID 来自路由，但租户和访问上下文由服务端建立；客户端提交的资源 ID、游标或对象摘要均不是授权。所有业务响应禁止缓存，错误返回结构化 `Error`，客户端不能把错误页当作空列表。

会话 Cookie 名称为 `wuji_session`，写操作同时要求 `X-CSRF-Token` 和服务端 Origin 校验。首个身份提供方已选定 Keycloak OIDC + Authlib，具体握手、会话和权限行为见 [Phase 1A Spec](stages/phase-1a/spec.md)。公开的登录/回调/健康操作显式取消根 Cookie 安全要求；原型演示身份不构成登录实现。

## 2. 接口清单

下表中 `P` 表示 `/projects/{project_id}`，所有地址均相对 `/api/v1`。

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/auth/login` | 创建浏览器绑定握手，302到配置IdP |
| GET | `/auth/callback` | 成功或失败均303回允许的站内页面，失败只含白名单错误和trace_id |
| POST | `/auth/logout` | 校验会话/CSRF/Origin，撤销提交后204 |
| GET | `/session` | 当前身份、会话有效期、CSRF Token 和权限版本 |
| GET | `/projects` | 按权限分页列出项目 |
| GET | `P` | 可访问项目详情，不存在与无权均404 |
| GET | `P/scopes` | 已批准且当前可用的 HTTP Scope 版本 |
| POST | `P/task-previews` | 规范化输入，返回服务端有效范围预览 |
| GET | `P/tasks` | 稳定游标分页列出任务 |
| POST | `P/tasks` | 接受创建命令，返回 202 和 CommandReceipt |
| GET | `P/tasks/{task_id}` | Task 权威快照及一致事件游标 |
| POST | `P/tasks/{task_id}/commands` | 提交 pause / resume / cancel |
| GET | `P/commands/{command_id}` | 读取命令接受回执 |
| GET | `P/command-keys/{idempotency_key}` | 响应丢失时核对原命令 |
| GET | `P/tasks/{task_id}/events` | 从游标补发持久事件通知 |
| GET | `P/tasks/{task_id}/artifacts` | 分页读取可查看证据元数据 |
| GET | `P/artifacts/{artifact_id}` | 单个证据的归属、摘要和可用性 |
| GET | `P/artifacts/{artifact_id}/preview` | 有大小上限的脱敏纯文本预览 |
| GET | `P/artifacts/{artifact_id}/download` | 经重新鉴权的附件下载 |

另有根路径 `GET /health/live` 和 `GET /health/ready`，通过操作级 `servers: [{url: /}]` 保持在 `/api/v1` 之外。存活200，就绪失败503；当前CORE未配置数据库时ready保持503。运行文档只公开已注册路由。

权限码是动作能力标识，由现有角色映射得到；不引入另一套角色管理。0.2.0追加`project.read`，保留`task.read/create/control`和`artifact.read/download_sensitive`。Phase 1A有效Viewer/Operator与已实现能力求交后只返回`project.read`，不能提前开放任务或证据功能；Viewer的普通查看能力不自动获得敏感原件下载能力。

项目列表使用`limit/cursor`、默认50/最多100、按`(created_at,id)`降序；游标绑定用户、权限版本、limit和最后排序键，15分钟到期。篡改或跨用户422，过期或权限版本变化410 `CURSOR_EXPIRED`，每页重新鉴权。

## 3. 预览与创建

TaskDraft 包含名称、已批准 Scope 的 ID/版本、一个目标 URL、固定 `http_observe`、GET/HEAD 方法和执行限额。首个契约把规模限制为最多 200 请求、2 请求/秒、并发 2、单次 10 秒、响应 1 MiB、任务 600 秒；这些是首个验证切片的上限，不是整个平台最终容量承诺。服务端还要与已批准 Scope 和上级限额求交。

预览只做输入规范化和策略计算，不执行 DNS、目标探测或模型调用。预览绑定当前用户、项目、规范化后的完整输入、Scope 版本和短时有效期；`can_create=false` 必须给出 blocker。前端修改输入后丢弃旧预览。

创建提交 `preview_id`、`input_digest` 和完整 draft。服务端重新计算摘要，检查绑定关系、权限、有效期、版本和业务端点语义，然后在同一事务内写入 Task queued、CommandReceipt 和 Outbox。固定到期时间不能由客户端延长。请求只携带已批准的策略引用，不接受客户端提供更宽的 origin 或任意工具配置。

URL Schema 只校验 HTTP(S) 语法和长度；实际 URL 规范化、路径段边界、编码、凭据、DNS/连接和重定向检查仍由平台策略及出口执行。JSON Schema 校验通过不等于获得执行授权。

## 4. 幂等命令与并发

创建和控制命令必须携带 UUID 格式的 `Idempotency-Key`。同一用户、项目内的 Task 命令共用键空间，键绑定命令种类、目标 Task 以及规范化完整请求摘要；复用键但更改内容返回 409 `IDEMPOTENCY_CONFLICT`。

服务端先检查当前身份与资源访问权限，再核对已接受命令。相同键、相同输入返回原始回执；即使 Task 已推进到新版本，也不能对重投的旧请求再次执行版本检查后误报冲突。新控制命令才以 `expected_version` 做原子比较更新。

| 情况 | 服务端行为 | 客户端行为 |
| --- | --- | --- |
| 创建响应丢失 | 相同键返回同一个 task_id | 按原键查询或重送完全相同的请求 |
| 取消响应 202 | 返回不可变接受回执；Task 进入 cancelling | 展示取消中，继续查询执行状态 |
| 原键查询 404 | 可能尚未提交，不能证明原请求未执行 | 保留原键重送相同请求，不自动生成新键 |
| 新控制请求版本冲突 | 409 VERSION_CONFLICT，不执行操作 | 重新获取快照；用户重新发起操作时使用新键和新版本 |
| 权限被撤销后重投 | 当前鉴权拒绝，不返回旧敏感回执 | 清理视图并停止重试 |
| 同一命令同时到达多个 API 副本 | 唯一约束和事务协调产生一份接受结果 | 消费相同回执，不以按钮禁用代替服务端去重 |

服务端幂等记录最少保留 24 小时，并覆盖允许的客户端核对窗口；记录存续及清理要有可观测策略。超过窗口的结果不明命令需显式核对，不能宣称长期无限去重。

CommandReceipt 的 `accepted_task_version` 记录接受时版本。回执不随实际执行失败改写，也不用于表示最终结果；客户端按 task_id 读取当前 Task。取消接受必须与“禁止新执行许可”的权威状态更新处于同一事务，不能仅把取消命令丢进队列后继续授权。

## 5. 状态与事件

Task 状态枚举沿用主架构。API 将执行状态、`cleanup_state`、活动/待核对调用数和出口状态分别提供。completed、cancelled、failed 要求活动及未知调用都为零、出口 revoked，且不能继续接受控制动作；paused 要求调用已排空且出口 frozen。条件 Schema 检查这些响应声明自洽，真实状态仍必须由执行端证据支持。

任务快照和 `event_cursor` 需要来自一致的已提交视图。数据库自增序号的分配顺序不保证事务提交顺序，服务端不能直接用“当前最大序号”作为已完整交付的游标。后端实现应选择能证明完整性的任务流序列化或发布游标方案，并用并发事务测试验证。

事件查询使用排他的 `after` 和有界 `limit`，空结果保持游标，`has_more` 表示是否继续补页。游标超出保留期返回 410 `CURSOR_EXPIRED`，前端重新获取快照。事件包含资源归属、版本和简短摘要，不包含原始证据正文；重复通知只能刷新视图，不能触发新的目标操作。

首版列表按稳定的 `(created_at, id)` 降序及绑定项目/查询条件的游标分页，每页默认 50、最大 100；任务名称筛选和排序扩展尚未进入接口。本地原型的示例筛选不是服务端分页或筛选实现。

## 6. 证据与错误

预览先按 Artifact ID 重新鉴权、检查归属和分类，再返回不超过 65,536 字符的脱敏文本；不足或截断明确标记，不渲染目标 HTML/SVG。请求不能提供一个任意 URL 让服务端代抓内容。无法安全预览的文件走下载或明确拒绝路径。

附件下载由 API 代理，返回 attachment、nosniff 和 no-store；受限原件要求独立权限并记录审计。首版不发放对象存储通用凭据或公开签名链接。到保留期限的证据返回明确不可用状态，不替换成最新文件。

错误主要区分 401 会话失效、403 无权限/CSRF、404 当前不可访问的资源、409 版本/幂等/状态冲突、410 游标或证据过期、422 输入不符、429 限额和 503 权威依赖不可用。敏感错误不回显凭据和跨租户资源信息，trace ID 用于后端核对。

## 7. 校验和变更

执行 `pnpm contracts:generate` 从 OpenAPI 生成类型，`pnpm contracts:check` 检查生成物一致性和 OpenAPI 结构，`pnpm test` 使用 Ajv 2020 校验共享夹具和关键反例。选择 OpenAPI 3.1.1 是为了使用与 JSON Schema 2020-12 对齐的 Schema 方言；校验器及生成器版本固定在锁文件。[OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)、[Ajv Schema 支持](https://ajv.js.org/json-schema.html)

夹具中的域名为示例域名，令牌和摘要为明确的占位数据，不代表可执行授权或真实证据摘要。前端依赖生成类型，CI 检查夹具符合 Schema；当前原型没有把网络响应通过运行时校验器接入，这属于正式 API 客户端的后续工作。

新增字段、枚举和操作先修改 OpenAPI 与反例，再重新生成类型，检查前端状态标签及错误处理。破坏兼容性的字段/状态变更必须升级契约并给旧客户端明确失效路径。服务端鉴权、并发幂等和停止时限只有集成测试后才能标记通过，不能由契约测试代替。
