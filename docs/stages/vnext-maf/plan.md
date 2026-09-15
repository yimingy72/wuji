# vNext MAF v2 执行计划入口

- 状态：approved / in-progress；基准 SHA：`1d73a767599732d9a53f81ad2cc553f4bf11d84e`。
- 实际计划：[P00—P20](../../vnext/PLAN.md)，机器索引：[plan_tasks.json](../../vnext/plan_tasks.json)。
- 框架复用、权限/数据/兼容、接口、文件所有权和依赖按上述计划及[实施决定](../../vnext/decision-register.md)。
- D11 交付组织：[M0–M5、操作前沿与六类既有合同交接](../../vnext/delivery-milestones.md)。它只重排可运行成果的交付次序，不增加任务/AC、替换权威 Spec，或预先标记实现和验收通过。
- M3 接缝：[P08 会话与审批实施合同](../../vnext/P08-implementation-contract.md)固定完整发布、原生调用身份、操作前沿及 P05/P06/P09/M2 消费；沿用原任务依赖和模型分工。
- M2 复核收口：[实际投递与受信结果补交](../../vnext/P10-implementation-contract.md)固定生产 Outbox 消费、精确执行身份和 current/historical 结果授权，作为已批准 P10 的集成修复，不重写旧 child 检查的覆盖范围。
- 分支：`codex/vnext-maf`；绝对工作树：`/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`。
- 当前开发次序以 [2026-09-15 开发任务与下一项执行计划](next-development-plan-2026-09-15.md)为入口：先完成 P15-L Layout CAS 垂直切片，再收口 P08 Session、P11 正式控制和 P12 可信完成，随后实现 ViewStream 与治理/发布。旧 2026-09-13 审核保留其当时截面。
- 本地 K8s arm64 新链路和首条 Task Pod 机制执行已经取得限定证据；当前 `api`、`runtime`、`scheduler`、`gates`、`wuji-web` 作为后续垂直切片的实际部署底座。具体通过范围仍以 acceptance 和永久证据为准。
- 2026-09-13 [下一批开发执行单](next-batch-plan.md)保留历史排序；当前负责人、迁移顺序、部署边界和停止条件以[2026-09-15执行计划](next-development-plan-2026-09-15.md)为准。

主代理负责架构、集成与质量。修复、测试、复核和轻量工作用 `gpt-5.6-sol/xhigh`，核心开发或重大复杂问题才用 `gpt-6-astra/xhigh`。按用户 2026-09-13 最新决定停止 Superpowers 流程，直接推进可运行功能，只做必要验证和定向修复；保留原始证据，共享数据库串行，不因交接重跑或反复编写流程文档。旧 Superpowers 台账仅为历史参考。

各实施合同中的旧“等待首RED后写核心”“固定旧Agent占用共享窗口”等编排条款仅描述当时安排，现由上述用户决定和当前计划替代；保留其产品/权限/数据合同，不恢复已经取消的流程关口。

每项先建立能揭示缺失行为的检查，再实现并运行直接相关的正/反向路径；集成统一执行一次所需完整入口，修复只复测受影响项。75 条核心验收不能由静态例子、空集合、自己填写的 pass 或采样日志替代。无累计开发检查时间预算；Profile 中机制夹具执行上限属于产品限制，含义独立。

代码本地提交；本地隔离 K8s 部署测试按已有授权执行。不自动推送、切换旧部署、停机、删旧数据或发起收费效果试验。最终交付注明实际完成项、未运行项、被测 SHA 和证据。

P01 固定交付入口：[当前报告](../../vnext/P01-report.md)、[CapabilityRecord](../../vnext/capability-record.json)、[永久证据及迁移映射](../../vnext/evidence/P01/relocation.json)。这些由 Wuji vNext P01 文档保留；`.superpowers/sdd/vnext-v2/` 只保留活动 scratch，不再 force-add 或承担永久证据保留。

M0 先完成 P06 已发现问题的最终消费者、公开交接与诚实证据收口；M1 随后以实际发布 MAF runtime 经真实 ModelGate/ToolGate 读取固定无害文件，形成 P03 Observation/EvidenceReceipt、原生工具结果、Agent Claim 和 P04 raw-first 接纳。M1 不等待通用 `platform_record`、完整 MCP/Kubernetes、P08 或完整 UI。后续 M2–M5 继续承接 Scheduler/Outbox/Supervisor、恢复控制与完成、正式画布/投影/流，以及 P16/P17/P19/P20；P18 可离线准备，但不构成收费效果试验授权。
