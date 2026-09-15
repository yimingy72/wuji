# P06 complete HTTP reproduction packets

P06 base: `f32678d5662965f44b32863e8ecdf306db676ffd`; fix: `67a8030e7c6a7c1cf767aa20a60fd6bfec5fe5e4`; migration: `vnext_0008_p06_admission_hardening`.
All bearer tokens and keys below are synthetic isolated test values. Packets are decoded verbatim from final JSONL captures and bodies are not truncated.

## test_current_run_model_gate_forwards_native_and_records_attempt

Contract point: Signed Run admission, native response, private Task key and durable receipt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImYzNWJlNzU0YmUzY2NjN2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjYsIm5iZiI6MTc4OTI2ODkyNSwiZXhwIjoxNzg5MjY5MjI2LCJqdGkiOiI2MzJjYTU2Mi00ZGNmLTRkZTctYTU3Ny00NjgyNjNkZWNlMjIifQ.f8rq6ZOsK2ark8m5JsOa6YJ51VoRnq3moe02M4nppCY21FeMwxrnUPVKBG2K3it_VBlWXD9S3MN_l4VTjxUkaNNo6iNysGsQLzkZ0SxHL-574ocES7H6lizC_Gkwcu7j8pU-FVw57beSkMpQOHPG8U8unQhATe0T6RyONRxdrLKFrKuzjJA9AEBjteqAVEZ0zPhxTOLfTQtcsOZoMKRVIRW1D6ISD4dasg2ZqwfX7WpYDwTND--_q93FDGt9jyumuNh0NkV8S2cg9VlJY0VrtSMaMZkCv_vaYIOu5J6efbK-zU2EdeN7l7ILEjQeCOH2SeSJHgdpK0wb4VbFWJ55GA
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-request-current-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 934d1b55-fada-4a4a-b21a-8034b87f8f87
x-wuji-model-attempt-id: c0f39ad5-35b6-4c37-9d05-e87df772ffaf
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/c0f39ad5-35b6-4c37-9d05-e87df772ffaf
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImYzNWJlNzU0YmUzY2NjN2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjYsIm5iZiI6MTc4OTI2ODkyNSwiZXhwIjoxNzg5MjY5MjI2LCJqdGkiOiI2MzJjYTU2Mi00ZGNmLTRkZTctYTU3Ny00NjgyNjNkZWNlMjIifQ.f8rq6ZOsK2ark8m5JsOa6YJ51VoRnq3moe02M4nppCY21FeMwxrnUPVKBG2K3it_VBlWXD9S3MN_l4VTjxUkaNNo6iNysGsQLzkZ0SxHL-574ocES7H6lizC_Gkwcu7j8pU-FVw57beSkMpQOHPG8U8unQhATe0T6RyONRxdrLKFrKuzjJA9AEBjteqAVEZ0zPhxTOLfTQtcsOZoMKRVIRW1D6ISD4dasg2ZqwfX7WpYDwTND--_q93FDGt9jyumuNh0NkV8S2cg9VlJY0VrtSMaMZkCv_vaYIOu5J6efbK-zU2EdeN7l7ILEjQeCOH2SeSJHgdpK0wb4VbFWJ55GA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 544
content-type: application/json
x-request-id: 41a228f4-87f8-4a29-80f7-bc7c19828c82

{"model_attempt_id":"c0f39ad5-35b6-4c37-9d05-e87df772ffaf","input_digest":"57d0d5d1f73d05a69fef3b3d9d68088f4408bde81680c5a37b2008cba4c46149","logical_request_id":"model-request-current-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"complete","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":true,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"377","retained_bytes":"377","forwarded_bytes":"377","output_bytes":"377"}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:64941/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64941
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: c0f39ad5-35b6-4c37-9d05-e87df772ffaf

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_revoked_run_cannot_request_model

Contract point: Credential revocation rejects before key resolution, upstream call or attempt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlkMjdlYTc4YWZmMzk4NDgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjcsIm5iZiI6MTc4OTI2ODkyNiwiZXhwIjoxNzg5MjY5MjI3LCJqdGkiOiI3OTU5MjZkYS1mMzkxLTQ3YWUtYWQ0Mi1iYTc2NzY2ZDdjZTIifQ.PFTUEwIgJBYyoHZ4yiB-fcIELJro0iUy76ECcy6p0HI6au7e4shIFZ-kBsoCGs5U1bLuCNQgCd5z5f5sWBznof5bpUppokJwo2HZmuJEsOYXHFAnWTh_280NUmQuQcD0zhcXAUsj4uZStlOYVM5xvZkRMHTEJ-dcoVwJJdZeA-yAJz-Qc8vlel2ZmwW8Dml-IYvtsoRKSndPHm-TFEdcdj-rysEb9Ydfvma1AmnOmdy3jheNGXLJyfU5frmIubHXzSU6LuhZIcjcgTBkLM1cGy4HavSsQ6X6qZx7dJP3NrwYf7mUiul6ja_FQ2JaEctazhtm-WibnLJHvekjZ4Hhmw
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-request-revoked-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 157
content-type: application/json
x-request-id: 18f360f8-ae9e-4a56-a72f-b1578fadf27f

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"18f360f8-ae9e-4a56-a72f-b1578fadf27f","retryable":false,"details":{}}
```

## test_p05_pause_makes_bound_run_identity_stale

Contract point: P05 pause invalidates an otherwise valid Run binding.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImRmZWIwOTQ0ZTJlNTg1OGEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjgsIm5iZiI6MTc4OTI2ODkyNywiZXhwIjoxNzg5MjY5MjI4LCJqdGkiOiJjMTM1NTczZS1iM2Y3LTRlNmQtOWRlZi0yMTc2MzZkZDU2OTgifQ.IUjO88JgsN3u3FO7JilzeFTnN5gfJplycV1kQBLoItoNfkyTGFopoEmagWHGaRm865M_jpN1xK7uRzxL0UVnVPTnZ2DlVNN8agvnRQgA9foYiUd7xy3-Ldv7sFrOKZqYqFcKr1-pLzm4BjhXu0Jfv9XfDhlQcbtnGfzNH92vCyCPVP1arsTUEvfVpEwlDPiTYRfhT4O_dTs4BPPwP9J4JKvZn4L8pUznCfcN3qKsK3Q93Ice366VTQU5nKHjAwUBw22-CYiegg-WVTV6erQCFzkaYKa4sn1cPtNpiI6Lr8pR_oXsBgdTZEHyIt66B3J_ZPCDLAjUzk-s6C03XCLfvg
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-request-paused-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 157
content-type: application/json
x-request-id: 024b7ae3-fd4f-4a02-b8df-23b09fe04bb6

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"024b7ae3-fd4f-4a02-b8df-23b09fe04bb6","retryable":false,"details":{}}
```

## test_model_request_replay_conflict_and_new_id_have_distinct_attempts

