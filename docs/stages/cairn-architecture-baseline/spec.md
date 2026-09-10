# Cairn 架构文档收口 Spec

- 状态：approved；实施状态见 acceptance.md。
- 日期：2026-09-10。
- 批准依据：用户明确要求实施《Wuji 架构复审修订版：Cairn 调度、平台侧 Agent 与共享 Kali》，本轮执行产物限定为架构文档。
- 基准：codex/phase-1c-prep@6ee84b5268a5012c69ba4567d78eb18727b41ee1。
- 背景：根 AGENTS、[背景索引](../../project-context.md)、[原阶段记录](../phase-1c-prep/acceptance.md)、[P0验收](../phase-1c-prep-p0/acceptance.md)、主架构、Harness/黑板设计与评估模型已读取；用户最新明确决定覆盖旧方案。

## 1. 目标与范围

交付一套没有有效约束冲突的架构文档，使后续开发能够区分已确认架构、候选版本、已实现业务和实际验收。新增[架构替代决策](../../cairn-architecture-decision.md)，同步主架构、Harness、黑板、协作规则、索引及受影响的活动设计入口。

本批不修改应用代码、OpenAPI、生成物、依赖/锁文件、数据库迁移或运行配置；不安装、部署、启动服务、不请求模型、不访问目标。公开 API 保持0.4.0；现有任务仍只有queued/cancelled。

## 2. 必须表达的架构行为

- 一个Wuji Project包含多个Task；一个Task对应一个Cairn Project。Agent在平台侧Worker Pod运行；多个Agent通过受控工具接口共用一个Kali容器，同时最多一个获准执行的Runtime attempt。
- Worker后端只管理Agent资源；Runtime Controller独占Kali资源。Cairn调度探索，Wuji负责身份、执行准入、停止与核对；active/stopped不作为执行许可。
- Cairn Server为Fact/Intent/Hint及探索关系唯一可写来源；首版单Server、单Dispatcher、持久化SQLite。Wuji PostgreSQL保留Task、AgentRun、工具账本、证据元数据和验证/报告；投影及原始提交不成为第二套可写Fact。
- 草稿不创建Cairn Project；正式Task通过稳定外部标识幂等绑定停止态Project。历史queued缺少start记录，不得自动执行。
- Worker配置身份和AgentRun执行身份分开。结果先持久化再同步黑板；同步失败只重投结果，不重跑探索。跨库使用按任务排序的幂等操作和回执，不假设分布式事务原子性。
- 完成先提案，平台核对覆盖、证据和停止条件；达成目标才写Cairn完成边，部分结束保持停止态。终态复测创建关联新Task。区分未知执行与已停止但结果缺失，不把未知写成成功或未复现。
- 目标链路复用Cairn、Pi coding-agent及LiteLLM；LangGraph/LangChain/Deep Agents不再是必选依赖，P0实验和证据保留。候选版本为Cairn 8e7e0ea、Pi 0.73.0、LiteLLM v1.100.0，尚未在Wuji集成验收。
- Pi工具显式限定，提供不可变快照读取及受控工作记忆，Kali操作经Tool Router/MCP；本地路径不能代替Artifact引用。上游Key不进入Agent或Kali。
- 管理员维护组织模型配置，任务配置金额预算USD；所有Agent及辅助调用共用Task预算，重启不重置。未知价格不按零计费，不承诺未经验证的并发零超支；关闭自动付费探活，发布要求同版本显式连接检查成功。
- 保留五场景、五主题、默认匿名、域名/子域授权和凭据受限共享；流量细节仍待后续设计，真实目标执行前必须有出口和停止边界的证据。

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
