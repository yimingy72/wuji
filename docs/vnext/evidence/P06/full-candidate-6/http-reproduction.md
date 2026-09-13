# P06 complete HTTP reproduction packets

P06 base: `f32678d5662965f44b32863e8ecdf306db676ffd`; fixes through `78095e617c0be14932937fb8a052fb9a256b0f56`; migration: `vnext_0009_p06_request_write_guards`.
All bearer tokens and keys below are synthetic isolated test values. Packets are decoded verbatim from final JSONL captures and bodies are not truncated.

## test_current_run_model_gate_forwards_native_and_records_attempt

Contract point: Signed Run admission, native response, private Task key and durable receipt.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjQzY2RhMWFhMzQ1NTQ4MTQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjEsIm5iZiI6MTc4OTI3MTg2MCwiZXhwIjoxNzg5MjcyMTYxLCJqdGkiOiJiY2M0YmE3ZC0xNzUwLTRjN2UtODJiNi1iNWY4YTk4OWU3N2QifQ.kFYzeLdOThxsGlDufxd0Um2_8aY7GtXhJAUm0QVpnsi6hvKrLOQd9UL0xKIemWXIwCbga2q6U6EN5IHyAzOC4eD_31LFq9CzbaGnednEant4m3CA4y61yixggFVOjbVw6nRVgz5Qm4NCDc7wpQhvAfvrIWhoFR_Neesz7XBYwNmbIX7JAFRS6rdK02tshnHtDieF0Up_E9P--vly67ds3tsj-tOBsF5g1r5_4WLxWs4zTT5xRiLmy3PYRHhANEAomW5syOTAwd3D4Bld8V9ihAX0XGEzeA3S5h-lfRGfIfk9rEPmxRgMRq3hYj74zyMu4WVy53wWlsm1AGwulVVtOA
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
x-request-id: 23476fe2-08d0-42df-b435-2287e7208e5d
x-wuji-model-attempt-id: 89cc94e2-55e6-48e7-9640-c61cfa285677
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/89cc94e2-55e6-48e7-9640-c61cfa285677
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjQzY2RhMWFhMzQ1NTQ4MTQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjEsIm5iZiI6MTc4OTI3MTg2MCwiZXhwIjoxNzg5MjcyMTYxLCJqdGkiOiJiY2M0YmE3ZC0xNzUwLTRjN2UtODJiNi1iNWY4YTk4OWU3N2QifQ.kFYzeLdOThxsGlDufxd0Um2_8aY7GtXhJAUm0QVpnsi6hvKrLOQd9UL0xKIemWXIwCbga2q6U6EN5IHyAzOC4eD_31LFq9CzbaGnednEant4m3CA4y61yixggFVOjbVw6nRVgz5Qm4NCDc7wpQhvAfvrIWhoFR_Neesz7XBYwNmbIX7JAFRS6rdK02tshnHtDieF0Up_E9P--vly67ds3tsj-tOBsF5g1r5_4WLxWs4zTT5xRiLmy3PYRHhANEAomW5syOTAwd3D4Bld8V9ihAX0XGEzeA3S5h-lfRGfIfk9rEPmxRgMRq3hYj74zyMu4WVy53wWlsm1AGwulVVtOA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 544
content-type: application/json
x-request-id: 818bfdab-0890-400e-aab9-d88455c9da30

{"model_attempt_id":"89cc94e2-55e6-48e7-9640-c61cfa285677","input_digest":"57d0d5d1f73d05a69fef3b3d9d68088f4408bde81680c5a37b2008cba4c46149","logical_request_id":"model-request-current-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"complete","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":true,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"377","retained_bytes":"377","forwarded_bytes":"377","output_bytes":"377"}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54412/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54412
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 89cc94e2-55e6-48e7-9640-c61cfa285677

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVhMjk0NWJlOTdlMDY4ODAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjMsIm5iZiI6MTc4OTI3MTg2MiwiZXhwIjoxNzg5MjcyMTYzLCJqdGkiOiI0OTVjNjZjZC02ZGFlLTRjMjItYmU1NS00OWZmOGViNjQ0ZTAifQ.cRs3wwEY_b36HYd34LKo0iJv00FAv8lsBlFoKcHLarfS-pS8PNUCBv7z_vCmG4Gxy97PDXU-BAOG-KwN_l3nzkh-FR_bC2Naruz3GaVClV8JnQSY_GkJ6dWSXjhd1NRfMLlawyKeWMqKWwtA5KOdKFt7KeQzeXpYiQjNjK5OBSnxgz-_txirywNR1IxqUCB-tMLdGw6qiP2NsFKdBJdm4n6PSA5N8i_M_TAw-zjRLk2EIZ56OE50U5GYZvNsxRfhGt2gWw4sQtXGzvlf-Jvyzkec9DSyFZYYIhbQynPSSEGTwUIbRs06iB4eIhWPYO2PNxr6ndI1jmzCQXw1QHIpKg
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
x-request-id: 6587d6cb-2c3b-4e4f-b2af-f1ec6e5416ac

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"6587d6cb-2c3b-4e4f-b2af-f1ec6e5416ac","retryable":false,"details":{}}
```

## test_p05_pause_makes_bound_run_identity_stale

Contract point: P05 pause invalidates an otherwise valid Run binding.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImIxMjhiNDY2Y2E3M2U3YjYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjQsIm5iZiI6MTc4OTI3MTg2MywiZXhwIjoxNzg5MjcyMTY0LCJqdGkiOiI2NDZjYzZkOC1mYWZmLTQ5MzUtYWY2Zi1jMjE2MTFiMTQyNGIifQ.QNJ0mLXJBr8NvOwdezZpuHny-cwE6imMNWau-kZZxtWLlieWKo_y3MPXfrjD6anzjQbZieL6VykW_C0SYgBrMY-cj-TUMyniBHcPZ5W7KBre_qqOQeM6cJuBM_SlY9uZPaxOW3LvQrztEL5ahH5pHnk-lAX_RXQWdQV4Qauev30Nf1GVGlJfXVM4wW78ctbSgcSZcWT8R7czdhGz4zYHmV0LlJ6KNdUpXE2zJ3Z0A-fmZdRrUtORqZoFR0ll-lpafvZAZ43Q4CyqdazYzmTwuVtCycoJZSIdbT1vUVhgE3azXn7OZ1uvM5qYr3MKiKJG9Uw8_JzeVAatkCJdkIkb7Q
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
x-request-id: 6827d259-7065-43c2-9cb3-3572e071dc46

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"6827d259-7065-43c2-9cb3-3572e071dc46","retryable":false,"details":{}}
```

## test_model_request_replay_conflict_and_new_id_have_distinct_attempts

