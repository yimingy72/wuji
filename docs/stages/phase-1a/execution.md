# Phase 1A 执行记录

- 状态：in-progress
- 批准：2026-09-09 用户在方案评审收口后回复“可以，继续”，覆盖本阶段 Spec / Plan。
- 规划基线：`c583f0b08f81df43b1f6508376d952ed23b17c34`
- 阶段分支：`codex/phase-1a`；已验收 master 继续保留开发基线。
- 角色：开发 A/B 为 `gpt-5.6-sol / xhigh`；独立测试为 `gpt-5.6-sol / high`；主代理集成和验收。

## 批次

| 批次 | 状态 | 提交与证据 |
| --- | --- | --- |
| CORE | 开发中 | A：`phase1a_developer_a`，独立分支 `codex/phase-1a-core`，工作树 `work/worktrees/phase-1a-core`，起点 `e0f4c84ae822f944c1729470263b76ce7281baf0` |
| SERVER | 等待 CORE | API、身份、数据库、迁移、Kubernetes 依赖与进程生命周期由 A 负责 |
| WEB | 等待 CORE | 正式页面、共享主题与原型主题迁移由 B 负责 |
| TEST | 等待 CORE | 独立编写用例，最终绑定集成 SHA 运行 |
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
