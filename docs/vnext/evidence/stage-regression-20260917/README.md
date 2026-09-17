# 阶段统一回归（2026-09-17）

- 日期：2026-09-17；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`；被测代码 `db4954a`（下含 P12-E / P15 ViewStream / T8 三个切片）。
- 环境：本地 fixture PostgreSQL 16（每个用例独立库 + 真实应用角色/迁移）、本地 Docker/Kubernetes 集群 `wuji-vnext-test`、入口 `http://127.0.0.1:44180/`。
- 目的：把当前所有已交付切片集中在一次回归里跑完，并修掉暴露出来的测试与 CI 阻塞。**这不是产品验收通过结论**，
  未覆盖项仍在各切片证据包与 [acceptance.md](../../../stages/vnext-maf/acceptance.md) 里逐条记录。

## 1. 结果

| 检查 | 命令 | 结果 |
|---|---|---|
| vNext Python 全量 | `./scripts/vnext/uv.sh run --frozen pytest tests/vnext -q` | **535 passed / 0 failed / exit 0**（861.66s）[原文](raw/pytest-full-2.txt) |
| v2 合同 | `scripts/vnext/generate_contracts.py --check` | exit 0 [原文](raw/contracts-check.txt) |
| Node Supervisor | `node --test tests/task-workers/*.test.mjs` | exit 0 [原文](raw/node-supervisor.txt) |
| 拓扑 Vitest | `vitest run --config tests/topology/vitest.config.ts` | 5 files / **29 passed** / exit 0 [原文](raw/vitest-topology.txt) |
| web typecheck + build | `pnpm --filter @wuji/web build` | exit 0 [原文](raw/web-build.txt) |

第一次全量运行是 **532 passed / 3 failed**（[原文](raw/pytest-full.txt)），暴露了两个真实问题，均已修复后复跑全绿：

1. **T8 接口变更打漏了一个测试替身**：`tests/vnext/test_maf_child_transport.py::_WrongProfileReceiptTransport`
   仍按旧的 `query(operation_id)` 签名实现，`task_id` 关键字传入后抛 `TypeError`。修复为转发 `task_id`（不改生产语义）。
2. **0016 升级检查没有跳过新 head**：`test_session_writer_exit_migration` 逐个 monkeypatch 后续 head 的升级函数，
   新增 `upgrade_view_stream` 后 0025 会被应用，破坏该用例“停在 session head”的前提。补上跳过。

顺带补齐的 CI 阻塞（此前 `pnpm test:vnext` 在 CI 上会直接收集失败）：

- `packages/maf-worker` 的 dev 组加入 `kubernetes==36.0.3`（`wuji_task_runtime` 的测试需要；锁文件同步更新），
  否则 `test_pod_runtime.py` / `test_configure_refresh.py` 无法收集；
- `test_configure_refresh.py` 改为断言当前的 `pod_runtime.tasks[]` 列表形态（refresh 只更新 bootstrap Task 的镜像）；
- CI 的拓扑 Vitest 步骤从 `apps/web/src/features/topology`（该目录没有测试文件，vitest 会以退出码 1 结束）
  改成 `--config tests/topology/vitest.config.ts`。

## 2. 覆盖与不覆盖

- 覆盖：P02–P13 的读写/权限/投影/布局/会话/Scheduler/Control/P05 控制面、P12 完成协议全套、P13 投影与快照、
  P15 布局与 ViewStream、T8 每 Task 端点与运行时路由，全部在真实 PostgreSQL（每用例独立库、真实应用角色与迁移）上执行；
  需要 `kubernetes` 包的两个文件现在也在同一 venv 中真实执行，不再跳过。
- 不覆盖：真实 K8s 故障矩阵（本轮未重跑，各切片证据包各自记录其真实集群结果）、真实模型网关计费、
  P16–P20 阶段、以及各证据包中已列明的“未覆盖”项。CI 远端是否真正变绿需要 GitHub 上的运行记录为准。
