# P06 complete HTTP reproduction packets

P06 base: `f32678d5662965f44b32863e8ecdf306db676ffd`; fixes: `67a8030e7c6a7c1cf767aa20a60fd6bfec5fe5e4`, `a9a768ced250ad7d80d7bf54f5777b9782550cb5`, `8a3a44d81bab8d4abd8292359b93495f80e7c083`; migration: `vnext_0008_p06_admission_hardening`.
All bearer tokens and keys below are synthetic isolated test values. Packets are decoded verbatim from final JSONL captures and bodies are not truncated.

## test_current_run_model_gate_forwards_native_and_records_attempt

Contract point: Signed Run admission, native response, private Task key and durable receipt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjI4MmE5NGYxZGMwYmEzNGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MTcsIm5iZiI6MTc4OTI3MDQxNiwiZXhwIjoxNzg5MjcwNzE3LCJqdGkiOiJkZjRkMDdiMC1kMDA0LTRlZWUtOTNlYS02OWMwYmViYzFjOGMifQ.V1yfCHtf8-WJUoRrJbejLf97PxOiYxKVJz63UjOXPPfVMt1Ju89_yyPpJ-vOZjlio_Py4L9Kca3qsUBjMUfLMvtvZam8SiF_A-D4CBKx8QEmGjVR1xm7Lib6-17IwaoG924z426zk8iE6m797YVBvGPP3pIjOSgGbUhbash8d1bqZGsEvudlTA_E4cEkIAG3qpQ-4qJyxI1E-sSbOVhT65idn9vrzFW-R0_n6hmeszRQsEQSamP4VCnwUmOm41hVtbKDHtmSFisgolg37XK43c_8aD7c8kHrh2md9hbDoYc6kfI8uuwHA0p9eTeBEdONtzCbpgYNQYVwk42SBzRK3A
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
x-request-id: ba86c527-ef08-46b7-932d-ba0039362512
x-wuji-model-attempt-id: f608830c-3e55-4995-a20f-559b8963eb40
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/f608830c-3e55-4995-a20f-559b8963eb40
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjI4MmE5NGYxZGMwYmEzNGIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MTcsIm5iZiI6MTc4OTI3MDQxNiwiZXhwIjoxNzg5MjcwNzE3LCJqdGkiOiJkZjRkMDdiMC1kMDA0LTRlZWUtOTNlYS02OWMwYmViYzFjOGMifQ.V1yfCHtf8-WJUoRrJbejLf97PxOiYxKVJz63UjOXPPfVMt1Ju89_yyPpJ-vOZjlio_Py4L9Kca3qsUBjMUfLMvtvZam8SiF_A-D4CBKx8QEmGjVR1xm7Lib6-17IwaoG924z426zk8iE6m797YVBvGPP3pIjOSgGbUhbash8d1bqZGsEvudlTA_E4cEkIAG3qpQ-4qJyxI1E-sSbOVhT65idn9vrzFW-R0_n6hmeszRQsEQSamP4VCnwUmOm41hVtbKDHtmSFisgolg37XK43c_8aD7c8kHrh2md9hbDoYc6kfI8uuwHA0p9eTeBEdONtzCbpgYNQYVwk42SBzRK3A
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 544
content-type: application/json
x-request-id: 30413d96-d9b1-4b6e-a0a1-8303d3a5c8b0

{"model_attempt_id":"f608830c-3e55-4995-a20f-559b8963eb40","input_digest":"57d0d5d1f73d05a69fef3b3d9d68088f4408bde81680c5a37b2008cba4c46149","logical_request_id":"model-request-current-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"complete","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":true,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"377","retained_bytes":"377","forwarded_bytes":"377","output_bytes":"377"}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51422/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51422
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: f608830c-3e55-4995-a20f-559b8963eb40

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImMyNDBkNDA2MmQxOTc3NzYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MTgsIm5iZiI6MTc4OTI3MDQxNywiZXhwIjoxNzg5MjcwNzE4LCJqdGkiOiJlZTBkNTJhZC04OTY3LTRmZDMtOGI1MC00ZGI0ZGNlNzJmZDQifQ.jKFyQtz5I7xfIDwRjEjMD14F77h9qqTKxoeLad6J1dCIQt-MNhKIqXQOyfPk7-i4wRDqaPAhbTDgoshBt3rmyeDogxFCUAFe6aFqt0y-XssRGuJZw4B1WJtzKjKH4wDq0bE0aPWWbDPDY4oKfYIGYfYvP228goFehy0MHUCOUpdze1RuI0F-jXX5pO9lmt8xol9_B5kJ9Qc10gEgE8-bw_far5GDUgUz8Z3u2yp4Qq0PFmChkvst7-ngPJhhR8Y8P6V45WXFd7TkKYn-b1d-gZQK9CoZaNPopmX4M1MWYTBsGc1_M272nyYARtdRVZ0LTEJeo6acssAMaKZNy6fWHw
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
x-request-id: ce149a13-ba32-4e14-ba23-f06c7e36c5c4

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"ce149a13-ba32-4e14-ba23-f06c7e36c5c4","retryable":false,"details":{}}
```

## test_p05_pause_makes_bound_run_identity_stale

Contract point: P05 pause invalidates an otherwise valid Run binding.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImFlODVjZWZmMzAzZGQ5NTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MTksIm5iZiI6MTc4OTI3MDQxOCwiZXhwIjoxNzg5MjcwNzE5LCJqdGkiOiIzOTY1OWY1Mi04NzNjLTRkYzQtYTI0YS1lNDE4OWRhMTNjMDQifQ.ES8Y_GCbUD6ODbV8Nnze7SGciiBeJhMgbV0S0EN9vV5JJbOub77BgotNappr51rL4LQmifWIENKF_wfYIQmW5ZGkGgfp8HZB7GkuuIyS9M2ZuTWlQXiXo2j6IAc3LkEmZ3KVN_jEu16JobsBtQF97IwvTlBLeAvh0RKFz6IRfiXoKKQxLgfLNpUPUUcEJ6nI-A_bkNQvur0OhDt-mx8j0_f8d-5v4NCpuZBsvjJ3wJ9TDQ12kNTJJKSR3txmKwK0VJy8BumshIo1hKCE--GIJqfRtfYZVO4f6g3KnHqdlMf0a4TU37ulx1TlrKUud8CPloEtuNtTlsvL5vK5FdRiRg
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
x-request-id: 55d5eda7-dc65-407c-8e47-0adc5a4f359c

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"55d5eda7-dc65-407c-8e47-0adc5a4f359c","retryable":false,"details":{}}
```

## test_model_request_replay_conflict_and_new_id_have_distinct_attempts

