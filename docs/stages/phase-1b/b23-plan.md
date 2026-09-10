# B2/B3 Plan

- 状态：complete；用户明确批准实施，起点60f6544。B2/B3最小验收通过，扩展验证另列待测。
- 规范：[b23-spec.md](b23-spec.md)。本计划不重新审批B2到B3的内部交接。

## 分工与顺序

|角色|模型|所有权|交付|
|---|---|---|---|
|A|gpt-5.6-sol/xhigh|apps/api、所有契约/生成器/manifest/锁文件/迁移、必要scripts/platform|先0.4契约，再任务/回执/事件全部服务端；唯一迁移0003|
|B|gpt-5.6-sol/xhigh|apps/web/src及必要theme/src，不改manifest|契约交接后真实页面、命令客户端、sessionStorage恢复、事件轮询|
|T|gpt-5.6-luna/xhigh|新B23测试、直接变化B1预期、独立验收记录|先按Spec备最小用例，固定候选一次执行；不改产品|
|主代理|当前主模型|阶段文档、集成、差异审阅、运行交付|约束接口，处理实质决策，最终验收|

主集成使用codex/phase-1b-b23；A/B/T使用独立codex/phase-1b-b23-*和worktree，无CodeGraph索引时直接rg，不复制主树索引。已有主工作区4180保持60f6544运行；只有交付时停止后更新HEAD。

公开契约先行提交后B开始接线。A独占版本/锁文件与0003，执行时检查已有CHECK名称后精确替换，保留全部现有业务数据。主代理审阅代码期间T不启动集群。所有代理完成后报告实际SHA（git rev-parse）、改动、实际检查秒数；未收到root允许不要退出上下文，避免代理恢复限制。

实施核对：现有change_membership与bump_permissions_version未使用用户锁；A在其写事务开始处补_lock_user，与set_user_enabled及新命令锁保持同一顺序，落实已批准的撤权协调要求。

主代理接口收口：详情需要读取已有状态变更，但快照只返回尾部游标，因此events允许省略after从位置0有界读取初始历史；有after时原增量语义不变。A同步操作级参数与描述，B以历史事件展示而非伪造记录，T使用limit=1验证补页。

## 验证预算与命令

所有B2/B3开发、测试共用600秒。A/B各预留60秒，T执行预留360秒，主代理集成及启动预留120秒；只按实际用时累计，不按代理/轮次重置。构建主代理统一一次，A/B不重复全量检查；Ant Design按技能必要info/lint限定改动路径。依赖仅缺失或版本变动时冻结安装，复用本机toolchain缓存，node_modules/.venv各树独立。

- 一次`pnpm contracts:check`和`pnpm build:platform`。
- 定向`./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_tasks.py -q`。
- 使用正式`test-platform.sh --serve-only`创建一个隔离run；设置绝对WUJI_TEST_RUN_FILE和WUJI_BROWSER_CHANNEL=chrome。
- 一条`pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/06-task-management.spec.ts --workers=1`。
- T可以编写与持久化无关的少量命令存储单测，仅在无法由上述真实主链覆盖的直接风险需要时加入预算；不扩展测试数量。
- 原B1预览/权限/revision预期精确更新，不重跑Phase1A全量、生命周期或pure未变矩阵。报告失败按实际日志最多两轮定向排查；达到预算记录待测，不转移代理继续相同循环。

## 交付

固定候选再测，测后停止归属明确的test supervisor保留数据证据。文档提交与被测SHA分别记录；两路完成后由root统一提交记录。保持master先前基线，Phase1A partial不冒充accepted。主树停止旧dev→切换集成代码→必要冻结依赖→dev:infra→dev:seed→dev:platform，就绪确认；CodeGraph集成后sync。运行时不再改主树HEAD。同期更新architecture/predevelopment/frontend/contract陈旧状态，用户页面不写内部实现说明。
