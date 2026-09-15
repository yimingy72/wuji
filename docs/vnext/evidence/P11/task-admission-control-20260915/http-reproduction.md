# P11-C control commands HTTP reproduction

Packets were sent to the isolated runtime control API through
`kubectl port-forward svc/runtime 18444:8443` with the deployment CA. The bearer is a freshly minted
operator token (issuer `https://identity.wuji-vnext-test.invalid`, audience `wuji-vnext-deployment`,
15 minute lifetime) and is redacted. Task `e51cee17-bc3c-4239-a2a2-8e185d4b34a6` was created by the
previous increment and admitted by `Job/p11c-task-admission2`.

## start

```http
POST /api/v2/tasks/e51cee17-bc3c-4239-a2a2-8e185d4b34a6/commands HTTP/1.1
Authorization: Bearer [REDACTED operator]
Content-Type: application/json
Idempotency-Key: p11c-start-1

{"schema_version":"wuji.api.v2","command":"start","expected_version":"1","reason":"P11-C K8s start probe"}
```

```http
HTTP/1.1 202 Accepted

{"command_id":"p11c-start-1","disposition":"accepted","resource_ref":{"entity_type":"task","id":"e51cee17-bc3c-4239-a2a2-8e185d4b34a6","revision":"2"},"resource_version":"2","request_id":"55040ffc-baaa-49e8-8201-339e6f1e2ea6","code":null}
```

## replay and stale version

```http
POST /api/v2/tasks/{id}/commands  (same Idempotency-Key, same body)
HTTP/1.1 202 Accepted   -> identical receipt

POST /api/v2/tasks/{id}/commands  (Idempotency-Key: p11c-start-2, expected_version 1)
HTTP/1.1 409 Conflict

{"code":"STALE_VERSION","message":"The request could not be completed.","request_id":"2305073f-15a4-4e11-9329-adde47301af8","retryable":false,"details":{}}
```

## pause and cancel

```http
POST /api/v2/tasks/{id}/commands  {"command":"pause","expected_version":"2",…}  -> 202, resource_version 3
POST /api/v2/tasks/{id}/commands  {"command":"cancel","expected_version":"3",…} -> 202, resource_version 4
```

```http
{"command_id":"p11c-cancel-1","disposition":"accepted","resource_ref":{"entity_type":"task","id":"e51cee17-bc3c-4239-a2a2-8e185d4b34a6","revision":"4"},"resource_version":"4","request_id":"8853cff8-897b-43a7-9343-6a56e4eaf56b","code":null}
```

The Task then reads `desired_state=cancel`, `observed_state=quiescing`, `execution_allowed=false`,
`execution_epoch=4`, `close_trigger=user_cancel`; `vnext.agent_run` has **0** rows for the Task, so no
process was running and no stop was observed.
