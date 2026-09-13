# M2 原 4P2 限定复审

状态：**PASS — 原四项 P2 全部 ADDRESSED，仅限本次 M2 host/child 切片。** 2026-09-13 最终判定依据下列固定源码及分 SHA 实测；不是完整 P07/P10、P08、其他 work kinds 或 Pod/Kubernetes 验收。

最终 current 运行 HEAD：`d61cb91cac633edcff8830586307e6efa61ada95`，产品修复 `4268b6ae6fc6dec23226803007047ee9b53eacc8`，测试修订 `0f545ba99eff00f7add8c614ffec7e7fc0d5d499`。r7 为 `1 passed in 11.55s / exit 0`；普通写点撤销及首次历史补交复用 r6 `7bc3d05` 的两项 PASS，profile/Pod/pure/Thread 分别复用下述原 SHA。未把分轮结果合称为某次“10项全跑”。

只复核 `P10-M2-review.md` 的四项 P2，不扩大 P08、完整 P07/P10、Node 已通过 settlement delta 或 Kubernetes。原审基准 `6e90a97` / `e40e7e2`；恢复时先检查至 `be7e7decd6d6a6696a6c949d94eae5580de0f148`，含 `069b242`、`750277c`、`b8b2b48`、`df24609`、`53f2d467`、`854ec48`、`1efc311`，再定向检查后续线程及partial-publication修复。Session transport 明确关闭的 `146d6d2` 仅核对 M2 分支。运行时 schema 临时选择 0013 的 dirty patch 属于候选绑定；不能把 HEAD 中 0014/P08 链称为本次测试对象。

本复审仅读取源码、diff、已保存的 HTTP/SQL/命令输出；没有运行测试、数据库、HTTP、进程或浏览器，也没有创建代理。读取 raw 时只输出 route/status/SQL事件定位，未打印令牌、私钥或 bootstrap。

## 原 finding 最终判定

| 原项 | 源码核对 | 关闭证据与判定 |
| --- | --- | --- |
| P2-1 Outbox/生产 caller | `RuntimeDispatcher.pending` 从真实 Outbox/Assignment/Run/receiver 查询，`deliver_pending` 调用 `DispatchOutbox.deliver`；Node bootstrap 成为唯一 bearer 获取入口，旧 FileBootstrapStore 已移除；journal 保留 query-before-PUT、attempted 后禁止再 PUT | **ADDRESSED**。r7由生产dispatcher实际deliver，Node首GET404→唯一PUT→后续查询同一进程；r3 wrong-pod证明unknown仍onePUT/no launch。CLI子缺陷 `ad9a4c8` + `7bc3d05` 真实service Thread/SQLite测试1passed1.27s。生产组合入口已存在，不再以测试node.start替代；未声称实际部署/Pod |
| P2-2 exact harness profile | `read_registered_run` 核对 TaskDefinition digest、work_kind 对应 harness ref/revision/body digest、Assignment profile tuple 和 tools；`validate_receipt` 精确比较 `run.harness_profile_id` | **ADDRESSED**。r2@b8b2b48 wrong-profile通过，错误model-profile回执不推进P05且容量仍reserved；后续修复未改变该守卫。旧pure按r1@ac8ac21四项PASS复用，不冒称r7重跑 |
| P2-3 current JTI / trusted retained | ordinary Worker每个model_output事务锁当前JTI；receiver独立权限绑定原source/Assignment/snapshot；accepted/historical分类不放宽Worker can_settle；4268b6a仅在retained恢复精确原raw/SDK/binding | **ADDRESSED**。r6@7bc3d05已证明Worker写点409及真正首次historical_only/zeroClaim；r7@d61cb91证明current源SDK复用、真实receive后companion故障恢复accepted/Claim，同原raw/ref/SDK/请求bytes，结果持久先于exit observation，无额外模型/工具 |
| P2-4 receiver Pod | start grant 比较 receiver_id/runtime_attempt/subject/environment/pod_uid 整组与 RegisteredRun；bootstrap重新核对 Assignment | **ADDRESSED**。r3@53f2d467 wrong-pod通过，拒绝发生在Node launch前，Run仍registered且reservation不释放。后续源码未改该检查；未冒称r7重新执行该负控 |

