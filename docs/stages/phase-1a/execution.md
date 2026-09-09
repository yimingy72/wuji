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


### 生命周期集成与第一轮独立预验收

A 的生命周期交付 `9f93977fa49ad5189573104aefaa48d4d37ed756` 集成为候选 `540e45ed362360724dffcd89272582d50991f608`。run-file schema v1、管理/控制入口、进程登记与信号清理、serve-only、有限转发恢复和本地开发命令均已落盘。PostgreSQL 重建同时校验 Pod、ReplicaSet、Deployment 的 owner UID 链，并使用 Kubernetes DeleteOptions.preconditions.uid 执行删除。主代理在独立 loopback HTTP 夹具上验证过本机 kubectl 确实发送 UID 条件，未向真实集群发出该探针的删除请求。

独立测试在上述候选完成工具链准备、两套冻结安装及 `pnpm check:platform`（含正式构建），退出码均为0；首轮生命周期为3通过、3失败，尚未进入完整API/浏览器测试。两项失败来自测试夹具 shebang 中的工作树空格，系统绕过不可执行的夹具后继续查找真实工具；第三项提前退出时测试没有保存父进程管道，无法从该次证据确定其直接错误。测试停止并核验端口、进程与锁已释放。这些结果保留为失败预验收，不计为平台通过。

主代理另确认两项产品问题并交 A 修正：自动恢复与手动恢复可同时启动转发并覆盖归属记录；已停止服务的 TIME_WAIT 被端口预检查误报占用。A 以同 run/service 操作锁串行化启动、暂停、恢复与就绪检查，锁内重读归属和 paused，暂停失败不得宣称成功；端口预检使用 SO_REUSEADDR、不开启 SO_REUSEPORT，动态端口正反探针确认真实 listener 仍被拒绝、TIME_WAIT 后允许立即重启。提交 `5462c2f52ed8ba9821dfc452af7fcdeb8d54d34c`、`a5662c78ba30acdce95aca2cf1ab8dcaf43de050`、`a9d562dcf3bac52e18772f6c378340fa283f54f1` 均已审查集成。

T 在 `5353c5a12a4c50387e1568fc675ab558157d759c` 修正为固定 /bin/sh 启动器并引用完整冻结 Python 路径，执行前自检夹具命中；提前退出也保存父进程输出。新增并发 resume、supervisor/control 竞争、暂停保持、唯一监听 PID 与 run-file 归属一致性断言。修复后4项不依赖真实集群的用例通过，完整6项生命周期仍须在集成候选执行。

第二轮候选固定为 `32107466bba20623b2881c4dfc9fa6b60e0652ed`。独立测试工作树直接检出同一 SHA，保留开发/测试任务分支；执行期间候选内容保持不变，完整验收结果随后记录。


### 生命周期通过与真实浏览器缺陷

候选 `32107466bba20623b2881c4dfc9fa6b60e0652ed` 的工程检查通过；生命周期5通过、1失败，剩余断言仍使用 SO_REUSEADDR=0 而把 TIME_WAIT 视作端口占用。测试修复 `4c16824c1e7715498095010063b7c8e00fc64e96` 先验证 lsof 无 listener，再检查实际可重绑定，未跳过端口验证。

新候选 `add1c2242320199d67366e15ab438960a4332fca` 完成冻结安装及 `pnpm check:platform`，6项生命周期全部通过（88.27秒）。主代理已读取命令日志、退出码，以及启动子进程异常、SIGINT=130、SIGTERM=143、运行时API退出=1的清理事件。数据保留与再次启动、暂停保持、并发恢复后的唯一监听进程均在该组独立测试中验证。

同一候选的完整运行 `p1a20260909t134906161a11` 仍失败：API 23通过/50失败，浏览器4通过/11失败，`pnpm test:platform` 退出1。API共因是测试把解析后的SameSite值精确比较为Lax，而实际为lax，导致登录辅助层提前失败；这些用例的后续业务行为尚未验证。浏览器定位出部分测试问题（实际link误用button定位、回调捕获abort等待、空alert否定断言），以及两项已确认产品缺陷：主题option的可访问名称回退英文值、权威401后详情路由未正确退出。B负责修复；撤权迟到200用例最初怀疑回填，后续trace确认未触发新的session请求，客户端尚未获得新权限版本，原先列表/空canary仅是loader等待状态，故应归为测试缺少前置屏障，不能据此宣称产品回填。

