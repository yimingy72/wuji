# C0 runtime adapters · complete redacted HTTP packets

These packets are decoded from the final captured JSONL files. Method, URL, headers, request body, status, response headers and response body are complete. Authorization/JWT and `execution_token` values are replaced by SHA-256-bearing placeholders; reissue fixture credentials and recalculate Content-Length before replay. No TLS verification setting was relaxed.

## main-revocation · kali

### Exchange 1

Request:

```http
POST https://127.0.0.1:59387/internal/v2/executor/dispatch HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=eb9e33c8c02e0842167ff656db9da976c9c89b6b37fab3c963e18ca49f15621f>
connection: keep-alive
content-length: 1544
content-type: application/json
host: 127.0.0.1:59387
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"version.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=58bd2c3d323f5612a14b724dec8ecd81e32a9aa7ffce933e919cbe059199e2a0>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:28.355193+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"f7f7ee3a-bc1a-417e-be2b-2ed7af43b93a","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67","tool_call_id":"e484b971-8af3-43c2-a759-0b877bc534e7","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 951
content-type: application/json
x-request-id: 0857c899-ff7f-49f0-81d9-0706277c66d8

{"completeness":"complete","error_code":null,"exited_at":"2026-09-13T14:10:58.518153Z","media_type":"application/octet-stream","output_base64":"Zml4dHVyZS12ZXJzaW9uPTE3Cg==","output_bytes":"19","output_sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","receipt_id":"0c662a9e-36d2-4c65-8b0d-0b8d135cfdd5","receiver_id":"receiver-fixture","source_receipt":{"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","environment_ref":"environment-fixture","output_bytes":19,"output_sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","receipt_id":"0c662a9e-36d2-4c65-8b0d-0b8d135cfdd5","receiver_id":"receiver-fixture","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"},"started_at":"2026-09-13T14:10:58.518012Z","status":"exited","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59387/internal/v2/executor/query HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=eb9e33c8c02e0842167ff656db9da976c9c89b6b37fab3c963e18ca49f15621f>
connection: keep-alive
content-length: 1544
content-type: application/json
host: 127.0.0.1:59387
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"version.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=58bd2c3d323f5612a14b724dec8ecd81e32a9aa7ffce933e919cbe059199e2a0>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:28.355193+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"f7f7ee3a-bc1a-417e-be2b-2ed7af43b93a","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67","tool_call_id":"e484b971-8af3-43c2-a759-0b877bc534e7","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 951
content-type: application/json
x-request-id: 60c9b449-23dc-430c-aee2-781bb77f7e0c

{"completeness":"complete","error_code":null,"exited_at":"2026-09-13T14:10:58.518153Z","media_type":"application/octet-stream","output_base64":"Zml4dHVyZS12ZXJzaW9uPTE3Cg==","output_bytes":"19","output_sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","receipt_id":"0c662a9e-36d2-4c65-8b0d-0b8d135cfdd5","receiver_id":"receiver-fixture","source_receipt":{"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","environment_ref":"environment-fixture","output_bytes":19,"output_sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","receipt_id":"0c662a9e-36d2-4c65-8b0d-0b8d135cfdd5","receiver_id":"receiver-fixture","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"},"started_at":"2026-09-13T14:10:58.518012Z","status":"exited","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

## main-revocation · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59386/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=62442ef7d9aedf866853472cf8b35308f54dbc48eab408d41a196fb155225983>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59386
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=58bd2c3d323f5612a14b724dec8ecd81e32a9aa7ffce933e919cbe059199e2a0>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"validate_receipt","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: b3995312-654a-481f-8525-05c383e491a4

{"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"validate_receipt","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59386/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=62442ef7d9aedf866853472cf8b35308f54dbc48eab408d41a196fb155225983>
connection: keep-alive
content-length: 476
content-type: application/json
host: 127.0.0.1:59386
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=58bd2c3d323f5612a14b724dec8ecd81e32a9aa7ffce933e919cbe059199e2a0>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"check_execution","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 169
content-type: application/json
x-request-id: 15226b78-988b-4434-a9c2-cab428e331dc

{"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"check_execution","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

### Exchange 3

Request:

```http
POST https://127.0.0.1:59386/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=62442ef7d9aedf866853472cf8b35308f54dbc48eab408d41a196fb155225983>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59386
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=58bd2c3d323f5612a14b724dec8ecd81e32a9aa7ffce933e919cbe059199e2a0>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"validate_receipt","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 2c644d5d-9037-4403-8f58-c0e7f0e1cf0a