Contract point: Same request ID replays, changed digest conflicts, new ID creates a new inference.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjgwMTQxMjgxZmM4YjUzNWIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjUsIm5iZiI6MTc4OTI3MTg2NCwiZXhwIjoxNzg5MjcyMTY1LCJqdGkiOiI1YTc0OTBlYS0yOWMxLTRiZDYtYjRiYy05Zjg4YTI0MWI3OWMifQ.XZ3Kelpz7fk3Xk14wl7Aks6PJICHPEqhlY4xTUYMMTBBf1slcbBOTk8TCPbYSDPSP0fIcPXcXz3tpYcgRQGVEOt6LVdgdVroCnysboi0q5q4e26C54mByydzc0tCo0GdJjY9JTcRWlApUabcUuerZeCTGeD_8f-FNwWzOH21Z4uUEAjunVNyQ5lvRMNIBPtZvNZIhqw0oexJACLww82VtGHzp-gI2Hjaa-Ux1pOqffNDGA0Wtn7tRSMrKzfQBDu6lSeQVvJ0c47OMAmnuipUhm_zxHWO38JPpNPe4WcMPf34k21SVyZ4FtxJICK5w8tzPa0B00hyRHOi3d-TDzvqAQ
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
x-request-id: a8063017-2eb3-47e9-9b44-b40423970044
x-wuji-model-attempt-id: 34a005d0-0a58-459d-ad89-3bf9ba2b622e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjgwMTQxMjgxZmM4YjUzNWIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjUsIm5iZiI6MTc4OTI3MTg2NCwiZXhwIjoxNzg5MjcyMTY1LCJqdGkiOiI1YTc0OTBlYS0yOWMxLTRiZDYtYjRiYy05Zjg4YTI0MWI3OWMifQ.XZ3Kelpz7fk3Xk14wl7Aks6PJICHPEqhlY4xTUYMMTBBf1slcbBOTk8TCPbYSDPSP0fIcPXcXz3tpYcgRQGVEOt6LVdgdVroCnysboi0q5q4e26C54mByydzc0tCo0GdJjY9JTcRWlApUabcUuerZeCTGeD_8f-FNwWzOH21Z4uUEAjunVNyQ5lvRMNIBPtZvNZIhqw0oexJACLww82VtGHzp-gI2Hjaa-Ux1pOqffNDGA0Wtn7tRSMrKzfQBDu6lSeQVvJ0c47OMAmnuipUhm_zxHWO38JPpNPe4WcMPf34k21SVyZ4FtxJICK5w8tzPa0B00hyRHOi3d-TDzvqAQ
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
x-request-id: fe89b960-1bde-48b9-a7fa-39367040428e
x-wuji-model-attempt-id: 34a005d0-0a58-459d-ad89-3bf9ba2b622e
x-wuji-replayed: true

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjgwMTQxMjgxZmM4YjUzNWIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjUsIm5iZiI6MTc4OTI3MTg2NCwiZXhwIjoxNzg5MjcyMTY1LCJqdGkiOiI1YTc0OTBlYS0yOWMxLTRiZDYtYjRiYy05Zjg4YTI0MWI3OWMifQ.XZ3Kelpz7fk3Xk14wl7Aks6PJICHPEqhlY4xTUYMMTBBf1slcbBOTk8TCPbYSDPSP0fIcPXcXz3tpYcgRQGVEOt6LVdgdVroCnysboi0q5q4e26C54mByydzc0tCo0GdJjY9JTcRWlApUabcUuerZeCTGeD_8f-FNwWzOH21Z4uUEAjunVNyQ5lvRMNIBPtZvNZIhqw0oexJACLww82VtGHzp-gI2Hjaa-Ux1pOqffNDGA0Wtn7tRSMrKzfQBDu6lSeQVvJ0c47OMAmnuipUhm_zxHWO38JPpNPe4WcMPf34k21SVyZ4FtxJICK5w8tzPa0B00hyRHOi3d-TDzvqAQ
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
x-request-id: a07fa863-d40d-42d4-8e26-9ca74d9aab62

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"a07fa863-d40d-42d4-8e26-9ca74d9aab62","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjgwMTQxMjgxZmM4YjUzNWIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjUsIm5iZiI6MTc4OTI3MTg2NCwiZXhwIjoxNzg5MjcyMTY1LCJqdGkiOiI1YTc0OTBlYS0yOWMxLTRiZDYtYjRiYy05Zjg4YTI0MWI3OWMifQ.XZ3Kelpz7fk3Xk14wl7Aks6PJICHPEqhlY4xTUYMMTBBf1slcbBOTk8TCPbYSDPSP0fIcPXcXz3tpYcgRQGVEOt6LVdgdVroCnysboi0q5q4e26C54mByydzc0tCo0GdJjY9JTcRWlApUabcUuerZeCTGeD_8f-FNwWzOH21Z4uUEAjunVNyQ5lvRMNIBPtZvNZIhqw0oexJACLww82VtGHzp-gI2Hjaa-Ux1pOqffNDGA0Wtn7tRSMrKzfQBDu6lSeQVvJ0c47OMAmnuipUhm_zxHWO38JPpNPe4WcMPf34k21SVyZ4FtxJICK5w8tzPa0B00hyRHOi3d-TDzvqAQ
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
x-request-id: 29f0c8fb-1bfb-4f1b-9b81-f338001d6ed4
x-wuji-model-attempt-id: 70a664b2-da21-4e1d-be76-d61c9d31e174
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54421/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54421
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 34a005d0-0a58-459d-ad89-3bf9ba2b622e

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
POST http://127.0.0.1:54421/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54421
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 70a664b2-da21-4e1d-be76-d61c9d31e174

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjU2YTY0Yjk5NmVkYjIyOTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsid29ya2VyIl0sImlhdCI6MTc4OTI3MTg2NywibmJmIjoxNzg5MjcxODY2LCJleHAiOjE3ODkyNzIxNjcsImp0aSI6ImZkZjg5ZjdmLTc3M2MtNGM4NC1iNGZmLWRiNjk5MjZmYjlkMSJ9.Tcp2xGZwlE5kSwbLP9LGhwAXXILyP1OqzJ3lb6nMEIdCkvEvIEjoKz04s9MKM4AWWxQyNNc35M8K1S80eWLZgORz5lkWt64WTrF26gJQzLsmfOFQk8sODtq-MHgyB3DLZDD4XySOju1O0STpVRU3KTvUqta4yBI9yKWHLBdkTgWpZD6O3bmv3vnHp3WMJ9CiLz8a2UmGkxxEF5DBUuLQ3xdFBg1RTHmT9RCNcR2V09PMaL4aRB9uGNTH4Vc33ECTjLFZMzzy_KhxxlBhbsY7XtptsqILCPbJ2lS13AN0sc2dh90DKUT6eddRyRbz9bM8WjqoZrLlS_Y9eE0cLsYivw
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
x-request-id: 0cccc374-4f5c-480d-a8b3-cb7eb1f5eca8

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"0cccc374-4f5c-480d-a8b3-cb7eb1f5eca8","retryable":false,"details":{}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjU2YTY0Yjk5NmVkYjIyOTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjcsIm5iZiI6MTc4OTI3MTg2NiwiZXhwIjoxNzg5MjcyMTY3LCJqdGkiOiJhMDg0MTRmNi05ZjJiLTQ5YWEtODE2Ni1hZTNiZGM1OTg4MWQifQ.GQrMhotEQTTJ695KP2FA60WIn85bPob77gb4wcumBDFX9lmEvi3f832g1R8JlS3z7ZsLeWkmQYVZSkEnejauoKsM9pP1kk7Nh4jJsRgDRd8kL9zAtVjYG2GdYabfb41lYTFS95ot8QKmsWk0kIG7Re5KYduSFOTIzrG-Wmb80wEzMbYOf3JK5NryfZjaDvafSM3FwmoCC2Dx28zeqTfnbGhbK2uJSEkzS7EHKWzbKfkNu9VZSC-XA4ZHP7nKgJnxBTHVj7LRGpRt9c8sGe3FVnY1xKoCPPIlscP2uONLqL7Kav-rVEPLVgLH-vBX5n5gZ-s4Ol0HmVa7JW5M-iw-bQ
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
x-request-id: 98e9c89d-42fa-4866-bd79-cb7f32fdeb4f
x-wuji-model-attempt-id: 765f49e9-0240-4c7d-8fc3-ba314b4e041e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54424/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54424
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 765f49e9-0240-4c7d-8fc3-ba314b4e041e

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg4MzRiYTgxMGUyNDJiM2YifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjgsIm5iZiI6MTc4OTI3MTg2NywiZXhwIjoxNzg5MjcyMTY4LCJqdGkiOiIzM2I1NjEzOS01ZDNjLTQ1MDMtODRlMy1mOGQyNDBiNzhiMjMifQ.SM6-pjREo4kcDmDlKDNnZsvY_thoEKtKj9MMz16rk3uCZOsHVOeA78HbUZPdt8BgrJUrxzvcDS5FEPctKXOigsNSMBxIqf-ZylMv-wuyCnNP3cKtb9430YE0YBqGGf4e2omqYMwE9dk-LdSHyNjGbbQoEY3MvaHlzoRHb0f4OYejVaHhdJ6qve-J30fti_RaacQMAYe-HAeR9hyGnzmCbCT13ntGVkfpO7gTES92vRK6GohVpngj3SK3NKT2bEZTysM0Koe5KeBG4d9_2wy1oGhJ-odQ3uhvq8EBEjTaPovqIPji6yHurt9pI_c_dvhuZMQht9xUaLNdv6fW4uzxQQ
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
x-request-id: a9329c93-c65b-4cd3-ac32-f3b98748c573
x-wuji-model-attempt-id: 46656202-ade5-4602-a18c-18b6a358335e
x-wuji-replayed: false