新增 retained SQL 的限定接线已读：私有表无 application SELECT；`bound_retained_run` 不再直接 JOIN 私有 binding；`require_model_mutation` 为固定 search_path SECDEF；`can_read_scheduler_snapshot` 的 retained 分支检查 exact run/assignment digest、d.snapshot_id、当前receiver及权限、snapshot层级，普通Worker原JTI分支保留。此为源码检查，不以此替代真实授权反例。

## 原 P2-1 残留：CLI journal 跨线程

以下中间小节保留复审过程中当时发现/等待的顺序；历史“等待”已由末尾r7结论替代，当前状态以首表为准。

在上述候选，`services/wuji-runtime/main.py:89` 于主线程 factory 构造 RuntimeController/DispatchOutbox，`dispatch_outbox.py:156` 以默认线程约束创建 `sqlite3.connect`；随后 main.py:93-104 启动新 Thread 执行 run_once。consumer 的 journal.attempted/save/reserve 与 finally.close 均访问别的线程创建的连接，将触发 ProgrammingError。现有 child 用例从测试线程直接调用 dispatcher，覆盖不到该 CLI 入口。main 已交 Dirac 修复；不能仅关闭 sqlite 线程检查而放弃单consumer串行所有权。

后续修复已独立只读核对：产品 `ad9a4c8a77f1d5ccafb37099137fbb91cad68014` 延迟打开 journal，首次 `_connection` 在 owner_lock 下固定 consumer thread，连接保持 sqlite 默认线程检查；异线程访问/关闭拒绝，同owner关闭幂等。构造失败会关闭临时connection并撤回owner，不会留下错误归属。`services/wuji-runtime/main.py` 将 uvicorn 导入限定到 main，允许直接使用原生产 `run` consumer。

测试 `7bc3d05539259e62557570d16f0370a9fdc063c2::test_runtime_service_owns_its_real_dispatch_journal_thread` 在主线程构造真实 DispatchOutbox，Thread 内调用生产 `run`，实际执行 journal.reserve_send 并由 run 的 finally 关闭，最后独立SQLite连接读到 attempted=1。仅 run_once 被缩成journal操作，故它证明线程/SQLite边界，不替代PG/网络派发。既有 `docs/vnext/evidence/P10/M2/outbox-review-fix/raw/runtime-thread-green.txt` 为 **1 passed in 1.27s**，相邻 exit-code 为0；复审未重跑。此CLI子缺陷关闭，原P2-1端到端项仍等待最终三case结果。

同一 `7bc3d05` 的三项 test-only调整已读：Worker负控改为等待真正result/sdk文件、revocation计数与submit409；历史负控先等待保留文件和首次503，再撤销，之后才调用会触发persistResults的Node.query；process比较改为typed时间/PID/birth。未修改historical期待值。其运行结论留待新raw。

## 证据历史（原结果不改写）

| 保存目录（work/p10-m2/ 下） | 输入 HEAD | 原输出 |
| --- | --- | --- |
| m2-four-p2-20260913T092311Z | ac8ac21 | 5 failed, 4 passed / 14.54s / exit 1 |
| m2-four-p2-r2-20260913T093356Z | b8b2b48 | 4 failed, 1 passed / 57.52s / exit 1；wrong-profile通过 |
| m2-four-p2-r3-20260913T095331Z | 53f2d467 | 3 failed, 1 passed / 65.59s / exit 1；wrong-pod通过 |
| m2-four-p2-r4-20260913T100718Z | 146d6d2 | 3 failed / 23.46s / exit 1 |
| m2-four-p2-r5-20260913T101948Z | be7e7de + recorded dirty patch | 3 failed / 31.70s / exit 1 |
| m2-four-p2-r6-20260913T103719Z | 7bc3d05 + frozen0013/recorded dirty patch | 1 failed, 2 passed / 45.26s / exit 1 |
| m2-four-p2-r7-20260913T105309Z | d61cb91 + frozen0013；relevant source dirty empty | 1 passed / 11.55s / exit 0，仅合法current |

