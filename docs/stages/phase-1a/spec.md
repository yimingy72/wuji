# Phase 1A Spec：正式工程与平台基础

- 状态：approved；按已评审范围实施
- 日期：2026-09-09
- 负责人：主代理
- 实施批准依据：2026-09-09 方案评审收口后，用户回复“可以，继续”，批准按本阶段 Spec / Plan 开始实施
- 上游：[架构 v0.4](../../architecture.md)、[Phase 1 契约](../../phase1-api-contract.md)、[协作流程](../../development-workflow.md)
- 方案评审：[修订记录](review.md)

## 1. 可交付结果

使用现有 Docker Desktop Kubernetes 启动开发依赖，启动正式 Platform API 与 `apps/web`，完成真实登录、会话、数据库项目查询及五套主题切换。重启 API 后仍可读取原项目和有效会话，登出或撤销权限后不能继续访问。

阶段不开放任务创建/执行、Scope 管理、Runtime、模型网关、Agent、SSE、资产/报告或知识管理。现有内存原型保留独立入口，不作为正式应用的数据源。下一阶段沿用本阶段的身份、事务、契约和前端基础层。

## 2. 运行环境与技术方案

| 部分 | 本阶段默认选择 |
| --- | --- |
| Python 平台工程 | Python 3.13.15 标准 GIL + uv；FastAPI / Pydantic / Uvicorn；一个 Platform API 业务服务 |
| 数据访问 | PostgreSQL 18.6、SQLAlchemy 2.0、psycopg 3；Alembic 迁移；API async engine、迁移 sync engine |
| 首个身份提供方 | Keycloak 26.7.2 的 OIDC；Authlib 处理协议，Wuji 保存应用会话与项目权限 |
| 本地开发 | macOS 运行 API/Vite；现有 `docker-desktop` 集群运行 PostgreSQL/Keycloak；kubectl Kustomize 清单和固定端口转发 |
| 正式前端 | 沿用已固定 React/TypeScript/Vite/Ant Design/Router/Query；新增 `apps/web`，不复制原型 Mock 控制逻辑 |
| 部署边界 | `wuji-dev` 开发命名空间、`wuji-test` 隔离验收命名空间；不创建第二套 Kubernetes，不以 Helm/Ingress 为本阶段前提 |

本机已只读确认 Docker 29.7.2、Kubernetes 1.36.1 Ready、默认 `hostpath` StorageClass；这不能证明 NetworkPolicy 执法或 PVC 实际持久性。CNI/出口仍由 Phase 1C 前的 P0-05 验证，不在本阶段声明任务隔离已通过。

## 3. 用户路径与身份

1. 未登录访问正式应用，进入简洁登录页；登录操作转向配置的 Keycloak，回调后显示当前身份与有权访问的项目。
2. 项目页只列出有效 Membership 对应项目，可选择项目进入基础工作区；未实现的任务操作不显示为可用功能。
3. 会话过期、用户禁用或成员关系撤销后，后续 API 请求拒绝；页面清理旧身份/项目缓存并显示实际状态。
4. 退出时撤销 Wuji 当前应用会话并清除 Cookie；本阶段不承诺注销其他应用的 Keycloak SSO 会话。下一次显式登录可复用 IdP 登录状态，但仍须重查 Wuji 成员关系。

采用 Authorization Code + PKCE S256，Authlib 验证 state、nonce、issuer、audience、签名及有效期。身份唯一键为 `(issuer, sub)`；不能按同名或邮箱自动合并账号，不能把 IdP group/role 直接当作项目权限。

本阶段 ID Token 固定允许 RS256，时钟宽限为 0 秒；discovery 的 issuer 必须与配置的 issuer 完全一致。通过 Authlib 的声明校验配置强制 issuer、audience 与握手 nonce 必需且匹配预期值；不能让 token 的 `nonce_supported=false` 关闭本平台的 nonce 要求。错误或缺失 nonce、错误 audience 即使 azp 正确也拒绝。此处配置已有库的校验能力，不另行实现 JWT 密码学。

OIDC 使用 `response_mode=query`。临时握手状态由后端保存，通过独立的不透明 HttpOnly/SameSite=Lax 握手 Cookie 绑定发起浏览器，5 分钟过期且一次性消费；仅持有正确 state 但缺少对应浏览器绑定的回调也必须拒绝。一个浏览器只保留一个当前握手 Cookie；再次发起登录使请求携带的仍待回调旧绑定失效，并设置新绑定。当前绑定已进入交换时，新登录返回 409 `INVALID_TRANSITION`，提示稍后重试；失去请求进程的交换记录到握手期限后失效，不能永远阻塞重试。并行首次登录以浏览器最后生效的 Cookie 为准，不承诺各个标签页同时登录成功。

