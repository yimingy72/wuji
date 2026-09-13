# 下一批开发执行单

2026-09-13；状态：用户已认可，in-progress。从计划提交 `1bf066a` 开始本批实施，结果以实际验收记录为准。属于已批准 vNext P08/P10/P11 和后续消费者的实施安排，不另立阶段、不新增 AC。

代码准备基线：`codex/vnext-maf@15aa6cdbc1ab1b22040ea7c3fa5dcb8a37562cd9`，工作树 `work/worktrees/vnext-maf`。基线无 tracked dirty，既有未跟踪资料保留。依据：[Spec](../../vnext/SPEC.md) S09–S11、[Plan](../../vnext/PLAN.md) P08/P10/P11、[当前验收](acceptance.md)、[进度审核](progress-audit-2026-09-13.md)、[P08合同](../../vnext/P08-implementation-contract.md)和[P10合同](../../vnext/P10-implementation-contract.md)。用户已要求停止 Superpowers，修复/验证使用 SOL xhigh，并明确本地 K8s 可部署测试。

## 本批目标与顺序

先交付三个可检查结果：**拒绝恢复后有符合合同的最终结果；Task/Work控制命令通过实际授权接口；新链路在本地K8s的真实Task Pod中跑通一次受控执行。** 随后继续完整会话能力和正式任务创建/浏览器身份，承接 P12 可信完成。K8s装配立即并行准备，部署已有切片不等待完整P08或UI。

执行顺序为：A1、B1源码准备、C0核心接线与C1镜像装配并行 → A2统一迁移 → B1实际控制验证；C0/C1齐备后C2部署串行占用共享资源 → A3完整Session组合、B2正式入口与C3部署消费者继续。具体依赖见表；不把所有独立源码工作串行化。

| 工作 | 负责人及模型 | 生产/测试写入范围 | 依赖与验收出口 |
| --- | --- | --- | --- |
| A1：修正reject结果出口 | Dewey，SOL xhigh | `tests/vnext/test_session_approval.py`、`tests/vnext/support/p08.py`；只有原始trace证明是生产转换问题才修改对应 `packages/maf-worker/src/wuji_maf_worker/` 文件，先注明具体文件；P04接纳规则保持原合同 | 从现有 `INVALID_SCHEMA` 的原始payload/receipt定位，不重跑来“重新发现”。新增最终ResultReceipt和持久结果断言；合法拒绝结论被接纳，原调用仍零ToolAttempt。测试先只执行该reject用例，生产变化涉及approve才复测approve |
| A2：迁移与退出撤销守卫 | Dewey，SOL xhigh；共享迁移唯一写入人 | `wuji_core/persistence/schema.py`、现有 `control_api_schema.py`、新增 `session_writer_exit_schema.py`；相应定向迁移/权限测试 | 保留0015给控制locator，预留0016给退出撤销修复。fresh和已知旧0014都能到同一实际schema；错误receiver、错Session/input、未settled不会误撤销。证据保留旧行/角色/权限，不能用删库冒充升级 |
| B1：Task/Work控制API | 主代理集成，SOL xhigh执行及修复；实施槽与A2错开 | 已有 `execution/control_api.py`、`http/commands.py`、`tests/vnext/test_control_integration.py`；共享 `execution/control.py` 变更先与Dewey按具体函数分配 | 复用既有ControlService，A2完成后执行现有两项真实PG/HTTP检查。覆盖start、hold、pause/resume不解除hold、幂等/版本与权限；取消回执和真实进程退出分别观察，进一步进程消费者由C2/C3承接 |
| C0：vNext到Task Pod及Kali的核心接线 | 主代理定接口；需要新核心实现时GPT-6 xhigh，验证/修复SOL xhigh | 新增 `wuji_core/execution/pod_runtime.py`、`wuji_core/admission/remote_workspace.py`、`services/wuji-kali-executor/main.py`；`packages/task-runtime/src/wuji_task_runtime/` 仅必要独立兼容改动。相应测试归SOL；不改C1的镜像/factory或A2迁移 | 实际P05许可/受管lease→TaskRuntimeController→真实PodUID→P09 receiver；真实ToolPermit→Kali只读executor→原始字节/回执→P03。现有新runtime未调用Pod基础库，Gate也未连接Kali，不能把这两项当现成配置。共享DB字段需求交A2；C0代码完整后由C2部署验证 |
| C1/C2：本地K8s装配与首条执行 | Bacon，SOL xhigh；重大架构问题由主代理裁定，普通构建/网络失败不升级模型 | 新增 `ops/vnext/images/`、`ops/vnext/kubernetes/`、`scripts/vnext/k8s.py`、`services/wuji-runtime/deployment.py`、`services/wuji-scheduler/deployment.py`、`services/maf-supervisor/deployment.mjs`、`tests/vnext/test_k8s_runtime.py`；现有service main的配置/TLS参数允许窄修改，核心状态机和共享迁移不归C | C1可立即准备；C2使用A2固定schema与已提交镜像。真实Scheduler/Outbox→Pod内Node→Python child→Gate工具→P03/P04→退出；记录实际PodUID/PID/birth/镜像摘要。先证明已有Explore切片，不把其他kind标成已验证 |
| A3：P08目标组合收口 | Dewey，SOL xhigh；确需新增复杂原生适配时主代理分出GPT-6 xhigh核心任务 | P08既有session/history/approval生产文件及直接测试；SQL继续A2统一归属 | A1/A2之后，完成固定版本memory、真实native compaction与child恢复。再按AC-038/039/041/042/043/066补半发布、单写/CAS/lock、原子回滚、旧批准失效、GC与前沿反例。已过路径仅在受影响时复测；完整前提满足才新建immutable verified capability |
| B2：正式任务创建与浏览器身份 | 主代理固定合同；新核心实现按需GPT-6 xhigh，所有检查/常规修复SOL xhigh | 拟新增 `wuji_core/tasks/`、`http/tasks.py`、独立新API装配；旧身份能力仅提取独立模块复用。OpenAPI/生成DTO由主代理单一归属，迁移由Dewey写入 | B1后进入实现；先完成下述三个合同决定的具体wire/schema，再写消费者。交付真实非运行TaskCreate、当前项目创建权限、初始TaskACL、实际浏览器身份及start，不用测试token注入冒充登录 |
| C3：K8s恢复/控制消费者 | Bacon，SOL xhigh | C线部署/测试文件，按固定SHA升级自己管理的测试资源 | 消费A3/B2已经提交的功能，验证需要跨进程/跨Pod观察的直接路径；不重跑完整宿主矩阵，不把单纯PodRunning当验收 |

