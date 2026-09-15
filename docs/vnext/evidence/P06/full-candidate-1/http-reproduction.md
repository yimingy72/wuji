# P06 complete HTTP reproduction packets

Candidate: `f32678d5662965f44b32863e8ecdf306db676ffd`; migration head: `vnext_0007_p06_admission`.
All credentials and keys below are synthetic, isolated test values. Packets are decoded verbatim from the final run's JSONL capture; bodies are not truncated.

## test_current_run_model_gate_forwards_native_and_records_attempt

Contract point: Signed Run admission, native response preservation, private Task key, durable receipt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkzZTI3YzI3ZGFhNjlhMmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTUsIm5iZiI6MTc4OTI2NjY5NCwiZXhwIjoxNzg5MjY2OTk1LCJqdGkiOiI5YTIyYTNjOC03OWM5LTRiNTQtOWIwOS0xNDkxMTMxNzU5NjYifQ.iRQDpj6dMrx0NM0OGuC8Nh4i06xjNpEXLvhRyBs-vMvWdXkZDNVatOBy9_1VnXEYoNJyJGz6cYGaBblj8JLOsK53ZGc9dPgtS9HfmD2ppfYQfD4kGnxw3IK12IudVJ0yUTDai4ui7E8ox2_Dq82RqE57EK0z1p-0epDQZjWAgA5Q195R4eay-razWC3ZbEbigARJYvykwkdEA0xQw9jA2IkjkRPoE2RrQ9mnfcel6Gfu90VhMGKrB64ggz7_WI7fc_83Kx-gZRoFDFLzDQrk99tRtRDH5tfffq-UTQIGAssMuKDRxgOSuaPRVJIw_T9BCXoTKdU9__YtpfabE_6abA
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
x-request-id: 98174ad4-b1a4-41da-a70f-fcccbf0bd237
x-wuji-model-attempt-id: 16794e65-a0aa-4978-9a25-df6917e6c91d
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/16794e65-a0aa-4978-9a25-df6917e6c91d
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkzZTI3YzI3ZGFhNjlhMmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTUsIm5iZiI6MTc4OTI2NjY5NCwiZXhwIjoxNzg5MjY2OTk1LCJqdGkiOiI5YTIyYTNjOC03OWM5LTRiNTQtOWIwOS0xNDkxMTMxNzU5NjYifQ.iRQDpj6dMrx0NM0OGuC8Nh4i06xjNpEXLvhRyBs-vMvWdXkZDNVatOBy9_1VnXEYoNJyJGz6cYGaBblj8JLOsK53ZGc9dPgtS9HfmD2ppfYQfD4kGnxw3IK12IudVJ0yUTDai4ui7E8ox2_Dq82RqE57EK0z1p-0epDQZjWAgA5Q195R4eay-razWC3ZbEbigARJYvykwkdEA0xQw9jA2IkjkRPoE2RrQ9mnfcel6Gfu90VhMGKrB64ggz7_WI7fc_83Kx-gZRoFDFLzDQrk99tRtRDH5tfffq-UTQIGAssMuKDRxgOSuaPRVJIw_T9BCXoTKdU9__YtpfabE_6abA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 544
content-type: application/json
x-request-id: f7cf19d0-2aa0-446d-8377-ac34cc415a30

{"model_attempt_id":"16794e65-a0aa-4978-9a25-df6917e6c91d","input_digest":"57d0d5d1f73d05a69fef3b3d9d68088f4408bde81680c5a37b2008cba4c46149","logical_request_id":"model-request-current-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"complete","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":true,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"377","retained_bytes":"377","forwarded_bytes":"377","output_bytes":"377"}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:59794/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59794
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 16794e65-a0aa-4978-9a25-df6917e6c91d

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

Contract point: Revoked Run credential returns STALE_EXECUTION without an upstream request or attempt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImNlOWFmNDE4MDg0M2ExZGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTYsIm5iZiI6MTc4OTI2NjY5NSwiZXhwIjoxNzg5MjY2OTk2LCJqdGkiOiIyODgwNGQyYS05ZGI0LTQxNDMtYWQ0NS1kMTJlYjkxOWM1MmIifQ.l5k3oYzd5B7tE0VtwryNAgSz3eweIYci9c24HpCCJo0IAG6pn9uHnFb5ADI0VOTsAYiDfTd1gNS3ZVinwuChNhMWdctSKscfigKGrosdwYz3LLfQpXZvPlltxwBh2oM9yzvdWigQvRQeovMu6eE0zaCosdS-3r4v87D11HMb2vTjSst5if7JoFvdeYupA5mnfHpzgj2lmjMXU9m3yUlm_uhIoikA3e30YdXfHSG5lXY686msdtOebXTRsnZ-H4oPRiorxsGm7_oFukcdlFy9ejANOIGiguthfkQXPXv6a0JfM4KaPepQA_FsOHXH12SOb_NXdZdEtI4Vb-CHMwhYHw
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
x-request-id: 10766c7b-fe61-4a3c-a94d-739b16a48f99

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"10766c7b-fe61-4a3c-a94d-739b16a48f99","retryable":false,"details":{}}
```

## test_p05_pause_makes_bound_run_identity_stale

Contract point: P05 pause invalidates the otherwise valid bound Run.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjE1OTM5YWE0ZDRhYTAzMzgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTcsIm5iZiI6MTc4OTI2NjY5NiwiZXhwIjoxNzg5MjY2OTk3LCJqdGkiOiJjNjYzM2NlYS1mY2Y1LTQwODktYmU1Yy01YzQ3ZjZiNmIyNDIifQ.iOdbucNV8lylafF9-iCVIRGu2jHaDv1mWjhB6Y80j-hueLo2WS4IOaiODdonAvm0S7zh5YqSOCG_gMU8yjaixrqKcC8qOdo0azYPG-KMFpyD4pqdtMF_B3MIN1MD4pdHBsabNl3gyleg8biSUcdhOl7Na8vu5Q0W6ULLo5K9aO_NIY7C1KLjf4zSUzyGupEVzxkFsJGrTpTYTcDssqTUvp69Z-HWeQMKKuyppUixZ_fqWai2clkVQRnFKEv-QtJYq92pVad2dpLvNl-7MT3oScXgCRTGIpX2di8alua2s_khWSO3y_j0lEWIxFa-MDI0RUHsKlEBNVFMW40Mb7l-Ig
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
x-request-id: fbd1ba46-74cb-4419-8617-1f34d4de3ea8

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"fbd1ba46-74cb-4419-8617-1f34d4de3ea8","retryable":false,"details":{}}
```

