# Wuji 自动化渗透平台

Wuji 是 Kubernetes 原生的 AI 授权安全验证平台。以 Task 组织目标、授权范围、模型预算、执行、知识、证据和评估，仅允许已授权的非破坏性验证。

## 当前开发线

唯一开发主线为 **`codex/vnext-maf`**。2026-09-22 用户确认舍弃 Cairn/Pi 路线；旧 `codex/github-upload` 本地开发线已归档，不再作为当前架构或启动入口。归档位置、工作树分工和恢复方法见[开发线与历史归档](docs/development-line.md)。

本机继续在 `work/worktrees/vnext-maf/` 开发，主目录保留 vNext 的 detached HEAD 快照。其他克隆先用 `git branch --show-current` 和 `git worktree list` 核对位置，不假定本机路径存在。

## 当前架构

- Wuji Blackboard / Scheduler：知识记录、评估、持久工作、执行准入与调度。
- Python MAF：单个 Agent 的模型—工具循环、原生会话和上下文能力。
- API / Launch / Runtime：任务命令、持久启动、Pod 管理、结果接纳和停止核对。
- ModelGate / ToolGate：逐调用身份、授权、限额、账本和证据登记。
- Task Runtime：每个 Task 一个 Pod，固定 agent 与 kali 两个容器。
- LiteLLM：已发布模型接入、受限 Task Key 和金额预算。
- PostgreSQL / RLS 与 Artifact PVC：领域记录、执行账本、会话材料和证据字节。
- React / Ant Design / React Flow：工作台及受权知识投影。

vNext 和首用流程仍为 **in-progress**。已有机制及局部集成证据不代表完整产品、真实模型效果或生产能力均已验收；实际范围以[vNext 验收](docs/stages/vnext-maf/acceptance.md)和[首用验收](docs/stages/first-use/acceptance.md)为准。

## 开发入口

- [协作约定](AGENTS.md)与[背景索引](docs/project-context.md)
- [vNext Spec](docs/vnext/SPEC.md)、[Plan](docs/vnext/PLAN.md)和[实施决定](docs/vnext/decision-register.md)
- [首用 Spec](docs/stages/first-use/spec.md)与[当前执行计划](docs/stages/first-use/plan.md)
- 核心代码：`packages/wuji-core/`、`packages/maf-worker/`
- 服务入口：`services/wuji-api/`、`services/wuji-launch/`、`services/wuji-scheduler/`、`services/wuji-runtime/`
- 部署与检查：`ops/vnext/`、`scripts/vnext/`、`tests/vnext/`

vNext Python 使用独立锁文件和 `scripts/vnext/uv.sh`。根目录 `pnpm dev`、`scripts/platform/` 及旧[本地工作台说明](docs/local-development.md)保留历史用途，不用于启动新核心。部署前按当前计划核对构建 SHA、配置与运行记录。

旧源码、设计和验收作为历史保留，不表示仍在维护 Cairn/Pi。密钥、本机配置、数据库和运行数据不纳入 Git；本次开发线整理不推送远端、不切换部署、不删除运行数据。
