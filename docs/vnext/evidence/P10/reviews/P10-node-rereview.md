# P10 Node Supervisor 窄 delta 复审

> 永久归档派生说明：本文件派生自 `.superpowers/sdd/vnext-v2/P10-node-rereview.md`；源字节 SHA-256 `356b3a528a515ebb8448e7ac3ee25726dcd722f54ed0381951fe6a0e7d695c8a`。除本说明与相对链接目标外，正文、执行者、提交 SHA 和各轮历史结论保持原样；精确行号引用使用本目录 `references/` 中的原字节副本。

- 日期：2026-09-13
- 结论：**P1 残留；非 PASS**
- 固定代码：`7f6debc06575a63ac168d1022d88f06ea1619a25`
- 固定证据：`0b595ba780ba2bd7df9b5917cfadd788c73f5096`
- 比较基线：`72d26a02308ab54db2c7c56b52f9861b8acdda82`
- 范围：`main.mjs` 的原 P2 修复、`persistResults` 窄 hook，以及提交内两个专用 test 和无害 support。旧 10-case、其余 Node、Python、P09/P13 与完整 M2 均未重审。
- 方法：本审查由 main 直接派出的独立 SOL/xhigh 审查代理执行；main 没有执行本审查。未运行 Node、进程、数据库、HTTP、浏览器或任何新测试；3 passed 仅复用 Dirac 封存证据。

## 已关闭：原 P2 可信 birth 丢失

原 P2 已由 `7f6debc` 正确关闭。

- [`services/maf-supervisor/main.mjs`](../../../../../services/maf-supervisor/main.mjs) 148–170 行先把 `lastKnownProof` 初始化为 `null`，并且只在 152/160 行 `validateProof()` 成功后，于 153/161 行保存带 process 的 proof。
- guardian challenge 或 `persistResults` 抛错时，166–170 行仍写 `unknown`，但把该已验证 proof 传入 `setState()`；112–118 行因此把可信 process/birth 保留到 observation 和 source receipt。
- 缺失或 invalid proof 会在赋值前失败，`lastKnownProof` 保持 `null`；不会用 PID、自报字段或无效 HMAC 填充未来事实。
- `query/observe` 不进入 174 行后的 start/spawn 分支；`unknown` 也不是 exited/release 证明。

[专用场景](../../../../../tests/task-workers/maf-supervisor-last-known-process.test.mjs)固定了“合法 running/birth proof + guardian socket 不可达 → unknown 且保留 process/source”路径。封存结果记录该场景通过；本次没有重跑。

## P1 · result 文件存在时，缺失或空 callback 被当作持久化成功

**文件与行：**[`services/maf-supervisor/main.mjs`](../../../../../services/maf-supervisor/main.mjs) 38–44、136–143、146–170 行，关键为 39、140、147、154–164 行。

**触发：**真实 Worker 已在固定 `record.directory/worker` 写入 `result-request.json` 或 `sdk-request.json`，但生产装配漏传 `persistResults`；或者已传 callback 直接 resolve `undefined/null`，没有完成 controller-side durable persistence。

**实际路径：**

1. 39 行把缺失的 callback 默认成 `async () => {}`，43–44 行的类型检查因此无法发现配置缺失。
2. 136–143 行看见请求文件后调用该 no-op；返回值没有任何非空/持久回执检查，resolved `undefined/null` 被当作成功。
3. 154–164 行随后可以把真实 proof 的 `running`/`exited` observation 持久化。
4. 一旦 inbox 已写 `exited`，147 行后续 `observe()` 直接返回，不再调用 `persistProducedResults()`。即使重启后补上真实 Controller callback，自动补交入口也已被终态短路。

**影响：**Supervisor 可以在结果字节尚未进入 controller/P03/P04 时，永久保存进程终态并停止自动补交。结果文件之后若按环境保留策略清理，会造成静默结果丢失；同时违反“先持久化已产出结果，再提交 P05 process observation”的固定顺序。Node 没有伪造 ResultReceipt，但把“未执行 callback”当作 persistence success，属于 fail-open 的数据完整性问题。