Contract point: Same request ID replays, changed digest conflicts, new ID creates a new inference.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlmYmNlZmZhNGZlYjg0ZjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjksIm5iZiI6MTc4OTI2ODkyOCwiZXhwIjoxNzg5MjY5MjI5LCJqdGkiOiI5YzNlYTU5Ny03Nzk5LTQ4NzMtYjA1Ni01OGQwM2QxNDY0YWQifQ.bzNlpqKXsfkmbCA0CB6_Y1kGfkimX1QOtTxDQfb0X0s_vQffI-VF1ZlskO-izqYd-HgkBsxT93YCZhVuj5YJ1CsNlnjLAk7IShrIb-Rjx6QyRbVIaxgSu_SCKt4q2OS_An5muXgiq4h2k_zd7jM0wC474tijxpFLuAFQVoMlC9F6_L3jTAjc4nSs_y3X5COfSc1ZSBCiKHradWNSJD-dn4MIRDJa-mUePLaKKxnclTsboXA02FSwq8siZzz_GakmeRpXqNt_dRPF5B5GAk8vYip9x0Ls4QNX0Ot4YY2Sy6b6on43HzgEHsOEHy9uOyXnfCBt3ZxDkIq4QVsXf4-wuQ
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-logical-replay-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 9b78be0d-d093-4048-9408-1d78a6401bd6
x-wuji-model-attempt-id: ca447961-8ecd-4ddc-88fc-24150935264d
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlmYmNlZmZhNGZlYjg0ZjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjksIm5iZiI6MTc4OTI2ODkyOCwiZXhwIjoxNzg5MjY5MjI5LCJqdGkiOiI5YzNlYTU5Ny03Nzk5LTQ4NzMtYjA1Ni01OGQwM2QxNDY0YWQifQ.bzNlpqKXsfkmbCA0CB6_Y1kGfkimX1QOtTxDQfb0X0s_vQffI-VF1ZlskO-izqYd-HgkBsxT93YCZhVuj5YJ1CsNlnjLAk7IShrIb-Rjx6QyRbVIaxgSu_SCKt4q2OS_An5muXgiq4h2k_zd7jM0wC474tijxpFLuAFQVoMlC9F6_L3jTAjc4nSs_y3X5COfSc1ZSBCiKHradWNSJD-dn4MIRDJa-mUePLaKKxnclTsboXA02FSwq8siZzz_GakmeRpXqNt_dRPF5B5GAk8vYip9x0Ls4QNX0Ot4YY2Sy6b6on43HzgEHsOEHy9uOyXnfCBt3ZxDkIq4QVsXf4-wuQ
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-logical-replay-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: de211a42-3d86-4e69-ac3f-1db7284818bd
x-wuji-model-attempt-id: ca447961-8ecd-4ddc-88fc-24150935264d
x-wuji-replayed: true

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlmYmNlZmZhNGZlYjg0ZjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjksIm5iZiI6MTc4OTI2ODkyOCwiZXhwIjoxNzg5MjY5MjI5LCJqdGkiOiI5YzNlYTU5Ny03Nzk5LTQ4NzMtYjA1Ni01OGQwM2QxNDY0YWQifQ.bzNlpqKXsfkmbCA0CB6_Y1kGfkimX1QOtTxDQfb0X0s_vQffI-VF1ZlskO-izqYd-HgkBsxT93YCZhVuj5YJ1CsNlnjLAk7IShrIb-Rjx6QyRbVIaxgSu_SCKt4q2OS_An5muXgiq4h2k_zd7jM0wC474tijxpFLuAFQVoMlC9F6_L3jTAjc4nSs_y3X5COfSc1ZSBCiKHradWNSJD-dn4MIRDJa-mUePLaKKxnclTsboXA02FSwq8siZzz_GakmeRpXqNt_dRPF5B5GAk8vYip9x0Ls4QNX0Ot4YY2Sy6b6on43HzgEHsOEHy9uOyXnfCBt3ZxDkIq4QVsXf4-wuQ
connection: keep-alive
content-length: 206
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-logical-replay-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"A changed logical request.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 163
content-type: application/json
x-request-id: 892541f2-6426-4c28-ad21-eb21f903a934

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"892541f2-6426-4c28-ad21-eb21f903a934","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlmYmNlZmZhNGZlYjg0ZjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MjksIm5iZiI6MTc4OTI2ODkyOCwiZXhwIjoxNzg5MjY5MjI5LCJqdGkiOiI5YzNlYTU5Ny03Nzk5LTQ4NzMtYjA1Ni01OGQwM2QxNDY0YWQifQ.bzNlpqKXsfkmbCA0CB6_Y1kGfkimX1QOtTxDQfb0X0s_vQffI-VF1ZlskO-izqYd-HgkBsxT93YCZhVuj5YJ1CsNlnjLAk7IShrIb-Rjx6QyRbVIaxgSu_SCKt4q2OS_An5muXgiq4h2k_zd7jM0wC474tijxpFLuAFQVoMlC9F6_L3jTAjc4nSs_y3X5COfSc1ZSBCiKHradWNSJD-dn4MIRDJa-mUePLaKKxnclTsboXA02FSwq8siZzz_GakmeRpXqNt_dRPF5B5GAk8vYip9x0Ls4QNX0Ot4YY2Sy6b6on43HzgEHsOEHy9uOyXnfCBt3ZxDkIq4QVsXf4-wuQ
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-logical-replay-2

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: afed5c85-e776-4f68-b219-6e6bc0081b8a
x-wuji-model-attempt-id: 6bbef897-bf90-43bb-abd5-0ca25dfbc1c8
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:64950/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64950
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: ca447961-8ecd-4ddc-88fc-24150935264d

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 2

Request:

