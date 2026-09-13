# P04 实施与自行验证

最新审查后 F1/F2 修复与首次定向验证见 [review fix round 1](review-fix-round1/report.md)，代码 `2ce5250322c43fdbf38d23e9eefcbb8ab04b785b`。以下保留原交付及首次可见性修复的历史记录。

日期：2026-09-13。状态：实现已提交，等待主代理审查；不声明完整阶段或后续 AC 集成通过。

代码提交：`638c33547d547327862e97de06d9a49d099e8568`；权限收口：`538f4d6d80d6e4132b1dd625f1a78216f81876a1`。源于已批准 P04 brief / [实施契约](../../P04-implementation-contract.md)，P03 基础为 `dcf5cc2903622a02b023f545e3e4c1585004ae59` + `c2a86e3a98895378532fff1427e9ee82420b4039`。本文是后续证据记录，不预写自身提交 SHA。

## 行为

- Agent candidate、自由文本和无依据假设正常共享；ClaimRevision 唯一正文，optional revises 对固定 Claim 做 CAS/当前修改权限检查。Intent 可基于假设被接纳，P04 不创建或启动执行工作。
- 评估为不可变事件，绑定实际 Actor、固定 Claim/输入和发布 policy；反证并存聚合为 disputed/inconclusive；替代/撤回/失效另写动作。精确 JSON Pointer 方法重读封存字节且匹配完整正文，只认证实际检查的命题；模型意见、成功文字及无关 prose 不升级。
- 生产 knowledge/records 路由使用 VNextAPIRouter 和显式校验的 DecimalJSONResponse。批内前向引用、缺失/循环/重复/竞争修订及拒绝传播保留合法无关组件，失败不留领域/registry/关系残行。
- ResultCommitter 先保存封存 raw output 和 received，再验证 AgentPayload、原文一致性并原子发布结果；可查询/恢复 received，重投重验权限和摘要。无关旧快照追加允许，过时依据保存 stale_input；撤销补交 historical_only，不复活任务。
- 同一 ArtifactStore 新增 Run-bound model_output staging，允许零 ToolAttempt。writer 能力与 capture 分开；P03 封存及租约 mutation guards 保留。当前迁移头 `vnext_0004_p04_assessment_visibility`，保留所有前驱且未知 head 拒绝。端口与迁移详见 [README](../../../../ops/vnext/migrations/README.md)。

## 主代理指出的权限风险与修复

在 `638c335` 真实复现 public Claim/public support/private contradiction：高权限为 disputed，低权限因 RLS 隐藏反证而错误得到 Fact。证据：[RED](fix-round1/red.txt)、[完整 RED/GREEN HTTP](fix-round1/http-reproduction.md)。

`538f4d6` 增加 scope/当前 ACL 检查的 SECURITY DEFINER 布尔 guard，检查同 ClaimRevision 的全部评估、动作和输入是否可见；没有返回隐藏数据，也没有新建 Fact 正文。Fact 读取在同一 Repeatable Read 事务完成 guard 和聚合。可见性不全时统一 `503/CAPABILITY_UNAVAILABLE`，details 为空；当前读、旧快照读和新快照创建均防止返回可见子集。

![实际浏览器截图：同一 Claim 的高低权限响应](screenshots/knowledge-and-visibility.jpg)

截图来自 CUA 对 loopback [已保存响应页](result.html) 的实际浏览器捕获，展示真实 ASGI 响应与命令结果；不是正在运行的产品 UI。截图对应的完整响应和输入没有裁剪，见上面的 HTTP 文件；来源与摘要见 [provenance](screenshots/provenance.json)。

## 命令、结果与代码绑定