Contract point: Same request ID replays, changed digest conflicts, new ID creates a new inference.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkxMTExYTM3ZjZiOTczY2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjAsIm5iZiI6MTc4OTI3MDQxOSwiZXhwIjoxNzg5MjcwNzIwLCJqdGkiOiIwYmJiZTBhNi1mYTZlLTQ1ZWEtYWFlYS02NmUwMmEyMDU4YjEifQ.PIEhxrnoGmiK8Hn3Nnlb9scaD1muo5TyTbeDDWlFyySNGZqSvdc5aG40Tf9ICFJc5GwBNJBFPoX2JWRWaQRUbR57vp27ONnEMaeFbTPlAkqXsrX5E2vaSNYYna8jYS_GLvrxdqMnFpoIZGnhRUAS-QNQ2Sk9ktga8-_HwwEHnTkW41cObu11D_kWazyDeUBHQ5JvK24doWo6Ke8wJ9f5srRep2kYRRitAxsfvTdMdaV19ei9lPikhk3abkAczfZWRBT0ASraVLe7w8MFZbETsBBe-01cp1oJpHJ5ZaMmzT2fAI4qkeDQd5ScbjWGggt-bdqfZoe_FN8HibkGqj6q5w
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
x-request-id: 340ef0c7-1336-4391-b90e-6f37636084f4
x-wuji-model-attempt-id: c7a0d403-328f-45f4-a60d-38edfcb6e14e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkxMTExYTM3ZjZiOTczY2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjAsIm5iZiI6MTc4OTI3MDQxOSwiZXhwIjoxNzg5MjcwNzIwLCJqdGkiOiIwYmJiZTBhNi1mYTZlLTQ1ZWEtYWFlYS02NmUwMmEyMDU4YjEifQ.PIEhxrnoGmiK8Hn3Nnlb9scaD1muo5TyTbeDDWlFyySNGZqSvdc5aG40Tf9ICFJc5GwBNJBFPoX2JWRWaQRUbR57vp27ONnEMaeFbTPlAkqXsrX5E2vaSNYYna8jYS_GLvrxdqMnFpoIZGnhRUAS-QNQ2Sk9ktga8-_HwwEHnTkW41cObu11D_kWazyDeUBHQ5JvK24doWo6Ke8wJ9f5srRep2kYRRitAxsfvTdMdaV19ei9lPikhk3abkAczfZWRBT0ASraVLe7w8MFZbETsBBe-01cp1oJpHJ5ZaMmzT2fAI4qkeDQd5ScbjWGggt-bdqfZoe_FN8HibkGqj6q5w
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
x-request-id: 4266541a-1687-4653-a4a0-b2bdb945c8f8
x-wuji-model-attempt-id: c7a0d403-328f-45f4-a60d-38edfcb6e14e
x-wuji-replayed: true

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkxMTExYTM3ZjZiOTczY2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjAsIm5iZiI6MTc4OTI3MDQxOSwiZXhwIjoxNzg5MjcwNzIwLCJqdGkiOiIwYmJiZTBhNi1mYTZlLTQ1ZWEtYWFlYS02NmUwMmEyMDU4YjEifQ.PIEhxrnoGmiK8Hn3Nnlb9scaD1muo5TyTbeDDWlFyySNGZqSvdc5aG40Tf9ICFJc5GwBNJBFPoX2JWRWaQRUbR57vp27ONnEMaeFbTPlAkqXsrX5E2vaSNYYna8jYS_GLvrxdqMnFpoIZGnhRUAS-QNQ2Sk9ktga8-_HwwEHnTkW41cObu11D_kWazyDeUBHQ5JvK24doWo6Ke8wJ9f5srRep2kYRRitAxsfvTdMdaV19ei9lPikhk3abkAczfZWRBT0ASraVLe7w8MFZbETsBBe-01cp1oJpHJ5ZaMmzT2fAI4qkeDQd5ScbjWGggt-bdqfZoe_FN8HibkGqj6q5w
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
x-request-id: 514fefdd-9fa5-4487-8894-890d8f51ce14

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"514fefdd-9fa5-4487-8894-890d8f51ce14","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkxMTExYTM3ZjZiOTczY2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjAsIm5iZiI6MTc4OTI3MDQxOSwiZXhwIjoxNzg5MjcwNzIwLCJqdGkiOiIwYmJiZTBhNi1mYTZlLTQ1ZWEtYWFlYS02NmUwMmEyMDU4YjEifQ.PIEhxrnoGmiK8Hn3Nnlb9scaD1muo5TyTbeDDWlFyySNGZqSvdc5aG40Tf9ICFJc5GwBNJBFPoX2JWRWaQRUbR57vp27ONnEMaeFbTPlAkqXsrX5E2vaSNYYna8jYS_GLvrxdqMnFpoIZGnhRUAS-QNQ2Sk9ktga8-_HwwEHnTkW41cObu11D_kWazyDeUBHQ5JvK24doWo6Ke8wJ9f5srRep2kYRRitAxsfvTdMdaV19ei9lPikhk3abkAczfZWRBT0ASraVLe7w8MFZbETsBBe-01cp1oJpHJ5ZaMmzT2fAI4qkeDQd5ScbjWGggt-bdqfZoe_FN8HibkGqj6q5w
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
x-request-id: 23bb6d7a-fa4c-485c-8472-c03d0cd1dfb6
x-wuji-model-attempt-id: 8769e96b-4023-4c6c-8845-fb6ce3fc9fb2
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51431/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51431
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: c7a0d403-328f-45f4-a60d-38edfcb6e14e

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
POST http://127.0.0.1:51431/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51431
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 8769e96b-4023-4c6c-8845-fb6ce3fc9fb2

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkyNGRmZDE3MjgwYTAwZTUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsid29ya2VyIl0sImlhdCI6MTc4OTI3MDQyMiwibmJmIjoxNzg5MjcwNDIxLCJleHAiOjE3ODkyNzA3MjIsImp0aSI6IjhjOTI4MjAzLWNlZWItNDlhOC1hMWNkLWMzYzYzMjY1OGRiNyJ9.uBvfPfEDZYh-d8hnE2ubVrq-PJSnUSkkllIzh0j4gkooNCjJswiDF74YD-hbSSDxGOzEzxtkgep7J_ynx-b_gk3tSGY6r96TQF1qBv_xKQJtKEGbtBgfYovQ1UzWGbfkwk2bOjMVo85RNO9nqoAYWC26oU5yAJqtFbsDKEQMCv0n4D6yJRooMEgsvyjnloPHGwA0cF3Ym8Ske8AuUM3mAE6xCgGpwSYWB9dxXgqynE3YnaTDM85PqFp4cIkCHiGSlfrNLy1bnDxxs6Gbc7ZRtvoWf79YBZdgY8vs-JtBOGVWEuVDcJgLztNnn8zSeR89iUO_KIv1TYioq1JUSBs3zA
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
x-request-id: 43311935-6f0e-4037-a6e3-129dbe7df183

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"43311935-6f0e-4037-a6e3-129dbe7df183","retryable":false,"details":{}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjkyNGRmZDE3MjgwYTAwZTUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjEsIm5iZiI6MTc4OTI3MDQyMCwiZXhwIjoxNzg5MjcwNzIxLCJqdGkiOiI2OGJkNzNiOC0yMTc5LTRmMTQtYWIzZS1jMjY4NDNjM2E3MDgifQ.RCkInJHIYe57AptwbCBfIZKzJ36vHLZGrsy935jsM06gGKsirYMSjn_CeHwB3_sb41G7zXs_GV5MIYYdPjS6hxJuboPJukskqtjr_E3wPUCCzP9THb9IF47v-qbKn212erGtfRcne56mr59HRLsTwepxLur-3rpwi8NmGDRR6QTkOJl8Rm8u-7C-uTiZ4GIL_n3nHyb5vVRjJiQf2ilNuYTxYLGZtlge7r4YtaB9arUsjZsSfnD5X3PtIlXtG_Fzm4ObDcYHjbdT0DAND7DjeElQdJ7jp9zrWo40nmV56IGE_Vs54OrAN8ar8ZU7NhGVMHsUpEEvb0Spat-m3DWzgw
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
x-request-id: 204171cd-e7be-435f-8396-e91cf7c2a280
x-wuji-model-attempt-id: 7ce37bcd-2d37-4bc5-9d17-6130aa5f19af
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51436/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51436
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 7ce37bcd-2d37-4bc5-9d17-6130aa5f19af

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk4MTk1MWM4ODk4Mjg4NTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjMsIm5iZiI6MTc4OTI3MDQyMiwiZXhwIjoxNzg5MjcwNzIzLCJqdGkiOiIwODI1MzUzNS04NTcyLTQ0MzQtYWNlZS0zNmFhN2ExZDhmNjEifQ.NfCaJjJCUnX5a2t7aipYtrfDF7qVe0ps3JS4-e90E4S8nJneNKdTDsdOEHDNLOB3vkL9jJIUHvdfgN61_HO-tzyBuzVQomb4SwYv5-JvUP31RpyRRHdIR6PzOqBQve1dzkZVtgDvxxMOTZOcmmd-XOpqCCO-IKzBK6IFsftF1pp1egxUsXE9IPRq2-h-lE-aYgMBcJAmiemyHqyb0WEkYqbvF_8xAZGRb2tZYI3g3tfr5bPoGVunuNCr1_fU31QWNf5BRzENDUEQLDb2j_BTHBo16suUIbUASBW-3d_YKgFCvtn4C0maHM2RyMkn7Q08Mx5vjUm93BFQHTx5ZVm1Vg
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
x-request-id: 57e06728-f2d7-418f-b146-03ced3f71645
x-wuji-model-attempt-id: aeed2a70-ed2d-4dd9-b423-a9c5b32465ce
x-wuji-replayed: false

