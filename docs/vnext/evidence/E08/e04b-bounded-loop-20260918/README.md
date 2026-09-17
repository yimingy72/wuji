# E04-B：有限收敛与精确去重（已交付 + 集群复核）

- 日期：2026-09-17/18；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`
- 代码：`21f1484347835111c35188e591f26df51b5ee951`（`work/vnext/k8s/build-25untd3y/source-commit.txt`）
- 镜像：platform `127.0.0.1:56615/wuji-vnext-platform@sha256:c47baa7534783c5be4fd1233238a25aa31f280cab015b4e8d3e2acf69eba865c`
  （`work/vnext/k8s/publish-vsknrrwu/images-published.json`）
- 运行时配置：`k8s-runtime-trial-v1` **revision 4**，本次首次发布 `max_no_progress_rounds: 3`（同批含 `max_reason_runs: 6`、`reason_retry_attempts: 2`、`max_work_items: 8`）
- 范围：与 M2 同一 CASE-A 夹具，公开入口创建 Task `05a6653b-4623-4801-bd9e-13d3f0064b2b`，验证"发布了无进展窗口之后，正在取得进展的循环不会被误停"；真正的停止路径由真实 PostgreSQL + 生产 Scheduler 的定向用例覆盖

## 1. 交付的两条规则

1. **精确去重**：Scheduler 按 (冻结问句, 依据 refs, 方法/能力版本, Profile 摘要, 环境, 输出合同) 重算 canonical digest；某个已受理 Intent 与该摘要命中既有 Work 时，只写一条 `intent.deduplicated` 事件（同时点名 Intent 与 Work、digest 与规则版本），**不创建第二个 Work**。新增依据或换环境会得到不同 digest，属于合法延续；措辞变化不被当成同一问题（只折叠首尾/连续空白）。
2. **有限无进展收敛**：运行时限新增可选 `max_no_progress_rounds`。一轮已结算且没有新材料的 Reason 只有在**没有其它排队/运行中的 Work、没有未满足的 waiter、没有更新的输入在等**时才计数——等待不算卡住。达到窗口时发出一份 `reason.completion_requested`（`reason=no_progress_window`）交给既有完成评审，并置 `blocked_reason='no_progress_window'`，在**新知识**到来前不再生成 Reason；失败重试与操作者阻断不会被新材料解除。另修正：整个 Work 恰是在消费自身退出观察时结算完成，waiter 现在对每条已记录事件重读谓词。

## 2. 本轮集群复核（原文见 `raw/`）

```text
五次决定：wait → propose_intents → wait → propose_completion → blocked
scheduler_state: trigger=9 consumed=9 failure=0 no_progress_count=0 blocked_reason=reason_operator_review
intent.deduplicated: 0    no_progress_window 请求: 0
work_item 7（reason 5 / explore 2）全部 done；AgentRun 7 全部 exited/accepted
Claim 2、Observation 2、捕获 Artifact 2（43 B / 70 B，text/plain, sealed）、completion.reviewed 1
```

- 结论：窗口已发布（3）而 `no_progress_count` 保持 0 —— 循环在**每一代都拿到新材料**时不会被误停，最终仍由 E05 评审缺口交给操作者（`reason_operator_review`），而不是被无进展规则截断。
- 独立评分：`verdict=pass`（`entry.json → registry-oct.json`、答案 `4.2.0`、诱饵 `4.3.1` 未读），见 [`grading.json`](grading.json)。

## 3. 停止/去重的定向验证（真实 PostgreSQL + 生产 Scheduler）

`tests/vnext/test_exploration_loop.py`（本轮 9 项全部通过）：

| 用例 | 断言 |
| --- | --- |
| `test_an_identical_question_is_associated_instead_of_executed_again` | 同一问句第二次被受理（两条 Intent revision）→ 只存在一个 Work；恰好一条 `intent.deduplicated`，`duplicate_of` 命中既有 Work，`problem_digest` 64 位、规则版本前缀 `exact-question` |
| `test_a_repeated_question_with_new_basis_is_a_legitimate_continuation` | 空白差异不改变 digest；basis 顺序无关；**新 basis 或新问句改变 digest**（合法继续） |
| `test_a_published_window_stops_the_loop_once_and_new_material_releases_it` | 窗口=2：第一轮含 seed 材料故不计数（0）；随后两轮各计 1 直到 2 → 恰好一份 `no_progress_window` 请求（带 `window`/`no_progress_count`）+ `blocked_reason='no_progress_window'`；再触发的 generation 不再生成 Reason；用 `_material` 写入新知识后计数归零、标志解除、Reason 重新可运行 |
| `test_a_real_wait_and_live_work_do_not_count_as_no_progress` | 真实 `wait` 登记为 `waiting` 且窗口=1 时计数仍为 0，且不产生无进展请求 |

## 4. 复现命令

```bash
# 1. 发布含窗口的运行时 profile（owner 阶段，幂等）
scripts/vnext/uv.sh run --frozen python ops/vnext/task_launch.py --submit --phase relock \
  --task <template-task> --image <platform> --agent-image <agent> --kali-image <kali> \
  --agent-auth-secret <template-agent-auth> --kali-auth-secret <template-kali-auth> \
  --input-secret trial-m2-input --job-name e04b-relock

# 2. 正式入口创建 Task，再用同一夹具的 case-config + owner 四阶段
scripts/vnext/uv.sh run --frozen python scripts/vnext/exploration_trials.py case-config \
  --suite docs/vnext/evidence/E08/m2-mechanism-loop-20260917/suite \
  --case A-reference --config <trial-config.json> --task <task-id> --out run-config.json
scripts/vnext/uv.sh run --frozen python ops/vnext/task_launch.py --submit --phase all --task <task-id> ...
```

`run-config.redacted.json` 为本次集群实际使用的运行配置（`roles` 与数据库口令已脱敏）。

## 5. 截图

- [`screenshots/e04b-task-topology.jpg`](screenshots/e04b-task-topology.jpg)：工作台（快照模式）绑定本 Task，可见 2 个 Intent（含只在观察字节里出现的 `materials/registry-oct.json` 问题）、2 条 Claim（第二条正文含 `version: 4.2.0`）、2 个 Observation、7 个 WorkItem 与 7 个 AgentRun，以及"任务完成 / 平台审核"面板显示判据 `registry-version` 缺少判定

## 6. 未覆盖

- 真实模型（无网关/Key/额度）、CASE-B 变体对照与 CASE-C 分支仍未运行
- 无进展窗口的"错误语义去重"不做：语义相似只是提示，不合并互相矛盾或适用条件不同的工作（按 §4.6 明确延期）