r5 独立核对：

- `3094c7d71e0c/postgres-events.jsonl:24726` 先 INSERT result_receipt，`:28198` 才 UPDATE run_credential revoked。controller HTTP 第24行 receiver-replay 已 accepted；测试通过 Node.query 轮询 exited 时实际触发 persistResults，所以原“撤销后首次 intake”前提不成立。不能改 expected 为 accepted，也不能把该 FAIL 当SQL错误分类的实证。
- current-receiver-intake 的时间戳 `.841Z` 对 `.841000Z`（exited同理）代表同一时刻，仅 JSON 文本精度不同；原严格字符串断言失败须保留，新检查应比较 typed时间和同PID/birth。
- `283331635b77` Worker负控 wait(5) 超时；保存的controller依次有 await-start ready、两次 resolve 200，Gate/upstream各有一次真实model请求200。只能断言“先等待超时、后保存记录中出现首请求”，不能断言具体冷启动成本。fixture finally关服务后的child connection/dangling-function错误属于连带清理结果，不能当独立产品缺陷。写点负控尚未验证。

以上过渡失败原样保留；各阶段发现与当时未关闭状态见下。最终状态以首表和r7核对结论为准，不将r1-r6的失败追改为通过。

## r6 两PASS与一产品残留

`work/p10-m2/m2-four-p2-r6-20260913T103719Z` 的原始输出为1 failed/2 passed，不能整体通过。以下只读检查没有运行测试：

- Worker写点负控 `evidence/283331635b77`：controller HTTP第10/12行 submit-result/archive-sdk=409 STALE_EXECUTION，第13/15行receiver-replay=historical_only。SQL第17525行撤销JTI，21509行写historical_only receipt，22636行count Claim返回0。Node保留相同PID4763/birth，末次响应exited/exit_code1，未以拒绝或receipt推断退出。
- 撤销后首次intake `evidence/3094c7d71e0c`：SQL第17769行撤销JTI早于21503行historical_only receipt，24342行Claim查询为null。HTTP首次receiver-replay即historical_only，旧Worker await-start为revoked；Node相同PID7669/birth、真实exit1。与r5先接受后撤销不同，此次已覆盖真正首次补交。
- 合法current `evidence/b5cdd39aebb1`：controller HTTP第13行普通archive-sdk=200，第14行receiver-replay=422 INVALID_REFERENCE；之后反复409 INPUT_DIGEST_CONFLICT，Node返回unknown并保留真实exit1。不是纯超时/可用更长等待修复。

源码/SQL定位合法current残留：`worker_host.py:480` 的archive_sdk可复用同Run原Worker发布的SDK Artifact，但`:235-247` 的_publish只接受receiver自身writer，拒绝source writer。SQL第21345行已INSERT result_submission，21490行读取该SDK，21492行实际字段为sealed/application-x-ndjson/model_output及原run.worker writer，21493事务回滚。随后`:448-454` saved分支要求result publication已有SDK及binding；第一轮只持久化raw，故原字节每次重试都409。已报main/Dirac；需受限地核对SQL授权source_writer、同Run、精确SDK/binding并完成既有received提交，不能任意放宽writer或创建替代结果。本残留仍属原结果恢复P2，等待修复新candidate及合法current实测。

## current 残留定向源码候选

产品 `4268b6ae6fc6dec23226803007047ee9b53eacc8` 仅改 worker_host；测试 `0f545ba99eff00f7add8c614ffec7e7fc0d5d499` 改原 current 单项及support故障点。已只读核对：