## test_model_request_replay_conflict_and_new_id_have_distinct_attempts

Contract point: Same request ID replays, changed digest conflicts, and a new ID creates a new inference.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUzYzJlMjA3ZGQ4Y2RmY2UifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTgsIm5iZiI6MTc4OTI2NjY5NywiZXhwIjoxNzg5MjY2OTk4LCJqdGkiOiI4NTg1NmIzNi0xNmZmLTRjYzgtYjcwOS01MmI3NjliZDU4NTkifQ.eDW_6kDrv49ku7rx1gOCk5l4spUmUGWz2_S4-FC5jo9rK59Q8xF_pzYvuBHG7FCTEMli7yHPHEj3pW4I8m11z4FxXi792ErI1o8svBNT4qTT3pYRxxrzsic4EOt7RAdIy1jxNCh3ut5NogPMZaSWztH3jZ6fbwSjHsC1o3C3oyjv1s5kkTCaeWRcqE0I6Ku_nd2E3V0XPDkjTc6FVLX7gVLSc1LezgACDQUNnXsEtiAtxF2M9su0Aok8R8BEfmoR8GQ2kAAGoNFfNjLmbCdyhOzwYPUu8AUyweM70GYqjhRAOBjJ3z3LLJU4KAyzcwBc1VFHN_lgxzK4SChfamAyhQ
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
x-request-id: 0d6a8e5c-f111-4ac7-89ed-bdabf054e368
x-wuji-model-attempt-id: 4ba1768d-5588-4501-9d2d-73024852dbe2
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUzYzJlMjA3ZGQ4Y2RmY2UifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTgsIm5iZiI6MTc4OTI2NjY5NywiZXhwIjoxNzg5MjY2OTk4LCJqdGkiOiI4NTg1NmIzNi0xNmZmLTRjYzgtYjcwOS01MmI3NjliZDU4NTkifQ.eDW_6kDrv49ku7rx1gOCk5l4spUmUGWz2_S4-FC5jo9rK59Q8xF_pzYvuBHG7FCTEMli7yHPHEj3pW4I8m11z4FxXi792ErI1o8svBNT4qTT3pYRxxrzsic4EOt7RAdIy1jxNCh3ut5NogPMZaSWztH3jZ6fbwSjHsC1o3C3oyjv1s5kkTCaeWRcqE0I6Ku_nd2E3V0XPDkjTc6FVLX7gVLSc1LezgACDQUNnXsEtiAtxF2M9su0Aok8R8BEfmoR8GQ2kAAGoNFfNjLmbCdyhOzwYPUu8AUyweM70GYqjhRAOBjJ3z3LLJU4KAyzcwBc1VFHN_lgxzK4SChfamAyhQ
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
x-request-id: 60686a77-fc56-48f8-8b20-d3df15db731c
x-wuji-model-attempt-id: 4ba1768d-5588-4501-9d2d-73024852dbe2
x-wuji-replayed: true

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUzYzJlMjA3ZGQ4Y2RmY2UifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTgsIm5iZiI6MTc4OTI2NjY5NywiZXhwIjoxNzg5MjY2OTk4LCJqdGkiOiI4NTg1NmIzNi0xNmZmLTRjYzgtYjcwOS01MmI3NjliZDU4NTkifQ.eDW_6kDrv49ku7rx1gOCk5l4spUmUGWz2_S4-FC5jo9rK59Q8xF_pzYvuBHG7FCTEMli7yHPHEj3pW4I8m11z4FxXi792ErI1o8svBNT4qTT3pYRxxrzsic4EOt7RAdIy1jxNCh3ut5NogPMZaSWztH3jZ6fbwSjHsC1o3C3oyjv1s5kkTCaeWRcqE0I6Ku_nd2E3V0XPDkjTc6FVLX7gVLSc1LezgACDQUNnXsEtiAtxF2M9su0Aok8R8BEfmoR8GQ2kAAGoNFfNjLmbCdyhOzwYPUu8AUyweM70GYqjhRAOBjJ3z3LLJU4KAyzcwBc1VFHN_lgxzK4SChfamAyhQ
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
x-request-id: 24f7d91c-56ad-4b39-b3b6-69bd72c2d844

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"24f7d91c-56ad-4b39-b3b6-69bd72c2d844","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUzYzJlMjA3ZGQ4Y2RmY2UifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTgsIm5iZiI6MTc4OTI2NjY5NywiZXhwIjoxNzg5MjY2OTk4LCJqdGkiOiI4NTg1NmIzNi0xNmZmLTRjYzgtYjcwOS01MmI3NjliZDU4NTkifQ.eDW_6kDrv49ku7rx1gOCk5l4spUmUGWz2_S4-FC5jo9rK59Q8xF_pzYvuBHG7FCTEMli7yHPHEj3pW4I8m11z4FxXi792ErI1o8svBNT4qTT3pYRxxrzsic4EOt7RAdIy1jxNCh3ut5NogPMZaSWztH3jZ6fbwSjHsC1o3C3oyjv1s5kkTCaeWRcqE0I6Ku_nd2E3V0XPDkjTc6FVLX7gVLSc1LezgACDQUNnXsEtiAtxF2M9su0Aok8R8BEfmoR8GQ2kAAGoNFfNjLmbCdyhOzwYPUu8AUyweM70GYqjhRAOBjJ3z3LLJU4KAyzcwBc1VFHN_lgxzK4SChfamAyhQ
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
x-request-id: a16c0fa1-c6c0-4177-8638-84c229e267b2
x-wuji-model-attempt-id: 30b605b5-9d1c-4588-ab03-823a388ad132
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:59803/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59803
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 4ba1768d-5588-4501-9d2d-73024852dbe2

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
POST http://127.0.0.1:59803/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59803
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 30b605b5-9d1c-4588-ab03-823a388ad132

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

