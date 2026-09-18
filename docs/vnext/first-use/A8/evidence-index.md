# A8 证据索引

2026-09-18。A8 代码 `1ddf90b` + 最终协议 `f3230c3`；证据文档为后续独立提交。原始32项、28项和最终BFF协议探针分别绑定当时代码字节，不把文档提交说成被测源码。最后CookieJar修正只由固定A3的14次HTTP协议探针复测，A1/renderer未因该修改重跑。

| 原始证据 | 范围/真实结果 |
| --- | --- |
| [material-observed.json](review-20260918/material-observed.json) | 固定A5 25c5df3，renderer纯探针exit1，2个问题 |
| [material-de958b1-observed.json](review-20260918/material-de958b1-observed.json) | 固定修复de958b1，同一探针exit0，2项反例关闭，partial保留 |
| [bff-protocol.json](review-20260918/bff-protocol.json) | A3真实BFF ASGI+合成下游，11次HTTP，exit0；源摘要在文件中 |
| [bff-access-protocol.json](review-20260918/bff-access-protocol.json) | 最终A3固定1d468931，14次HTTP，exit0；可重登/旧Cookie撤销/注销401 |
| [bff-access-first-cookieconflict.json](review-20260918/bff-access-first-cookieconflict.json) | A8客户端重复加载CookieJar时的失败，已修；保留当时完整报文 |
| [driver-final-tests.txt](review-20260918/driver-final-tests.txt) | 可重登协议定向测试28passed/4deselected/exit0 |
| [bff-protocol-first-422.json](review-20260918/bff-protocol-first-422.json) | 首轮输入只有name被真实BFF正确422拒绝；失败ledger保留 |
| [http-reproduction.md](review-20260918/http-reproduction.md) | 从上述HTTP ledger逐项输出方法/URL/headers/请求和响应正文，不截断 |
| [run-history.json](review-20260918/run-history.json) | 命令/退出码/实际计数与适用范围，含fixture错误历史 |
| [review-20260918.png](screenshots/review-20260918.png) | 实际浏览器显示这些原始观察数据；不充当产品浏览器截图 |

A1 真实 PG 初轮失败原审计（临时目录，仅用于原因核对、不承诺长期保留）：`/private/var/folders/vr/mqgnp21s1lg8n3b5052v3ckw0000gq/T/pytest-of-yym1ng/pytest-852/test_a1_frozen_environment_set1/pg.jsonl`。前置行带started_at解释了“空操作”用例实际不空；output_expectation=unknown解释了另一个失败。修正仅在新增A8测试的动作前设置输入。

Cookie/Set-Cookie/本机Access只在公开交换中标 `[REDACTED]`；历史bootstrap记录同样脱敏。复现时用A0受限配置重新登录，不能复用示例cookie。没有provider Key、真实敏感正文或私有配置文件入Git。

源SHA对原始Artifact字节，表示SHA对UTF-8表示字节，不能互换。未执行的DG1/DG2/DG3保持not_run；不因为本目录出现截图或HTTP包就放行87项。
