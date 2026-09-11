# 本地工作台

Phase 1A 功能已集成，完整验收当前为 partial：最近一次独立检查中 API 73/73、生命周期 6/6、Chrome 12/15 通过，3 个真实 Keycloak 回调场景仍待集中测试。实际结论见[阶段验收](stages/phase-1a/acceptance.md)和[待测清单](stages/phase-1a/deferred-tests.md)。

## 环境与入口

使用本机 Docker Desktop 已启用的 Kubernetes：Docker context 为 `desktop-linux`，Kubernetes context 为 `docker-desktop`。PostgreSQL 与 Keycloak 运行在专属命名空间，本地进程运行 API 和前端。

| 环境 | 工作台 | API | Keycloak | PostgreSQL | 命名空间 |
| --- | --- | --- | --- | --- | --- |
| 开发 | http://127.0.0.1:4180 | http://127.0.0.1:8000 | http://127.0.0.1:18080 | 127.0.0.1:15432 | wuji-dev |
| 独立测试 | http://127.0.0.1:4182 | http://127.0.0.1:8002 | http://127.0.0.1:18082 | 127.0.0.1:15434 | wuji-test |

原型仍使用 `pnpm dev` 和 http://127.0.0.1:4173。正式工作台使用数据库中的身份与项目，保留登录、项目访问和五套主题。B2/B3新增任务创建、查询、取消和事件同步；交付状态见[B2/B3验收](stages/phase-1b/b23-acceptance.md)。381ae3a开发基线仍不执行任务；当前0.5候选在独立4182按文末封闭夹具流程运行Cairn/Pi/Kali。

## 首次准备

首次检出或冻结依赖变化后，在仓库根目录执行：

```sh
./scripts/bootstrap-toolchain.sh
./scripts/uv.sh sync --frozen
pnpm install --frozen-lockfile
```

工具链和依赖版本由仓库固定。Python 使用项目的 `scripts/uv.sh` 入口。

## 普通启动

终端一启动基础设施和本地转发，并保持前台运行：

```sh
pnpm dev:infra
```

`dev:infra` 输出就绪信息后，在终端二准备迁移、身份和种子，再启动工作台并保持前台运行：

```sh
pnpm dev:seed
pnpm dev:platform
```

每次 `dev:infra` 创建当前开发 run 后都执行一次 `dev:seed`。打开 http://127.0.0.1:4180，选择“使用组织账号登录”。

开发账号保存在本机私有文件 `work/run/dev.json` 的 `seed_users` 中。以下命令只读取一个账号的登录字段；可将 `single_a` 改为 `dual_ab` 或 `no_projects`：

```sh
WUJI_ACCOUNT=single_a ./scripts/uv.sh run --frozen python -c 'import json, os; user=json.load(open("work/run/dev.json"))["seed_users"][os.environ["WUJI_ACCOUNT"]]; print("username:", user["username"]); print("password:", user["password"])'
```

`single_a` 对应单项目身份，`dual_ab` 用于跨租户项目与翻页，`no_projects` 用于空列表。凭据只在本机终端读取，不要复制整个运行文件到聊天、日志或 Git。

工作台右上角可以切换雾银、冰蓝、青瓷、亮石墨和原石墨，主动选择会保存到本机浏览器。`?theme=glacier` 等比较链接只临时覆盖当前标签页。

## 停止

在第三个终端停止本次运行，或对前台命令使用 Ctrl-C：

```sh
pnpm dev:down
```

普通停止保留集群对象、Secret、PVC 和业务数据。命令仅清理经核验属于当前运行的进程；遇到端口占用会报告失败。更新代码前先停止旧版本的开发进程，更新后重新启动，避免私有运行记录的提交 SHA 与工作树不一致。

## 检查入口