回调在交换 code 前原子取得并消费匹配 state/浏览器绑定/期限的记录，事务提交后才调用 IdP；同一回调并发只能一份取得记录，协议/网络失败也不恢复该握手，用户重新发起登录。成功后清除握手 Cookie、撤销被替换的旧应用会话并创建不透明 `wuji_session`：32 字节安全随机值，数据库只保存其哈希及会话记录。IdP token 不进入该 Cookie、URL 或前端持久存储；无需调用 IdP API 的 token 在登录完成后不保留。协议回调参数在访问日志中剔除。

会话绝对期限 8 小时，空闲期限 30 分钟；会话接口返回 `min(absolute_expires_at, last_seen_at + 30 分钟)`。认证检查使用数据库时间，在同一原子条件更新中检查句柄、用户启用、撤销和两个期限后推进 last_seen_at；不能先延长已过期会话再检查。所有成功认证的业务请求计入空闲续期，健康探针和未登录请求不计入；本阶段前端不持续轮询会话续期。项目访问检查当前 Membership，不以长期权限缓存延迟撤销。撤销提交后开始的新请求应拒绝；已返回的数据不声称可追溯收回。

Session 保存独立随机 32 字节 CSRF Token，仅认证存储角色可读，经 `/session` 提供到当前浏览器内存；CSRF Token 本身不是登录凭据。重启 API 不改变有效会话的 CSRF Token。日志、URL 和 Git 均不收录 Session/CSRF/握手凭据。

Cookie 使用 HttpOnly、SameSite=Lax、Path=/。生产必须 Secure/HTTPS；只在显式本地开发 profile 且绑定 loopback 时允许 HTTP Cookie。写请求同时校验绑定会话的 CSRF Token 与允许 Origin；不能只靠 SameSite。登录后的返回地址只接受本站 `/projects` 或其下合法路由，拒绝外部/协议相对地址。

## 4. API 与契约增量

OpenAPI 继续作为权威契约，CORE 已将其扩展为 0.2.0，并生成类型和浏览器校验器；SERVER / WEB 按该版本实施。Session、Project、ProjectPage 和 Error 保留现有字段含义；Permission 枚举追加 `project.read`，保留既有任务/证据枚举。项目角色的有效能力与平台已实现能力取交集：Phase 1A 中有效 Viewer/Operator 均只返回 `project.read`，未实现的任务/证据能力不据此开放入口。

| 接口 | 本阶段行为 |
| --- | --- |
| `GET /api/v1/auth/login` | 验证 return_to、建立握手状态，302 到已配置 IdP；不接受客户端指定 issuer |
| `GET /api/v1/auth/callback` | 成功创建/轮换会话后 303 到允许的项目路由；失败 303 到固定登录页，仅携带白名单错误码和 trace_id，不能回显 code/state/token |
| `POST /api/v1/auth/logout` | 会话 + CSRF + Origin 校验，撤销当前会话并清除 Cookie，返回 204 |
| `GET /api/v1/session` | 返回数据库支持的 Session；未登录/过期 401，依赖故障 503 |
| `GET /api/v1/projects` | 返回有权访问的 ProjectPage；参数沿用 `limit` / `cursor`，默认 50、最大 100，按 `(created_at, id)` 降序，游标绑定当前用户和权限版本 |
| `GET /api/v1/projects/{project_id}` | 返回可访问 Project，未授权与不存在均返回 404，供切换项目和深链接鉴权 |
| `GET /health/live`、`GET /health/ready` | 分别报告进程与数据库/迁移就绪；不返回连接串或内部凭据，ready 未就绪 503 |

登录/回调及健康探针显式声明 `security: []`；logout 保持现有 Session + CSRF 契约。健康探针保留根路径 `/health/*`，在同一权威 OpenAPI 内用操作级 `servers: [{url: /}]` 覆盖业务 `/api/v1` 前缀。CORE 必须对该前缀和安全声明分别检查，不能把登录或探针错误地设为已登录可用。