{"permit_digest":"8c0883a06b088a65b328f416d82250f3d947ebe8dc5fb5be37e846b4afe27fe9","purpose":"validate_receipt","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67"}
```

## main-revocation · gate-p03

### Exchange 1

Request:

```http
POST http://testserver/internal/v2/tool-calls HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: <REDACTED_AUTHORIZATION sha256=fb90ea74a8a61cb4429c58be4840187365eceab6094442f8fae92eea69f17cbb>
connection: keep-alive
content-length: 261
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: c0-real-https

{"approval_ref":null,"arguments":{"path":"version.txt"},"message_id":"message-p06-tool-1","provider_call_id":"call-c0-real-https","sdk_approval_id":null,"sdk_content_id":null,"session_lineage":"session-lineage-fixture","tool_definition_ref":"fixture-reader-v1"}
```

Response:

```http
HTTP/1.1 200 OK
content-length: 751
content-type: application/json
x-request-id: 2969670d-b36e-4e3f-94c1-6e9193804bea

{"evidence_receipt":{"artifact_refs":[{"id":"64cf46fb-216c-4648-8ae1-dd7274e6df4b","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","version":"1"}],"capture_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67","code":null,"observation_ref":{"entity_type":"observation","id":"89d566e5-979c-4696-883a-c2106882a4e0","revision":"1"},"request_id":"fixture-request","status":"accepted"},"operation_id":"e484b971-8af3-43c2-a759-0b877bc534e7","reason_code":null,"result_ref":{"id":"64cf46fb-216c-4648-8ae1-dd7274e6df4b","sha256":"e5827e5ed84fc556bcd91e1a7b53289324c11d1f986cb5756074aa7962d23076","version":"1"},"status":"complete","tool_attempt_id":"60ac0e98-c59b-4ff4-bfc5-d1a49056ea67","tool_call_id":"e484b971-8af3-43c2-a759-0b877bc534e7"}
```

### Exchange 2

Request:

```http
GET http://testserver/api/v2/artifacts/64cf46fb-216c-4648-8ae1-dd7274e6df4b/content?version=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: <REDACTED_AUTHORIZATION sha256=fb90ea74a8a61cb4429c58be4840187365eceab6094442f8fae92eea69f17cbb>
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
x-request-id: b92bed42-1289-4129-9364-ed7a1bd151f8

fixture-version=17

```

### Exchange 3

Request:

```http
POST http://testserver/internal/v2/tool-calls HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: <REDACTED_AUTHORIZATION sha256=fb90ea74a8a61cb4429c58be4840187365eceab6094442f8fae92eea69f17cbb>
connection: keep-alive
content-length: 263
content-type: application/json
host: testserver
user-agent: python-httpx/0.28.1
x-wuji-request-id: c0-after-revoke

{"approval_ref":null,"arguments":{"path":"version.txt"},"message_id":"message-p06-tool-1","provider_call_id":"call-c0-after-revoke","sdk_approval_id":null,"sdk_content_id":null,"session_lineage":"session-lineage-fixture","tool_definition_ref":"fixture-reader-v1"}
```

Response:

```http
HTTP/1.1 409 Conflict
content-length: 157
content-type: application/json
x-request-id: c7259390-a2ed-4444-982e-327fd30bd276

