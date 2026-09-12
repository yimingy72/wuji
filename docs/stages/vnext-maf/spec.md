# vNext MAF v2 重构阶段

- 状态：approved / implementation in-progress。
- 批准依据：用户 2026-09-13 明确要求按 `/Users/yym1ng/Downloads/wuji_maf_redesign_v2` 的 Spec/Plan 进入重构，并授权按需使用 SOL xhigh / GPT-6 xhigh 子代理。
- 负责人：当前会话主代理。
- 权威行为与验收：[完整 Spec](../../vnext/SPEC.md)、[合同枚举](../../vnext/contracts.json)、[75项验收定义](../../vnext/ACCEPTANCE.md)。
- 实施补充：[决定记录](../../vnext/decision-register.md)。

范围为自有 Blackboard/Scheduler、真实 Python MAF、持久执行与审批/恢复、React Flow 工作台、历史只读归档和独立新发布物。首批是合成模型与受控无敏感夹具的机制验证；真实模型效果、生产环境切换和旧数据删除不在本次自动执行授权内。

新链路不依赖 Cairn/Pi；保留旧实现、历史证据和主目录未提交变更。新代码在独立分支及独立测试数据库/运行环境实施，不能提前修改旧部署。
