# P15 X04 实测：snapshot 绑定、SSE reset 与浏览器实时视图

- 日期：2026-09-18
- 代码：后端/合同 `20175ca`；工作台开关 `7df5bfb`
- 集群：`docker-desktop` / `wuji-vnext-test`
- Task：`2abfdd57-7a0f-4cba-8ce4-2a57f751d0b0`
- 迁移头：`vnext_0028_p06_platform_run_settlement`（包含 `vnext_0025_p15_view_stream`）
- platform/API/gateway 镜像：`127.0.0.1:56615/wuji-vnext-platform@sha256:58a4a979b670dcb416bc33d23a7956fa691a42c98594c26c1fa0c1e4b793659d`
- Web 镜像：`127.0.0.1:56615/wuji-web@sha256:e8fbdb7bec3e813556363f7feb76576027b0803abc4e6ff2727ed7ab838cbe6b`

## 结果

1. 直接 API 拓扑读取返回 `view_revision=1` 和初始 `snapshot_id`。
2. Runtime `pause` 返回 `202 Accepted`；同一 SSE 连接收到 `wuji.view-event.v3`，视图从 `1→2→3` 推进，每个事件携带新的 `snapshot_id`。
3. 使用已消费的旧 cursor 重连，收到 `view-reset.v2`，原因是 `change_too_large`；不会从错误基线继续应用补丁。
4. Web/BFF 修复部署签名键漂移后，浏览器显示“实时视图已连接”；再次 pause 后无需刷新，画布视图修订从 `1` 变为 `2`，快照身份和节点修订同步变化。
5. 测试结束后通过完整 `resume` 控制请求恢复 Task：最终 `desired=run / observed=running`。

## 证据

- [完整 SSE 请求与响应](raw/sse.request.txt)
- [SSE 响应头](raw/sse.response.headers)
- [SSE v3 批次原文](raw/sse.response.body)
- [旧 cursor reset 请求/响应](raw/stale-cursor.request.txt)
- [pause 完整 HTTP 包](raw/pause.http) / [resume 完整 HTTP 包](raw/resume.http) / [第二次 pause 完整 HTTP 包](raw/pause2.http)
- [清理 resume 完整 HTTP 包](raw/cleanup-resume.http)
- [BFF 登录与拓扑 HTTP 包](raw/bff-login.request.txt) / [BFF topology](raw/bff-topology.request.txt)
- [数据库状态](raw/database-state.txt) / [清理后状态](raw/database-state-after-cleanup.txt)
- [浏览器可访问性回读](raw/browser-ax.txt)
- [终端截图](screenshots/x04-sse-reset-terminal.png)

Bearer、Session Cookie 和签名密钥均已脱敏。截图同时显示了 v3 SSE 批次、stale-cursor reset，以及浏览器“实时视图已连接”和无刷新后的视图修订变化。

## 限制

本次覆盖单 Task、单连接和单浏览器；多标签公平性、跨 BFF 重启后的恢复及规模 p95 仍未验证。`LIVE_VIEW_ENABLED` 已在受保护的 X04 代码同版本中开启；真实模型与生产身份仍不在本试次范围内。
