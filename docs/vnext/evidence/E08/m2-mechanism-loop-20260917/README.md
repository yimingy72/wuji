# M2：真实观察触发非预写 Intent 的机制闭环（CASE-A）

- 日期：2026-09-17；工作树 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`
- 被测代码：`4047e12b919811c69190f8d850b41e113f848197`（`work/vnext/k8s/build-iii37gyi/source-commit.txt`）
- 镜像（同一提交，`work/vnext/k8s/publish-tisu4mca/images-published.json`）：
  platform `127.0.0.1:56615/wuji-vnext-platform@sha256:7c17bc8ba7cf5e36baaf4d73c8468beaa7115bb4b9334b7ce6ad968c6e509f74`、
  agent `…wuji-vnext-agent@sha256:1448750869f1e38ed800ec180e889907bfba20a129151c2e9fa0bf572569274c`、
  kali `…wuji-vnext-kali@sha256:94bcff696b38ae51d0f065cd7becc6b41067f6a211c43a93ec341c9ee0eb7d4a`
  （M2 期间针对会话对象边界与 peer 缺陷又各重建一次，最终集群运行的 platform 摘要见 `trial.json`）
- 模式：`mechanism_synthetic`（隔离 Gate Pod 内的 loopback 机制 peer + 已发布的 `workspace-read-v1`），不触达真实目标、不产生付费调用
- 范围：通过公开入口 `POST /api/v2/tasks` 新建的 Task `ff045b32-68f6-4faa-b74c-482af7f0c148` 的首次 attempt

## 1. 这一段证明了什么

| M2 要求 | 本次实测 |
| --- | --- |
| 真实观察触发 Reason | Explore 读取 `materials/entry.json` 后，`evidence_ingested` → 新 generation → 新 Reason work（快照含 Observation 与捕获 Artifact 正文） |
| 非预写 Intent | 第二个 Intent 的问句来自**只存在于被观察字节里的指针**：`{"pointer": "materials/registry-oct.json"}`。部署里没有任何地方写过这个文件名；换一份材料就会得到另一个问题 |
| 正式调度执行 | Committer 接纳该 Intent（`intent_shared`）→ Scheduler 物化 Explore work → Kali 真实读取 `materials/registry-oct.json` |
| 新证据改变后续判断 | 下一次 Reason 的决定从 `wait`（无材料）→ `propose_intents`（有指针）→ `wait`（问题已在执行，等待其结果）→ `propose_completion`（指向的文件已读、正文带答案）；评审缺判据后 `blocked`，等待操作者，而不是空转 |
| 正确等待/阻断/结束 | 两次真实 `scheduler_waiter` 登记并 `ready` 唤醒；最终 `scheduler_state.blocked_reason=reason_operator_review`，`no_progress_count=1` |

最终判分（独立评分文档 `suite/grader/A-reference.json`，不在材料根内）：`verdict=pass`，答案链 `materials/entry.json` → `materials/registry-oct.json`，答案 `4.2.0`，诱饵版本 `4.3.1` 从未被读取。见 [`grading.json`](grading.json)。

## 2. 五次 Reason 决定（`raw/db-loop.txt` 原文）

```text
generation 2  wait               "Nothing has been observed ... waits for the admitted question's own accepted result."
generation 5  propose_intents    "The observed bytes point at materials/registry-oct.json ..."
generation 6  wait               "The question for materials/registry-oct.json is already admitted ... instead of asking the same thing twice."
generation 8  propose_completion "The pointed file ... was read and its own bytes carry the value the Goal asks for."
generation 9  blocked            "The recorded completion review still reports open basis (criteria_unmet) ..."
```

工作统计：work_item 7（reason 5 / explore 2）全部 `done`，AgentRun 7 个全部 `exited/accepted`，Intent 2、Claim 2、Observation 2、捕获 Artifact 2、`reason.completion_requested` 1、`completion.reviewed` 1。

## 3. 可复现步骤

```bash
# 1. 夹具与预检（不触达目标、不调用模型）
scripts/vnext/uv.sh run --frozen python scripts/vnext/exploration_trials.py fixtures  --suite <suite>
scripts/vnext/uv.sh run --frozen python scripts/vnext/exploration_trials.py preflight --suite <suite>   # 0 = 无阻塞

