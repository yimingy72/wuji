# P08 Descartes review fixes — SOURCE_ONLY

固定审查：[P08-platform-review.md](../reviews/P08-platform-review.md)。修复代码：`f4c3b76`。状态：4P1+2P2 源码已处理；实际 PG/SDK/HTTP/跨进程候选与完整 P08 均为 `not_run/未验证`。

源码变化：0014 只增加精确 approval transition；reject frontier 固定真实 P01/core1.18 result、持久 decision/delivery、完整 binding 与零 Attempt；input/approval INSERT 增加初态和 deferred source guards；源 Worker 在自身 ACL/JTI 下遍历完整 graph，新 model-output 必须有 session_object provenance，已发布祖先不要求旧 JTI 永久有效；每个 model frontier 固定 P06 request messages/digest/predecessor positions，并要求完成工具结果进入后继真实 request。

已有无 DB checks：approval trigger source RED→GREEN；rejected frontier type RED→GREEN；intake guard source RED；P06 request causal mapping 定向 GREEN；最终 F1/F2/F3/F5 source batch 为 `3 passed in 0.80s`。F4/F6 没有用 mock 图自证，必须由真实数据库 publication/ACL/JTI 负例验证。完整 raw 均留在 `work/p08/` 受限 ignored 目录，本目录只发布来源与摘要：[binding.json](binding.json)。

本切片没有运行 PostgreSQL、DDL、真实 SDK/Gate、HTTP、child/Host 或浏览器，没有新增截图/HTTP 包，也不把源码检查写成 P08/G2 通过。
