# P14 Aquinas 审查定向修复证据

日期：2026-09-13。依据：`.superpowers/sdd/vnext-v2/P14-review.md`。被测代码提交：`bd3111a62a624aa5acef7d167ffe96b18747934a`。本报告所在证据提交不在正文预写自身 SHA。

本轮只修复 P14 审查 F1—F4；没有修改 shared backend、RootContract、P15 或 Auth，没有执行 P13 API、Layout CAS、stream 或规模 p95。

## 修复结果

- F1：新增规范十进制 `RevisionString` 校验与无损比较。`follow_latest` 遍历同一逻辑 anchor，以长度和字典序比较已验证的非负十进制字符串，不依赖数组/patch 到达顺序，也不使用 `Number`。TopologySnapshot parser 同时拒绝 `01`、`1.0` 等非规范 view/node revision。
- F2：`TopologyContainer` 将 `taskId/mode/snapshotId/readSnapshot` 组成请求维度 key。任何维度变化立即重建内部请求组件，隔离旧 snapshot、local selection、local layout 和动作状态；旧 reader 即使忽略 abort 并迟到完成也无法写回。相同维度的手动重读仍保留最后确认快照及明确错误提示。
- F3：正式 `ExecutionObservation` 恢复 `blackboard` 默认视图；“拓扑”入口和真实 v2 reader 保留，未接好的 topology API 不再抢占默认体验。
- F4：固定 DTO 新增中文领域动作“重新核对”。浏览器用例先在 live 中用键盘触发“执行 重新核对”并点击“展开关联”，确认两个回调各执行一次；再进入 history，确认两个真实控件均不存在，节点键盘选择后领域与展开回调仍为 0。

## RED 证据

- `follow_latest` 乱序 `@10,@2`：修复前错误选择 `claim:claim-1@2`，期望 `claim:claim-1@10`。
- 超出 JS 安全整数范围：修复前错误选择 `@9007199254740992`，期望 `@9007199254740993`。
- 非规范 revision：修复前 parser 接受 `view_revision=01` 和 `revision=1.0`。
- 请求隔离：更换 reader 后修复前仍显示 1 个“任务 A 授权入口”，期望立即为 0。

## 实际 GREEN 范围

```text
PATH="$PWD/work/toolchain/bin:$PATH" pnpm exec vitest run --config tests/topology/vitest.config.ts tests/topology/projection.test.ts --reporter=verbose
1 test file passed; 16 tests passed; exit 0; duration 2.02 s.

PATH="$PWD/work/toolchain/bin:$PATH" pnpm exec playwright test --config playwright.topology.config.ts --grep 'request dimensions|live actions'
2 Chromium tests passed; exit 0; duration 3.6 s.

PATH="$PWD/work/toolchain/bin:$PATH" pnpm --filter @wuji/web typecheck
tsc --noEmit; exit 0.
```

未重跑全平台、web build、后端、数据库、K8s 或五主题截图用例。生产依赖与视觉样式未变化；已有五主题截图保持原文件未改写。

## 证据入口

- [Aquinas 原审查永久归档](P14-review.md)
- [Darwin 定向复审永久归档](P14-rereview.md)
- [受影响浏览器动作测试](browser.spec.ts)
- [revision / parser 单元测试](projection.test.ts)
- [既有雾银截图](screenshots/silver.png)
- [既有原石墨截图](screenshots/graphite.png)
- [既有完整 HTTP 请求与响应](http-reproduction.md)

截图与 HTTP 报文仍是固定 DTO 专用浏览器页证据，不代表真实 P13 API/Auth/Layout/stream/M4 闭环。没有发现新资产或新接口；现有 `GET /api/v2/tasks/{task_id}/topology` 合同状态保持 pending。
