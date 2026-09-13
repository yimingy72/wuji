# P08 initial SessionRepository RED

任务开始时工作树 HEAD 为 `01f977d440d36fac765a3277cdde227761151cef`，随后并发 owner 持续推进。`INTERFACE_READY` 后重跑的实际首 RED 在命令输出中精确捕获 HEAD `29a09e088d504afdcbd1323fdbd229f90718a157`，并绑定本目录对应的未提交 P08 测试 diff。日期：2026-09-13。

本切片只冻结 `SessionRepository` constructor、`publish` 与 `load_published` 的参数形状。`--collect-only` 成功收集 1 项；执行该项以退出码 1 失败，原因是生产模块 `wuji_core.execution.sessions` 尚不存在。这是实现前 RED；P08 工程验收状态仍为 `not_run/未验证`。

- 收集日志：[collect-only.txt](collect-only.txt)
- 接口就绪后的精确 SHA RED：[red-interface-ready.txt](red-interface-ready.txt)
- 更早的同根因 RED（命令瞬间未捕获 HEAD）：[red.txt](red.txt)

本切片未连接 PostgreSQL，未启动服务，未发送或捕获 HTTP 请求；因此没有可复现 HTTP 报文，也没有据此声称数据库、HTTP 或 SDK 行为通过。验证截图待主代理在完成实际成果验证时统一纳入，不把文字渲染图伪装成运行截图。
