# 核心闭环验收记录

日期：2026-09-11；状态：**accepted：本批封闭夹具核心闭环；完整生产能力仍未验收**。开发与验收由当前会话主代理负责，按明确范围使用gpt-6-astra/low开发子代理；不称为独立测试。起点5631d80，分支codex/phase-1c-core-loop。

## 已实现

M1真实v2草稿/授权/模型价格配置快照/ready；M2持久start消费者、epoch/AgentRun/工具账本/Task Key与Pod生命周期；M3固定Cairn Dispatcher、Pi0.73.0、LiteLLM1.100.0和共享Kali；M4真实Fact/工具/证据/结果、完成与取消停止核对。0006/0007已在隔离测试库实施。原生Cairn Core未修改，Pi保留原生会话、循环和压缩。真实长上下文压缩未专项验收。

## 首轮证据（不冒称最终候选实测）

- 代码10f89a7：contracts:check退出0；正式web build退出0；pytest tests/task-creation tests/core-control退出0（8项）；node --test tests/task-workers/boundaries.test.mjs退出0（2项）。记录位于artifacts/phase-1c-core-loop下contracts.json、web-build.json、core-unit.json、workers.json。
- 真实环境代码c797ae75fc8bc8c3e66e6d233647df4102cc8d24，run_id=p1a20260911t065757f39dca，wuji-test/4182。浏览器创建过程包含后续e3f8357已提交的DatePicker修复；不将当时有前端改动的工作区称为纯c797候选。
- Task6525f458-3f31-4492-8c9a-fa42395e48b6：实际服务端202被测试代理丢弃，刷新仅按原键a514106c-518c-4b1c-bfef-2a2fdbec54c8核对，数据库始终一个Task；start前0个AgentRun。
- 显式启动后运行6个独立AgentRun、1个Task attempt、实际双容器Pod；3个Kali工具调用完成HTTP标记、共享文件写入、另一Agent读取；形成原生f001/f002/f003和3份Artifact，Task completed、清理完成、Task Key blocked，报告费用0.0028 USD（合成价和用量，无真实模型费用）。
- 同一路径Task e550f5c9-e818-41a1-a387-7a793d77d086取消运行中的延迟HTTP工具：cancelled，active_calls=unknown_calls=0，清理完成。迟到派发和旧epoch工具调用均409。
- 金额Task c276ae95-4dd5-4603-aa63-3041d51a31dc：max_budget=0.000001 USD，首次在途请求实际计0.0002，后续请求被原生预算拒绝；证明累计/拒绝，不证明零超支。
- Viewer读取实际Artifact200且SHA-256一致；读取其他提交者回执404，写命令403。对应native-budget-stop.json、artifact-access.json、cancel-budget.json。

## 已发现并定向修正

- 本机代理影响Keycloak管理客户端，改为本地调用trust_env=False；不增加额外协议或依赖。
- 镜像源HTTP及Git公网传输失败，使用官方HTTPS、已固定基础镜像摘要和经核对的固定Cairn源码缓存；未升级Cairn或修改Core。
- 日期输入未保持，改为Ant Design DatePicker并实测预览的时区和截止时间；相关构建通过。
- 最终Reason原生完成回写后与停止核对竞态，使成功结果被显示为取消：e3f8357先登记成功结果，再触发收尾，旧原生回执先核对再检查新执行许可。该项及M4关系读取在最终候选上复核。

## 最终定向验收

业务候选：**6c5934c33df8bd4ac9e8f32be9ae9c3e979342b8**；run_id：**p1a20260911t080823ff8011**；Docker Desktop、wuji-test、4182；代码与实际镜像摘要见本机`artifacts/phase-1c-core-loop/final-check.json`。合成配置辅助脚本将context_window设为32768，避免本轮夹具无意触发Pi默认16384保留空间下的压缩；这不是生产默认或压缩能力验收。API/控制器/工具/Dispatcher与候选一致。

| 检查 | 实际结果与证据 |
| --- | --- |
| 契约和构建 | 包含M4的候选内容上contracts:check、正式web build、core image build均退出0；contracts-m4.log、web-m4-build.log、core-m4-image.log。契约11条既有warning、web大chunk提示保留，无错误。 |
| 真实正常执行 | Task e6abfc7a-aa48-41f5-928b-521abfe9f46e：6个AgentRun全部exited/synced/success；3个实际工具、3份Artifact、3个结果Fact，加origin/goal共5个Fact；1个runtime_attempt；Task completed、清理completed。 |
| 关系与证据 | 按intent_id、agent_run_id、tool_call_id筛选均对应真实对象；跨筛选游标及错误筛选422；3份证据内容SHA-256均核对一致。 |
| 结果核对 | 模拟原生conclude已提交、平台journal响应未持久的缺口；保留同操作参数只读核对成功，AgentRun/ToolCall/Fact数量均不增长。结束后原回执仍可读取；模拟记录随后恢复。 |
| 金额结束原因 | Task 3c99fe15-ea62-416b-9dd9-2984ac95c942由真实原生预算拒绝后结束，stop_reason=budget_exhausted。原生累计和超支边界复用首轮native-budget-stop证据。 |
| Codex浏览器 | 真实登录→Intent i003→AgentRun 9bc00f7e-a8b0-4481-b243-e6488c661f2e→workspace_read→Artifact 9324399c-8b97-5868-bbc9-0a33f98c2881；时间线完整显示创建至已核对停止，结果费用0.0028 USD、目标未判定、限制和资源清理分别展示。 |

