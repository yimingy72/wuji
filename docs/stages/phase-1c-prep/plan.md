# Phase 1C 前置：0.5 配置与创建 Plan 草案

> **当前状态：superseded / historical draft，不可执行（2026-09-10）。** 下方旧草案正文保留历史原貌，不是当前实施计划。Token 总上限、P0 自建 Provider 生产化及 LangGraph / Deep Agents 目标链路已由 [Cairn 架构替代决策](../../cairn-architecture-decision.md) 取代；旧模型分工、强制独立 worktree 和独立测试代理规则也已失效，以根 [AGENTS.md](../../../AGENTS.md) 与 [协作流程](../../development-workflow.md) 为准。当前设计采用 Task 一对一 Cairn Project、Cairn Server / Dispatcher 与 Pi coding-agent；Agent 在平台侧运行，同 Task 多个 Agent 共用一个 Kali Runtime，LiteLLM 执行 Task 金额（USD）预算。
>
> 新阶段入口：[架构基线 Spec](../cairn-architecture-baseline/spec.md)、[Plan](../cairn-architecture-baseline/plan.md)、[Acceptance](../cairn-architecture-baseline/acceptance.md)。本轮只批准架构文档；0.5 业务未实施，后续须依据新架构重新规划。原 P0 实验及其验收证据保留；预算已用 426/600 秒、余 174 秒，4 次真实调用已用完，均不重置。以下原文中的状态、建议及待决项只说明当时草案。

## 历史草案正文

- 状态：draft / 供Plan模式评审，不可直接派发业务开发。
- 日期：2026-09-10；起点：4b3feb4；对应Spec见spec.md。
- 当前模式由应用控制。本轮只整理草案，无迁移、安装、测试、模型调用或业务代码修改。

## 1. 已固定的复用与工程边界

复用P0的ModelConfig/原生模型工厂、Provider子进程、框架消息序列化与取消等待；复用现有FastAPI、SQLAlchemy/Alembic、用户事务锁、幂等回执、任务事件/游标和前端命令恢复机制。

新增drafts、scope_confirmations、model_configuration三个路由/服务/存储模块，避免继续向main.py和DatabaseAuthority堆全部业务；只提取已有鉴权依赖，不重构旧身份/任务全模块。组织模型配置是Platform模块，原生Provider调用保持独立进程。无Redis、消息队列、图数据库或新通用Agent循环。

P0的256输出和4次额度仅属于probe。正式模型配置与检查策略分开建模，不能直接把这些常量作为Task预算。此批不运行Deep Agents任务，不解锁P0未验证的流式、压缩或恢复能力。

## 2. 接口草案

以下是需要在Plan模式冻结的候选路径与语义，不代表已发布接口；全部沿用已有会话、Origin/CSRF和实时权限检查。

| 范围 | 接口候选 | 主要约定 |
| --- | --- | --- |
| 组织入口 | GET /api/v1/tenants | 返回当前用户可见组织及组织级管理能力，不扩大项目可见性 |
| 模型服务 | GET/POST /api/v1/tenants/{tenant_id}/model-services；GET/PATCH /model-services/{id} | 管理元数据与版本；Key只写，新版本生成新secret_ref，GET不回显 |
| 模型方案 | GET/POST /api/v1/tenants/{tenant_id}/model-profiles；PATCH /model-profiles/{id}；POST /model-profiles/{id}/versions/{version}/publish | 方案绑定不可变服务版本、模型ID与检查记录；停用不删除历史 |
| 配额关系 | GET/POST /api/v1/tenants/{tenant_id}/quota-groups | 管理员明确共享关系，本批不实现生产分布式配额调度 |
| 连接检查 | POST /api/v1/tenants/{tenant_id}/model-checks；GET /model-checks/{id} | 写入模型版本与幂等键，202返回检查ID；queued/running/succeeded/failed/unknown，前端有界查询 |
| 创建选项 | GET /api/v1/projects/{project_id}/task-creation-options | 场景能力、已发布模型摘要、服务器预算默认/边界、执行不可用原因 |
| 草稿 | GET/POST /api/v1/projects/{project_id}/task-drafts；GET/PATCH/DELETE /task-drafts/{id} | 原作者权限；部分输入；expected_version条件更新；已转换草稿保留来源关联 |
| 范围确认 | POST /api/v1/projects/{project_id}/task-drafts/{id}/scope-confirmations | 固定草稿版本与规范化范围，返回不可变确认ID和有效期 |
| 预览 | POST /api/v1/projects/{project_id}/task-previews | 接收草稿ID/版本及确认ID，返回摘要、冻结输入、缺项及短期preview_id |
| 创建 | POST /api/v1/projects/{project_id}/tasks | 接收草稿ID/版本、preview_id、input_digest，复用Idempotency-Key；202回执，实际状态读取快照 |
| 任务读取/取消 | 保留现有列表、快照、commands、command-keys、events路径 | DTO扩展场景/ConfigSnapshot与ready；旧回执原样可查，pause/resume/start仍不开放 |

