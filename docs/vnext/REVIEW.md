# Wuji vNext REVIEW · 对上一版三份文档的复审

**版本：2.0-review；日期：2026-09-13。**

对象不是仅原上传草案，而是我上一轮给出的 `V1_SPEC.md`、`V1_PLAN.md`、`V1_REVIEW.md`，并与原稿及用户后续澄清交叉核对。原件逐字节保存在 source/。全文阅读覆盖见 [AUDIT_COVERAGE](AUDIT_COVERAGE.md)。本文件是设计审查，不是复现了产品漏洞；本轮没有测试真实 Wuji 运行状态。

## 结论与责任

上一版“Agent不能自证、不能伪造采集”的边界值得保留；“Fact只能由确定性抽取器生成”是我增加的过严实现约束。原稿本来已经允许Claim/假设并保留证据状态，不应把它描述成没有事实分层。[O1 §4；V1 Review R03]

本轮也发现状态、完成、会话、事件隐私、测试与切换的可实施性问题，不能只修改Fact一段。修订集中在能解释正向流程、失败路径和证据来源的合同，不改换MAF/React Flow/自有黑板路线，不增加一套竞争的Agent调度器。

**优先级：**P0=在相关核心功能发布前必须收口；P1=实现/联调必须明确。**分类：**内部矛盾可从原文直接对照；设计缺口/欠明确是需补合同的风险；过度约束与范围选择不是已发生的运行错误。每项状态为“文档已修订，产品验证not_run”，不宣称已修复生产代码。

## 逐项发现

<a id="REV-01"></a>
### REV-01 · 把Fact来源限制成确定性规则

**P0 / 过度约束**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L35。

**原文定位：**`| REQ-003 | Agent 不能直接写 Fact；Fact 只能由可信采集/规则抽取路径生成。 |`

**问题：**v1新增约束将作者和事实接纳混为一谈；虽然允许Claim保存，但没有把Agent提炼的候选事实作为明确正向合同。不是原稿自身已存在的错误。

**本版决定：**允许候选事实；ClaimRevision统一正文，FactLedger为有证据评估的视图；作者身份保留。

**核对落点：**Spec S03；Plan P04；验收 AC-005, AC-006。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-02"></a>
### REV-02 · 线性记录链误导为强制工作流

**P1 / 过度约束**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L114。

**原文定位：**`    O --> F[Fact / 规则抽取的有条件断言]`

**问题：**图与P16贯通路径强调逐级转换，容易要求每条记录都过Fact和Verification。

**本版决定：**改为分支关系；Observation可直接支持Claim；没有Fact也能完成合法工作。

**核对落点：**Spec S03, S08；Plan P04, P05, P17；验收 AC-034, AC-007。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-03"></a>
### REV-03 · 内容支持、使用目的与来源身份未贯通

**P0 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L159。

**原文定位：**`ClaimRevision 保留 kind（observation-summary / hypothesis / derived-conclusion）、正文、依据、作者、来源 Run 和 supersedes。评估状态 unassessed / supported / contradicted / inconclusive 独立于正文版本，由验证结果或明确人审产生。`

**问题：**v1只有基本证据状态，未充分规定linked与content_checked、候选使用和Goal接纳差别。

**本版决定：**加入四个独立轴和使用政策；保留原kind，模型复核不单独认证。

**核对落点：**Spec S03, S11；Plan P04, P12；验收 AC-010, AC-009。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-04"></a>
### REV-04 · 事实入账阻塞工具结果

**P1 / 过度约束**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L377。

**原文定位：**`Tool Router 登记 → 执行端保存启动回执 → 实际工具运行 → 可信采集端封存 Artifact/Observation → 确定性抽取 Fact → 原子公布 evidence receipt → 向 Agent 返回受限摘要及引用。`

**问题：**v1把抽取放进向Agent返回之前；缺解析器可能阻断真实证据交付。

