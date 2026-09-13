# P10 / M2 实际投递与受信结果补交收口

2026-09-13，主代理在独立 SOL 审查后固定的修复合同。原 Spec S07/S08/S10、P10 与 M2 目标不变。当前范围 **changes required**；本文件描述待闭合行为，不是新的通过证据。

## 现有证据边界

`6e90a97` 核心、`e40e7e2` 桥接测试和 `87e1304` Node 修复后的实际 child 检查，已证明 P09 生成 Assignment、真实 Node/Python 子进程、P05 started 屏障、两 Gate、P03/P04 及原字节补交的限定链路。该场景直接调用 Node start，未消费生产 DispatchOutbox；撤销后的检查只是取回先前已接纳回执。不能据此声称完整 Scheduler→Outbox 或撤销后首次补交已通过。

独立 SOL 审查共有四项 P2：真实 Outbox/产品装配缺失和未消费 bootstrap 文件；回执缺精确 Harness Profile 绑定；撤销后首次 intake 与普通 Worker 写入竞态；start grant 缺当前注册的 Pod UID 比对。修复按一个固定候选组织必要检查，旧 Node 十项和无关 P06/M1 不重复运行。

## 生产入口与唯一 bootstrap 路径

新增生产 RuntimeDispatcher/服务入口，组合真实 DispatchOutbox、持久 DispatchJournal、WorkerHostBridge/HTTP router、ReceiverAuthorizer 和 Reconciler。服务从当前接收者有权管理的真实 Task Outbox/Assignment 读取稳定 operation，不从测试 helper 或模型生成启动身份。轮询有界，外部网络请求不占长数据库事务。

实际启动顺序是读取并核对规范 Outbox/完整注册 → query 原 operation → 若没有既有/不明发送，耐久保存 attempted → 唯一 PUT → 真实 Supervisor 观察 → P05 记录。发送响应不明时只查询原 operation；404 或租约超时不清掉 attempted，不换 ID 再启动。Reconciler 继续先保存已产出结果，再记录进程观察；结果回执不等于进程退出。

凭据只保留一条已实际消费的 bootstrap 路径：Node ControllerAdapter.bootstrap → WorkerHostBridge.receiver_bootstrap → P09 当前 receiver-scoped 凭据读取 → Worker 私有目录。DispatchOutbox 不再额外写无人读取的 FileBootstrapStore 明文凭据。所有秘密留在相应受限主体和文件，不进入 Outbox、公开回执、命令行、模型参数或普通报告；Child 不持数据库、Task Gateway Key 或签发 Key。

生产应用的配置/依赖可由部署显式装配，不能 import 测试 support 或旧 Cairn app。P20 的镜像、完整部署参数与干净启动仍另行验收；新增库类存在本身不构成产品服务已安装的证明。

## 精确执行绑定

RegisteredRun 从冻结 TaskDefinition 的 `worker_profiles[assignment.work_kind]` 解析实际 Harness ref/digest，核对定义摘要、kind 与 Assignment 绑定。进程回执的 profile_id 必须与这一精确 Harness ref 一致；model/runtime ref 虽也在 profile_refs 内，不能代替 Harness。

start grant 在启动前核对当前 scheduler_receiver 的 receiver_id、runtime_attempt、subject、environment_ref 和 pod_uid，全量匹配实际 RegisteredRun；后置 await-start 检查不能替代此项。错配置或错 Pod 身份不能启动，即使原 bootstrap/签名回执的其他字段有效。实际退出仍依赖可信 process birth/exit 证据，不用 PID 存在判断所属。

## 普通写入与受信补交分别授权

普通 Worker 的模型输出/SDK 保存必须在实际持久事务中重读当前 Run credential、有效期、撤销和完整归属；HTTP `_ready` 的先行检查不能覆盖随后撤销的竞态。维持 Worker 没有 control/observe/admit/can_settle 的边界。

新增受限 receiver retained-result 组合入口，使用**实际验签的 receiver 主体**、明确 settlement 权限及持久 receiver/Run/source-writer 绑定。不能根据请求字段构造替身 Worker/Supervisor Principal，不能伪改交易权限或 Run 状态。原 P04 普通 `run_disposition` 语义保留。

补交同时覆盖两个明确分支：原 Run、Worker 绑定和当前许可仍有效时，核对精确原字节、上下文、调用/回执及来源后，按原 P04 合法结果接纳规则处理；真实撤销/epoch stale 的首次 intake 只进入 historical_only，保留原始结果，不新增 Claim/Intent/ready、不解除 hold/pause、不重开已关闭 Task。不能因 receiver 不具备普通 Worker 写权限而丢掉所有正常 503 补交，也不能把 settlement 权限升级为执行或任意知识写权限。

先按当前访问权限核对原幂等记录；已接纳结果的重复读取保持原回执，内容冲突拒绝。未接纳的新补交绑定实际保留请求的字节/摘要、原 Assignment、Run、context/read_set 和 SDK/tool receipts；缺真实来源不构造成功。接收者的权限和 source-writer 绑定只能来自受控平台登记，不由其自授。

新增数据库能力须专用于 retained-result，受角色、Task 当前 ACL 与精确 receiver/Run 约束；P06 四类 request/settlement purpose 的现有边界不放松。Artifact provenance 仍是对应 Run 的 model_output，不假造 collector 或目标 capture。

## 所有权、迁移与最小检查

修复、测试与复核统一 SOL/xhigh。M2 原 owner 负责新增 runtime_dispatcher、retained_results、独立服务、dispatch_outbox/reconcile/worker_bridge/Node 的必要接缝，以及 ArtifactStore/ResultCommitter 的窄扩展。UoW、schema 链和迁移 README 已由主代理从尚未修改它们的 P08 SOL 移交给 M2 owner；P08 平台核心仍拥有正在写的 worker_host/P09 文件，共享接缝必须先协调，不能并发改文件或复制第二套接纳逻辑。

当前已验证迁移头为 0012。主代理分配 `vnext_0013_receiver_results` 给本修复，P08 原预留但未执行的 0013 顺延 `vnext_0014_p08_session_approval`；没有改写任何历史已执行迁移记录。

固定候选需要的检查为：通过生产 Outbox 启动原真实 child 场景、发送不明后只 query 且一个 launch；错误 Harness Profile/当前 Pod UID 的直接拒绝；普通 Worker ready→撤销→写入拒绝；撤销后 retained bytes 的首次 receiver intake 为 historical_only；正常 current 503 补交与旧回执幂等仍成立。必要共享源码稳定后串行执行真实 PG/平台 HTTP，保留准确被测字节/SHA、完整交换与进程/SQL原始记录。没有实际执行的部分继续标为未验证。
