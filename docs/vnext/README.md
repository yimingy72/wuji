# Wuji vNext · v2 文档包

**版本：2.0-review｜日期：2026-09-13｜状态：文档修订，不是已部署产品。**

这次审查针对上一版的 Spec、Plan、Review，而不是只改上传原稿的一段。保留用户确定的 MAF、自有黑板与 Scheduler、React Flow `TopologyFlowCanvas`、退出 Cairn 的路线；修正我上一版的过度约束和合同矛盾。

## 先读哪些文件

| 文件 | 用途 |
|---|---|
| [REVIEW.md](REVIEW.md) | 34 项复审发现：原文定位、问题分类、修订理由、Spec/Plan/验收落点 |
| [CHANGELOG.md](CHANGELOG.md) | v1→v2 的关键破坏性变化与保持不变的边界 |
| [SPEC.md](SPEC.md) | 完整目标合同：知识、状态、调度、MAF、会话、完成、画布、迁移 |
| [PLAN.md](PLAN.md) | 21 项实施任务，路径、接口、代表性测试、依赖、运行关口 |
| [ACCEPTANCE.md](ACCEPTANCE.md) | 75 个正向/反例/故障验收条目；全部产品状态为 not_run |
| [AUDIT_COVERAGE.md](AUDIT_COVERAGE.md) | 上一版三文档各章节的阅读与交叉核对范围 |
| [SOURCES.md](SOURCES.md) | 原稿、v1、用户新要求、外部文档与本版决定分开 |
| [VALIDATION_REPORT.md](VALIDATION_REPORT.md) | 本轮实际执行的文档检查，以及未执行的产品验证 |

不了解全部设计时，先读 Spec S03（知识）、S05（状态）、S11（完成）、S12（画布）。不要将旧架构彩图与本版混用；其中出现过非原生 Cairn 实体和强制流程的错误。本版的 Mermaid 是新方案逻辑关系，不是已运行的拓扑。

## 核心修订

Agent 可以提出候选 Fact，也可以保存没有确定性解析器的摘要/假设。ClaimRevision 是断言正文唯一记录；FactLedger 是根据固定证据评估形成的读视图。模型不能伪造采集回执或自行提升证据等级，但未验证假设可用于受控探索。

工具证据不必先变成 Fact 才能交给 Agent。结果接纳不等于进程退出。审批、会话、工作暂停、完成收敛和前端视图各自有明确生命周期；对应的正常路径与失败反例必须一起验证。

## 机器可读附件

- [contracts.json](contracts.json)：固定枚举、状态转移和接口字段清单；不是已实现完整 OpenAPI。
- [requirements.json](requirements.json)、[plan_tasks.json](plan_tasks.json)、[acceptance_cases.json](acceptance_cases.json)、[audit_findings.json](audit_findings.json)：与正文对应的索引。
- [traceability.json](traceability.json)：需求→章节→任务→验收→发现的反向索引。
- [示例目录说明](examples/README.md)：11 个正例、3 个必须拒绝的反例；全部是离线示意数据。
- [source_manifest.json](source_manifest.json)：未修改原件的字节数、行数与 SHA-256。
- [artifact_manifest.json](artifact_manifest.json)：交付文件清单与 SHA-256，不含自身，防止自引用。

`source/` 原样保留原稿和 v1。它们是审计证据，不是与 v2 并列生效的合同。没有覆盖原件，没有改仓库或提交代码。

## 重跑本包检查

Python 3.10+；文档检查只需标准库和 `jsonschema`，本轮使用版本见 VALIDATION_REPORT。

```bash
python -m pip install -r checks/requirements.txt
python checks/validate_documents.py --verify-manifest --no-write-report
```

上述检查不访问网络，不运行 MAF、PostgreSQL、Supervisor 或浏览器，不发送工具请求。Plan 中的 pytest/Vitest/Playwright 命令是未来产品实施步骤，不能与本命令的结果混淆。

结构映射完整不等于设计没有遗漏。本版仍需按 Plan 在用户真实代码和已锁定发行物中验证；实际能力不支持时应记录并修改相应合同，不能宣称靠文档解决运行问题。
