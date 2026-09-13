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
| M2 host/child transport | reviewed / passed（限定切片） | [永久证据](../../vnext/evidence/P10/M2/README.md)提交 `bdee147`：原四项 P2 全部关闭，真实 Scheduler/Outbox→Node→MAF child→Gates→P03/P04、当前/历史补交和半提交恢复已按分 SHA 验证。最终 current 场景 `d61cb91`（产品 `4268b6a`、测试 `0f545ba`、冻结0013）1项/11.55s；其余撤销、Pod、profile、基础与真实 Thread 检查复用各自记录，不合称一次全量运行。r1–r6 FAIL 保留。范围仅 hosted Explore，不覆盖完整P07/P10/P08、其他work kind或Kubernetes |
| P09 Scheduler 已验证切片与定向复审 | reviewed / partial；非完整 accepted | 基线 `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c` 原 31 项、直接消费者 4 项、共享容量竞态 1 项；修复 `e0a10b586905ed705b0d7f520bda6f6f96b26cac` 提交前 A/B/C RED 3→GREEN 3、0010→0011 升级 1、synthetic receiver UID 复制 1。[永久证据与缺口](../../vnext/evidence/P09/README.md)、[machine index](../../vnext/evidence/P09/index.json)、[初审](../../vnext/evidence/P09/reviews/P09-review.md)和 [Dalton 独立定向复审 PASS](../../vnext/evidence/P09/reviews/P09-rereview.md)；本次只归档原输出，不重跑。逐查询 SQL/参数/结果及临时原始输入缺失已登记；真实 P10/M2、P08 非知识事件、真实退出 failure/retry 闭环与恢复仍 partial，关联 AC 不标全通过 |
| P08 会话与审批 | in-progress / changes required | 平台源码 `a755847`、Worker `65e4472`、B2 `1f17179` 已接入后续修复；`f4c3b76` 的[定向复审](../../vnext/evidence/P08/reviews/P08-platform-rereview.md)仍有 F2/F3/F4/F5 四项残留（3P1+1P2），F1/F6仅source-addressed。SOL正直接修复并准备真实0014/SDK/跨进程审批验证；现有局部source/wire检查不代表完整P08通过 |
| P10—P12 完整机制验收 | partial / not accepted | 已有切片按各自行记录；真实 Outbox、完整控制/恢复/完成与相应集成尚未通过，不以 P09 局部结果或迁移关口代替 |
| P13 受权图投影与持久视图 | backend reviewed / M4 partial | core `3015ca6`、P04 port `592bed2`、0012迁移与测试 `44ddc68` 的[真实结果](../../vnext/evidence/P13/runtime-green/report.md)为 12 项通过。独立审查发现的两项 P2 已在 `69e3a1d` 修复，[定向证据](../../vnext/evidence/P13/review-fix/report.md)为 3 项 / 3.16s、生成检查、22 组 HTTP 与截图；[独立复审](../../vnext/evidence/P13/reviews/P13-rereview.md)关闭两项，[完整证据入口](../../vnext/evidence/P13/README.md)。原 12 项及 pure builder 9项未重跑。Layout、ViewStream、P14正式容器与后续P12类型仍未验收，故不标 M4 全过 |
| P14 TopologyFlowCanvas fixed DTO slice | reviewed / partial | 原代码 `9a1c8e20ccd57b19e74d748129a3d5d524eab6f4`，修复代码 `bd3111a62a624aa5acef7d167ffe96b18747934a`，证据 `64bbdf2974b39856a2cb29dd1eee97cb1a70ca93`；[实施与截图](../../../tests/topology/report.md)、[修复证据](../../../tests/topology/review-fix-report.md)、[初审归档](../../../tests/topology/P14-review.md)与[PASS 复审](../../../tests/topology/P14-rereview.md)固定实际范围。16 Vitest、2 个受影响 Chromium 用例及 web typecheck 通过；复用原五主题截图。真实 P13 API/Auth、Layout CAS、ViewStream、记录详情与规模 p95 仍 pending/not_run，不是 M4 闭环 |
| P15—P20 开发和机制验收 | not_run | 按依赖执行，未验证不标通过 |
| 真实模型效果 | not_run | 需明确模型/数据及新增 USD 额度 |
| 生产切换/旧数据删除 | not_run | 需独立明确授权；开发不隐式实施 |

运行中仅用自建夹具；HTTP/UI成果提供完整交互及截图，离线记录按其原生媒介保留。自行检查与代理审查如实区分；不宣称第三方认证。P13 纯片由主代理委派的 SOL/xhigh 执行，不冒称主代理独立测试。记录文档的提交与被测代码提交分开。

本次 P07/P14 状态更新仅修正实施状态文档的落点，复用上述已绑定代码、测试、截图与审查证据，不重跑验证。导入源包 `docs/vnext/ACCEPTANCE.md` 保持原始字节。

P01 永久证据由 Wuji vNext P01 文档维护，位于 [docs/vnext/evidence/P01](../../vnext/evidence/P01/relocation.json)，不放入可清理的 SDD scratch。当前 [CapabilityRecord](../../vnext/capability-record.json) 与 [实际截图来源](../../vnext/evidence/P01/screenshots/provenance.json) 已发布；原缺图/初审状态与旧运行结果按原样归档，不追写历史通过结论。