Contract point: Two Runs race the final Task model quota; exactly one request reaches the upstream.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEyM2RhOTdkYzIwMzg5ZWEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsid29ya2VyIl0sImlhdCI6MTc4OTI2NjcwMCwibmJmIjoxNzg5MjY2Njk5LCJleHAiOjE3ODkyNjcwMDAsImp0aSI6Ijk5YTQ1ZDkwLWRjNzgtNGJkNC05MDFjLTAwZWNjNjliNDk5YSJ9.ZQ0DwcRMWtR_l1c2HgR0Ro9NaCQlBSwBAy5opjmD_qnHFviK7Um1dPm07fLDQZi5yi_x8WVepKj-XritOuUaS3I7qOZ7uxDH77AGUavIxoqFsRLr0GFqEleVQ6Mv3AiFcO-M9hdgBMdz0DHYidaS5fVJ693E0tAISFiTQ1s-4EF0LOe5KohquGOkjRr3hEqubQR2eiDva9BvyaZ6rgS1dKUd7XOnEBCtyV0SUutbZ2ZNdwKZsWab_wCubyFK003jCxXRpll82YbohdnL1GA2w_AFG_IFXCHgUQ6H8I1kmDP0hYYc5sp8rcgML5dZgcT3D5CEfsHjcWAqcILDVkPjRA
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
x-request-id: 08fff08c-f3cc-4e0e-a583-cb10ba861e27

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"08fff08c-f3cc-4e0e-a583-cb10ba861e27","retryable":false,"details":{}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEyM2RhOTdkYzIwMzg5ZWEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY2OTksIm5iZiI6MTc4OTI2NjY5OCwiZXhwIjoxNzg5MjY2OTk5LCJqdGkiOiJhNjkxZTYwMi1jNjEyLTRlMTQtOGZjZC1lZmZmMzUzODZmNzgifQ.e0wlUc1wehaR9jr8lOvszGgb1SRN6P9131mLzU6vV0_udIaJkENM9QVlPQlLoyEDcvRRt2pMT63XkOVMGV9xiHVUSm2F-hlQA9iO66hfzYvmh2J4AmTzVZo6jn0-U409RMYg0bNsIkfcDkJ7cgoWWSQ423ZhIrproiyayrmXQcKn1tVYo0KoZ75eW_Iy54uq12ZkFsrJPZMv9P0HPhqSqvruWklJV8Qhy1GCzARsFKakdaCuG_V0GZc9_w4qptOv9-uFCw7GoS3F1oLQ_dz4LEWRwqD9degIH_DQkLib0CzNLdKgfJlWWJtKBzRC4CvTGd4a_cMlAQFwmIpLP_1hhA
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
x-request-id: d01ae98e-a483-49a4-9063-3e85e16b9347
x-wuji-model-attempt-id: 4730032e-3eee-4765-b34f-084104478e1b
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:59810/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59810
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 4730032e-3eee-4765-b34f-084104478e1b

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

Contract point: A stream without [DONE] remains partial, does not fabricate completion, and releases a proven-ended local slot.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjJhYTM5OGYzZjhlMGVmNzMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDEsIm5iZiI6MTc4OTI2NjcwMCwiZXhwIjoxNzg5MjY3MDAxLCJqdGkiOiI1MDM5NTQ3ZS05MGE1LTRlNTQtYWYyZC0yODBkNmMzZWUyMGMifQ.Ph-m5cEtIzKC2V0qv45C9kPy-4PJBc8KIlw0u_OiqYyiNDiTS-eDacR---5WG-p1xX9oENuwMprOnySJsThdvsx5OyKMM49l3U6U7KDc8KDmM3mdbfmy9HutjsmIT8XrUf0topayH4IbUHw9vzEsy_oC0KjyNko0b1MPMbEIR5kb01JrHGEwTRIKTuHHxxYsO3kJI6ouPHY6aFE5lVZYrkyPNJKq-tEwJPEqlVEUV0PAFFmkMwAD_PM_mojQEMk331DI6HNPO9LqaJLSY5Wizmd3AMtpuYvsiwycPlRdeWV_B8pB7ZM0tzS8nw_AVaD9vL2YJDaopsmXhV-9eo3ONA
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
x-request-id: fc0e8a2a-6744-46a8-826e-3f6f0d204ed2
x-wuji-model-attempt-id: 4fa9548e-cbc6-400f-b924-b40933f0cc42
x-wuji-replayed: false

