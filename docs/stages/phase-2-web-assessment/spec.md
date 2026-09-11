# W1：封闭 Web 自主验证与评估 Spec

状态：**implemented / 机制验收通过，见acceptance.md**。2026-09-11，起点`b79efa6e65a0d976c43c66588630fea7eb5a22ca`。用户已在Plan模式确认并以PLEASE IMPLEMENT THIS PLAN批准W1实施，当前Default执行模式。只交付机制和合成链路，不新增真实模型费用或外部目标。最新接口细化见[实施合同](implementation-contracts.md)。

## 1. 背景与本次终点

[核心闭环验收](../phase-1c-task-creation/acceptance.md)已经通过，复用真实创建/原键恢复、start、Cairn/Pi/LiteLLM、双容器Task Pod、共享文件、Artifact及停止核对。不重新开展“先接通框架”或旧全量回归。

当前`fixture-web-v1`的确定性模型和`Core.evidence_complete()`验证HTTP标记与跨Agent文件交接，适合作为集成夹具；它不判断普通Web任务Goal。`goal_status=unknown`是正确边界，不能直接改成met。

下一阶段终点：只给自建Web站点入口、有限评估目标及必要线索，由模型自主选择观察顺序和普通Intent；平台从真实HTTP证据产生有条件的验证结果、覆盖与未完成原因，经当前停止链路结束。首批仅验证**跨源响应配置与匿名访问前提**，不称为全量Web渗透或真实数据窃取验证。已批准的五类任务、默认匿名、可编辑Goal及授权语义保持。

依据：[产品](../../../PRODUCT.md)、[架构](../../cairn-architecture-decision.md)、[评估模型](../../assessment-model.md)、[核心执行合同](../phase-1c-task-creation/execution-contracts.md)。架构分析交接是设计输入，本Spec由用户批准版及实施合同修正；架构由主代理负责。

## 2. 复用与保留边界

- Cairn Server/SQLite/Fact/Intent/Hint/complete/reopen保持原样，探索仍由原生Dispatcher决定；Wuji只处理准入、记录、评估与停止。
- Pi 0.73.0继续管理模型调用、Agent循环、会话和压缩；LiteLLM v1.100.0保持单进程、Task限定Key及USD预算。没有新SDK、计费器或压缩算法。
- 一个Task Pod、agent/kali双容器、多个独立AgentRun、一个获准attempt不变。Reason只读已有证据，主动请求交普通Intent/Explore。
- 只允许部署注册的自建Web实验站点。继续拒绝外部目标、任意Shell、任意MCP地址、代理、登录凭据输入及任意网络访问；这不是生产出口隔离验收。
- 现有fixture Profile继续使用原判据；新`closed-web-assessment-v1`是独立运行Profile。历史Task不补绑定新规则、不重算历史结果。

## 3. 自建站点与三条必要路径

站点由独立镜像提供，部署注册包含服务身份、镜像摘要、origin和内容版本；仅测试命名空间可启用。测试端保存预期答案清单，Agent镜像、Assignment、平台规则文件和模型输入均不得包含答案清单、预定Fact、producer/consumer脚本或所需工具顺序。

| 路径 | 自建站点行为 | 平台应接受的结果 |
| --- | --- | --- |
| 问题 | 一个公开资源对两个不同测试Origin均反射其值，并同时返回Access-Control-Allow-Credentials:true | 在本次资源与条件下确认“观察到宽松跨源响应配置”；证据包含两组实际交换。不能由此推导浏览器已读取真实用户数据或宣称高危漏洞 |
| 正常对照 | 对同样两个Origin不返回允许跨源凭据的组合，或只允许预定可信Origin | 仅在方法完整执行、响应/对照有效时记录not_reproduced；不能证明整个站点安全 |
| 前提不足 | 被声明需要认证的实验资源返回401/403；本任务仍为匿名身份 | authenticated维度blocked/unassessed，保留响应证据；不能伪造账号或把阻断记为未复现 |

页面只公开普通站点说明与可发现链接。模型需自行发现资源并选择方法，不要求固定Agent数量或顺序。站点不包含真实账号、商业信息或持久化破坏操作。标准方法说明可以向Agent公开；目标答案与路径到结论的映射只留验收端。

## 4. 受控HTTP工具

新增`http_request`，复用当前ToolCall/ToolAttempt、epoch、attempt、deadline、Supervisor及Artifact；旧fixture_http不改名、不改变历史合同。

