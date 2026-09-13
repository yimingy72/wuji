# P13 持久受权投影独立审查

日期：2026-09-13  
执行角色：SOL/xhigh，独立只读代码审查  
结论：**CHANGES REQUIRED — 未发现 P1，发现 P2 × 2。**

本轮固定核心来源为 `3015ca6a56b31aaa666e12bd9e81781b3bc1ff9b`，最终代码为 `44ddc68e48e1c36974cec7e705d1cd3812c7a031`，既有证据提交为 `a1fc4ff42f6c18b13f64c15031dce8aa7b85d03f`。审查只覆盖 P13 `projection/{builder,access,records,snapshots}.py`、0012 projection schema 及 `schema.py` 接线、`http/topology.py`、P04 `FactLedger.read_in_transaction` 提取和对应 P13 tests/support；中间 P07/P09/P10/P14、P08 新目录和当前共享树其他未提交内容均未混入结论。

工作树没有 `.codegraph/`，因此按项目约定回退到不可变 Git 对象、`rg` 和逐行读取。审查开始时 HEAD 为证据提交 `a1fc4ff`；主线随后并发推进到 `b7d39c85ef8601e60de9544dfe43296cdd1338c0`，`a1fc4ff..b7d39c8` 没有改动上述 P13 固定范围。已有其他阶段未提交内容均保留且未修改。本轮没有运行 pytest、数据库、HTTP、浏览器、服务、构建或 formatter，没有创建测试数据，也没有修改源码或测试。

## Findings

### P2 · `mode=live` 可绑定历史 `snapshot_id`，公开视图身份允许 live/history 混写

**定位：**[`packages/wuji-core/src/wuji_core/projection/snapshots.py`](../../../packages/wuji-core/src/wuji_core/projection/snapshots.py) 63–81 行，关键为 65–80 行；公开参数入口在 [`packages/wuji-core/src/wuji_core/http/topology.py`](../../../packages/wuji-core/src/wuji_core/http/topology.py) 38–52 行。行号固定于 `44ddc68`。

`topology()` 只拒绝 `mode=history` 且没有 `snapshot_id` 的组合。只要请求带 `snapshot_id`，77–80 行便读取保存的历史 materialization，并把调用方原始 `ViewQuery` 写入新 view。因 `ViewQuery` 没有 live/snapshot 交叉约束，`mode=live&snapshot_id=H1` 会生成一个内容来自 H1、query 身份却仍标为 live 的新 view。

**触发：**先保存 H1，再写 Claim revision 2，然后请求：

```http
GET /api/v2/tasks/task-fixture/topology?mode=live&snapshot_id=${H1}&node_limit=300&edge_limit=600 HTTP/1.1
Host: testserver
Authorization: Bearer ${TOKEN_reader_fixture}
```

该组合按当前数据流进入 `_materialization(..., history=True)` 和 `_new_view(...)`，而不是返回 `422/INVALID_SCHEMA`。本轮遵守用户只读约束，没有发送这条请求；这是待 Locke 执行的最小复现意图，不是本审查伪造的 HTTP 结果。

**影响：**调用方可以把固定历史数据当成 live 视图。当前 P13 所有 `allowed_actions` 为空且 P15 尚未实现，所以本轮没有证据表明已经执行命令或混入 stream；但这个已公开并持久化的 mode/query 边界会让 P14/P15 后续按 live 语义消费 H1，直接破坏当前/历史隔离。修复应在服务端拒绝不合法组合，至少固定 live 不带 snapshot、history 必带 snapshot；history 正向和 continuation 继续绑定原 mode/snapshot/query。

### P2 · records/snapshots 实际返回 410，但冻结 OpenAPI 未声明该响应

**定位：**[`packages/wuji-core/src/wuji_core/projection/snapshots.py`](../../../packages/wuji-core/src/wuji_core/projection/snapshots.py) 146–159、183–204、248–256、268–317 行；[`packages/wuji-core/src/wuji_core/http/topology.py`](../../../packages/wuji-core/src/wuji_core/http/topology.py) 22–35、54–70 行；`packages/contracts/openapi-v2.yaml` 在 `44ddc68` 的 218–255 行。

