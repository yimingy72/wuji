# Wuji 开发协作约定

## 测试目标范围

- 已获授权；仅允许非破坏性验证。
- 禁止目标数据破坏、禁止目标持久化、禁止越权扩散。
- 平台数据库、证据、检查点及界面偏好按保留策略保存，不属于目标持久化。
- 使用自建夹具、测试租户与隔离运行环境；真实模型网关只在已授权的数据与预算范围内验证。
- 密钥、会话凭据、原始敏感证据和本机配置不得写入 Git、子代理任务书或普通报告。

## 阶段规划与实施

- 主代理负责架构决策、每阶段 Spec / Plan、拆分、集成审查和最终验收。
- 新阶段先在 Plan 模式完成具体规划；模式由应用控制，代理不得声称已自行切换模式。
- 已批准计划进入执行模式后落盘并实施。下一阶段草案可以准备，但草案不自动授权业务开发。
- 每阶段维护 `docs/stages/<stage>/spec.md`、`plan.md`、`acceptance.md`，明确 draft、approved、in-progress、accepted 等真实状态。
- Spec 定义行为与验收；Plan 固定方案、接口、任务依赖、负责人及验证入口。实质变更由主代理更新阶段设计。
- 已有授权与约定持续生效，常规可逆实施、修复、本地提交和验收不重复索要许可。

## 子代理与模型

- 开发子代理：`gpt-5.6-sol`，`reasoning_effort=xhigh`。
- 后续独立集中测试子代理：`gpt-5.6-luna`，`reasoning_effort=xhigh`；既有 SOL/high 测试记录按实际模型保留。
- 指定模型不可用时报告，不静默换模型。主代理模型保持当前选择。
- 默认开发阶段最多两个开发代理和一个测试代理同时工作；集中测试阶段按下文单独限制。仅独立任务并行，依赖项顺序执行。
- 子代理使用独立上下文和分配的 worktree；任务书必须包含绝对工作目录、基准提交、Spec / Plan、允许修改范围、验证要求与交付格式。
- 子代理不得在主工作区编辑或重置他人变更；不得自行继续拆代理或扩大任务范围。
- 公共契约、锁文件和迁移编号必须指定唯一负责人。开发者提交实现与本地检查；独立测试者按 Spec 核查，不能仅重复实现逻辑。

## 精简测试与停止条件

以下约束依据用户 2026-09-09 的要求，优先于阶段文档中可能导致重复全量验证的旧流程。

- **默认只做最小必要验证。** 覆盖本次需求的主流程、直接受影响的失败路径及必要权限边界；不主动扩展无关极端场景、故障注入或跨平台矩阵。
- **每个开发任务默认测试总预算为 10 分钟。** 包含测试执行、等待、测试脚本排查与复跑；所有代理共享预算，不按代理、提交 SHA、对话轮次或修复轮次重置，也不能拆分同一问题规避预算。达到预算即停止追加测试，清理自有进程并记录待测项。用户另有明确指示时才扩大范围或预算。
- **文档、文案和小样式改动不新增测试。** 按影响选择 diff 检查、构建或一次页面查看；不因此启动完整后端、Kubernetes 或整套回归。
- **代码修复只复测受影响项。** 未变代码复用已有证据，注明原 SHA 及不受影响依据；不得把旧结果冒称新提交的实测。仅提交 SHA、报告或测试辅助代码变化，不构成重跑安装、构建、API、生命周期全套检查的理由。
- **测试脚本同类问题最多排查两轮。** 先根据实际 trace、日志和返回码确认失败点，再做定向验证；仍未解决则转入待测清单。禁止靠猜测反复改脚本并重跑整套测试。
- **通过即停止。** 所需检查通过后不为了增加信心再扩大回归，不以“必须全绿”为由无限测试。阶段全量验收集中安排一次，先解决已知测试阻塞，再统一执行。
- **延期必须如实记录。** 待测清单写明场景、原因、已有证据、执行命令、模型与依赖；关键未通过项不能标为通过，开发交付与完整验收分开记录。
- **集中测试分批执行。** 使用 `gpt-5.6-luna / xhigh`，由主代理拆分任务并汇总结论；批量表示任务队列，不表示无限并发。当前最多同时运行3个测试子代理；共享数据库、API配置、故障注入及固定端口由一个负责人串行操作，不能为并发而扩大测试环境。

Phase 1A 剩余项见 [后续集中测试清单](docs/stages/phase-1a/deferred-tests.md)。

## Git 与验收

- `master` 保存阶段基线；首次提交只是现有项目快照，独立验证后才记录基线通过。
- 阶段分支 `codex/<stage>`，子任务分支 `codex/<stage>-<task>`；默认独立 worktree 位于被忽略的 `work/worktrees/`。
- 仓库本地提交身份：`Wuji Development <wuji-dev@localhost>`；不修改全局 Git 身份。
- 显式检查变更清单和暂存内容，禁止盲目收录依赖、密钥、运行产物或本机索引。
- 主代理集成子任务并解决冲突。验收绑定被测试的提交 SHA；后续修复重新验证受影响项。
- 验收记录如作为后续文档提交，必须区分被测试代码 SHA 和记录提交；不声称文档能预先记录自己的 SHA。
- 按实际结果记录通过、失败和未覆盖。缺少证据不得标记通过；原型检查不替代平台集成验收。
- 默认只做本地版本控制；不自动推送、发布或修改远端。

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

主代理核对已有索引所属工作树和新鲜度，在集成后执行 `codegraph sync`。子代理不得将主工作区索引的代码当作自己分支的现状；索引无结果或工作树无索引时回退 `rg` 和直接读取，并说明限制。
