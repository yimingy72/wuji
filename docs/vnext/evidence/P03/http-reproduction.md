# P03 complete HTTP reproduction package

Tested code: `dcf5cc2903622a02b023f545e3e4c1585004ae59`. 38 complete HTTP exchanges from the first final candidate run.

These are recorded requests/responses through the actual ASGI application, reconstructed as HTTP messages for reproduction; no external target or TCP packet capture is claimed. Authorization values are ephemeral tokens from isolated, destroyed synthetic issuers, not production credentials. Regenerate them by rerunning the recorded pytest command. Bodies and headers below are untruncated; the JSONL files also retain exact body bytes as base64.

Validation boundaries (not external vulnerability findings): collector authentication and attempt binding; 202 durable acceptance versus 403 rejection; replay/conflict; actual byte hashes; late historical_only; rollback. Snapshot/GC/RLS-only checks retain native SQL/file evidence rather than invented HTTP.

## Exchange 1 — tests/vnext/test_capture_transactions.py::test_agent_cannot_use_capture_endpoint

Native record: [runtime/eb980ec0ed7b/http-exchanges.jsonl](runtime/eb980ec0ed7b/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjA4ZjRlN2U0ZTQ5MjkyNzIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJhZ2VudC1maXh0dXJlIiwidGVuYW50X2lkIjoidGVuYW50LWZpeHR1cmUiLCJyb2xlcyI6WyJhZ2VudCJdLCJpYXQiOjE3ODkyNTA0MzYsIm5iZiI6MTc4OTI1MDQzNSwiZXhwIjoxNzg5MjUwNzM2LCJqdGkiOiJlZTUzODM2Zi01Y2EwLTRkMTgtOWU2Ni04N2ZlYjlhMTc4MGYifQ.MZYphU0g_utUxCP7Ed0GMQTOLKYevqExyCki6OdG9GYJRGX-CfhEroN-om8J1NAmXpEbsd4eswH-iCNJdb9kKtySyoNMiZJWu9U61c7QrcPwcXfqRHvhkODyL8ZTOiZR-6_QtkGOjDB7Mh_YMQCSNiFhQrxo3OH_XtgSw2vCA1BiePxBpawhY2geLXDJYXUL3phlJr55X0fv35zCL3Gi7JYs8TDPGinHTl0sojl31hQt41W4buYICpvbBtU5AVcYPsDPmAlK_aqpP39T3lz1cw6mXK7aHrS3NkphZd__PjoLrusJDd_Kghg3isW0Y8_qnRgG0APu5GhbJbNgGZ2b-g
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"9c5c7165-ce4c-41f4-89b8-2efc64c5182e","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"3762b38a-85e0-4403-b843-27cf81ccf3de","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: d555af41-6721-4305-b3fe-9b674b834337

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"d555af41-6721-4305-b3fe-9b674b834337","retryable":false,"details":{}}
```

## Exchange 2 — tests/vnext/test_capture_transactions.py::test_bound_collector_persists_one_observation_all_bytes_without_extractor

Native record: [runtime/317a8c55f053/http-exchanges.jsonl](runtime/317a8c55f053/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUxMWI5NjY5ZmNmZmZiMzIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6IjNkNjZiYTZhLTk1ZmUtNGQ1OC1iMmEyLTYzNmE0NzdmMjk0NCJ9.hBIr0WPTV1dH94WljOI8f4YFWsoregC14aAb2UDTlKvLRuRVVAowgR4zCTB0aJk-UqZ9aH5niGOlYDYN98_BN8B86WSfRi15GnFWSPRQMJ2R_F4q7tIqGYrtFu7DfR45yu9KgyhY9RZhldlZo5UuXeIih7I0z0PcgzeVcpP2wM0HhAiXjWwxFoprUxN9VUM9w_Yg35AEvHS7D2JF70RPLph3BFGAMmW79EDyh3_xLLaalTRRn1igGpzti9QBpHhDNaeroy8LkIMXbRCLbgdzYp9qkSMLysTIJiorHiRDcy8yUENDoov8kc738B9KXwR2x2zgo7oSs0K9MWz4TMDsGw
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"6b365e80-d4bc-4632-813a-e7a7f29d8ca4","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"a66e31cf-26cb-4709-8f7f-202054e86e26","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 15ff2add-8984-4cfd-9fea-5368beaf13bb

{"observation_ref":{"entity_type":"observation","id":"16b6cfe1-6fd3-48e9-93a7-7dca7b8a4a99","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"6b365e80-d4bc-4632-813a-e7a7f29d8ca4","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"a66e31cf-26cb-4709-8f7f-202054e86e26","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"15ff2add-8984-4cfd-9fea-5368beaf13bb","code":null}
```

## Exchange 3 — tests/vnext/test_capture_transactions.py::test_bound_collector_persists_one_observation_all_bytes_without_extractor

Native record: [runtime/317a8c55f053/http-exchanges.jsonl](runtime/317a8c55f053/http-exchanges.jsonl), JSONL row 2.

```http
GET http://testserver/api/v2/artifacts/6b365e80-d4bc-4632-813a-e7a7f29d8ca4/content?version=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUxMWI5NjY5ZmNmZmZiMzIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJyZWFkZXItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsicmVhZGVyIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6ImZlOGY3NDRhLTE2NjMtNDM1My1hZmE1LWFkNzljMWIxZWM2NCJ9.nFQ3-7Jl42txQAtA-Pmg80ijfYS0eZKjdobXGX32m7bAid2-mp4Skjd_yNi06R5uJHh8RwQzHiIvSOasrlGvpRutfA34-0SGEwUeNWoqtflY0DroLaDy4yO6r54wS76gS5a47ubKWbzNXJeukO4nlf4aqdBvc8KbXj3kZuXel2Lf-z-Wpx3vUo45GRKPF7OkXyd04fbPSlXpAJQ0Xiwbp83m4w-V8DyefYEEu4tISYSRKagO1VHJolhhl6bXazFeHZ4Z5d6FbyqiOWanxYl4OHbGD0URreWJBnsja8Ue5OwPfM4iEDhbZ9PzXf9HDXS2c0HoW3vGxuzoA6bIzRaBhw
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-disposition: attachment
content-security-policy: default-src 'none'
content-type: application/octet-stream
digest: sha-256=mix+hFuKB64TDrAeYUV9mgMkNywuvsBitn0PgR37F6w=
x-content-type-options: nosniff
x-request-id: bd156ca7-15f4-4939-8ca0-0269a46f9ac3

  {"version":17,"message":"system healthy"}

```

## Exchange 4 — tests/vnext/test_capture_transactions.py::test_bound_collector_persists_one_observation_all_bytes_without_extractor

Native record: [runtime/317a8c55f053/http-exchanges.jsonl](runtime/317a8c55f053/http-exchanges.jsonl), JSONL row 3.

```http
GET http://testserver/api/v2/artifacts/a66e31cf-26cb-4709-8f7f-202054e86e26/content?version=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjUxMWI5NjY5ZmNmZmZiMzIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJyZWFkZXItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsicmVhZGVyIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6ImZlOGY3NDRhLTE2NjMtNDM1My1hZmE1LWFkNzljMWIxZWM2NCJ9.nFQ3-7Jl42txQAtA-Pmg80ijfYS0eZKjdobXGX32m7bAid2-mp4Skjd_yNi06R5uJHh8RwQzHiIvSOasrlGvpRutfA34-0SGEwUeNWoqtflY0DroLaDy4yO6r54wS76gS5a47ubKWbzNXJeukO4nlf4aqdBvc8KbXj3kZuXel2Lf-z-Wpx3vUo45GRKPF7OkXyd04fbPSlXpAJQ0Xiwbp83m4w-V8DyefYEEu4tISYSRKagO1VHJolhhl6bXazFeHZ4Z5d6FbyqiOWanxYl4OHbGD0URreWJBnsja8Ue5OwPfM4iEDhbZ9PzXf9HDXS2c0HoW3vGxuzoA6bIzRaBhw
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-disposition: attachment
content-security-policy: default-src 'none'
content-type: application/octet-stream
digest: sha-256=wlSWC5dQ/j1NXYM86LIQQgOLP5K5Xe9hLF5/txq2hAM=
x-content-type-options: nosniff
x-request-id: a0c9cc6a-97d2-4d37-a64c-3f6c11096f27

{"fixture_prerequisite":true,"exit_code":0}

```

## Exchange 5 — tests/vnext/test_capture_transactions.py::test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected

