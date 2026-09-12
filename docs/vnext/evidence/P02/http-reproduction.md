# P02 完整 HTTP 复现包

日期：2026-09-13。被测代码：`20f9199182d2b016428524997d5c688dbf4ab941`。

以下 Authorization 均为本次测试进程临时 RSA 私钥签发的合成 JWT，issuer 为 `https://identity.fixture.invalid`、audience 为 `wuji-vnext-tests`，不含用户或生产凭据。私钥从未落盘。原始逐交换 JSONL 位于各节列出的 `runtime/` 路径，报文未截断。

## 成果 HTTP-1：issuer-signed 身份到达真实 ASGI 组合路由

- test_name：`test_issuer_signed_identity_reaches_the_real_asgi_route`
- 风险点：若生产边界仅解码而不验签，伪造主体可进入后续业务路由。本例同时以 tampered/wrong issuer/wrong audience/expired 用例验证拒绝分支。
- 原始记录：[`runtime/247a8daa9b47/http-exchanges.jsonl`](runtime/247a8daa9b47/http-exchanges.jsonl)、[`runtime/247a8daa9b47/identity-events.jsonl`](runtime/247a8daa9b47/identity-events.jsonl)

### 请求

```http
POST http://testserver/api/v2/test/identity HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY4MTFlOWRmOTFiY2NmNGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhZ2VudC1maXh0dXJlIiwidGVuYW50X2lkIjoidGVuYW50LWZpeHR1cmUiLCJyb2xlcyI6WyJhZ2VudCJdLCJpYXQiOjE3ODkyNDIwNDQsIm5iZiI6MTc4OTI0MjA0MywiZXhwIjoxNzg5MjQyMzQ0LCJqdGkiOiJkODZjOGYwOC00YzdjLTQwMGUtYWI2Yy1lYmUwOGQyZWJiYmYifQ.QkbJeRtiHaYtb04JsdobX0yoYmdyObbxpmmVsas6oznqEmqwBYbMisCa7eD2UkGrKMM40_-wU_xNWqLeruzBqaFHviCQKDM593-hMLMvFS_tvExq8_d628YaotdMvd_09LpOT5B6eHEWCqw4CwnoQPeiohRWNylAuuQ4ckX6xY6RDrrLDtMSHSXe3MwANfmuZu9HlzAIXbJdSvU-amPmAaDEdH7A6N5sqK51230XH2D5QxKsVemccL6Tl4Es26sn0dGw011LRpDO8v2cKGGcwUajeWervB_JIK42N6aCDlfCHYLcBmPnapudyhv50rL3n5-JHcH2FsD9ifrcVQoIew
connection: keep-alive
content-length: 18
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1

{"probe":"signed"}
```

### 响应

```http
HTTP/1.1 200 OK
content-length: 103
content-type: application/json
x-request-id: 8ed85d87-2de7-4134-a514-31c1410eba60

{"subject":"agent-fixture","tenant_id":"tenant-fixture","roles":["agent"],"payload":{"probe":"signed"}}
```

## 成果 HTTP-2：非有限数字在路由分派前拒绝

- test_name：`test_asgi_boundary_rejects_unsafe_json_before_route_dispatch[{"coordinate":NaN}]`
- 风险点：Python 标准 JSON 解析默认接受 `NaN`；若进入模型或幂等摘要会形成非标准 wire 值。
- 原始记录：[`runtime/2023e889058e/http-exchanges.jsonl`](runtime/2023e889058e/http-exchanges.jsonl)、[`runtime/2023e889058e/identity-events.jsonl`](runtime/2023e889058e/identity-events.jsonl)

### 请求

