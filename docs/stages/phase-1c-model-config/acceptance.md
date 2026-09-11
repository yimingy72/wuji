# D2 组织模型配置验收

- D2后端/原生网关最小链路：accepted；日期2026-09-11。
- 最终实现及打包候选：`86f927f487a21009170b9b7b51ccafe7c377aace`；基准d84b2f5，分支codex/phase-1c-model-config。
- run_id：`model-config-d2-20260911`；[Spec](spec.md)、[Plan](plan.md)。本文是后续文档提交，自身SHA从git log追溯。
- 主代理独立设计、实现HTTP适配/流程/接口/契约并执行验收；gpt-6-astra/low子代理按固定范围实现存储/迁移、部署入口、测试夹具，未设计架构或独立执行验收。

## 1. 已交付

TenantAdmin独立授权与CLI，组织查询，模型服务/方案及不可变版本，稳定幂等键和操作查询（含原键恢复），显式连接检查，发布/停止发布/安全撤销，以及项目已发布模型选择接口。配置单价由管理员提供，平台组织配置不设置Task预算。

Wuji通过原生LiteLLM Credentials/Model/Health接口执行，不重写厂商协议；服务Key不存Wuji表或公开返回。配置原生ID按实例/租户/版本绑定，丢失创建响应可只读核对；检查响应丢失不再次发请求。已撤销版本即使原生block失败，也从平台选择列表移除并保留未知同步状态。

迁移0005衔接0004；原有Task仍queued/cancelled，不开放start。新增OpenAPI/生成校验器保持0.5.0开发候选，完整任务控制面及前端未交付。

## 2. 真实结果与SHA

| 范围 | 结果 | 被测版本及证据 |
| --- | --- | --- |
| M01 权限 | passed | ad17a15：真实PostgreSQL/session/RLS；非admin、跨租户、撤权拒绝；管理员不隐式得到项目访问；auth无模型表权限 |
| M02 保存/重放 | passed | ad17a15：版本创建/分页/同键回放及异输入冲突；密钥正文不在Wuji表或公开响应中，保存不触发检查 |
| M03 原生两协议 | passed | e91f5b9：固定原生LiteLLM+合成OpenAI/Anthropic，真实Wuji API及数据库完成服务/方案保存、指定模型检查、发布 |
| M04 发布门槛/unknown | passed | ad17a15：缺价、未检查新版本、检查结果不明不能发布；丢失创建响应只读恢复；丢失检查响应后重放/查询无第二次检查 |
| M05 选择/撤销 | passed | ad17a15：普通项目成员只能选择published/synced版；retire及revoke移除选择，block失败仍本地revoked/同步unknown |
| M06 重启/部署结构 | passed（见边界） | e91f5b9：原生网关重启后两协议再检查成功；2项无集群结构检查核对固定镜像/探针/Secret分离/schema v1及UID条件删除的stopping语义 |
| 契约检查 | passed | 602a27f：TS与standalone validators一致，OpenAPI lint通过，3条既有警告 |
| API sdist/wheel | passed | 86f927f：0.5.0包构建成功，声明已使用的httpx0.28.1运行依赖 |

5项配置API测试通过，另1项原生链路与2项部署结构检查通过，共8项定向测试。后续86f927f只把已安装/已被测试的httpx0.28.1声明为API运行依赖，无运行源码变化，未因此重跑整个验证。契约之后的修复也未修改DTO、路由或生成内容，复用602a27f证据，不冒称全部在最终SHA重新执行。

## 3. 命令、环境与修正

Python3.13.15，Wuji测试库为本机PostgreSQL16.14；原生网关独立PostgreSQL16-alpine容器，应用角色NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOBYPASSRLS，原生迁移成功。网关镜像：

`ghcr.io/berriai/litellm@sha256:c8756e7b9a61fe45df2ccb5b781d388c3b2f3a21ef9e4956630caef20f9f03aa`

