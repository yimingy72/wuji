# P05 fix round1 · controller review

2026-09-13。结论：**PASS**。本次是主控制器对 `4c57bb2d6768e0195973fcf7a48198ef0e018f01..3102579a5b1a19b164d08972d068e924e7448bfe` 的定向独立代码复核及证据包离线核对；没有重跑修复用例、原 P05 28 项、SDK 或其他阶段测试，也不把实施者已采集的结果称为本次独立测试。

## 两项审查目标

- **F1 closed 保持：通过。** `_observe_task` 在任务已为 `closed` 时不再重算 observed_state 或递增 control_version。reconcile 与迟到 observation 仍经过原持久入口；新守卫只阻止终态投影被覆盖，不重新开放 execution_allowed，也不跳过历史 observation 的登记。
- **F2 结算后输入恢复：通过。** `_settle` 在已确认退出、操作已结算、pending input 已持久且 `_recoverable` 成立时接纳 `reconciling`，随后在现有 Task/Work 锁与同一事务内调用 `_update_work` 和 `_restore`，依次走公开图中既有的 `reconciling→suspended`、`suspended→waiting_input`。存在 user_hold 等 suspension cause 时 `_stop` 保持 `suspended` 与 wait_ref，显式 resume 后才恢复；已解除的 `operations_unsettled` 被清除。

实际代码提交只含 `packages/wuji-core/src/wuji_core/execution/control.py` 与 `tests/vnext/test_p05_fix_round1.py`。没有发现要求继续修改代码的确切问题。

## 复用的已采集证据

实施者在提交前固定候选 tree `86915aa1e2f77c9ad941fc717e18a9fd2d79f3ef` 上采集一次最终 GREEN，记录为 **3 passed / 2.38s / exit 0**；该 tree 与代码提交 `3102579^{tree}` 离线核对一致。三项分别覆盖 closed 后 reconcile/迟到观察、退出后结算恢复 pending input、hold 下保持 suspended 并在显式 resume 后恢复。对应 JUnit 为 3 tests、0 failures、0 errors，`test-results.json` 三项均为 pass。以上均为复用的实施者证据。

## 证据包核对

- `review-counterexamples.tar.gz` 4 个成员、`red-runtime-redacted.tar.gz` 10 个成员、`final-runtime-redacted.tar.gz` 10 个成员；全部为普通相对路径文件，成员数量、长度和 SHA256 与 `archive-members.json` 一致。
- 离线解析所有 JSON/JSONL 成功；F2 最终 SQL 记录中的 suspended 与 waiting_input 两次 UPDATE 均返回 UPDATE 1，且两者之间没有 transaction_commit。
- `http-reproduction.md` 的方法、URL、Headers、空请求体、状态码、响应 Headers 与完整响应体，与最终归档中同一 F2 exchange 一致。Bearer 已替换为 `<EPHEMERAL_TEST_JWT_REISSUE>`；P05 没有控制 HTTP 路由，报告没有伪造对应端点。
- 已实际查看 `screenshots/f1-f2-verification.jpg`，内容与 test-results、代码 SHA 和范围说明一致。通用密钥/JWT/凭据 URL/未替换 Bearer 扫描无命中；交付副本另将 RED 输出中的本机 pytest 临时路径和 JUnit hostname 替换为明确占位符。
- 本轮没有发现新目标资产或接口，因此无需更新资产梳理文档。

本结论只关闭 P05-review 的 F1/F2，不扩大为完整 Runtime、Supervisor、P08/P09/P10/P11/P12 集成或全平台验收。
