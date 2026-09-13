# P05 完整 HTTP 复现包

被测代码 `71741c4eec7b7e3b10beaff05fd300ec1ace3b55`。以下均为最终采集的真实 ASGI 请求/响应，业务路由来自现有 P03/P04；ControlService 在同一测试的真实 PG 事务中调用，P05 没有伪造控制 HTTP 路由。

认证头中的短期测试 JWT 已替换为 `<EPHEMERAL_TEST_JWT_REISSUE>`，未截断请求/响应业务正文。令牌由 `tests/vnext/support/identity_provider.py` 的临时签发器重新生成，私钥仅在进程内。隔离 DB、对象与固定前提由 `tests/vnext/test_work_state_guards.py::control_case` 及各测试建立。重放需运行报告命令；不可将旧签名或动态 UUID 当作跨运行凭据。

## HTTP 1 · test_cancel_preserves_independent_captured_evidence_without_fact

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/evidence HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 747
content-type: application/json
host: testserver
idempotency-key: 958865fc-4bb5-4bd6-b489-86df5587fe5a
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.capture.v2","capture_id":"958865fc-4bb5-4bd6-b489-86df5587fe5a","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"tool_call_id":"tool-fixture","tool_attempt_id":"attempt-fixture","artifact_refs":[{"id":"5724e991-6016-4eba-b5e8-ed97469e8ff4","version":"1","sha256":"dcf11759c88a10b9d37f6b42db3bf168eaf6715f77bf21764e7b91a7034480a7"}],"capture_layer":"fixture_file_bytes","observed_at":"2026-09-13T00:00:00Z","received_at":"2026-09-13T00:00:01Z","evidence_origin":"fixture_capture","conditions":[],"completeness":"complete"}
```

```http
HTTP/1.1 202
content-length: 398
content-type: application/json
x-request-id: 01df7c90-65b7-49dc-b6ad-bdd6e16d2e74

{"observation_ref":{"entity_type":"observation","id":"87b665a2-29fe-44b8-8907-7b067f6d6e25","revision":"1"},"capture_id":"958865fc-4bb5-4bd6-b489-86df5587fe5a","status":"accepted","artifact_refs":[{"id":"5724e991-6016-4eba-b5e8-ed97469e8ff4","version":"1","sha256":"dcf11759c88a10b9d37f6b42db3bf168eaf6715f77bf21764e7b91a7034480a7"}],"request_id":"01df7c90-65b7-49dc-b6ad-bdd6e16d2e74","code":null}
```

## HTTP 2 · test_exit_receipt_before_running_notification_settles_without_illegal_edge

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: d81f5d8f-d9f0-49a9-930f-ef75fa9e4b7d
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"d81f5d8f-d9f0-49a9-930f-ef75fa9e4b7d","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"f55ffec4-1532-46ae-b833-370370a9f8a6","read_set":[],"raw_output_ref":{"id":"9920d903-141a-4578-9872-dced9134342c","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 156
content-type: application/json
x-request-id: 08f1cc3a-1ea3-4796-b119-db23abcee310

{"submission_id":"d81f5d8f-d9f0-49a9-930f-ef75fa9e4b7d","status":"accepted","components":[],"request_id":"08f1cc3a-1ea3-4796-b119-db23abcee310","code":null}
```

## HTTP 3 · test_explicit_process_failure_keeps_accepted_result_separate

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: 148f5efb-2930-4d8a-b2bf-8a18c18680dd
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"148f5efb-2930-4d8a-b2bf-8a18c18680dd","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"9979f16e-d224-4852-8084-32f226092989","read_set":[],"raw_output_ref":{"id":"79e8f140-8b39-4e33-a1d8-1dbc6e86fdbd","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 156
content-type: application/json
x-request-id: 1c548ba9-5a71-4322-a148-d2a67b0e1293

