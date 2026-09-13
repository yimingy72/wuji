# P04 review fix round 1 — complete HTTP reproduction

F1: public premise v1 is superseded by a private v2. RED reproduces false-current Fact and missing STALE_INPUT; FINAL checks current Fact and ResultCommitter against full authoritative revision state. These are real production ASGI endpoints with isolated PostgreSQL and sealed bytes.

Authorization headers replace only ephemeral fixture bearer tokens with `${TOKEN_subject}`. Run the exact pytest command in first-final-targeted.json to regenerate the isolated database, signed fixture issuer and all prerequisite grants. Private signing keys are never saved. Full other headers and bodies are retained; lossless SQL gzip and original input bytes are under runtime/.

## Exchange 1 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 147
content-type: application/json
host: testserver
idempotency-key: 9a9f8ee4-4a49-4a0d-b273-7cc15eeb6f4f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Public premise","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 9903f9ea-023b-444b-a892-5cbf4eb39a52

{"status":"accepted_shared","local_ref":"c","request_id":"9903f9ea-023b-444b-a892-5cbf4eb39a52","canonical_ref":{"entity_type":"claim","id":"c30904c0-339e-46da-93c2-c5993599c9ee","revision":"1"},"code":null}
```

## Exchange 2 · red

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 248254f2-4426-42bf-8ab0-834d106bc1c1
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"248254f2-4426-42bf-8ab0-834d106bc1c1","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"1946ae9f-4e37-4dbd-bd00-ce580b933f0a","version":"1","sha256":"bc804c5dd68caee79c4dca1845b215f25c187a658ae1f8cbd7640f71f654de11"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 50dc4a1a-b3fd-464a-bde2-5626910e1af5

{"observation_ref":{"entity_type":"observation","id":"10446560-088f-420a-971c-5972cbf50627","revision":"1"},"capture_id":"248254f2-4426-42bf-8ab0-834d106bc1c1","status":"accepted","artifact_refs":[{"id":"1946ae9f-4e37-4dbd-bd00-ce580b933f0a","version":"1","sha256":"bc804c5dd68caee79c4dca1845b215f25c187a658ae1f8cbd7640f71f654de11"}],"request_id":"50dc4a1a-b3fd-464a-bde2-5626910e1af5","code":null}
```

## Exchange 3 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 331
content-type: application/json
host: testserver
idempotency-key: fabe728a-78f2-47f0-9913-ce82b73008ae
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Private successor","basis_refs":[{"entity_type":"observation","id":"10446560-088f-420a-971c-5972cbf50627","revision":"1"}],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"c30904c0-339e-46da-93c2-c5993599c9ee","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 7a968f2c-bdf8-427f-b3c1-dbda3933541f

{"status":"accepted_shared","local_ref":"c","request_id":"7a968f2c-bdf8-427f-b3c1-dbda3933541f","canonical_ref":{"entity_type":"claim","id":"c30904c0-339e-46da-93c2-c5993599c9ee","revision":"2"},"code":null}
```

## Exchange 4 · red

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1110
content-type: application/json
host: testserver
idempotency-key: debbb68f-29bc-45be-8d55-df2e3d8b5661
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"debbb68f-29bc-45be-8d55-df2e3d8b5661","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"68ac23a0-3d59-4ab1-bc89-ca79e98ccbf2","read_set":[{"entity_type":"claim","id":"c30904c0-339e-46da-93c2-c5993599c9ee","revision":"1"}],"raw_output_ref":{"id":"863118ec-4225-4232-bffc-15013126c9ea","version":"1","sha256":"5796a59956789ee9e4df39a73ef4f427ef0a9c2d35e18f5557a2c26b3f2adffc"},"raw_output_digest":"5796a59956789ee9e4df39a73ef4f427ef0a9c2d35e18f5557a2c26b3f2adffc","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Old snapshot analysis","basis_refs":[{"entity_type":"claim","id":"c30904c0-339e-46da-93c2-c5993599c9ee","revision":"1"}],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 363
content-type: application/json
x-request-id: 640ddcae-0864-4151-a334-f8c6ff0cda71

{"submission_id":"debbb68f-29bc-45be-8d55-df2e3d8b5661","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"640ddcae-0864-4151-a334-f8c6ff0cda71","canonical_ref":{"entity_type":"claim","id":"36b2a763-1aed-401a-b0aa-8898e9ed9c53","revision":"1"},"code":null}],"request_id":"640ddcae-0864-4151-a334-f8c6ff0cda71","code":null}
```

