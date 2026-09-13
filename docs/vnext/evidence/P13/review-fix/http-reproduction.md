# P13 review-fix 完整 HTTP 请求与响应

以下报文来自两个定向真实 PG/签名 ASGI 用例。method、URL、headers、请求体、响应 headers/status/body 均完整保留；Authorization 已替换为可重新签发的测试变量并保留原 Header SHA-256。

## Exchange 1 · 52c6f113d302

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: c445a32b-f339-4706-986b-facdc0d72591
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"c445a32b-f339-4706-986b-facdc0d72591","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"181adc2a-8f7c-4556-931c-2967babbc7ac","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 3adc18b9-d6e6-40c1-9901-5c142e91f839

{"observation_ref":{"entity_type":"observation","id":"a2f975d2-df9a-4f0f-94c2-457019b3e48e","revision":"1"},"capture_id":"c445a32b-f339-4706-986b-facdc0d72591","status":"accepted","artifact_refs":[{"id":"181adc2a-8f7c-4556-931c-2967babbc7ac","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"3adc18b9-d6e6-40c1-9901-5c142e91f839","code":null}
```

## Exchange 2 · 52c6f113d302

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: e7b69f2b-2ccd-4c43-8ddb-0e6632f9ea51
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 181adc2a-8f7c-4556-931c-2967babbc7ac@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"a2f975d2-df9a-4f0f-94c2-457019b3e48e","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"181adc2a-8f7c-4556-931c-2967babbc7ac","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 108cf44b-72fe-419b-9f48-f257fe14e838

{"status":"accepted_shared","local_ref":"c","request_id":"108cf44b-72fe-419b-9f48-f257fe14e838","canonical_ref":{"entity_type":"claim","id":"f17d03d1-4bf5-4526-849d-ab108b007798","revision":"1"},"code":null}
```

## Exchange 3 · 52c6f113d302

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 03383d5d-8eb0-4f88-841a-b6d5157d03a2
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"598fbfae-5648-4626-acd4-d04055978fe4","claim_ref":{"entity_type":"claim","id":"f17d03d1-4bf5-4526-849d-ab108b007798","revision":"1"},"input_refs":[{"entity_type":"observation","id":"a2f975d2-df9a-4f0f-94c2-457019b3e48e","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: e0469f36-9892-403e-8e0b-50c2761c513e

{"assessment_id":"598fbfae-5648-4626-acd4-d04055978fe4","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"f17d03d1-4bf5-4526-849d-ab108b007798","revision":"1"},"request_id":"e0469f36-9892-403e-8e0b-50c2761c513e","code":null}
```

## Exchange 4 · 52c6f113d302

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8fbb36bb-36c2-43b8-a701-16d019af58c7
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: e8caab43-0488-4769-b07b-06496220fc34

{"view_id":"09d53ddd-6bf9-4068-a486-d8d3d366d197","snapshot_id":"1519b66c-2e5c-4c7e-878d-898a1277b477","view_revision":"1","query_digest":"bf64b351435e915dd7f3db024bded3e055a4cabaa4c3585643fac61e2e8470bf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:181adc2a-8f7c-4556-931c-2967babbc7ac@1","ref":{"entity_type":"artifact","id":"181adc2a-8f7c-4556-931c-2967babbc7ac","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"-RSkZEQWr-ymI0-GV_4y-2ksPOOysr1RPI21Q2VU_EY","truncated":true,"continuation":"-RSkZEQWr-ymI0-GV_4y-2ksPOOysr1RPI21Q2VU_EY","allowed_actions":[]}
```

## Exchange 5 · 52c6f113d302

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: b215b23e-a7c7-4162-92b8-4dcbf920dbdc
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: e3334e56-1c12-49aa-bf6f-690156bf5151

{"view_id":"36b819c4-3eb0-44a6-9be0-0bc8a17a356e","snapshot_id":"6c7857b5-8b6e-49d2-98a7-060875cf46a0","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:181adc2a-8f7c-4556-931c-2967babbc7ac@1","ref":{"entity_type":"artifact","id":"181adc2a-8f7c-4556-931c-2967babbc7ac","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:f17d03d1-4bf5-4526-849d-ab108b007798@1","ref":{"entity_type":"claim","id":"f17d03d1-4bf5-4526-849d-ab108b007798","revision":"1"},"display_kind":"fact","label":"已捕获内容 181adc2a-8f7c-4556-931c-2967babbc7ac@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:a2f975d2-df9a-4f0f-94c2-457019b3e48e@1","ref":{"entity_type":"observation","id":"a2f975d2-df9a-4f0f-94c2-457019b3e48e","revision":"1"},"display_kind":"observation","label":"Observation c445a32b-f339-4706-986b-facdc0d72591","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:039eee82fb48797d2b7d58353808b8887cd1c984d34083ecd2d687ac2244fa40","source":"observation:a2f975d2-df9a-4f0f-94c2-457019b3e48e@1","target":"artifact:181adc2a-8f7c-4556-931c-2967babbc7ac@1","edge_type":"captured_artifact","label":null},{"id":"relation:b8f3a10bc0ab900b65b90c084cdc58369777bdb9421dd6c71e15c303c4512754","source":"claim:f17d03d1-4bf5-4526-849d-ab108b007798@1","target":"observation:a2f975d2-df9a-4f0f-94c2-457019b3e48e@1","edge_type":"cites","label":null}],"opaque_cursor":"m7Vy04MmPtSgVgy2roA2Q1UYNM9-FsVNjveY_guUf4A","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 6 · 52c6f113d302

漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 3a6adc16-2943-41f6-a969-0373a6fb8db6
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 453
content-type: application/json
x-request-id: 46c8ee26-10b7-4ebe-82f2-9785c0dc4d90

{"items":[{"snapshot_id":"6c7857b5-8b6e-49d2-98a7-060875cf46a0","view_id":"36b819c4-3eb0-44a6-9be0-0bc8a17a356e","view_revision":"1","created_at":"2026-09-13T07:57:06.102712Z","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":300,"edge_limit":600}}],"opaque_cursor":"sRseMxVyODjxK3_dvpLVAoO6I7OkRwkefiMH7dNc598"}
```

## Exchange 7 · 52c6f113d302

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=1&edge_limit=1&cursor=-RSkZEQWr-ymI0-GV_4y-2ksPOOysr1RPI21Q2VU_EY HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8a67db49-459c-4d6c-8d8d-37e49ba8da5f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 154
content-type: application/json
x-request-id: 22ea640b-de0e-4125-928c-009838d91a63

{"code":"VIEW_EXPIRED","message":"The request could not be completed.","request_id":"22ea640b-de0e-4125-928c-009838d91a63","retryable":false,"details":{}}
```

## Exchange 8 · 52c6f113d302

漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/not-present?revision=1&snapshot_id=1519b66c-2e5c-4c7e-878d-898a1277b477 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: d70aa9b7-bef5-43f0-8dad-a2c9adacf1a4
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 158
content-type: application/json
x-request-id: 22d2657e-9616-4d6b-81d3-e4b0bf7c7d59

{"code":"SNAPSHOT_EXPIRED","message":"The request could not be completed.","request_id":"22d2657e-9616-4d6b-81d3-e4b0bf7c7d59","retryable":false,"details":{}}
```

## Exchange 9 · 52c6f113d302

漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots?cursor=sRseMxVyODjxK3_dvpLVAoO6I7OkRwkefiMH7dNc598 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 74c6d5d2-bcf5-4cac-a086-ce7e8f44c4c7
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 154
content-type: application/json
x-request-id: 0ed7835d-96bd-40cb-9fde-18b514ba2d8e

{"code":"VIEW_EXPIRED","message":"The request could not be completed.","request_id":"0ed7835d-96bd-40cb-9fde-18b514ba2d8e","retryable":false,"details":{}}
```

## Exchange 10 · 578af394c892

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 4a80f4ed-937f-42ff-9e99-88990003158f
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"4a80f4ed-937f-42ff-9e99-88990003158f","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"a0910150-b9ac-4017-84ec-29871e7c8232","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 0e2a9e3f-91fa-4bf3-ab67-dbe01c212ee4

{"observation_ref":{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"},"capture_id":"4a80f4ed-937f-42ff-9e99-88990003158f","status":"accepted","artifact_refs":[{"id":"a0910150-b9ac-4017-84ec-29871e7c8232","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"0e2a9e3f-91fa-4bf3-ab67-dbe01c212ee4","code":null}
```

## Exchange 11 · 578af394c892

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: a2077499-d6e6-4325-ad64-bc4cbf61b948
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a0910150-b9ac-4017-84ec-29871e7c8232@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"a0910150-b9ac-4017-84ec-29871e7c8232","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: ad7d507b-5e97-4993-873f-173113970d67

{"status":"accepted_shared","local_ref":"c","request_id":"ad7d507b-5e97-4993-873f-173113970d67","canonical_ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"code":null}
```

## Exchange 12 · 578af394c892

真实前提：既有生产 API 建立隔离证据与 Claim。

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 9ed07543-ae51-42e3-89f0-a5f63d5d48ec
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"58f4310e-8085-473d-8dc8-d4d73d46c295","claim_ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"input_refs":[{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 300e1b1a-830f-4b9a-90e4-e48ed8386be3

{"assessment_id":"58f4310e-8085-473d-8dc8-d4d73d46c295","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"request_id":"300e1b1a-830f-4b9a-90e4-e48ed8386be3","code":null}
```

## Exchange 13 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: c111d764-a5ca-4015-ba85-14d441c15327
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: d24ee29e-c823-4fc0-a97b-9b32aa7dfad4

{"view_id":"93d95d5a-1f6e-4f50-a0ef-f07ed26c2aeb","snapshot_id":"b9fbaf7f-650b-4e41-9601-974bb05197a8","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","ref":{"entity_type":"artifact","id":"a0910150-b9ac-4017-84ec-29871e7c8232","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"display_kind":"fact","label":"已捕获内容 a0910150-b9ac-4017-84ec-29871e7c8232@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","ref":{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"},"display_kind":"observation","label":"Observation 4a80f4ed-937f-42ff-9e99-88990003158f","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:06b90b7424a7a5b1fb3cd26a245c72be456bc558cc69b8d60e5cfa8a13f17867","source":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","target":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","edge_type":"captured_artifact","label":null},{"id":"relation:e617bea3f4642eb32cd40c5112a8b9a8ea0c2fadf4a5b326560418f440eaa3a7","source":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","target":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","edge_type":"cites","label":null}],"opaque_cursor":"TENnot9Ba10KObif7QWtDiSSdjY7Zno09zPGtcyrEgw","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 14 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8909b801-247b-4606-b8c9-392b433b3c36
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: 3961fc5b-58df-4810-834f-1ab19cd3005d

{"view_id":"aa502bed-f32f-4dca-b2b3-19d845d59dec","snapshot_id":"4d462627-16fe-4e7f-9f84-23948fbc9bad","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","ref":{"entity_type":"artifact","id":"a0910150-b9ac-4017-84ec-29871e7c8232","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"display_kind":"fact","label":"已捕获内容 a0910150-b9ac-4017-84ec-29871e7c8232@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","ref":{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"},"display_kind":"observation","label":"Observation 4a80f4ed-937f-42ff-9e99-88990003158f","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:06b90b7424a7a5b1fb3cd26a245c72be456bc558cc69b8d60e5cfa8a13f17867","source":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","target":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","edge_type":"captured_artifact","label":null},{"id":"relation:e617bea3f4642eb32cd40c5112a8b9a8ea0c2fadf4a5b326560418f440eaa3a7","source":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","target":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","edge_type":"cites","label":null}],"opaque_cursor":"mOAOJzmt3nVX2GFL5AvPos5waNRG-3_L_Cus5AT1UCQ","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 15 · 578af394c892

漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: a8eea937-682f-4d42-acd8-c018b6af564e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 453
content-type: application/json
x-request-id: 31550867-9bc9-44d7-a5dc-380d00cd2300

{"items":[{"snapshot_id":"4d462627-16fe-4e7f-9f84-23948fbc9bad","view_id":"aa502bed-f32f-4dca-b2b3-19d845d59dec","view_revision":"1","created_at":"2026-09-13T07:57:04.956647Z","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":300,"edge_limit":600}}],"opaque_cursor":"3wd8klNeziufp6KiD4NwewCGsYVj9py-nG2zeleqiY4"}
```

## Exchange 16 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 5d14754a-a8ed-45df-a1d1-d4eb7896320a
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 2176
content-type: application/json
x-request-id: bc2400a5-9c51-4203-8207-c2fcf09ead78

{"view_id":"da07d08b-b1c6-4ddb-8c6b-37a89b56ddec","snapshot_id":"be2a094c-d932-42b7-a1a9-48cb1d8c6883","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","ref":{"entity_type":"artifact","id":"a0910150-b9ac-4017-84ec-29871e7c8232","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]},{"id":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"display_kind":"fact","label":"已捕获内容 a0910150-b9ac-4017-84ec-29871e7c8232@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]},{"id":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","ref":{"entity_type":"observation","id":"30200b53-26e1-410e-8673-9dbed8554f87","revision":"1"},"display_kind":"observation","label":"Observation 4a80f4ed-937f-42ff-9e99-88990003158f","state":"complete","allowed_actions":[]},{"id":"work_item:work-b@1","ref":{"entity_type":"work_item","id":"work-b","revision":"1"},"display_kind":"work_item","label":"explore · work-b","state":"ready","allowed_actions":[]},{"id":"work_item:work-fixture@1","ref":{"entity_type":"work_item","id":"work-fixture","revision":"1"},"display_kind":"work_item","label":"explore · work-fixture","state":"ready","allowed_actions":[]}],"edges":[{"id":"relation:06b90b7424a7a5b1fb3cd26a245c72be456bc558cc69b8d60e5cfa8a13f17867","source":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","target":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","edge_type":"captured_artifact","label":null},{"id":"relation:e617bea3f4642eb32cd40c5112a8b9a8ea0c2fadf4a5b326560418f440eaa3a7","source":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","target":"observation:30200b53-26e1-410e-8673-9dbed8554f87@1","edge_type":"cites","label":null}],"opaque_cursor":"F8E9jZSGbe2aAV0cEHmlp1I-HkAcVUxxr-08PzctA70","truncated":false,"continuation":null,"allowed_actions":[]}
```

## Exchange 17 · 578af394c892

漏洞/控制点：过期历史/游标返回声明内 410，不回退 latest。

```http
GET http://testserver/api/v2/tasks/task-fixture/snapshots?cursor=3wd8klNeziufp6KiD4NwewCGsYVj9py-nG2zeleqiY4 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: ddfa4fd3-4884-4faa-a072-3cb9fe7f221e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 412
content-type: application/json
x-request-id: 8ff1c85d-f421-4558-af84-82ce17bc97f6

{"items":[{"snapshot_id":"b9fbaf7f-650b-4e41-9601-974bb05197a8","view_id":"93d95d5a-1f6e-4f50-a0ef-f07ed26c2aeb","view_revision":"1","created_at":"2026-09-13T07:57:04.912590Z","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":300,"edge_limit":600}}],"opaque_cursor":null}
```

## Exchange 18 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=1&edge_limit=1&snapshot_id=b9fbaf7f-650b-4e41-9601-974bb05197a8 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 4277ba78-b8c9-4ff5-8d6b-b18c3060cdb9
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 764
content-type: application/json
x-request-id: 7b5d85d3-b61f-4b10-a2af-90755b902c5f

{"view_id":"c7f40c3c-69a1-4a1a-9e3d-0ef1824512f7","snapshot_id":"b9fbaf7f-650b-4e41-9601-974bb05197a8","view_revision":"1","query_digest":"a11e8c50e195f8afbb31d099625d444c7524462b4adb4c6c93e1eebd9e734c18","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"artifact:a0910150-b9ac-4017-84ec-29871e7c8232@1","ref":{"entity_type":"artifact","id":"a0910150-b9ac-4017-84ec-29871e7c8232","revision":"1"},"display_kind":"artifact","label":"application/json · 14 B","state":"sealed","allowed_actions":[]}],"edges":[],"opaque_cursor":"4v3rfzy5-HOjJ5NUcDO2zQk89GtVg67I0jO36yQ9Iws","truncated":true,"continuation":"4v3rfzy5-HOjJ5NUcDO2zQk89GtVg67I0jO36yQ9Iws","allowed_actions":[]}
```

## Exchange 19 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=1&edge_limit=1&snapshot_id=b9fbaf7f-650b-4e41-9601-974bb05197a8&cursor=4v3rfzy5-HOjJ5NUcDO2zQk89GtVg67I0jO36yQ9Iws HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 849e900e-6706-43ed-ac93-469c053eb238
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 819
content-type: application/json
x-request-id: 534bd912-f2a1-4ccf-92ab-8a40bd2eae75

{"view_id":"c7f40c3c-69a1-4a1a-9e3d-0ef1824512f7","snapshot_id":"b9fbaf7f-650b-4e41-9601-974bb05197a8","view_revision":"1","query_digest":"a11e8c50e195f8afbb31d099625d444c7524462b4adb4c6c93e1eebd9e734c18","access_scope_digest":"a50cc22ea7f2910a8abc13737623d22b1b4b57277cffc6e3483375e6f48d7ba2","projection_version":"wuji.topology.v1","nodes":[{"id":"claim:3ca3ccf3-aeb6-4793-9928-1e297e6708b3@1","ref":{"entity_type":"claim","id":"3ca3ccf3-aeb6-4793-9928-1e297e6708b3","revision":"1"},"display_kind":"fact","label":"已捕获内容 a0910150-b9ac-4017-84ec-29871e7c8232@1 的 /version 字段等于 17。","state":"supported","allowed_actions":[]}],"edges":[],"opaque_cursor":"Fgy7Acy1TEg6B653E2it8ofBcMpxLJKL_lS0eJWT7dI","truncated":true,"continuation":"Fgy7Acy1TEg6B653E2it8ofBcMpxLJKL_lS0eJWT7dI","allowed_actions":[]}
```

## Exchange 20 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=live&node_limit=300&edge_limit=600&snapshot_id=b9fbaf7f-650b-4e41-9601-974bb05197a8 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: af53f498-64d1-4542-bac0-25a8fa652314
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 422
cache-control: no-store
content-length: 156
content-type: application/json
x-request-id: 6adbde96-1535-4caa-b4fd-35338146ccef

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"6adbde96-1535-4caa-b4fd-35338146ccef","retryable":false,"details":{}}
```

## Exchange 21 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=300&edge_limit=600&snapshot_id=unknown-saved-snapshot HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: e810f6bf-f5af-4648-b2e7-2f1ed879e1cb
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 410
cache-control: no-store
content-length: 161
content-type: application/json
x-request-id: 2f72f971-53a0-4950-a7ed-bf1aac1c952d

{"code":"HISTORY_UNAVAILABLE","message":"The request could not be completed.","request_id":"2f72f971-53a0-4950-a7ed-bf1aac1c952d","retryable":false,"details":{}}
```

## Exchange 22 · 578af394c892

漏洞/控制点：live 携带历史 snapshot_id 必须拒绝，history 续页保持原查询身份。

```http
GET http://testserver/api/v2/tasks/task-fixture/topology?mode=history&node_limit=300&edge_limit=600 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: f53eae31-5c41-4964-ae32-fbcdc7584aec
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 422
cache-control: no-store
content-length: 156
content-type: application/json
x-request-id: 46562e8d-e79d-409c-81b4-a03182236f7e

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"46562e8d-e79d-409c-81b4-a03182236f7e","retryable":false,"details":{}}
```
