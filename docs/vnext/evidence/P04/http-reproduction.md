# P04 complete fixture HTTP exchanges

Production ASGI routes, not mock handlers; original body bytes are untruncated. `http://testserver` is the in-process ASGI authority, not an external host. PostgreSQL connections and artifact files are real isolated fixtures.

Authorization headers use `${TOKEN_subject}` instead of publishing bearer credentials. Re-run `./scripts/vnext/uv.sh run --frozen pytest tests/vnext/test_knowledge_admission.py -q` to create the isolated database, actual parents/policy grants, freshly signed test issuer and every request. The issuer implementation is `tests/vnext/support/identity_provider.py`; the P04 fixture explicitly adds worker and qualified-human roles. Private signing keys are never saved. Original header hashes are retained in runtime JSONL.

SQL (including requests, parameters, actual results/errors and transaction outcomes) is losslessly gzip-compressed per test. Runtime JSONL retains exact HTTP bodies as base64. Inputs named `capture-*.bin` / `raw-*.bin` retain actual sealed source bytes.

Validation boundaries: candidate self-certification, unrelated prose, partial negation, same-batch failed dependencies, current ACLs and model-output/capture authority are the intentional negative controls below.

## Exchange 1 · 0780bc6e969c

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 472a7358-36b9-4551-9b74-86626459092c
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"472a7358-36b9-4551-9b74-86626459092c","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"e48d3f5a-5d1d-403d-bbad-9e050880ccdd","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 2f888023-378e-4a53-917f-84e2062348e6

