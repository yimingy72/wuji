# D3-B → 执行账本与安全场景调度衔接提案

状态：**历史提案**。2026-09-11后续更新：其中运行/调度基础、单Task双容器、Reason只读/Explore补证已被核心计划批准实施；以[核心验收](acceptance.md)为准。未实现的验证/覆盖增强转入[W1草案](../phase-2-web-assessment/spec.md)。以下“未授权/建议”保留当时语境，不覆盖后续明确决定。

原来源：来源为[架构分析交接](../../cairn-security-specialization-handoff.md)、[Harness](../../agent-harness-decision.md)、[黑板](../../cairn-blackboard-design.md)与[评估模型](../../assessment-model.md)。Cairn 固定 0.2.1 / 8e7e0ea，Pi 固定 0.73.0；这里提出接入合同，不修改或声称原生已支持新增能力。

## 1. 保持的架构与本次新增职责

Task 统筹业务；每 Task 一个 Pod，agent 内动态多个 AgentRun，kali 提供共享工具与文件。Controller 独占整个 Pod，Dispatcher 后端仅启动/停止 agent 内进程；同一 runtime_attempt 供所有 AgentRun 使用。Cairn Server/SQLite/Fact/Intent/Hint/complete/reopen 全部保持原样。

Pi 继续负责循环、模型客户端、会话和压缩；LiteLLM 继续负责模型接入与 Task 金额计量。新增工作限于可信任务合同装配、调用账本、受限工具、持久结果及证据/文件关联，不增加模型 SDK、压缩算法、第二个探索调度器或可写 Fact 副本。

下面采用的结构是 Wuji 内部输入/结果信封，不向 Cairn Core 添加字段，不要求页面手填这些内容。未确定的扩展 hook 需读取固定版本 Pi SDK 再冻结，不能只写“每轮注入”就声称可用。

## 2. 调度前置：真实执行身份和合同

Dispatcher 原生阶段/worker 选择之后，平台按当前 Task 许可登记 AgentRun，才能启动进程。Assignment 由可信控制服务生成：
- task、原生 project/intent（适用时）、phase、worker_profile、agent_run/session、execution_epoch、runtime_attempt；
- CreationConfigSnapshot 与 ExecutionConfigSnapshot 引用，以及当前有效 Scope；
- 用户实际 Goal/完成条件、起始条件、阶段目标和本次 Intent；
- 精确工具白名单、当前预算/期限限制、受限图快照引用及其采集时间/摘要；
- 对应阶段输出 Schema/提示模板版本、工作目录及已知持久交接引用。

真实归属不从模型 JSON 中相信或覆盖。graph snapshot 是本次采集的输入，不是原生事务版本，不包含所有会话/文件；在途 Agent 必须显式刷新或接收平台安排的更新才能看到新增发现。刷新失败保留可知的旧采集版本，不把缺图当空图继续。

初始提示和每次新阶段/恢复都从持久合同装配；压缩后复用 Pi 支持的扩展机制重新提供短合同或限定读取入口。Scope/epoch/工具权限始终在服务端检查，不能依赖压缩摘要记住。完整模型历史仍由 Pi 维护，不定期用另一个模型重建状态。

## 3. 阶段提示与工具配置

同一场景模板组合不同阶段提示；不固定 Planner→Explorer→Verifier 流水线，不假定原生 worker priority 就是安全能力匹配。

| 阶段 | 特化输入与职责 | 返回处理 |
| --- | --- | --- |
| Bootstrap | 起点、Goal、允许工具、已知对象与现有成果；完成可用能力内的初始观察，明确空缺 | 保持原生 Fact/complete 合同，结果先持久化，再对预建 Intent 按原生方式提交 |
| Reason | 最新图采集、已知覆盖与尝试、阻断、预算；提出必要且非重复的探索，明确完成提案依据 | 保持 complete/intents/noop；不把自创 data.fact 当原生已支持分支 |
| Explore | 具体 Intent、输入 Fact、可用文件/证据、范围和方法前提；交付有条件和限制的增量结果 | 原生 conclude 追加 Fact，附平台保存的交接引用；运行完成与结论被接纳分开 |
| 收尾 | 本次运行的实际持久结果、未完成工作、仍活跃的受管句柄；优先保存已有成果 | 遵循各阶段原生收尾合同；无预算不再调用模型，不能靠收尾猜测或重跑目标 |

所有阶段关闭默认平台本地文件/Shell/自动插件发现；需要的 Kali 能力经受控工具接口开放。Reason 并非被用户要求“永远只读”，其权限按下节提案收口；不得借原生 Pi 有 bash 就开放平台主机执行。

## 4. Reason 补证的具体建议

**首批建议采用 Reason 提出普通补证 Intent，由 Explore 执行。** Reason 可以读取当前 Task 已存证据/文件/覆盖数据进行核对；确需新增主动操作时交给原生 Intent→Explore→conclude。这样能同时复用现有调度和原生 Fact 写入路径，不增加 Reason 私有 Fact 返回协议。

这是一项本次设计建议，不是用户已要求 Reason 只读，也不否认将来可受控补证。若决定首批就支持 Reason 内直接补证，必须在实施前把以下整条路径纳入同一 Spec，不能仅加提示词：
1. 平台登记补证操作与专用执行身份，申请/核对原生 Intent，未知创建不能盲重投。
2. 持有效 epoch/attempt 的调用许可，通过同一工具账本和 Task 预算执行。
3. 保存原始结果，按已知 Intent conclude 追加 Fact；未知返回读取原生结果核对。
4. 取得真实新 Fact ID 后刷新本次 Reason 输入，再允许提案引用；没有 ID 不能猜编号。
5. 约束 Reason 租约持有、耗时/工具轮数；长操作交回普通 Explore。
6. 禁止覆盖已有 Fact，不让原生 claim 超时导致同一补证重跑。

