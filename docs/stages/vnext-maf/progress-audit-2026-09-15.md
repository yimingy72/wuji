# vNext 进度审核 — 2026-09-15（对照 Spec / Plan 全量任务面）

- 审核者：当前会话主代理；本文只核对现有提交、测试与证据，不重跑已记录的单项证据。
- 权威来源：[Spec](../../vnext/SPEC.md)、[P00–P20 Plan](../../vnext/PLAN.md)、[75 条验收](../../vnext/ACCEPTANCE.md)、[验收状态](acceptance.md)、[实施决定](../../vnext/decision-register.md)。
- 工作树：`work/worktrees/vnext-maf`，分支 `codex/vnext-maf`，HEAD `788c49e`（本轮系列提交见下）。
- 本轮最终测试截面：真实隔离 PostgreSQL 的完整可运行集合 **411 passed / 0 failed（394s）**，原始输出 `work/vnext/p11c/audit-suite.txt`。

## 1. 结论摘要

平台基础（P00–P06）与执行链的局部切片（P07 M1、P09、P10 M2）已在前序会话验收并继续复用。本次会话把**三个此前只有设计或局部证据的工作面**推进到「有真实 K8s/PG 证据」：

1. **P15-L 个人布局 CAS**：合同、0018 迁移、RLS、`If-Match`、BFF、工作台读写全部落地，并在真实浏览器验证刷新保留与 409 冲突；实测发现并修复「409 后自动回写」缺陷。
2. **P08-S 会话/操作前沿收口**：红色基线清零，修掉「恢复后的批准回调无法证明原始批准身份」这一真实产品缺陷，并把 P06 前驱映射改为按 attempt 唯一匹配 + fail closed；F2–F5 四项平台复审残留逐项核对关闭。
3. **P11-C 创建与控制**：`POST /api/v2/tasks`（0019 迁移 + 发布 profile 目录 + SECURITY DEFINER 创建函数）、owner 侧 admission 发布、真实 K8s 的 `start/pause/cancel` 回执与 **cancel 真正删除运行中的 Task Pod**；并定位/修复 runtime 的两处可诊断性缺陷与「资源按 attempt 分代」根因。

仍未进入实现或未验收的主工作面：**P12 可信完成、P13/P15 ViewStream、P16 治理、P17 集中验收、P18/P19/P20 发布物与切换**；P07/P08/P11 的完整范围与生产身份也未收口。

## 2. P00–P20 逐项状态

