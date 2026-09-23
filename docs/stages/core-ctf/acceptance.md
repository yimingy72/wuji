# Core CTF 验收定义与当前状态

日期：2026-09-22；更新至2026-09-24。开发状态：in-progress。**独立本地 synthetic 机制主链 b18 已通过；C01—C08 完整验收仍未 accepted，真实模型CTF为 not_run。**
用户授权整体讨论后实施，Astra/high完成审查，Sol/xhigh开始核心调度及上下文切片。不把代码在写、子Agent意见或JSON结构检查当作产品通过。业务基准 `3682eda`，未来实际被测提交和镜像另记。

## 1. 八组必要验收

| ID | 实际场景 | 必须看到的结果 | 当前 |
| --- | --- | --- | --- |
| C01 | 真实MAF原生MCP调用exec；登记后丢一次回复并重连 | 正常未篡改执行器下稳定identity/handle，针对同一平台调用的传输重发仅一次spawn；同键异参拒绝；不双扣额度 | 局部：b18 exec/read 主链通过；丢回复/重连未做完整Task验收 |
| C02 | 长进程输出、stdin、读cursor、停止；Task取消与额度耗尽 | 字节连续有界；未知输入不重投；正常执行器的进程报告与外部Task终止分开核对；取消后exec/input拒绝且平台stop仍可用 | 局部：b18 命令和外部停止通过；stdin/额度边界未覆盖 |
| C03 | Kali root能力/挂载检查；伪造本地receipt；独立Task handle | Kali UID0但dropALL；没有平台共享bearer/collector/数据库/模型凭据；本地报告不能直接写账本或伪造平台准入/发送/Runtime终止事实，只作为executor_reported观察保存；跨Task拒绝；init失败不启动 | 局部：先前隔离能力检查通过；完整Task权限矩阵未覆盖 |
| C04 | curl与Python通过代理访问自建HTTP/TLS；有限二进制/压缩/重复头 | 请求与响应实体长度/hash一致；协议如实记录；明文Artifact与PCAP可下载；H2只在实际验证后纳入 | 局部：b18 Python HTTP 两交换、明文及PCAP通过；协议矩阵未覆盖 |
| C05 | 清代理直连、未支持协议；capture退出及writer存储失败；在途连接 | 不悄悄旁路；现有代理连接收敛，Task停止/核对；受影响证据partial/unknown；正常封口与故障窗口区别明确 | 局部：b17 故障自动撤权、b18 正常封口实测；完整故障矩阵未覆盖 |
| C06 | A生成脚本发布，B读取manifest并装载运行；重复发布与改缓存 | 同操作同publication；副本修改生成新版本；并发CAS一胜一冲突不丢工作副本；sealed旧版不变；publication ACL正确；B实际文件hash和来源可核对；新材料真实handoff | 局部：b18 A→B固定版本与结果通过；多版本并发CAS仍按定向PG证据单列 |
| C07 | 运行中发布发现、后继问题、已有后台exec、跨attempt材料恢复 | 不重复工作/不按token唤醒Reason；WorkResult有效依据进入brief；父exec未结算不done；旧workspace Session不自动续跑 | 局部：b18 Reason→A/B及Claim/结果消费通过；跨attempt/通知全边界未覆盖 |
| C08 | 正式工作台新Task → 显式start → 双Agent交接 → 结果/证据 → cancel/finish | 创建后零执行；机制链实际通过；真实模型/CTF单独列结果；进程与采集清理真实完成或保留unknown | 局部：b18 synthetic主链、capture sealed、外部四终态及三页只读浏览器通过；完整前端/业务close与真实CTF未通过 |

D-NET已选严格受支持HTTP(S)明文，原始扫描/基础probe后置。不以PCAP密文留存通过明文验收。

C07同时覆盖全局链路：Task配置的并发真实生效（测试可用2及4，产品不固定2）、一个活动Reason与多个Explore可共存；A执行中发布发现，A未结束时B在下一模型边界已收到更新提示并能按固定引用读取；无Claim负结果终态/有效用户输入能唤醒Reason。C06/C07同时核对新旧WorkResult reader、冻结snapshot→后继Brief、同一snapshot重复resolve一致。

