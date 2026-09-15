# P13 public API Kubernetes reproduction

The following packets were captured through a local `kubectl port-forward` to the running `api` Service. The bearer value is deliberately redacted in the request copy; the response bodies are complete.

## Authenticated live topology

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
Host: api.wuji-vnext-test.svc:18444
Authorization: Bearer [REDACTED]
Accept: application/json

```

Response headers:

```http
HTTP/1.1 200 OK
date: Tue, 15 Sep 2026 01:39:16 GMT
server: uvicorn
cache-control: no-store
content-length: 1009
content-type: application/json
x-request-id: c5266938-dc52-4110-8dba-e97e53db4f7f

```

Response body:

```json
{"view_id":"f369a9f1-0ddc-43fa-9117-6e08633cc866","snapshot_id":"ca955fa4-9708-4cd2-a9eb-3e5f923a8814","view_revision":"1","query_digest":"a831200899924e700596f69f121950e80a8a5bd3562753355e2bcc949b5eb5cf","access_scope_digest":"975495938722b0b12b176950c2a11fa90f75b1ad73f6107c3053e3c5e8bec247","projection_version":"wuji.topology.v1","nodes":[{"id":"intent:778ac2ff-d006-4764-a11f-9f3e83473ade@1","ref":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"display_kind":"intent","label":"Read version.txt once through the registered Kali workspace tool.","state":"admitted","allowed_actions":[]},{"id":"origin:a41a59ed-29e1-4801-b68b-dfea395eae30@1","ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","label":"C2 isolated Kali workspace read","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"GnqRzjuRyYmI8_43qhU62gS0ILGQAagxvcCySE8U68A","truncated":false,"continuation":null,"allowed_actions":[]}```

## Missing bearer negative case

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/topology?mode=live&node_limit=300&edge_limit=600 HTTP/1.1
Host: api.wuji-vnext-test.svc:18444
Accept: application/json

```

Response headers:

```http
HTTP/1.1 401 Unauthorized
date: Tue, 15 Sep 2026 01:54:17 GMT
server: uvicorn
content-type: application/json
content-length: 155
x-request-id: 61e10aa4-1cdf-4258-a6f5-8d0a58242769

```

Response body:

```json
{"code":"UNAUTHENTICATED","message":"A valid bearer token is required.","request_id":"61e10aa4-1cdf-4258-a6f5-8d0a58242769","retryable":false,"details":{}}
```

The auth boundary is the relevant negative result: the route does not treat an anonymous browser request as a valid projection reader.
