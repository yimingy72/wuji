# Phase 1A 执行记录

- 状态：in-progress
- 批准：2026-09-09 用户在方案评审收口后回复“可以，继续”，覆盖本阶段 Spec / Plan。
- 规划基线：`c583f0b08f81df43b1f6508376d952ed23b17c34`
- 阶段分支：`codex/phase-1a`；已验收 master 继续保留开发基线。
- 角色：开发 A/B 为 `gpt-5.6-sol / xhigh`；独立测试为 `gpt-5.6-sol / high`；主代理集成和验收。

## 批次

| 批次 | 状态 | 提交与证据 |
| --- | --- | --- |
| CORE | 交接门槛通过 | A：`phase1a_developer_a`；起点 `e0f4c84ae822f944c1729470263b76ce7281baf0`，交付 `8af768fd51ce121bbe434b1f13e4fb449e73f148`，集成及主代理复核版本 `68e6a557e5f1d76261ddac210eee6cf874ffd39c` |
| SERVER | 开发中 | A：`phase1a_developer_a`；分支 `codex/phase-1a-server`，工作树 `work/worktrees/phase-1a-server`，起点 `b1730e6e9937d42084df11137c8843d21af774a6` |
| WEB | 开发中 | B：`phase1a_developer_b`；分支 `codex/phase-1a-web`，工作树 `work/worktrees/phase-1a-web`，同一起点 `b1730e6e9937d42084df11137c8843d21af774a6` |
| TEST | 独立编写用例 | `phase1a_independent_test`；分支 `codex/phase-1a-test`，工作树 `work/worktrees/phase-1a-test`，同一起点 `b1730e6e9937d42084df11137c8843d21af774a6`；运行等待集成 SHA |
| ACCEPT | pending | 主代理核对独立证据并复核关键链路 |

本文件持续记录实际任务起点、交付 SHA、设计修订、检查结果与未解决事项。尚未执行的 P1A-01–10 保持未通过；文档提交不作为被测试的产品实现。

## 实施期间设计细化

- 主代理核对 Authlib 1.8 固定发行源码后，明确 SERVER 使用 essential claims 绑定配置 issuer、client_id audience 和握手 nonce，固定 RS256 及零时钟宽限。SDK 的默认 nonce_supported 兼容分支不能放宽 Wuji 的校验要求。Spec §3 / Plan §2 已同步；CORE 不依赖此实现，SERVER 和独立协议测试按新配置接入。

## CORE 开发期间审查

本表记录开发中发现的问题，最终是否通过仍以交付提交上的检查为准。

| 项目 | 发现与处理 | 当前证据 |
| --- | --- | --- |
| 工具链安装边界 | uv 默认在用户 bin 生成 Python 入口；改为 `--no-bin`、项目 bin 目录，并精确移除本次链接 | 开发者重跑安装；主代理只读复核用户 bin 的 python/python3/python3.13 均不存在 |
| 交接依赖与检查 | 原型缺共享主题依赖，平台检查需包含 antd，uv 检查需冻结解析 | 已交 A 修正，待 CORE 提交检查 |
| 公共接口 | 项目列表补500和游标语义，回跳路径限定现有项目路由 | 已交 A 修正，待生成物及用例验证 |
| 浏览器校验器 | Ajv standalone 的 esm 选项仍生成两个 CommonJS require，原生 ESM 导入失败 | 主代理在内存复现 require 未定义；已交 A 修正生成器与 helper 导入，待正反例及浏览器消费验证 |

## CORE 交接验收

主代理接受 CORE 的工程交接门槛，允许 SERVER / WEB 基于固定集成版本并行实施，独立测试开始按 Spec 编写用例。此结论不改变 P1A-01–10 的待测试状态。

开发者的最终 `uv sync --frozen`、`pnpm install --frozen-lockfile`、`pnpm check:platform` 和原型构建退出码均为0。主代理在集成提交 `68e6a557e5f1d76261ddac210eee6cf874ffd39c` 的主工作区重新安装项目工具链和冻结依赖，完整 `pnpm check:platform` 通过：26项契约测试、3项Python unit（含真实健康响应的openapi-core校验）、正式前端/主题/原型类型及构建检查通过。主代理另外执行原型构建和Chrome校验器浏览器探针，分别退出0、1/1通过。

主代理亲自启动 API，通过动态分配的loopback监听端口验证 live=200、ready=503、尚未实现的session/login=404，所有响应no-store；运行OpenAPI只包含两个公开health操作且使用根server。向该自建进程发SIGINT后退出0，没有占用固定开发端口。证据在主工作区 ignored 的 `artifacts/phase-1a/core-root-review/check-platform.log`、`api-smoke.json`、`api-smoke.log`。

