# Cairn 安全场景特化与下一阶段开发交接

日期：2026-09-11。用途：向主开发任务交接用户确认、源码分析与继续开发要求；不是新阶段 Spec/Plan，不替代既有架构正文。

用户最新要求：“将目前的得到的结论整理，然后发送给主开发会话，然后进行下一步的开发”。此前“增强点先记住、暂不执行”是讨论阶段限制；现在进入主开发任务续接，但不把全部候选机制解释成已逐项批准。

交接时主业务为 codex/phase-1b-b23@381ae3a；有效开发工作树为 work/worktrees/phase-1c-prep，分支 codex/phase-1c-creation-prototype，HEAD 276b6a8。D3-A 已交付、用户交互评审以对应记录和主开发最新用户输入为准；本交接不伪造原型验收。接手重新核对 Git、背景索引与阶段材料。

## 用户确认与当前讨论结论

1. 平台按 Web 单点、CTF、综合渗透、攻防演练、代码审计提供默认 Goal/完成条件模板，创建任务允许自定义。沿用 ScenarioProfileVersion 和 Task 配置快照。用户不必从零编写完整任务提示；模板正文、字段和交互待下一阶段固定。
2. Worker 提示词需要按安全场景和 Bootstrap/Reason/Explore/收尾阶段特化，Fact 与成果交接需要规范。将此方向带入下一阶段，但本轮未逐项批准新 Schema、所有字段、固定角色流水线或新的调度算法。
3. 长任务不能只靠 Agent 记住初始要求；区分输出格式遗漏、执行记录遗失和攻击面漏测。Goal 完成、覆盖、执行停止、资源清理分别表达。
4. 用户认为 Reason 可能需要主动核实，并询问新增/更新 Fact；“Reason 必须只读”不是用户决定。具体补证权限、写回方式尚需设计。
5. 同 Task 的文件、脚本和阶段成果要能够共享；黑板发现及引用、完整会话、临时工作文件与正式证据分工明确。