C08增加用户最新前端与登录要求：账号密码登录；两个浏览器并存、单独退出及服务重启后会话保持；概览/活动/工作区/发现证据可用，默认不堆内部诊断；任务切换不串记录，停止中不假称已停止。参考平台浏览只是设计研究，不计Wuji验收通过。

## 2. 证据与判定

- 每组实际成果包含对应目录 `screenshots/` 的真实终端/浏览器/接口验证截图，并在记录中引用。
- HTTP/MCP成果保存完整方法、URL、headers、请求体、响应状态/headers/body；不得用省略号代替关键字节。敏感材料受限存放，普通报告脱敏并说明影响。
- PCAP保存段manifest、hash/长度、接口/时间/丢包与完整性；HTTP2输出标为协议语义表示，不伪装HTTP1原始线上字节。
- 命令开始/退出属于执行端报告，明确来源可信度；Task实际终止由外部Runtime观察。API202、kill请求、Kali自报或Pod删除受理都不是Task停止证明。
- A/B交接保存源脚本、manifest、canonical Claim/Intent引用、B所用文件摘要和执行结果；模型自述不是验证。
- 记录代码SHA、dirty摘要（若有）、镜像digest、迁移head、Profile、执行者、命令、退出码、失败历史。后续记录提交不能冒称新代码实测。

## 3. 最小命令入口（实施后才成立）

这些是Plan拟新增文件对应的早期示例；机制driver后来已实际运行，前两条文件名不作为当前检查入口。实际b18命令与退出码见§7及原始报告：

```sh
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_core_process.py tests/vnext/test_workspace_bundle.py -q
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_core_capture.py -q
./scripts/vnext/uv.sh run --frozen python tests/vnext/run_core_ctf.py --mode mechanism --run-file ABSOLUTE_PRIVATE_RUN_FILE
```

真实模式必须另核对有效目标/数据/模型/金额许可，命令不含密钥。没有该许可不自动运行；保留mechanism结果并将real列为not_run。

## 4. 性能和效果范围

首批只记录：Task/Run排队与就绪、模型耗时/token/费用、工具时间、平台交接时间、发布到B可读时间、采集写入开销、重复问题与成功判据。先得基线，再优化实际瓶颈，不设未经测量的性能SLA或承诺提速比例。

对照单Agent与双Agent时固定模型、题目版本、工具、环境、授权和额度；题目答案/验证器不进入Agent上下文。预先固定小题集，完成即停，不反复换题直到出现成功。

## 5. 通过条件

C01—C07及C08机制链的关键项通过，才可称本阶段核心开发交付。真实CTF另记success/failed/not_run及原因。正常主链路不得存在未解释采集缺口、未结算unknown、错误跨Task访问、传输重发导致的重复spawn或证据丢失。故障场景以正确关断、标记partial/unknown并保留已取得证据为通过条件；不能把故障交易写成complete。

初稿完成时只检查了文档链接、字段来源、围栏和版本表述；2026-09-23后实际运行结果见下文§7。

## 6. 实施进度：局部代码检查，不替代C01—C08

以下为2026-09-23早期代码开发截面：当时基准HEAD为`3682eda`，改动未提交或部署。后续真实部署与验收以§7为准，不把旧状态冒称当前。