命令：`.venv/bin/python artifacts/phase-1c-core-loop/final_check.py --run-file ABS`首次退出1，原因仅为检查脚本误连PostgreSQL管理库；此前正常执行/关系/证据检查已通过。修正为本次隔离业务数据库后，用`--existing-task e6abfc7a-aa48-41f5-928b-521abfe9f46e`继续原任务，退出0；没有重新运行正常探索。同类脚本问题只修正这一轮。对应final-check.log、final-recheck.log及final-check.json。

浏览器截图`browser-workspace-m4.png`、`browser-result-m4.png`。走查时修正主视图标题下过宽的span样式选择器，使已选按钮继续使用Ant Design原有文字对比；只复核页面，不重跑后端。最终记录提交仅包含文档、这一CSS修复和上述合成配置参数，不将其声称为一轮新全量实测。

## 交付运行与版本

验收记录提交与被测代码SHA分别记录，不预写记录自身SHA。交付前通过原生命周期停止验收进程和Core/网关，保留测试数据及PVC；提交记录后用正常serve-only创建当前HEAD的新运行记录。新的交付入口保持4182，私有记录`work/run/core-delivery.json`，公开ID/状态写入`artifacts/phase-1c-core-loop/delivery.json`。该运行可准备一条实际演示Task；沿用已通过的同版本执行代码，不再运行取消/故障/预算矩阵。主目录381ae3a、master28fcd44和4180始终保留。

## 限制

本轮只开放服务端登记的自建HTTP夹具与合成模型上游，不开放任意Shell、代理或外部目标。未验收Pod生产出口隔离、全量网络采集、真实模型渗透效果、长上下文恢复、自动重建续跑或完整Goal评估。Artifact为开发专用独立PVC；费用报告不等于最终结算；停止已确认与目标达成分别显示。Phase1A partial保持，master与4180开发环境不前移。

---

以下为批准前历史记录，保留当时事实，不代表本轮当前进度。

# D3-B / 核心闭环阶段状态与交接记录

- 日期：2026-09-11；状态：**plan draft / 正式业务未实施**。
- 方案代码参考起点：276b6a8；当前工作树已另完成D3-A评审修复，业务原型源码3094e6d，测试入口9a6b4ae。
- 本记录不能作为D3-B或核心执行验收；自身文档提交SHA从git log读取。
- 当前会话主代理处理架构与开发，未使用子代理，也未声称独立测试。

## 已完成的授权工作

读取并集成架构分析任务的handoff及assessment/context/backend-handoff未提交变更；保留用户确认和源码事实/候选建议区别。读取现行架构、阶段材料和实际DTO/迁移/事务/前端恢复代码；当前工作树无CodeGraph，按约定rg定位。

形成：
- [核心闭环总计划](core-loop-plan.md)：M1创建→M2控制→M3真实框架/共享执行→M4结果与停止。ready不是最终目标。
- [M1 Spec](spec.md)/[Plan](plan.md)：草稿2.0、Task自有授权、预览/幂等/快照/ready、原Scope/queued兼容、模型状态协调和正式前端路径。
- [五场景模板](goal-templates.md)：默认目标/完成条件与自定义快照。
- [执行合同提案](execution-handoff.md)：原生阶段、Reason补证建议、持久尝试/成果、文件/进程/证据交接；不修改Core。

收到用户创建页真实反馈后，已直接实施获准的D3-A补丁，见[原型补充记录](../phase-1c-creation-prototype/acceptance.md#创建入口评审反馈补丁2026-09-11)。没有将完整原型或正式平台标为用户已通过。

## 本阶段未发生的动作

未修改正式API/契约/迁移/数据库/Task执行状态；未启动Cairn、Pi、Kali或新LiteLLM；真实模型调用0、目标调用0。主目录HEAD381ae3a/master28fcd44及其运行记录/服务保留。只重建了独立4186原型静态产物，原用户草稿标签页保留。

正式业务验证命令尚未执行，C1—C6及核心联合验收均pending。D3-A的2个定向用例、构建/浏览器检查不替代这些验收。文档只做差异和本地链接校对，结果见本次交付日志。

文档校对实际结果：git diff --check通过；17份变更/新增Markdown中的175个相对文件链接均存在，未检出密钥形状文本。检查基准9a6b4ae与当时文档工作区，日志artifacts/phase-1c-creation-prototype/feedback-doc-check.json；未访问外部链接或运行框架测试。

## 下一步与真实门槛

当前应用Default，根AGENTS要求新阶段先在Plan模式完成具体规划。当前已具备可审阅的完整终点、M1接口/迁移细则与M2—M4依赖；应用切换后集中收口具体运行控制存储、固定版本LiteLLM受限Key/预算参数和集群出口能力，不把未验证候选写成已实现。

整体方案批准后持续完成内部里程碑，不在ready结束后只留新草案；实质变化更新方案。已经落实的用户入口意见不重复问；原型不再承担完整五主题/故障矩阵。尚未实现的真实模型能力和真实外部目标开放仍按既有授权/预算/出口条件处理。