**最小反例：**

```text
NodeSupervisor.open({ ..., persistResults omitted })
fixed child writes worker/result-request.json and exits
observe/query sees signed exited proof
persistProducedResults() calls default no-op
inbox becomes exited while result was never sent or persisted

restart with a real persistResults callback
observe() returns exited at its terminal-state guard
callback is never invoked
```

该反例只使用 `7f6debc` 的公开构造参数和已有固定 workerDir，不依赖 Python、PG、HTTP、PID 探测或完整 M2。

**合同依据：**

- [P10 core interface](references/P10-core-interface.md) 39 行要求 `persist_results` 先耐久核对既有 M1 结果，再把 observation 交给 P05。
- [P10 shared handoff](references/P10-shared-handoff.md) 8–9 行要求补交精确已产出 bytes，缺失 raw transport 不能成为伪造 process settlement 或释放容量的理由。
- [P10 Worker bridge interface](references/P10-worker-bridge-interface.md) 45–48、59–64、122–126 行把不确定提交限定为重放同一已保存请求，并要求真实 controller receipt，禁止本地假成功。

**最小修复方向：**保留“没有 result/sdk 文件时无需 callback”的兼容行为；一旦检测到任一请求文件，必须要求显式注册的 `persistResults`，并要求其返回可识别的非空 durable result/archive settlement。callback 缺失、返回 `undefined/null` 或抛错都保持 `unknown` 与 last-known process，不能写 `running/exited`。这样旧 10 个无结果文件的 Node cases 无需重跑；只需为“文件存在 + callback 缺失/空返回”增加窄 RED→GREEN，并复测现有 3 个 delta cases。

## hook 相邻安全性核对

除上述 P1 外，当前窄 hook 的相邻约束成立：

- 136–143 行只从已持久 operation 的 `record.directory/worker` 派生目录，并向 callback 传 canonical Assignment copy；调用者 auth/body 中的路径不能替换它。
- 两个文件都不存在时直接返回，不虚构结果。
- 显式 callback 抛错会被 166 行捕获，最终为 `unknown`；由于 last-known proof 在 callback 前保存，失败仍保留可信 birth，不写 submitted/exited/release。
- 已注册 [`ControllerAdapter.persistResults`](../../../../../services/maf-supervisor/controller-adapter.mjs) 的相邻实现使用固定目录、`O_NOFOLLOW`、0600 文件约束、显式最大字节、Assignment 精确匹配与受限 controller action。该 adapter 不是本次 delta 的审查对象；这里只确认 hook 可把边界交给它，不能据此标完整 M2 通过。

## 证据复用与范围

- [delta 报告](../../../../../docs/vnext/evidence/P10/node-delta/report.md)和 [完整输出](../../../../../docs/vnext/evidence/P10/node-delta/test-output.txt)记录代码 `7f6debc` 的 3 passed、0 failed、409.782292 ms：1 个 last-known process 场景和 2 个 persistResults 场景。它们覆盖成功 callback 与 callback 抛错，没有覆盖 callback 缺失或 resolve 空值。
- 截图：[P10 Node delta](../../../../../docs/vnext/evidence/P10/node-delta/screenshots/node-delta.png)。

![P10 Node delta 既有截图](../../../../../docs/vnext/evidence/P10/node-delta/screenshots/node-delta.png)

- 这些 direct NodeSupervisor tests 没有启动 HTTP server 或发送 HTTP 请求，因此没有新增 HTTP 报文；未伪造请求包。旧 10-case 的[完整 HTTP 复现包](../../../../../docs/vnext/evidence/P10/node-first-flow/http-reproduction.md)保持原证据用途，本次不重读为新 delta 通过证明。
- 旧四窗口、单 receiver、digest conflict、accepted≠stopped 与旧身份判断全部复用上一轮审查，不扩大矩阵。
- Python、Task started、真实 P05/P09、MAF HostTransport、Pod/同 UID 隔离、容量和完整 M2 仍未验证。本次没有执行 cleanup 探活或进程操作。
