# 控制面 D1 验收

- D1结论：accepted / 独立草稿后端最小验证通过；日期2026-09-11。
- 整体0.5控制面：partial，D2模型配置、D3配置快照/ready/start、D4权威执行账本尚未实施。
- 被测候选：`aa62b9a6a3b8ec57edffc794b7bc6455e1babb9f`；分支codex/phase-1c-control-plane，起点1da3ec6。
- run_id：`control-plane-d1-20260911`；[Spec](spec.md)、[Plan](plan.md)。本文为后续文档提交，自身SHA从git log查询。
- 设计、集成、审查和测试执行：主代理；gpt-6-astra/low子代理按固定接口分别实现存储/迁移、测试夹具，不设计架构；不称为独立测试执行。

## 1. 已实现与最小验证

新增独立task_drafts表和3个草稿API：PUT保存、GET详情、GET列表。五类场景均可保存不完整输入；模型/金额可空，字段填写后执行本地格式校验。所有草稿属于当前用户与项目，不产生Task/Cairn Project、授权、模型请求或执行。公开契约保留旧TaskDraft，新增SavedTaskDraft/SavedTaskDraftPage和对应生成校验器。

| 验收 | 结果 | 实际证据 |
| --- | --- | --- |
| D01 | passed | 五场景无模型保存/读回；规范化名称/URL/金额；URL凭据、fragment、金额类型/精度/零值、NUL、未知字段、双源码来源及内容大小拒绝 |
| D02 | passed | PostgreSQL真实执行0001→0004迁移；保存/紧邻同请求重放/更新/旧版本409、列表分页及游标用途/项目隔离；tasks/回执/事件/授权表没有草稿副作用 |
| D03 | passed | 实际session与分离运行角色；他人/跨项目/跨租户404，Viewer读自身旧草稿但写403；无上下文RLS零行、auth无表权限、project不得改归属；Origin/CSRF/会话及鉴权后权限版本变化受保护 |
| D04 | passed | 每类响应按OpenAPI本地JSON Schema验证；生成TS/standalone校验器与契约一致；API sdist/wheel构建成功 |

没有将读取Cairn/Pod或模型作为草稿校验的一部分。新增权限为task.draft.read与task.draft.write，不赋予TenantAdmin或扩大Scope权限。

## 2. 环境、命令、退出码

Python3.13.15，PostgreSQL16.14（本机既有Homebrew二进制），uv0.12.11，pnpm10.32.1/项目Node24.20.0。单个临时PostgreSQL目录权限700，随机本机端口和随机测试凭据，实际创建独立migration/auth/project角色并迁移；ASGI请求复用真实会话表，不启动Web、OIDC或Kubernetes服务。fixture的finally已成功停止自有数据目录并删除临时文件。

| 命令 | 退出码 | 结果 / 命令墙钟 |
| --- | --- | --- |
| `pnpm install --frozen-lockfile --ignore-scripts` | 0 | 当前树尚无node_modules，202个包来自缓存，报告2.8秒；无依赖升级 |
| `uv lock --offline` | 0 | 仅wuji-api/workspace版本0.4.0→0.5.0；0.107秒 |
| `uv sync --frozen --group cairn-bridge --offline` | 0 | 更新本工作树editable元数据；0.565秒 |
| `.venv/bin/python -m pytest tests/control-plane -q --tb=short` | 0 | 5 passed，pytest3.83秒，命令5.676秒 |
| `pnpm contracts:check` | 0 | 生成内容一致及OpenAPI lint通过，3.412秒；保留3条旧警告 |
| `uv build --package wuji-api --out-dir artifacts/phase-1c-control-plane/dist --offline` | 0 | sdist/wheel成功，0.797秒 |

uv由主目录work/toolchain/bin/uv执行，--directory指向当前工作树；缓存/受管Python沿用既有工具链。完整被测命令、SHA、退出码及耗时见忽略目录`artifacts/phase-1c-control-plane/{api,contract,build}.json`及对应log。包产物位于同目录dist。

契约准备时修正了新增YAML片段与原文重复anchor命名；未改旧路径或错误响应。另一次准备检查后，为准确表达互斥源码输入补齐Schema，再在最终候选执行上表契约检查。没有API测试失败或复跑，没有重跑旧完整API/浏览器/Kubernetes矩阵；所需检查通过后停止。

## 3. 主代理审查

- 写入使用现成用户事务锁，当前项目权限和permissions_version复核在数据库事务内；先授权再处理重放。主键防止并发新建重复，行锁避免更新覆盖。
- 紧邻重放只在当前version=expected_version+1且规范化摘要相同时确认；存在后续版本时409，不倒退、不伪造旧回执。
- 迁移只新增草稿表，不修改旧tasks/preview/回执/事件；按列授予运行角色更新权限，不能改变归属。SQL错误转现有脱敏依赖错误。
- 保存内容不接受凭据字段；引用ID只是未确认草稿选择，生产模型发布/Scope确认/Artifact权限仍要在正式创建时重新验证。
- 与基准契约对比，所有旧paths及旧schemas内容保持相同，仅Permission增加草稿权限。新schema未覆盖旧TaskDraft。CursorCodec既有tasks用途保持默认，草稿使用独立task_drafts用途。
- 当前工作树无CodeGraph索引，按规则rg/直接读取；未用主目录旧索引判断候选实现。

## 4. 交付边界与下一步

主目录仍为381ae3a、master仍28fcd44；0.5.0是开发候选，不宣称完整0.5平台已发布。当前开发数据库、旧任务、用户和Scope未迁移或重置。迁移随本工作树源代码交付，API wheel本身不替代迁移与部署工程。新版创建页面尚未制作/评审/接入，草稿暂通过API使用。

后续顺序为D2 TenantAdmin和LiteLLM模型配置/显式检查/发布，D3草稿正式创建/授权确认/快照/ready/start，D4执行代次和AgentRun/工具账本及Dispatcher接线。正式start必须有真实消费者和准入条件，不能先返回202后空转；旧queued仍不得自动执行。Cairn黑板核心、Pi/LiteLLM目标选型和单Task Pod双容器架构保持。

本批未验证生产部署、真实模型费用、目标出口、Pi工具或Kali进程停止；真实模型和目标请求为0。P0原4次调用记录保留，不因取消检查时间预算增加付费检查。压力、长期断线和完整主题回归未执行。
