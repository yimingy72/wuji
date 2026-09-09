# Phase 1A 独立测试记录

- 状态：partial；下文准备阶段内容保留为历史，当前结果见本节末尾及阶段验收
- 测试角色：独立 `gpt-5.6-sol / high`
- 测试工作树：`work/worktrees/phase-1a-test`
- 测试实现基准：`b1730e6e9937d42084df11137c8843d21af774a6`
- 收口统一起点：`6293d9eb62d33f270284adcd586401a0714a36e9`
- 被测试产品提交 SHA：`f337ef3d4b7d4a5f8aee569152e09ba06383aa4e`
- 平台测试 run_id：`p1a20260909t143035156a02`
- 阶段结论：partial；完整验收未通过

本文件保留独立测试套件的准备历史，并在末尾记录实际执行结果。CORE 检查、受控 issuer 自身冒烟和测试收集成功均不能替代 P1A-01–10 的最终平台验收。最终报告必须绑定主代理给出的唯一集成 SHA 和新建的隔离 run；失败或关键 skip 时保持不通过。

## 已准备的独立覆盖

| 验收项 | 测试入口与观察点 | 当前状态 |
| --- | --- | --- |
| P1A-01 | 冻结生命周期、迁移/种子重放、同 run API 重启与 PostgreSQL Pod 重建后会话/项目/cursor 保持 | 待运行 |
| P1A-02 | 真实 Keycloak 浏览器 Code+PKCE、跨浏览器/替换/并发/重放；loopback issuer 的 RS256、issuer/aud/nonce/signature/time 反例；握手交换状态与日志脱敏；旧交换过期后迟到成功、协议失败或依赖失败均不创建 Session、不清新握手 Cookie | 待运行 |
| P1A-03 | Cookie 不透明及仅哈希落库、8h/30m 边界、API 重启、禁用再启用、登录/禁用双方到达同一用户锁的确定性屏障、认证行锁等待期间跨过 idle/absolute 期限 | 待运行 |
| P1A-04 | CSRF/Origin 正反例、204 后旧 Cookie 失效、DB 失联时 503、前端遮蔽和显式重试 | 待运行 |
| P1A-05 | 单/双租户、同租户互斥 U1/P1 与 U2/P2、真实运行角色、普通与 TEMP DDL 42501、无上下文、事务级池复用、游标及复合 FK | 待运行 |
| P1A-06 | 项目/租户撤权、版本和审计同事务、幂等 no-op、审计失败回滚、迟到 200/错误、真实空项目 | 待运行 |
| P1A-07 | Session/Project/ProjectPage/Error 的 openapi-core 真实响应验证、API→DB 失联恢复、全新未迁移库 fail closed | 待运行 |
| P1A-08 | 五主题主页面/浮层/键盘、设备偏好、URL 临时覆盖、无效/不可用存储、项目及分页状态 | 待运行 |
| P1A-09 | 深链接刷新与回跳、真实退出、项目切换、回调错误 own-key 白名单、生产 bundle 凭据/Mock/未实现入口检查 | 待运行 |
| P1A-10 | manifest schema/0600/工作树/SHA/profile-namespace/DSN 端口语义与错误脱敏；context/端口；错误集群归属写前拒绝；登记前信号/异常、启动期与就绪后子进程失败；SIGINT/SIGTERM；并发运行记录；外部父测试核对独立进程组清理、端口/锁复用及旧 run DB/realm 保留 | 待运行 |

Python API 用例位于 `tests/api`，生命周期父测试位于 `tests/platform-lifecycle`，浏览器用例位于 `tests/platform-browser`，协议夹具位于 `tests/fixtures/oidc/issuer.py`。协议夹具只绑定 loopback，校验 confidential client 与 PKCE S256，通过受限控制 token 选择单一协议反例；应用仍走正常 Authlib/OIDC 路径。生命周期测试只终止事件中已核验 PID、进程组和命令标识的本 run 进程；集群错误归属反例使用 PATH 内独立命令夹具，不连接或修改真实集群资源。

## 准备阶段证据

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `./scripts/bootstrap-toolchain.sh` | 0 | 安装项目固定 uv 0.12.11 与 CPython 3.13.15 到 ignored 工作树目录 |
| `./scripts/uv.sh sync --frozen` | 0 | 冻结 Python 依赖安装成功 |
| `pnpm install --frozen-lockfile` | 0 | Node 24.20.0 / pnpm 10.32.1 锁文件安装成功 |
| `pnpm check:platform` | 0 | 当前 CORE 基准检查通过；26 项契约、3 项 Python unit、类型/antd/构建通过，不计作 P1A 平台通过 |
| `python -m py_compile tests/fixtures/oidc/issuer.py tests/api/*.py` | 0 | Python 测试与夹具可编译 |
| `pytest --collect-only ... tests/api` | 0 | 67 个平台用例可收集；正式入口需 SERVER 添加 strict marker |
| `playwright test --config playwright.platform.config.ts --list` | 0 | 14 个浏览器用例可收集；使用临时无凭据 manifest，仅做收集 |
| `tsc --noEmit ... playwright.platform.config.ts tests/platform-browser/*.ts` | 0 | 独立浏览器测试严格类型检查通过 |
| loopback issuer discovery → authorization → token smoke | 0 | confidential client、PKCE S256、RS256 ID Token 路径可运行 |
| `pytest --collect-only tests/platform-lifecycle tests/api`（收口） | 0 | 73 个 API 用例及 6 个生命周期用例可收集；不计作实际平台通过 |
| `playwright ... --list`（收口） | 0 | 15 个浏览器用例可收集；使用无凭据临时 manifest，不计作实际平台通过 |

准备阶段没有启动 Wuji Kubernetes 依赖、没有测试正式 API/前端，也没有修改开发或既有 run 数据。工作树无 `.codegraph/`，按仓库约定使用 `rg`、直接读取当前文件及固定提交内容。

## 实际执行汇总

主代理根据独立测试代理的交付与本机日志汇总：冻结安装/check:platform均exit0，生命周期6/6，API73/73，Chrome12/15；整体test:platform exit1。提交为`f337ef3d4b7d4a5f8aee569152e09ba06383aa4e`，run为`p1a20260909t143035156a02`。具体P1A映射、环境、限制与证据路径见[阶段验收](acceptance.md)。

用户2026-09-09要求停止长时间重复测试。当前已清理测试进程，保留DB/realm；未通过的3项真实Keycloak回调用例及未验证helper草案转入[后续集中测试清单](deferred-tests.md)。后续使用Luna/xhigh，并执行根AGENTS.md的精简测试约束。