{"code":"STALE_EXECUTION","details":{},"message":"The request could not be completed.","request_id":"c7259390-a2ed-4444-982e-327fd30bd276","retryable":false}
```

## callback-lost-ack · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59398/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=1f62b585c341cf9dad55329c7a76a91e5b2f2580a726dbd01292e22abff43290>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59398
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=a11ac228006bda04a35600b6e1c53f76fa369558b95c8517259385df8b146087>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"68ae140a341b4e141c3df15d04778d33cc99882b517bb1f41043fc8883325e41","purpose":"validate_receipt","tool_attempt_id":"96f92c2d-099e-4504-953d-fcfbf13826ac"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 191536f9-dd69-4bc9-b1f2-dc83710bbbc2

{"permit_digest":"68ae140a341b4e141c3df15d04778d33cc99882b517bb1f41043fc8883325e41","purpose":"validate_receipt","tool_attempt_id":"96f92c2d-099e-4504-953d-fcfbf13826ac"}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59398/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=1f62b585c341cf9dad55329c7a76a91e5b2f2580a726dbd01292e22abff43290>
connection: keep-alive
content-length: 476
content-type: application/json
host: 127.0.0.1:59398
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=a11ac228006bda04a35600b6e1c53f76fa369558b95c8517259385df8b146087>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"68ae140a341b4e141c3df15d04778d33cc99882b517bb1f41043fc8883325e41","purpose":"check_execution","tool_attempt_id":"96f92c2d-099e-4504-953d-fcfbf13826ac"}
```

Response:

```http
NO HTTP RESPONSE (connection closed before ACK)
```

### Exchange 3

Request:

```http
POST https://127.0.0.1:59398/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=1f62b585c341cf9dad55329c7a76a91e5b2f2580a726dbd01292e22abff43290>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59398
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=a11ac228006bda04a35600b6e1c53f76fa369558b95c8517259385df8b146087>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"68ae140a341b4e141c3df15d04778d33cc99882b517bb1f41043fc8883325e41","purpose":"validate_receipt","tool_attempt_id":"96f92c2d-099e-4504-953d-fcfbf13826ac"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 4a4c41db-9ab8-45a3-bd78-22f4cb35c9dd

{"permit_digest":"68ae140a341b4e141c3df15d04778d33cc99882b517bb1f41043fc8883325e41","purpose":"validate_receipt","tool_attempt_id":"96f92c2d-099e-4504-953d-fcfbf13826ac"}
```

## callback-503 · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59406/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=0f445d98abfe9c13407ac1b17a01d5b47c9d5fa5842ea9787a3ae7755c34836b>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59406
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=ee83620cc0947e30e34b1e497939cd18cae9b8fc020716c3f26b659959666a25>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"99a9a6904265e5d9e58a35316ad08eeecd7508b01763844e96fb2816d940c1d2","purpose":"validate_receipt","tool_attempt_id":"db71d5a6-ba04-4966-bfeb-7555b58d8f92"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: b478f69e-f583-47cc-ba67-c4939952117d

{"permit_digest":"99a9a6904265e5d9e58a35316ad08eeecd7508b01763844e96fb2816d940c1d2","purpose":"validate_receipt","tool_attempt_id":"db71d5a6-ba04-4966-bfeb-7555b58d8f92"}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59406/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=0f445d98abfe9c13407ac1b17a01d5b47c9d5fa5842ea9787a3ae7755c34836b>
connection: keep-alive
content-length: 476
content-type: application/json
host: 127.0.0.1:59406
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=ee83620cc0947e30e34b1e497939cd18cae9b8fc020716c3f26b659959666a25>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"99a9a6904265e5d9e58a35316ad08eeecd7508b01763844e96fb2816d940c1d2","purpose":"check_execution","tool_attempt_id":"db71d5a6-ba04-4966-bfeb-7555b58d8f92"}
```

Response:

```http
HTTP/1.1 503 Service Unavailable
connection: close
content-length: 73
content-type: application/json

{"code":"CAPABILITY_UNAVAILABLE","message":"post-commit ACK unavailable"}
```

### Exchange 3

Request:

```http
POST https://127.0.0.1:59406/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=0f445d98abfe9c13407ac1b17a01d5b47c9d5fa5842ea9787a3ae7755c34836b>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59406
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=ee83620cc0947e30e34b1e497939cd18cae9b8fc020716c3f26b659959666a25>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"99a9a6904265e5d9e58a35316ad08eeecd7508b01763844e96fb2816d940c1d2","purpose":"validate_receipt","tool_attempt_id":"db71d5a6-ba04-4966-bfeb-7555b58d8f92"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 2fa9b623-bb8f-40e1-997b-f7551ac0b0ca

