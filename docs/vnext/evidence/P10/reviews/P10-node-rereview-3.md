# P10 Node settlement P1 第三次窄复审

> 永久归档派生说明：本文件派生自 `.superpowers/sdd/vnext-v2/P10-node-rereview-3.md`；源字节 SHA-256 `358fc07dd92db790118af7e54fc991fbf92d3d0ba7145d2106e2bd1e35577dfc`。除本说明与相对链接目标外，正文、执行者、提交 SHA 和各轮历史结论保持原样；精确行号引用使用本目录 `references/` 中的原字节副本。

- 日期：2026-09-13
- 源码结论：**PASS**
- 固定源码：`87e13042a62768b5ad1206f6e7837dee7b28c607`
- 比较对象：`01f977d440d36fac765a3277cdde227761151cef`
- 固定证据：`886697618e052febc10d4c20b85b07c0c6e999d0`
- 证据状态：Dirac 的 7 项聚合输出、HTML 与 PNG 已提交归档
- 角色：本审查由 main 直接派出的独立 SOL/xhigh 审查代理执行；main 没有执行本审查
- 方法：只读源码窄复审；本审查没有运行 Node、测试、进程、数据库、HTTP 或浏览器

## 结论

`87e1304` 的源码窄复审 PASS。前两轮报告指出的同一 settlement P1 两个漏口均已关闭：

1. 非严格的顶层 ResultReceipt lookalike 不再能冒充 durable settlement。
2. settlement 类型已与固定 workerDir 中实际存在的 result/sdk 文件绑定；result request 不能再由 BlobRef 代替结算。

该结论只表示本次固定 Node 源码增量没有发现原 P1 残留，且对应窄证据已经完成工程归档。它不表示完整 P10、M2、Python bridge、PG、平台 HTTP、真实生产隔离或其他阶段验收通过。

## 源码核对

### ControllerAdapter 严格验证与可信内部 ack

[`services/maf-supervisor/controller-adapter.mjs`](../../../../../services/maf-supervisor/controller-adapter.mjs) 在生成内部 settlement ack 前执行以下核对：

- ResultReceipt 顶层只允许合同 required/optional 字段，status 使用固定枚举。
- 每个 ComponentReceipt 递归检查 exact keys、component status、local/request ref、可选 KnowledgeRef 和 ErrorCode。
- KnowledgeRef 检查固定 entity type、ID 和 revision；ErrorCode 只接受现有合同枚举或空值。
- result receipt 的 `submission_id` 必须等于原 Assignment identity 与 operation 计算出的稳定 `maf-m1:*` submission identity。
- sdk-only 路径只接受严格 BlobRef，并要求其 `sha256` 等于原 `sdk-request.json` 中的 `sdk_digest`。
- 外部 ResultReceipt/BlobRef 通过后才转换成 `wuji.worker-settlement.v1` 内部判别式 ack；ack 固定包含 kind、Assignment digest、原 submission identity 或 SDK artifact/digest 绑定以及 receipt digest。
- controller 响应异常、合同不完整、嵌套字段无效、submission 不匹配或 SDK digest 不匹配均抛错，不生成可信 ack。

### Supervisor 文件类型与 ack kind 绑定

[`services/maf-supervisor/main.mjs`](../../../../../services/maf-supervisor/main.mjs) 的窄 hook 执行以下规则：

- `result-request.json` 与 `sdk-request.json` 都不存在时，不要求 `persistResults`，普通无输出 child 可按真实 process proof 进入合法终态。
- 存在 `result-request.json` 时，期望 kind 固定为 `result`；即使同时存在 sdk 文件，也只能接受绑定原 Assignment digest 与稳定 submission identity 的 result ack。
- 仅存在 `sdk-request.json` 时，期望 kind 固定为 `archive`；只接受绑定原 Assignment digest、严格 BlobRef 和 receipt digest 的 archive ack。
- 缺 callback、callback 抛错、返回 null/undefined、外部原始 BlobRef/ResultReceipt、kind 错误、Assignment/submission 错误或不可识别 ack 都不能通过。
- settlement 未确认时仍保持 `unknown`，并保留已经通过 guardian proof 验证的 process/birth；不会写 `running/exited`，不会进入 spawn，也不构成容量释放证明。

因此，第二轮报告中的两个最小反例现在均 fail closed：`components=[null]` 的伪 ResultReceipt 无法生成内部 result ack；result 文件存在时返回原始 BlobRef 也无法通过 Supervisor 的 kind-bound ack 检查。

## 三轮历史

- [第一次审查](P10-node-review.md)：固定 `72d26a0`，发现 unknown 转换丢失已验证 process/birth 的 P2。
- [第一次窄复审](P10-node-rereview.md)：`7f6debc` 关闭 birth P2，但发现 result 文件存在时缺失/空 callback 可被当作成功的 P1。
- [第二次窄复审](P10-node-rereview-2.md)：`01f977d` 关闭缺 callback/null 直接反例，但发现 ResultReceipt 仅顶层检查且 result 文件可接受 BlobRef 的同一 P1 两个具体漏口。
- 本次第三次窄复审：`87e1304` 关闭上述两个漏口，源码结论 PASS。

前两轮发现、触发、影响和当时固定 SHA 均按原报告保留；本报告不改写历史失败，也不把后续修复倒填为旧提交已通过。

## Dirac 证据与归档绑定

Dirac 已在证据提交 `886697618e052febc10d4c20b85b07c0c6e999d0` 固定以下窄证据：

- [证据报告](../../../../../docs/vnext/evidence/P10/node-delta/review-fix-2/report.md)
- [7 项聚合输出](../../../../../docs/vnext/evidence/P10/node-delta/review-fix-2/test-output.txt)
- [验证截图](../../../../../docs/vnext/evidence/P10/node-delta/review-fix-2/screenshots/node-settlement-kind.png)

![P10 Node settlement 类型绑定截图](../../../../../docs/vnext/evidence/P10/node-delta/review-fix-2/screenshots/node-settlement-kind.png)

固定记录绑定代码 `87e13042a62768b5ad1206f6e7837dee7b28c607`，保留的 aggregate 为 7 passed、0 failed、880.645375 ms，包含原五项以及“invalid nested result settlement”和“result file + BlobRef”两个定向反例。原 per-test timing stream 未保留，证据已如实注明且没有补造逐项耗时。该输出由 Dirac 执行，本审查只复用和读取，没有重跑，也不称为独立测试。

证据提交只新增上述 report、聚合输出、HTML 与 PNG，没有修改源码。本次绑定仅核对实际路径、文件、代码 SHA 和 evidence SHA；源码仍为 `87e1304`，因此没有再次执行源码复审。

上述 direct Node 测试没有启动 HTTP server 或发送 HTTP 请求，所以没有新增 HTTP 报文；不得构造请求包代替不存在的交互。旧 10-case 与其 HTTP/截图证据保持原历史用途，本次未重跑、未重审。

受影响 M2 child 的单项结果属于 Dirac/M2 证据，不在本源码审查范围，也不用于提升完整 P10/M2 状态。Python、Bridge/OpenAPI 其余实现、P09/P13、PG、平台 HTTP、同 UID/生产隔离与完整生命周期同样不在本次结论内。