| 任务 | 当前状态 | 依据 / 缺口 |
| --- | --- | --- |
| P00 基线与来源 | accepted（本项） | acceptance 表；本轮未改动 |
| P01 SDK 探针 | accepted（局部能力） | SDK/watchdog/离线渲染原证据 |
| P02 合同与测试底座 | accepted（本项） | 合同生成/校验；本轮 `contracts:check:v2` 通过 |
| P03 规范持久化与证据 | accepted（本项） | 53 项 + 修复；本轮修复两处 fixture 漂移（`work_dependency` 需 control 能力、`test_capture_transactions`） |
| P04 知识接纳与评估 | accepted（本项） | 24 项 + 可见性/新鲜度；本轮 `AgentPayload` 边界断言改到真实执行点 |
| P05 控制与容量 | accepted（局部） | 状态机测试全绿；本轮修掉「等待输入恢复需要生产 SessionRepository」的 fixture 缺口 |
| P06 模型/工具准入与账本 | accepted（局部） | 35 项等；本轮修掉 per-attempt 前驱映射与两处过期期望 |
| P07 ContextBundle pure slice | complete | 原证据 |
| P07 M1 hosted runtime | reviewed / passed（切片） | 原证据；**完整 SDK/runtime 合同仍 partial** |
| P08 会话与审批 | in-progress（本轮显著推进） | 红色基线 3 项清零；F2–F5 现状核对关闭（[记录](../../vnext/evidence/P08/reviews/P08-residual-closure.md)）；**仍缺**：固定 memory/原生 compaction 的真实 child、GC、跨进程半发布、旧批准边界全量 |
| P09 Scheduler | reviewed / partial | M2 限定链通过；其他 work kind 与 failure/retry 未全验收 |
| P10 Supervisor | M2 host/child reviewed / passed（限定） | 原证据 + 本轮 K8s fresh Task 的 Pod 生命周期（创建/停止） |
| P11 控制与恢复集成 | partial（本轮推进最大） | 创建入口 `d0204db`、admission `8d6c972`、K8s 回执与 Pod 停止 `c9e23a3`；**仍缺**：owner 工具在首次激活前定稿 definition（含 `worker_profiles`）与发布 `session_capability`、initial Intent/Work 建立、worker 往返、生产 OIDC 与失败域集成 |
| P12 可信完成 | not implemented | precheck/quiescing/settlement/报告冻结未实现 |
| P13 受权图投影与 API | backend reviewed / M4 partial | topology/snapshots/records + 独立 K8s API；本轮补 Layout；**ViewStream 未实现** |
| P14 TopologyFlowCanvas | reviewed / partial | 画布/列表、记录详情、历史快照、布局 CAS 均已实测；生产 OIDC 与规模 p95 未测 |
| P15 视图/历史/浏览器 | partial | 记录详情、历史选择、Layout CAS 有永久证据；ViewStream、Artifact 预览、重连/reset 未实现 |
| P16 数据治理与观测 | not run | 保留/GC/purge、访问审计未实现 |
| P17 集中机制验收 | not run | 75 条 AC 尚无整体汇总运行；`check_all.sh` 未建立 |
| P18 离线效果评测 | not run | 仅计划；真实收费模型试验需单独授权 |
| P19 历史只读归档 | not run | 归档解析与切换演练未实现 |
| P20 新发布物与切换 | not run | 发布清单、独立停机与切换未开始 |

## 3. 本轮会话增量（提交 → 证据）

| 提交 | 内容 | 证据 |
| --- | --- | --- |
| `b465238` + `e97eab8` | P15-L 布局 CAS：合同/0018/RLS/repository/BFF/工作台 + 证据包 | [P15-L](../../vnext/evidence/P15/layout-cas-20260915/README.md)（含 409 回写缺陷修复前后对照） |
| `93f2fc6` | 恢复批准回调身份修复；红色基线清零；三处过期期望 | 20 passed + 117 passed；见 `deferred-suite-failures` |
| `2366969` | `work_dependency` 需 control 能力的两处 fixture 修复 | 46 passed |
| `cc65fef` | 控制 fixture 按生产接 `SessionRepository`，等待输入经 `save_delivery` 解析 | `test_p05_fix_round1`、`test_work_state_guards` 通过 |
| `0245fae` | P08 四项残留现状核对 | [P08 残留关闭记录](../../vnext/evidence/P08/reviews/P08-residual-closure.md) |
| `d0204db` + `51302c3` | Task 创建入口（0019、发布 profile 目录、`create_task`） | [P11 创建证据](../../vnext/evidence/P11/task-creation-20260915/README.md)（K8s 201/幂等/409） |
| `8d6c972` + `56d5cf1` | owner admission 发布；K8s start/pause/cancel 回执 | [P11 admission 证据](../../vnext/evidence/P11/task-admission-control-20260915/README.md) |
| `c9e23a3` | cancel 真正删除运行中的 Task Pod（5s），Task 保持 reconciling、不伪造退出 | [P11 pod-stop 证据](../../vnext/evidence/P11/pod-stop-20260915/README.md) |
| `56ba97d` / `b5cc4ca` | runtime dispatch 输出有界错误码；Pod 环境非 ready 不再静默 | 上表证据第三/四节 |
| `905fd51` | **资源按 runtime attempt 分代**（修 inbox 身份冲突根因） | 29 + 22 passed |
| `47d9778` / `49bcb2a` / `4c290fc` / `788c49e` | dispatch 停顿诊断、代次守卫、attempt 身份接线清单 | 同 pod-stop 证据包 |

此外本轮清理两项环境债：四个 Deployment 的过期凭据以部署签名键重签（24h），agent/platform/kali/web 全平面按提交重建并滚动到同一 revision。