data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk","created":1,"model":"fixture-model","choices":[{"index":0,"delta":{"role":"assistant","content":"partial"},"finish_reason":null}]}


```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/4fa9548e-cbc6-400f-b924-b40933f0cc42
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjJhYTM5OGYzZjhlMGVmNzMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDEsIm5iZiI6MTc4OTI2NjcwMCwiZXhwIjoxNzg5MjY3MDAxLCJqdGkiOiI1MDM5NTQ3ZS05MGE1LTRlNTQtYWYyZC0yODBkNmMzZWUyMGMifQ.Ph-m5cEtIzKC2V0qv45C9kPy-4PJBc8KIlw0u_OiqYyiNDiTS-eDacR---5WG-p1xX9oENuwMprOnySJsThdvsx5OyKMM49l3U6U7KDc8KDmM3mdbfmy9HutjsmIT8XrUf0topayH4IbUHw9vzEsy_oC0KjyNko0b1MPMbEIR5kb01JrHGEwTRIKTuHHxxYsO3kJI6ouPHY6aFE5lVZYrkyPNJKq-tEwJPEqlVEUV0PAFFmkMwAD_PM_mojQEMk331DI6HNPO9LqaJLSY5Wizmd3AMtpuYvsiwycPlRdeWV_B8pB7ZM0tzS8nw_AVaD9vL2YJDaopsmXhV-9eo3ONA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 536
content-type: application/json
x-request-id: ddaf9955-c526-4cd1-90fd-9e4098013216

{"model_attempt_id":"4fa9548e-cbc6-400f-b924-b40933f0cc42","input_digest":"cc712b587519e826c7e1e943cc65088a98dc0d8cd3d981eda39c2aa8c5a620ad","logical_request_id":"model-partial-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"partial","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":false,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"200","retained_bytes":"200","forwarded_bytes":"200","output_bytes":"200"}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjJhYTM5OGYzZjhlMGVmNzMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDEsIm5iZiI6MTc4OTI2NjcwMCwiZXhwIjoxNzg5MjY3MDAxLCJqdGkiOiI1MDM5NTQ3ZS05MGE1LTRlNTQtYWYyZC0yODBkNmMzZWUyMGMifQ.Ph-m5cEtIzKC2V0qv45C9kPy-4PJBc8KIlw0u_OiqYyiNDiTS-eDacR---5WG-p1xX9oENuwMprOnySJsThdvsx5OyKMM49l3U6U7KDc8KDmM3mdbfmy9HutjsmIT8XrUf0topayH4IbUHw9vzEsy_oC0KjyNko0b1MPMbEIR5kb01JrHGEwTRIKTuHHxxYsO3kJI6ouPHY6aFE5lVZYrkyPNJKq-tEwJPEqlVEUV0PAFFmkMwAD_PM_mojQEMk331DI6HNPO9LqaJLSY5Wizmd3AMtpuYvsiwycPlRdeWV_B8pB7ZM0tzS8nw_AVaD9vL2YJDaopsmXhV-9eo3ONA
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
x-request-id: 0b9c4fdb-2ca9-4562-820e-9d0b38200b6f
x-wuji-model-attempt-id: f86ccda5-58b6-44f9-9bbc-31c2f4492166
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:59812/v1/chat/completions
accept: text/event-stream
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 213
content-type: application/json
host: 127.0.0.1:59812
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 4fa9548e-cbc6-400f-b924-b40933f0cc42

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
POST http://127.0.0.1:59812/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59812
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: f86ccda5-58b6-44f9-9bbc-31c2f4492166

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

Contract point: Production workspace_read returns only after Artifact and EvidenceReceipt persistence; GET does not re-execute.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEzZDYzNDc4MWZkNjk3NmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDIsIm5iZiI6MTc4OTI2NjcwMSwiZXhwIjoxNzg5MjY3MDAyLCJqdGkiOiIwNDQ1MjBkYy05YTcwLTQ0Y2ItYjQxZS0xZjZhYTM2NzFiOWEifQ.ipkFm-gdmj4rr75geEgjRB9PlWKiWSdPYMgx_VMSmx2cNZ5AEKBVLl-Vfu-yjXJPeRu6XiFSXOq5EdcbiZJgwP0T-T0cLDDAgBhZ0MBoVb7fmxtMsiwlWc-GbPHsdiUIq3T8VLQSi3UlrjNu__EFFm2Z-Evo0ojE2eojKge0Y7TIzb8phvOrrfcVpsY3NMmAcn7EQ5q8_A8zrTmOKquj4XRxFo_irMtu3NPWKEOKmsq_wyBrFrG8-k1031Y0zIkjCSonJd0DYh_RKwDkt9h7zz5D6BYOsmeBGpji6HsCMZIuqZNIr3djcs0-RdoU5nzjCCI8XKGwFJTSP2rlHAu9bw
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
x-request-id: c2ec99b7-5e98-4aa4-a0e5-3accc1dc2522

{"tool_call_id":"45d64d83-3698-4435-ab3a-6e44b86a368f","operation_id":"45d64d83-3698-4435-ab3a-6e44b86a368f","tool_attempt_id":"5e76b5b4-7e64-4ed6-8658-c950a60ef908","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"22d5ba27-c61b-4702-8906-9ad45688c51a","revision":"1"},"capture_id":"5e76b5b4-7e64-4ed6-8658-c950a60ef908","status":"accepted","artifact_refs":[{"id":"94393d03-ab53-48ad-bdb1-a72fea4de4a3","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"94393d03-ab53-48ad-bdb1-a72fea4de4a3","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/94393d03-ab53-48ad-bdb1-a72fea4de4a3/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEzZDYzNDc4MWZkNjk3NmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDIsIm5iZiI6MTc4OTI2NjcwMSwiZXhwIjoxNzg5MjY3MDAyLCJqdGkiOiIwNDQ1MjBkYy05YTcwLTQ0Y2ItYjQxZS0xZjZhYTM2NzFiOWEifQ.ipkFm-gdmj4rr75geEgjRB9PlWKiWSdPYMgx_VMSmx2cNZ5AEKBVLl-Vfu-yjXJPeRu6XiFSXOq5EdcbiZJgwP0T-T0cLDDAgBhZ0MBoVb7fmxtMsiwlWc-GbPHsdiUIq3T8VLQSi3UlrjNu__EFFm2Z-Evo0ojE2eojKge0Y7TIzb8phvOrrfcVpsY3NMmAcn7EQ5q8_A8zrTmOKquj4XRxFo_irMtu3NPWKEOKmsq_wyBrFrG8-k1031Y0zIkjCSonJd0DYh_RKwDkt9h7zz5D6BYOsmeBGpji6HsCMZIuqZNIr3djcs0-RdoU5nzjCCI8XKGwFJTSP2rlHAu9bw
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
x-request-id: dd710385-b1a1-485b-8ee9-5c662ebef97d

fixture-version=17

```

