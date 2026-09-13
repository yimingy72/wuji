# P08 平台审查归档

本目录永久保存 P08 平台授权、恢复与原子性静态审查。归档为 derived 文档，只调整永久路径、相对链接和来源标记；没有重跑测试、数据库、HTTP、SDK、截图、formatter 或 browser。

| 报告 | 固定源码 sourceSHA | 结论 | 运行证据 | 源审查 SHA-256 |
| --- | --- | --- | --- | --- |
| [P08 平台静态审查](P08-platform-review.md) | `a75584777af917d269480f48af97a696ecb0a821` | CHANGES REQUIRED：P1 × 4、P2 × 2 | 未运行；source-only | `c129742c4633e945eb3b183ac950a82c102de745683c7ce5c809303f6a72c7cd` |
| [原六项定向复审](P08-platform-rereview.md) | `f4c3b761f4c829cd0bd28cc71425ec000a798c31` | CHANGES REQUIRED：F2/F3/F4 为 P1、F5 为 P2；F1/F6 仅 source-addressed | 复审无新 checks；真实 DB/RLS/SDK/跨进程验收 pending | `f254b5e55f14b62760fa93cdff0d5bc5cb285db795b58b690e6d60c2de607e5a` |

初审六项与复审四项残留均已交 Dewey。后续固定四残留 diff 及实际证据准备好后再恢复定向复审；未变 F1/F6 复用本次 source-addressed 依据，不据此宣布 P08 通过。D12/candidate、B2、M2/0013 current-intake 与当前 dirty 字节不属于上述固定复审结论。
