# 文档验证报告

**文档日期：2026-09-13；版本：2.0-review。**

以下记录由实际运行 `python checks/validate_documents.py` 生成；容器记录时间为 `2026-09-12T17:11:41+00:00`（可能与对话所设日期/时区不同，未据此改写源文档日期）。

- Python：`3.13.5`
- jsonschema：`4.26.0`
- 本轮检查结果：**10/10 项通过**。
- 产品验收状态：**75 条均为 not_run**。

| 检查 | 结果 | 实际覆盖 |
|---|---|---|
| JSON文件可解析 | pass | 26 JSON files parsed with duplicate-key/nonfinite rejection |
| 编号唯一且连续 | pass | 40 requirements / 21 tasks / 75 acceptance cases / 34 findings |
| 需求与验收交叉引用 | pass | All indexed references resolve; all planned product cases remain not_run |
| 计划依赖与正文一致 | pass | P00–P20 ordered dependency graph is acyclic; tests match plan text |
| 追溯矩阵一致 | pass | 40 bidirectional requirement entries consistent |
| 原件摘要与复审定位 | pass | 9 archived originals unchanged; 34 excerpts match recorded lines |
| 状态与示例合同一致 | pass | State endpoints valid; terminal states remain terminal; required fields match example-profile schema |
| 示例正反例与基本不变量 | pass | 11 positive examples accepted / 3 explicit negative examples rejected; basic identity/watermark invariants checked |
| 代码片段静态语法与围栏 | pass | 18 Python blocks AST-parsed only; 2 TypeScript blocks not compiled or executed |
| 当前文档本地链接与占位符 | pass | 66 current-document local file/explicit-anchor links resolve; no unresolved placeholder markers; external and archived URLs not revalidated |

## 校验器修正记录

打包复核曾发现生成报告中的检查说明包含被扫描的占位标记词，导致报告扫描自身时误报。已改写该说明并重新执行全套文档检查，未关闭该项检查。

## 这份结果不证明什么

没有安装/执行 MAF Agent、模型网关或真实模型；没有运行 PostgreSQL/RLS/并发测试；没有启动 Supervisor/Kubernetes/外部工具；没有编译 React Flow/TypeScript 或跑浏览器；没有验证 Mermaid 布局；没有运行 Plan 的产品pytest/Vitest/Playwright。Python块只AST解析，导入与测试逻辑未执行。JSON示例schema只覆盖明示示例profile，并非已完成OpenAPI。

需求映射和数量只能证明索引有对应项，不能证明架构正确、完全无遗漏或CTF/靶场效果。34项复审发现是人工文档推理结果，不是34个已复现产品故障。source摘要证明原件未修改，不证明原件里每个陈述真实。

最终打包后另运行 `python checks/validate_documents.py --verify-manifest --no-write-report`，防止改写本报告而循环改变清单；该命令退出码在交付时检查。本轮没有改用户仓库或提交实现代码。