以上 `wuji_core/` 相对路径均位于 `packages/wuji-core/src/wuji_core/`。Dewey为现有代理 `01a099b6-d3fe-7f12-96c7-7e6031fa5a05`，Bacon为 `01a099f0-235d-7023-b8d8-be3b88b5e834`；本次仅准备，未要求其开始写码或部署。C0/B2核心代理在实际开工时创建，避免空闲代理占上下文；独立文件可并行，不为相邻依赖创建额外交接。B1由SOL顺序承接短验证，不额外创建长期测试槽。

执行更新：用户已认可并要求继续。Dewey开始A1/A2并随后承接B1，先占host PG/HTTP窗口；Bacon开始C1装配和镜像准备。C0分为Mencius `01a09b01-d374-7e71-847c-3a4f87270037`（Pod核心）与Jason `01a09b01-d421-7920-8ecf-10ee795380f1`（远程workspace核心），均GPT-6 xhigh，生产源码写完交SOL验证/修复。之前“仅准备”描述保留为计划时状态。

## 现在固定的共享决定

**迁移。** 0014冻结为当前 `6f6892a` 已提交定义，此后新增/修正DDL进入增量迁移；0015保持现有控制API用途，0016精确安装或替换退出撤销函数/触发器，0017预留正式Task创建/项目权限。统一迁移器明确 `0014→0015→0016` 的已知链，不直接重放整份0014。0016需兼容有/无当前退出触发器两种已知0014来源，替换在同一事务内完成；其他旧来源先识别，不默认为兼容。不修改历史运行的DDL摘要。A线需要其他SQL修复时统一加入尚未冻结的0016；冻结并运行后再分配后续编号。

开工后的编号更新：C0需要实际受限Pod receiver登记/禁用函数，先分配0017；未实现的Task创建迁移顺延0018。实际升级链保持0014→0015→0016→0017，不留跳号，也不在已执行链中间补迁移。Dewey单一写入，Mencius提供具体锁key及谓词需求，Bacon消费实际迁移版本。

**框架。** 继续固定当前发布版MAF、Python及worker lock；会话/压缩使用公开能力，Wuji增加持久化、权限和操作前沿核对。K8s不以升级依赖解决装配问题，不复制MAF循环或压缩实现。

**创建与身份。** B2的接口设计有三个确定语义：显式起始输入与授权范围分开，离线输入固定不可变版本、不填假URL；项目级create权限与创建后的TaskACL由服务端建立，角色签名不等于项目授权，创建者不成为TenantAdmin；浏览器继续使用服务端会话与写CSRF，由受信独立身份适配建立新核心Principal，Run/JTI及网关Key不交浏览器。具体字段、项目输入登记与原子创建事务是B2先行合同产出，由主代理固定到单一OpenAPI再生成代码。该设计工作不阻塞A/B1/C；B2消费者不能凭旧fixture自行猜字段。

**配置与入口。** 部署factory显式装配真实 `build_runtime_controller`、Scheduler、Registry、UoW、Gate和ArtifactStore；不import `tests.vnext.support`来启动产品，不import旧应用main。测试bootstrap只建立已授权租户/项目/配置等前提，实际Assignment、进程观察、工具与结果必须由生产服务产生。公开API、私有worker-host和Gate分别绑定需要的角色/权限，不能因合并启动就让任意身份跨用端口。