| 切片 | 当时结果（2026-09-23早期） | 当时检查/证据及后续边界 |
| --- | --- | --- |
| Task并发配置与CTF入口 | 代码已写；0036追加迁移、旧payload省略语义、冻结instructions及UI字段 | 定向PG3项、context1项、合同生成检查、Web build通过；`work/core-ctf-test-evidence/task-configuration/`。未做运行库升级/浏览器走查 |
| WorkResult与后继上下文 | 代码已写；有效引用投影、snapshot冻结与ACL、Brief消费、旧context重放 | 纯逻辑3项；最终PG1项通过，`work/core-ctf-test-evidence/context-results/db-work-result-snapshot-final.txt`。尚未做真实双Agent/MCP交接 |
| 调度容量与触发 | 代码已写；配置上限、终态/input触发与无进展窗口 | 主代理最终角色/未结算槽3实例通过，`work/core-ctf-test-evidence/scheduler-slice/main-final-role-check.txt`；其他定向结果与失败历史在同目录 |
| 增量Claim增强用例 | 当时待测；后续b18已实际board_publish，专门增量边界仍待测 | 当时最后一次测试在未登记collector attempt的夹具设置处`FORBIDDEN_COLLECTOR`，未进入增量逻辑；`main-final-claim-check.txt`。该失败保留；后续真实board_publish联合用例与b18主链另见§7，模型产物不应计外部新证据的边界不因b18自动通过 |
| 密码登录 | 当时代码已写，尚未部署或设置实际用户凭据；后续独立Core已部署 | 登录/多浏览器/单会话退出/重建及旧模式等7项、CLI1项和Web build通过；loopback HTTP与持久PVC的集成修正3项通过。原始记录`work/core-ctf-test-evidence/local-password/`；b18实际登录只作为机制入口，不替代完整C08会话矩阵 |
| 运行中通知/board_publish | 实施中，框架通知接缝已局部验证 | 真实MAF框架的三轮mock stream通过：发布后下一模型边界获metadata、显式read后才获正文；失败不持久推进游标。原始记录`work/core-ctf-test-evidence/context-results/native-notice-middleware-final.txt`。PG联合节点在准备链修复后仍因旧Profile与native delivery通道不匹配失败，最终native配置调整尚未重跑；`db-notifications-node-final.txt`保留失败，不记C07通过 |
| 任务概览/活动读视图与工作台 | 当时接口局部检查与前端构建通过、尚未部署；后续独立Core已部署 | PG与HTTP定向1项通过，覆盖Task权限、stale判据、真实预算、活动投影与分页/筛选；`work/core-ctf-test-evidence/task-workbench/task-read-views-db-final.txt`。概览/活动/工作区/发现页签、技术信息折叠、任务切换与独立请求、记录下钻已接线，Web build通过见同目录`web-build.txt`。同目录保留launch读取权限和SQL JOIN两次失败及修复过程；b18三页浏览器截图见§7，其余浏览器下钻未覆盖 |
| M2a独立capture | HTTP/TLS、拒绝路径与Linux采集组件局部验证通过 | `work/core-ctf-test-evidence/capture/local-http-tls-final.txt`为3项通过；Linux镜像`sha256:c559bd5af0a216c638524e964c86c7b7a7c1302f8f1e9912e261c63fef7059ed`，运行记录`full-image-runtime-r2.txt`。报告`capture/report.md`含完整请求响应与`screenshots/capture-verification.png`。该证据不包含Task UID出口强制、mTLS拉取入库及完整停止；统计采样/丢包关断后续修正也不冒称被旧镜像覆盖 |
| M1原生MCP与进程归档 | 当时无DB工具语义与PG主链局部通过 | `work/evidence/core-ctf-m1-20260923/no-db-tests.log`为9项通过；`process-pg-autofinalize.log`为单节点通过。真实native MCP→签名HTTPS Kali→单spawn重放→后台watch自主归档，得到accepted EvidenceReceipt、sealed command-log，父exec为exited。旧诊断版直接finalizer日志不替代自主路径；后续b18在真实Task Pod内完成MCP/Kali与取消终态，范围见§7 |
| Kubernetes终止机制 | 独立三容器Pod探针通过 | `work/core-ctf-test-evidence/runtime-deadline/`记录docker-desktop v1.36.1下UID/resourceVersion条件patch，将activeDeadlineSeconds 600→1；同UID三个容器均terminated、Pod对象保留，后清理临时namespace。仅证明该K8s机制，不替代Wuji停止编排/终态持久化 |
| M2b UID网络与抓包能力 | 当时Docker共享netns机制通过、Task Pod装配未验收 | `work/core-ctf-test-evidence/runtime-netns/report.md`含截图、完整HTTP/TLS字节及规则/进程capability记录。capture `sha256:b6302759dd0f0b4a79f52699a1cbde9cfb621d0fafb18655cfc1fa875fbb8647`；Kali `sha256:a8779183fa81b73089e7e5a7cfc3b0fb3cc373c59250e5d929916eb3cd477fcc`。代理TLS成功、IPv4/IPv6直连拒绝；tcpdump独得NET_RAW、Kali与其他capture进程无有效cap。后续b18已有真实Task Pod、mTLS采集拉取与Runtime终态证据，不能把当时镜像digest冒称b18版本 |
| M3脚本发布/装载/CAS | 当时已落盘、联合节点未通过；后续定向PG节点1 passed，b18固定版本交接通过 | `context-results/workspace-bundle-a-to-b-node-v1.txt`缺少fixture角色限额；v2进入真实Scheduler后被旧工具能力白名单拒绝，这两次失败保留为当时结果。后续`test_workspace_bundles.py::test_workspace_bundle_a_to_b_fixed_version_materialize_and_cas`定向PG 1 passed（6.62秒），b18在真实Task完成A发布→B装载/执行并保存manifest与文件hash；C06全部CAS/权限矩阵仍未accepted |
| 有界知识/采集合同及读取接缝 | 当时无DB局部检查通过、PG联合检查待完成；后续定向PG及b18见§7 | `work/core-ctf-test-evidence/context-results/context-m2c-no-db-final-v1.txt`记录合同生成一致、路由集合、process metadata-only、required-only query及采集材料renderer等13项通过。该次无DB检查时，capture PG节点曾停在fixture控制权限前置；后续结果见下一行。`runtime-capture-pg-attempts-v1.txt`是失败过程摘要，数据库/身份原始事件在同目录`b15098c4895b/`。该记录本身不覆盖有界snapshot容量、累计计数或terminal的PG验证。 |
| 2026-09-23核心PG联合窗口 | 当时capture节点通过、其余3项未通过；后续分批修复/定向通过 | `context-results/core-four-pg-final-v1.txt`四项共同阻断于新增0040重复CREATE FUNCTION，未进业务；迁移已改为append-only replacement。`core-four-pg-final-v2.txt`中capture节点通过，覆盖gap真实Artifact、固定引用重放、累计计数与无receiver/撤权后终态。当时M3/容量受执行校验与replay错误列阻断，通知夹具时序不符；后续M3、容量和通知定向节点及b18实测见下一行与§7，旧失败不改写成通过 |
| 2026-09-23后继定向核对 | 当时capture终态helper、容量ContextV4与F3读视图局部通过；M3/通知尚待后测 | 本轮pytest工具transcript中，真实capture节点1项通过，覆盖完整四容器终态缺项阻断/齐全放行及累计水位；1001 items ContextV4节点1项通过。`test_task_read_views.py::test_task_overview_and_activity_are_acl_scoped_and_cursor_bound`扩展后1项通过，覆盖命令分页、读权限与空publication；合同生成`--check`一致。本轮stdout未另存文件，不用前轮日志冒充。当时M3停在测试RootModel断言、通知夹具UPDATE 0；后续M3与隔离PG通知节点各1 passed，b18真实A/B及非空共享版本见§7，C07全边界仍未accepted。 |
| 独立Core平台与密码Web装配 | 当时renderer局部检查通过、未部署；后续独立Core 8/8 Ready | `work/core-ctf-test-evidence/platform-web/renderer-web.log` 7项通过，覆盖独立namespace、共享RunCredential加密key、Runtime 8MiB传输边界、capture CA路径、账号密码BFF、持久会话PVC与旧web默认兼容。入口要求6类固定镜像及私有scrypt文件；后续b18实际浏览器和Task结果见§7 |
| 2026-09-23 Runtime/F3收口 | 当时代码冻结待联合部署；后续b18真实driver通过 | GPT-6 Sol/high接续后报告Runtime定向10项、BFF新增读路由1项、capture HTTP摘要1项、web build及最终typecheck通过；stdout仅工具记录。已接命令/版本/HTTP/PCAP分页与真实容器停止投影。当时主代理driver终态绑定/敏感头隐藏1项通过，原日志`work/core-ctf-test-evidence/mechanism-driver/pure-check.log`；后续b18真实driver退出0、三页浏览器截图见§7，其他页面未完整验收。renderer显式容量传参1项通过，`platform-web/renderer-capacity.log` |
| 2026-09-23 F4采集材料路由 | 独立Core浏览器局部通过；b18主链后来通过，C08全项仍未accepted | `75cfbd0` Web镜像实际digest `sha256:fd1ee55febf8ad42dc0873e35dbfcff4fa1a6fc9a95f989aee4e197df0ff1896`；Docker内typecheck/Vite build、core-web rollout/Ready通过。既有b6 Task的912B manifest `omitted+source`预览正常、原文下载SHA匹配；20,411,486B PCAP从材料页定位到对应采集原件item。实际页面截图、完整私有HTTP报文及原始响应见`work/core-ctf/local-20260923/evidence-f4/route-75cfbd0/report.md`。该轮未重复执行Task控制、旧登录用例或机制driver；b18本Task三页浏览器截图另见§7 |
| 通用MCP/Kali、capture、共享脚本版本、任务详情整体改造 | b18 synthetic机制主链通过；完整验收仍分阶段推进 | C01—C08现为§1所列局部结果，完整组尚未accepted；真实模型/外部CTF仍not_run，不因单条主链把全部边界标通过 |

