# B1 Plan：首批实施任务

- 状态：in-progress；用户明确批准 Plan 模式最终方案，按本计划实施。
- 对应：[B1 Spec](b1-spec.md)。主代理负责决策与集成，开发使用 SOL/xhigh，独立测试使用 Luna/xhigh。
- 本计划沿用本地 Docker Desktop 集群及固定端口；当前主工作树运行 Phase 1A，本次评审在独立工作树进行，不修改其 HEAD 或运行记录。

## 1. 已固定实现方案

复用 FastAPI、SQLAlchemy/psycopg、Alembic、现有 project/auth 两个运行角色、React/Ant Design 和生成校验器。Scope 作为 API 内模块实现，不拆新服务，不换 HTTP/URL 第三方依赖，不修改集群清单或私有 run-file schema。

新增 `scope_policy.py` 放纯输入规范化、策略计算、摘要；`scopes.py` 放 DTO、存储与路由服务。现有 DatabaseAuthority 继续管理连接和身份；新业务通过显式的受限事务上下文访问 project engine，不复制认证实现。抽取权限投影供项目列表、详情和预览共同使用，替换当前硬编码 `permissions=["project.read"]`，保留项目游标既有格式。

契约固定为0.3.0：新权限和 blocker、预览 Session+CSRF、500错误、精确登录回跳路由，以及生成的 validateApprovedScope、validateScopePage、validateTaskPreview。预览删除没有实际语义的409/410；Scope列表保留游标410。阶段状态 Schema 同时增加 egress_state=not_granted，terminal允许not_granted或revoked，以便B2如实描述从未授权执行的任务。生成器同时维护 JS 和 d.ts 导出；同步 schemaId、包版本和相关版本断言，不手改生成文件。既有快照/夹具只作必要兼容修订，不增加全量安装或测试要求。

新增单一 Alembic 迁移，编号在分派时由 A 根据实际 HEAD 确定。当前唯一 revision 为 `20260909_0001`，同步 API EXPECTED_REVISION、初始化权限与 seed；不能只加表而让健康检查继续期待旧版本。Scope 管理导入复用 manage.py 及 database_admin.py 的受信事务和错误处理。

## 2. 任务归属与依赖

| 任务 | 负责人 | 允许修改范围 | 交付条件 |
| --- | --- | --- | --- |
| B1-A1 契约与服务端 | SOL/xhigh A | packages/contracts、scripts/generate-contracts.mjs、apps/api；必要 scripts/platform 接线；全部 manifest/锁文件/迁移/根命令 | 完成三表、管理导入、范围/预览API、角色权限、后端回跳及响应生成物，提交固定 SHA |
| B1-B1 页面接入 | SOL/xhigh B | apps/web 非 manifest 源码；必要 packages/theme/src 组件样式 | A1 契约集成后实现入口、分页 Scope 选择、表单、真实POST校验、回跳和迟到响应隔离 |
| B1-T 必要验证 | Luna/xhigh 独立测试 | tests/unit/test_scope_policy.py、tests/api/test_phase1b_scopes.py、tests/platform-browser/05-scope-preview.spec.ts、B1测试记录 | 对固定集成SHA执行精简用例；不改产品或公共契约 |
| 集成与验收 | 主代理 | 阶段文档、冲突与交付记录 | 审查权限/契约/纯函数与真实页面证据；不以测试代理声明代替验收 |

A/B 不共享写入文件；前端可以先读布局，依赖 A1 的代码开发等待公共契约。测试可以先从 Spec 列断言，执行等唯一候选固定。不在 B1 夹带创建/取消、调用账本或执行器代码。

## 3. 验证命令与停止条件

以下是开发后要执行的入口，本次评审未运行。先确认依赖存在；只有依赖实际变更或缺失时安装。10分钟为所有代理共享的累计测试、等待、脚本排查与复跑预算；不得通过分批重置同一问题的预算。

1. 契约有变化时执行一次 `pnpm contracts:check`；纯函数执行 `./scripts/uv.sh run --frozen pytest tests/unit/test_scope_policy.py -q`，输入向量限制在 Spec 列表。
2. 前端完成后执行一次 `pnpm build:platform`；相关代码未再变化时不重复构建。
3. 独立测试使用 `./scripts/platform/test-platform.sh --serve-only` 的正式准备路径，设置其生成的绝对 `WUJI_TEST_RUN_FILE`；只运行 `./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_scopes.py -q` 与 `pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/05-scope-preview.spec.ts --workers=1`。
4. 同一环境串行完成四类API检查和一次页面预览；退出后清理自有测试进程，保留数据/证据。不启动 `pnpm test:platform`、生命周期故障注入或旧回调专项。
5. 任一测试脚本同类问题最多两轮；耗尽预算/轮次则停下记录场景、命令和证据。产品缺陷定向修复，复测只覆盖受影响项，未验证不记为通过。

后续集中队列仅保存扩展URL编码/IPv6输入组合、50条以上Scope翻页边界、反复权限切换与迟到预览、全部主题视觉细节，不为这些场景延长首批开发收口。

## 4. Git 与运行交付

评审通过并进入获准实施模式后，从固定基线创建 `codex/phase-1b`；A/B 分别使用独立 worktree。主代理集成后的候选才启动测试，报告绑定实际 SHA；只改文档不用重跑产品。

切换本机正式工作台到 B1 前先用现有 dev:down 停止归属明确的旧开发进程，完成集成，再执行 dev:infra、dev:seed、dev:platform；这属于正常开发启动，不删除已有业务数据。master 在完整验收之前仍保留原已验收基线。当前阶段没有启动上述操作。
