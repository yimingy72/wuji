# A8 重验完整脱敏 HTTP 复现包

来源：`seams-02/budget-lost-response.json`。候选工作树 HEAD `ef8d4624c80a4a6ba763654b1feab3ee0bb7f7e4`，其中生产修复为父提交 `f957a46dbafb6d842212aaeeed69085d03445e70`。

边界必须区分：Task API 报文来自真实 FastAPI/HTTPX ASGI 路由、正式签名校验和真实隔离 PostgreSQL，但不是监听端口上的已部署服务；预算管理报文来自明确的 `httpx.MockTransport` 合成网关，不是真实 LiteLLM 或供应商。没有访问 Kubernetes、DeepSeek 或目标。唯一凭据是本地测试 JWT，已统一替换为 `[REDACTED TEST CREDENTIAL]`；合成 `sk-...` 只存在于测试进程，不对应任何服务。

## 1. 创建不运行 Task（真实应用路由 + 真实 PostgreSQL）

验证点：创建仅持久化 `pause/ready`，不启动执行。

```http
POST http://testserver/api/v2/tasks HTTP/1.1
Host: testserver
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Authorization: [REDACTED TEST CREDENTIAL]
Idempotency-Key: a8-lost-budget-create
Content-Length: 641
Content-Type: application/json

{"schema_version":"wuji.api.v2","project_id":"project-fixture","name":"Created fixture task","scenario":"web_single","goal":{"text":"Read the fixture version","criteria":[{"criterion_id":"version","object":"fixture bytes","condition":"version captured","evidence_requirements":["sealed bytes"],"allowed_methods":["deterministic"],"responsible_party":"fixture-checker","required":true}]},"authorization_scope":[{"host":"fixture.invalid","protocol":"https","port":443}],"authorization_expires_at":"2099-01-01T00:00:00Z","model_profile_ref":"fixture-model-v1","runtime_profile_ref":"fixture-runtime-v1","budget":{"amount":"5","currency":"USD"}}
```

```http
HTTP/1.1 201 Created
Content-Length: 353
Content-Type: application/json
X-Request-Id: 1e923c56-355d-45d6-80d3-ce824dea975a

{"task_id":"26c5299b-7872-42c1-bb7d-3e2a69497809","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

## 2. 同 Key 读取 Task（真实应用路由 + 真实 PostgreSQL）

```http
GET http://testserver/api/v2/tasks/26c5299b-7872-42c1-bb7d-3e2a69497809 HTTP/1.1
Host: testserver
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Authorization: [REDACTED TEST CREDENTIAL]

```

```http
HTTP/1.1 200 OK
Content-Length: 369
Content-Type: application/json
X-Request-Id: 5087d584-bf76-49d0-853f-47fb099b36c6

{"task_id":"26c5299b-7872-42c1-bb7d-3e2a69497809","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":["start","cancel"]}
```

## 3. 显式启动（真实应用路由 + 真实 PostgreSQL）

```http
POST http://testserver/api/v2/tasks/26c5299b-7872-42c1-bb7d-3e2a69497809/commands HTTP/1.1
Host: testserver
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Authorization: [REDACTED TEST CREDENTIAL]
Idempotency-Key: a8-lost-budget-start
Content-Length: 100
Content-Type: application/json

{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"first-use start"}
```

```http
HTTP/1.1 202 Accepted
Content-Length: 246
Content-Type: application/json
X-Request-Id: 1cddf019-6b1d-4162-b020-8316616fd09b

{"command_id":"a8-lost-budget-start","disposition":"accepted","resource_ref":{"entity_type":"task","id":"26c5299b-7872-42c1-bb7d-3e2a69497809","revision":"1"},"resource_version":"1","request_id":"1cddf019-6b1d-4162-b020-8316616fd09b","code":null}
```

## 4. 预算管理丢响应与同 Key GET 恢复（合成网关）

验证点：首次 GET 确认 Key 不存在；POST 已由合成网关持久化但响应丢失；恢复轮只对同一 Key hash 再次 GET，不发送第二次 POST。该段证明本地协议，不冒充真实 LiteLLM 服务。

```http
GET https://synthetic-budget.invalid/key/info?key=46d516cc1e6fb82368af3955269eed6e99782cb10164b1d63fda7b22c8329e69 HTTP/1.1
Host: synthetic-budget.invalid
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1

```

```http
HTTP/1.1 404 Not Found
Content-Length: 0

```

```http
POST https://synthetic-budget.invalid/key/generate HTTP/1.1
Host: synthetic-budget.invalid
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Content-Type: application/json
Content-Length: 201

{"key":"sk-synthetic-budget-test-only-0000000000000000","models":["model-fixture"],"max_budget":1.0,"metadata":{"wuji_task_id":"26c5299b-7872-42c1-bb7d-3e2a69497809","wuji_tenant_id":"tenant-fixture"}}
```

```text
NO HTTP RESPONSE: httpx.ReadTimeout("synthetic lost accepted response")
Synthetic transport state after the exception: key persisted = true
```

```http
GET https://synthetic-budget.invalid/key/info?key=46d516cc1e6fb82368af3955269eed6e99782cb10164b1d63fda7b22c8329e69 HTTP/1.1
Host: synthetic-budget.invalid
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1

```

```http
HTTP/1.1 200 OK
Content-Length: 153
Content-Type: application/json

{"info":{"models":["model-fixture"],"max_budget":1,"metadata":{"wuji_task_id":"26c5299b-7872-42c1-bb7d-3e2a69497809","wuji_tenant_id":"tenant-fixture"}}}
```

## 5. 读取恢复后的 Launch（真实应用路由 + 真实 PostgreSQL）

```http
GET http://testserver/api/v2/tasks/26c5299b-7872-42c1-bb7d-3e2a69497809/launch HTTP/1.1
Host: testserver
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Authorization: [REDACTED TEST CREDENTIAL]

```

```http
HTTP/1.1 200 OK
Content-Length: 491
Content-Type: application/json
X-Request-Id: 4800b7b6-522e-4d0e-a06c-9eb8a63b447e

{"operation_id":"a8-lost-budget-start","command_id":"a8-lost-budget-start","task_id":"26c5299b-7872-42c1-bb7d-3e2a69497809","definition_digest":"cf025177c31e7d53eb90d8e645bc3fa3968bcf6b56f44ed4eec6a21d5bd8fb78","profile_digest":"82361b6c3016e44df649fc731e8d334c1acef7c3937c6d311f02c1c44148f07b","runtime_attempt":"1","execution_epoch":"2","phase":"ready","phase_status":"succeeded","reason_code":null,"allowed_actions":["pause","cancel","finish"],"observed_at":"2026-09-19T10:26:05.306192Z"}
```

请求顺序断言为 `GET /key/info → POST /key/generate（响应丢失）→ GET /key/info`，两次 GET 的 `key` 查询完全相同；`task_key_reads` 也记录同一个 tenant/task 被读取两次。完整结构化原始记录见 `seams-02/budget-lost-response.json`，以上正文无字段截断。