### Inbound ASGI exchange 3

Request:

```http
GET http://testserver/internal/v2/tool-calls/45d64d83-3698-4435-ab3a-6e44b86a368f
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEzZDYzNDc4MWZkNjk3NmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDIsIm5iZiI6MTc4OTI2NjcwMSwiZXhwIjoxNzg5MjY3MDAyLCJqdGkiOiIwNDQ1MjBkYy05YTcwLTQ0Y2ItYjQxZS0xZjZhYTM2NzFiOWEifQ.ipkFm-gdmj4rr75geEgjRB9PlWKiWSdPYMgx_VMSmx2cNZ5AEKBVLl-Vfu-yjXJPeRu6XiFSXOq5EdcbiZJgwP0T-T0cLDDAgBhZ0MBoVb7fmxtMsiwlWc-GbPHsdiUIq3T8VLQSi3UlrjNu__EFFm2Z-Evo0ojE2eojKge0Y7TIzb8phvOrrfcVpsY3NMmAcn7EQ5q8_A8zrTmOKquj4XRxFo_irMtu3NPWKEOKmsq_wyBrFrG8-k1031Y0zIkjCSonJd0DYh_RKwDkt9h7zz5D6BYOsmeBGpji6HsCMZIuqZNIr3djcs0-RdoU5nzjCCI8XKGwFJTSP2rlHAu9bw
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 79902582-3b10-4f0e-b2e4-e8043fcb7f47

{"tool_call_id":"45d64d83-3698-4435-ab3a-6e44b86a368f","operation_id":"45d64d83-3698-4435-ab3a-6e44b86a368f","tool_attempt_id":"5e76b5b4-7e64-4ed6-8658-c950a60ef908","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"22d5ba27-c61b-4702-8906-9ad45688c51a","revision":"1"},"capture_id":"5e76b5b4-7e64-4ed6-8658-c950a60ef908","status":"accepted","artifact_refs":[{"id":"94393d03-ab53-48ad-bdb1-a72fea4de4a3","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"94393d03-ab53-48ad-bdb1-a72fea4de4a3","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_revoked_run_cannot_dispatch_workspace_tool

Contract point: A revoked Run cannot dispatch the registered workspace executor.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImFkOGU5M2QyMzUzYjJjMDYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDMsIm5iZiI6MTc4OTI2NjcwMiwiZXhwIjoxNzg5MjY3MDAzLCJqdGkiOiI3NGE3Yjg3Yy0wOGFlLTRiZDAtODIyMi1kMzI5NGMyYjMzZmIifQ.uYiGlRJi1Eh3YHn_SGVJurKJ0IteOmU69Mgsc7OIL-IZd-Z4z9U0jsjYsWgPY0LYqTgUX_QGfPdP0AT-gJftYAen6kqt8en_qUFjwo6nGmfr5otZdabM8QjMA4fvAAuF1N7VUxUR5JuWS-gfZoHATNCpnuX46laBbfOD3dxZXOX9l5GbQushLH2gVfpZ5iinK-uHGGXF69oXOMtp2AhiVrStFSux9zrodtb-KVmmI3I-YasRsQIUbCpAubyqQ_ty3pDTnEFjxFijhIC9SQ7xZfHTx3u_ygxuZ3DWCTA0U15VYjRHsIegShNslDfgZctKN1zBuEAF4kNgTs56wE9dnQ
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
x-request-id: 2b0603ec-18e3-499d-89e9-e99e3dfc2397

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"2b0603ec-18e3-499d-89e9-e99e3dfc2397","retryable":false,"details":{}}
```

## test_task_output_limit_is_cumulative_across_model_attempts