```http
POST http://127.0.0.1:64950/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64950
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 6bbef897-bf90-43bb-abd5-0ca25dfbc1c8

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_two_runs_cannot_both_take_the_last_task_model_request

Contract point: Two Runs race the final Task model quota; one reaches the upstream.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImM5OTJhNmJlNDdiYzVlMGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsid29ya2VyIl0sImlhdCI6MTc4OTI2ODkzMSwibmJmIjoxNzg5MjY4OTMwLCJleHAiOjE3ODkyNjkyMzEsImp0aSI6ImI2OTQxYzZjLWNiMzYtNGZlZC1hNWE0LWY2YjlkYWVmOTM5OSJ9.TP_4VxlYrqNHh-c_vFnR6-0cRizs8zfNkC43D2xoSOzvU4b7ps76OL0Kw1mv9MJ3EO6-XTliGCJylJTlMOItwY4ktnq5Lxu1DqhsR2z0bCtEhMXdlmBQZTW1-MdgTc1DZTmOVw1opwYPuBKIUSmFblyXC-kbv0CTSLN69TusJQa1eZqzmTdMA4s_cFw2aOaqYSkQB3BYjHFLyveI7gujBWzd2U0F8yaavXnkir5lGAV0ufAlIX5bl_NK67CziE4XiDFvu5kCpfFMIOZyZ4Hky2g-kk3LTzAUGQfU00OgqmoJN2M2wZ84RC1ZA59pXIFGjvCh8h5buu4KOXgnISMgEg
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-final-slot-b

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 429 Too Many Requests
content-length: 155
content-type: application/json
x-request-id: 47364c0a-e3e4-4a89-ba1a-2b8893c3005a

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"47364c0a-e3e4-4a89-ba1a-2b8893c3005a","retryable":false,"details":{}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImM5OTJhNmJlNDdiYzVlMGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzEsIm5iZiI6MTc4OTI2ODkzMCwiZXhwIjoxNzg5MjY5MjMxLCJqdGkiOiJlNWQyMzQzOS0zY2I5LTQyN2QtYWI5ZC1mZGZkOTY4NTJjNTkifQ.VZp94usEweGrphTyCmzuaoPHEygNMbigTd6ag5zHsNBFClckHwp07a3U_z3MuB2AVtfbiLOdOLoFL0yx_gTEt8cKiT98Os-y9b5WEQJmXFv9oWIJfK2_Lz1-QR1DthyyqKHE4d7BEaz6T4u5s7J2go2RAGbQoLsPYHSOg4h-kyUcqHD74Qc6YCH9ShSZgS99lxHf-y1uMG1X8CzD5-fLx9BQ5LxDm0TYism8wHnbHlfiTnpSeUgkQzyI5w2Vh7fhEzsve-x9CmCUm63m2pB-BIh-nT3SCHbppnup4tvqgyRDeTbdK_vs7qk3q1r3EUNsH7sTuUQ4xw4DyCmeAp3QRQ
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-final-slot-a

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 5b63e6c2-fb7f-4c6e-ae53-01fb8b2afbec
x-wuji-model-attempt-id: 8201cde7-3243-4bb4-a7bd-f8431c001793
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:64953/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64953
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 8201cde7-3243-4bb4-a7bd-f8431c001793

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_partial_stream_releases_local_inflight_without_settling_billing

Contract point: Missing [DONE] remains partial and releases only a proven-ended local slot.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQyNGMzOTMyN2M2YjViNWEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzIsIm5iZiI6MTc4OTI2ODkzMSwiZXhwIjoxNzg5MjY5MjMyLCJqdGkiOiIwNTY1OWI5OS05NjQwLTQ3YzAtYTJkZC1jYzdjZWY0ZWVhNzkifQ.tRzOIrYKUoLzxWpFuMJmPtmHm-K7zbvISSGzuRVuluOLSIgjMMKBCwnvZlB_8qIKifUDN7lbkaoeR3eDjymZM8yE7zdPx8laWrqUoEjrlGkJ9rb6WeXHNdZB4MFGQmEf6GDLzcFTQ23t6SZHbfmwj-OhJ_4g6Ql2da2Xacpuhi9exFDs6rZ1iVBWgX9g0MPddYvHreBnQZOUtcWcmfNQVxpVntqQkwNnfqrUgr2WMEUeZg0ySX7PAjF72AQIUlPQ9sOFPhDni2mE1GzW9yVQAjhjIl2Y05V52Vt9BxgEt4REhwJ0lZhO5khHJgpPuLNQI9AbyPtXco5Ag57ryghUpQ
connection: keep-alive
content-length: 204
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-partial-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":true,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-type: text/event-stream; charset=utf-8
x-request-id: 638e79b9-6ef2-48b2-93c8-fbb91a56551b
x-wuji-model-attempt-id: 08059077-19d4-4c5c-a123-7d60288642d7
x-wuji-replayed: false

data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk","created":1,"model":"fixture-model","choices":[{"index":0,"delta":{"role":"assistant","content":"partial"},"finish_reason":null}]}


```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/08059077-19d4-4c5c-a123-7d60288642d7
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQyNGMzOTMyN2M2YjViNWEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzIsIm5iZiI6MTc4OTI2ODkzMSwiZXhwIjoxNzg5MjY5MjMyLCJqdGkiOiIwNTY1OWI5OS05NjQwLTQ3YzAtYTJkZC1jYzdjZWY0ZWVhNzkifQ.tRzOIrYKUoLzxWpFuMJmPtmHm-K7zbvISSGzuRVuluOLSIgjMMKBCwnvZlB_8qIKifUDN7lbkaoeR3eDjymZM8yE7zdPx8laWrqUoEjrlGkJ9rb6WeXHNdZB4MFGQmEf6GDLzcFTQ23t6SZHbfmwj-OhJ_4g6Ql2da2Xacpuhi9exFDs6rZ1iVBWgX9g0MPddYvHreBnQZOUtcWcmfNQVxpVntqQkwNnfqrUgr2WMEUeZg0ySX7PAjF72AQIUlPQ9sOFPhDni2mE1GzW9yVQAjhjIl2Y05V52Vt9BxgEt4REhwJ0lZhO5khHJgpPuLNQI9AbyPtXco5Ag57ryghUpQ
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 536
content-type: application/json
x-request-id: b9cb88b4-5592-47d8-bfb5-aedce3e89929