上表保留早期局部验证及失败的历史截面，M2a已有相应截图和请求包；当前完整Task synthetic联合链证据见§7，C01—C08完整验收仍未accepted。参考平台产品研究不是本平台测试成果。

## 7. 2026-09-23 独立 Core synthetic 机制实测

在独立`wuji-core-ctf`创建新Task `c29071ad-d332-435d-9ee3-6586f0e98ed6`（b18），固定 synthetic 模型与自建目标、非破坏性范围。driver实际退出码0，[完整私有报告与原始证据](../../../work/core-ctf/local-20260923/evidence-b18/report.md)保留了固定输入、全部HTTP请求响应、两条完整目标请求包、A/B清单与文件、三份命令记录、两条HTTP明文、PCAP、最终采集manifest及四容器终态；[执行停止截图](../../../work/core-ctf/local-20260923/evidence-b18/screenshots/b18-overview-stopped.png)、[活动截图](../../../work/core-ctf/local-20260923/evidence-b18/screenshots/b18-activity.png)、[共享版本截图](../../../work/core-ctf/local-20260923/evidence-b18/screenshots/b18-publications.png)是同Task实际浏览器渲染。前端命令/网络采集/发现页签只拿到API记录，浏览器下钻截图未完成，不记C08完整通过。

本轮platform镜像来源`cc5ca31`，capture来源`8e89607`，agent/kali来源`f0eed7e`，Web来源`75cfbd0`；各角色实际digest在报告固定输入中。A/B两个Work及对应Claim、版本化脚本/结果、Kali MCP命令、同一capture session两条完整HTTP exchange + 7,593,624B PCAP + final manifest均有原始证据。driver在机制核对后正式cancel，Runtime同attempt/UID的init、agent、kali、capture四终态均terminated，采集批次sealed。Task业务仍`cancel/quiescing`、`completion_epoch_id=null`、`result_outcome=null`：取消撤权与外部停止已验证，P12完成审查/close不是本次driver自动执行的动作，故不记`closed`或Goal满足。

历史b17 Task因capture status控制请求超时由Runtime自动fail-closed撤权，平台capture session保持failed；只读PVC发现第二条HTTP已由Sidecar写盘但未入库。根因是采集索引候选唯一key被摘要字段循环覆盖，第二条候选无法推进水位并持锁；`8e89607`只修该变量，定向两交换/late gap/重复refresh节点1 passed（0.41秒），b18新Task实测连续入库两条HTTP。不追认b17为通过。真实模型/外部CTF与C01—C08剩余矩阵均未运行；阶段仍in-progress。
