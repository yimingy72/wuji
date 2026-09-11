# D2 组织模型配置与 LiteLLM Spec

状态approved / implementation accepted；2026-09-11，用户明确批准D2实施。基准d84b2f5，沿用phase-1c-prep工作树。主代理独立设计；本树无CodeGraph索引，使用rg/直接读取。背景来源：AGENTS、项目索引、D1 Spec/验收、Cairn架构决策、Harness设计及本轮已批准计划；上游固定LiteLLM v1.100.0的credentials/model management/health源码和官方价格文档已核对。

## 目标与边界

管理员配置服务→添加模型方案→显式检查→发布→项目草稿选择。只接配置后端和本地网关；不开放Task start、不启动Cairn Agent/Kali、不接正式配置页面、不改变现有0.4工作台/开发数据/master。管理员填写公司网关单价（USD/百万Token），Task创建者设置金额预算；本批不实现预算引擎或任务key。

复用LiteLLM原生/credentials、/credentials/by_name/{name}、/model/new、/model/info、/health?model_id、/model/block。不用企业版Team BYOK，不另加模型SDK。Wuji保存权限、不可变配置版本及持久操作，密钥正文只交给LiteLLM原生加密库；不打补丁修改上游。

## 配置模型

服务/方案各有稳定definition ID和多个不可变version ID。创建definition同时创建首版，新增版本保留旧版；版本内容无PATCH入口。版本state为draft/published/retired/revoked，sync_state为pending/synced/failed/unknown；state_revision从1开始用于发布命令CAS。

服务config：protocol(openai/anthropic)、base_url。创建请求额外包含writeOnly api_key，Wuji不落库或返回；原生credential_name由实例/tenant/version UUID生成。初始允许Base URL为https://ai-api-gateway.app.baizhi.cloud/api/openai及/api/anthropic；测试可在明确local-test部署配置中覆盖。拒绝凭据/查询/fragment/环境变量引用和任意厂商参数。服务name在版本中保留。

方案config：service_version_id、model_id、context_window(nullable positive int)、max_output_tokens(nullable positive int)、timeout_seconds(default30,1..60)、pricing(nullable)。pricing含source(nonempty)、input_per_million/output_per_million(Decimal字符串，>=0)、cache_mode(standard_input或separate)，separate需cache_read_per_million/cache_creation_per_million；standard_input显式表示网关按普通输入单价计缓存，不能默用官方价；两项基础价不能同时为0（首批不发布免费预算豁免模型）。价格最多12位整数/12位小数，转换到LiteLLM每Token数值，不以float做业务计算。方案容量/价格可缺省保存和检查，发布时必须完整且输出上限<=上下文容量。模型ID按所选协议映射openai/<id>或anthropic/<id>，不接受通配路由和调用方自填provider前缀。

每个方案版本唯一原生deployment ID=版本UUID和别名wuji_<tenanthex>_<versionhex>；记录显式gateway_instance_id，不按URL猜数据实例。native model_info/credential_info带平台实例、租户、版本和请求指纹，仅用于已知对象核对，不做第二套厂商配置来源。禁止平台外原地修改Wuji托管版本。

## 权限与HTTP接口

TenantAdmin为独立tenant_admin_grants，要求有效组织成员，不改变operator/viewer角色，不授予项目/Scope权限。可信CLI显式grant/revoke，复用用户锁/permissions_version/identity_audit，不自动提升seed用户。

GET /api/v1/tenants返回当前组织及model.config.read/write（仅admin）能力。下列管理路径位于/api/v1/tenants/{tenant_id}，仅TenantAdmin可读写：
- GET/POST /model-services；GET/POST /model-services/{definition_id}/versions。
- GET/POST /model-profiles；GET/POST /model-profiles/{definition_id}/versions。
- GET /model-profile-versions/{version_id}（也用于版本恢复）；GET /model-service-versions/{version_id}。
- POST /model-profile-versions/{version_id}/checks：body为空对象。
- POST /model-profile-versions/{version_id}/commands：{action:publish|retire|revoke,expected_version:state_revision}。
- GET /model-operations/{operation_id}；GET /model-operation-keys/{idempotency_key}按当前用户原键只读恢复，避免丢失创建响应后必须重新输入密钥。
GET /api/v1/projects/{project_id}/model-profiles沿用项目读取权限，返回同组织published+synced版本，不返回凭据。