data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk","created":1,"model":"fixture-model","choices":[{"index":0,"delta":{"role":"assistant","content":"partial"},"finish_reason":null}]}


```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/aeed2a70-ed2d-4dd9-b423-a9c5b32465ce
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk4MTk1MWM4ODk4Mjg4NTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjMsIm5iZiI6MTc4OTI3MDQyMiwiZXhwIjoxNzg5MjcwNzIzLCJqdGkiOiIwODI1MzUzNS04NTcyLTQ0MzQtYWNlZS0zNmFhN2ExZDhmNjEifQ.NfCaJjJCUnX5a2t7aipYtrfDF7qVe0ps3JS4-e90E4S8nJneNKdTDsdOEHDNLOB3vkL9jJIUHvdfgN61_HO-tzyBuzVQomb4SwYv5-JvUP31RpyRRHdIR6PzOqBQve1dzkZVtgDvxxMOTZOcmmd-XOpqCCO-IKzBK6IFsftF1pp1egxUsXE9IPRq2-h-lE-aYgMBcJAmiemyHqyb0WEkYqbvF_8xAZGRb2tZYI3g3tfr5bPoGVunuNCr1_fU31QWNf5BRzENDUEQLDb2j_BTHBo16suUIbUASBW-3d_YKgFCvtn4C0maHM2RyMkn7Q08Mx5vjUm93BFQHTx5ZVm1Vg
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 536
content-type: application/json
x-request-id: 91d4a6db-da55-4f44-9642-517b86ed7e07

{"model_attempt_id":"aeed2a70-ed2d-4dd9-b423-a9c5b32465ce","input_digest":"cc712b587519e826c7e1e943cc65088a98dc0d8cd3d981eda39c2aa8c5a620ad","logical_request_id":"model-partial-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"partial","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":false,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"200","retained_bytes":"200","forwarded_bytes":"200","output_bytes":"200"}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk4MTk1MWM4ODk4Mjg4NTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjMsIm5iZiI6MTc4OTI3MDQyMiwiZXhwIjoxNzg5MjcwNzIzLCJqdGkiOiIwODI1MzUzNS04NTcyLTQ0MzQtYWNlZS0zNmFhN2ExZDhmNjEifQ.NfCaJjJCUnX5a2t7aipYtrfDF7qVe0ps3JS4-e90E4S8nJneNKdTDsdOEHDNLOB3vkL9jJIUHvdfgN61_HO-tzyBuzVQomb4SwYv5-JvUP31RpyRRHdIR6PzOqBQve1dzkZVtgDvxxMOTZOcmmd-XOpqCCO-IKzBK6IFsftF1pp1egxUsXE9IPRq2-h-lE-aYgMBcJAmiemyHqyb0WEkYqbvF_8xAZGRb2tZYI3g3tfr5bPoGVunuNCr1_fU31QWNf5BRzENDUEQLDb2j_BTHBo16suUIbUASBW-3d_YKgFCvtn4C0maHM2RyMkn7Q08Mx5vjUm93BFQHTx5ZVm1Vg
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
x-request-id: eeefc4e6-f3d8-4947-ad2a-b4ac4ba2e5ed
x-wuji-model-attempt-id: dc55bd7d-5a59-49f4-9e2b-5323b211aafc
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51438/v1/chat/completions
accept: text/event-stream
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 213
content-type: application/json
host: 127.0.0.1:51438
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: aeed2a70-ed2d-4dd9-b423-a9c5b32465ce

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
POST http://127.0.0.1:51438/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51438
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: dc55bd7d-5a59-49f4-9e2b-5323b211aafc

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImI0N2FmNzE0NzE2N2VjYmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjQsIm5iZiI6MTc4OTI3MDQyMywiZXhwIjoxNzg5MjcwNzI0LCJqdGkiOiIzNGY2ZjdjYS0zZWJmLTRmZDktYTZjNC03NjdmZjgxZGE1NTIifQ.ey9nWivKJiioU8B7-CYIxBoDquIGn6TwKLl5VIjgYlK4_hk3ikhKhnBetiV8yIRAzwkZEyVkhoGMLB8Ok2bFrFspO-MjmfEBNQvrqBEZo89BIvj02vbfNZtClON61pcihNEU6Q6PrVF_PT9_7YI1SRTr0QRDDnyNPRwNfJbylHoSW3cUrRL0ReSzSiJSF-DJertqXDJaA8UbtADhjQW1BI9cF0xl4xx14iuqEkRxf_2L0oqNiamy1-uVX-lNiCtyQ0zguesnaDsZ2Lb0zFQRVtV3imDaPV1AolZomF3jHeI1mNlxgjkOUu59BuH3GYG7WACtaYJo5dYO_FxXcmCG5Q
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
x-request-id: 29b773dc-e17c-4fe3-b046-14ab7766a0d5

{"tool_call_id":"72fb16fd-0f98-40e1-bc63-ff5cd0463579","operation_id":"72fb16fd-0f98-40e1-bc63-ff5cd0463579","tool_attempt_id":"46acc071-83e5-4794-9792-1c3f79da1214","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"ad43b527-72f0-4a66-8e8b-7a74820098d3","revision":"1"},"capture_id":"46acc071-83e5-4794-9792-1c3f79da1214","status":"accepted","artifact_refs":[{"id":"67e1e9e5-0e4c-43b3-b72a-160a6ce4398b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"67e1e9e5-0e4c-43b3-b72a-160a6ce4398b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/67e1e9e5-0e4c-43b3-b72a-160a6ce4398b/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImI0N2FmNzE0NzE2N2VjYmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjQsIm5iZiI6MTc4OTI3MDQyMywiZXhwIjoxNzg5MjcwNzI0LCJqdGkiOiIzNGY2ZjdjYS0zZWJmLTRmZDktYTZjNC03NjdmZjgxZGE1NTIifQ.ey9nWivKJiioU8B7-CYIxBoDquIGn6TwKLl5VIjgYlK4_hk3ikhKhnBetiV8yIRAzwkZEyVkhoGMLB8Ok2bFrFspO-MjmfEBNQvrqBEZo89BIvj02vbfNZtClON61pcihNEU6Q6PrVF_PT9_7YI1SRTr0QRDDnyNPRwNfJbylHoSW3cUrRL0ReSzSiJSF-DJertqXDJaA8UbtADhjQW1BI9cF0xl4xx14iuqEkRxf_2L0oqNiamy1-uVX-lNiCtyQ0zguesnaDsZ2Lb0zFQRVtV3imDaPV1AolZomF3jHeI1mNlxgjkOUu59BuH3GYG7WACtaYJo5dYO_FxXcmCG5Q
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
x-request-id: 82f2fe98-0190-4919-b295-3d3f14032f4a

fixture-version=17

```

