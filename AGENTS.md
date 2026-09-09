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
- 独立测试子代理：`gpt-5.6-sol`，`reasoning_effort=high`。
- 指定模型不可用时报告，不静默换模型。主代理模型保持当前选择。
- 默认最多两个开发代理和一个测试代理同时工作；仅独立任务并行，依赖项顺序执行。
- 子代理使用独立上下文和分配的 worktree；任务书必须包含绝对工作目录、基准提交、Spec / Plan、允许修改范围、验证要求与交付格式。
- 子代理不得在主工作区编辑或重置他人变更；不得自行继续拆代理或扩大任务范围。
- 公共契约、锁文件和迁移编号必须指定唯一负责人。开发者提交实现与本地检查；独立测试者按 Spec 核查，不能仅重复实现逻辑。

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
