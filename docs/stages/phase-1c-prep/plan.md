# Phase 1C 前置开发 Plan

> 已批准的第一批现以 [P0 Spec](../phase-1c-prep-p0/spec.md) / [Plan](../phase-1c-prep-p0/plan.md) 为准；本文件中的其余新版创建/配置业务仍需细化，不因P0实施自动获批。

状态：draft / 需修订；以下任务表尚不是可派发的开发任务书。实施须先按应用 Plan 模式完成具体方案评审；此文件不表示原型或业务开发已经启动。

## 最新确认的修订输入

本文件原基准为 `95c5ed3`，最新文档来源见 [背景索引](../../project-context.md)。用户已确认基础模型配置页面、组织共享/管理员维护及创建者确认范围。下表是原顺序草案，必须补齐模型配置与检查后重新完成方案评审；不得依据原表跳过这些能力。

需要显式完成框架复用映射：模型客户端使用既有成熟 Provider 集成，连接检查和将来的 Harness 共用接入能力；不自写协议/SSE/摘要循环。配置存储、发布快照、TenantAdmin 权限、密钥隔离、QuotaGroup 与任务预算是平台补充。Deep Agents 仍是优先验证候选，不因配置页面提前交付就标为集成完成。框架版本、实际能力与 Gateway 边界在具体方案中固定。

## 1. 交付顺序

| 顺序 | 工作 | 负责人 | 交付检查点 |
| --- | --- | --- | --- |
| P1 | 修正场景目录、Web 四步及其他场景差异原型 | 开发 B：SOL/xhigh | 用户可评审最新交互；无模型/网络执行 |
| P2a | 冻结创建选项、草稿、配置快照、ready 和兼容迁移契约 | 主代理决策，开发 A：SOL/xhigh | 合同提交供前后端共用；字段、权限、失败语义明确 |
| P2b | 草稿存储、创建 ready、取消、旧任务兼容、场景能力读取 | 开发 A：SOL/xhigh | 真实 API 与增量迁移，无执行入口 |
| P2c | 原型交互接入 apps/web，列表/详情与回执恢复 | 开发 B：SOL/xhigh | 真实配置管理闭环 |
| P3 | 一次定向验收、主代理审查、记录与本地交付 | Luna/xhigh + 主代理 | 集成候选、证据、剩余限制和 4180 入口 |

P1 → 交互确认 → P2。确认前可以准备契约草案，不提前做后端业务开发。P2a 固定后，P2b/P2c 才并行；不让前端代理猜 DTO。P3 只有一个集成候选，必要修复只复测受影响项。

## 2. 文件归属与 Git

- 文档来源分支 `codex/product-interaction-plan`，当前设计基准 `95c5ed3`；主工作区代码基准 `381ae3a`。执行时复核实际 HEAD、未提交改动和运行服务，不移动正在运行且绑定 SHA 的主工作区。
- 主代理负责阶段集成分支 `codex/phase-1c-prep`、Spec/Plan、冲突解决和验收。保留 master 和 Phase 1A partial 状态。
- 开发 A worktree/分支：`work/worktrees/phase-1c-prep-server` / `codex/phase-1c-prep-server`；独占 `apps/api/**`、迁移目录、`packages/contracts/**`、`scripts/generate-contracts.mjs`、manifest、锁文件及根命令。
- 开发 B worktree/分支：`work/worktrees/phase-1c-prep-web` / `codex/phase-1c-prep-web`；限定 `spikes/frontend/src/**`、`apps/web/src/**`；共享主题原则上复用，需要修改时提前归属给 B。不能改契约、锁文件、迁移或服务脚本。
- 独立测试 worktree/分支：`work/worktrees/phase-1c-prep-test` / `codex/phase-1c-prep-test`；只负责对应 API/浏览器测试和证据报告，不独立改变产品行为。
- 开工时才创建这些 worktree 和代理。最多两个开发、一个测试并行；指定模型不可用时报告，不替换。Agent 任务书包含实际基准 SHA、绝对目录、文件范围、Spec/Plan、共享预算与交付格式。
- 主工作区有索引则 CodeGraph 优先，确认工作树与新鲜度；新 worktree 无索引时回退 rg/直接读取；业务最终集成后同步主索引。

