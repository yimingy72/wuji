# 模型网关基础验证

- **日期**：2026-09-09
- **授权**：用户提供接口与凭据并允许测试
- **范围**：模型发现、固定短文本、空参数模拟工具调用；未发送项目文件或目标数据，未执行目标工具
- **状态**：基础协议验证完成；Agent SDK / Harness 集成尚未验证

## 1. 接口配置

| 协议 | 用户提供的 base URL | 本轮实际请求路径 |
| --- | --- | --- |
| OpenAI 兼容 | `https://ai-api-gateway.app.baizhi.cloud/api/openai` | `/api/openai/models`、`/api/openai/chat/completions`、`/api/openai/responses` |
| Anthropic 兼容 | `https://ai-api-gateway.app.baizhi.cloud/api/anthropic` | `/api/anthropic/v1/models`、`/api/anthropic/v1/messages` |

OpenAI 使用 Bearer 认证；Anthropic 使用 `x-api-key` 与 `anthropic-version: 2023-06-01`。上表为实际成功路径，客户端接入时须检查 URL 拼接，不要为两个 base URL 统一追加 `/v1`。

凭据只用于本次请求，未写入仓库、前端、配置样例或验证记录。后续后端接入从环境或 Secret 引用读取；前端仅展示服务端允许公开的模型能力与配置状态。

## 2. 实际结果

| 请求 | 模型 | 结果 | 已证明的能力 |
| --- | --- | --- | --- |
| 两个模型列表 GET | — | 均 HTTP 200，返回相同的 35 个 ID | 两种发现接口可访问；不代表列表内每个模型实时可用 |
| Chat Completions：请求工具调用 | `qwen-flash` | HTTP 200，约 0.71 秒 | 返回 `wuji_ping`、空对象参数及工具调用 ID |
| Chat Completions：回传工具结果 | `qwen-flash` | HTTP 200，约 0.71 秒 | 正确接收关联结果并回复 `WUJI_GATEWAY_OK` |
| Messages：请求工具调用 | `qwen-flash` | HTTP 200，约 0.63 秒 | 返回 `tool_use`，工具名与输入符合请求 |
| Messages：回传工具结果 | `qwen-flash` | HTTP 200，约 0.61 秒 | 接收 `tool_result` 并回复 `WUJI_GATEWAY_OK` |
| Responses：短文本 | `gpt-5.4-mini` | HTTP 502，约 1.50 秒；上游称模型暂不可用 | 该模型在本次请求不可用；不能据此判定 Responses 不支持 |
| Responses：单独换模型验证 | `qwen-flash` | HTTP 200，约 0.68 秒，状态 completed | 非流式文本返回 `WUJI_GATEWAY_OK` |

共发出 2 次 GET、6 次 POST。模拟工具的结果固定为 `{"ok":true}`；没有根据模型输出执行文件或网络操作。客户端开启 TLS 证书验证、禁止自动跳转、设置超时与响应大小上限；没有客户端自动重试。最后一条是显式更换模型的一次独立能力探测。

成功响应返回了 Token 用量；失败请求没有可用用量，不能视为零消耗。延迟为少量样本的观察值，不能用于吞吐量或 SLA 承诺。本地脱敏结果位于 `artifacts/model-gateway/connectivity.json`，该目录已被 Git 忽略；本文保留可审查结论。

## 3. 能力边界与下一步

已验证的是上述协议与 `qwen-flash` 的具体请求组合。它可用于后续基础接入验证，尚未通过安全评估推理能力测试，不作为正式主模型选型结论。

以下项目仍未验证：SSE 流式工具增量、断线和取消、并行工具调用、复杂 Schema 与严格结构化输出、上下文压缩、SDK 会话恢复、长任务稳定性、所有模型的实时可用性、真实底层模型身份、上游内部重试和计费对账。

列表没有 `claude-*` ID；Anthropic 协议兼容不能推导已经提供 Claude 模型。Responses 文本成功也不能推导 Codex 的完整运行时已经兼容。没有安装或启动 Claude Agent SDK、Codex SDK、pi、Deep Agents 或 DeepSeek Harness 做端到端测试。

后续按 [Agent 执行框架决策](agent-harness-decision.md) 验证一个默认候选，并将“协议能力”“实际模型可用性”“Harness 能力”分别登记。上游共享配额映射、数据策略与重试可观测性满足主架构要求前，本结果只支持开发接入，不代表生产模型网关验收通过。
