# vNext MAF v2 实施验收状态

状态：in-progress；日期：2026-09-13。代码起点 `1d73a767599732d9a53f81ad2cc553f4bf11d84e`。

用户已批准实施；原始 [75条验收定义](../../vnext/ACCEPTANCE.md)中的 not_run 是导入时状态，不能当作当前代码结果。实际执行证据将在本阶段按任务、命令和被测提交追加。此时没有产品通过结论。

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| P00 基线与来源 | accepted（本项） | 基线 c9871a6；源文件保留与实际环境已核对，GPT-6/xhigh 审查无发现 |
| P01 SDK 探针 | accepted（局部能力） | [当前报告](../../vnext/P01-report.md)；SDK13项@8c3fa9c，watchdog3项@1d77954，离线渲染4项@1598ea2；[最终范围复核](../../vnext/evidence/P01/review-round2.md)关闭所有发现，后续产品 Gate 独立 |
| P02 合同与测试底座 | accepted（本项） | [原报告](../../vnext/evidence/P02/report.md)、[修复](../../vnext/evidence/P02/fix-round1/report.md)、[最终范围复核](../../vnext/evidence/P02/final-controller-review.md)；后续完整 AC 仍 partial |
| P03 规范持久化与证据 | accepted（本项） | 53项@dcf5cc2；修复6项@c2a86e3；[范围复审](../../vnext/evidence/P03/fix-round1/review.md)关闭2项P2；完整AC仍按下游分工 |
| P04 知识接纳与评估 | accepted（本项） | [报告](../../vnext/evidence/P04/report.md)；24项原候选、6项可见性、3项新鲜度定向结果；[范围复核](../../vnext/evidence/P04/review-fix-round1/controller-review.md)关闭F1/F2 |
| P05 控制与容量 | accepted（本项） | 代码 `3102579`；[修复报告](../../vnext/evidence/P05/fix-round1/report.md)与[主控制器定向复核](../../vnext/evidence/P05/fix-round1/controller-review.md)关闭初审 F1/F2；复用实施者已采集 3 项定向证据，不扩大为完整 Runtime 集成验收 |
| P06 模型/工具准入与累计账本 | test-first in-progress | [实施合同](../../vnext/P06-implementation-contract.md)；SOL Curie `01a09869` 负责测试，GPT-6 Faraday `01a0981b` 负责核心实现且待 `START` |
| P07—P20 开发和机制验收 | not_run | [P07 实施合同](../../vnext/P07-implementation-contract.md)已由主代理设计；其余按依赖执行，未验证不标通过 |
| 真实模型效果 | not_run | 需明确模型/数据及新增 USD 额度 |
| 生产切换/旧数据删除 | not_run | 需独立明确授权；开发不隐式实施 |

运行中仅用自建夹具；HTTP/UI成果提供完整交互及截图，离线记录按其原生媒介保留。自行检查与代理审查如实区分；不宣称第三方认证。记录文档的提交与被测代码提交分开。

P01 永久证据由 Wuji vNext P01 文档维护，位于 [docs/vnext/evidence/P01](../../vnext/evidence/P01/relocation.json)，不放入可清理的 SDD scratch。当前 [CapabilityRecord](../../vnext/capability-record.json) 与 [实际截图来源](../../vnext/evidence/P01/screenshots/provenance.json) 已发布；原缺图/初审状态与旧运行结果按原样归档，不追写历史通过结论。