### Inbound ASGI exchange 3

Request:

```http
GET http://testserver/internal/v2/tool-calls/72fb16fd-0f98-40e1-bc63-ff5cd0463579
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImI0N2FmNzE0NzE2N2VjYmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjQsIm5iZiI6MTc4OTI3MDQyMywiZXhwIjoxNzg5MjcwNzI0LCJqdGkiOiIzNGY2ZjdjYS0zZWJmLTRmZDktYTZjNC03NjdmZjgxZGE1NTIifQ.ey9nWivKJiioU8B7-CYIxBoDquIGn6TwKLl5VIjgYlK4_hk3ikhKhnBetiV8yIRAzwkZEyVkhoGMLB8Ok2bFrFspO-MjmfEBNQvrqBEZo89BIvj02vbfNZtClON61pcihNEU6Q6PrVF_PT9_7YI1SRTr0QRDDnyNPRwNfJbylHoSW3cUrRL0ReSzSiJSF-DJertqXDJaA8UbtADhjQW1BI9cF0xl4xx14iuqEkRxf_2L0oqNiamy1-uVX-lNiCtyQ0zguesnaDsZ2Lb0zFQRVtV3imDaPV1AolZomF3jHeI1mNlxgjkOUu59BuH3GYG7WACtaYJo5dYO_FxXcmCG5Q
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: f5a8fe50-2bf2-47c3-9b91-71aacaa491db

{"tool_call_id":"72fb16fd-0f98-40e1-bc63-ff5cd0463579","operation_id":"72fb16fd-0f98-40e1-bc63-ff5cd0463579","tool_attempt_id":"46acc071-83e5-4794-9792-1c3f79da1214","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"ad43b527-72f0-4a66-8e8b-7a74820098d3","revision":"1"},"capture_id":"46acc071-83e5-4794-9792-1c3f79da1214","status":"accepted","artifact_refs":[{"id":"67e1e9e5-0e4c-43b3-b72a-160a6ce4398b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"67e1e9e5-0e4c-43b3-b72a-160a6ce4398b","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_revoked_run_cannot_dispatch_workspace_tool

Contract point: Revoked Run creates no ToolAttempt or receiver execution.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY3OWNjNmI3N2MzNjM1N2UifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjUsIm5iZiI6MTc4OTI3MDQyNCwiZXhwIjoxNzg5MjcwNzI1LCJqdGkiOiIxNTY5Y2VlOS02MjhhLTQ0NDctYmY1MS0xMzU2YzFkOWFiNzAifQ.RupxLedJKmY-21o5y37Cyx-Jzbk6AcJXF_0B9Zs_N6aeVpTPiR-MRc0FZcwWHiz7BKjIY8GdyNs_0cf_4FRQ4fYiDnfNvonh8ph9D6EFRdVePiYbwOnd1pn6UTUATDL7fA1anXtCIMe4S_I4unz05yvQ_ftX96xWxU4vJNOWvf2jm5CDmDdZC2s1lfm0bGu2NAzn0hQX96PC_LrnB1gzhoUJLlJYwmYBb0gw1RZv5HCCK5GDrVuF2E1rjgA2BmiCPNICWr0XtviZQ_n7uXN__FJEjp1vq176d7mKMIP1J-vNIPzyhYkb3ioNfBuQHaoOBmqt2Qvy7Q2QSfvWRBa43g
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
x-request-id: bfe8a64f-c872-4797-932d-13b2bdb12944

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"bfe8a64f-c872-4797-932d-13b2bdb12944","retryable":false,"details":{}}
```

## test_task_output_limit_is_cumulative_across_model_attempts