上述四项开发审查问题均在交付中修正。Redocly的三条4xx例外仅用于回调和两个健康端点，由契约测试固定；保留登录302/回调303引发的两条2xx提示。Ant Design保留原型已有的两条virtual=false提示，正式骨架与主题检查无问题。本机使用系统Chrome，尚未运行Linux CI。主代理首次把依赖检查与工具链安装同时启动，检查按设计因uv尚未就绪退出1；安装完成后按顺序重跑完整检查退出0，该次编排错误不记为产品缺陷。

当前 `test:platform` 明确返回非零，等待 SERVER / TEST 实现完整生命周期；未部署Wuji集群依赖，未实现真实身份、项目或任务执行。CORE工作树保持干净并保留证据，后续为SERVER创建新工作树。

## 共享主题交接验收

WEB 开发者从原型抽出单份五套主题与 Ant Design token，交付 `7f4229bc0b0133ffaf5d91cb59d8d72eeba04912`；主代理集成为 `89118a49ae5b856b71729a9ad008e025fe1e5a3f`。原型只改主题导入，保留其每标签页偏好与交互。

主代理在该集成 SHA 执行共享主题/原型类型检查、原型构建及共享主题 antd lint，退出码均为0；Chrome 原型浏览器回归12/12通过，覆盖五主题可读性、原交互与标签页偏好。ignored 证据目录为 `artifacts/phase-1a/theme-root-review/`，`summary.json` 记录代码 SHA、命令和退出码。这通过了主题抽取的交接门槛；正式平台 P1A-08 / P1A-09 仍待独立集成测试。

## SERVER / WEB 开发期间审查

| 项目 | 发现与处理 | 状态 |
| --- | --- | --- |
| PostgreSQL 18 数据目录 | 固定 PVC 挂载 `/var/lib/postgresql`、PGDATA `/var/lib/postgresql/18/docker`；Plan 已同步，开发者确认 | 待真实卷与重建验证 |
| 成员关系 RLS | 存储草稿的 TenantMembership 策略遗漏 enabled 过滤，已交 A 修正 | 待交付及真实角色反例 |
| 数据库初始化 | ALTER ROLE 密码不能用默认 psycopg 服务端参数绑定；改为安全客户端值组合，不能打印密码 SQL | 待交付及真实初始化验证 |
| 迟到错误响应 | 项目切换后旧请求的401/503也必须检查代次，不能只防旧200/404 | 已交 B 修正，待独立竞态测试 |
| 退出确认 | 畸形401响应不能等同于符合契约的 UNAUTHENTICATED；退出失败保留显式重试 | 已交 B 修正，待独立退出测试 |

独立测试正在按 Spec 编写协议、数据库故障、权限和浏览器用例。测试运行文件/控制命令由 SERVER 唯一实现，测试者提供受控 issuer；完整执行仍须等待固定集成 SHA。

## 收口批次执行

2026-09-09 用户明确批准实施《Phase 1A 收口与集成验收》。主代理先将 SERVER 未提交生命周期草稿保存到 ignored 的 `work/draft-backups/phase-1a-closeout-20260909/`，记录文件摘要，再更新 Spec / Plan / closeout；合并统一基线后逐项确认草稿未变。

已集成身份 API `955045644d2ab4b886ecff58018da0e43bae4017`（主线 `ebf1bf0`）、正式 WEB `d201cde8faf40846f4c52329b6410b78a5d361ab`（主线 `39e0e27`）和独立测试 `0b194da668790870dd276b276cd339f14e47f114`（主线 `f43f5d2`）。这些是工程交付，完整平台仍未验收。

收口统一主线为 `2f15ae89ed9474987699a806c1ee2de1f2cdce2c`。保留任务原历史后，A 的工作树起点为 `2dc217c9ad321a74db22217f2cfa75c693a59d01`，B 为 `bc7f618bb3f224dd1f2d3a6ff385a4557f9c2e1c`，T 为 `6293d9eb62d33f270284adcd586401a0714a36e9`；三者包含同一已集成产品内容。

