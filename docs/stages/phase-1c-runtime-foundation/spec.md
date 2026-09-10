# Phase 1C：单 Task Pod 执行基础 Spec

- 状态：approved；日期：2026-09-11。
- 批准依据：用户明确选定“Task统一治理、Cairn原生黑板、单Task Pod双容器、动态Agent进程、共享Kali工作区”，要求更新Spec/Plan后开始开发。
- 起始基准：eee81b4746a27cba633769c3cdf0fcdf60198028及同会话已确认的架构澄清；分支codex/phase-1c-runtime-foundation，沿用phase-1c-prep工作树。
- 已读取：根AGENTS、背景索引、主架构、Harness/黑板、原P0及架构收口记录。当前工作树无CodeGraph索引，使用rg和直接读取。

## 1. 本批交付

开始实现独立Python基础包`packages/task-runtime`：执行配置、单Pod双容器清单、资源归属检查、受许可的Pod创建/复用、基础设施就绪检查、带UID条件的停止请求，以及Kubernetes官方SDK适配。

这是后续控制面与Cairn执行后端要调用的真实基础模块，不是完整运行服务。本批不接公开API、不迁移业务数据库、不部署镜像或Pod、不调用模型/目标；API保持0.4.0。Cairn核心不修改，Pi会话/工具MCP与Controller持续调谐进程留后续接入。本批不声明已具备目标出口、真实停止或完整调度能力。

## 2. 配置与清单

使用冻结的内部配置对象TaskRuntimeConfig：tenant_id/task_id为UUID；namespace为合法DNS标签；runtime_attempt/execution_epoch为正整数；scope_digest/config_digest为SHA-256；agent/kali镜像分别固定为带sha256 digest的引用。容器CPU/内存request/limit、临时目录大小和Pod最长存活秒数由配置显式提供，不从P0测试值推导产品默认。

资源名称由Task UUID确定：Pod名包含attempt，配置/凭据/PVC名称按Task派生。两个配置ConfigMap、两个独立Secret和两个PVC分别服务agent/kali，不允许把任意用户路径、Pod名、宿主目录或秘密值拼入模板。

Pod固定两个容器`agent`、`kali`。分别挂载配置、只读任务凭据、会话卷或Kali工作卷，各有临时目录；不交叉挂载凭据/会话卷。禁止hostNetwork/hostPID/hostIPC/hostPath/privileged和ServiceAccount token自动挂载；不共享PID空间，非root且禁止提权、drop ALL、RuntimeDefault seccomp。镜像入口由受信镜像实现：agent入口等待受管进程请求，kali入口提供受管工具/MCP，均不得自行开始目标或模型调用。

全Pod网络以Task为边界，本批不生成或声称验证了NetworkPolicy。两个镜像更新形成新配置，不原地修改活动Pod。Kali工作卷由后续工具适配按`agents/<agent_run_id>`和`shared`组织，本批不运行目录初始化命令。

## 3. 许可与资源控制

PermitSource为内部可信接口，提供Task当前已接受start的许可快照：Task/租户、attempt、epoch、scope/config摘要、start_command_id和有时区的expires_at。没有有效许可或任一绑定不符，不创建Pod。该接口需后续接权威Task存储，本批对象本身不构成对外身份认证。

TaskRuntimeController为唯一Pod生命周期调用方，提供ensure(config)和stop(config, pod_uid)：

- ensure先检查当前许可，读取确定名称；仅明确404视为不存在。已有Pod必须有匹配的名称/namespace、管理标签、Task/租户/attempt、epoch及配置模板摘要；不匹配则拒绝，不修补或删除。
- 新建前查询同Task自有Pod；仍有其他attempt资源时阻止创建新代次，要求先显式核对/回收。核对引用ConfigMap/Secret/PVC的归属；缺失或归属不符不创建。PVC不强制预先Bound，避免WaitForFirstConsumer死锁。
- 创建前再读一次许可；创建返回后再读许可，撤销/过期则按返回UID请求停止新资源，不能报告ready。
- 创建409只读取并核对已有对象一次；其他失败/超时保留错误或结果不明，不自动重试写请求。
- 返回observed状态仅有基础设施意义：provisioning、ready、stopping、stopped。ready要求Running、Pod Ready和两个容器均ready且无deletionTimestamp；不代表出口、工具授权或任务评估已经就绪。
- stop只处理验证过归属且UID匹配的具体Pod。删除使用UID及resourceVersion前置条件；删除请求被接受只返回stopping，后续明确404才表示该资源已不存在。403、连接错误等不能误判为已停止。配置变化不影响按原UID安全回收，但仍须核对Task/租户/attempt归属。

Kubernetes适配使用官方Python客户端`kubernetes==36.0.3`，构造器接受已配置CoreV1Api；不自动加载/切换本机kubeconfig。设置有限API请求超时，不日志输出Secret内容或上游原始错误body；非Pod引用资源仅向上返回metadata。

## 4. 内部接口与兼容

包提供TaskRuntimeConfig、ContainerResources、ExecutionPermit、RuntimeObservation、RuntimeError子类、build_task_pod、verify_pod_ownership、TaskRuntimeController、KubernetesPodClient。具体Python签名由Plan固定；资源清单是Kubernetes v1 Pod字典，SDK负责协议。

不修改Task UUID、历史queued、现有OpenAPI或回执；旧任务没有start许可时不能调用本模块创建资源。权限判定、并发创建许可的数据库事务、镜像/配置/Secret/PVC的实际准备及持续Controller服务尚未实现，不能把基础库检查冒称平台级恢复/鉴权验收。

## 5. 最小验收与停止条件

| 编号 | 必要验证 |
| --- | --- |
| R01 | 两容器、独立镜像/卷/Secret、安全字段和确定资源名称正确，配置/镜像变化不被已有Pod静默接受 |
| R02 | 无许可、过期或绑定不符拒绝创建；新建后许可撤销只按自有UID请求停止 |
| R03 | 自有Pod复用，错误归属/旧attempt仍存在时拒绝创建；非404读取错误不创建 |
| R04 | 停止使用UID/resourceVersion条件，接受删除不等于停止；错误UID不删除 |
| R05 | 官方SDK适配通过注入的API替身核对调用形状、404和脱敏错误；不连接集群 |

只运行一次定向单元检查和包导入/构建检查，修复仅复测受影响项。依赖准备、等待、执行、排查共享原剩余174秒，不按新分支/批次/模型重置；P0真实4次额度已用完，本批0次真实调用。达到预算或同类排查两轮即停止并记录未覆盖。真实Kubernetes、镜像运行、Cairn/Pi/MCP、取消实际进程和出口联调明确延期。