Contract point: Task output allowance remains cumulative across model attempts.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjU2NzI1ODE2ZGRjOTdhYmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjcsIm5iZiI6MTc4OTI3MDQyNiwiZXhwIjoxNzg5MjcwNzI3LCJqdGkiOiI3M2Q1NWM3Ni1mNmZmLTQ0NDItOTU0NS00ZjRmZTBkNzBlNTcifQ.eyojBO-X3KWZy_D6NmIrVwcuL6VDmDvDcs1MMFbc5tOG2cWSQ4Up2OWhvANOD0ajUAmx-DOvHuF_XNVnHXsKpmhyj7t-3EMmorfE0KFumNOxcputOF2f8ZnpPE48trSNv_IBga-M9TEB821TAv9K2-_McqG2D474WeJSvv7DA_dOQvhzZLqqZhclG6JIyCywQM0uRG0YbkxKzXXBhAeiyvTNxHo7dMs-LqCJmxvjLcwug8C4Ujysgx1jDlRLOVayRsPPfiOwzX980FSHJSmU1MX8bv8j1F6Na2314Ildy6A7ddHu5ssrLCfm1BHjPAKtgvulXrE8fggDzsmBfIqwkQ
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
x-request-id: 1f187616-80f1-4b3e-9e09-2a1712acc30e
x-wuji-model-attempt-id: efc10e13-cfaa-4a9c-a20e-6e61e7781193
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjU2NzI1ODE2ZGRjOTdhYmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjcsIm5iZiI6MTc4OTI3MDQyNiwiZXhwIjoxNzg5MjcwNzI3LCJqdGkiOiI3M2Q1NWM3Ni1mNmZmLTQ0NDItOTU0NS00ZjRmZTBkNzBlNTcifQ.eyojBO-X3KWZy_D6NmIrVwcuL6VDmDvDcs1MMFbc5tOG2cWSQ4Up2OWhvANOD0ajUAmx-DOvHuF_XNVnHXsKpmhyj7t-3EMmorfE0KFumNOxcputOF2f8ZnpPE48trSNv_IBga-M9TEB821TAv9K2-_McqG2D474WeJSvv7DA_dOQvhzZLqqZhclG6JIyCywQM0uRG0YbkxKzXXBhAeiyvTNxHo7dMs-LqCJmxvjLcwug8C4Ujysgx1jDlRLOVayRsPPfiOwzX980FSHJSmU1MX8bv8j1F6Na2314Ildy6A7ddHu5ssrLCfm1BHjPAKtgvulXrE8fggDzsmBfIqwkQ
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
x-request-id: 6e0f6f92-f759-4993-ac83-df06edd0a57f

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"6e0f6f92-f759-4993-ac83-df06edd0a57f","retryable":false,"details":{}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51448/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51448
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: efc10e13-cfaa-4a9c-a20e-6e61e7781193

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
POST http://127.0.0.1:51448/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51448
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 88c37dff-78eb-4395-b0bd-2932f7b1593a

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImNlMmJlMmUwZjkwZTFiMjUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjgsIm5iZiI6MTc4OTI3MDQyNywiZXhwIjoxNzg5MjcwNzI4LCJqdGkiOiJkYTA3ZTgwNy1iNjJhLTQwNWQtYjU5ZS1mMzg1ZTY4NmIzMmYifQ.QkDZx8y2kaQVnvW2k8DxjUeuime8I_-xg7--sPqx5mxAwCmZ1lKngMVPpPqCeqyZMfQP4860mwRc3Sr2-89bPKq1XbLsT07fU0M8BgB-KJoSZoH-jdHoHQ3MQ4sHbyB65PDPFEVxRJU3bFVrXSQgVC0biuqftWpbaqodNeiU7oI41C0H2I5tzflpx_kmWjX100Rejp7dqCrL_Ogl3Xl2LrIsIkIAec-LD8ilRTm-0au3XGt1Dv8J6QyeDH-q4rlEJ1Lu17XPQL9zmueuwGXEijQKij9I_4LViFCDYOn1ZiwK8sAVVY24QGxCCoqMv8ybk7uZZopXf-sM-giG1ELQwA
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
x-request-id: d08f0d11-f48a-4e36-a23b-d86127f145be