第 1 点已补入 [评估配置契约](assessment-model.md#21-配置契约)、[背景索引](project-context.md)和 [D3-B 衔接](stages/phase-1c-creation-prototype/backend-handoff.md)。这三个文件已有本讨论任务的未提交文档补充，请保留、审查并集成；未改业务代码。

## 固定源码事实

基准 Cairn 0.2.1 / 8e7e0ea67552383851dfcabfba0c4e9c8d007878；已核对安装的 Server/Dispatcher 共 41 个 Python 文件与该提交一致，另静态核对 Pi v0.73.0。

- 黑板包含 Project、Fact、Intent、Hint、Reason 租约。Fact 只有 id/description；普通 conclude 创建新 Fact 并更新已有 Intent.to。原生没有 Fact 编辑接口或固定逐 Fact 审查 Worker。
- Bootstrap 的保留 Intent 由 Dispatcher 预建；主阶段成功输出 Fact+complete，超时/解析失败可同会话收尾，只输出阶段 Fact。没有新 Fact 时不保证转入 Reason，可能重试。
- Reason 的标准输出是 complete/intents/noop；无 open Intent 且未完成时不允许 noop。新 Fact/Hint 或 open Intent 从有到全结束等触发 Reason，没有攻击面覆盖完整性保证。
- Explore 按容量并行，新的 Fact 可以触发 Reason，不必等所有 Explore 结束。原生优先较新未认领 Intent；Worker 先过滤类型/容量/冷却，再按 priority、负载、随机平局选择，没有安全领域能力匹配。
- Pi 的原生 Reason 与收尾仍开放本地读写/命令工具；Reason 写回没有新增 Fact 分支，仅增加 data.fact 提示不会自动生效。
- 阶段提示已有 JSON、客观增量发现、长数据存文件并引用的要求；代码主要校验结构和 description 非空，不验证真实性、文件存在/归属/完成或完整交接。
- Pi 将 Cairn 阶段提示作为会话输入；压缩后用摘要与近期消息。摘要要求保留目标/约束/进度，但不保证逐字保留。JSON 事件流不保证最终业务输出符合 Cairn 契约。
- 镜像 AGENTS.md 有持续会话交接提示，但 PiDriver 关闭上下文文件自动加载，不能据文件存在宣称 Pi 已收到规则。
- 图快照不包含全部文件正文、工具输出和聊天；在途 Agent 不自动收到新发现。ProjectDetail 与 export 分次读取，没有原生事务快照版本保证。
- 原生 stop/completed 阻止派发，Dispatcher 轮询取消进程并异步清理。claim 过期或部分失败允许再次调度，不证明旧目标操作已停止；Future/checkpoint 是内存状态。

源码：[调度](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/scheduler/loop.py)、[输出契约](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/contracts.py)、[Pi 驱动](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/cairn/src/cairn/dispatcher/workers/adapters/pi.py)、[Pi 压缩](https://github.com/earendil-works/pi/blob/v0.73.0/packages/coding-agent/docs/compaction.md)。

## 纳入方案、尚未冻结的机制

| 方向 | 候选补充及边界 |
| --- | --- |
| 任务合同 | 固定 Goal/阶段/Intent/允许工具/输出要求，复用 Pi 扩展重装必要内容，不重写循环与压缩 |
| 覆盖和尝试 | 沿用 Wuji CoveragePlan/VerificationRun/ToolCall 目标模型，表达已测、未测、阻断、前提和证据；不是所有目标跑全部方法 |
| Fact 规范与复核 | 发现、方法/身份/条件、证据、限制；按需复核，纠错追加新 Fact，当前接纳结论由验证/研判版本表达 |
| Reason 补证 | 可继续委托 Explore，或受控短小补证；若后者，固定原生 Intent→conclude、执行身份、租约、预算、持久结果、快照刷新及新 ID 引用顺序 |
| 文件交接 | 关键文件记录用途/路径/状态/摘要/来源，未完成事项及受管进程/会话句柄；临时文件直接共享，正式证据再 Artifact |
| 共享环境 | AgentRun 独立会话/目录、浏览器 Context、端口与进程协调；目录不是恶意执行者强隔离 |
| 结果核对 | 原始结果与操作先持久化，再写 Core；Bootstrap/Reason/Explore 全部入口处理未知，不盲重投或重跑 |
| 费用与停滞 | LiteLLM 原生 Task 金额预算涵盖全部阶段，关闭自动付费探活，耗尽不额外请求收尾 |

不预设向量库、新调度引擎、固定角色流水线、收益评分算法或全场景一次性上线。Reason 直接覆盖旧 Fact、给 Core 加业务字段/回执/事务事件不符合当前已确认边界。复核不以第二模型同意代替证据，也不默认重复访问目标。

## 请主开发任务实际续接

用户已要求进行下一步开发，请接手后实际推进，不止回复“收到”。先读取本文件及有效设计、当前 Spec/Plan/Acceptance，处理已有未提交文档；按当前应用模式和 AGENTS 的规划/实施约定收口下一阶段具体方案，不声称自行切换模式。

依赖顺序继续为 D3-B 正式创建/授权/配置快照/ready，随后权威执行账本与调度/共享 Runtime。把默认可自定义 Goal 模板及 Worker/Fact/交接规范纳入对应方案；可独立交付的模板/合同与依赖真实执行的增强分批推进。不提供空转 start，不自动接管旧 queued，不一次开放五场景执行。

最新继续开发要求允许主任务推进后续工作，不意味着此前每项候选均已确认。常规可逆实现与已有批准范围直接推进；实质未决事项按阶段规约形成具体可审阅方案后处理。主开发根据自己的最新用户输入判断 D3-A 评审门槛，不伪造已评审事实。

保留 Cairn Core/协议不改、唯一可写图、Pi 复用、单 Task Pod 双容器、Controller 唯一 Pod 所有权、执行准入与调用账本、LiteLLM 共享金额预算、密钥和授权边界。单价按公司网关填写，缺价不发布。没有累计检查时间预算，仍仅最小必要验证、通过即停；真实模型授权额度和非破坏性限制不变，不因本交接追加付费模型或目标请求。

## 分析证据与附图

- [长任务、覆盖与交接完整复审](../../../../artifacts/cairn-dispatch-explained/cairn-memory-coverage-handoff-review.md)。
- [单画布原生调度图](../../../../artifacts/cairn-dispatch-explained/cairn-penetration-dispatch.drawio)；同目录有 SVG 和高清 PNG。目标、发现和时序是虚构示例，不是运行证据。
- 初次分析执行过 7 项纯函数探针，后续仅源码复审。未运行原生测试全集、真实 Agent/容器/模型/目标，不代替平台接入验收。
- 详细旧报告位于分析任务产物；主开发所需结论已在本文件和上述复审交接，不依赖聊天摘要代替源码与设计正文。