- 参数：url、method（GET/HEAD/OPTIONS）、headers；不接受body、代理、TLS关闭、主机解析覆盖或任意SDK参数。
- headers仅允许Accept、Origin；名称大小写归一，拒绝CR/LF及重复冲突。Origin作为请求数据，不授予访问该Origin的网络权限。
- url必须是当前Task授权与本运行Profile注册origin的交集，禁止userinfo和fragment；URL路径只作为请求资源，不引入授权路径ACL。
- 不自动跟随重定向。记录3xx与Location；后续请求需新的ToolCall并重新鉴权，不继承前跳许可。
- 单次最多30秒、请求头合计8KiB、响应正文1MiB。达到限制保存已接收字节、截断/超时原因，不能当成完整响应或丢弃已发生的请求。
- 保留请求方法/实际URL/允许头、响应状态/头/正文、时间和工具版本。Set-Cookie等敏感头默认从模型及普通展示剔除并记录剔除标记；不建立隐式Cookie jar。
- 原始响应不自动成为提示指令；模型得到有界摘录和Artifact引用。二进制/不可解码正文保留字节引用与类型，不猜文本。
- 在Router及Kali helper两端校验。工具开始前重新检查Task许可；取消/到期仍使用已验收进程回执。接口声明能力不表示CNI已阻止所有旁路。

生产流量截获、HTTPS解密、DNS重绑定防护和外域依赖加载策略仍需后续出口方案；本阶段只围绕固定自建目的地扩展受控HTTP工具。

## 5. 最小评估合同

复用评估模型的语义，不同时实现完整资产库、Finding研判、知识平台或报告发布。

| 对象 | 本批固定内容 |
| --- | --- |
| AssessmentProfile快照 | profile_id/version/digest、允许方法/规则版本、适用维度、运行工具版本、Goal映射方式，固定在本次执行快照 |
| CoveragePlan | 不可变计划快照；资源为入口及完整入口HTML第一层<a href>发现的最多10个同源且获授权资源；不是路径授权或全站覆盖 |
| CoverageItem | target、匿名/需认证前提、方法族、状态、关联VerificationRun、具体阻断/未测原因 |
| VerificationRun | 固定主张、方法/规则版本、身份、来源AgentRun/Intent、实际ToolCall/Observation；重新验证用新ID |
| VerificationResultRevision | 追加结论unassessed/confirmed/not_reproduced/inconclusive、判据来源、证据、限制、supersedes引用；不得覆盖旧结论 |
| Observation | 由工具真实回执产生http.exchange.v1，绑定Task/AgentRun/ToolCall/attempt、采集时间、Artifact摘要及截断状态 |
| EvidenceLink | 关联Observation/Artifact与具体主张/结论，标supports/refutes/limits以及头名称或正文位置；不从Fact描述全文猜关系 |

模型通过`verification_submit`提交候选主张、rule_id、已存在tool_call_ids、限制和纠错引用。输入先不可变持久化再校验；服务器从已有回执产生结论，不采信模型提交的verdict。相同AgentRun/request_id只返回原提交，改正文409；不为修复格式自动再次请求模型或目标。归属/工具/规则无效返回明确拒绝，保留已发生的工具账本。

跨源方法至少需要同一资源、相同Task/授权/匿名身份、两个不同Origin的完整响应；比较规则是版本化可信代码，不在模型自由文本中执行表达式。完整对照未观察到主张才not_reproduced；网络失败、响应截断、401/403或其他前提缺失不构成负结果。

Verification是主张的核实，不是独立“第二个Agent”，confirmed不自动计作漏洞。当前工作台显示验证类型与条件，不新增虚构漏洞数。后续支持其他方法按独立规则版本扩充，不直接将测试答案写进通用评估器。

## 6. 结果交接、快照与Reason

`graph_read`继续读取本AgentRun的分配快照，返回snapshot_id、captured_at、digest，不改成静默latest。新增显式`graph_refresh`：通过Wuji读取原生Core，保存新的只读快照并返回同样元数据；失败保留旧快照引用及错误，不返回空图代替失败。

新增`assessment_read`读取持久覆盖/验证/未完成项的revision；`evidence_read`只读本Task已登记证据的有界片段。读取不调用模型、不访问目标。Reason可以使用这些读取工具，不获得http_request或verification_submit等新增目标/成果写权限；需要新的验证或纠错证据时生成普通Intent。