**本版决定：**原始Capture先独立接受；抽取/评估可选有界异步处理，可信采集不能省略。

**核对落点：**Spec S08；Plan P03, P05；验收 AC-034, AC-033。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-05"></a>
### REV-05 · 失效只保存字段，未充分传播到引用者

**P1 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L153。

**原文定位：**`Fact 正文不更新。撤回、过期、冲突使用独立 FactAssessment 追加记录：effective / disputed / stale / retracted，注明依据和规则；历史报告保留当时状态。相互矛盾的 Fact 可同时存在，因为时间、环境、工具可信度可能不同。`

**问题：**没有完整交代新正文revision、环境重置、旧关系和继承状态的相互作用。

**本版决定：**评估固定ClaimRevision和环境；新版本不继承supported，反证失效关联待执行与完成决定。

**核对落点：**Spec S03, S04, S10；Plan P04, P12；验收 AC-014, AC-056。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-06"></a>
### REV-06 · WorkItem使用了未定义superseded状态

**P0 / 内部矛盾**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L509。

**原文定位：**`最终关闭还必须明确结算剩余 ready/blocked/waiting 工作：记录 cancelled/superseded 及 Task 结束原因，而不是把未执行工作改成 done。撤销具体待批操作；保留其原始请求供审计。`

**问题：**状态表不含WorkItem.superseded，但最终关闭要求写它。

**本版决定：**WorkItem统一cancelled+reason=intent_superseded；Intent自己的superseded独立。

**核对落点：**Spec S05, S11；Plan P02, P05；验收 AC-019。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-07"></a>
### REV-07 · Task关闭原因与结果混在同一枚举

**P1 / 模型歧义**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L223。

**原文定位：**`| Task.close_reason | completed / partial / inconclusive / cancelled / failed / budget_exhausted / time_limit / no_progress，未关闭为空 |`

**问题：**completed/partial/inconclusive和budget/time/user_cancel混成互斥值，难表达取消但保留部分结果。

**本版决定：**close_trigger与result_outcome分轴；UI独立展示Goal、执行、交付、费用。

**核对落点：**Spec S05, S11；Plan P05, P12；验收 AC-052。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-08"></a>
### REV-08 · Result接受可能被误当进程结束

**P0 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L486。

**原文定位：**`先认证并查相同 submission_id 的原回执 → 保存原始正文/摘要 → 对不可变引用解析与校验 → 短事务核对状态和依赖 → 接纳 Claim/Intent 提案、结算 WorkItem/Run、追加事件及回执。`

**问题：**描述接纳与结算相邻，但没给出接受早于exit时释放容量的明确守卫。

**本版决定：**result_state、process_state、workstate分开；确认退出前不done，不释放可能占用容量。

**核对落点：**Spec S05, S07；Plan P05, P10；验收 AC-020。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-09"></a>
### REV-09 · Task暂停与单工作hold的叠加缺合同

**P0 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L297。

**原文定位：**`UI 的“停止这个 Agent”默认操作是 hold WorkItem + revoke run_epoch + stop Run。不能自动重新 ready。只有显式 ResumeWork 或新的受权工作提案才能继续。Task pause/cancel 则撤销 execution_epoch，并影响全部相关 Run。`

**问题：**整Task恢复如何保留原先user_hold和wait_ref不明确。

**本版决定：**suspension_causes区分user_hold/task_pause/completion；恢复只解除自身原因。

**核对落点：**Spec S05, S09；Plan P05, P11；验收 AC-022, AC-023。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-10"></a>
### REV-10 · Intent DAG和执行依赖满足条件不充分

**P1 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L180。

**原文定位：**`| depends_on | IntentRevision → IntentRevision | 前者等待后者指定结算条件 | 是，必须无环 |`

**问题：**声明依赖无环但没有完整定义前驱failed/cancelled/done如何满足不同需求，也容易在WorkItem重复实现。

