# P15 snapshot-bound record HTTP reproduction

Requests were captured through `Service/wuji-web` at `127.0.0.1:44180`. The HttpOnly cookie is redacted as a credential; all paths, query values, non-secret headers and response bodies are complete.

## login

Request:

```http
POST /auth/login HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-record-detail-verifier/1.0
Origin: http://127.0.0.1:44180
Accept: application/json
Content-Length: 0
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:56:29 GMT
Content-Type: application/json
Content-Length: 253
Connection: keep-alive
cache-control: no-store
set-cookie: wuji_vnext_session=[REDACTED]; HttpOnly; Max-Age=1800; Path=/; SameSite=strict

{"authenticated":true,"display_name":"Local Kubernetes operator","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","expires_at":"2026-09-15T03:26:29Z"}
```

## topology

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/topology?mode=live&node_limit=1000&edge_limit=2000 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-record-detail-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:56:30 GMT
Content-Type: application/json
Content-Length: 1009
Connection: keep-alive
cache-control: no-store
x-request-id: 6d48d861-4755-46c8-bcc0-fc49761a31d5

{"view_id":"c9005da6-a8c2-4965-b40c-7cc124e83238","snapshot_id":"529f4925-e163-47dc-8d47-73e70d8d9994","view_revision":"1","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","access_scope_digest":"975495938722b0b12b176950c2a11fa90f75b1ad73f6107c3053e3c5e8bec247","projection_version":"wuji.topology.v1","nodes":[{"id":"intent:778ac2ff-d006-4764-a11f-9f3e83473ade@1","ref":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"display_kind":"intent","label":"Read version.txt once through the registered Kali workspace tool.","state":"admitted","allowed_actions":[]},{"id":"origin:a41a59ed-29e1-4801-b68b-dfea395eae30@1","ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","label":"C2 isolated Kali workspace read","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"Jl8uu7PQo9ayY43K0xVaEmy-HdLaNVRm1l1XrAbmIVw","truncated":false,"continuation":null,"allowed_actions":[]}
```

## intent

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/records/intent/778ac2ff-d006-4764-a11f-9f3e83473ade?revision=1&snapshot_id=529f4925-e163-47dc-8d47-73e70d8d9994 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-record-detail-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:56:30 GMT
Content-Type: application/json
Content-Length: 469
Connection: keep-alive
cache-control: no-store
x-request-id: 6ac5ef82-38d9-4083-a481-411cef38b52d

{"assessment":null,"ref":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"display_kind":"intent","record":{"intent_id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","question":"Read version.txt once through the registered Kali workspace tool.","basis_refs":[],"expected_output":"wuji.agent-payload.v2","acceptance_state":"admitted","created_at":"2026-09-15T01:14:38.172239Z"}}
```

## origin

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/records/origin/a41a59ed-29e1-4801-b68b-dfea395eae30?revision=1&snapshot_id=529f4925-e163-47dc-8d47-73e70d8d9994 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-record-detail-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:56:30 GMT
Content-Type: application/json
Content-Length: 550
Connection: keep-alive
cache-control: no-store
x-request-id: 42167faf-4df2-4d8c-b7f1-58b73b2cf49b

{"assessment":null,"ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","record":{"task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","version":"1","name":"C2 isolated Kali workspace read","scenario":"web_single","desired_state":"pause","observed_state":"ready","goal_revision":"1","execution_epoch":"1","activated_at":null,"close_trigger":null,"result_outcome":null,"allowed_actions":[]}}
```