{"tool_call_id":"fa93837f-89bd-4584-b77d-b4198172fd20","operation_id":"fa93837f-89bd-4584-b77d-b4198172fd20","tool_attempt_id":null,"status":"pending_approval","evidence_receipt":null,"result_ref":null,"reason_code":null}
```

## test_tool_operation_replay_conflict_and_new_call_id_control_execution

Contract point: Canonical ToolCall replay/conflict/new provider call identity.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg1Yjc1YWMxYmVmNjEzN2MifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjksIm5iZiI6MTc4OTI3MDQyOCwiZXhwIjoxNzg5MjcwNzI5LCJqdGkiOiI1Mzc2MjRmYS01YTI5LTQyMjMtYmJlYy1hOTc2NTcxYmE5ZTMifQ.Xbz-lpxuOcD8R3Z_8b5Weg49IeXdIMNCSrwEbH4zaz-P47nfCJtn9GKK-9rC8UBiOqiQsYwpvg69TR9C9d4qjCOyxhKIWhJvt1Gz0NC7ka30uC63WfnjKY7wMVEIXi0EzA9bGhHYGXnFvkjjOnPyodhrj4OI4r5-Gp0gMsABS0s4TJIJgdL6-8U2UZqTnyY3cfS3PHmm1pfvGlANBaCr0miYCTbG-360HEGLL0HoI5QIJlqX-c_OHrdGXLULX7gctpu0YUOQsOAt08P0mesmD5ug6ef8DF-TX4c5UMJc7e3mv9LbybqyyQU4CGr5i5N0NCHvD-0MJQ__LwKsDkNmUQ
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
x-request-id: 80e08478-52cc-403a-9562-63b82edf33c2

{"tool_call_id":"caabc588-e532-476b-8dc7-484ab94cfe4d","operation_id":"caabc588-e532-476b-8dc7-484ab94cfe4d","tool_attempt_id":"407ae1d8-df56-4903-9360-9a64ebd4cd61","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"d64ad01f-c947-44d6-a510-391e15262301","revision":"1"},"capture_id":"407ae1d8-df56-4903-9360-9a64ebd4cd61","status":"accepted","artifact_refs":[{"id":"201e4a24-f16e-46a2-b5ac-f1f17a40f095","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"201e4a24-f16e-46a2-b5ac-f1f17a40f095","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg1Yjc1YWMxYmVmNjEzN2MifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjksIm5iZiI6MTc4OTI3MDQyOCwiZXhwIjoxNzg5MjcwNzI5LCJqdGkiOiI1Mzc2MjRmYS01YTI5LTQyMjMtYmJlYy1hOTc2NTcxYmE5ZTMifQ.Xbz-lpxuOcD8R3Z_8b5Weg49IeXdIMNCSrwEbH4zaz-P47nfCJtn9GKK-9rC8UBiOqiQsYwpvg69TR9C9d4qjCOyxhKIWhJvt1Gz0NC7ka30uC63WfnjKY7wMVEIXi0EzA9bGhHYGXnFvkjjOnPyodhrj4OI4r5-Gp0gMsABS0s4TJIJgdL6-8U2UZqTnyY3cfS3PHmm1pfvGlANBaCr0miYCTbG-360HEGLL0HoI5QIJlqX-c_OHrdGXLULX7gctpu0YUOQsOAt08P0mesmD5ug6ef8DF-TX4c5UMJc7e3mv9LbybqyyQU4CGr5i5N0NCHvD-0MJQ__LwKsDkNmUQ
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
x-request-id: 50e5847e-38a7-4fce-bd42-0ae68c99cb36

{"tool_call_id":"caabc588-e532-476b-8dc7-484ab94cfe4d","operation_id":"caabc588-e532-476b-8dc7-484ab94cfe4d","tool_attempt_id":"407ae1d8-df56-4903-9360-9a64ebd4cd61","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"d64ad01f-c947-44d6-a510-391e15262301","revision":"1"},"capture_id":"407ae1d8-df56-4903-9360-9a64ebd4cd61","status":"accepted","artifact_refs":[{"id":"201e4a24-f16e-46a2-b5ac-f1f17a40f095","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"201e4a24-f16e-46a2-b5ac-f1f17a40f095","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg1Yjc1YWMxYmVmNjEzN2MifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjksIm5iZiI6MTc4OTI3MDQyOCwiZXhwIjoxNzg5MjcwNzI5LCJqdGkiOiI1Mzc2MjRmYS01YTI5LTQyMjMtYmJlYy1hOTc2NTcxYmE5ZTMifQ.Xbz-lpxuOcD8R3Z_8b5Weg49IeXdIMNCSrwEbH4zaz-P47nfCJtn9GKK-9rC8UBiOqiQsYwpvg69TR9C9d4qjCOyxhKIWhJvt1Gz0NC7ka30uC63WfnjKY7wMVEIXi0EzA9bGhHYGXnFvkjjOnPyodhrj4OI4r5-Gp0gMsABS0s4TJIJgdL6-8U2UZqTnyY3cfS3PHmm1pfvGlANBaCr0miYCTbG-360HEGLL0HoI5QIJlqX-c_OHrdGXLULX7gctpu0YUOQsOAt08P0mesmD5ug6ef8DF-TX4c5UMJc7e3mv9LbybqyyQU4CGr5i5N0NCHvD-0MJQ__LwKsDkNmUQ
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
x-request-id: 650f6f5d-0c18-436e-93ad-56b5b7a09db6

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"650f6f5d-0c18-436e-93ad-56b5b7a09db6","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg1Yjc1YWMxYmVmNjEzN2MifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MjksIm5iZiI6MTc4OTI3MDQyOCwiZXhwIjoxNzg5MjcwNzI5LCJqdGkiOiI1Mzc2MjRmYS01YTI5LTQyMjMtYmJlYy1hOTc2NTcxYmE5ZTMifQ.Xbz-lpxuOcD8R3Z_8b5Weg49IeXdIMNCSrwEbH4zaz-P47nfCJtn9GKK-9rC8UBiOqiQsYwpvg69TR9C9d4qjCOyxhKIWhJvt1Gz0NC7ka30uC63WfnjKY7wMVEIXi0EzA9bGhHYGXnFvkjjOnPyodhrj4OI4r5-Gp0gMsABS0s4TJIJgdL6-8U2UZqTnyY3cfS3PHmm1pfvGlANBaCr0miYCTbG-360HEGLL0HoI5QIJlqX-c_OHrdGXLULX7gctpu0YUOQsOAt08P0mesmD5ug6ef8DF-TX4c5UMJc7e3mv9LbybqyyQU4CGr5i5N0NCHvD-0MJQ__LwKsDkNmUQ
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
x-request-id: 41525169-da43-4c0e-b8cd-f8db06f316d4

{"tool_call_id":"d95be527-66c2-4596-a4f2-c78a4256ebc4","operation_id":"d95be527-66c2-4596-a4f2-c78a4256ebc4","tool_attempt_id":"1b2f4f25-3120-47c1-bc44-10459bd418f1","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"bbef8fce-28e8-4c63-a5db-602a6f5cc2e4","revision":"1"},"capture_id":"1b2f4f25-3120-47c1-bc44-10459bd418f1","status":"accepted","artifact_refs":[{"id":"668bdc20-4f61-430d-9841-711dcd823a10","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"668bdc20-4f61-430d-9841-711dcd823a10","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjM0ZmZjOTExOWM0MzMxNzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzEsIm5iZiI6MTc4OTI3MDQzMCwiZXhwIjoxNzg5MjcwNzMxLCJqdGkiOiI1Y2Q5YjQwYi02ZDYxLTQzN2ItYTRhOC0yZDJlODE1ZTU5YWIifQ.P8ElkpEpzqAANZolOd8QSZM1U4IeMqUnRvnCS0fpCiaj5k2N8iWtV4l-JwY17zVEWKbv53SbNuUpekFCReAsYzO03zWxn0cnKIhLEkdE_e524MgtVzsQR4gFw9gxaGsGShbkPlfSCSRs6MgtFiKakeopxIeNBTtAiPoeuxr5cVnRU16EeHUOmDdBE8tHREHQS52K1xA4vfb4UfZgcaDhu2yGTq1uqWB2bJ9YBF4pz7IKeRlq7DIF_zQlCkXM_-HTYOiav5_Dw0dQfKsBch9St4zs99CIivj7zMy-vM2iN-mjYwSnQdhywg6PYMQab99rmEyU8h8H-HTK94d4h_k51w
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
x-request-id: f8f6c20f-2adc-4eaa-94d8-c08d86a84e85

{"tool_call_id":"9dc10bf0-76cf-4aee-9499-a2d417ff1365","operation_id":"9dc10bf0-76cf-4aee-9499-a2d417ff1365","tool_attempt_id":"8f247832-4094-4839-a286-2bda71909889","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"44c82330-9d67-4c12-a57c-cb2b3065dadf","revision":"1"},"capture_id":"8f247832-4094-4839-a286-2bda71909889","status":"accepted","artifact_refs":[{"id":"0db411f4-df46-45ce-b193-a2469f019281","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"0db411f4-df46-45ce-b193-a2469f019281","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/tool-calls/9dc10bf0-76cf-4aee-9499-a2d417ff1365
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjM0ZmZjOTExOWM0MzMxNzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzEsIm5iZiI6MTc4OTI3MDQzMCwiZXhwIjoxNzg5MjcwNzMxLCJqdGkiOiI1Y2Q5YjQwYi02ZDYxLTQzN2ItYTRhOC0yZDJlODE1ZTU5YWIifQ.P8ElkpEpzqAANZolOd8QSZM1U4IeMqUnRvnCS0fpCiaj5k2N8iWtV4l-JwY17zVEWKbv53SbNuUpekFCReAsYzO03zWxn0cnKIhLEkdE_e524MgtVzsQR4gFw9gxaGsGShbkPlfSCSRs6MgtFiKakeopxIeNBTtAiPoeuxr5cVnRU16EeHUOmDdBE8tHREHQS52K1xA4vfb4UfZgcaDhu2yGTq1uqWB2bJ9YBF4pz7IKeRlq7DIF_zQlCkXM_-HTYOiav5_Dw0dQfKsBch9St4zs99CIivj7zMy-vM2iN-mjYwSnQdhywg6PYMQab99rmEyU8h8H-HTK94d4h_k51w
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 1e19a1b9-74b5-4803-aa42-55f6c08b4ac2

{"tool_call_id":"9dc10bf0-76cf-4aee-9499-a2d417ff1365","operation_id":"9dc10bf0-76cf-4aee-9499-a2d417ff1365","tool_attempt_id":"8f247832-4094-4839-a286-2bda71909889","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"44c82330-9d67-4c12-a57c-cb2b3065dadf","revision":"1"},"capture_id":"8f247832-4094-4839-a286-2bda71909889","status":"accepted","artifact_refs":[{"id":"0db411f4-df46-45ce-b193-a2469f019281","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"0db411f4-df46-45ce-b193-a2469f019281","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjM0ZmZjOTExOWM0MzMxNzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzEsIm5iZiI6MTc4OTI3MDQzMCwiZXhwIjoxNzg5MjcwNzMxLCJqdGkiOiI1Y2Q5YjQwYi02ZDYxLTQzN2ItYTRhOC0yZDJlODE1ZTU5YWIifQ.P8ElkpEpzqAANZolOd8QSZM1U4IeMqUnRvnCS0fpCiaj5k2N8iWtV4l-JwY17zVEWKbv53SbNuUpekFCReAsYzO03zWxn0cnKIhLEkdE_e524MgtVzsQR4gFw9gxaGsGShbkPlfSCSRs6MgtFiKakeopxIeNBTtAiPoeuxr5cVnRU16EeHUOmDdBE8tHREHQS52K1xA4vfb4UfZgcaDhu2yGTq1uqWB2bJ9YBF4pz7IKeRlq7DIF_zQlCkXM_-HTYOiav5_Dw0dQfKsBch9St4zs99CIivj7zMy-vM2iN-mjYwSnQdhywg6PYMQab99rmEyU8h8H-HTK94d4h_k51w
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
x-request-id: 67b7c0e0-7515-4c46-a310-94f8e1436986

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"67b7c0e0-7515-4c46-a310-94f8e1436986","retryable":false,"details":{}}
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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImFmMTZjMmU1NTkwYjg3YzcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzMsIm5iZiI6MTc4OTI3MDQzMiwiZXhwIjoxNzg5MjcwNzMzLCJqdGkiOiIwZjdiZDBjZS03MTg3LTRhN2ItYTQxYS0wZTVmNGJmZDI5NWQifQ.EZcvO5l_9nrfFUv_knkPhDssv_wl3PKlPhdoUEEqQzZaqKIOKyn-o4Y6FgDKk7IN22v3CT21FrRt5J29zc1FbrVZnDXROb_RdO3w3U3OWoCaPYJFW98pBgLCPM57nzvrExWqrhcq89FUdrdtJoLyzYH9ZoZfJ9muj4Aajh2tMlLaa0rxeFhplEAbqP8jh14QYByxdKlMyDJcPUpv5iPgZf-QE4ChM3tArMzG8Zy5vacbye0qC0G3tTu7ojA2An4npkMPirlwvCV5JlGP5h_sWcU-7_BLH1vfU4kiNjgAUCt_8f-d2ub7N-wi5mQFHvLuCqX7LfSNpfL-RAGZbJe-tg
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
x-request-id: adadab6b-8101-44fc-a3db-4d791d892d80

{"code":"OPERATION_UNKNOWN","message":"The request could not be completed.","request_id":"adadab6b-8101-44fc-a3db-4d791d892d80","retryable":false,"details":{"model_attempt_id":"e55b18f0-0ec8-4972-82ac-5b6e4fd072a2","receipt_url":"/internal/v2/model-attempts/e55b18f0-0ec8-4972-82ac-5b6e4fd072a2"}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImFmMTZjMmU1NTkwYjg3YzcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzMsIm5iZiI6MTc4OTI3MDQzMiwiZXhwIjoxNzg5MjcwNzMzLCJqdGkiOiIwZjdiZDBjZS03MTg3LTRhN2ItYTQxYS0wZTVmNGJmZDI5NWQifQ.EZcvO5l_9nrfFUv_knkPhDssv_wl3PKlPhdoUEEqQzZaqKIOKyn-o4Y6FgDKk7IN22v3CT21FrRt5J29zc1FbrVZnDXROb_RdO3w3U3OWoCaPYJFW98pBgLCPM57nzvrExWqrhcq89FUdrdtJoLyzYH9ZoZfJ9muj4Aajh2tMlLaa0rxeFhplEAbqP8jh14QYByxdKlMyDJcPUpv5iPgZf-QE4ChM3tArMzG8Zy5vacbye0qC0G3tTu7ojA2An4npkMPirlwvCV5JlGP5h_sWcU-7_BLH1vfU4kiNjgAUCt_8f-d2ub7N-wi5mQFHvLuCqX7LfSNpfL-RAGZbJe-tg
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
x-request-id: ca75593d-eb26-479b-be0d-a5569dccd2aa
x-wuji-model-attempt-id: 2e8c4579-506c-4824-b074-55df6c94cf73
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51459/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:51459
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 2e8c4579-506c-4824-b074-55df6c94cf73

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImJlMGJjYWEyNmU5YTZjYzgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzUsIm5iZiI6MTc4OTI3MDQzNCwiZXhwIjoxNzg5MjcwNzM1LCJqdGkiOiIxMDllNTMwYy05OGFjLTQ5MGMtODA4MS1hOWQ1ZDcyNmU5NTgifQ.Z6HWYk-R4f-Lpzv75qGLtMpqw1y4e-i5ibWwgY-_ksp6tEive8u7iU_upfXKJ28Ns8oKkcsiSRwipPbGiYTBGolAe4B_ECz4YOprZRPcduXSaOS54-azrZwmU-DgpW3MgHCmrw0cmhVkuB-yyIGDvSPEyym_LYCmeQTJxub4CSUk6WOGBl0Ee84pHyvdflovc0zQy9KjiQhuWD3KROK6wQFyv4EK5uoom-N9ulKv5XtJ2B3GHQJx6ab_WlnYHZRjhaOv7ETig9lwUqGKO7i0ilrno99ZRwcix-dRHXg1Drz4aNvwg1cnwN0_pxfntewuq-7aacQIqMxh07hd8PHnJQ
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
x-request-id: 2afe55f0-fc47-480e-a239-9f68a6331369

{"tool_call_id":"b0eb6e6c-466d-4506-84b1-a1ee494ad533","operation_id":"b0eb6e6c-466d-4506-84b1-a1ee494ad533","tool_attempt_id":"9b3a6e71-210a-4fcc-a5bb-0b3d181bdc7b","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"37119678-1896-44b2-a1cb-94ea1fa82b18","revision":"1"},"capture_id":"9b3a6e71-210a-4fcc-a5bb-0b3d181bdc7b","status":"accepted","artifact_refs":[{"id":"6333de93-7067-43d9-9487-380923c04957","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"6333de93-7067-43d9-9487-380923c04957","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_explicit_null_tools_is_a_valid_native_model_request

Contract point: Explicit tools:null is accepted as native no-tools input.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImMyYTRiNGYxMGU1MTE5YjMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzcsIm5iZiI6MTc4OTI3MDQzNiwiZXhwIjoxNzg5MjcwNzM3LCJqdGkiOiIyODg0MTQzOS1jMDcxLTQ3MDktYjRiNy01NmRmMWE2ZmY3NzUifQ.dYAL-MqJMLaVlXSvuNziupubcAhplS_IQjBVEnXhErJqJiia7wcCHdFr1mPeRFsb4eYqGmaokutrp8aum_7s2siZ_VpOQDbOAN40KiZzJJjO-jshCnTHD2g6d-R7olv44cHCkN7ZXe5s1Pe5cyX6DuYxfpzjH6TKnhR4sIk3mmf1TrWCaS95CiBYMuCIeoz770paHkMm19LsHVJvvJsaSZw4Tj2bIgur1SptXguT2kAJwie7gzLKQq-JGA03sTHDsPwiGJTnKT7xUpLJqlULwlSh4U5D-mtEcNgbIh9Cgge0LLJ4DQ2gGa4kPC8cyxhDqXaLDu-f7AMMcLcWup3hRw
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
x-request-id: 2cae8d14-fae9-4890-93ab-8567092c3338
x-wuji-model-attempt-id: 930087d3-e94c-4bc5-af48-9c4fbe7f05b3
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51472/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 227
content-type: application/json
host: 127.0.0.1:51472
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 930087d3-e94c-4bc5-af48-9c4fbe7f05b3

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjMwNzk3MGNmMTBkY2FhYjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0MzgsIm5iZiI6MTc4OTI3MDQzNywiZXhwIjoxNzg5MjcwNzM4LCJqdGkiOiIxMjNmYzE3ZS1kN2RlLTQ3NDAtYjVkZi1kM2I1NjcyZDdjYTcifQ.SYSqfijqRftZfG9o28dIKSjV5xZ_r1Z5aPZSKuXgLzr9B5H46AW8LvH8_AIy8JVBlu0jEMkYzbQQeCX0aesuakNn94pkJgGBXztPdgUaB57igMppx9a0U2PXlOcQ_-y1V49_B8nsDwVTq2Ztd9nIGY6gdUMHDwo17X0kQZikYoRIak2to_kViUBC6CHuHrgXsiWTe98c4IxgvUa3MwGPYJg62byZ-i3kmJk0apDoOX7DN7FAl2XNMVFYo1ZSt_prLTZMy_m6Cboi6aulx0DeRazjb4t_slAZXoUZV2oVpfit1oZbxAWEFjofj3oV0qqZHhY9JTxQJx21nrmBx2F9Gg
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
x-request-id: 8ce82396-f46d-45a0-9bd5-069322f52f39

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"8ce82396-f46d-45a0-9bd5-069322f52f39","retryable":false,"details":{}}
```

