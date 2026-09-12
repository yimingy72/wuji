# v1 → v2 改动记录

本文件说明本次显式设计变更；不把改动倒写为原稿已经要求的内容。

## 保持不变

MAF 负责单项 Agent 执行，Wuji 负责全局状态与调度；React Flow 是画布而不是数据库；保留真实证据与独立授权；新系统不运行 Cairn/Pi；旧记录离线归档，不自动重新执行。真实模型/场景效果与机制验收分开。

## 主要变化

| 主题 | v1 的问题或含糊处 | v2 的明确选择 | 实施影响 |
|---|---|---|---|
| Fact | 确定性抽取器被当作唯一内容来源 | Agent 可提候选；统一 ClaimRevision，Fact 为评估读视图 | 不建立第二份 Fact 正文；改 DTO/评估/投影/测试 |
| 探索 | 知识链容易被做成逐级强制流水线 | Observation 可直接支持 Claim；假设可驱动受控工作 | 不因缺 FactExtractor 阻断证据或共享 |
| 证据等级 | 来源、引用和结论支持易混淆 | grounding/evidence/applicability/producer 分开 | 无依据、模型复核、冲突与人审均保留身份 |
| 评估冲突 | 单一状态不足以表达多个支持与反证 | 按版本化政策聚合，不能最后写入者自动胜出 | 反证失效与历史保存要做真实测试 |
| 状态 | 使用未定义的 WorkItem.superseded | Intent 可 superseded；WorkItem cancelled+reason | 生成统一枚举并测试所有转移 |
| 工作完成 | 接纳结果与停止执行未贯通 | accepted result ≠ exited process ≠ settled operation | 不提前释放容量、资源或宣布 done |
| 暂停 | Task resume 可能复活单项 user hold | 暂停原因叠加，分别解除；保留未答 wait_ref | 控制服务与 UI 动作合同同步修改 |
| 触发 | board_revision 覆盖不了依赖/输入变化 | 独立 trigger_generation；原子 waiter | 防丢唤醒、Reason 自触发与事件重放 |
| 派发 | prepared→spawn 窗口易被称作幂等完成 | 状态 unknown 时核对，不能再次 spawn | Inbox/outbox 与真实进程故障注入 |
| Session | 只固定 history/state，记忆可能读到 latest | manifest 同时固定 memory 与 pending operation | 测试半提交、跨进程审批与单写者 |
| 审批 | 批准消费和实际操作可能分开提交 | 批准绑定唯一 ToolOperation 同事务 | 重启/网络丢响应不会生成第二操作 |
| 完成 | 冻结新动作却等必要工作继续 | precheck 先判必要工作，再有界 quiescing | abort-close 只解除自身暂停原因 |
| 迟到证据 | 历史收录但未说明结论争议提示 | 冻结 ReportCommit，追加 amendment | 不覆写旧报告、不自动重启 Task |
| 图同步 | 全局序号与隐藏记录隐私冲突 | 外部 ViewStream 单独版本、不透明 cursor | 修改快照/SSE/查询切换与重连协议 |
| 历史 | 短事务被误当跨请求或任意时点快照 | 持久 SnapshotManifest；仅回放真实保存点 | 不提供无证据的“时间旅行” |
| 节点身份 | revision 节点与个人布局容易错绑 | 逻辑 LayoutAnchor 与具体 revision 分开 | Fact/Claim切换不换节点，旧边不迁新版本 |
| API | 所有写都要求总版本会误拒并行追加 | 状态命令CAS；追加按固定引用/读集合核对 | 追加与控制不能共享一个粗糙版本检查 |
| 测试 | 自报 capability 布尔值、空工具表也能通过 | 实际函数/请求计数、持久状态、正反例 | 三类测试分开：结构、机制、效果 |
| 迁移 | 过早修改旧 Supervisor | 新实现独立；dry-run与实际切换分开 | 开发阶段不破坏仍在运行的旧链路 |
| REVIEW | 把我增加的偏好归咎原稿缺失 | 分类为矛盾/缺口/过度约束，保留原文定位 | 不再用“20项都修完”代替产品验证 |

## 明确的破坏性合同变更

`entity_type=fact` 不再是新系统独立可写断言类型，规范引用使用 ClaimRevision，旧记录导入有映射。外部 event_seq 改为 ViewStream；WorkItem/Task 的状态轴、ResultEnvelope、SessionManifest 与验收编号改变。不得把本版当作兼容补丁直接覆盖已有实现。P00 先确认用户本地是否已有 v1 代码/数据。

## 本次刻意没有增加的内容

不新增通用推理数据库、强制 Verifier Agent、无限子 Agent、自研模型循环、多活动 Scheduler、任意策略代码上传或自动生产部署。五类场景目标继续保留；不通过放宽权限来补效果。
