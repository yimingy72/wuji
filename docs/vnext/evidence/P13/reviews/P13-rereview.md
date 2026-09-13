# P13 两项 P2 定向独立复审

日期：2026-09-13
结论：**PASS — `P13-review.md` 的两项 P2 在修复提交 `69e3a1d906b3f0948651afc12b176f03ee6281dc` 中均已关闭。**

本结论只覆盖 `live/history + snapshot` 选择边界，以及 snapshots index / record detail 的实际 410 与冻结合同一致性；不提升完整 P13、P14、P15 或其他阶段状态。

## 独立性、固定来源与方法

- 本复审者是主代理直接派出的独立 SOL/xhigh，未参与 P13 原实现、初审 findings 或 Locke 的修复与测试执行；未创建任何下级 agent。
- 原代码：`44ddc68e48e1c36974cec7e705d1cd3812c7a031`。
- 修复代码：`69e3a1d906b3f0948651afc12b176f03ee6281dc`。
- 证据提交：`3b6b4551fe16c8205588c4baa2381c357b4e0650`。
- 固定输入为 `.superpowers/sdd/vnext-v2/P13-review.md`、`docs/vnext/evidence/P13/review-fix/report.md`、修复提交的 4 个文件及证据提交中的绑定、结果和完整 HTTP 记录。
- 工作树没有 `.codegraph/`，因此直接读取不可变 Git 对象和归档证据。本复审未运行 pytest、PostgreSQL、HTTP、生成器、服务或浏览器；下文 `3 passed in 3.16s` 与生成检查均由 Locke 执行，本复审只核对其代码和原始证据。

修复提交只改：

1. `packages/wuji-core/src/wuji_core/projection/snapshots.py`
2. `packages/contracts/openapi-v2.yaml`
3. `packages/contracts/src/v2/generated.ts`
4. `tests/vnext/test_view_snapshots.py`

`binding.json` 中这四个文件的 SHA-256 与修复提交 Git 对象逐一一致，因此测试时 working-tree bytes 与随后提交内容的绑定成立。

## P2-1 · live/history 与 snapshot 身份混写

状态：**PASS / closed**。

`ProjectionRepository.topology` 现在执行：

```python
if (query.mode.value == "history") != (query.snapshot_id is not None):
    raise DomainError("INVALID_SCHEMA", 422)
```

这恰好只允许 `live + snapshot_id=None` 和 `history + snapshot_id`。检查位于事务和 materialization/view 创建之前，因此 `live + 历史 snapshot` 不会生成内容来自历史、身份标为 live 的新视图；`history` 缺 snapshot 也同样在读取前拒绝。

Locke 执行的 `test_history_lists_only_saved_views_and_freezes_its_opaque_page` 同时证明了正负路径：

- `history + H1` 首屏返回 200，并固定 H1；
- 使用同一 `mode=history`、H1、limits 和 continuation 返回 200，`view_id` 与 `snapshot_id` 均保持原值；
- `live + H1` 返回 422 / `INVALID_SCHEMA`；
- `history` 缺 snapshot 返回 422；未知历史 snapshot 保持既有 410 / `HISTORY_UNAVAILABLE`。

归档 `raw/578af394c892/p13-http-exchanges.jsonl` 保存了上述实际请求/响应。可见 history 首屏和 continuation 均为 200，随后 `mode=live&snapshot_id=H1` 为 422；这不是只靠测试名或布尔自报得出的结论。

## P2-2 · snapshots/records 的 410 合同缺失

状态：**PASS / closed**。

冻结 OpenAPI 现在为以下两个 GET 显式声明 `410: Expired`：

- `/api/v2/tasks/{task_id}/snapshots`
- `/api/v2/tasks/{task_id}/records/{record_type}/{record_id}`

同一修复提交的 TypeScript 生成物在 `listTaskSnapshotsV2.responses` 和 `getTaskRecordV2.responses` 中均包含 `410: components["responses"]["Expired"]`。Locke 另执行生成检查并记录：`Generated Python and TypeScript v2 contracts match OpenAPI.`，退出码 0。

`test_expired_view_and_snapshot_return_explicit_410_errors` 实际使 snapshot materialization、拓扑 continuation cursor 和 snapshot-index cursor 过期，并断言：

- record detail + 过期 snapshot 返回 410 / `SNAPSHOT_EXPIRED`；
- snapshots + 过期 index cursor 返回 410 / `VIEW_EXPIRED`；
- 相邻 topology continuation 仍返回既有 410 / `VIEW_EXPIRED`。

归档 `raw/52c6f113d302/p13-http-exchanges.jsonl` 保存了三个实际 410；其中前两项分别对应本 finding 的 records 与 snapshots 公开合同。`test_openapi_declares_actual_410_responses_for_snapshot_reads` 则直接读取冻结 OpenAPI 并要求两个响应槽都存在。三者合起来覆盖“运行时实际返回”和“冻结合同声明”，未通过删除错误、改成 404 或放宽过期守卫实现。

## 复用的 Locke 执行证据

Locke 的定向命令为：

```text
WUJI_TEST_EVIDENCE_DIR="$PWD/docs/vnext/evidence/P13/review-fix/raw" ./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_view_snapshots.py::test_openapi_declares_actual_410_responses_for_snapshot_reads tests/vnext/test_view_snapshots.py::test_history_lists_only_saved_views_and_freezes_its_opaque_page tests/vnext/test_view_snapshots.py::test_expired_view_and_snapshot_return_explicit_410_errors -q
```

结果：退出码 0，`3 passed in 3.16s`。三项测试分别对应：

1. 两个 OpenAPI 410 声明；
2. history 首屏/continuation 正常及 live+snapshot 422；
3. records/snapshots 的两个实际 410（并保留相邻 topology 410）。

生成检查：

```text
./scripts/vnext/uv.sh run --frozen python scripts/vnext/generate_contracts.py --check
```

结果：退出码 0，Python/TypeScript 生成物与 OpenAPI 一致。完整绑定见 `docs/vnext/evidence/P13/review-fix/binding.json`；22 组完整 HTTP、原始 SQL/身份事件、摘要索引和截图均保存在同一证据目录。本复审没有重跑或改写这些结果。

## 范围边界

- 未复核或声明 P13 其余 12 项 runtime slice、pure builder、完整投影权限矩阵或性能。
- 未覆盖 P14 Layout、P15 stream、浏览器 current/history 切换、P08、M2、生产环境或外部目标。
- 生成物一致性只确认本 finding 的两个 410 响应槽及 Locke 已执行的全文件生成检查，不把同一分支上的其他 OpenAPI 改动带入 P13 结论。
- 本范围没有发现新的 P1/P2 或原 finding 的残留缺陷。两项 P2 可按 **PASS / closed** 交回主代理。