当前不实现第二条路径，不新增 Reason 隐式目标请求。是否需要它不阻塞 D3-B 创建与快照开发。

## 5. 原始结果、Fact 与成果合同

AgentRun 的原始提交先以不可变版本保存。信封至少表达：

| 内容 | 记录方式与来源 |
| --- | --- |
| 原生业务输出 | 保留 accepted/data 及阶段合法动作，不修改 Core 协议 |
| 发现 | 主张/观察、方法与前提、身份引用、支持或反驳的证据、限制 |
| 实际尝试 | 已有 ToolCall/ToolAttempt/VerificationRun 引用；控制服务核对归属和实际状态，不能仅凭模型列出的 ID |
| 未完成 | 未测/阻断/未知，原因与可能的下一步；不得把未测记为未复现 |
| 工作文件 | 路径、用途、状态、大小/摘要（可用时）、producer、相关尝试；元数据由 Supervisor 核实 |
| 活动资源 | 受管进程/浏览器 Context/端口等句柄与已知状态，不用可任意执行的文本恢复命令代替 |
| 纠错关联 | 引用原 Fact，追加反证/限制与来源；旧 Fact 和历史报告保留 |

Phase/Scenario 提示使用这些规范，严格结构和归属校验由 Wuji 完成。Core 的 Fact.description 保存可读增量发现及受限引用，不嵌入密钥。平台结果记录仅追加/核对，不提供第二个 Fact 编辑界面。

校验分层：格式合法 → 归属/版本/许可 → 证据/产物存在与状态 → 结论规则。HTTP 成功码、工具退出 0、第二模型同意或 JSON 合法都不能单独证明漏洞成立。证据不全时标为 inconclusive/待补充，保留已发生的工具记录；不为补格式自动重跑模型或工具。

没有发现也要交接实际尝试与缺口；是否追加某个原生 Fact 服从对应阶段合同，不能合成虚构发现来促使 Reason 运行。格式不合法保留 raw result + validation errors；修正已保存结构只在明确可确定的转换内进行，其余需有界、受预算的显式处理。

## 6. 共享 Kali 文件与进程

沿用 /workspace/inputs、/workspace/agents/<agent_run_id>、/workspace/shared。普通临时文件直接共享，不强制每个中间文件上传对象存储。

作为关键交接发布的文件：
- 写入中、可读取、缺失/失效分别显示；由受管文件接口核验路径/归属/实际状态，不能只相信模型说已保存。
- 使用临时文件完成写入后原子发布或新版本路径；已引用内容改变时摘要不符，接手者不能静默使用不同正文。
- “存在、可读、摘要匹配”只证明文件状态，不证明内容结论真实；正式证据另登记 Artifact。
- 目录不是同容器恶意执行者强隔离。共享覆盖、端口和会话的冲突由 Supervisor 协调，不让两个 Agent 用同一配置名充当同一执行身份。
- 任务终态/重建可使临时文件引用失效；标缺失，不能拿新 attempt 的同名文件假充旧成果。
- 凭据通过受限 credential_ref 和工具注入共享，不广播正文；旧会话/凭据不自动授权新目标。

工具开始和结束均及时写账本，不能等到模型最后返回 Fact 才知道是否执行。后台进程存受管句柄，Harness 退出不能直接将其标已停。

## 7. 覆盖与完成

沿用 CoveragePlan/VerificationRun 目标模型，避免新增一个“安全任务图”。首批把实际调用和结果登记完整，再基于已有对象生成有版本的适用检查项；不把一份通用清单当作每个目标必须执行全部方法。

Reason 读取平台只读覆盖/尝试摘要并继续选择方向；Coverage 是评估记录，不决定黑板下一 Intent，也不作为新授权。blocked/not_run/inconclusive/excluded 分别记录；必须有依据才能 evaluated。平台先接受结果再异步核对图提交，图不可用只同步结果、不重新探索。

Cairn complete 保持原生探索完成语义；Wuji 独立记录 Goal 达成依据、覆盖限制、执行停止和清理。预算耗尽可部分结束，不为补“漂亮总结”额外付费；已保存证据的整理用确定性处理。完整覆盖率/报告不在 D3-B 页面放出占位数值。

## 8. 开发依赖与验证入口要求

1. **D3-B**：持久实际 Goal/完成条件、模板和创建快照；本文件只作为后续边界，不执行调度。
2. **D4 执行控制**：Task execution_epoch、AgentRun、ToolCall/attempt、停止核对与权威 PermitSource/ControlSource；将现有桥接和 Runtime 基础库接上真实存储。
3. **调度合成闭环**：Cairn 绑定消费者、原生阶段接入、Pi 显式工具表/合同/持久结果、一个 Task Pod 两容器及共享成果。先用确定性合成上游与工具验证，不追加真实付费模型调用。
4. **任务金额与真实工具**：LiteLLM Task 限定凭据/统一预算必须在任何实际模型请求前就绪；出口/停止必须在任何真实目标请求前通过。可以并入上一步的具体批次，但不能后置到真实执行之后。

第 2—4 步仍需独立具体 Spec/Plan，固定 Schema、消费者、锁顺序、版本和单一最小入口；本文件不是自动授权。首批只验证未启动拒绝、独立 AgentRun 共用一个 attempt、结果同步不重探索、工具越权拒绝、取消后迟到派发拒绝、旧 queued 不执行，以及一条工作文件交接。长压缩/故障/压力矩阵留后续，静态提示审查不冒称 Harness 验收。