本轮所有测试端口与锁已安全释放。ignored证据在T工作树 `artifacts/phase-1a/independent-final/add1c2242320199d67366e15ab438960a4332fca/commands/`（每命令0600日志及退出码JSON）、`artifacts/phase-1a/platform/p1a20260909t134906161a11/` 和 `artifacts/phase-1a/lifecycle-independent/`。此前两轮未保存完整命令总日志，仅保留工具输出和部分运行证据；该证据流程缺口已经修正，不能把早先结果作为最终验收记录。


T 的功能测试修复 `43ed3b9ceefdda98cf9259310a2fc3a7018e1688` 保留Cookie其他约束，按规范忽略SameSite大小写；使用实际登录link角色、以204捕获真实OIDC回调，并修正空alert否定断言。撤权补例 `e775b31f6e89f434ac127ec87fa609d6ac8f0d28` 仍使用真实API权限变更和SPA Link，但在释放旧200前显式派发正常focus事件、等待新session权限版本及新详情404，建立确定性屏障。两提交已集成，相关路径仍待最终候选重跑。


### 前端修复与测试时序收口

B 交付 `450bbd10de5d388300ba1d2dde14adf444444bfb`：当权威401清除身份并取消session query时，未被中止的路由loader依据当前signed-out状态安全回登录页；新的身份或已中止导航不受迟到loader影响。主题使用中文字符串label及公开labelRender/optionRender保留色块，5项Select关闭虚拟化，使实际option进入可访问树。开发者19项Chrome定向检查、12项既有SPA断言、构建和antd检查通过；仅保留5项关闭虚拟化的性能提示。没有修改共享主题定义或原型代码。

候选 `20c166c2ea7cbf23de0aa33c862f99e008a7bb9b` 的工程检查和6项生命周期通过；完整运行 `p1a20260909t141450e45bf6` 为API 59通过/14失败、浏览器10通过/5失败，退出1。两项前端产品修复及建立屏障后的撤权旧响应断言均已通过。剩余API失败来自测试helper对已打开httpx.Client二次进入上下文，以及8h时长精确比较未容忍DB时钟分次求值的微秒差异。浏览器剩余失败来自回调被截获后仍等待原导航、对默认未变主题要求写入偏好、未等分页数据到达就比较列表。

T 在 `f58ab59aa5a91b4162282096cffd92fcf23328c0` 修复上述测试问题：Client在单一context内登录并yield；8h仅允许1ms误差，保留过期拒绝与重启检查；真实Keycloak表单requestSubmit后等待捕获的真实回调；主题默认UI与实际切换持久化分别验证；分页等待50→4→50实际行数。另 `eb489fd0f45bcd0ead4842a8297298e77968775c` 使用Ant Design支持的方向键操作，保留键盘返回雾银后的持久化断言。

集成候选为 `f337ef3d4b7d4a5f8aee569152e09ba06383aa4e`。独立测试在该SHA重新执行全部检查，命令证据保存在T工作树 `artifacts/phase-1a/independent-final/f337ef3d4b7d4a5f8aee569152e09ba06383aa4e/commands/`。环境记录区分系统Node25.3.0与`pnpm exec/run`使用的项目Node24.20.0，历史安装命令记录不事后改写。完整结论见后续验收记录，当前段落不将尚未结束的测试记为通过。


### 用户要求精简测试并延期集中验证

候选 `f337ef3d4b7d4a5f8aee569152e09ba06383aa4e` 的正式run `p1a20260909t143035156a02` 已达到API73/73、生命周期6/6、Chrome12/15通过；全量命令仍exit1。剩余三个真实Keycloak回调测试超时，不能记为通过。310925仅修改测试辅助代码，后续定向验证仍失败，没有产品源码变化。

2026-09-09用户明确指出测试耗时过长，并要求写入约束。主代理确认存在过度测试：对未变范围重复全量检查、测试辅助代码多次猜测性修复，以及没有及时设置停止条件。当前停止新增测试与修复，所有测试进程已由其负责人安全清理；未验证的测试草案留在独立分支。后续执行根AGENTS.md的10分钟共享预算、两轮定向排查上限、仅复测受影响项和Luna/xhigh集中测试规则。剩余项及准确证据见[后续集中测试清单](deferred-tests.md)，阶段完整验收保持partial。
