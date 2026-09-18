# A8 首用 driver 合同

该文件是测试 driver 的输入/输出合同，不是公开生产 API，也不修改 OpenAPI。A0 集成后只需把真实 BFF 地址、TaskCreate JSON 和受权读链证据交给 driver。

## 调用

```bash
./scripts/vnext/uv.sh run python scripts/vnext/first_use_acceptance.py run \
  --base-url http://127.0.0.1:44180 \
  --create-payload /private/task-create.json \
  --auth-env WUJI_FIRST_USE_BEARER \
  --read-chain /private/read-chain.json \
  --candidate-sha <fixed-integration-sha> \
  --evaluation-mode mechanism_synthetic \
  --output /private/first-use-evidence.json
```

`WUJI_FIRST_USE_BEARER` 只存在于进程环境；driver 不打印、写入 Git 或普通证据。也可以使用 BFF Cookie/session 适配，但应由 A0 通过受信本机环境注入，不把值写到 Task 文本。

## read-chain 输入

完整 JSON 对象至少包含：

```json
{
  "task_id": "<TaskView.task_id>",
  "run_id": "<AgentRun.id>",
  "tool_call_id": "<ToolCall.id>",
  "artifact_ref": {"id": "<sealed Artifact>", "revision": "1"},
  "read_set": [{"entity_type": "artifact", "id": "<same Artifact>", "revision": "1"}],
  "model_attempt_ids": ["<first ModelAttempt>", "<second ModelAttempt>"],
  "material": {
    "status": "delivered",
    "source": {
      "artifact_ref": {"id": "<same Artifact>", "revision": "1"},
      "artifact_sha256": "<64 lowercase hex>"
    },
    "representation": {
      "encoding": "utf-8",
      "text": "<actual fixture material, including marker in the second request>",
      "representation_sha256": "<64 lowercase hex>"
    }
  }
}
```

这只核对引用/正文/摘要的一致性，不把模型文本当作事实，也不判定业务答案。`read_set` 必须来自平台保存的实际快照或交接记录，不可由 driver 根据 `task_id` 猜造。

## 安全与边界

- driver 只允许本地 HTTP BFF 公共 Task 路径；不直接调用 provider、Kali、owner 或 internal model route。
- F1/F2 fixture 的独立答案/评分文件不在材料目录、Task Goal、driver 输入或运行时环境中；fixture 只回显随机 marker 和当前安全读取材料。
- HTTP 证据保存完整方法、URL、非敏感 headers、请求体、状态、响应 headers、响应体；Authorization/Cookie 等敏感 headers 脱敏并注明。
- 读链缺失、BFF 不可达、现场未许可均为 `blocked`，不是 synthetic pass。
