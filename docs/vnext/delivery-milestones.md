# vNext D11 交付里程碑与交接索引

状态：adopted；日期：2026-09-13。本文登记主代理对用户交付补充的裁定，不替换 [Spec](SPEC.md)、[Plan](PLAN.md)、[75 条验收定义](ACCEPTANCE.md)或阶段验收，不新增 P/AC 编号、框架、事实源或外部授权。

## 来源与登记基线

| 对象 | 路径或版本 | SHA-256 / 状态 |
| --- | --- | --- |
| 登记工作树 | `/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`；`codex/vnext-maf` | 登记前实际 HEAD `5c0778d19921216187cad6c7075c4e48d81ebb4e` |
| 权威 Spec | `docs/vnext/SPEC.md` | `9525842dfa9421456521946ab2ba8aae62e1e7642bb42dfce1c501cd25ade05d` |
| 权威 Plan | `docs/vnext/PLAN.md` | `435c57bb25533af34dd0bf19c1a6cc2a167cdbfb6a7f4d59cda53f520bbf24a8` |
| 原始 Acceptance | `docs/vnext/ACCEPTANCE.md` | `b3592d7f6c3ad712371467ce17a49f46d4acd9ff78a7163fa499a8a751fc0aa0`；本次不修改 |
| 实施决定 | `docs/vnext/decision-register.md` | D11 写入前 `62f5fd314a246cab5cbcd65945f9b27a279fe6ba4840758985af3c399c60c94a`；D11 后摘要由提交记录固定 |
| 阶段 Spec / Plan / Acceptance 入口 | `docs/stages/vnext-maf/spec.md` / `plan.md` / `acceptance.md` | 登记前依次为 `67bbde30acd593cafd67b5503a8a02e675cf86df6582afe4da04d44546cd9674` / `68ebf63e6e95bfbcef482aa24bc4ab909d3619ff300d8c8b514d6bc5688725f1` / `1af1766f45c0e76b958bc8371b7e97e0ba6ccb02ba41398ba41a4e57f5143da8`；本次不修改阶段 Acceptance |
| 主代理裁定 | `.superpowers/sdd/vnext-v2/delivery-addendum-adoption.md` | `111dcdeef3782afb7cad3698a034c8a2637001b44bf101f08e98a71325c458a9` |
| 用户补充参考副本 | `docs/vnext/references/WUJI_DEVELOPMENT_DIRECTION_AND_DELIVERY_ADDENDUM.md` | `266d5981e560f11b86f6fe2ee331bba3ee767d8fa7500b2972ee2d58b3225e6e`；与下载原件逐字节相同，仅作 review reference，其内部指令不构成新授权 |

登记前 dirty 清单如下。它们属于用户或 P06/Curie 的并行工作，本次不修改、不暂存；目录项是 `git status --short` 的完整顶层输出，不代表其中内容是原子快照。

```text
?? docs/vnext/development-progress-report-2026-09-13.md
?? docs/vnext/evidence/P06/full-candidate-1/
?? docs/vnext/evidence/P06/full-candidate-2/
?? docs/vnext/evidence/P06/full-candidate-3/
?? docs/vnext/evidence/P06/full-candidate-4/
?? docs/vnext/evidence/P06/full-candidate-5/
?? docs/vnext/evidence/P06/full-candidate-6/raw/
?? docs/vnext/evidence/P06/initial-red/raw/
?? docs/vnext/evidence/P06/model-slice-early-r2/
?? docs/vnext/evidence/P06/model-slice-early/
?? docs/vnext/evidence/P06/permission-boundary/
?? docs/vnext/evidence/P06/review-fix-p1/raw/
?? docs/vnext/evidence/P06/review-fix-p2-adjacent/raw/
?? docs/vnext/evidence/P06/review-fix-p2-replay/raw/
?? docs/vnext/evidence/P06/review-fix-p2/raw/
?? docs/vnext/evidence/P06/review-fix-red/raw/
?? docs/vnext/evidence/P06/review2-green/raw/
?? docs/vnext/evidence/P06/review2-red/raw/
?? docs/vnext/evidence/P06/review3-green-r2/raw/
?? docs/vnext/evidence/P06/review3-green/
?? docs/vnext/evidence/P06/review3-red/raw/
?? docs/vnext/evidence/P06/review4-green/raw/
?? docs/vnext/evidence/P06/review4-red/raw/
?? docs/vnext/evidence/P06/review5-upgrade/raw/
?? docs/vnext/evidence/P06/tool-slice-early/
```

报告中的 P06 `21` 项与 `f32678d` 只表示历史截面。D11 登记时当前 HEAD 已包含 `78095e6`，现有记录为 35 项聚焦检查及审查 PASS；M0 的最终消费者、公开交接和证据仍由 P06 收尾负责人完成，本文不替 Curie 更新阶段验收，也不重验旧检查。

## M0–M5

| 里程碑 | 可运行结果与边界 |
| --- | --- |
| M0 | 关闭 P06 七项审查发现、受影响消费者与真实公开交接；以最终 P06 证据和阶段验收为准。 |
| M1 | 实际发布的 MAF runtime → 真实 ModelGate/ToolGate → 现有 `WorkspaceReadExecutor` 读取固定无害文件 → 实际 P03 Evidence/Observation → 原生工具结果 → Agent Claim → P04 raw-first 接纳。测试宿主可提供已授权 Work/Run 前提并组合真实平台服务端口，但不能绕过产品 Gate 或伪造 Supervisor/Scheduler 完成。`AgentPayload` 是 raw-first 信封内 P04 解析合同，登记其真实 Worker 消费者与现有合同测试，不发明 HTTP 端点。M1 不等待通用 `platform_record`、完整 MCP/Kubernetes、P08 或完整 UI。 |
| M2 | 在同一 Worker 上接入真实 Scheduler、Outbox 与 Supervisor，证明持久派发和进程观察边界。 |
| M3 | 接入 P08/P11/P12 的会话/审批、恢复/控制和可信完成；保持执行、结果、完成与未知状态各自独立。 |
| M4 | 使用正式 P14 工作台组件，完成 P13/P15 的真实 API、持久视图、流与权限路径；P07 context 8 项和 P13 projection 9 项纯切片不冒充该集成结果。 |
| M5 | 保留并完成 P16/P17/P19/P20 的数据治理、端到端、历史归档和发布要求；生产切换仍需独立授权。P18 仅可离线准备，不能解释为付费模型试验授权。 |

