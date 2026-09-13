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
| P06 模型/工具准入与累计账本 | accepted（本项） | 基础 `f32678d`，修复至 `78095e6`，迁移头 `vnext_0009_p06_request_write_guards`；[最终报告](../../vnext/evidence/P06/full-candidate-6/report.md)记录 35 项 P06、1 项 P04 权限消费者与合同检查通过，[独立静态复审](../../vnext/evidence/P06/full-candidate-6/independent-review.md) PASS；完整 MCP/P08/P10/P16/P17 与真实 LiteLLM/外部目标仍 not_run |
| P07 ContextBundle pure slice | complete | D10 SOL/xhigh Raman `01a0989e` 执行目标测试，8 passed；代码/测试 `491ec0144ae63724e3696e9b47f259ea350ea4eb`，[证据](../../vnext/evidence/P07/context-pure-green)提交 `e22f7ce09c8aa052862440bca769506f4ee89ffa`；仅证明纯函数上下文构建及直接输入边界 |
| P07 M1 hosted runtime slice | reviewed / passed（本切片） | 修复代码 `5cfd581129c7991deaddaad9bfdaf8b4ee34b140`、[证据](../../vnext/evidence/P07/M1/review-fixes/README.md)提交 `57ec12ea2ada7acf7fe6a0ac7ac98b40e7c66012`；M1 5 项与直接受影响 P06 native consumer 2 项通过，[初审](../../vnext/evidence/P07/M1/reviews/P07-M1-review.md)的 2 个 P1/1 个 P2 已由 [PASS 复审](../../vnext/evidence/P07/M1/reviews/P07-M1-rereview.md)全部关闭；只确认 hosted M1 |
| P07 完整 SDK/runtime 合同 | partial / not accepted | M1 不覆盖原生审批、压缩、Session 恢复、完整负控、Supervisor/process truth、Scheduler、Task completion、Kubernetes/Pod 或真实模型效果；完整 P07 未 accepted |
| M2 host/child transport | not_run / not accepted | M1 的 `MafRuntime`、`run_assignment`、`PlatformWorkerHost` 与 verified-token 边界可复用；真实 child transport、P05 started 后启动屏障及 P10 Host 接入尚未形成 M2 验收证据 |
| P08—P12 开发和机制验收 | not_run | 按依赖执行，未验证不标通过 |
| P13 受权图投影与持久视图 | pure slice complete / persistence and API not_run | 纯函数代码与测试提交 `78a26e3`，[实际结果](../../vnext/evidence/P13/pure-green/report.md)为 9 项通过；只证明 builder 映射边界。持久快照、历史、分页、权限与 API 按[实施合同](../../vnext/P13-implementation-contract.md)等待 P06 门控后实施，不标完整 P13 accepted |
| P14 TopologyFlowCanvas fixed DTO slice | reviewed / partial | 原代码 `9a1c8e20ccd57b19e74d748129a3d5d524eab6f4`，修复代码 `bd3111a62a624aa5acef7d167ffe96b18747934a`，证据 `64bbdf2974b39856a2cb29dd1eee97cb1a70ca93`；[实施与截图](../../../tests/topology/report.md)、[修复证据](../../../tests/topology/review-fix-report.md)、[初审归档](../../../tests/topology/P14-review.md)与[PASS 复审](../../../tests/topology/P14-rereview.md)固定实际范围。16 Vitest、2 个受影响 Chromium 用例及 web typecheck 通过；复用原五主题截图。真实 P13 API/Auth、Layout CAS、ViewStream、记录详情与规模 p95 仍 pending/not_run，不是 M4 闭环 |
| P15—P20 开发和机制验收 | not_run | 按依赖执行，未验证不标通过 |
| 真实模型效果 | not_run | 需明确模型/数据及新增 USD 额度 |
| 生产切换/旧数据删除 | not_run | 需独立明确授权；开发不隐式实施 |

运行中仅用自建夹具；HTTP/UI成果提供完整交互及截图，离线记录按其原生媒介保留。自行检查与代理审查如实区分；不宣称第三方认证。P13 纯片由主代理委派的 SOL/xhigh 执行，不冒称主代理独立测试。记录文档的提交与被测代码提交分开。

本次 P07/P14 状态更新仅修正实施状态文档的落点，复用上述已绑定代码、测试、截图与审查证据，不重跑验证。导入源包 `docs/vnext/ACCEPTANCE.md` 保持原始字节。

P01 永久证据由 Wuji vNext P01 文档维护，位于 [docs/vnext/evidence/P01](../../vnext/evidence/P01/relocation.json)，不放入可清理的 SDD scratch。当前 [CapabilityRecord](../../vnext/capability-record.json) 与 [实际截图来源](../../vnext/evidence/P01/screenshots/provenance.json) 已发布；原缺图/初审状态与旧运行结果按原样归档，不追写历史通过结论。