**本版决定：**唯一WorkDependency图，条件settled/accepted_result/criterion_satisfied，Task锁内并发查环。

**核对落点：**Spec S04, S06；Plan P04, P05, P09；验收 AC-015, AC-016。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-11"></a>
### REV-11 · Reason触发只看board水位会丢其他变化

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L277。

**原文定位：**`每 Task 保存 TriggerAccumulator：pending_reasons、highest_pending_board_revision、consumed_revision、inflight_work_item_id。初始化、新有效 Fact/验证、依赖结算、有效 Hint、完成反馈和明确阻断解除可以触发；Token、心跳、布局、工具轮询不触发。`

**问题：**依赖、控制和人工事件可能没有board增长；仅board水位不能覆盖所有触发。

**本版决定：**独立trigger_generation，领取/消费水位分开，失败有界，自身Intent不自激。

**核对落点：**Spec S06；Plan P09；验收 AC-026, AC-027。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-12"></a>
### REV-12 · wait登记没有防丢唤醒协议

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L281。

**原文定位：**`ReasonResult 是判别联合：propose_intents / wait / propose_completion / blocked。wait 必须携带已登记 dependency/question/event；没有这些条件的“再等一会儿”拒绝为 INVALID_WAIT。blocked 要有 reason_code、解除动作和责任人。`

**问题：**仅引用一个事件不处理事件在waiter登记前已发生。

**本版决定：**事务登记+检查谓词，事件到达原子标ready，重启补偿扫描。

**核对落点：**Spec S06；Plan P09；验收 AC-028。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-13"></a>
### REV-13 · 精确去重、语义相似和进展不能互替

**P1 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L285。

**原文定位：**`ExactExecutionKey 由规范化工作目标、方法族与版本、身份条件、相关依据版本、预期输出组成；不能仅用自然语言标题，也不能仅用参数 hash 猜测某外部操作已经执行。文本相似只提示合并。`

**问题：**v1原则有价值，但Plan容易把语义去重/进展算作现成算法；缺不同问题同参数和等价问题换标题的反例。

**本版决定：**限定确定性key，语义相似只提示；hard limits独立；增加双向反例和公平性容量测试。

**核对落点：**Spec S06；Plan P09；验收 AC-029, AC-024。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-14"></a>
### REV-14 · prepared到spawn的崩溃窗口未验

**P0 / 设计缺口**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L414。

**原文定位：**`- [ ] **3. 实现最小功能。** 启动回执先持久化再启动进程；同operation/query复用，不重新spawn。撤销/hold先落控制状态，再发停止信号；单工作hold不影响其他Run。环境UID/代次不一致拒绝。`

**问题：**v1主要测响应丢失，无法证明回执与spawn之间无重复；持久化不能让进程spawn与DB原子。

**本版决定：**四窗口故障矩阵；不明则reconciling，查询同operation，不能自动spawn。

**核对落点：**Spec S07；Plan P10；验收 AC-030, AC-031。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-15"></a>
### REV-15 · 单活动Scheduler不等于重启没有旧执行者

**P1 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L104。

**原文定位：**`部署可复用镜像，调度入口必须独立于 HTTP 请求生命周期。首版一个活动 Scheduler；数据库约束不因单实例而取消。LISTEN/NOTIFY 或其他唤醒仅为优化，持久扫描负责补偿。`

**问题：**单实例声明未定义重启/分区时旧实例仍投递的责任，容量仅有效写者也可能漏旧进程。

**本版决定：**leader_epoch、Inbox与执行端检查；unknown仍占可能在运行容量；不声称零残余窗口。

**核对落点：**Spec S02, S05, S07；Plan P09, P10；验收 AC-032, AC-024。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-16"></a>
### REV-16 · 会话manifest遗漏记忆的确定版本

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L347。

