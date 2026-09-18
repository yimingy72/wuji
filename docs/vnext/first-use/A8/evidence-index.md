# A8 首用证据索引（初始）

状态：未验收。此索引只登记证据形状和当前缺口；未生成通过结论。

## 证据目录

```text
docs/vnext/first-use/A8/
  acceptance-results.json       # 87 项，初始全部 not_run
  integration-review.md         # 本次独立静态发现与 DG 结论
  driver-contract.md            # 真实 BFF driver/read-chain 输入合同
  evidence-index.md
  screenshots/                  # A0 集成后写入实际浏览器/终端截图
  request-packages/             # 无害 fixture 可保存完整请求/响应；敏感材料只存受限引用
```

当前没有可提交的实测截图；`screenshots/README.md` 明确标记待 A8 固定 SHA 运行后补齐。由于没有真实运行，87 项保持 `not_run` 或 `blocked`，不把 fixture 单测当作 E2E。

## 每条结果必备字段

`test_id`、`candidate_sha`、运行环境/镜像、配置摘要、执行日期、实际命令、退出码、`status`、`observed`、`evidence_refs`。HTTP/UI 成果还需 `screenshots/` 下至少一张实际截图及完整脱敏报文。

## HTTP 报文要求

F1/F2 自建无害 fixture 可以保留完整：方法、URL、请求 headers、请求体、响应状态、响应 headers、响应体；A8 driver 对 BFF 交换同样保留非敏感字段，Authorization/Cookie 只保留 `[REDACTED]` 占位，不把 Key 放入普通报告。source digest 与 representation digest 分开记录。

## 现有缺口

| 证据 | 当前状态 | 解除条件 |
| --- | --- | --- |
| 浏览器新建 Task 截图 | blocked | A0 提供同一候选本地 BFF 页面和登录/主体模式 |
| create/start/readiness/launch/pause/cancel 完整报文 | not_run | 运行 `first_use_acceptance.py run` 并保存输出 |
| F1 marker→第二次模型请求 | not_run | A5/A6 接入真实 Gate/MAF 后提供 ModelAttempt 与 fixture 计数关联 |
| F2 变体→后续 Reason | not_run | 真实读取后提供 exact read-set 与后续 Intent/Reason 记录 |
| DeepSeek usage/费用 | blocked | A0/A6 提供受信网关记录、有效预算和允许外发数据 |
| 用户指定现场 | blocked | A0 明确现场实例/安全入口/停止许可；A8 不自行访问 |
