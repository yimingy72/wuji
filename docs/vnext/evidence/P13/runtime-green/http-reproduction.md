# P13 完整夹具 HTTP 请求与响应

以下报文来自真实签名 ASGI 路由与隔离 nonowner PostgreSQL 运行。请求方法、URL、Headers、请求体、响应状态、Headers 与响应体均完整保留；body 同时保存在 runtime JSONL 的原始 base64 字节中。Authorization 替换为可重新签发的测试变量，并保留原 Header SHA-256；未提交 bearer 或私钥。

复现命令：`./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_view_snapshots.py -q`。输入实现绑定见 `binding.json`。`http://testserver` 是真实 ASGI transport 的测试 authority；没有外部目标、收费模型或生产流量。

## Exchange 1 · test_current_clearance_invalid0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: dca11cd9-69bd-48f4-838c-7e58d5f452a5
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"dca11cd9-69bd-48f4-838c-7e58d5f452a5","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"c3a4e15f-1efd-45eb-b5e4-1b4b7109e919","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 9339f14a-0e49-461f-9608-566b43a1807c

{"observation_ref":{"entity_type":"observation","id":"7fe61450-4a4f-4e46-b575-41295a014658","revision":"1"},"capture_id":"dca11cd9-69bd-48f4-838c-7e58d5f452a5","status":"accepted","artifact_refs":[{"id":"c3a4e15f-1efd-45eb-b5e4-1b4b7109e919","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"9339f14a-0e49-461f-9608-566b43a1807c","code":null}
```

## Exchange 2 · test_current_clearance_invalid0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 48c2f9f3-fd53-41b8-b412-52d088fe3f76
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 c3a4e15f-1efd-45eb-b5e4-1b4b7109e919@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"7fe61450-4a4f-4e46-b575-41295a014658","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"c3a4e15f-1efd-45eb-b5e4-1b4b7109e919","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 356ff7dc-a0ac-4b7c-998c-445664f4c331

{"status":"accepted_shared","local_ref":"c","request_id":"356ff7dc-a0ac-4b7c-998c-445664f4c331","canonical_ref":{"entity_type":"claim","id":"2be61604-c25a-4dcc-9efe-71c676371117","revision":"1"},"code":null}
```

## Exchange 3 · test_current_clearance_invalid0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 70d946e7-a8db-4ba1-b9a9-7c5ccd68bd72
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"2f4b5d4f-3509-4c4c-9f78-a19456fa78ed","claim_ref":{"entity_type":"claim","id":"2be61604-c25a-4dcc-9efe-71c676371117","revision":"1"},"input_refs":[{"entity_type":"observation","id":"7fe61450-4a4f-4e46-b575-41295a014658","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 5cb10d80-35c6-4c79-b8e6-0b49f92eb3a7

{"assessment_id":"2f4b5d4f-3509-4c4c-9f78-a19456fa78ed","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"2be61604-c25a-4dcc-9efe-71c676371117","revision":"1"},"request_id":"5cb10d80-35c6-4c79-b8e6-0b49f92eb3a7","code":null}
```

## Exchange 4 · test_current_clearance_invalid0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8dc6cbe2-a482-4a1d-a40f-02bee859319e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: 44abe172-d8b1-42b6-9476-d0349bf29d1a

{"view_id":"6f8bba73-f177-4c0c-b8bf-a860aa5dcc3a","snapshot_id":"b098e90b-1ba7-4d4e-bd4b-a09bcd59d01c","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"0ff7582e396a2b74e3cb52eeae49f75a8414f7751104711a7dcaf5df2a01f246","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:c3a4e15f-1efd-45eb-b5e4-1b4b7109e919@1","ref":{"entity_type":"artifact","id":"c3a4e15f-1efd-45eb-b5e4-1b4b7109e919","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"pqj490DLMLx8D-y-mh6kn4g_O6bFeqPED3fHAY2PTFE","truncated":true,"continuation":"pqj490DLMLx8D-y-mh6kn4g_O6bFeqPED3fHAY2PTFE","allowed_actions":[]}
```

## Exchange 5 · test_current_clearance_invalid0

漏洞/控制点：旧视图或错误主体/查询不能复用 opaque cursor。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=pqj490DLMLx8D-y-mh6kn4g_O6bFeqPED3fHAY2PTFE HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8473e189-a1da-46e3-8c8c-5ec50d7b7de8
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
cache-control: no-store
content-length: 164
content-type: application/json
x-request-id: 29a6933a-2187-475e-a947-10603f5d926e

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"29a6933a-2187-475e-a947-10603f5d926e","retryable":false,"details":{}}
```

## Exchange 6 · test_current_clearance_invalid0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/2be61604-c25a-4dcc-9efe-71c676371117?revision=1&snapshot_id=b098e90b-1ba7-4d4e-bd4b-a09bcd59d01c HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: bf2c3e2d-aae7-4cb6-93dc-c093f38bbd69
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 161
content-type: application/json
x-request-id: c762cfc9-266b-4ec4-8a44-2476555f3537

{"code":"HISTORY_UNAVAILABLE","message":"The request could not be completed.","request_id":"c762cfc9-266b-4ec4-8a44-2476555f3537","retryable":false,"details":{}}
```

## Exchange 7 · test_current_clearance_invalid0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 705c2266-5675-4e60-b4bb-3fae43623fed
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 860
content-type: application/json
x-request-id: 57f5dc8c-2e8e-4119-a49c-349ca3318a34

{"view_id":"b6b792af-6895-424d-93a8-dc6c07eb7f53","snapshot_id":"96bead61-57f0-4ef5-a135-fc5f59c1af24","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"gOQRfjWEeDZ_HkMl9gQxAJiWI4DKuXtVQmiDJetQEZk","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 8 · test_expired_view_and_snapshot0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 7a97a327-1088-4ae6-abd9-9fb86da2abf7
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"7a97a327-1088-4ae6-abd9-9fb86da2abf7","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: ccebb8a6-e77d-42e7-bd6c-92946614d22d

{"observation_ref":{"entity_type":"observation","id":"45a7ab07-8d4e-48ee-a5ee-2ff593232b97","revision":"1"},"capture_id":"7a97a327-1088-4ae6-abd9-9fb86da2abf7","status":"accepted","artifact_refs":[{"id":"d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"ccebb8a6-e77d-42e7-bd6c-92946614d22d","code":null}
```

## Exchange 9 · test_expired_view_and_snapshot0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: e49ee94a-de07-4902-8531-ea04748c729e
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"45a7ab07-8d4e-48ee-a5ee-2ff593232b97","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: f8fda51c-f4bf-48ac-8423-f95724f9af37

{"status":"accepted_shared","local_ref":"c","request_id":"f8fda51c-f4bf-48ac-8423-f95724f9af37","canonical_ref":{"entity_type":"claim","id":"a828055b-5544-4efd-a32d-caede393aaf3","revision":"1"},"code":null}
```

## Exchange 10 · test_expired_view_and_snapshot0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 95fbfd75-1365-4384-8c13-120bbdd71df4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"816c3bf9-0d84-47a7-9867-8d70dc652812","claim_ref":{"entity_type":"claim","id":"a828055b-5544-4efd-a32d-caede393aaf3","revision":"1"},"input_refs":[{"entity_type":"observation","id":"45a7ab07-8d4e-48ee-a5ee-2ff593232b97","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 69b0966c-fa76-49c4-8ebd-250e472c2e13

{"assessment_id":"816c3bf9-0d84-47a7-9867-8d70dc652812","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"a828055b-5544-4efd-a32d-caede393aaf3","revision":"1"},"request_id":"69b0966c-fa76-49c4-8ebd-250e472c2e13","code":null}
```

## Exchange 11 · test_expired_view_and_snapshot0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: f7f550c7-f5b4-494f-a683-9d11858c7018
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: f560d9fa-5e09-461b-b265-d2fa5a2cd970

{"view_id":"f11dc373-4213-4352-8dea-6f0c9a176295","snapshot_id":"a1fb6b2a-4054-4f84-8e21-fa1e3f0e8a9c","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5@1","ref":{"entity_type":"artifact","id":"d4e4baf4-46a9-4658-9fd8-9535cdd3b5d5","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"xc5wdZmMdUrIz2CZctjai_Od45oeniFRbpYJs9fRpr8","truncated":true,"continuation":"xc5wdZmMdUrIz2CZctjai_Od45oeniFRbpYJs9fRpr8","allowed_actions":[]}
```

## Exchange 12 · test_expired_view_and_snapshot0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=xc5wdZmMdUrIz2CZctjai_Od45oeniFRbpYJs9fRpr8 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 0eca1e4e-3e34-4e12-bb1c-828bdd344933
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 154
content-type: application/json
x-request-id: 79126c70-52f1-4729-8165-b5b96aa09790

{"code":"VIEW_EXPIRED","message":"The request could not be completed.","request_id":"79126c70-52f1-4729-8165-b5b96aa09790","retryable":false,"details":{}}
```

## Exchange 13 · test_expired_view_and_snapshot0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/not-present?revision=1&snapshot_id=a1fb6b2a-4054-4f84-8e21-fa1e3f0e8a9c HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 0174dd5f-765d-4b84-a91d-4dbe422532cf
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 158
content-type: application/json
x-request-id: 62b4c3c8-322a-4566-a223-d67f6f768a49

{"code":"SNAPSHOT_EXPIRED","message":"The request could not be completed.","request_id":"62b4c3c8-322a-4566-a223-d67f6f768a49","retryable":false,"details":{}}
```

## Exchange 14 · test_fact_ledger_reads_the_unc0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 64c9f51c-799a-4ff2-9d91-8be1440a36c2
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"64c9f51c-799a-4ff2-9d91-8be1440a36c2","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"56f0349c-ae1c-421c-bc34-5eaa88752988","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 29429c37-3539-49d0-a332-ecb14fa12c41

{"observation_ref":{"entity_type":"observation","id":"b2decb96-d5e5-4d09-9ab3-ade08fa1c5ad","revision":"1"},"capture_id":"64c9f51c-799a-4ff2-9d91-8be1440a36c2","status":"accepted","artifact_refs":[{"id":"56f0349c-ae1c-421c-bc34-5eaa88752988","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"29429c37-3539-49d0-a332-ecb14fa12c41","code":null}
```

## Exchange 15 · test_fact_ledger_reads_the_unc0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 2b37cc7b-084b-4eef-9024-373f8867273d
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 56f0349c-ae1c-421c-bc34-5eaa88752988@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"b2decb96-d5e5-4d09-9ab3-ade08fa1c5ad","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"56f0349c-ae1c-421c-bc34-5eaa88752988","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 936735c7-2765-4bab-8822-8af6bd182e5a

{"status":"accepted_shared","local_ref":"c","request_id":"936735c7-2765-4bab-8822-8af6bd182e5a","canonical_ref":{"entity_type":"claim","id":"87513495-6144-468a-9946-b45b749f47c4","revision":"1"},"code":null}
```

## Exchange 16 · test_fact_ledger_reads_the_unc0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 91467cf6-022d-4d2b-9b20-f973a664d6f4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"a39256f6-cbbc-4e9a-87cf-574dfd1b50ae","claim_ref":{"entity_type":"claim","id":"87513495-6144-468a-9946-b45b749f47c4","revision":"1"},"input_refs":[{"entity_type":"observation","id":"b2decb96-d5e5-4d09-9ab3-ade08fa1c5ad","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 0561cfc2-d2c6-4511-9e00-dde5af174290

{"assessment_id":"a39256f6-cbbc-4e9a-87cf-574dfd1b50ae","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"87513495-6144-468a-9946-b45b749f47c4","revision":"1"},"request_id":"0561cfc2-d2c6-4511-9e00-dde5af174290","code":null}
```

## Exchange 17 · test_history_lists_only_saved_0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 095479a6-538a-4a49-b2d2-faef5dfda0cb
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"095479a6-538a-4a49-b2d2-faef5dfda0cb","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"41a20d67-7941-4972-bbed-e21b8bf79fde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: b9cb10d0-3911-41fd-a561-d3f33b9f9931

{"observation_ref":{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"},"capture_id":"095479a6-538a-4a49-b2d2-faef5dfda0cb","status":"accepted","artifact_refs":[{"id":"41a20d67-7941-4972-bbed-e21b8bf79fde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"b9cb10d0-3911-41fd-a561-d3f33b9f9931","code":null}
```

## Exchange 18 · test_history_lists_only_saved_0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: aa730f9a-bfe2-439b-b9f8-b64771943079
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 41a20d67-7941-4972-bbed-e21b8bf79fde@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"41a20d67-7941-4972-bbed-e21b8bf79fde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: c714377d-29d4-4935-a94a-e9699d6d4a67

{"status":"accepted_shared","local_ref":"c","request_id":"c714377d-29d4-4935-a94a-e9699d6d4a67","canonical_ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"code":null}
```

## Exchange 19 · test_history_lists_only_saved_0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: c198a040-dbf6-424f-8601-c5858d3427a2
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"0691e631-acc8-47c3-b7be-cdae043784d0","claim_ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"input_refs":[{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: e86337f3-4d97-47dc-a097-b5f5201781b4

{"assessment_id":"0691e631-acc8-47c3-b7be-cdae043784d0","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"request_id":"e86337f3-4d97-47dc-a097-b5f5201781b4","code":null}
```

## Exchange 20 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: c5573b9f-761d-4c2e-a64e-f53114cd04fb
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: 891b4edc-0c95-4da8-be73-2374b406f7a0

{"view_id":"cf104fe8-e1e2-484e-b4e7-77a0e57b3683","snapshot_id":"b05c2522-569f-4fda-8ac6-2bcd78ec26b3","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","ref":{"entity_type":"artifact","id":"41a20d67-7941-4972-bbed-e21b8bf79fde","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"display_kind":"fact","label":"已捕获内容 41a20d67-7941-4972-bbed-e21b8bf79fde@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","ref":{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"},"display_kind":"observation","label":"Observation 095479a6-538a-4a49-b2d2-faef5dfda0cb","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:9c0b347fe3f62c2e1671aa4d1a16330338c3bee47ee2a67180ccdbe70a836f46","source":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","target":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","edge_type":"captured_artifact","label":null},{"id":"relation:b8257028fdfb3c4ae031547019aa4c68f8e0ea33f9fddc56b10cc10e64c4c354","source":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","target":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","edge_type":"cites","label":null}],"opaque_cursor":"vWuOO46pXir_cvPEwwmex4hCAc470068nsBKTZbD-Qc","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 21 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: accf17d2-15bf-4153-9d63-d4dfad2a307c
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: 1eb21337-8a45-4c3a-b0ce-2f9b771421d9

{"view_id":"8b87e811-44f6-4e68-a447-6e0c987e9324","snapshot_id":"b9c6fa78-3bd1-4a13-9edb-515d83621dbf","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","ref":{"entity_type":"artifact","id":"41a20d67-7941-4972-bbed-e21b8bf79fde","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"display_kind":"fact","label":"已捕获内容 41a20d67-7941-4972-bbed-e21b8bf79fde@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","ref":{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"},"display_kind":"observation","label":"Observation 095479a6-538a-4a49-b2d2-faef5dfda0cb","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:9c0b347fe3f62c2e1671aa4d1a16330338c3bee47ee2a67180ccdbe70a836f46","source":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","target":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","edge_type":"captured_artifact","label":null},{"id":"relation:b8257028fdfb3c4ae031547019aa4c68f8e0ea33f9fddc56b10cc10e64c4c354","source":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","target":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","edge_type":"cites","label":null}],"opaque_cursor":"7mPc3LL2lEjHhYCa7EV18TyAmtKiBm_OEdzrwnpDDiw","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 22 · test_history_lists_only_saved_0

漏洞/控制点：只列真实保存且当前可访问的历史，索引页保持冻结。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 25a53ede-57b7-4e9c-95e9-b8da89c1119f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 453
content-type: application/json
x-request-id: d4b9e2ed-dbe7-43c8-8b69-390b8f128fda

{"items":[{"snapshot_id":"b9c6fa78-3bd1-4a13-9edb-515d83621dbf","view_id":"8b87e811-44f6-4e68-a447-6e0c987e9324","view_revision":"1","created_at":"2026-09-13T07:19:07.868315Z","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":300,"edge_limit":600}}],"opaque_cursor":"B_f3OL1g9hDsmwWfCcI0FHUPdrxWxePNFaqFREmaG3Y"}
```

## Exchange 23 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: b2bf6cd2-b2b1-4427-b9d9-46af4d746472
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: 7c1638fd-7f9e-4c17-b1ef-9185ccda269c

{"view_id":"f4e55782-541c-4a6c-91eb-05cf74b983f6","snapshot_id":"51da1976-6db1-4284-ba96-8ee2b0110b6d","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","ref":{"entity_type":"artifact","id":"41a20d67-7941-4972-bbed-e21b8bf79fde","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"display_kind":"fact","label":"已捕获内容 41a20d67-7941-4972-bbed-e21b8bf79fde@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","ref":{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"},"display_kind":"observation","label":"Observation 095479a6-538a-4a49-b2d2-faef5dfda0cb","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:9c0b347fe3f62c2e1671aa4d1a16330338c3bee47ee2a67180ccdbe70a836f46","source":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","target":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","edge_type":"captured_artifact","label":null},{"id":"relation:b8257028fdfb3c4ae031547019aa4c68f8e0ea33f9fddc56b10cc10e64c4c354","source":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","target":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","edge_type":"cites","label":null}],"opaque_cursor":"JP7xEd5v7qtTUv0ufpF-KMc5BBELSNokqStvQlyDQdY","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 24 · test_history_lists_only_saved_0

漏洞/控制点：只列真实保存且当前可访问的历史，索引页保持冻结。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots?cursor=B_f3OL1g9hDsmwWfCcI0FHUPdrxWxePNFaqFREmaG3Y HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: ec15d88d-3cba-4bce-8471-b546333be628
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 412
content-type: application/json
x-request-id: 7f243ddf-9dde-45d3-b7d9-c59b64247777

{"items":[{"snapshot_id":"b05c2522-569f-4fda-8ac6-2bcd78ec26b3","view_id":"cf104fe8-e1e2-484e-b4e7-77a0e57b3683","view_revision":"1","created_at":"2026-09-13T07:19:07.825724Z","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":300,"edge_limit":600}}],"opaque_cursor":null}
```

## Exchange 25 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=300&edge_limit=600&snapshot_id=b05c2522-569f-4fda-8ac6-2bcd78ec26b3 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: d369b352-a85e-4296-b645-566a840f2931
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: d65a2d4f-4c62-4bbb-8e86-d17bfb15b9a0

{"view_id":"634e181a-7568-4a59-b2a9-2715b170a94f","snapshot_id":"b05c2522-569f-4fda-8ac6-2bcd78ec26b3","view_revision":"1","query_digest":"c41f89753428ae666a30988a04c1a541261af6c8d7f1a1987da812f3dae141c6","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","ref":{"entity_type":"artifact","id":"41a20d67-7941-4972-bbed-e21b8bf79fde","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","ref":{"entity_type":"claim","id":"e375da13-30c9-4211-bfb9-48ad53b38998","revision":"1"},"display_kind":"fact","label":"已捕获内容 41a20d67-7941-4972-bbed-e21b8bf79fde@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","ref":{"entity_type":"observation","id":"f82557d3-2c16-4f57-b0be-473bd348696f","revision":"1"},"display_kind":"observation","label":"Observation 095479a6-538a-4a49-b2d2-faef5dfda0cb","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:9c0b347fe3f62c2e1671aa4d1a16330338c3bee47ee2a67180ccdbe70a836f46","source":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","target":"artifact:41a20d67-7941-4972-bbed-e21b8bf79fde@1","edge_type":"captured_artifact","label":null},{"id":"relation:b8257028fdfb3c4ae031547019aa4c68f8e0ea33f9fddc56b10cc10e64c4c354","source":"claim:e375da13-30c9-4211-bfb9-48ad53b38998@1","target":"observation:f82557d3-2c16-4f57-b0be-473bd348696f@1","edge_type":"cites","label":null}],"opaque_cursor":"J9z9wGLR1z8cdBYVKfTX2e4cIsAsBa4cGCq877K2mZo","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 26 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=300&edge_limit=600&snapshot_id=unknown-saved-snapshot HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: c27fca3e-ae25-49c0-ba2d-4f9e8e81117d
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 161
content-type: application/json
x-request-id: 7a69bed1-36a2-4d88-a739-0673dac3eb73

{"code":"HISTORY_UNAVAILABLE","message":"The request could not be completed.","request_id":"7a69bed1-36a2-4d88-a739-0673dac3eb73","retryable":false,"details":{}}
```

## Exchange 27 · test_history_lists_only_saved_0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: e429b5b6-7d03-4d70-b7f4-bd581d5ae259
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 422
cache-control: no-store
content-length: 156
content-type: application/json
x-request-id: 288ecf3c-c0c6-48c8-bf66-a473ef1bf04d

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"288ecf3c-c0c6-48c8-bf66-a473ef1bf04d","retryable":false,"details":{}}
```

## Exchange 28 · test_opaque_cursor_is_persiste0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 3382256c-f579-4906-bc49-91d200499c5b
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"3382256c-f579-4906-bc49-91d200499c5b","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"d515bf3b-5a85-4312-b76b-4d74597816f0","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: ed635b61-d826-4235-8b9c-8116b087e9ea

{"observation_ref":{"entity_type":"observation","id":"09ad6313-4a69-43d4-bb48-fa5ad7dfbf9f","revision":"1"},"capture_id":"3382256c-f579-4906-bc49-91d200499c5b","status":"accepted","artifact_refs":[{"id":"d515bf3b-5a85-4312-b76b-4d74597816f0","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"ed635b61-d826-4235-8b9c-8116b087e9ea","code":null}
```

## Exchange 29 · test_opaque_cursor_is_persiste0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 28098910-40b1-4d56-a6e0-36a8a0896c50
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 d515bf3b-5a85-4312-b76b-4d74597816f0@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"09ad6313-4a69-43d4-bb48-fa5ad7dfbf9f","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"d515bf3b-5a85-4312-b76b-4d74597816f0","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 92b296f5-7bff-4dd2-bac7-16c20bab58c1

{"status":"accepted_shared","local_ref":"c","request_id":"92b296f5-7bff-4dd2-bac7-16c20bab58c1","canonical_ref":{"entity_type":"claim","id":"a3901124-4279-431a-9175-89791a08d18d","revision":"1"},"code":null}
```

## Exchange 30 · test_opaque_cursor_is_persiste0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: bcf6f937-1e12-442f-a235-5858d27c49c6
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"0394190d-b63c-4ead-bd65-d670b92de16a","claim_ref":{"entity_type":"claim","id":"a3901124-4279-431a-9175-89791a08d18d","revision":"1"},"input_refs":[{"entity_type":"observation","id":"09ad6313-4a69-43d4-bb48-fa5ad7dfbf9f","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 2a416518-484a-4240-9928-28953447ea83

{"assessment_id":"0394190d-b63c-4ead-bd65-d670b92de16a","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"a3901124-4279-431a-9175-89791a08d18d","revision":"1"},"request_id":"2a416518-484a-4240-9928-28953447ea83","code":null}
```

## Exchange 31 · test_opaque_cursor_is_persiste0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: d3a3eaa2-5f23-4b5a-914d-88758f26afde
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: 723af332-62ee-4b2a-b449-acb9db3cb0c8

{"view_id":"70ab7c65-248f-42b8-93d8-0cd714f887a3","snapshot_id":"236aa861-5854-49d4-a0e0-e604cd83748e","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:d515bf3b-5a85-4312-b76b-4d74597816f0@1","ref":{"entity_type":"artifact","id":"d515bf3b-5a85-4312-b76b-4d74597816f0","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"2B-xzca7qM_i20cxOxjc2wfjqJonoV-JnUOS7PbJ4uo","truncated":true,"continuation":"2B-xzca7qM_i20cxOxjc2wfjqJonoV-JnUOS7PbJ4uo","allowed_actions":[]}
```

## Exchange 32 · test_opaque_cursor_is_persiste0

漏洞/控制点：旧视图或错误主体/查询不能复用 opaque cursor。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=2&edge_limit=1&cursor=2B-xzca7qM_i20cxOxjc2wfjqJonoV-JnUOS7PbJ4uo HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 86684ce4-3d59-4633-885f-22636ea3aaa9
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
cache-control: no-store
content-length: 164
content-type: application/json
x-request-id: 6c655fe1-fa98-4835-8a8c-7395f956e3a0

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"6c655fe1-fa98-4835-8a8c-7395f956e3a0","retryable":false,"details":{}}
```

## Exchange 33 · test_opaque_cursor_is_persiste0

漏洞/控制点：旧视图或错误主体/查询不能复用 opaque cursor。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&cursor=2B-xzca7qM_i20cxOxjc2wfjqJonoV-JnUOS7PbJ4uo&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_other}
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
cache-control: no-store
content-length: 164
content-type: application/json
x-request-id: be4d4a33-de9f-4959-802b-cd3f211edf6e

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"be4d4a33-de9f-4959-802b-cd3f211edf6e","retryable":false,"details":{}}
```

## Exchange 34 · test_opaque_cursor_is_persiste0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 401
content-length: 155
content-type: application/json
x-request-id: d9983c43-bb3c-4140-a70d-88f98a45e539

{"code":"UNAUTHENTICATED","message":"A valid bearer token is required.","request_id":"d9983c43-bb3c-4140-a70d-88f98a45e539","retryable":false,"details":{}}
```

## Exchange 35 · test_real_run_origin_is_safe_f0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 4877
content-type: application/json
x-request-id: f42ed26c-28e6-46bd-94fd-6d3a2de33b68

{"view_id":"1bc02563-bf34-4f5d-bd95-1801cbb4b646","snapshot_id":"8e778c0f-e6ec-46dd-a0c6-fa0c0df17010","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"agent_run:a4703552-6300-43f8-b24d-b536b6def408@1","ref":{"entity_type":"agent_run","id":"a4703552-6300-43f8-b24d-b536b6def408","revision":"1"},"display_kind":"agent_run","label":"Run a4703552-6300-43f8-b24d-b536b6def408","state":"registered","allowed_actions":[]},{"id":"agent_run:aa09c282-e76e-434c-94e4-1ca9f113fa36@1","ref":{"entity_type":"agent_run","id":"aa09c282-e76e-434c-94e4-1ca9f113fa36","revision":"1"},"display_kind":"agent_run","label":"Run aa09c282-e76e-434c-94e4-1ca9f113fa36","state":"registered","allowed_actions":[]},{"id":"artifact:39f0e136-0882-465f-b2fc-d5b280a4d116@1","ref":{"entity_type":"artifact","id":"39f0e136-0882-465f-b2fc-d5b280a4d116","revision":"1"},"display_kind":"artifact","label":"text/plain · 27 B","state":"sealed","allowed_actions":[]},{"id":"claim:8a857037-26fb-4277-9f69-bb70bf481334@1","ref":{"entity_type":"claim","id":"8a857037-26fb-4277-9f69-bb70bf481334","revision":"1"},"display_kind":"claim","label":"The isolated P09 input is available.","state":"unassessed","allowed_actions":[]},{"id":"intent:2aced01c-0281-4191-89da-a32987786f6e@1","ref":{"entity_type":"intent","id":"2aced01c-0281-4191-89da-a32987786f6e","revision":"1"},"display_kind":"intent","label":"Read the isolated P09 input.","state":"admitted","allowed_actions":[]},{"id":"origin:task-fixture@2","ref":{"entity_type":"origin","id":"task-fixture","revision":"2"},"display_kind":"origin","label":"P05 isolated fixture","state":"running","allowed_actions":[]},{"id":"work_item:008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7@2","ref":{"entity_type":"work_item","id":"008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7","revision":"2"},"display_kind":"work_item","label":"explore · 008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7","state":"leased","allowed_actions":[]},{"id":"work_item:4cc1b657-fa2f-41af-a934-bc0acdc27a36@2","ref":{"entity_type":"work_item","id":"4cc1b657-fa2f-41af-a934-bc0acdc27a36","revision":"2"},"display_kind":"work_item","label":"reason · 4cc1b657-fa2f-41af-a934-bc0acdc27a36","state":"leased","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:d63e37933e11f5665b3a0092a35c59ec6f1eb1fd101a9b6e8ecff95a218d96c2","source":"claim:8a857037-26fb-4277-9f69-bb70bf481334@1","target":"artifact:39f0e136-0882-465f-b2fc-d5b280a4d116@1","edge_type":"cites","label":null},{"id":"relation:5828bd6b1a0a295d16b2962d979e3058a37e7eb0d8c088c7921898e225976a30","source":"claim:8a857037-26fb-4277-9f69-bb70bf481334@1","target":"intent:2aced01c-0281-4191-89da-a32987786f6e@1","edge_type":"input_to","label":null},{"id":"relation:2e6cb5852e9724e109d91d8110b46e379cf2339614965eb627d5b8307c91be14","source":"origin:task-fixture@2","target":"work_item:008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7@2","edge_type":"contains_work","label":null},{"id":"relation:351cf61f439d653e3d51ce7ff0c7fd5255e81eb4bd03465e2f17cdbbb7891fc8","source":"work_item:008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7@2","target":"agent_run:aa09c282-e76e-434c-94e4-1ca9f113fa36@1","edge_type":"has_run","label":null},{"id":"relation:ff89889380e5d6801a6bb402a6009c3ffb0cd3910d5b552dbec1e9302db76b22","source":"intent:2aced01c-0281-4191-89da-a32987786f6e@1","target":"work_item:008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7@2","edge_type":"scheduled_as","label":null},{"id":"relation:983c76309b94ec0aa612bcae4228e4aff4b77e8026d543d3bfe842800f940072","source":"origin:task-fixture@2","target":"work_item:4cc1b657-fa2f-41af-a934-bc0acdc27a36@2","edge_type":"contains_work","label":null},{"id":"relation:a2bb6458633f1a83c4e4a694556e2f4aaef07cdf8bed3d82164d843ad36ff95d","source":"work_item:4cc1b657-fa2f-41af-a934-bc0acdc27a36@2","target":"agent_run:a4703552-6300-43f8-b24d-b536b6def408@1","edge_type":"has_run","label":null},{"id":"relation:0aa7ea862e43b3e0aacc4f705b1c152c663205be1c1d8c64b18c70b2f8abd75c","source":"origin:task-fixture@2","target":"work_item:work-b@1","edge_type":"contains_work","label":null},{"id":"relation:b82297766f9c8b81afcda450e5b1b5beaab93b6612775da38a632b3a13e229ae","source":"origin:task-fixture@2","target":"work_item:work-fixture@1","edge_type":"contains_work","label":null}],"opaque_cursor":"y1ZVSOQlZhNLYJ0-Gy4B4i8rIsejtNJlNEwuE96olL0","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 36 · test_real_run_origin_is_safe_f0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/agent_run/aa09c282-e76e-434c-94e4-1ca9f113fa36?revision=1&snapshot_id=8e778c0f-e6ec-46dd-a0c6-fa0c0df17010 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 609
content-type: application/json
x-request-id: b6502549-5b4f-4073-90ce-9716337a2c18

{"assessment":null,"ref":{"entity_type":"agent_run","id":"aa09c282-e76e-434c-94e4-1ca9f113fa36","revision":"1"},"display_kind":"agent_run","record":{"identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"008ce0c0-76ce-4b31-aa2b-a9b5f2c3d6d7","agent_run_id":"aa09c282-e76e-434c-94e4-1ca9f113fa36","execution_epoch":"2","run_epoch":"2","runtime_attempt":"1","receiver_id":"receiver-fixture"},"process_state":"registered","result_state":"none","model_mode":"synthetic","created_at":"2026-09-13T07:19:11.361084Z","exited_at":null,"session_manifest":null}}
```

## Exchange 37 · test_real_run_origin_is_safe_f0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/origin/task-fixture?revision=2&snapshot_id=8e778c0f-e6ec-46dd-a0c6-fa0c0df17010 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 473
content-type: application/json
x-request-id: a4d77e73-fc76-4854-afe0-cf157fd6bb29

{"assessment":null,"ref":{"entity_type":"origin","id":"task-fixture","revision":"2"},"display_kind":"origin","record":{"task_id":"task-fixture","tenant_id":"tenant-fixture","project_id":"project-fixture","version":"2","name":"P05 isolated fixture","scenario":"web_single","desired_state":"run","observed_state":"running","goal_revision":"1","execution_epoch":"2","activated_at":"2026-09-13T07:19:10.946807Z","close_trigger":null,"result_outcome":null,"allowed_actions":[]}}
```

## Exchange 38 · test_saved_pages_and_record_st0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 81f4de27-67bd-4223-a92e-5a8049107ae7
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"81f4de27-67bd-4223-a92e-5a8049107ae7","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: d9851dc2-2d81-417f-9e0d-0b628d4a042e

{"observation_ref":{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"},"capture_id":"81f4de27-67bd-4223-a92e-5a8049107ae7","status":"accepted","artifact_refs":[{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"d9851dc2-2d81-417f-9e0d-0b628d4a042e","code":null}
```

## Exchange 39 · test_saved_pages_and_record_st0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 0a70dae2-7f7a-4724-aac1-9268e69abd0f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 571d3825-d8a7-4731-a99a-d73c9eece91f@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 64a86a6b-feeb-4b65-b8da-548a52287e2b

{"status":"accepted_shared","local_ref":"c","request_id":"64a86a6b-feeb-4b65-b8da-548a52287e2b","canonical_ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"},"code":null}
```

## Exchange 40 · test_saved_pages_and_record_st0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 32658176-6bda-4901-99e3-53363985d823
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"98390282-00ba-4317-a083-af09c7d02c7a","claim_ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"},"input_refs":[{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 7f08479f-33b9-45fb-86f9-6e2c7efb7153

{"assessment_id":"98390282-00ba-4317-a083-af09c7d02c7a","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"},"request_id":"7f08479f-33b9-45fb-86f9-6e2c7efb7153","code":null}
```

## Exchange 41 · test_saved_pages_and_record_st0

真实前提：通过既有生产 API 建立证据、Claim 或评估，不是 fake 服务。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 594
content-type: application/json
host: testserver
idempotency-key: f5485930-0692-42da-8075-441313f33bdc
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"New unassessed revision","basis_refs":[{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17},"revises":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 6bb91793-c842-4fa5-b46f-b047aa6e9a45

{"status":"accepted_shared","local_ref":"c","request_id":"6bb91793-c842-4fa5-b46f-b047aa6e9a45","canonical_ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"2"},"code":null}
```

## Exchange 42 · test_saved_pages_and_record_st0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 7af41eb6-5801-41d5-9fa2-afbcb035a0e0
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: fad4b1b5-e010-4d3e-ac7f-f364582fe81c

{"view_id":"fbdadd29-8753-4f1f-bd8c-90a653b4496f","snapshot_id":"7ba73290-a098-47f1-af94-dd46460328e1","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:571d3825-d8a7-4731-a99a-d73c9eece91f@1","ref":{"entity_type":"artifact","id":"571d3825-d8a7-4731-a99a-d73c9eece91f","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"rZnC2nOqma_qG7ZU0gmMfKS8p36VkdRrfoPyc_orllM","truncated":true,"continuation":"rZnC2nOqma_qG7ZU0gmMfKS8p36VkdRrfoPyc_orllM","allowed_actions":[]}
```

## Exchange 43 · test_saved_pages_and_record_st0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=rZnC2nOqma_qG7ZU0gmMfKS8p36VkdRrfoPyc_orllM HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 7835835d-5cd9-4c01-b9bf-837a4a5ba2a9
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 819
content-type: application/json
x-request-id: 155f67d5-e4e6-447b-b6b3-9f1b1a5d0b6c

{"view_id":"fbdadd29-8753-4f1f-bd8c-90a653b4496f","snapshot_id":"7ba73290-a098-47f1-af94-dd46460328e1","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"claim:569b4a03-e806-490a-b855-3aff11018e37@1","ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"},"display_kind":"fact","label":"已捕获内容 571d3825-d8a7-4731-a99a-d73c9eece91f@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]}],"edges":[],"opaque_cursor":"Wi2T1wExSc0_fsTvG4a8531IBdmC8tZpnn1tIHp0eus","truncated":true,"continuation":"Wi2T1wExSc0_fsTvG4a8531IBdmC8tZpnn1tIHp0eus","allowed_actions":[]}
```

## Exchange 44 · test_saved_pages_and_record_st0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=Wi2T1wExSc0_fsTvG4a8531IBdmC8tZpnn1tIHp0eus HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 024af52d-dc29-432a-a5b5-123932273df5
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1047
content-type: application/json
x-request-id: 2fc836a9-d977-4e40-be69-e89926a52d26

{"view_id":"fbdadd29-8753-4f1f-bd8c-90a653b4496f","snapshot_id":"7ba73290-a098-47f1-af94-dd46460328e1","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"observation:7e13d793-65e9-487a-824d-81e24844da85@1","ref":{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"},"display_kind":"observation","label":"Observation 81f4de27-67bd-4223-a92e-5a8049107ae7","state":"complete","allowed_actions":[]}],"edges":[{"id":"relation:8897e29a7b885ef9d8252e29917f36792186a6562cb9760d4b0407d53caaeee4","source":"observation:7e13d793-65e9-487a-824d-81e24844da85@1","target":"artifact:571d3825-d8a7-4731-a99a-d73c9eece91f@1","edge_type":"captured_artifact","label":null}],"opaque_cursor":"lZvDG0TECJye9kIS3GUcdupO96C-J-QaY-M0313iH80","truncated":true,"continuation":"lZvDG0TECJye9kIS3GUcdupO96C-J-QaY-M0313iH80","allowed_actions":[]}
```

## Exchange 45 · test_saved_pages_and_record_st0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=lZvDG0TECJye9kIS3GUcdupO96C-J-QaY-M0313iH80 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 220ce1bc-5cf0-47b4-92b5-d7b519339530
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 932
content-type: application/json
x-request-id: 410df3f6-3ff5-4dac-8ef3-f557405093bb

{"view_id":"fbdadd29-8753-4f1f-bd8c-90a653b4496f","snapshot_id":"7ba73290-a098-47f1-af94-dd46460328e1","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:d142e69caaf470054246731abf620c110802556148168207766b7cd1886b629c","source":"claim:569b4a03-e806-490a-b855-3aff11018e37@1","target":"observation:7e13d793-65e9-487a-824d-81e24844da85@1","edge_type":"cites","label":null}],"opaque_cursor":"yrcTEcpr24WIyZkjHigsCbis2izb4xXFlXkmcGNgJmI","truncated":true,"continuation":"yrcTEcpr24WIyZkjHigsCbis2izb4xXFlXkmcGNgJmI","allowed_actions":[]}
```

## Exchange 46 · test_saved_pages_and_record_st0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=yrcTEcpr24WIyZkjHigsCbis2izb4xXFlXkmcGNgJmI HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: dfb5a61c-4474-4c8a-b298-3463bbce6e03
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 677
content-type: application/json
x-request-id: d051760e-f528-4dde-84b6-8aaafa3444e0

{"view_id":"fbdadd29-8753-4f1f-bd8c-90a653b4496f","snapshot_id":"7ba73290-a098-47f1-af94-dd46460328e1","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"TxiAFLLBM9HCG98qXYpUkDxsQr1y6vJ7Meiu7cRRBFI","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 47 · test_saved_pages_and_record_st0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/569b4a03-e806-490a-b855-3aff11018e37?revision=1&snapshot_id=7ba73290-a098-47f1-af94-dd46460328e1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: fb611c14-1e57-4c60-99ac-4354a9411c52
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: ee5788f9-fe13-4ff7-98ab-61be254b6544

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["98390282-00ba-4317-a083-af09c7d02c7a"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"},"display_kind":"fact","record":{"claim_id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 571d3825-d8a7-4731-a99a-d73c9eece91f@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-13T07:19:05.141526Z","supersedes":null}}
```

## Exchange 48 · test_saved_pages_and_record_st0

漏洞/控制点：详情读取当前重验权限，并从保存版本读取固定正文。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/569b4a03-e806-490a-b855-3aff11018e37?revision=2 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 08942f9d-d744-4880-b34b-6001c75bd67a
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1123
content-type: application/json
x-request-id: f2d444ca-157c-4c7c-9a35-15059157b680

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"2"},"display_kind":"claim","record":{"claim_id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"2","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"New unassessed revision","structured_assertion":{"artifact_ref":{"id":"571d3825-d8a7-4731-a99a-d73c9eece91f","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"7e13d793-65e9-487a-824d-81e24844da85","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-13T07:19:05.252028Z","supersedes":{"entity_type":"claim","id":"569b4a03-e806-490a-b855-3aff11018e37","revision":"1"}}}
```

## Exchange 49 · test_topology_reads_do_not_cre0

漏洞/控制点：固定 snapshot 分页，隐藏数据与内部序号不得进入公开图。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 1a1c10eb-4a1b-486c-917f-8121bb2c87da
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 860
content-type: application/json
x-request-id: 096fe90a-a835-4423-8a91-ffb01b4d4a76

{"view_id":"6fa75a1e-cf5d-455e-9cfb-aeabe574f3d4","snapshot_id":"3866e37e-9686-4523-983e-18fedc18eb84","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"gWQc7OIhT8r3MagUDjKCLuf8J7rGqMb0ik5-x1CTuqA","truncated":false,"continuation":null,"allowed_actions":[]}
```
