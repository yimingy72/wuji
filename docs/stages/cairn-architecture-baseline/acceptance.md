# Cairn 架构文档收口验收

- 文档检查：passed；本批文档阶段结论：accepted。
- 业务测试：not-tested / 本批不适用；不表示平台业务或框架集成验收通过。
- 日期：2026-09-10；文档检查批次：cairn-docs-20260910-944e95b。
- 起始基准：6ee84b5268a5012c69ba4567d78eb18727b41ee1。
- 被检查文档提交：944e95b360af079b99f76ee35ca1296706450b25。该提交等于通过检查的暂存树；后续仅补本文及Plan完成状态，不重跑无变化的业务检查。
- 本验收记录提交通过 `git log -- docs/stages/cairn-architecture-baseline/acceptance.md` 查询，不预填自身SHA。
- 依据：[Spec](spec.md)、[Plan](plan.md)、用户批准的架构复审修订计划。
- 架构设计与最终审查：当前会话主代理。可选文档整理：gpt-6-astra / low，只修改流程、通用模板和旧草案标注，不设计架构；本次不是独立测试。

## 1. 结果

| 项目 | 结果 | 实际证据 |
| --- | --- | --- |
| D01 架构一致性 | passed | 主代理逐项核对已批准决定：Task/Project一对一、平台Agent与共享Kali分离、资源唯一所有权、真实执行准入、结果先持久化、完成提案、单一图来源、LiteLLM Task金额及受限快照工具；旧规则只保留在注明历史/替代范围的材料中 |
| D02 文档与导航 | passed | 新Spec/Plan/Acceptance和架构决策均已落盘；25个变更Markdown的201个本地文件链接通过存在性检查；主目录规则与导航能进入有效工作树 |
| D03 状态与历史 | passed | 正式API仍0.4.0；P0及Phase1A/B验收文件未变；旧0.5 Spec/Plan在历史标记下正文逐字保留；原phase-1c-prep验收只追加当前入口 |
| D04 变更边界 | passed | 暂存清单只含25个Markdown文件，无业务源码/契约/锁文件/迁移/运行文件；两处AGENTS正文一致；主HEAD与master核对未前移；新增变更文档未发现长sk凭据模式 |
| D05 后续依赖 | passed | 明确控制面基础→调度适配→共享Runtime→产品接入→真实目标开放；旧0.5草案superseded，下一批具体业务Spec/接口/迁移仍未批准 |

## 2. 命令与检查说明

| 实际操作 | 退出码 | 结果 |
| --- | --- | --- |
| `git diff --check` | 0 | 文档差异无空白错误 |
| `git diff --cached --check` | 0 | 被提交暂存树检查通过 |
| `python3 -` 内联文档检查 | 0 | 枚举暂存文件，检查本地Markdown链接、秘密模式、两处AGENTS一致、主HEAD/master及历史正文；25份文档、201个链接，缺失0 |
| `git commit -m 'docs: adopt Cairn dispatch and shared Kali architecture'` | 0 | 形成944e95b文档提交 |

文档检查器第一版错误截断了带括号的原件路径，返回1；修正对Markdown尖括号目标的解析后第二次返回0，无需修改该原件链接。未扩大为业务测试或新增常驻测试脚本。此检查不验证网络链接可达性、外部源代码能力或所有Markdown锚点，也不是完整秘密扫描。

环境：本地phase-1c-prep工作树，使用Git和Python3进行静态文档检查。未安装依赖、构建、启动浏览器/Kubernetes、请求模型或访问目标；源码定位无需本批代码索引，纯文档不重建CodeGraph。

## 3. Git与运行边界

- 主业务工作区HEAD仍为381ae3a2205965ad6aab1ce787d490d2c02839f3。
- master仍为28fcd44eebc205a35735d3e7b60a308ce5f749bc。
- 正式文档提交位于codex/phase-1c-prep；主目录AGENTS与临时docs/project-context.md同步但保持未提交，以免改变绑定运行SHA。
- 本批未操作既有服务、数据库或私有运行记录，没有依赖安装、数据库迁移、远端推送或部署。

## 4. 保留限制与后续

Cairn、Pi、LiteLLM、平台Worker后端及共享Runtime尚未在Wuji业务实现或集成验收。候选版本与上游静态能力不等于可用部署。P0仅验收原受限Deep Agents/客户端切片，见[原验收](../phase-1c-prep-p0/acceptance.md)；Phase1A保持partial。

原Phase1C前置业务检查预算已用426/600秒、剩174秒，真实4次额度已用完；本次纯文档检查不重置或追加这些额度。下一批控制面Spec需固定0.5契约、配置快照、ready/start、执行代次、AgentRun/工具账本和Cairn绑定；本批文档完成不能代替其批准或验收。
