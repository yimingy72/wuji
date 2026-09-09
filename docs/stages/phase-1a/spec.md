# Phase 1A Spec：正式工程与平台基础

- 状态：draft；供下一轮 Plan 评审，不代表已批准业务开发
- 日期：2026-09-09
- 负责人：主代理
- 批准依据：无；本轮只获准准备此阶段规划
- 上游：[架构 v0.4](../../architecture.md)、[Phase 1 契约](../../phase1-api-contract.md)、[协作流程](../../development-workflow.md)

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

OIDC 临时握手状态由后端保存，通过独立的不透明 HttpOnly/SameSite=Lax 握手 Cookie 绑定发起浏览器，5 分钟过期且一次性消费；仅持有正确 state 但缺少对应浏览器绑定的回调也必须拒绝。成功后清除握手 Cookie 并轮换不透明 `wuji_session`：32 字节安全随机值，数据库只保存其哈希及会话记录；IdP token 不进入该 Cookie、URL 或前端持久存储。无需调用 IdP API 的 token 在登录完成后不保留；协议回调参数在访问日志中剔除。

会话绝对期限 8 小时，空闲期限 30 分钟；会话接口返回有效截止时间。每次请求检查会话与用户状态，项目访问检查当前 Membership，不以长期权限缓存延迟撤销。撤销提交后开始的新请求应拒绝；已返回的数据不声称可追溯收回。

Cookie 使用 HttpOnly、SameSite=Lax、Path=/。生产必须 Secure/HTTPS；只在显式本地开发 profile 且绑定 loopback 时允许 HTTP Cookie。写请求同时校验绑定会话的 CSRF Token 与允许 Origin；不能只靠 SameSite。登录后的返回地址只接受本站 `/projects` 或其下合法路由，拒绝外部/协议相对地址。

## 4. API 与契约增量

现有 OpenAPI 继续作为权威契约，当前 0.1.0 在此阶段扩展为 0.2.0；实现后再修改源文件并生成类型，本草案不修改当前契约。Session、Project、ProjectPage 和 Error 保留现有字段含义。

| 接口 | 本阶段行为 |
| --- | --- |
| `GET /api/v1/auth/login` | 验证 return_to、建立握手状态，302 到已配置 IdP；不接受客户端指定 issuer |
| `GET /api/v1/auth/callback` | 验证并消费握手状态，创建/轮换应用会话，303 返回本站；无效回调按现有 Error 结构失败 |
| `POST /api/v1/auth/logout` | 会话 + CSRF + Origin 校验，撤销当前会话并清除 Cookie，返回 204 |
| `GET /api/v1/session` | 返回数据库支持的 Session；未登录/过期 401，依赖故障 503 |
| `GET /api/v1/projects` | 返回有权访问的 ProjectPage；默认 50、最大 100，按 `(created_at, id)` 稳定排序，游标绑定当前用户 |
| `GET /api/v1/projects/{project_id}` | 返回可访问 Project，未授权与不存在均返回 404，供切换项目和深链接鉴权 |
| `GET /health/live`、`GET /health/ready` | 分别报告进程与数据库/迁移就绪；不返回连接串或内部凭据，ready 未就绪 503 |

登录/回调使用 OIDC 协议校验，不伪装为已有应用会话鉴权；logout 保持现有写操作的 CSRF 契约。FastAPI 输入校验与未捕获异常统一转换为 Error，不能直接暴露原始异常或返回框架的另一种 422 格式。未实现的 Phase 1 操作保持未注册，不返回假成功。

业务响应统一 no-store。运行服务只发布已实现路由的文档；仓库中后续 Phase 1 契约保持“设计基线”状态。真实响应需通过契约验证，不能只比较生成类型是否可编译。

## 5. 数据与权限

本阶段创建 User、ExternalIdentity、Tenant、TenantMembership、Project、ProjectMembership、Session、OIDCHandshake 与身份审计记录。用户为全局登录主体，租户/项目记录使用明确复合外键；会话与身份映射由受信认证模块访问。后续 Task/Scope/ToolCall/Outbox 业务表由 Phase 1B 增加，不先创建整个平台的空表。