| 项目 | 状态与证据 |
| --- | --- |
| 工程复核 | 主代理在统一主线执行 `./scripts/uv.sh sync --frozen`、`pnpm install --frozen-lockfile`、`pnpm check:platform` 均退出0，后者包含正式构建；证据 `artifacts/phase-1a/closeout-root/baseline-check-summary.json` 及同目录日志 |
| 登录文案 | B 交付 `15cccc5c6301df13fb3d230b892be2909bea3e18`，仅精简登录页说明与排版；开发者构建、antd lint、6项浏览器探针通过，主代理审查后集成 |
| 身份与运行权限 | A 修正迟到握手、TEMP 授权及会话刷新时效边界；独立测试补确定性时序，仍待真实数据库验收 |
| 生命周期与控制 | A 完成原草稿，T 配套 serve-only 与独立生命周期测试；仍待交付与统一候选测试 |
| 真实 WEB / ACCEPT | 等待真实生命周期启动和最终候选 SHA；开发者 Mock 检查不计入 P1A 验收 |

主代理在会话鉴权中另发现：持锁 SELECT 检查过期后，刷新 last_seen 的 UPDATE 未重查有效期；锁等待或两条语句之间跨过期限时存在恢复过期会话的风险。已交 A 收紧刷新条件，T 用真实会话行锁和数据库时钟验证。此项属于既有会话过期验收边界，不增加接口。

### 身份与 TEMP 修正交接

A 交付 `77b132fcd9f0401d622a4f696609ac4fec809f15`，主代理审查后集成为 `722d6d6422c2e0a8f4d643a9767d0c447f67c819`。开发者 `pnpm check:api` 退出0（11项），真实DB的过期/替换握手均不创建新会话且保留旧会话；幂等权限修复前后为8用户/57项目，两运行角色普通建表及临时建表均返回42501。证据在 A 工作树 `artifacts/phase-1a/server/closeout/`。

主代理另外在同一真实开发数据库中创建两条专属测试会话，比较旧 SQL 与集成后的实际 `DatabaseAuthority.authenticate`。通过 pg_stat_activity 确认请求等待行锁，再等数据库时钟跨过空闲期限后释放：旧 SQL 仍通过并刷新时间，修正实现拒绝且时间不变。两条测试会话均精确删除，未改动已有会话或业务数据。证据 `artifacts/phase-1a/closeout-root/session-lock-probe.json` 绑定上述集成 SHA，退出0。初次探针使用 migration 角色观测其他角色的 wait 字段，权限不足未能建立屏障；改用既有管理连接后完成确定性对照，此为探针修正而非产品失败。独立测试仍需在最终测试 run 重验。

### 前端与测试有效性审查

主代理发现登录错误白名单用 `in` 接受了 `__proto__` 等继承键。B 在 Chrome 复现登录页崩溃后，以自有属性守卫修复，交付 `6f7fd22c89a176326c3d5e44133bb386a1a0838d`（集成 `a39b31e`）；开发者浏览器25项断言、构建及antd检查通过。证据在B工作树 `artifacts/phase-1a/web-login-error-whitelist/`。

原浏览器竞态用例使用整页 `page.goto`，会重建JavaScript上下文，不能证明SPA代次检查。T已改成真实项目Link点击和焦点刷新；B按该流程提前自测，发现权限版本变化取消旧loader后误入错误页。修复 `4021c275810e99bbda399f8711bf07e72aaed7fa`（集成 `d2cdd07`）只在同一仍活动的项目导航、身份上下文已经更新时重新鉴权，新导航已中止的loader不能恢复旧路由。开发者12项SPA断言、构建和antd检查通过，证据在B工作树 `artifacts/phase-1a/web-spa-race/`；仍待独立真实API验收。

T交付的补例实际提交为 `a218b4f7c2bb3ad02bd35044bf7195ffa4b2ee93`、`85af81cbe4b477c19e9622626f482c05f30203bd`、`4d070f24f3c7529c168b7d48818b719fe2bc4ddc`、`d51b05c0632980634c3356d21693e7d68e123924`，均已集成。当前收集73项API、15项浏览器及6项生命周期用例；编译和收集不计为平台通过。

测试自身的进程清理断言曾引用错误字段而跳过记录，已改为核对启动时间、命令及进程组，并检查独立子进程组消失；端口冲突同时核对明确错误码和实际锁释放，父进程输出以0600保留。运行文件增加权限、工作树、SHA、环境/DSN端口及错误脱敏负例。

主代理审查启动登记窗口后，T用自建sleep进程定位到信号屏蔽会被子进程继承的副作用；A使用显式子进程launcher恢复信号后exec真实命令，开发者探针已确认SIGTERM退出。转发恢复增加明确截止时间/连续尝试上限，并在退避后重读暂停状态。这些生命周期修正仍待提交集成及独立运行，不能以静态审查或开发者声明结案。
