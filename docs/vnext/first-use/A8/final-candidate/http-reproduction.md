# 完整复现报文：固定5cdbd17的预算/启动接缝

来源：真实ASGI Task API + 隔离PG；网关是httpx合成transport，不是DeepSeek。以下正文完整保留，Authorization标为 `[REDACTED TEST CREDENTIAL]`。核对点：首轮Key创建响应丢失后launch错误终结；修订用例明确执行同Key GET恢复。预设合成provider不能证明DG2。

## 第一轮实际failed观察

被测SHA：`5cdbd170939f1d2e410868ab591381331f5cdba9`。模式：`real_pg_launch_synthetic_gateway`。

### 1. POST http://testserver/api/v2/tasks

```http
POST http://testserver/api/v2/tasks HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]
idempotency-key: a8-lost-budget-create
content-length: 641
content-type: application/json

{"schema_version":"wuji.api.v2","project_id":"project-fixture","name":"Created fixture task","scenario":"web_single","goal":{"text":"Read the fixture version","criteria":[{"criterion_id":"version","object":"fixture bytes","condition":"version captured","evidence_requirements":["sealed bytes"],"allowed_methods":["deterministic"],"responsible_party":"fixture-checker","required":true}]},"authorization_scope":[{"host":"fixture.invalid","protocol":"https","port":443}],"authorization_expires_at":"2099-01-01T00:00:00Z","model_profile_ref":"fixture-model-v1","runtime_profile_ref":"fixture-runtime-v1","budget":{"amount":"5","currency":"USD"}}
```

```http
HTTP/1.1 201
content-length: 353
content-type: application/json
x-request-id: 93b6ad45-b0a6-4829-b224-0f84e40653fa

{"task_id":"37e95d33-5c6b-483c-8dc4-206cdcd5d8c4","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

### 2. GET http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4

```http
GET http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4 HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]


```

```http
HTTP/1.1 200
content-length: 369
content-type: application/json
x-request-id: 6b8234bc-4361-4467-b777-150180426c91

{"task_id":"37e95d33-5c6b-483c-8dc4-206cdcd5d8c4","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":["start","cancel"]}
```

### 3. POST http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4/commands

```http
POST http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4/commands HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]
idempotency-key: a8-lost-budget-start
content-length: 100
content-type: application/json

{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"first-use start"}
```

```http
HTTP/1.1 202
content-length: 246
content-type: application/json
x-request-id: 9e5b3c8b-3e88-49e7-9712-188f79800992

{"command_id":"a8-lost-budget-start","disposition":"accepted","resource_ref":{"entity_type":"task","id":"37e95d33-5c6b-483c-8dc4-206cdcd5d8c4","revision":"1"},"resource_version":"1","request_id":"9e5b3c8b-3e88-49e7-9712-188f79800992","code":null}
```

### 4. GET http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4/launch

```http
GET http://testserver/api/v2/tasks/37e95d33-5c6b-483c-8dc4-206cdcd5d8c4/launch HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]


```

```http
HTTP/1.1 200
content-length: 484
content-type: application/json
x-request-id: 0081212e-43cc-472b-a929-743847b7ac87

{"operation_id":"a8-lost-budget-start","command_id":"a8-lost-budget-start","task_id":"37e95d33-5c6b-483c-8dc4-206cdcd5d8c4","definition_digest":"cf025177c31e7d53eb90d8e645bc3fa3968bcf6b56f44ed4eec6a21d5bd8fb78","profile_digest":"82361b6c3016e44df649fc731e8d334c1acef7c3937c6d311f02c1c44148f07b","runtime_attempt":"1","execution_epoch":"1","phase":"prepare","phase_status":"failed","reason_code":"launch_adapter_failed","allowed_actions":[],"observed_at":"2026-09-19T10:04:25.487257Z"}
```

## 修订预算恢复语义观察

被测SHA：`5cdbd170939f1d2e410868ab591381331f5cdba9`。模式：`real_pg_launch_synthetic_gateway`。

### 1. POST http://testserver/api/v2/tasks

```http
POST http://testserver/api/v2/tasks HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]
idempotency-key: a8-lost-budget-create
content-length: 641
content-type: application/json

{"schema_version":"wuji.api.v2","project_id":"project-fixture","name":"Created fixture task","scenario":"web_single","goal":{"text":"Read the fixture version","criteria":[{"criterion_id":"version","object":"fixture bytes","condition":"version captured","evidence_requirements":["sealed bytes"],"allowed_methods":["deterministic"],"responsible_party":"fixture-checker","required":true}]},"authorization_scope":[{"host":"fixture.invalid","protocol":"https","port":443}],"authorization_expires_at":"2099-01-01T00:00:00Z","model_profile_ref":"fixture-model-v1","runtime_profile_ref":"fixture-runtime-v1","budget":{"amount":"5","currency":"USD"}}
```

```http
HTTP/1.1 201
content-length: 353
content-type: application/json
x-request-id: 826144b7-5692-4735-b4f9-73d14c25717d

{"task_id":"a60d33de-94f2-42d9-bcfb-b3cbcec31d61","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

### 2. GET http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61

```http
GET http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61 HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]


```

```http
HTTP/1.1 200
content-length: 369
content-type: application/json
x-request-id: 0d8a5ec0-7924-4b65-beb0-be94cc4e1893

{"task_id":"a60d33de-94f2-42d9-bcfb-b3cbcec31d61","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"1","name":"Created fixture task","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":["start","cancel"]}
```

### 3. POST http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61/commands

```http
POST http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61/commands HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]
idempotency-key: a8-lost-budget-start
content-length: 100
content-type: application/json

{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"first-use start"}
```

```http
HTTP/1.1 202
content-length: 246
content-type: application/json
x-request-id: a8c01486-566d-4ab1-bb08-a5e6eae5ab19

{"command_id":"a8-lost-budget-start","disposition":"accepted","resource_ref":{"entity_type":"task","id":"a60d33de-94f2-42d9-bcfb-b3cbcec31d61","revision":"1"},"resource_version":"1","request_id":"a8c01486-566d-4ab1-bb08-a5e6eae5ab19","code":null}
```

### 4. GET http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61/launch

```http
GET http://testserver/api/v2/tasks/a60d33de-94f2-42d9-bcfb-b3cbcec31d61/launch HTTP/1.1
host: testserver
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: python-httpx/0.28.1
authorization: [REDACTED TEST CREDENTIAL]


```

```http
HTTP/1.1 200
content-length: 491
content-type: application/json
x-request-id: 071c592b-4390-4dbc-9508-c5c055d89780

{"operation_id":"a8-lost-budget-start","command_id":"a8-lost-budget-start","task_id":"a60d33de-94f2-42d9-bcfb-b3cbcec31d61","definition_digest":"cf025177c31e7d53eb90d8e645bc3fa3968bcf6b56f44ed4eec6a21d5bd8fb78","profile_digest":"82361b6c3016e44df649fc731e8d334c1acef7c3937c6d311f02c1c44148f07b","runtime_attempt":"1","execution_epoch":"2","phase":"ready","phase_status":"succeeded","reason_code":null,"allowed_actions":["pause","cancel","finish"],"observed_at":"2026-09-19T10:10:57.304064Z"}
```