认证存储角色、项目业务运行角色、迁移/初始化角色分离。项目角色非表 owner、无 BYPASSRLS/DDL/TRUNCATE，租户表启用 RLS；事务级 user/tenant/project 上下文从已校验会话和资源归属建立，连接池归还后不得残留。跨租户项目列表按用户 Membership 查询，不能先信任客户端 tenant_id。直接关联不匹配 tenant/project 的记录由数据库约束拒绝。

开发种子提供两个租户、多个项目及 Operator/Viewer/无项目用户。User/ExternalIdentity 和 Membership 由幂等管理命令准备；不提供开放注册或自动赋予租户管理员。撤销会话、禁用用户、撤销 Membership 由同一管理命令及审计记录实现，供本阶段验收，管理 UI 后续开发。

开发 PostgreSQL 实例可同时承载 Wuji 与 Keycloak，但必须使用独立数据库与角色；测试使用独立命名空间/实例。PVC 仅用于开发数据，不作为生产备份或高可用方案。种子与重置命令限定本项目命名空间和所有权标签，不能修改其他集群资源。

## 6. 前端行为

保留已确认的专业工作台组件风格。登录、项目选择和基础工作区使用同一 AppShell；页面只显示必要操作文案，不呈现内部架构解释。新增路由 `/login`、`/projects`、`/projects/:projectId`。

五套主题为 silver/雾银（默认）、glacier/冰蓝、celadon/青瓷、slate/亮石墨、graphite/原石墨。共享主题模块迁入正式应用；默认按设备保存非敏感主题 ID。有效 URL theme 仅覆盖当前标签页，打开比较链接不改写已保存偏好；用户主动选择时保存新偏好。存储不可用或主题 ID 无效时仍正常显示，主题切换不重建业务状态或清空表单。

会话与项目数据由 TanStack Query 管理，接口边界执行 Schema 校验。项目切换/退出提升上下文代次，停止旧请求并拒绝迟到结果回填。主题属于非敏感设备偏好，与会话/项目缓存分离。

## 7. 验收标准

| ID | 可观察通过条件 |
| --- | --- |
| P1A-01 | 从冻结依赖和已记录镜像启动；迁移可重复执行；API 重启后项目与有效会话可继续读取 |
| P1A-02 | 真实 Keycloak 登录成功；错误 state/nonce/issuer/audience、跨浏览器回调、回调重放和外部 return_to 被拒绝 |
| P1A-03 | 应用会话 Cookie 为不透明句柄；过期、注销、禁用用户均拒绝后续访问；IdP token 不进入前端/日志 |
| P1A-04 | 缺失/错误 CSRF 或非法 Origin 的退出请求被拒绝；正常退出返回 204 并使旧 Cookie 无效 |
| P1A-05 | 租户 A 无法读取 B 项目；篡改游标、连接池交替租户和复合外键反例不产生串租 |
| P1A-06 | 成员关系撤销提交后新请求不可读原项目，前端旧请求/缓存不能回填；无项目用户显示真实空状态 |
| P1A-07 | 实际 Session/Project/Page/Error 与权威契约一致；输入错误、DB 失联、未迁移状态有正确错误与 readiness |
| P1A-08 | 五套主题在主页面及浮层可切换，重新打开恢复偏好；URL 临时覆盖、存储故障、表单状态与键盘操作通过 |
| P1A-09 | 前端深链接刷新、登录回跳、退出与项目切换完成；生产构建不包含 Mock/测试凭据，未实现执行入口未开放 |
| P1A-10 | 集群操作限定 docker-desktop 的 Wuji 所有权资源；停止开发进程只清理本次转发/服务，不重置集群 |

P1A-01–10 对应架构 F01/F04/F05/F11/F12 与 S15 的适用部分，不能据此宣告完整 Phase 1 或 80 个架构场景通过。实际身份/数据库/前端检查必须在实施后记录 SHA 和证据。
