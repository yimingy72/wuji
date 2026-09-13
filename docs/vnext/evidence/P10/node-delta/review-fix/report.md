# P10 Node persistResults settlement 复审修复

状态：Epicurus 针对 `7f6debc` 提出的 P1 已在代码
`01f977d440d36fac765a3277cdde227761151cef` 定向修复。既有 Node 10-case 矩阵未重跑。

Supervisor 仍允许未配置 `persistResults`，以保持没有输出文件的普通 child 退出路径；但一旦固定 workerDir 中存在 `result-request.json` 或 `sdk-request.json`，就必须实际调用显式 callback，并且 callback 必须返回可识别的严格 BlobRef 或 ResultReceipt。callback 缺失、抛错、返回 null/undefined 或其他不可识别值，都沿现有 `observe` 路径保持 `unknown`，保留已验证 process/birth，且不写 exited、不释放、不重新 spawn。

fresh 新增 delta 命令为 **5 passed / 0 failed / 739.813917ms**，其中包括原 3 场景和缺失/null settlement 两个新增场景。完整输出见 [test-output.txt](test-output.txt)。同一变更后的真实 M2 child 受影响测试为 **1 passed in 8.91s**；它由 controller-adapter 返回真实 P04 ResultReceipt，因此满足 durable settlement 识别，不依赖 no-op。

这些 Node 测试直接调用 NodeSupervisor，没有 HTTP server 或请求，因此没有 HTTP 报文可附。未运行 PG、旧 Node 10-case、P06、M1 或外部服务。

验证截图：

![P10 Node settlement review fix](screenshots/node-settlement.png)

本结果只关闭该 Node P1，不提升完整 M2/P10/P07。
