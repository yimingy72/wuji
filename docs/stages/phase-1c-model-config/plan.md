# D2 实施Plan

状态in-progress；基准d84b2f5；对应Spec已由用户明确批准。当前会话完成，主代理设计和验收。

## 唯一归属与顺序

- 存储子任务gpt-6-astra/low：model_store.py、0005迁移、database_admin.py中的tenant admin管理函数和manage.py CLI/真实revision标签。不得改DTO/Settings/main/契约。
- 部署子任务gpt-6-astra/low：infra/kubernetes/model-gateway、scripts/platform/gateway.py及网关启动/停止入口、schema v1可选gateway字段、run_file.py相关校验、common.py仅gateway环境/转发/范围扩展、local-development网关说明。不得改API Settings/DTO/数据库迁移/现有主服务，禁止直接部署或环境检查。
- 主代理：DTO、HTTP薄适配、流程编排/路由、Settings/main/EXPECTED_REVISION、游标、OpenAPI/生成器、测试/真实模型夹具、所有环境操作/候选提交和集成验收。

## 存储接口冻结

ModelStore(authority)，async actor(user_id,tenant_id,permissions_version) contextmanager获取既有_fresh_user_lock，核对有效tenant+tenant_membership+tenant_admin_grant后yield Actor(user_id,tenant_id)。RLS app.user_id/app.tenant_id在每个短project事务设置，app.project_id清空；actor期间外层auth事务持用户锁，project事务不跨HTTP。

方法均接受actor参数且返回字典（内部字段可含digest/native_id，公共DTO由主代理投影）：
- list_tenants(user_id,limit,position)->list[dict id,name,created_at,is_admin]（limit+1）。
- list_definitions(actor,kind,limit,position)、list_versions(actor,kind,definition_id,limit,position)、get_version(actor,version_id,kind=None)。
- prepare_version(actor,key,request_digest,kind,name,config,definition_id,gateway_instance_id)->tuple(operation,version)；definition_id=None创建root。service config不含api_key，profile config含service_version_id，持久化请求指纹由主代理提供。
- prepare_action(actor,key,request_digest,version_id,kind(check/publish/retire/revoke),expected_version=None)->tuple(operation,version)。同键同digest直接原operation；新动作下检查已同步/发布条件及expected_version，发布/retire为本地事务直接succeeded；revoke先本地revoked、revision+1并生成prepared operation供网关block。check要求profile synced且未revoked。publish要latest check operation为succeeded、pricing/容量完整。
- claim(actor,operation_id)->bool prepared→sent并保存sent_at；finish(actor,operation_id,state,result=None)->operation，sent/unknown→终态，成功service/profile-create更新version.synced，失败create更新failed/unknown；check不改变config sync；revoke成功标同步。
- get_operation(actor,operation_id)->operation（超期sent按45秒转unknown）；replay sent/unknown不重发。
- project_profiles(user_id,project_id,limit,position)->list[version dict]：沿用当前项目权限，仅published synced同组织。
position均用TaskCursorPosition(created_at,task_id)复用表示通用ID。列表definition不存在404，错误kind/tenant404。所有数据库异常脱敏AuthorityUnavailable；身份异常沿用现有库。

表字段：tenant_admin_grants(tenant_id,user_id,enabled,created_at,updated_at)，复合FK到tenant_memberships；model_definitions(id,tenant_id,kind,name,created_at)；model_versions(id,tenant_id,kind,definition_id,number,name,config JSONB,service_version_id nullable,service_kind固定service,gateway_instance_id UUID,native_id varchar,request_digest char64,state,state_revision,sync_state,created_at)；model_operations(id,tenant_id,user_id,idempotency_key,kind,version_id,request_digest,state,result JSONB,sent_at,created_at,updated_at)。kind分别service/profile或create_service/create_profile/check/publish/retire/revoke；create首版及后续版均用相同kind，请求摘要包含parent区分。native_id service=wuji_<instancehex>_<tenanthex>_<versionhex>，profile=版本UUID；原生模型alias由主代理同字段生成。

## 部署接口冻结

API Settings字段（主代理实现）：model_gateway_url nullable、model_gateway_key SecretStr nullable、model_gateway_instance_id UUID nullable、model_gateway_allowed_bases list[str]默认用户两个BaseURL。三项连接字段必须一起提供；不用时D1仍可运行，model写返回503。

运行schema v1可选model_gateway对象：instance_id UUID、url、database_name、database_role、master_key Secret、salt_secret_name、database_secret_name、master_secret_name；运行文件含master_key(0600)，不保存salt明文/网关DB密码（仅K8Secret）。processRecord新增可选credential_scope model_gateway_management，原3项旧记录仍有效；仅实际API启用gateway时记4项。API环境仅注入URL/master/instance/allowed_bases。独立gateway.py提供prepare/up/down/status CLI --run-file既有已验证文件（主目录旧run不能绕过SHA）；复用common的Kube/record/process组件。部署代码不执行主API迁移或启动，测试可生成自有run。准备nativeDB只在可信管理进程完成，独立db/role无Wuji权限，Secret幂等复用，所有资源先ownership检查，down不删DB/Secret/PVC。

## 验证交付

固定候选后先临时PostgreSQL+HTTP替身最小权限/操作流程，再一个真实LiteLLM实例+合成协议上游和重启检查；公司网关调用0。环境/真实实例统一主代理串行管理。实际原生依赖不兼容时如实记录，不能用替身宣称集成成功。契约检查/API构建通过即停，不跑旧浏览器矩阵。

实现细化：原键查询新增get_operation_by_key(actor,key)和GET /model-operation-keys/{key}，不接触秘密；配置使用原生费用记录并关闭prompt正文记录。真实原生验证用已缓存Docker镜像和内部network，一套独立PostgreSQL非管理员应用角色及合成两协议上游；本批不改变运行中的Kubernetes工作台，仅交付Kubernetes生命周期入口及其定向结构检查。
