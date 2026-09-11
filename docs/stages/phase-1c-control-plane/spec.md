# Phase 1C 控制面：独立草稿与后续接入 Spec

- 日期：2026-09-11；D1状态approved / implementation accepted；D2—D4为待细化后续范围，不表示已经实现。
- 承接用户确认的架构、无模型可保存草稿和本轮“继续开发”；当前为执行模式，未声称自行切换Plan模式。
- 基准：1da3ec6d0bfec04a948ca5c6461cbac21c819db9，沿用phase-1c-prep工作树，分支codex/phase-1c-control-plane。
- 来源：根AGENTS、project-context、PRODUCT、主架构、Cairn架构决策/黑板/Harness设计、场景交互、评估模型、Runtime和桥接验收；源代码实际Task仅queued/cancelled，TenantAdmin尚不存在。

## 1. 交付顺序与兼容

D1本批交付正式API中的独立任务草稿保存、恢复与列表。草稿不是Task，不创建Cairn Project、模型预算、Pod、授权记录或事件；不发模型/目标/源码下载请求。没有模型方案允许保存，已填版本ID只作为待验证选择，不能因此声称可创建或执行。

D2组织模型配置：先实现显式TenantAdmin权限，复用LiteLLM原生管理与连接检查，发布固定版本方案；管理员配置不包含任务金额预算。D3创建和启动：草稿→复查配置/创建者范围确认→不可变快照→ready；显式start只有消费者与准入齐备才能接受，旧queued不自动执行。D4持久执行：AgentRun/工具账本/epoch与权威ControlSource，之后接真实Dispatcher。D2—D4具体接口及迁移在实施前补充，禁止复用已被替代的旧0.5草案或新增空转start入口。

本批契约为0.5.0开发候选的首个增量，只新增草稿API；原有Task API和回执/事件行为不变。完整0.5控制面尚未交付，主业务仍0.4.0，不切换现有服务或主分支。新版创建前端继续遵守先评审原型的约定，本批不新增页面或虚构配置菜单。

## 2. 用户行为与内容

用户选场景即可保存不完整草稿，稍后在同项目继续。空名称、目标、范围或模型不是保存失败；填写了字段则验证其格式。五种场景是ctf、web_single、comprehensive、exercise、code_audit，互斥内容，不把API字段当最终页面设计。

共有内容：schema_version=1.0、name、objective、starting_point、constraints、reference_ids、model_profile_version_id、runtime_profile_version_id、budget_usd。文本默认空，引用默认空集合，模型/环境/金额默认null；金额为正数USD十进制字符串，最多12位整数和6位小数，不用二进制浮点或Token。草稿不执行计费，也不代表发布模型可用。

- CTF：challenge、可选entry_url。
- Web单点：可选entry_url、include_subdomains默认false、additional_origins默认空；仅表达待确认范围，不授权。路径只在入口中保留，不能设置路径ACL或初始账号。
- 综合渗透：assets候选文字列表、access_notes；不自动授权内网。
- 攻防演练：organization_name、known_domains；单位或已知资产不自动批准测试。
- 代码审计：repository_url或source_reference_id、revision；两类来源互斥，可均为空；不导入/解析或执行仓库。

引用限20个，资产/附加范围限100个，URL沿用既有纯本地HTTP(S)规范化，拒绝URL内凭据与fragment；未知字段拒绝。文本及列表各有限长，完整规范化内容UTF-8最多64KiB。不得提供Key、Cookie、密码字段；自由说明仍属于用户资料，不作为指令或授权。

## 3. API与并发

统一路径前缀/api/v1/projects/{project_id}。

| 接口 | 行为 |
| --- | --- |
| PUT /task-drafts/{draft_id} | 客户端UUID作稳定草稿ID；全量保存{expected_version,content}，创建expected_version=0；更新使用当前版本；返回200 SavedTaskDraft |
| GET /task-drafts/{draft_id} | 当前用户自己的草稿，返回SavedTaskDraft；他人/其他项目/失去项目访问返回404 |
| GET /task-drafts | 默认50、最大100；按created_at/id降序，签名cursor绑定用户、权限版本、项目、页大小及task_drafts用途；返回SavedTaskDraftPage |

SavedTaskDraft包含id/tenant_id/project_id/user_id、version、content、created_at/updated_at。没有allowed_actions或可执行承诺。列表只返回自己的草稿；Viewer可以读自己仍有项目权限的存量草稿，不能写；Operator可新建/更新。原有Project权限响应增加task.draft.read，Operator再增加task.draft.write，不授予组织管理权限。

会话/Origin/CSRF复用现有流程。写入取得用户事务锁后复查enabled、permissions_version及当前两层Operator身份，先鉴权再重放；过期身份401、失权403、不可见404、版本冲突409 VERSION_CONFLICT、格式错误422、数据库不可用503。权限版本改变使旧写请求409，客户端刷新身份再保存。

同草稿ID、同expected_version及相同规范化内容的紧邻重放返回已有版本，不增加版本；仅当前版本=expected_version+1且内容摘要相同时可确认该重放。若已有后续更新，不回滚、不假装旧写已成功，返回409。响应丢失用原请求重送或GET核对，不能自动换ID产生多个草稿。更新锁行，数据库主键处理同时首次创建冲突；任务正式创建的幂等回执不拿来记录草稿保存。

## 4. 存储和权限

迁移20260911_0004衔接0003，只新增task_drafts；不修改旧tasks、scope、回执和事件。id主键，tenant/project/user归属、JSONB content、SHA256 content_digest、正version、创建/更新时间；复合FK到projects，user FK到users。数据库检查内容为object、schema_version/scenario及jsonb文本表示不超过128KiB；DTO和Store仍严格检查规范化内容64KiB（避免jsonb输出空格误拒绝合法内容），RLS同时要求当前app.user_id/tenant_id/project_id、有效租户与项目及成员。运行project角色仅SELECT/INSERT和指定内容/版本/更新时间UPDATE；不得改归属、删表、管理角色；auth角色无草稿权限。

复用DatabaseAuthority的分离引擎、_fresh_user_lock、_authorize_project_connection；草稿存储独立模块，避免继续膨胀Task命令实现。迁移仅在自有临时PostgreSQL验证，现有开发数据库不迁移。本批数据库版本检查更新至0004，新API不得误连接未迁移旧库。

## 5. 最小验收

D01：五类不完整草稿均可保存/读取，模型null不发任何外部调用，字段规范化/非法URL/金额和未知字段拒绝。
D02：真实PostgreSQL经过0001→0004迁移；保存/重放/更新/版本冲突和分页恢复；旧task表及预览无草稿副作用。
D03：真实运行角色RLS拒绝他人/跨项目，Viewer写拒绝；会话Origin/CSRF保护及权限改变处理。
D04：生成契约及校验器一致，新增响应通过权威契约校验；API包构建通过。

不设置累计检查时间预算。使用单个临时本地PostgreSQL（本机已安装16.14），临时目录/独立端口/随机测试凭据，结束只停止并删除本次自有实例；ASGI请求不需要启动web/Keycloak/Kubernetes。不会借依赖未变化重跑旧全套。没有模型请求、真实目标访问或真实执行验收。

契约兼容：旧TaskDraft保留为0.4预览/命令输入，新草稿响应命名SavedTaskDraft/SavedTaskDraftPage，禁止覆盖旧schema。
