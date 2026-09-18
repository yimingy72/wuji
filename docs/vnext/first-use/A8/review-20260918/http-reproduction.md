# 完整复现报文：A8 BFF 协议验证

固定 A3 `1d46893163a54e5acd6a50f1f430c828fd777aa8`；源摘要 `73b799950964bc90b3b29bbe3c17dc494ec35fd7b090f74394582a34a383c511`。

范围：真实 BFF ASGI，合成下游 API；不是产品 E2E。以下逐项来自原始 ledger，不截断正文。Cookie、Set-Cookie 与本机 Access 凭据脱敏；复现须由 A0 提供有效本机入口凭据。关键验证点：写请求精确 Origin、Cookie 身份；relogin 后旧 Cookie 401，logout 后当前 Cookie 401。

## 1. POST http://127.0.0.1:44991/auth/login

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/auth/login HTTP/1.1
host: 127.0.0.1:44991
content-length: 0
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
x-wuji-local-access: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-length: 231
content-type: application/json
set-cookie: [REDACTED]

{"authenticated":true,"mode":"local_single_operator","subject":"operator-a8","display_name":"A8 synthetic local operator","tenant_id":"tenant-a8","project_id":"project-a8","initial_task_id":null,"expires_at":"2026-09-18T10:47:51Z"}
```

## 2. GET http://127.0.0.1:44991/auth/session

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/auth/session HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-length: 231
content-type: application/json

{"authenticated":true,"mode":"local_single_operator","subject":"operator-a8","display_name":"A8 synthetic local operator","tenant_id":"tenant-a8","project_id":"project-a8","initial_task_id":null,"expires_at":"2026-09-18T10:47:51Z"}
```

## 3. POST http://127.0.0.1:44991/api/v2/tasks

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/api/v2/tasks HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
content-type: application/json
idempotency-key: a8-create
cookie: [REDACTED]
content-length: 679

{"authorization_expires_at": "2099-01-01T00:00:00Z", "authorization_scope": [{"host": "fixture.invalid", "port": 443, "protocol": "https"}], "budget": {"amount": "5", "currency": "USD"}, "goal": {"criteria": [{"allowed_methods": ["deterministic"], "condition": "version captured", "criterion_id": "version", "evidence_requirements": ["sealed bytes"], "object": "fixture bytes", "required": true, "responsible_party": "fixture-checker"}], "text": "Read the fixture version"}, "model_profile_ref": "fixture-model-v1", "name": "Created fixture task", "project_id": "project-a8", "runtime_profile_ref": "fixture-runtime-v1", "scenario": "web_single", "schema_version": "wuji.api.v2"}
```

响应：

```http
HTTP/1.1 201
cache-control: no-store
content-type: application/json
content-length: 84

{"task_id":"task-a8","version":"1","desired_state":"pause","observed_state":"ready"}
```

## 4. GET http://127.0.0.1:44991/api/v2/tasks/task-a8/readiness

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/api/v2/tasks/task-a8/readiness HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-type: application/json
content-length: 62

{"task_id":"task-a8","version":"2","observed_state":"running"}
```

## 5. GET http://127.0.0.1:44991/api/v2/tasks/task-a8/launch

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/api/v2/tasks/task-a8/launch HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-type: application/json
content-length: 62

{"task_id":"task-a8","version":"2","observed_state":"running"}
```

## 6. POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
content-type: application/json
idempotency-key: a8-start
cookie: [REDACTED]
content-length: 125

{"command": "start", "expected_version": "1", "reason": "synthetic upstream protocol check", "schema_version": "wuji.api.v2"}
```

响应：

```http
HTTP/1.1 202
cache-control: no-store
content-type: application/json
content-length: 50

{"command_id":"command-a8","resource_version":"2"}
```

## 7. POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
content-type: application/json
idempotency-key: a8-pause
cookie: [REDACTED]
content-length: 125

{"command": "pause", "expected_version": "1", "reason": "synthetic upstream protocol check", "schema_version": "wuji.api.v2"}
```

响应：

```http
HTTP/1.1 202
cache-control: no-store
content-type: application/json
content-length: 50

{"command_id":"command-a8","resource_version":"2"}
```

## 8. POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/api/v2/tasks/task-a8/commands HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
content-type: application/json
idempotency-key: a8-cancel
cookie: [REDACTED]
content-length: 126

{"command": "cancel", "expected_version": "1", "reason": "synthetic upstream protocol check", "schema_version": "wuji.api.v2"}
```

响应：

```http
HTTP/1.1 202
cache-control: no-store
content-type: application/json
content-length: 50

{"command_id":"command-a8","resource_version":"2"}
```

## 9. GET http://127.0.0.1:44991/auth/session

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/auth/session HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-length: 231
content-type: application/json

{"authenticated":true,"mode":"local_single_operator","subject":"operator-a8","display_name":"A8 synthetic local operator","tenant_id":"tenant-a8","project_id":"project-a8","initial_task_id":null,"expires_at":"2026-09-18T10:47:51Z"}
```

## 10. POST http://127.0.0.1:44991/auth/login

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/auth/login HTTP/1.1
host: 127.0.0.1:44991
content-length: 0
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
x-wuji-local-access: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-length: 231
content-type: application/json
set-cookie: [REDACTED]

{"authenticated":true,"mode":"local_single_operator","subject":"operator-a8","display_name":"A8 synthetic local operator","tenant_id":"tenant-a8","project_id":"project-a8","initial_task_id":null,"expires_at":"2026-09-18T10:47:52Z"}
```

## 11. GET http://127.0.0.1:44991/auth/session

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/auth/session HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 200
cache-control: no-store
content-length: 231
content-type: application/json

{"authenticated":true,"mode":"local_single_operator","subject":"operator-a8","display_name":"A8 synthetic local operator","tenant_id":"tenant-a8","project_id":"project-a8","initial_task_id":null,"expires_at":"2026-09-18T10:47:52Z"}
```

## 12. GET http://127.0.0.1:44991/auth/session

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/auth/session HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 401
cache-control: no-store
content-length: 152
content-type: application/json

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"b68cd6b2-5175-4374-9f59-d41bc1225db7","retryable":false,"details":{}}
```

## 13. POST http://127.0.0.1:44991/auth/logout

请求（方法/完整 URL/Headers/正文）：

```http
POST http://127.0.0.1:44991/auth/logout HTTP/1.1
host: 127.0.0.1:44991
content-length: 0
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json
origin: http://127.0.0.1:44991
cookie: [REDACTED]


```

响应：

```http
HTTP/1.1 204
cache-control: no-store
set-cookie: [REDACTED]


```

## 14. GET http://127.0.0.1:44991/auth/session

请求（方法/完整 URL/Headers/正文）：

```http
GET http://127.0.0.1:44991/auth/session HTTP/1.1
host: 127.0.0.1:44991
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: testclient
accept: application/json


```

响应：

```http
HTTP/1.1 401
cache-control: no-store
content-length: 152
content-type: application/json

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"0fee1698-2e6d-4c8d-9cf5-34899e5588ac","retryable":false,"details":{}}
```
