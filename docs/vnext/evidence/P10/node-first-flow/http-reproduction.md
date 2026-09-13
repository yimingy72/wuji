# P10 Node Supervisor 完整 HTTP 复现包

基线：Node core `72d26a02308ab54db2c7c56b52f9861b8acdda82`；测试 `8e2fc7df599dc83756ebf2676ace44b761b41270`。所有地址均为测试进程临时绑定的 `127.0.0.1` 端口；Bearer 是固定无权限测试字符串。崩溃窗口的首个 PUT 被真实 `SIGKILL` 中断，因此没有 HTTP 响应体，随后 GET/PUT 展示持久恢复结果。

## after-running-before-response

漏洞点/验证点：running 已持久化但响应丢失时必须返回原回执，不能双 spawn。

### 请求/响应 1

```http
PUT /operations/start-after-running-before-response HTTP/1.1
Host: 127.0.0.1:63573
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 874

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-after-running-before-response","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-after-running-before-response","work_item_id":"work-after-running-before-response","agent_run_id":"run-after-running-before-response","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-after-running-before-response","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```text
<connection closed by injected Supervisor SIGKILL>
TypeError: fetch failed
```

### 请求/响应 2

```http
GET /operations/start-after-running-before-response HTTP/1.1
Host: 127.0.0.1:63575
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"48ea734cf6770aa27a97c9d0fc36c7b2d137395cddafb08facf4ecaac20be60c","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"observation":{"environment_ref":"local-after-running-before-response","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"kind":"started","observed_at":"2026-09-13T06:43:09.817Z","operation_id":"start-after-running-before-response","pod_uid":"pod-after-running-before-response","process":{"birth_id":"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23707,"started_at":"2026-09-13T06:43:09.795Z"},"reason":"running","receipt_id":"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f","source_digest":"6792bc45bec024beae233b498f68418df9c7422308907c191cce2ea63b7fa760","source_receipt":"{\"environment_ref\":\"local-after-running-before-response\",\"identity\":{\"agent_run_id\":\"run-after-running-before-response\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-running-before-response\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-running-before-response\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.817Z\",\"operation_id\":\"start-after-running-before-response\",\"pod_uid\":\"pod-after-running-before-response\",\"process\":{\"birth_id\":\"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23707,\"started_at\":\"2026-09-13T06:43:09.795Z\"},\"reason\":\"running\",\"receipt_id\":\"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f\"}"},"operation_id":"start-after-running-before-response","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-running-before-response","pod_uid":"pod-after-running-before-response","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 3

```http
PUT /operations/start-after-running-before-response HTTP/1.1
Host: 127.0.0.1:63575
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 874

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-after-running-before-response","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-after-running-before-response","work_item_id":"work-after-running-before-response","agent_run_id":"run-after-running-before-response","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-after-running-before-response","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"48ea734cf6770aa27a97c9d0fc36c7b2d137395cddafb08facf4ecaac20be60c","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"observation":{"environment_ref":"local-after-running-before-response","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"kind":"started","observed_at":"2026-09-13T06:43:09.817Z","operation_id":"start-after-running-before-response","pod_uid":"pod-after-running-before-response","process":{"birth_id":"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23707,"started_at":"2026-09-13T06:43:09.795Z"},"reason":"running","receipt_id":"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f","source_digest":"6792bc45bec024beae233b498f68418df9c7422308907c191cce2ea63b7fa760","source_receipt":"{\"environment_ref\":\"local-after-running-before-response\",\"identity\":{\"agent_run_id\":\"run-after-running-before-response\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-running-before-response\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-running-before-response\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.817Z\",\"operation_id\":\"start-after-running-before-response\",\"pod_uid\":\"pod-after-running-before-response\",\"process\":{\"birth_id\":\"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23707,\"started_at\":\"2026-09-13T06:43:09.795Z\"},\"reason\":\"running\",\"receipt_id\":\"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f\"}"},"operation_id":"start-after-running-before-response","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-running-before-response","pod_uid":"pod-after-running-before-response","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 4

```http
GET /operations/start-after-running-before-response HTTP/1.1
Host: 127.0.0.1:63575
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"48ea734cf6770aa27a97c9d0fc36c7b2d137395cddafb08facf4ecaac20be60c","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"observation":{"environment_ref":"local-after-running-before-response","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"kind":"started","observed_at":"2026-09-13T06:43:09.817Z","operation_id":"start-after-running-before-response","pod_uid":"pod-after-running-before-response","process":{"birth_id":"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23707,"started_at":"2026-09-13T06:43:09.795Z"},"reason":"running","receipt_id":"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f","source_digest":"6792bc45bec024beae233b498f68418df9c7422308907c191cce2ea63b7fa760","source_receipt":"{\"environment_ref\":\"local-after-running-before-response\",\"identity\":{\"agent_run_id\":\"run-after-running-before-response\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-running-before-response\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-running-before-response\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.817Z\",\"operation_id\":\"start-after-running-before-response\",\"pod_uid\":\"pod-after-running-before-response\",\"process\":{\"birth_id\":\"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23707,\"started_at\":\"2026-09-13T06:43:09.795Z\"},\"reason\":\"running\",\"receipt_id\":\"719a14fde0e60b230f2e404b2b85f3f1b2cfde02210609480be639ea8884822f\"}"},"operation_id":"start-after-running-before-response","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-running-before-response","pod_uid":"pod-after-running-before-response","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 5

```http
GET /operations/start-after-running-before-response HTTP/1.1
Host: 127.0.0.1:63575
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"48ea734cf6770aa27a97c9d0fc36c7b2d137395cddafb08facf4ecaac20be60c","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"observation":{"environment_ref":"local-after-running-before-response","identity":{"agent_run_id":"run-after-running-before-response","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-running-before-response","tenant_id":"tenant-p10","work_item_id":"work-after-running-before-response"},"kind":"exited","observed_at":"2026-09-13T06:43:09.941Z","operation_id":"start-after-running-before-response","pod_uid":"pod-after-running-before-response","process":{"birth_id":"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:09.928Z","pid":23707,"started_at":"2026-09-13T06:43:09.795Z"},"reason":"exited","receipt_id":"2dd25346939f654883efce0ecdf803ca05202a84cd913affcf631a642ebb6338","source_digest":"19881d63e062566bc304f1e9d8cffb1f315956254e91ff74aa0b7ef5953a34b1","source_receipt":"{\"environment_ref\":\"local-after-running-before-response\",\"identity\":{\"agent_run_id\":\"run-after-running-before-response\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-running-before-response\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-running-before-response\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:09.941Z\",\"operation_id\":\"start-after-running-before-response\",\"pod_uid\":\"pod-after-running-before-response\",\"process\":{\"birth_id\":\"b6f8338e86171520631ad4ea64bbc73e58c5505f89357162f10023466f3ae3a2:c4c70735fd1658733e2a6a109d2e6725d48bd33e1abd6e694b768e0739e51791:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:09.928Z\",\"pid\":23707,\"started_at\":\"2026-09-13T06:43:09.795Z\"},\"reason\":\"exited\",\"receipt_id\":\"2dd25346939f654883efce0ecdf803ca05202a84cd913affcf631a642ebb6338\"}"},"operation_id":"start-after-running-before-response","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-running-before-response","pod_uid":"pod-after-running-before-response","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-after-running-before-response",
      "fixture_instance_id": "8ac58611-0267-4025-8dfc-7f9adb61cb30",
      "pid": 23707
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-after-running-before-response",
      "fixture_instance_id": "8ac58611-0267-4025-8dfc-7f9adb61cb30",
      "pid": 23707,
      "ppid": 23684,
      "observed_at": "2026-09-13T06:43:09.832Z",
      "monotonic_ns": "406827590063458"
    },
    {
      "event": "exit",
      "operation_id": "start-after-running-before-response",
      "fixture_instance_id": "8ac58611-0267-4025-8dfc-7f9adb61cb30",
      "pid": 23707,
      "ppid": 23684,
      "observed_at": "2026-09-13T06:43:09.925Z",
      "monotonic_ns": "406827682466583",
      "reason": "release_file",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": [
    {
      "window": "after_running_before_response",
      "operation_id": "start-after-running-before-response",
      "pid": 23662
    }
  ]
}
```

## after-spawn-before-running-receipt

漏洞点/验证点：实际出生后、running 回执前崩溃必须恢复同一进程身份，不能双 spawn。

### 请求/响应 1

```http
PUT /operations/start-after-spawn-before-running-receipt HTTP/1.1
Host: 127.0.0.1:63568
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 899

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-after-spawn-before-running-receipt","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-after-spawn-before-running-receipt","work_item_id":"work-after-spawn-before-running-receipt","agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-after-spawn-before-running-receipt","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```text
<connection closed by injected Supervisor SIGKILL>
TypeError: fetch failed
```

### 请求/响应 2

```http
GET /operations/start-after-spawn-before-running-receipt HTTP/1.1
Host: 127.0.0.1:63570
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"f273150edf895fb6cbc2cfa32c0088526e0bb7a03686ad5d201e7169555f4dae","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"observation":{"environment_ref":"local-after-spawn-before-running-receipt","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"kind":"started","observed_at":"2026-09-13T06:43:09.551Z","operation_id":"start-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","process":{"birth_id":"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23660,"started_at":"2026-09-13T06:43:09.425Z"},"reason":"running","receipt_id":"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915","source_digest":"38cc0e9000f11fbdd301407e826831fb811df1f2b98e097633557c7b2eefd29f","source_receipt":"{\"environment_ref\":\"local-after-spawn-before-running-receipt\",\"identity\":{\"agent_run_id\":\"run-after-spawn-before-running-receipt\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-spawn-before-running-receipt\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-spawn-before-running-receipt\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.551Z\",\"operation_id\":\"start-after-spawn-before-running-receipt\",\"pod_uid\":\"pod-after-spawn-before-running-receipt\",\"process\":{\"birth_id\":\"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23660,\"started_at\":\"2026-09-13T06:43:09.425Z\"},\"reason\":\"running\",\"receipt_id\":\"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915\"}"},"operation_id":"start-after-spawn-before-running-receipt","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 3

```http
PUT /operations/start-after-spawn-before-running-receipt HTTP/1.1
Host: 127.0.0.1:63570
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 899

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-after-spawn-before-running-receipt","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-after-spawn-before-running-receipt","work_item_id":"work-after-spawn-before-running-receipt","agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-after-spawn-before-running-receipt","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"f273150edf895fb6cbc2cfa32c0088526e0bb7a03686ad5d201e7169555f4dae","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"observation":{"environment_ref":"local-after-spawn-before-running-receipt","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"kind":"started","observed_at":"2026-09-13T06:43:09.551Z","operation_id":"start-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","process":{"birth_id":"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23660,"started_at":"2026-09-13T06:43:09.425Z"},"reason":"running","receipt_id":"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915","source_digest":"38cc0e9000f11fbdd301407e826831fb811df1f2b98e097633557c7b2eefd29f","source_receipt":"{\"environment_ref\":\"local-after-spawn-before-running-receipt\",\"identity\":{\"agent_run_id\":\"run-after-spawn-before-running-receipt\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-spawn-before-running-receipt\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-spawn-before-running-receipt\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.551Z\",\"operation_id\":\"start-after-spawn-before-running-receipt\",\"pod_uid\":\"pod-after-spawn-before-running-receipt\",\"process\":{\"birth_id\":\"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23660,\"started_at\":\"2026-09-13T06:43:09.425Z\"},\"reason\":\"running\",\"receipt_id\":\"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915\"}"},"operation_id":"start-after-spawn-before-running-receipt","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 4

```http
GET /operations/start-after-spawn-before-running-receipt HTTP/1.1
Host: 127.0.0.1:63570
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"f273150edf895fb6cbc2cfa32c0088526e0bb7a03686ad5d201e7169555f4dae","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"observation":{"environment_ref":"local-after-spawn-before-running-receipt","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"kind":"started","observed_at":"2026-09-13T06:43:09.551Z","operation_id":"start-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","process":{"birth_id":"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23660,"started_at":"2026-09-13T06:43:09.425Z"},"reason":"running","receipt_id":"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915","source_digest":"38cc0e9000f11fbdd301407e826831fb811df1f2b98e097633557c7b2eefd29f","source_receipt":"{\"environment_ref\":\"local-after-spawn-before-running-receipt\",\"identity\":{\"agent_run_id\":\"run-after-spawn-before-running-receipt\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-spawn-before-running-receipt\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-spawn-before-running-receipt\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.551Z\",\"operation_id\":\"start-after-spawn-before-running-receipt\",\"pod_uid\":\"pod-after-spawn-before-running-receipt\",\"process\":{\"birth_id\":\"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23660,\"started_at\":\"2026-09-13T06:43:09.425Z\"},\"reason\":\"running\",\"receipt_id\":\"f6a4366c035d6c52a682a3ebca99fe3304475df68a5a0a03d28a5a855eda9915\"}"},"operation_id":"start-after-spawn-before-running-receipt","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 5

```http
GET /operations/start-after-spawn-before-running-receipt HTTP/1.1
Host: 127.0.0.1:63570
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"f273150edf895fb6cbc2cfa32c0088526e0bb7a03686ad5d201e7169555f4dae","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"observation":{"environment_ref":"local-after-spawn-before-running-receipt","identity":{"agent_run_id":"run-after-spawn-before-running-receipt","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-after-spawn-before-running-receipt","tenant_id":"tenant-p10","work_item_id":"work-after-spawn-before-running-receipt"},"kind":"exited","observed_at":"2026-09-13T06:43:09.583Z","operation_id":"start-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","process":{"birth_id":"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:09.571Z","pid":23660,"started_at":"2026-09-13T06:43:09.425Z"},"reason":"exited","receipt_id":"4f800e7d14a2935d821201b88b5f5846a54404a5575d2ce48e31e58668eb9e3d","source_digest":"7e2752b02fdfcd55ffd96d7ffb7b22ab04121dd21943768add7605e7ebbe3eb2","source_receipt":"{\"environment_ref\":\"local-after-spawn-before-running-receipt\",\"identity\":{\"agent_run_id\":\"run-after-spawn-before-running-receipt\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-after-spawn-before-running-receipt\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-after-spawn-before-running-receipt\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:09.583Z\",\"operation_id\":\"start-after-spawn-before-running-receipt\",\"pod_uid\":\"pod-after-spawn-before-running-receipt\",\"process\":{\"birth_id\":\"db578eb26370fb6faaa2f78442dec72f9e39ab5794970e45c9642caa478479c9:933ce8c92de05eb115bff72cddd8dc812ce6590080284f842a2392546fef5def:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:09.571Z\",\"pid\":23660,\"started_at\":\"2026-09-13T06:43:09.425Z\"},\"reason\":\"exited\",\"receipt_id\":\"4f800e7d14a2935d821201b88b5f5846a54404a5575d2ce48e31e58668eb9e3d\"}"},"operation_id":"start-after-spawn-before-running-receipt","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-after-spawn-before-running-receipt","pod_uid":"pod-after-spawn-before-running-receipt","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-after-spawn-before-running-receipt",
      "fixture_instance_id": "ac25007d-deb6-432e-bcae-2d94404d708d",
      "pid": 23660
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-after-spawn-before-running-receipt",
      "fixture_instance_id": "ac25007d-deb6-432e-bcae-2d94404d708d",
      "pid": 23660,
      "ppid": 23659,
      "observed_at": "2026-09-13T06:43:09.462Z",
      "monotonic_ns": "406827219937416"
    },
    {
      "event": "exit",
      "operation_id": "start-after-spawn-before-running-receipt",
      "fixture_instance_id": "ac25007d-deb6-432e-bcae-2d94404d708d",
      "pid": 23660,
      "ppid": 23659,
      "observed_at": "2026-09-13T06:43:09.569Z",
      "monotonic_ns": "406827326264875",
      "reason": "release_file",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": [
    {
      "window": "after_spawn_before_running_receipt",
      "operation_id": "start-after-spawn-before-running-receipt",
      "pid": 23658
    }
  ]
}
```

## before-prepared

漏洞点/验证点：prepared 前崩溃不能留下伪执行事实；原 operation 可重新派发且实际只出生一次。

### 请求/响应 1

```http
PUT /operations/start-before-prepared HTTP/1.1
Host: 127.0.0.1:63561
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 804

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-before-prepared","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-before-prepared","work_item_id":"work-before-prepared","agent_run_id":"run-before-prepared","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-before-prepared","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```text
<connection closed by injected Supervisor SIGKILL>
TypeError: fetch failed
```

### 请求/响应 2

```http
GET /operations/start-before-prepared HTTP/1.1
Host: 127.0.0.1:63563
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 404
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"code":"OPERATION_NOT_FOUND"}
```

### 请求/响应 3

```http
PUT /operations/start-before-prepared HTTP/1.1
Host: 127.0.0.1:63563
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 804

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-before-prepared","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-before-prepared","work_item_id":"work-before-prepared","agent_run_id":"run-before-prepared","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-before-prepared","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"64c0eeee05719b99756c2bff729f23db8bd0032bed56c4203a861601d16575d9","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"observation":{"environment_ref":"local-before-prepared","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"kind":"started","observed_at":"2026-09-13T06:43:09.177Z","operation_id":"start-before-prepared","pod_uid":"pod-before-prepared","process":{"birth_id":"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23657,"started_at":"2026-09-13T06:43:09.150Z"},"reason":"running","receipt_id":"265aba6f0a107359dd5829349d5e993dade47abf93afa928e1f0060265c1f2f5","source_digest":"e19c28ffcd2508ed213ed1533e23b2c822c6c8723f9252c9796c475b9195226f","source_receipt":"{\"environment_ref\":\"local-before-prepared\",\"identity\":{\"agent_run_id\":\"run-before-prepared\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-before-prepared\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-before-prepared\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.177Z\",\"operation_id\":\"start-before-prepared\",\"pod_uid\":\"pod-before-prepared\",\"process\":{\"birth_id\":\"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23657,\"started_at\":\"2026-09-13T06:43:09.150Z\"},\"reason\":\"running\",\"receipt_id\":\"265aba6f0a107359dd5829349d5e993dade47abf93afa928e1f0060265c1f2f5\"}"},"operation_id":"start-before-prepared","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-before-prepared","pod_uid":"pod-before-prepared","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 4

```http
GET /operations/start-before-prepared HTTP/1.1
Host: 127.0.0.1:63563
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"64c0eeee05719b99756c2bff729f23db8bd0032bed56c4203a861601d16575d9","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"observation":{"environment_ref":"local-before-prepared","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"kind":"started","observed_at":"2026-09-13T06:43:09.177Z","operation_id":"start-before-prepared","pod_uid":"pod-before-prepared","process":{"birth_id":"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23657,"started_at":"2026-09-13T06:43:09.150Z"},"reason":"running","receipt_id":"265aba6f0a107359dd5829349d5e993dade47abf93afa928e1f0060265c1f2f5","source_digest":"e19c28ffcd2508ed213ed1533e23b2c822c6c8723f9252c9796c475b9195226f","source_receipt":"{\"environment_ref\":\"local-before-prepared\",\"identity\":{\"agent_run_id\":\"run-before-prepared\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-before-prepared\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-before-prepared\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:09.177Z\",\"operation_id\":\"start-before-prepared\",\"pod_uid\":\"pod-before-prepared\",\"process\":{\"birth_id\":\"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23657,\"started_at\":\"2026-09-13T06:43:09.150Z\"},\"reason\":\"running\",\"receipt_id\":\"265aba6f0a107359dd5829349d5e993dade47abf93afa928e1f0060265c1f2f5\"}"},"operation_id":"start-before-prepared","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-before-prepared","pod_uid":"pod-before-prepared","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 5

```http
GET /operations/start-before-prepared HTTP/1.1
Host: 127.0.0.1:63563
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:09 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"64c0eeee05719b99756c2bff729f23db8bd0032bed56c4203a861601d16575d9","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"observation":{"environment_ref":"local-before-prepared","identity":{"agent_run_id":"run-before-prepared","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-before-prepared","tenant_id":"tenant-p10","work_item_id":"work-before-prepared"},"kind":"exited","observed_at":"2026-09-13T06:43:09.209Z","operation_id":"start-before-prepared","pod_uid":"pod-before-prepared","process":{"birth_id":"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:09.203Z","pid":23657,"started_at":"2026-09-13T06:43:09.150Z"},"reason":"exited","receipt_id":"c88378e0b400eb22968deffe9f5474cd5f7d7905401c4613724051324293259c","source_digest":"d91a8940433e46dc9358d7eb53261a4d26ed98517d336b213b5887f032a6638a","source_receipt":"{\"environment_ref\":\"local-before-prepared\",\"identity\":{\"agent_run_id\":\"run-before-prepared\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-before-prepared\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-before-prepared\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:09.209Z\",\"operation_id\":\"start-before-prepared\",\"pod_uid\":\"pod-before-prepared\",\"process\":{\"birth_id\":\"1da0645fd1c6075aed5200f957405fe944d846d1ae18b7734954d164868ba4ca:68b579876db18dd3eaba3383a7dc0ab2d3abbc28a01dc6e636ff991bc36cd049:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:09.203Z\",\"pid\":23657,\"started_at\":\"2026-09-13T06:43:09.150Z\"},\"reason\":\"exited\",\"receipt_id\":\"c88378e0b400eb22968deffe9f5474cd5f7d7905401c4613724051324293259c\"}"},"operation_id":"start-before-prepared","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-before-prepared","pod_uid":"pod-before-prepared","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-before-prepared",
      "fixture_instance_id": "288ea5d9-4454-478b-aaeb-59e896aa8795",
      "pid": 23657
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-before-prepared",
      "fixture_instance_id": "288ea5d9-4454-478b-aaeb-59e896aa8795",
      "pid": 23657,
      "ppid": 23656,
      "observed_at": "2026-09-13T06:43:09.189Z",
      "monotonic_ns": "406826946797000"
    },
    {
      "event": "exit",
      "operation_id": "start-before-prepared",
      "fixture_instance_id": "288ea5d9-4454-478b-aaeb-59e896aa8795",
      "pid": 23657,
      "ppid": 23656,
      "observed_at": "2026-09-13T06:43:09.201Z",
      "monotonic_ns": "406826958509625",
      "reason": "release_file",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": [
    {
      "window": "before_prepared",
      "operation_id": "start-before-prepared",
      "pid": 23653
    }
  ]
}
```

## control-exit

漏洞点/验证点：旧 control 身份必须拒绝；accepted 不能冒充 exited。

### 请求/响应 1

```http
PUT /operations/start-control-exit HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 789

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-control-exit","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-control-exit","work_item_id":"work-control-exit","agent_run_id":"run-control-exit","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-control-exit","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 2

```http
POST /operations/start-control-exit/control HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 306

{"control_operation_id":"stop-stale","action":"stop","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-control-exit","work_item_id":"work-control-exit","agent_run_id":"run-control-exit","execution_epoch":"1","run_epoch":"0","runtime_attempt":"1","receiver_id":"receiver-p10"}}
```

```http
HTTP/1.1 409
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"code":"STALE_EXECUTION"}
```

### 请求/响应 3

```http
POST /operations/start-control-exit/control HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 308

{"control_operation_id":"stop-current","action":"stop","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-control-exit","work_item_id":"work-control-exit","agent_run_id":"run-control-exit","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"}}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"accepted_at":"2026-09-13T06:43:10.759Z","execution":{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"},"identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"operation_id":"stop-current","start_operation_id":"start-control-exit","status":"accepted"}
```

### 请求/响应 4

```http
POST /operations/start-control-exit/control HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 308

{"control_operation_id":"stop-current","action":"stop","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-control-exit","work_item_id":"work-control-exit","agent_run_id":"run-control-exit","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"}}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"accepted_at":"2026-09-13T06:43:10.759Z","execution":{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"},"identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"operation_id":"stop-current","start_operation_id":"start-control-exit","status":"accepted"}
```

### 请求/响应 5

```http
GET /operations/start-control-exit HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:11 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 6

```http
GET /operations/start-control-exit HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:11 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 7

```http
GET /operations/start-control-exit HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:11 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"started","observed_at":"2026-09-13T06:43:10.738Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"running","receipt_id":"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e","source_digest":"099ed1d9fbc5608aa06d972e19d69a043733433a3c7e8a2ad482c5d57594ed39","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.738Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"running\",\"receipt_id\":\"ae6e73fda4edb900ed0d7f16e6a388d8f29565f72627889898dd43b6727b0d8e\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 8

```http
GET /operations/start-control-exit HTTP/1.1
Host: 127.0.0.1:63582
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:11 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"6e140d27f77d6b2e4ae723f39b0b3361c1764bfe4a55519ec220014db79cdee7","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"observation":{"environment_ref":"local-control-exit","identity":{"agent_run_id":"run-control-exit","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-control-exit","tenant_id":"tenant-p10","work_item_id":"work-control-exit"},"kind":"exited","observed_at":"2026-09-13T06:43:11.532Z","operation_id":"start-control-exit","pod_uid":"pod-control-exit","process":{"birth_id":"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:11.526Z","pid":23761,"started_at":"2026-09-13T06:43:10.712Z"},"reason":"exited","receipt_id":"14c40b338de95a16e6104812495fed776df1babc20f77735fb84ef7e601dc397","source_digest":"b235339ce4a8315e86ba468d606c6107496e0463bd40c4283b893b52713089b3","source_receipt":"{\"environment_ref\":\"local-control-exit\",\"identity\":{\"agent_run_id\":\"run-control-exit\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-control-exit\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-control-exit\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:11.532Z\",\"operation_id\":\"start-control-exit\",\"pod_uid\":\"pod-control-exit\",\"process\":{\"birth_id\":\"15295880fb0ae76774e72da7646ff3da8121b538c99a92f3c4471006cbbaf352:75cc58daeb29eb7302af26621ff2294ac144467a6651d2b5d81571c0661f7ca8:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:11.526Z\",\"pid\":23761,\"started_at\":\"2026-09-13T06:43:10.712Z\"},\"reason\":\"exited\",\"receipt_id\":\"14c40b338de95a16e6104812495fed776df1babc20f77735fb84ef7e601dc397\"}"},"operation_id":"start-control-exit","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-control-exit","pod_uid":"pod-control-exit","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-control-exit",
      "fixture_instance_id": "f5bccdad-f641-4900-94d6-e8954a974dce",
      "pid": 23761
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-control-exit",
      "fixture_instance_id": "f5bccdad-f641-4900-94d6-e8954a974dce",
      "pid": 23761,
      "ppid": 23739,
      "observed_at": "2026-09-13T06:43:10.754Z",
      "monotonic_ns": "406828512057708"
    },
    {
      "event": "exit",
      "operation_id": "start-control-exit",
      "fixture_instance_id": "f5bccdad-f641-4900-94d6-e8954a974dce",
      "pid": 23761,
      "ppid": 23739,
      "observed_at": "2026-09-13T06:43:11.523Z",
      "monotonic_ns": "406829280678083",
      "reason": "SIGTERM",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": []
}
```

## digest-conflict

漏洞点/验证点：同 operation 的不同 Assignment 摘要必须冲突拒绝。

### 请求/响应 1

```http
PUT /operations/start-digest-conflict HTTP/1.1
Host: 127.0.0.1:63580
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 804

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-digest-conflict","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-digest-conflict","work_item_id":"work-digest-conflict","agent_run_id":"run-digest-conflict","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-digest-conflict","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"fb2e72dc303efd4644e29d6903d92285154414edc377db1fcc78a51675e34303","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"observation":{"environment_ref":"local-digest-conflict","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"kind":"started","observed_at":"2026-09-13T06:43:10.452Z","operation_id":"start-digest-conflict","pod_uid":"pod-digest-conflict","process":{"birth_id":"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23737,"started_at":"2026-09-13T06:43:10.431Z"},"reason":"running","receipt_id":"7900f5f3cd1dbc21f71cbad62e348037444267810e01dcaef58d9874add10559","source_digest":"5ccc99a2d56d4f768a99c34552f35fa660eaab6ddb86de49bcf72e31e9dc1d8d","source_receipt":"{\"environment_ref\":\"local-digest-conflict\",\"identity\":{\"agent_run_id\":\"run-digest-conflict\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-digest-conflict\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-digest-conflict\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.452Z\",\"operation_id\":\"start-digest-conflict\",\"pod_uid\":\"pod-digest-conflict\",\"process\":{\"birth_id\":\"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23737,\"started_at\":\"2026-09-13T06:43:10.431Z\"},\"reason\":\"running\",\"receipt_id\":\"7900f5f3cd1dbc21f71cbad62e348037444267810e01dcaef58d9874add10559\"}"},"operation_id":"start-digest-conflict","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-digest-conflict","pod_uid":"pod-digest-conflict","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 2

```http
PUT /operations/start-digest-conflict HTTP/1.1
Host: 127.0.0.1:63580
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 800

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-digest-conflict","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-digest-conflict","work_item_id":"work-digest-conflict","agent_run_id":"run-digest-conflict","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-conflicting","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 409
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"code":"INPUT_DIGEST_CONFLICT"}
```

### 请求/响应 3

```http
GET /operations/start-digest-conflict HTTP/1.1
Host: 127.0.0.1:63580
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"fb2e72dc303efd4644e29d6903d92285154414edc377db1fcc78a51675e34303","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"observation":{"environment_ref":"local-digest-conflict","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"kind":"started","observed_at":"2026-09-13T06:43:10.452Z","operation_id":"start-digest-conflict","pod_uid":"pod-digest-conflict","process":{"birth_id":"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23737,"started_at":"2026-09-13T06:43:10.431Z"},"reason":"running","receipt_id":"7900f5f3cd1dbc21f71cbad62e348037444267810e01dcaef58d9874add10559","source_digest":"5ccc99a2d56d4f768a99c34552f35fa660eaab6ddb86de49bcf72e31e9dc1d8d","source_receipt":"{\"environment_ref\":\"local-digest-conflict\",\"identity\":{\"agent_run_id\":\"run-digest-conflict\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-digest-conflict\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-digest-conflict\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.452Z\",\"operation_id\":\"start-digest-conflict\",\"pod_uid\":\"pod-digest-conflict\",\"process\":{\"birth_id\":\"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23737,\"started_at\":\"2026-09-13T06:43:10.431Z\"},\"reason\":\"running\",\"receipt_id\":\"7900f5f3cd1dbc21f71cbad62e348037444267810e01dcaef58d9874add10559\"}"},"operation_id":"start-digest-conflict","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-digest-conflict","pod_uid":"pod-digest-conflict","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"running"}
```

### 请求/响应 4

```http
GET /operations/start-digest-conflict HTTP/1.1
Host: 127.0.0.1:63580
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"fb2e72dc303efd4644e29d6903d92285154414edc377db1fcc78a51675e34303","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"observation":{"environment_ref":"local-digest-conflict","identity":{"agent_run_id":"run-digest-conflict","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-digest-conflict","tenant_id":"tenant-p10","work_item_id":"work-digest-conflict"},"kind":"exited","observed_at":"2026-09-13T06:43:10.491Z","operation_id":"start-digest-conflict","pod_uid":"pod-digest-conflict","process":{"birth_id":"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:10.480Z","pid":23737,"started_at":"2026-09-13T06:43:10.431Z"},"reason":"exited","receipt_id":"1396677773a932f96e6a27e2245b46802f4d930f314217bf1ce20d69ae3e6338","source_digest":"1e457eabe03f62e113241c934a9407fd7b3577395a669206026ef12fc2ca8960","source_receipt":"{\"environment_ref\":\"local-digest-conflict\",\"identity\":{\"agent_run_id\":\"run-digest-conflict\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-digest-conflict\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-digest-conflict\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:10.491Z\",\"operation_id\":\"start-digest-conflict\",\"pod_uid\":\"pod-digest-conflict\",\"process\":{\"birth_id\":\"8382b6367cbb8fe478afd3736a926cac6f254e28938ac4a79cb8ee8b39b03508:84ec13239a10d30259bcada29ac39fdb0fc5a908d774dbac0bf440ccd14f44dd:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:10.480Z\",\"pid\":23737,\"started_at\":\"2026-09-13T06:43:10.431Z\"},\"reason\":\"exited\",\"receipt_id\":\"1396677773a932f96e6a27e2245b46802f4d930f314217bf1ce20d69ae3e6338\"}"},"operation_id":"start-digest-conflict","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-digest-conflict","pod_uid":"pod-digest-conflict","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-digest-conflict",
      "fixture_instance_id": "5847b9c0-cb95-468e-869d-974188dd848f",
      "pid": 23737
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-digest-conflict",
      "fixture_instance_id": "5847b9c0-cb95-468e-869d-974188dd848f",
      "pid": 23737,
      "ppid": 23736,
      "observed_at": "2026-09-13T06:43:10.466Z",
      "monotonic_ns": "406828224182333"
    },
    {
      "event": "exit",
      "operation_id": "start-digest-conflict",
      "fixture_instance_id": "5847b9c0-cb95-468e-869d-974188dd848f",
      "pid": 23737,
      "ppid": 23736,
      "observed_at": "2026-09-13T06:43:10.478Z",
      "monotonic_ns": "406828235578333",
      "reason": "release_file",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": []
}
```

## old-runtime

漏洞点/验证点：旧 runtime_attempt 必须在 spawn 前拒绝。

### 请求/响应 1

```http
PUT /operations/start-old-runtime HTTP/1.1
Host: 127.0.0.1:63578
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 784

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-old-runtime","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-old-runtime","work_item_id":"work-old-runtime","agent_run_id":"run-old-runtime","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-old-runtime","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 409
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"code":"STALE_EXECUTION"}
```

### 请求/响应 2

```http
PUT /operations/start-old-runtime HTTP/1.1
Host: 127.0.0.1:63578
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 784

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-old-runtime","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-old-runtime","work_item_id":"work-old-runtime","agent_run_id":"run-old-runtime","execution_epoch":"1","run_epoch":"1","runtime_attempt":"2","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-old-runtime","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"e750d4fd7aca976a944abb9f5df29e19bb35173fdc10c1082a0e48e06c2ab6bf","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"observation":{"environment_ref":"local-old-runtime","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"kind":"started","observed_at":"2026-09-13T06:43:10.176Z","operation_id":"start-old-runtime","pod_uid":"pod-old-runtime","process":{"birth_id":"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23733,"started_at":"2026-09-13T06:43:10.156Z"},"reason":"running","receipt_id":"32c7d4dc1c315d0ccde1dd5c604d5dfec3e61f33b4777bc566800ac2f455c204","source_digest":"5eddfeadca4a7f592cc24eb5c7879f91a5fdd8a3777bb4a1f7e6a2c8d7c1e200","source_receipt":"{\"environment_ref\":\"local-old-runtime\",\"identity\":{\"agent_run_id\":\"run-old-runtime\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"2\",\"task_id\":\"task-old-runtime\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-old-runtime\"},\"kind\":\"started\",\"observed_at\":\"2026-09-13T06:43:10.176Z\",\"operation_id\":\"start-old-runtime\",\"pod_uid\":\"pod-old-runtime\",\"process\":{\"birth_id\":\"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23733,\"started_at\":\"2026-09-13T06:43:10.156Z\"},\"reason\":\"running\",\"receipt_id\":\"32c7d4dc1c315d0ccde1dd5c604d5dfec3e61f33b4777bc566800ac2f455c204\"}"},"operation_id":"start-old-runtime","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-old-runtime","pod_uid":"pod-old-runtime","receiver_id":"receiver-p10","runtime_attempt":"2"},"state":"running"}
```

### 请求/响应 3

```http
GET /operations/start-old-runtime HTTP/1.1
Host: 127.0.0.1:63578
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"e750d4fd7aca976a944abb9f5df29e19bb35173fdc10c1082a0e48e06c2ab6bf","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"observation":{"environment_ref":"local-old-runtime","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"kind":"unknown","observed_at":"2026-09-13T06:43:10.216Z","operation_id":"start-old-runtime","pod_uid":"pod-old-runtime","process":{"birth_id":"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event","exit_code":null,"exited_at":null,"pid":23733,"started_at":"2026-09-13T06:43:10.156Z"},"reason":"process_truth_unresolved","receipt_id":"5440f10a22aa13df46d25380948a693ad5b16a35a65684ef5ab59175940e4774","source_digest":"b1654e8b8cd1605f12e3c50a3e1d8e0de87f28b8acb6ef3dd85f5f93ca587f22","source_receipt":"{\"environment_ref\":\"local-old-runtime\",\"identity\":{\"agent_run_id\":\"run-old-runtime\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"2\",\"task_id\":\"task-old-runtime\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-old-runtime\"},\"kind\":\"unknown\",\"observed_at\":\"2026-09-13T06:43:10.216Z\",\"operation_id\":\"start-old-runtime\",\"pod_uid\":\"pod-old-runtime\",\"process\":{\"birth_id\":\"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event\",\"exit_code\":null,\"exited_at\":null,\"pid\":23733,\"started_at\":\"2026-09-13T06:43:10.156Z\"},\"reason\":\"process_truth_unresolved\",\"receipt_id\":\"5440f10a22aa13df46d25380948a693ad5b16a35a65684ef5ab59175940e4774\"}"},"operation_id":"start-old-runtime","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-old-runtime","pod_uid":"pod-old-runtime","receiver_id":"receiver-p10","runtime_attempt":"2"},"state":"unknown"}
```

### 请求/响应 4

```http
GET /operations/start-old-runtime HTTP/1.1
Host: 127.0.0.1:63578
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:10 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"e750d4fd7aca976a944abb9f5df29e19bb35173fdc10c1082a0e48e06c2ab6bf","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"observation":{"environment_ref":"local-old-runtime","identity":{"agent_run_id":"run-old-runtime","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"2","task_id":"task-old-runtime","tenant_id":"tenant-p10","work_item_id":"work-old-runtime"},"kind":"exited","observed_at":"2026-09-13T06:43:10.232Z","operation_id":"start-old-runtime","pod_uid":"pod-old-runtime","process":{"birth_id":"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event","exit_code":0,"exited_at":"2026-09-13T06:43:10.206Z","pid":23733,"started_at":"2026-09-13T06:43:10.156Z"},"reason":"exited","receipt_id":"c3613c40d449ab1ad28a41e70de853d7fe4d8bab81614f4eb3332076580a7d16","source_digest":"c75610983bf93f1e63422518be603d29383fe8975ba081d657030c81a272deaf","source_receipt":"{\"environment_ref\":\"local-old-runtime\",\"identity\":{\"agent_run_id\":\"run-old-runtime\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"2\",\"task_id\":\"task-old-runtime\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-old-runtime\"},\"kind\":\"exited\",\"observed_at\":\"2026-09-13T06:43:10.232Z\",\"operation_id\":\"start-old-runtime\",\"pod_uid\":\"pod-old-runtime\",\"process\":{\"birth_id\":\"cac0264af474d6b5e451dff232a4b43593f78122621a8118e40f7c227e9309b2:3d7f02443956dda58b0ce8b609b69209997e919879625276f492e4c73bb16325:child-process-spawn-event\",\"exit_code\":0,\"exited_at\":\"2026-09-13T06:43:10.206Z\",\"pid\":23733,\"started_at\":\"2026-09-13T06:43:10.156Z\"},\"reason\":\"exited\",\"receipt_id\":\"c3613c40d449ab1ad28a41e70de853d7fe4d8bab81614f4eb3332076580a7d16\"}"},"operation_id":"start-old-runtime","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-old-runtime","pod_uid":"pod-old-runtime","receiver_id":"receiver-p10","runtime_attempt":"2"},"state":"exited"}
```

实际进程证据：

```json
{
  "actual_starts": [
    {
      "operation_id": "start-old-runtime",
      "fixture_instance_id": "c19948cc-123a-4de2-a306-2f3b18c310c2",
      "pid": 23733
    }
  ],
  "child_lifecycle": [
    {
      "event": "birth",
      "operation_id": "start-old-runtime",
      "fixture_instance_id": "c19948cc-123a-4de2-a306-2f3b18c310c2",
      "pid": 23733,
      "ppid": 23732,
      "observed_at": "2026-09-13T06:43:10.192Z",
      "monotonic_ns": "406827949659333"
    },
    {
      "event": "exit",
      "operation_id": "start-old-runtime",
      "fixture_instance_id": "c19948cc-123a-4de2-a306-2f3b18c310c2",
      "pid": 23733,
      "ppid": 23732,
      "observed_at": "2026-09-13T06:43:10.204Z",
      "monotonic_ns": "406827961592666",
      "reason": "release_file",
      "exit_code": 0
    }
  ],
  "supervisor_crashes": []
}
```

## prepared-before-spawn

漏洞点/验证点：prepared 已持久化但无可信未启动证明时必须 unknown，不能盲目 spawn。

### 请求/响应 1

```http
PUT /operations/start-prepared-before-spawn HTTP/1.1
Host: 127.0.0.1:63557
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 834

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-prepared-before-spawn","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-prepared-before-spawn","work_item_id":"work-prepared-before-spawn","agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-prepared-before-spawn","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```text
<connection closed by injected Supervisor SIGKILL>
TypeError: fetch failed
```

### 请求/响应 2

```http
GET /operations/start-prepared-before-spawn HTTP/1.1
Host: 127.0.0.1:63559
Accept: application/json
Authorization: Bearer p10-test-controller-token


```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:08 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"06ea33eb3eaa20fbca1392569d90ddb2707bfce4385e90699187b7130fcbdd13","identity":{"agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-prepared-before-spawn","tenant_id":"tenant-p10","work_item_id":"work-prepared-before-spawn"},"observation":{"environment_ref":"local-prepared-before-spawn","identity":{"agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-prepared-before-spawn","tenant_id":"tenant-p10","work_item_id":"work-prepared-before-spawn"},"kind":"unknown","observed_at":"2026-09-13T06:43:08.807Z","operation_id":"start-prepared-before-spawn","pod_uid":"pod-prepared-before-spawn","process":null,"reason":"process_truth_unresolved","receipt_id":"26c7cbb0df5b0b16bc5509dc6cd1f57dc3602c707e1b8a50c9f307b739eaacb4","source_digest":"397d813963417b018a9b64da89e076786c495fe143bd5cce3ea2d85237aae27a","source_receipt":"{\"environment_ref\":\"local-prepared-before-spawn\",\"identity\":{\"agent_run_id\":\"run-prepared-before-spawn\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-prepared-before-spawn\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-prepared-before-spawn\"},\"kind\":\"unknown\",\"observed_at\":\"2026-09-13T06:43:08.807Z\",\"operation_id\":\"start-prepared-before-spawn\",\"pod_uid\":\"pod-prepared-before-spawn\",\"process\":null,\"reason\":\"process_truth_unresolved\",\"receipt_id\":\"26c7cbb0df5b0b16bc5509dc6cd1f57dc3602c707e1b8a50c9f307b739eaacb4\"}"},"operation_id":"start-prepared-before-spawn","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-prepared-before-spawn","pod_uid":"pod-prepared-before-spawn","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"unknown"}
```

### 请求/响应 3

```http
PUT /operations/start-prepared-before-spawn HTTP/1.1
Host: 127.0.0.1:63559
Accept: application/json
Authorization: Bearer p10-test-controller-token
Content-Type: application/json
Content-Length: 834

{"assignment":{"schema_version":"wuji.assignment.v2","operation_id":"start-prepared-before-spawn","identity":{"tenant_id":"tenant-p10","project_id":"project-p10","task_id":"task-prepared-before-spawn","work_item_id":"work-prepared-before-spawn","agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","run_epoch":"1","runtime_attempt":"1","receiver_id":"receiver-p10"},"work_kind":"explore","snapshot_id":"snapshot-prepared-before-spawn","profile_refs":["harmless-node-v1"],"session_manifest_ref":null,"tool_definition_refs":["read_record:v1"],"limits":{"max_work_items":4,"max_reason_runs":1,"max_model_requests":2,"max_tool_calls":2,"max_single_output_bytes":65536,"max_total_output_bytes":131072,"max_elapsed_seconds":30,"max_attempts_per_work":1,"repair_attempts":0},"resume_reason":null},"profile_id":"harmless-node-v1"}
```

```http
HTTP/1.1 200
cache-control: no-store
connection: keep-alive
content-type: application/json
date: Sun, 13 Sep 2026 06:43:08 GMT
keep-alive: timeout=5
transfer-encoding: chunked

{"assignment_digest":"06ea33eb3eaa20fbca1392569d90ddb2707bfce4385e90699187b7130fcbdd13","identity":{"agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-prepared-before-spawn","tenant_id":"tenant-p10","work_item_id":"work-prepared-before-spawn"},"observation":{"environment_ref":"local-prepared-before-spawn","identity":{"agent_run_id":"run-prepared-before-spawn","execution_epoch":"1","project_id":"project-p10","receiver_id":"receiver-p10","run_epoch":"1","runtime_attempt":"1","task_id":"task-prepared-before-spawn","tenant_id":"tenant-p10","work_item_id":"work-prepared-before-spawn"},"kind":"unknown","observed_at":"2026-09-13T06:43:08.807Z","operation_id":"start-prepared-before-spawn","pod_uid":"pod-prepared-before-spawn","process":null,"reason":"process_truth_unresolved","receipt_id":"26c7cbb0df5b0b16bc5509dc6cd1f57dc3602c707e1b8a50c9f307b739eaacb4","source_digest":"397d813963417b018a9b64da89e076786c495fe143bd5cce3ea2d85237aae27a","source_receipt":"{\"environment_ref\":\"local-prepared-before-spawn\",\"identity\":{\"agent_run_id\":\"run-prepared-before-spawn\",\"execution_epoch\":\"1\",\"project_id\":\"project-p10\",\"receiver_id\":\"receiver-p10\",\"run_epoch\":\"1\",\"runtime_attempt\":\"1\",\"task_id\":\"task-prepared-before-spawn\",\"tenant_id\":\"tenant-p10\",\"work_item_id\":\"work-prepared-before-spawn\"},\"kind\":\"unknown\",\"observed_at\":\"2026-09-13T06:43:08.807Z\",\"operation_id\":\"start-prepared-before-spawn\",\"pod_uid\":\"pod-prepared-before-spawn\",\"process\":null,\"reason\":\"process_truth_unresolved\",\"receipt_id\":\"26c7cbb0df5b0b16bc5509dc6cd1f57dc3602c707e1b8a50c9f307b739eaacb4\"}"},"operation_id":"start-prepared-before-spawn","profile_id":"harmless-node-v1","receiver":{"environment_ref":"local-prepared-before-spawn","pod_uid":"pod-prepared-before-spawn","receiver_id":"receiver-p10","runtime_attempt":"1"},"state":"unknown"}
```

实际进程证据：

```json
{
  "actual_starts": [],
  "child_lifecycle": [],
  "supervisor_crashes": [
    {
      "window": "after_prepared_before_spawn",
      "operation_id": "start-prepared-before-spawn",
      "pid": 23588
    }
  ]
}
```
