# 本地工作台

Phase 1A 功能已集成，完整验收当前为 partial：最近一次独立检查中 API 73/73、生命周期 6/6、Chrome 12/15 通过，3 个真实 Keycloak 回调场景仍待集中测试。实际结论见[阶段验收](stages/phase-1a/acceptance.md)和[待测清单](stages/phase-1a/deferred-tests.md)。

## 环境与入口

使用本机 Docker Desktop 已启用的 Kubernetes：Docker context 为 `desktop-linux`，Kubernetes context 为 `docker-desktop`。PostgreSQL 与 Keycloak 运行在专属命名空间，本地进程运行 API 和前端。

| 环境 | 工作台 | API | Keycloak | PostgreSQL | 命名空间 |
| --- | --- | --- | --- | --- | --- |
| 开发 | http://127.0.0.1:4180 | http://127.0.0.1:8000 | http://127.0.0.1:18080 | 127.0.0.1:15432 | wuji-dev |
| 独立测试 | http://127.0.0.1:4182 | http://127.0.0.1:8002 | http://127.0.0.1:18082 | 127.0.0.1:15434 | wuji-test |

原型仍使用 `pnpm dev` 和 http://127.0.0.1:4173。正式工作台使用数据库中的身份与项目；本阶段包含登录、项目访问和五套主题，任务执行与 Agent 在后续阶段实现。

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

日常开发只执行覆盖当前改动的最小检查：文档改动检查 diff；契约、API 或前端改动分别选择 `pnpm contracts:check`、`pnpm check:api` 或 `pnpm --filter @wuji/web build`。跨模块平台改动使用 `pnpm check:platform`；直接修改生命周期时才运行 `pnpm test:platform:lifecycle`。

`pnpm test:platform` 是显式安排的集中全量验收入口，不与前述命令默认串行执行。它在 `wuji-test` 为本次运行创建独立数据库和 realm，不清空开发数据或上次运行的数据；协议夹具占用 18083，空迁移库探针占用 8003。最近一次全量运行仍有 3 个回调用例待测，不能据此标记完整通过。

运行与验收证据保存在 ignored 的 `artifacts/phase-1a/`，私有运行记录在 `work/run/`。最终验收报告记录候选提交 SHA、run_id、命令、退出码及未通过项；本机证据不随 Git 提交分发。
