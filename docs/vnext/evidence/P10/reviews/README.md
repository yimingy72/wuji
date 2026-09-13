# P10 Node Supervisor 审查归档

本目录永久保存 P10 Node-only Supervisor 的四次独立 SOL/xhigh 源码审查。归档动作只复制既有文档、调整相对链接并记录来源哈希；没有重跑测试、截图、进程、数据库、HTTP 或业务流程。main 没有执行这些源码审查。

## 审查历史

| 报告 | 固定源码 | 当时结论 | 后续状态 | scratch 源字节 SHA-256 |
| --- | --- | --- | --- | --- |
| [首次审查](P10-node-review.md) | `72d26a02308ab54db2c7c56b52f9861b8acdda82` | P2，非 PASS：unknown 丢失已验证 birth | 由 `7f6debc` 关闭 | `fc991ccb4ccc90bbe95a5331ab526ee7803bfe9c967def9745479608d7dd311c` |
| [第一次窄复审](P10-node-rereview.md) | `7f6debc06575a63ac168d1022d88f06ea1619a25` | P1，非 PASS：缺失/空 settlement 可被当作成功 | 由 `01f977d` 关闭直接反例 | `356b3a528a515ebb8448e7ac3ee25726dcd722f54ed0381951fe6a0e7d695c8a` |
| [第二次窄复审](P10-node-rereview-2.md) | `01f977d440d36fac765a3277cdde227761151cef` | P1，非 PASS：顶层 lookalike 与 result/BlobRef 类型未绑定 | 由 `87e1304` 关闭 | `be3658c925171a7ec41a96b226465cfb305062795c2d8fd0fde0d7f61d64b8e0` |
| [第三次窄复审](P10-node-rereview-3.md) | `87e13042a62768b5ad1206f6e7837dee7b28c607` | SOURCE PASS：旧 P1 两个漏口已关闭 | 固定证据 `8866976` | `358fc07dd92db790118af7e54fc991fbf92d3d0ba7145d2106e2bd1e35577dfc` |

前两轮失败没有因后续修复改写为旧 PASS；每份报告保留其固定 SHA、执行者、触发、影响与当时结论。

## 证据入口

- [Node first-flow：旧 10-case、四窗口与完整 HTTP](../node-first-flow/report.md)
- [Node delta：可信 birth 与初始 persistResults hook](../node-delta/report.md)
- [Node delta review-fix：缺 callback/null settlement](../node-delta/review-fix/report.md)
- [Node delta review-fix-2：严格 settlement 类型与身份绑定](../node-delta/review-fix-2/report.md)

第三次报告仅证明固定 Node 源码的 P1 已关闭，并绑定上述 review-fix-2 证据。完整 P10/M2、Python、真实生产隔离及其他后续发现仍由各自验收记录表达。

## 历史接口引用

报告引用的四份 scratch 接口文档以原字节复制到 [references/](references/)，用于保持原行号和审查语境；它们不是新的权威 Spec/Plan，也没有因归档改变状态。

| 原字节副本 | SHA-256 |
| --- | --- |
| [P10-M2-brief.md](references/P10-M2-brief.md) | `79b433129be32b21deccf198b454387ae2587e580f0c17e4e0dac82179bcdad1` |
| [P10-core-interface.md](references/P10-core-interface.md) | `ca373a78271dc4875be8ffae321c7cf8e044b4ae8ea7dbb9b8de967d7c4a3d37` |
| [P10-shared-handoff.md](references/P10-shared-handoff.md) | `cc9b991d89f50309301240374a7820df2b0103c0a4ac4098b8aeb4a5e91943b0` |
| [P10-worker-bridge-interface.md](references/P10-worker-bridge-interface.md) | `41c5a3ed77ca43060267ab0b0acf4de3a58d7219ab2ee2dbd8096ed4837d810b` |