**原文定位：**`持久化流程：写不可变状态/历史对象 → 校验完整性 → 短事务 CAS 发布 manifest 和消息终点 → 才允许下一项需持久保障的动作。历史单独存储时 manifest 固定终点；不能用“最后一个文件名”拼出未提交状态。文件记忆也需要受控写入及版本关联。`

**问题：**文字提到关联，但manifest字段未要求memory根，恢复可混旧历史与新笔记。

**本版决定：**memory_manifest_ref必填或显式空根；CAS绑定完整history/state/memory。

**核对落点：**Spec S09；Plan P08；验收 AC-038, AC-066。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-17"></a>
### REV-17 · 核心审批能力可被Profile关闭绕过

**P0 / 发布歧义**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L337。

**原文定位：**`不以源码 HEAD 的版本号当 wheel 兼容证明。若某个持久化边界或审批续接不能通过公开 API 实现，发布该 Profile 前选择：仅支持已结算工作段恢复，或停止发布并提交明确差异；不能静默改用 Pi/Cairn，也不能直接修改 MAF 私有实现。`

**问题：**v1对必要审批恢复和可选细粒度checkpoint降级没有区分；可能全部关闭后宣称重构完成。

**本版决定：**核心审批跨进程为必要Gate；只有运行中自由注入/细粒度恢复可选关闭。

**核对落点：**Spec S01, S09, S17；Plan P01, P08, P11；验收 AC-040, AC-043。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-18"></a>
### REV-18 · 审批消费与ToolOperation创建非原子

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L361。

**原文定位：**`ApprovalRequest 绑定 task/work/session、checkpoint、原 call_id、参数摘要、tool/profile/scope version、请求 Run、审批人资格和 expires_at。批准与消费分开去重；批准后再准入。恢复由新 Run 显式继承原操作，不给未知旧 ToolCall 新建执行 ID。[E3]`

**问题：**批准和消费分别去重仍有消费后未派发的崩溃窗。

**本版决定：**当前准入与批准绑定唯一ToolOperation/Outbox同事务；重复恢复原操作。

**核对落点：**Spec S09；Plan P08, P11；验收 AC-041。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-19"></a>
### REV-19 · 工具与模型unknown一概阻断会伤可用性

**P1 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L498。

**原文定位：**`    Q --> R[结算所有已登记Run/Tool/Model/结果]`

**问题：**不同unknown状态可能影响不同资源；费用晚到不等于仍有副作用。

**本版决定：**分本地进程/副作用/响应/费用轴，相关失败域冻结；费用pending可本地关闭。

**核对落点：**Spec S06, S08, S11；Plan P06, P11, P12；验收 AC-046, AC-044。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-20"></a>
### REV-20 · quiescing冻结动作却期待必要工作继续

**P0 / 内部矛盾**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L505。

**原文定位：**`CompletionReview 检查必须排除“已经结算的发起 Reason”本身，不能等待自己的未结算记录造成死锁。quiescing 后不发新模型/工具许可；已持久操作允许补交结果。新反证到达使旧完成依据失效，最终关闭前重读 board/assessment/goal/policy 版本并在 Task 锁内再次检查。`

**问题：**必要工作可能仍需下一次调用才能退出成功；若不规定stop边界，收敛可能死锁。

**本版决定：**先precheck必要工作，未完不冻结；真正quiescing只结算既有操作并有界停止。

**核对落点：**Spec S11；Plan P11, P12；验收 AC-048, AC-049。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-21"></a>
### REV-21 · abort-close和迟到反证缺用户可见后果

**P1 / 欠明确**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L500。

**原文定位：**`    C -->|仍有缺口且可继续| OPEN[记录反馈后重新running]`

**问题：**重新running未说明恢复哪些工作；closed历史反证只存historical_only会让旧报告继续误导。

**本版决定：**CompletionEpoch撤销仅解除自己暂挂；报告追加争议/补充，不改正文、不自动重跑。

