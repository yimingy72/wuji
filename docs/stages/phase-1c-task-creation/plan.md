# D3-B 实施 Plan

状态：**approved / in-progress**；2026-09-11。用户已在Plan模式完成整体方案评审并批准实施，当前Default模式执行；本Plan为M1，连续接M2—M4。以下原计划的待审批描述已被本状态替代，最新对接见[实施合同](execution-contracts.md)。对应[Spec](spec.md)。

## 1. 开发来源与前置门槛

代码起点 276b6a8，已有 D1 aa62b9a、D2 86f927f、D3-A b6afc12；主目录 381ae3a/master 28fcd44 不动。先集成研究任务留下的四份文档，保持其确认/候选标签和实际证据；不把研究探针当平台验收。

业务实施前在应用Plan模式评审[核心闭环总计划](core-loop-plan.md)及本M1具体方案。用户的真实D3-A反馈已接收：模式切换无条件弹窗、URL与Goal混淆、模板未预填、线索字段臃肿；当前会话已经直接修复这些明确问题，不要求再次解释或重做四组原型回归。补丁不伪造整个平台或正式执行已验收。

本批由当前会话主代理负责设计、实现、集成与验收。不强制子代理；如分派，使用用户指定 gpt-6-astra/low，限定已冻结的文件和任务，不让代理补做架构决定。沿用现有工作树，可在执行时建立 codex/phase-1c-task-creation 分支；不另开开发会话。

## 2. 框架复用与增量

| 已有实现 | 复用内容 | 本批增量 |
| --- | --- | --- |
| Pydantic / SQLAlchemy / Alembic / PostgreSQL | 严格 DTO、事务、权限用户锁、RLS、迁移 | 草稿 2.0、Task 自有授权、新预览、创建快照、ready |
| D1 DraftStore | 私有草稿、全量保存/版本冲突、分页 | 双 Schema、可信模型摘要及最近创建入口，不另写草稿协议 |
| D2 ModelStore/Workflow | TenantAdmin、LiteLLM 原生管理/检查/发布/撤销 | 正式页面、创建期间读取已发布配置、模型状态协调锁 |
| B2/B3 | 原键/回执、任务分页、cancel、同任务序号与事件恢复 | 同一键空间接受新版创建，混合新旧任务返回 |
| React Router / TanStack Query / Ant Design / @wuji/theme | 路由、请求缓存、表单、五主题 | D3-A 交互抽取，接真实 API；不导入演示 Store |
| Cairn / Pi / LiteLLM | 目标链路保持原选型 | 本批不启动；只交付后续可用的真实 Goal/配置依据 |

不新增依赖主版本，不写模型 SDK、Cairn Core、通用网关、Agent 循环或模板引擎。模板是内置 JSON 资源和确定性规范化，不提供可执行表达式。

## 3. 具体文件归属

主代理独占公共契约、迁移和任何锁文件变更。本表为新文件拟议位置，当前尚未创建业务文件：