## 4. 对照 Spec 的关键差距（按能力，不按任务号）

1. **执行闭环尚未闭合**：新建 Task 已能创建、发布 admission、生成并运行 Pod（2/2 Running），但还缺「首次激活前定稿 definition（附 `worker_profiles`）→ 发布 `session_capability` → 建立初始 Intent/Work → scheduler 租出 → assignment 到达 supervisor → worker 执行 → 干净退出观测」这一段 owner 接线；当前 dispatch 循环干净空转（`observed: 0`）。
2. **正式身份与授权入口**：浏览器入口仍是本地机制会话，生产 OIDC、项目选择、写命令授权未实现（P11 产品面）。
3. **完成协议与报告**：P12 全部未实现，因此任务无法进入可信完成/报告冻结。
4. **视图流与治理**：ViewStream（受权 revision、opaque cursor、SSE、duplicate/gap/reset、权限变更关流）与 P16 保留/GC/purge、访问审计未实现。
5. **集中验收与发布**：P17 的 75 AC 整体汇总、P18 离线评测工具、P19 归档演练、P20 发布清单与切换均未开始；真实收费模型与生产出口需单独授权。

## 5. 测试与证据现状

- 本轮最终截面：`411 passed / 0 failed`（真实隔离 PostgreSQL，394s）。
- 另有需部署运行时依赖的测试（`test_configure_refresh.py`、`test_k8s_runtime.py`、`test_pod_runtime.py`）需 `PYTHONPATH=packages/task-runtime/src:ops/vnext/.venv/lib/python3.13/site-packages`；本轮已在该环境跑过 29 passed（pod/configure/task-runtime）。
- 永久证据包：P15-L、P11（创建、admission/控制、Pod 停止）、P08 残留关闭记录；每包含截图、完整 HTTP/SQL、绑定与哈希。
- 已知延期项与历史缺口集中在 [deferred-suite-failures-20260915.md](../../vnext/deferred-suite-failures-20260915.md)（两类均已关闭）与各阶段 acceptance。

## 6. 环境现状

- `44180`（Kubernetes LoadBalancer）正常；`api`/`runtime`/`scheduler`/`gates`/`wuji-web` 均 Running。
- 镜像：`api`/`runtime` = `56ba97d` 平台镜像；`scheduler`/`gates` = `8d6c972`；`wuji-web` = `8d6c972` web 镜像。下一次部署应把它们统一到含 `905fd51`（attempt 分代）的 revision。
- 数据库 head=`vnext_0019_p11_task_creation`；存在 fixture Task（cancelled，runtime_attempt=2）与本轮新建 Task（`6451e9f2…`，run/running，Pod 就绪、等待 Work）。

## 7. 建议的下一步顺序

1. **P11-C 收尾（最高优先）**：把「创建 → 定稿 definition（附已发布 harness profiles）→ admission/资源/Service/runtime/gates 接线 → 发布 session capability → 建立初始 Intent/Work」实现为一条 owner 命令，并在新 Task 上取得 worker 执行与干净退出观测。
2. **P12-T 可信完成**：precheck、quiescing、有限结算、ReportCommit/Delivery、迟到反证与 abort-close。
3. **P15-S ViewStream**（依赖 P08/P11/P12 事件稳定）→ P15-A/P16 治理。
4. **P17 集中机制验收**：按 AC 组织一次统一运行并归档；随后 P19 归档演练、P20 发布物与切换（需单独授权）。

## 8. 审核结论

本轮把「创建入口 + 代次化执行环境 + 控制命令受理与真实停止」从设计推进到了有 K8s/PG 证据的状态，并修掉 4 个真实产品缺陷（批准身份、前驱绑定、dispatch 可诊断性、attempt 分代资源）与多处测试/夹具漂移；测试面全绿。但按 Spec 的整体目标衡量，**执行闭环、完成协议、视图流与治理、集中验收与发布仍是未完成的主工作面**，当前状态应记为「P11 部分交付、P08 显著推进、其余按 acceptance 表」，不构成阶段整体 accepted。
