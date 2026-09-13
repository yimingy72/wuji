# P10 Node-only Supervisor 独立审查

> 永久归档派生说明：本文件派生自 `.superpowers/sdd/vnext-v2/P10-node-review.md`；源字节 SHA-256 `fc991ccb4ccc90bbe95a5331ab526ee7803bfe9c967def9745479608d7dd311c`。除本说明与相对链接目标外，正文、执行者、提交 SHA 和各轮历史结论保持原样；精确行号引用使用本目录 `references/` 中的原字节副本。

- 日期：2026-09-13
- 结论：**P2（非 PASS）**；未发现 P1
- 审查对象：Node core `72d26a02308ab54db2c7c56b52f9861b8acdda82` 的四个 owned files：`services/maf-supervisor/{main,inbox,guardian,protocol}.mjs`
- 测试来源：`cab5008b7f49bc4a44f3cc3bb03df5e7b6140693`（10 cases 与 support）、`8e2fc7df599dc83756ebf2676ace44b761b41270`（证据采集 support）
- 封存证据：`57e4a3499f11c42e409dc0b8b889a25c07048348`，`docs/vnext/evidence/P10/node-first-flow/`
- 方法：SOL/xhigh 独立静态代码审查，主线程复核合同、提交归属和既有证据。**本次没有运行 Node、数据库、HTTP、浏览器或新增测试；下述 10/10 是复用 Ptolemy 已封存结果，不称为本次独立测试。**

## Finding

### P2 · unknown 转换丢失已经验证的进程出生身份

**文件与行：**[`services/maf-supervisor/main.mjs`](../../../../../services/maf-supervisor/main.mjs)，109–147 行，关键为 136–147 行。

**触发：**operation 的 inbox 状态仍为 `prepared`；`process.json` 已提供合法 HMAC、完整 `running`/birth 记录，`validateProof()` 已通过；随后 guardian challenge 因 guardian 退出、socket 不可达或瞬时失败而失败。

**实际路径：**`observe()` 在 136–140 行只对签名的 `exited/not_started` 立即落状态。签名 `running` 证明虽然已验证，却没有保存在局部可回退值或 inbox observation。challenge 失败后，147 行调用 `setState(record, 'unknown', null, ...)`；110 行只能从 `proof?.process` 或既有 `record.observation?.process` 取出生身份。此时两者均为空，最终 `unknown` observation 的 `process` 为 `null`。

**影响：**保守的 `unknown` 和“原 operation 不再 spawn”仍成立，因此不会造成双启动；但系统丢失已经可信确认的历史 birth identity。P05/reconciler 后续只能看到没有 process identity 的 unknown，削弱同一实际进程的核对、控制、审计以及 Incident 人工解除依据。

**最小反例：**

```text
record.state = prepared
record.observation = null
signed process.json = running + {pid, birth_id, started_at}
guardian socket = unavailable

GET/query -> unknown + observation.process = null
```

该反例不依赖 PID 存在检查，也不要求运行新测试。它直接来自 136–147 行的数据流。

**违反合同：**

- [`docs/vnext/SPEC.md`](../../../../../docs/vnext/SPEC.md) 303、306 行：应记录进程出生信息；无法判断当前执行时转为 unknown/reconciling。
- [`.superpowers/sdd/vnext-v2/P10-M2-brief.md`](references/P10-M2-brief.md) 7 行：记录 actual birth/exit；稳定可信进程记录可解析事实。
- [`.superpowers/sdd/vnext-v2/P10-core-interface.md`](references/P10-core-interface.md) 35、80 行：缺少当前 guardian/exit 证明时保持 unknown；receiver 的 signed-process-derived unknown 应保留有效 P05 source。
- [`docs/vnext/P05-implementation-contract.md`](../../../../../docs/vnext/P05-implementation-contract.md) 39–41 行：适用时保存完整进程出生/退出身份，缺正确出生身份保持 reconciling。

**最小修复方向：**签名 `running` proof 已通过验证但 challenge 失败时，状态仍写 `unknown`，同时把该已验证 proof 的 process/birth 作为历史事实带入 observation；不得因此把当前状态写成 `running` 或释放容量。修复后只需对这一窄窗口增加/执行定向 Node 验证，不扩展通用 cleanroom、Kubernetes 或完整 M2 矩阵。

## 合同逐项核对

