# P11-C 收尾计划：从产品入口到真实 worker 往返

- 状态：in-progress（主代理设计并执行）
- 日期：2026-09-15
- 工作树：`work/worktrees/vnext-maf`，分支 `codex/vnext-maf`
- 权威来源：[Spec](../../vnext/SPEC.md)、[P00–P20 Plan](../../vnext/PLAN.md)、[验收](acceptance.md)、[决定 D18](../../vnext/decision-register.md)、[下一项执行计划](next-development-plan-2026-09-15.md)

## 1. 背景与缺口

`POST /api/v2/tasks` 已能创建 Task，`publish_task_admission` 已能把该 Task 变成可调度对象，但创建后的 Task 仍无法真正跑起来，缺口在 owner 侧：

1. 创建入口写入的 definition 只有 `task/start_points/model_profile/runtime_profile/lock_digest`，没有部署已发布的 `worker_profiles`，激活后 runtime 会以 `worker_profile_unavailable` 拒绝。
2. 租户没有任何 `session_capability` 行，Session 工作种类拿不到 capability（`CAPABILITY_UNAVAILABLE`）。
3. 新 Task 没有初始 Intent/WorkItem，scheduler 无可派发工作。
4. 新 Task 的 attempt 资源（agent/kali ConfigMap、Secret、PVC）、固定名 Service 选择器、runtime `pod_runtime`/`task_ids`、gates `executors[].binding` 都还指向 fixture；此前靠 `work/` 下的原型脚本手工克隆对象，不是可复现的 owner 动作。
5. `executor_registration` 只有 fixture 一行，绑定的是 fixture 的 receiver/environment。

已确认的设计约束（必须遵守，来源见上文证据）：

- definition 必须在首次激活前定稿：permit 绑定最早一条 `task.started` 的 `definition_digest`，激活后再改必然 `PermitDenied`。
- 一次 runtime attempt 的身份是一个代次，必须同时移动：任务资源（`905fd51` 起为 `wuji-task-…-a<N>-…`）、`task-agent`/`task-kali` Service 选择器、runtime `pod_runtime`（task_id/attempt/epoch/receiver/environment/digest）、gates `executors[].binding`、以及 attempt 的 `executor_registration`。
- capability 的 mechanism candidate 绑定 `pod_uid`，只能在该 attempt 的 Pod 注册之后发布；`scheduler_receiver` 行由 Pod 注册路径写入，不能预先伪造。
- 只做非破坏性验证；不伪造退出与完成。

## 2. 用户结果

通过产品入口创建一个 Task 后，一条 owner 命令即可让该 Task 在本地 K8s 中真实运行：Task Pod 2/2 就绪、scheduler 租出工作、runtime 把 assignment 投递到 Pod 内 supervisor、模型与工具调用受控经过 gates、`agent_run` 离开 `registered`；随后 `cancel` 得到真实的退出观测（`execution_observation` 记录 exited/stop_kind），Task 不伪造未发生的完成。

## 3. 组件裁剪

复用（不重写）：

- `wuji_core.admission.registry`：`publish_task_admission`、`register_executor`、`register_session_capability`、`session_client_snapshot`、`model_gateway_digest`。
- `wuji_core.blackboard.claims.ClaimService.propose_intent`：初始 Intent/WorkItem 由真实公共领域服务产生。
- `ops/vnext/deployment_common.Deployment`：部署配置与 owner/领域服务组装。
- 既有渲染语义（`ops/vnext/kubernetes/render.py` 的资源形状、`build_task_pod` 命名）与 `PodEnvironment` 的 Pod 归 runtime 创建，不由 owner 直接建 Pod。

新增（本任务唯一新增代码面）：

- `ops/vnext/task_launch.py`：单一 owner 命令，三个有序阶段 `prepare`（领域/DB）、`wire`（K8s 资源与平台配置）、`capability`（绑定 Pod UID 的 session capability），并支持 `--all` 由本机一次性执行（DB 阶段以 Job 运行）。
- `docs` 与证据包：本计划、证据 README、截图、完整 HTTP/SQL 报文。

不新增数据库结构与迁移；不修改 OpenAPI；不改 Cairn；不改旧 app。

## 4. 权限、数据与兼容影响

- DB 阶段仍要求 owner（`wuji_migration`，`vnext` schema owner）身份，沿用既有 `_owner_only` 守卫；不新增权限面。
- `wire` 阶段的 K8s 写入限定本命名空间：任务自有 ConfigMap/Secret/PVC、固定名 `task-agent`/`task-kali` Service 选择器、`runtime-config`/`gates-config` 的 Task 绑定字段、`runtime`/`gates` Deployment 滚动。
- session capability 为 `mechanism_candidate`，绑定该 Task/attempt/receiver/pod UID，并设置有限 `expires_at`；不发布 `verified`，不冒称生产证明。
- runtime/gates 固定名 Service 意味着该切片同一时刻只服务一个 Task；多 Task 并发仍按原计划延期，不在本任务扩张范围。

## 5. 实施步骤（顺序固定）

1. **镜像统一**：以当前 HEAD 构建 platform 镜像并滚动 `api`/`runtime`/`scheduler`/`gates`；确认运行镜像包含 `905fd51` 的 attempt 资源命名。
2. **`prepare`**：校验 Task 存在且未激活 → 合并部署已发布的 `worker_profiles` 并重算 `definition_digest`（已存在必须一致，否则拒绝）→ `publish_task_admission`（model/runtime 由 definition 推导；容量池、访问行、调度身份模板、pod controller 取自部署固定值）→ `register_executor`（新 attempt 的 receiver/environment）→ `propose_intent`（初始 Intent/WorkItem）。
3. **`start`**：经产品接口 `POST /api/v2/tasks/{task_id}/commands` 以 `start` 激活（202），确认 `task.started`、`execution_epoch` 推进。
4. **`wire`**：按第 3 节约束渲染并应用 attempt 资源与平台配置，滚动 runtime/gates；等待 runtime 创建并注册该 attempt 的 Pod（2/2 ready），记录 Pod UID。
5. **`capability`**：以真实 Pod UID 发布 `session_capability`（reason/explore/report 三个 work kind，绑定同一 attempt），确认 `_validate_mechanism_candidate` 通过。
6. **观察往返**：scheduler 租出 → runtime 投递 → supervisor/模型/工具活动 → `agent_run` 状态离开 `registered`。
7. **干净停止**：`cancel` → Pod 在限时内删除 → `execution_observation` 出现真实退出观测；不得伪造 exited。
8. **归档**：证据包（截图 + 完整 HTTP/SQL 报文 + 镜像摘要 + migration head + Pod UID + 未覆盖项），更新验收与计划文档。

## 6. 最小验证与停止条件

- 真实隔离 PostgreSQL 上的定向测试：definition 定稿幂等/冲突、admission+executor 发布、初始 Intent 产生 WorkItem、capability 发布被 `registry.session_capability` 命中；通过即停止，不扩展无关回归。
- 未改动代码复用既有证据并标注原 SHA。
- K8s 实测：第 5–7 节观测到的真实对象与报文，浏览器或终端至少一张截图。
- 关键未通过项如实记录，不得标记通过；不把局部机制切片写成完整 P11/P12 验收。

## 7. 延期项（不在本任务）

- 多 Task 并发（固定 Service 名与单 runtime pod_runtime 绑定）。
- worker profile 的产品化发布（创建入口直接选择已发布 session profile）。
- 真实模型网关与生产身份；本轮仍为 synthetic 机制模型。
- P12 可信完成与报告冻结。
