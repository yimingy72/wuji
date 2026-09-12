# P04 fix round 1 · complete HTTP exchanges

Boundary under test: public support plus private contradiction must not yield a Fact to a low-clearance reader. RED and GREEN retain full production ASGI requests/responses below. PostgreSQL audit streams are losslessly compressed under runtime/.

Authorization uses freshly generated fixture tokens; `${TOKEN_subject}` replaces the original bearer credential. Regenerate with `tests/vnext/support/identity_provider.py` through the exact pytest command in `green.txt.json`; no private signing key is saved. Methods, URLs, other headers and bodies are complete.

## 1 · red

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 32f5b6ad-ea52-4c18-b914-8d183f5ace76
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"32f5b6ad-ea52-4c18-b914-8d183f5ace76","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 407bb167-5619-4f0a-94f3-f9c06a9f9b25

{"observation_ref":{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"},"capture_id":"32f5b6ad-ea52-4c18-b914-8d183f5ace76","status":"accepted","artifact_refs":[{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"407bb167-5619-4f0a-94f3-f9c06a9f9b25","code":null}
```

## 2 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 56317d07-25d6-4b4d-97e6-f6712fa3f460
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 ed859d00-e262-4d4f-8609-2f646de74a0f@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: cf827306-bc3b-48e0-a91b-460a27b2150b

{"status":"accepted_shared","local_ref":"c","request_id":"cf827306-bc3b-48e0-a91b-460a27b2150b","canonical_ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"code":null}
```

## 3 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 2ae2e098-cac0-43a0-bdec-6662655b36f4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"8863a533-8ed3-43b1-b61c-1ae5360ebd69","claim_ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"input_refs":[{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 15ce8be1-4b90-4736-bfee-6d7404039bc4

{"assessment_id":"8863a533-8ed3-43b1-b61c-1ae5360ebd69","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"request_id":"15ce8be1-4b90-4736-bfee-6d7404039bc4","code":null}
```

## 4 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: d27da707-da58-43a1-8327-63e10900a93c
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: 4abe9aca-3945-413b-a113-befed3ab72d4

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["8863a533-8ed3-43b1-b61c-1ae5360ebd69"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"display_kind":"fact","record":{"claim_id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 ed859d00-e262-4d4f-8609-2f646de74a0f@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:25:30.436655Z","supersedes":null}}
```

## 5 · red

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 3973b05d-c82e-4b79-9649-1465d30b19b4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"3973b05d-c82e-4b79-9649-1465d30b19b4","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"d67412d8-13c8-4975-a7eb-c0a70aff8191","version":"1","sha256":"f2bce444fc9c94d35b4f01a39d0ff560e4fb38f03d7748df298a84b4e6ad33f0"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 50925d6a-2041-4a25-8f62-07ee0aeae372

{"observation_ref":{"entity_type":"observation","id":"47c0f5fa-42be-462e-bf55-cb16feac95a5","revision":"1"},"capture_id":"3973b05d-c82e-4b79-9649-1465d30b19b4","status":"accepted","artifact_refs":[{"id":"d67412d8-13c8-4975-a7eb-c0a70aff8191","version":"1","sha256":"f2bce444fc9c94d35b4f01a39d0ff560e4fb38f03d7748df298a84b4e6ad33f0"}],"request_id":"50925d6a-2041-4a25-8f62-07ee0aeae372","code":null}
```

## 6 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 667
content-type: application/json
host: testserver
idempotency-key: 82121d4b-1c71-4b44-bcf6-42aa8c09309b
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"36b0540f-2d2e-4eb8-a989-87158713e485","claim_ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"input_refs":[{"entity_type":"observation","id":"47c0f5fa-42be-462e-bf55-cb16feac95a5","revision":"1"}],"grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 81f41651-14ae-4200-a0e3-3b3b101cc69c

{"assessment_id":"36b0540f-2d2e-4eb8-a989-87158713e485","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"request_id":"81f41651-14ae-4200-a0e3-3b3b101cc69c","code":null}
```

## 7 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 17ae73f4-8435-4baf-9148-a5df469c87d6
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1215
content-type: application/json
x-request-id: 2f5aa475-5809-4fda-9473-eed56cde75c1

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["36b0540f-2d2e-4eb8-a989-87158713e485","8863a533-8ed3-43b1-b61c-1ae5360ebd69"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"display_kind":"claim","record":{"claim_id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 ed859d00-e262-4d4f-8609-2f646de74a0f@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:25:30.436655Z","supersedes":null}}
```

## 8 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: dd6fd86d-549d-4424-9cb0-98870a2721b0
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: f1dea733-65f1-4fda-b926-383d50ed7e1d

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["8863a533-8ed3-43b1-b61c-1ae5360ebd69"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1"},"display_kind":"fact","record":{"claim_id":"a7a34eaa-9b2d-4bfa-8c6e-9d01ed8f5319","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 ed859d00-e262-4d4f-8609-2f646de74a0f@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"ed859d00-e262-4d4f-8609-2f646de74a0f","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e2f62e9f-7829-4e67-a2de-39eaf846b545","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:25:30.436655Z","supersedes":null}}
```

## 9 · green

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 6785e682-164d-447b-ac73-bb1bde10ad68
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"6785e682-164d-447b-ac73-bb1bde10ad68","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 6ea0212f-9bc0-4ccd-9d54-d1491871ba9b

{"observation_ref":{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"},"capture_id":"6785e682-164d-447b-ac73-bb1bde10ad68","status":"accepted","artifact_refs":[{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"6ea0212f-9bc0-4ccd-9d54-d1491871ba9b","code":null}
```

## 10 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: candidate
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 651294f7-365e-499b-9f0c-4b0eba9cbdde@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 03abd2d7-fa0b-4921-865f-6ec5278b126a

{"status":"accepted_shared","local_ref":"c","request_id":"03abd2d7-fa0b-4921-865f-6ec5278b126a","canonical_ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"code":null}
```

## 11 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/da08e325-611e-444b-9e5d-129fc77f6d32?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 1604626d-9291-44d3-bc9f-540a1f03d37e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1108
content-type: application/json
x-request-id: 1da89391-c7f5-4127-9dbd-7bb7aeda6374

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"display_kind":"claim","record":{"claim_id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 651294f7-365e-499b-9f0c-4b0eba9cbdde@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.367087Z","supersedes":null}}
```

## 12 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 7ec3fcd3-2e49-438f-92b6-7fc93341605a
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"05dbde10-1961-4035-a1b2-c14e11e885ae","claim_ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"input_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 159be927-a6b0-4bb5-84cc-4923c3a77535

{"assessment_id":"05dbde10-1961-4035-a1b2-c14e11e885ae","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"request_id":"159be927-a6b0-4bb5-84cc-4923c3a77535","code":null}
```

## 13 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/da08e325-611e-444b-9e5d-129fc77f6d32?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 10d4d013-f92a-47c4-ba63-348615ccc88e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: d13c6274-604e-401b-bfa3-039d1c5f9416

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["05dbde10-1961-4035-a1b2-c14e11e885ae"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"display_kind":"fact","record":{"claim_id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 651294f7-365e-499b-9f0c-4b0eba9cbdde@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.367087Z","supersedes":null}}
```

## 14 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: candidate
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 651294f7-365e-499b-9f0c-4b0eba9cbdde@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: aaeb6208-9479-4506-ae2a-26fc6af07c70

{"status":"accepted_shared","local_ref":"c","request_id":"03abd2d7-fa0b-4921-865f-6ec5278b126a","canonical_ref":{"entity_type":"claim","id":"da08e325-611e-444b-9e5d-129fc77f6d32","revision":"1"},"code":null}
```

## 15 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 565
content-type: application/json
host: testserver
idempotency-key: candidate
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 651294f7-365e-499b-9f0c-4b0eba9cbdde@1 的 /version 字段等于 17。 ","basis_refs":[{"entity_type":"observation","id":"e4f8afad-218c-43bb-b70b-63652bec3f36","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"651294f7-365e-499b-9f0c-4b0eba9cbdde","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 409
content-length: 163
content-type: application/json
x-request-id: 670edb12-bf03-4800-afef-c95b40a1925e

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"670edb12-bf03-4800-afef-c95b40a1925e","retryable":false,"details":{}}
```

## 16 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: bb35fb20-4890-4b34-9f0c-a972962e6477
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: a0880a7a-e3a9-414d-b113-03ef00c1496c

{"status":"accepted_shared","local_ref":"c","request_id":"a0880a7a-e3a9-414d-b113-03ef00c1496c","canonical_ref":{"entity_type":"claim","id":"f957f74c-a4c8-4460-875a-2a37d91e3ad0","revision":"1"},"code":null}
```

## 17 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/intents/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 182
content-type: application/json
host: testserver
idempotency-key: ebc289a3-3af3-4b64-af0a-951d5f2bb697
user-agent: python-httpx/0.28.1

{"client_ref":"i","question":"Check hypothesis","basis_refs":[{"entity_type":"claim","id":"f957f74c-a4c8-4460-875a-2a37d91e3ad0","revision":"1"}],"expected_output":"actual evidence"}
```

```http
HTTP/1.1 202
content-length: 208
content-type: application/json
x-request-id: 0e22fe53-f88a-4bdc-af3b-381ed733a5d3

{"status":"accepted_shared","local_ref":"i","request_id":"0e22fe53-f88a-4bdc-af3b-381ed733a5d3","canonical_ref":{"entity_type":"intent","id":"8945b2c8-a2fd-41b7-ba91-6bab7feef96c","revision":"1"},"code":null}
```

## 18 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/intent/8945b2c8-a2fd-41b7-ba91-6bab7feef96c?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 1b3cee0c-642e-4382-a116-2db7ae4f7e2f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 472
content-type: application/json
x-request-id: bdc33ede-feb6-4140-9d0b-12ebef2cec42

{"assessment":null,"ref":{"entity_type":"intent","id":"8945b2c8-a2fd-41b7-ba91-6bab7feef96c","revision":"1"},"display_kind":"intent","record":{"intent_id":"8945b2c8-a2fd-41b7-ba91-6bab7feef96c","revision":"1","task_id":"task-fixture","question":"Check hypothesis","basis_refs":[{"entity_type":"claim","id":"f957f74c-a4c8-4460-875a-2a37d91e3ad0","revision":"1"}],"expected_output":"actual evidence","acceptance_state":"admitted","created_at":"2026-09-12T23:27:11.218943Z"}}
```

## 19 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/intent/8945b2c8-a2fd-41b7-ba91-6bab7feef96c?revision=1&snapshot_id=17cc79f9-9bb8-4594-a71e-f5d8b7faeca7 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: bad7df75-a2d9-4c77-b9eb-8e0a4fa2a730
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: be007b99-9ad3-421e-a316-04c927602b44

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"be007b99-9ad3-421e-a316-04c927602b44","retryable":false,"details":{}}
```

## 20 · green

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 40396aaf-83b6-47b2-9262-6816cd5ac995
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"40396aaf-83b6-47b2-9262-6816cd5ac995","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"6c00cafd-7bec-4a5e-b34b-0470b0705ee6","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: a8e3b5b1-719f-47ec-8024-e56e3be7af3e

{"observation_ref":{"entity_type":"observation","id":"e5403926-71a4-4ac8-8005-642109d12213","revision":"1"},"capture_id":"40396aaf-83b6-47b2-9262-6816cd5ac995","status":"accepted","artifact_refs":[{"id":"6c00cafd-7bec-4a5e-b34b-0470b0705ee6","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"a8e3b5b1-719f-47ec-8024-e56e3be7af3e","code":null}
```

## 21 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 6c58cbd4-9849-42ae-b858-777e34584abb
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 6c00cafd-7bec-4a5e-b34b-0470b0705ee6@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"e5403926-71a4-4ac8-8005-642109d12213","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"6c00cafd-7bec-4a5e-b34b-0470b0705ee6","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 585eb919-4f21-495b-bf97-d7c5319da2b9

{"status":"accepted_shared","local_ref":"c","request_id":"585eb919-4f21-495b-bf97-d7c5319da2b9","canonical_ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"code":null}
```

## 22 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 0873e000-db4d-42f6-8af8-eef196f24051
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"4873e26c-6f7a-438b-a7ed-ebaf6ae194a2","claim_ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"input_refs":[{"entity_type":"observation","id":"e5403926-71a4-4ac8-8005-642109d12213","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 64a02daf-ad91-411c-9f84-fadf340515f8

{"assessment_id":"4873e26c-6f7a-438b-a7ed-ebaf6ae194a2","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"request_id":"64a02daf-ad91-411c-9f84-fadf340515f8","code":null}
```

## 23 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6e3309ef-0554-4bf5-8a57-b2c10bf5159e?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: f04fe1d6-2948-4e6d-9400-7543f7fe5c54
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: a2a6fd30-5a43-4468-9003-13cae3a26cac

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["4873e26c-6f7a-438b-a7ed-ebaf6ae194a2"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"display_kind":"fact","record":{"claim_id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 6c00cafd-7bec-4a5e-b34b-0470b0705ee6@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"6c00cafd-7bec-4a5e-b34b-0470b0705ee6","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e5403926-71a4-4ac8-8005-642109d12213","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:11.760060Z","supersedes":null}}
```

## 24 · green

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 90d0cd7a-3ac3-447d-8e38-17b7cb23c5cf
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"90d0cd7a-3ac3-447d-8e38-17b7cb23c5cf","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"7293e4fd-da9e-4d50-8df6-e14d83dc3f3d","version":"1","sha256":"f2bce444fc9c94d35b4f01a39d0ff560e4fb38f03d7748df298a84b4e6ad33f0"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: d6f7b8af-936a-4f9d-b4c2-cf2864ab6a7e

{"observation_ref":{"entity_type":"observation","id":"67deaa90-ccac-47b9-af97-7f84c3c80eb5","revision":"1"},"capture_id":"90d0cd7a-3ac3-447d-8e38-17b7cb23c5cf","status":"accepted","artifact_refs":[{"id":"7293e4fd-da9e-4d50-8df6-e14d83dc3f3d","version":"1","sha256":"f2bce444fc9c94d35b4f01a39d0ff560e4fb38f03d7748df298a84b4e6ad33f0"}],"request_id":"d6f7b8af-936a-4f9d-b4c2-cf2864ab6a7e","code":null}
```

## 25 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 667
content-type: application/json
host: testserver
idempotency-key: f58ae2bd-6eb8-419d-be8d-27539113b6c8
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"ba7e47fd-ddcc-458c-93a1-7dde7ec10949","claim_ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"input_refs":[{"entity_type":"observation","id":"67deaa90-ccac-47b9-af97-7f84c3c80eb5","revision":"1"}],"grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 801e0ddf-e92e-44c8-a0ca-b56f35e45360

{"assessment_id":"ba7e47fd-ddcc-458c-93a1-7dde7ec10949","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"request_id":"801e0ddf-e92e-44c8-a0ca-b56f35e45360","code":null}
```

## 26 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6e3309ef-0554-4bf5-8a57-b2c10bf5159e?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 95e1d950-501f-41da-b144-747cd48ef81f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1215
content-type: application/json
x-request-id: 259a88ab-1bd3-4ad2-9a4d-beff9459e09c

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["4873e26c-6f7a-438b-a7ed-ebaf6ae194a2","ba7e47fd-ddcc-458c-93a1-7dde7ec10949"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1"},"display_kind":"claim","record":{"claim_id":"6e3309ef-0554-4bf5-8a57-b2c10bf5159e","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 6c00cafd-7bec-4a5e-b34b-0470b0705ee6@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"6c00cafd-7bec-4a5e-b34b-0470b0705ee6","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"e5403926-71a4-4ac8-8005-642109d12213","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:11.760060Z","supersedes":null}}
```

## 27 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6e3309ef-0554-4bf5-8a57-b2c10bf5159e?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: db7bb0c8-51db-42e8-b089-cf96606ea704
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 503
content-length: 164
content-type: application/json
x-request-id: aa4a8daa-526a-4233-894a-e6eaf5c912b4

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"aa4a8daa-526a-4233-894a-e6eaf5c912b4","retryable":false,"details":{}}
```

## 28 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6e3309ef-0554-4bf5-8a57-b2c10bf5159e?revision=1&snapshot_id=9f82c8a1-5d31-4037-9c72-eb9109a5781b HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 07ea1df0-3486-4488-881e-f136e34d6029
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 503
content-length: 164
content-type: application/json
x-request-id: b97fdb0c-a506-4ec6-86ad-3ae730f82205

{"code":"CAPABILITY_UNAVAILABLE","message":"The request could not be completed.","request_id":"b97fdb0c-a506-4ec6-86ad-3ae730f82205","retryable":false,"details":{}}
```

## 29 · green

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 7edf1c79-3aa1-4f6a-af5b-901052c85f88
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"7edf1c79-3aa1-4f6a-af5b-901052c85f88","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 37330e3b-e964-472d-b079-f287aa9f48ac

{"observation_ref":{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"},"capture_id":"7edf1c79-3aa1-4f6a-af5b-901052c85f88","status":"accepted","artifact_refs":[{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"37330e3b-e964-472d-b079-f287aa9f48ac","code":null}
```

## 30 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 0d5f928a-f88c-4eae-97f9-82c442e4a5b1
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 529bd895-efe4-461c-975a-1d69d29503a9

{"status":"accepted_shared","local_ref":"c","request_id":"529bd895-efe4-461c-975a-1d69d29503a9","canonical_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"code":null}
```

## 31 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: dcdd4dfa-f073-4bdc-99b2-98dec56ad59d
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"c595915e-6d59-4a88-9d3d-bde49b860149","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"input_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 41bf1be6-9bc6-4c21-b8d6-a8a274b413c3

{"assessment_id":"c595915e-6d59-4a88-9d3d-bde49b860149","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"request_id":"41bf1be6-9bc6-4c21-b8d6-a8a274b413c3","code":null}
```

## 32 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 667
content-type: application/json
host: testserver
idempotency-key: 6e586b9f-463c-433e-8123-e8a7141225a5
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"input_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 46310f17-4494-4ce0-ac56-867b03ae360d

{"assessment_id":"5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"request_id":"46310f17-4494-4ce0-ac56-867b03ae360d","code":null}
```

## 33 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: bfa32cae-a56c-4f5e-86c8-59ed504d87ba
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1215
content-type: application/json
x-request-id: 720d7844-c853-492b-b865-0a42254d4256

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","c595915e-6d59-4a88-9d3d-bde49b860149"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.864389Z","supersedes":null}}
```

## 34 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=1&snapshot_id=41c4ba98-8991-4a6b-bc1d-0e13c9caa699 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 7ed5a0cc-1117-4c2d-9841-8544285457b2
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: c02e656e-9bd0-4843-93fd-ab40a88c3835

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["c595915e-6d59-4a88-9d3d-bde49b860149"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"display_kind":"fact","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.864389Z","supersedes":null}}
```

## 35 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: cff81079-7db9-4d66-88ce-98e509ca8bcb
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"02d33e74-84fc-4a85-bf75-6d75cac33c78","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"input_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: ae66fcb5-7b37-406f-bdd5-bf2b11181ced

{"assessment_id":"02d33e74-84fc-4a85-bf75-6d75cac33c78","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"request_id":"ae66fcb5-7b37-406f-bdd5-bf2b11181ced","code":null}
```

## 36 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 35bfdb47-dfc7-4e7f-9aac-c3b345ecf6f0
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: 35972ea8-eea3-4d7e-997f-c03451d64401

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["02d33e74-84fc-4a85-bf75-6d75cac33c78","5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","c595915e-6d59-4a88-9d3d-bde49b860149"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.864389Z","supersedes":null}}
```

## 37 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 657
content-type: application/json
host: testserver
idempotency-key: 55566451-28f2-4438-9773-2d7c40cc9ff2
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17},"revises":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 5ad94549-b18e-4a01-92a9-567af5dd88af

{"status":"accepted_shared","local_ref":"c","request_id":"5ad94549-b18e-4a01-92a9-567af5dd88af","canonical_ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"2"},"code":null}
```

## 38 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=2 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 78f81942-d27e-4ee3-b7fd-1d9f1c9b5135
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1186
content-type: application/json
x-request-id: 209a4408-a41b-45e8-8913-102eacf067a5

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"2"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"2","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:10.072755Z","supersedes":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"}}}
```

## 39 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 657
content-type: application/json
host: testserver
idempotency-key: 2144caea-3cbf-4aae-a6ae-d22a413b3717
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17},"revises":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"}}
```

```http
HTTP/1.1 409
content-length: 155
content-type: application/json
x-request-id: 13e2df06-9b15-413c-bd65-9e5c64cd9bbf

{"code":"STALE_VERSION","message":"The request could not be completed.","request_id":"13e2df06-9b15-413c-bd65-9e5c64cd9bbf","retryable":false,"details":{}}
```

## 40 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 73b4ccbb-dda9-4dee-83b7-245fc7362a20
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: 3e9461cb-3001-40b0-9b35-be9d209a5ddc

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["02d33e74-84fc-4a85-bf75-6d75cac33c78","5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","c595915e-6d59-4a88-9d3d-bde49b860149"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.864389Z","supersedes":null}}
```

## 41 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=2 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: f81bfeb5-1c57-42b9-927c-99a81e35a403
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1186
content-type: application/json
x-request-id: d376f87a-aa15-48b0-997c-dcc614953d3c

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"2"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"2","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:10.072755Z","supersedes":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"}}}
```

## 42 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/d145052c-89ba-413b-ad73-8706a88fa10d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 7013a793-4b63-4d8c-84cc-d7337eea6808
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: af0ab7ec-5fbc-4dd0-bfc6-6fe4edc2c70c

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["02d33e74-84fc-4a85-bf75-6d75cac33c78","5dd34ce9-dfc0-4c58-abf9-bb052a3c0982","c595915e-6d59-4a88-9d3d-bde49b860149"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1"},"display_kind":"claim","record":{"claim_id":"d145052c-89ba-413b-ad73-8706a88fa10d","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 a1a0852b-2478-4d0a-b616-d57db4c1e9ef@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"a1a0852b-2478-4d0a-b616-d57db4c1e9ef","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"c2bd6e74-9995-4573-b110-76bce4da630a","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:27:09.864389Z","supersedes":null}}
```

## 43 · green

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 4552346f-f655-4bdc-8d42-1d7d0492105d
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"4552346f-f655-4bdc-8d42-1d7d0492105d","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"9f0eb8da-4fe7-4738-b371-0e4dd9a04ef4","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 50a5d108-eadf-48b5-bf44-ba2d9bddad58

{"observation_ref":{"entity_type":"observation","id":"db089e7a-21b9-4a54-9f16-dec39bfc6d2f","revision":"1"},"capture_id":"4552346f-f655-4bdc-8d42-1d7d0492105d","status":"accepted","artifact_refs":[{"id":"9f0eb8da-4fe7-4738-b371-0e4dd9a04ef4","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"50a5d108-eadf-48b5-bf44-ba2d9bddad58","code":null}
```

## 44 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 156
content-type: application/json
host: testserver
idempotency-key: 9c1d9845-3ec9-4b90-a2ca-7d0d6de8bdba
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Reviewed prose","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: cdfc31cf-eb2e-463a-835a-51f27be3c15f

{"status":"accepted_shared","local_ref":"c","request_id":"cdfc31cf-eb2e-463a-835a-51f27be3c15f","canonical_ref":{"entity_type":"claim","id":"bf701160-4b21-4cc7-bda8-3f4e665731d5","revision":"1"},"code":null}
```

## 45 · green

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 664
content-type: application/json
host: testserver
idempotency-key: db49b7e5-b04a-4f57-b762-34cd4f9a040e
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"4b3495a5-5b55-4b1f-b6f8-105aa36c06a7","claim_ref":{"entity_type":"claim","id":"bf701160-4b21-4cc7-bda8-3f4e665731d5","revision":"1"},"input_refs":[{"entity_type":"observation","id":"db089e7a-21b9-4a54-9f16-dec39bfc6d2f","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 14d62893-b57f-4216-bcea-f0d5fe8a3dd7

{"assessment_id":"4b3495a5-5b55-4b1f-b6f8-105aa36c06a7","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"bf701160-4b21-4cc7-bda8-3f4e665731d5","revision":"1"},"request_id":"14d62893-b57f-4216-bcea-f0d5fe8a3dd7","code":null}
```

## 46 · green

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/bf701160-4b21-4cc7-bda8-3f4e665731d5?revision=1&snapshot_id=7fd97692-842a-4957-b853-f623009a22f3 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: c539f28d-f4ad-44b4-ab54-db1a0466d850
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: 9bc7c1ab-23d6-4aed-ae62-62528ab73a66

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"9bc7c1ab-23d6-4aed-ae62-62528ab73a66","retryable":false,"details":{}}
```