**Pod与工具适配。** 复用 `TaskRuntimeController` 的 `PermitSource.current`、独占lease、资源归属检查；许可必须从真实P05当前状态读取，Pod创建成功并核对UID之后才登记可派发receiver。基础库的UUID类型限制不能导致vNext既存Task/TenantID被改写；在独立配置边界适配标识并保留原身份。远程workspace客户端实现现有P06 executor端口；Kali侧复用现有只读执行逻辑，执行前通过受信Gate核对持久ToolPermit、当前许可、完整Run/Task身份和参数摘要，持久复用同一次ToolAttempt回执；丢响应先lookup，不制造新attempt。只开放受限读取/回执查询/取消端口，不新增通用shell。双方均不能通过内部请求传一个allow=true绕过Gate。HTTP wire在单一合同源登记后再实现消费者，映射现有Permit/receipt而非第二套许可状态机。

## K8s首批落地边界

- 使用本机 `docker-desktop`，隔离namespace定为 `wuji-vnext-test`，带本批管理标签；首次创建前核对context/namespace归属和实际创建权限。现有 `wuji-test`、旧服务和其他namespace不由本批修改。不用旧部署脚本强行通过其固定namespace限制。
- 控制服务与数据库运行在各自独立的平台Pod；每Task仍只有agent+kali两个容器，Node和独立Python child位于agent中，Controller唯一管理Task Pod，Node只管理Run进程。Task Pod不持数据库管理员凭据、平台签名私钥或集群管理凭据。
- 固定 `linux/arm64` 镜像、实际发行版本和镜像摘要。复用隔离MAF依赖；Task Runtime仅复用不依赖Cairn/Pi的资源构建/归属检查与Kubernetes客户端。实际PodUID通过受信API/Downward API核对后登记，不能沿用宿主fixture的PodUID。
- 跨Pod Controller/Gate/Supervisor通信使用HTTPS及受信测试CA，保留现有“非loopback不能明文HTTP”的规则；CA私钥不进入Task Pod，服务证书仅挂需要的容器，不用关闭证书校验使测试通过。
- 候选合成模型放在调用该gateway的Gate服务同一Pod，通过loopback提供服务，保持D12规则；不把cluster DNS随意加入候选白名单。机制候选固定新的真实Task/receiver/runtime_attempt/PodUID，不能复制旧宿主候选绑定。首个无Session切片沿用已验证的关闭能力配置。
- 首个工具仍为 `WorkspaceReadExecutor` 的受限无害文件读取，但实际执行位置移至Kali，由C0的远程executor适配连接Gate。保持现有卷隔离：agent只挂自己的state，Kali挂 `/workspace`，多个Run通过受控工具访问同Task工作区；不把Kali卷挂给agent或Gate以冒充远程接线。夹具文件、原字节摘要与P03证据必须对应，完整目标工具另按实际实现验收。
- 数据库使用独立测试库，迁移owner与非owner应用身份分离；Artifact、Node inbox、dispatch journal使用持久卷与明确UID权限，Task清理不隐式删除证据卷。仅创建本批自有Secret，秘密留在受限本地/K8s，不进Git或普通报告。
- 首次只开放所需集群内部连接和本机port-forward。出口限制必须有实际证据；若本地CNI不执行NetworkPolicy，只能记录该隔离项未通过并保持合成/无外部目标范围，不能把policy对象存在当隔离生效。

## 可执行入口与停止条件

现有入口，按负责人的源码变化选择最小集合：

```bash
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_session_approval.py::test_real_rejection_http_restores_native_denial_without_execution -q
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_control_integration.py -q
work/toolchain/bin/pnpm contracts:check:v2
```

第三条仅在wire/生成合同变化时运行。A2新增迁移/负控测试需先登记实际test_name；不以collection代替执行。C线将新增 `scripts/vnext/k8s.py` 的 `prepare`、`deploy`、`test`、`status`、`cleanup` 子命令；现在尚不存在，不能把它们写为已执行成功。`cleanup`只按本批管理清单处理受管测试资源，并默认保留证据/数据卷。

共享PG/API/K8s运行窗口由主代理逐批安排；独立源码和镜像构建可以并行。每次测试绑定提交或保存的dirty diff、DDL和镜像摘要。保留完整stdout/stderr、HTTP、实际SQL/进程事件，成果引用真实截图；原始秘密脱敏后再归档。不为了报告提交SHA重跑。

A1/B1/C2各自达到出口后即停止该项检查并继续下一依赖；测试脚本同类问题最多两轮后据真实trace列出阻塞，不猜测重跑、不按耗时自动升级模型。已过M2/P13/P14不重开全量复审。P12/正式流与布局、全量治理、历史归档、效果评测及最终发布继续按总计划；本批结果不冒充它们的验收。
