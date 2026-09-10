# B2/B3 验收

- 实施：complete；B2/B3主流程最小验收通过，扩展验证保留待测。
- 实测业务候选：`e76a265d445ae9548d7f56fdb85f9b8b5c005759`；run_id：`p1a20260910t0159448786fa`。
- 开发基准60f6544，用户批准后连续实施B2/B3。
- 总测试/构建/启动等待/排查预算600秒。检查准备约44.12秒；将01:59:41–02:08:38 UTC整个环境启动、独立执行、协调等待、脚本定位与清理窗口保守计538秒，合计约582秒。已停止追加测试，不以等待或代理切换重置预算。
- Phase1A仍为partial，master仍为`28fcd44eebc205a35735d3e7b60a308ce5f749bc`。本记录不宣称集中扩展验证或完整Phase1验收通过。

## 交接记录

Spec/Plan基准235f05f；主集成codex/phase-1b-b23使用原phase-1b独立工作树，主工作区继续运行60f6544。A/T使用独立phase-1b-b23-server/test树；A先行契约b73ec54集成为f1681ba，事件首读ea72081集成为a3c5feb，B从f1681ba建独立web树。开发SOL/xhigh、独立测试Luna/xhigh均已成功启动，没有模型替换。

所有新树未建CodeGraph索引，使用rg和直接读取；主树已核对索引归属/新鲜度，交付集成后sync。仅toolchain及缓存复用，node_modules与Python虚拟环境各树独立。

## 实测与证据

|检查|执行者/命令|退出码|实际结果|
|---|---|---|---|
|契约|主代理：`pnpm contracts:check`，提交09cc6e9|0|生成一致、OpenAPI有效；保留2个OIDC重定向提示和未使用After参数提示；后续未改契约，复用此证据|
|正式构建|主代理：`pnpm build:platform`|0|5390b5f为4.84秒；去除重复提示后e76a265为3.76秒；未再重跑|
|API|Luna/xhigh：`./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_tasks.py -q`|0|6/6，12.65秒；真实角色/数据库、创建取消回执、同键并发、拒绝边界及事件分页|
|浏览器初次|Luna/xhigh：`WUJI_BROWSER_CHANNEL=chrome pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/06-task-management.spec.ts --workers=1`|1|实际业务已完成，末尾宽泛定位匹配3个文本而失败，不能计为通过|
|浏览器定向复跑|同上，仅该文件|0|1/1，8.9秒；丢失已提交响应→刷新按原键核对→列表/详情→取消与权威快照version2|
|隔离环境|正式`test-platform.sh --serve-only`，显式run-file/event-file|143|增量迁移0003、seed、ready通过；主代理核验supervisor PID/启动标记/命令/进程组后SIGTERM，cleanup_complete，保留DB/realm|

API/浏览器均使用集成树绝对`WUJI_TEST_RUN_FILE`，没有更换产品候选。浏览器脚本定位修正868d477与唯一名称夹具9ea345c由测试代理提交，root在保持HEAD=e76a265时精确同步脚本再复跑；停止服务后才正式集成为bc75cac/46036d3。因此被测业务SHA和测试脚本SHA明确分开。独立原始报告见[b23-independent-test.md](b23-independent-test.md)。

主代理审阅迁移/RLS、用户锁、权限投影、命令摘要/重放顺序、同事务事件、快照游标以及前端存储和请求隔离，并亲自查看真实最终截图：取消状态、版本2、Scope版本1以及两条创建/取消记录。最终截图页脚v0.3单独同步v0.4，属于不改变行为的文案修正，复用上述业务证据。

本机证据位于集成树`artifacts/phase-1b/b23/`（构建日志/JSON）及`artifacts/phase-1a/platform/p1a20260910t0159448786fa/`（沿用生命周期目录名，含Playwright JSON与b23-task-management.png），事件在`work/run/b23-events.jsonl`；均不含于Git。测试未访问目标，未调用模型、Runtime或执行工具。

## 交付与剩余范围

开发工作台按旧版本dev:down→集成代码→缓存冻结准备→dev:infra→dev:seed→dev:platform交付，保留既有身份、Scope和数据。实际交付SHA及就绪结果写入主工作区ignored的`artifacts/phase-1b/b23-development-delivery.json`，不在此预写记录提交自身SHA。启动说明见[本地工作台](../../local-development.md)。

游标过期专项、额外撤权竞争、存储失败、项目切换/可见性延时矩阵、完整主题和压力留到[集中测试清单](b23-deferred-tests.md)。任务只queued/cancelled；Runtime、实际HTTP执行、证据和Agent属于后续阶段，尚未实现。