**核对落点：**Spec S10, S11；Plan P12, P16；验收 AC-050, AC-053。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-22"></a>
### REV-22 · 短RR读不足以支撑多请求历史

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L580。

**原文定位：**`子图查询和分页固定 snapshot_id；不在第二页切换 latest。快照过期返回 410；无法保留增量时返回 resync_required。初始节点/边上限防止巨图卡死，展开必须受权。内容补取时固定记录 revision；不能让旧 patch 混入新正文。`

**问题：**要求固定snapshot_id但没完整定义状态/关系快照如何持久化，可能第二页或历史混latest。

**本版决定：**持久SnapshotManifest固定状态和引用；首版历史限真实保存快照，缺失明确报错。

**核对落点：**Spec S04, S12；Plan P03, P13；验收 AC-054, AC-063。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-23"></a>
### REV-23 · 禁止隐藏计数泄漏却发送全局空事件水位

**P0 / 内部矛盾**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L578。

**原文定位：**`前端只接受连续且更高版本的批；重复批丢弃，过期批不回退状态；缺口/游标过期/access_scope_digest 改变则 resync。服务端若过滤事件，返回不含敏感内容的水位批，不要求客户端通过猜缺失序号读取隐藏数据。SSE 断开只影响观察，worker 继续按持久控制状态工作。`

**问题：**内部seq和空批本身暴露隐藏变更次数，与禁止隐藏计数不一致。

**本版决定：**独立受权ViewStream版本，不透明cursor，固定keepalive；内部序号不发受限用户。

**核对落点：**Spec S12；Plan P13, P15；验收 AC-060。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-24"></a>
### REV-24 · 视图切换和节点revision身份未定义完整

**P1 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L542。

**原文定位：**`NodeDTO 包含稳定 node_id、KnowledgeRef、kind、标题与脱敏摘要、执行/证据状态、render_version、allowed_actions。node_id 由实体身份确定，不能用数组下标或随机渲染 ID。`

**问题：**同实体多revision和Fact/Claim展示切换未消歧；SSE未明确不同查询流隔离。

**本版决定：**node_id固定entity:id@revision，display_kind不改ID；view/query/access分别绑定。

**核对落点：**Spec S12；Plan P13, P14, P15；验收 AC-055, AC-061, AC-056。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-25"></a>
### REV-25 · 派生摘要与撤回能力容易过度承诺

**P0 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L544。

**原文定位：**`EdgeDTO 包含稳定 edge_id、source/target node_id、edge_type、关系 revision、脱敏理由。隐藏任一端点就不返回该边；不得泄露隐藏节点的名字、数量、布局位置或关系解释。`

**问题：**仅隐藏节点/边不足以保护由受限证据形成的摘要；已送出数据不能回收。

**本版决定：**派生默认继承严格权限；审核脱敏另存；当前鉴权/有界下载TTL，明确残余披露边界。

**核对落点：**Spec S14；Plan P13, P16；验收 AC-059, AC-067。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-26"></a>
### REV-26 · 永久引用保护与合法保留删除缺处理

**P1 / 设计缺口**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L770。

**原文定位：**`7. 原始staged对象尚未封存不参与事实生成/报告；manifest发布后引用对象不被垃圾回收。外部存储失败时保留pending，不伪装完整成功。`

**问题：**普通GC保护与授权purge不是一回事；v1未交代删除后证据和报告如何显示。

**本版决定：**正常GC保引用/提交租约；显式purge留tombstone与报告不可用提示。

**核对落点：**Spec S09, S14；Plan P03, P08, P16；验收 AC-066, AC-067。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-27"></a>
### REV-27 · Result示例与附录类型不一致、身份边界不明

**P1 / 内部不一致**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L738。

**原文定位：**`ResultSubmission 包含 schema_version、submission_id、raw_response_ref/digest、snapshot_id、read_refs、outcome、claims、intent_proposals、reason_decision、limitations。归属从认证上下文派生；Agent自行填写的身份不改变归属。`

