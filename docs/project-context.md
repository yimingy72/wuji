# Wuji 项目背景与有效文档索引

2026-09-13 当前实施：用户批准按完整 [vNext v2 Spec](vnext/SPEC.md) / [Plan](vnext/PLAN.md)进入重构。执行工作树为 `work/worktrees/vnext-maf`，分支 `codex/vnext-maf`，起点 `1d73a767599732d9a53f81ad2cc553f4bf11d84e`。见[阶段入口](stages/vnext-maf/spec.md)、[实施决定](vnext/decision-register.md)与[验收状态](stages/vnext-maf/acceptance.md)。下文 Cairn/Pi 为旧实现及历史来源，不再约束新核心；新链路不允许运行旧内核。主目录上一轮草案未提交变更保留。

本轮最新模型分工见实施决定 D10：修复、验证及轻量重复工作使用 SOL/xhigh，核心开发或重大复杂问题才使用 GPT-6/xhigh；下文及历史报告中的旧模型限定仅描述当时约定。

更新：2026-09-11；当前文档与GitHub交付分支为 `codex/github-upload`，业务来源为 `codex/phase-2-web-assessment@40472c6`（旧运行检出保留），架构收口起点6ee84b5。此页负责恢复背景与导航；设计正文、阶段验收各有独立权威来源，不在此复制完整架构。先读根 [AGENTS.md](../AGENTS.md)。

GitHub 克隆入口：默认分支 `codex/github-upload` 基于 W1 记录提交 `40472c6` 整理，本文档及阶段文档均在当前克隆内。下文工作树路径描述原开发机器的来源，不是克隆依赖；版本对应见[仓库交接说明](repository-handoff.md)。

## 1. 产品背景与当前决定

Wuji 是 Kubernetes 原生的授权安全验证平台。产品流程是创建任务 → 执行观察 → 人工介入 → 查看结果，五类场景决定输入与流程。前端沿用 Ant Design 工作台、五套主题，表单表达用户意图，不直接照搬 API 字段。默认匿名测试；授权、执行、证据和预算由平台负责；Agent 框架复用成熟能力。

2026-09-10 对话已确认、需要带入下一阶段的决定：

