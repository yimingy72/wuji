# M1：正式任务入口 → 真实 MAF/工具 → 独立证据（机制模式）

- 日期：2026-09-17；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`
- 被测代码：`36f8771`（含 E00/E01/E02/E03/E06 与 worker lock 复锁收口）。镜像 `source_revision=36f8771`：
  platform `127.0.0.1:56615/wuji-vnext-platform@sha256:1f0e1b08…`（本次实跑取自 `work/vnext/k8s/publish-v5b3tp9v/images-published.json`）、
  agent `…wuji-vnext-agent@sha256:b832f0be…`、kali `…wuji-vnext-kali@sha256:e266e144…`
- 范围：**通过公开创建入口 `POST /api/v2/tasks` 新建**的 Task `45d4ee2f-878c-4c12-86aa-8069f1443a4c` 的首次 attempt。
- 模式：`mechanism_synthetic`（loopback 合成模型 + 已发布的 `workspace-read-v1` 工具），不触达任何真实目标、不产生付费调用。

## 1. 这一段证明了什么

| 需求 | 本次实测 |
| --- | --- |
| 真实任务入口 | `POST /api/v2/tasks` 返回 201，Task 为 `pause/ready`；不是手工插入的任务行 |
| 定义在激活前定稿 | `prepare` 写入 `definition_changed=true`，`definition_digest=8e09920e…`，随后 `activate` 用同一摘要启动 |
| 模型拿到真实 Task 上下文 | 发布的三份 profile 正文包含 `goal: Read the isolated fixture file for this Task…`、判据、授权范围、金额预算、硬上限与角色职责（见 `raw/launch.log` 的 `worker_profiles`） |
| Pod 与执行环境 | `wire` 报 `controller_ready=true`，Pod `wuji-task-v-ed69727aea0772661471a423c9129f57-a1`、`pod_uid=835445c0…` |
| 能力发布 | `capability` 发布 `session-capability-45d4ee2f…-a1-{reason,explore,report}` |
| 实际 MAF 与允许工具完成工作 | 两个 work item（`reason`/`explore`）都到 `done`；两个 Run `process_state=exited`、`result_state=accepted` |
| 证据独立保存 | 8 份 sealed artifact（含 `text/plain; charset=utf-8` 的工作区读取捕获与 MAF SDK ndjson/结果绑定），2 条候选 Claim 被接纳 |

## 2. 可复现步骤

```bash
# 1. 正式入口创建 Task（operator bearer 由部署签名钥现场签发）
scripts/vnext/uv.sh run --frozen python work/vnext/p11c/mint-token.py
curl -sS -X POST --cacert work/vnext/k8s/tls/ca.crt \
  -H "Authorization: Bearer $(cat work/vnext/p11c/operator.token)" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: m1-exploration-20260917-4" \
  --data @create.request.json https://127.0.0.1:18456/api/v2/tasks

# 2. owner 命令四阶段（在集群内 Job 中执行）
scripts/vnext/uv.sh run --frozen python ops/vnext/task_launch.py --submit --phase all \
  --task 45d4ee2f-878c-4c12-86aa-8069f1443a4c \
  --image 127.0.0.1:56615/wuji-vnext-platform@sha256:1f0e1b08… \
  --agent-image 127.0.0.1:56615/wuji-vnext-agent@sha256:b832f0be… \
  --kali-image 127.0.0.1:56615/wuji-vnext-kali@sha256:e266e144… \
  --agent-auth-secret wuji-task-v-ca604b6abddb91218b985ea232f4c239-agent-auth \
  --kali-auth-secret wuji-task-v-ca604b6abddb91218b985ea232f4c239-kali-auth
```

## 3. 创建请求与响应（完整报文）

```http
POST /api/v2/tasks HTTP/1.1
Host: 127.0.0.1:18456
Authorization: Bearer <operator RS256, iss=https://identity.wuji-vnext-test.invalid, aud=wuji-vnext-deployment, sub=operator>
Content-Type: application/json
Idempotency-Key: m1-exploration-20260917-4
```

请求体见 [`create.request.json`](create.request.json)，响应体见 [`create.response.json`](create.response.json)：

```text
HTTP/1.1 201 Created
{"task_id":"45d4ee2f-878c-4c12-86aa-8069f1443a4c","tenant_id":"1fc6b1f3-…","project_id":"81e8c413-…",
 "name":"M1 mechanism exploration task","scenario":"web_single","desired_state":"pause",
 "observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"allowed_actions":[]}
```

## 4. 运行结果（数据库回读，原文见 `raw/`）

```text
kind    | state | current_run
explore | done  | c1695f0e
reason  | done  | 639242d6

run      | process_state | result_state | stop_kind | model_mode
639242d6 | exited        | accepted     | exited    | synthetic
c1695f0e | exited        | accepted     | exited    | synthetic

outbox: task.started 1, intent_shared 1, run.dispatch_requested 2,
        tool.dispatch_requested 2, result_committed 2, session.published 2
```

artifact（8 份，全部 `sealed`）与 claim 明细见 [`raw/db-artifacts.txt`](raw/db-artifacts.txt)、[`raw/db-claims.txt`](raw/db-claims.txt)。
截图见 [`screenshots/m1-mechanism-loop.html`](screenshots/m1-mechanism-loop.html)。

## 5. 本次实跑发现并修复的部署缺陷（同一提交内）

1. **worker lock 变更后所有新 Task 无法 prepare**：`62c232c` 改了 `packages/maf-worker/uv.lock`，部署 2026-09-15 发布的
   `k8s-runtime-v1` 仍写旧摘要，新 Task 冻结旧 profile 后 `finalise_definition` 以 `INPUT_DIGEST_CONFLICT` 拒绝（fail-closed 正确，
   但缺修复路径）。新增 `preflight` 的 `worker_lock` 检查与 owner 阶段 `--phase relock`，本次实测发布 `k8s-runtime-v1` revision 4
   （见 [`raw/relock.log`](raw/relock.log)）。
2. **runtime profiles ConfigMap 混合两个 Worker lock**：`wire` 之前把新 profile 追加进共享 ConfigMap，旧 deployment 的
   `harness.*.deployment.v{1,2}` 仍带旧 lock，runtime 启动即 `one fixed Worker lock required`。现在按 lock 退休旧条目
   （`runtime-profiles: pruned:N`），不再让两种 lock 共存；本次现场同时按同样规则清理了 ConfigMap（旧 C2 夹具 profile 退休）。
3. **每 Task Service 证书缺少本 Task DNS 名**：`rotate-task-certs` 只重签了 `work/vnext/k8s/tls/` 状态文件，没有推送到部署的
   Task 模板 secret，新建 Task 复制到的是旧 SAN 证书，runtime 到 supervisor 的 HTTPS 调用报 `URLError`（本题第一次尝试即因此未投递）。
   现场把模板 secret 更新为带 `*.wuji-vnext-test.svc` 的证书后，新建 Task 一次成功。**修复工具化仍未完成**：
   `rotate-task-certs` 尚未自动更新模板 Task secret，属下一项最小工作。

## 6. 未覆盖

- 首次尝试（Task `0e44b153…`）因证书问题未投递，Task 停在 `cancel|reconciling`；本包只以成功任务为 M1 证据，不把该失败算作通过。
- 真实模型、真实靶场未使用（无付费/目标授权）：本项是机制模式，不证明真实模型效果。
- reason 的 `propose_intents` 动态链路（E04-A）本轮未在集群实跑；产品侧回归仍在 `tests/vnext/test_exploration_loop.py` 的进度中。
