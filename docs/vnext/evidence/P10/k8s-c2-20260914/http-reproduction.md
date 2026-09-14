# Complete HTTP reproduction packets

The following packets use the exact request bodies and response bodies from the run. Authorization values are redacted because the original bearer is a deployment secret; a reproduction must use a newly issued test token for the same isolated tenant and task. No target system was contacted.

## 1. Start the Task

```http
POST /api/v2/tasks/2032601e-79ac-4e5d-bc5f-7a33620e3659/commands HTTP/1.1
Host: 127.0.0.1:18443
Authorization: Bearer [REDACTED FRESH4 TEST TOKEN]
Content-Type: application/json
Accept: application/json
Idempotency-Key: c2-fresh6-start-20260914-1

{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"Start isolated synthetic C2 deployment task"}
```

```http
HTTP/1.1 202 Accepted
content-type: application/json
x-request-id: 7f65920b-20b8-427c-ba8f-7add0ccbde4f

{"command_id":"c2-fresh6-start-20260914-1","disposition":"accepted","resource_ref":{"entity_type":"task","id":"2032601e-79ac-4e5d-bc5f-7a33620e3659","revision":"2"},"resource_version":"2","request_id":"7f65920b-20b8-427c-ba8f-7add0ccbde4f","code":null}
```

## 2. ModelGate request/response

There were four successful model requests (`200`, SSE, 622/977-byte durable response bodies). The exact durable request bodies are in `raw/model-1-request.json` through `raw/model-4-request.json`; the exact SSE bodies are in `raw/model-response-1.sse` through `raw/model-response-4.sse`.

```http
POST /internal/v2/model/chat/completions HTTP/1.1
Host: gates.wuji-vnext-test.svc:8443
Authorization: Bearer [REDACTED RUN CREDENTIAL]
Content-Type: application/json
Accept: text/event-stream
X-Wuji-Request-ID: [RECORDED PER-REQUEST ID]

[exact body in raw/model-N-request.json]
```

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
X-Wuji-Model-Attempt-ID: [DURABLE MODEL ATTEMPT ID]

[exact body in raw/model-response-N.sse]
```

## 3. ToolGate request/response

Two ToolGate calls returned complete durable evidence. Exact request and response bodies are in `raw/tool-1-request.json`, `raw/tool-1-receipt.json`, `raw/tool-2-request.json`, and `raw/tool-2-receipt.json`.

```http
POST /internal/v2/tool-calls HTTP/1.1
Host: gates.wuji-vnext-test.svc:8443
Authorization: Bearer [REDACTED RUN CREDENTIAL]
Content-Type: application/json
Accept: application/json

[exact body in raw/tool-N-request.json]
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

[exact body in raw/tool-N-receipt.json]
```

The receipt is bound to the exact `tool_attempt_id`, `receiver_id`, `environment_ref`, argument digest, 19 output bytes and SHA-256. The downstream result packets are in `raw/result-1-envelope.json`/`raw/result-1-receipt.json` and `raw/result-2-envelope.json`/`raw/result-2-receipt.json`.

## 4. Cancel and formal cleanup

```http
POST /api/v2/tasks/2032601e-79ac-4e5d-bc5f-7a33620e3659/commands HTTP/1.1
Host: 127.0.0.1:18443
Authorization: Bearer [REDACTED FRESH6 TEST TOKEN]
Content-Type: application/json
Accept: application/json
Idempotency-Key: c2-fresh6-cancel-20260914-1

{"schema_version":"wuji.api.v2","command":"cancel","expected_version":"2","reason":"End isolated C2 mechanism run after evidence capture"}
```

```http
HTTP/1.1 202 Accepted
content-type: application/json
x-request-id: 931d3f90-60d3-44bc-af67-3489ad6ef6e4

{"command_id":"c2-fresh6-cancel-20260914-1","disposition":"accepted","resource_ref":{"entity_type":"task","id":"2032601e-79ac-4e5d-bc5f-7a33620e3659","revision":"3"},"resource_version":"3","request_id":"931d3f90-60d3-44bc-af67-3489ad6ef6e4","code":null}
```

The packets above are the public control requests. Database and Pod event evidence for internal requests is retained in `raw/final-db-state.stdout`, `raw/task-pod.json`, and `raw/task-events.stdout`.