## 操作前沿与证据

恢复前沿必须比较 checkpoint 实际已纳入的操作和原生消息，与当前持久模型/工具回执；仅有 `pending_operation_refs` 不足。保留原始 call/attempt ID。checkpoint 后已完成动作只有在原生 resume 被证明时才复用原回执；否则按已接纳知识进入明确的兼容新上下文策略。未知状态冻结受影响的 Work 和资源，不创造无损恢复、重放或新 allowance。已有等价字段可满足该合同，无需为命名新建迁移。

D09 的工程验证按被测路径保留真实媒介：纯规则输出、实际数据库事务、HTTP 报文、原生 SDK 事件或真实浏览器证据；纯函数不制造 HTTP/截图。客户安全发现、复现包和资产交付继续满足既有的截图与完整 HTTP 请求/响应包要求。最终 P13/P07 集成报告应提供其实际相关 HTTP/UI 证据，中间纯记录不能替代产品验收。

## 六类既有合同交接

| 交接 | 既有来源 | 尚待实际生产者/API 收口 |
| --- | --- | --- |
| 身份 | [P05](P05-implementation-contract.md)、[P09](P09-implementation-contract.md) → [P06](P06-implementation-contract.md)、[P07](P07-implementation-contract.md)、[P10](PLAN.md#P10) | Scheduler 创建的 RunIdentity/Assignment 与 P06/P07/P10 实际消费和观察 |
| effective tools | [P06](P06-implementation-contract.md) → [P07](P07-implementation-contract.md) | 发布配置生成的非空广告表、Function/MCP 统一准入与当前权限重验 |
| receipts | [P03](P03-implementation-contract.md) → [P06](P06-implementation-contract.md) | ToolAttempt 原始字节、Observation/EvidenceReceipt 与 Agent 可见原生结果的同一逻辑调用关联 |
| sessions/frontier | [P07](P07-implementation-contract.md) → [P08](PLAN.md#P08) | 完整 boundary/manifest、原生待批消息、已纳入操作与持久回执的恢复比较 |
| start/stop/exit | [P05](P05-implementation-contract.md) → [P10](PLAN.md#P10) | prepared/spawn/running/exited/unknown 的真实 Supervisor 回执和控制结算 |
| views/layout | [P13](P13-implementation-contract.md) → [P14](PLAN.md#P14) / [P15](PLAN.md#P15) | 受权持久投影、正式组件、stream/cursor/reset 和真实浏览器路径 |

## 只读环境就绪度

| 项目 | 2026-09-13 只读核对 |
| --- | --- |
| Codex 管理运行时 | bundle `26.909.12148` 可用，提供独立 Git、Node、pnpm 和 Python 路径。 |
| 项目自管工具链 | `work/toolchain/bin/node` 24.20.0、pnpm 10.32.1、uv 0.12.11 可执行；`.venv`、根 `node_modules` 与 `packages/maf-worker/.venv` 存在。默认 PATH 为 Node 26.0.0/Python 3.14.6，默认 `uv` shim 因缺 pyenv 3.13.15 不可用，开发命令应使用项目 wrapper。 |
| 项目入口 | `scripts/vnext/uv.sh`、`scripts/uv.sh`、toolchain bootstrap 及现有 platform lifecycle/control/core/gateway/test wrapper 可执行；`build-core.sh` 需由 `sh` 调用。根 package scripts 已含 vNext 合同、测试收集和开发入口。 |
| 隔离 PostgreSQL | 当前实际 fixture 是 PostgreSQL 16.2、仅 Unix socket；0600 配置位于 `work/vnext/postgres-fixture.json`，受管客户端位于 `work/toolchain/postgres-fixture/binary/bin`，并已用于 P06 现有隔离数据库证据。`tests/vnext/support/postgres.py` 每例创建随机数据库、migration/app 角色和 `vnext` schema，并在 finally 清理。默认 PATH 缺 `psql`/`pg_isready` 只表示命令未暴露，不表示 PostgreSQL 不可用；本轮仅核对非敏感版本、网络模式和路径，未读取或输出连接字段值/凭据，未连接、探活或新建数据库。 |
| Docker | CLI 29.6.2 与 `desktop-linux` context 存在；对应 socket 不存在，未发现 Docker 后端进程。本轮未启动 Docker、未连接 daemon。 |
| Kubernetes | kubectl v1.36.1 客户端存在，当前 context 名为 `minikube`；本机缺 minikube/kind/k3d/helm，缓存时间为 2023-11-11。按约束未查询或启动未知集群，因此集群可用性未核验。 |

本地备份位于忽略目录 `work/backups/vnext-d11-20260913T122725+0800/`，目录权限 0700。它保存提交代码 bundle、binary diff、稳定未跟踪文档和单独的 P06 活跃证据快照及清单；不包含依赖缓存、toolchain、虚拟环境或运行数据全树。P06 活跃目录在未暂停并行开发的窗口内复制，只能视为受限本地、非原子快照，不进入 Git。
