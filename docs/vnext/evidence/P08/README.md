# P08 evidence index

状态：`not_run/未验证`。本目录目前只保存开工接口 RED，不表示 Session 发布、CAS、恢复、审批或 SDK consumer 已通过。

- 首 RED：[initial-red/README.md](initial-red/README.md)
- 测试入口：`tests/vnext/test_session_approval.py`
- fixture/support：`tests/vnext/support/p08.py`

后续证据必须来自真实 `SessionRepository`、Input/Approval service、Worker SDK adapter 及其实际消费者。PG/HTTP/OpenAPI 未获本 owner 执行窗口；当前没有相关运行证据。
