# Phase 1C：Task 与原生 Cairn 桥接 Spec

- 状态：approved；日期：2026-09-11。
- 批准依据：用户已选定单Task Pod双容器并要求开始开发，本轮“继续开发”承接已确认的Task治理/Cairn核心不改方向。
- 基准：7cfcf386ca0d0388b039d60a941bc2812e118d5a；分支codex/phase-1c-cairn-bridge，沿用现有工作树。
- 背景：已读取根规则、项目索引、运行基础Spec/Plan/Acceptance、黑板设计、现有Task数据访问及Cairn固定源码。索引尚未覆盖此工作树，代码定位使用rg/直接读取。

## 1. 本批范围

新增可选Python包wuji-cairn-bridge，固定复用Cairn提交8e7e0ea67552383851dfcabfba0c4e9c8d007878的原生客户端、Pydantic模型和Server。实现Task探索输入、原生Project创建/查询、未获准任务过滤、结果提交/响应不明核对，以及Wuji侧SQLAlchemy持久操作日志。

本批不是完整0.5 API或真实Agent启动：不修改Cairn核心，不创建/启动Dispatcher、Pod或模型请求，不访问目标，不对外发布新接口，不执行生产迁移。生产Task授权/许可读取、数据库迁移/RLS、Cairn Dispatcher接线及动态进程留后续控制面接入；不能把本包内部接口当作公共身份认证。

## 2. Task与原生输入

TaskKey包含tenant_id、project_id、task_id（UUID）；Task保持Wuji业务主体。探索输入只把title/origin/goal/bootstrap_enabled送给Cairn CreateProjectRequest。模型、预算、工具、授权、凭据和外部控制配置不随整个Task对象写入黑板。

Core实例使用部署配置显式提供、绑定持久数据实例的UUID server_id标识，不从URL猜测；数据丢失/重建时须冻结并明确核对实例身份，不得仅复用旧URL假定原生ID仍指向原数据；同Task不能静默重绑其他Core实例。原生Project/Intent/Fact ID验证为受限路径片段。

## 3. 持久记录与写入边界

Wuji侧日志只保存Task归属、原生Project引用、输入摘要、原始结果与操作状态，不保存可独立编辑的Fact图。

- 创建绑定每Task唯一，原生Project在同server_id下不能绑定两个Task。同输入重放返回既有绑定；同Task异输入/异归属/异实例冲突。
- 写请求前必须将操作从pending原子claim为sent并提交本地事务。只有claim成功者能发出一次请求；进程崩溃遗留sent按结果不明处理，不能抢占为pending自动重发。
- 原生创建201且响应可校验后记录bound；明确4xx拒绝记录rejected；网络/5xx/异常响应记录unknown。创建响应丢失不按名称或时间猜Project，也不自动再创建。
- Agent结果先持久化。每个operation_id绑定Task、AgentRun、原生Intent、描述及配置/许可代次摘要；同键异输入冲突。
- conclude成功时核对原生Intent/Fact/worker/描述关系后记录applied。响应丢失可按已知Project+Intent只读核对：只有to指向的Fact描述和worker均匹配才确认applied；仍open则保持unknown，不自动重投；其他已结论记录conflict。
- 已应用结果重放只返回日志；取消后或AgentRun未登记为活动时，新结果保留为rejected记录，不提交Core。原生查询核对不触发目标或模型。

日志适配接受调用方提供的SQLAlchemy Engine，不读取DSN、不自动建生产表。表属于Wuji控制面，生产迁移/RLS/Task外键和服务角色仍须后续接入后才能对外使用。本批用临时SQLite验证持久状态与重放，不宣称PostgreSQL权限已经验收。

## 4. 调度预选与准入

ControlSource.current(TaskKey)返回可信控制面快照或None。快照含Task归属、TaskRuntimeConfig、ExecutionPermit、RuntimeObservation、control_state、execution_ready和已登记活动AgentRun集合；不得由模型请求参数伪造。

只有原生Project为active、绑定成功、control_state=running、execution_ready为真、许可未过期且与Task/配置/Scope/epoch/attempt匹配、运行资源为ready且Pod名/UID匹配时，才进入预选列表。重用上一批许可校验，不另写一套判定。

预选列表不是永久执行许可；authorize_dispatch在实际派发前重新检查。没有绑定或来源失联时拒绝；旧queued/未启动Task不能因为Core为active就被放行。该门槛只有接入所有Dispatcher执行入口后才构成真实平台保证，本批不启动Dispatcher。

## 5. 客户端复用

使用CairnClient的原生查询/conclude和原生模型，薄扩展其未提供的create_project入口；不重写黑板Server或模型协议。客户端Base URL不得含凭据/query/fragment，关闭重定向与环境代理，设置有限超时，不自动重试写入。原生异常只保留状态/操作类别，不输出上游响应正文。

## 6. 最小验收

| 编号 | 场景 |
| --- | --- |
| C01 | 原生Server临时数据库创建Project，Task重复创建只得到一个Project；平台配置不进入原生输入 |
| C02 | 原生active Project在未启动/许可失效时不进入预选；有效上下文才允许，派发前再次检查 |
| C03 | 原生Intent结论正常提交并重放；模拟响应丢失后按原生图核对到同一Fact，不重复写入 |
| C04 | 创建结果不明跨日志实例重读后仍不自动发第二次创建；错误Task归属/异输入冲突 |
| C05 | 取消后新结果不写Core；日志持久状态CAS与关闭/核对行为符合约定 |

测试使用原生Cairn FastAPI应用与临时SQLite，通过进程内HTTP适配器连接原生客户端；不启动网络服务、Agent、Kubernetes或真实模型。原检查预算已用508/600秒，剩92秒，依赖准备/等待/候选/检查共同累计；不重置，P0真实4次额度仍已耗尽。只做定向检查及新包构建，改动共用许可函数时仅复测其直接用例，通过即停。
