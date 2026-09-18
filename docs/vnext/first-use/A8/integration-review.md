# A8 独立首用审查（初始工作包）

标题状态：现场未验收。本文不是产品通过报告；`acceptance-results.json` 的 87 项仍全部 `not_run`，直到 A0 在固定集成 SHA 上提供真实服务、数据库、MAF/Gate、浏览器和许可证据。

## 固定输入

| 项目 | 记录 |
| --- | --- |
| 开工基线 | `b1ba8ec6a7205230f6ea2067e273c82c447d977b` |
| A0 合同候选 | `a43b0f5`（A8 分支未合并该提交，driver 按其 C01/C02/C03 命名准备） |
| A8 代码提交 | 交付时填写；不得把文档提交 SHA 当作被测代码 SHA |
| 运行模式 | 尚未运行；F1/F2 fixture 仅 `mechanism_synthetic` |
| 现场许可/预算 | 未由 A8 读取或推断；DG2/DG3 不自动触发 |

## 基线发现

| 严重度 | 位置 | 发现与复现 | 阻断 | 负责方 |
| --- | --- | --- | --- | --- |
| P1 | `scripts/vnext/run_acceptance.py::build_report` | 固定目录只读取 `docs/vnext/acceptance_cases.json` 的 75 项；`tests/vnext/test_acceptance_report.py::test_catalog_has_all_cases_and_default_report_is_incomplete` 明确断言 75，不覆盖本批 87 项、DG0–DG3、F1/F2 或用户首用链 | A8 不能用旧 P17 报告代替本批验收 | A0/A8 |
| P1 | `tests/vnext/test_end_to_end.py`、既有 E08 证据 | 历史机制链有真实局部证据，但不能据此证明本批从正式浏览器新建 Task，再经 A0 BFF create/start/readiness/launch、材料读链、pause/cancel 的同一候选闭环 | DG1/E2E-01、E2E-02、E2E-03、E2E-05 | A0 + A2–A7 |
| P1 | `scripts/vnext/exploration_trials.py` | 既有 CASE-A/B/C 是工作区材料/owner launcher 试验，不是本批 F1 的随机一次性 marker→第二次模型请求，也不是 F2 两变体的 HTTP 指路分支；它不能冒充模型正文送达 | MAT-02/03、E2E-02/03 | A5/A6/A8 |
| P1 | `docs/stages/first-use/acceptance.md` | A0 首批合同 `a43b0f5` 已冻结 entry path 与 material v2，但该提交本身没有把真实 BFF/launch/readiness/pause/cancel 运行证据变成通过结论 | DG0 仅可列 implemented/under_review，DG1–DG3 仍 not_run | A0 |
| P1 | 本目录 `acceptance-results.json` | 87 项模板必须逐条绑定 candidate SHA、命令、实际退出码和证据；空项保持 `not_run`，阻断项用 `blocked` 和具体输入，不得按数量汇总成 pass | 全部 DG | A8 |

## 本次交付的独立 driver

`scripts/vnext/first_use_acceptance.py` 是真实本地 BFF driver，不是 report builder。它固定执行以下公开链：

```text
POST /api/v2/tasks (201, ready/pause)
  → GET /api/v2/tasks/{task_id}
  → GET /api/v2/tasks/{task_id}/readiness  (start 前无模型/目标动作)
  → POST /api/v2/tasks/{task_id}/commands {start, expected_version}
  → GET task + GET /launch + GET /readiness
  → POST command {pause} → GET task 核对状态
  → POST command {cancel} → GET task 核对状态
  → 外部提供的 Task/Run/ToolCall/Artifact/material/read_set 读链核对
```

driver 只接受 `localhost`/`127.0.0.1`/`::1` HTTP BFF；不访问 provider、目标、owner/internal route，也不读取答案文件。认证值只从环境变量读取，日志和证据中的 Authorization/Cookie 始终为 `[REDACTED]`。HTTP 失败/服务不可达分别返回 `FAILED`/`BLOCKED`，不会写成功状态。

## 当前关口结论

| 关口 | 结论 | 首个缺口 |
| --- | --- | --- |
| DG0 | under_review | A0 候选需集成后由 A8 在固定 SHA 独立检查生成 wire、权限和旧兼容 |
| DG1 | not_run | 尚无同一构建的浏览器新建→正式 BFF→Scheduler/MAF/Gate→fixture→停止证据 |
| DG2 | blocked | A8 不读取 Key；需 A0/A6 提供受信 SecretRef、预算/数据许可与真实 Gate→LiteLLM→DeepSeek 记录 |
| DG3 | blocked | 当前没有 A8 可使用的指定现场实例许可、运行入口和真实工具停止证据；不索取不存在的 Run |

## 复测规则

收到 A0 固定候选 SHA 后，A8 先读取实际 diff 和交接，再独立运行受影响用例；实现者命令不直接转为 `pass`。每项结果同时记录 `test_id`、candidate SHA、环境/镜像、命令、退出码、状态和 evidence refs。没有截图或完整脱敏 HTTP 包的成果保持 `not_run`/`blocked`，不补写通过。