# 2. 正式入口创建 Task（operator bearer 由部署签名钥现场签发）
scripts/vnext/uv.sh run --frozen python work/vnext/p11c/mint-token.py
curl -sS -X POST --cacert work/vnext/k8s/tls/ca.crt \
  -H "Authorization: Bearer $(cat work/vnext/p11c/operator.token)" \
  -H "Content-Type: application/json" -H "Idempotency-Key: m2-case-a-20260917-5" \
  --data @create.request.json https://127.0.0.1:18456/api/v2/tasks

# 3. 用本案例的封闭材料生成运行配置，并交由既有 owner 命令执行四阶段
scripts/vnext/uv.sh run --frozen python scripts/vnext/exploration_trials.py case-config \
  --suite <suite> --case A-reference --config <trial-config.json> --task <task-id> --out run-config.json
scripts/vnext/uv.sh run --frozen python ops/vnext/task_launch.py --submit --phase all --task <task-id> ...
```

完整报文与数据库回读见 §4、§5；本案例的运行配置只比部署文档多了 `k8s-runtime-trial-v1` 这一份限值更宽的运行时 profile（见 §6），提交版为 [`run-config.redacted.json`](run-config.redacted.json)（`roles` 与数据库口令已脱敏，其余字段与集群实际使用的一致）。

## 4. 完整请求包

### 4.1 创建 Task（正式入口）

```http
POST /api/v2/tasks HTTP/1.1
Host: 127.0.0.1:18456
Authorization: Bearer <operator RS256, iss=https://identity.wuji-vnext-test.invalid, aud=wuji-vnext-deployment, sub=operator>
Content-Type: application/json
Idempotency-Key: m2-case-a-20260917-5
```

请求体 [`create.request.json`](create.request.json)（Goal 与判据即评分文档期望的答案链，但**不含答案**）：

```json
{"schema_version": "wuji.api.v2", "project_id": "81e8c413-ba26-45fb-8b5a-1bc477eef99f", "name": "M2 information-driven exploration (CASE-A)", "scenario": "web_single", "goal": {"text": "Report the inventory service version recorded in the registry file that the workspace entry document points to, and cite the file it came from.", "criteria": [{"criterion_id": "registry-version", "object": "the registry file the workspace entry document points to", "condition": "its recorded inventory service version is reported together with the file it came from", "evidence_requirements": ["sealed bytes of the registry file"], "allowed_methods": ["deterministic"], "required": true, "responsible_party": "deployment-test"}]}, "authorization_scope": [{"host": "fixture.invalid", "port": 443, "protocol": "https"}], "authorization_expires_at": "2026-12-31T00:00:00Z", "model_profile_ref": "k8s-model-v1", "runtime_profile_ref": "k8s-runtime-trial-v1", "budget": {"amount": "5", "currency": "USD"}}
```

响应（原文 [`raw/create.response.json`](raw/create.response.json)）：

```text
HTTP/1.1 201 Created
{"task_id":"ff045b32-68f6-4faa-b74c-482af7f0c148","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","version":"1","name":"M2 information-driven exploration (CASE-A)","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

### 4.2 owner 四阶段（集群内 Job，原文 [`raw/launch.log`](raw/launch.log)）

```text
{"event": "task_launch", "phases": ["prepare","activate","wire","capability"], "result": {
  "prepare": {"definition_changed": true, "definition_digest": "…", "evaluation_mode": "mechanism_synthetic",
              "intent_local_ref": "workspace-materials-entry-json",
              "intent_ref": {"entity_type":"intent","id":"b2d1ecd9-cb29-44be-a086-a34b082d749c","revision":"1"}},
  "activate": {"execution_epoch": 2, "response": {"command_id": "task-launch-start-ff045b32-…-a1", "disposition": "accepted"}},
  "wire": {"controller_ready": true, "agent_image": "…wuji-vnext-agent@sha256:14487508…", "kali_image": "…wuji-vnext-kali@sha256:94bcff69…"},
  "capability": {"capabilities": ["session-capability-ff045b32-…-a1-{explore,reason,report}"]}}}
TASK_LAUNCH_JOB_STATUS SuccessCriteriaMet|1|
```

> 注：`prepare` 生成的第一个 Intent 采用**部署发布的材料路径**（`workspace:materials/entry.json`），这是本案例给定的起点；M2 断言的是**之后**的问题来自运行中观察到的字节（见 §2 的 generation 5）。

## 5. 数据库回读（原文见 `raw/`）

- `raw/db-loop.txt`：五次决定全文、两次 waiter、`scheduler_state`、只读集里 `model_output` 计数为 0、每个 Run 的模型请求字节数
- `raw/db-state.txt`：work_item/run/outbox/snapshot 明细
- `raw/db-claims.txt`、`raw/db-claim-texts.txt`：两条 Claim（第一次读 entry、第二次读 registry-oct）与两份捕获 Artifact（43 B / 70 B，`text/plain; charset=utf-8`，`sealed`）
- `raw/db-intents.txt`：两个 Intent 的问句与 `admitted`
- `raw/db-completion-review.json`：E05 评审原文（`decision=wait`、`reasons=["criteria_unmet"]`、覆盖表里 `registry-version` 为 `missing`）
- `raw/trial-preflight.json`：夹具预检（答案在材料根之外、材料字节未改、变体标签不外泄）

## 6. 本轮实测发现并修复的缺陷（同一阶段内提交）

| # | 现象 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | 模型只见 receipt，不见工具读到的字节 | 工具结果只投递 receipt，`material` 仅存在于跨 Run 的上下文 | `e8f15e0`：新增 `/internal/v2/tool-calls/{id}/material`（受发布输出上限约束、按固定原因省略），worker 在同一 Run 内把正文交给模型；重放的工具消息只在按 `sha256` 校验正文等于封存 Artifact 后才被接受 |
| 2 | 第二个 Reason 提出 Intent 被拒 `reason_intent_not_accepted` | peer 用**原始 Artifact 引用**做问题依据（平台只接受 Claim/Observation），且会把已在执行的问题再问一遍 | `8208934`：依据改为最新 Claim、退化到 Observation；已有同路径问题时改为 `wait`，不重复提问 |
| 3 | 新 Task `wire` 阶段 `INPUT_DIGEST_CONFLICT` | Session profile 身份只哈希 instructions/tool/lock，限值不同而 ref 相同 | `fa94f4c`：身份覆盖整个已发布 body |
| 4 | 会话对象 `LIMIT_BLOCKED`：上下文随代际增长直至 Run 无法提交 | 快照默认把**每个** sealed Artifact 当作黑板材料，Run 的私有产物（模型响应、会话根、结果绑定）回流进下一次上下文 | `4047e12`：新 Run 的快照只冻结 claim/intent/observation 及其证据闭包；`raw/db-loop.txt` 实测只读集中 `model_output` 计数为 0，快照引用数从 20+ 降到 1–8，模型请求从 23 KB 降到 3–13 KB |

## 7. 截图证据

- [`screenshots/m2-topology.jpg`](screenshots/m2-topology.jpg)：工作台绑定该 Task 的受权拓扑快照（快照模式），可见 2 个 Intent、2 条 Claim、2 个 Observation、7 个 WorkItem 与 7 个 AgentRun，以及“任务完成 / 平台审核”面板显示判据 `registry-version` 缺少判定
- [`screenshots/m2-claim-answer-detail.jpg`](screenshots/m2-claim-answer-detail.jpg)：选中第二条 Claim 后的“记录详情 / 固定快照”，公开记录正文即 `materials/registry-oct.json` 的原始字节与 `version: 4.2.0`

## 8. 未覆盖与阻塞

- 真实模型：无网关/Key/额度，`real_model` 分支未执行（`blocked_configuration`）；本证据不宣称模型质量或成功率
- 样本量：单 Task、机制模式单次闭环；变体对照（CASE-B 一致/冲突）与 CASE-C 未在本轮运行
- 无效进展收敛（E04-B）与 SSE 实时视图（X04/R04–R05）仍未做，工作台保持快照模式