| 项目 | 结论 | 实现与证据 |
| --- | --- | --- |
| durable prepared before spawn | 符合 | [`inbox.mjs`](../../../../../services/maf-supervisor/inbox.mjs) 18–21 行使用 `synchronous=FULL` 的独立 inbox；[`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 181 行 insert 在 189 行 guardian spawn 之前。既有 `prepared-before-spawn` 记录为 unknown、0 actual start。 |
| 单 receiver / inbox owner | 符合 | [`inbox.mjs`](../../../../../services/maf-supervisor/inbox.mjs) 13–26 行使用独立 `owner.sqlite` lifetime `BEGIN EXCLUSIVE` 并固定 receiver metadata；[`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 67–70 行串行化进程内操作。既有第 10 case 覆盖同时 owner 与重开 identity。 |
| actual process identity + guardian challenge；PID 不可单独证明 | **存在上述 P2** | [`guardian.mjs`](../../../../../services/maf-supervisor/guardian.mjs) 18–29、73–87 行生成 launch/guardian/OS birth 与 exit；[`protocol.mjs`](../../../../../services/maf-supervisor/protocol.mjs) 90–128 行使用 HMAC、随机 challenge、launch identity；[`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 118–130 行拒绝缺失 birth/guardian 字段的 proof。当前 P2 不接受 PID 假证明，但会丢失已验证 birth。 |
| 四崩溃窗口 unknown / 不再 spawn | 符合当前 Node receiver 边界 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 180–209 行固定四个 hook；155–159 行只 observe 已存在 operation，不进入 spawn；133–147 行无法核实时转 unknown。`before_prepared` 因 spawn 尚未发生可由原 operation 重投；其余持久 operation 不再 spawn。既有证据记录四次真实 Supervisor SIGKILL。 |
| same ID + different digest conflict | 符合 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 99–100 行生成 canonical assignment digest，155–158 行同 operation 改 digest/profile 返回 `INPUT_DIGEST_CONFLICT`；237–242 行 control 同键改体同样冲突。既有 digest 场景为 409、实际 start 仍为 1。 |
| control accepted 不等于 stopped | 符合 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 237–249 行先持久 accepted intent，再通知 guardian，响应另带独立 execution observation；[`guardian.mjs`](../../../../../services/maf-supervisor/guardian.mjs) 82–87 行只有实际 child exit 才写 exited。既有 control 场景先返回 accepted + running，后返回 exited。 |
| 旧身份拒绝 | Node 内与 adapter 合同符合；生产事实未验证 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 88–100 行拒绝 receiver/runtime_attempt 不匹配，73–85 行要求 grant 精确匹配完整 identity/receiver/digest/freshness，227–235 行拒绝旧 control identity。真实 P09/P05 current-row authorizer 尚未在本范围运行，不能由反射式夹具替代。 |
| 固定 launch profile/env、无 token argv/公开回复、受控路径 | Node 静态边界符合；真实 token/log 与生产隔离未验证 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 49–59 行只接受部署提供的绝对 command/cwd、固定 args/env/workKinds；175–190 行 Worker env 不继承父环境，只补 assignment/bootstrap 两个受控路径，guardian argv 只有固定模块和私有 launch 目录；103–106、253–286 行公开回复不含 secret/token/path。[`guardian.mjs`](../../../../../services/maf-supervisor/guardian.mjs) 31–37 行将 child stdout/stderr 原样写入私有有界日志；当前夹具没有真实 Run token，因此“真实凭据绝不进入日志”仍须由后续 Worker/bootstrap 与生产隔离窄验证证明，不能用本次 10/10 宣称。 |
| 边界/unknown 不偷偷复投 | Node receiver 符合；sender/host transport 未验证 | [`main.mjs`](../../../../../services/maf-supervisor/main.mjs) 155–159 行对已有 operation 只 observe，214–223 行 query 404 不合成 `not_started`，且 inbox 的 run key 唯一约束阻止同一 Run 换 operation 偷跑。Python sender、Task started 与 MAF host transport 均不属于四个 Node owned files，本报告不为它们标通过。 |

## 既有证据核对（复用，不是本次测试）

- [原验证报告](../../../../../docs/vnext/evidence/P10/node-first-flow/report.md)和 [JUnit](../../../../../docs/vnext/evidence/P10/node-first-flow/node-junit.xml)记录 10/10、0 failed、5191.985083 ms；用户补充确认主 Node test 命令 exit 0。证据报告第 36 行“Node core 六个源文件”的措辞不作为本审查范围依据；Git 证明 `72d26a0` 只拥有上述四个 Node 文件且从该提交到证据 HEAD 未变。
- [完整 HTTP 复现包](../../../../../docs/vnext/evidence/P10/node-first-flow/http-reproduction.md)共 1073 行、96145 bytes，SHA-256 `15095fc5f2bfd224b947b5dd0c78e261b0c8e662380909950f00fafd1694c47c`。本次只读解析七个 raw JSON，把 34 组 method/URL/全部 headers/完整请求体、响应 status/全部 headers/完整响应体或断连错误逐项与该文档比对，未发现缺段或截断。该核对没有发送 HTTP。
- 四次 Supervisor SIGKILL 分别为 `before_prepared`、`after_prepared_before_spawn`、`after_spawn_before_running_receipt`、`after_running_before_response`。七个 raw 场景中六个实际 child 各有同一 fixture instance/PID 的 birth 与 exit，exit code 均为 0；`prepared-before-spawn` 为 0 start/0 birth/0 exit。它们证明已执行场景的真实进程记录，不覆盖本 Finding 的“签名 running proof 已存在但 guardian 同时不可达”组合。
- 截图：[Node first-flow](../../../../../docs/vnext/evidence/P10/node-first-flow/screenshots/node-first-flow.png)。

![P10 Node first-flow 既有验证截图](../../../../../docs/vnext/evidence/P10/node-first-flow/screenshots/node-first-flow.png)

## cleanup 核对

Ptolemy 已发送 10/10 封存完成。main 随后发送最小 cleanup 状态询问并关闭该代理；关闭工具返回的 previous status 是正在处理新消息的 `running`，因此**没有取得该条 cleanup ack**。这属于代理交接证据缺口，不是 Node 代码失败。

既有测试 teardown 仍提供以下资源证据：

- [`tests/task-workers/support/supervisor-harness.mjs`](../../../../../tests/task-workers/support/supervisor-harness.mjs) 227–242 行对活跃 host 发 SIGTERM、最多等待 2 秒后才对该已知 host 使用 SIGKILL并等待 exit；270–275 行依次封存证据、release child、等待 host、再删测试目录。
- [`tests/task-workers/maf-supervisor.test.mjs`](../../../../../tests/task-workers/maf-supervisor.test.mjs) 95–126 行要求每个实际 child 的 birth/exit、同实例/PID及 exit code；128–215 行的直接 response-loss case 也在 finally 中 release、等待 exited、关闭 Supervisor 后删目录。
- 2026-09-13T15:03:39+08:00 对证据中明确记录的 4 个 crash host PID、6 个 guardian PPID 和 6 个 child PID做只读 `ps` 核对，无一存在；对完整 HTTP 包记录的 11 个临时 loopback 端口逐一只读 `lsof` 核对，均无 listener。没有启动或杀死任何进程。

限制：重启后正常退出的 Supervisor host PID 没有写入 raw 封存包，因此没有逐 host 的历史 exit receipt；其退出由 awaited teardown、主命令 exit 0 与当前端口无 listener 共同佐证。结论只能写为“记录到的 child/guardian/crash host 与临时 HTTP 当前均已结束；代理 cleanup ack 未取得”，不能包装成额外独立测试或更广的环境清理证明。

## 范围与未验证项

- 未审查、未运行、未标通过 Python `fd9c474ab2be9d32aeabda2690a120cb2c003343`。
- Node-only 测试的 Supervisor、guardian 与 child 使用同一 UID；它没有证明生产 Worker 看不到 guardian key/inbox/socket，也没有证明 Pod、进程组或后代进程隔离。
- 真实 Task started、P09/P05 current-row authorizer、receiver/pod binding、`await_start` barrier、同一实际 MAF `run_assignment`、HostTransport、结果先于 observation、容量与 Kubernetes 均未验证；因此完整 M2 保持未验收。
- main 后续交给 Dirac 的 `main.mjs` 窄 `persistResults` hook、真实 workerDir 中 result/sdk request 的已存 bytes 补交及其新 diff/最小 Node 验证，不属于固定 `72d26a0` 与旧 10 cases。本报告不审它、不改变其状态；需要时只对该窄 diff 另行复审，不重开完整 M2。
- 工作树没有 `.codegraph/`；本次按项目约定回退到 `git show`、`rg` 和逐文件读取。除本报告外未修改源码、测试或永久证据。
