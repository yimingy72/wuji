# Cairn 架构文档收口 Spec

> 2026-09-11后续澄清已确认：[Task主体、核心不改、单Task Pod双容器](clarification.md)。本Spec同步现行边界；原944e95b验收只适用于当时文档，业务开发进入[新阶段Spec](../phase-1c-runtime-foundation/spec.md)。

- 状态：approved；实施状态见 acceptance.md。
- 日期：2026-09-10。
- 批准依据：用户明确要求实施《Wuji 架构复审修订版：Cairn 调度、平台侧 Agent 与共享 Kali》，本轮执行产物限定为架构文档。
- 基准：codex/phase-1c-prep@6ee84b5268a5012c69ba4567d78eb18727b41ee1。
- 背景：根 AGENTS、[背景索引](../../project-context.md)、[原阶段记录](../phase-1c-prep/acceptance.md)、[P0验收](../phase-1c-prep-p0/acceptance.md)、主架构、Harness/黑板设计与评估模型已读取；用户最新明确决定覆盖旧方案。

## 1. 目标与范围

交付一套没有有效约束冲突的架构文档，使后续开发能够区分已确认架构、候选版本、已实现业务和实际验收。新增[架构替代决策](../../cairn-architecture-decision.md)，同步主架构、Harness、黑板、协作规则、索引及受影响的活动设计入口。

本批不修改应用代码、OpenAPI、生成物、依赖/锁文件、数据库迁移或运行配置；不安装、部署、启动服务、不请求模型、不访问目标。公开 API 保持0.4.0；现有任务仍只有queued/cancelled。

## 2. 必须表达的架构行为

- Task是完整业务主体，统筹目标/起点/终点、场景、工具、约束、模型预算和外部执行控制；一个Task使用一个Cairn Project探索上下文。
- 单Task Pod双容器：agent动态运行多个独立AgentRun；kali提供共享工具/工作区。Task Runtime Controller唯一拥有Pod生命周期；Cairn后端只管理agent进程。Runtime attempt为整个执行环境代次，同时最多一代获准执行。
- Cairn Server、数据库和Fact/Intent/Hint及原生协议保持原样；适配在Dispatcher/执行后端/工具和Wuji外围。不添加核心外部Task字段、原子停止态创建、图版本、幂等回执或事务事件。
- 未启动任务由外部许可和所有调度入口共同阻止，不能依赖Cairn默认active状态。原始结果先保存，原生写入响应不明先核对；无法确认不盲目重投，更不重跑模型/目标。
- Cairn探索完成与Wuji执行/评估状态分开；保留原生完成语义，独立核对停止、证据和覆盖。不把结果未知写成成功或未复现，不自动reopen已交付历史。
- 工作文件直接在Kali的agents/<agent_run_id>及shared目录交接；正式证据、报告和长期归档再登记Artifact。凭据仍通过受限引用共享。
- 首个Harness采用Pi，模型/循环/压缩复用现成能力；LiteLLM执行Task USD金额预算，所有辅助调用共享，重启不重置。上游Key在网关，agent任务凭据不挂载给kali；关闭自动付费探活。
- 保留五场景、五主题、匿名Web、域名/子域授权和旧queued不自动执行；网络约束以整个Task Pod为单位，真实目标开放前需有出口/停止证据。

## 3. 协作、兼容与历史

按用户最新要求在当前会话连续完成。架构由主代理独立设计；允许按需子代理，本次模型gpt-6-astra/low。删除旧的强制SOL/Luna、固定并发、必须独立worktree/测试代理等规则；保留Git、精简测试和证据真实性要求。

主业务工作区HEAD保持381ae3a；master保持28fcd44。主目录AGENTS与临时索引可同步但保持未提交，避免改变运行SHA。提交发生在phase-1c-prep分支，不清理历史工作树。

旧0.5 Spec/Plan标记为被替代的历史草案；旧Token预算、P0 Provider生产化和LangGraph调度不再作为开工依据。P0及Phase1A/B历史SHA、命令、测试数字和未覆盖事实不改写。下一批业务Spec/Plan尚未批准，不用本批文档验收代替业务验收。

## 4. 验收标准

| 编号 | 必须有的证据 |
| --- | --- |
| D01 | 根规则、决策、主架构、Harness/黑板正文表达一致；旧约束只能出现在明确标注的历史范围 |
| D02 | 当前阶段Spec、Plan、Acceptance齐全，背景索引能导航到新权威来源；本地相对链接可解析 |
| D03 | 当前实现仍标0.4.0，P0范围及Phase1A partial不被夸大，候选框架不标为已部署 |
| D04 | Git差异仅文档；主HEAD/master未前移，无运行记录、依赖、迁移或秘密进入提交 |
| D05 | 后续依赖顺序明确：控制面基础→调度适配→共享Runtime→产品接入→真实目标开放；具体业务接口仍由后续Spec冻结 |

只做文档diff、一致性和链接检查。不启动业务测试。Phase1C前置检查预算仍为已用426/600秒、剩174秒，真实模型4次额度已用完；本轮不重置、不追加。