{"observation_ref":{"entity_type":"observation","id":"f08844fb-a716-4fd6-a980-5c6d83a7e761","revision":"1"},"capture_id":"472a7358-36b9-4551-9b74-86626459092c","status":"accepted","artifact_refs":[{"id":"e48d3f5a-5d1d-403d-bbad-9e050880ccdd","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"2f888023-378e-4a53-917f-84e2062348e6","code":null}
```

## Exchange 2 · 0780bc6e969c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 490
content-type: application/json
host: testserver
idempotency-key: 23b294d9-7d13-4164-837a-ffb2b7249f76
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"系统安全","basis_refs":[{"entity_type":"observation","id":"f08844fb-a716-4fd6-a980-5c6d83a7e761","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"e48d3f5a-5d1d-403d-bbad-9e050880ccdd","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: d11c016b-572d-4a53-9807-49bd0da5fd3a

{"status":"accepted_shared","local_ref":"c","request_id":"d11c016b-572d-4a53-9807-49bd0da5fd3a","canonical_ref":{"entity_type":"claim","id":"41be60b1-3809-4e9e-aaf3-cf89439f4438","revision":"1"},"code":null}
```

## Exchange 3 · 0780bc6e969c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 4f0bf8ea-23f3-4e25-8905-2b2e6b89e875
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"305cf807-bf59-45ca-9a11-3984c233da26","claim_ref":{"entity_type":"claim","id":"41be60b1-3809-4e9e-aaf3-cf89439f4438","revision":"1"},"input_refs":[{"entity_type":"observation","id":"f08844fb-a716-4fd6-a980-5c6d83a7e761","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 5ec77e8a-04c8-4c33-b5a9-385876a71ad1

{"assessment_id":"305cf807-bf59-45ca-9a11-3984c233da26","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"41be60b1-3809-4e9e-aaf3-cf89439f4438","revision":"1"},"request_id":"5ec77e8a-04c8-4c33-b5a9-385876a71ad1","code":null}
```

## Exchange 4 · 0780bc6e969c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/41be60b1-3809-4e9e-aaf3-cf89439f4438?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 27cf3ea6-c00c-424a-b3af-0680ba3662fa
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1090
content-type: application/json
x-request-id: 1af68d95-3f17-460c-be0d-dae63bc9e734

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":["305cf807-bf59-45ca-9a11-3984c233da26"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"41be60b1-3809-4e9e-aaf3-cf89439f4438","revision":"1"},"display_kind":"claim","record":{"claim_id":"41be60b1-3809-4e9e-aaf3-cf89439f4438","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"系统安全","structured_assertion":{"artifact_ref":{"id":"e48d3f5a-5d1d-403d-bbad-9e050880ccdd","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"f08844fb-a716-4fd6-a980-5c6d83a7e761","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:03.982514Z","supersedes":null}}
```

## Exchange 5 · 0d4ce76ad1ab

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 141
content-type: application/json
host: testserver
idempotency-key: 01c0208d-839b-4124-bee1-edf392028e46
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"original","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: d08dfa48-42d8-4f73-86be-f071b7107a51

{"status":"accepted_shared","local_ref":"c","request_id":"d08dfa48-42d8-4f73-86be-f071b7107a51","canonical_ref":{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"1"},"code":null}
```

## Exchange 6 · 0d4ce76ad1ab

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 234
content-type: application/json
host: testserver
idempotency-key: cc7be6e9-dfa3-4030-b227-bc51f1424d5e
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"revision","basis_refs":[],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 362fba11-10df-4f4f-a063-4e98f66ac780

{"status":"accepted_shared","local_ref":"c","request_id":"362fba11-10df-4f4f-a063-4e98f66ac780","canonical_ref":{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"2"},"code":null}
```

## Exchange 7 · 0d4ce76ad1ab

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1101
content-type: application/json
host: testserver
idempotency-key: 91bf4ba4-de9e-4c9c-8875-ecd739d07583
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"91bf4ba4-de9e-4c9c-8875-ecd739d07583","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"4c310c5c-382a-483d-805e-44b9d5aa4582","read_set":[{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"1"}],"raw_output_ref":{"id":"9a62aedc-ccbb-4453-80cd-088fccb4d2e5","version":"1","sha256":"b8423b15e5f833945141d2402a5d39266fd0d8295f309e42d67418b991008549"},"raw_output_digest":"b8423b15e5f833945141d2402a5d39266fd0d8295f309e42d67418b991008549","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"old analysis","basis_refs":[{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"1"}],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 372
content-type: application/json
x-request-id: 5e531965-d61b-45e5-994a-9120791b0971

{"submission_id":"91bf4ba4-de9e-4c9c-8875-ecd739d07583","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"5e531965-d61b-45e5-994a-9120791b0971","canonical_ref":{"entity_type":"claim","id":"16d63953-5cb0-474a-b40f-5788acef190d","revision":"1"},"code":"STALE_INPUT"}],"request_id":"5e531965-d61b-45e5-994a-9120791b0971","code":null}
```

## Exchange 8 · 0d4ce76ad1ab

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/16d63953-5cb0-474a-b40f-5788acef190d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 3706f9b2-2a9a-4c97-99e3-8b9755bf951e
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 939
content-type: application/json
x-request-id: f0a0cb24-b1e1-4ba0-90b0-277bf2229ecd

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture","stale_input: basis no longer current; cannot drive control decisions"]},"ref":{"entity_type":"claim","id":"16d63953-5cb0-474a-b40f-5788acef190d","revision":"1"},"display_kind":"claim","record":{"claim_id":"16d63953-5cb0-474a-b40f-5788acef190d","revision":"1","task_id":"task-fixture","kind":"hypothesis","assertion_role":"candidate_fact","text":"old analysis","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"175a38b4-7d83-4d99-850d-92ec3ebed4e5","revision":"1"}],"limitations":["isolated fixture","stale_input: basis no longer current; cannot drive control decisions"],"producer_kind":"agent","producer_ref":"run-fixture","created_at":"2026-09-12T23:20:12.007853Z","supersedes":null}}
```

## Exchange 9 · 1445cc054819

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1209
content-type: application/json
host: testserver
idempotency-key: 36ea1b21-d650-4ad9-95aa-2d6c0902fab4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"36ea1b21-d650-4ad9-95aa-2d6c0902fab4","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"2d37f735-26b3-404b-b5eb-8b368dad7261","read_set":[],"raw_output_ref":{"id":"0b3ed290-9a6b-44cb-a84c-815904f4889e","version":"1","sha256":"3f72ad247801e3f37928f20a1c01c09fc2b7fd11cea0c91648eeff0672ada677"},"raw_output_digest":"3f72ad247801e3f37928f20a1c01c09fc2b7fd11cea0c91648eeff0672ada677","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"one","basis_refs":[],"limitations":["isolated fixture"]},{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"two","basis_refs":[],"limitations":["isolated fixture"]},{"client_ref":"ok","kind":"hypothesis","assertion_role":"candidate_fact","text":"unrelated","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 640
content-type: application/json
x-request-id: 1a9baeb8-7560-4fcc-9f88-5963dbe0d4a8

{"submission_id":"36ea1b21-d650-4ad9-95aa-2d6c0902fab4","status":"accepted","components":[{"status":"rejected","local_ref":"a","request_id":"1a9baeb8-7560-4fcc-9f88-5963dbe0d4a8","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"rejected","local_ref":"a","request_id":"1a9baeb8-7560-4fcc-9f88-5963dbe0d4a8","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"accepted_shared","local_ref":"ok","request_id":"1a9baeb8-7560-4fcc-9f88-5963dbe0d4a8","canonical_ref":{"entity_type":"claim","id":"01257fb9-f894-412f-88f6-d33b3d6ab74c","revision":"1"},"code":null}],"request_id":"1a9baeb8-7560-4fcc-9f88-5963dbe0d4a8","code":null}
```

## Exchange 10 · 1ceb1aaa4465

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 87f7b45a-5d88-404a-a4f7-ccc28d35d181
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"87f7b45a-5d88-404a-a4f7-ccc28d35d181","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 0d2c9e8f-0672-4d7f-928e-a67b1b48cd1a

{"observation_ref":{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"},"capture_id":"87f7b45a-5d88-404a-a4f7-ccc28d35d181","status":"accepted","artifact_refs":[{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"0d2c9e8f-0672-4d7f-928e-a67b1b48cd1a","code":null}
```

## Exchange 11 · 1ceb1aaa4465

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

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 48ba8abd-fbc2-4fd3-bee5-c8177502a1e1@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 23bfa304-d478-47fd-a3dc-9619f77eb50b

{"status":"accepted_shared","local_ref":"c","request_id":"23bfa304-d478-47fd-a3dc-9619f77eb50b","canonical_ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"code":null}
```

## Exchange 12 · 1ceb1aaa4465

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/3ad56c53-7305-40b5-b85c-215478998de6?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: fc8f74e1-8eac-4907-b588-b7f72f803979
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1108
content-type: application/json
x-request-id: 8f21f4ee-2c29-44ce-988f-377e54d949bd

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"display_kind":"claim","record":{"claim_id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 48ba8abd-fbc2-4fd3-bee5-c8177502a1e1@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:02.743779Z","supersedes":null}}
```

## Exchange 13 · 1ceb1aaa4465

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 7be0b6e5-a10b-4be4-8601-59adf84535b9
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"1e4aeb18-8104-467d-827d-d34dc2d39845","claim_ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"input_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 3d4ba51a-e957-4873-8769-bce4fe1b73e3

{"assessment_id":"1e4aeb18-8104-467d-827d-d34dc2d39845","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"request_id":"3d4ba51a-e957-4873-8769-bce4fe1b73e3","code":null}
```

## Exchange 14 · 1ceb1aaa4465

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/3ad56c53-7305-40b5-b85c-215478998de6?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 86b0feeb-0275-4484-9ef0-b98cbd23d2b5
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: 74a324a6-7223-4dae-9cb7-0bdc10ea126d

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["1e4aeb18-8104-467d-827d-d34dc2d39845"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"display_kind":"fact","record":{"claim_id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 48ba8abd-fbc2-4fd3-bee5-c8177502a1e1@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:02.743779Z","supersedes":null}}
```

## Exchange 15 · 1ceb1aaa4465

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

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 48ba8abd-fbc2-4fd3-bee5-c8177502a1e1@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 5728d87b-f75d-4b4b-810c-f7258ffc0fff

{"status":"accepted_shared","local_ref":"c","request_id":"23bfa304-d478-47fd-a3dc-9619f77eb50b","canonical_ref":{"entity_type":"claim","id":"3ad56c53-7305-40b5-b85c-215478998de6","revision":"1"},"code":null}
```

## Exchange 16 · 1ceb1aaa4465

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

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 48ba8abd-fbc2-4fd3-bee5-c8177502a1e1@1 的 /version 字段等于 17。 ","basis_refs":[{"entity_type":"observation","id":"1bd86634-9869-4187-9dd2-9849c14fe9d8","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"48ba8abd-fbc2-4fd3-bee5-c8177502a1e1","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 409
content-length: 163
content-type: application/json
x-request-id: 58e5fb43-9b95-4d5b-86d0-295839b41778

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"58e5fb43-9b95-4d5b-86d0-295839b41778","retryable":false,"details":{}}
```

## Exchange 17 · 21ec8deca74c

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 676
content-type: application/json
host: testserver
idempotency-key: zero-tool-result
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"zero-tool-result","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-b","agent_run_id":"zero-tool-run","receiver_id":"zero-receiver","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"e289be6e-0e4c-4e2a-b61f-814fe3ec79f0","read_set":[],"raw_output_ref":{"id":"523db691-e9b9-438a-9b11-2721d967399d","version":"1","sha256":"602502483a638f815d691a8200ad08dfeadb92187a51bf633b4d123dbef07151"},"raw_output_digest":"602502483a638f815d691a8200ad08dfeadb92187a51bf633b4d123dbef07151","payload":null,"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 343
content-type: application/json
x-request-id: 6bb354aa-5ff3-43d0-bca6-6c2acdb41403

{"submission_id":"zero-tool-result","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"6bb354aa-5ff3-43d0-bca6-6c2acdb41403","canonical_ref":{"entity_type":"claim","id":"32d6b90b-5fb2-4de9-9be5-ee6350eed0a6","revision":"1"},"code":null}],"request_id":"6bb354aa-5ff3-43d0-bca6-6c2acdb41403","code":null}
```

## Exchange 18 · 2a590f32de0c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 140
content-type: application/json
host: testserver
idempotency-key: e2cd2278-e65f-4a9b-ab57-1226c55f1298
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"initial","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 857cf0dc-e520-414e-9ecf-ca3dc6b7f7ef

{"status":"accepted_shared","local_ref":"c","request_id":"857cf0dc-e520-414e-9ecf-ca3dc6b7f7ef","canonical_ref":{"entity_type":"claim","id":"d6f4da3d-6074-463a-b8d3-0e1363730d59","revision":"1"},"code":null}
```

## Exchange 19 · 2a590f32de0c

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1395
content-type: application/json
host: testserver
idempotency-key: 564dbe29-c6fc-4e7d-a4e1-22145872d15f
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"564dbe29-c6fc-4e7d-a4e1-22145872d15f","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"b48cf5c4-2e90-43f2-b94d-a9c626ef19d7","read_set":[],"raw_output_ref":{"id":"bfdcef71-e14e-4f66-87fb-a887e9911fc5","version":"1","sha256":"bf704378c0a0e6105960b9dad240d4782189b7ec70c168b29ea094a32d6ce2f4"},"raw_output_digest":"bf704378c0a0e6105960b9dad240d4782189b7ec70c168b29ea094a32d6ce2f4","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"one","basis_refs":[],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"d6f4da3d-6074-463a-b8d3-0e1363730d59","revision":"1"}},{"client_ref":"b","kind":"hypothesis","assertion_role":"candidate_fact","text":"two","basis_refs":[],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"d6f4da3d-6074-463a-b8d3-0e1363730d59","revision":"1"}},{"client_ref":"ok","kind":"hypothesis","assertion_role":"candidate_fact","text":"unrelated","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 640
content-type: application/json
x-request-id: 28ef751d-98de-4dd6-9679-63be5ac31a1e

{"submission_id":"564dbe29-c6fc-4e7d-a4e1-22145872d15f","status":"accepted","components":[{"status":"rejected","local_ref":"a","request_id":"28ef751d-98de-4dd6-9679-63be5ac31a1e","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"rejected","local_ref":"b","request_id":"28ef751d-98de-4dd6-9679-63be5ac31a1e","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"accepted_shared","local_ref":"ok","request_id":"28ef751d-98de-4dd6-9679-63be5ac31a1e","canonical_ref":{"entity_type":"claim","id":"0cf92ed1-5a34-4ed5-824e-786def379347","revision":"1"},"code":null}],"request_id":"28ef751d-98de-4dd6-9679-63be5ac31a1e","code":null}
```

## Exchange 20 · 30e5e4fb1b23

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: 366f72b5-0dc1-48d9-b610-bbae8aeb84ee
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 311bd9f3-2dca-42f3-b58b-3943a36f8127

{"status":"accepted_shared","local_ref":"c","request_id":"311bd9f3-2dca-42f3-b58b-3943a36f8127","canonical_ref":{"entity_type":"claim","id":"fea324c8-e2f6-4c1d-92f0-2b783b90d5c2","revision":"1"},"code":null}
```

## Exchange 21 · 30e5e4fb1b23

```http
POST http://testserver/api/v2/tasks/task-fixture/intents/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 182
content-type: application/json
host: testserver
idempotency-key: d714aee6-6cab-42a6-9c4b-bed9a6334088
user-agent: python-httpx/0.28.1

{"client_ref":"i","question":"Check hypothesis","basis_refs":[{"entity_type":"claim","id":"fea324c8-e2f6-4c1d-92f0-2b783b90d5c2","revision":"1"}],"expected_output":"actual evidence"}
```

```http
HTTP/1.1 202
content-length: 208
content-type: application/json
x-request-id: 1867d6b1-5ff8-4a75-b897-995806e7f59a

{"status":"accepted_shared","local_ref":"i","request_id":"1867d6b1-5ff8-4a75-b897-995806e7f59a","canonical_ref":{"entity_type":"intent","id":"686892b4-8644-4699-9d1d-5419e744208d","revision":"1"},"code":null}
```

## Exchange 22 · 30e5e4fb1b23

```http
GET http://testserver/api/v2/tasks/task-fixture/records/intent/686892b4-8644-4699-9d1d-5419e744208d?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8f93aed5-ce26-43d3-a0ef-98c2bcde2ec5
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 472
content-type: application/json
x-request-id: c63f1f85-a1e2-42cf-94c5-5088e4cf2688

{"assessment":null,"ref":{"entity_type":"intent","id":"686892b4-8644-4699-9d1d-5419e744208d","revision":"1"},"display_kind":"intent","record":{"intent_id":"686892b4-8644-4699-9d1d-5419e744208d","revision":"1","task_id":"task-fixture","question":"Check hypothesis","basis_refs":[{"entity_type":"claim","id":"fea324c8-e2f6-4c1d-92f0-2b783b90d5c2","revision":"1"}],"expected_output":"actual evidence","acceptance_state":"admitted","created_at":"2026-09-12T23:20:15.264192Z"}}
```

## Exchange 23 · 30e5e4fb1b23

```http
GET http://testserver/api/v2/tasks/task-fixture/records/intent/686892b4-8644-4699-9d1d-5419e744208d?revision=1&snapshot_id=8988dcbc-fbb5-4fac-9f6d-9e7aa6645257 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 02d7733e-9f06-4238-a53c-a150295a3c9f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 422
content-length: 159
content-type: application/json
x-request-id: 6cf7f54e-3cd9-48f3-932e-dfb048f9fc61

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"6cf7f54e-3cd9-48f3-932e-dfb048f9fc61","retryable":false,"details":{}}
```

## Exchange 24 · 70993de7ade9

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 703
content-type: application/json
host: testserver
idempotency-key: c2c7c547-a884-4a25-ad45-c3f3827441d3
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"c2c7c547-a884-4a25-ad45-c3f3827441d3","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"4c5c48fe-1e4b-41fe-b168-8f71cf447e2c","read_set":[],"raw_output_ref":{"id":"30fffc11-7f0d-4aa9-8560-f50ed51b602c","version":"1","sha256":"658f2246fd8f6e2c79a749755d7fab8ea69bc4d34c1d6e947ef131886a05cfeb"},"raw_output_digest":"658f2246fd8f6e2c79a749755d7fab8ea69bc4d34c1d6e947ef131886a05cfeb","payload":null,"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 168
content-type: application/json
x-request-id: 361dda67-5c2a-4c0a-b103-e7d07896084f

{"submission_id":"c2c7c547-a884-4a25-ad45-c3f3827441d3","status":"rejected","components":[],"request_id":"361dda67-5c2a-4c0a-b103-e7d07896084f","code":"INVALID_SCHEMA"}
```

## Exchange 25 · 70993de7ade9

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 703
content-type: application/json
host: testserver
idempotency-key: c2c7c547-a884-4a25-ad45-c3f3827441d3
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"c2c7c547-a884-4a25-ad45-c3f3827441d3","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"4c5c48fe-1e4b-41fe-b168-8f71cf447e2c","read_set":[],"raw_output_ref":{"id":"30fffc11-7f0d-4aa9-8560-f50ed51b602c","version":"1","sha256":"658f2246fd8f6e2c79a749755d7fab8ea69bc4d34c1d6e947ef131886a05cfeb"},"raw_output_digest":"658f2246fd8f6e2c79a749755d7fab8ea69bc4d34c1d6e947ef131886a05cfeb","payload":null,"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 168
content-type: application/json
x-request-id: 44428cfa-9880-4368-9f2e-6b9e8c63b05b

{"submission_id":"c2c7c547-a884-4a25-ad45-c3f3827441d3","status":"rejected","components":[],"request_id":"361dda67-5c2a-4c0a-b103-e7d07896084f","code":"INVALID_SCHEMA"}
```

## Exchange 26 · 71c03add015c

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 0146523c-54fa-4ac1-b8a2-b2b94b0b5bda
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"0146523c-54fa-4ac1-b8a2-b2b94b0b5bda","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 1b71f76d-6488-43e7-9f95-79358f139461

{"observation_ref":{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"},"capture_id":"0146523c-54fa-4ac1-b8a2-b2b94b0b5bda","status":"accepted","artifact_refs":[{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"1b71f76d-6488-43e7-9f95-79358f139461","code":null}
```

## Exchange 27 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 8f122a71-f5f5-4c48-822a-93e3d81a5657
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 89d6b885-57f2-412b-82be-5c15be6210bb

{"status":"accepted_shared","local_ref":"c","request_id":"89d6b885-57f2-412b-82be-5c15be6210bb","canonical_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"code":null}
```

## Exchange 28 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: e86229d6-37a8-4fa2-86cc-68374cbe0718
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"764f85a0-e1bd-4bfc-903f-38064e4c31a2","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"input_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 531dc1ba-c1e1-44fb-9190-6f39cb5aa61f

{"assessment_id":"764f85a0-e1bd-4bfc-903f-38064e4c31a2","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"request_id":"531dc1ba-c1e1-44fb-9190-6f39cb5aa61f","code":null}
```

## Exchange 29 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 667
content-type: application/json
host: testserver
idempotency-key: 070150fb-c1ef-4654-bd70-a60ad2ab712d
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"8527eef1-8af6-457c-8601-2b0f12b4ec9b","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"input_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 59341516-411b-4781-9d5c-9c523059a63a

{"assessment_id":"8527eef1-8af6-457c-8601-2b0f12b4ec9b","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"request_id":"59341516-411b-4781-9d5c-9c523059a63a","code":null}
```

## Exchange 30 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: c24abfa2-064b-419e-8dc1-941cf58efe6b
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1215
content-type: application/json
x-request-id: 76830969-144c-4f08-b2f0-0de04e9f08af

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["764f85a0-e1bd-4bfc-903f-38064e4c31a2","8527eef1-8af6-457c-8601-2b0f12b4ec9b"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.526101Z","supersedes":null}}
```

## Exchange 31 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=1&snapshot_id=f79e9541-5d37-49b2-82cc-0f410d14c199 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: e85d9f93-1b0a-498f-9044-b6d9b7a4ddef
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1170
content-type: application/json
x-request-id: ff4f8cf0-fd07-4d29-8026-371cef7d6fbc

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["764f85a0-e1bd-4bfc-903f-38064e4c31a2"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"display_kind":"fact","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.526101Z","supersedes":null}}
```

## Exchange 32 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 3ef2fad2-2569-4d63-9ce7-3a2d256f69b6
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"ee244773-556b-49e7-b0a5-d6dfc561a1fd","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"input_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 6c0f702b-e6a6-497c-aa53-58241d9b3883

{"assessment_id":"ee244773-556b-49e7-b0a5-d6dfc561a1fd","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"request_id":"6c0f702b-e6a6-497c-aa53-58241d9b3883","code":null}
```

## Exchange 33 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 7f9cb280-e6bd-404f-915b-3b4e3b5a2ef8
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: 1d3a9a4e-91d5-49be-8b77-74fe7541427f

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["764f85a0-e1bd-4bfc-903f-38064e4c31a2","8527eef1-8af6-457c-8601-2b0f12b4ec9b","ee244773-556b-49e7-b0a5-d6dfc561a1fd"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.526101Z","supersedes":null}}
```

## Exchange 34 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 657
content-type: application/json
host: testserver
idempotency-key: 73448457-ee0b-4add-b847-451a21fd2a93
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17},"revises":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 536a1491-c424-49af-b59a-6f72d7ecef37

{"status":"accepted_shared","local_ref":"c","request_id":"536a1491-c424-49af-b59a-6f72d7ecef37","canonical_ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"2"},"code":null}
```

## Exchange 35 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=2 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 05f7774d-5e12-4968-b85c-cb1f97322ec3
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1186
content-type: application/json
x-request-id: 808285c5-9d20-4dc3-bc43-559ba614058f

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"2"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"2","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.714021Z","supersedes":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"}}}
```

## Exchange 36 · 71c03add015c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 657
content-type: application/json
host: testserver
idempotency-key: f6b15b88-f9df-4e2f-93c4-dc30a03349f9
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17},"revises":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"}}
```

```http
HTTP/1.1 409
content-length: 155
content-type: application/json
x-request-id: 69007369-9a35-405b-9451-2bc79f4c9254

{"code":"STALE_VERSION","message":"The request could not be completed.","request_id":"69007369-9a35-405b-9451-2bc79f4c9254","retryable":false,"details":{}}
```

## Exchange 37 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 6b5504ef-990d-4bd8-8bef-a1482683e2ec
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: a7ca5962-000c-4014-855a-0259d73c9b77

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["764f85a0-e1bd-4bfc-903f-38064e4c31a2","8527eef1-8af6-457c-8601-2b0f12b4ec9b","ee244773-556b-49e7-b0a5-d6dfc561a1fd"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.526101Z","supersedes":null}}
```

## Exchange 38 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=2 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 772e408f-dd87-4537-afa1-53b549852f1b
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1186
content-type: application/json
x-request-id: 1b92214b-5097-4b32-8096-6554840b55f4

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"2"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"2","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.714021Z","supersedes":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"}}}
```

## Exchange 39 · 71c03add015c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/1d769114-f3fe-450e-b08f-6f8b26b7f873?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 3f6ea876-2de8-43aa-a6c7-12475c68bd62
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1254
content-type: application/json
x-request-id: bfa34e32-ec39-4a74-89a6-055c6c6eb834

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"disputed","eligible":false,"assessment_ids":["764f85a0-e1bd-4bfc-903f-38064e4c31a2","8527eef1-8af6-457c-8601-2b0f12b4ec9b","ee244773-556b-49e7-b0a5-d6dfc561a1fd"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1"},"display_kind":"claim","record":{"claim_id":"1d769114-f3fe-450e-b08f-6f8b26b7f873","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 8014dbc7-15df-4a26-9ad6-f880fc6b1d7c@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"8014dbc7-15df-4a26-9ad6-f880fc6b1d7c","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"be45b0aa-afc1-468a-8e8c-b6a68b5e4edd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.526101Z","supersedes":null}}
```

## Exchange 40 · 742e31b18ea6

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 947
content-type: application/json
host: testserver
idempotency-key: b6634c73-89c5-4d42-8348-d47d835e68db
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"b6634c73-89c5-4d42-8348-d47d835e68db","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"dcf69960-c185-4477-a415-c8da3ce13a8d","read_set":[],"raw_output_ref":{"id":"283a874b-3a9b-49e3-91db-5fca690a0b7b","version":"1","sha256":"955edc32f292018ac7217061f86e50314ab8adeb96c86a537939d2b17819c8f3"},"raw_output_digest":"955edc32f292018ac7217061f86e50314ab8adeb96c86a537939d2b17819c8f3","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"received, then publish","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 363
content-type: application/json
x-request-id: 711ab5d5-13c1-4997-95a5-da29ebd5f9c8

{"submission_id":"b6634c73-89c5-4d42-8348-d47d835e68db","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"711ab5d5-13c1-4997-95a5-da29ebd5f9c8","canonical_ref":{"entity_type":"claim","id":"66624030-52e7-42c9-84ff-566cf9e9f605","revision":"1"},"code":null}],"request_id":"711ab5d5-13c1-4997-95a5-da29ebd5f9c8","code":null}
```

## Exchange 41 · 742e31b18ea6

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 941
content-type: application/json
host: testserver
idempotency-key: 5be26a5c-2b9b-4b89-a9b9-4a687697a7e8
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"5be26a5c-2b9b-4b89-a9b9-4a687697a7e8","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"0bf601f0-1ca1-45fe-9d81-3d5ccf762d86","read_set":[],"raw_output_ref":{"id":"a85e2472-f1a9-4513-9248-870960027f77","version":"1","sha256":"5be36948f7d0b532b67f6c257ba4cf49e55f48fd70bebabc44ff394231a258e1"},"raw_output_digest":"5be36948f7d0b532b67f6c257ba4cf49e55f48fd70bebabc44ff394231a258e1","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"client alternate","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 168
content-type: application/json
x-request-id: ee3bc2df-2ee7-4f01-8dbc-9fcb7a523126

{"submission_id":"5be26a5c-2b9b-4b89-a9b9-4a687697a7e8","status":"rejected","components":[],"request_id":"ee3bc2df-2ee7-4f01-8dbc-9fcb7a523126","code":"INVALID_SCHEMA"}
```

## Exchange 42 · 742e31b18ea6

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 940
content-type: application/json
host: testserver
idempotency-key: ce817765-4443-4c0a-b0cb-605f352e1e5e
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"ce817765-4443-4c0a-b0cb-605f352e1e5e","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"9495e801-363e-460c-80c1-9a83670568c0","read_set":[],"raw_output_ref":{"id":"d9ccbd55-8432-4453-b943-5b3ba24a1d7b","version":"1","sha256":"eb6105fbc6643f44499a45d601a0e2d217dea0e8b9ee406c3fe6121a9fa30011"},"raw_output_digest":"eb6105fbc6643f44499a45d601a0e2d217dea0e8b9ee406c3fe6121a9fa30011","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"historical only","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 163
content-type: application/json
x-request-id: f75cf0c7-3587-4a9e-b3c5-627cb54448b1

{"submission_id":"ce817765-4443-4c0a-b0cb-605f352e1e5e","status":"historical_only","components":[],"request_id":"f75cf0c7-3587-4a9e-b3c5-627cb54448b1","code":null}
```

## Exchange 43 · 77036ba0c796

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 0adaa11b-ae7c-4786-8320-46e1247f9c63
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"0adaa11b-ae7c-4786-8320-46e1247f9c63","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"697f2d24-541b-4362-a10e-de88dff77644","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 2f5b7faa-84f1-463b-9637-47d298e290ab

{"observation_ref":{"entity_type":"observation","id":"73388b9d-4412-4d98-a903-1965d3d2fada","revision":"1"},"capture_id":"0adaa11b-ae7c-4786-8320-46e1247f9c63","status":"accepted","artifact_refs":[{"id":"697f2d24-541b-4362-a10e-de88dff77644","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"2f5b7faa-84f1-463b-9637-47d298e290ab","code":null}
```

## Exchange 44 · 77036ba0c796

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: fd1ee790-11f0-4141-aef2-4d699b8f6741
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 697f2d24-541b-4362-a10e-de88dff77644@1 的 /version 字段等于 18。","basis_refs":[{"entity_type":"observation","id":"73388b9d-4412-4d98-a903-1965d3d2fada","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"697f2d24-541b-4362-a10e-de88dff77644","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":18}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 8558bf83-811d-4a1a-bb96-fa84339abac7

{"status":"accepted_shared","local_ref":"c","request_id":"8558bf83-811d-4a1a-bb96-fa84339abac7","canonical_ref":{"entity_type":"claim","id":"6e35c481-50e2-4289-a753-a30653f33d42","revision":"1"},"code":null}
```

## Exchange 45 · 77036ba0c796

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 9476a33f-392a-48d5-89e3-271d9a6691dd
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"be7f6a4d-bb8b-4fe7-8b76-f6995aef0856","claim_ref":{"entity_type":"claim","id":"6e35c481-50e2-4289-a753-a30653f33d42","revision":"1"},"input_refs":[{"entity_type":"observation","id":"73388b9d-4412-4d98-a903-1965d3d2fada","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 0c96c385-7856-4306-8ac3-a333659f9855

{"assessment_id":"be7f6a4d-bb8b-4fe7-8b76-f6995aef0856","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"6e35c481-50e2-4289-a753-a30653f33d42","revision":"1"},"request_id":"0c96c385-7856-4306-8ac3-a333659f9855","code":null}
```

## Exchange 46 · 77036ba0c796

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6e35c481-50e2-4289-a753-a30653f33d42?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 0a4059b3-5b9a-4090-8e0f-fa5a182a05f6
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1175
content-type: application/json
x-request-id: 6824fbfe-9b70-4480-8e2a-49bf706ffd21

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","eligible":false,"assessment_ids":["be7f6a4d-bb8b-4fe7-8b76-f6995aef0856"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"6e35c481-50e2-4289-a753-a30653f33d42","revision":"1"},"display_kind":"claim","record":{"claim_id":"6e35c481-50e2-4289-a753-a30653f33d42","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 697f2d24-541b-4362-a10e-de88dff77644@1 的 /version 字段等于 18。","structured_assertion":{"artifact_ref":{"id":"697f2d24-541b-4362-a10e-de88dff77644","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":18,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"73388b9d-4412-4d98-a903-1965d3d2fada","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:03.292406Z","supersedes":null}}
```

## Exchange 47 · 7c3e160ac9ca

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 746
content-type: application/json
host: testserver
idempotency-key: 6ed787fb-30ae-4504-8142-3aedfe94f393
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"6ed787fb-30ae-4504-8142-3aedfe94f393","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"1fe795bc-9b50-45b5-a78f-4d7a327bab32","version":"1","sha256":"50eabeac941abbde0d6306985771fee58c27e9d539a59ccb3c42c5d941b29f6c"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 84b42b1d-0231-493f-b44b-16d900a1724e

{"observation_ref":{"entity_type":"observation","id":"0febfdad-fdc8-495f-b7ae-033a1dbed263","revision":"1"},"capture_id":"6ed787fb-30ae-4504-8142-3aedfe94f393","status":"accepted","artifact_refs":[{"id":"1fe795bc-9b50-45b5-a78f-4d7a327bab32","version":"1","sha256":"50eabeac941abbde0d6306985771fee58c27e9d539a59ccb3c42c5d941b29f6c"}],"request_id":"84b42b1d-0231-493f-b44b-16d900a1724e","code":null}
```

## Exchange 48 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 580
content-type: application/json
host: testserver
idempotency-key: 2784c6d4-2084-4d11-97f7-4257334fb2d8
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 1fe795bc-9b50-45b5-a78f-4d7a327bab32@1 的 /version 字段等于 \"healthy\"。","basis_refs":[{"entity_type":"observation","id":"0febfdad-fdc8-495f-b7ae-033a1dbed263","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"1fe795bc-9b50-45b5-a78f-4d7a327bab32","version":"1","sha256":"50eabeac941abbde0d6306985771fee58c27e9d539a59ccb3c42c5d941b29f6c"},"pointer":"/version","expected":"healthy"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 65632348-b186-4bdc-a291-e592775e1c64

{"status":"accepted_shared","local_ref":"c","request_id":"65632348-b186-4bdc-a291-e592775e1c64","canonical_ref":{"entity_type":"claim","id":"7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6","revision":"1"},"code":null}
```

## Exchange 49 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: f7465f19-a2a3-4d8c-ad04-6d7363cae2c5
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"4081fb2b-af46-470a-b5c9-4f7f722b2552","claim_ref":{"entity_type":"claim","id":"7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6","revision":"1"},"input_refs":[{"entity_type":"observation","id":"0febfdad-fdc8-495f-b7ae-033a1dbed263","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 8336f96a-9abd-4dc0-b0e6-e24976a84231

{"assessment_id":"4081fb2b-af46-470a-b5c9-4f7f722b2552","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6","revision":"1"},"request_id":"8336f96a-9abd-4dc0-b0e6-e24976a84231","code":null}
```

## Exchange 50 · 7c3e160ac9ca

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 498b9a4a-1b18-4393-8c07-d7d0d623cacb
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1186
content-type: application/json
x-request-id: 909ecf29-14da-4589-b513-6c3fd4510ad9

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["4081fb2b-af46-470a-b5c9-4f7f722b2552"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6","revision":"1"},"display_kind":"fact","record":{"claim_id":"7b36b6f7-fb71-48b1-b4ec-5865fed8c8c6","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 1fe795bc-9b50-45b5-a78f-4d7a327bab32@1 的 /version 字段等于 \"healthy\"。","structured_assertion":{"artifact_ref":{"id":"1fe795bc-9b50-45b5-a78f-4d7a327bab32","sha256":"50eabeac941abbde0d6306985771fee58c27e9d539a59ccb3c42c5d941b29f6c","version":"1"},"expected":"healthy","pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"0febfdad-fdc8-495f-b7ae-033a1dbed263","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:13.188111Z","supersedes":null}}
```

## Exchange 51 · 7c3e160ac9ca

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 746
content-type: application/json
host: testserver
idempotency-key: 25b3d5a5-0aa8-4ba2-a7c5-72729707ae49
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"25b3d5a5-0aa8-4ba2-a7c5-72729707ae49","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"b807ad63-fce8-4927-8cbb-98123fc21bf5","version":"1","sha256":"9f429eae1f2546d8b5ad01e9fe3dc26da2eb7b1c1ac33e4a39435b258557a44d"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 848af0b4-85ca-488d-806d-26f73b154bb0

{"observation_ref":{"entity_type":"observation","id":"443118bf-f1ca-4c73-8cbd-fa0f60894f26","revision":"1"},"capture_id":"25b3d5a5-0aa8-4ba2-a7c5-72729707ae49","status":"accepted","artifact_refs":[{"id":"b807ad63-fce8-4927-8cbb-98123fc21bf5","version":"1","sha256":"9f429eae1f2546d8b5ad01e9fe3dc26da2eb7b1c1ac33e4a39435b258557a44d"}],"request_id":"848af0b4-85ca-488d-806d-26f73b154bb0","code":null}
```

## Exchange 52 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 562
content-type: application/json
host: testserver
idempotency-key: 060f750c-010b-47cd-9114-d2544ae79fe4
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 b807ad63-fce8-4927-8cbb-98123fc21bf5@1 的 /version 字段等于 0。","basis_refs":[{"entity_type":"observation","id":"443118bf-f1ca-4c73-8cbd-fa0f60894f26","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"b807ad63-fce8-4927-8cbb-98123fc21bf5","version":"1","sha256":"9f429eae1f2546d8b5ad01e9fe3dc26da2eb7b1c1ac33e4a39435b258557a44d"},"pointer":"/version","expected":0}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: a0073e15-9ca5-4ed4-b687-810288d0f637

{"status":"accepted_shared","local_ref":"c","request_id":"a0073e15-9ca5-4ed4-b687-810288d0f637","canonical_ref":{"entity_type":"claim","id":"6585f30c-11f3-49e6-98dc-42b2191bcd07","revision":"1"},"code":null}
```

## Exchange 53 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 73285580-1bb2-4580-9310-9edd64b4fd48
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"876f2104-0fa2-4a2a-a92b-7b595b8447d9","claim_ref":{"entity_type":"claim","id":"6585f30c-11f3-49e6-98dc-42b2191bcd07","revision":"1"},"input_refs":[{"entity_type":"observation","id":"443118bf-f1ca-4c73-8cbd-fa0f60894f26","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 9e46ebf4-1253-4636-b7bd-1435322473f0

{"assessment_id":"876f2104-0fa2-4a2a-a92b-7b595b8447d9","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"6585f30c-11f3-49e6-98dc-42b2191bcd07","revision":"1"},"request_id":"9e46ebf4-1253-4636-b7bd-1435322473f0","code":null}
```

## Exchange 54 · 7c3e160ac9ca

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/6585f30c-11f3-49e6-98dc-42b2191bcd07?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 445e2df5-eb20-48e1-bc12-82e977f85e6c
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1173
content-type: application/json
x-request-id: 54cf41a0-4b09-4000-a5c7-5e92ff5a3df3

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","eligible":false,"assessment_ids":["876f2104-0fa2-4a2a-a92b-7b595b8447d9"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"6585f30c-11f3-49e6-98dc-42b2191bcd07","revision":"1"},"display_kind":"claim","record":{"claim_id":"6585f30c-11f3-49e6-98dc-42b2191bcd07","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 b807ad63-fce8-4927-8cbb-98123fc21bf5@1 的 /version 字段等于 0。","structured_assertion":{"artifact_ref":{"id":"b807ad63-fce8-4927-8cbb-98123fc21bf5","sha256":"9f429eae1f2546d8b5ad01e9fe3dc26da2eb7b1c1ac33e4a39435b258557a44d","version":"1"},"expected":0,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"443118bf-f1ca-4c73-8cbd-fa0f60894f26","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:13.326571Z","supersedes":null}}
```

## Exchange 55 · 7c3e160ac9ca

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 746
content-type: application/json
host: testserver
idempotency-key: 9ab213d8-235f-4da7-a229-abd789c66caa
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"9ab213d8-235f-4da7-a229-abd789c66caa","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"88348476-01bd-490c-bfbd-3f68cb1a29bb","version":"1","sha256":"e784b579c8413da35b5571d4721f587eb45a6436aa210975bc90b8ef5b293d12"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 5a607c1c-e6f8-42fc-88a2-6fb0e77a0970

{"observation_ref":{"entity_type":"observation","id":"ff9a3317-e905-4c40-8c2d-f3cab513d589","revision":"1"},"capture_id":"9ab213d8-235f-4da7-a229-abd789c66caa","status":"accepted","artifact_refs":[{"id":"88348476-01bd-490c-bfbd-3f68cb1a29bb","version":"1","sha256":"e784b579c8413da35b5571d4721f587eb45a6436aa210975bc90b8ef5b293d12"}],"request_id":"5a607c1c-e6f8-42fc-88a2-6fb0e77a0970","code":null}
```

## Exchange 56 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 592
content-type: application/json
host: testserver
idempotency-key: cafaccdd-f2ea-47f5-9e3b-c0ea4f4808ce
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 88348476-01bd-490c-bfbd-3f68cb1a29bb@1 的 /version 字段等于 9007199254740993。","basis_refs":[{"entity_type":"observation","id":"ff9a3317-e905-4c40-8c2d-f3cab513d589","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"88348476-01bd-490c-bfbd-3f68cb1a29bb","version":"1","sha256":"e784b579c8413da35b5571d4721f587eb45a6436aa210975bc90b8ef5b293d12"},"pointer":"/version","expected":9007199254740993}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: a98dd640-95ba-45ea-8cc5-5ae6deeef57c

{"status":"accepted_shared","local_ref":"c","request_id":"a98dd640-95ba-45ea-8cc5-5ae6deeef57c","canonical_ref":{"entity_type":"claim","id":"ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0","revision":"1"},"code":null}
```

## Exchange 57 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: d92c70b0-7862-4603-96cf-cc9fdc46d16e
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"b099094b-d826-4549-8f35-cdb165d8b98f","claim_ref":{"entity_type":"claim","id":"ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0","revision":"1"},"input_refs":[{"entity_type":"observation","id":"ff9a3317-e905-4c40-8c2d-f3cab513d589","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: db7cf45d-5aae-4b8d-9a07-08158673e96b

{"assessment_id":"b099094b-d826-4549-8f35-cdb165d8b98f","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0","revision":"1"},"request_id":"db7cf45d-5aae-4b8d-9a07-08158673e96b","code":null}
```

## Exchange 58 · 7c3e160ac9ca

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 2b4a81a7-c55f-428f-8977-fce24735690d
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1198
content-type: application/json
x-request-id: cc9e8319-4309-4740-a1c6-64abca4264be

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["b099094b-d826-4549-8f35-cdb165d8b98f"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0","revision":"1"},"display_kind":"fact","record":{"claim_id":"ae5157a8-5b1e-42f4-a38f-bb4d3b58cdf0","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 88348476-01bd-490c-bfbd-3f68cb1a29bb@1 的 /version 字段等于 9007199254740993。","structured_assertion":{"artifact_ref":{"id":"88348476-01bd-490c-bfbd-3f68cb1a29bb","sha256":"e784b579c8413da35b5571d4721f587eb45a6436aa210975bc90b8ef5b293d12","version":"1"},"expected":9007199254740993,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"ff9a3317-e905-4c40-8c2d-f3cab513d589","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:13.471001Z","supersedes":null}}
```

## Exchange 59 · 7c3e160ac9ca

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 746
content-type: application/json
host: testserver
idempotency-key: dc6dbb60-2b1f-41c5-b1c6-fb43bbfa674f
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"dc6dbb60-2b1f-41c5-b1c6-fb43bbfa674f","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"00144ce3-3dd1-4107-b28f-09a76d229415","version":"1","sha256":"4a9fc0ddd1faccc8b14b8c7bea56720b0f379853983b5d020a5c1c8a0fa6c8fa"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 717b910d-fd74-458b-98e7-82f6685b4355

{"observation_ref":{"entity_type":"observation","id":"1f2f6936-d560-4e7a-b5bc-7a29167c4d5b","revision":"1"},"capture_id":"dc6dbb60-2b1f-41c5-b1c6-fb43bbfa674f","status":"accepted","artifact_refs":[{"id":"00144ce3-3dd1-4107-b28f-09a76d229415","version":"1","sha256":"4a9fc0ddd1faccc8b14b8c7bea56720b0f379853983b5d020a5c1c8a0fa6c8fa"}],"request_id":"717b910d-fd74-458b-98e7-82f6685b4355","code":null}
```

## Exchange 60 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 568
content-type: application/json
host: testserver
idempotency-key: 7d2a11e1-1592-438d-b2b4-11dabf24c6ef
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 00144ce3-3dd1-4107-b28f-09a76d229415@1 的 /version 字段等于 null。","basis_refs":[{"entity_type":"observation","id":"1f2f6936-d560-4e7a-b5bc-7a29167c4d5b","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"00144ce3-3dd1-4107-b28f-09a76d229415","version":"1","sha256":"4a9fc0ddd1faccc8b14b8c7bea56720b0f379853983b5d020a5c1c8a0fa6c8fa"},"pointer":"/version","expected":null}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 953f8a88-5fc8-4497-a05e-c696d1a48cd0

{"status":"accepted_shared","local_ref":"c","request_id":"953f8a88-5fc8-4497-a05e-c696d1a48cd0","canonical_ref":{"entity_type":"claim","id":"04ba09f5-657c-4f9a-9318-13b7c57b130f","revision":"1"},"code":null}
```

## Exchange 61 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 44bfa748-f804-4b6b-bac1-57ccaea03d22
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"944ec953-a91d-4ece-ab23-4af21e56b239","claim_ref":{"entity_type":"claim","id":"04ba09f5-657c-4f9a-9318-13b7c57b130f","revision":"1"},"input_refs":[{"entity_type":"observation","id":"1f2f6936-d560-4e7a-b5bc-7a29167c4d5b","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 2ff1f984-ef9c-427f-9827-b73291cc5767

{"assessment_id":"944ec953-a91d-4ece-ab23-4af21e56b239","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"04ba09f5-657c-4f9a-9318-13b7c57b130f","revision":"1"},"request_id":"2ff1f984-ef9c-427f-9827-b73291cc5767","code":null}
```

## Exchange 62 · 7c3e160ac9ca

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/04ba09f5-657c-4f9a-9318-13b7c57b130f?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 8a20136f-48a2-4625-a862-95a488edceb0
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1174
content-type: application/json
x-request-id: 4a6e6d7c-287d-4b2d-9304-584ed6613892

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["944ec953-a91d-4ece-ab23-4af21e56b239"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"04ba09f5-657c-4f9a-9318-13b7c57b130f","revision":"1"},"display_kind":"fact","record":{"claim_id":"04ba09f5-657c-4f9a-9318-13b7c57b130f","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 00144ce3-3dd1-4107-b28f-09a76d229415@1 的 /version 字段等于 null。","structured_assertion":{"artifact_ref":{"id":"00144ce3-3dd1-4107-b28f-09a76d229415","sha256":"4a9fc0ddd1faccc8b14b8c7bea56720b0f379853983b5d020a5c1c8a0fa6c8fa","version":"1"},"expected":null,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"1f2f6936-d560-4e7a-b5bc-7a29167c4d5b","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:13.605708Z","supersedes":null}}
```

## Exchange 63 · 7c3e160ac9ca

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: d0015309-603c-4440-a607-7f4811e7f2e1
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"d0015309-603c-4440-a607-7f4811e7f2e1","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"5c955889-dcca-4211-94ba-21feb872c550","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: a9cf8f30-90ab-4aed-bca4-4024314990cd

{"observation_ref":{"entity_type":"observation","id":"4f16ad09-1c60-4e24-bd82-0da8052d78df","revision":"1"},"capture_id":"d0015309-603c-4440-a607-7f4811e7f2e1","status":"accepted","artifact_refs":[{"id":"5c955889-dcca-4211-94ba-21feb872c550","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"a9cf8f30-90ab-4aed-bca4-4024314990cd","code":null}
```

## Exchange 64 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 546
content-type: application/json
host: testserver
idempotency-key: 524f9f43-2b86-454c-a881-8538398dcd9a
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"完整捕获内容 5c955889-dcca-4211-94ba-21feb872c550@1 中不存在 /missing。","basis_refs":[{"entity_type":"observation","id":"4f16ad09-1c60-4e24-bd82-0da8052d78df","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-absent-v1","artifact_ref":{"id":"5c955889-dcca-4211-94ba-21feb872c550","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/missing"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 4d9bdac5-a3b4-4c25-94a7-8ff7a6549eff

{"status":"accepted_shared","local_ref":"c","request_id":"4d9bdac5-a3b4-4c25-94a7-8ff7a6549eff","canonical_ref":{"entity_type":"claim","id":"f68627a2-05be-413e-ab47-df3a5126c591","revision":"1"},"code":null}
```

## Exchange 65 · 7c3e160ac9ca

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: b3b91150-b011-43d8-ac0d-fd1b32da235f
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"f9f00299-9e3c-4960-95d9-7557d0189cde","claim_ref":{"entity_type":"claim","id":"f68627a2-05be-413e-ab47-df3a5126c591","revision":"1"},"input_refs":[{"entity_type":"observation","id":"4f16ad09-1c60-4e24-bd82-0da8052d78df","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-absent-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: c823acc3-04ef-4326-bef3-cdc65f66f335

{"assessment_id":"f9f00299-9e3c-4960-95d9-7557d0189cde","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"f68627a2-05be-413e-ab47-df3a5126c591","revision":"1"},"request_id":"c823acc3-04ef-4326-bef3-cdc65f66f335","code":null}
```

## Exchange 66 · 7c3e160ac9ca

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/f68627a2-05be-413e-ab47-df3a5126c591?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: cf10f6b4-91bf-4def-9eae-a54fd8b32439
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1152
content-type: application/json
x-request-id: 7b61d99d-4d43-4c67-bbee-837ff33dc263

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["f9f00299-9e3c-4960-95d9-7557d0189cde"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"f68627a2-05be-413e-ab47-df3a5126c591","revision":"1"},"display_kind":"fact","record":{"claim_id":"f68627a2-05be-413e-ab47-df3a5126c591","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"完整捕获内容 5c955889-dcca-4211-94ba-21feb872c550@1 中不存在 /missing。","structured_assertion":{"artifact_ref":{"id":"5c955889-dcca-4211-94ba-21feb872c550","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"pointer":"/missing","predicate":"json-pointer-absent-v1"},"basis_refs":[{"entity_type":"observation","id":"4f16ad09-1c60-4e24-bd82-0da8052d78df","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:13.737168Z","supersedes":null}}
```

## Exchange 67 · 887e177d85b5

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 24a1708d-4806-493e-9786-a0295bd11c80
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"24a1708d-4806-493e-9786-a0295bd11c80","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"c439ad64-7666-4a39-8d1e-aae36942f918","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 19f6d950-910f-4567-9642-7cb793285a5a

{"observation_ref":{"entity_type":"observation","id":"6a2e5187-0aff-4b44-a412-62a924657303","revision":"1"},"capture_id":"24a1708d-4806-493e-9786-a0295bd11c80","status":"accepted","artifact_refs":[{"id":"c439ad64-7666-4a39-8d1e-aae36942f918","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"19f6d950-910f-4567-9642-7cb793285a5a","code":null}
```

## Exchange 68 · 887e177d85b5

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 8f60baf0-a8df-4be5-a3fd-69f3c4cc9608
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 c439ad64-7666-4a39-8d1e-aae36942f918@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"6a2e5187-0aff-4b44-a412-62a924657303","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"c439ad64-7666-4a39-8d1e-aae36942f918","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 6758025b-95d0-4e8a-b5d0-925244b9cc54

{"status":"accepted_shared","local_ref":"c","request_id":"6758025b-95d0-4e8a-b5d0-925244b9cc54","canonical_ref":{"entity_type":"claim","id":"4276ca81-a808-41a4-a0a5-9dc2fbf76031","revision":"1"},"code":null}
```

## Exchange 69 · 887e177d85b5

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 4a503c3f-3baa-4516-bf9f-9db51d7827d5
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"2e76ac39-52f1-4d59-b5c0-5365755b439e","claim_ref":{"entity_type":"claim","id":"4276ca81-a808-41a4-a0a5-9dc2fbf76031","revision":"1"},"input_refs":[{"entity_type":"observation","id":"6a2e5187-0aff-4b44-a412-62a924657303","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: fe6f447d-158f-4546-a8df-5f14228e6e14

{"assessment_id":"2e76ac39-52f1-4d59-b5c0-5365755b439e","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"4276ca81-a808-41a4-a0a5-9dc2fbf76031","revision":"1"},"request_id":"fe6f447d-158f-4546-a8df-5f14228e6e14","code":null}
```

## Exchange 70 · 95629cd4214c

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1245
content-type: application/json
host: testserver
idempotency-key: 8fcd8390-b869-46d4-9358-17f4401becea
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"8fcd8390-b869-46d4-9358-17f4401becea","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"4ce88eb4-7ff0-4ca6-b1d9-8768d1f0c83e","read_set":[],"raw_output_ref":{"id":"01999144-0bae-4b5a-8229-712269ca58e8","version":"1","sha256":"c8322508ee87405214b90a493c07c4f486f4cf14a4b3f10990d0e8e525430ed2"},"raw_output_digest":"c8322508ee87405214b90a493c07c4f486f4cf14a4b3f10990d0e8e525430ed2","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"one","basis_refs":[{"client_ref":"b"}],"limitations":["isolated fixture"]},{"client_ref":"b","kind":"hypothesis","assertion_role":"candidate_fact","text":"two","basis_refs":[{"client_ref":"a"}],"limitations":["isolated fixture"]},{"client_ref":"ok","kind":"hypothesis","assertion_role":"candidate_fact","text":"unrelated","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 640
content-type: application/json
x-request-id: bdef71ab-7b92-409f-8f86-26de5c7690e3

{"submission_id":"8fcd8390-b869-46d4-9358-17f4401becea","status":"accepted","components":[{"status":"rejected","local_ref":"a","request_id":"bdef71ab-7b92-409f-8f86-26de5c7690e3","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"rejected","local_ref":"b","request_id":"bdef71ab-7b92-409f-8f86-26de5c7690e3","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"accepted_shared","local_ref":"ok","request_id":"bdef71ab-7b92-409f-8f86-26de5c7690e3","canonical_ref":{"entity_type":"claim","id":"44973b1e-fff4-4116-9389-3a325bfa1619","revision":"1"},"code":null}],"request_id":"bdef71ab-7b92-409f-8f86-26de5c7690e3","code":null}
```

## Exchange 71 · 95bf41eaef8c

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 086e2d05-b584-4e92-b6bd-71c21a7ac8b4
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"086e2d05-b584-4e92-b6bd-71c21a7ac8b4","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"a1108d94-11ac-4338-81b1-8354c95cbbf6","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 709fb19e-0212-46aa-85ad-3fa4aa3657a5

{"observation_ref":{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"},"capture_id":"086e2d05-b584-4e92-b6bd-71c21a7ac8b4","status":"accepted","artifact_refs":[{"id":"a1108d94-11ac-4338-81b1-8354c95cbbf6","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"709fb19e-0212-46aa-85ad-3fa4aa3657a5","code":null}
```

## Exchange 72 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: c8016479-889e-4fd3-8151-95552f080a3b
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 6f88a0f4-9553-43e4-a35d-59d17c56b6ab

{"status":"accepted_shared","local_ref":"c","request_id":"6f88a0f4-9553-43e4-a35d-59d17c56b6ab","canonical_ref":{"entity_type":"claim","id":"b20164eb-b0fc-43b2-ab33-dd7502d0c290","revision":"1"},"code":null}
```

## Exchange 73 · 95bf41eaef8c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/b20164eb-b0fc-43b2-ab33-dd7502d0c290?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: d299194d-9f4a-4142-898f-1d02b16cbd21
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 734
content-type: application/json
x-request-id: 1d41a150-7d07-416e-be9b-3c3f0d429004

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"unchecked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"b20164eb-b0fc-43b2-ab33-dd7502d0c290","revision":"1"},"display_kind":"claim","record":{"claim_id":"b20164eb-b0fc-43b2-ab33-dd7502d0c290","revision":"1","task_id":"task-fixture","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","structured_assertion":null,"basis_refs":[],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.008214Z","supersedes":null}}
```

## Exchange 74 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 254
content-type: application/json
host: testserver
idempotency-key: 48bb2541-7ed3-4af6-8139-22c3f31058d0
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"tool says system healthy","basis_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 05a4cca7-d316-4255-865c-16d205673f88

{"status":"accepted_shared","local_ref":"c","request_id":"05a4cca7-d316-4255-865c-16d205673f88","canonical_ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"code":null}
```

## Exchange 75 · 95bf41eaef8c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/7f217d28-e324-43f7-8ed3-b022922bc19a?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 074362c0-d2a4-49e3-b177-71491798727a
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 826
content-type: application/json
x-request-id: f240e94e-c7f8-4d30-a61f-1a17f8ea4001

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"display_kind":"claim","record":{"claim_id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"tool says system healthy","structured_assertion":null,"basis_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.038702Z","supersedes":null}}
```

## Exchange 76 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 188
content-type: application/json
host: testserver
idempotency-key: 24c49328-8ebe-4f2b-9fe8-d22cabc41982
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","basis_refs":[],"limitations":["isolated fixture"],"evidence_state":"supported"}
```

```http
HTTP/1.1 422
content-length: 293
content-type: application/json
x-request-id: ead21fef-9066-4bd2-a129-38a7e52b9e45

{"code":"INVALID_SCHEMA","message":"Request does not satisfy the v2 contract.","request_id":"ead21fef-9066-4bd2-a129-38a7e52b9e45","retryable":false,"details":{"errors":[{"type":"extra_forbidden","loc":["body","<field>"],"msg":"Input does not satisfy the field contract."}],"truncated":false}}
```

## Exchange 77 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: c1a569fa-02e3-4f4f-896f-3feeff627ef9
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"0e5b7ee9-8427-4381-a83b-a88ef06c0b79","claim_ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"input_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 403
content-length: 160
content-type: application/json
x-request-id: f0b07102-63a6-47cd-9055-201b6abbb263

{"code":"FORBIDDEN_ASSESSOR","message":"The request could not be completed.","request_id":"f0b07102-63a6-47cd-9055-201b6abbb263","retryable":false,"details":{}}
```

## Exchange 78 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 654
content-type: application/json
host: testserver
idempotency-key: 534f06b0-3492-4603-93a0-52f738fa45c1
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"60198c6e-c4bd-43be-a634-a584cbb9a56e","claim_ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"input_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"model_review","method_version":"model-review-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 422
content-length: 279
content-type: application/json
x-request-id: f249d49c-972d-4dd3-8280-c28c53d720ce

{"code":"INVALID_SCHEMA","message":"Request does not satisfy the v2 contract.","request_id":"f249d49c-972d-4dd3-8280-c28c53d720ce","retryable":false,"details":{"errors":[{"type":"value_error","loc":["body"],"msg":"Input does not satisfy the field contract."}],"truncated":false}}
```

## Exchange 79 · 95bf41eaef8c

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 657
content-type: application/json
host: testserver
idempotency-key: f7a82416-4bd8-49b5-b39d-7339eecef608
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"61124d59-8210-463a-8bb8-49ef2c5736f2","claim_ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"input_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"grounding_state":"content_checked","evidence_state":"inconclusive","applicability_state":"current","method_kind":"model_review","method_version":"model-review-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 0300548b-6397-43e5-b032-d61c552ab05d

{"assessment_id":"61124d59-8210-463a-8bb8-49ef2c5736f2","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"request_id":"0300548b-6397-43e5-b032-d61c552ab05d","code":null}
```

## Exchange 80 · 95bf41eaef8c

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/7f217d28-e324-43f7-8ed3-b022922bc19a?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 113a59ca-8006-4b04-99c0-39a0dfabfbd0
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 882
content-type: application/json
x-request-id: 43f633f4-c02e-446b-9a25-e8cbb05ebf0f

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":["61124d59-8210-463a-8bb8-49ef2c5736f2"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1"},"display_kind":"claim","record":{"claim_id":"7f217d28-e324-43f7-8ed3-b022922bc19a","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"tool says system healthy","structured_assertion":null,"basis_refs":[{"entity_type":"observation","id":"b24018cb-310f-4add-8aed-a152a79618dd","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:05.038702Z","supersedes":null}}
```

## Exchange 81 · a3de3e6df007

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 220ebe2e-1c61-4cf3-8804-8402ddf0c4ea
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"220ebe2e-1c61-4cf3-8804-8402ddf0c4ea","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"44b34beb-43a5-4ccf-91b2-46e7ffe9a62b","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: ebad75b6-79fb-4e5e-b1e6-b9e23a53c3e7

{"observation_ref":{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"},"capture_id":"220ebe2e-1c61-4cf3-8804-8402ddf0c4ea","status":"accepted","artifact_refs":[{"id":"44b34beb-43a5-4ccf-91b2-46e7ffe9a62b","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"ebad75b6-79fb-4e5e-b1e6-b9e23a53c3e7","code":null}
```

## Exchange 82 · a3de3e6df007

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 564
content-type: application/json
host: testserver
idempotency-key: 9035825f-01ba-4271-b35f-b86caca8609d
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 44b34beb-43a5-4ccf-91b2-46e7ffe9a62b@1 的 /version 字段等于 17。","basis_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-equals-v1","artifact_ref":{"id":"44b34beb-43a5-4ccf-91b2-46e7ffe9a62b","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/version","expected":17}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: eb3da71f-acef-4a61-93c5-e63a0ba25a22

{"status":"accepted_shared","local_ref":"c","request_id":"eb3da71f-acef-4a61-93c5-e63a0ba25a22","canonical_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"code":null}
```

## Exchange 83 · a3de3e6df007

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 4891595c-ff4f-4b99-ada6-577f235146e9
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"a2dba74a-06a2-41db-950b-133708b6e3cd","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"input_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: d47f6f7f-fa0c-443d-9fbe-488191e5f625

{"assessment_id":"a2dba74a-06a2-41db-950b-133708b6e3cd","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"request_id":"d47f6f7f-fa0c-443d-9fbe-488191e5f625","code":null}
```

## Exchange 84 · a3de3e6df007

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 667
content-type: application/json
host: testserver
idempotency-key: dde11555-6f97-4608-b628-c50c327d1cca
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"9e942e02-f1ce-4b10-a0c0-bceb7265b4b3","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"input_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"grounding_state":"content_checked","evidence_state":"contradicted","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 8f408ae8-82d0-4aa4-a55a-1169f8c6b9f3

{"assessment_id":"9e942e02-f1ce-4b10-a0c0-bceb7265b4b3","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"request_id":"8f408ae8-82d0-4aa4-a55a-1169f8c6b9f3","code":null}
```

## Exchange 85 · a3de3e6df007

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 722
content-type: application/json
host: testserver
idempotency-key: 60ce23bc-bccb-41c6-8269-d8aa02c6fd83
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"c875d521-695b-4445-9880-e9b5d3680f6e","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"input_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-equals-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":["9e942e02-f1ce-4b10-a0c0-bceb7265b4b3"],"supersedes_reason":"Correct prior assessment"}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 537fbc30-9fec-419c-8e01-ae65e515bdf1

{"assessment_id":"c875d521-695b-4445-9880-e9b5d3680f6e","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"request_id":"537fbc30-9fec-419c-8e01-ae65e515bdf1","code":null}
```

## Exchange 86 · a3de3e6df007

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/ac25d8d2-0594-40b8-85ee-a6ae3722c4c5?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 2c8c384c-87b4-4db9-93c8-b09c975cf844
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1209
content-type: application/json
x-request-id: d819cf88-2518-4166-8be7-5a8f33819c41

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["a2dba74a-06a2-41db-950b-133708b6e3cd","c875d521-695b-4445-9880-e9b5d3680f6e"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"display_kind":"fact","record":{"claim_id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 44b34beb-43a5-4ccf-91b2-46e7ffe9a62b@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"44b34beb-43a5-4ccf-91b2-46e7ffe9a62b","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:08.554951Z","supersedes":null}}
```

## Exchange 87 · a3de3e6df007

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/ac25d8d2-0594-40b8-85ee-a6ae3722c4c5?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: fdff274f-05e5-4033-913a-2cf1280dd0be
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1106
content-type: application/json
x-request-id: 5039807a-db33-41be-b5f3-efbbabb2472c

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"stale","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1"},"display_kind":"claim","record":{"claim_id":"ac25d8d2-0594-40b8-85ee-a6ae3722c4c5","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"已捕获内容 44b34beb-43a5-4ccf-91b2-46e7ffe9a62b@1 的 /version 字段等于 17。","structured_assertion":{"artifact_ref":{"id":"44b34beb-43a5-4ccf-91b2-46e7ffe9a62b","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"expected":17,"pointer":"/version","predicate":"json-pointer-equals-v1"},"basis_refs":[{"entity_type":"observation","id":"840ed11f-2e99-4005-93f3-7599e1800b23","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:08.554951Z","supersedes":null}}
```

## Exchange 88 · a6430e169dc0

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 746
content-type: application/json
host: testserver
idempotency-key: 79dfb7f9-a0f3-4faa-ba1e-f66603860183
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"79dfb7f9-a0f3-4faa-ba1e-f66603860183","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"b18f740b-31bc-40b2-ae9d-99a400395c03","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"partial"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 4a25dfcb-2c1b-4e05-9224-b415600ba3ee

{"observation_ref":{"entity_type":"observation","id":"a24bfa1f-aa11-4c3e-9afa-6c06bf40a456","revision":"1"},"capture_id":"79dfb7f9-a0f3-4faa-ba1e-f66603860183","status":"accepted","artifact_refs":[{"id":"b18f740b-31bc-40b2-ae9d-99a400395c03","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"4a25dfcb-2c1b-4e05-9224-b415600ba3ee","code":null}
```

## Exchange 89 · a6430e169dc0

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 546
content-type: application/json
host: testserver
idempotency-key: 3a94a943-3e02-4e62-a62b-d268f51cc6d1
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"完整捕获内容 b18f740b-31bc-40b2-ae9d-99a400395c03@1 中不存在 /missing。","basis_refs":[{"entity_type":"observation","id":"a24bfa1f-aa11-4c3e-9afa-6c06bf40a456","revision":"1"}],"limitations":["isolated fixture"],"structured_assertion":{"predicate":"json-pointer-absent-v1","artifact_ref":{"id":"b18f740b-31bc-40b2-ae9d-99a400395c03","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"},"pointer":"/missing"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 8ba0d25a-8253-40df-b0ea-3fb1e7bd3ebe

{"status":"accepted_shared","local_ref":"c","request_id":"8ba0d25a-8253-40df-b0ea-3fb1e7bd3ebe","canonical_ref":{"entity_type":"claim","id":"7719a54b-265d-4393-9c68-f526bd9e88d4","revision":"1"},"code":null}
```

## Exchange 90 · a6430e169dc0

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 662
content-type: application/json
host: testserver
idempotency-key: 6d6a59f5-af76-454d-85b6-500a09b1f039
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"8828af27-698c-482d-89f6-2de36ac19470","claim_ref":{"entity_type":"claim","id":"7719a54b-265d-4393-9c68-f526bd9e88d4","revision":"1"},"input_refs":[{"entity_type":"observation","id":"a24bfa1f-aa11-4c3e-9afa-6c06bf40a456","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"deterministic","method_version":"json-pointer-absent-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 83db38aa-4b5d-4b5a-ac92-8d9be92c6045

{"assessment_id":"8828af27-698c-482d-89f6-2de36ac19470","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"7719a54b-265d-4393-9c68-f526bd9e88d4","revision":"1"},"request_id":"83db38aa-4b5d-4b5a-ac92-8d9be92c6045","code":null}
```

## Exchange 91 · a6430e169dc0

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/7719a54b-265d-4393-9c68-f526bd9e88d4?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: b153b4ae-1e99-4f31-bb99-b93cb82710ca
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 1148
content-type: application/json
x-request-id: 11a7cc28-4d21-4092-927a-78768d63501c

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"inconclusive","applicability_state":"current","eligible":false,"assessment_ids":["8828af27-698c-482d-89f6-2de36ac19470"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"7719a54b-265d-4393-9c68-f526bd9e88d4","revision":"1"},"display_kind":"claim","record":{"claim_id":"7719a54b-265d-4393-9c68-f526bd9e88d4","revision":"1","task_id":"task-fixture","kind":"observation-summary","assertion_role":"candidate_fact","text":"完整捕获内容 b18f740b-31bc-40b2-ae9d-99a400395c03@1 中不存在 /missing。","structured_assertion":{"artifact_ref":{"id":"b18f740b-31bc-40b2-ae9d-99a400395c03","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665","version":"1"},"pointer":"/missing","predicate":"json-pointer-absent-v1"},"basis_refs":[{"entity_type":"observation","id":"a24bfa1f-aa11-4c3e-9afa-6c06bf40a456","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:20:04.434429Z","supersedes":null}}
```

## Exchange 92 · aa613bc25678

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1360
content-type: application/json
host: testserver
idempotency-key: 762f92da-2383-4a0a-a41b-be9de5382cc9
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"762f92da-2383-4a0a-a41b-be9de5382cc9","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"812425e6-1b05-4562-82ca-6bf90f2bad94","read_set":[],"raw_output_ref":{"id":"d2dd42fa-8167-4849-901d-b3b78dabe00a","version":"1","sha256":"07b6032005cdf84475195ba849a90f19bfc3f64328f08cd1377a389d838f6681"},"raw_output_digest":"07b6032005cdf84475195ba849a90f19bfc3f64328f08cd1377a389d838f6681","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"A","basis_refs":[{"client_ref":"b"}],"limitations":["isolated fixture"]},{"client_ref":"b","kind":"hypothesis","assertion_role":"candidate_fact","text":"B","basis_refs":[{"client_ref":"missing"}],"limitations":["isolated fixture"]},{"client_ref":"ok","kind":"hypothesis","assertion_role":"candidate_fact","text":"independent","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[{"client_ref":"i","question":"Check hypothesis","basis_refs":[{"client_ref":"a"}],"expected_output":"Evidence"}],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 778
content-type: application/json
x-request-id: 42ca6af7-9f57-4dca-a784-6442c8ebaf95

{"submission_id":"762f92da-2383-4a0a-a41b-be9de5382cc9","status":"accepted","components":[{"status":"rejected","local_ref":"a","request_id":"42ca6af7-9f57-4dca-a784-6442c8ebaf95","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"rejected","local_ref":"b","request_id":"42ca6af7-9f57-4dca-a784-6442c8ebaf95","canonical_ref":null,"code":"INVALID_REFERENCE"},{"status":"accepted_shared","local_ref":"ok","request_id":"42ca6af7-9f57-4dca-a784-6442c8ebaf95","canonical_ref":{"entity_type":"claim","id":"255d3f81-35b2-4492-8fb6-89888befd26c","revision":"1"},"code":null},{"status":"rejected","local_ref":"i","request_id":"42ca6af7-9f57-4dca-a784-6442c8ebaf95","canonical_ref":null,"code":"INVALID_REFERENCE"}],"request_id":"42ca6af7-9f57-4dca-a784-6442c8ebaf95","code":null}
```

## Exchange 93 · aa613bc25678

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1190
content-type: application/json
host: testserver
idempotency-key: bf278fcf-80d0-4c16-ba29-08b28e9c888c
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"bf278fcf-80d0-4c16-ba29-08b28e9c888c","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"ad7d0644-c814-41dd-afa7-b37550bf9afe","read_set":[],"raw_output_ref":{"id":"e8881db2-937d-4e52-916b-b20021bb91eb","version":"1","sha256":"61e019a3c699c8fb4bacd60f99c105ca289641527c00f1e03c699102d1840167"},"raw_output_digest":"61e019a3c699c8fb4bacd60f99c105ca289641527c00f1e03c699102d1840167","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"a","kind":"hypothesis","assertion_role":"candidate_fact","text":"A","basis_refs":[{"client_ref":"b"}],"limitations":["isolated fixture"]},{"client_ref":"b","kind":"hypothesis","assertion_role":"candidate_fact","text":"B","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[{"client_ref":"i","question":"Check hypothesis","basis_refs":[{"client_ref":"a"}],"expected_output":"Evidence"}],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 780
content-type: application/json
x-request-id: b104cd84-289f-42eb-95dc-2d46cacaec53

{"submission_id":"bf278fcf-80d0-4c16-ba29-08b28e9c888c","status":"accepted","components":[{"status":"accepted_shared","local_ref":"a","request_id":"b104cd84-289f-42eb-95dc-2d46cacaec53","canonical_ref":{"entity_type":"claim","id":"748aab9a-0991-4589-b7f7-c921ab2309fd","revision":"1"},"code":null},{"status":"accepted_shared","local_ref":"b","request_id":"b104cd84-289f-42eb-95dc-2d46cacaec53","canonical_ref":{"entity_type":"claim","id":"252eb737-a0cc-4520-88d8-1e5c18365640","revision":"1"},"code":null},{"status":"accepted_shared","local_ref":"i","request_id":"b104cd84-289f-42eb-95dc-2d46cacaec53","canonical_ref":{"entity_type":"intent","id":"40cd4bf3-a937-4010-a1d6-d74971916591","revision":"1"},"code":null}],"request_id":"b104cd84-289f-42eb-95dc-2d46cacaec53","code":null}
```

## Exchange 94 · af4aa7f38219

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 930
content-type: application/json
host: testserver
idempotency-key: 94a5c3c7-ab82-4ce3-88df-570492dd3e60
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"94a5c3c7-ab82-4ce3-88df-570492dd3e60","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"d3d98bc1-35ff-4781-a828-3a9452b29fd7","read_set":[],"raw_output_ref":{"id":"21a05763-a05b-47bf-a64d-6985d9873a59","version":"1","sha256":"aa6c91a8dd82990e8d06210babdf968157f7b4fdd26375176facb97731109810"},"raw_output_digest":"aa6c91a8dd82990e8d06210babdf968157f7b4fdd26375176facb97731109810","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"first","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 363
content-type: application/json
x-request-id: 9f5eb0cc-2132-4621-9622-731e81885001

{"submission_id":"94a5c3c7-ab82-4ce3-88df-570492dd3e60","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"9f5eb0cc-2132-4621-9622-731e81885001","canonical_ref":{"entity_type":"claim","id":"a37d904e-47d8-43e1-8568-5d9d571474b1","revision":"1"},"code":null}],"request_id":"9f5eb0cc-2132-4621-9622-731e81885001","code":null}
```

## Exchange 95 · af4aa7f38219

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 931
content-type: application/json
host: testserver
idempotency-key: e324141c-5421-497d-a6c4-2296dee18e53
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"e324141c-5421-497d-a6c4-2296dee18e53","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"d3d98bc1-35ff-4781-a828-3a9452b29fd7","read_set":[],"raw_output_ref":{"id":"ab83ee93-f356-4745-a7ae-97869651c1d4","version":"1","sha256":"9a80ca6e53ac20742096efd7d0885e1e37ca846b6045b4474c494b25aef73b55"},"raw_output_digest":"9a80ca6e53ac20742096efd7d0885e1e37ca846b6045b4474c494b25aef73b55","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"second","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 363
content-type: application/json
x-request-id: 9bf698ec-7833-4081-a0d6-3912509a4d77

{"submission_id":"e324141c-5421-497d-a6c4-2296dee18e53","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"9bf698ec-7833-4081-a0d6-3912509a4d77","canonical_ref":{"entity_type":"claim","id":"09df6a92-c6a3-4c9d-939e-70d33b1f72c2","revision":"1"},"code":null}],"request_id":"9bf698ec-7833-4081-a0d6-3912509a4d77","code":null}
```

## Exchange 96 · af4aa7f38219

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 930
content-type: application/json
host: testserver
idempotency-key: 94a5c3c7-ab82-4ce3-88df-570492dd3e60
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"94a5c3c7-ab82-4ce3-88df-570492dd3e60","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"d3d98bc1-35ff-4781-a828-3a9452b29fd7","read_set":[],"raw_output_ref":{"id":"21a05763-a05b-47bf-a64d-6985d9873a59","version":"1","sha256":"aa6c91a8dd82990e8d06210babdf968157f7b4fdd26375176facb97731109810"},"raw_output_digest":"aa6c91a8dd82990e8d06210babdf968157f7b4fdd26375176facb97731109810","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"first","basis_refs":[],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: 83330455-01e1-4798-876b-dd8cfdfd6375

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"83330455-01e1-4798-876b-dd8cfdfd6375","retryable":false,"details":{}}
```

## Exchange 97 · befa63abe267

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
content-length: 143
content-type: application/json
host: testserver
idempotency-key: 9cc2e429-f20c-4094-b810-a883caf71f73
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"human text","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 1af3cc40-73f4-41de-ab2e-4f3f2f39503f

{"status":"accepted_shared","local_ref":"c","request_id":"1af3cc40-73f4-41de-ab2e-4f3f2f39503f","canonical_ref":{"entity_type":"claim","id":"7bd29652-d429-444f-92aa-f6f336e34b97","revision":"1"},"code":null}
```

## Exchange 98 · befa63abe267

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 233
content-type: application/json
host: testserver
idempotency-key: edd6a20e-f66f-4ce4-b040-6f6d548b31a5
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"rewrite","basis_refs":[],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"7bd29652-d429-444f-92aa-f6f336e34b97","revision":"1"}}
```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: dc153b05-7954-4787-98db-d907534344cc

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"dc153b05-7954-4787-98db-d907534344cc","retryable":false,"details":{}}
```

## Exchange 99 · befa63abe267

```http
POST http://testserver/api/v2/tasks/task-sibling/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 140
content-type: application/json
host: testserver
idempotency-key: ee37b1c0-cdf7-4d43-86f4-016ce8b2a29f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"sibling","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: c8045099-bac0-409b-bb70-ab084896531b

{"status":"accepted_shared","local_ref":"c","request_id":"c8045099-bac0-409b-bb70-ab084896531b","canonical_ref":{"entity_type":"claim","id":"e32c2c5f-242f-470b-95cd-f3397964085f","revision":"1"},"code":null}
```

## Exchange 100 · befa63abe267

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 241
content-type: application/json
host: testserver
idempotency-key: 91fd1910-e899-4887-ac54-1d225b38be34
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"A freely shared hypothesis","basis_refs":[{"entity_type":"claim","id":"e32c2c5f-242f-470b-95cd-f3397964085f","revision":"1"}],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 137
content-type: application/json
x-request-id: a446f2a4-7e1c-4b24-b726-e310c16a56bc

{"status":"rejected","local_ref":"c","request_id":"a446f2a4-7e1c-4b24-b726-e310c16a56bc","canonical_ref":null,"code":"INVALID_REFERENCE"}
```

## Exchange 101 · eebaf480182f

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: f6449ef1-c859-4866-bc0e-3097e1306096
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"f6449ef1-c859-4866-bc0e-3097e1306096","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"c7ea04df-4c72-4760-bd9c-79d5180a3b30","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: fee9877e-27c3-4d9c-a627-0c8cdd04b3ec

{"observation_ref":{"entity_type":"observation","id":"dc271559-c740-47a8-a0b7-def4af8ae836","revision":"1"},"capture_id":"f6449ef1-c859-4866-bc0e-3097e1306096","status":"accepted","artifact_refs":[{"id":"c7ea04df-4c72-4760-bd9c-79d5180a3b30","version":"1","sha256":"7f8657fdb0bc4e2190fb39a2641aafc3e3a5b713b0d3bfd04af35094fdd67665"}],"request_id":"fee9877e-27c3-4d9c-a627-0c8cdd04b3ec","code":null}
```

## Exchange 102 · eebaf480182f

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 156
content-type: application/json
host: testserver
idempotency-key: d8be5312-efb3-447e-8ace-d6492d8865a6
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Reviewed prose","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 044ac142-2e55-4c71-b1bd-2c6b45c0f1c9

{"status":"accepted_shared","local_ref":"c","request_id":"044ac142-2e55-4c71-b1bd-2c6b45c0f1c9","canonical_ref":{"entity_type":"claim","id":"2fd0b35b-8aab-4f4e-9588-d93a0e66beb4","revision":"1"},"code":null}
```

## Exchange 103 · eebaf480182f

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 664
content-type: application/json
host: testserver
idempotency-key: d051057e-b146-477c-b311-b28609b05d82
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"108e5d3b-126f-4036-a61b-7b1f0bc80851","claim_ref":{"entity_type":"claim","id":"2fd0b35b-8aab-4f4e-9588-d93a0e66beb4","revision":"1"},"input_refs":[{"entity_type":"observation","id":"dc271559-c740-47a8-a0b7-def4af8ae836","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 471ba62e-72bf-48a8-85fb-96738fa88144

{"assessment_id":"108e5d3b-126f-4036-a61b-7b1f0bc80851","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"2fd0b35b-8aab-4f4e-9588-d93a0e66beb4","revision":"1"},"request_id":"471ba62e-72bf-48a8-85fb-96738fa88144","code":null}
```

## Exchange 104 · eebaf480182f

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/2fd0b35b-8aab-4f4e-9588-d93a0e66beb4?revision=1&snapshot_id=872df7e4-1112-45ea-aba0-1fb7e402c074 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 78200b53-9aa6-4736-aa60-0cc2cc62613a
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: 369277eb-3457-4564-8259-dc071990c5de

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"369277eb-3457-4564-8259-dc071990c5de","retryable":false,"details":{}}
```
