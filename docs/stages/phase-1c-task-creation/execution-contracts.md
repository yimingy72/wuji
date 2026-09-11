# 核心闭环执行合同（已批准计划的实施细化）

状态：approved / in-progress；2026-09-11，起点5631d80，分支codex/phase-1c-core-loop。对应用户本轮《Wuji核心任务闭环实施计划》；本次为Default执行模式，不再为M1—M4重复审批。主代理冻结以下接入合同，实现可调整代码组织，不改变行为或Core协议。

## 执行范围与固定配置

只允许部署配置中登记的fixture origin与合成模型；不开放任意Shell或外部目标。现有Docker Desktop不宣称NetworkPolicy已生效。交付wuji-test/4182，保留wuji-dev/4180及master。Reason只读已有证据，主动补证走普通Intent/Explore，此选择已获用户确认。

夹具Profile：agent并发2，Task最长900秒且不超过授权期，Agent每次阶段最长90秒、最多12次模型turn，单Task最多64个新工具启动。状态查询不新增目标尝试；等待单请求最长20秒，可凭原句柄继续。工具超时30秒（测试延迟夹具可由可信测试配置延长至60秒）。许可15秒有效、5秒续租；失联到期停止新调用并停止已有受管进程。SIGTERM后5秒仍在运行才SIGKILL，实际退出才出停止回执。这些是夹具运行限制，不是开发检查预算或未来全场景默认。

## M1共享契约

新草稿2.0保留五scenario；共有name/objective、goal_template:{id,version,digest}|null、completion_criteria:string[]、supplemental_hints:string、model_profile_version_id|null、budget_usd|null。Web有entry_url|null、authorization:{schema_version:'1.0',includes:[{host,include_subdomains,endpoint:{scheme,port}}],excludes:[{host,include_subdomains,endpoints:'all_included'|[{scheme,port}]}],valid_until:datetime|null}|null。其他场景内容沿用D1；旧1.0完整兼容，不自动转换约束。

NewCreateTaskRequest={creation_kind:'saved_web_draft',draft_id,draft_version,preview_id,input_digest,scope_confirmation:{accepted:true,authorization_digest}}。仍用Idempotency-Key头，响应原CommandReceipt。新增ScenarioProfilePage、TaskCreationPreview校验器。新WebTask响应保留旧Task公共字段，task_kind='web_assessment'，scope={authorization_id,version,hash}，creation_config（不可变完整快照）；target_url为entry_url。旧Task响应不附新必需字段。TaskPage/TaskSnapshot的Task改为旧/新oneOf。

迁移0006由主代理维护：task_drafts新增selected_model_summary jsonb和last_created_task_id，schema允许1.0/2.0；task_creation_previews(id,tenant_id,project_id,user_id,draft_id,draft_version,draft_digest,permissions_version,normalized_content jsonb,model_snapshot jsonb,input_digest,authorization_digest,can_create,blockers jsonb,created_at,expires_at)；task_authorizations(id,tenant_id,project_id,task_id,version,scope jsonb,scope_hash,valid_from,valid_until,confirmed_by,permissions_version,confirmation_text_version,confirmed_at)。tasks新增task_kind默认legacy_http、task_authorization_id、creation_config_snapshot_id、creation_config jsonb；旧policy元组仅新类型可空，复合FK和新旧CHECK分别约束。创建事务生成Task/auth/snapshot ID，同事务写回执/事件；auth/task循环FK延迟到提交校验。

新创建Store复用DatabaseAuthority用户事务锁；锁顺序用户→项目权限→原键回执→草稿行→模型版本advisory lock。模型版本锁key以namespace+tenant+version稳定派生；D2状态更新共用。create前不调用网关。ModelUnavailable/CreationBlocked映射409；Scope不合法预览blocker，摘要错误422。预览TTL复用Settings.preview_ttl_seconds（若实际名称不同用已存在的同义配置）。数据公开命名以Pydantic/生成契约统一。

## M2—M4服务与身份

执行控制服务为独立Python服务，复用现有SQLAlchemy/HTTPX/Kubernetes库；提供私有控制、工具路由、结果/Artifact和持久操作消费者。用户API只写命令/读权限化视图。Cairn Server原生单实例SQLite持久化，原生ASGI外围鉴权，不改Core。Dispatcher固定源码小补丁调用执行控制并使用远程进程后端；不修改.venv安装副本作为交付。

任务执行、AgentRun、ToolCall/attempt、Bridge operations与Artifact均有tenant/project/task复合归属。可信执行角色仅拥有所需执行表/状态列权限；Agent/Kali不持有PG或集群管理凭据。每次私有操作验证服务或AgentRun限定凭据和当前epoch/attempt，不接受请求正文改写归属。

