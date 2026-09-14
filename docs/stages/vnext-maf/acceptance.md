# vNext MAF v2 实施验收状态

状态：in-progress；日期：2026-09-13。代码起点 `1d73a767599732d9a53f81ad2cc553f4bf11d84e`。

用户已批准实施；原始 [75条验收定义](../../vnext/ACCEPTANCE.md)中的 not_run 是导入时状态，不能当作当前代码结果。实际执行证据将在本阶段按任务、命令和被测提交追加。此时没有产品通过结论。

2026-09-13 最新进度审核以代码 `6f6892a` 为截面，见[审核与后续安排](progress-audit-2026-09-13.md)。本次只核对既有记录，不重跑测试；下表区分历史切片通过、最新局部实测和完整产品未覆盖项。

该次定向审核发现：P08 reject 虽满足原调用拒绝零执行与两代恢复断言，最终 P04 回执却为 `rejected / INVALID_SCHEMA`，测试未检查结果接纳。该历史发现现已有A1修正和实测，见下文更新；审核原文不改写。`6f6892a` 的退出撤销SQL已通过A2增量升级与定向守卫检查，完整P08仍未验收。

用户认可下一批计划后的实际更新：

- A1：问题来自合成模型的拒绝最终正文不符合AgentPayload，测试未检查结果接纳。`5233f8c`修正夹具并补持久ResultReceipt断言；[最终原输出](../../../work/p08/a1-reject-result-2/stdout.txt)为1 passed / 32.60s / exit0，仍零ToolAttempt。首轮新增检查中的SQL歧义失败保留于原目录；测试时HEAD/dirty绑定以同目录文件为准，不冒称提交后另跑。
- A2：`9a83e64`接入0015/0016增量迁移；[原输出](../../../work/p08/a2-session-writer-exit-1/stdout.txt)为6 passed / 23.60s / exit0，覆盖已知旧0014升级及精确退出撤销条件；不是新增6项真实OS退出验收。
- B1：`37aa463`移除测试中重复安装已统一迁移locator的前提；[原输出](../../../work/p11/b1-control-api-2/stdout.txt)为2 passed / 1.75s / exit0，实际PG+签名HTTP路由。前一安装冲突失败保留；这些本地结果的永久成果包尚待收口。
- C0：生产核心`3bd7d8a`/`e89dea8`、0017迁移`890b540`及SOL消费者修复`d2beac6`；Remote 7 passed / 14.81s，另2项Pod许可/receiver数据库检查通过。已有[永久原始证据、截图、HTTP/SQL与源码绑定](../../vnext/evidence/P10/runtime-adapters/README.md)，归档提交`eccc155`；严格TLS、丢ACK保持unknown、错误身份拒绝等按包内范围通过。记录型PodClient不代表K8s运行。
- C1/C2：`9d42f5e`/`708accc`完成TLS与arm64部署装配；随后 `a47e198` 修正Worker生产依赖、`3e79cb9`修正合成模型完整endpoint、`2a0c7ee`/`bc0f0f1`补齐work kind与workspace初始化、`df5c926`固定单Work容量。fresh6实际K8s链路已通过：[永久证据](../../vnext/evidence/P10/k8s-c2-20260914/README.md)，代码源 `df5c926`，Pod UID `6db41752-9826-4687-aae4-b9cf5e640632`；Reason/Explore各1项完成、4次模型200、2次Kali读取、2次accepted Run、2个sealed Artifact/Observation链和2个P04结果提交。随后通过正式cancel及 `556b8f4` stop修复完成receiver禁用、容量归零和Pod删除。范围限单一合成机制Task，不扩大为完整P08/P12或生产验收。
- A3：固定memory输入与原生compaction继续实施；`a455363`增加固定输入来源，`cfb1c2d`/`7956660`补对应wire及生成类型。实际child首次因缺wire字段在resolve失败已保留；后续真实child验证仍在进行，纯API/生成检查不替代恢复验收。

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
| P09 Scheduler 已验证切片与定向复审 | reviewed / partial；非完整 accepted | 基线 `a3f7a95eacce20cbdeeaf654ea8f86064222ba0c` 原 31 项、直接消费者 4 项、共享容量竞态 1 项；修复 `e0a10b586905ed705b0d7f520bda6f6f96b26cac` 提交前 A/B/C RED 3→GREEN 3、0010→0011 升级 1、synthetic receiver UID 复制 1。[永久证据与缺口](../../vnext/evidence/P09/README.md)、[machine index](../../vnext/evidence/P09/index.json)、[初审](../../vnext/evidence/P09/reviews/P09-review.md)和 [Dalton 独立定向复审 PASS](../../vnext/evidence/P09/reviews/P09-rereview.md)保留。其后真实 Outbox/child 的限定 Explore M2 已通过，按上行证据；P08 两代 child 输入恢复按下行局部实测。其他非知识事件、完整 failure/retry 与各 work kind 仍未全验收；旧逐查询输入缺口不追写成已有 |
| P08 会话与审批 | in-progress / runtime partial；not accepted | 后续产品/测试已至 `dd400bf`、`6f6892a`。两代真实 Node/Python child 的 approve/reject 为 2 passed / 60.37s / exit 0，运行时 HEAD=`dd400bf` 加保存的 diff，随后提交 `6f6892a`；旧混合 cold 批 5 项与权限 3 项分别保留原范围。真实0014/native boundary已有局部结果。见[本地原始入口与缺口](progress-audit-2026-09-13.md)：压缩、真实 child 记忆、原子失败、并发/CAS/旧 writer、半发布/GC、旧批准控制边界等尚待收口；候选未发布 verified。`f4c3b76` [历史四残留复审](../../vnext/evidence/P08/reviews/P08-platform-rereview.md)不代表最新源码结论，也不能被两项成功路径整体关闭；最新证据仍待永久归档 |
| P11 控制 API 与恢复集成 | runtime partial；not accepted | `64f4c29`审批路由已被P08真实HTTP消费；`f6cad17` Task/Work command API与受限Work locator已通过后续A2统一迁移/B1两项真实PG+签名HTTP路由检查，见本页更新。正式创建/项目权限/浏览器身份、完整hold/pause/cancel恢复与失败域集成待完成 |
| P12 可信完成 | not implemented / not accepted | 已有冻结合同与前置服务；可信 precheck、quiescing/settlement、ReportCommit/Delivery 与实际完成协议尚未交付。P10真实退出与P04结果接纳均不替代Task完成 |
| P10—P12 完整机制验收 | partial / not accepted | 真实 Outbox/child 限定 M2 与 fresh6 K8s Explore 切片已通过；完整控制/恢复/可信完成、浏览器入口、其他 work kind 与部署故障矩阵仍待实际集成，不扩大已有切片结论 |
| P13 受权图投影与持久视图 | backend reviewed / M4 partial | core `3015ca6`、P04 port `592bed2`、0012迁移与测试 `44ddc68` 的[真实结果](../../vnext/evidence/P13/runtime-green/report.md)为 12 项通过。独立审查发现的两项 P2 已在 `69e3a1d` 修复，[定向证据](../../vnext/evidence/P13/review-fix/report.md)为 3 项 / 3.16s、生成检查、22 组 HTTP 与截图；[独立复审](../../vnext/evidence/P13/reviews/P13-rereview.md)关闭两项，[完整证据入口](../../vnext/evidence/P13/README.md)。原 12 项及 pure builder 9项未重跑。Layout、ViewStream、P14正式容器与后续P12类型仍未验收，故不标 M4 全过 |
| P14 TopologyFlowCanvas fixed DTO slice | reviewed / partial | 原代码 `9a1c8e20ccd57b19e74d748129a3d5d524eab6f4`，修复代码 `bd3111a62a624aa5acef7d167ffe96b18747934a`，证据 `64bbdf2974b39856a2cb29dd1eee97cb1a70ca93`；[实施与截图](../../../tests/topology/report.md)、[修复证据](../../../tests/topology/review-fix-report.md)、[初审归档](../../../tests/topology/P14-review.md)与[PASS 复审](../../../tests/topology/P14-rereview.md)固定实际范围。16 Vitest、2 个受影响 Chromium 用例及 web typecheck 通过；复用原五主题截图。真实 P13 API/Auth、Layout CAS、ViewStream、记录详情与规模 p95 仍 pending/not_run，不是 M4 闭环 |
| P15—P20 开发和机制验收 | not_run | 按依赖执行，未验证不标通过 |
| 真实模型效果 | not_run | 需明确模型/数据及新增 USD 额度 |
| 生产切换/旧数据删除 | not_run | 需独立明确授权；开发不隐式实施 |

运行中仅用自建夹具；HTTP/UI成果提供完整交互及截图，离线记录按其原生媒介保留。自行检查与代理审查如实区分；不宣称第三方认证。P13 纯片由主代理委派的 SOL/xhigh 执行，不冒称主代理独立测试。记录文档的提交与被测代码提交分开。

本次 P07/P14 状态更新仅修正实施状态文档的落点，复用上述已绑定代码、测试、截图与审查证据，不重跑验证。导入源包 `docs/vnext/ACCEPTANCE.md` 保持原始字节。

P01 永久证据由 Wuji vNext P01 文档维护，位于 [docs/vnext/evidence/P01](../../vnext/evidence/P01/relocation.json)，不放入可清理的 SDD scratch。当前 [CapabilityRecord](../../vnext/capability-record.json) 与 [实际截图来源](../../vnext/evidence/P01/screenshots/provenance.json) 已发布；原缺图/初审状态与旧运行结果按原样归档，不追写历史通过结论。