日常开发只执行覆盖当前改动的最小检查：文档改动检查 diff；契约、API 或前端改动分别选择 `pnpm contracts:check`、`pnpm check:api` 或 `pnpm --filter @wuji/web build`。跨模块改动按实际影响选择检查，不默认串行运行全量 `pnpm check:platform`；直接修改生命周期时才运行 `pnpm test:platform:lifecycle`。

`pnpm test:platform` 是显式安排的集中全量验收入口，不与前述命令默认串行执行。它在 `wuji-test` 为本次运行创建独立数据库和 realm，不清空开发数据或上次运行的数据；协议夹具占用 18083，空迁移库探针占用 8003。最近一次全量运行仍有 3 个回调用例待测，不能据此标记完整通过。

运行与验收证据保存在 ignored 的 `artifacts/phase-1a/`，私有运行记录在 `work/run/`。最终验收报告记录候选提交 SHA、run_id、命令、退出码及未通过项；本机证据不随 Git 提交分发。

## 批准范围、预览与任务（B2/B3）

用 `single_a` 登录后进入项目的任务列表，点击“新建任务”，选择批准范围并填写任务名称与目标 URL，生成预览后创建任务。开发种子包含本机协议夹具 origin、根路径与 `/admin` 排除路径；界面展示具体 origin。预览只计算范围和有效限额，不访问目标。旧B1预览必须重新生成。Viewer可以查看范围和任务，不能预览、创建或取消。

本批新任务状态为queued，取消后为cancelled，尚未接入实际执行。详情从服务端读取Scope版本、当前状态及变更记录，刷新可恢复。创建或取消结果不明时，页面保留“提交结果待确认”；刷新后点击“核对提交结果”按原键查询。404仍代表结果待确认。刷新已丢失原请求正文，不能直接重送；查看任务列表后，可明确放弃旧核对再发起新操作。标签页不保存目标URL、请求正文或凭据，关闭标签页会丢失核对标记；已创建任务仍保存在数据库中。

B2/B3基线的`dev:seed`执行至`20260910_0003`；当前0.5候选执行至实际迁移头`20260911_0007`，管理命令返回实际版本。迁移 并幂等添加三个开发项目的范围，保留既有数据库、身份、范围和任务。管理侧导入使用当前私有运行文件与绝对 JSON 路径：

```sh
./scripts/platform/control.sh --run-file "$PWD/work/run/dev.json" scope import --file /absolute/path/scope.json
```

JSON 顶层为 `authorization` 与 `scope`：前者包含 `id`、`tenant_id`、`project_id`、`subject`、`basis`、`approved_by`、带时区的 `valid_from` / `valid_until`；后者包含 `policy_id`、正整数 `version`、`label`、`origins`、`allowed_path_prefixes`、`excluded_path_prefixes`、`allowed_methods` 与六项 `limits`。字段约束见 `apps/api/src/wuji_api/scopes.py`。项目必须已经存在；相同版本相同内容重复导入不新增记录，同版本内容变化会被拒绝，应使用新版本。此入口仅供本机管理，不暴露为公开 API。

B1 定向验证入口为 `tests/unit/test_scope_policy.py`、`tests/api/test_phase1b_scopes.py` 和 `tests/platform-browser/05-scope-preview.spec.ts`。真实 API / 浏览器检查共用 `test-platform.sh --serve-only` 创建的隔离环境；不自动运行 Phase 1A 全量用例。当前交付状态以 [B1 验收记录](stages/phase-1b/acceptance.md) 为准。

B2/B3的必要验证限定为`tests/api/test_phase1b_tasks.py`和`tests/platform-browser/06-task-management.spec.ts`，加一次契约检查与正式构建。通过即停止，不串行补跑旧全套。实际候选、命令、预算和延期项见[B2/B3验收](stages/phase-1b/b23-acceptance.md)。

## 组织模型网关（D2）

