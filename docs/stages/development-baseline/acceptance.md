# 开发基线验收记录

- 测试状态：`passed`，仅针对本阶段 B01–B08
- 阶段结论：`accepted`
- 日期：2026-09-09
- 对应：[Spec](spec.md)、[Plan](plan.md)、[独立测试报告](independent-test.md)
- 被测试产品代码 SHA：`a5d462e5b566a8e84bcbe7d40e80663b90675ac6`
- 指南/模板复核 SHA：`9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece`
- Phase 1A 草案/导航复核 SHA：`81ba4ada1e0360d4e4d08c83a73481b92d4966a7`
- 验收前集成候选 SHA：`e85a95c5d37d2e2ce0e79f547117779577ee7061`
- 独立测试：`gpt-5.6-sol` / `high`；最终验收：主代理

集成候选与被测产品 SHA 的差异全部为 Markdown；运行源码、配置、契约、锁文件及测试完全一致。本文及完成状态导航作为后续文档提交，不冒充重新执行产品测试。验收记录自身提交使用 `git log -- docs/stages/development-baseline/acceptance.md` 查询。

## 结果与证据

| ID | 结果 | 证据 |
| --- | --- | --- |
| B01 | `passed` | 首次快照 `50f194a641b322a0e918f895f72d78ae93ee57c1`；显式文件清单及凭据模式扫描无发现；依赖/运行产物/密钥/本机索引被忽略；本地身份 `Wuji Development <wuji-dev@localhost>`，无远端 |
| B02 | `passed` | 根 AGENTS、开发指南、阶段模板的模型、职责、并发、授权及 Git 规则一致；未声称后端或 Runtime 已实现 |
| B03 | `passed` | BASE-02 开发实际使用 SOL/xhigh；BASE-03 为独立 SOL/high；两个任务使用独立上下文及 worktree；另有 SOL/xhigh 只读调研，不修改代码 |
| B04 | `passed` | Spec/Plan/Acceptance 模板及当前具体阶段文档均存在；主代理修正验收文档自身 SHA 循环引用问题 |
| B05 | `passed` | Node 24.20.0 / pnpm 10.32.1：冻结安装、生成契约一致性、OpenAPI、21/21 Vitest、类型与构建通过；Ant Design lint 退出码 0，保留两条已知提示 |
| B06 | `passed` | 独立 Chrome 153.0.8010.36 / 4175 浏览器用例 12/12；评审服务 4173 前后仍由 PID 27676 监听 |
| B07 | `passed` | 独立静态审查 + 下述主代理关键契约/交互复核完成；新增文档链接有效；历史截图不纳入 Git 的限制明确保留 |
| B08 | `passed` | Phase 1A Spec/Plan 明确为 draft，验收为 not-tested/pending；实际 docker-desktop 环境已核实；P1A-01–10、后端/Runtime/Harness 保持未完成 |

独立测试报告原始提交 `282398f6f56377c9eb72f7ccf58f82c966f4b94b` 与措辞修正 `3f5dc43a8d0af231027f0726fe31f6e895662ed8`，分别集成为 `51de5b3b6114d6e7a03c40f20f05c2ca76da3d1c` 和 `e85a95c5d37d2e2ce0e79f547117779577ee7061`。独立报告保留 B07 的主代理门槛，由本文补充验收，不改写测试者结论。

开发工作树为 `work/worktrees/baseline-workflow`（分支 `codex/development-baseline-workflow`），测试工作树为 `work/worktrees/baseline-tests`（分支 `codex/development-baseline-tests`），均位于主仓库下的 ignored 目录。分支保留供追溯。

## 主代理复核

关键契约复核确认：OpenAPI 0.1.0 明确为设计基线；写操作声明 Session + CSRF；命令接受回执不能代表执行已完成；终态要求活动/未知调用为零、出口已撤销且无可用操作。这些约束目前由 Schema 和内存原型演示，尚无后端执行证据。

主代理在被测 SHA 的已构建原型上单独启动 4176，使用 Chrome 153、1440×1000 视口执行并查看截图：

1. 取消请求后保持“取消中”，没有提前显示“已取消”。
2. 雾银切换为冰蓝时，取消状态保持。
3. 单独触发模拟停止回执后，才显示“已取消”和“已清理”。
4. 进入完整证据页，脚本/图片标记仍为惰性文本；0 外部 origin，0 pageerror。

复核结果位于本机 ignored 的 `artifacts/development-baseline/root-review/result.json`、`cancel-pending.png`、`evidence-glacier.png`。独立测试的命令日志位于 `work/worktrees/baseline-tests/artifacts/base03/`，截图及配色对比度结果位于其相邻的 `workbench-current/` 和 `palettes/`。4176 复核服务已停止，4173 评审服务保留。

主工作区已有 CodeGraph 索引已同步，`cancelDemoTask` / `stopDemoTask` 查询能返回当前源码；测试工作树无索引，按约定使用 rg/直接读取。CodeGraph 对 YAML/测试定位未给出所需源码时回退直接读取，未将“未发现覆盖测试”提示当作实际无测试。

本机只读检查再次确认：Docker context `desktop-linux`；Kubernetes context/node `docker-desktop`，v1.36.1、Ready=True；默认 hostpath StorageClass 存在。记录位于本机 `artifacts/development-baseline/root-review/environment-and-git.json`。Phase 1A 将复用现有集群，通过 kubectl Kustomize 管理自身开发依赖。

## 修正与复核范围

| 问题 | 修正 | 复核 |
| --- | --- | --- |
| 初次差异检查发现 model.ts 多余末尾空行 | `a5d462e5b566a8e84bcbe7d40e80663b90675ac6` | 仅删除一个空行；之后全部产品检查通过 |
| 模板要求回填自身提交 SHA，会产生自引用 | `9fc1b5a4ee0963e225cd8b2aa2f2bf10a2f0eece` | 开发者修正、独立测试者和主代理复核；无产品变化 |
| 环境发现不足可能误判 Kubernetes 不存在 | `81ba4ada1e0360d4e4d08c83a73481b92d4966a7` | 主代理与独立测试者实际查询节点 Ready；草案复用 docker-desktop |
| Helm 的 PATH 检查不能证明未安装 | `e85a95c5d37d2e2ce0e79f547117779577ee7061` | 测试者收窄报告措辞；主代理复核两处文档差异 |

## 剩余限制与阶段结论

- 两条 Ant Design 提示来自固定 5 项配色与 2 项观察方法的 Select 禁用虚拟滚动；未放宽检查规则。
- 旧验证文档的 15 张截图属于 ignored 运行产物。测试工作树重新生成其中 10 张，5 张早期截图缺失；主工作区本机仍有这些旧截图。干净检出不保证这些链接存在，不能把历史截图当作本次测试证据。
- 本轮在 macOS/Chrome 完成验证，未执行 Linux CI 或生产部署；完整无障碍、容量与性能验收未完成。
- Kubernetes Ready 不证明 PVC 重建持久性、NetworkPolicy 执法、受控出口或 Runtime 清理；本轮未部署数据库、Keycloak 或平台资源。
- 本轮通过的是开发基线和现有原型检查，不代表 80 个架构场景或 Phase 1A–4 已完成。正式后端、身份、数据库、任务执行、Harness 集成仍待各阶段实施。

B01–B08 有独立证据及主代理复核，开发基线接受；本验收与完成状态文档提交后快进合入本地 master。Phase 1A 下一步为具体 Spec / Plan 评审，草案不自动启动业务开发。