{"permit_digest":"99a9a6904265e5d9e58a35316ad08eeecd7508b01763844e96fb2816d940c1d2","purpose":"validate_receipt","tool_attempt_id":"db71d5a6-ba04-4966-bfeb-7555b58d8f92"}
```

## callback-bad-ack · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59414/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=e7ec662abd237a8f063b098fa2c0b7a761188d844fc497c12071d361966fc775>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59414
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=23585adf7dc3da192211938725f82a4b05c23110664de7a592cd1be5d539b07f>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"4e0415114b26846bc75c135f4d3d00c716c299706aae2630128de8d2e092cb37","purpose":"validate_receipt","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 368d783e-ff71-4a15-afd5-35b4fddc3f6c

{"permit_digest":"4e0415114b26846bc75c135f4d3d00c716c299706aae2630128de8d2e092cb37","purpose":"validate_receipt","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59414/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=e7ec662abd237a8f063b098fa2c0b7a761188d844fc497c12071d361966fc775>
connection: keep-alive
content-length: 476
content-type: application/json
host: 127.0.0.1:59414
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=23585adf7dc3da192211938725f82a4b05c23110664de7a592cd1be5d539b07f>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"4e0415114b26846bc75c135f4d3d00c716c299706aae2630128de8d2e092cb37","purpose":"check_execution","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

Response:

```http
HTTP/1.1 200 OK
connection: close
content-length: 169
content-type: application/json

{"permit_digest":"0000000000000000000000000000000000000000000000000000000000000000","purpose":"check_execution","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

### Exchange 3

Request:

```http
POST https://127.0.0.1:59414/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=e7ec662abd237a8f063b098fa2c0b7a761188d844fc497c12071d361966fc775>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59414
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=23585adf7dc3da192211938725f82a4b05c23110664de7a592cd1be5d539b07f>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"4e0415114b26846bc75c135f4d3d00c716c299706aae2630128de8d2e092cb37","purpose":"validate_receipt","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: c7d894b2-68d5-495b-a092-4e940157f88f

{"permit_digest":"4e0415114b26846bc75c135f4d3d00c716c299706aae2630128de8d2e092cb37","purpose":"validate_receipt","tool_attempt_id":"691f45ee-8118-4051-a24f-e9fc0db032a3"}
```

## dispatch-not-registered · kali

### Exchange 1

Request:

```http
POST https://127.0.0.1:59422/internal/v2/executor/dispatch HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=5c93da65578cde27f6f406614787b917a445e8f685962b6f4cb8b92650b34812>
connection: keep-alive
content-length: 1544
content-type: application/json
host: 127.0.0.1:59422
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"version.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=db4d363400f8357f2dc98738909819a0744e7f5976ca1319ffb9300aafd5ec28>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:36.938547+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"9ac94419-4866-4b37-81f4-280b2b6ef43d","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f","tool_call_id":"3737f23a-025c-48f9-9e6e-c07aa56e38bd","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"681074479f5eb9f515979535f91749b6f9e8449b865be3b7e0393bbd88931c5f"}
```

Response:

```http
NO HTTP RESPONSE (connection closed before ACK)
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59422/internal/v2/executor/query HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=5c93da65578cde27f6f406614787b917a445e8f685962b6f4cb8b92650b34812>
connection: keep-alive
content-length: 1544
content-type: application/json
host: 127.0.0.1:59422
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"version.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=db4d363400f8357f2dc98738909819a0744e7f5976ca1319ffb9300aafd5ec28>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:36.938547+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"9ac94419-4866-4b37-81f4-280b2b6ef43d","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f","tool_call_id":"3737f23a-025c-48f9-9e6e-c07aa56e38bd","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"681074479f5eb9f515979535f91749b6f9e8449b865be3b7e0393bbd88931c5f"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 706
content-type: application/json
x-request-id: 2329398f-d654-404b-b3ad-73ada1416aa4

{"completeness":"unknown","error_code":"not_registered","exited_at":null,"media_type":null,"output_base64":null,"output_bytes":null,"output_sha256":null,"permit_digest":"681074479f5eb9f515979535f91749b6f9e8449b865be3b7e0393bbd88931c5f","receipt_id":"3ef504f0-210e-4266-bd02-839420253130","receiver_id":"receiver-fixture","source_receipt":{"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","environment_ref":"environment-fixture","receipt_id":"3ef504f0-210e-4266-bd02-839420253130","receiver_id":"receiver-fixture","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f"},"started_at":null,"status":"not_started","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f"}
```

## dispatch-not-registered · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59421/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=61004d88074b92d19101481803e6247e4d65ade99d24454184c3c5989054e510>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59421
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=db4d363400f8357f2dc98738909819a0744e7f5976ca1319ffb9300aafd5ec28>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"681074479f5eb9f515979535f91749b6f9e8449b865be3b7e0393bbd88931c5f","purpose":"validate_receipt","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f"}
```

Response:

```http
HTTP/1.1 200 OK
cache-control: no-store
connection: close
content-length: 170
content-type: application/json
x-request-id: 8f468eb7-bbba-4722-9c77-d60b248fa5da