Native record: [runtime/9e3edd3a9f52/http-exchanges.jsonl](runtime/9e3edd3a9f52/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjhkMjBlNTJjMGI2NDE0YWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6IjQzNTFiNzVkLTBjMjktNDI0Yy1iYzM5LTZkYzlhODYxY2M1ZCJ9.moVlJJe3YNcr_P-L47tAK9D0Hb-t9oWFuITjtRfviM83Kv-mV1m_exP6Ao8yDWy7zv-7uZk5zMjOqz1cfn7ettXC4_lY57BalIeBSm7XKPxLGl5oHg0a-EexKff8YyEs6HTaMrcUsZiDrGGcO2dXhVdxnTfSa7XQTTGO-48t3G2YJ2bPG4N5XwgNAMo21DyIy6w21M8QiNBZjgGClsXQ3K8CqmgR7voa1wF9eJRUaPOXN2BnsmLbhDa_FsLtWr1BFWER88Aof29gmrottcUEJQC2mCt_OhE6_LeitEsf8sR2wQdDqY-rZ1gYW13M4ipb3gK31vj3u2lqk3jEiYkXDQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7fab6963-23e9-4446-b6a5-22ad340fc4fc","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"d339ba49-f3ff-4df9-aac6-1d2c1b8c0745","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 82e36f06-15c0-4cfd-bcfb-46a770f0d3af

{"observation_ref":{"entity_type":"observation","id":"ccc9b001-ebb9-4e2a-be9a-06c6c0355ae6","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"7fab6963-23e9-4446-b6a5-22ad340fc4fc","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"d339ba49-f3ff-4df9-aac6-1d2c1b8c0745","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"82e36f06-15c0-4cfd-bcfb-46a770f0d3af","code":null}
```

## Exchange 6 — tests/vnext/test_capture_transactions.py::test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected

Native record: [runtime/9e3edd3a9f52/http-exchanges.jsonl](runtime/9e3edd3a9f52/http-exchanges.jsonl), JSONL row 2.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjhkMjBlNTJjMGI2NDE0YWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6IjQzNTFiNzVkLTBjMjktNDI0Yy1iYzM5LTZkYzlhODYxY2M1ZCJ9.moVlJJe3YNcr_P-L47tAK9D0Hb-t9oWFuITjtRfviM83Kv-mV1m_exP6Ao8yDWy7zv-7uZk5zMjOqz1cfn7ettXC4_lY57BalIeBSm7XKPxLGl5oHg0a-EexKff8YyEs6HTaMrcUsZiDrGGcO2dXhVdxnTfSa7XQTTGO-48t3G2YJ2bPG4N5XwgNAMo21DyIy6w21M8QiNBZjgGClsXQ3K8CqmgR7voa1wF9eJRUaPOXN2BnsmLbhDa_FsLtWr1BFWER88Aof29gmrottcUEJQC2mCt_OhE6_LeitEsf8sR2wQdDqY-rZ1gYW13M4ipb3gK31vj3u2lqk3jEiYkXDQ
connection: keep-alive
content-length: 1062
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{
  "completeness": "complete",
  "conditions": [
    "fixture bytes"
  ],
  "evidence_origin": "fixture_capture",
  "received_at": "2026-09-13T00:00:01Z",
  "observed_at": "2026-09-13T00:00:00Z",
  "capture_layer": "fixture_file_bytes",
  "artifact_refs": [
    {
      "id": "7fab6963-23e9-4446-b6a5-22ad340fc4fc",
      "version": "1",
      "sha256": "9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"
    },
    {
      "id": "d339ba49-f3ff-4df9-aac6-1d2c1b8c0745",
      "version": "1",
      "sha256": "c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"
    }
  ],
  "tool_attempt_id": "attempt-fixture",
  "tool_call_id": "tool-fixture",
  "identity": {
    "tenant_id": "tenant-fixture",
    "project_id": "project-fixture",
    "task_id": "task-fixture",
    "work_item_id": "work-fixture",
    "agent_run_id": "run-fixture",
    "receiver_id": "receiver-fixture",
    "execution_epoch": "1",
    "run_epoch": "1",
    "runtime_attempt": "1"
  },
  "capture_id": "capture-fixture",
  "schema_version": "wuji.capture.v2"
}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 472a0b2c-0f30-4caf-b753-1812bf57b501

{"observation_ref":{"entity_type":"observation","id":"ccc9b001-ebb9-4e2a-be9a-06c6c0355ae6","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"7fab6963-23e9-4446-b6a5-22ad340fc4fc","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"d339ba49-f3ff-4df9-aac6-1d2c1b8c0745","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"82e36f06-15c0-4cfd-bcfb-46a770f0d3af","code":null}
```

## Exchange 7 — tests/vnext/test_capture_transactions.py::test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected

Native record: [runtime/9e3edd3a9f52/http-exchanges.jsonl](runtime/9e3edd3a9f52/http-exchanges.jsonl), JSONL row 3.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjhkMjBlNTJjMGI2NDE0YWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6IjQzNTFiNzVkLTBjMjktNDI0Yy1iYzM5LTZkYzlhODYxY2M1ZCJ9.moVlJJe3YNcr_P-L47tAK9D0Hb-t9oWFuITjtRfviM83Kv-mV1m_exP6Ao8yDWy7zv-7uZk5zMjOqz1cfn7ettXC4_lY57BalIeBSm7XKPxLGl5oHg0a-EexKff8YyEs6HTaMrcUsZiDrGGcO2dXhVdxnTfSa7XQTTGO-48t3G2YJ2bPG4N5XwgNAMo21DyIy6w21M8QiNBZjgGClsXQ3K8CqmgR7voa1wF9eJRUaPOXN2BnsmLbhDa_FsLtWr1BFWER88Aof29gmrottcUEJQC2mCt_OhE6_LeitEsf8sR2wQdDqY-rZ1gYW13M4ipb3gK31vj3u2lqk3jEiYkXDQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"d339ba49-f3ff-4df9-aac6-1d2c1b8c0745","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"},{"id":"7fab6963-23e9-4446-b6a5-22ad340fc4fc","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 409
content-length: 163
content-type: application/json
x-request-id: f1666035-a485-4076-a722-9be63cee0697

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"f1666035-a485-4076-a722-9be63cee0697","retryable":false,"details":{}}
```

## Exchange 8 — tests/vnext/test_capture_transactions.py::test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected

Native record: [runtime/9e3edd3a9f52/http-exchanges.jsonl](runtime/9e3edd3a9f52/http-exchanges.jsonl), JSONL row 4.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjhkMjBlNTJjMGI2NDE0YWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzNywibmJmIjoxNzg5MjUwNDM2LCJleHAiOjE3ODkyNTA3MzcsImp0aSI6IjQzNTFiNzVkLTBjMjktNDI0Yy1iYzM5LTZkYzlhODYxY2M1ZCJ9.moVlJJe3YNcr_P-L47tAK9D0Hb-t9oWFuITjtRfviM83Kv-mV1m_exP6Ao8yDWy7zv-7uZk5zMjOqz1cfn7ettXC4_lY57BalIeBSm7XKPxLGl5oHg0a-EexKff8YyEs6HTaMrcUsZiDrGGcO2dXhVdxnTfSa7XQTTGO-48t3G2YJ2bPG4N5XwgNAMo21DyIy6w21M8QiNBZjgGClsXQ3K8CqmgR7voa1wF9eJRUaPOXN2BnsmLbhDa_FsLtWr1BFWER88Aof29gmrottcUEJQC2mCt_OhE6_LeitEsf8sR2wQdDqY-rZ1gYW13M4ipb3gK31vj3u2lqk3jEiYkXDQ
connection: keep-alive
content-length: 878
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7fab6963-23e9-4446-b6a5-22ad340fc4fc","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"d339ba49-f3ff-4df9-aac6-1d2c1b8c0745","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes "],"completeness":"complete"}
```

```http
HTTP/1.1 409
content-length: 163
content-type: application/json
x-request-id: 44eebecb-16f5-4a26-8da5-59b984b19fca

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"44eebecb-16f5-4a26-8da5-59b984b19fca","retryable":false,"details":{}}
```

## Exchange 9 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tenant_id-tenant-other]

Native record: [runtime/270a0d05cd18/http-exchanges.jsonl](runtime/270a0d05cd18/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjA3ZWM0NmRkZTBiYjFkYmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzOCwibmJmIjoxNzg5MjUwNDM3LCJleHAiOjE3ODkyNTA3MzgsImp0aSI6IjFhZjBjZTRkLWM4MWMtNGM5Yi04NzgwLTg0N2Q4NmI2YTg3ZiJ9.TeqNXMWAYVxEPhowZuGmS0mFJbvPP_8dEcEm57WNHqH4243YnEQShxr9zCbLgtngAWiSBm40DKQ7U3hEQaPLk5_pthb8RKVUDX3Ro2BXWIcrIekfz2sQ_KkaeAlC87ZEcdS8MEJplQGx9LyCV4jxZEVz-uqmgCYChg3D5ZMFy1TTp9AfB0QuhpeQKGsiuu2nsx2qvgs07t6V64j0lB9cMW7Grvp26RJZ2J32uOjCiSu0k2Y1vXJpWUKwEDRccGHMM_MwxoQB97Cs8H986v8Im8Le6yfjvJtmazrt8iM1KVab7I7R44kdZe-T5WHyPGN9kbucLlc4kVrVw9HBBX2Orw
connection: keep-alive
content-length: 875
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-other","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"c227c0ce-76f0-4872-8601-bf657ae22626","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"4ebbeb6d-ec60-4d4f-9c4f-fd6e912b2411","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: c8552deb-0619-4cf2-9095-47493b9501a7

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"c8552deb-0619-4cf2-9095-47493b9501a7","retryable":false,"details":{}}
```

## Exchange 10 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[project_id-project-other]

Native record: [runtime/8d0c9337ec9c/http-exchanges.jsonl](runtime/8d0c9337ec9c/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImRlMDIxOGRmN2Q3YWM0YTQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzOCwibmJmIjoxNzg5MjUwNDM3LCJleHAiOjE3ODkyNTA3MzgsImp0aSI6ImNiYTU1NTBiLTk1NDYtNGIyZi1iMzcyLTQzMmI5MmFlMDJhYyJ9.bXSoOSOp6GP_gTLVRmw5iFXSiPC-qlkDl_c-QIh7jGqVLgtKBVkO9R43TBtzKoCO3HeVSSksbSURZfu2wfPxe_eYpURtepA55vqHN7QL-CewfRY0qL_-R5hA1ZGwX84bojYRjAKCkPyMIxYiejixWOmSldSC4t8MUz2G5Llhxwhukfx5S4YvyKVq5MH0uIRFPyxrQnPZuAudPSIedQBYIlua3HS7fxqrNJQechxQsCt1pJefCasEEuumjCYDEv0yuaflmYiE8TTfGP-J-q4WsPyssdceKX7mtfWQOcYAN_7MndFAXeTPe6Lqr1IHJ8Nrd9Do-m0WQao5419ow-16tQ
connection: keep-alive
content-length: 875
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-other","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"8ac6008d-bc94-4a56-85f3-d35e71847c08","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"8aebf861-065a-4a19-97fa-d354c5565f93","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 4b88f425-7116-42e6-b3ae-815f95199711

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"4b88f425-7116-42e6-b3ae-815f95199711","retryable":false,"details":{}}
```

## Exchange 11 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[task_id-task-sibling]

Native record: [runtime/8d53de33f0ad/http-exchanges.jsonl](runtime/8d53de33f0ad/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQ1YTAxNWUzNWJhMTQ3YzgifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzOCwibmJmIjoxNzg5MjUwNDM3LCJleHAiOjE3ODkyNTA3MzgsImp0aSI6ImU4ODk0MTgzLTM2NDYtNDM2MC1iNjYzLWM2OThjOWExZTg1NyJ9.iTrz3NOlbnQJllkjXkmjTiw4Ls3mz2CM8nVDjTSCzrQCEtbgsqb3A_CRdoUJc8JwAdan67byUB_2HK-qlSYeWlJHpfxPUZnsJ23266kcaBLZ7r0lnJ0dk24t088xNv1zsJXpy6yYfVYlkUmfvD27glAwmT2U3_5LGZDdb8dRBRFjoeM2AjZjngSNcb_Kc99shJCMAOqSk11rd4B3zVIXui7-hbs5JcEWH9Gt7P8Bj7DyDEM3TeE5D4WwhKjnOXDL9F5d5aCtIqYXGnZAz4MTMA_Lgct63bHQncEiyoZImr7J0QCsgDe8vbjDj14k1rIQByaH_6_oXSYEf4AtCFCIgA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-sibling","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"c7a94899-76e5-4dd0-b181-6f1fe716b297","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"ca31523c-2769-42a6-af09-cebab646734c","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: c43fd6fa-143b-4985-b419-9a7edf9828be

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"c43fd6fa-143b-4985-b419-9a7edf9828be","retryable":false,"details":{}}
```

## Exchange 12 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[work_item_id-work-b]

Native record: [runtime/eb52adb1519b/http-exchanges.jsonl](runtime/eb52adb1519b/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjQxNWExNzRmYjFkZTFlMzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzOSwibmJmIjoxNzg5MjUwNDM4LCJleHAiOjE3ODkyNTA3MzksImp0aSI6IjVhOTM2OGU4LTM2MjItNGNjMS05NzE0LThiMGFlOGUzZDJhMyJ9.SQE35GhEZUDNZ8ZfxyL0jL8wTulFjEusUwUwe04UaCN_1EMMGEF2NtuZpSDjRSA87olp0bsS0SOwgvAoy9-gDOvK3IiuMiFa3SSN8_z8vteyuHtfYYXax92A9XkYuONezQSmReFgqdMVguRQDXyHiuI18rm3yU1Rfa_IgeWHAnlplbI4D_RwSrr8mQgb_b_Tnc5tNLmb0uHI1D462IPIvyn6-pLg-VG2Rjjw0Hu4RWkI7fKlp2vDh2zIwHe7zsaneQKOTVRfRE2VaUuFQOTU0b2DqnT9KjotstLhJAXzSZmtY3XJ-LEESL6EhxtTA7jWmUQ_piUTeKRThCz__RJXqg
connection: keep-alive
content-length: 871
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-b","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"657e2d7f-3167-47f5-8c60-73e84fcaa15e","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"ff0bd485-a12d-40be-ab14-63ca6ac2863b","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 424541d8-e46e-4348-b3dc-7c3d7ce41b92

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"424541d8-e46e-4348-b3dc-7c3d7ce41b92","retryable":false,"details":{}}
```

## Exchange 13 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[agent_run_id-missing]

Native record: [runtime/4f7e764b079e/http-exchanges.jsonl](runtime/4f7e764b079e/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjA5MjE4NGM2OWE0YzE4MmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQzOSwibmJmIjoxNzg5MjUwNDM4LCJleHAiOjE3ODkyNTA3MzksImp0aSI6ImU1NmM5MWU1LTE5MWMtNDIwNy1iN2U3LWIxNDJmOWZjMThjYiJ9.IRAUIWJeSvqhPegMBsMsPGx4Y05s08NUcmR_LVSg7hYY4LGHZDC4p6mx8JpQNR__y5GC_jLRKPJLvUwl2ANDFWaFiT12j6SPrsmsAqMhrh4LKJclj5s16ktJgOjzCj9dAkOPsKsC5y2gcOmHIvChJj1U0W_PSxQmw-6QqPQOcOIoRtmEkC5BIOi_ICbcRpBbcarpW_bEpyZO9RUZib1XxXBBidr4qUMZeDEKo4SL2bABIhw4edYgvxqC3f8FtHmzq3RxQCGghc0RasPrtiiRX_J74DrFg6BiG4k2MW9k61zvbBWYESeI3CcBqwU7j6-laE6gtNksciYBwxNThzw4MA
connection: keep-alive
content-length: 873
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"missing","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"73688506-a5d9-4234-8cd3-f43726f97dd8","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"b5fbcccb-6c52-4b30-9b5e-5359da1c2b4c","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 99cf5368-3b8e-47b2-b28e-f634084f6a47

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"99cf5368-3b8e-47b2-b28e-f634084f6a47","retryable":false,"details":{}}
```

## Exchange 14 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[receiver_id-other]

Native record: [runtime/972bc6be6082/http-exchanges.jsonl](runtime/972bc6be6082/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjBhMmM0YTI1MDFiYzYyY2IifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MCwibmJmIjoxNzg5MjUwNDM5LCJleHAiOjE3ODkyNTA3NDAsImp0aSI6ImI4Yjc1ZDUyLWNlMWMtNGQ5My1iYjI2LTY1YmZlNzcxNzkwOCJ9.OobPkQfRcQUVhHrbZtyN99Onm1HV5xvcFMokFkJzbYg6ByIfwvyZKbKY-uDQ_kLlMVLFsK85JG6BuTn9ymudhh6Wweb1C5uPDXY2rDkYNA-VbD_CUCew6EjzjI3KWRCwYpq9XscTeT21lVhb_9TgjTl_FjgpB0ICBhFNHOz34BtsHcllzByXxwWF16q-RQWcLPx_bQaRl0x7JJG6MXwoXRyyM1dCIkxK2a3OpMgy1GhP7e0wBx4H1XFFKMyiprDU3vOcXhSfegjHWPIkGxuJzy8ElXcWhmvigVff2TgYm0E9tED1V5ODfYxaldHLS609QFXAaVKEOOwh5KT2Gr-sRQ
connection: keep-alive
content-length: 866
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"other","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"f5ec5a21-e5ce-4fb5-bf88-54af3ac141a2","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"2f17043e-d42a-47a6-8ec2-f62cba0a84f0","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 46a1d919-3b03-497a-a229-0c53e57e4bb4

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"46a1d919-3b03-497a-a229-0c53e57e4bb4","retryable":false,"details":{}}
```

## Exchange 15 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[execution_epoch-2]

Native record: [runtime/213ce6f0460a/http-exchanges.jsonl](runtime/213ce6f0460a/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEzZWRlZjJkOTk3MDViMDkifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MCwibmJmIjoxNzg5MjUwNDM5LCJleHAiOjE3ODkyNTA3NDAsImp0aSI6ImVjZDQ2MzgzLTEzZGQtNDM1Ni04YWMwLWNmNWI1NTU0ZjhjNCJ9.FCDYdgCTHZ02L6cKwfuCfDMnNWvCyOZw_CqJH0_ZZDam_imGnU4K0bryYGbe0LoNGwYHvnv0bdfvRQk6nGPUf8C_7kMYhQTdHuh7gRQSEiuUrcMmxw8rVJiqButpkS8Gh2r73MO5tCNk_bSujxziZ8_L0p2xggyiyt7jXpSsK31HqNx8zJKe9yrmfTxIJS8CufARkD0WElvx_YhaP3Aj-bf_POXYDNNeqy3lsNxpF0wtclTwvZyTlsl-A1humxnctkWPTkOPhiN4jQD998JvKu3vH-jQ-3df6bI03whAeefaMiEFdi-cg5KLZeF3DVv0NOJkQLwT7errzlWnnza4gQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"2","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"359ea1b7-bcd2-40a8-bbe1-35691ecc7944","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"99d633f5-1ece-4d4f-8378-8c594ada3ad1","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 8601f777-e8cf-43da-9a64-99fff71f24ed

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"8601f777-e8cf-43da-9a64-99fff71f24ed","retryable":false,"details":{}}
```

## Exchange 16 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[run_epoch-2]

Native record: [runtime/72180197b536/http-exchanges.jsonl](runtime/72180197b536/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImMzODI1MjY3OWFiMmI3MzEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MSwibmJmIjoxNzg5MjUwNDQwLCJleHAiOjE3ODkyNTA3NDEsImp0aSI6IjE5ODY2NGI0LTgwNzctNDZlOC1iYzA5LTU2NzRiZGZiNTkwMyJ9.g9-6By2plXg-veh7JEqWjBBaYEv4SLtvEpRAFQdVR-oGsLNMIoUV65_5Dd3Ni3vFc-tM7vxxMAmSFivQfhGDJ-9qLM7cLUOtiaWynDIv5h4QGhbg-NKfNIS_BJd3lL_Qf1ZljepSyGkpfAMv868zIJ9L6L_YbZRixoAfIcCl2bFMnASYxQZcvtXScaGZjSf5ZTgvmILjzwURl8aIgQtRh4cQaB6zg79-S5Sw2GJXvRXAJlZO-3-oy56RkzfXuQ7V_CjM5V98eBHysVci3a-MEt2-ND7j5a-rCppINyLQi70j1r1yUcgKZg5VOODujLr5FMGyU5xfDsjmY3ehxhXgqw
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"2","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"259ce630-1ff4-4370-89ad-7b7dc6bbb25f","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"1af32318-d4db-435a-a98e-cb03cb0f8e3d","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 2046bef2-883e-498f-bf3e-a2bdce58d7fd

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"2046bef2-883e-498f-bf3e-a2bdce58d7fd","retryable":false,"details":{}}
```

## Exchange 17 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[runtime_attempt-2]

Native record: [runtime/b19c920c7657/http-exchanges.jsonl](runtime/b19c920c7657/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjYxYzJlOTM0OWYyNmVkYzUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MSwibmJmIjoxNzg5MjUwNDQwLCJleHAiOjE3ODkyNTA3NDEsImp0aSI6IjEyMzMwNzczLThlY2EtNDc0Ny1iOGRiLTE5YWVhMjdjODgyNSJ9.oboBr75n1EIWBRxdQmHk-_U5G09tj0fZ1iZEVjFp5OXTySAXGWZXivuwTqCkZDizPzILimf4CY5aYOws1iLK0RGy4M9DcgscRo9ddxqMz6K4vTHsAVjGkkxabOEGXBPAGXtvRuMEBRCobt-OHTkMO_iDSOyiuod4nEKz89NW4lDdUj73MNKJoVy1FB5RTYEgE2GpD9r3kAVDf7SxIX2aOzqrJXF7yuYTSih1FqID8qMTeiecAJBG5CLFVLGNsSHvgkkYssxlklhnztVKH1ZTsXa9a0ZnXLJPhhQ1JS3GY6K2BVQOccvZ9OXaMzf0zlXG9TK_WU2Zr4wuFB1skLC7Rw
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"2"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"086ab627-e460-4915-aa39-525bba832ffb","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"91e991f4-f668-49d5-92b6-00ae5f4b8f59","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 0e3ca9c7-63ef-4bf0-8ac5-be543b70cc1d

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"0e3ca9c7-63ef-4bf0-8ac5-be543b70cc1d","retryable":false,"details":{}}
```

## Exchange 18 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tool_call_id-provider-opaque-call]

Native record: [runtime/9cba1bca4093/http-exchanges.jsonl](runtime/9cba1bca4093/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjczNjg1NmM2ZDk1MTY5NzAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MSwibmJmIjoxNzg5MjUwNDQwLCJleHAiOjE3ODkyNTA3NDEsImp0aSI6ImQzNjhiMDY1LWU3ZDgtNGNmOC04NGEzLTVjOTRmMDU5Mzg1MSJ9.CyavGiISDi7yYTen-S0pR8ac-IlrNJT80FgxyLBIeWU-YwTki8_Qb4-FMKV6qssNaHhrE9M8jzMSJTWf4dFkthq_wD4WE6Wf7tw_mxlDnAI1T-8kAWSH94M9xOMea7FN-eOHxeCCv6FIeAq5bf3TtwdWoU4i-0eYu49PUuce16uhsPE7gkU_AeKQqgkRd9TDMw9yt-rRKqg24BlgHVtI1XUTyBW5uH4Fv1-iEW5sdoM5vgUCNLSdLDaDRdSI2BWHEwpWaqEgtkFowhppH2DhDGBbt05sJGkLv2wReOAA9LkLlycpjGMCit1hgld4PxjJwHVOUdVtiIpCOiLJXm13Ew
connection: keep-alive
content-length: 885
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"provider-opaque-call","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"f65af1cf-e27c-49a0-b564-7b2feed69664","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"c9e30ad4-4393-4c5f-a6db-4dfdfb9d01c1","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 98637abd-ebd8-4f4c-a083-1fb5f2018bb9

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"98637abd-ebd8-4f4c-a083-1fb5f2018bb9","retryable":false,"details":{}}
```

## Exchange 19 — tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tool_attempt_id-missing]

Native record: [runtime/4f0f6f2d0cbf/http-exchanges.jsonl](runtime/4f0f6f2d0cbf/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjRkYjM1NmZkMDBiZTMxYTAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MiwibmJmIjoxNzg5MjUwNDQxLCJleHAiOjE3ODkyNTA3NDIsImp0aSI6IjQwMWVjNTUxLWM4OWQtNDZjMi1hM2E4LTMxZWEwMWRlNjgwZSJ9.Wrm5rcMNVbYfiAxuPzaYUlxgEh_3TlvgGEWjDJFBkT4j4xgBc4zHKcwZW1-z1Lnn2LnZ02BSRqGs7wh4sZqQcS2q5ejHwTJP6lyYc6pNtb8DLdUD9Agp5F4UxHmcKBWT7JqA9i1XuI271_o9XOZu096k1hg-SwDbC5VA-b2r2krciheaiZGzQGSDA2zm--RBa5lG9khy8A6mp-_8BmhwDVISQgD8SdUW7zoYj9P9mNSGXpCN51nBtxhiRXg_iRZtwMMJLmSV-rVghCHKjoBcxugc0vLKLh-nCsSi5_EBJVIQmpIyrw0WCZ1Zd9zcsNiaY7RFCCO3d0Z7hU2htfDiVQ
connection: keep-alive
content-length: 869
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"missing","artifact_refs":[{"id":"e5b120ce-ee36-44cf-95fc-0d53a76c5e0d","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"1b200d4b-ace0-4771-81a5-411b414fc0a5","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 161
content-type: application/json
x-request-id: 68802556-a6ce-4e2f-8c7b-277a850d1a0f

{"code":"FORBIDDEN_COLLECTOR","message":"The request could not be completed.","request_id":"68802556-a6ce-4e2f-8c7b-277a850d1a0f","retryable":false,"details":{}}
```

## Exchange 20 — tests/vnext/test_capture_transactions.py::test_evidence_requires_capture_id_as_idempotency_key[None]

Native record: [runtime/f9e292d73da2/http-exchanges.jsonl](runtime/f9e292d73da2/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQ5YmI4ZGNmODA5ODY3ZTUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MiwibmJmIjoxNzg5MjUwNDQxLCJleHAiOjE3ODkyNTA3NDIsImp0aSI6IjQzZWQ2NWI4LWYzOWMtNGM0MC1iMmUzLTcwMmJjZjZlMzBkZiJ9.0eePp7qC8se57ie3cXA0UnD4pgBvxFrSs_cC3Kf_kR_9gzLkQzj8klNhRGRma--hIemClHI7KS_lOhrriCBaTmwHlCSwShhAgFVZ9dtSsdXLs9rpsmTVUzg0Dgk1ef3CHR08hYLG3Z-CO7pNXKe_bnOZ0o7Wz8wohSHnL9WxFsxm2NOtHA4VCQLVHh-9gxCPcxlCX_6OBsMjHGsnzH4I9ULXmI0OmC3Olea49RicT_UT2fbEpsSya2gktkKPF8X4PzVrzy_RJnn3W-LcQDhaspCSi8uzQy3jcfk87OoyQJcBJhGwvSqW3tRZ3zRs634orpeg1swEdCmmpriYc1wqag
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"bdb7b6ed-0517-424f-9fc8-27187b95e48b","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"69a56668-c56f-48d1-b1e0-35926f5d7311","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 287
content-type: application/json
x-request-id: d6ab02eb-cdeb-40e8-b610-96a6be15ae8e

{"code":"INVALID_SCHEMA","message":"Request does not satisfy the v2 contract.","request_id":"d6ab02eb-cdeb-40e8-b610-96a6be15ae8e","retryable":false,"details":{"errors":[{"type":"missing","loc":["header","<field>"],"msg":"Input does not satisfy the field contract."}],"truncated":false}}
```

## Exchange 21 — tests/vnext/test_capture_transactions.py::test_evidence_requires_capture_id_as_idempotency_key[different-operation]

Native record: [runtime/239d0dd42efc/http-exchanges.jsonl](runtime/239d0dd42efc/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY5Nzc5MjBiZThiNDA4ZWUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MywibmJmIjoxNzg5MjUwNDQyLCJleHAiOjE3ODkyNTA3NDMsImp0aSI6Ijk4OGYwMmY4LTg2YjUtNGFhZi1iOWI0LTk5MDdlMzVmZTY4YSJ9.XrGZ6G6FtnIzBMGw1psGszzs2KQQdwrD0JRkhKYix8HtJxr4DJdwocPc5ysB6cK_sn1rymfPkcypi8usb8CI2C9WbvewW-EPwCpRlsirgJIn0fU2A1diDybQFjezSA6W7h4MvkIkmMMZuluCkIpkTBzPLvELy0W7pdtCUxvyRHTSF_vWe4wmDvegDruV8ZspETnKNYmvggGM_U_WXgsZE7bph0OiTCd99ZYz9Ocuei2CJwIu7ce4Fe_wD9d7povxTRCJk9sRqWGE7kBwxIwNHJD2b3Nzuxdc239AGHgeQZbAHALHrAJzDPrXaPXD0gFU-DUjSYi7iiDTDqLVtE7hmQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: different-operation
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"02a4c95b-6325-4693-8d16-a564d6086952","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"40f80918-7988-4d2d-86f6-45813e219881","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 156
content-type: application/json
x-request-id: f5812a04-bb38-4f66-a90f-7eacf971de20

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"f5812a04-bb38-4f66-a90f-7eacf971de20","retryable":false,"details":{}}
```

## Exchange 22 — tests/vnext/test_capture_transactions.py::test_replay_and_artifact_download_recheck_current_permission

Native record: [runtime/2f1b983ff2d4/http-exchanges.jsonl](runtime/2f1b983ff2d4/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MjNjYzc4NDI1NzMzNDUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MywibmJmIjoxNzg5MjUwNDQyLCJleHAiOjE3ODkyNTA3NDMsImp0aSI6Ijk0MDhhZjYyLTY1ODUtNDI1Yi04ZWMyLTIwOWVmMGRkNjFiZiJ9.MMpKB8s31deqkun5YKJ-zUT8g0JtaXL3rt0YAUqqKT9-bts8tBZOxy9OQ0xu2GqwTmKsIFxDvfdJqh4Do6tsM7tkDFxGZ1j5yNa2vgXO-PyC5nInOv8w9UBm0lusH6GVuTF82-PNwO4LiXxo1mPkFe0BAWAiy_WE7us6iS5cCc20kg15pdnTUoT7hoHRRL9hVGwKas9vztUJBA5rafeqEDkgZE97eR9KbJ1Y-YhiasCNAevUEauF1qyeVs3z8K0Fk_yj-jjg0TvVqZkiBuBzV2ZwMPKZRlnT3igo2DDDiriHykZ_0nwQIwOI-Xq90MikDobRTwLLr997ALDA9sLaWQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7551362d-b4a4-4b4f-83f4-4635abd76ca8","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"4f10889b-df6e-49db-9825-f7603da1a570","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: dd7b4ce4-aa37-4705-9855-6a179cf7ba58

{"observation_ref":{"entity_type":"observation","id":"eb227161-bc16-4ac4-8df4-d5323875ad11","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"7551362d-b4a4-4b4f-83f4-4635abd76ca8","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"4f10889b-df6e-49db-9825-f7603da1a570","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"dd7b4ce4-aa37-4705-9855-6a179cf7ba58","code":null}
```

## Exchange 23 — tests/vnext/test_capture_transactions.py::test_replay_and_artifact_download_recheck_current_permission

Native record: [runtime/2f1b983ff2d4/http-exchanges.jsonl](runtime/2f1b983ff2d4/http-exchanges.jsonl), JSONL row 2.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MjNjYzc4NDI1NzMzNDUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MywibmJmIjoxNzg5MjUwNDQyLCJleHAiOjE3ODkyNTA3NDMsImp0aSI6Ijk0MDhhZjYyLTY1ODUtNDI1Yi04ZWMyLTIwOWVmMGRkNjFiZiJ9.MMpKB8s31deqkun5YKJ-zUT8g0JtaXL3rt0YAUqqKT9-bts8tBZOxy9OQ0xu2GqwTmKsIFxDvfdJqh4Do6tsM7tkDFxGZ1j5yNa2vgXO-PyC5nInOv8w9UBm0lusH6GVuTF82-PNwO4LiXxo1mPkFe0BAWAiy_WE7us6iS5cCc20kg15pdnTUoT7hoHRRL9hVGwKas9vztUJBA5rafeqEDkgZE97eR9KbJ1Y-YhiasCNAevUEauF1qyeVs3z8K0Fk_yj-jjg0TvVqZkiBuBzV2ZwMPKZRlnT3igo2DDDiriHykZ_0nwQIwOI-Xq90MikDobRTwLLr997ALDA9sLaWQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7551362d-b4a4-4b4f-83f4-4635abd76ca8","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"4f10889b-df6e-49db-9825-f7603da1a570","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 164
content-type: application/json
x-request-id: 77b2cdd2-726f-4ced-94bc-082887a556d1

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"77b2cdd2-726f-4ced-94bc-082887a556d1","retryable":false,"details":{}}
```

## Exchange 24 — tests/vnext/test_capture_transactions.py::test_replay_and_artifact_download_recheck_current_permission

Native record: [runtime/2f1b983ff2d4/http-exchanges.jsonl](runtime/2f1b983ff2d4/http-exchanges.jsonl), JSONL row 3.

```http
GET http://testserver/api/v2/artifacts/7551362d-b4a4-4b4f-83f4-4635abd76ca8/content?version=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ijk2MjNjYzc4NDI1NzMzNDUifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJyZWFkZXItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsicmVhZGVyIl0sImlhdCI6MTc4OTI1MDQ0MywibmJmIjoxNzg5MjUwNDQyLCJleHAiOjE3ODkyNTA3NDMsImp0aSI6IjUwNzZiN2M0LTUxMzgtNDA4OC1hNzllLTQzMTE0ZjY4ZmQwMiJ9.SfIKwOkZ_j7hL9nzbzGp7jtWj1-YvbPbMZqxpFZjvwsM92O4W-lN8LmGjcRZO2HhrGGRZVE493TRDWaDjy-EwGpIhU_i6PP2qFboJtCqlxYOPJdDHhcrWJk32amoP-xyf-Cr-5mG9YqhtX2zR2RuHUV0q1hCfiiw70JXMg3lh21p0xO9OexYYEL2htW2bIElUo4spxmYgnSnvI9j5x8FrJJlS8Mx4ftiO87eaUhkF0sjMhzZOLfS7e5QwXvuSR12IYkKeWcDuFByYlW53fG2lnmTE991z85RyS_4UO7enYOyapkw_OIat_G7rBic42jIPlS60yWj9BTKJOsFmj7n6A
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: 9b454de9-c405-4417-8140-e337a366bf0a

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"9b454de9-c405-4417-8140-e337a366bf0a","retryable":false,"details":{}}
```

## Exchange 25 — tests/vnext/test_capture_transactions.py::test_started_late_attempt_is_historical_only_with_settlement_authority[True]

Native record: [runtime/eec3d370cd50/http-exchanges.jsonl](runtime/eec3d370cd50/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjE2ZGUxYzY3NmNiNDFhODMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0MywibmJmIjoxNzg5MjUwNDQyLCJleHAiOjE3ODkyNTA3NDMsImp0aSI6IjkxZGU0MmRmLTlkYTEtNGJlYS1iZjlhLTRhYjg1NTg5NTZiOSJ9.1UeyPQMjOZbihgb23blzsUzrA3wfipbF47KuxzYG-eYzvEdq3t-oHj08EhFOWe1PPA15jH_Cp5C0EKJQE2UfZPKCOpSk3R8ZJCTc2hdKYIrh8_Smjexy7nBT1FOUzmqZxqpfMRjNZ2H2NlL4AhyeyxqODJYG1X2ESsKWJ1bwYNsFQVRC_cc2jQQWBBXQxejccuz-wS4G6CJGD6h1IrYv0TBoapxoRlKbsdkczTaXrmDEEsUwY-c5_sjKjf5SwMkKpuWF1bWemnD4FAkg4FvUf7clWfbbMvi5o2R6ctsC5tITj90OIV5L0vQOi1FZY2yFPySO0J3xo1W2NIWylmbL2g
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"e60ca4ef-9c1c-4871-b9ec-b18509e2838a","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"86537662-6b8c-41da-8c91-2587aeb446c5","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 520
content-type: application/json
x-request-id: 25a10a06-2b21-4f19-9167-acce1ad8def3

{"observation_ref":{"entity_type":"observation","id":"a0ff8a72-a990-4d84-93eb-083ec9470d6a","revision":"1"},"capture_id":"capture-fixture","status":"historical_only","artifact_refs":[{"id":"e60ca4ef-9c1c-4871-b9ec-b18509e2838a","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"86537662-6b8c-41da-8c91-2587aeb446c5","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"25a10a06-2b21-4f19-9167-acce1ad8def3","code":null}
```

## Exchange 26 — tests/vnext/test_capture_transactions.py::test_started_late_attempt_is_historical_only_with_settlement_authority[False]

Native record: [runtime/02a194da39c9/http-exchanges.jsonl](runtime/02a194da39c9/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImY5ZjcwZjZjOGJlYjkxYjAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NCwibmJmIjoxNzg5MjUwNDQzLCJleHAiOjE3ODkyNTA3NDQsImp0aSI6ImYwOGNlMzNlLTRhODgtNGYwNi1hOTlhLThjZTQ1MjE2NWMxYSJ9.G_WMDASpWDV47v9vuJTS4yVlR_fKqhM-DSNYTj5R8H9IhBg6Z4OmNRj4aGZdSat8q_vi2u5mRAD5_kImpMq1a9AJoLN7UnYqM7GiS5TwzZV2dPLTJuW-ANCYdggAnUv_HdsW3PkD1sBgjO4jjJfRQb3OjvfoIfGFHi-EE816NHlOkCWHjFwyqdSZrWsMdzcdn2fP48uN5qNtynx2Pk9OYLkSUVC0kslt50nOOL2GCqEpWYiV2L__ceot81cueCRG921Ktxg7FBv_TrzAayzqn7l9_eEGbepZcxR-wmp-jQwOS58egWPU-B7I-SpU6kXiFGX4YJHe7bkFBW6DO_cFyg
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"2adfb41e-183a-4911-aa31-f63dbadf8c12","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"6db72a5e-3743-4691-901f-4b6eafcc2eac","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 157
content-type: application/json
x-request-id: bd2b7fca-d550-4345-b37e-612cc82c41bd

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"bd2b7fca-d550-4345-b37e-612cc82c41bd","retryable":false,"details":{}}
```

## Exchange 27 — tests/vnext/test_capture_transactions.py::test_capture_rejects_missing_or_changed_actual_bytes[missing]

Native record: [runtime/2f8a46ddca2b/http-exchanges.jsonl](runtime/2f8a46ddca2b/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjFkMjAxOGQ1MDM2NGRkMDIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NCwibmJmIjoxNzg5MjUwNDQzLCJleHAiOjE3ODkyNTA3NDQsImp0aSI6IjU2OTU0NWExLWU4OTktNDgwNy04OTI1LTUzNjQ3ODhjNjc0MyJ9.nNF345ePoujt-n82tOIlZ6m4VXv94kngM0zLXZLgKBHDz04QdTOnhqw5paeG0RmtZyh-OLCcsAOmBIyQwnm_G_7PamAXsMNSgPZzvbsZ0yVUCl0AQmXIYtAvaeUGok2kUI0M8z_5Dntzo3KXM7Hee8EaRogaDeDWYx_qzDyBIy5nOkB_bOtz-Vq_ECCvbGSRKYN5O7eMn8WHg3JpdQw60Iv7TvNP94SS0FOijsSkPxpZZ7aO0r8HEDILGIULoCaL3-a7-1GC8ShhjOs-eLiREvoh2xS02SE_epAzDYP6e_ma2csHYDqjS49O2NKCEci9AFaoW00UwcN2_KRC37hqoA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"b9f67c1d-fe00-4d62-93d3-a621e0b239ad","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"c68aa47d-e946-45f1-8b22-1d2f1c30b919","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: 81e18465-b7ac-4b36-bdd0-f3ff70928c8b

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"81e18465-b7ac-4b36-bdd0-f3ff70928c8b","retryable":false,"details":{}}
```

## Exchange 28 — tests/vnext/test_capture_transactions.py::test_capture_rejects_missing_or_changed_actual_bytes[changed]

Native record: [runtime/f6f93410ab95/http-exchanges.jsonl](runtime/f6f93410ab95/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjI3ZjhiNzE5NjE1ZTdkNjIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NCwibmJmIjoxNzg5MjUwNDQzLCJleHAiOjE3ODkyNTA3NDQsImp0aSI6ImY4MWNiYjMwLTM1ZjQtNDYyMy1iYTM3LThiM2UwYjg1MGUyYiJ9.MdMEICHT9vhJ2Vmf9kDXZH9WbDzm_TMGfMHERzfR0ca9nuGq4Xe8G7WYGg_1uVVq8meTKWmBZKP-LMTw_8YxHvV1pz0H_psQHwerrqX8RzSiWp33n0IlacIu_veXmS7gsN7OdoTufRbIsFwVABsNb-pRUx1ljL89RFt-3Cj9OGcEBmcYfdeDvdzPIlg_qq9AZAgFKb-r8ME-N-LtaGWfrSZXfU0dcPy5uPZSNEnfBq1JaqI0VWHpsVOgf7XdJqGrIlDCcUBbyZtXcJnxpYBI6X6iMQYDP5NvJ2bJrnRsMwl4muLbnEospDrg3lMd7eBALR3Z49CylQQknBAspans7g
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7319b9a0-c6b2-46cc-99c5-d4a2a95b46fd","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"cc124ece-bfae-4746-83ac-cd4207ae5258","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: e2ce50fc-4e19-449d-9ce4-12cb45c62960

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"e2ce50fc-4e19-449d-9ce4-12cb45c62960","retryable":false,"details":{}}
```

## Exchange 29 — tests/vnext/test_capture_transactions.py::test_capture_publication_database_failure_rolls_back_all_domain_state

Native record: [runtime/502019a47492/http-exchanges.jsonl](runtime/502019a47492/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImYxYjk5MzM2YTkwZGIwZjYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NSwibmJmIjoxNzg5MjUwNDQ0LCJleHAiOjE3ODkyNTA3NDUsImp0aSI6ImE0NDFkNWU5LWEzYzctNGM3YS05NjllLWFkYmJhY2RjMTI1NCJ9.AOonMAXKKzWSjZOctahXPAOkjfbGDTwedZ9eeUqCT1gUug_EO-mFpfCsg_OFJ42DQO9c_FWChn-H5Thx-yM2zS32mpUjI0m19nQSTiLngR_t2GYtpBbK90Bs1Q-2WfuCQeYto0o7o8Tvja3fweqCgeNCSI0nkdlkHcbrKmcKGboQmD5dbXnupYFHd-9W9Ti8WcaAsJamJyXNycUJYDrIwtnU3ZBJU3VAY_PluLpl3wascVqC8q09Gjvz2bReBb4NxgvQCI9aLiMwLM5rwPzxl-D6uTnK2UVeOgAm1Vzkwm9wCpcj60tGy2CZzggrH4V8olAwiaKXdIgH7_Nea8_OEA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"fb55c579-73bc-49c5-8d42-280506c56bd1","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"7affa2d1-efa8-443b-97fd-e9d984a682cc","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 503
content-length: 164
content-type: application/json
x-request-id: 550d944c-d1fe-489b-a1cd-795505cbb403

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"550d944c-d1fe-489b-a1cd-795505cbb403","retryable":false,"details":{}}
```

## Exchange 30 — tests/vnext/test_capture_transactions.py::test_capture_publication_database_failure_rolls_back_all_domain_state

Native record: [runtime/502019a47492/http-exchanges.jsonl](runtime/502019a47492/http-exchanges.jsonl), JSONL row 2.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImYxYjk5MzM2YTkwZGIwZjYifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NSwibmJmIjoxNzg5MjUwNDQ0LCJleHAiOjE3ODkyNTA3NDUsImp0aSI6ImE0NDFkNWU5LWEzYzctNGM3YS05NjllLWFkYmJhY2RjMTI1NCJ9.AOonMAXKKzWSjZOctahXPAOkjfbGDTwedZ9eeUqCT1gUug_EO-mFpfCsg_OFJ42DQO9c_FWChn-H5Thx-yM2zS32mpUjI0m19nQSTiLngR_t2GYtpBbK90Bs1Q-2WfuCQeYto0o7o8Tvja3fweqCgeNCSI0nkdlkHcbrKmcKGboQmD5dbXnupYFHd-9W9Ti8WcaAsJamJyXNycUJYDrIwtnU3ZBJU3VAY_PluLpl3wascVqC8q09Gjvz2bReBb4NxgvQCI9aLiMwLM5rwPzxl-D6uTnK2UVeOgAm1Vzkwm9wCpcj60tGy2CZzggrH4V8olAwiaKXdIgH7_Nea8_OEA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"fb55c579-73bc-49c5-8d42-280506c56bd1","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"7affa2d1-efa8-443b-97fd-e9d984a682cc","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 4768ca33-2e1d-4c1b-8105-3679e48ef061

{"observation_ref":{"entity_type":"observation","id":"48e03072-d90b-471f-b980-b0c7d2856d82","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"fb55c579-73bc-49c5-8d42-280506c56bd1","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"7affa2d1-efa8-443b-97fd-e9d984a682cc","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"4768ca33-2e1d-4c1b-8105-3679e48ef061","code":null}
```

## Exchange 31 — tests/vnext/test_capture_transactions.py::test_partial_output_and_source_axes_do_not_certify_business_truth

Native record: [runtime/456024ef745f/http-exchanges.jsonl](runtime/456024ef745f/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEwMGFjYmRjYTJhYjQ3ZmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NSwibmJmIjoxNzg5MjUwNDQ0LCJleHAiOjE3ODkyNTA3NDUsImp0aSI6ImRiYTY3NzZjLWNlMmQtNDUzZi04ZWViLWYwZGFhOGQ5N2Q2NSJ9.TpSlDztNIZH-ivV0Jnqs83EQHxgomgMj_G-OBpfiYlvhExBanvgiBSvBgFgAcKAk12pB84rmbcc-geGbVo5ALOekAHsdewCCrfHKtdzYjnmzBWQgyxmj8fGpCYGwnXkSqvlt-gOO_9mP9hnng1gOnroL-9KNNcEshvrYwJi9nsWZDBMKut3LcZDmQYd7kSkEa4NzWmS6qp-DqxWTaU7X0W2yhc1SL-wTNu2QI1dHmljCMqx8oQAQSrT1RDAcCVKCRgey08Lr3NXsytzS9hqVigLuAqKbmc8_X_I742Hs3smcijzt0MRLqLKkB5_FJalqDXT6e93VeylZAk98a9JQLw
connection: keep-alive
content-length: 900
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"8856461a-8790-4224-aede-b6ef0c8b90b4","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"3cfb27f8-7923-4ffc-ba96-ad8a5a3ac86b","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes; remainder unavailable"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: 5c71666b-a544-4ebe-937a-4b5a6e02f9c2

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"5c71666b-a544-4ebe-937a-4b5a6e02f9c2","retryable":false,"details":{}}
```

## Exchange 32 — tests/vnext/test_capture_transactions.py::test_partial_output_and_source_axes_do_not_certify_business_truth

Native record: [runtime/456024ef745f/http-exchanges.jsonl](runtime/456024ef745f/http-exchanges.jsonl), JSONL row 2.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjEwMGFjYmRjYTJhYjQ3ZmMifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NSwibmJmIjoxNzg5MjUwNDQ0LCJleHAiOjE3ODkyNTA3NDUsImp0aSI6ImRiYTY3NzZjLWNlMmQtNDUzZi04ZWViLWYwZGFhOGQ5N2Q2NSJ9.TpSlDztNIZH-ivV0Jnqs83EQHxgomgMj_G-OBpfiYlvhExBanvgiBSvBgFgAcKAk12pB84rmbcc-geGbVo5ALOekAHsdewCCrfHKtdzYjnmzBWQgyxmj8fGpCYGwnXkSqvlt-gOO_9mP9hnng1gOnroL-9KNNcEshvrYwJi9nsWZDBMKut3LcZDmQYd7kSkEa4NzWmS6qp-DqxWTaU7X0W2yhc1SL-wTNu2QI1dHmljCMqx8oQAQSrT1RDAcCVKCRgey08Lr3NXsytzS9hqVigLuAqKbmc8_X_I742Hs3smcijzt0MRLqLKkB5_FJalqDXT6e93VeylZAk98a9JQLw
connection: keep-alive
content-length: 899
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"8856461a-8790-4224-aede-b6ef0c8b90b4","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"3cfb27f8-7923-4ffc-ba96-ad8a5a3ac86b","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes; remainder unavailable"],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 053fb125-bd6f-41fc-84f2-47e961accc3e

{"observation_ref":{"entity_type":"observation","id":"2b3599ca-7fef-4e45-9c78-02eacc4f38c2","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"8856461a-8790-4224-aede-b6ef0c8b90b4","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"3cfb27f8-7923-4ffc-ba96-ad8a5a3ac86b","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"053fb125-bd6f-41fc-84f2-47e961accc3e","code":null}
```

## Exchange 33 — tests/vnext/test_capture_transactions.py::test_model_or_imported_bytes_cannot_be_laundered_into_capture[model_output]

Native record: [runtime/0f9acdc2472c/http-exchanges.jsonl](runtime/0f9acdc2472c/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjdmNWNlMGIxYjI5NjNkOTIifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NiwibmJmIjoxNzg5MjUwNDQ1LCJleHAiOjE3ODkyNTA3NDYsImp0aSI6ImI5MDQyNDY5LThmNDUtNDcyYS1iNjc3LWI2MzRjNGZlYjYxNCJ9.BSLLjxMCDBWA0VA29CXZ6tjRevE5GO5KvoA6qo07j_N5gWEhQCNbYGlva1pUIaekTK6V7STAf2-b6ArBBMusKly-9xoYZC3yvldjydVVXgpQ_mdKnQq_jvotD8If8PRUUKYI1rq9KROES7uSm0uqM64L5abpTMKm9Mpqayc0lE9tTiBgl23Ebxv2nLMKPMtUd6oziYIE82qAWCVuI4RowFSOti_LsSbbZD6UHKjD4OsM_rf1NHGovm6dSWo4zBwlyuB--km-9DMPQbSc7fpVrzd8vEIqjN_F4AD6nBPKEQ9LfoEK0KYVn2-AaNGkPM0q-ZL-z34Y5j4O4KHklgbRvA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"e9ff8858-bf7a-4a57-856e-7d8d4cb7663d","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"ccbad9b0-4e46-494a-bbdb-79c09c035f53","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: d5dd9e63-6dcd-4682-8958-e5ae91fe2d57

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"d5dd9e63-6dcd-4682-8958-e5ae91fe2d57","retryable":false,"details":{}}
```

## Exchange 34 — tests/vnext/test_capture_transactions.py::test_model_or_imported_bytes_cannot_be_laundered_into_capture[import]

Native record: [runtime/461e82ce951f/http-exchanges.jsonl](runtime/461e82ce951f/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjNjOTk5N2EyMjNiYWY1ODEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NiwibmJmIjoxNzg5MjUwNDQ1LCJleHAiOjE3ODkyNTA3NDYsImp0aSI6IjM2MWM5MmZlLWM1M2YtNDljYi1iZDdlLWVjMTg2Yzc4YzJjYyJ9.bYC4vPgTp2owaDLnhhNA6IT2VZDdt8-8yC_LUdmtV0PEKNbJe4JAaZQXHO-vLOUK0C5IVtkorgIJy1wmHU4fcHFQyr6rIPQWnmivveMsQBaicISZvu5h20mrj80TDSFE9_H2vbX8VY88xmWkyo-P1hRD0gwaXSEW5vwMRtWNfJIJue9U1vEaHvXQKEpJiP8igavT1ZlPCaqtd_W4CCC7rOjoaDbjYkxSazl3NCjmTLY3VkCHxdV_h1eBSDPxtYSGbm56U0KNb6wFoL_AEo9CkHpMe5NGXucvZAKnlL-m3xv4PRZ0CDSLToTyip73V9aMP4tpZJDR_W-OLFUr7OqHbQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"4ecd88ee-83ff-4b1e-80aa-524532c9eb8f","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"9aebc5eb-5212-4f15-92de-df9758404946","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: 68ef60ed-f018-40d3-8856-3152c78a3cb9

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"68ef60ed-f018-40d3-8856-3152c78a3cb9","retryable":false,"details":{}}
```

## Exchange 35 — tests/vnext/test_capture_transactions.py::test_snapshot_pins_revisions_states_relations_after_connection_close

Native record: [runtime/055cbf137607/http-exchanges.jsonl](runtime/055cbf137607/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjI0MmUzYTg1YTcwM2FlODQifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0NywibmJmIjoxNzg5MjUwNDQ2LCJleHAiOjE3ODkyNTA3NDcsImp0aSI6ImJlMTE2ZWQxLTY2NWMtNGI3Ni1hZTI2LWRhN2Y4OTM5MGMzMCJ9.bVGrzOQhYSTVIZ9fxN7ovaq_l4RKFRPx1aWkjMsgfC2lbc7UTGXLArIjRZwllt8s68XmYr9YYsZQDprJO_fzZ9zTGrKTG5UcHX4Uzm7GBVWxU5lWzJJibxeKpA11eq3a55-aPtE1TqqlyhO3Ikt-KKrXk8LSQ2NMzTRiBMFWjxLNz7PncuLZB2-y9HSPM03MTwF7ef0Op0Q4Z4IJnwqWOYfxUEf6YIybTaFhkw7K7HDsN_PxtLx8Qyo6onejYlWp1IpyYqV7C32Zi-kQlaiWzntHaerwMcUABInQSVte5QpJeSWV5_nYMoRmrp6TG55Eoy7lKSBjHQQY8ZzM53W1kA
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"5ad00177-6a0d-4644-9277-08337f0b4e40","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"1fa89647-f52c-4dc6-a3cb-dba2257c079c","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 72df8534-1373-4bc3-ba13-dc9ef564243e

{"observation_ref":{"entity_type":"observation","id":"e3702b6e-f26a-4cc8-a953-115fb130fcbb","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"5ad00177-6a0d-4644-9277-08337f0b4e40","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"1fa89647-f52c-4dc6-a3cb-dba2257c079c","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"72df8534-1373-4bc3-ba13-dc9ef564243e","code":null}
```

## Exchange 36 — tests/vnext/test_capture_transactions.py::test_partial_body_and_complete_metadata_remain_one_partial_observation

Native record: [runtime/c7d42a7d7e66/http-exchanges.jsonl](runtime/c7d42a7d7e66/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjQ1MGFmM2YwZGQyNTUwMjAifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ0OSwibmJmIjoxNzg5MjUwNDQ4LCJleHAiOjE3ODkyNTA3NDksImp0aSI6ImQwYzdjMjI1LTI5ZGUtNDc4Yi1hMWYzLWFlMDkzNmY3NDcxNSJ9.ikxybUvDXsmBdWKVCLbhzCX0Ewq4bZODDqA4bI71LLMy33S6Hw-bCkHfENpJDtCF-IChAerSzrd6nlr2jx6UU7YnlkNNWBQAChoQMUD2D9Aaou0r0BObaJxKFGrFjCEKXyToz0YzvjiNyy0LfKmoP69ltTvbDxCSGZ-NcoxPheb5ya5QxCxvcNPDeL1ItnYrHypAJ3ZUHY-P6-z0n433HAqiYRFvH0Olowd2pF0uYh2d79kxYUC22bcJNruz8QH4WdPmuctDNLOHPadrDeyn3J2nfvNx7y9-DirQHaw6O7AG173aD-RFAEpl9HzDPdGNqtUwzTWzKdL0bzOIfVHlhA
connection: keep-alive
content-length: 893
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"1d049b70-c642-4567-88f8-9f783c44191f","version":"1","sha256":"d6d465a010aaa856300a61e8e1cadbdf9a33070af84523a751d5892d53f6fd53"},{"id":"f1b4b591-17f9-47a2-ae28-186242b86ac6","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes","body truncated"],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: be2ab5c1-8c29-4bc5-9aea-c052fdecd2c9

{"observation_ref":{"entity_type":"observation","id":"e3361f61-a60b-4b46-9ce9-2bf9cc233a26","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"1d049b70-c642-4567-88f8-9f783c44191f","version":"1","sha256":"d6d465a010aaa856300a61e8e1cadbdf9a33070af84523a751d5892d53f6fd53"},{"id":"f1b4b591-17f9-47a2-ae28-186242b86ac6","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"request_id":"be2ab5c1-8c29-4bc5-9aea-c052fdecd2c9","code":null}
```

## Exchange 37 — tests/vnext/test_capture_transactions.py::test_late_receipt_requires_a_trusted_start_record

Native record: [runtime/843ab2402eee/http-exchanges.jsonl](runtime/843ab2402eee/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImQzMzVhNzY2ZjczNTA4NTcifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ1MCwibmJmIjoxNzg5MjUwNDQ5LCJleHAiOjE3ODkyNTA3NTAsImp0aSI6ImNkNjFkYjE4LTMxM2MtNGRhYy1iNDk3LTI1MDdkYTJiODQ5ZiJ9.GJR6xWESpNr_rXXXQEVbaF-ghZVR8UrYPzTLhmzqGQ_nhzBHALSVAvgw6a3-PcIr-J3yyKUtFX0HrQhp4r1AX6naHU-xghlvQymcqFl5rUpGyvPaOEYcCJaoCmXNvh2iqiVfLNXjzCcOcG-XYVqz4nDhlEkyR-uytai5MX60FjEWq1SWAfy85GB7ehKBmnjcwuvHSuSKjeb_R0q84fmgPqZoZvd2kOvdFV7Qavk683go1dI9jja_VmzMGadmbSnct9V_loZ9sPjepXLqSCTMPo96RMy3hzF9nPeCtPCSg12s0nMiYPf73ToCiHrwiz3qedsB3_Nb4pf0wLLwuN5m0A
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"cf3ede6c-cadf-40fd-a5dc-541ac9c2919d","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"2fe3181d-c942-4c31-9613-887f88cc25e7","version":"1","sha256":"c254960b9750fe3d4d5d833ce8b21042038b3f92b95def612c5e7fb71ab68403"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 403
content-length: 157
content-type: application/json
x-request-id: f4370ac5-311d-4c43-b18d-a2cf00e1ab49

{"code":"STALE_EXECUTION","message":"The request could not be completed.","request_id":"f4370ac5-311d-4c43-b18d-a2cf00e1ab49","retryable":false,"details":{}}
```

## Exchange 38 — tests/vnext/test_capture_transactions.py::test_private_publication_pin_protects_visible_bytes_from_lower_clearance_gc

Native record: [runtime/e49663aa58dd/http-exchanges.jsonl](runtime/e49663aa58dd/http-exchanges.jsonl), JSONL row 1.

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImNiZGU1MDE0NzM4MGYzZTEifQ.eyJpc3MiOiJodHRwczovL2lkZW50aXR5LmZpeHR1cmUuaW52YWxpZCIsImF1ZCI6Ind1amktdm5leHQtdGVzdHMiLCJzdWIiOiJjb2xsZWN0b3ItZml4dHVyZSIsInRlbmFudF9pZCI6InRlbmFudC1maXh0dXJlIiwicm9sZXMiOlsiY29sbGVjdG9yIl0sImlhdCI6MTc4OTI1MDQ1MCwibmJmIjoxNzg5MjUwNDQ5LCJleHAiOjE3ODkyNTA3NTAsImp0aSI6ImFiYWUzYWZlLTJjZjktNDY3NC04MzA2LTUxODgwNmViNDNkNSJ9.cJnkKkoKgjc3xgpzSz0Z3Frre8_4tngZ_o3enm-y2cfEIUeRl81OgG3lZPEVjcpHlbFFg1oaw1SxmjFJnzqmz061SNgZoCanyikcjRVJTWRZRbiQh9l4jItsVbqObwxJXuD2MIpJLyHuvJ0BdKJFG_ASAeT5_Jl4svXZ-JRxDRcZ1-2KgUzE-kWulBnlAw40cEScBXJ2s1akH1k4TGW6nBN83rCiBmY3tv0Z1SD2M742Ih81d7SCAyU7ShDyB-cWA1qp0M8I8La5vqqkyoOmXAqC7xoyCUxhBQKQg7RNz-sw524LOSsngIQ8m3GPQzVVSdf3LyQvBmGBHULKEjoSBQ
connection: keep-alive
content-length: 877
content-type: application/json
host: testserver
idempotency-key: capture-fixture
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"capture-fixture","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"0b4a8192-ed8c-47a4-aecd-a0688830c738","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"96365319-7a6f-405f-a075-1ee66db3cea9","version":"1","sha256":"91b172346dd8b6a26765fc89f252757736515c0cedcdc5602afb86169093f57f"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":["fixture bytes"],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 513
content-type: application/json
x-request-id: 7b062c83-502d-4b55-85a8-f99615cd8598

{"observation_ref":{"entity_type":"observation","id":"a8bd3b78-448c-40a8-ae46-0c881d20076c","revision":"1"},"capture_id":"capture-fixture","status":"accepted","artifact_refs":[{"id":"0b4a8192-ed8c-47a4-aecd-a0688830c738","version":"1","sha256":"9a2c7e845b8a07ae130eb01e61457d9a0324372c2ebec062b67d0f811dfb17ac"},{"id":"96365319-7a6f-405f-a075-1ee66db3cea9","version":"1","sha256":"91b172346dd8b6a26765fc89f252757736515c0cedcdc5602afb86169093f57f"}],"request_id":"7b062c83-502d-4b55-85a8-f99615cd8598","code":null}
```

## Native SQL and byte inputs

Connection wrappers record migration SET ROLE, application connections, SQL parameters, receipts, row reads and commit/rollback outcomes. Generated database/role cleanup is limited to each new fixture database.

- `tests/vnext/test_rls.py::test_rls_uses_nonowner_role_and_resets_request_scope` — [runtime/4d04b4b6e913/postgres-events.jsonl](runtime/4d04b4b6e913/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_registry_requires_real_domain_and_rolls_back_event` — [runtime/d496b9b249b5/postgres-events.jsonl](runtime/d496b9b249b5/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_composite_refs_reject_missing_type_or_revision[target0]` — [runtime/6afe3da67959/postgres-events.jsonl](runtime/6afe3da67959/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_composite_refs_reject_missing_type_or_revision[target1]` — [runtime/c1f3d8bffec7/postgres-events.jsonl](runtime/c1f3d8bffec7/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_composite_refs_reject_missing_type_or_revision[target2]` — [runtime/d8faab50ef6f/postgres-events.jsonl](runtime/d8faab50ef6f/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_same_tenant_other_project_task_cannot_supply_a_reference` — [runtime/7968b2c643e0/postgres-events.jsonl](runtime/7968b2c643e0/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_immutable_claim_and_agent_assessment_boundary` — [runtime/83dd408a0629/postgres-events.jsonl](runtime/83dd408a0629/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_two_connections_cannot_commit_dependency_cycle` — [runtime/bed045078972/postgres-events.jsonl](runtime/bed045078972/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_agent_database_context_cannot_forge_observation` — [runtime/fc4937b45e0d/postgres-events.jsonl](runtime/fc4937b45e0d/postgres-events.jsonl)
- `tests/vnext/test_rls.py::test_derived_claim_cannot_lower_source_visibility` — [runtime/36b9b6918041/postgres-events.jsonl](runtime/36b9b6918041/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_agent_cannot_use_capture_endpoint` — [runtime/eb980ec0ed7b/postgres-events.jsonl](runtime/eb980ec0ed7b/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_bound_collector_persists_one_observation_all_bytes_without_extractor` — [runtime/317a8c55f053/postgres-events.jsonl](runtime/317a8c55f053/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_replay_is_stable_and_conflicting_arrays_or_text_are_rejected` — [runtime/9e3edd3a9f52/postgres-events.jsonl](runtime/9e3edd3a9f52/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tenant_id-tenant-other]` — [runtime/270a0d05cd18/postgres-events.jsonl](runtime/270a0d05cd18/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[project_id-project-other]` — [runtime/8d0c9337ec9c/postgres-events.jsonl](runtime/8d0c9337ec9c/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[task_id-task-sibling]` — [runtime/8d53de33f0ad/postgres-events.jsonl](runtime/8d53de33f0ad/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[work_item_id-work-b]` — [runtime/eb52adb1519b/postgres-events.jsonl](runtime/eb52adb1519b/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[agent_run_id-missing]` — [runtime/4f7e764b079e/postgres-events.jsonl](runtime/4f7e764b079e/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[receiver_id-other]` — [runtime/972bc6be6082/postgres-events.jsonl](runtime/972bc6be6082/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[execution_epoch-2]` — [runtime/213ce6f0460a/postgres-events.jsonl](runtime/213ce6f0460a/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[run_epoch-2]` — [runtime/72180197b536/postgres-events.jsonl](runtime/72180197b536/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[runtime_attempt-2]` — [runtime/b19c920c7657/postgres-events.jsonl](runtime/b19c920c7657/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tool_call_id-provider-opaque-call]` — [runtime/9cba1bca4093/postgres-events.jsonl](runtime/9cba1bca4093/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_unbound_or_mismatched_identity[tool_attempt_id-missing]` — [runtime/4f0f6f2d0cbf/postgres-events.jsonl](runtime/4f0f6f2d0cbf/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_evidence_requires_capture_id_as_idempotency_key[None]` — [runtime/f9e292d73da2/postgres-events.jsonl](runtime/f9e292d73da2/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_evidence_requires_capture_id_as_idempotency_key[different-operation]` — [runtime/239d0dd42efc/postgres-events.jsonl](runtime/239d0dd42efc/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_replay_and_artifact_download_recheck_current_permission` — [runtime/2f1b983ff2d4/postgres-events.jsonl](runtime/2f1b983ff2d4/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_started_late_attempt_is_historical_only_with_settlement_authority[True]` — [runtime/eec3d370cd50/postgres-events.jsonl](runtime/eec3d370cd50/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_started_late_attempt_is_historical_only_with_settlement_authority[False]` — [runtime/02a194da39c9/postgres-events.jsonl](runtime/02a194da39c9/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_missing_or_changed_actual_bytes[missing]` — [runtime/2f8a46ddca2b/postgres-events.jsonl](runtime/2f8a46ddca2b/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_rejects_missing_or_changed_actual_bytes[changed]` — [runtime/f6f93410ab95/postgres-events.jsonl](runtime/f6f93410ab95/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_capture_publication_database_failure_rolls_back_all_domain_state` — [runtime/502019a47492/postgres-events.jsonl](runtime/502019a47492/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_partial_output_and_source_axes_do_not_certify_business_truth` — [runtime/456024ef745f/postgres-events.jsonl](runtime/456024ef745f/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_model_or_imported_bytes_cannot_be_laundered_into_capture[model_output]` — [runtime/0f9acdc2472c/postgres-events.jsonl](runtime/0f9acdc2472c/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_model_or_imported_bytes_cannot_be_laundered_into_capture[import]` — [runtime/461e82ce951f/postgres-events.jsonl](runtime/461e82ce951f/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_snapshot_pins_revisions_states_relations_after_connection_close` — [runtime/055cbf137607/postgres-events.jsonl](runtime/055cbf137607/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_snapshot_query_scope_current_access_and_expiration` — [runtime/3f4873e841cb/postgres-events.jsonl](runtime/3f4873e841cb/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_gc_retains_live_commit_leases_and_published_snapshot_bytes` — [runtime/fbf9e3c32a35/postgres-events.jsonl](runtime/fbf9e3c32a35/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_snapshot_publication_and_gc_use_two_coordinated_connections` — [runtime/bd2a77f99d94/postgres-events.jsonl](runtime/bd2a77f99d94/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_partial_body_and_complete_metadata_remain_one_partial_observation` — [runtime/c7d42a7d7e66/postgres-events.jsonl](runtime/c7d42a7d7e66/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_late_receipt_requires_a_trusted_start_record` — [runtime/843ab2402eee/postgres-events.jsonl](runtime/843ab2402eee/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_private_publication_pin_protects_visible_bytes_from_lower_clearance_gc` — [runtime/e49663aa58dd/postgres-events.jsonl](runtime/e49663aa58dd/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_read_only_member_can_create_a_snapshot_without_domain_write` — [runtime/5bebed7a370b/postgres-events.jsonl](runtime/5bebed7a370b/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_revoked_collector_cannot_release_commit_lease` — [runtime/cdc083fcd18c/postgres-events.jsonl](runtime/cdc083fcd18c/postgres-events.jsonl)
- `tests/vnext/test_capture_transactions.py::test_gc_preserves_artifact_cited_by_claim_before_snapshot` — [runtime/a84020e2904c/postgres-events.jsonl](runtime/a84020e2904c/postgres-events.jsonl)

Complete byte-input inventory: [input-manifest.json](input-manifest.json).
