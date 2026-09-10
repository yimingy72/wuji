# Task / Cairn 桥接验收

- 本批结论：accepted / 原生Server进程内最小验证通过；日期：2026-09-11。
- 真实部署与任务执行链路：not-tested，尚未接正式API、Dispatcher、Pi或Kali。
- 当前代码候选：`8e250f439ed50c7516a685a128dfb1ffc9281c50`。
- 初轮被测候选：`fd10efbae3e53143b277483a43e1a046483925a1`，桥接源码来自`f5cffc295a420c57a759f627327fc0ebc3a2664d`。
- run_id：`cairn-bridge-20260911-resumed`；[Spec](spec.md)、[Plan](plan.md)。本验收记录是后续文档提交，自身SHA由git log查询。
- 主代理设计、修复并执行验证；gpt-6-astra/low子代理完成持久日志实现及另一次静态审查，未执行测试，不称为独立测试。

## 1. 承接与范围

前轮依赖安装成功、预算守卫exit124而测试尚未运行的事实完整保存在[初次记录](acceptance-initial.md)。用户随后明确取消累计检查时间预算，本轮使用现有环境补跑必要检查，没有重复安装依赖。旧记录中的时间限制已不再生效；真实模型调用授权额度保持原约定。

本批复用固定Cairn `8e7e0ea67552383851dfcabfba0c4e9c8d007878`（包0.2.1）的原生客户端、Pydantic模型和FastAPI Server，未修改黑板核心。Task绑定、操作日志和执行准入属于Wuji；平台配置不随原生Project输入写入黑板。

## 2. 验收证据

| 编号 | 结果 | 实际依据 |
| --- | --- | --- |
| C01 | passed | 初轮原生创建/查询/重放，仅向Core提交title/origin/goal/bootstrap_enabled；只创建一个Project |
| C02 | passed | 初轮未启动不预选、有效上下文允许、读取期间取消后再次准入拒绝；5个共用许可相关用例通过 |
| C03 | passed | 初轮及修复后均覆盖原生conclude、同操作重放、提交后丢失响应和按已知Intent/Fact只读核对，无第二次conclude |
| C04 | passed | 初轮跨日志实例保持创建unknown、不猜Project或重新创建；Task归属/异输入/原生Project重复绑定冲突 |
| C05 | passed | 初轮及修复后覆盖取消/未登记AgentRun拒绝、持久claim与状态核对；新增迟到拒绝不得覆盖另一请求sent状态的回归通过 |
| 包构建 | passed | 当前候选生成sdist与wheel；安装来源仍要求workspace及冻结锁文件 |

初轮11项通过；发现并发问题后，只执行直接受影响的4项检查（含1项新增回归），全部通过。初轮的创建、过滤与共用许可测试未重跑：修复只涉及结果拒绝/CAS，不修改对应实现、依赖、数据库模板或Runtime源码。历史Runtime候选`026457f`的其他未变范围仍引用其[原验收](../phase-1c-runtime-foundation/acceptance.md)。不将所有历史用例冒称为当前候选重新实测。

## 3. 发现与修复

静态审查发现：同一operation的两个调用都读到pending后，A已claim为sent，B此时失去准入会将A覆盖为rejected；A即使已写入Core，也无法登记成功或按图核对。

当前候选新增`reject_pending_result`：发送前拒绝仅CAS pending→rejected，竞争失败返回现态；已发送请求的原生响应处理仍单独进行。确定性用例固定“另一请求claim→取消→迟到拒绝→原生写入完成→只读核对”的顺序，验证sent不被覆盖、最后applied且只发生一次原生写入。核心Server与协议保持原样。

## 4. 环境、命令及退出码

Python3.13.15、uv0.12.11、SQLAlchemy2.0.52；使用已有工作树.venv。原生Server通过TestClient和requests进程内适配器连接，Cairn数据库及Wuji日志均在pytest临时目录。

| 操作 | 退出码 | 用例结果 / 命令墙钟秒数 |
| --- | --- | --- |
| 初轮定向pytest（命令A） | 0 | 11 passed，3.535秒 |
| 修复后相关pytest（命令B） | 0 | 4 passed，2.184秒 |
| `uv build --package wuji-cairn-bridge --out-dir artifacts/phase-1c-cairn-bridge/dist` | 0 | sdist/wheel成功，1.201秒 |

上述为命令墙钟记录，不是累计检查时间上限。两次pytest均有一条上游Starlette/AnyIO弃用告警，未造成失败，未因此升级依赖或扩大检查。

命令A：
```sh
.venv/bin/python -m pytest packages/cairn-bridge/tests packages/task-runtime/tests/test_controller.py::test_invalid_current_permission_never_creates packages/task-runtime/tests/test_controller.py::test_revocation_during_create_stops_only_returned_uid -q
```

命令B：
```sh
.venv/bin/python -m pytest packages/cairn-bridge/tests/test_journal.py::test_durable_claim_and_identity packages/cairn-bridge/tests/test_native_bridge.py::test_native_conclusion_replay_and_lost_response_reconciliation packages/cairn-bridge/tests/test_native_bridge.py::test_cancelled_or_unregistered_agent_result_does_not_write_core packages/cairn-bridge/tests/test_native_bridge.py::test_late_rejection_preserves_inflight_result -q
```

原始证据在忽略目录`artifacts/phase-1c-cairn-bridge/`：`resumed-validation-initial.json`、`resumed-tests-initial.log`、`resumed-validation-final.json`、`resumed-tests-final.log`、`resumed-build.log`及dist产物。uv命令使用主目录工具链，--directory指向当前工作树；记录包含实际命令与SHA。

## 5. 部署与剩余工作

公开API仍0.4.0，主业务HEAD/master/服务及数据库未切换；未部署Cairn，未运行Dispatcher、Pod、Agent或目标工具。本轮真实模型、Kubernetes集群和目标请求均为0。当前工作树没有CodeGraph索引，使用rg/直接读取；未用主业务旧索引冒充本分支源码。

- 控制面：正式0.5契约、配置快照、ready/start、执行代次、权威ControlSource与AgentRun账本尚未接入；旧queued不自动执行。
- 数据库：平台Task外键、生产迁移、RLS及服务角色待实施。本批内部日志不能直接暴露给外部身份调用。
- 执行：真实Dispatcher所有入口的准入、agent容器动态Harness进程、Pi受限工具、Kali MCP、共享目录、镜像及资源准备待实现。
- 开放：LiteLLM真实金额预算、出口和停止核对尚未联调，不能开放真实目标或把Pod就绪当成可执行证明。
- 发行：当前包通过workspace与冻结uv.lock固定Git来源；独立wheel安装来源声明尚未完善，不从PyPI解析裸cairn包名。
- 恢复：原生Project创建结果不明仍无法自动恢复绑定；不新增Core回执或按名称猜关联。Core数据实例替换必须核对server_id。

本批通过后停止追加检查。下一实施依赖为控制面基础，先冻结新0.5具体接口/迁移和最小验证入口，再接真实调度；历史0.5草案不能直接复用为开发任务书。