**问题：**正文示例缺附录必需原文ref/read_refs等；submission元数据似由模型填写；input_required和failed语义混执行。

**本版决定：**可信ResultEnvelope与AgentPayload分离；原生审批/执行状态不能靠模型字段决定；统一examples/schema。

**核对落点：**Spec S10, S13；Plan P02, P04, P08；验收 AC-075, AC-009。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-28"></a>
### REV-28 · 错误说明与回执状态混用

**P1 / 内部不一致**；来源 [`V1_SPEC.md`](source/V1_SPEC.md) L455。

**原文定位：**`内部可信采集入口的身份禁止用 FORBIDDEN_COLLECTOR（HTTP 403）；成功回执 code 可用 ADMITTED、ACCEPTED、ACCEPTED_AS_OPINION，业务状态仍以 data 中的固定枚举为准。`

**问题：**句子有明显歧义；EvidenceReceipt把sealed混进接纳状态；正文与附录值不一致。

**本版决定：**明确403/FORBIDDEN_COLLECTOR；Artifact封存和Receipt接纳独立；contracts.json统一枚举。

**核对落点：**Spec S13；Plan P02, P03；验收 AC-019, AC-008。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-29"></a>
### REV-29 · Plan验收条件依赖尚未完成后续任务

**P0 / 计划不可验证**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L355。

**原文定位：**`**退出条件：** A17,A18,A19,A20,A21 的相关机制有实际测试证据；任何未通过的权限、去重、恢复或持久化条件阻断下游发布，不由文档豁免。`

**问题：**P06把端到端审批/Session列出口但持久化在P10；P08还缺P06依赖，局部/最终Gate混同。

**本版决定：**重排P00–P20；P01探针、P08持久化、P11控制联调、P17完整Gate分别标证据。

**核对落点：**Spec S17；Plan P01, P08, P10, P11, P17；验收 AC-040, AC-075。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-30"></a>
### REV-30 · 测试夹具可能代演被测产品

**P0 / 测试薄弱**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L338。

**原文定位：**`    assert result.sdk_was_real is True`

**问题：**world/maf_probe抽象和布尔标志容易空通过；缺真实正向候选路径，只有拒绝伪造。

**本版决定：**实际ASGI/PG/子进程/协议捕获；对应AC定义可见结果和反例，不以布尔自报作为验收。

**核对落点：**Spec S17；Plan P02, P04, P07, P17；验收 AC-005, AC-003, AC-075。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-31"></a>
### REV-31 · 计划路径、接口和最终命令有遗漏

**P1 / 计划不完整**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L110, L694。

**原文定位：**`| import_archive | ArchiveImporter.import，不创建执行WorkItem |`

**问题：**import是Python关键字；最终命令漏Node Supervisor测试；v2合同生成命令未明确，根旧testpaths可能漏新增。

**本版决定：**改import_archive；显式v2生成与全套收集、Node/正式web/browser、依赖清单检查。

**核对落点：**Spec S13, S17；Plan P02, P19, P20；验收 AC-075, AC-073。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-32"></a>
### REV-32 · 新开发提前改旧Supervisor与隔离切换相冲突

**P0 / 迁移矛盾**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L392。

**原文定位：**`**文件：** 修改 services/task-workers/supervisor.mjs 以只启动受控Python入口；新增 wuji_core/scheduling/dispatch_outbox.py、wuji_maf_worker/entrypoint.py、tests/vnext/test_dispatch_recovery.py、tests/task-workers/maf-supervisor.test.mjs。`

**问题：**v1说最后才退出旧引擎，但中期任务直接移除旧Supervisor启动分支；测试与生产迁移边界不清。

**本版决定：**新Supervisor/迁移在独立位置先验证；P19只dry-run；P20独立批准再切换。

