# Phase 1A Plan：正式工程与平台基础

- 状态：in-progress；先执行 CORE，按交付门槛推进后续批次
- 日期：2026-09-09
- 对应：[Spec](spec.md)
- 评审参考基线：`28fcd44eebc205a35735d3e7b60a308ce5f749bc`
- 已复核规划基线：`c583f0b08f81df43b1f6508376d952ed23b17c34`；任务分派的实际起点在[执行记录](execution.md)及任务书固定，不能自动跟随分支漂移
- 实施批准依据：2026-09-09 方案评审收口后，用户回复“可以，继续”，批准按本阶段 Spec / Plan 开始实施
- 方案评审：[发现与修订记录](review.md)

## 1. 固定方案与依赖

主代理选择 Python 平台栈，与后续 LangGraph 执行层保持语言一致；本阶段只初始化 Platform API，不提前创建空的 Router、Controller 或 Agent 服务。采用已发布依赖的具体版本作为解析输入，实际安装、互相兼容和镜像拉取仍须在阶段实施中验证。

| 运行部分 | 候选固定版本 / 配置 |
| --- | --- |
| Python / uv | Python 3.13.15 标准 GIL；项目专用 uv 0.12.11；根目录 Python workspace 和 uv.lock；不改系统默认 Python/uv |
| API | FastAPI 0.141.1、Uvicorn 0.52.4、Pydantic 2.13.5、pydantic-settings 2.15.0 |
| 数据库客户端 | SQLAlchemy 2.0.52、psycopg[binary] 3.3.5、Alembic 1.19.2 |
| 身份客户端 | Authlib 1.8.0 + HTTPX2 2.12.0，显式运行时依赖；不依赖已弃用的旧 HTTPX 回退 |
| Python 验证 | pytest 9.1.1、httpx 0.28.1（只用于 ASGI 测试）、openapi-core 0.23.1；异步用例由 asyncio 驱动，不另加测试插件 |
| 开发依赖镜像 | PostgreSQL 18.6、Keycloak 26.7.2；部署前解析并固定 linux/amd64 对应镜像 digest，禁止 latest |
| 前端 | 沿用根锁文件 Node 24.20.0 / pnpm 10.32.1 及已有 React/antd 等精确版本；增加 apps/* workspace |

本机 uv 0.10.8 的 `uv python list 3.13.15` 无结果；`--all-versions 3.13` 只列出最高 3.13.12 的可下载发行，本机另有非 uv 管理的 3.13.14。因此修正项目 uv 为 0.12.11：官方清单已包含标准 GIL 的 `cpython-3.13.15-darwin-x86_64-none` 和 `cpython-3.13.15-linux-x86_64-gnu`（build 20260901）。这只是发行元数据核实，不是已安装或完成依赖兼容验证。[uv 版本机制](https://docs.astral.sh/uv/concepts/python-versions/#installing-a-python-version)、[0.12.11 发行](https://github.com/astral-sh/uv/releases/tag/0.12.11)、[固定发行的 Python 清单](https://github.com/astral-sh/uv/blob/0.12.11/crates/uv-python/download-metadata.json)

CORE 增加项目 bootstrap 入口：将固定版本 uv 与受管 Python 安装至 ignored 的 `work/toolchain/`，核对发行 SHA-256 后使用显式项目路径；CI 固定相同版本。Python 安装不能写入用户全局 bin、修改 shell 配置或替换 Homebrew/Miniforge 解释器。所有 uv 命令以下均指此项目工具链，不能继续误用 PATH 中 0.10.8。CORE 提交工具链清单和 `uv.lock`；安装失败时报告实际原因，不能静默换版本。

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
| 协议夹具 / 未迁移 API | `18083 / 8003`，仅限测试 run 的 loopback 进程 |
| 现有原型 | 保持 4173 评审入口和 4175 原型测试入口 |

OIDC client 使用 confidential client + PKCE S256，开发回调固定 `http://127.0.0.1:4180/api/v1/auth/callback`；测试使用对应测试端口。生产配置要求显式 HTTPS public origin 与 issuer，启动时拒绝继承开发回调或关闭 Secure。后端不能从未验证的 Host/Forwarded 头生成回调地址。

SERVER 显式配置 ID Token 校验：固定 RS256、`leeway=0`，先核对 discovery issuer 等于配置 issuer，再通过 Authlib `claims_options` 强制 `iss`、`aud`、`nonce` 的 essential 与预期值。不能仅依赖 `client_id` / `nonce` 位置参数；Authlib 的默认实现可能从 discovery 推导 issuer、提供时间宽限，且对 `nonce_supported=false` 关闭 nonce 参数。受控 issuer 测试增加缺失 nonce、该标记伴随错误 nonce、错误 aud 但正确 azp 的反例，继续走正常协议客户端。[固定发行的解析实现](https://github.com/authlib/authlib/blob/v1.8.0/authlib/integrations/base_client/async_openid.py)、[声明配置实现](https://github.com/authlib/authlib/blob/v1.8.0/authlib/oauth2/claims.py)

复用 Authlib 的 OAuth/OIDC 客户端和 ID Token 校验，通过 Wuji 的 PostgreSQL 状态适配接入；不直接采用默认 Starlette `request.session` 状态存储，因为其读取/清除不是本项目数据库的原子消费。`OIDCHandshake` 至少保存 state_hash、binding_hash、nonce、code_verifier、return_to、expires_at 和消费状态。回调以条件状态更新原子领取，再提交事务并交换 code，失败不能退回可消费状态；同一回调并发仅允许一个成功领取者。新登录替换仍待回调的旧绑定；当前绑定正在交换时拒绝启动第二次交换并要求稍后重试。协议 URL 使用 query 回调，返回站内页面的成功/失败映射按 Spec；不自行实现 OAuth/JWT 密码学。[Authlib 状态适配源码](https://github.com/authlib/authlib/blob/v1.8.0/authlib/integrations/starlette_client/integration.py)

Session 存储 token_hash、user_id、csrf_token、created_at、last_seen_at、absolute_expires_at、revoked_at。条件更新同时校验当前用户/句柄/两个期限并续期；权限版本从 User 当前行读取。会话创建/替换、注销、禁用用户和权限管理命令的审计与状态变更同事务提交。注销只有事务提交后才返回 204/清 Cookie；认证已确认不存在有效会话时返回 401/清失效 Cookie，前端可以据此确认当前已登出，不能声称本次撤销了一个有效会话。数据库故障时不得返回 401 或假 204。

迁移/初始化、auth、project 使用三个独立凭据/连接入口。auth 只读 User/ExternalIdentity，读写 Session/OIDCHandshake 并追加身份审计；project 只读四张租户/成员/项目表，不可读取认证存储。API 只加载 auth/project DSN，不继承管理进程的迁移或 Keycloak 管理凭据。身份预置和权限变更走专用管理命令，禁止以运行时 SET ROLE 绕过边界。

RLS 四表及复合约束按 Spec。事务用 `set_config(..., true)` 设置已验证的 user 上下文；TenantMembership/ProjectMembership 行均必须满足 `row.user_id = app.user_id`，后者还需同 `(tenant_id,user_id)` 的有效 TenantMembership。Project 只允许匹配 `(tenant_id,project_id,app.user_id)` 的有效 ProjectMembership，Tenant 只允许匹配 `(tenant_id,app.user_id)` 的有效 TenantMembership。详情在同一受限事务内查明归属后再设置 tenant/project；无上下文默认拒绝。用真实 project/auth 角色执行反例，不能用表 owner/迁移角色代替 RLS 验收。[PostgreSQL 事务级设置](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-SET)、[RLS 边界](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)

种子包含单租户、双租户、Operator/Viewer 和无项目用户；外部身份映射以 IdP 返回的稳定 sub 为准。权限管理命令实现幂等更新及 User.permissions_version 的同事务递增。开发密码和 client secret 由初始化流程生成，保存在 ignored 环境文件/专用 Secret，不写入清单、任务书或日志。项目开发依赖清单与测试清单共享 base，分别使用命名空间、端口与凭据。

`dev:infra` 使用前台 supervisor 管理本次 PostgreSQL/Keycloak 转发；Pod 重建导致转发退出时，以有界退避恢复，超时清楚报告未就绪。`dev:platform` 只管理自己的 API/Vite。每个 run 原子记录 ID、工作树/SHA、PID、启动标识和端口；dev/test 分别加进程锁，端口被未知进程占用立即失败，不能按端口杀进程或凭旧 PID 文件直接终止进程。信号/finally 只清理本次拥有的进程组；普通 `dev:down` 不删除 Kubernetes 对象、Secret 或 PVC。重置数据是独立显式命令，先核对 context、namespace 和所有权标签。[port-forward 生命周期](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/)

## 3. 契约与前端接入

先扩展权威 OpenAPI 到 0.2.0，保留现有字段语义，追加 `project.read` 及 Spec 的身份/项目路由；health 在同一文件中声明操作级根 server。公开端点显式 `security: []`，logout 显式 Session + CSRF。保留原 Phase 1 设计夹具，另加 Phase 1A 实际响应夹具，不能把原型带有未实现权限的 DTO 用作正式 API 期望。错误/回调重定向/安全声明/参数名/游标失败均先写契约；FastAPI 运行文档从已注册路由生成或筛选，不能发布未实现能力。

前端消费 `@wuji/contracts/types` 和新增的 `@wuji/contracts/validators`。沿用已固定 Ajv 2020 / ajv-formats，在构建时从同一 OpenAPI Schema 生成 Session、Project、ProjectPage、Error 的 standalone ESM 校验函数及类型声明；CORE 负责生成器、必要 runtime helper 依赖和导出，不让浏览器运行 Schema 编译器。生成校验包含格式、严格额外字段和嵌套引用；`--check` 同时检查类型与校验生成物，真实 API 另由 openapi-core 校验，不能以 TS 编译替代。[Ajv standalone](https://ajv.js.org/standalone.html)

正式主题代码从现有实现提取到可复用模块；原型继续使用现有每标签页偏好策略，正式应用使用 Spec 的设备偏好策略。两者只共享颜色/组件 token 定义，不能把原型 fixture 状态搬进正式查询层。本阶段抽离公共主题包，只保留单份主题 token，避免两份复制长期漂移。

公共包固定为 `packages/theme` / `@wuji/theme`，保留现有五套色值及公开 token API。正式应用使用稳定的单个 ConfigProvider 和 antd App 上下文；消息/弹窗使用上下文实例，确保浮层跟随主题。Provider/Router/QueryClient 不以主题 ID 为 key，也不在主题切换时销毁。设备偏好写入 localStorage 的独立键 `wuji.workbench.palette`，有效 URL 参数只临时覆盖；只有主动选择才写设备偏好，存储失败保持当前内存主题。本阶段为 CSR，不引入 SSR/Pro/Umi/Ant Design X。[Ant Design 主题与上下文](https://ant.design/docs/react/customize-theme-cn/)

项目页和基础工作区提供加载、空项目、无权限、错误及失效状态。Router Data Mode loader 复用 Query 定义；请求同时使用 AbortSignal 与身份/项目代次，不能只依赖卸载组件或清缓存。项目列表只有服务端游标翻页，不新增未入契约的搜索/排序。401、项目404、权限版本变化与退出未确认分别按 Spec 处理；迟到成功和迟到错误都不得改变新上下文。[TanStack Query 请求取消](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation)

## 4. 子任务与唯一归属

阶段分支为 `codex/phase-1a`，工作树根为主仓库 ignored 的 `work/worktrees/phase-1a-<task>`。创建时任务书记录完整绝对路径与固定基准 SHA；表中所有任务当前均未派发。

| 任务 | 执行者 | 修改归属 | 依赖与交付 |
| --- | --- | --- | --- |
| P1A-CORE | SOL/xhigh 开发 A | 根 Python/Node workspace、项目工具链、所有 manifest/锁文件、契约/生成器/契约测试、apps/api 基础骨架、apps/web 的 manifest/初始配置、packages/theme 骨架、CI/根命令 | 首先完成；公共导出和依赖冻结后交付固定 SHA。此后 apps/web 非 manifest 的配置/源码和主题源码交 B，manifest/锁文件始终归 A |
| P1A-SERVER | 同一开发 A | apps/api、Alembic、infra/kubernetes、scripts/platform 的初始化/启动/管理/测试生命周期入口 | 基于 CORE；实现依赖、身份、数据库、RLS、会话与项目 API；独占迁移编号及全部契约/manifest/锁文件更新 |
| P1A-WEB | SOL/xhigh 开发 B | apps/web 的非 manifest 配置/源码、packages/theme/src 内容、原型主题导入、可访问标识 | 基于 CORE，可与 SERVER 并行；不修改权威契约/锁文件/manifest，依赖需求交 A 解析 |
| P1A-TEST | 独立 SOL/high 测试 | tests/api（含 conftest/fixtures）、tests/platform-browser、tests/fixtures/oidc、playwright.platform.config.ts、阶段测试报告 | CORE 后可按 Spec 写用例；集成后运行；可写受控协议夹具和故障用例，不改实现/权威契约/根脚本或降低预期 |
| P1A-ACCEPT | 主代理 | 阶段文档、集成冲突与最终验收 | 审查候选 SHA、关键边界和证据；修复交回对应开发者后复测 |

只使用两个开发上下文和一个独立测试上下文。每次共享契约/锁文件变化先由 A 提交并经主代理集成，B 和测试者再基于明确提交更新，不能各自在自己的分支生成不同版本后覆盖。

交付按批次留证：CORE 完成冻结安装、类型/校验生成一致性和 API 导入/启动检查后，才放行 SERVER/WEB 并行；SERVER 的存储/身份/API 与 WEB 的页面分别交付，再形成完整唯一集成 SHA。测试者可以在 CORE 之后编写用例，开发者不得把尚未接入的接口返回假成功来提前通过。最终完整 P1A-01–10 通过之前，master 保持已验收业务基线。

## 5. 实施后必须执行的检查

以下为将要新增的命令契约，不是当前仓库已有可运行命令：

| 入口 | 行为与验收 |
| --- | --- |
| `uv sync --frozen`、`pnpm install --frozen-lockfile` | 安装已解析锁文件；记录实际 Python/Node 与完整依赖版本 |
| `pnpm dev:infra` | 预检 context/端口、部署本项目 dev 依赖、就绪/PVC验证，启动有限本地转发 |
| `pnpm dev:seed` | 应用 Alembic 与幂等身份/项目种子；不清空已有业务数据 |
| `pnpm dev:platform` | 启动本机 API 和正式前端，退出时只停止本次创建的进程 |
| `pnpm dev:down` | 核对 run 归属后停止对应本地进程组，保留 Kubernetes 资源和数据 |
| `pnpm check:platform` | 无集群检查：契约/生成一致性、正式应用类型/antd检查/构建、标记为 unit 的 Python 测试与静态导入；默认 Ubuntu CI 只承诺此范围 |
| `pnpm test:platform` | Docker Desktop 本机完整验收入口，依次执行下述生命周期；不冒充默认 Ubuntu CI 已跑 Kubernetes 集成 |

### 5.1 测试生命周期与隔离

`test:platform` 固定执行：预检 context/端口/独占锁 → 幂等部署并等待 wuji-test 依赖 → 启动本 run 转发 → 创建本 run 数据库及测试身份 → migrate/seed → 启动 API/Vite/协议夹具 → API/浏览器检查 → 保存报告与证据 → finally 停止本 run 进程。使用独立 `playwright.platform.config.ts` 和 `tests/platform-browser`；浏览器使用全新隔离 context，不复用用户配置目录或原型的 tests/browser/4175。

测试 Wuji DB 以 `wuji_test_<run_id>` 独立命名，Keycloak 使用独立持久数据库和每 run realm/身份；run_id 写入所有权记录。每次测试从新数据库开始，不清空上一 run 或开发数据；完成持久性/恢复检查前不能重建数据库。失败保留该 run 数据和脱敏日志供诊断，下一 run 用新 ID。旧 run 的数据库/realm 只由显式清理命令按所有权删除，禁止 test 入口重置整个 namespace/PVC。固定端口使同一测试配置串行执行；开发与测试可独立运行。

所有规定端口均先检查，包括夹具18083和未迁移API8003。关键检查未就绪时退出非零，不能通过 skip 或空测试集声明通过；故障清理在 finally 执行并保留失败证据，端口和独占锁都须可再次使用。测试者记录候选 SHA、run_id、DB/realm 标识、浏览器版本、实际用例数及各阶段退出码；不记录凭据。

### 5.2 协议、故障与竞态验证

- **真实身份链路：** Keycloak 覆盖真实浏览器 Code+PKCE 成功、退出、state/绑定、替换/重放及 return_to；另有 loopback 受控 issuer 夹具参与 discovery/authorization/token/JWKS，分别制造错误 nonce/issuer/audience/签名/有效期。独立 API 测试进程显式配置该 issuer 并预置身份，应用仍走正常 Authlib 校验，禁止测试专用绕过分支。回调失败检查303的安全 Location、无有效新会话Cookie/DB行、审计原因和无原始code/token日志；并发同回调只允许至多一个新Session。
- **数据库网络失联：** Keycloak 通过集群内 Service 使用自己的 DB，API 只通过本 run 独占的 PostgreSQL port-forward。暂时暂停 supervisor 对该转发的自动恢复并终止此子进程；验证 live=200、ready=503、持原有效 Cookie 的 session/projects 为结构化503，同时 IdP discovery可用。恢复转发后验证 ready=200、原 Cookie 和原项目可读。此例只证明 API→DB 网络路径故障恢复，不宣称 PostgreSQL Pod 故障隔离。
- **持久性/未迁移：** PostgreSQL Pod 重建单独执行，等待数据库、Keycloak、转发和 API 全部恢复再读原数据。未迁移反例使用该 run 另一个全新空 Wuji DB 与8003 API，启动不自动迁移，观察live200、ready/业务503；不能downgrade已有DB。
- **撤权/迟到响应：** 挂起一个已授权的项目响应，管理命令提交撤权并记录完成，再用新请求观察404及页面清理，随后释放旧200；其项目专属canary不得回到DOM，重新进入该路由仍404。另验注销/禁用后的旧Cookie401、项目切换后迟到错误不覆盖新页。时间上允许撤销前已开始的请求完成，页面知道失权之后不能恢复旧数据。
- **期限与RLS：** 通过管理数据库调整本run会话时间验证两个边界，不等待8小时；使用真实auth/project角色、池复用和无上下文请求，检查无越权读取/关联/写权限。种子明确包含同租户互斥项目成员 U1→P1、U2→P2，U1 不得读取 U2 的成员行/P2，反向同样验证。复合外键反例由管理夹具角色插入并期待数据库拒绝，与运行角色的禁止写入检查分别取证。权限变更/版本递增/审计失败时共同回滚，幂等重放不多增版本。

主题检查覆盖五套主题、URL 临时覆盖、设备偏好恢复、禁用存储、浮层/键盘与当前项目/游标分页状态保持。本阶段没有 Wuji 业务编辑表单，“表单草稿保持”不作为虚构通过项；后续引入表单时再验收。原型原有检查继续运行一次回归，防止共享主题迁移影响已确认样式。所有结果记录候选 SHA，修复后的差异决定复测范围。

## 6. 准入与 CORE 交付门槛

本修订已完成方案审查并获用户实施批准，当前在执行模式推进。Python 3.13.15、uv 0.12.11、上述依赖及镜像的实际安装结果在执行记录中更新；镜像 digest、发行校验值与解析后的传递依赖是 P1A-CORE 的锁定产物，不能预先视为已验证。若安装/协议小验证揭示不兼容，由主代理修订方案，不由子代理静默降级。

最终独立复核已确认方案可进入 CORE，见[评审结论](review.md#最终复核与开发准入)。实施批准后，主代理从已复核规划建立 `codex/phase-1a`，记录固定基准 SHA，再为开发 A 创建独立工作树。CORE 必须交付以下证据后，主代理才放行 SERVER / WEB：

1. 项目工具链清单、发行校验值、`uv.lock` 和更新后的 pnpm 锁文件；从显式项目路径完成冻结安装，记录实际解释器、包管理器及关键依赖版本。
2. OpenAPI 0.2.0、生成的类型和 standalone 校验器一致；公开端点安全覆盖、health 根路径和原 Phase 1 夹具回归检查通过。
3. API 骨架可导入和启动，健康响应真实反映当前依赖状态；正式前端骨架可类型检查和构建。尚未实现的登录/项目功能不能用固定成功响应占位。
4. 公共导出、WEB 初始配置、共享主题迁移接口及各检查入口有交接说明；未完成的 SERVER / WEB 能力和集成检查保持未通过。原型现有契约、类型与构建检查继续通过。
5. 开发 A 提交允许范围内的文件，报告提交 SHA、执行命令、退出码及限制；主代理复核差异并集成为后续任务共同采用的 CORE SHA。独立测试上下文按该版本的 Spec 编写用例，完整运行以最终集成 SHA 为准。

后续生产 IdP 对接、生产 Kubernetes/存储、高可用和 CNI 方案不属于本阶段交付；本阶段只承诺现有本地集群上的真实基础闭环。P1A 验收通过后再进入任务管理，不因基础页面能打开就开放目标执行。
