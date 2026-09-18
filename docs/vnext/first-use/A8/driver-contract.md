# A8 HTTP 控制 driver（v2，非 E2E）

`scripts/vnext/first_use_acceptance.py control` 每次只执行一个明确动作。`create`、`start`、`read`、`pause`、`cancel` 分开调用；start 后由 A0 采集模型/工具/Reason 数据，再发停止命令。它不直接请求目标、模型、owner 或 internal 接口，不用预填 read-chain 文件给新 Task 宣布成功。

## 本地 BFF 协议

已与 A3 确认最终协议，并对固定 `1d46893163a54e5acd6a50f1f430c828fd777aa8` 实测：

- `POST /auth/login`：空正文、精确 Origin/Host、`X-Wuji-Local-Access`，来自部署 `local_access_token_file`。该本机 access secret 可重复兑换，不能当作多用户登录。
- `GET /auth/session`：`wuji_vnext_session` Cookie；返回 `mode=local_single_operator`。后续每次 mutation 都发送 Origin。
- Cookie 仅写 A0 指定的仓库外 0600 session 文件，后续动作复用 Cookie。显式 `--relogin --access-env ...` 重新兑换会撤销所有旧会话；过期不会静默重新登录。Authorization 不参与协议。
- `POST /auth/logout` 撤销后，原 Cookie 读取 session 返回 401。

access 环境变量由 A0 在受信本机环境注入；不把值放进命令行、Git、普通报文、浏览器存储或截图。provider Key 不参与 driver。session 的 `initial_task_id` 仅为 UI 提示，driver 不用它选择/授权 Task。

## 调用

保留 `scripts/vnext/uv.sh` 工具链。独立工作树测试使用主树解释器，加 `PYTHONPATH` 指向本树，避免重装 editable 或修改锁。以下 `python` 指该已配置解释器：

```sh
python scripts/vnext/first_use_acceptance.py control \
  --action create --base-url http://127.0.0.1:44180 \
  --create-payload /private/task-create.json \
  --session-file /private/a8-session.json --access-env WUJI_A8_LOCAL_ACCESS \
  --state /private/a8-control-state.json --output /private/a8-create-observed.json \
  --candidate-sha <完整40位固定候选SHA>
```

后续命令保留同一个 `--state` 和 `--session-file`，去掉 `--create-payload/--access-env`，改 `--action start|read|pause|cancel`，每次指定新的 `--output`。driver 不自动重投已登记操作；丢响应时先使用原 journal 中的 Idempotency-Key/路径/回执核对。单一 state 文件不供并发 driver 进程共写。

轮询只看 `observed_state`。cancel 后仅等到 `closed` 才结束 HTTP 状态等待；`paused/reconciling/quiescing` 返回 blocked。即使 closed，结果仍标 `process_stop/operations_settled/billing=not_verified`，需要独立运行账本佐证。

完整 HTTP ledger 在发送前与每次响应后保存，最后的失败/超限/未知也保留。Cookie、Set-Cookie 和 access header 脱敏；未脱敏 JSON 保留原始正文。超限明确 incomplete，不能作为完整响应证据。返回码：0=该控制动作观察完成；1=失败；2=阻断/状态待核对。输出永远保留 `e2e_status=not_run`。

## 独立原始采集包核对

```sh
python scripts/vnext/first_use_acceptance.py validate-read-chain \
  --input /private/a8-actual-captures.json \
  --task-id <本次新建Task> --candidate-sha <完整40位固定候选SHA>
```

输入必须包含 `task_id/candidate_sha/run_id/tool_call_id/native_tool_call_id/marker`、真实 `source_bytes_base64`、`artifact_ref={id,version,sha256}`、确切 `read_set`、`tool_receipt`、完整材料 v2，以及有原始 request/response body 的两条有序 `model_captures`（各带 Task/Run/ModelAttempt）。模型响应支持 JSON 和 Chat Completions SSE。

检查源字节 SHA、BlobRef 的版本/摘要、read-set 的完整引用相等、材料 UTF-8 长度/摘要、第一请求未预载 marker、第一响应实际发出原生 call ID、第二请求的 tool message 包含同一完整 receipt+material。substring、非 dict ref、缺正文、篡改摘要/长度/Task/版本全部拒绝。

这只验证受信导出包的离线一致性，不能认证任意手写文件的来源。正式 DG1/DG2 仍须 A8 对照平台与网关原始记录、fixture 计数、浏览器和固定构建；不以校验 exit 0 自动填写 87 项矩阵。