data: {"id":"chatcmpl-p06-partial","object":"chat.completion.chunk","created":1,"model":"fixture-model","choices":[{"index":0,"delta":{"role":"assistant","content":"partial"},"finish_reason":null}]}


```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/model-attempts/46656202-ade5-4602-a18c-18b6a358335e
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg4MzRiYTgxMGUyNDJiM2YifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjgsIm5iZiI6MTc4OTI3MTg2NywiZXhwIjoxNzg5MjcyMTY4LCJqdGkiOiIzM2I1NjEzOS01ZDNjLTQ1MDMtODRlMy1mOGQyNDBiNzhiMjMifQ.SM6-pjREo4kcDmDlKDNnZsvY_thoEKtKj9MMz16rk3uCZOsHVOeA78HbUZPdt8BgrJUrxzvcDS5FEPctKXOigsNSMBxIqf-ZylMv-wuyCnNP3cKtb9430YE0YBqGGf4e2omqYMwE9dk-LdSHyNjGbbQoEY3MvaHlzoRHb0f4OYejVaHhdJ6qve-J30fti_RaacQMAYe-HAeR9hyGnzmCbCT13ntGVkfpO7gTES92vRK6GohVpngj3SK3NKT2bEZTysM0Koe5KeBG4d9_2wy1oGhJ-odQ3uhvq8EBEjTaPovqIPji6yHurt9pI_c_dvhuZMQht9xUaLNdv6fW4uzxQQ
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 536
content-type: application/json
x-request-id: f683aea4-2292-4daa-bc34-0ccd19b65804

{"model_attempt_id":"46656202-ade5-4602-a18c-18b6a358335e","input_digest":"cc712b587519e826c7e1e943cc65088a98dc0d8cd3d981eda39c2aa8c5a620ad","logical_request_id":"model-partial-1","grouping_state":"known","admission_state":"admitted","send_state":"sent","response_state":"partial","billing_state":"pending","local_state":"ended","inflight":false,"upstream_status":200,"response_available":false,"gateway_usage_ref":null,"gateway_spend_ref":null,"received_bytes":"200","retained_bytes":"200","forwarded_bytes":"200","output_bytes":"200"}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijg4MzRiYTgxMGUyNDJiM2YifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NjgsIm5iZiI6MTc4OTI3MTg2NywiZXhwIjoxNzg5MjcyMTY4LCJqdGkiOiIzM2I1NjEzOS01ZDNjLTQ1MDMtODRlMy1mOGQyNDBiNzhiMjMifQ.SM6-pjREo4kcDmDlKDNnZsvY_thoEKtKj9MMz16rk3uCZOsHVOeA78HbUZPdt8BgrJUrxzvcDS5FEPctKXOigsNSMBxIqf-ZylMv-wuyCnNP3cKtb9430YE0YBqGGf4e2omqYMwE9dk-LdSHyNjGbbQoEY3MvaHlzoRHb0f4OYejVaHhdJ6qve-J30fti_RaacQMAYe-HAeR9hyGnzmCbCT13ntGVkfpO7gTES92vRK6GohVpngj3SK3NKT2bEZTysM0Koe5KeBG4d9_2wy1oGhJ-odQ3uhvq8EBEjTaPovqIPji6yHurt9pI_c_dvhuZMQht9xUaLNdv6fW4uzxQQ
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
x-request-id: 6a20ed74-fea6-45b7-9883-e350491a22a6
x-wuji-model-attempt-id: 2596d06f-8bb7-4b1b-b432-dcbecf3cb63e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54426/v1/chat/completions
accept: text/event-stream
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 213
content-type: application/json
host: 127.0.0.1:54426
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 46656202-ade5-4602-a18c-18b6a358335e

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
POST http://127.0.0.1:54426/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54426
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 2596d06f-8bb7-4b1b-b432-dcbecf3cb63e

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImEzZWU2N2IzMDY3YzJlYjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzAsIm5iZiI6MTc4OTI3MTg2OSwiZXhwIjoxNzg5MjcyMTcwLCJqdGkiOiIxYTgzODRiNy1kZmVjLTRjNzYtYmJmNi1kODYyOGE5MzllNjMifQ.CqiCSi1j7oHoZzSEyhJ1KeXlKksx9KP0pu1PaFM0hLaOIN4CuYtuHaVFFaKTL8l7eRjtGFduIxsqSzIiTJ5xjp0jxwYvx9U8MhgQvQbL5eRG60FNImiCmAh_Vm20JXcEDXfPupgnxFTXgTNBM5gYoWlTdf6lhkMaL3TciKFhNWeGg7uo6oTmtz0SZHErTRW00KpIe8bqzthJJvYyioKBKmZKu7-yRmOw1-MaQHgkRBWnk-gfVLu4cuk5eydUF_p57FpFWoYjAYkBfKiuTok82g0ZEg9NknJjbGmnafyYgexzYvaV0F9qOKQAcwuW_PoQb7VqHLoXq6NbzqnY_xMjUA
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
x-request-id: 50f8f7ce-3001-4271-ad7a-f26628d40e04

{"tool_call_id":"7cad0886-99d7-485e-9a6e-67b970dae4bf","operation_id":"7cad0886-99d7-485e-9a6e-67b970dae4bf","tool_attempt_id":"c6783202-0282-47a4-abf0-f4323c17395f","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"b5b78f2b-0c72-4ccd-84d7-3db8856a3dd8","revision":"1"},"capture_id":"c6783202-0282-47a4-abf0-f4323c17395f","status":"accepted","artifact_refs":[{"id":"900ad599-fda1-4396-aa49-da4b50a92a03","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"900ad599-fda1-4396-aa49-da4b50a92a03","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/900ad599-fda1-4396-aa49-da4b50a92a03/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImEzZWU2N2IzMDY3YzJlYjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzAsIm5iZiI6MTc4OTI3MTg2OSwiZXhwIjoxNzg5MjcyMTcwLCJqdGkiOiIxYTgzODRiNy1kZmVjLTRjNzYtYmJmNi1kODYyOGE5MzllNjMifQ.CqiCSi1j7oHoZzSEyhJ1KeXlKksx9KP0pu1PaFM0hLaOIN4CuYtuHaVFFaKTL8l7eRjtGFduIxsqSzIiTJ5xjp0jxwYvx9U8MhgQvQbL5eRG60FNImiCmAh_Vm20JXcEDXfPupgnxFTXgTNBM5gYoWlTdf6lhkMaL3TciKFhNWeGg7uo6oTmtz0SZHErTRW00KpIe8bqzthJJvYyioKBKmZKu7-yRmOw1-MaQHgkRBWnk-gfVLu4cuk5eydUF_p57FpFWoYjAYkBfKiuTok82g0ZEg9NknJjbGmnafyYgexzYvaV0F9qOKQAcwuW_PoQb7VqHLoXq6NbzqnY_xMjUA
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
x-request-id: 3b0c3014-fcdc-4dd2-94ef-021f5d8a4753

fixture-version=17

```

