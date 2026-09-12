# vNext MAF v2 执行计划入口

- 状态：approved / in-progress；基准 SHA：`1d73a767599732d9a53f81ad2cc553f4bf11d84e`。
- 实际计划：[P00—P20](../../vnext/PLAN.md)，机器索引：[plan_tasks.json](../../vnext/plan_tasks.json)。
- 框架复用、权限/数据/兼容、接口、文件所有权和依赖按上述计划及[实施决定](../../vnext/decision-register.md)。
- 分支：`codex/vnext-maf`；绝对工作树：`/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`。

主代理负责实际基线、计划一致性、契约/迁移/锁文件归属、审查与集成；按需用用户授权的 `gpt-5.6-sol/xhigh`、`gpt-6-astra/xhigh` 实施和审查明确任务，不另建用户开发任务。使用版本隔离的 Superpowers 台账记录任务、原始结果、修复与审查，不反复派发已完成任务。

每项先建立能揭示缺失行为的检查，再实现并运行直接相关的正/反向路径；集成统一执行一次所需完整入口，修复只复测受影响项。75 条核心验收不能由静态例子、空集合、自己填写的 pass 或采样日志替代。无累计开发检查时间预算；Profile 中机制夹具执行上限属于产品限制，含义独立。

代码本地提交；不自动推送、部署、停机、删旧数据或发起收费效果试验。最终交付注明实际完成项、未运行项、被测 SHA 和证据。
