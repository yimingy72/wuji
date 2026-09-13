# C0 定向验证原始证据

被测基线为 `890b54064f370c6e9ace2bc5d92cce2a86a1eefc` 加本批保存的 C0 SOL diff。Remote 最终结果为 7 passed / 14.81s；Pod 两项在首轮目标集合末尾通过，未因 Remote 测试 CA 修复而重跑。Pod 使用真实 PostgreSQL P05/0017 和记录型 PodClient，只证明数据库许可、session lease、Pod API 输入及 receiver 登记，不证明真实 Kubernetes Pod；后者归 C2。

前两轮 collection 分别因 maf-worker venv 看不到 `wuji_task_runtime`、加入源码路径后仍缺其已锁定的 `kubernetes` 依赖而停止；这是测试入口依赖前提，不是产品运行失败。随后改用仓库现有根 `task-runtime` dependency group，import 探针确认 `kubernetes 36.0.3` 与 Pod runtime 同时可加载，未修改 Bacon 管理的 lock。该类问题至此停止排查。最终 Remote 命令执行了整个测试文件，因此纯 wire 用例被顺带复跑一次；之后不再重复。

![验证截图](screenshots/verification.png)

完整输出：[`raw/pytest.txt`](raw/pytest.txt)。默认未启用 receipts 配置的模板兼容检查：[`raw/default-template-compat.txt`](raw/default-template-compat.txt)。Pod 首轮完整输出：[`../c0-sol-target/raw/pytest.txt`](../c0-sol-target/raw/pytest.txt)，collection 顺序：[`../c0-sol-target/raw/pod-collection.txt`](../c0-sol-target/raw/pod-collection.txt)。

依赖前提两轮原始 collection 输出：[`../c0-sol-first/raw/pytest.txt`](../c0-sol-first/raw/pytest.txt)、[`../c0-sol-second/raw/pytest.txt`](../c0-sol-second/raw/pytest.txt)。

以下 JSONL 每行保留完整方法、URL、Headers、请求体和响应体；body 以未截断 base64 保存，测试凭据均由隔离身份夹具签发：

- 主链及撤销后旧回执：[Kali 原报文](raw/b822a945b704/c0-kali-https.jsonl)、[平台 callback 原报文](raw/b822a945b704/c0-platform-https.jsonl)、[Gate/P03 原报文](raw/b822a945b704/p06-tool-http-exchanges.jsonl)。验证点是 DB 原 ToolPermit 经双向 HTTPS 读取真实文件、P03 产物已可取回、撤销后只查询旧 attempt 且新调用被拒绝。
- callback 已提交后 ACK 丢失：[平台原报文](raw/382794ef5011/c0-platform-https.jsonl)。验证点是 check_execution 已把 attempt 写成 dispatched，但传输只得到不明结果，Kali 保留 prepared/unknown。
- callback 已提交后 5xx：[平台原报文](raw/f39b985609cf/c0-platform-https.jsonl)。验证点同上。
- callback 已提交后坏 ACK：[平台原报文](raw/2d7809d2e735/c0-platform-https.jsonl)。验证点同上。
- dispatch 不明且 query 返回 not_registered：[Kali 原报文](raw/917e9296c298/c0-kali-https.jsonl)、[平台 callback 原报文](raw/917e9296c298/c0-platform-https.jsonl)。验证点是只用同一 attempt 查询一次，Gate 保持 unknown，retry 不产生新 attempt。
- permit 篡改、错误 executor 与错误 Gate 主体：[Kali 原报文](raw/c42020885ee8/c0-kali-https.jsonl)、[平台 callback 原报文](raw/c42020885ee8/c0-platform-https.jsonl)。验证点是自算摘要的篡改 permit 仍被 DB 原 permit 拒绝，错误部署身份不执行也不写 receiver receipt。
