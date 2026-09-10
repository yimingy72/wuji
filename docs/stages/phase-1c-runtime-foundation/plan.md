# 单 Task Pod 执行基础 Plan

- 状态：in-progress；日期：2026-09-11；用户已在执行模式明确授权更新Spec/Plan后开始开发，不声称自行切换模式。
- 对应[Spec](spec.md)，基准eee81b4746a27cba633769c3cdf0fcdf60198028加本次已确认文档修订。

## 1. 复用与范围

新增可选workspace包wuji-task-runtime，Python3.13.15/hatchling沿用工程版本，官方kubernetes客户端固定36.0.3。新group task-runtime显式安装，不挂入API启动路径；主代理独占根pyproject/uv.lock。Cairn、Pi及其核心源码不在本批下载/修改，P0依赖版本保留。

后续控制面调用本包，不在API main.py堆资源管理；本批不实现另一套模型/工具循环，不创建新的权威Task数据库。实际ConfigMap/Secret/PVC和镜像准备留后续Control Plane/部署。

## 2. 固定Python接口

- models.py：冻结dataclass ContainerResources(cpu_request,memory_request,cpu_limit,memory_limit)；TaskRuntimeConfig(tenant_id,task_id,namespace,runtime_attempt,execution_epoch,scope_digest,config_digest,agent_image,kali_image,agent_resources,kali_resources,tmp_size_limit,pod_deadline_seconds)。派生pod_name、resource_names、template_digest和identity_labels；合法性在构造时检查。
- ExecutionPermit(tenant_id,task_id,runtime_attempt,execution_epoch,scope_digest,config_digest,start_command_id,expires_at)；PermitSource.current(task_id)返回该对象或None。controller注入clock，重复检查current及其绑定/期限。
- manifest.py：build_task_pod(config)->dict；verify_pod_ownership(pod,config,*,require_template=True,expected_uid=None)->None；verify_resource_ownership(resource,config)->None。完整模板核对包含两个容器及安全/卷挂载字段，允许Kubernetes补充正常默认值；停止时只核对身份和UID，不因期望模板升级而拒绝安全回收。
- controller.py：TaskRuntimeController(pods,permits,clock)；ensure(config)->RuntimeObservation(state,pod_name,pod_uid,reason=None)；stop(config,pod_uid)->RuntimeObservation。PodClient协议为read_pod、list_task_pods、read_resource、create_pod、delete_pod，所有方法显式namespace，删除参数含uid/resource_version。
- kubernetes_client.py：KubernetesPodClient(core_v1_api,request_timeout_seconds=10)，使用官方CoreV1Api和V1DeleteOptions/V1Preconditions；CoreV1Api须在构造ApiClient前配置retries=0，适配器验证而不修改共享客户端。只把404变成不存在，409创建交由controller核对；其他API状态脱敏为RuntimeTransportError，连接不明为RuntimeStateUnknown。

labels使用app.kubernetes.io/managed-by=wuji-task-runtime-controller、wuji.dev/task-id、tenant-id、runtime-attempt；annotations保存execution-epoch、scope/config/template-digest。Pod名wuji-task-<task UUID hex>-a<attempt>；引用资源名基于wuji-task-<UUID hex>加agent-config/kali-config/agent-auth/kali-auth/agent-state/kali-work后缀。配置资源不接受秘密值。

agent挂载/config、/run/wuji/credentials、/var/lib/wuji/agent、/tmp；kali挂载/config、/run/wuji/credentials、/workspace、/tmp；名称与卷引用分别独立。工作卷使用Task专属PVC，/tmp为有sizeLimit的emptyDir。容器runAsUser分别10001/10002、Pod fsGroup=10000并使用OnRootMismatch，镜像/卷需支持这些身份；restartPolicy=Never，失败需新代次，不隐式重启执行；不推导产品预算默认值。

## 3. 分工和顺序

1. 主代理完成已批准单Pod文档/Spec/Plan及models/package公共接口。
2. 可选gpt-6-astra/low实现manifest.py及其定向测试，限定该文件范围，不设计架构，不运行检查或提交。
3. 主代理实现controller、官方SDK适配、其余定向测试和包说明，审查并集成。
4. 主代理统一启动预算计时，解析锁定依赖并执行一次最小验证；不并行启动共享环境、不运行旧API/浏览器全套。
5. 固定候选提交，记录命令/退出码/累计预算及延期项，后续报告提交与候选分开。主目录服务HEAD/master不前移，仅规则/导航同步。

## 4. 验证入口

使用现有仓库uv工具和缓存，执行group task-runtime的冻结安装；pytest只运行packages/task-runtime/tests；包构建只针对wuji-task-runtime。测试注入API替身和许可源，不调用Kubernetes、不读取真实Secret或模型配置。

原检查预算426/600秒已用、剩174秒；从第一次依赖/检查准备开始统一计时并设置剩余超时，记录完整窗口，不仅累加成功命令。到限停止，未覆盖保持partial，不追加真实模型额度。

## 5. 交付与下一步

本批交付资源控制基础库及其离线证据。0.5业务接口、持续Controller进程、Cairn执行进程/取消适配、双镜像构建、MCP和真实出口均未接入；后续控制面Spec承接此包，不把基础设施ready当作可开始目标测试。
