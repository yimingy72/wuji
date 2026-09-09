# 开发基线独立测试报告

- 报告状态：`complete`；独立测试工作完成，阶段验收仍由主代理复核
- 测试日期：2026-09-09
- 任务：BASE-03
- 独立测试执行者与模型：独立测试子代理，`gpt-5.6-sol` / `reasoning_effort=high`
- 被测试产品代码提交 SHA：`a5d462e5b566a8e84bcbe7d40e80663b90675ac6`
- 指南/模板复核 SHA：`9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece`
- 最终 Phase 1A 草案/导航复核 SHA：`81ba4ada1e0360d4e4d08c83a73481b92d4966a7`
- 分支：`codex/development-baseline-tests`
- 独立 worktree：`/Users/yym/Documents/ChatGPT/Wuji 自动化渗透平台/work/worktrees/baseline-tests`

文档提交 `9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece` 相对被测试产品提交只修改开发指南和 Acceptance 模板；`81ba4ada1e0360d4e4d08c83a73481b92d4966a7` 再只修改 README、开工文档、本阶段 Plan 并增加 Phase 1A 三份文档。两次都没有修改运行源码、测试、配置、契约或锁文件。因此产品命令仍绑定 `a5d462e5b566a8e84bcbe7d40e80663b90675ac6`；文档结论分别绑定对应文档提交，不把这些 SHA 混写成同一被测对象。

## 环境

| 项目 | 实际值 |
| --- | --- |
| 系统 Node | `v25.3.0` |
| 项目 Node | `v24.20.0`，由 `pnpm exec node --version` 确认 |
| pnpm | `10.32.1` |
| 浏览器 | Google Chrome `153.0.8010.36` |
| Playwright 服务 | `127.0.0.1:4175`，`reuseExistingServer: false`、`strictPort` |
| 评审服务 | `127.0.0.1:4173`，测试前后均由 PID 27676 监听，未停止或复用 |
| CodeGraph | 当前测试 worktree 无 `.codegraph/`，按约定回退 `rg` 与直接读取；未使用主工作区索引 |
| Docker Desktop | Docker context `desktop-linux`；客户端/服务端 `29.7.2` |
| 本地 Kubernetes | context `docker-desktop`；节点 `docker-desktop` Ready；客户端/服务端与 kubelet 均为 `v1.36.1` |
| 开发存储/Helm | 默认 `hostpath` StorageClass（`docker.io/hostpath`）；Helm 未安装，草案使用 kubectl 内置 Kustomize |

## 命令结果

| 顺序 | 命令 | 退出码 | 结果 |
| --- | --- | ---: | --- |
| 1 | `pnpm install --frozen-lockfile` | 0 | 锁文件无需解析变化；依赖冻结安装成功 |
| 2 | `pnpm exec node --version` | 0 | 输出 `v24.20.0`，系统 Node 25 未改变项目工具链 |
| 3 | `pnpm check` | 0 | 生成 TypeScript 契约与 OpenAPI 一致；OpenAPI 有效；Vitest 1 个文件、21/21 测试通过；TypeScript 检查通过 |
| 4 | `pnpm exec antd lint spikes/frontend/src --format json` | 0 | 2 条 performance warning，0 deprecated、0 a11y、0 usage、0 skipped，扫描不是 partial |
| 5 | `pnpm build` | 0 | TypeScript 与 Vite 生产构建通过；转换 3146 个模块；最大输出块约 355.25 kB / gzip 120.40 kB |
| 6 | `WUJI_BROWSER_CHANNEL=chrome pnpm test:e2e` | 0 | Chrome 上 12/12 用例通过；结束后 4175 无监听 |

Playwright 会在启动时清理 `test-results/`，第一次执行时其中的前序命令日志随之删除。为保留稳定证据，在产品代码未变化的前提下按相同顺序复核一次，并把日志保存到不会被 Playwright 清理、且被 Git 忽略的 `artifacts/base03/`；两次产品检查结果一致。

Ant Design 两条提示均为显式关闭 Select 虚拟滚动：

- `spikes/frontend/src/main.tsx:45`：配色选择器固定 5 项。
- `spikes/frontend/src/pages/CreateTask.tsx:35`：观察方法固定 GET / HEAD 2 项。

两条均为小列表的已知性能提示，没有扩展阈值、删除检查或修改测试预期。

## B01–B08 独立核查

