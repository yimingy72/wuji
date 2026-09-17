# E07：R04/R05 未关闭前，工作台固定在单一快照

- 日期：2026-09-17；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`；提交 `05ce2e2`。
- 范围：`apps/web`（React Flow 工作台）的视图读取路径。**不**宣称 P15 完成，也**不**把实时模式标为可用。

## 1. 变更与理由

R04（view revision 与 snapshot 未原子绑定）与 R05（重连不证明从已见基线真正续传）仍未关闭，因此：

- 新增 `LIVE_VIEW_ENABLED = false`：该开关关闭时前端**不建立 SSE 订阅**，图、详情与引用全部来自同一次受权快照读取；
- 界面显式显示「快照模式：实时订阅未启用，图为当前受权快照」，并提供「刷新快照」按钮（重新读取一次快照，而不是局部打补丁）；
- 实时状态文案（已连接/连接中/重连中/已暂停）保留在开关打开后的分支，供 X04 修好后恢复。

## 2. 验证（原始记录见 `raw/`，截图见 `screenshots/snapshot-mode.html`）

```text
$ pnpm --filter @wuji/web typecheck      # exit=0
$ kubectl -n wuji-vnext-test get deploy wuji-web -o jsonpath='{...image}'
127.0.0.1:56615/wuji-web@sha256:e6df65ff…      # 本次构建并滚动到位的镜像
$ curl -s http://127.0.0.1:44180/assets/index-Dh9JUBIn.js | grep -o '快照模式…'
快照模式：实时订阅未启用，图为当前受权快照
t===`live`&&!1                                  # 打包后的常量就是 false
```

服务中的 bundle 确实包含该文案与关闭后的常量，说明部署到 `http://127.0.0.1:44180/` 的工作台已经是快照模式。

## 3. 未覆盖

- 未执行浏览器交互截图（本次以服务中的 bundle 与 typecheck 作为证据）；
- 实时模式本身未修复：`LIVE_VIEW_ENABLED` 的打开必须与 X04（R04+R05）及其真实 SSE 证据一起进行。
