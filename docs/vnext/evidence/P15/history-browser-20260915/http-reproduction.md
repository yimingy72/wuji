# P15 historical snapshot HTTP reproduction

Captured through the Kubernetes Web gateway at `127.0.0.1:44180`. The HttpOnly cookie is redacted; paths, opaque identifiers, non-secret headers and bodies are complete.

## login

Request:

```http
POST /auth/login HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-history-verifier/1.0
Origin: http://127.0.0.1:44180
Accept: application/json
Content-Length: 0
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:07:25 GMT
Content-Type: application/json
Content-Length: 253
Connection: keep-alive
cache-control: no-store
set-cookie: wuji_vnext_session=[REDACTED]; HttpOnly; Max-Age=1800; Path=/; SameSite=strict

{"authenticated":true,"display_name":"Local Kubernetes operator","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","expires_at":"2026-09-15T03:37:25Z"}
```

## snapshots

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/snapshots HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-history-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:07:25 GMT
Content-Type: application/json
Content-Length: 2706
Connection: keep-alive
cache-control: no-store
x-request-id: adae2412-309c-49f2-8b38-31d484bea11c

{"items":[{"snapshot_id":"56b5e838-11b7-4b29-9dd5-70ef2e5f9e8f","view_id":"4a07564c-a8b9-4011-bb91-44e0fef86a94","view_revision":"1","created_at":"2026-09-15T03:05:45.890802Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"b06e7af3-55f6-415f-a76f-99cec2e6f4f9","view_id":"e823ffb5-4e94-4455-8905-d1073986b7f1","view_revision":"1","created_at":"2026-09-15T03:05:27.806981Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"529f4925-e163-47dc-8d47-73e70d8d9994","view_id":"c9005da6-a8c2-4965-b40c-7cc124e83238","view_revision":"1","created_at":"2026-09-15T02:56:30.110681Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"bc6e604d-dbf4-4217-a52b-e4a31d24c983","view_id":"9c030ecb-e256-409b-9f5f-b6bc6d173d6f","view_revision":"1","created_at":"2026-09-15T02:54:15.911556Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"d9563f86-386b-48fc-a201-76a1ca40b51d","view_id":"72cd10ff-76a4-4376-b701-ed537941c2b3","view_revision":"1","created_at":"2026-09-15T02:48:05.268010Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"98d12aee-c110-45ae-a147-f2987dc6ea0b","view_id":"8252558d-a21c-4d26-9c49-e95bd227b62b","view_revision":"1","created_at":"2026-09-15T02:37:46.722894Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}},{"snapshot_id":"4d28297b-4022-4c38-a624-12ec5c6c7f8a","view_id":"14c8f3f5-7350-45c7-bb42-b832c3eecc45","view_revision":"1","created_at":"2026-09-15T02:36:32.127913Z","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","projection_version":"wuji.topology.v1","query":{"mode":"live","snapshot_id":null,"cursor":null,"node_limit":1000,"edge_limit":2000}}],"opaque_cursor":null}
```

## history

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/topology?mode=history&snapshot_id=529f4925-e163-47dc-8d47-73e70d8d9994&node_limit=1000&edge_limit=2000 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-history-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:07:25 GMT
Content-Type: application/json
Content-Length: 1009
Connection: keep-alive
cache-control: no-store
x-request-id: 6272d9ae-bf28-4405-a88e-b9412e261457

{"view_id":"a1763a5a-1708-4415-a9ee-e03a3eedaa95","snapshot_id":"529f4925-e163-47dc-8d47-73e70d8d9994","view_revision":"1","query_digest":"92cda42e22e5664ebfbd56f88c71adcb75b2da8854f7fc78046d1ca1dab32c10","access_scope_digest":"975495938722b0b12b176950c2a11fa90f75b1ad73f6107c3053e3c5e8bec247","projection_version":"wuji.topology.v1","nodes":[{"id":"intent:778ac2ff-d006-4764-a11f-9f3e83473ade@1","ref":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"display_kind":"intent","label":"Read version.txt once through the registered Kali workspace tool.","state":"admitted","allowed_actions":[]},{"id":"origin:a41a59ed-29e1-4801-b68b-dfea395eae30@1","ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","label":"C2 isolated Kali workspace read","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"7ZslQqsve3yrHbHkquMFide8SFUz_EyHLHygmSceAQs","truncated":false,"continuation":null,"allowed_actions":[]}
```

## record

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/records/origin/a41a59ed-29e1-4801-b68b-dfea395eae30?revision=1&snapshot_id=529f4925-e163-47dc-8d47-73e70d8d9994 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-history-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:07:26 GMT
Content-Type: application/json
Content-Length: 550
Connection: keep-alive
cache-control: no-store
x-request-id: b31d1c70-b736-4e0f-b3ab-dd1c78d8c84b

{"assessment":null,"ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","record":{"task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","version":"1","name":"C2 isolated Kali workspace read","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}}
```
