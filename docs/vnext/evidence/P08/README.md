# P08 evidence index

状态：已有局部无 DB checks 执行；完整 P08 仍为 `not_run/未验证`。现有记录不表示 Session 发布、CAS、跨进程恢复、批准消费或真实 SDK/Gate consumer 已通过。

- 首 RED：[initial-red/README.md](initial-red/README.md)
- Worker SOURCE_ONLY 测试收集：[source-collection.txt](source-collection.txt)
- Worker 无 DB 单元检查：[worker-unit.txt](worker-unit.txt)
- 版本化记忆输入定向修复：[memory-context-fix/README.md](memory-context-fix/README.md)
- SessionRepository 接口 GREEN：[platform-interface/README.md](platform-interface/README.md)
- Candidate/0014 SOURCE_ONLY checks：[source-prep/README.md](source-prep/README.md)
- 测试入口：`tests/vnext/test_session_approval.py`
- fixture/support：`tests/vnext/support/p08.py`

后续完整证据必须来自真实 `SessionRepository`、Input/Approval service、Worker SDK adapter 及其实际消费者。当前无 DB 结果只覆盖公开接口形状、M1 snapshot、公开 Content/identity 恢复、固定 memory store 与版本化记忆输入；不证明自动记忆学习、原生 FileMemoryProvider、SDK 模型往返、ToolGate、发布/CAS、跨进程恢复或 capability 发布。PG/HTTP/OpenAPI 当前没有本 owner 的固定执行窗口；没有相关运行证据。