`ProjectionRepository` 明确在过期/未知路径发出 `HISTORY_UNAVAILABLE`、`SNAPSHOT_EXPIRED` 或 `VIEW_EXPIRED`，`respond()` 会保留 `DomainError.status`。但冻结 OpenAPI 中 `/snapshots` 只声明 200/401/404，`/records/{record_type}/{record_id}` 只声明 200/401/404/422；两条路径都没有已实现的 410。Topology 自身已声明 410，所以不是全局约定可以补足的模糊点。

**触发：**分别使用过期 index cursor 请求 `/snapshots`，以及带过期 `snapshot_id` 请求 `/records/...`。既有 P13 测试已经保存过 record 过期返回 410 的结果，但未覆盖 index cursor 过期，且其 OpenAPI 没有同步这些响应。

**影响：**由单一 OpenAPI 生成的客户端无法把这两条实际 410 纳入类型化恢复流程，P14 消费者会把“重新取 view”和“历史不可用”当成未声明响应处理；现有 HTTP 成功证据也不能使未声明 wire 行为变成冻结合同的一部分。最小修复范围是补齐两个 GET 的 410 response，重生成 DTO，并只做对应契约检查与两条定向 HTTP；审查开始时存在的未提交契约文件属于其他进行中工作，本审查没有读取其内容或据此改变固定 SHA 结论。

## 限定通过范围

除上述两项外，逐行审查未发现同级或更高缺陷。以下结论是 `44ddc68` 源码与 `a1fc4ff` 既有材料的限定静态判断，不是本轮重跑结果：

- **一个 RR 物化与 canonical Fact guard：**`ProjectionRepository.topology/create_in_transaction` 在同一个 snapshot-purpose Repeatable Read 事务中创建 P03 manifest、读取 P04 frozen assessment、固定 Task/Work/Run、写 materialization/view/cursor；没有第二个 latest 事务。`FactLedger.read_in_transaction` 重新取得同一事务内 canonical manifest，逐字段拒绝 caller 伪造，要求 ref 属于 manifest，并使用冻结 assessment；foreign-task manifest 统一拒绝。
- **分页、详情与历史固定：**续页只从保存的 `materialization_json` 读取；节点和边位置独立推进，边只在精确端点已经交付后出现。带 `snapshot_id` 的详情从保存的 `records` 白名单读取；历史索引先冻结已保存 P13 materialization ID，再逐项重验，未知历史不回退 latest。Finding 1 只涉及 mode 与 snapshot 的组合身份，不否定保存内容本身的固定性。
- **Fact/Claim 与 revision：**builder 以 `entity_type:id@revision` 生成节点身份，Claim 的 fact 展示只取 canonical `assessment.eligible`；display hint 不能提升。关系使用精确端点，隐藏/缺失端点不输出边，旧 relation 不迁移到新 revision。
- **当前 ACL、私有依据与派生输出：**view/cursor/materialization 绑定 owner、subject、角色和当前 `can_*`/clearance 摘要；每次读取重验保存的知识、assessment input、Artifact、Observation、Work/Run、dependency/result 和 relation guard。权限降低使旧 view 失效；派生边没有复制标签，公开节点/详情来自显式 DTO 白名单，没有隐藏总数或任意 DB row metadata。
- **opaque cursor：**handle 由服务端随机生成并持久化；page cursor 通过 FK 和运行时检查绑定 view、完整规范 query digest、access digest、projection version、subject/Task 和 expiry。index cursor 同样由 subject/query/access/version/expiry 检查保护；公开 handle 不编码内部水位。
- **`projection_run_origin`：**0012 中函数为 `SECURITY DEFINER` 且固定 `search_path=pg_catalog`，PUBLIC EXECUTE 被撤销，应用角色只获窄 EXECUTE。查询重新核对当前 Task ACL/clearance，并同时绑定实际 AgentRun、Assignment、start operation、Outbox kind/payload、完整 RunIdentity 及对 canonical `assignment_json` 的真实 SHA-256；唯一返回列为 `created_at`。普通 reader 没有 Assignment 表读取权。
- **不泄内部序号/secret：**`internal_event_origin` 只保存于私有 materialization 行，未进入 TopologySnapshot、RecordView、label、query metadata 或 cursor。公开 Run 只含 typed identity/state/model mode/真实时间；没有 Assignment、credential ref 或 digest。既有 HTTP 包中的 authorization 已替换为 fixture 变量；本轮静态扫描没有发现 bearer、私钥或 token ciphertext。
- **不执行动作、不造未知来源节点：**三个 P13 路由均为 GET，所有 view/node `allowed_actions` 为空。读取会持久化派生 snapshot/view，但没有领域命令、Run/Assignment/credential/Outbox 创建。Run 没有真实 P09 registration/dispatch 来源便不投影，也不拿 snapshot time/started_at 填充；TaskCreate definition 只给 Origin 固定初始 `goal_revision=1`，没有 P12 生产者时不创建 Goal/Verification/Completion/Report 节点。
- **0012 权限：**三张派生表启用 RLS；应用角色只有 SELECT/INSERT，无 UPDATE/DELETE；函数 PUBLIC EXECUTE 已撤销。schema chain 从 0011 接入 0012，不改写旧 head。

