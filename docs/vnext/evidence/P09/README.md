# P09 永久证据交接

归档日期：2026-09-13。状态：**已验证切片、独立复审 PASS；完整 P09/M2 仍 partial**。本次仅从原始任务记录、Git 对象和 scratch 审查归档，没有运行测试、数据库、HTTP 或生产检查。

原执行者为 Archimedes（按分工 SOL/xhigh）。完整命令、退出码、UTC 时间、原始记录定位及摘要见 [machine index](index.json)。以下数字按各自代码版本解释，不能相加成新提交的全量验收：

| 已执行范围 | 原始结果 | 代码绑定与输出 |
| --- | --- | --- |
| 原 P09 文件 | exit 0；31 passed in 16.57s | 提交后 `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c`；[输出](outputs/baseline-31.txt) |
| 快照/P04/P06 直接消费者 | exit 0；4 passed in 3.53s | 同一 `a3f7a95`；[输出](outputs/consumers-4.txt) |
| 两租户共享最后容量 | exit 0；1 passed in 0.74s | 同一 `a3f7a95`，复用 P05 两连接用例；[输出](outputs/capacity-race-1.txt) |
| 审查 A/B/C RED | exit 1；3 failed in 5.04s | `57ec12e` 基础与未提交测试，P09 生产仍为 `a3f7a95`；[完整失败输出](outputs/review-abc-red.txt) |
| 审查 A/B/C GREEN | exit 0；3 passed in 5.00s | 提交前工作树，随后七个路径提交为 `e0a10b586905ed705b0d7f520bda6f6f96b26cac`；[输出](outputs/review-abc-green.txt) |
| 0010→0011 升级/重复 migrate | exit 0；1 passed in 1.22s | 同一提交前候选；[输出](outputs/upgrade-0011.txt) |
| receiver Pod UID 复制 | exit 0；1 passed in 2.49s | 同一提交前候选；[输出](outputs/pod-uid-1.txt) |

两份审查按原字节保存：[Nash 初审 NEEDS FIX](reviews/P09-review.md)、[Dalton 独立定向复审 PASS](reviews/P09-rereview.md)。PASS 仅关闭 A/B/C 与 receiver UID 接缝，可作为后续持久化迁移的 P09 关口，不等于所有关联 AC 通过。审查内“尚无永久包”等描述保留其当时事实；本目录是后续归档。

A 修复在任何接收者相关准入写入前验证 receiver 当前 read/observe 权限；B 拒绝无真实同 Task/Reason Run canonical Intent 的 `propose_intents`，保持原 P04 结果及 generation；C 持久保存每 Work consideration round，考虑/拒绝均推进，rank/aging 只在轮次内排序。0011 在 0010 上增量添加可信 receiver `pod_uid`；旧无 UID 注册会禁用，不能猜测回填。

数据库用例使用既有隔离 PostgreSQL：业务路径为非 owner、无 BYPASSRLS 应用角色；迁移和显式部署前提由独立 owner 角色设置。31 项混合纯函数与 PG；其中双连接用例是 Scheduler ownership 竞争，另列的竞态 1 才是两租户容量竞争。升级 1 只执行 migration role，不冒称它验证了应用 RLS。上述属性根据原命令及绑定测试实现核对，原逐查询记录缺失的限制如下。

证据载体与缺口：

- [命令原始记录摘录](command-records.jsonl.gz)保存七组目标记录及同任务已有失败/过渡命令，含 stderr/stdout、返回码、时间和 Git 提交记录。只做路径/凭据脱敏，没有删改失败为成功；原记录中的 pytest 自带摘要/省略保留。
- [输入和代码索引](codefile-index.json)给出每个 Git blob、SHA-256 及 [压缩源码包](codefiles.tar.gz)成员。包含三个历史截面的测试输入工厂、P09 源码、SQL 定义及直接依赖，不使用当前被 P13/M2 修改的文件。这些是源码副本，**不是重建出来的 SQL 执行轨迹或运行环境**。
- [审查修复编辑记录](review-edit-records.jsonl.gz)保留原未提交补丁。C 的首 RED 因 `last_considered_work_id` 不存在失败，最终实现改用 `consideration_round`；它不是完整的饥饿运行轨迹。RED 未提交测试的完整最终字节快照未保存，不能拿 e0a10b5 的测试冒充当时输入。
- 原 pytest 临时目录已不含这些 P09 运行；`postgres-events.jsonl` 中的 SQL/参数/返回行、随机输入/原始产物、身份事件及相关 HTTP 交换均未找回，登记为 **missing**。因此不能提供完整 SQL 复现包。原 stdout 和 Git 输入源码仍可核对，不重跑补齐。原命令未指定 JUnit，本次也不生成 JUnit。
- 原 4 项回归包含进程内 P04 HTTP 调用；此前交接口头“没有 HTTP 交换”过于宽泛，应以绑定测试实现为准。本包没有找回这些交换，也不补造 HTTP 或截图。
- `e0a10b5` 的 3+1+1 在提交前执行，无提交后 DB 重跑；代码绑定来自原编辑/提交记录及 Dalton 复审。缺少当时逐文件 SHA-256 清单，本次计算的 Git 指纹只证明所归档源码版本，不能升级为当时实时文件指纹。
- 未脱敏命令摘录保存在被忽略的 `work/p09-evidence-private/`（目录 0700、文件 0600），不入 Git；本包排除本机 PG 配置、私钥和 bearer。合成密钥生成代码与 synthetic UID 是测试前提，不是生产密钥或 Kubernetes 证据。

AC-007/015/018/024/025/026/027/028/029 仍保持 **partial**。特别是：真实 P10/M2 Outbox→Supervisor→Worker/Pod、P08 同 board_revision 的非知识事件、真实退出回执驱动的 Reason failure/有限重试、Session 恢复、完整正向 Reason/wait/completion 消费链，均不由本包标通过。B 的 all-rejected 拒绝路径已有实测；空/非 Intent 等其他分支在复审中静态核对，不冒称额外测试。

归档脚本 [archive_records.py](archive_records.py)仅解析原 JSONL、读取固定 Git 对象并输出脱敏/压缩数据；不导入生产模块。执行它不会重新运行上表测试。清单与文件摘要见 [SHA256SUMS](SHA256SUMS)，其中不包含清单自身。迁移和公共方法交接见 [P09 handoff](../../P09-handoff.md)。