- 正常 `_publish` 仍是exactself；只有retained允许SQL开启的 `source_writer_subject` 与当前receiver两者，且同Run、sealed/model_output必需。`publication_ref` SQL policy按scope/level/write/model_output，trigger要求原Artifact sealed和继承level，没有writer-equality暗中拒绝；无SQL放宽。
- saved分支核对原envelope raw ref、正文bytes、精确identity/snapshot/readset；缺SDK pin时从唯一原 `maf-sdk:<operation_digest>` publication取得同Run/受权writer SDK并核验bytes，不新造SDK。binding按原raw/sdk/context/tool receipt复算；已有binding必须bytes相符，缺失才补充派生binding。补pins后重读必须恰好raw/sdk/binding三件，随后调用真实 `reconcile_retained`，不直接回假的accepted。
- test的RetainedHost继承真实PlatformWorkerHost，仅第一次 `result:` _publish抛出503，发生在真实committer.receive已提交之后；下次Node.query走原保存内容恢复，保留single failure、真实receipt/model/tool断言。
- 对r6已核的JTI锁、SQL retained disposition、profile/Pod/journal逻辑无变化；这些事实按原SHA复用，不重跑。normal saved分支仍不获得retained补件能力。

此候选先完成定向源码检查，再依据下述r7运行闭合；没有以源码可导入或静态检查代替运行通过。

## r7 最终实证

原始目录：[r7](../../../work/p10-m2/m2-four-p2-r7-20260913T105309Z/)。已实际读取 `pytest.stdout-stderr.txt`、`exit-code.txt`、`working-tree-fingerprint.json`，并核对 `evidence/b5cdd39aebb1` 下controller/Node/Gate/upstream HTTP、PostgreSQL事件及summary。输出为 **1 passed in 11.55s / exit 0**。

候选 HEAD `d61cb91` 里的相关源码blob与fingerprint逐文件SHA-256一致。schema是显式冻结的0013运行版本（SHA-256 `6803916d1c22f3df803c64d0a739df37b46f3b7329acb57388fe85e776dca815`），非HEAD内P08/0014链；relevant dirty paths为空。后续归档提交由Dirac补充，不预写归档SHA。

1. controller HTTP第11行normal submit-result503，13行原Worker archive-sdk200，14行receiver-replay真实receive后一次companion publication故障503，16行恢复accepted及accepted_shared Claim，19行重放同receipt；20行旧Worker await-start revoked。四次submit/replay请求body字节完全一致。
2. PostgreSQL第19421行保留原 `maf-sdk` SDK，21345行提交result_submission，21352行原raw pin，23155/23157行补SDK/binding pins；最终恰好三件，raw ref未改、SDK ref复用原archive、未伪造新raw/SDK。23630行accepted result_receipt早于25300行P05真实exit observation。故障前后恢复的是同一operation与原内容。
3. Node HTTP共7行：首次GET404→一次PUT→查询running/unknown→exited及重复exited；PUT总数1。进程PID68661、birth始终同一，真实exit_code=1（注入的submit失败导致），并未把accepted伪装为exit0。真实结果与进程状态分离。
4. Gate仅3条（2模型请求、1工具调用），upstream2条；summary为2model、accepted结果含1个accepted_shared Claim、Task仍running。测试在late replay前后比较调用数无增加，未重执行模型或工具。

与既核r6两个撤销PASS及r2/r3/pure/Thread证据合并，足以关闭原4P2及其本轮线程/partial-publication残留。正常Writer仍exactself；新增source-writer允许只在retained结果路径且同Run/SQL source绑定下有效，未更改JTI锁、disposition、profile/Pod守卫或派发journal，所以相应原PASS可按原SHA复用。

## 最终边界

**原4P2：4 addressed，0 not-addressed，限定复审PASS。** 本复审没有执行新的测试、DB、HTTP、process、browser或生成检查；只是独立读取源码及Dirac现有实测记录。原 `e40e7e2`、r1-r6结果/归属全部保留。只认可已测Explore host/child、production assembly+实际dispatcher消费及service Thread归属，不提升完整P07/P10、其他work kinds、P08、Pod/K8s或生产上线。永久脱敏归档/归档SHA是后续证据固定工作，不能改变本次运行事实。