- 创建者在任务创建中确认具体授权范围，不仅从管理员预导入列表中选择；新增职责不等于获得组织管理权限。
- 基础配置页面纳入下一步规划；模型服务在组织内共享，由管理员维护，沿用目标架构的 TenantAdmin 职责，任务选择模型方案。
- 删除路径级授权，保留域名/子域及协议端口；外域资源正常加载不授予主动测试权限。流量控制细节与实现留待后续，不作为本次配置页面开发的前提。
- Task模型预算改为金额USD，采用LiteLLM原生限制；组织模型配置不设置Task预算。主/子Agent、Reason、收尾和摘要共用，重启不重置；未知价格不按零计费，不承诺未经验证的并发零超支。
- 没有可用模型方案时只能保存草稿，配置好模型后再创建任务；发布要求同版本显式连接检查成功，关闭自动付费探活。旧0.5 Spec/Plan已标superseded，不可直接实施。
- 2026-09-11 用户确认：平台为五类场景提供默认Goal/完成条件模板，并允许创建任务时自定义；沿用版本化场景与快照，详见[评估配置契约](assessment-model.md#21-配置契约)。用户后续要求精简创建入口，补丁3094e6d已落实模板、无弹窗保留输入和补充线索。正式[D3-B方案](stages/phase-1c-task-creation/spec.md)已随核心闭环计划获批。Reason只读已有证据，主动补证通过Intent交给Explore；其余长期记忆和覆盖增强仍按独立方案处理。
- 直接复用Cairn Server/Dispatcher、Pi coding-agent与LiteLLM。一个Task对应一个Cairn Project；每个Task一个Pod，agent容器运行多个Agent，kali容器提供共享执行环境。Task统筹目标与外部工具/约束，Cairn黑板核心不改。Cairn是唯一可写探索图，Wuji保存任务、准入、执行账本及验证；结果先保存再同步。
- LangGraph/LangChain/Deep Agents不再是目标必选依赖；P0仅为历史实验。候选版本及必要增量见[架构替代决策](cairn-architecture-decision.md)，已完成首轮真实封闭夹具联调，最终候选收口以本阶段验收为准；不代表生产出口或真实模型效果已验收。
- 本次开发在当前会话，架构由主代理独立设计；可按需使用gpt-6-astra/low子代理，不再强制SOL/Luna、并发数、独立worktree或独立测试代理。历史报告中的实际模型不改写。
- 2026-09-11用户最终确认单Task Pod双容器并授权开始开发。运行基础及Task/Cairn桥接基础库已完成最小验收；范围见[Task/Cairn桥接Spec](stages/phase-1c-cairn-bridge/spec.md)/[Plan](stages/phase-1c-cairn-bridge/plan.md)：原生客户端/Server复用、Task绑定、持久操作日志、调度预选及结果核对；不接正式API或启动真实模型/目标。该段为基础库阶段范围；后续0.5控制面与Cairn执行已随核心闭环交付，W1新增有限评估，以下表和对应验收为准。

不得把助手曾提出但未确认的预算数字、默认端口集合或 Scope 有效期写成永久默认值。

## 2. 当前基准与文档位置

| 对象 | 已核对来源 | 含义 |
| --- | --- | --- |
| 本机旧运行工作区 | `codex/phase-1b-b23`，`381ae3a2205965ad6aab1ce787d490d2c02839f3` | 正式业务 0.4.0；不是全部架构验收完成 |
| 核心闭环历史来源 | `codex/phase-1c-core-loop`，起点`5631d80` | 0.5候选、0006/0007与真实框架闭环；最终SHA见阶段验收，4182测试环境 |
| 当前 W1 业务来源 | `codex/phase-2-web-assessment@40472c6`，被测 `f12a46f` | 0.5.0、迁移0008、有限Web评估机制；真实模型效果待验收 |
| GitHub 当前入口 | `codex/github-upload` | W1源码及更新后的说明文档；文档提交不增加业务验收结论 |
| D3-A交互原型 | 原型代码保留于同工作树 `spikes/creation-workbench` | 4186独立演示，不代表真实Task状态 |
| 历史设计来源 | `codex/product-interaction-plan@8dcf7ec`，此前修订起点`0051651047daeeee3b8741c460f182d42e755238` | 历史参考，不能覆盖后续用户确认 |
| 产品原型 | `codex/product-interaction-prototype`，`2e35177` | 旧版两条模拟路径，未实现新版五场景与真实执行 |
| master | `28fcd44eebc205a35735d3e7b60a308ce5f749bc` | 保留原阶段基线，不因文档或最小验收自动前移 |

当前文档整理工作树为 `work/worktrees/github-upload/`，W1业务来源为 `work/worktrees/phase-2-web-assessment/`；历史设计工作树位于仓库下 `work/worktrees/product-interaction/`，原型位于 `work/worktrees/product-interaction-prototype/`。这些位置是当前检索入口，执行时用 `git worktree list` 核对，不将历史路径当成永远有效。若新检出缺少最新文档，先查上述设计分支和 Git 历史，不在旧文档上重复决策。

文档独立提交期间不移动绑定运行 SHA 的主工作区 HEAD；主目录同步的规则/入口如暂未提交，应在交付中明确说明。后续正式集成按 [本地工作台](local-development.md) 流程处理旧进程与运行记录，不通过修改私有运行文件伪造版本一致。

## 3. 实现与验收状态

各历史行描述该阶段结束时的范围；“未接入”等字样不能覆盖其后的核心闭环与W1验收。

| 阶段 | 阶段结束时的真实状态 | 权威记录 |
| --- | --- | --- |
| 开发基线 / Phase 0 | 工程规则与旧原型通过，不能代表 Runtime 或平台架构完成 | [基线验收](stages/development-baseline/acceptance.md)、[历史原型证据](phase0-validation.md) |
| Phase 1A | 正式身份、项目、数据库、生命周期与主题已集成；完整验收 partial，3 项真实回调待测 | [验收](stages/phase-1a/acceptance.md)、[延期清单](stages/phase-1a/deferred-tests.md) |
| Phase 1B B1 | Scope 与预览已实现，通过最小验证 | [验收](stages/phase-1b/acceptance.md) |
| Phase 1B B2/B3 | 创建、查询、取消、幂等回执、事件同步已实现，最小 API 6/6、浏览器 1/1；仅 queued/cancelled | [验收](stages/phase-1b/b23-acceptance.md)、[延期清单](stages/phase-1b/b23-deferred-tests.md) |
| 产品交互 | 旧原型 review-ready / partial；新五场景设计不能沿用该验收 | [记录](stages/product-interaction/acceptance.md) |
| Phase 1C 前置 | P0原实验最小验收有效；旧0.5草案已被新架构替代，业务尚未启动 | [Spec](stages/phase-1c-prep/spec.md)、[Plan](stages/phase-1c-prep/plan.md)、[记录](stages/phase-1c-prep/acceptance.md) |
| Harness适配 | 独立P0包通过受限Deep Agents与两协议工具往返；未接正式Agent | [P0验收](stages/phase-1c-prep-p0/acceptance.md) |
| Cairn架构收口 | 用户已批准，本批文档交付状态以验收为准；不代表业务实现 | [Spec](stages/cairn-architecture-baseline/spec.md)、[Plan](stages/cairn-architecture-baseline/plan.md)、[验收](stages/cairn-architecture-baseline/acceptance.md) |
| Runtime基础库 | 026457f完成首批基础库，25个离线用例和包构建通过；未接真实执行 | [Spec](stages/phase-1c-runtime-foundation/spec.md)、[验收](stages/phase-1c-runtime-foundation/acceptance.md) |
| Task/Cairn桥接 | 8e250f4修复结果拒绝竞态；初轮11项、相关复测4项和包构建通过，本批基础库accepted；未接正式调度 | [Spec](stages/phase-1c-cairn-bridge/spec.md)、[验收](stages/phase-1c-cairn-bridge/acceptance.md) |
| 控制面D1 | aa62b9a完成独立草稿API/迁移/权限，5项真实PostgreSQL与API检查、契约、构建通过；完整0.5仍未交付 | [Spec](stages/phase-1c-control-plane/spec.md)、[Plan](stages/phase-1c-control-plane/plan.md)、[验收](stages/phase-1c-control-plane/acceptance.md) |
| D2模型配置 | 86f927f交付TenantAdmin/版本配置/原生检查/发布/选择；5项API+1项原生两协议重启+2项结构检查通过，真实K8生命周期未执行 | [Spec](stages/phase-1c-model-config/spec.md)、[验收](stages/phase-1c-model-config/acceptance.md) |
| D3-A创建原型 | b6afc12原四组走查保留；3094e6d落实用户入口反馈，构建/浏览器及9a6b4ae上2项定向检查通过；完整用户通过未宣称，入口4186 | [Spec](stages/phase-1c-creation-prototype/spec.md)、[记录](stages/phase-1c-creation-prototype/acceptance.md)、[D3-B衔接](stages/phase-1c-creation-prototype/backend-handoff.md) |
| 核心闭环与D3-B | accepted（封闭夹具）：6c5934c完成真实创建/启动、Cairn/Pi/共享Kali、Fact/证据/结果/停止及M4关系视图；未开放生产出口和真实外部目标 | [核心总计划](stages/phase-1c-task-creation/core-loop-plan.md)、[D3-B Spec](stages/phase-1c-task-creation/spec.md)/[Plan](stages/phase-1c-task-creation/plan.md)、[状态](stages/phase-1c-task-creation/acceptance.md) |
| Cairn / Pi / LiteLLM / Runtime集成 | 固定版本已通过真实K8封闭HTTP/合成模型路径；未开放外部目标、生产出口或全量流量采集 | [架构替代决策](cairn-architecture-decision.md)及下节设计 |
| W1封闭Web评估 | accepted（机制）：f12a46f真实合成闭环及Pi原生压缩通过；4资源三类结果、证据和Reason补充反馈已交付；真实模型自主效果待明确新增USD授权 | [Spec](stages/phase-2-web-assessment/spec.md)、[Plan](stages/phase-2-web-assessment/plan.md)、[状态](stages/phase-2-web-assessment/acceptance.md) |

表内测试是复用历史记录，未在本次文档提交重跑。B2/B3 测试代码基准为 `e76a265d445ae9548d7f56fdb85f9b8b5c005759`，具体 run 与限制以验收正文为准。架构验收目录的 80 项不是本次或每次开发必须执行的清单。

## 4. 按任务阅读

| 任务 | 必读文档 | 阅读时保留的区别 |
| --- | --- | --- |
| 新阶段与整体规划 | [架构替代决策](cairn-architecture-decision.md)、[产品](../PRODUCT.md)、[主架构](architecture.md)、[评估模型](assessment-model.md)、[开工准备](predevelopment-plan.md) | 目标架构不等于现有代码；当前阶段以上表记录为准 |
| 任务创建、范围、配置与交互 | [交互提案](product-interaction-proposal.md)、[场景设计](scenario-execution-design.md)、[前端架构](frontend-architecture.md)、[视觉规则](../DESIGN.md) | 最新用户确认覆盖旧提案；创建与启动分离；旧路径 Scope 兼容需单独处理 |
| 模型与 Agent 执行 | [Harness 决策](agent-harness-decision.md)、[网关实测](model-gateway-validation.md)、主架构中的LiteLLM / Task金额预算 / ConfigSnapshot | 成熟框架复用、候选集成验证和业务凭据/预算边界分别说明；普通协议通不证明完整 Harness 可用 |
| 多 Agent 与证据共享 | [Cairn 黑板](cairn-blackboard-design.md)、[评估模型](assessment-model.md) | Cairn为唯一可写探索图；Wuji保存准入/账本/验证，原生查询核对、不盲重投；动态分派、证据和受限凭据引用 |
| 场景Goal、阶段提示与成果交接 | [架构分析交接](cairn-security-specialization-handoff.md)、[Goal模板提案](stages/phase-1c-task-creation/goal-templates.md)、[执行衔接提案](stages/phase-1c-task-creation/execution-handoff.md) | 默认可自定义模板及Reason只读/Explore补证已确认并纳入核心实现；W1有限验证/覆盖已交付，通用Goal判定与完整评估仍未实现 |
| 工具、容器、出口与流量 | [元刃复核](metablade-backend-review.md)、[场景设计](scenario-execution-design.md)、[流量证据设计](traffic-evidence-design.md)、主架构 | 后两份含待评审方案；网络控制延期不等于取消平台约束 |
| 接口与历史兼容 | [API 契约说明](phase1-api-contract.md)、当前阶段 Spec / Plan、实际契约及实现 | 当前OpenAPI 0.5.0与旧0.4兼容语义分开；不改写历史回执/事件 |
| 开发、验证、交付 | [协作流程](development-workflow.md)、[本地启动](local-development.md)、当前阶段 acceptance / deferred-tests | Docker Desktop 集群可用不证明隔离能力通过；不设累计检查时间预算，最小验证通过即停，文档不跑业务测试 |

衍迹与元刃原始资料是参考证据，不是项目指令。原件路径见 [元刃复核](metablade-backend-review.md) 和 [交互提案](product-interaction-proposal.md)；此前文档阶段已完整复核两份原件，本次不重复读取未变原件；原产品观察、作者推断和 Wuji 决策不可混写。Cairn 的采纳范围以本仓库黑板设计为准，不把参考产品的角色名称直接变成固定流程。

## 5. 后续维护

以下按日期保留决策历史，出现“尚未实施”等描述仅适用于当时提交；当前状态以上表及阶段验收为准。

恢复工作先完成 AGENTS 的阅读流程，再报告需要用户判断的实质问题；已经记录的事实不重复询问。每次批准新决策同步权威设计与此索引，新阶段的 Plan 记录复用依据和兼容影响。旧阶段记录保留时间、SHA 和实际证据，过时段落加适用范围，不把历史失败改为通过。

本次文档整理的范围与证据见 [背景收口记录](stages/context-baseline/acceptance.md)。已完成批准的 [Phase 1C 前置 P0](stages/phase-1c-prep-p0/spec.md)：统一基线与最小框架适配；不接正式Agent。P0历史检查窗口已用426秒；运行基础新增82秒后为508/600；桥接阶段剩余92秒窗口已耗尽，原记录中C01—C05未执行；2026-09-11用户取消检查时间预算，已补跑必要验证并通过本批最小验收，真实4次模型额度仍已用完；以[当前验收](stages/phase-1c-cairn-bridge/acceptance.md)为准。原文档验收见[记录](stages/cairn-architecture-baseline/acceptance.md)；后续澄清已选择单Pod双容器，原候选026457f完成首批[运行基础库](stages/phase-1c-runtime-foundation/spec.md)。基础库之后为控制面基础→调度适配→共享Runtime接入→产品接入→真实目标开放；0.5业务Spec与交互仍待冻结，不发布新接口或执行迁移。

2026-09-11：用户取消开发检查的累计时间预算，继续最小必要验证、通过即停；产品Task金额预算及真实模型调用授权额度保持原约定。最新补跑结果以桥接阶段验收为准。

2026-09-11本轮继续：先交付D1独立草稿，承接无模型可保存的用户决定；D2组织模型配置→D3快照/ready/start→D4权威执行账本按依赖实施。完整0.5和新版创建页面尚未交付。

2026-09-11 D2已完成最小验收。管理员手填公司网关单价；LiteLLM原生配置/检查/重启已实测，完整Task预算/调度仍未接入。后续D3配置快照/范围确认/ready-start→D4账本与调度；不跳过创建交互评审。

2026-09-11用户确认首批正式创建先Web单点，创建者填写授权截止时间。D3-A新增独立4186原型，不接API；排除优先/默认子域及全部包含端口、创建结果不明原键恢复、服务新版Key重输、显式缓存价格和平台/网关撤销状态已落入原型，仍待用户交互评审。

2026-09-11：用户要求将 Cairn 调度、长任务记忆、覆盖、Fact 与文件交接结论发送主开发任务并继续下一步开发；见[开发交接](cairn-security-specialization-handoff.md)。默认可自定义 Goal 模板已确认，其他候选机制按交接说明收口，不将继续请求解释为全部技术细节已批准。

2026-09-11 主开发已读取交接与实际代码，完成D3-B具体Spec/Plan、五模板和调度衔接草案，并纠正主架构残留“独立Agent Pod”措辞。随后收到用户真实创建评审反馈并直接完成原型修复；用户强调完整核心优先，已收敛为一个有明确终点的总计划。当前仍Default模式，已批准的原型修改已实施，尚未冻结的正式接口/调度不先施工；在应用Plan模式完成整体方案后按内部里程碑连续推进，不重复发起微批次审批。

2026-09-11 核心闭环计划已获明确实施授权，分支codex/phase-1c-core-loop连续开发M1—M4。已实现0006/0007、D2正式模型页、v2任务创建、受控start、真实Cairn/Pi/LiteLLM/双容器Task Pod与Artifact持久卷。最新M4采用黑板/时间线/工作区及真实关系导航；不得将早期draft状态当成当前进度。最终候选与复用证据见[核心验收](stages/phase-1c-task-creation/acceptance.md)。主目录381ae3a、master28fcd44、4180保留。

2026-09-11 核心交付后：主代理依据实际b79efa6及分析交接准备[W1 Spec/Plan](stages/phase-2-web-assessment/spec.md)，目标是有限自建Web评估，先A层机制、后明确授权的B层真实模型效果。草案不是新业务或付费批准；当前4182保持运行，文档暂未提交以保留其绑定HEAD。

2026-09-11：W1已获PLEASE IMPLEMENT THIS PLAN授权；当前在独立phase-2-web-assessment工作树实施，仅机制与合成模型，真实效果等待明确新增USD授权。

2026-09-11 W1机制已验收，具体事实与限制见[W1验收](stages/phase-2-web-assessment/acceptance.md)。不再按旧草案将评估接口/有限覆盖/原生压缩机制称为未实现；真实模型效果仍未验收。