Assignment固定Goal、原生from Fact集合、合同版本、初始图与Assessment引用；每次执行读到的新快照记录在本AgentRun的访问账本中。若刷新获得不在本次允许from集合的新Fact，不让Agent把它偷偷写进原生返回；应留给下一次有新Assignment的原生调度，避免破坏固定Cairn返回校验。

Explore的原始输出仍先保存再走原生conclude；Fact.description可携带经平台校验的Verification/Artifact引用。纠错追加反证Fact和Verification结果revision，不改旧Fact。黑板同步未知只核对原操作，不能再次运行探索来补回结果。

Pi仍自行压缩；短合同只携带来源、当前阶段与限定读取入口，持久证据与评估不依赖模型摘要保存。若本批改动context扩展，则只补一个真实Pi原生压缩后的合同/工具/记录读取检查；合成摘要只能证明机制连续，不能证明真实模型长期记忆质量。

## 7. 完成提案与停止

将`evidence_complete`拆为FixtureEvidenceEvaluator和WebAssessmentEvaluator，按执行快照选择；不按任务名称或URL字符串猜Profile。Web评估不要求producer/consumer文件交接。

- CoveragePlan必需项形成有效结论时，assessment_outcome=complete；部分blocked/not_run/inconclusive则partial或inconclusive。这只说明已披露的有限计划，不代表自定义总Goal成立。
- 本批只结算有限评估项。现有广泛目标、自定义目标的goal_status均保持unknown，不新增模板和创建交互。沿用Task.assessment_outcome的complete/partial/inconclusive/not_assessed枚举，不增加criteria_met。
- Reason发出complete后，平台先登记完成提案及assessment revision。必需项可继续但未完成时返回明确评估缺口，保留原生Project active；不是Core网络失败，不立刻按agent_result_incomplete结束Task。
- 缺口通过持久Reason触发记录传回后续原生Reason，由它提出普通Intent；Wuji不自行选择下一探索方向。相同评估revision、没有新工具/观察的重复完成提案最多两次，再以no_progress部分结束；此限制为用户已确认运行策略，非开发测试时间预算。
- 明确前提不足、无可行动项、预算/期限终止时允许部分结束，Cairn保持stopped，不伪造指向goal的完成边。执行状态、Goal结论、结果同步、Key阻断与Pod清理分别记录。
- 真实执行未知仍reconciling，不重派、不冒称已停。停止路径复用当前实现，新增工具只补其受影响的取消证据。

## 8. 权限、接口与兼容

公开API仍为开发候选0.5.0。新增项目Task下有界读取：GET /assessment、/verifications、/verifications/{id}、/observations；复用会话、task.read、项目过滤、签名游标和生成校验器。result保留现有字段，新增可选assessment引用；历史记录缺少评估时返回not_assessed，不回填结果。

私有Agent入口复用现有按Run认证的tool-calls通道。读取和候选提交的工具权限在服务端注册表与Pi工具表同时约束；模型不能传tenant/project/epoch改变身份。新增记录均具备tenant/project/task复合归属，现有Artifact授权沿用本轮纯合成数据范围。完整敏感证据分级授权不在本批偷做或预先宣称已通过。

迁移20260911_0008衔接0007，只增加评估/观察/关联/访问与完成提案记录，不更改Cairn数据库。项目角色只读评估，可信执行角色负责受限写入；原用户Task命令权限、幂等键空间及旧queued禁止执行保持。

## 9. 验收分层与付费条件

用户已选择本轮只实施A层；B层保留为待明确授权的后续验收。

A层：使用合成协议上游完成工具、持久记录、判据、失败语义及三条路径的机制验证。它可以先实施和验收，但不称为自主推理效果通过。

B层：同一组站点交给真实已发布模型，自主产生Intent/工具序列；不能将预期答案或固定响应脚本注入模型。只验证问题、正常对照、前提不足三条代表路径和直接受影响的停止/权限；不要求固定Agent数。

B层执行前必须具备：明确已发布模型version_id、管理员填写的实际公司价格及容量、同版本连接检查证据、用户明确的本次USD总额度与各Task上限、可发送的纯合成数据范围。现有真实调用额度已耗尽；此草案不新增额度。缺少条件时完成可逆代码/站点准备与A层，B层标pending，而非切换其他模型或追加探活。

保留4182已交付环境及旧基线；新候选验收时按正常生命周期串行切换，保留旧库/PVC/记录。React Flow只读画布作为后续独立UI切片，不成为本阶段前置条件。