## Exchange 5 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: b567b9e5-6a7e-4f0d-9baa-98af9c57c092
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Public premise v1","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 4996ad84-bbd5-4a6d-8b54-8e7d5defb886

{"status":"accepted_shared","local_ref":"c","request_id":"4996ad84-bbd5-4a6d-8b54-8e7d5defb886","canonical_ref":{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"},"code":null}
```

## Exchange 6 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 254
content-type: application/json
host: testserver
idempotency-key: 047d12d9-3ec4-4d58-a02f-f00d1403274f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","basis_refs":[{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: bbbf3efc-a48c-451c-9a35-3c4b22523475

{"status":"accepted_shared","local_ref":"c","request_id":"bbbf3efc-a48c-451c-9a35-3c4b22523475","canonical_ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"code":null}
```

## Exchange 7 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 658
content-type: application/json
host: testserver
idempotency-key: 40e6b036-9a6a-44ee-a1db-76b7e0f12437
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"e8f26504-832b-4807-8149-4c669cf9bc37","claim_ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"input_refs":[{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: 3da0357e-75b1-4c2e-83e6-91cbe01beb19

{"assessment_id":"e8f26504-832b-4807-8149-4c669cf9bc37","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"request_id":"3da0357e-75b1-4c2e-83e6-91cbe01beb19","code":null}
```

## Exchange 8 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/15ec1468-3d19-49ba-8da2-df2b77dc975b?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: a36a890d-0c51-4418-b8d0-8ee431521783
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 888
content-type: application/json
x-request-id: f7a0a21c-0e56-4ae9-b2c2-10f7a2cf48ea

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["e8f26504-832b-4807-8149-4c669cf9bc37"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"display_kind":"fact","record":{"claim_id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:55:31.773782Z","supersedes":null}}
```

## Exchange 9 · red

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: e583c9f0-99aa-44fa-b0f3-bc5a7c17adfb
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"e583c9f0-99aa-44fa-b0f3-bc5a7c17adfb","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"70264a61-c02f-4910-ad47-0551ab69f824","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: ad8f646f-0901-40e5-97cd-7af94cb4941e

{"observation_ref":{"entity_type":"observation","id":"6f204594-5f26-4f01-84f5-81828e546b6d","revision":"1"},"capture_id":"e583c9f0-99aa-44fa-b0f3-bc5a7c17adfb","status":"accepted","artifact_refs":[{"id":"70264a61-c02f-4910-ad47-0551ab69f824","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"request_id":"ad8f646f-0901-40e5-97cd-7af94cb4941e","code":null}
```

## Exchange 10 · red

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 349
content-type: application/json
host: testserver
idempotency-key: 8d1baeae-cd7e-4c5d-8847-5582517fc214
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Revised private premise v2","basis_refs":[{"entity_type":"observation","id":"6f204594-5f26-4f01-84f5-81828e546b6d","revision":"1"}],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 99dbc539-f0e9-4a39-8ba6-24c110978689

{"status":"accepted_shared","local_ref":"c","request_id":"99dbc539-f0e9-4a39-8ba6-24c110978689","canonical_ref":{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"2"},"code":null}
```

## Exchange 11 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/15ec1468-3d19-49ba-8da2-df2b77dc975b?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 31077830-7858-47dd-bfdf-96973f0e61ae
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 824
content-type: application/json
x-request-id: f1b4c192-18a6-426d-ad01-42cc7f5ef2bc

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"stale","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"display_kind":"claim","record":{"claim_id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:55:31.773782Z","supersedes":null}}
```

## Exchange 12 · red

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/15ec1468-3d19-49ba-8da2-df2b77dc975b?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 4b425dd1-ae37-46ae-b70b-bc2504d44bd3
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 888
content-type: application/json
x-request-id: 2dfb138a-418a-4640-a26e-dee24835661e

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["e8f26504-832b-4807-8149-4c669cf9bc37"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1"},"display_kind":"fact","record":{"claim_id":"15ec1468-3d19-49ba-8da2-df2b77dc975b","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"30b5b42c-8c48-499c-bb19-fbfc659a6d25","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:55:31.773782Z","supersedes":null}}
```

## Exchange 13 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 147
content-type: application/json
host: testserver
idempotency-key: 1b2cfe64-6a8d-488d-975f-4d73d2ef0d34
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Public premise","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: eb19f865-5009-4dea-8bc1-4b06a7bb2331

{"status":"accepted_shared","local_ref":"c","request_id":"eb19f865-5009-4dea-8bc1-4b06a7bb2331","canonical_ref":{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"1"},"code":null}
```

## Exchange 14 · final

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: b7e0e0a2-3bdf-4d21-848c-4342c6ee2234
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"b7e0e0a2-3bdf-4d21-848c-4342c6ee2234","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"1277c5a7-4ffe-411b-bb8d-b4ad30eaea20","version":"1","sha256":"bc804c5dd68caee79c4dca1845b215f25c187a658ae1f8cbd7640f71f654de11"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: f1a07adc-e7e8-4416-9399-ac4aa4ffebf4

{"observation_ref":{"entity_type":"observation","id":"0357a194-6dba-4890-a0ca-9d3cbdfecabd","revision":"1"},"capture_id":"b7e0e0a2-3bdf-4d21-848c-4342c6ee2234","status":"accepted","artifact_refs":[{"id":"1277c5a7-4ffe-411b-bb8d-b4ad30eaea20","version":"1","sha256":"bc804c5dd68caee79c4dca1845b215f25c187a658ae1f8cbd7640f71f654de11"}],"request_id":"f1a07adc-e7e8-4416-9399-ac4aa4ffebf4","code":null}
```

## Exchange 15 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 331
content-type: application/json
host: testserver
idempotency-key: 012461c6-6928-450e-86cd-625779977d76
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Private successor","basis_refs":[{"entity_type":"observation","id":"0357a194-6dba-4890-a0ca-9d3cbdfecabd","revision":"1"}],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 84bd0794-ad2e-4e76-b0b3-b9c99fa46679

{"status":"accepted_shared","local_ref":"c","request_id":"84bd0794-ad2e-4e76-b0b3-b9c99fa46679","canonical_ref":{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"2"},"code":null}
```

## Exchange 16 · final

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_worker_fixture}
connection: keep-alive
content-length: 1110
content-type: application/json
host: testserver
idempotency-key: 06d86976-108a-495d-947b-b62ef7a3873f
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"06d86976-108a-495d-947b-b62ef7a3873f","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"9e16873c-d0ce-47b4-bd66-5e2028311b00","read_set":[{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"1"}],"raw_output_ref":{"id":"fe9bf53a-df59-4bb9-82b5-fcfe66bb3f2b","version":"1","sha256":"e513a47a1aeae6635d85680562f70f5e10488f5a27eb997d32a6a38477c2a083"},"raw_output_digest":"e513a47a1aeae6635d85680562f70f5e10488f5a27eb997d32a6a38477c2a083","payload":{"schema_version":"wuji.agent-payload.v2","claims":[{"client_ref":"c","kind":"hypothesis","assertion_role":"candidate_fact","text":"Old snapshot analysis","basis_refs":[{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"1"}],"limitations":["isolated fixture"]}],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 372
content-type: application/json
x-request-id: c5e9b978-2a45-4626-92f2-6b188aef52a3

{"submission_id":"06d86976-108a-495d-947b-b62ef7a3873f","status":"accepted","components":[{"status":"accepted_shared","local_ref":"c","request_id":"c5e9b978-2a45-4626-92f2-6b188aef52a3","canonical_ref":{"entity_type":"claim","id":"7a65549a-15ee-44b5-9cd4-40d7e2a17373","revision":"1"},"code":"STALE_INPUT"}],"request_id":"c5e9b978-2a45-4626-92f2-6b188aef52a3","code":null}
```

## Exchange 17 · final

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/7a65549a-15ee-44b5-9cd4-40d7e2a17373?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 702ddc94-06de-4fec-9821-ab8f14a2087f
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 948
content-type: application/json
x-request-id: 8b68141a-1747-44c6-a608-3fbdd4efc3ea

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"current","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture","stale_input: basis no longer current; cannot drive control decisions"]},"ref":{"entity_type":"claim","id":"7a65549a-15ee-44b5-9cd4-40d7e2a17373","revision":"1"},"display_kind":"claim","record":{"claim_id":"7a65549a-15ee-44b5-9cd4-40d7e2a17373","revision":"1","task_id":"task-fixture","kind":"hypothesis","assertion_role":"candidate_fact","text":"Old snapshot analysis","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"a1df77bd-7db1-466d-ad83-08c62c0eddd2","revision":"1"}],"limitations":["isolated fixture","stale_input: basis no longer current; cannot drive control decisions"],"producer_kind":"agent","producer_ref":"run-fixture","created_at":"2026-09-12T23:57:20.413260Z","supersedes":null}}
```

## Exchange 18 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 159
content-type: application/json
host: testserver
idempotency-key: 94be2d0d-6dd2-4fde-8b12-4577d61f201f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Public premise v1","basis_refs":[],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 28b1def6-3bff-4062-9228-a7db760bd881

{"status":"accepted_shared","local_ref":"c","request_id":"28b1def6-3bff-4062-9228-a7db760bd881","canonical_ref":{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"},"code":null}
```

## Exchange 19 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 254
content-type: application/json
host: testserver
idempotency-key: b1bc0d7a-25b3-45f5-9c5e-a1cc4cbf4021
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","basis_refs":[{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}],"limitations":["isolated fixture"]}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 7c546020-aeef-4941-9cf4-5864c667cd0a

{"status":"accepted_shared","local_ref":"c","request_id":"7c546020-aeef-4941-9cf4-5864c667cd0a","canonical_ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"code":null}
```

## Exchange 20 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/assessments HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_assessor_fixture}
connection: keep-alive
content-length: 658
content-type: application/json
host: testserver
idempotency-key: b290c505-d041-4485-8516-b053d25c6695
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.api.v2","expected_version":"1","assessment":{"assessment_id":"bdb8be03-2ac3-4cdb-8ef7-087d1eeb1de7","claim_ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"input_refs":[{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}],"grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","method_kind":"human_attestation","method_version":"human-attestation-v1","reviewer_ref":"assessor-fixture","conditions":["isolated fixture"],"reason":"Read fixed evidence and assertion"},"supersedes_assessment_ids":[],"supersedes_reason":null}
```

```http
HTTP/1.1 202
content-length: 260
content-type: application/json
x-request-id: deeb64ba-1157-4f7e-8486-98761201adcb

{"assessment_id":"bdb8be03-2ac3-4cdb-8ef7-087d1eeb1de7","revision":"1","status":"accepted_for_check","claim_ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"request_id":"deeb64ba-1157-4f7e-8486-98761201adcb","code":null}
```

## Exchange 21 · final

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/37a63917-7fe7-4a76-97c4-3880f4a9a192?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 1145d556-46a3-499a-ae6a-18d5677becc7
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 888
content-type: application/json
x-request-id: bade272b-9d59-4e85-b558-2f47dd1df9e6

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"content_checked","evidence_state":"supported","applicability_state":"current","eligible":true,"assessment_ids":["bdb8be03-2ac3-4cdb-8ef7-087d1eeb1de7"],"conditions":["isolated fixture"],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"display_kind":"fact","record":{"claim_id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:57:19.570951Z","supersedes":null}}
```

## Exchange 22 · final

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_collector_fixture}
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 2f00ebd5-f516-487c-8540-c36f0a934fe7
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"2f00ebd5-f516-487c-8540-c36f0a934fe7","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"5efed33b-6c4a-4ed6-b464-e33baf4aece5","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 16fdcfe1-32ec-4c51-b446-8673b7103ccf

{"observation_ref":{"entity_type":"observation","id":"898aed1f-c166-4849-8dc5-c2aca8ea06d8","revision":"1"},"capture_id":"2f00ebd5-f516-487c-8540-c36f0a934fe7","status":"accepted","artifact_refs":[{"id":"5efed33b-6c4a-4ed6-b464-e33baf4aece5","version":"1","sha256":"6229aa30275316d05bbd53735691f7885ec7eabd67d54ca2308e4818126a6ba9"}],"request_id":"16fdcfe1-32ec-4c51-b446-8673b7103ccf","code":null}
```

## Exchange 23 · final

```http
POST http://testserver/api/v2/tasks/task-fixture/claims/proposals HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
content-length: 349
content-type: application/json
host: testserver
idempotency-key: 580511be-4d9c-4624-87e1-2444c532b28f
user-agent: python-httpx/0.28.1

{"client_ref":"c","kind":"observation-summary","assertion_role":"candidate_fact","text":"Revised private premise v2","basis_refs":[{"entity_type":"observation","id":"898aed1f-c166-4849-8dc5-c2aca8ea06d8","revision":"1"}],"limitations":["isolated fixture"],"revises":{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}}
```

```http
HTTP/1.1 202
content-length: 207
content-type: application/json
x-request-id: 30bd3370-0f21-401c-95ed-710b6719f519

{"status":"accepted_shared","local_ref":"c","request_id":"30bd3370-0f21-401c-95ed-710b6719f519","canonical_ref":{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"2"},"code":null}
```

## Exchange 24 · final

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/37a63917-7fe7-4a76-97c4-3880f4a9a192?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_agent_fixture}
connection: keep-alive
host: testserver
idempotency-key: 24e6521b-e9b7-4742-9981-3f93956048af
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 824
content-type: application/json
x-request-id: 46318f24-be11-4a50-870a-1eb11bac0f7d

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"stale","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"display_kind":"claim","record":{"claim_id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:57:19.570951Z","supersedes":null}}
```

## Exchange 25 · final

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/37a63917-7fe7-4a76-97c4-3880f4a9a192?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: c8cd6ec1-3a88-44f5-bed9-5a3377bb126c
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-length: 824
content-type: application/json
x-request-id: f90113d9-89a5-42f5-9636-5aeda4d3c065

{"assessment":{"policy_version":"assessment-policy-v1","grounding_state":"linked","evidence_state":"unassessed","applicability_state":"stale","eligible":false,"assessment_ids":[],"conditions":[],"limitations":["isolated fixture"]},"ref":{"entity_type":"claim","id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1"},"display_kind":"claim","record":{"claim_id":"37a63917-7fe7-4a76-97c4-3880f4a9a192","revision":"1","task_id":"task-fixture","kind":"derived-conclusion","assertion_role":"candidate_fact","text":"Conclusion supported by premise","structured_assertion":null,"basis_refs":[{"entity_type":"claim","id":"38207a28-8ee8-4a06-a847-6749aef79068","revision":"1"}],"limitations":["isolated fixture"],"producer_kind":"agent","producer_ref":"agent-fixture","created_at":"2026-09-12T23:57:19.570951Z","supersedes":null}}
```

## Exchange 26 · final

```http
GET http://testserver/api/v2/tasks/task-fixture/records/claim/37a63917-7fe7-4a76-97c4-3880f4a9a192?revision=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer ${TOKEN_reader_fixture}
connection: keep-alive
host: testserver
idempotency-key: 951cf45b-f12b-4907-b69a-a58340f908aa
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 404
content-length: 164
content-type: application/json
x-request-id: 49a31177-4b76-4953-8250-89aded03cbe9

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"The request could not be completed.","request_id":"49a31177-4b76-4953-8250-89aded03cbe9","retryable":false,"details":{}}
```
