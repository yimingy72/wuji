# P14 TopologyFlowCanvas 固定 DTO 切片报告

日期：2026-09-13。状态：正式组件与固定 DTO 浏览器展示完成；P14 总体仍为 `partial`，不是 M4 闭环通过。被测代码提交为 `9a1c8e20ccd57b19e74d748129a3d5d524eab6f4`。本报告所在记录提交不在正文预写自身 SHA。

## 审查归档索引

- [初次独立代码/视觉审查](P14-review.md)：永久 `derived copy`，固定原代码 `9a1c8e20ccd57b19e74d748129a3d5d524eab6f4` 与原证据 `e456425fe3deb6c3ada5c8f424aa1ac3a7a50fa7`，当时结论为 `CHANGES REQUIRED`。
- [定向修复证据](review-fix-report.md)：绑定修复代码 `bd3111a62a624aa5acef7d167ffe96b18747934a` 与证据提交 `64bbdf2974b39856a2cb29dd1eee97cb1a70ca93`，记录 16 Vitest、2 个受影响 Chromium 用例和 web typecheck。
- [定向复审](P14-rereview.md)：永久 `derived copy`，固定上述三个提交且排除中间 M1/P09，最终结论 `PASS`，F1—F4 全部关闭。

本报告下文保留 `9a1c8e2` 当时的实现与测试事实；其中“拓扑为默认视图”已由 `bd3111a` 的 F3 修复替代，正式 `ExecutionObservation` 当前保持 blackboard 默认、拓扑仅作为新增入口。归档只调整相对证据链接，没有改写原 SHA、执行范围或审查结论。

## 交付行为

- `TopologyFlowCanvas` 使用 `@xyflow/react@12.11.6` 的受控 nodes/edges、自定义完整节点类型、受控 viewport 和稳定回调。没有 `fitView`，新增节点保持当前 viewport；自由连接、重连和 Delete 删除均关闭。
- `toFlowElements` 原样保留精确 `entity_type:id@revision` 身份和 edge endpoint。同一 Claim 从 claim 显示为 fact 时只改变 `displayKind`，不产生第二个正文节点；旧关系不迁移到新 revision。
- `LayoutPreference` 区分逻辑 anchor 与 revision 专用 anchor。精确位置优先，多个 revision 继承同一逻辑位置时使用不重叠偏移；pinned 节点不可拖动。客户端拖动只改个人布局 entry，保留原 `layout_revision` 和 viewport。
- explicit revision 与 follow latest 选择分开。列表视图、原生键盘按钮、文本状态、截断提示和五套共享主题均由同一正式组件提供。历史模式隐藏 projected action。
- `TopologyContainer` 默认以同源 cookie 请求真实 `GET /api/v2/tasks/{task_id}/topology`，严格检查固定 TopologySnapshot 形状、节点规范身份、唯一 ID/动作及 edge endpoint。失败时显示错误，不回退到测试 DTO。
- 获授权的窄集成只修改 `features/task-execution/ExecutionObservation.tsx`：新增默认“拓扑”主视图并挂正式容器；既有黑板、时间线、工作区及 Task 创建语义均保留。

## 可复用接口

`TopologyFlowCanvasProps`：`snapshot`、`layout`、`mode`、`selection`、`onSelect`、`onLayoutChange`、`onCommandRequested`、`onExpandRequested`。

`TopologyContainerProps`：`taskId`、`mode`、可选 `snapshotId/layout/selection`，以及可组合的 `readSnapshot/onSelect/onLayoutChange/onCommandRequested/onExpandRequested`。未注入 reader 时使用真实 v2 topology GET；测试 fixture 没有进入生产组件或容器。

`LayoutPreference`：`view_name/layout_revision/selection_mode/entries/viewport`。其中 entries 直接使用生成合同的 `LayoutEntry/LayoutAnchor`，TopologySnapshot/KnowledgeRef/NodeEntityType 同样直接取自现有 v2 generated DTO；本切片未修改 OpenAPI 或生成文件。

## TDD 与验证结果

RED 记录：

- 首轮 Vitest 正确失败于 topology 模块不存在。
- 容器边界测试正确失败于 `TopologyContainer` 不存在。
- 自动布局反例得到 `7` 个唯一坐标而期望 `13`，定位到不同实体类型复用列内第 0 行。
- revision 继承反例得到卡片重叠，定位到 36×28 偏移小于节点尺寸。
- DTO 反例证明旧 parser 会接受空 view ID、重复动作、节点身份不匹配与悬空端点；随后收紧运行时检查。

GREEN 命令与实际结果：

```text
PATH="$PWD/work/toolchain/bin:$PATH" pnpm exec vitest run --config tests/topology/vitest.config.ts tests/topology/projection.test.ts --reporter=verbose
1 test file passed; 13 tests passed; exit 0.

PATH="$PWD/work/toolchain/bin:$PATH" pnpm --filter @wuji/web typecheck
tsc --noEmit; exit 0.

PATH="$PWD/work/toolchain/bin:$PATH" pnpm --filter @wuji/web build
3322 modules transformed; production build completed; exit 0.
Vite reported the existing >500 kB chunk-size advisory; it did not fail the build.

PATH="$PWD/work/toolchain/bin:$PATH" pnpm exec playwright test --config playwright.topology.config.ts
3 Chromium tests passed in 4.7 s; exit 0.
```

登记的浏览器 `test_name` 与动作：

- `fixed snapshot remains keyboard-readable and cannot issue graph mutations`：13 节点真实渲染；无 connectable handle 或 edge updater；Enter 选择精确 revision；Delete 后仍为 13 节点且领域命令计数为 0；切到列表后键盘选择 @2；新增 @3 后为 14 节点且 viewport style 不变；pinned @2 不可拖；拖动 Intent 产生布局回调而 revision 仍为 `17`。
- `history mode suppresses every projected action`：历史视图没有执行动作，领域命令计数为 0。
- `the same formal component renders in all five shared themes`：silver、glacier、celadon、slate、graphite 均取得对应 `data-palette` 并渲染正式画布。

## 截图与请求证据

- [雾银](screenshots/silver.png)
- [冰蓝](screenshots/glacier.png)
- [青瓷](screenshots/celadon.png)
- [亮石墨](screenshots/slate.png)
- [原石墨](screenshots/graphite.png)
- [完整 HTTP 请求与响应](http-reproduction.md)

截图和 HTTP 报文来自专用固定 DTO 浏览器页。固定数据仅用于组件测试，因此这些证据不代表真实 P13 API、真实身份或 M4 端到端闭环。

## P13 / P15 待接

- `pending`：v2 auth 与 TaskDetail 现有身份状态的统一错误/失效处理；当前只证明同源 cookie 请求和正式路由挂载。
- `not_run`：P13 持久 topology endpoint 的真实签名请求、当前权限、历史、分页、opaque cursor、隐藏依据及 404/410 实际响应。
- `pending`：服务端 LayoutPreference 读取入口、`PUT /layouts/{view}`、`If-Match layout_revision` 冲突处理和跨用户隔离；当前只验证组件内个人布局事件。
- `pending`：P15 ViewStream/ViewReset、原子 patch、重连、权限变化清缓存、增量分页与 expand 查询。
- `not_run`：300/600 与 1000/2000 图规模的固定环境 p95；本次浏览器只覆盖两次 13→14 节点固定 DTO。
- `not_run`：任意 structured record 的详情读取/无损 JSON 展示。当前 TopologySnapshot 不含该字段，组件没有解析、转成浮点或截断任意 record data；后续记录侧栏必须保留原始文本或使用无损解析。