{"permit_digest":"681074479f5eb9f515979535f91749b6f9e8449b865be3b7e0393bbd88931c5f","purpose":"validate_receipt","tool_attempt_id":"e02f7f6c-ba9e-4461-bbda-41b194c56f5f"}
```

## tamper-and-identity · kali

### Exchange 1

Request:

```http
POST https://127.0.0.1:59431/internal/v2/executor/dispatch HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=71f4e144ee43af74aa33dfd47eb508b9ae48b897f6a72dd727bd0b5c7075775f>
connection: keep-alive
content-length: 1542
content-type: application/json
host: 127.0.0.1:59431
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"other.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=8b08e0a20142f49f8acb392cc5bcd51663de92a08db499c3e438df576e163a91>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:39.511289+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"36c2545f-e308-4bb2-a672-bd4edd44f401","tool_attempt_id":"a3bb55df-8667-4ee1-aea5-f2d09d682cce","tool_call_id":"cb565255-80c9-4593-aae0-a9c5aef23f57","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"7ae1a30977f6c5b92fafe2956d0844e92b799b72cc66a4deaa60251c69dc8f5e"}
```

Response:

```http
HTTP/1.1 404 Not Found
connection: close
content-length: 164
content-type: application/json
x-request-id: 739e7881-a71d-4120-bb37-01a0047ae1a5

{"code":"NOT_FOUND_OR_FORBIDDEN","details":{},"message":"The request could not be completed.","request_id":"739e7881-a71d-4120-bb37-01a0047ae1a5","retryable":false}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59431/internal/v2/executor/dispatch HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=ef0b7d266a3a674540fc253800d0d99207b2b723c7e67d1bfc383902aa7432d4>
connection: keep-alive
content-length: 1544
content-type: application/json
host: 127.0.0.1:59431
user-agent: python-httpx/0.28.1