Contract point: The second response exceeds the remaining cumulative output allowance and is rejected without retained overflow.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImI2OWIxYjlmOWE0MmY2MTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDQsIm5iZiI6MTc4OTI2NjcwMywiZXhwIjoxNzg5MjY3MDA0LCJqdGkiOiI3ODVhYWM4MS1iMDQ0LTRiY2QtYjBlYi1hOWZmN2FjZmU4OTYifQ.sK2MK8yau6hwoqUzx0o3E31McpchD4z5b60DnRSkkXB70a-s3bjkYfChumZvHRSvbH6CpV1BuxVyRJRi5iiTmKR7O6UQ-ZShc1lKXKGcAwG7vHI3Q9o744BRMKWsym2h9ZjuqXpElW5z4-QI3ktmbVBL6OcqT-mByZV8eN3gSLzg3nC_UTueRhJA3ZV9qV08CCVBqsjK_I4rMqEY5Asi5pQf8Vd2PvBb-r_onedWnIJeeIoGnJ_90yxHBz68ySOjXYMWnvLoFFqpsQwOuQKbZWkNd1o6u6hMkhG-Ri16pqDMAMOsMhpLH08Yz7aD1zFH0DNwsn2ILpYh46IiPFP1Dw
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
x-request-id: 56dc5dcf-03aa-417c-8f9f-cb3f43a4392a
x-wuji-model-attempt-id: f5ac0000-dfd5-4a12-93d2-54765547fe43
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImI2OWIxYjlmOWE0MmY2MTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDQsIm5iZiI6MTc4OTI2NjcwMywiZXhwIjoxNzg5MjY3MDA0LCJqdGkiOiI3ODVhYWM4MS1iMDQ0LTRiY2QtYjBlYi1hOWZmN2FjZmU4OTYifQ.sK2MK8yau6hwoqUzx0o3E31McpchD4z5b60DnRSkkXB70a-s3bjkYfChumZvHRSvbH6CpV1BuxVyRJRi5iiTmKR7O6UQ-ZShc1lKXKGcAwG7vHI3Q9o744BRMKWsym2h9ZjuqXpElW5z4-QI3ktmbVBL6OcqT-mByZV8eN3gSLzg3nC_UTueRhJA3ZV9qV08CCVBqsjK_I4rMqEY5Asi5pQf8Vd2PvBb-r_onedWnIJeeIoGnJ_90yxHBz68ySOjXYMWnvLoFFqpsQwOuQKbZWkNd1o6u6hMkhG-Ri16pqDMAMOsMhpLH08Yz7aD1zFH0DNwsn2ILpYh46IiPFP1Dw
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
x-request-id: c66a741a-62c3-416a-ae58-4f57f1454ade

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"c66a741a-62c3-416a-ae58-4f57f1454ade","retryable":false,"details":{}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:59818/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59818
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: f5ac0000-dfd5-4a12-93d2-54765547fe43

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
POST http://127.0.0.1:59818/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:59818
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: a1f69a6a-b271-44c9-a405-d4e185e1eef4

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

Contract point: An unbound approval-required proposal remains pending and creates no ToolAttempt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjAwMTliMjI0NGI1Nzg5YmQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDUsIm5iZiI6MTc4OTI2NjcwNCwiZXhwIjoxNzg5MjY3MDA1LCJqdGkiOiJjMTg1NjVhNy0wZTg3LTRmMDgtOWViNi1hMTU3YTM5NzBmMmQifQ.uVTqW0UsRfplMblsNPJJ7X8igRgjy_spLUGi3FXyv0Hft-cWiQ03hxn4oKVpRSddh3wxhuYfqEncqUDMxNbb82P05VOkAvXZGSGx0WZZLKb5f_RH41kES40EQLq5phNQRFXEJtG9P1eirmraKQ1kiT2AGJYXBf00oQigNb69oRZAnZ7B5Ohm8fJC6XOdrzKZUMZo9rMt5Nqlg6uzpyCXx9NOPuS5xaySFq08bt2jlXbSmm4LnK20Oihsy_3pfiO3dN7i3vKgQelwMZ0gbgsMvmUrlufRJxhTT4zgbd7IQHhf_T4hkMl9hy8BG-HlUqFwHZzuJGmRMFUrunI_K9ZWlg
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
x-request-id: 891a7ac3-6466-422a-9408-c63083c62c31