{"submission_id":"148f5efb-2930-4d8a-b2bf-8a18c18680dd","status":"accepted","components":[],"request_id":"1c548ba9-5a71-4322-a148-d2a67b0e1293","code":null}
```

## HTTP 4 · test_completion_closes_with_partial_and_cancels_only_unsettled_work

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: d2c736e5-43a9-4773-bd2a-94376c9cd872
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"d2c736e5-43a9-4773-bd2a-94376c9cd872","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"38728154-161a-4205-8941-95b8ca7b19ce","read_set":[],"raw_output_ref":{"id":"a4cae862-fbf7-477d-be10-f758f1234f7b","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 156
content-type: application/json
x-request-id: 61a539b2-885d-4bbe-b997-c3e3dd226068

{"submission_id":"d2c736e5-43a9-4773-bd2a-94376c9cd872","status":"accepted","components":[],"request_id":"61a539b2-885d-4bbe-b997-c3e3dd226068","code":null}
```

## HTTP 5 · test_result_projection_replay_incomplete_and_late_receipt

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: e44044b5-03de-4a7d-af6f-f413a38963ed
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"e44044b5-03de-4a7d-af6f-f413a38963ed","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"fde27f12-1140-4d4e-b618-965aec2deeff","read_set":[],"raw_output_ref":{"id":"c37ccab9-d04c-41fc-9e70-c556b78e909a","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 156
content-type: application/json
x-request-id: 64b50726-839e-4067-a893-cdb5f1d135e2

{"submission_id":"e44044b5-03de-4a7d-af6f-f413a38963ed","status":"accepted","components":[],"request_id":"64b50726-839e-4067-a893-cdb5f1d135e2","code":null}
```

## HTTP 6 · test_accepted_result_keeps_capacity_until_stored_exit

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: 22fe0617-5ec1-4ed7-a942-0100093f9bed
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"22fe0617-5ec1-4ed7-a942-0100093f9bed","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"fde65c53-961c-4b2c-b52a-bec356d3bf48","read_set":[],"raw_output_ref":{"id":"a93208a8-4072-4703-9b4f-4bce8a4c3730","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 156
content-type: application/json
x-request-id: 472fc64a-7666-4a7a-8e45-08c6ebba4495

{"submission_id":"22fe0617-5ec1-4ed7-a942-0100093f9bed","status":"accepted","components":[],"request_id":"472fc64a-7666-4a7a-8e45-08c6ebba4495","code":null}
```

## HTTP 7 · test_missing_final_output_cas_preserves_late_history

守卫/验证点：原始采集或结果发布与控制/退出状态独立；实际回执在 SQL 记录中可关联，接纳不直接结束进程。

```http
POST http://testserver/internal/v2/results HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
content-length: 792
content-type: application/json
host: testserver
idempotency-key: 9d569f40-e704-41c4-88ca-8a151f3a40e6
user-agent: python-httpx/0.28.1

{"schema_version":"wuji.result-envelope.v2","submission_id":"9d569f40-e704-41c4-88ca-8a151f3a40e6","identity":{"tenant_id":"tenant-fixture","project_id":"project-fixture","task_id":"task-fixture","work_item_id":"work-fixture","agent_run_id":"run-fixture","receiver_id":"receiver-fixture","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1"},"snapshot_id":"9bdabb67-0a1c-4fc7-994e-feb50848e85e","read_set":[],"raw_output_ref":{"id":"59f278b6-65fd-4850-94e6-e8675bfd1113","version":"1","sha256":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718"},"raw_output_digest":"09a33363b92b7cb6ac8aca454fa4b7a5e5ee4ad572c14c19337ae4c1eac67718","payload":{"schema_version":"wuji.agent-payload.v2","claims":[],"intent_proposals":[],"limitations":[]},"producer_version":"fixture-v1"}
```

```http
HTTP/1.1 202
content-length: 163
content-type: application/json
x-request-id: ee81b7a2-a815-4bba-a6c2-085616942da7

{"submission_id":"9d569f40-e704-41c4-88ca-8a151f3a40e6","status":"historical_only","components":[],"request_id":"ee81b7a2-a815-4bba-a6c2-085616942da7","code":null}
```
