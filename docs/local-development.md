# 本地工作台

本文随 Phase 1A 收口交付更新；当前完整运行验收仍在进行，最终结论见[阶段验收](stages/phase-1a/acceptance.md)。

## 环境与入口

使用本机 Docker Desktop 已启用的 Kubernetes：Docker context 为 `desktop-linux`，Kubernetes context 为 `docker-desktop`。PostgreSQL 与 Keycloak 运行在专属命名空间，本地进程运行 API 和前端。

| 环境 | 工作台 | API | Keycloak | PostgreSQL | 命名空间 |
| --- | --- | --- | --- | --- | --- |
| 开发 | http://127.0.0.1:4180 | http://127.0.0.1:8000 | http://127.0.0.1:18080 | 127.0.0.1:15432 | wuji-dev |
| 独立测试 | http://127.0.0.1:4182 | http://127.0.0.1:8002 | http://127.0.0.1:18082 | 127.0.0.1:15434 | wuji-test |

原型仍使用 `pnpm dev` 和 http://127.0.0.1:4173。正式工作台使用数据库中的身份与项目；本阶段包含登录、项目访问和五套主题，任务执行与 Agent 在后续阶段实现。

## 首次准备

在仓库根目录执行：

```sh
./scripts/bootstrap-toolchain.sh
./scripts/uv.sh sync --frozen
pnpm install --frozen-lockfile
```

工具链和依赖版本由仓库固定。Python 使用项目的 `scripts/uv.sh` 入口。

## 启动和停止

终端一启动基础设施和本地转发，保持前台运行并等待就绪：

```sh
pnpm dev:infra
```

终端二首次初始化或重放迁移与预置身份，然后启动工作台：

```sh
pnpm dev:seed
pnpm dev:platform
```

打开 http://127.0.0.1:4180，选择“使用组织账号登录”。开发账号保存在本机私有文件 `work/run/dev.json` 的 `seed_users` 中；`single_a` 对应单项目身份，`dual_ab` 用于跨租户项目与翻页，`no_projects` 用于空列表。只在本地读取所需账号的 `username` 与 `password`，不要复制整个运行文件到聊天、日志或 Git。

工作台右上角可以切换雾银、冰蓝、青瓷、亮石墨和原石墨，主动选择会保存到本机浏览器。`?theme=glacier` 等比较链接只临时覆盖当前标签页。

在第三个终端停止开发进程，或对前台命令使用 Ctrl-C：

```sh
pnpm dev:down
```

普通停止保留集群对象、Secret、PVC 和业务数据。命令仅清理经核验属于当前运行的进程；遇到端口占用会报告失败。更新代码前先停止旧版本的开发进程，更新后重新启动，避免私有运行记录的提交 SHA 与工作树不一致。

## 检查与独立验收

```sh
pnpm check:platform
pnpm test:platform:lifecycle
pnpm test:platform
```

完整平台测试在 `wuji-test` 为本次运行创建独立数据库和 realm，不清空开发数据或上次运行的数据。协议夹具占用18083，空迁移库探针占用8003；这些端口应保持空闲。测试命令退出时清理自己启动的本地进程，故障恢复在同一次运行中验证原会话和原项目。

运行与验收证据保存在 ignored 的 `artifacts/phase-1a/`，私有运行记录在 `work/run/`。最终验收报告记录候选提交 SHA、run_id、命令、退出码及未通过项；本机证据不随 Git 提交分发。
