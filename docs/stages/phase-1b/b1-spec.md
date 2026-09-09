# B1 Spec：范围选择与任务预览

- 状态：review-ready；方案供用户评审，未批准业务实现。
- 基础代码：`70668be2d5d42c9468764399b5be2d5157951943`；开发启动时固定实际集成 SHA。
- 对应：[阶段 Spec](spec.md)、[B1 Plan](b1-plan.md)。本批次不执行目标请求。

## 1. 用户路径

Operator 在项目工作区进入“任务预览”，选择已批准范围，填写名称、目标 URL、GET/HEAD 及限额，提交后看到服务端计算的规范化地址、有效范围、限额和阻断原因。更改输入立即丢弃旧预览；切换主题保留当前表单；离开项目清除草稿与预览。草稿仅存当前页面内存，不写浏览器持久存储。

Viewer 可以读取项目范围，但不能提交预览。无可用 Scope 显示“暂无可用范围”，不生成默认授权；入口不展示模型、Runtime 或执行器配置。本批次没有“创建任务”按钮，B2 接入后才开放。

## 2. 契约与权限

权威 OpenAPI 在 B1 开发时从 0.2.0 升级为 0.3.0；保留既有字段，新增 `task.preview` 权限和 `CREATION_UNAVAILABLE` 预览 blocker。前后端与生成校验器在同一交付版本升级；不依赖旧客户端忽略未知枚举。

| 接口 | 条件 | 结果 |
| --- | --- | --- |
| GET `/api/v1/projects/{project_id}/scopes` | 有效会话、当前项目可读 | 200 ScopePage，默认50/最多100，按 `(created_at,policy_id,version)` 降序；只列生效且未撤销/未过期的批准版本 |
| POST `/api/v1/projects/{project_id}/task-previews` | 会话、CSRF、Origin、当前项目 task.preview | 200 TaskPreview；只做规范化与策略计算，不要求 Idempotency-Key |

两接口补齐 500 Error 声明，预览显式声明 SessionCookie + CsrfToken 安全要求，删除没有对应行为的409/410响应；Scope列表保留游标410。不存在/不可见的项目或 Scope 均404；可见项目但缺少预览权限403；输入不合法422；数据库不可用503。不得用空列表代替依赖错误。

有效 Operator 要求当前 TenantMembership 和 ProjectMembership 都有效且角色均为 operator；任一为 viewer 时只读。B1 Project.permissions 对 Operator 返回 `project.read, task.preview`，Viewer 只返回 `project.read`，列表和详情一致；未实现的 task.create/read/control 不提前授予。API 与 SQL 写策略都检查角色，不能只靠页面隐藏按钮。

B1 的有效范围计算成功时也返回 `can_create=false` 和 `CREATION_UNAVAILABLE`（“任务创建尚未开放”）；其他实际 blocker 一并保留。页面分别呈现范围计算结果和创建可用性，不把 false 一概显示为越界。B2 开放创建后重新预览，有权限且范围合规的请求可 `can_create=true`。没有部署 Runtime 不阻止保存排队任务；执行许可由 Phase 1C 单独核验。`MISSING_ADAPTER` 只表示所选观察配置未被平台支持，不用于代指本批次尚无执行器。

TaskPreview 有效期固定为300秒且不超过授权截止时间；blocked 预览可以返回已经到期的 expires_at，不产生可创建权限。已过期授权返回 AUTHORIZATION_EXPIRED；尚未生效或已撤销的可见授权返回 SCOPE_DENIED 及对应说明。客户端不延长有效期；到期后要求重新预览。B2 不接受先前 can_create=false 的预览。

## 3. 输入和范围算法

本批次固定一个纯计算模块，管理导入、预览与后续创建共用它，不访问 DNS、HTTP、Kubernetes 或模型。

1. `TaskDraft` 拒绝额外字段。名称去除首尾空白后为1–120字符；tool 固定 http_observe；method 只允许 GET/HEAD；限额遵守现有 Limits，并拒绝 NaN/Infinity。
2. URL 限2048字符；仅接受 ASCII 表示的绝对 HTTP(S) URL。域名可使用 ASCII punycode，暂不自动转换 Unicode 域名。拒绝原始空格、控制字符、反斜杠、userinfo、fragment、空 host 和无效端口。端口为1–65535；scheme/域名小写，默认端口移除，空路径变为 `/`。
3. IPv4 仅接受标准点分十进制；IPv6 仅接受带方括号的字面量，规范化为压缩小写形式，拒绝 zone ID。拒绝十六进制、单整数或非标准省略 IP 写法。预览不把解析成功视为目的地址已经通过出口审查。
4. 路径必须以 `/` 开始，拒绝重复斜杠及 `.`/`..` 路径段。百分号必须组成合法 `%HH`；仅解码 ASCII unreserved 字符，解码后再次拒绝点路径段。其他百分号编码的路径字符在首批拒绝，尤其不接受编码斜杠、反斜杠和二次编码。原始路径仅允许 unreserved、`/`、`:`、`@` 和 sub-delims `!$&'()*+,;=`。这是 B1 的明确支持范围，不宣称覆盖所有 URL 表示法。
5. query 保留原有参数顺序、重复参数、加号及编码字节；只校验百分号语法并统一十六进制大小写，不解码或重排。非 ASCII 查询需由用户提供百分号编码。query 参与摘要，但不能用它扩大 path/origin 授权；导入者仍须明确批准这些端点的非破坏性观察用途。
6. Scope origins 规范化为无 path/query 的 origin；路径前缀执行同一规范化。匹配前缀先移除末尾 `/`（根路径除外），只有完全相等或以 `prefix + '/'` 起始才匹配。`/public` 匹配 `/public`、`/public/a`，不匹配 `/publicity`。任何排除前缀命中均拒绝；方法必须在允许集合中。
7. effective_scope 的 limits 对 draft、批准 Scope 和平台上限逐字段取最小值；保留规范化原 draft，不悄悄把用户请求限额改写为有效限额。SHA-256 input_digest 以带 `task-draft/v1` 标记、固定字段类型、排序键和紧凑 JSON 的规范化 draft 计算；Scope hash 独立绑定完整不可变策略内容。

