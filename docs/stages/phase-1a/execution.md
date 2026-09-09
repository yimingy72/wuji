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