创建/新增版本请求为{name,config}，服务再含api_key；新增版本的name保存该版显示名。写请求必须Idempotency-Key UUID、Origin、CSRF及当前会话。POST统一返回200 ModelOperation（包含id/kind/version_id/state/result/created_at/updated_at），可按version_id读取对应版本；不是没有消费者的202。状态prepared/sent/succeeded/failed/unknown，result为受限{error_code,usage,cost_usd}，未知用量/费用null。
列表默认50最大100、created_at/id倒序，游标绑定用户、权限版本、租户/项目、父definition、用途、limit；失效410，跨上下文422。沿用401/403/404/409/422/503脱敏错误；幂等键异请求409，过时state_revision409；发布条件不符409 INVALID_TRANSITION。

## 持久化与并发

0005衔接0004，仅新增组织管理授权与model_definitions/model_versions/model_operations。各表有tenant FK、复合归属FK/RLS；model_versions中profile的service_version_id通过复合FK限制为本租户service版。运行project角色不能修改管理员授权或版本配置/归属、删除记录；auth无模型表权限。管理CLI修正_migrate版本输出，从真实alembic_version读取。

请求指纹用现有cursor_signing_key经独立域标记HMAC计算，服务秘密只参与HMAC，不进持久payload/公开结果。请求键按tenant/user唯一并绑定kind、parent/target、完整请求指纹。先重新授权，再取原操作，未发送prepared可以由同键原请求继续；sent/unknown只读核对，禁止盲重投。原生创建成功必须按已知ID与平台归属/指纹核对；响应不明但原对象存在且标记一致可确认，不能匹配保持unknown。

本批单次管理操作由ModelStore.actor持有既有用户事务锁，多个project事务分别提交prepare/claim/result，保证HTTP前记录已持久化。最多一次有界原生写/检查及必要读，权限变更等待该已接受操作结束；不持有project写事务跨HTTP。网关管理请求timeout10秒，健康检查20秒/客户端25秒；所有重试关闭。阶段尚无真实Task执行，不将此管理锁策略冒称执行停止机制。

版本创建与operation准备原子；prepared→sent CAS只允许一位发送者。原生写明确4xx失败，断连/5xx或不合规响应unknown。sent超期（45秒）查询时仅标unknown，不发模型。检查只对已同步指定版执行一次原生/health?model_id，最多256输出Token，短固定合成输入；成功只说明连通，用量/费用缺失为null。保存/列表/发布/readiness不请求模型。

publish要求同版本最新明确成功检查、synced、完整价格与容量；retire仅阻止新选择；revoke在发网关block前本地标revoked，远端未确认保持sync_state unknown/pending，平台即刻不再选择。重放不得重新做版本检查或重复模型请求。配置版本更新不改D1草稿旧ID，草稿选择不强制自动保存。

## 部署与验收

LiteLLM v1.100.0固定镜像digest sha256:c8756e7b9a61fe45df2ccb5b781d388c3b2f3a21ef9e4956630caef20f9f03aa。单副本、独立DB/角色、无Redis；原生迁移，原生credentials加密，master/salt分别Secret持久保存。API不接收盐或网关DB DSN。配置只作infra，store_model_in_db开启，background_health_checks/retries/fallback/cache/外部遥测关闭；探针为liveliness/readiness。开发/测试端口18400/18402，schema v1可选gateway扩展，旧记录保持兼容。资源/进程沿用ownership/UID/锁定记录与清理规则，不改主工作区绑定SHA。

M01权限/跨租户/撤权/不隐式获得项目；M02保存/重放/版本/无密钥回显；M03原生LiteLLM+合成OpenAI/Anthropic保存检查发布；M04缺价/旧版检查/unknown不能发布、丢失检查不重发；M05项目选择/retire/revoke；M06网关重启保持配置/凭据、契约与API构建。

无累计检查预算，只做必要路径通过即停；复用D1临时PostgreSQL检查，原生网关统一由主代理串行管理。公司真实网关调用0次；P0原额度不增加。生产Task预算/价格准确性、Pi和Kali/出口均不属于本批通过项。

实施细化：补充GET原键查询供丢失保存响应后恢复；撤销同步失败可由管理员用新操作显式重试block，本地始终revoked，不自动重发。网关保留原生费用日志但不保存prompt/response正文。

开发网关实例以仓库共同Git目录+开发namespace稳定派生，源码run_id改变不会重新生成开发密钥/DB；测试实例另外绑定run_id保持隔离。
