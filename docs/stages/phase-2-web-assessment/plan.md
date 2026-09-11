# W1 实施 Plan

状态：**approved / in-progress**；起点b79efa6。用户已批准实施。新工作树codex/phase-2-web-assessment从b79efa6建立，旧交付检出保留；合成链路前不切换4182。精确数据/工具合同见implementation-contracts.md。

## 1. 已复核来源与框架能力

- accepted基线：[核心验收](../phase-1c-task-creation/acceptance.md)、实际services/execution-control、cairn-dispatcher、task-workers与core-fixtures源码。
- 产品与领域：[评估模型](../../assessment-model.md)、[Task/Cairn架构](../../cairn-architecture-decision.md)、[Harness边界](../../agent-harness-decision.md)。分析任务的后续指导与React Flow核对是输入，不是已批准接口。
- 固定Cairn原生`tasks/reason.py`会把complete的409当failed；当前Core.finish_run据此停止Task。不能仅把完成判断替换为更严格的bool；必须同时改Dispatcher适配中的业务缺口反馈路径。
- 当前Cairn按初始allowed_fact_ids校验Reason返回；显式刷新不能凭空扩大本轮允许引用集合。
- 当前Pi扩展graph_read直接返回assignment固定快照；context hook只追加短引用。沿用现成机制，不自写循环/压缩或新模型客户端。
- 当前`poll_call`已登记Artifact后才生成展示摘录，可复用；`fixture_http`超过上限丢弃部分观察，新增http_request需要单独保存截断回执，不能改写旧夹具历史。

## 2. 依赖顺序与交付

| 批次 | 主体和文件范围 | 交付 / 后续依赖 |
| --- | --- | --- |
| W1-1 合同与评估核心 | 主代理：apps/api DTO、迁移0008、packages/contracts；services/execution-control/assessment/ | 版本化规则、覆盖/验证/观察读写及完成评估接口；先提交公共合同 |
| W1-2 自建站点与HTTP工具 | 可选gpt-6-astra/low：services/web-assessment-lab、task-workers/helper/扩展、控制服务tool handlers | 固定站点、工具请求/部分响应/证据；答案只在tests，接入W1-1记录 |
| W1-3 调度反馈与上下文 | 主代理：cairn-dispatcher适配、execution-control准入/完成、Assignment、只读工具 | 保留原生阶段，完成缺口反馈与受限刷新，无新Dispatcher或Core协议 |
| W1-4 结果工作台 | 可选gpt-6-astra/low：apps/web/src/features/task-execution、api.ts | 当前三视图呈现Coverage/验证/证据/具体限制，保持五主题；不换画布库 |
| W1-5 最小联合验收 | 主代理 | 固定SHA运行A层；满足明确付费条件后才运行B层，分别记录通过和pending |

架构、迁移、契约、锁文件由主代理唯一负责；子代理只实施冻结文件范围。任务共享模块串行交接，具体开发使用当前会话，不另建Codex任务。新阶段分支codex/phase-2-web-assessment；已建立一个独立阶段工作树以保留原运行SHA，不删除历史树。

## 3. 数据和API草案

建议新增以下窄表，避免一轮建设完整评估平台：

- assessment_plans（items为严格校验的有界JSON快照）：Task、revision、固定Profile摘要、目标/维度/方法、required、状态、理由。一次计划变更生成revision，旧版本只读。
- verification_runs / verification_result_revisions：固定主张/方法/来源；result revision追加结论/限制/规则及supersedes。
- observations / evidence_links：ToolCall唯一来源、HTTP交换Artifact、完整/截断标记；证据与主张版本的supports/refutes/limits。
- 候选提交复用现有ToolCall的AgentRun/request_id唯一、规范摘要、原输入和回执，不增加assessment_submissions表。
- 显式快照读取复用平台工具ToolCall审计及AgentRun分配快照，不增加agent_snapshot_reads表。
- completion_reviews：Task/AgentRun/原输出digest/assessment_revision、accepted/needs_followup/partial、缺项及同revision触发次数，持久Reason补充触发。

现有task_executions.execution_snapshot固定assessment Profile，不重复存模型Key/上游凭据。assessment数据只在Task当前epoch内接受新Agent写入；已接受原提交回执在任务结束后仍可只读核对，处理顺序与当前命令约定一致。

同一次验证结算：先锁Task检查许可→锁计划revision→核对原submission→读取真实ToolCall/Artifact归属/状态→保存result revision与EvidenceLink→更新覆盖投影→同事务写Task事件。网络访问、文件读取和Cairn写入不置于长数据库事务；摘要完整性失败返回待核对，不能生成confirmed。

迁移0008的精确DDL与DTO由主代理在评审后先落盘，RLS继续租户/项目过滤；跨Cairn关联只保存原生ID，不宣称跨库FK或原子事务。现有任务/快照/result字段尽量增量兼容，不重写0006/0007。

## 4. 运行Profile与工具实现

Core增加静态、版本化Profile注册表：fixture-web-v1指向现有FixtureEvidenceEvaluator；closed-web-assessment-v1指向WebAssessmentEvaluator及HTTP方法规则。Profile只有部署管理员可注册，Task输入不能提供任意实现路径或Class名。

