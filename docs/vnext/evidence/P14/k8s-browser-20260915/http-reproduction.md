# P14 browser workbench HTTP reproduction

These packets were captured through the Kubernetes `wuji-web` Service at `127.0.0.1:44180`. Cookie values are redacted because they are authentication credentials; methods, paths, non-secret headers, bodies and response bodies are otherwise complete.

## anonymous

Request:

```http
GET /auth/session HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Accept: */*
```

Response:

```http
HTTP/1.1 401 Unauthorized
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:31 GMT
Content-Type: application/json
Content-Length: 152
Connection: keep-alive
cache-control: no-store

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"5a928dee-97bc-4a59-84c3-2436af07155d","retryable":false,"details":{}}
```

## login

Request:

```http
POST /auth/login HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Origin: http://127.0.0.1:44180
Accept: application/json
Content-Length: 0
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:31 GMT
Content-Type: application/json
Content-Length: 253
Connection: keep-alive
cache-control: no-store
set-cookie: wuji_vnext_session=[REDACTED]; HttpOnly; Max-Age=1800; Path=/; SameSite=strict

{"authenticated":true,"display_name":"Local Kubernetes operator","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","expires_at":"2026-09-15T03:06:31Z"}
```

## session

Request:

```http
GET /auth/session HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:31 GMT
Content-Type: application/json
Content-Length: 253
Connection: keep-alive
cache-control: no-store

{"authenticated":true,"display_name":"Local Kubernetes operator","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","expires_at":"2026-09-15T03:06:31Z"}
```

## topology

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/topology?mode=live&node_limit=1000&edge_limit=2000 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:32 GMT
Content-Type: application/json
Content-Length: 1009
Connection: keep-alive
cache-control: no-store
x-request-id: 1fbc7cae-fc01-463d-9da0-022c5857fbca

{"view_id":"14c8f3f5-7350-45c7-bb42-b832c3eecc45","snapshot_id":"4d28297b-4022-4c38-a624-12ec5c6c7f8a","view_revision":"1","query_digest":"de12cb7f737c068e06fc19ef2f41d757e2c20ba0fceaca58503dfb5f1aa45718","access_scope_digest":"975495938722b0b12b176950c2a11fa90f75b1ad73f6107c3053e3c5e8bec247","projection_version":"wuji.topology.v1","nodes":[{"id":"intent:778ac2ff-d006-4764-a11f-9f3e83473ade@1","ref":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"display_kind":"intent","label":"Read version.txt once through the registered Kali workspace tool.","state":"admitted","allowed_actions":[]},{"id":"origin:a41a59ed-29e1-4801-b68b-dfea395eae30@1","ref":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":"1"},"display_kind":"origin","label":"C2 isolated Kali workspace read","state":"ready","allowed_actions":[]}],"edges":[],"opaque_cursor":"oH7ZIL6-MOHmUvXFw_Pc2fMHkG-AKuBUY-lS4F4qInk","truncated":false,"continuation":null,"allowed_actions":[]}
```

## wrong-task

Request:

```http
GET /api/v2/tasks/00000000-0000-0000-0000-000000000000/topology?mode=live&node_limit=1000&edge_limit=2000 HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 404 Not Found
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:32 GMT
Content-Type: application/json
Content-Length: 153
Connection: keep-alive
cache-control: no-store

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"Resource is unavailable.","request_id":"23bb3188-00ef-41b3-8787-7e59fc6e4743","retryable":false,"details":{}}
```

## logout

Request:

```http
POST /auth/logout HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Origin: http://127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Accept: */*
Content-Length: 0
```

Response:

```http
HTTP/1.1 204 No Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:58 GMT
Connection: keep-alive
cache-control: no-store
set-cookie: wuji_vnext_session=[REDACTED]; expires=Tue, 15 Sep 2026 02:36:58 GMT; HttpOnly; Max-Age=0; Path=/; SameSite=strict
```

## after-logout

Request:

```http
GET /auth/session HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: wuji-web-gateway-verifier/1.0
Accept: */*
```

Response:

```http
HTTP/1.1 401 Unauthorized
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 02:36:58 GMT
Content-Type: application/json
Content-Length: 152
Connection: keep-alive
cache-control: no-store

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"d190f704-4d49-4772-b47c-d352ca70313d","retryable":false,"details":{}}
```