| 范围 | 文件 |
| --- | --- |
| 场景版本与输入 | apps/api/src/wuji_api/scenario_profiles.py、scenario_profiles/*.json、drafts.py |
| Web 范围 | apps/api/src/wuji_api/task_authorization.py；复用 scope_policy.py 的 URL/IP 标准化，不改变旧 evaluate_scope |
| 创建与快照 | apps/api/src/wuji_api/task_creation.py、task_creation_store.py、task_creation_routes.py |
| 草稿和模型衔接 | draft_store.py、draft_routes.py、model_store.py；新增 model_selection.py 共用版本锁/可选模型读取 |
| 旧/新任务读写 | tasks.py、database.py、main.py；仅提取必要共用回执/事件写入，不顺手大改身份模块 |
| 迁移 | apps/api/migrations/versions/20260911_0006_task_creation.py |
| 契约 | packages/contracts/openapi.yaml、scripts/generate-contracts.mjs 及其生成物/必要 fixture |
| 正式前端 | apps/web/src/features/task-creation/*、features/model-config/*、api.ts、queries.ts、pendingCommand.ts、tasks.tsx |
| 接入与回跳 | apps/web/src/router.tsx/routing.ts/pages.tsx；apps/api/src/wuji_api/security.py；关联版本检查与实际数据库版本输出 |
| 最小验证 | tests/task-creation/、定向 contracts fixture、单条正式浏览器脚本；复用已有临时数据库和测试登录设施 |
| 文档 | 本目录 Spec/Plan/Acceptance、project-context、predevelopment-plan、必要权威说明 |

新 UI 以 feature 划分，旧未变模块不迁移。范围展示组件在确认/详情共用，服务端预览为最终权威。原型可留作评审，不删除旧代码，不把其内存行为直接当生产逻辑。

## 4. 数据迁移 0006

衔接 20260911_0005，只向前兼容升级；不自动对现有开发数据库执行。业务执行时根据真实日期调整迁移文件日期只能由主代理统一处理，不占用别的分支编号。

### 4.1 草稿

task_drafts 的内容 schema 检查扩展为 1.0/2.0；保留同一 content_digest 算法前缀与 canonical JSON（版本字段本身参与摘要），不重算历史内容。增加：
- selected_model_summary jsonb nullable：仅保存服务端曾验证可选择的 ID/名称/版本；不是当前模型状态。
- last_created_task_id uuid nullable：任务归属复合 FK；只由创建事务写，普通草稿保存不改变。只有原作者且当前有 Task 阅读权限才展示入口。

模型失效查询用“当次已发布选择查询 + 已保存摘要”得出状态，不新增通用读取任意未发布模型的 project 接口。切换到新不可见 ID 清旧摘要；保存允许 unresolved。schema 2.0 的大小限制包含新增字段。

### 4.2 Task 自有授权和新预览

新增 task_authorizations：id、tenant/project/task、version=1、scope jsonb、scope_hash、valid_from/until、confirmed_by、permissions_version、confirmation_text_version、confirmed_at。scope 有显式 schema_version=1.0。只 INSERT/SELECT，无通用 UPDATE/DELETE；后续扩权需新版本，不在本批实现。

task_authorizations → tasks 用 tenant/project/task 复合 FK；tasks → 指定授权也绑定其自身 task ID，两个约束延迟到提交校验。先生成真实 Task/授权 UUID，同事务插入，不填全零 ID 或暂时删除 FK。任一对象不能挂到其他 Task 的授权。

新增 task_creation_previews：id、tenant/project/user、draft ID/version/digest、permissions_version、normalized_content、model_snapshot（可空）、input_digest、authorization_digest、blockers、can_create、created_at/expires_at。INSERT/SELECT，不原地更新预览内容；不复用旧表强制非空的 policy_id。过期预览不自动删，按后续保留策略清理，不增加无消费者队列。

### 4.3 Task 和不可变快照

tasks 增加 task_kind，默认 legacy_http 保持旧 INSERT；新值 web_assessment。增加 creation_config_snapshot_id（真实唯一 UUID）及 creation_config jsonb，快照作为 Task 行中的只读内容保存，不先建通用多表配置系统。快照 schema=1.0、摘要由规范化内容派生，内部读取器按 Task 归属提供访问。

旧 policy_id/version/hash 列对新类型可为空，原 FK 保留；CHECK 约束显式二选一：
- legacy_http：原 policy 元组全部非空、task_authorization/creation_config 全空；原 effective_scope 和路径数据保持。
- web_assessment：旧 policy 元组全空，task_authorization 非空、creation_config 完整；effective_scope 存与授权对应的规范范围，不能混入旧路径 Schema。

初始状态约束按类型分支：legacy_http queued/version1 或 cancelled/version2；web_assessment ready/version1 或 cancelled/version2。active/unknown=0、egress=not_granted 和 cleanup/assessment 原约束保持，不为未来 Runtime 先放松。

快照在 DTO/Store 严格校验并限制大小，数据库至少检查对象类型/Schema/必要键与 ID/hash。项目角色仅 INSERT 和现有状态/版本更新列，不授予改写 draft、授权、快照、归属的 UPDATE。取消只改原允许列。

### 4.4 RLS 和运行角色

草稿/预览仅本人；Task/授权/快照按现有有效租户+项目成员可读，写按 Operator 和当前主体。TenantAdmin 不因此得到项目权限。新表不允许 auth 角色、PUBLIC 或普通项目角色管理表/角色。

D2 普通成员只能读取 published/synced 模型，不为 FOR UPDATE 扩大模型 UPDATE policy。创建与管理员模型状态更新用共同 advisory lock 协调，不用表权限换锁能力。模型配置正文仍由 D2 原生版本接口维护。

更新 EXPECTED_REVISION、实际版本报告、仅受版本前提影响的 fixtures；保留 0001—0005 和原验收事实。downgrade 仅支持没有新任务/授权/2.0 草稿的隔离空库，有业务数据则显式拒绝破坏性降级。

## 5. 事务、摘要和权限并发

新创建锁顺序：用户权限锁 → 当前项目鉴权 → 原键回执 → 草稿行锁 → 模型版本协调锁 → 重新读模型/预览并校验 → 写 Task/授权/快照/回执/事件。D2 动作顺序：管理员权限锁 → 同模型版本协调锁 → 原生版本行锁 → 提交本地状态；网关 HTTP 在事务外。

单一模型版本锁由 model_selection.py 导出，键为稳定 namespace + tenant/version；各调用使用同一数据库 PostgreSQL advisory transaction lock。D2 publish/retire/revoke 及影响可选择状态的同步完成路径均遵守。锁超时返回可核对的数据库不可用结果，不自动改键提交；不在持锁时做任何付费检查。

保留 wuji-command-v1 摘要格式，但新版完整请求包含 creation_kind，旧分支不加默认新字段；因此旧回执摘要不变，新旧类型同键必冲突。服务端预览摘要另用 wuji-creation-preview-v1 前缀，包含规范草稿、配置与身份版本；授权摘要只对规范范围、期限及确认文案版本计算。对预览做摘要验证不能替代归属/权限检查。

回执读取与重放仍先鉴权；已接受命令允许按原键读旧结果，不重新执行新版前提。取消锁 Task 并检查版本/从未执行，事件顺序与 Task.version 同事务更新。快照读取可关联不可变授权，但游标必须来自读到的 Task 行，不能取事件全局最大值。

## 6. 前后端接入顺序

1. **契约与领域**：固定 v2 content、模板、Web 范围/快照、新预览与 Task 分支；扩展生成器/校验器。先生成后实现，不让前端猜字段。
2. **存储与新创建**：0006、DraftStore 增量、CreationStore 原子写入、D2 模型协调锁；将新请求分支接入同 POST /tasks。旧路径 Scope 和旧 CreateTask 保留原代码分支。
3. **读模型与恢复**：混合任务列表/快照、ready cancel、原事件/原键查询；读取旧 Task 不要求新模型/模板字段。
4. **正式创建页**：抽取 D3-A 展示组件；使用真实 saved draft 与 preview，不保留演示角色/Map/异常开关。四步输入保持和失效处理，全部关键响应经生成校验器。
5. **正式模型页**：D2 列表、服务/方案新版、显式检查、发布与撤销；组织级 loader 独立于项目 loader。管理恢复标记按 user/tenant/操作键隔离，临时 Key 不进入 sessionStorage/Query cache。
6. **路由与权限**：同步项目 drafts 和组织模型路由及回跳；身份/项目切换中止请求、升上下文代次；保留 old key 防迟到覆盖。
7. **固定候选验证**：统一暂存审查、本地代码提交，再执行下节最小检查，按实际失败只修受影响项。
8. **交付**：记录实际 SHA/run_id/命令/退出码/限制。不自动替换 4180；正式服务切换采用既有合法生命周期与增量迁移流程，保留旧数据/身份/Scope。

## 7. 验证入口与复用证据

计划命令（下列新增测试文件在实施时创建，现在没有运行）：
- `.venv/bin/python -m pytest tests/task-creation -q --tb=short`：单个自有临时 PostgreSQL，迁移 0001→0006，按 Spec C1—C4 检查；无需启动 Kubernetes。
- `pnpm contracts:check`，`pnpm exec vitest run tests/task-creation-contracts.test.mjs`：新增与旧 Task/草稿分支代表 fixture，不扩大旧全量用例。
- `./scripts/uv.sh build --package wuji-api`；`pnpm --filter @wuji/web build`。
- `pnpm exec antd lint apps/web/src/features/task-creation --format json` 和 `pnpm exec antd lint apps/web/src/features/model-config --format json`，另按单路径检查实际修改的共享文件；当前CLI已确认每次只接受一个path。
- 浏览器脚本只包含 C5 一条丢响应恢复/取消及 C6 必要表单。用现有正式测试启动路径启动隔离环境，页面/后台同一候选；不得通过修改旧运行记录 SHA 冒充新服务。固定测试端口串行，端口冲突先报告归属。
- Codex 浏览器只复核接入后的创建/模型关键页面；未改五套 token 不重新跑完整主题矩阵。

D1/D2 的已有 API/原生两协议与重启证据继续引用原 SHA；只重测本次触及的选择/撤销协调。D3-A 的桌面/窄屏/主题/四条模拟流程证明交互，不能代替正式 API 验收。新增 Goal 行为单独验证来源、自定义保存与快照，不能把旧原型报告改成已覆盖。

同类脚本问题最多两轮，失败按trace定向定位；没有累计时间预算、没有额外真实模型预算。本D3-B草案只做diff/文档链接检查，不执行这里的正式业务命令；本轮另有D3-A获准交互补丁，构建和定向检查记录在D3-A验收中。

## 8. 后续调度收口

D3-B 保存可追溯目标与配置，为 D4 提供输入；[execution-handoff](execution-handoff.md)固定提案范围和风险，不是第二阶段业务批准：
- 先真实 AgentRun/ToolCall/epoch/PermitSource，再接 Dispatcher。
- 默认建议 Reason 新增主动补证通过普通 Explore；是否首批做 Reason 内补证单独决策，不偷偷改变原生返回分支。
- 按阶段装配提示，原始结果先持久化，校验 Fact/文件/证据/尝试的来源；不动 Core。
- Task USD 网关凭据、单 Task Pod 共享 Kali、出口和停止各自有实际证据后再开放对应能力。