### Inbound ASGI exchange 3

Request:

```http
GET http://testserver/internal/v2/tool-calls/7cad0886-99d7-485e-9a6e-67b970dae4bf
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImEzZWU2N2IzMDY3YzJlYjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzAsIm5iZiI6MTc4OTI3MTg2OSwiZXhwIjoxNzg5MjcyMTcwLCJqdGkiOiIxYTgzODRiNy1kZmVjLTRjNzYtYmJmNi1kODYyOGE5MzllNjMifQ.CqiCSi1j7oHoZzSEyhJ1KeXlKksx9KP0pu1PaFM0hLaOIN4CuYtuHaVFFaKTL8l7eRjtGFduIxsqSzIiTJ5xjp0jxwYvx9U8MhgQvQbL5eRG60FNImiCmAh_Vm20JXcEDXfPupgnxFTXgTNBM5gYoWlTdf6lhkMaL3TciKFhNWeGg7uo6oTmtz0SZHErTRW00KpIe8bqzthJJvYyioKBKmZKu7-yRmOw1-MaQHgkRBWnk-gfVLu4cuk5eydUF_p57FpFWoYjAYkBfKiuTok82g0ZEg9NknJjbGmnafyYgexzYvaV0F9qOKQAcwuW_PoQb7VqHLoXq6NbzqnY_xMjUA
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 7d5da7cd-0e55-4e12-bea0-2736b18c5253

{"tool_call_id":"7cad0886-99d7-485e-9a6e-67b970dae4bf","operation_id":"7cad0886-99d7-485e-9a6e-67b970dae4bf","tool_attempt_id":"c6783202-0282-47a4-abf0-f4323c17395f","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"b5b78f2b-0c72-4ccd-84d7-3db8856a3dd8","revision":"1"},"capture_id":"c6783202-0282-47a4-abf0-f4323c17395f","status":"accepted","artifact_refs":[{"id":"900ad599-fda1-4396-aa49-da4b50a92a03","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"900ad599-fda1-4396-aa49-da4b50a92a03","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_revoked_run_cannot_dispatch_workspace_tool

Contract point: Revoked Run creates no ToolAttempt or receiver execution.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBlNzY5NjU0MDg0NDZhODcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzEsIm5iZiI6MTc4OTI3MTg3MCwiZXhwIjoxNzg5MjcyMTcxLCJqdGkiOiJkMDRkNTg2Mi0xY2EyLTRkOWEtOTE3NS0wYWFkZjExMjc0ZDIifQ.p2iCkiCBXrOSyPOJ2cG59zOZbDsKrY3mQcYaJjeQRW5m8_yqahV6f_7a5q3V_mn4bpO16AvXVvXDFwHOTbKeevADmTetjB7GIhGZf0L2smu4Ra9T7wj969tA0jxmCm8a1w7JAiTh9auT3rd9p7n5pwcDiPRccrfJgloXM3vc0U57QL9cXQH8OIh5z2a1j2yC3MJj2-df-1OwJjhHeZix0dOhcReF3JUlkdN6pGWlgZZGx-_ixrPFd_-J3MdRyXmgWauxZTFsad25-Ppye4QyoArw8FnVv_mj54ldsun6WzX0Cv_sEVLLr3s1lugf5CxkqCX-AqPT01YMPIwUS8Pr0A
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
x-request-id: 277363ca-a028-4d39-84fc-a26cd98795a6

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"277363ca-a028-4d39-84fc-a26cd98795a6","retryable":false,"details":{}}
```

## test_task_output_limit_is_cumulative_across_model_attempts

Contract point: Task output allowance remains cumulative across model attempts.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjIzMjZlMjUwZDgwYjFmOTgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzIsIm5iZiI6MTc4OTI3MTg3MSwiZXhwIjoxNzg5MjcyMTcyLCJqdGkiOiJlZGZkZmE5NC00ODFmLTQxNzUtYjM3OC1mOWYzZjRlZDBkODQifQ.TMhgibtEaBnQwpqRZh0WEhQvPwNr0bAeOtgYnniZDHaRjk4qnKXnRXofIhZo_1x7V2JGbGHiBTUyxrM1yiyO8UmYv3wlTnaNiEIqRzGqQ1We1tLmA9AgV--vRGNfho7IoieiOHIRiJt7pWyq0HKvDKt0GhIj1g7PKZuOetQruQWn6u5Lf5Kylyrin-bdiVkakcE7fHYNO-sEumvbXt0pawBkK4H11txpCHLH4MIgqz6vDZmoIvUTc6ogfcyx5wkyRSxVzryiSJsteufuIJ514QQDmN4dMpFKjClTf1KkRkFC2Zo7ihrG0dDtdoC1MfNDpk3HqTQ1cdAxtFAC_I31BQ
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
x-request-id: 3e7370e3-5042-4276-b7b3-548ab479da03
x-wuji-model-attempt-id: 5fc66126-2de3-4208-bc60-4559338e5574
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjIzMjZlMjUwZDgwYjFmOTgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzIsIm5iZiI6MTc4OTI3MTg3MSwiZXhwIjoxNzg5MjcyMTcyLCJqdGkiOiJlZGZkZmE5NC00ODFmLTQxNzUtYjM3OC1mOWYzZjRlZDBkODQifQ.TMhgibtEaBnQwpqRZh0WEhQvPwNr0bAeOtgYnniZDHaRjk4qnKXnRXofIhZo_1x7V2JGbGHiBTUyxrM1yiyO8UmYv3wlTnaNiEIqRzGqQ1We1tLmA9AgV--vRGNfho7IoieiOHIRiJt7pWyq0HKvDKt0GhIj1g7PKZuOetQruQWn6u5Lf5Kylyrin-bdiVkakcE7fHYNO-sEumvbXt0pawBkK4H11txpCHLH4MIgqz6vDZmoIvUTc6ogfcyx5wkyRSxVzryiSJsteufuIJ514QQDmN4dMpFKjClTf1KkRkFC2Zo7ihrG0dDtdoC1MfNDpk3HqTQ1cdAxtFAC_I31BQ
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
x-request-id: 44d630a8-76b5-4af4-b251-26b8518007c8