新的自建站点origin与Deployment UID/镜像由正常生命周期绑定，不把删除fixture allowlist当成目标开放。工具以固定handler注册，新增http_request走现有Kali受管进程；新增assessment_read/evidence_read/graph_refresh/verification_submit走平台模块，但同样登记原操作与真实归属。

每个工具定义JSON Schema、读/写类别、允许阶段、目标访问类别、大小/时间界限和已批准版本。Reason只拥有只读工具；Bootstrap/Explore按Profile获得受控HTTP和候选提交。无通用插件加载或自动下载MCP。

HTTP采集由helper生成结构化回执；控制服务登记Observation/Artifact并返回小型引用。头部/正文内容作为数据，禁止写进系统合同。新调用读取当时Task许可，GET/HEAD/OPTIONS之外请求明确拒绝；部分响应仍可查看，但完整性判据不得通过。

## 5. 完成反馈的适配方法

保留原生Cairn的complete/intents/noop返回模型。Wuji在实际调用Core complete之前登记并评估完成提案：

1. 满足本Profile且Goal映射有效：按现有原生complete回写/核对及停止流程。
2. 只能部分结束：先按平台撤许可/停止核对，Core仅stop，不伪造成功完成边。
3. 缺口仍可推进：保存needs_followup，不调用Core complete；Dispatcher适配识别这是业务结果，不能传普通409给原生Reason后按failed结束整Task。

实现采用Wuji自有Reason调用包装：受控客户端对明确needs_followup抛出专用结果类型，包装器在原生阶段finally释放租约后记录“输出已保存、完成提案未接受”。不制造Core成功响应。持久completion_reviews驱动原生_reason_trigger的补充输入；仍由原生Reason提出Intent。原生checkpoint只作运行缓存，不承担触发回执。

评估revision未变化时最多接受两次相同缺口的完成提案；达到上限记录no_progress部分结束。新证据/评估revision允许新判断但仍受Task预算/时间/工具轮次限制。网络unknown、真实执行unknown与needs_followup分开，unknown继续核对，不启动补充Reason。

必须同步更新Core.finish_run、WujiDispatcher._reap_futures与Reason包装之间的结果分类；不得只改一个返回码。最小契约夹具覆盖这条直接变化的行为，Core源码哈希仍保持。

## 6. Goal与覆盖的可评审边界

首批规则只对有限HTTP安全配置主张做确定性评估。本批不实现总Goal映射、不改模板或创建页面。总Goal保持unknown，只报告有限评估项与证据。

Coverage不是第二个任务图：它记录哪些批准的方法有证据、哪些被阻断；不直接调度工具或新增授权。Reason基于coverage读取生成普通Intent；发现新资源后仅在同Task授权与已注册目的地内验证，超出则记录待授权，不进行“无害探测”绕过范围。

本阶段不实现完整Finding生命周期、严重度引擎、报表发布或通用规则DSL。UI显示主张、方法、验证结论、证据与覆盖项，不把confirmed一律汇总为漏洞。

## 7. 验证入口与停止条件

以下为拟新增入口，现在未运行：

- `pytest tests/web-assessment -q --tb=short`：一个临时PostgreSQL，三条规则路径、候选归属/幂等、追加纠错和完成缺口分类。
- `node --test tests/task-workers/http-observation.test.mjs`：自建站点三路径及一组必要拒绝/截断/取消，复用旧进程边界测试证据。
- `pnpm contracts:check`与相关API包/正式web构建各一次；未变Python/Node锁文件不重新安装。
- `tests/web-assessment/run_closed_web.py --run-file ABS --mode synthetic`：同一真实Cairn/Pi/LiteLLM/K8链路的A层合同验收；不复跑旧预算/双容器矩阵。
- 同入口`--mode approved-model --authorization-record ABS`：只有模型版本/价格/用户授权USD额度齐备才启用B层。实际命令参数最终与实现一致，不创建一个缺少消费者的空脚本占位。
- Codex浏览器只走一次新结果页：主张→观察→证据、正常对照及阻断原因可分辨；不重跑创建四步、五主题和全部旧事件测试。

如改context合同，增加一个原生Pi压缩后读取平台持久记录的定向检查。无论A/B都不使用参考平台为目标，不追加模型探活、换模型、压力或长断线矩阵；失败据trace定向修复，同类脚本最多两轮，通过即停。

## 8. 交付与当前未决项

交付代码/合成实验站点、版本化方法及工具合同、迁移/生成API、实际结果页、A/B分开的SHA/run_id/命令/退出码/局限记录。继续保留4182已交付运行、381ae3a及master；真正测试候选切换前正常停止并保留其记录，不手改SHA。

用户已确认本批只读HTTP方法与有限范围、两次无进展部分结束和总Goal保持unknown。付费模型版本和新增USD授权是B层前置输入，当前不存在，不能推断。React Flow和布局库版本留独立后续切片；本Plan不授权其安装或替换工作台。