## test_model_tool_advertisement_accepts_the_actual_tool_gate_assembly

Contract point: Shared resolver accepts a registered and actually assembled workspace tool.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImYzYWM0ZDdjZTdjZmRmZmEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhc3NlbWJsZWQtbW9kZWwtd29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0NDAsIm5iZiI6MTc4OTI3MDQzOSwiZXhwIjoxNzg5MjcwNzQwLCJqdGkiOiIwYmM4NzU4MC1hMzg1LTRmMGUtOWVhOS0xMTFmYTY2YzM3MDQifQ.cSXFiCHckTYsR9I5dvs38LCxpdexKMah4d3DU5UXLjFt5OiOKzcpUOnp-889rabzfcSQGOfa2OlMnEL0bxnnjNhCWHXg1seeXw4ZSAFbKUS5OclZ4bu2EBk-hWtYjLEFtfK0QWdnn9HdNXfwPvUarzEcC3WpGBHdYG9bffPxg59bBX1PxrjKRaWieXfZaFfpSTyOk9hl4XAfELj8hXMlXIe5Cpi0jd2L8gpGSlgrMkD-g1QObwkXxL7yHGvxPW0ESt5Wm3faMVdStmt3GnQUGzPq6YAkr0V2v84ilqVSY7Ipw0uVUAR_-_t9wyhZ_xEH_JptWvvyrrq4XSfY8KOWZg
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
x-request-id: 86d30e07-02fa-4066-ae29-8ed62334a6df
x-wuji-model-attempt-id: 15854300-e362-4049-9a19-9d08a4aec16e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:51478/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 460
content-type: application/json
host: 127.0.0.1:51478
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 15854300-e362-4049-9a19-9d08a4aec16e

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBiNTYwZjdmZGUwZGFhNjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0NDAsIm5iZiI6MTc4OTI3MDQzOSwiZXhwIjoxNzg5MjcwNzQwLCJqdGkiOiJjZWI5MDdiMS02ZTNlLTQ3MjctYTlhOC1kZTJlZGE2OGUzODgifQ.M0ZJHBh24yQ6QOhkxXZHsZ6QgazS1UQL9b8sRu9jnvtcA1ldNZJlOdEhkjYE0qQwkKs-kXVFewrN7DWy4VOqTxya0v1iCSkti5YJzIdijAa7tM7dZNuAiJfRdWKofs-0qvrU8EuaA40ullPW7Yr6oYY3xbgnKSKs9apBFiI2l7lYsY8d-vscL9ydTeUpC1jZTanl59P-amKthxOzwyDr1iYBNCDgoEhsiQbBThfLkz2RJSZhDcP6WRFCxtzPnQ0In2Ptk7yl6QR26iT8GfaG3EDoKUYVnGqqf0-KArmcuZ0YXr-AQaGeMjexzjGON5cDul2pnpnV9x_LsY-La1tYKg
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
x-request-id: 5e537005-085d-430f-9820-df010c2e0b5e

