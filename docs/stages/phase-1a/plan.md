# Phase 1A Plan：正式工程与平台基础

- 状态：draft；下一轮 Plan 评审候选，尚未批准实施
- 日期：2026-09-09
- 对应：[Spec](spec.md)
- 规划参考基线：`9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece`
- 执行基线：阶段获批时的已验收 master SHA，分派前由主代理记录，不能自动跟随分支漂移
- 批准依据：无；用户已批准的是开发流程与本轮基线工作

## 1. 固定方案与依赖

主代理选择 Python 平台栈，与后续 LangGraph 执行层保持语言一致；本阶段只初始化 Platform API，不提前创建空的 Router、Controller 或 Agent 服务。采用已发布依赖的具体版本作为解析输入，实际安装、互相兼容和镜像拉取仍须在阶段实施中验证。

| 运行部分 | 候选固定版本 / 配置 |
| --- | --- |
| Python / uv | Python 3.13.15 标准 GIL；uv 0.10.8；根目录 Python workspace 和 uv.lock；项目级安装，不改系统默认 Python |
| API | FastAPI 0.141.1、Uvicorn 0.52.4、Pydantic 2.13.5、pydantic-settings 2.15.0 |
| 数据库客户端 | SQLAlchemy 2.0.52、psycopg[binary] 3.3.5、Alembic 1.19.2 |
| 身份客户端 | Authlib 1.8.0 + HTTPX2 2.12.0，显式运行时依赖；不依赖已弃用的旧 HTTPX 回退 |
| Python 验证 | pytest 9.1.1、httpx 0.28.1（只用于 ASGI 测试）、openapi-core 0.23.1；异步用例由 asyncio 驱动，不另加测试插件 |
| 开发依赖镜像 | PostgreSQL 18.6、Keycloak 26.7.2；部署前解析并固定 linux/amd64 对应镜像 digest，禁止 latest |
| 前端 | 沿用根锁文件 Node 24.20.0 / pnpm 10.32.1 及已有 React/antd 等精确版本；增加 apps/* workspace |

Authlib 1.8 的 Starlette 集成使用 HTTPX2，而包本身不会自动安装 HTTP 客户端；HTTPX2 必须单独声明。旧 HTTPX 仅留在测试组。[官方集成](https://docs.authlib.org/en/latest/oauth2/client/web/starlette.html)、[发行源码](https://github.com/authlib/authlib/blob/v1.8.0/pyproject.toml)、[HTTPX2 元数据](https://pypi.org/project/httpx2/2.12.0/)

SQLAlchemy 的 psycopg 方言支持同步和异步使用，因此 API 与迁移共用一个驱动。[官方说明](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) Python、数据库与身份提供方版本依据：[Python 3.13.15](https://www.python.org/downloads/release/python-31315/)、[PostgreSQL 版本](https://www.postgresql.org/support/versioning/)、[Keycloak 26.7.2](https://www.keycloak.org/2026/08/keycloak-2672-released)。这些资料不替代锁文件安装检查。

## 2. 本地环境、数据与身份实现

使用 `kubectl --context docker-desktop apply -k` 管理专用命名空间资源。Kustomize 复用 kubectl，不需要先安装 Helm；不修改当前 context、不创建新集群、不接触其他 namespace 的业务资源。开发依赖采用单实例 PostgreSQL + 单实例 Keycloak，Keycloak 使用独立数据库/账号。先验证 PVC 绑定、重建保持和资源配额，再把依赖就绪作为启动成功。

| 本地入口 | 地址 / 用途 |
| --- | --- |
| 正式开发前端 | `http://127.0.0.1:4180`；Vite 同源代理 `/api` 到 API |
| API 热更新 | `http://127.0.0.1:8000`；前端浏览器不直接跨域请求此端口 |
| Keycloak | `http://127.0.0.1:18080`；realm `wuji-dev`，issuer 在浏览器与 API 一致 |
| PostgreSQL | `127.0.0.1:15432`；port-forward 只绑定 loopback |
| 测试前端 / API / IdP / DB | `4182 / 8002 / 18082 / 15434`，独立 `wuji-test` 资源 |
| 现有原型 | 保持 4173 评审入口和 4175 原型测试入口 |

OIDC client 使用 confidential client + PKCE S256，开发回调固定 `http://127.0.0.1:4180/api/v1/auth/callback`；测试使用对应测试端口。生产配置要求显式 HTTPS public origin 与 issuer，启动时拒绝继承开发回调或关闭 Secure。后端不能从未验证的 Host/Forwarded 头生成回调地址。

通过 Authlib 的 Starlette 集成与受限服务器状态存储适配保存 OIDC 临时握手数据；应用 Session 独立保存在 PostgreSQL。不要复制将 token 全部存入浏览器签名 SessionCookie 的示例。会话哈希、CSRF、TTL、一次性握手及失败路径按 Spec 实现；不自行实现 OAuth/JWT 密码学。登录成功只映射已预置 `(issuer, sub)`，未预置身份返回无权访问，不按邮箱自动注册。

迁移/初始化角色创建表、约束与 RLS；认证角色仅访问 User/ExternalIdentity/Session/OIDCHandshake 及身份审计，项目业务角色仅访问被授权的租户/项目表。业务请求先完成认证，再在事务内设定 `app.user_id`；项目详情再由服务端验证资源归属并设置 tenant/project 上下文。Membership RLS 以当前用户自身关联为基础，Project/Tenant 读取仅允许对应有效成员关系；避免互相递归的 RLS 子查询。事务退出时清除上下文，不能把进程全局变量当租户上下文。

两个租户、Operator/Viewer/无项目用户的种子及会话/成员撤销采用幂等管理命令；开发密码和 client secret 由初始化流程生成并保存到 ignored 环境文件/专用 Secret，不写入清单、任务书或日志。项目开发依赖清单与测试清单共享 base，分别使用命名空间、端口与凭据；停止脚本只停止本次启动并记录的进程。数据重置是单独的显式管理命令，默认 dev-down 不删除 PVC。

## 3. 契约与前端接入

先扩展权威 OpenAPI 到 0.2.0，保留现有字段语义，添加 Spec 中的登录/回调/退出/单项目读取，并另行声明 health 探针。错误继续使用现有 Error 枚举和结构；新增路由的成功/失败响应与安全要求均纳入契约测试，FastAPI 默认错误响应需统一映射。

前端正式应用通过生成类型和运行时 Schema 校验访问 `/session`、`/projects` 及项目详情；Schema 从同一契约生成构建产物，不能再手写一套字段定义。保留根目录原型检查命令，增加明确的正式应用检查命令，不使原型测试误测新应用。

正式主题代码从现有实现提取到可复用模块；原型继续使用现有每标签页偏好策略，正式应用使用 Spec 的设备偏好策略。两者只共享颜色/组件 token 定义，不能把原型 fixture 状态搬进正式查询层。本阶段抽离公共主题包，只保留单份主题 token，避免两份复制长期漂移。

项目页和基础工作区提供加载、空项目、无权限、错误及失效状态。路由 loader 复用 Query 定义，项目切换/退出使用上下文代次抑制迟到响应。身份令牌不存浏览器持久层；主题 ID 存储与私有缓存清理分开。

## 4. 子任务与唯一归属

阶段分支为 `codex/phase-1a`，工作树根为主仓库 ignored 的 `work/worktrees/phase-1a-<task>`。创建时任务书记录完整绝对路径与固定基准 SHA；表中所有任务当前均未派发。

| 任务 | 执行者 | 修改归属 | 依赖与交付 |
| --- | --- | --- | --- |
| P1A-CORE | SOL/xhigh 开发 A | 根 Python/Node workspace、锁文件、契约/生成器、API 基础骨架、共用主题包骨架、CI 入口 | 首先完成；固定依赖、OpenAPI 0.2.0、可安装工程和前后端公共契约 |
| P1A-SERVER | 同一开发 A | Platform API 源码、Alembic、Kustomize/初始化/启动/管理命令 | 基于 CORE；实现集群依赖、身份、数据库、RLS、会话与项目 API；独占迁移编号与所有锁文件更新 |
| P1A-WEB | SOL/xhigh 开发 B | apps/web、公共主题包内容及原型主题导入、正式浏览器测试所需可访问标识 | 基于 CORE，可与 SERVER 并行；不修改根锁文件/契约，新增依赖需求提交 A 统一解析 |
| P1A-TEST | 独立 SOL/high 测试 | tests/api、正式浏览器用例、阶段测试报告 | CORE 后可依据 Spec 写用例；SERVER/WEB 集成后运行，不能改实现或降低预期 |
| P1A-ACCEPT | 主代理 | 阶段文档、集成冲突与最终验收 | 审查候选 SHA、关键边界和证据；修复交回对应开发者后复测 |

只使用两个开发上下文和一个独立测试上下文。每次共享契约/锁文件变化先由 A 提交并经主代理集成，B 和测试者再基于明确提交更新，不能各自在自己的分支生成不同版本后覆盖。

## 5. 实施后必须执行的检查

以下为将要新增的命令契约，不是当前仓库已有可运行命令：

| 入口 | 行为与验收 |
| --- | --- |
| `uv sync --frozen`、`pnpm install --frozen-lockfile` | 安装已解析锁文件；记录实际 Python/Node 与完整依赖版本 |
| `pnpm dev:infra` | 预检 context/端口、部署本项目 dev 依赖、就绪/PVC验证，启动有限本地转发 |
| `pnpm dev:seed` | 应用 Alembic 与幂等身份/项目种子；不清空已有业务数据 |
| `pnpm dev:platform` | 启动本机 API 和正式前端，退出时只停止本次创建的进程 |
| `pnpm check:platform` | 契约一致性、正式应用类型/构建、Python 测试与静态导入检查 |
| `pnpm test:platform` | 在 wuji-test 实例验证 P1A-01–10：真实 OIDC、DB/RLS、撤销、响应契约及浏览器路径 |

独立测试包含错误 state/nonce/issuer/audience、跨浏览器与一次性回调、恶意 return_to、Cookie/CSRF/Origin、会话期限、成员撤销、跨租户游标/关联/连接池、数据库故障和实际 Keycloak 登录。集成环境中使用测试实例进行故障注入；不能对其他用户的资源测试。

主题检查覆盖五套主题、URL 临时覆盖、设备偏好恢复、禁用存储、浮层/键盘与切换时保持业务状态。原型原有检查继续运行一次回归，防止共享主题迁移影响已确认样式。所有结果记录候选 SHA，修复后的差异决定复测范围。

## 6. 准入与待评审内容

本草案已经选定默认方案，仍须在下一轮 Plan 模式确认阶段范围后进入开发。Python 3.13.15、上述依赖及镜像尚未在本项目安装；镜像 digest 和解析后的传递依赖是 P1A-CORE 的机械锁定产物，不能冒充本轮已验证。若安装/协议小验证揭示不兼容，由主代理修订方案，不由子代理静默降级。

后续生产 IdP 对接、生产 Kubernetes/存储、高可用和 CNI 方案不属于本阶段交付；本阶段只承诺现有本地集群上的真实基础闭环。P1A 验收通过后再进入任务管理，不因基础页面能打开就开放目标执行。
