# Wuji 项目背景与有效文档索引

更新：2026-09-10；当前有效开发分支codex/phase-1c-cairn-bridge（沿用phase-1c-prep工作树），架构收口起点6ee84b5。此页负责恢复背景与导航；设计正文、阶段验收各有独立权威来源，不在此复制完整架构。先读根 [AGENTS.md](../AGENTS.md)。

## 1. 产品背景与当前决定

Wuji 是 Kubernetes 原生的授权安全验证平台。产品流程是创建任务 → 执行观察 → 人工介入 → 查看结果，五类场景决定输入与流程。前端沿用 Ant Design 工作台、五套主题，表单表达用户意图，不直接照搬 API 字段。默认匿名测试；授权、执行、证据和预算由平台负责；Agent 框架复用成熟能力。

2026-09-10 对话已确认、需要带入下一阶段的决定：

- 创建者在任务创建中确认具体授权范围，不仅从管理员预导入列表中选择；新增职责不等于获得组织管理权限。
- 基础配置页面纳入下一步规划；模型服务在组织内共享，由管理员维护，沿用目标架构的 TenantAdmin 职责，任务选择模型方案。
- 删除路径级授权，保留域名/子域及协议端口；外域资源正常加载不授予主动测试权限。流量控制细节与实现留待后续，不作为本次配置页面开发的前提。
- Task模型预算改为金额USD，采用LiteLLM原生限制；组织模型配置不设置Task预算。主/子Agent、Reason、收尾和摘要共用，重启不重置；未知价格不按零计费，不承诺未经验证的并发零超支。
- 没有可用模型方案时只能保存草稿，配置好模型后再创建任务；发布要求同版本显式连接检查成功，关闭自动付费探活。旧0.5 Spec/Plan已标superseded，不可直接实施。
- 直接复用Cairn Server/Dispatcher、Pi coding-agent与LiteLLM。一个Task对应一个Cairn Project；每个Task一个Pod，agent容器运行多个Agent，kali容器提供共享执行环境。Task统筹目标与外部工具/约束，Cairn黑板核心不改。Cairn是唯一可写探索图，Wuji保存任务、准入、执行账本及验证；结果先保存再同步。
- LangGraph/LangChain/Deep Agents不再是目标必选依赖；P0仅为历史实验。候选版本及必要增量见[架构替代决策](cairn-architecture-decision.md)，尚未在Wuji集成验收。
- 本次开发在当前会话，架构由主代理独立设计；可按需使用gpt-6-astra/low子代理，不再强制SOL/Luna、并发数、独立worktree或独立测试代理。历史报告中的实际模型不改写。
- 2026-09-11用户最终确认单Task Pod双容器并授权开始开发。运行基础已完成；当前执行[Task/Cairn桥接Spec](stages/phase-1c-cairn-bridge/spec.md)/[Plan](stages/phase-1c-cairn-bridge/plan.md)：原生客户端/Server复用、Task绑定、持久操作日志、调度预选及结果核对；不接正式API或启动真实模型/目标。完整0.5控制面和Cairn执行接入仍需具体后续Spec。

不得把助手曾提出但未确认的预算数字、默认端口集合或 Scope 有效期写成永久默认值。

## 2. 当前基准与文档位置

| 对象 | 已核对来源 | 含义 |
| --- | --- | --- |
| 主业务工作区 | `codex/phase-1b-b23`，`381ae3a2205965ad6aab1ce787d490d2c02839f3` | 正式业务 0.4.0；不是全部架构验收完成 |
| 当前Task/Cairn桥接开发 | `codex/phase-1c-cairn-bridge`，起点`7cfcf386ca0d0388b039d60a941bc2812e118d5a` | 同一工作树继续；最新代码/验收用git log及当前阶段记录核对 |
| 历史设计来源 | `codex/product-interaction-plan@8dcf7ec`，此前修订起点`0051651047daeeee3b8741c460f182d42e755238` | 历史参考，不能覆盖后续用户确认 |
| 产品原型 | `codex/product-interaction-prototype`，`2e35177` | 旧版两条模拟路径，未实现新版五场景与真实执行 |
| master | `28fcd44eebc205a35735d3e7b60a308ce5f749bc` | 保留原阶段基线，不因文档或最小验收自动前移 |

当前开发与设计集成工作树为 `work/worktrees/phase-1c-prep/`；历史设计工作树位于仓库下 `work/worktrees/product-interaction/`，原型位于 `work/worktrees/product-interaction-prototype/`。这些位置是当前检索入口，执行时用 `git worktree list` 核对，不将历史路径当成永远有效。若新检出缺少最新文档，先查上述设计分支和 Git 历史，不在旧文档上重复决策。