首批必要输入向量：默认443端口与域名大小写归一；`/public/a`通过；`/publicity`与`/public/logout`拒绝；`%2e%2e`和`%2f`拒绝。其他编码与解析矩阵集中后测，不新增长时间模糊测试。

## 4. 存储与管理入口

新增三类数据：

| 表 | 必要内容和约束 |
| --- | --- |
| authorization_records | id、tenant/project、授权主体/依据、批准者、valid_from/until、revoked_at；不可把 URL 输入当作授权证明 |
| scope_policy_versions | policy_id/version、tenant/project、authorization_id、规范化 Scope JSON、policy_hash、created_at；同策略版本唯一且内容不可覆盖 |
| task_previews | id、tenant/project/user、permissions_version、规范化 draft、input_digest、policy_id/version/hash、effective_scope、can_create/blockers、created_at/expires_at |

项目/授权/策略/预览使用 tenant/project 复合外键。Scope 和授权仅由迁移管理入口写入；project 运行角色只读必要授权字段、读 Scope、插入/读取当前用户预览。预览 INSERT 的 WITH CHECK 同时核验当前项目、当前用户及有效 Operator；不授予 UPDATE/DELETE/DDL/TEMP 或身份库写权限。新表启用 RLS，缺失上下文拒绝。事务内建立已验证的 user、tenant、project 上下文，不继承其他请求的连接状态。

新增 `wuji-manage --run-file <absolute> scope import --file <absolute>`，复用现有受信管理凭据和脱敏 JSON 输出。输入严格校验批准信息、有效期、归属和非空允许集合；相同 policy_id/version/hash 重放为 no-op，修改同版本拒绝并要求新版本。开发 seed 仅预置本项目自建夹具的开发范围，原有身份/项目数据保留；一般用户提供的地址不会自动导入。导入和预览均不探测目标。

Scope 列表游标使用现有签名基础，另设 endpoint=scopes，绑定 user/permissions_version/project/limit/排序位置，15分钟到期且不超过512字符；用紧凑固定字段编码，不改写既有项目游标格式。篡改或跨上下文422，过期或权限版本变化410；查询每页复核有效授权。不承诺多页一致快照。

本批次不创建 Task、RuntimeAttempt、ToolCall 或消息服务；不增加自动数据清理作业。

## 5. 前端和回跳

唯一新业务路由为 `/projects/:projectId/tasks/new`，可从项目工作区的“任务预览”进入。后端 normalize_return_path、前端 normalizeReturnTo 与 OpenAPI 登录/回调路径模式同步增加这个精确路由；不开放任意站内 URL、query、协议相对路径或外站回跳。Task 列表/详情路由留给 B2。

沿用现有 Query、AbortSignal、身份/项目代次和五套主题。另加表单修订号：每次输入变化及预览提交递增；迟到的预览成功或错误都不能覆盖较新输入。POST 不通用自动重试，失败保留输入供用户显式重试；服务端返回的 draft 只作为本次预览结果展示，不触发循环提交。

Scope 选择使用服务端分页，可继续加载下一页；不只给用户第一批50条，也不实现未入契约的全文搜索。预览页面显示必要字段、有效限额及失败原因，不展示契约版本、内部权限码或算法解释。收到401/项目404时沿用现有清理；收到403停止预览并重取项目权限；主题切换不重建表单。

## 6. 验收边界

B1 只验四个 API 场景：合法输入返回规范化范围及当前批次 blocker；路径越界拒绝；跨项目 Scope 拒绝；Viewer/缺少CSRF不能预览。加纯函数输入向量及一次真实页面预览、前端构建。合计测试与脚本排查共享10分钟，达到预算即记录剩余项；不重跑 Phase 1A 全量或三个延期回调。

未执行的检查如实保持待测；B1 完成不表示创建、执行或完整 Phase 1B 已验收。
