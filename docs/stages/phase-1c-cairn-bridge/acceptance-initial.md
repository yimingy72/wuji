# Task / Cairn 桥接验收

- 代码状态：已交付；阶段验收：partial / verification pending。
- 日期：2026-09-11；基准7cfcf386ca0d0388b039d60a941bc2812e118d5a。
- 代码提交：f5cffc295a420c57a759f627327fc0ebc3a2664d。本提交尚未执行定向测试，不能称为被测通过候选。
- run_id：cairn-bridge-20260911；[Spec](spec.md)、[Plan](plan.md)。记录自身提交通过git log查询。
- 主代理负责设计/客户端/桥接/集成；gpt-6-astra/low仅按固定接口实现持久日志及对应测试，未运行测试或设计架构。

## 1. 已交付内容

固定依赖Cairn 8e7e0ea67552383851dfcabfba0c4e9c8d007878（包版本0.2.1），复用原生客户端、模型及Server；未修改Cairn核心。新增内部Task探索输入、平台持久操作日志、调度预选/再次准入、AgentRun归属检查、原生结论提交及已知Intent的只读核对。共用上一批ExecutionPermit校验函数，避免两处判定漂移。

日志构造器不创建生产表，不读取DSN；临时SQLite建表只在测试夹具中定义。本包需要workspace和冻结uv.lock提供固定Git来源，不作为可从PyPI独立解析裸cairn包名的发行物使用。

## 2. 实际执行与未覆盖

| 操作 | 结果 | 证据 |
| --- | --- | --- |
| uv lock | exit0 | 固定Git提交解析成功，Cairn及桥接依赖写入锁文件；命令墙钟23.167秒 |
| uv sync --frozen --group cairn-bridge | exit0 | 依赖及editable包安装成功；命令墙钟5.788秒 |
| 后续命令前预算守卫 | exit124；命令未启动 | 检查窗口已耗尽，未继续解析/测试/构建 |
| C01 原生创建/重放 | not-tested | 测试代码已写，未运行 |
| C02 调度准入/撤销 | not-tested | 测试代码已写，未运行 |
| C03 原生结论/响应丢失 | not-tested | 测试代码已写，未运行 |
| C04 持久恢复/冲突 | not-tested | 测试代码已写，未运行 |
| C05 取消与日志CAS | not-tested | 测试代码已写，未运行 |
| 共用许可函数受影响回归 | not-tested | 上一批026457f证据保留，不冒称覆盖本次提取后的源码 |
| 独立sdist/wheel构建 | not-run | 依赖安装中的editable构建不代替此项 |

没有运行原生Server测试夹具，没有启动网络服务、Dispatcher、Pod或Agent；真实模型/集群/目标调用均为0。旧API/浏览器/主题矩阵未重跑。

## 3. 预算与组织限制

起始已用508/600秒、剩92秒。依赖步骤在窗口开始约29秒时完成；之后候选准备和包元数据审查消耗剩余窗口，后续命令的执行前守卫返回124，没有启动该命令。

守卫退出前未持久化精确最终结束时间，因此不能宣称完整窗口被精确验证为92秒或所有验证在该时限内完成。按剩余额度全额记为耗尽，**当前剩余检查预算为0**，不得换分支/批次/日志重置。日志记录见忽略的artifacts/phase-1c-cairn-bridge/validation.json及lock/sync.log。

包独立发行的来源声明在候选准备中被发现尚未固定，未在超时后继续解析；已恢复与成功解析锁文件一致的workspace来源，限制在README说明。未追加测试、不运行第二套框架。后续检查守卫必须在任何提前退出前先保存状态，避免再次缺失终点证据。

## 4. 后续定向入口（本次未执行）

获得新的检查额度后，先使用现有环境运行：

```sh
.venv/bin/python -m pytest packages/cairn-bridge/tests packages/task-runtime/tests/test_controller.py::test_invalid_current_permission_never_creates packages/task-runtime/tests/test_controller.py::test_revocation_during_create_stops_only_returned_uid -q
```

随后只构建wuji-cairn-bridge；若依赖或源码未变化，不重复安装/构建整个平台。测试夹具必须把原生Cairn数据库指向tmp_path，并使用进程内HTTP适配，不能写用户默认Core数据库或启动Agent。失败只修复并复测受影响项，仍按已批准的新额度计时。

## 5. 部署与业务边界

公开API仍0.4.0，主业务HEAD/master/服务及数据库未切换；Cairn仅作为当前开发环境依赖安装，未部署。平台Task外键、生产迁移/RLS/服务角色、真实ControlSource、Dispatcher接线、动态Agent/Pi/MCP、镜像资源准备和真实出口均未接入。

原生Project创建结果不明时无法依赖新增回执恢复，因为Core不修改；本批明确不按名字猜绑定或自动再创建。Core数据实例重建需明确核对server_id和绑定；Task代码与原生ID相似不能证明数据连续性。

本批代码可供审查，但C01—C05缺少执行证据，不能标为accepted或开放真实任务执行。