## 3. 开工前必须固定的具体契约

本轮给出任务计划，以下决策在 Plan 模式完成；未固定前不能派代理自行填空：

1. 场景目录/创建选项读取、部分草稿 CRUD、草稿版本与预览绑定的请求/响应和错误码。
2. 草稿权限及幂等保存/创建转换方式；Task 配置快照兼容当前 TaskSnapshot、分页和事件游标。
3. 场景及配置引用的来源：组织级基础模型配置、已发布方案与真实能力状态、缺失模型/环境的 UI 表达；其他能力不扩成全部配置中心。模型管理权限沿用 TenantAdmin 目标设计，当前运行角色的具体映射与迁移仍需固定。
4. 域名级 Scope 与历史路径 Scope 的并存/批准入口；创建者确认任务范围的职责、事务边界与当前项目角色的映射；不继续沿用“仅管理员预导入”的旧草案。
5. 基础模型配置管理、显式连接检查的接口与错误语义、原生客户端参数映射、凭据保存/访问边界、配额与检查预算；模型目录、上游可用性和已验证能力分开展示。
6. 旧 queued 任务如何保留原版本/回执并阻止自动执行，新状态如何升级已发布校验器。增量迁移编号在实际主线复核后分配。

流量控制产品选型、TLS 采集、CNI、代理池、候选 IP 主动核验、DNSLog、凭据共享、Worker 循环参数不属于本前置任务的决策前提。只保留后续挂接的对象边界，不发布空壳执行 API。

## 4. 最小验证与预算

P1/P2/P3 总共 600 秒，安装、启动等待、构建、测试排查与复跑均计入；不是每个子步骤各 10 分钟。预算由主代理记录一个累加表，计划留至少一半给集成主流程，任何代理不得自主开全量套件。

- P1：一次 `pnpm --dir spikes/frontend build` 和短浏览器走查；必要 `pnpm exec antd lint spikes/frontend/src --format json`。不跑旧原型 12 项。
- P2/P3：一次 `pnpm contracts:check`、`pnpm build:platform`；相关前端的 antd lint。冻结依赖安装只在需要时做一次。
- 定向 API 入口拟为 `./scripts/uv.sh run --frozen pytest tests/api/test_phase1c_configuration.py -q`，浏览器入口拟为 `WUJI_BROWSER_CHANNEL=chrome pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/07-task-configuration.spec.ts --workers=1`。两文件是计划新增，当前不存在，不写作已通过。
- 测试环境沿用现有受管启动路径与固定端口，由一名负责人串行管理；API/浏览器共用同一次启动，不重复生命周期检查。具体 run-file 在执行时生成并绑定实际候选。
- API 合并覆盖草稿版本/权限、幂等创建、ready 取消、旧 queued 与旧 Scope；浏览器一条保存→刷新→创建→列表/详情→取消流程。P1 已确认的纯展示不再在正式版本重跑五场景/五主题矩阵。
- 通过即停止。同类脚本问题最多两轮；达到预算后清理自有测试进程并记录待测，关键未通过则不开执行能力、不标 accepted。

## 5. 本地交付与后续顺序

代码集成后按现有启动/停止流程切换正式 4180 工作台，先停止旧 SHA 所属进程再迁移和启动；保留数据库/身份/Scope。原型 4185 与正式入口用途明确。独立报告绑定被测业务 SHA、测试脚本 SHA、run_id、命令/退出码；后续文档提交不伪装同一个被测提交。

之后单独规划 Phase 1C Runtime/执行与证据，再进入 Phase 2 Harness + 单 Agent + 最小黑板，最后扩展多 Agent 和其他场景。真实目标访问前再确定并验证流量控制边界，本轮不展开该选型。