{"model_attempt_id":"08059077-19d4-4c5c-a123-7d60288642d7","input_digest":"cc712b587519e826c7e1e943cc65088a98dc0d8cd3d981eda39c2aa8c5a620ad","logical_request_id":"model-partial-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"partial","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":false,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"200","retained_bytes":"200","forwarded_bytes":"200","output_bytes":"200"}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQyNGMzOTMyN2M2YjViNWEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzIsIm5iZiI6MTc4OTI2ODkzMSwiZXhwIjoxNzg5MjY5MjMyLCJqdGkiOiIwNTY1OWI5OS05NjQwLTQ3YzAtYTJkZC1jYzdjZWY0ZWVhNzkifQ.tRzOIrYKUoLzxWpFuMJmPtmHm-K7zbvISSGzuRVuluOLSIgjMMKBCwnvZlB_8qIKifUDN7lbkaoeR3eDjymZM8yE7zdPx8laWrqUoEjrlGkJ9rb6WeXHNdZB4MFGQmEf6GDLzcFTQ23t6SZHbfmwj-OhJ_4g6Ql2da2Xacpuhi9exFDs6rZ1iVBWgX9g0MPddYvHreBnQZOUtcWcmfNQVxpVntqQkwNnfqrUgr2WMEUeZg0ySX7PAjF72AQIUlPQ9sOFPhDni2mE1GzW9yVQAjhjIl2Y05V52Vt9BxgEt4REhwJ0lZhO5khHJgpPuLNQI9AbyPtXco5Ag57ryghUpQ
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-after-partial-2

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 92eb18c1-d065-42b0-8ba4-754540b4a672
x-wuji-model-attempt-id: 49b16c97-b343-479f-8639-9ad74ef86039
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:64964/v1/chat/completions
accept: text/event-stream
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 213
content-type: application/json
host: 127.0.0.1:64964
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 08059077-19d4-4c5c-a123-7d60288642d7

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":true,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
connection: close
content-type: text/event-stream

data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk","created":1,"model":"fixture-model","choices":[{"index":0,"delta":{"role":"assistant","content":"partial"},"finish_reason":null}]}


```

### Outbound localhost model exchange 2

Request:

```http
POST http://127.0.0.1:64964/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64964
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 49b16c97-b343-479f-8639-9ad74ef86039

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_workspace_read_returns_only_after_persisting_evidence

Contract point: Production workspace_read persists receiver receipt, Artifact and EvidenceReceipt before return.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQwNGUxZWExZTcxMGM5OTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzQsIm5iZiI6MTc4OTI2ODkzMywiZXhwIjoxNzg5MjY5MjM0LCJqdGkiOiI3OTA5MDA5OC05NDljLTRjNjctYWNkYi0xN2Q0NjU4NmUwMGIifQ.JoVHVKbOuGvZyMQ5Whqyxtp23BqDvuCii6zFtI4KILghGUAnaTy_21Ez9NqPdmJ4WGDHwjqds4298YbraGqBcV-NUV3SRThtFcNNBuqHXpTs92hz86Q2_MW8HQSoEJ9MjlFxdVRSsWZGyZ_2gB-OepYEgZ7fGH6h8akS0SSXfsSmD-nrjABAXEp6omh4pNENzNZGDRHHn1OjIAR4pOJo4tcbqG-t4OEgObqO0ELMkjKsP3lmiAfl_pJzywGbu4d43MQlXY_qNPy7y8-Y61BsSC6_VPjiSH2izBtac6YqtjwFGaYkqdomYXaABZlQbr0IvZ-LNQ29ofv54B_KsxREaw
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-workspace-read-1

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 540e431c-484c-423c-8990-9b5f5515fbe8

{"tool_call_id":"e7ec3849-d99e-4910-abc9-3ed34943b4af","operation_id":"e7ec3849-d99e-4910-abc9-3ed34943b4af","tool_attempt_id":"a2cbf87f-7028-4d43-8bda-ec9fe02e0a93","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"eda462e9-9180-4077-9ca6-010c9571fdd1","revision":"1"},"capture_id":"a2cbf87f-7028-4d43-8bda-ec9fe02e0a93","status":"accepted","artifact_refs":[{"id":"dd726b41-baae-4d3e-bdda-67fea323ee9b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"dd726b41-baae-4d3e-bdda-67fea323ee9b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/dd726b41-baae-4d3e-bdda-67fea323ee9b/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQwNGUxZWExZTcxMGM5OTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzQsIm5iZiI6MTc4OTI2ODkzMywiZXhwIjoxNzg5MjY5MjM0LCJqdGkiOiI3OTA5MDA5OC05NDljLTRjNjctYWNkYi0xN2Q0NjU4NmUwMGIifQ.JoVHVKbOuGvZyMQ5Whqyxtp23BqDvuCii6zFtI4KILghGUAnaTy_21Ez9NqPdmJ4WGDHwjqds4298YbraGqBcV-NUV3SRThtFcNNBuqHXpTs92hz86Q2_MW8HQSoEJ9MjlFxdVRSsWZGyZ_2gB-OepYEgZ7fGH6h8akS0SSXfsSmD-nrjABAXEp6omh4pNENzNZGDRHHn1OjIAR4pOJo4tcbqG-t4OEgObqO0ELMkjKsP3lmiAfl_pJzywGbu4d43MQlXY_qNPy7y8-Y61BsSC6_VPjiSH2izBtac6YqtjwFGaYkqdomYXaABZlQbr0IvZ-LNQ29ofv54B_KsxREaw
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-disposition: attachment
content-security-policy: default-src 'none'
content-type: application/octet-stream
digest: sha-256=5YJ+XthPxVa82R4ae1MokyTBHR+YbLV1YHSqeWLSMHY=
x-content-type-options: nosniff
x-request-id: 1519d899-fa6e-4bf5-8f4d-3a49a577a6a3

fixture-version=17

```

### Inbound ASGI exchange 3

Request:

```http
GET http://testserver/internal/v2/tool-calls/e7ec3849-d99e-4910-abc9-3ed34943b4af
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQwNGUxZWExZTcxMGM5OTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzQsIm5iZiI6MTc4OTI2ODkzMywiZXhwIjoxNzg5MjY5MjM0LCJqdGkiOiI3OTA5MDA5OC05NDljLTRjNjctYWNkYi0xN2Q0NjU4NmUwMGIifQ.JoVHVKbOuGvZyMQ5Whqyxtp23BqDvuCii6zFtI4KILghGUAnaTy_21Ez9NqPdmJ4WGDHwjqds4298YbraGqBcV-NUV3SRThtFcNNBuqHXpTs92hz86Q2_MW8HQSoEJ9MjlFxdVRSsWZGyZ_2gB-OepYEgZ7fGH6h8akS0SSXfsSmD-nrjABAXEp6omh4pNENzNZGDRHHn1OjIAR4pOJo4tcbqG-t4OEgObqO0ELMkjKsP3lmiAfl_pJzywGbu4d43MQlXY_qNPy7y8-Y61BsSC6_VPjiSH2izBtac6YqtjwFGaYkqdomYXaABZlQbr0IvZ-LNQ29ofv54B_KsxREaw
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 5e4d2173-aff0-45f0-935b-383629663b2c

{"tool_call_id":"e7ec3849-d99e-4910-abc9-3ed34943b4af","operation_id":"e7ec3849-d99e-4910-abc9-3ed34943b4af","tool_attempt_id":"a2cbf87f-7028-4d43-8bda-ec9fe02e0a93","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"eda462e9-9180-4077-9ca6-010c9571fdd1","revision":"1"},"capture_id":"a2cbf87f-7028-4d43-8bda-ec9fe02e0a93","status":"accepted","artifact_refs":[{"id":"dd726b41-baae-4d3e-bdda-67fea323ee9b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"dd726b41-baae-4d3e-bdda-67fea323ee9b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_revoked_run_cannot_dispatch_workspace_tool

Contract point: Revoked Run creates no ToolAttempt or receiver execution.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjM4MjFmNTY4YzhmMjljZjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzUsIm5iZiI6MTc4OTI2ODkzNCwiZXhwIjoxNzg5MjY5MjM1LCJqdGkiOiI1MTM5OTA0OC05ZmI1LTRlNWUtOTc1Ny00ZDZhOTgwNDBjMmEifQ.E_uzMjF3RRpDZ0Yl4d9zhlNyXkMLPd6SzHr1U5JQiXcA8rRakuJTPP9hXIX0HqXSQ6QgO-D_4cYDAt-QidJr1WLcSGdvVibNAQ9qKCARUJp56Lj23b-hxbW5Gve20LClQWdFqZysDMlrhDbH08u4ryn7sBdpGVInxcT88TAp3cx9BDM8we19jb99Chhxl9NXFOA0xalbw7eixgYNOUguK7g4HKjffPjWDM_-q5IYlnrYo9tMpnvtn6uwbuig32BAAPKO8O8RgaddiEYafZWFNy-1R9GqRryqp5h_dn7rezAOpJmDij_3fJr5N4lU5by8cxfmRT_fzssFNY8hU8VxCA
connection: keep-alive
content-length: 259
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-workspace-revoked-1

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-revoked","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 157
content-type: application/json
x-request-id: 1058030e-fc97-4aff-b88d-0ce1097b0630

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"1058030e-fc97-4aff-b88d-0ce1097b0630","retryable":false,"details":{}}
```

## test_task_output_limit_is_cumulative_across_model_attempts

Contract point: Task output allowance remains cumulative across model attempts.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZhMDUyZGI2YzNhOTVkMDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzYsIm5iZiI6MTc4OTI2ODkzNSwiZXhwIjoxNzg5MjY5MjM2LCJqdGkiOiJlYWYwOTkzNC0zNWIwLTRmMTAtYWQ3Ni00ZGRlNDRiZjZkMGUifQ.gTt3aOQyeR3FZGUlzwrUYRFfA07dlOXSlMiyDeRLrISY8rz7EdjHOLdzeL20LZtYPDB5g97qy2EFAyNXCiktXLCC_4BwA5HvkNiL5KylGQPv5UMuFXMAUnOBPCqCqQiswD9dX-mlp7eFlY3D3EHY9FFiscY5KbJy8qMVIHgVvAU8L2SqLPAZ3IaH-YL01TjbH7mk7jOX67YyJuhq8PbfaGQ6C3IwICdzV6q4tc5K8svKsWBojhVxNjcgrfKk671AMDlW9YA42ftJIRDQ3D99RCDk9M9Gmoj10rMFMTAp9CNTL9E7Dvk_ACN6YhFQsmSdfZirR0TOLpRjMqX2lt_R3Q
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-output-budget-1

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: d7b72700-5452-4a4d-92e7-d6135d8067bc
x-wuji-model-attempt-id: eb2ab2bd-b3ca-45e0-8ecb-163fba5fb321
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZhMDUyZGI2YzNhOTVkMDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzYsIm5iZiI6MTc4OTI2ODkzNSwiZXhwIjoxNzg5MjY5MjM2LCJqdGkiOiJlYWYwOTkzNC0zNWIwLTRmMTAtYWQ3Ni00ZGRlNDRiZjZkMGUifQ.gTt3aOQyeR3FZGUlzwrUYRFfA07dlOXSlMiyDeRLrISY8rz7EdjHOLdzeL20LZtYPDB5g97qy2EFAyNXCiktXLCC_4BwA5HvkNiL5KylGQPv5UMuFXMAUnOBPCqCqQiswD9dX-mlp7eFlY3D3EHY9FFiscY5KbJy8qMVIHgVvAU8L2SqLPAZ3IaH-YL01TjbH7mk7jOX67YyJuhq8PbfaGQ6C3IwICdzV6q4tc5K8svKsWBojhVxNjcgrfKk671AMDlW9YA42ftJIRDQ3D99RCDk9M9Gmoj10rMFMTAp9CNTL9E7Dvk_ACN6YhFQsmSdfZirR0TOLpRjMqX2lt_R3Q
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-output-budget-2

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 429 Too Many Requests
content-length: 155
content-type: application/json
x-request-id: dd10e5c2-3a8e-4331-9c77-094aeed46114

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"dd10e5c2-3a8e-4331-9c77-094aeed46114","retryable":false,"details":{}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:64975/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64975
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: eb2ab2bd-b3ca-45e0-8ecb-163fba5fb321

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 2

Request:

```http
POST http://127.0.0.1:64975/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:64975
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: acaf36a0-f72b-42bf-9262-d830c54ec340

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_approval_required_tool_does_not_create_an_execution_attempt

Contract point: Unbound approval stays pending with no ToolAttempt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRjM2NmZjU3NWNiOTg5ZTMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzcsIm5iZiI6MTc4OTI2ODkzNiwiZXhwIjoxNzg5MjY5MjM3LCJqdGkiOiI1NDgwMjFmMS00YzZjLTQyY2MtOGY4NC1mMGZmNjEzYWNlNDQifQ.Mwu9d9bBw40B3k0glNNqPniI4An1ZVC0KdnKtN7MgVsGjFHGFYsKRvoLbnp8BuWXnRgncziac3iQgdvflhVAtqIp1Gs6zCXu_yD-R13rhK4nRP0c1zUVRCGNHW-yzJaHrPaaT0XZDwY_4D2CzlwbQr6zsD5LJxLeiye3uPnnYM0TYz9LdltRcpDMav8S1gnMAqA_JwuhmiUr8OumsQWaQYWsIr9-SSBGq3Edevz4oLExeefbcpNI2_0A-dxodpQYHNgQzmVIY4G_0sio51X2irhgkwkRocNWbCXcvXckS3YXauXWNDiQku07DaT8-BNyZn-XdTrwqHUtoqEGinNoPA
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-awaiting-approval-1

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 221
content-type: application/json
x-request-id: 436a87ba-c54a-4c6a-ae60-460948476e97

{"tool_call_id":"72b2e41c-f5be-42d8-87bf-f9b2798c20fd","operation_id":"72b2e41c-f5be-42d8-87bf-f9b2798c20fd","tool_attempt_id":null,"status":"pending_approval","evidence_receipt":null,"result_ref":null,"reason_code":null}
```

## test_tool_operation_replay_conflict_and_new_call_id_control_execution

Contract point: Canonical ToolCall replay/conflict/new provider call identity.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRlYjNjNzJkZDAzMjg5OGYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzksIm5iZiI6MTc4OTI2ODkzOCwiZXhwIjoxNzg5MjY5MjM5LCJqdGkiOiI0NTQyM2U4ZS1kY2FmLTQ1YWYtYTFjMS0wZjdmNDJiYmYxMTYifQ.aPM2v80soSgLzpM0lO7dovkWVGD9PYjMDVFEsztKrvmC4PfWM2P7rtMLErsAW7y78TtEm7wczWmEukxMIyzPp3twJ_d7ngBXgiZE9JRCzXoHxkj4JylI1rXpitGzF4NZttegt8th1g5gfEdDvt3gyYyOSvHTPzzWnXTztmLql9k3C05LnCRM9tmjpypaDPfAJH1rlFSBwXOz2EX1NHzZ8FJvbTMPJDmXqcVPKPuu7XSpQDhKZlj8tO6DOkSYauQoCQnAEUUI5po87sx048pv_LAkTBKloq4Pv57yYdbLHqvJZOmTspcOFg7AvwqWJwna2lMSycFhZGfG_BfcpVOsGA
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-operation-first

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: d6cc0b5c-9d8f-4eee-8cf1-45b671981d31

{"tool_call_id":"04d02691-385d-41eb-be41-5ca682f3a2ab","operation_id":"04d02691-385d-41eb-be41-5ca682f3a2ab","tool_attempt_id":"b3d9e1a1-529f-4d1a-9e9b-63487b4f4a26","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"1af20692-c777-4e5b-98f0-7bb5ea8c47dc","revision":"1"},"capture_id":"b3d9e1a1-529f-4d1a-9e9b-63487b4f4a26","status":"accepted","artifact_refs":[{"id":"c4509c39-5787-4390-a9b5-0a4cf6283e11","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"c4509c39-5787-4390-a9b5-0a4cf6283e11","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRlYjNjNzJkZDAzMjg5OGYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzksIm5iZiI6MTc4OTI2ODkzOCwiZXhwIjoxNzg5MjY5MjM5LCJqdGkiOiI0NTQyM2U4ZS1kY2FmLTQ1YWYtYTFjMS0wZjdmNDJiYmYxMTYifQ.aPM2v80soSgLzpM0lO7dovkWVGD9PYjMDVFEsztKrvmC4PfWM2P7rtMLErsAW7y78TtEm7wczWmEukxMIyzPp3twJ_d7ngBXgiZE9JRCzXoHxkj4JylI1rXpitGzF4NZttegt8th1g5gfEdDvt3gyYyOSvHTPzzWnXTztmLql9k3C05LnCRM9tmjpypaDPfAJH1rlFSBwXOz2EX1NHzZ8FJvbTMPJDmXqcVPKPuu7XSpQDhKZlj8tO6DOkSYauQoCQnAEUUI5po87sx048pv_LAkTBKloq4Pv57yYdbLHqvJZOmTspcOFg7AvwqWJwna2lMSycFhZGfG_BfcpVOsGA
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-operation-replay

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: d0158127-b5ea-4d97-bc51-1e0a683645ff

{"tool_call_id":"04d02691-385d-41eb-be41-5ca682f3a2ab","operation_id":"04d02691-385d-41eb-be41-5ca682f3a2ab","tool_attempt_id":"b3d9e1a1-529f-4d1a-9e9b-63487b4f4a26","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"1af20692-c777-4e5b-98f0-7bb5ea8c47dc","revision":"1"},"capture_id":"b3d9e1a1-529f-4d1a-9e9b-63487b4f4a26","status":"accepted","artifact_refs":[{"id":"c4509c39-5787-4390-a9b5-0a4cf6283e11","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"c4509c39-5787-4390-a9b5-0a4cf6283e11","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRlYjNjNzJkZDAzMjg5OGYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzksIm5iZiI6MTc4OTI2ODkzOCwiZXhwIjoxNzg5MjY5MjM5LCJqdGkiOiI0NTQyM2U4ZS1kY2FmLTQ1YWYtYTFjMS0wZjdmNDJiYmYxMTYifQ.aPM2v80soSgLzpM0lO7dovkWVGD9PYjMDVFEsztKrvmC4PfWM2P7rtMLErsAW7y78TtEm7wczWmEukxMIyzPp3twJ_d7ngBXgiZE9JRCzXoHxkj4JylI1rXpitGzF4NZttegt8th1g5gfEdDvt3gyYyOSvHTPzzWnXTztmLql9k3C05LnCRM9tmjpypaDPfAJH1rlFSBwXOz2EX1NHzZ8FJvbTMPJDmXqcVPKPuu7XSpQDhKZlj8tO6DOkSYauQoCQnAEUUI5po87sx048pv_LAkTBKloq4Pv57yYdbLHqvJZOmTspcOFg7AvwqWJwna2lMSycFhZGfG_BfcpVOsGA
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-operation-conflict

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"missing.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 163
content-type: application/json
x-request-id: cb11538e-764a-4920-9d78-236975a5b0b1

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"cb11538e-764a-4920-9d78-236975a5b0b1","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRlYjNjNzJkZDAzMjg5OGYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5MzksIm5iZiI6MTc4OTI2ODkzOCwiZXhwIjoxNzg5MjY5MjM5LCJqdGkiOiI0NTQyM2U4ZS1kY2FmLTQ1YWYtYTFjMS0wZjdmNDJiYmYxMTYifQ.aPM2v80soSgLzpM0lO7dovkWVGD9PYjMDVFEsztKrvmC4PfWM2P7rtMLErsAW7y78TtEm7wczWmEukxMIyzPp3twJ_d7ngBXgiZE9JRCzXoHxkj4JylI1rXpitGzF4NZttegt8th1g5gfEdDvt3gyYyOSvHTPzzWnXTztmLql9k3C05LnCRM9tmjpypaDPfAJH1rlFSBwXOz2EX1NHzZ8FJvbTMPJDmXqcVPKPuu7XSpQDhKZlj8tO6DOkSYauQoCQnAEUUI5po87sx048pv_LAkTBKloq4Pv57yYdbLHqvJZOmTspcOFg7AvwqWJwna2lMSycFhZGfG_BfcpVOsGA
connection: keep-alive
content-length: 260
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-operation-new-call

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read-new","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 299796eb-51e9-49db-8d95-995fb5de7e5d

{"tool_call_id":"39a285dc-b128-46b0-94b5-fac10011bd0a","operation_id":"39a285dc-b128-46b0-94b5-fac10011bd0a","tool_attempt_id":"7f82d49d-3b11-4900-8c22-5d7a9011dc94","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"224f6dae-252b-45cf-9dda-dcb431c757c1","revision":"1"},"capture_id":"7f82d49d-3b11-4900-8c22-5d7a9011dc94","status":"accepted","artifact_refs":[{"id":"cdf20470-908b-451c-880f-64773115e584","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"cdf20470-908b-451c-880f-64773115e584","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_missing_mcp_type_and_revoked_function_adapter_do_not_execute

Contract point: Missing official MCP type fails closed; function adapter observes tool revocation.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_started_tool_can_settle_after_revocation_but_new_work_is_rejected

Contract point: Started work settles after revocation while new work remains denied.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBmZTYxYjE0NzdkOGFjMmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDIsIm5iZiI6MTc4OTI2ODk0MSwiZXhwIjoxNzg5MjY5MjQyLCJqdGkiOiI5MmIxYTJhZi04ZDQ0LTRlYWItYTQyYi0xNmY5Yzk1OGM3YTgifQ.uyFCpU7nkQvn8TZ84Kjv7BkgOxdxLArrEIRbLxJeCK3OTh2UCk06NDm69nKzBMcq9WSdcQLfj7pBafIcIEH6gkmqjns3-gMhR2ufoHGIluE6gstTbl5qcS32RC26kC3UrqBYfOj2T4yc-Wnq70JhiS3Xw2N2tTRiGVKGuskv8fde2mA4VeY6kKEfYBvsN5rMPfV1OVzHKSaChqnzpUTlrTjPs1MM9-_yHyhkWPp29o_IxpXuZCxiBvBqwb7R94HpGPHL_5iRmm7aOfEJ1qE9hrELsMTHEd9X-xG-ovGPUY9Dy2e9WdTbVmLJJA7zeHLgV-zqksBdibdyQMClaNcQuA
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-late-settlement

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-late","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 0e672a06-215e-41a6-9924-8106b165a1ca

{"tool_call_id":"b5c3b407-e278-43b0-a9b0-314b768385ad","operation_id":"b5c3b407-e278-43b0-a9b0-314b768385ad","tool_attempt_id":"0e83c5b4-4f4e-472a-a9dd-43596c675898","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"fbb244f1-32cb-4258-b524-cf70b8233e84","revision":"1"},"capture_id":"0e83c5b4-4f4e-472a-a9dd-43596c675898","status":"accepted","artifact_refs":[{"id":"366c1122-267e-4f98-9eee-3003818981af","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"366c1122-267e-4f98-9eee-3003818981af","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/tool-calls/b5c3b407-e278-43b0-a9b0-314b768385ad
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBmZTYxYjE0NzdkOGFjMmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDIsIm5iZiI6MTc4OTI2ODk0MSwiZXhwIjoxNzg5MjY5MjQyLCJqdGkiOiI5MmIxYTJhZi04ZDQ0LTRlYWItYTQyYi0xNmY5Yzk1OGM3YTgifQ.uyFCpU7nkQvn8TZ84Kjv7BkgOxdxLArrEIRbLxJeCK3OTh2UCk06NDm69nKzBMcq9WSdcQLfj7pBafIcIEH6gkmqjns3-gMhR2ufoHGIluE6gstTbl5qcS32RC26kC3UrqBYfOj2T4yc-Wnq70JhiS3Xw2N2tTRiGVKGuskv8fde2mA4VeY6kKEfYBvsN5rMPfV1OVzHKSaChqnzpUTlrTjPs1MM9-_yHyhkWPp29o_IxpXuZCxiBvBqwb7R94HpGPHL_5iRmm7aOfEJ1qE9hrELsMTHEd9X-xG-ovGPUY9Dy2e9WdTbVmLJJA7zeHLgV-zqksBdibdyQMClaNcQuA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 979a34e4-172f-4aa3-87c9-00cf74ffcf9d

{"tool_call_id":"b5c3b407-e278-43b0-a9b0-314b768385ad","operation_id":"b5c3b407-e278-43b0-a9b0-314b768385ad","tool_attempt_id":"0e83c5b4-4f4e-472a-a9dd-43596c675898","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"fbb244f1-32cb-4258-b524-cf70b8233e84","revision":"1"},"capture_id":"0e83c5b4-4f4e-472a-a9dd-43596c675898","status":"accepted","artifact_refs":[{"id":"366c1122-267e-4f98-9eee-3003818981af","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"366c1122-267e-4f98-9eee-3003818981af","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBmZTYxYjE0NzdkOGFjMmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDIsIm5iZiI6MTc4OTI2ODk0MSwiZXhwIjoxNzg5MjY5MjQyLCJqdGkiOiI5MmIxYTJhZi04ZDQ0LTRlYWItYTQyYi0xNmY5Yzk1OGM3YTgifQ.uyFCpU7nkQvn8TZ84Kjv7BkgOxdxLArrEIRbLxJeCK3OTh2UCk06NDm69nKzBMcq9WSdcQLfj7pBafIcIEH6gkmqjns3-gMhR2ufoHGIluE6gstTbl5qcS32RC26kC3UrqBYfOj2T4yc-Wnq70JhiS3Xw2N2tTRiGVKGuskv8fde2mA4VeY6kKEfYBvsN5rMPfV1OVzHKSaChqnzpUTlrTjPs1MM9-_yHyhkWPp29o_IxpXuZCxiBvBqwb7R94HpGPHL_5iRmm7aOfEJ1qE9hrELsMTHEd9X-xG-ovGPUY9Dy2e9WdTbVmLJJA7zeHLgV-zqksBdibdyQMClaNcQuA
connection: keep-alive
content-length: 264
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-new-after-revoke

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-after-revoke","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 157
content-type: application/json
x-request-id: 883fb09e-f5ec-461d-8f28-c2314faef81d

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"883fb09e-f5ec-461d-8f28-c2314faef81d","retryable":false,"details":{}}
```

## test_run_credential_does_not_grant_control_admit_or_capture

Contract point: Run purpose binding does not widen control, admit, capture or observe ACLs.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_authorized_not_sent_model_attempt_can_be_reconciled_without_refund

Contract point: Trusted reconcile ends a proven not-sent slot, preserves count and fences old begin_send.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjE2NTVmM2I1ZDA4MDk5ODcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDQsIm5iZiI6MTc4OTI2ODk0MywiZXhwIjoxNzg5MjY5MjQ0LCJqdGkiOiJjOTFmNjFmNy02NGIwLTQ5OWItOTFkMy1jNTFiYTJjZjhhNzYifQ.WyooQOQNSDQ6KdEybYJJnSuzu5GE9aF4-ha37s5SSYA3muC6JTg-BaZtroitHYJlRS-S45O4S5uUicN-e4K04b6IUKBha7Yk0BkeTdWGMwfWm2mXN3ltwkoje5QhpI1beGNtodqYvuoKn9py-pBGq8y5PVuHmCHMns-8VeHihgL5OO8lmKsLk5frr8GbtzTXjmpkOIH26eir_JQgO7egVOHttXKqSihTjWaOjAzy1ai2N_TT_05h7oJscBicH7WVf_yCL_fz5U6L4fs-fK-PqxI1DEuyMmZwpOndGHC8EtfMeibCXkBkOMy29_-eAsv9Keqxhp3l6sBTtvbeT1b6AA
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-authorized-not-sent

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 297
content-type: application/json
x-request-id: 42d1f0bc-a8b3-437d-a90f-d5d51c382ab6

{"code":"OPERATION_UNKNOWN","message":"The request could not be completed.","request_id":"42d1f0bc-a8b3-437d-a90f-d5d51c382ab6","retryable":false,"details":{"model_attempt_id":"de5d1e1f-41d2-4b3d-9eb9-bc61d17bd642","receipt_url":"/internal/v2/model-attempts/de5d1e1f-41d2-4b3d-9eb9-bc61d17bd642"}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjE2NTVmM2I1ZDA4MDk5ODcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDQsIm5iZiI6MTc4OTI2ODk0MywiZXhwIjoxNzg5MjY5MjQ0LCJqdGkiOiJjOTFmNjFmNy02NGIwLTQ5OWItOTFkMy1jNTFiYTJjZjhhNzYifQ.WyooQOQNSDQ6KdEybYJJnSuzu5GE9aF4-ha37s5SSYA3muC6JTg-BaZtroitHYJlRS-S45O4S5uUicN-e4K04b6IUKBha7Yk0BkeTdWGMwfWm2mXN3ltwkoje5QhpI1beGNtodqYvuoKn9py-pBGq8y5PVuHmCHMns-8VeHihgL5OO8lmKsLk5frr8GbtzTXjmpkOIH26eir_JQgO7egVOHttXKqSihTjWaOjAzy1ai2N_TT_05h7oJscBicH7WVf_yCL_fz5U6L4fs-fK-PqxI1DEuyMmZwpOndGHC8EtfMeibCXkBkOMy29_-eAsv9Keqxhp3l6sBTtvbeT1b6AA
connection: keep-alive
content-length: 205
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-after-not-sent

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 84b0e29a-8435-476f-a3c3-bd014dc4fb29
x-wuji-model-attempt-id: 5acd5559-22e2-45a4-9043-c47bb3bc9dcd
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:65009/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:65009
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 5acd5559-22e2-45a4-9043-c47bb3bc9dcd

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_cancel_replay_delivers_same_persisted_cancel_operation

Contract point: Cancel replay delivers the same durable cancellation after a post-commit crash.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_database_write_policies_separate_model_and_tool_purposes

Contract point: 0008 RLS and counter trigger prevent cross-purpose ledger writes.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImMwMTQ2MzI3MzRlNWJiM2MifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDYsIm5iZiI6MTc4OTI2ODk0NSwiZXhwIjoxNzg5MjY5MjQ2LCJqdGkiOiI5YzdkOThmYS0xNTA1LTRmZTQtOWFjOS0yYjAxMjI3NWMwMjkifQ.fgvph0sAqBhWbyM9c1peGdjalsLbO1-MJxRC4eBr9DTtxBlYZFnc7aPDvAQbl2MC1AkNuAcV6k7vzikKZqEQOqiBb3zQwvugxz3piTLAp5E3DK3N2lNVi4d5ZdpNURGn_Q5C5rm-bMkh3F4X6VhI_9i2wbFMvzM1jVCz53KlR9wd_uJvgwEGv6eH6NhM_Zd-LQTINhrott0lOVa6_EtROkJ8Z0E2u5pvdEcxkXBqgZH3Mi8tSuDHwg6l__ujd0LK7ceHsX_6s7r2uogWn-AArmYh8BhoaFFCWi-6gr0lp75VL2eDqA2IbxOd-IrDkwN0lE-fJ64AtHUmLlU4Vzgf7A
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-purpose-fixture

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 61d928cc-066c-46c6-b0d0-4e926e6e4782

{"tool_call_id":"1f0e1b6f-fccb-405d-8658-feb484d5d0b9","operation_id":"1f0e1b6f-fccb-405d-8658-feb484d5d0b9","tool_attempt_id":"491d6581-bcf7-42b8-b5bd-56d6253a87b5","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"2bd19d85-e147-469d-adf8-088c39b9be16","revision":"1"},"capture_id":"491d6581-bcf7-42b8-b5bd-56d6253a87b5","status":"accepted","artifact_refs":[{"id":"d9752080-014b-4161-95fd-cd8c30c3e416","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"d9752080-014b-4161-95fd-cd8c30c3e416","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_explicit_null_tools_is_a_valid_native_model_request

Contract point: Explicit tools:null is accepted as native no-tools input.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZjN2RhMWUyZjQxYTI3MGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDgsIm5iZiI6MTc4OTI2ODk0NywiZXhwIjoxNzg5MjY5MjQ4LCJqdGkiOiJmMWVkZjM4Ni1lMjZhLTQ0MTgtOGU1ZS1iZjc0NzYxODhmMDEifQ.OFEuVm8BLuCvQztWikiOMZ0uXQ3AEKV1ccXXpOdICG2af4k-UeiZyx4CZ8EZ0VMpkB0c1ImnwNWBIj0D6y_RDS4SnfE_WEVAfUaB7xtExWPEaFjGcieCl51kF8YqGQDabQqpcsfrHCk01QA5rhBEDRydPf2Z9vYY4PsayNTEdXHDBmeYAe_9U1zc_DckEweWFFyA-D2RAXLvGyvBhgiG38Nw_crIYubt5qu6ZC3hFLuwQdGe5f1O-EaQb1xQHOAnt2tpzsZ-cJtnFLk59lyZi2BEWu8rbbBOVqK735d_0NZelDhGJxYFChuPvcUnnu67nWqItaNFApE9KR8hvHW-BA
connection: keep-alive
content-length: 218
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-tools-null

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125,"tools":null}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 9c0190bf-2dc7-4fcb-b570-bd381ee383f7
x-wuji-model-attempt-id: 96b859eb-f999-48cf-8e14-53b9dbad9588
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:65022/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 227
content-type: application/json
host: 127.0.0.1:65022
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 96b859eb-f999-48cf-8e14-53b9dbad9588

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125,"tools":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_model_tool_advertisement_requires_actual_gate_assembly

Contract point: Registered definition without actual ToolGate assembly fails before inference.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRlYjlmNWI5M2QwOWQ5OTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NDksIm5iZiI6MTc4OTI2ODk0OCwiZXhwIjoxNzg5MjY5MjQ5LCJqdGkiOiIxN2U1ZGU3Ni02Yjk0LTRmNjgtYTA4ZC01OTNmYjI0MzY1YmEifQ.iB0aZOUpj-cwqvwB3ahLp5LOiJX9qS469ivTrpUHHJhrxecowYEZ59ZUkijX5bTY8nJZUiUaAyCq78mp6xdWZVBdPeLNSZJZyCAYcizPXVbQFiXQFHzVeG4LBc0Oyp-W6zS-U_VTtJY2y6uRGdjE020RgfC-uV47nFec5LbeYThD9iMrr73akqLsoSBwHaHmwwTi69YsCKU1inQGwf8Sez3GTfSqLhOw3BP7QiCFM1hTtskSA3YNMHeMqBi5zh7bXTkH_lr1LlXVsjN1GJWT-4j6n-RhN77zorJTQCw92-etJEbVS_nFMfbhJbmLRoGHY-XacLdGPcCGNOuEeyWemA
connection: keep-alive
content-length: 451
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-unassembled-tool

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125,"tools":[{"function":{"description":"Read an isolated fixture file.","name":"read_fixture","parameters":{"additionalProperties":false,"properties":{"path":{"minLength":1,"type":"string"}},"required":["path"],"type":"object"}},"type":"function"}]}
```

Response:

```http
HTTP/1.1 503 Service Unavailable
content-length: 164
content-type: application/json
x-request-id: 0cfec509-142f-40c0-83d2-e0005bc35340

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"0cfec509-142f-40c0-83d2-e0005bc35340","retryable":false,"details":{}}
```

## test_model_tool_advertisement_accepts_the_actual_tool_gate_assembly

Contract point: Shared resolver accepts a registered and actually assembled workspace tool.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjM2MDI3ZjM4N2QwMzFmYTUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhc3NlbWJsZWQtbW9kZWwtd29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NTAsIm5iZiI6MTc4OTI2ODk0OSwiZXhwIjoxNzg5MjY5MjUwLCJqdGkiOiI2MjUyMGU1ZC00NTE1LTRlOGEtYWNiNy1hNTI2MTIyMmEyOGMifQ.GE3Wj_b48u2v3KoTgEn2TEDQHD25PLRg4zXzDihYiE_yCjPi2Iy38CQkuvh1K6SFuLwZTXMuHCIbpaCT1pO07XyjIDx2GGwMgOKuJWNii024HmoO_QY4nnUq33rvqBPx-c9dcGI64wLEzsntbfZ9XUEhcGCrue_N2B21A8w2fxqYeK3SmoT9SrH2cwaLRHsUdgacsMKeji7KKjFL1QxSY69nIPiySUpQz3qWO6xVpKz7QaGtvSV4dUFyztiolJ3cdqNDpylJwhFWD6WKFaDeOKpqJEF1yo-MBwi0wwAJszFJrm9yW3L_nJ14oVPwDkU5XbzgsCk8Cui15m9PD8_M9w
connection: keep-alive
content-length: 451
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: model-assembled-tool

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-model","stream":false,"temperature":0.125,"tools":[{"function":{"description":"Read an isolated fixture file.","name":"read_fixture","parameters":{"additionalProperties":false,"properties":{"path":{"minLength":1,"type":"string"}},"required":["path"],"type":"object"}},"type":"function"}]}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-length: 377
content-type: application/json
x-request-id: 36ab3429-4903-4a24-b334-cea301cc7f94
x-wuji-model-attempt-id: ad9e6c19-fc83-4922-aa6c-b7b1b4950879
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:65032/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 460
content-type: application/json
host: 127.0.0.1:65032
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: ad9e6c19-fc83-4922-aa6c-b7b1b4950879

{"max_tokens":64,"messages":[{"content":"Use only the synthetic fixture.","role":"system"},{"content":"Read the fixture version.","role":"user"}],"model":"fixture-upstream-model","stream":false,"temperature":0.125,"tools":[{"function":{"description":"Read an isolated fixture file.","name":"read_fixture","parameters":{"additionalProperties":false,"properties":{"path":{"minLength":1,"type":"string"}},"required":["path"],"type":"object"}},"type":"function"}]}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 377
content-type: application/json

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

## test_workspace_output_limit_returns_partial_evidence_and_reason

Contract point: Tool output retains a bounded prefix with partial evidence and LIMIT_BLOCKED.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjMxZWYwYTgxZDcwMDUyOTMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NTEsIm5iZiI6MTc4OTI2ODk1MCwiZXhwIjoxNzg5MjY5MjUxLCJqdGkiOiI3NzYwNjg0OS1lNjZlLTRmOWQtYjg1ZS0xNjRiNzk1YzUyM2EifQ.kOsfmuIFH462gc-qQytpuWO15Iz7NxMeY2AaRY2KLWLtTSMD2vSO0ZUB-f7gozS-hfRVsQaaV_K-KRfWRCfla4y84t23tp266UZU6RX4mTBDNagHR2O1lHC9fbhOjSaJlTZf4h4VLTT-j7zbVw3bLMNkZCpNmveHwWnpOSbQJluvJhAjPPUKDeQeWkuNxdqneVECD0PgZS79VzYggNDEArJEZtPnJKA9vsZEbSsmUKy46NwKS1Q7quSzLOtV3dD2rrb2Bd9HD9hDGVUDSqahdEU2OkpjpYyWIFBejvUcmsgb6XQlb71UmMCHPcLQPgD_vSzN5RxU1qcYr3aeebkjJQ
connection: keep-alive
content-length: 256
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: tool-partial-output-limit

{"session_lineage":"session-lineage-fixture","message_id":"message-p06-tool-1","provider_call_id":"call-p06-read","tool_definition_ref":"fixture-reader-v1","arguments":{"path":"version.txt"},"sdk_content_id":null,"sdk_approval_id":null,"approval_ref":null}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 762
content-type: application/json
x-request-id: 6d0515d8-ad90-4c74-8b79-ce406d71cbb4

{"tool_call_id":"57aa4c3d-6eae-4f22-b116-9c55ef86320f","operation_id":"57aa4c3d-6eae-4f22-b116-9c55ef86320f","tool_attempt_id":"22753c47-9b6b-4dbc-811a-58f9afa0a472","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"1e8b3a3e-7a2d-45df-a5ee-6a32ebcc18c5","revision":"1"},"capture_id":"22753c47-9b6b-4dbc-811a-58f9afa0a472","status":"accepted","artifact_refs":[{"id":"7641f9ff-9807-4dd4-b563-7ba771c28a9a","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"7641f9ff-9807-4dd4-b563-7ba771c28a9a","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"},"reason_code":"LIMIT_BLOCKED"}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/7641f9ff-9807-4dd4-b563-7ba771c28a9a/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjMxZWYwYTgxZDcwMDUyOTMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjg5NTEsIm5iZiI6MTc4OTI2ODk1MCwiZXhwIjoxNzg5MjY5MjUxLCJqdGkiOiI3NzYwNjg0OS1lNjZlLTRmOWQtYjg1ZS0xNjRiNzk1YzUyM2EifQ.kOsfmuIFH462gc-qQytpuWO15Iz7NxMeY2AaRY2KLWLtTSMD2vSO0ZUB-f7gozS-hfRVsQaaV_K-KRfWRCfla4y84t23tp266UZU6RX4mTBDNagHR2O1lHC9fbhOjSaJlTZf4h4VLTT-j7zbVw3bLMNkZCpNmveHwWnpOSbQJluvJhAjPPUKDeQeWkuNxdqneVECD0PgZS79VzYggNDEArJEZtPnJKA9vsZEbSsmUKy46NwKS1Q7quSzLOtV3dD2rrb2Bd9HD9hDGVUDSqahdEU2OkpjpYyWIFBejvUcmsgb6XQlb71UmMCHPcLQPgD_vSzN5RxU1qcYr3aeebkjJQ
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
content-disposition: attachment
content-security-policy: default-src 'none'
content-type: application/octet-stream
digest: sha-256=7fxaTzN0gVA1EfzUcIki7HzBU3qQXHj9A67NATwyGcI=
x-content-type-options: nosniff
x-request-id: 9fa5301f-8bb9-473d-9ba9-a27de67f27f3

fixtu
```

## test_partial_workspace_receipt_replay_compares_original_output_metadata

Contract point: Repeated receiver receipt compares original digest/length without duplicate accounting.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_model_openapi_declares_runtime_correlation_headers

Contract point: OpenAPI declares runtime attempt and replay response headers.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.
