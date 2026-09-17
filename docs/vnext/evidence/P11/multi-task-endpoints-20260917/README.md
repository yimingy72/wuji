# T8 实测：每个 Task 自己的 supervisor 端点，两个 Task 并行各自收取派发

- 日期：2026-09-17；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`；被测代码 `425a187`。
- 集群：`docker-desktop` / `wuji-vnext-test`；镜像 platform `127.0.0.1:56615/wuji-vnext-platform@sha256:4f2ffefc…`、
  agent `…wuji-vnext-agent@sha256:2a102c4b…`、kali `…wuji-vnext-kali@sha256:d4169225…`。
- 对象：两个新 Task `abbeab81-becf-471c-a110-12ed480e93bf`（A）与 `989eead2-b571-422c-b5db-f90f70472c94`（B），
  均为 `web_single` + 固定合成模型 + 只读 `workspace-read-v1` 工具。

## 1. 本切片交付

此前所有 Task 共用一个 `task-agent` / `task-kali` Service（launcher 每次把 selector 改指向“最新那个 Pod”），
所以两个 Task 同时存活时，runtime 自己的 Pod 校验会拒绝第二个 Task，派发也可能落到错误的 Pod。现在：

- launcher 为每个 attempt 创建 `<task-agent|task-kali>-<task 前 12 位>` 两个 Service，并把
  `task_runtime.tasks[]` 里该 Task 的条目写成 `service_names` + `supervisor_url`（部署级固定名仍保留给旧条目）；
- gates 的 executor 条目按 Task 写 `base_url=https://task-kali-<prefix>.<ns>.svc:8444`，Kali 也走各自的端点；
- runtime 用 `TaskSupervisorTransport` 路由 `query/start/control`：声明了端点的 Task 走自己的 transport，
  没有声明的仍回落部署 URL；`PodEnvironment` 按 Task 校验“Service 端点 UID == 该 Task 的 Pod UID”；
- 两个 task Service 叶证书新增一层通配 SAN，`scripts/vnext/k8s.py rotate-task-certs` 复用既有 CA 只重签这两张叶证书。

## 2. 真实 Kubernetes 证据

两个 Pod **同时 Running**，各自的 Service 只指向自己的 Pod（`raw/pods.txt`、`raw/services.txt`、`raw/endpoint-routing.json`）：

```text
wuji-task-v-1ff9a800…-a1   2/2 Running   (Task A)
wuji-task-v-8a04f602…-a1   2/2 Running   (Task B)

task-agent-abbeab81becf -> wuji-task-v-1ff9a800…-a1 (ready)
task-kali-abbeab81becf  -> wuji-task-v-1ff9a800…-a1 (ready)
task-agent-989eead2b571 -> wuji-task-v-8a04f602…-a1 (ready)
task-kali-989eead2b571  -> wuji-task-v-8a04f602…-a1 (ready)
task-agent (旧固定名)    -> wuji-task-v-8a04f602…-a1   ← 正是旧设计会串台的地方
```

runtime 配置里只有这两个 Task 带自己的端点（`raw/runtime-config-tasks.json`），gates 同样按 Task 走自己的 Kali
（`raw/gates-executors.json`）：

```json
{"task_id":"abbeab81-…","service_names":{"agent":"task-agent-abbeab81becf","kali":"task-kali-abbeab81becf"},
 "supervisor_url":"https://task-agent-abbeab81becf.wuji-vnext-test.svc:8443"}
{"task_id":"989eead2-…","base_url":"https://task-kali-989eead2b571.wuji-vnext-test.svc:8444"}
```

派发与结果（`raw/runtime-log.txt`、`raw/database-state.txt`）：

```text
runtime  {"event":"runtime_dispatch_transport","method":"PUT","status":200}   ×2   ← 两个 Task 各自的 start
task     A running|attempt 1|epoch 2      B running|attempt 1|epoch 2
work     A reason|done  explore|done      B reason|done  explore|done
run      A 0c9af8e9|accepted|settled      B 804197da|accepted|settled
         A c4e6f915|accepted|settled      B 3342fbb4|accepted|settled
receiver A task-abbeab81-…-a1 enabled     B task-989eead2-…-a1 enabled
dispatch A 02:41:00Z ×2                   B 02:42:27Z ×2
```

最关键的一段是**每 Pod 自己的启动收件箱**（`raw/pod-launch-inboxes.txt`，直接在容器里读取）：

```text
Task A pod wuji-task-v-1ff9a800…-a1
  e60e45c70a2a abbeab81-… 0c9af8e9-… task-abbeab81-…-a1
  e88f691c6bf2 abbeab81-… c4e6f915-… task-abbeab81-…-a1
Task B pod wuji-task-v-8a04f602…-a1
  1c6e884ff533 989eead2-… 804197da-… task-989eead2-…-a1
  226d4057f947 989eead2-… 3342fbb4-… task-989eead2-…-a1
```

每个 Pod 只持有**自己 Task** 的两个 Run assignment（task/run/receiver 三个身份全部匹配），没有对方的 Run；
supervisor 本身会按 mounted `receiver_id` 校验 Assignment 身份，因此“回执被接纳”只可能来自正确的 Pod。

## 3. 证据与检查

- 原始文件：[`raw/pods.txt`](raw/pods.txt)、[`raw/services.txt`](raw/services.txt)、[`raw/endpoint-routing.json`](raw/endpoint-routing.json)、
  [`raw/runtime-config-tasks.json`](raw/runtime-config-tasks.json)、[`raw/gates-executors.json`](raw/gates-executors.json)、
  [`raw/runtime-log.txt`](raw/runtime-log.txt)、[`raw/pod-launch-inboxes.txt`](raw/pod-launch-inboxes.txt)、
  [`raw/database-state.txt`](raw/database-state.txt)、[`raw/launch-task-a.txt`](raw/launch-task-a.txt)、[`raw/launch-task-b.txt`](raw/launch-task-b.txt)
  （两次 launch 的原文都显示 `task-agent-<prefix>`/`task-kali-<prefix>` **created** 且 `SuccessCriteriaMet|1|`）。
- 检查原文：[`raw/checks-pytest.txt`](raw/checks-pytest.txt)（53 passed / exit 0，含 launcher/证书/路由/pod 配置/运行时批隔离 6 个套件）。
- 本切片没有 UI 变化，因此没有截图；证据全部是集群对象、原始日志与容器内持久记录。

## 4. 未覆盖

- 旧 Task 条目（没有 `service_names`）仍然回落到固定 `task-agent`/`task-kali`；它们与新 Task 同时运行时会互相抢这个固定名。
  并发运行需要每个 Task 都由本次之后的 launcher 启动（或在下次滚动时补写端点）。
- 只验证了两个 Task 各一轮真实派发；多 Task 的长时间公平性、每 Task 独立 bearer 轮换与 per-attempt 证书签发仍未做。
- 取消其中一个 Task 时另一个不被连带停止，已在早前的
  [two-task regression](../two-task-regression-20260916/README.md) 中验证；本切片没有再复跑该场景。