模型配置管理与检查是组织权限；任务创建仍依赖项目Operator权限。租户管理员能力在tenant_memberships上独立表示，不用把所有role字符串替换为管理员而破坏已有项目角色判定。具体数据库RLS、管理能力变更入口与seed身份在最终计划中固定。

新增DTO候选：TenantSummary、ModelServiceVersion、ModelProfileVersion、ModelCheck、TaskCreationOptions、TaskDraftDocument、TaskScopeConfirmation、TaskConfigSnapshot。旧TaskDraft字段名与新的持久草稿区分，避免复用旧http_observe表单作为全部场景输入。

## 3. 存储、事务与兼容

使用新迁移衔接0003；候选编号20260910_0004，执行前核对是否被其他已集成工作占用。迁移唯一owner为开发A，所有对象使用租户/项目复合归属及RLS。

草稿版本与规范化目标声明独立存储；Task冻结场景、范围、模型方案/服务版本、预算和配置schema版本。秘密只引用，不进草稿或Task JSON。已转换草稿保留task_id，重复操作返回原任务关联，不生成第二个任务。

旧Scope与queued记录原样保留；新建ready使用新schema版本。Task版号约束不再绑定固定状态版本1/2；取消仍锁Task、核对expected_version、更新事件位置。旧接口形状的新命令在升级后给出明确重新创建/预览错误，已经接受的同键重放先核对旧回执，不重新解释旧输入。

连接检查先持久化记录再派发；Provider返回只更新对应不可变配置版本的检查状态。具体作业领取/异常恢复需要按待决项固定，禁止先写202接口却没有消费者。不得复用P0文件账本冒充多用户平台检查账本。

## 4. 顺序、代理与文件归属

| 顺序 | 交付 | 负责人 | 依赖 |
| --- | --- | --- | --- |
| R0 | Plan模式解决本稿待决项，固定行为、接口、迁移和预算 | 主代理 | P0证据已具备，不追加框架验证 |
| R1 | 新五场景创建、模型配置及无模型/检查失败状态的可点击原型 | SOL/xhigh 前端代理 | R0；合成数据；用户评审后再接业务 |
| R2 | 0.5契约、生成器、迁移与权限基础提交 | SOL/xhigh 开发A | 原型交互确认；主代理冻结公共契约 |
| R3A | 模型配置/检查、草稿、范围确认、ready与兼容 | SOL/xhigh 开发A | R2 |
| R3B | 正式前端接入、列表详情、命令恢复 | SOL/xhigh 开发B | R2，与R3A独立范围并行 |
| R4 | 固定集成候选，一次最小验收与主代理复核 | Luna/xhigh + 主代理 | R3A/B完成 |

开发A独占apps/api、packages/agent-integration、迁移、契约生成器、manifest、Python/Node锁文件及根命令；开发B限定spikes/frontend/src、apps/web/src，复用packages/theme，必要主题改动提前归属B；测试代理限定本阶段定向测试及报告。主代理维护Spec/Plan/验收并集成。开发前才从当前集成基线创建独立worktree，不自动清理旧树。

## 5. 验证与交付

总预算仍为600秒，P0保守消耗426秒，余174秒；原型构建/查看、正式构建、安装、启动、检查、等待、排查都累计。不能按R1/R4或代理重置，也不把已耗真实调用额度换账本重新领取。

R1只构建一次并短走查，不跑旧12项或五主题矩阵。R4复用缓存与一次环境启动，集中执行契约检查、正式构建、合并的权限/草稿/幂等/旧数据兼容API用例、一条浏览器主流程。模型检查使用受控夹具，P0原生协议证据注明被测SHA复用。已有无影响部分不重跑。

验证入口应由一条总控命令记录UTC/monotonic起止并设剩余时间截止，finally清理自有进程和写报告；避免再次缺失完整窗口证据。具体脚本路径在R0固定，测试代理不另创第二套平台启动路径。预算不足即partial和待测，不擅自增加预算。

交付时才按既有流程停止旧主目录运行、核验未提交导航、集成候选、增量迁移/seed、启动4180并同步CodeGraph。保留身份、数据库、Scope、任务与回执；不篡改运行SHA。文档记录与实测候选SHA分开，master只在对应基线已验收后按原规则处理。

## 6. R0必须收口的决策

用户已确认无模型只能保存草稿，补齐可用方案再创建。以下为主代理在Plan模式继续收口的技术决策，不重复询问已确认产品行为：

1. 本机私有凭据后端还是本批Kubernetes Secret接入；前者复用P0最快，后者需额外限定Secret权限与生命周期，不能误用Runtime Controller权限。
2. 服务端任务Token/时间预算默认值与硬上限来源，避免从probe复制数字。
3. 发布是否强制同版本连接成功；本草案推荐强制，但连接成功不证明工具能力可执行。
4. 模型检查消费者采用API托管受限子进程还是独立Gateway作业进程，并明确版本、恢复、幂等及既有本地生命周期接入。

上述未决项未解决前不标approved、不派发业务开发。
