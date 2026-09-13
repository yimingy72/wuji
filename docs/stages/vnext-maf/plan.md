# vNext MAF v2 执行计划入口

- 状态：approved / in-progress；基准 SHA：`1d73a767599732d9a53f81ad2cc553f4bf11d84e`。
- 实际计划：[P00—P20](../../vnext/PLAN.md)，机器索引：[plan_tasks.json](../../vnext/plan_tasks.json)。
- 框架复用、权限/数据/兼容、接口、文件所有权和依赖按上述计划及[实施决定](../../vnext/decision-register.md)。
- D11 交付组织：[M0–M5、操作前沿与六类既有合同交接](../../vnext/delivery-milestones.md)。它只重排可运行成果的交付次序，不增加任务/AC、替换权威 Spec，或预先标记实现和验收通过。
- M3 接缝：[P08 会话与审批实施合同](../../vnext/P08-implementation-contract.md)固定完整发布、原生调用身份、操作前沿及 P05/P06/P09/M2 消费；沿用原任务依赖和模型分工。
- M2 复核收口：[实际投递与受信结果补交](../../vnext/P10-implementation-contract.md)固定生产 Outbox 消费、精确执行身份和 current/historical 结果授权，作为已批准 P10 的集成修复，不重写旧 child 检查的覆盖范围。
- 分支：`codex/vnext-maf`；绝对工作树：`/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`。

主代理负责实际基线、计划一致性、契约/迁移/锁文件归属、审查与集成。按用户最新决定，修复、测试、验证、代码复核和轻量重复任务统一由 `gpt-5.6-sol/xhigh` 承担；核心功能开发或重大复杂问题才用 `gpt-6-astra/xhigh`。核心开发与测试可按不重叠文件分工，共享数据库验证串行执行；交接保留原始证据，不因换模型重跑。不另建用户开发任务。使用版本隔离的 Superpowers 台账记录任务、原始结果、修复与审查，不反复派发已完成任务。

每项先建立能揭示缺失行为的检查，再实现并运行直接相关的正/反向路径；集成统一执行一次所需完整入口，修复只复测受影响项。75 条核心验收不能由静态例子、空集合、自己填写的 pass 或采样日志替代。无累计开发检查时间预算；Profile 中机制夹具执行上限属于产品限制，含义独立。

代码本地提交；不自动推送、部署、停机、删旧数据或发起收费效果试验。最终交付注明实际完成项、未运行项、被测 SHA 和证据。

P01 固定交付入口：[当前报告](../../vnext/P01-report.md)、[CapabilityRecord](../../vnext/capability-record.json)、[永久证据及迁移映射](../../vnext/evidence/P01/relocation.json)。这些由 Wuji vNext P01 文档保留；`.superpowers/sdd/vnext-v2/` 只保留活动 scratch，不再 force-add 或承担永久证据保留。

M0 先完成 P06 已发现问题的最终消费者、公开交接与诚实证据收口；M1 随后以实际发布 MAF runtime 经真实 ModelGate/ToolGate 读取固定无害文件，形成 P03 Observation/EvidenceReceipt、原生工具结果、Agent Claim 和 P04 raw-first 接纳。M1 不等待通用 `platform_record`、完整 MCP/Kubernetes、P08 或完整 UI。后续 M2–M5 继续承接 Scheduler/Outbox/Supervisor、恢复控制与完成、正式画布/投影/流，以及 P16/P17/P19/P20；P18 可离线准备，但不构成收费效果试验授权。