JSON API 的 FastAPI 输入校验与未捕获异常统一转换为 Error，不能暴露原始异常或框架默认错误结构。非法 return_to 返回 422 `VALIDATION_FAILED`，项目不可访问返回 404 `NOT_FOUND`，数据库/IdP 依赖失败返回 503 `SERVICE_UNAVAILABLE`，未预期异常返回 500 `INTERNAL_ERROR`。浏览器顶层 OIDC 回调是明确的重定向例外：`/login?error=UNAUTHENTICATED|FORBIDDEN|SERVICE_UNAVAILABLE|INTERNAL_ERROR&trace_id=<UUID>`；分别表示协议失败/用户取消、未预置或已禁用身份、依赖失败及内部失败。前端只按白名单显示固定文案，回调始终用该路由处理错误，不能将 code 等参数当框架校验错误直接输出 JSON。无当前有效握手的失败响应不清除可能属于新登录流程的 Cookie。未实现的 Phase 1 操作保持未注册，不返回假成功。

业务响应统一 no-store。运行服务只发布已实现路由的文档；仓库中后续 Phase 1 契约保持“设计基线”状态。真实响应需通过契约验证，不能只比较生成类型是否可编译。

项目列表覆盖当前用户有权访问的所有租户；多租户成员可看到两边的授权项目，不等于允许任意跨租户读取。游标有完整性保护、15 分钟期限，并绑定接口、用户、权限版本、分页条件及最后排序键；篡改/换用户使用返回 422 `VALIDATION_FAILED`，到期或权限版本变化返回 410 `CURSOR_EXPIRED`。翻页始终重新鉴权，不承诺跨页数据库快照；前端使用下一页及本地游标栈返回前页，不虚构总页数或数字页码跳转。

## 5. 数据与权限

本阶段创建 User、ExternalIdentity、Tenant、TenantMembership、Project、ProjectMembership、Session、OIDCHandshake 与身份审计记录。用户为全局登录主体，租户/项目记录使用明确复合外键；会话与身份映射由受信认证模块访问。后续 Task/Scope/ToolCall/Outbox 业务表由 Phase 1B 增加，不先创建整个平台的空表。

`User.permissions_version` 初始为 1。授予/撤销/修改 TenantMembership 或 ProjectMembership、角色或用户可用状态时，在同一数据库事务内递增受影响用户的版本并写审计；幂等命令重放且无变化时不递增。`GET /session` 读取当前版本，不保存登录时的永久副本；禁用用户同时撤销其已有应用会话，重新启用不能复活旧 Cookie。成员撤销只影响对应项目访问，不自动注销用户在其他项目中的会话。

认证存储角色、项目业务运行角色、迁移/初始化角色采用独立凭据和连接入口；API 进程只获得前两者，不执行 SET ROLE，也不持有迁移角色凭据。项目角色只读 Tenant、TenantMembership、Project、ProjectMembership 必要列；四表均启用 RLS，角色非表 owner、无 BYPASSRLS/DDL/TRUNCATE。列表只建立已校验的事务级 user 上下文，详情在该受限事务内验证归属后再设置 tenant/project；缺失上下文返回零授权行，连接池归还后不得残留。

数据库约束包括 `Project UNIQUE(tenant_id,id)`、`TenantMembership UNIQUE(tenant_id,user_id)`；ProjectMembership 用复合外键同时关联上述两者。可访问项目必须同时有有效 TenantMembership 和 ProjectMembership；撤销租户成员关系会使其下项目全部不可读。

RLS 精确关联条件：TenantMembership 行的 user_id 必须是当前 app.user_id；ProjectMembership 行也必须是当前用户，且存在同 `(tenant_id,user_id)` 的有效 TenantMembership；Project 必须存在匹配 `(tenant_id,project_id,app.user_id)` 的有效 ProjectMembership；Tenant 必须存在匹配 `(tenant_id,app.user_id)` 的有效 TenantMembership。所有成员关系均检查有效状态，不能只因用户属于某租户就允许读取该租户所有 ProjectMembership/Project。策略依赖保持单向，避免相互递归。RLS 是对可信服务建立上下文的纵深隔离，不声称能防御已攻陷的共享数据库客户端。

开发种子提供两个租户、多个项目，覆盖 A 租户 Operator/Viewer、B 租户用户、同时属于 A/B 的用户及无项目用户。User/ExternalIdentity 和 Membership 由幂等管理命令准备；不提供开放注册或自动赋予租户管理员。撤销会话、禁用用户、撤销 Membership 由同一管理命令及审计记录实现，供本阶段验收，管理 UI 后续开发。