```http
POST http://testserver/api/v2/test/identity HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjIyMmQ4Mzk3Y2YzMzk3NmUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhZ2VudC1maXh0dXJlIiwidGVuYW50X2lkIjoidGVuYW50LWZpeHR1cmUiLCJyb2xlcyI6WyJhZ2VudCJdLCJpYXQiOjE3ODkyNDIwNDUsIm5iZiI6MTc4OTI0MjA0NCwiZXhwIjoxNzg5MjQyMzQ1LCJqdGkiOiJjYmFhMDJiZi03NTI4LTQzZTItYmZjMi1kMDBlYWIzNWUyMTAifQ.pDn28DA4bjGFXJjnD5HC4UMCtWO2stsa5dq_G8rX34MhZgQP_cmSzizzhzQV8Fb5MlbRLf8VMom_2lJRhCZ7ht6Vmf1trT4kE5jJfWeeKthhxh2xep6cmu5XDDoEjGnuBKpSmgeOGv6r3F5BcOcCgmrw_J5i0NVB_8kXQ1MLcjoKpG_QntxP9dKctPfNyOsrITkn3uQXt5OrOw3LKh4ljIy0X255dONiNQ-36Nrt9WsqAadc4HDMLiuA8vWXAox2dMzJTSa-Zj0juCAU6uFgaDMFasQoGjTrPADhXPiLAD03PFAPvBK2Adrp9MUVp4wvu21of0w23BB17yj6OWNCHQ
connection: keep-alive
content-length: 18
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1

{"coordinate":NaN}
```

### 响应

```http
HTTP/1.1 422 Unprocessable Entity
content-length: 159
content-type: application/json
x-request-id: 659151b2-770b-4943-b4f1-e9a09903d836

{"code":"INVALID_SCHEMA","message":"Request body is not valid strict JSON.","request_id":"659151b2-770b-4943-b4f1-e9a09903d836","retryable":false,"details":{}}
```

## 成果 HTTP-3：合同错误不回显原始 input/ctx

- test_name：`test_asgi_model_validation_uses_the_versioned_error_envelope`
- 风险点：FastAPI/Pydantic 原始 error item 包含 `input` 与 `ctx`，可能把候选文本或异常对象复制到公共响应。当前边界仅发布 `type`、规范化 `loc` 和固定消息。
- 原始记录：[`runtime/bc8dbb66fe40/http-exchanges.jsonl`](runtime/bc8dbb66fe40/http-exchanges.jsonl)、[`runtime/bc8dbb66fe40/identity-events.jsonl`](runtime/bc8dbb66fe40/identity-events.jsonl)

### 请求

```http
POST http://testserver/api/v2/test/claim HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjNhY2FiMzY5MzU1ZDFkOGQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhZ2VudC1maXh0dXJlIiwidGVuYW50X2lkIjoidGVuYW50LWZpeHR1cmUiLCJyb2xlcyI6WyJhZ2VudCJdLCJpYXQiOjE3ODkyNDIwNDUsIm5iZiI6MTc4OTI0MjA0NCwiZXhwIjoxNzg5MjQyMzQ1LCJqdGkiOiJlMmI4ZjUzYS1kOWNlLTRiZmUtODgwNS0wMmM2MThlMTFhNTEifQ.Y6J1vO3JVOA0zsREGT0bQP8y2uwoCz_Baxdcpran_Qci6n7po6hPP6bjQcdXI3uFA6Y6nOWF8evL7fNucpXf2ZDrZCkhPiGGnRsP-aiNs63mk7nE20ihj3LbxxY3nvHmSaiMSCZb5CwKKURBsjl-J4dZG1uJU4Bxq-gP3Z_54kd3IIWj8IpwUkWunF_mOrdTaafsq0ZcCpV0I0Xq3CP2IoYZ8vVZ-B-C0WiMhc94gU4IppeK0-sTU01Uyxu0RbJ5wVHGG-vaMkiRjuCubXuc1T_CB1kon2nlVjyYM2vSFQOuDOLnEEmgqz3uC7exxzR6b0yFxUasLlnnAtoZiU1Nxw
connection: keep-alive
content-length: 175
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1

{"client_ref":"claim-1","kind":"SENSITIVE-INVALID-KIND","assertion_role":"candidate_fact","text":"SENSITIVE-CANDIDATE-CONTENT version 为 17","basis_refs":[],"limitations":[]}
```

### 响应

```http
HTTP/1.1 422 Unprocessable Entity
content-length: 261
content-type: application/json
x-request-id: 6345deb6-3994-48bf-8a12-ea2514412426

{"code":"INVALID_SCHEMA","message":"Request does not satisfy the v2 contract.","request_id":"6345deb6-3994-48bf-8a12-ea2514412426","retryable":false,"details":{"errors":[{"type":"enum","loc":["body","kind"],"msg":"Input does not satisfy the field contract."}]}}
```

响应中没有 `SENSITIVE-INVALID-KIND`、`SENSITIVE-CANDIDATE-CONTENT`、`input` 或 `ctx`。
