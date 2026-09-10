# Task / Cairn 桥接 Plan

- 状态：code-delivered / verification-pending；日期：2026-09-11；对应[Spec](spec.md)。
- 当前用户“继续开发”授权承接既定架构；本次不改变核心选型或实际运行环境。

## 1. 实现顺序与归属

1. 主代理固定Spec/Plan、models/errors及接口，新增可选workspace包/依赖group。
2. gpt-6-astra/low可选子代理仅实现SQLAlchemy日志及对应测试，不设计架构，不运行检查或提交。
3. 主代理复用固定Cairn客户端/模型，完成Bridge、执行预选和原生Server测试；核心源文件不修改。
4. 统一计时解析依赖、冻结安装，固定候选SHA后运行定向检查和包构建；共享原剩余92秒。
5. 记录实际结果、限制与预算，更新入口并本地提交；主工作区HEAD/master/服务不前移。

## 2. 固定接口

- TaskKey(tenant_id, project_id, task_id)；ExplorationInput(key,title,origin,goal,bootstrap_enabled=True)显式转换为原生CreateProjectRequest并计算规范化摘要。
- DispatchContext(key,runtime_config,permit,observation,control_state,execution_ready=False,active_agent_run_ids=frozenset())。ControlSource.current(key)返回它或None；复用ExecutionPermit的公共绑定/过期校验。
- AgentResult(key,operation_id,agent_run_id,intent_id,description,runtime_attempt,execution_epoch,scope_digest,config_digest)，来源先在平台侧日志记录；不包含秘密或任意原生Project ID。
- SQLAlchemyJournal(engine)：prepare_binding(key,server_id,digest)、claim_binding(key)、finish_binding(key,project_id)、set_binding_state(key,state)、get_binding(key)、list_bindings(server_id)；prepare_result(result,server_id,project_id,digest)、claim_result(key,operation_id)、finish_result(key,operation_id,fact_id)、set_result_state(key,operation_id,state)、get_result(key,operation_id)。
- BindingRecord(key,server_id,request_digest,state,project_id=None)；ResultRecord(result,server_id,project_id,request_digest,state,fact_id=None)。方法均以完整TaskKey限定归属；TaskUUID全局唯一、(server_id,project_id)绑定唯一，operation_id全局唯一并核对所属Task及摘要。
- CairnPlatformClient(server_id,base_url,timeout=10)：复用CairnClient，create_project(native_request)->ApiResult。会话禁止代理/重定向，读写原生模型；不加载本机登录态。
- CairnTaskBridge(client,journal,controls,clock)：ensure_project(input)->BindingRecord；get_project(key)->原生ProjectDetail；eligible_projects()->list[ProjectSummary]；authorize_dispatch(key)->DispatchContext；submit_result(result)->ResultRecord；reconcile_result(key,operation_id)->ResultRecord。只调用原生Core接口，不实现Agent循环。

## 3. 持久表与失败规则

日志表wuji_cairn_bindings和wuji_cairn_results属于平台扩展，不是Cairn图表。绑定pending/sent/bound/rejected/unknown；结果pending/sent/applied/rejected/unknown/conflict。使用SQLAlchemy事务、唯一约束及带state条件的UPDATE实现claim。日志提交发生在HTTP请求前，失败不自动重置sent。

表结构在包metadata中定义供部署迁移引用；导入/构造时不create_all。测试可在tmp_path创建SQLite表；生产Wuji Task外键、RLS、服务角色和迁移明确延期，不能把测试建表脚本当上线入口。

原生成功响应需验证ID/worker/描述一致性；0/5xx/解码失败为unknown，明确400/401/403/404/422为rejected，409需要核对而不重投。创建unknown不提供按名称猜绑定的修复；结果unknown仅在已知Intent/Fact和worker匹配时确认applied。取消不妨碍只读核对已发生结果，但禁止新Core写入。

## 4. 依赖与验证

固定Git依赖Cairn 8e7e0ea67552383851dfcabfba0c4e9c8d007878，subdirectory=cairn；使用其原生客户端/模型/Server，保留AGPL来源说明。SQLAlchemy版本沿用2.0.52，wuji-task-runtime为workspace依赖；不更换Pi/LiteLLM候选，不追加模型协议层。

用仓库既有uv和缓存安装可选group cairn-bridge；原生测试必须将Cairn数据库指向临时目录，禁止写用户默认Cairn数据目录。执行packages/cairn-bridge/tests和受影响的task-runtime许可用例，不跑旧API/浏览器全套。包构建仅wuji-cairn-bridge。

所有检查由主代理统一计时；本批起始剩92秒，失败同类最多两轮；不足即记录待测。Schema/RLS、真实Core服务、真实Dispatcher/Pod/Pi和模型网关联调均不计作本批通过项。