{"code":"LIMIT_BLOCKED","message":"The request could not be completed.","request_id":"44d630a8-76b5-4af4-b251-26b8518007c8","retryable":false,"details":{}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54433/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54433
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 5fc66126-2de3-4208-bc60-4559338e5574

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
POST http://127.0.0.1:54433/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54433
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 070fd46a-a792-40e9-91bc-275f00997bd3

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZiM2MzNjc5ZWM1ODcxY2EifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzMsIm5iZiI6MTc4OTI3MTg3MiwiZXhwIjoxNzg5MjcyMTczLCJqdGkiOiJhOWNmNTA2NC00ZTM5LTRhMmItYTBlYS02ZjhhYjA0MDA2NGYifQ.pZlZKBLZazkZgJ4iL-OS3ZOdI-Au8RDiBO1fxdPKILq_lPbzBrFRimleCAfdvPpsnyPchYnV3N0nnTX-ZWSANCdNdmLJNeN0032o7vwYe3oWaJ-6CTZ2DkUmO2rlfzQuMJlTt5bn4oY7sN7P23IP3lKsoQad7VoMeR1vXedk9M6EdvEgcUtn7YrRTcI7MiTnV3xkDnkuZQfRrRoMYQ5OHC7-oo38KDyRC6yNYYuiBj7qyEVy1lqip-gY1vwH70HsigDwZwAdSVdKx--LhhSVCFEdYxLUHAj63bux2EzONVEkxKDCFd7dJYjC2qX88xyn-xcy-eca_tL8v2wI32Ck8w
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
x-request-id: 0e76fb14-a22f-46f8-b8c0-33fb54f46aae

{"tool_call_id":"e0bb13e8-ceb0-440d-b9e4-be7bc7f2fc08","operation_id":"e0bb13e8-ceb0-440d-b9e4-be7bc7f2fc08","tool_attempt_id":null,"status":"pending_approval","evidence_receipt":null,"result_ref":null,"reason_code":null}
```

## test_tool_operation_replay_conflict_and_new_call_id_control_execution

Contract point: Canonical ToolCall replay/conflict/new provider call identity.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRmYWRlNzJkYmY5OGQwNDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzQsIm5iZiI6MTc4OTI3MTg3MywiZXhwIjoxNzg5MjcyMTc0LCJqdGkiOiIxZjg5Mjk2My02ODhkLTQ0ZDEtOTNjNi1kYzk2NGExNTM1YTEifQ.ZchDjl_AphozSJTNC2BSKg9MOz_6JflPuz8DH9WLvlbdbc1PIsiKK8Ysqe9i0CF7CUgmw3Cjx5vdDrsPXmrnyw2DvNthWtchisg6EvcjCSVVn5166qz1IMzkyYqnizGNUVUHbDNDzl8EHGygpnjLAhTkTJh9YaJC7i2MEfTuIUI9pbR8w9TqmEQqrocMChLTNRP5tNbCjC_a0XFbicOdjnVEuIhbKjf-EQRSWsr7u4N0g2yF9MOemdHKwfQ4Jh1oG6k_eAwwI2BTVxp38ehMx5Zr4GhO5taJG9DQ5b7mZXXhV4gi8tmMdND9vHayWkltqlZ5tYGALka9tHNy5urYQA
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
x-request-id: 38690e5f-9690-42e4-bd18-a83b783a3b3a

{"tool_call_id":"8aa31faa-c76c-4d8d-8eb3-ed8e5c4a41ba","operation_id":"8aa31faa-c76c-4d8d-8eb3-ed8e5c4a41ba","tool_attempt_id":"f1441a5f-ba1d-44f4-a613-bd13edb13975","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"de441a82-ce41-45bd-bace-67bf5e34cc74","revision":"1"},"capture_id":"f1441a5f-ba1d-44f4-a613-bd13edb13975","status":"accepted","artifact_refs":[{"id":"96f49dd3-b78c-4eca-8d72-3cde165736ea","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"96f49dd3-b78c-4eca-8d72-3cde165736ea","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRmYWRlNzJkYmY5OGQwNDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzQsIm5iZiI6MTc4OTI3MTg3MywiZXhwIjoxNzg5MjcyMTc0LCJqdGkiOiIxZjg5Mjk2My02ODhkLTQ0ZDEtOTNjNi1kYzk2NGExNTM1YTEifQ.ZchDjl_AphozSJTNC2BSKg9MOz_6JflPuz8DH9WLvlbdbc1PIsiKK8Ysqe9i0CF7CUgmw3Cjx5vdDrsPXmrnyw2DvNthWtchisg6EvcjCSVVn5166qz1IMzkyYqnizGNUVUHbDNDzl8EHGygpnjLAhTkTJh9YaJC7i2MEfTuIUI9pbR8w9TqmEQqrocMChLTNRP5tNbCjC_a0XFbicOdjnVEuIhbKjf-EQRSWsr7u4N0g2yF9MOemdHKwfQ4Jh1oG6k_eAwwI2BTVxp38ehMx5Zr4GhO5taJG9DQ5b7mZXXhV4gi8tmMdND9vHayWkltqlZ5tYGALka9tHNy5urYQA
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
x-request-id: efc9bf30-dff6-4005-83c8-6a43f9f7895c

{"tool_call_id":"8aa31faa-c76c-4d8d-8eb3-ed8e5c4a41ba","operation_id":"8aa31faa-c76c-4d8d-8eb3-ed8e5c4a41ba","tool_attempt_id":"f1441a5f-ba1d-44f4-a613-bd13edb13975","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"de441a82-ce41-45bd-bace-67bf5e34cc74","revision":"1"},"capture_id":"f1441a5f-ba1d-44f4-a613-bd13edb13975","status":"accepted","artifact_refs":[{"id":"96f49dd3-b78c-4eca-8d72-3cde165736ea","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"96f49dd3-b78c-4eca-8d72-3cde165736ea","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRmYWRlNzJkYmY5OGQwNDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzQsIm5iZiI6MTc4OTI3MTg3MywiZXhwIjoxNzg5MjcyMTc0LCJqdGkiOiIxZjg5Mjk2My02ODhkLTQ0ZDEtOTNjNi1kYzk2NGExNTM1YTEifQ.ZchDjl_AphozSJTNC2BSKg9MOz_6JflPuz8DH9WLvlbdbc1PIsiKK8Ysqe9i0CF7CUgmw3Cjx5vdDrsPXmrnyw2DvNthWtchisg6EvcjCSVVn5166qz1IMzkyYqnizGNUVUHbDNDzl8EHGygpnjLAhTkTJh9YaJC7i2MEfTuIUI9pbR8w9TqmEQqrocMChLTNRP5tNbCjC_a0XFbicOdjnVEuIhbKjf-EQRSWsr7u4N0g2yF9MOemdHKwfQ4Jh1oG6k_eAwwI2BTVxp38ehMx5Zr4GhO5taJG9DQ5b7mZXXhV4gi8tmMdND9vHayWkltqlZ5tYGALka9tHNy5urYQA
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
x-request-id: 53be2ea1-ffcb-46a3-9759-64075e010e1f

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"53be2ea1-ffcb-46a3-9759-64075e010e1f","retryable":false,"details":{}}
```

### Inbound ASGI exchange 4

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRmYWRlNzJkYmY5OGQwNDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzQsIm5iZiI6MTc4OTI3MTg3MywiZXhwIjoxNzg5MjcyMTc0LCJqdGkiOiIxZjg5Mjk2My02ODhkLTQ0ZDEtOTNjNi1kYzk2NGExNTM1YTEifQ.ZchDjl_AphozSJTNC2BSKg9MOz_6JflPuz8DH9WLvlbdbc1PIsiKK8Ysqe9i0CF7CUgmw3Cjx5vdDrsPXmrnyw2DvNthWtchisg6EvcjCSVVn5166qz1IMzkyYqnizGNUVUHbDNDzl8EHGygpnjLAhTkTJh9YaJC7i2MEfTuIUI9pbR8w9TqmEQqrocMChLTNRP5tNbCjC_a0XFbicOdjnVEuIhbKjf-EQRSWsr7u4N0g2yF9MOemdHKwfQ4Jh1oG6k_eAwwI2BTVxp38ehMx5Zr4GhO5taJG9DQ5b7mZXXhV4gi8tmMdND9vHayWkltqlZ5tYGALka9tHNy5urYQA
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
x-request-id: b4f378d1-d1da-4760-bf9f-9300538822ce

{"tool_call_id":"c9d0707f-3d95-48d0-b9a9-5a13d160a8f1","operation_id":"c9d0707f-3d95-48d0-b9a9-5a13d160a8f1","tool_attempt_id":"310ae5e9-bf42-4fe1-bdea-7ea853c1646c","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"d8bac6de-d9f5-4d20-92f7-c28177b1a63d","revision":"1"},"capture_id":"310ae5e9-bf42-4fe1-bdea-7ea853c1646c","status":"accepted","artifact_refs":[{"id":"e110260d-8850-4448-9742-b2ed008bd96a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"e110260d-8850-4448-9742-b2ed008bd96a","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImRiYzM5NTRiZDhiMzRmMzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzYsIm5iZiI6MTc4OTI3MTg3NSwiZXhwIjoxNzg5MjcyMTc2LCJqdGkiOiJiODU0ZjhkMi1kNTdlLTQ0ZDYtOTg4Yy1hMjI0YjlmOWMwNDIifQ.AKnAQ2D1HUDa8QvUjK44C-2zUSnn8ZvdZ32RoF7u-hSsmDbdpdpi4L3ZUd1BRMMlumfwEwgy3vDk5eYXlEMAMURrlEw7w8tDrKi9pt9bVBUDiv6w9KHah--H-bG3pQfJOrVbHwGLNGCD-xTjDoc7u9w1mAwSENkMTzwCfnUULZ06YjR_U5C4kfiqWy8Hszd-LO7AwfOFZmPHF3HBSgFvg6ImGSyRGvSEN8vMQ50y7lOYRQ0ftot9-dHr39HlVLtwvzmMFkJUcLHgthHAQe4YgOHLhsX2hNgqh-d-150PlT9pRI3qz9-bY_sl2Kuf-OJcuMuTt7RSNWPmjreMXfntQg
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
x-request-id: 3c102a73-fd44-462c-9ca4-7c8b36d814c9

{"tool_call_id":"1a211d43-ad2c-4226-8454-d3a1b07aa8d0","operation_id":"1a211d43-ad2c-4226-8454-d3a1b07aa8d0","tool_attempt_id":"e72b869b-4943-4576-bcf6-aad8baf2c20a","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"2f59bb30-6faa-4b89-8ae9-3bcf81803f3c","revision":"1"},"capture_id":"e72b869b-4943-4576-bcf6-aad8baf2c20a","status":"accepted","artifact_refs":[{"id":"09c66550-d4ae-4a69-a4f2-bcebfaae5fca","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"09c66550-d4ae-4a69-a4f2-bcebfaae5fca","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/internal/v2/tool-calls/1a211d43-ad2c-4226-8454-d3a1b07aa8d0
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImRiYzM5NTRiZDhiMzRmMzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzYsIm5iZiI6MTc4OTI3MTg3NSwiZXhwIjoxNzg5MjcyMTc2LCJqdGkiOiJiODU0ZjhkMi1kNTdlLTQ0ZDYtOTg4Yy1hMjI0YjlmOWMwNDIifQ.AKnAQ2D1HUDa8QvUjK44C-2zUSnn8ZvdZ32RoF7u-hSsmDbdpdpi4L3ZUd1BRMMlumfwEwgy3vDk5eYXlEMAMURrlEw7w8tDrKi9pt9bVBUDiv6w9KHah--H-bG3pQfJOrVbHwGLNGCD-xTjDoc7u9w1mAwSENkMTzwCfnUULZ06YjR_U5C4kfiqWy8Hszd-LO7AwfOFZmPHF3HBSgFvg6ImGSyRGvSEN8vMQ50y7lOYRQ0ftot9-dHr39HlVLtwvzmMFkJUcLHgthHAQe4YgOHLhsX2hNgqh-d-150PlT9pRI3qz9-bY_sl2Kuf-OJcuMuTt7RSNWPmjreMXfntQg
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 4727f0cf-979e-44e7-b2f5-3bafce6046e2

{"tool_call_id":"1a211d43-ad2c-4226-8454-d3a1b07aa8d0","operation_id":"1a211d43-ad2c-4226-8454-d3a1b07aa8d0","tool_attempt_id":"e72b869b-4943-4576-bcf6-aad8baf2c20a","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"2f59bb30-6faa-4b89-8ae9-3bcf81803f3c","revision":"1"},"capture_id":"e72b869b-4943-4576-bcf6-aad8baf2c20a","status":"accepted","artifact_refs":[{"id":"09c66550-d4ae-4a69-a4f2-bcebfaae5fca","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"09c66550-d4ae-4a69-a4f2-bcebfaae5fca","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

### Inbound ASGI exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImRiYzM5NTRiZDhiMzRmMzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzYsIm5iZiI6MTc4OTI3MTg3NSwiZXhwIjoxNzg5MjcyMTc2LCJqdGkiOiJiODU0ZjhkMi1kNTdlLTQ0ZDYtOTg4Yy1hMjI0YjlmOWMwNDIifQ.AKnAQ2D1HUDa8QvUjK44C-2zUSnn8ZvdZ32RoF7u-hSsmDbdpdpi4L3ZUd1BRMMlumfwEwgy3vDk5eYXlEMAMURrlEw7w8tDrKi9pt9bVBUDiv6w9KHah--H-bG3pQfJOrVbHwGLNGCD-xTjDoc7u9w1mAwSENkMTzwCfnUULZ06YjR_U5C4kfiqWy8Hszd-LO7AwfOFZmPHF3HBSgFvg6ImGSyRGvSEN8vMQ50y7lOYRQ0ftot9-dHr39HlVLtwvzmMFkJUcLHgthHAQe4YgOHLhsX2hNgqh-d-150PlT9pRI3qz9-bY_sl2Kuf-OJcuMuTt7RSNWPmjreMXfntQg
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
x-request-id: 3d2f785a-db96-4db5-83aa-723f62e91e0f

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"3d2f785a-db96-4db5-83aa-723f62e91e0f","retryable":false,"details":{}}
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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlkYjZkNDdjMzk3YjZkZDMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzgsIm5iZiI6MTc4OTI3MTg3NywiZXhwIjoxNzg5MjcyMTc4LCJqdGkiOiI5YzdiMjg5ZS1lMDhmLTRlZWItYTU1NS1lOWNkYzFmMmFkOTIifQ.suT6S_HsOPh5Rcv43yADbv1EvY-RE1EXUyP2cOOC8-JQQr0j0g8df7REkF1SNI9Lkg--cQ557mcRqLrGAkY0dePtvOLj1egp5zTyZ74F8lzS_sy6-qStyWta4Tq1bHn1AlVLlnhfnShtlPzs4LvrSfWYrDoIOTiU2wlTK4WvUmLyCZk_swx9vXVqgwE7oKenUUNKQcrMOd0i1cbw-gNjPrI5C9azXwBNv4wFx6PaeS3G4WIubRfRJLzRn4zivo3ywa8YsA4wiV2i5CX9GgxZ7HH-oOzYHwKi8OsKcN0mtVn46vn5bkK-a59A5QPlxYQuFR08aE2pwVINrJWr3955Zg
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
x-request-id: d211ee02-3f03-4f57-a901-a279eb511eaf

{"code":"OPERATION_UNKNOWN","message":"The request could not be completed.","request_id":"d211ee02-3f03-4f57-a901-a279eb511eaf","retryable":false,"details":{"model_attempt_id":"e49d9320-531b-48b2-a7a0-81cc3b7a2935","receipt_url":"/internal/v2/model-attempts/e49d9320-531b-48b2-a7a0-81cc3b7a2935"}}
```

### Inbound ASGI exchange 2

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjlkYjZkNDdjMzk3YjZkZDMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4NzgsIm5iZiI6MTc4OTI3MTg3NywiZXhwIjoxNzg5MjcyMTc4LCJqdGkiOiI5YzdiMjg5ZS1lMDhmLTRlZWItYTU1NS1lOWNkYzFmMmFkOTIifQ.suT6S_HsOPh5Rcv43yADbv1EvY-RE1EXUyP2cOOC8-JQQr0j0g8df7REkF1SNI9Lkg--cQ557mcRqLrGAkY0dePtvOLj1egp5zTyZ74F8lzS_sy6-qStyWta4Tq1bHn1AlVLlnhfnShtlPzs4LvrSfWYrDoIOTiU2wlTK4WvUmLyCZk_swx9vXVqgwE7oKenUUNKQcrMOd0i1cbw-gNjPrI5C9azXwBNv4wFx6PaeS3G4WIubRfRJLzRn4zivo3ywa8YsA4wiV2i5CX9GgxZ7HH-oOzYHwKi8OsKcN0mtVn46vn5bkK-a59A5QPlxYQuFR08aE2pwVINrJWr3955Zg
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
x-request-id: c46f033f-ccfa-454d-8eb1-b5003ccd417d
x-wuji-model-attempt-id: e7cddd49-25bb-43c5-b9ac-b6c6b31eebda
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54451/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 214
content-type: application/json
host: 127.0.0.1:54451
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: e7cddd49-25bb-43c5-b9ac-b6c6b31eebda

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZkMWQ1NjY2M2YxODAyNWQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODEsIm5iZiI6MTc4OTI3MTg4MCwiZXhwIjoxNzg5MjcyMTgxLCJqdGkiOiI4NmY5OTQxNi0yNjZjLTQ2MTYtOGM1OS1lYWU2NGRlNDBlNzcifQ.OlxZSVa4nACy_hsU5G2O5eUSASjyBO5H6ZkcLbjX7XhK8MmOCK8LV_bpr19ncjT7VJH7z7Ky05AbGe_lFVtH9GNELqacu-piJHjn-1V4Cx5TWmOtjnFhGt-Ht9UKQE_ouGx4PFo5092FhVrEJIX6GC0D8e1xGYkhYuEIAKlmfLFRG8Q51HJ6r1X4_iU0fEUguvN_R6_biZgBDzSYHMP13yzagr-mVIbIiLHGIxL3dTc-8xnv5SSxl2XIiuKDH2PT0noKKAMMNBLT84ApW3Lm9ehJ4dk9IEHLwkK6NAuwPynMKsWtFWpzzK8nXyxFTheQ8P-Cvw18jq2g_6_Vx8E-PA
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
x-request-id: 50f31ecc-ea26-4649-8569-63de425eb435

{"tool_call_id":"f22f5b46-a8cb-4e45-aa95-b1ffd05b4d05","operation_id":"f22f5b46-a8cb-4e45-aa95-b1ffd05b4d05","tool_attempt_id":"37482829-0582-4a78-bf6f-001c892d36fa","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"11164106-9ed3-48f9-b6be-89b0913701d1","revision":"1"},"capture_id":"37482829-0582-4a78-bf6f-001c892d36fa","status":"accepted","artifact_refs":[{"id":"cae5887a-1731-4256-928d-12f0875fdfe1","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"cae5887a-1731-4256-928d-12f0875fdfe1","version":"1","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076"},"reason_code":null}
```

## test_explicit_null_tools_is_a_valid_native_model_request

Contract point: Explicit tools:null is accepted as native no-tools input.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjdmNjJjMGM5ZGQ2ZWUwN2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODIsIm5iZiI6MTc4OTI3MTg4MSwiZXhwIjoxNzg5MjcyMTgyLCJqdGkiOiJlM2EyNzU3My1iOTk2LTQ2YmYtYjY3Zi05NWIzMGNmODA1ZjcifQ.EJCCU1kuRlRutceYwSY5wD9RBK8xIDxUBrPhyC3F4RPSEMmIvffB9NvgTZMDMHT6NBw5y4ILmJcg3MFTqhuhZ3KlEhypSOn4-FebX3z41XHKm8FUwnPS5-72qfH05BlkDFH41wmiJr3p4VZrWCoinHMY_oBZWsusiWTk7V4RYmoSjC5TYzMigw10TwuQUJ-zaNS4G6ignwEI7wKzIptiK5SO5SLgsUkSXF9V0vI_7zlH6jVZHylBeImZLU4a4eoCHGu67xbvjqrYXP6_KFw37kcMGux_3DEFHSU9p-ZSR90nyoNsvERPV9QGahINXMyY1oReGxryHSlUo1VJgEVQsA
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
x-request-id: 62d96864-f1b4-425f-82d8-c7288f63c78e
x-wuji-model-attempt-id: 71f36f04-3640-49e9-afb2-f8dcb6367f7e
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54458/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 227
content-type: application/json
host: 127.0.0.1:54458
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 71f36f04-3640-49e9-afb2-f8dcb6367f7e

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImEwOGQ2YjMzYWE3NjgzMjcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODMsIm5iZiI6MTc4OTI3MTg4MiwiZXhwIjoxNzg5MjcyMTgzLCJqdGkiOiI0YmVjYmNiMC0yOGNhLTQwMGQtYmVlNi0zMTFkNTg5ZGU0ZGIifQ.NuLmslvVBELdJ9-NUPinZcZyA9IYRdo8DR1sBsX7vzoKxnG4VR9qtUvdBexxNFRAiwAP7iYa7T9IqhFPBQklgGXYoKl01ytH7AojIn1kD6Tg4V5hRSDTv3hIiKobHBzug5FIJTiIuJFEa7Z7vK26sY5Q5CO7g8ArpXYA9ETsNM_nGjF1l9I4V5hGYtmUSFZVd6pMbQhpgMOkzxak_xK1TmkEtdw0qUJ9eIuUGiy-wjgxr4iw_ZNJ4BWZX9J7RWRd1iggKbVC_Qs06ib3rQzSj5MsivEFnWxtiDg-dYbwEPJwrbHsFMR20oGIkW30FAPqTmMN8vbX6yII1BshymWeDg
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
x-request-id: 3fae8acd-a25f-4ca8-9f2e-55bcbe46dcc5

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"3fae8acd-a25f-4ca8-9f2e-55bcbe46dcc5","retryable":false,"details":{}}
```

## test_model_tool_advertisement_accepts_the_actual_tool_gate_assembly

Contract point: Shared resolver accepts a registered and actually assembled workspace tool.

### Inbound ASGI exchange 1

Request:

```http
POST http://testserver/internal/v2/model/chat/completions
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjFhMWNiZmFiZTEzOWE5OWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhc3NlbWJsZWQtbW9kZWwtd29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODUsIm5iZiI6MTc4OTI3MTg4NCwiZXhwIjoxNzg5MjcyMTg1LCJqdGkiOiI3ZDQ1MWM0ZS00MjdiLTQxZWUtOWE2NC03ODE5MmQ4M2FjMjgifQ.J6WRIdbGe1RAYSQt9gx3kIdOVhP6C6rFXY_lgLta0AxcQWes8tQdeRx5JmTSYhbi9sUQNBNnRYINK3kZGUqW1Y92YtKMnEkrVnBB9wJM9YKGBcwBPjyHwyFXsCE02v5d4KdxxaQq3LoSt-EB3BLJPjBlA8yuc-54jP7uuTvGifkof-xV1TwNlmOwBWKTJhkO1P2Qfvy4MDSO3JQMDfE38ZwKf1OaHBPoxquM8kx_-PVW6RjDk1aypmmwwEi9R3JLgmi8za3MWRkNCVtYb5QYbothQTM8yO85n4B44-RHW25wpe-h10nHlcftPx0g4XIEeauVh4huo2a_9u3cXccILw
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
x-request-id: 34b540a1-4d97-4882-bb72-0e56d0a14f60
x-wuji-model-attempt-id: 8213463a-ad41-4b7b-8a9e-103dad237f85
x-wuji-replayed: false

{"choices":[{"finish_reason":"tool_calls","index":0,"message":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\"path\":\"version.txt\"}","name":"read_fixture"},"id":"call-p06-read","type":"function"}]}}],"created":1,"id":"chatcmpl-p06-fixture","model":"fixture-model","object":"chat.completion","usage":{"completion_tokens":8,"prompt_tokens":17,"total_tokens":25}}
```

### Outbound localhost model exchange 1

Request:

```http
POST http://127.0.0.1:54467/v1/chat/completions
accept: application/json
accept-encoding: gzip, deflate
authorization: Bearer p06-synthetic-task-key
connection: keep-alive
content-length: 460
content-type: application/json
host: 127.0.0.1:54467
user-agent: python-httpx/0.28.1
x-wuji-model-attempt-id: 8213463a-ad41-4b7b-8a9e-103dad237f85

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
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjJiNzU0ZjE5NTAyZGYwNmQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODUsIm5iZiI6MTc4OTI3MTg4NCwiZXhwIjoxNzg5MjcyMTg1LCJqdGkiOiJiNjZjMTVmZS1jZTc5LTQ4MzAtYWI0Ny01YzQyNTJmNTExN2YifQ.Yv3pZxl2-UYAVHYGzew-ur1FyQWk3sdZ1r4ByrlcqE27_Sz4OOMmBCj42vU32PYeuw-tjMbASOWEL_sRCueiCJ41bUQ0B0N7duSzh2UgQ3O-43OQGjS3zrvO60rnoAfmraIAyMPvtvedm4YBrBtpfhHz9HHXSR-QR4V0iZz1GcIbdHdfki8-KHjAqdAXNeqvPwv4Zy97UFPMChJHgDz15IwfpXSJqBCfpx4TXsZxDd2YTCYGU4M-2lZQqK4ING_s8JIPia0Qc0Z6Lq1aSnhCGT5ecM1jNTB3gDaPDpsvI8DC74Yk3dy84p1asmIL3gFpyPP54RFZtE2m5m40fiLE0A
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
x-request-id: 410c43d7-cf5c-419a-9136-6969a594c67a