**核对落点：**Spec S16；Plan P00, P10, P19, P20；验收 AC-072, AC-074。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-33"></a>
### REV-33 · 架构效果没有公平验证任务

**P1 / 范围缺口**；来源 [`V1_PLAN.md`](source/V1_PLAN.md) L790。

**原文定位：**`effectiveness_real_model：明确模型/数据/费用授权后的独立效果实验，本计划默认不执行。`

**问题：**v1仅说真实效果另需授权，但没有同预算单Harness对照的可执行测量工作。

**本版决定：**P18交付评测工具和独立评分协议；真实收费不自动运行；机制结果不冒充任务能力。

**核对落点：**Spec S15；Plan P18；验收 AC-070, AC-071。

**状态：**文档修订；产品验证 `not_run`。

<a id="REV-34"></a>
### REV-34 · 上一轮Review把自身设计偏好写成草案必改缺陷

**P0 / 审查方法问题**；来源 [`V1_REVIEW.md`](source/V1_REVIEW.md) L29。

**原文定位：**`| R03 | P0 | §4 L92–106 | 已把 Observation 与 Claim 分开，但未定义用户要求的“真实 Fact”写入路径。 | 保留原名并新增 Fact：由可信采集服务按规则从不可变调用证据抽取的有条件断言；Agent 只提交 Claim/IntentProposal。 |`

**问题：**原稿已区分Observation与Claim；我新增确定性Fact层，却以“缺真实Fact”为P0表述并未充分做正向场景检验。

**本版决定：**复审明确三类来源和v1自身责任；保留原稿思想，逐条列v1位置与修改，不将文档计数自检称为语义正确。

**核对落点：**Spec S01, S18；Plan P00, P20；验收 AC-001, AC-075。

**状态：**文档修订；产品验证 `not_run`。

## 不应推翻的原设计

保留自有黑板/调度、MAF底座、可信采集、候选解释与业务结论分开、不可变原始内容、稳定回执身份、未知先核对、无Cairn终态、画布只是投影、计费/观测分开、核心能力与实际效果分开。新版本不是因用户指出Fact就改成“模型说什么都直接当真”。

## 上一轮R01–R20处置

| 旧项 | 本轮处置 |
|---|---|
| R01 / R02 | 保留退出Cairn与React Flow目标，补独立开发/切换和完整视图合同 |
| R03 | 替代：确定性Fact独立写模型改为Agent候选+证据评估+单正文视图 |
| R04 | 保留真实采集不等于真命题；增加内容/来源/适用性/作者四轴 |
| R05 | 保留RR稳定读，补持久manifest和外部独立视图水位 |
| R06 | 替代不完整冻结流程，加入precheck、有限结算、abort-close与真实退出守卫 |
| R07 / R15 | 保留公开SDK能力门，补memory版本和核心审批不可豁免 |
| R08 / R11 | 保留hold与fencing，补叠加暂停、真实spawn窗及unknown容量 |
| R09 / R16 | 替代全局空事件水位；补查询流隔离和派生摘要权限 |
| R10 | 保留key/进展分离，补反例、公平对照和generation/waiter协议 |
| R12 / R17 | 统一枚举、依赖、Envelope和API，去掉未定义WorkItem状态 |
| R13 / R14 | 保留薄准入与版本核验，补不同unknown失败域与实际包探针证据 |
| R18 / R19 | 保留来源限制与媒介适用性；不把五场景标签当已交付能力 |
| R20 | 重新编写AC与任务映射；旧计数自检不视为正确性证明 |

## 本轮未证明的事项

未安装运行MAF/React Flow/Wuji，未跑PostgreSQL并发、真实Supervisor停止、浏览器图交互、LiteLLM费用、CTF或靶场效果；未获本地仓库/生产部署的本轮更新。外部文档核对仅证明框架公开描述，不证明项目实现。文档结构检查、JSON/schema和静态例子检查的实际结果见 VALIDATION_REPORT。
