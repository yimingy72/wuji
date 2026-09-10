# Phase 1B 验收记录

B1与B2/B3均已开发完成并通过各自最小功能验证；最新任务/命令/事件结果见[B2/B3验收](b23-acceptance.md)。扩展场景仍待集中验证，Phase 1A 的三个回调延期项独立保留，master不因此前移。下文保留B1当时的历史证据与范围。

- 实测候选：`55bf6bd3c5c0370b017b879e098772843932e467`。
- run_id：`p1a20260909t16282154d284`；私有 schema v1，隔离数据库/realm，Docker Desktop Kubernetes `wuji-test`。
- 代码：服务端 `3b5725d26041bf66d84887bce243c218551eca0b`，前端 `9c077f0e8834adfec08380011cf6ae10318b520b`；公共契约 0.3.0。
- 开发：两名 SOL/xhigh；用例初稿 Luna/xhigh。协作工具拒绝恢复/新建测试代理（agent thread limit reached），接口对齐和实际执行由主代理完成，不能称为独立代理执行验收。

| 检查 | 命令 | 退出码 | 结果 / 耗时 |
| --- | --- | --- | --- |
| 契约 | `pnpm contracts:check` | 0 | 生成一致、lint通过，3.16秒；保留登录重定向的2个2XX提示 |
| 纯函数 | `./scripts/uv.sh run --frozen pytest tests/unit/test_scope_policy.py -q` | 0 | 6/6，6.07秒 |
| 正式构建 | `pnpm build:platform` | 0 | TypeScript/Vite通过，4.70秒；保留大chunk提示 |
| 真实 API | `./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_scopes.py -q` | 0 | 4/4，10.73秒 |
| Chrome | `pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/05-scope-preview.spec.ts --workers=1` | 0 | 1/1，6.68秒 |
| 环境 | `./scripts/platform/test-platform.sh --serve-only --run-file-out "$PWD/work/run/b1-candidate.json" --event-file "$PWD/work/run/b1-events.jsonl"` | 143（主动SIGTERM） | 正式路径完成迁移/seed/就绪；测试完成后清理自有进程，保留数据库和realm，报告ok=true |

API/浏览器均设置当前树绝对 `WUJI_TEST_RUN_FILE`；Chrome设置 `WUJI_BROWSER_CHANNEL=chrome`。API覆盖合法规范化与限额收紧、排除路径、跨项目绑定404、Viewer403和缺少CSRF403。浏览器从实际Scope读取目标，使用真实Keycloak登录及接口，断言唯一阻断项为CREATION_UNAVAILABLE。主代理查看预览截图并核对权限投影、存储/契约一致性；没有访问测试目标。

证据在集成工作树 ignored 的 `artifacts/phase-1b/checks/*.log` 与 `artifacts/phase-1a/platform/p1a20260909t16282154d284/`（沿用生命周期目录名）；包括 Playwright JSON 与 `b1-scope-preview.png`。生命周期事件在 `work/run/b1-events.jsonl`。证据路径包含phase-1a不代表重跑该阶段测试。

预算按所有代理共享600秒：开发A检查8.62秒、B检查6.70秒，主代理五项检查31.34秒；另计依赖准备、启动/清理及排查等待。本批最小检查通过即停止，没有全量回归或故障注入。首次前端构建的3个类型错误已修复，由上述集成构建覆盖；没有反复修改测试脚本重跑。

## 延期与实际限制

- 管理导入相同版本重放/变更拒绝、授权到期/撤销、Scope 50条以上翻页、扩展IPv6/编码矩阵：源码已审查，尚无专项实测。
- 权限反复变化、迟到成功/失败响应、五主题全部视觉细节：已实现隔离与保留主题，扩展自动化待集中执行。
- 上述队列交后续 Luna/xhigh 按批验证，沿用600秒预算与共享环境单一负责人，不再延长B1收口。入口分别为管理CLI、纯函数测试、API文件和浏览器文件；用例准备前不得声称已有通过证据。
- 任务创建/取消、命令账本、事件、Runtime和Agent不在B1实现范围。
- 后续仅表单必填标记和重复文案调整不触及行为，依照精简约束复用候选证据；记录与文案提交不冒称已在上述SHA运行。

本地使用见[启动与Scope导入说明](../../local-development.md)。

展示修正来自47e5e5756a316b71f7727a61ad734ebc0592886b，集成为57a8222，仅删除optional标记和重复description。开发工作台切换就绪证据保存于主工作树ignored `artifacts/phase-1b/development-delivery.json`；此文件绑定实际交付SHA，不提交运行凭据。
