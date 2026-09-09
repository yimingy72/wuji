# Phase 1A 后续集中测试清单

- 状态：deferred；2026-09-09按用户要求停止重复测试。
- 执行模型：后续 `gpt-5.6-luna / xhigh`，主代理分工和验收；当前没有启动新测试代理。
- 约束：[精简测试与停止条件](../../../AGENTS.md#精简测试与停止条件)。默认共享10分钟，同类脚本问题最多两轮定向排查。
- 当前完整验收保持partial；`master`不因此标记为Phase 1A已验收基线。

## 已有证据，直接复用

被测试提交：`f337ef3d4b7d4a5f8aee569152e09ba06383aa4e`。正式run：`p1a20260909t143035156a02`，由独立SOL/high代理执行。

| 范围 | 实际结果 |
| --- | --- |
| 冻结安装、check:platform、正式构建 | exit 0；契约26、API unit 11通过 |
| API | 73/73通过，无失败/跳过；含租户隔离、权限、会话竞争及同run故障恢复 |
| 生命周期 | 6/6通过，87.61秒；含归属、端口、信号、清理和并发转发 |
| Chrome | 12/15通过；剩余3项如下 |
| test:platform整体 | exit 1，不能写成完整通过 |

证据在测试工作树 `work/worktrees/phase-1a-test/artifacts/phase-1a/independent-final/f337ef3d4b7d4a5f8aee569152e09ba06383aa4e/commands/` 及同树 `artifacts/phase-1a/platform/p1a20260909t143035156a02/`。这些ignored文件只保存在本机，不含在Git交付中。环境明确区分系统Node25.3.0与项目Node24.20.0。

## 当前待测项

三个用例均在 `tests/platform-browser/01-keycloak-auth.spec.ts`，共享 `captureKeycloakCallback` 辅助函数，实际结果为45秒超时，尚未验证通过。

| ID | 场景与通过标准 | 批次 |
| --- | --- | --- |
| CB-01 | 错误浏览器不能消费有效state；持有握手Cookie的浏览器仍能完成真实Keycloak回调 | A，串行 |
| CB-02 | 新握手替代旧绑定；旧回调失败，新回调成功 | A，串行 |
| CB-03 | 同一真实Keycloak回调并发只成功一次，重放失败 | A，串行 |

先只复现CB-01，读取trace的before/log/after和真实网络请求，确定实际等待点，再修helper。此前对“evaluate本身未返回”的推断未得到充分证据：310925定向trace中该调用已经存在完成after事件，不能继续沿用该假设反复尝试。真实Code+PKCE、Cookie绑定和服务端请求保留，不用伪造回调绕过认证。

未验证的noWait草案保留在分支 `codex/phase-1a-test-callback-nowait`，提交 `56ced109431cb58b712d49cec0e6c70a3b84beeb`；只做过serve-only启动/清理，未集成到主阶段，也不能称为修复通过。另310925的定向运行 `p1a20260909t143921831e0d` 为2项超时、1项中止，失败证据保留。

## 后续执行边界

1. 分配一名Luna/xhigh负责批次A，使用正式 `scripts/platform/test-platform.sh --serve-only` 准备环境；同一固定端口环境只有一个负责人。
2. 只执行上述3项：`pnpm exec playwright test --config playwright.platform.config.ts --grep 'wrong browser|new browser binding|same Keycloak callback'`，使用该run生成的绝对 `WUJI_TEST_RUN_FILE`。先让单项通过，再跑3项；不先重跑73个API或6个生命周期。
3. 产品源码未变时，复用已有通过证据并注明SHA。批次失败达到两轮或预算耗尽后停止、清理、更新本清单，不转移给新代理继续相同循环。
4. 后续集中验收窗口如需全量，只在已知阻塞解决后执行一次。正常路径、故障恢复和环境边界不因测试helper修改反复重跑。
5. 大批量任务按后续模块逐步加入队列，最多3名测试代理并行处理互不干扰的任务；数据库断网、Pod重建、API配置切换、共享身份撤权等串行执行。

## 本轮收尾

测试代理已清理归属明确的本地进程。最后run `p1a20260909t144329fd7c1e` 的cleanup_complete为SIGTERM/143，六个测试端口已释放；DB、realm和证据保留。本轮不再启动全量测试，也不以待测项冒充完整验收。
