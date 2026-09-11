# Wuji 自动化渗透平台

Wuji 是 Kubernetes 原生的 AI 授权安全验证平台。以 Task 组织授权范围、目标、模型预算、执行、证据和评估，面向 CTF、Web 单点渗透、综合渗透、攻防演练和代码审计五类场景。仅允许已授权的非破坏性验证。

## 当前进度

截至 2026-09-11，核心执行闭环和 W1 有限 Web 评估机制已通过封闭夹具验收：真实 Cairn / Pi / LiteLLM、每 Task 一个双容器 Pod、受控 HTTP 观察、覆盖与验证记录、证据关联、Reason 补充反馈及 Pi 原生压缩。

上述验证使用合成模型上游；真实模型自主效果仍待验收，尚未开放任意外部目标或生产出口。Phase 1A 完整验收仍为 partial。具体被测 SHA、命令和限制以[W1 验收](docs/stages/phase-2-web-assessment/acceptance.md)及[项目背景索引](docs/project-context.md)为准。

## 架构

- Wuji：任务、租户/项目权限、授权、执行准入、生命周期、调用账本及评估证据。
- Cairn Server / Dispatcher：唯一可写探索黑板与原生探索调度；保持黑板核心协议。
- Pi coding-agent：模型客户端、Agent 循环、独立会话及压缩。
- Task Runtime：一个 Pod 内固定 agent 与 kali 容器，多个 AgentRun 通过受控工具共用任务工作区。
- LiteLLM：组织模型服务与任务 USD 预算；上游凭据只留在网关。
- PostgreSQL、Cairn SQLite、LiteLLM 独立数据库和开发 Artifact PVC：分别承担业务、黑板、模型网关与产物存储。
- React / TypeScript / Vite / Ant Design：任务工作台和五套主题。

## 目录

| 路径 | 内容 |
| --- | --- |
| `apps/` | 平台 API 与正式 Web 工作台 |
| `services/` | 执行控制、Cairn 适配、Agent/Kali Worker 及自建夹具 |
| `packages/` | API 契约、生成类型和共享包 |
| `infra/kubernetes/` | 数据库、身份、网关和核心执行的 Kubernetes 配置 |
| `scripts/`、`toolchain/` | 生命周期、构建与锁定工具链 |
| `tests/` | 契约、单元和集成验证入口 |
| `spikes/` | 历史实验与交互原型 |
| `docs/` | 当前设计、阶段 Spec / Plan / Acceptance 和历史记录 |

## 开发入口

运行要求与初始化步骤见[本地工作台](docs/local-development.md)。先按说明准备固定 Node、pnpm、Python/uv 及 Docker Desktop Kubernetes 环境；正式平台需要数据库、身份、模型网关与执行服务，不能仅靠启动前端运行。

```sh
./scripts/bootstrap-toolchain.sh
pnpm install --frozen-lockfile
./scripts/uv.sh sync --frozen --group task-runtime --group cairn-bridge
pnpm build:platform
```

W1 启动按本地工作台的“核心闭环候选”和“W1 有限Web评估”章节执行，在当前克隆目录生成新的私有 run-file。`pnpm dev` 启动的是历史内存原型；正式前端开发命令为 `pnpm dev:web`。

## 文档入口

- [项目背景与有效文档索引](docs/project-context.md)
- [协作约定](AGENTS.md)与[开发流程](docs/development-workflow.md)
- [产品定义](PRODUCT.md)、[视觉基线](DESIGN.md)与[架构决策](docs/cairn-architecture-decision.md)
- [核心闭环验收](docs/stages/phase-1c-task-creation/acceptance.md)
- [W1 Spec](docs/stages/phase-2-web-assessment/spec.md)、[Plan](docs/stages/phase-2-web-assessment/plan.md)与[验收](docs/stages/phase-2-web-assessment/acceptance.md)
- [GitHub 整理与版本说明](docs/repository-handoff.md)

仓库保留完整源码与阶段提交历史。依赖缓存、密钥、本机配置、数据库、会话和原始运行产物不纳入 Git；历史文档引用的 `work/`、`artifacts/` 和本机路径不随克隆提供。Cairn 上游来源和许可见架构决策及对应依赖定义。
