# P07 M1 独立审查修复接口状态

绑定代码 SHA：`5cfd581129c7991deaddaad9bfdaf8b4ee34b140`。

| 接口/资产 | 验证状态 | 当前行为 |
| --- | --- | --- |
| `MafRuntime(..., token_verifier=...)` | 已利用 | 首次 SDK 请求前用真实 TokenVerifier 验签 bearer |
| `PlatformWorkerHost.resolve(..., verified_principal=...)` | 已利用 | Principal 必须与 Host access 完全相同，registry binding full RunIdentity 必须与 Assignment 相同 |
| 两个有效 Run 的错配负控 | 已利用 | Run B token + Run A Host/Assignment 返回 `STALE_EXECUTION`，零 Gate HTTP、零上游、零 model attempt |
| native `ChatCompletionRequest` | 已利用 | 原样保留 `parallel_tool_calls=false`、`stream_options.include_usage=true`、`max_completion_tokens`；与 `max_tokens` 互斥 |
| OpenAPI / Python / TypeScript DTO | 已利用 | 生成检查 exit 0；P06 原样入账、仅替换发布的 upstream model 名称 |
| SDK archive publication | 已利用 | sealed `application/x-ndjson` 由稳定 `maf-sdk:<operation digest>` publication 固定 |
| Result binding publication | 已利用 | `result:<submission_id>` 同时引用 raw、SDK 与 canonical binding artifacts |
| Canonical result binding | 已利用 | 固定 raw/sdk refs 与 digest、完整 RunIdentity、context/read_set/record_refs/relations digest、实际 tool receipt IDs/digest |
| Result replay | 已利用 | 先比较完整 binding；SDK/tool/context 任一变化均 `INPUT_DIGEST_CONFLICT`，相同输入返回原 P04 receipt |
| 新 DDL / migration | 未使用 | 复用既有 publication/publication_ref；未修改 0010、schema、migrate 或 snapshot |
| 完整 P07 / P08 恢复 / Supervisor / Scheduler | 未利用 | 仍为后续范围，本结果只证明 hosted M1 闭环 |
