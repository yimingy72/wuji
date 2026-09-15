# P11-C Task creation HTTP reproduction

All packets were sent to the isolated public API through `kubectl port-forward svc/api 18443:8443`
with the deployment CA (`ConfigMap/api-config` `ca.crt`). Tokens are credentials: the minted operator
bearer is redacted; the code revision, tenant and Task are complete. The browser entry at
`127.0.0.1:44180` deliberately does not proxy this route (see the last exchange).

## anonymous create

```http
POST /api/v2/tasks HTTP/1.1
Host: api.wuji-vnext-test.svc
Content-Type: application/json
Idempotency-Key: k-anon

{"schema_version":"wuji.api.v2"}
```

```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"code":"UNAUTHENTICATED","message":"A valid bearer token is required.","request_id":"af5582e2-dd9b-49a5-b06c-a127f7321f9e","retryable":false,"details":{}}
```

## create a non-running task

```http
POST /api/v2/tasks HTTP/1.1
Host: api.wuji-vnext-test.svc
Authorization: Bearer [REDACTED operator, iss=https://identity.wuji-vnext-test.invalid, aud=wuji-vnext-deployment, exp=+900s]
Content-Type: application/json
Idempotency-Key: p11c-k8s-2

{"schema_version":"wuji.api.v2","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","name":"P11-C K8s creation probe","scenario":"web_single","goal":{"text":"Read the isolated workspace version file","criteria":[{"criterion_id":"version","object":"fixture bytes","condition":"version captured","evidence_requirements":["sealed bytes"],"allowed_methods":["deterministic"],"responsible_party":"fixture-checker","required":true}]},"authorization_scope":[{"host":"fixture.invalid","protocol":"https","port":443}],"authorization_expires_at":"2099-01-01T00:00:00Z","model_profile_ref":"k8s-model-v1","runtime_profile_ref":"k8s-runtime-v1","budget":{"amount":"1","currency":"USD"}}
```

```http
HTTP/1.1 201 Created
content-type: application/json
x-request-id: 0f1f4a8b-… 

{"task_id":"e51cee17-bc3c-4239-a2a2-8e185d4b34a6","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","version":"1","name":"P11-C K8s creation probe","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}
```

## idempotent replay

The identical request (same `Idempotency-Key`, same body) returns `201` again with the same
`task_id` and creates no second Task.

```http
HTTP/1.1 201 Created

{"task_id":"e51cee17-bc3c-4239-a2a2-8e185d4b34a6", …}
```

## the same key with a different body

```http
POST /api/v2/tasks HTTP/1.1
Idempotency-Key: p11c-k8s-2

{ … "name": "Conflicting body" … }
```

```http
HTTP/1.1 409 Conflict

{"code":"INPUT_DIGEST_CONFLICT","message":"The request could not be completed.","request_id":"324a8fb0-9e2e-45c4-be9f-526abcaa2c88","retryable":false,"details":{}}
```

## browser entry keeps this route closed

```http
POST /api/v2/tasks HTTP/1.1
Host: 127.0.0.1:44180
Content-Type: application/json
Idempotency-Key: k-anon

{"schema_version":"wuji.api.v2"}
```

```http
HTTP/1.1 405 Method Not Allowed

{"detail":"Method Not Allowed"}
```

The gateway answers from its own route table and never forwards the request; exposing task creation
to the browser needs the P11 identity/CSRF design and is not part of this slice.