## 既有证据核对

[`docs/vnext/evidence/P13/runtime-green/report.md`](../../../docs/vnext/evidence/P13/runtime-green/report.md)记录的命令为：

```text
./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_view_snapshots.py -q
............                                                             [100%]
12 passed in 8.16s
```

这是原 SOL/xhigh 执行者绑定最终代码 `44ddc68e48e1c36974cec7e705d1cd3812c7a031` 的既有结果；本审查没有重跑，也不称为本审查者独立测试。只读核对确认现有报告列出的数量与目录一致：[`完整 HTTP 请求/响应包`](../../../docs/vnext/evidence/P13/runtime-green/http-reproduction.md)有 49 个 Exchange，`runtime/` 有 43 个原生文件，[`evidence-index.json`](../../../docs/vnext/evidence/P13/runtime-green/evidence-index.json)有 43 条索引。49 组响应正文中未出现 `event_seq`、`board_revision`、`assignment_json`、`assignment_digest` 或 `credential_ref`；48 个有认证的请求使用 fixture token 变量，唯一无 Authorization 的交换是未认证负例。

![P13 既有持久投影验证截图](../../../docs/vnext/evidence/P13/runtime-green/screenshots/p13-runtime.jpg)

截图是既有 loopback 页面渲染，展示保存的 `12 passed`、最终代码 SHA 和选定响应；不是产品 UI，也不是本轮新截图。截图来源与摘要见 [`provenance.json`](../../../docs/vnext/evidence/P13/runtime-green/screenshots/provenance.json)。本轮两项 Finding 尚无已执行响应包；用户明确要求只读审查，因此只提供最小复现意图并交 Locke 在共享 PG 窗口释放后执行，不能把上述既有 49 组报文错配成 Finding 的复现证据。

## 未提升范围

- P14 正式容器、真实 Auth 消费、Layout CAS、ViewStream/P15、浏览器 current/history 切换和规模 p95 仍未验收。
- P12 Goal/Verification/Completion/Report 生产者仍未接入；builder 支持相应 DTO 不等于已有生产节点。
- 当前报告不证明 P09/P10/P08、真实容器、Kubernetes、收费模型、外部目标或完整 M4。
- P13 的 12 项定向后端结果和 pure builder 9 项历史结果保持原执行者、命令和 SHA，不因本次审查改写或扩大。

## 并行处理状态

两项 P2 的具体触发、文件、影响与最小复现意图已发送到 Locke 线程 `01a09948-7453-7341-a733-5b82efc97009`。消息明确要求等待当前 M2 Dirac PostgreSQL 收口后再使用共享窗口，只做 P13 窄修复/验证，不扩 P15、P14、P08 或全分支回归。
