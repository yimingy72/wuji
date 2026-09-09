# Phase 0 本地验证记录

- **日期**：2026-09-09
- **对象**：OpenAPI 0.1.0、共享夹具、独立前端原型和最小工程检查
- **环境**：macOS x64；Node 24.20.0；pnpm 10.32.1；Chrome 153.0.8010.36
- **范围**：本地文件与本地静态服务；浏览器测试使用示例数据，没有连接平台执行端、模型或测试目标

## 1. 第一版检查结果

| 检查 | 结果 | 证据与边界 |
| --- | --- | --- |
| 冻结依赖安装 | 通过 | `pnpm install --frozen-lockfile`；严格 peer 检查，锁文件无待解析变化 |
| OpenAPI 校验与类型生成一致性 | 通过 | 15 个操作、28 个 Schema；Redocly 校验无警告；生成物与源契约一致 |
| 契约测试 | 21 个通过 | Vitest + Ajv 2020；夹具、禁止的输入、终态执行约束、命令接受语义、条件预览和契约安全声明 |
| TypeScript 与生产构建 | 通过 | 四个路由模块按需加载；未实现正式客户端或后端服务 |
| Ant Design CLI 检查 | 通过 | CLI 6.6.3；0 issues、0 skipped files；不是完整可访问性审计 |
| 浏览器流程 | 5 个通过 | Playwright 1.63.0；创建/预览、取消、证据隔离、异常状态、键盘与窄窗口 |
| 页面截图检查 | 已检查 | 1440 px 桌面四页及 390 px 窄窗口；未进行完整设备矩阵检查 |
| 远端 CI | 未执行 | 已写入 GitHub Actions 文件，没有推送或触发远端运行 |

本机浏览器测试使用已安装 Chrome：`WUJI_BROWSER_CHANNEL=chrome pnpm test:e2e`。配套 Chromium 下载未完成，本次没有将它算作验证环境；CI 默认安装 Playwright 配套 Chromium 后运行，Linux CI 结果仍待确认。

## 2. 本地截图

- [任务列表](../artifacts/phase0/tasks.png)
- [创建与范围预览](../artifacts/phase0/create.png)
- [任务详情与取消中](../artifacts/phase0/task-detail.png)
- [证据纯文本预览](../artifacts/phase0/evidence.png)
- [窄窗口](../artifacts/phase0/narrow.png)

第一版截图留档于被 Git 忽略的 `artifacts/phase0/`；当前浏览器测试生成第 5 节的第二版截图。新检出仓库时这些本地链接可能尚不存在。可重现依据是已保存的契约、夹具、源码、锁文件和测试，而不是截图单独构成的证明。

## 3. 构建与兼容性发现

类型生成器声明 TypeScript 5 的 peer 要求，因此固定 TypeScript 5.9.3。初次条件 Schema 缺失分支类型，已补齐并在严格模式下校验；没有关闭 strictTypes 来绕过问题。

页面最初集中在一个约 937 kB 的压缩后 JS 文件中，拆为四个懒加载路由后，最大单个 JS 块约 356 kB，gzip 约 111 kB。最大块体积不等于首屏总资源，也不证明性能达标；正式页面还需在指定设备/网络上测量完整加载和交互预算。

Ant Design 主题调色需要可解析的颜色输入，原型在主题边界将 OKLCH 转换为 sRGB，CSS 设计值保持 OKLCH。另修正了装饰图标参与按钮可访问名称、初始焦点/页面就绪同步，以及未执行任务不应展示已有观察记录的问题。

## 4. 未覆盖的架构要求

原 v0.3 的 70 个架构场景仍未整体标记通过；v0.4 新增 H01–H10 后共 80 项。本次前端检查提供 F01、F02、F03、F08、F11、F12 的部分契约或界面证据，不构成这些场景的完整验收，也不验证 Harness。

尚未验证实际会话/CSRF/权限撤销、租户与项目隔离、数据库唯一约束与并发幂等、事件持久化/SSE、执行停止/出口断流、Runtime 清理、万条数据性能、生产 Ingress 和备份恢复。Schema 中禁止某种响应只能检查声明是否自洽，不能证明目标没有收到请求或进程已经停止。