| ID | 独立结果 | 证据与限制 |
| --- | --- | --- |
| B01 | `passed` | `50f194a641b322a0e918f895f72d78ae93ee57c1` 保存首次 50 文件快照，`a5d462e5b566a8e84bcbe7d40e80663b90675ac6` 保存阶段指南/模板与约定的空行清理。被测产品 SHA 有 54 个跟踪文件，写入本报告前工作区干净；跟踪路径中没有依赖、构建、测试、运行产物、环境文件、私钥或 CodeGraph 索引；高置信凭据模式扫描为 0。仓库本地身份为 `Wuji Development <wuji-dev@localhost>`，未配置远端。 |
| B02 | `passed` | AGENTS.md、开发指南中的主代理职责、SOL/xhigh 开发代理、独立 SOL/high 测试代理、并发、授权、分支/worktree、本地 Git 和失败处理规则一致。README 与开工文档明确尚无平台后端、Runtime 部署或平台运行验收。文档提交 `9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece` 补充一次批准可同时覆盖同阶段 Spec/Plan，并消除验收文档回填自身 SHA 的要求；只读 diff 复核通过。 |
| B03 | `passed` | 本任务按 SOL/high 独立执行；分支、绝对 worktree 和产品 SHA 均与任务书一致，未拆分子代理，未修改产品代码、契约、锁文件或测试预期。 |
| B04 | `passed` | Spec、Plan、Acceptance 三种模板均覆盖真实状态、范围/非目标、决策、依赖/顺序、分工/owner、验证入口、证据、被测代码 SHA、复测和主代理复核。当前阶段已有 approved Spec 与 in-progress Plan。`9fc1b5a4` 后 Acceptance 模板通过 Git 历史追溯自身提交，不要求文档预知自身 SHA。 |
| B05 | `passed` | 固定 Node 24.20.0 / pnpm 10.32.1 完成冻结安装、契约生成一致性、OpenAPI lint、21 项契约测试、类型检查和构建；全部退出码为 0。 |
| B06 | `passed` | Chrome 153 上 12 项浏览器用例全部通过，服务端口为 4175；测试前后 4173 评审服务保持同一 PID 监听。 |
| B07 | `not-tested` | 独立部分已完成：源码/跟踪清单/忽略规则检查通过。最终文档提交的 24 个 Markdown 中检查 94 个本地链接，79 个在提交树中可解析；其余 15 个全部是 `docs/phase0-validation.md` 指向被 Git 忽略的截图。当前测试 worktree 已重新生成其中 10 个 `workbench-current` / `palettes` 产物，只有 5 个早期 `artifacts/phase0/*.png` 不存在；该文档第 31 行已明确新检出仓库中链接可能不存在，截图不是单独证明。新增 Phase 1A 与导航链接均有效。B07 仍要求主代理复核关键契约和至少一条交互证据，独立测试者不代替该复核，因此整体不标记通过。 |
| B08 | `passed` | `81ba4ada1e0360d4e4d08c83a73481b92d4966a7` 中 Phase 1A Spec 为 `draft` 且批准依据为无，Plan 为 `draft` 且明确尚未批准实施，Acceptance 为 `not-tested` / `pending` 且被测业务代码 SHA 为无。README、开工文档与开发基线 Plan 将该草案和当前基线分开，后端、Runtime、Harness、数据库/身份部署及 P1A-01–10 均保持未实现/未测试。只读环境检查确认草案所述 docker-desktop Kubernetes `v1.36.1` 节点 Ready、默认 hostpath StorageClass 存在；Helm 未安装与使用 `kubectl apply -k` 的方案一致。 |

## 样本与真实平台边界

Vitest 的 21 项检查验证 OpenAPI/生成类型一致性、共享 JSON 夹具、严格输入、终态执行约束、命令接受语义、预览阻断、证据预览上限，以及写操作声明 Session + CSRF；这些测试不能证明后端已实现或实际执法。

Playwright 的 12 项检查只针对本地内存原型和 `127.0.0.1:4175` 静态服务，覆盖创建/预览、取消等待回执、惰性证据文本、未知执行/清理中/拒绝状态、深链接、键盘入口、窄窗口、工作台关系、五套主题可读性与主题持久化。外部请求拦截用例确认该本地样本没有访问其他 origin。本轮未访问真实测试目标、平台执行端或真实模型 API。

这些结果不验收真实会话/CSRF 执法、租户/项目隔离、数据库约束与并发幂等、SSE/Outbox、Runtime 生命周期、受控出口/断流、清理、模型 Harness、生产部署、完整可访问性或性能容量。相关项目必须继续保持未完成，不能由原型测试替代。

## 证据

忽略目录中的稳定证据根路径：

`/Users/yym/Documents/ChatGPT/Wuji 自动化渗透平台/work/worktrees/baseline-tests/artifacts/base03/`

- `00-summary.log`：六个规定命令的退出码汇总。
- `01-pnpm-install.log` 至 `06-playwright-chrome.log`：按规定顺序保存的命令输出。
- `07-environment.log`：被测 SHA、分支、Node/pnpm/Chrome、CodeGraph 与端口记录。
- `08-static-review.log`：Git 跟踪/忽略、凭据模式、Markdown 本地链接和文档 SHA 差异清单。
- `09-final-doc-review.log`：最终草案状态、提交树链接和 Docker Desktop / Kubernetes 只读核查。
- `../workbench-current/`：代表性流程截图。
- `../palettes/`：五套主题截图和逐状态对比度 JSON。

本报告只提供独立测试事实。阶段是否 accepted、关键契约及代表性交互证据是否满足最终验收，由主代理在绑定最终集成 SHA 后复核。