| 执行 | 实际结果 | 绑定 |
| --- | --- | --- |
| `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_knowledge_admission.py -q --junitxml=.../junit.xml` | 24 passed，13.18s，exit 0 | 原候选 `638c335`；[输出](final-tests.txt)、[命令/16文件指纹](final-run.json)、[提交比对](commit-binding.json) |
| `work/toolchain/bin/pnpm contracts:check:v2` | exit 0；Python/TS 与 OpenAPI 一致；1 warning | 同一原候选；[完整输出](contracts-check.txt) |
| 权限修复 RED：同测试文件 `-k hidden_counterevidence` | 1 failed / 24 deselected，exit 1 | `638c335`；[命令](fix-round1/red.txt.json) |
| 权限修复及直接影响项：`-k 'hidden_counterevidence or candidate_real or revision_conflict or fixed_snapshot or migration_preserves or unverified_intent_is_readable'` | 6 passed / 19 deselected，3.41s，exit 0 | `538f4d6`；[输出](fix-round1/green.txt)、[命令/变更指纹](fix-round1/green.txt.json)、[提交比对](fix-round1/commit-binding.json) |

测试在提交前的工作树运行，随后逐文件 SHA-256 与实际代码提交比对，匹配才绑定。修复只改 Fact 可见性、追加迁移、相应测试与迁移说明；未重跑其余19项，也未把它们标成 `538f4d6` 的新实测。契约未被权限修复修改，复用原候选生成检查。OpenAPI 的唯一 warning 是 AgentPayload 成为独立第二阶段 schema，不再被外层 payload 直接引用；未降低校验来消除此提示。

TDD 过程保存在 [tdd/](tdd/)：原始缺入口/新 wire RED；随后实际 API 定位 DTO/日期序列化；评估输入快照闭包、评估 Actor FK、Intent 读枚举分别有具体 RED/GREEN。初始 RED 日志记录11个失败，但当时外层包装没有单独保留 pytest 退出码，不能把包装进程的0当测试通过；后续命令的真实退出码均单独保存。

## 覆盖和交接

- AC-005/006/009/010：实际 API 正向 Agent 接纳、无解析器/空依据、精确字段与无关正文反例、模型/Agent 自认证拒绝。
- AC-011/012：工具成功文字不证明健康，partial 局部 scalar 可核验，全量否定 inconclusive；字符串/null/大整数与 bool/number 区分及完整文档 absence 正例。
- AC-014：正文 CAS/归属、旧关系不迁移、矛盾聚合、替代/stale 动作、冻结快照及评估输入闭包。额外覆盖隐藏反证不可制造低权限 Fact。
- AC-007/017：假设 Intent 共享、旧快照追加/过时 read_set、当前权限重验；真实 Profile/预算/调度拒绝及 Goal 判据仍留 P05/P09/P12，不以本轮取代完整 AC。
- AC-016：沿用 P03 已通过的 Task 锁内 WorkDependency DAG 约束，相关基础 SQL 未修改；本轮新实测的是提交引用拓扑与无残行，未重跑两连接 WorkDependency 用例。P05/P09 继续消费唯一 WorkDependency。
- 原文语法失败留存、payload/raw 不一致、received 恢复/幂等、历史结算、零工具 Run 输出、model writer 对 capture seal/lease UPDATE/DELETE 的数据库拒绝均有真实服务/PG/字节用例。

无额外模型调用、旧服务启动、生产切换、推送或用户数据删除。测试父身份/Run/开始回执由明确 SQL 夹具提供，不冒充 Supervisor 集成。生命周期自动触发失效、完整 Goal/Topology/报告补充由后续所有者接线；`AssessmentService.invalidate` 已提供追加端口。当前完整接口与 narrow schema 变更由主代理审查后决定 gate。

完整证据：[原候选104次HTTP](http-reproduction.md)、[权限修复46次HTTP](fix-round1/http-reproduction.md)、[原生证据索引](evidence-index.json)、[修复证据索引](fix-round1/evidence-index.json)、[原候选test_name](test-names.json)及两份 JUnit。PostgreSQL JSONL 无损 gzip 保存，HTTP/body 与原始 bytes 无截断；Authorization 仅以需重新签发的 fixture token 变量替代，未提交 bearer 凭据或私钥。

变更范围：五个 blackboard 模块；knowledge/records 生产路由；同一 ArtifactStore/UoW/snapshots/schema 与追加迁移；窄 OpenAPI/Python/TS DTO；P04 测试及迁移说明。没有锁文件或旧核心改动。
