# P04 review counterexample — complete ASGI HTTP exchanges

Production routes and isolated PostgreSQL; not an external target. Only fixture Authorization credentials are redacted. Re-run counterexample.py with the existing isolated test database manifest; it creates and cleans up only its own temporary database/roles. Full SQL and sealed input bytes accompany this file.

Failure point: after private premise revision 2, the final low-clearance GET still returns supported/current/eligible=true while the preceding high-clearance GET returns unassessed/stale/eligible=false.

## Exchange 1

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: 83ee6159-78bf-4374-865c-aff80cbe8653
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Public premise v1","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: d17840e2-0398-4f34-aa5f-851fc7f40f9d

{"status":"accepted_shared","local_ref":"c","request_id":"d17840e2-0398-4f34-aa5f-851fc7f40f9d","canonical_ref":{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"},"code":null}
```

## Exchange 2

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 258
content-type: application/json
host: testserver
idempotency-key: 794db15b-2811-4027-bde5-1825775690e3
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by the premise","basis_refs":[{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: d81a0253-7f61-430a-97bf-b28c77bf322e

{"status":"accepted_shared","local_ref":"c","request_id":"d81a0253-7f61-430a-97bf-b28c77bf322e","canonical_ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"code":null}
```

## Exchange 3

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 658
content-type: application/json
host: testserver
idempotency-key: fc624ff9-f419-4069-b8eb-04d11ea9b85b
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"1e261aad-2186-4ada-9c1c-b70b6c2be01d","claim_ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"input_refs":[{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 4d303918-6e1b-423f-a8ed-5be5692ddbce

{"assessment_id":"1e261aad-2186-4ada-9c1c-b70b6c2be01d","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"request_id":"4d303918-6e1b-423f-a8ed-5be5692ddbce","code":null}
```

## Exchange 4

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/306660bb-a371-454b-a890-bc29e4689684?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: cfec93d4-b09e-4bfb-a1fa-5270e02be307
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 892
content-type: application/json
x-request-id: 5bd00573-082d-4bb2-a513-649527904356

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["1e261aad-2186-4ada-9c1c-b70b6c2be01d"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"display_kind":"fact","record":{"claim_id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by the premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:43:57.467194Z","supersedes":null}}
```

## Exchange 5

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: a20cc9fc-6195-4adc-8a41-1d725fc77897
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"a20cc9fc-6195-4adc-8a41-1d725fc77897","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"1b577173-3e2b-479b-bc35-f7c8aa1f5d40","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 8c85e9ec-c2fb-4f0f-9547-e4211e2634a0

{"observation_ref":{"entity_type":"observation","id":"8aa52ad9-470e-460c-8af6-58b43e9cf572","revision":"1"},"capture_id":"a20cc9fc-6195-4adc-8a41-1d725fc77897","status":"accepted","artifact_refs":[{"id":"1b577173-3e2b-479b-bc35-f7c8aa1f5d40","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"request_id":"8c85e9ec-c2fb-4f0f-9547-e4211e2634a0","code":null}
```

## Exchange 6

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 349
content-type: application/json
host: testserver
idempotency-key: d071164b-b3cb-452b-97bd-50c4314b5041
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Revised private premise v2","basis_refs":[{"entity_type":"observation","id":"8aa52ad9-470e-460c-8af6-58b43e9cf572","revision":"1"}],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 617068b4-99cc-44f3-aa3e-f6f4733a6a1d

{"status":"accepted_shared","local_ref":"c","request_id":"617068b4-99cc-44f3-aa3e-f6f4733a6a1d","canonical_ref":{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"2"},"code":null}
```

## Exchange 7

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/306660bb-a371-454b-a890-bc29e4689684?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 6926e6c8-cce6-4d60-89ed-b4466b10536a
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 828
content-type: application/json
x-request-id: ec7f039e-424e-44c6-98f7-43b577c054c1

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"stale","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"display_kind":"claim","record":{"claim_id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by the premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:43:57.467194Z","supersedes":null}}
```

## Exchange 8

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/306660bb-a371-454b-a890-bc29e4689684?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: f2fdca58-eb18-484b-8066-65c7f4d692ff
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 892
content-type: application/json
x-request-id: 812e956f-17db-4b33-8e62-18a8858da985

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["1e261aad-2186-4ada-9c1c-b70b6c2be01d"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1"},"display_kind":"fact","record":{"claim_id":"306660bb-a371-454b-a890-bc29e4689684","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by the premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"91314a38-cc48-4423-a8d0-5addd8f17ee1","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:43:57.467194Z","supersedes":null}}
```