| 命令 | 退出码 | 实际结果 / 命令墙钟 |
| --- | --- | --- |
| `pytest tests/model-config/test_models.py -q --tb=short` 初轮 | 1 | 迁移JSON默认值中的: null绑定问题，业务用例尚未执行；4.628秒 |
| 同一定向命令，修正后 | 0 | 5 passed；5.424秒 |
| `pnpm contracts:check` | 0 | 生成一致及lint通过；4.029秒 |
| `pytest tests/model-config/test_native.py -q --tb=short` 初轮 | 1 | 原生服务完成迁移/启动，但宿主机无法通过Docker internal网络映射端口访问；134.109秒 |
| `pytest tests/model-config/test_native.py tests/model-config/test_deployment.py -q --tb=short` 修正后 | 0 | 3 passed；109.769秒 |
| `uv lock --offline` | 0 | 仅添加已有httpx0.28.1为API直接依赖，未新增/升级包版本 |
| `uv build --package wuji-api --out-dir artifacts/phase-1c-model-config/dist --offline` | 0 | sdist/wheel完成；0.848秒 |

pytest由工作树.venv/bin/python -m执行；uv来自主目录既有工具链并--directory到本工作树。原始命令/完整SHA/退出码/耗时见忽略目录`artifacts/phase-1c-model-config/`下api、api-fixed、contracts、native、native-fixed、build的JSON及log。

迁移问题已将默认结果改为合法空JSON，公开DTO仍返回明确null用量/费用。网关测试保留封闭Docker内部网络，改用docker exec/stdin在容器内发真实HTTP并回传响应，未用MockTransport冒充原生服务；该传输只属于夹具，不进入产品。原生启动失败诊断在私有脱敏日志保留，未放宽为可访问公司网关的测试网络。

原生测试共4次合成推理：两协议初次各一次，重启后各一次；保存、发布、readiness和重启本身均未增加推理计数。公司网关与真实模型调用0次，原P0四次额度不改写。原生health未提供本次用量/费用，API保持null，不推算为零。

## 4. 资源与兼容边界

两个原生测试尝试均完成自有容器/网络清理，结束后按fixture ownership label检查无残留；本机临时PostgreSQL也由fixture停止删除。保留缓存镜像和忽略目录证据，未修改用户现有集群、主开发数据库或工作台。

Kubernetes入口为`./scripts/platform/gateway.sh prepare|up|status|down --run-file ABS`，依赖正常项目工具链和当前SHA生成的私有run；可用当前已同步.venv直接运行gateway.py。它复用既有ownership/进程登记、固定18400/18402端口、独立native数据库及角色、三个持久Secret。开发网关实例以共同Git目录+namespace稳定派生，不因新run_id重置；测试实例再绑定run_id隔离。down保留持久数据，删除接受仅表示stopping。

本轮**未在真实Kubernetes中执行gateway up/down或端口转发**，只交付入口并通过定向结构检查；原生服务启动/迁移/协议/重启已在实际固定Docker镜像验证。不能把这条证据扩大为Kubernetes完整生命周期或网络隔离验收。

schema v1增加可选网关对象，旧无网关记录/三项API凭据scope仍可读；API只接收管理URL/key/instance，不接收网关DB凭据或salt。迁移管理命令返回真实alembic_version，修正旧0003显示。当前树没有CodeGraph索引，使用rg/直接读取，不以主目录旧索引当作本分支事实。

## 5. 交付状态与后续

主业务仍381ae3a、master仍28fcd44，当前开发树保持独立。前端配置原型/正式页面未接入，D3的范围确认、配置快照及ready/start、D4执行账本仍待实施；已发布模型仅表示配置发布，不表示Pi、Task金额限制或目标执行已经验收。

本批使用已有用户锁序列化一次有界管理操作，project事务不跨HTTP；权限变更会等待已接受管理操作结束。它不是未来Task执行停止机制。网关实例替换、原地管理修改和丢失创建结果不能按相似名称猜关联；未核对状态保持unknown。当前同操作记录的写回限定原提交者，其他管理员可读；离职操作者遗留unknown的管理修复入口尚需后续细化。

模型价格由管理员填写并固定版本；特殊阶梯、免费预算豁免、真实费用对账、任务虚拟Key金额限制、Pi/Cairn调度、Kali/出口、长断线和完整主题矩阵均未验收。本批必要检查通过后停止追加回归。