{"permit":{"arguments":{"path":"version.txt"},"arguments_digest":"ee0714e74232a3dcef876c936d501d2151837c13762abf4dd368d60c70a7a4fe","execution_token":"<REDACTED_EXECUTION_TOKEN sha256=8b08e0a20142f49f8acb392cc5bcd51663de92a08db499c3e438df576e163a91>","executor_ref":"workspace-reader-fixture","expires_at":"2026-09-13T14:11:39.511289+00:00","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"resource_keys":["workspace:environment-fixture:version.txt"],"roles":["worker"],"runtime":{"allowed_tool_refs":["fixture-reader-v1"],"buffer_bytes":1024,"chunk_bytes":512,"idle_timeout_seconds":5.0,"limits":{"max_attempts_per_work":3,"max_elapsed_seconds":300,"max_model_requests":2,"max_reason_runs":2,"max_single_output_bytes":4096,"max_tool_calls":2,"max_total_output_bytes":8192,"max_work_items":4,"repair_attempts":1},"lock_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","max_inflight_model_requests":1,"max_inflight_tools":1,"max_pending_operations":4,"published_at":"2026-09-13T00:00:00Z","ref":"fixture-runtime-v1","revision":"1","total_timeout_seconds":30.0},"subject":"run-worker-fixture","token_id":"36c2545f-e308-4bb2-a672-bd4edd44f401","tool_attempt_id":"a3bb55df-8667-4ee1-aea5-f2d09d682cce","tool_call_id":"cb565255-80c9-4593-aae0-a9c5aef23f57","tool_definition_ref":"fixture-reader-v1"},"permit_digest":"06b12508f6b4d646a8a843de3a35d070b0d91a6c80cbc0dc97d78dcf75ed62b1"}
```

Response:

```http
HTTP/1.1 404 Not Found
connection: close
content-length: 164
content-type: application/json
x-request-id: 3e36c264-eeb8-4253-8ec9-c9c34329fe09

{"code":"NOT_FOUND_OR_FORBIDDEN","details":{},"message":"The request could not be completed.","request_id":"3e36c264-eeb8-4253-8ec9-c9c34329fe09","retryable":false}
```

## tamper-and-identity · platform

### Exchange 1

Request:

```http
POST https://127.0.0.1:59430/internal/v2/executors/workspace-reader-fixture/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=3c34e016ffe03d85e6da124a1bd1ce3e34c6ef1406e872ee5188f4d4a0d9f5f5>
connection: keep-alive
content-length: 477
content-type: application/json
host: 127.0.0.1:59430
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=8b08e0a20142f49f8acb392cc5bcd51663de92a08db499c3e438df576e163a91>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"7ae1a30977f6c5b92fafe2956d0844e92b799b72cc66a4deaa60251c69dc8f5e","purpose":"validate_receipt","tool_attempt_id":"a3bb55df-8667-4ee1-aea5-f2d09d682cce"}
```

Response:

```http
HTTP/1.1 404 Not Found
connection: close
content-length: 164
content-type: application/json
x-request-id: 6f01cf72-bda2-463b-8e82-6d8263c3806a

{"code":"NOT_FOUND_OR_FORBIDDEN","details":{},"message":"The request could not be completed.","request_id":"6f01cf72-bda2-463b-8e82-6d8263c3806a","retryable":false}
```

### Exchange 2

Request:

```http
POST https://127.0.0.1:59430/internal/v2/executors/not-this-executor/permits/check HTTP/1.1
accept: application/json
accept-encoding: identity
authorization: <REDACTED_AUTHORIZATION sha256=3c34e016ffe03d85e6da124a1bd1ce3e34c6ef1406e872ee5188f4d4a0d9f5f5>
connection: keep-alive
content-length: 476
content-type: application/json
host: 127.0.0.1:59430
user-agent: python-httpx/0.28.1

{"execution_token":"<REDACTED_EXECUTION_TOKEN sha256=8b08e0a20142f49f8acb392cc5bcd51663de92a08db499c3e438df576e163a91>","identity":{"agent_run_id":"run-fixture","execution_epoch":"1","project_id":"project-fixture","receiver_id":"receiver-fixture","run_epoch":"1","runtime_attempt":"1","task_id":"task-fixture","tenant_id":"tenant-fixture","work_item_id":"work-fixture"},"permit_digest":"06b12508f6b4d646a8a843de3a35d070b0d91a6c80cbc0dc97d78dcf75ed62b1","purpose":"check_execution","tool_attempt_id":"a3bb55df-8667-4ee1-aea5-f2d09d682cce"}
```

Response:

```http
HTTP/1.1 404 Not Found
connection: close
content-length: 164
content-type: application/json
x-request-id: f0706b99-6ca1-4519-9101-fa3bb69b5011

{"code":"NOT_FOUND_OR_FORBIDDEN","details":{},"message":"The request could not be completed.","request_id":"f0706b99-6ca1-4519-9101-fa3bb69b5011","retryable":false}
```