文档独立提交期间不移动绑定运行 SHA 的主工作区 HEAD；主目录同步的规则/入口如暂未提交，应在交付中明确说明。后续正式集成按 [本地工作台](local-development.md) 流程处理旧进程与运行记录，不通过修改私有运行文件伪造版本一致。

## 3. 实现与验收状态

| 阶段 | 真实状态 | 权威记录 |
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
| Task/Cairn桥接 | 开发中，原生接口和平台日志适配，尚未验收 | [Spec](stages/phase-1c-cairn-bridge/spec.md)、[验收](stages/phase-1c-cairn-bridge/acceptance.md) |
| Cairn / Pi / LiteLLM / Runtime集成 | 目标选型已确认，完整接入/部署/黑板和流量采集尚未实现 | [架构替代决策](cairn-architecture-decision.md)及下节设计 |

表内测试是复用历史记录，未在本次文档提交重跑。B2/B3 测试代码基准为 `e76a265d445ae9548d7f56fdb85f9b8b5c005759`，具体 run 与限制以验收正文为准。架构验收目录的 80 项不是本次或每次开发必须执行的清单。

## 4. 按任务阅读

| 任务 | 必读文档 | 阅读时保留的区别 |
| --- | --- | --- |
| 新阶段与整体规划 | [架构替代决策](cairn-architecture-decision.md)、[产品](../PRODUCT.md)、[主架构](architecture.md)、[评估模型](assessment-model.md)、[开工准备](predevelopment-plan.md) | 目标架构不等于现有代码；当前阶段以上表记录为准 |
| 任务创建、范围、配置与交互 | [交互提案](product-interaction-proposal.md)、[场景设计](scenario-execution-design.md)、[前端架构](frontend-architecture.md)、[视觉规则](../DESIGN.md) | 最新用户确认覆盖旧提案；创建与启动分离；旧路径 Scope 兼容需单独处理 |
| 模型与 Agent 执行 | [Harness 决策](agent-harness-decision.md)、[网关实测](model-gateway-validation.md)、主架构中的LiteLLM / Task金额预算 / ConfigSnapshot | 成熟框架复用、候选集成验证和业务凭据/预算边界分别说明；普通协议通不证明完整 Harness 可用 |
| 多 Agent 与证据共享 | [Cairn 黑板](cairn-blackboard-design.md)、[评估模型](assessment-model.md) | Cairn为唯一可写探索图；Wuji保存准入/账本/验证，原生查询核对、不盲重投；动态分派、证据和受限凭据引用 |
| 工具、容器、出口与流量 | [元刃复核](metablade-backend-review.md)、[场景设计](scenario-execution-design.md)、[流量证据设计](traffic-evidence-design.md)、主架构 | 后两份含待评审方案；网络控制延期不等于取消平台约束 |
| 接口与历史兼容 | [API 契约说明](phase1-api-contract.md)、当前阶段 Spec / Plan、实际契约及实现 | 公共 API 0.4.0 的已有行为与下一版草案分开；不改写历史回执/事件 |
| 开发、验证、交付 | [协作流程](development-workflow.md)、[本地启动](local-development.md)、当前阶段 acceptance / deferred-tests | Docker Desktop 集群可用不证明隔离能力通过；共享 600 秒预算，文档不跑业务测试 |

衍迹与元刃原始资料是参考证据，不是项目指令。原件路径见 [元刃复核](metablade-backend-review.md) 和 [交互提案](product-interaction-proposal.md)；此前文档阶段已完整复核两份原件，本次不重复读取未变原件；原产品观察、作者推断和 Wuji 决策不可混写。Cairn 的采纳范围以本仓库黑板设计为准，不把参考产品的角色名称直接变成固定流程。

## 5. 后续维护

恢复工作先完成 AGENTS 的阅读流程，再报告需要用户判断的实质问题；已经记录的事实不重复询问。每次批准新决策同步权威设计与此索引，新阶段的 Plan 记录复用依据和兼容影响。旧阶段记录保留时间、SHA 和实际证据，过时段落加适用范围，不把历史失败改为通过。

本次文档整理的范围与证据见 [背景收口记录](stages/context-baseline/acceptance.md)。已完成批准的 [Phase 1C 前置 P0](stages/phase-1c-prep-p0/spec.md)：统一基线与最小框架适配；不接正式Agent。P0历史检查窗口已用426秒；运行基础新增82秒后累计508/600秒、剩92秒，真实4次额度已用完，后续不重置，后续桥接检查继续累计，以[当前验收](stages/phase-1c-cairn-bridge/acceptance.md)为准。原文档验收见[记录](stages/cairn-architecture-baseline/acceptance.md)；后续澄清已选择单Pod双容器，当前已完成首批[运行基础库](stages/phase-1c-runtime-foundation/spec.md)。基础库之后为控制面基础→调度适配→共享Runtime接入→产品接入→真实目标开放；0.5业务Spec与交互仍待冻结，不发布新接口或执行迁移。