网关固定使用 LiteLLM v1.100.0 `ghcr.io/berriai/litellm@sha256:c8756e7b9a61fe45df2ccb5b781d388c3b2f3a21ef9e4956630caef20f9f03aa` 及原生迁移，依赖现有已启动的专属 PostgreSQL、可用数据库转发、项目 Python 依赖与 Docker Desktop Kubernetes。它单独保存 native 数据库，使用无平台角色成员关系的专属登录角色。开发端口为 `18400`，测试端口为 `18402`。

使用当前工作树、当前提交创建的私有 run 文件：

```sh
./scripts/platform/gateway.sh prepare --run-file "$PWD/work/run/dev.json"
./scripts/platform/gateway.sh up --run-file "$PWD/work/run/dev.json"
./scripts/platform/gateway.sh status --run-file "$PWD/work/run/dev.json"
./scripts/platform/gateway.sh down --run-file "$PWD/work/run/dev.json"
```

`prepare` 增加 schema v1 可选的 `model_gateway`，创建并复用三个持久 Secret：管理 key、加密 salt 和数据库密码。只有管理 key 写入 0600 run 文件；salt、数据库密码只存 Kubernetes Secret。中断后使用相同 run 重试，已有配置缺 Secret 时拒绝自动轮换。禁止手改旧 run 的 source SHA 来绕过版本核验。

`up` 包含准备、单副本 Deployment/Service/ConfigMap 和自有 loopback 转发，等待 `/health/readiness`。探针只使用原生 liveliness/readiness，关闭重试、fallback、缓存、后台模型健康检查和外部遥测，不导入上游凭据或请求付费模型。`down` 只停止可核验的自有转发，并以 UID/resourceVersion 前置条件删除该实例 Deployment，保留 Secret、数据库、PVC、Service 和 ConfigMap；删除被接受时返回 `state=stopping`，随后 `status` 确认 Deployment 不存在且转发进程组已结束，才返回 `state=stopped`。平台停止前先停止网关。

网关命令不运行 Wuji 迁移、不重启 API。准备后按现有平台启动流程启动 API，它才会接收网关 URL、管理 key 和实例 ID，并在进程记录中添加 `model_gateway_management` scope。旧三项 scope 和没有网关的旧 schema v1 文件保持可读。上游 Base URL 使用 API Settings 的受限默认值；合成上游覆盖仅由显式 `local-test` 验证环境配置。本批原生部署的实际验证状态见 D2 验收记录。

当前独立工作树已同步Python环境时，也可用`.venv/bin/python scripts/platform/gateway.py <action> --run-file ABS`运行同一入口；shell wrapper要求该检出已完成工具链bootstrap。TenantAdmin由可信管理CLI的`tenant-admin grant|revoke --user <seed-symbol> --tenant <seed-symbol>`显式设置，不自动提升Operator。

## 核心闭环候选（wuji-test / 4182）

在`codex/phase-1c-core-loop`所在检出执行；保留4180和开发数据库。当前入口只运行自建HTTP夹具，模型上游为合成协议服务，不产生公司模型费用。Task授权目标为`http://wuji-core-fixtures:8000/`，通过同版本检查并发布合成方案后才能启动；外部目标创建不等于获准在此执行。

构建三个本地镜像（固定Pi/Cairn与基础摘要；首次准备需已同步锁定的Cairn依赖缓存）：

```sh
docker --context desktop-linux build -t wuji-task-agent:core-loop -f services/task-workers/Dockerfile.agent .
docker --context desktop-linux build -t wuji-task-kali:core-loop -f services/task-workers/Dockerfile.kali .
sh scripts/platform/build-core.sh
```

终端一保持前台，正常生命周期生成私有运行记录并完成0007迁移/种子/身份/工作台：

```sh
.venv/bin/python scripts/platform/lifecycle.py test-platform --serve-only --run-file-out "$PWD/work/run/core-final.json" --event-file "$PWD/artifacts/phase-1c-core-loop/lifecycle-final.jsonl"
```

