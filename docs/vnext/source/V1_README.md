# Wuji MAF 重构文档包

版本 1.0-review · 2026-09-12

这是一份基于上传草案、指定仓库快照和官方框架文档的修订交付。目标是完全退出 Cairn 运行内核，用 Wuji Blackboard / Scheduler + MAF Harness，并由 React Flow `TopologyFlowCanvas` 展示业务图。

## 文件

| 文件 | 用途 |
|---|---|
| [REVIEW.md](REVIEW.md) | 20 项草案发现，区分保留、修正和本轮新增要求 |
| [SPEC.md](SPEC.md) | 目标架构、领域模型、状态机、事实链、事务/接口、画布和 40 项验收 |
| [PLAN.md](PLAN.md) | 19 个实施任务（P00–P18）、文件路径、接口、测试、依赖与发布关口 |
| [traceability.json](traceability.json) | 32 项需求 → 40 项验收 → 实施任务的机器可读映射 |
| [plan_tasks.json](plan_tasks.json) | P01–P18 的任务元数据；P00 为基线/批准关口，见 Plan |
| [SOURCES.md](SOURCES.md) | 来源、基线和未完成验证；区分原草案与设计建议 |
| [INPUT_SPEC.md](INPUT_SPEC.md) | 上传草案的原始副本，未修改 |
| [VALIDATION_REPORT.md](VALIDATION_REPORT.md) | 本次实际完成的文档级检查，不是产品测试报告 |

## 最重要的三个约束

**React Flow 不是黑板数据库。** 领域记录在 PostgreSQL，画布是可重建投影，布局单独保存。

**真实 Fact 来自受限采集断言。** 工具原文、模型解释和经规则接纳的结论分开；Agent 不能直接写 Fact。

**完全退出 Cairn 不等于删掉旧证据。** 新运行不需要旧服务/SDK；旧记录离线归档，未知旧操作先核对，切换失败进入维护态。

## 执行边界

本轮仅创建这些文档，没有修改远端仓库、运行产品、调用收费模型或部署集群。Spec 与 Plan 为 review-ready 候选；业务实施、数据切换与真实环境操作需要明确批准。所有未来测试均标为待执行，没有预写通过结论。

Mermaid 图以可编辑文本嵌入 Spec/Plan；本次只检查代码围栏完整性，未声明已用 Mermaid 渲染器验证所有布局。