## 5. 工作台第二版验证（2026-09-09）

按用户反馈完成三栏工作台、Ant Design 暗色 tokens、本地字体、证据检查器以及创建/证据详情的统一样式。介绍性文案移出业务页面，演示控制进入设置抽屉。记录见 [视觉基线](../DESIGN.md)。

- TypeScript 与生产构建通过，最大单个 JS 块约 343 kB / gzip 116 kB；React 运行时独立分块，没有提升告警阈值。字体资源本地打包，Inter 拉丁字形约 48 kB、IBM Plex Mono WOFF2 约 15 kB。
- 6 个浏览器测试全部通过：原 5 组流程随布局更新，新增队列筛选/重置、范围 Tab、证据元数据和完整证据导航。测试服务使用 4175 端口，避免中断供评审的 4173 服务。
- Ant Design CLI：0 废弃 API、0 可访问性、0 用法问题，1 个性能提示。原因是方法 Select 显式关闭虚拟滚动；该控件固定只有 GET / HEAD 两项，保留真实选项 DOM 便于辅助技术和交互检查。它不用于大数据列表。
- 实际渲染检查覆盖桌面、390 px 窄窗口及四个入口；修正了代码行排版、下拉选项 DOM 与主按钮文字对比度。对工作台可见文字、按钮和搜索占位符做 sRGB 对比度抽查；这不替代完整 WCAG 审计。
- 证据标签保持惰性文本，外部请求拦截测试未记录对其他主机的请求；字体也从本地静态服务加载。本轮未修改契约与夹具，21 个契约测试沿用第一版记录，未将界面回归计作平台集成验收。

当前流程截图由 `WUJI_BROWSER_CHANNEL=chrome pnpm test:e2e` 生成，随默认主题更新：

- [任务工作台](../artifacts/workbench-current/tasks.png)
- [创建与范围预览](../artifacts/workbench-current/create.png)
- [取消中](../artifacts/workbench-current/task-detail.png)
- [完整证据](../artifacts/workbench-current/evidence.png)
- [窄窗口](../artifacts/workbench-current/narrow.png)

这些文件属于被忽略的本地验证产物。平台 API、真实执行和第 4 节未覆盖要求仍未完成。


## 6. 多配色与可读性验证（2026-09-09）

保留三栏结构，新增雾银、冰蓝、青瓷和亮石墨，原石墨继续作为对照。默认使用雾银；主题同时覆盖 CSS Modules、Ant Design 控件、抽屉浮层与证据正文。

新增 `tests/browser/palettes.spec.ts`：逐套测量工作台、按钮悬停、创建预览、表单错误、证据、结果不明与设置抽屉的可见文字/占位符；验证切换不会重置取消状态、跨路由和刷新保持主题、不同标签页独立选择、窄窗口切换。加上现有 6 个业务流程检查，共 12 项浏览器测试。

| 配色 | 抽查最低对比度 | 工作台截图 |
| --- | --- | --- |
| 雾银 | 5.20:1 | [预览](../artifacts/palettes/silver.png) |
| 冰蓝 | 5.05:1 | [预览](../artifacts/palettes/glacier.png) |
| 青瓷 | 5.37:1 | [预览](../artifacts/palettes/celadon.png) |
| 亮石墨 | 5.64:1 | [预览](../artifacts/palettes/slate.png) |
| 原石墨 | 6.46:1 | [预览](../artifacts/palettes/graphite.png) |

本机 Chrome 中抽查每套约 490 个文本实例，均超过 4.5:1；测试采用浏览器 sRGB 颜色转换和祖先背景透明度合成。此检查没有覆盖完整键盘/读屏审计、所有控件状态、系统高对比模式或完整设备矩阵，不能当作完整 WCAG 合规结论。

Ant Design CLI 保留 2 个关闭虚拟滚动的性能提示，分别对应固定 5 项的配色选择器与固定 2 项的观察方法；不用于大数据集。构建最大 JS 块约 355 kB / gzip 120 kB。没有修改平台 API、执行状态机和证据隔离逻辑。

本轮截图、创建页截图与逐状态对比度 JSON 位于 `artifacts/palettes/`，属于本地验证产物；通过浏览器测试可重新生成。
