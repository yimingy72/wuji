# vNext v2 实施决定

日期：2026-09-13。用户已明确要求按本目录对应下载包的 Spec/Plan 进入重构；本文补充实际代码落点，不修改原始包的历史报告、版本或摘要。

| ID | 决定与依据 | 若判断不合适的代价 |
| --- | --- | --- |
| D01 | 本轮执行 v2 `SPEC.md` / `PLAN.md`，不继承旧 v1 已准备的任务编号、Fact 独立正文或事件水位。隔离树中原三份文档与 `source/V1_*` 相同，已逐字节保留 | 仅后续用户新决定会改变此基线 |
| D02 | 沿用已存在的 `codex/vnext-maf` 工作树；主目录旧草案和旧部署不动。旧 `.superpowers/sdd/PLAN` 属 v1，本轮使用独立 `vnext-v2` 台账 | 两套历史准备记录需要区分，避免重复或遗漏任务 |
| D03 | 用户明确实施请求已提供开发授权；不因源包日期仍写 review 而要求重新批准。付费目标模型、停机/切换、数据删除和推送仍按 Spec S01/S16 单独处理 | 业务代码可完成，实际运维切换仍等待明确许可 |
| D04 | P01 隔离新 Python 依赖和冻结 lock，不让新测试环境解析旧 Cairn/Pi workspace。使用实际可用 Python/uv，精确组合写 capability-record；对 Plan 的根 uv 命令以新项目包装实现 | 必要的工具入口增加，但旧运行工具链不变化 |
| D05 | P02 的 OpenAPI v2 是外部 wire schema 单一来源；生成 Python/TS DTO，领域 contracts 模块重导出或增加内部行为，不维护第二套 wire 定义 | 若生成库不满足严格输入要求，需要调整生成配置/入口校验，而非放宽合同 |
| D06 | 计划各任务关联的 AC 包括后续集成才能验证的路径。局部任务只登记已实现且实测部分，最终 AC 由完整所需证据汇总；不因纯函数用例通过标记端到端完成 | 局部完成与完整 Gate 状态须明确分开 |
| D07 | `check_all.sh` 在 P17 建立集成入口、P20 增加发布清单并核验；解决 P17 最终 prose 与 P20 文件列表的交叉归属 | 多一次明确的串行文件交接 |
| D08 | 新 API 入口保持与旧 API 启动和依赖隔离，可复用经核验的独立模块；不得通过导入旧主 app 拉起 Cairn 服务。P02/P03先提供实际路由测试底座，后续任务添加行为 | 少量适配入口代码，旧兼容与新独立启动分别验收 |
| D09 | 产品 DeliveryProfile 按 v2 S15/AC-069 的证据媒介要求实现；开发验收对实际 HTTP/UI 路径保留完整交换与截图，纯离线材料保留原生字节/摘要/定位，不伪造不适用 HTTP | 若未来用户要求更严格交付，调整对应 Profile，不篡改原始证据 |
| D10 | 用户后续明确：修复、测试、验证、代码复核和轻量重复工作统一使用 `gpt-5.6-sol/xhigh`，核心功能开发或重大复杂问题才使用 `gpt-6-astra/xhigh`。常规失败不自动升级；保留主代理架构与集成职责，交接复用已有证据 | 核心开发与验证有明确交接，不为模型切换重跑或改写历史执行者 |
| D11 | 采纳用户补充材料中经主代理裁定的交付组织：保持 P00–P20、架构和 75 AC 编号不变，以 M0–M5 组织可运行交付；补入 checkpoint 已纳入操作/原生消息与持久模型/工具回执的操作前沿核对；区分工程验证的原生证据媒介与客户安全成果既有截图/完整 HTTP 包要求；用六类既有合同交接索引承接，不新建框架或平行事实源。原文件作为 review reference 原字节归档，摘要与详细映射见[交付里程碑](delivery-milestones.md) | M0 先关闭 P06 最终消费者与公开交接，M1 先证明最小真实闭环；后续里程碑不能被当作新增 AC、付费试验、部署授权或已完成状态 |
| D12 | P08 首次真实机制验证采用受限部署 owner 登记的 mechanism_candidate，与 verified 能力状态明确区分；固定 Task/receiver/版本/有效期、不可变 mechanism_synthetic 定义、loopback 合成模型与 fixture workspace_read 工具；所有真实执行/恢复/事务守卫保留。详见[P08 合同](P08-implementation-contract.md) | 避免“必须先有本次 PASS 才能做首次验证”的循环；候选不是已验证证明、生产发布或收费/外部目标许可，通过后以新正式 ref/digest 收口 |
| D13 | 按用户审核后要求准备[下一批执行单](../stages/vnext-maf/next-batch-plan.md)：P08修复、P11控制/正式入口和本地K8s装配并行；0014冻结当前定义、0015保持control、0016增量修复，共享迁移单一写入。K8s补真实P05→Pod→receiver和Gate→Kali受控executor接线，保持双容器卷隔离、HTTPS与D12 loopback限制 | 集群可用无需等待后期，但缺失的产品接线不能用fixture或共享挂载冒充；新增核心端口先固定合同，部署/修复/验证使用SOL，核心开发才按需GPT-6。计划准备不构成新测试通过 |
| D14 | 2026-09-15 本地K8s首个浏览器读取入口采用同Pod BFF：浏览器只持有HttpOnly、SameSite=Strict短会话，BFF按请求签发不超过60秒的内部Bearer，并只代理固定Task的topology/snapshots/records GET。签名键和会话键仅在K8s Secret，前端配置不含Bearer；公开P13 API保持独立Deployment。该适配只用于本地机制工作台，生产OIDC、项目选择和写命令仍按P11/P15完成 | 先获得可审查的真实浏览器路径，同时避免把临时operator token放入JS或浏览器存储；后续正式身份可替换BFF登录来源而不改P13权限检查 |
| D15 | 2026-09-15 当前下一项冻结为[P15-L Layout CAS垂直切片](../stages/vnext-maf/next-development-plan-2026-09-15.md)：先补齐LayoutPreference GET、viewport wire、0018个人偏好持久化、If-Match CAS、受权node identity校验及K8s浏览器刷新/冲突证据。布局只需当前Task读权，不产生领域事件。完成后先收口P08 Session、P11正式控制和P12可信完成，再实现ViewStream | 当前读工作台已有完整前置且Layout切片范围独立；先实现ViewStream会围绕尚未稳定的控制/完成事件重复调整。OpenAPI现状缺GET和viewport，若不先修合同将无法真实证明刷新保留布局 |
| D16 | 2026-09-15 本地浏览器入口由`Service/wuji-web`的Docker Desktop Kubernetes `LoadBalancer`直接暴露`localhost:44180`，替换需要常驻宿主机进程的port-forward。Wuji业务Pod仍使用节点可达的Docker VM loopback registry拉取不可变摘要镜像；该registry属于构建/分发基础设施，不冒称K8s业务组件。空的旧`wuji-vnext-registry`只登记为待清理，不在本次删除 | 消除终端退出导致工作台失联；把应用运行平面与集群启动前就必须存在的镜像分发平面明确分开，避免把ClusterIP registry误当作节点可拉取地址或形成自举循环 |

21 项任务及共享接口逐项检查表在本工作树的忽略台账 `.superpowers/sdd/vnext-v2/preflight.md`，任务完成以提交、具体测试和审查记录为准。源包 `ACCEPTANCE.md` / `VALIDATION_REPORT.md` 保持原始文档检查事实；实施结果另记，不覆盖原包。

常规实现和修复按批准范围连续推进。必要权限、恢复或真实 MAF 核心能力不满足时，记录实际失败与合同影响，不通过削弱测试或更换框架来宣称通过。