开发 PostgreSQL 实例可同时承载 Wuji 与 Keycloak，但必须使用独立数据库与角色；测试使用独立命名空间/实例。PVC 仅用于开发数据，不作为生产备份或高可用方案。种子与重置命令限定本项目命名空间和所有权标签，不能修改其他集群资源。

## 6. 前端行为

保留已确认的专业工作台组件风格。登录、项目选择和基础工作区使用同一 AppShell；页面只显示必要操作文案，不呈现内部架构解释。新增路由 `/login`、`/projects`、`/projects/:projectId`。

五套主题为 silver/雾银（默认）、glacier/冰蓝、celadon/青瓷、slate/亮石墨、graphite/原石墨。共享主题模块迁入正式应用；默认按设备保存非敏感主题 ID。有效 URL theme 仅覆盖当前标签页，打开比较链接不改写已保存偏好；用户主动选择时保存新偏好。存储不可用或主题 ID 无效时仍正常显示，主题切换不重建业务状态或重置当前项目/分页状态。

会话与项目数据由 TanStack Query 管理，接口边界执行 Schema 校验。身份代次与项目代次分开；查询键包含用户和对应项目/租户归属，fetch 消费 AbortSignal，返回前复核代次，避免切换后的迟到结果回填。收到 401 时清理身份及全部私有缓存；当前项目 404 时只清理该项目并回到项目选择；发现新的权限版本时丢弃旧项目列表游标并重查权限。只读瞬时网络/503 最多重试 1 次，401/403/404/410 不自动循环，写操作无通用自动重试。

点击退出立即遮蔽私有视图并停止旧请求；只有服务器确认会话撤销或权威确认会话已无效后才显示退出完成。网络失败/503 保持“退出未完成”并允许显式重试，不自动进入新的 SSO 登录；内存只保留完成该次重试所需的会话绑定信息。主题属于非敏感设备偏好，与会话/项目缓存分离。

## 7. 验收标准

| ID | 可观察通过条件 |
| --- | --- |
| P1A-01 | 从冻结依赖和已记录镜像启动；迁移/种子可重复执行；API 重启及 PostgreSQL Pod 重建后，在依赖恢复就绪时原项目和有效会话仍可读取；测试结束前不重置这些数据 |
| P1A-02 | 真实 Keycloak 登录成功；错误 state/nonce/issuer/audience/签名/有效期、跨浏览器、被取代及重放回调不产生有效新会话；并发同一回调至多一份会话；失败回到登录页且无协议凭据泄露 |
| P1A-03 | 应用会话 Cookie 为不透明句柄；绝对/空闲期限、注销、禁用用户均拒绝后续访问；禁用后再启用旧 Cookie 仍无效；IdP token 不进入前端/日志 |
| P1A-04 | 缺失/错误 CSRF 或非法 Origin 的退出请求被拒绝；正常退出事务提交后返回 204 并使旧 Cookie 无效；超时/503 不显示撤销成功，显式重试可恢复 |
| P1A-05 | A 单租户用户无法读取 B 项目，A/B 双成员用户能读取两边授权项目；同租户两用户分别只加入 P1/P2 时不能读取对方成员行或项目；篡改/跨用户/过期游标、池复用、缺失上下文和复合外键反例均符合规定 |
| P1A-06 | 权限修改在同事务递增版本；撤销提交后新请求不可读原项目，释放撤销前挂起的旧 200 也不能回填已清理视图；无项目用户显示真实空状态 |
| P1A-07 | 实际 Session/Project/Page/Error 与权威契约一致；API→DB 失联时 live=200、ready/业务=503；恢复后 ready=200 且原会话/项目可读；空的未迁移测试 DB 同样 fail closed |
| P1A-08 | 五套主题在主页面及浮层可切换，重新打开恢复偏好；URL 临时覆盖、存储故障、键盘操作及当前项目/分页状态保持通过；本阶段不为测试额外创建业务表单 |
| P1A-09 | 前端深链接刷新、登录回跳、退出与项目切换完成；生产构建不包含 Mock/测试凭据，未实现执行入口未开放 |
| P1A-10 | 集群操作限定 docker-desktop 的 Wuji 所有权资源；停止开发进程只清理本次转发/服务，不重置集群 |

P1A-01–10 对应架构 F01/F04/F05/F11/F12 与 S15 的适用部分，不能据此宣告完整 Phase 1 或 80 个架构场景通过。实际身份/数据库/前端检查必须在实施后记录 SHA 和证据。