{"tool_call_id":"35be0d55-b1a3-4477-89b5-2b9bb2ded334","operation_id":"35be0d55-b1a3-4477-89b5-2b9bb2ded334","tool_attempt_id":"713271cb-7d83-42e6-932f-081384769c3b","status":"complete","evidence_receipt":{"observation_ref":{"entity_type":"observation","id":"28fd5243-935b-43b6-aeef-98f16218b971","revision":"1"},"capture_id":"713271cb-7d83-42e6-932f-081384769c3b","status":"accepted","artifact_refs":[{"id":"7dc488ea-70a4-46f5-86b7-7514c162eeb7","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"}],"request_id":"fixture-request","code":null},"result_ref":{"id":"7dc488ea-70a4-46f5-86b7-7514c162eeb7","version":"1","sha256":"edfc5a4f337481503511fcd4708922ec7cc1537a905c78fd03aecd013c3219c2"},"reason_code":"LIMIT_BLOCKED"}
```

### Inbound ASGI exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/7dc488ea-70a4-46f5-86b7-7514c162eeb7/content?version=1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjJiNzU0ZjE5NTAyZGYwNmQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJydW4td29ya2VyLWZpeHR1cmUiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtZml4dHVyZSIsInJvbGVzIjpbIndvcmtlciJdLCJpYXQiOjE3ODkyNzE4ODUsIm5iZiI6MTc4OTI3MTg4NCwiZXhwIjoxNzg5MjcyMTg1LCJqdGkiOiJiNjZjMTVmZS1jZTc5LTQ4MzAtYWI0Ny01YzQyNTJmNTExN2YifQ.Yv3pZxl2-UYAVHYGzew-ur1FyQWk3sdZ1r4ByrlcqE27_Sz4OOMmBCj42vU32PYeuw-tjMbASOWEL_sRCueiCJ41bUQ0B0N7duSzh2UgQ3O-43OQGjS3zrvO60rnoAfmraIAyMPvtvedm4YBrBtpfhHz9HHXSR-QR4V0iZz1GcIbdHdfki8-KHjAqdAXNeqvPwv4Zy97UFPMChJHgDz15IwfpXSJqBCfpx4TXsZxDd2YTCYGU4M-2lZQqK4ING_s8JIPia0Qc0Z6Lq1aSnhCGT5ecM1jNTB3gDaPDpsvI8DC74Yk3dy84p1asmIL3gFpyPP54RFZtE2m5m40fiLE0A
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
x-request-id: d6ced728-5e78-4fd6-8e5c-e19954ed906d

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

## test_tool_request_cannot_replace_nonterminal_status_with_result_state

Contract point: Table-driven running/unknown/evidence-pending ToolCalls cannot be changed directly to result states by tool_request.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_tool_request_cannot_insert_an_inactive_resource_claim

Contract point: A request cannot insert an inactive claim to evade active resource ownership.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_model_settle_cannot_insert_response_bytes_before_send

Contract point: Settlement cannot attach response bytes to a model attempt that never crossed the send fence.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_earliest_v8_upgrade_installs_model_update_guard

Contract point: Exact 67a v8 upgrades to v9 and installs the model update trigger for nonowner requests.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.

## test_earliest_v8_upgrade_installs_tool_update_guards

Contract point: Exact 67a v8 upgrades to v9 and installs every tool update trigger for nonowner requests.

HTTP packet: not applicable. This check exercises a production service, database policy, receiver receipt, or OpenAPI document directly; no HTTP exchange is claimed.