{"tool_call_id":"94a843cb-06c0-4215-8942-6cbcaa3db785","operation_id":"94a843cb-06c0-4215-8942-6cbcaa3db785","tool_attempt_id":"5271530b-66df-4a42-82ec-9656b529f313","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"25e7688a-f3d7-40f9-be39-500d53255121","revision":"1"},"capture_id":"5271530b-66df-4a42-82ec-9656b529f313","status":"accepted","artifact_refs":[{"id":"1e584a7c-c4b3-43ef-899e-2b99c9495f37","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"1e584a7c-c4b3-43ef-899e-2b99c9495f37","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"},"reason_code":"LIMIT_BLOCKED"}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/1e584a7c-c4b3-43ef-899e-2b99c9495f37/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBiNTYwZjdmZGUwZGFhNjkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzA0NDAsIm5iZiI6MTc4OTI3MDQzOSwiZXhwIjoxNzg5MjcwNzQwLCJqdGkiOiJjZWI5MDdiMS02ZTNlLTQ3MjctYTlhOC1kZTJlZGE2OGUzODgifQ.M0ZJHBh24yQ6QOhkxXZHsZ6QgazS1UQL9b8sRu9jnvtcA1ldNZJlOdEhkjYE0qQwkKs-kXVFewrN7DWy4VOqTxya0v1iCSkti5YJzIdijAa7tM7dZNuAiJfRdWKofs-0qvrU8EuaA40ullPW7Yr6oYY3xbgnKSKs9apBFiI2l7lYsY8d-vscL9ydTeUpC1jZTanl59P-amKthxOzwyDr1iYBNCDgoEhsiQbBThfLkz2RJSZhDcP6WRFCxtzPnQ0In2Ptk7yl6QR26iT8GfaG3EDoKUYVnGqqf0-KArmcuZ0YXr-AQaGeMjexzjGON5cDul2pnpnV9x_LsY-La1tYKg
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
x-request-id: 7a47aff7-47d0-4c08-b9a9-88cfb6e12ba2

fixtu
```

## test_partial_workspace_receipt_replay_compares_original_output_metadata

Contract point: Repeated receiver receipt compares original digest/length without duplicate accounting.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_model_openapi_declares_runtime_correlation_headers

Contract point: OpenAPI declares runtime attempt and replay response headers.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_model_request_cannot_write_model_settlement_fields

Contract point: Application-role model_request cannot forge response, billing, local settlement or slot release.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_tool_request_cannot_write_tool_settlement_or_release_resources

Contract point: Application-role tool_request cannot forge receipt/output/result or release resource reservations.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_request_inserts_require_zero_counters_and_initial_model_state

Contract point: Application-role request INSERT requires zero counters and an unsettled not-sent model call.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_tool_request_inserts_require_admitted_reserved_pending_state

Contract point: Application-role tool INSERT requires admitted attempt, reserved resource and pending settlement states.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_explicit_tool_retry_reopens_only_from_registered_stopped_attempt

Contract point: A terminal ToolCall reopens only through an already-registered explicit retry attempt.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.