{"tool_call_id":"9fd01820-eb07-4a1a-98b2-575821bd3c56","operation_id":"9fd01820-eb07-4a1a-98b2-575821bd3c56","tool_attempt_id":null,"status":"pending_approval","evidence_receipt":null,"result_ref":null,"reason_code":null}
```

## test_tool_operation_replay_conflict_and_new_call_id_control_execution

Contract point: A ToolCall replays by canonical identity, rejects changed arguments, and treats a new provider call ID as new work.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY3MDQ3NDk3MWI2YTNkMTAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDUsIm5iZiI6MTc4OTI2NjcwNCwiZXhwIjoxNzg5MjY3MDA1LCJqdGkiOiJjZjJkYTEwYy0xZWNmLTQyN2ItYjcyNC01Y2JiODQ5Yjk5YjUifQ.Oyxrhprjzs_vo_xjPU_2yVhGCM3-jcJJkeOi9-KfCOvMPJT_QsgkrKhQlclGIhPADO50UWB733eZOI2u7RCLJScNxhDqZg-GTMOv_TdxF9vqoWLykau6sMHzPd2ia0xXSjv-mnSLPojcJ7I5duz02nqDhjlxj0Tcwcg1hKrEzMcqEmdJdzjz2OyNeRrqCqdOpxC_gnjj9hBS-A9m1Ix6IvH8XE2EFWmfEcIoOWEJf6_NTythRm3ncFQjzp8Yhbze5tLDGEjFAjtgWdqppqx8X83uUsd_KlwR-udbF4NDyup9S3ePwp_9wAJjw3Oo7LYJ16Qxgc6_l6VAaikLzibOwg
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
x-request-id: 7dd48cfd-0738-4fee-8ce5-3b527dd4f9cb

{"tool_call_id":"2ca0c194-c7b0-4ef1-a0ef-521b363de453","operation_id":"2ca0c194-c7b0-4ef1-a0ef-521b363de453","tool_attempt_id":"9371109f-bf73-4009-90f8-2fae707680e5","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"63d18f32-353c-494b-a4f4-48eb3edb48fd","revision":"1"},"capture_id":"9371109f-bf73-4009-90f8-2fae707680e5","status":"accepted","artifact_refs":[{"id":"3f02e07c-24b4-44a1-adc9-c2b1e0c9221a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"3f02e07c-24b4-44a1-adc9-c2b1e0c9221a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY3MDQ3NDk3MWI2YTNkMTAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDUsIm5iZiI6MTc4OTI2NjcwNCwiZXhwIjoxNzg5MjY3MDA1LCJqdGkiOiJjZjJkYTEwYy0xZWNmLTQyN2ItYjcyNC01Y2JiODQ5Yjk5YjUifQ.Oyxrhprjzs_vo_xjPU_2yVhGCM3-jcJJkeOi9-KfCOvMPJT_QsgkrKhQlclGIhPADO50UWB733eZOI2u7RCLJScNxhDqZg-GTMOv_TdxF9vqoWLykau6sMHzPd2ia0xXSjv-mnSLPojcJ7I5duz02nqDhjlxj0Tcwcg1hKrEzMcqEmdJdzjz2OyNeRrqCqdOpxC_gnjj9hBS-A9m1Ix6IvH8XE2EFWmfEcIoOWEJf6_NTythRm3ncFQjzp8Yhbze5tLDGEjFAjtgWdqppqx8X83uUsd_KlwR-udbF4NDyup9S3ePwp_9wAJjw3Oo7LYJ16Qxgc6_l6VAaikLzibOwg
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
x-request-id: 38471f27-6257-4659-8bf4-57974e9e2646

{"tool_call_id":"2ca0c194-c7b0-4ef1-a0ef-521b363de453","operation_id":"2ca0c194-c7b0-4ef1-a0ef-521b363de453","tool_attempt_id":"9371109f-bf73-4009-90f8-2fae707680e5","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"63d18f32-353c-494b-a4f4-48eb3edb48fd","revision":"1"},"capture_id":"9371109f-bf73-4009-90f8-2fae707680e5","status":"accepted","artifact_refs":[{"id":"3f02e07c-24b4-44a1-adc9-c2b1e0c9221a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"3f02e07c-24b4-44a1-adc9-c2b1e0c9221a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY3MDQ3NDk3MWI2YTNkMTAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDUsIm5iZiI6MTc4OTI2NjcwNCwiZXhwIjoxNzg5MjY3MDA1LCJqdGkiOiJjZjJkYTEwYy0xZWNmLTQyN2ItYjcyNC01Y2JiODQ5Yjk5YjUifQ.Oyxrhprjzs_vo_xjPU_2yVhGCM3-jcJJkeOi9-KfCOvMPJT_QsgkrKhQlclGIhPADO50UWB733eZOI2u7RCLJScNxhDqZg-GTMOv_TdxF9vqoWLykau6sMHzPd2ia0xXSjv-mnSLPojcJ7I5duz02nqDhjlxj0Tcwcg1hKrEzMcqEmdJdzjz2OyNeRrqCqdOpxC_gnjj9hBS-A9m1Ix6IvH8XE2EFWmfEcIoOWEJf6_NTythRm3ncFQjzp8Yhbze5tLDGEjFAjtgWdqppqx8X83uUsd_KlwR-udbF4NDyup9S3ePwp_9wAJjw3Oo7LYJ16Qxgc6_l6VAaikLzibOwg
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
x-request-id: 664b2cb3-5f1a-477c-a9ef-4cd48f2e7892

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"664b2cb3-5f1a-477c-a9ef-4cd48f2e7892","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY3MDQ3NDk3MWI2YTNkMTAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDUsIm5iZiI6MTc4OTI2NjcwNCwiZXhwIjoxNzg5MjY3MDA1LCJqdGkiOiJjZjJkYTEwYy0xZWNmLTQyN2ItYjcyNC01Y2JiODQ5Yjk5YjUifQ.Oyxrhprjzs_vo_xjPU_2yVhGCM3-jcJJkeOi9-KfCOvMPJT_QsgkrKhQlclGIhPADO50UWB733eZOI2u7RCLJScNxhDqZg-GTMOv_TdxF9vqoWLykau6sMHzPd2ia0xXSjv-mnSLPojcJ7I5duz02nqDhjlxj0Tcwcg1hKrEzMcqEmdJdzjz2OyNeRrqCqdOpxC_gnjj9hBS-A9m1Ix6IvH8XE2EFWmfEcIoOWEJf6_NTythRm3ncFQjzp8Yhbze5tLDGEjFAjtgWdqppqx8X83uUsd_KlwR-udbF4NDyup9S3ePwp_9wAJjw3Oo7LYJ16Qxgc6_l6VAaikLzibOwg
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
x-request-id: 7dee0896-7d24-4127-9620-25d6392a0cb4

{"tool_call_id":"1f6eb42d-0bd9-4b0e-939f-6fb2eadf1d51","operation_id":"1f6eb42d-0bd9-4b0e-939f-6fb2eadf1d51","tool_attempt_id":"1f8cb8dc-4fb6-42f7-a8ce-f4ebcd6c031e","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"806459a5-7182-4e40-ba78-215fc5f74699","revision":"1"},"capture_id":"1f8cb8dc-4fb6-42f7-a8ce-f4ebcd6c031e","status":"accepted","artifact_refs":[{"id":"22623e9b-ed1b-4ef7-b1b1-56d34c0656b8","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"22623e9b-ed1b-4ef7-b1b1-56d34c0656b8","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_missing_mcp_type_and_revoked_function_adapter_do_not_execute

Contract point: Missing official MCP types fail closed; the function adapter observes server-side tool revocation. No HTTP route is involved.

HTTP packet: not applicable. This test calls the production function/MCP normalization methods directly; the official `mcp.types` package is absent and the adapter fails closed before transport.

## test_started_tool_can_settle_after_revocation_but_new_work_is_rejected

Contract point: An already-started tool settles through trusted receipt handling after revocation while a new operation is rejected.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBhNmE4YTNmODA3MzA3MDAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDcsIm5iZiI6MTc4OTI2NjcwNiwiZXhwIjoxNzg5MjY3MDA3LCJqdGkiOiIxMDgyYmI0Yy0yZTkxLTQ4MTItOTliMi05ZGJlNDcwZWJiNjYifQ.T1lQc0PTXhwjYpS1MsKEVAqBMXkNse6OtZetQctkntHOBtnL8eFCYe6Ne2RMzA2M4vqpDT_2LkHBMTBKNC5gmNT9i-PUZKiEVYZ1MgvsrslgZfD4EU0wYgYaEVK_7yUXIh-nezVT5_hnhIMsD8HsirdTTJIuukCQGb-whSV-W_SKGWeEhj79gxYp_oCpRaqp6a2-hjr7Ye3gTWUlj9kMV9IojrhYVjh5gBqSvFi5VK4gcbhpslFkKc-VuMaoyuwx9tlwk1U-GeNUzWGBApys_BBdxc2MnSHZdoviA843Wp0T2qts74D_KLqHx3dj5eoOcnqXzewls82mo6F3xhGoVA
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
x-request-id: 5c015133-53e0-4632-819c-e6baef1732e8

{"tool_call_id":"90765453-b078-4615-9004-638ca50bb192","operation_id":"90765453-b078-4615-9004-638ca50bb192","tool_attempt_id":"ebb2f0ed-1b11-43dd-a501-8eca3b56e470","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"4a2eace4-dff1-4da4-b75f-26af9cf10ed7","revision":"1"},"capture_id":"ebb2f0ed-1b11-43dd-a501-8eca3b56e470","status":"accepted","artifact_refs":[{"id":"759d40a8-31b4-40da-bd68-2e7a1cbe1700","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"759d40a8-31b4-40da-bd68-2e7a1cbe1700","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/tool-calls/90765453-b078-4615-9004-638ca50bb192
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBhNmE4YTNmODA3MzA3MDAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDcsIm5iZiI6MTc4OTI2NjcwNiwiZXhwIjoxNzg5MjY3MDA3LCJqdGkiOiIxMDgyYmI0Yy0yZTkxLTQ4MTItOTliMi05ZGJlNDcwZWJiNjYifQ.T1lQc0PTXhwjYpS1MsKEVAqBMXkNse6OtZetQctkntHOBtnL8eFCYe6Ne2RMzA2M4vqpDT_2LkHBMTBKNC5gmNT9i-PUZKiEVYZ1MgvsrslgZfD4EU0wYgYaEVK_7yUXIh-nezVT5_hnhIMsD8HsirdTTJIuukCQGb-whSV-W_SKGWeEhj79gxYp_oCpRaqp6a2-hjr7Ye3gTWUlj9kMV9IojrhYVjh5gBqSvFi5VK4gcbhpslFkKc-VuMaoyuwx9tlwk1U-GeNUzWGBApys_BBdxc2MnSHZdoviA843Wp0T2qts74D_KLqHx3dj5eoOcnqXzewls82mo6F3xhGoVA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 894122d4-ccf8-42b6-a666-c600389323cd

{"tool_call_id":"90765453-b078-4615-9004-638ca50bb192","operation_id":"90765453-b078-4615-9004-638ca50bb192","tool_attempt_id":"ebb2f0ed-1b11-43dd-a501-8eca3b56e470","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"4a2eace4-dff1-4da4-b75f-26af9cf10ed7","revision":"1"},"capture_id":"ebb2f0ed-1b11-43dd-a501-8eca3b56e470","status":"accepted","artifact_refs":[{"id":"759d40a8-31b4-40da-bd68-2e7a1cbe1700","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"759d40a8-31b4-40da-bd68-2e7a1cbe1700","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBhNmE4YTNmODA3MzA3MDAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNjY3MDcsIm5iZiI6MTc4OTI2NjcwNiwiZXhwIjoxNzg5MjY3MDA3LCJqdGkiOiIxMDgyYmI0Yy0yZTkxLTQ4MTItOTliMi05ZGJlNDcwZWJiNjYifQ.T1lQc0PTXhwjYpS1MsKEVAqBMXkNse6OtZetQctkntHOBtnL8eFCYe6Ne2RMzA2M4vqpDT_2LkHBMTBKNC5gmNT9i-PUZKiEVYZ1MgvsrslgZfD4EU0wYgYaEVK_7yUXIh-nezVT5_hnhIMsD8HsirdTTJIuukCQGb-whSV-W_SKGWeEhj79gxYp_oCpRaqp6a2-hjr7Ye3gTWUlj9kMV9IojrhYVjh5gBqSvFi5VK4gcbhpslFkKc-VuMaoyuwx9tlwk1U-GeNUzWGBApys_BBdxc2MnSHZdoviA843Wp0T2qts74D_KLqHx3dj5eoOcnqXzewls82mo6F3xhGoVA
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
x-request-id: 128772e2-968b-466d-95db-34c86a7a6f84

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"128772e2-968b-466d-95db-34c86a7a6f84","retryable":false,"details":{}}
```