终端二配置现有网关及测试身份；所有命令核对当前检出/提交，禁止手改run.source_sha：

```sh
.venv/bin/python scripts/platform/gateway.py up --run-file "$PWD/work/run/core-final.json"
.venv/bin/python scripts/platform/control.py --run-file "$PWD/work/run/core-final.json" api restart --profile issuer_fixture
.venv/bin/wuji-manage --run-file "$PWD/work/run/core-final.json" tenant-admin grant --user single_a --tenant tenant_a
```

通过正式模型页面保存OpenAI兼容服务`http://wuji-core-fixtures:8000/v1`（任意测试专用Key）和模型`wuji-fixture`方案，填写明确合成价格与容量。取方案版本ID，然后启动真实Core服务：

```sh
.venv/bin/python scripts/platform/core.py prepare --run-file "$PWD/work/run/core-final.json" --model-profile-version-id <方案版本UUID>
.venv/bin/python scripts/platform/core.py up --run-file "$PWD/work/run/core-final.json"
```

此时模型页面显式检查并发布。4182使用组织登录进入测试fixture的single_a身份；创建Web任务、填写未来授权截止时间、选择合成模型和USD预算、确认范围，创建后显式启动。黑板、时间线、工作区展示实际执行记录，登记证据按项目权限读取。配置页的价格为合成检查规则，不能沿用到公司模型。

停止先取消活动Task并等待真实停止状态，再依次运行`core.py down`、`gateway.py down`（同一--run-file），最后在serve-only终端Ctrl-C。保留测试数据库、身份、Cairn及Artifact PVC，停止不删除历史证据。更新代码前先停旧服务；新候选使用正常生命周期生成新run，不修改旧记录绕过版本核验。验收细节见[核心记录](stages/phase-1c-task-creation/acceptance.md)。


上述D2保存、Core启动和一次显式合成检查/发布也可用单独入口完成：

```sh
.venv/bin/python scripts/platform/core-fixture-setup.py --run-file "$PWD/work/run/core-final.json"
```

该命令要求网关、issuer_fixture API和TenantAdmin已准备，固定自建合成上游；会保存0600原操作标识，结果不明只核对，不再次发起检查。浏览器登录前执行，避免同一测试用户新登录撤销原浏览器会话。


## W1 有限Web评估

有效开发检出为`work/worktrees/phase-2-web-assessment`。沿用上面的test-platform --serve-only、gateway up、issuer_fixture API restart及TenantAdmin grant顺序；迁移头为0008。固定4182串行使用，不能与旧测试run并行占用端口。开发4180保持原样。

额外构建独立站点镜像：

```sh
docker --context desktop-linux build -t wuji-web-assessment-lab:w1 -f services/web-assessment-lab/Dockerfile .
```

现有Agent/Kali/Core镜像仍用前述命令。准备已注册站点与合成模型：

```sh
.venv/bin/python scripts/platform/core-fixture-setup.py --run-file "$PWD/work/run/w1-delivery.json" --profile closed-web-assessment-v1
```

这会显式执行一次合成连接检查和发布，不调用公司模型。创建Web任务入口填`http://wuji-web-assessment-lab:8000/`，设置授权期限、合成模型方案和Task USD上限；启动后进入工作区→评估，查看条件、验证和证据。方法不访问外部目标，总Goal保持尚未判定。根页面第一层资源仅作为有限评估清单，不是路径ACL。

压缩探针仅在安排定向验收时为setup追加`--compaction-probe`，普通交付不加。探针复用Pi原生阈值压缩与同会话下一条只读消息，不是新的Agent循环；它不能证明真实模型记忆质量。

停止仍先核对Task结束，再core down、gateway down、serve-only Ctrl-C，均使用当前合法run-file；保留数据/PVC。当前实际交付入口与Task见artifacts/phase-2-web-assessment/delivery.json，验收事实见W1阶段acceptance.md。