## Worker及Supervisor共享HTTP合同

两个镜像分开。agent容器PID1为受管进程服务，监听8001；kali容器为受管工具服务，监听8003。服务启动从只读/config读取任务绑定，从/run/wuji/credentials读取限定凭据；监听端口不是鉴权依据。状态和输出保存在各自挂载卷。进程注册使用固定UUID操作标识；同标识同请求返回原对象，不重启。

agent接口（仅执行后端凭据可调用）：PUT /runs/{agent_run_id} body {phase,assignment,prompt,model:{base_url,model_id,context_window,max_output_tokens,timeout_seconds},tool_names,deadline,operation_id}；GET /runs/{id}；GET /runs/{id}/output；POST /runs/{id}/cancel。assignment含task_id、project_id、tenant_id、execution_epoch、runtime_attempt、graph_snapshot及Goal/完成条件/Hint。Task模型Key从受限文件读取，不由body/argv携带。返回{id,state:registered/running/exited/unknown,returncode,pid,started_at,finished_at,cancel_requested,output_digest}；输出用同对象读，不执行任意command。

kali接口（仅Tool Router凭据可调用）：PUT /calls/{tool_call_id} body {operation_id,agent_run_id,task_id,execution_epoch,runtime_attempt,tool,args,expires_at}；GET /calls/{id}；POST /calls/{id}/cancel。tool仅fixture_http、workspace_read、workspace_write、workspace_list、fixture_wait；所有路径限制在/workspace；fixture_http目标必须匹配/config里的fixture registry，禁止任意redirect/代理/环境变量/命令。返回{id,state:registered/running/exited/unknown,returncode,result,started_at,finished_at,cancel_requested}。JSON错误不能泄露凭据/内部异常。

跨平台通信采用独立服务凭据，AgentRun工具请求采用按Run签发的短期凭据，执行控制再查账本。Agent扩展到控制端路由：POST /internal/v1/agent-runs/{id}/tool-calls body {request_id,tool,args}；GET /internal/v1/tool-calls/{id}；POST .../cancel。模型原生toolCallId作request_id，重复请求沿原账本核对；Task/epoch从认证映射派生，不让模型填写。平台Tool Router转发到当前Kali attempt。Supervisor每5秒核对lease，逾期终止受管进程，控制端失联不继续接新调用。

Pi真实CLI JSON模式，固定@mariozechner/pi-coding-agent@0.73.0；--no-extensions/--no-skills/--no-prompt-templates/--no-themes/--no-context-files/--no-builtin-tools，显式-e受信扩展；session目录/agent配置按AgentRun隔离，PI_CODING_AGENT_DIR不复用用户HOME。扩展注册白名单工具，context装配合同，before_agent_start装配阶段提示。保留原生响应解析，不造模型协议/Agent循环。模型调用/压缩均通过同一Task LiteLLM Key。

## 金额、结果、停止

LiteLLM固定已核对镜像，单副本单进程，无Redis；reservation启用，fail_closed_budget_enforcement=true。稳定Task Key先保存Secret，再/key/generate，models仅本次部署别名，max_budget取Task USD，不设置budget_duration；未知用原Key hash查询/key/info，block原Key，永不重建清预算。只用合成上游，不付费探活。

结果先写原始AgentResult，再调用原生Core。每项原生副作用有平台operation_id，未知写不盲重投：已知Intent conclude可读结果核对，未知Project/Intent创建保持unknown，禁止该阶段重新探索。完成与取消先关派发，再核对Agent、工具、模型/证据同步；SDKabort/Pod删除接受不作为已停证明。结果未知和执行未知分开。

Artifact用独立持久卷文件后端，原子落文件并校验摘要后标available；由API按项目权限通过ID读取，普通响应无文件系统路径。共享Kali临时文件可直接交接，正式证据才Artifact。结果使用确定性模板，保留已测/未测/阻断与具体证据，不假造覆盖/漏洞数。

## 验证与交付

M1有限PostgreSQL/契约检查；M2/M3必要离线边界后统一实际夹具集成；M4真实浏览器一次。最终必须真实Cairn/Pi/LiteLLM/K8而非前端伪造，不跑旧完整回归。固定SHA和run_id，单个wuji-test串行管理。本阶段未完成前不标accepted；不设置累计检查预算，不额外增加真实模型调用额度。

## M4 关系读取

agent-runs支持intent_id，tool-calls支持agent_run_id，artifacts支持tool_call_id；同一请求只接受所属端点的一项筛选，误用422。过滤与Task/租户/项目条件共同生效；有界分页及签名游标绑定筛选。Artifact公开tool_call_id，不公开存储位置。NativeGraph的Intent和Hint使用原生字段的严格生成校验器，读取端不写图。
