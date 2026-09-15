# P15-L personal layout CAS — complete HTTP reproduction

All packets were sent to the Kubernetes `wuji-web` LoadBalancer at `127.0.0.1:44180` for Task `a41a59ed-29e1-4801-b68b-dfea395eae30`.
Cookie values are redacted because the browser session is a credential; paths, methods, non-secret headers,
request bodies and response bodies are complete. The captured session is the local mechanism operator, not a
production identity.

## anonymous layout read

A browser without a session cookie receives 401 before any Task or layout lookup.

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Accept: application/json
```

Response:

```http
HTTP/1.1 401 Unauthorized
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 152
Connection: keep-alive
cache-control: no-store

HTTP status: 401

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"a63b201f-fbe8-403e-8cc5-8550c5d92392","retryable":false,"details":{}}
```

## browser session login

The gateway mints an HttpOnly, SameSite=strict 30-minute browser session.

Request:

```http
POST /auth/login HTTP/1.1
Host: 127.0.0.1:44180
Origin: http://127.0.0.1:44180
Content-Length: 0
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 253
Connection: keep-alive
cache-control: no-store
set-cookie: wuji_vnext_session=[REDACTED]; HttpOnly; Max-Age=1800; Path=/; SameSite=strict

HTTP status: 200

{"authenticated":true,"display_name":"Local Kubernetes operator","tenant_id":"1fc6b1f3-6f24-456b-9dc1-4e14c7197604","project_id":"81e8c413-ba26-45fb-8b5a-1bc477eef99f","task_id":"a41a59ed-29e1-4801-b68b-dfea395eae30","expires_at":"2026-09-15T07:25:56Z"}
```

## read the personal layout (baseline)

Default or previously saved preference for this subject and view.

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Accept: application/json
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 500
Connection: keep-alive
cache-control: no-store
x-request-id: 2339acdc-37fc-4719-b326-94efc123d5f1

HTTP status: 200

{"schema_version":"wuji.api.v2","view_name":"knowledge-live","layout_revision":"51","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":77.5,"y":-12.25,"pinned":true},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":1138.2734268417462,"y":148.3888130968622,"pinned":false}],"viewport":{"x":-174.26526982380688,"y":230.71716938080237,"zoom":0.9289032900692605}}
```

## save the personal layout with If-Match

Compare-and-swap accepts the request computed from the current revision and returns the new revision.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <current layout_revision>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 105
Connection: keep-alive
cache-control: no-store
x-request-id: 96b58866-931a-4ff9-95d5-8d1aad62923d

HTTP status: 200

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

## stale If-Match is rejected

The second request reuses the first revision; the server answers 409 STALE_VERSION and does not overwrite.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <same, now stale, revision>
```

Response:

```http
HTTP/1.1 409 Conflict
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 155
Connection: keep-alive
cache-control: no-store
x-request-id: 0681684d-b70d-4bcc-9f9f-107dea207c06

HTTP status: 409

{"code":"STALE_VERSION","message":"The request could not be completed.","request_id":"0681684d-b70d-4bcc-9f9f-107dea207c06","retryable":false,"details":{}}
```

## layout after the stale rejection

The accepted revision is still the only stored preference.

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 435
Connection: keep-alive
cache-control: no-store
x-request-id: 16b81a75-ee7b-45ce-bb98-20bd1588cc01

HTTP status: 200

{"schema_version":"wuji.api.v2","view_name":"knowledge-live","layout_revision":"52","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

## history view keeps a separate preference

Live and history layouts are independent rows with their own selection mode.

Request:

```http
GET /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-history HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
```

Response:

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 177
Connection: keep-alive
cache-control: no-store
x-request-id: ab7b737a-f2ac-4469-9511-a50c23bca5ea

HTTP status: 200

{"schema_version":"wuji.api.v2","view_name":"knowledge-history","layout_revision":"0","selection_mode":"explicit_revision","entries":[],"viewport":{"x":0.0,"y":0.0,"zoom":0.82}}
```

## cross-Task read is indistinguishable from absence

The gateway only forwards the fixed Task; other Task ids return 404.

Request:

```http
GET /api/v2/tasks/00000000-0000-0000-0000-000000000000/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
```

Response:

```http
HTTP/1.1 404 Not Found
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:55:56 GMT
Content-Type: application/json
Content-Length: 153
Connection: keep-alive
cache-control: no-store

HTTP status: 404

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"Resource is unavailable.","request_id":"7d345c9d-7262-4f13-afb6-97b62e7706aa","retryable":false,"details":{}}
```

## missing Origin is rejected before forwarding

A layout write without the exact browser Origin never reaches the internal API.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 403 Forbidden
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 146
Connection: keep-alive
cache-control: no-store

HTTP status: 403

{"code":"FORBIDDEN","message":"Browser origin is not allowed.","request_id":"7abf7684-5443-4ca1-b1fa-5d7467725444","retryable":false,"details":{}}
```

## wrong Origin is rejected

Only the configured origins are accepted.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://evil.example
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 403 Forbidden
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 146
Connection: keep-alive
cache-control: no-store

HTTP status: 403

{"code":"FORBIDDEN","message":"Browser origin is not allowed.","request_id":"da41d88d-ded2-4a32-a09a-321858965f5f","retryable":false,"details":{}}
```

## non-canonical If-Match is rejected

Revisions are canonical decimal strings.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: 01

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 157
Connection: keep-alive
cache-control: no-store

HTTP status: 422

{"code":"INVALID_SCHEMA","message":"If-Match must be a decimal revision.","request_id":"4a41a9d6-ae23-481d-acb3-01c321697106","retryable":false,"details":{}}
```

## non-JSON content type is rejected

Layout writes require application/json.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: text/plain
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 149
Connection: keep-alive
cache-control: no-store

HTTP status: 422

{"code":"INVALID_SCHEMA","message":"Layout updates require JSON.","request_id":"bb3b178c-5064-423b-aad7-4d6afcbf561a","retryable":false,"details":{}}
```

## unknown anchor cannot become a shadow node

Body anchors `claim:missing`, which is not in the authorized projection: 422 INVALID_REFERENCE.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"claim","id":"missing"},"x":1,"y":2,"pinned":false}],"viewport":{"x":0,"y":0,"zoom":0.82}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 159
Connection: keep-alive
cache-control: no-store
x-request-id: 0ab3ef11-aa33-4323-acf7-69618105aa7f

HTTP status: 422

{"code":"INVALID_REFERENCE","message":"The request could not be completed.","request_id":"0ab3ef11-aa33-4323-acf7-69618105aa7f","retryable":false,"details":{}}
```

## duplicate anchors are rejected

Two entries for the same anchor: 422 INVALID_SCHEMA.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":1,"y":2,"pinned":false},{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":3,"y":4,"pinned":false}],"viewport":{"x":0,"y":0,"zoom":0.82}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 156
Connection: keep-alive
cache-control: no-store
x-request-id: 516a00db-b553-43ee-af35-e238b913ec83

HTTP status: 422

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"516a00db-b553-43ee-af35-e238b913ec83","retryable":false,"details":{}}
```

## NaN zoom is rejected by the strict JSON boundary

The body contains a bare `NaN` token.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[],"viewport":{"x":0,"y":0,"zoom":NaN}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 155
Connection: keep-alive
cache-control: no-store

HTTP status: 422

{"code":"INVALID_SCHEMA","message":"Layout request is not strict JSON.","request_id":"8f295f30-5f10-4c6a-be7b-c85983863bef","retryable":false,"details":{}}
```

## selection mode must match the view

`knowledge-live` requires follow_latest; explicit_revision is rejected.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/layouts/knowledge-live HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: <current>

{"schema_version":"wuji.api.v2","selection_mode":"explicit_revision","entries":[],"viewport":{"x":0,"y":0,"zoom":0.82}}
```

Response:

```http
HTTP/1.1 422 Unprocessable Content
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 156
Connection: keep-alive
cache-control: no-store
x-request-id: d819c8eb-4d1f-4f26-b57f-4a90c6541b91

HTTP status: 422

{"code":"INVALID_SCHEMA","message":"The request could not be completed.","request_id":"d819c8eb-4d1f-4f26-b57f-4a90c6541b91","retryable":false,"details":{}}
```

## task command path stays closed

Only the two layout paths accept PUT; every other path is 404 and is not forwarded.

Request:

```http
PUT /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/commands HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json
If-Match: 1

{"schema_version":"wuji.api.v2","selection_mode":"follow_latest","entries":[{"anchor":{"entity_type":"origin","id":"a41a59ed-29e1-4801-b68b-dfea395eae30","revision":null},"x":120.5,"y":-40.25,"pinned":false},{"anchor":{"entity_type":"intent","id":"778ac2ff-d006-4764-a11f-9f3e83473ade","revision":"1"},"x":640.75,"y":210.5,"pinned":false}],"viewport":{"x":-30.0,"y":55.5,"zoom":1.1}}
```

Response:

```http
HTTP/1.1 404 Not Found
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 153
Connection: keep-alive
cache-control: no-store

HTTP status: 404

{"code":"NOT_FOUND_OR_FORBIDDEN","message":"Resource is unavailable.","request_id":"3bfd5444-4add-4e73-8fbc-07814080b98f","retryable":false,"details":{}}
```

## task command path stays closed for POST

The gateway has no POST route: 405 from the gateway itself, with no upstream call.

Request:

```http
POST /api/v2/tasks/a41a59ed-29e1-4801-b68b-dfea395eae30/commands HTTP/1.1
Host: 127.0.0.1:44180
Cookie: wuji_vnext_session=[REDACTED]
Origin: http://127.0.0.1:44180
Content-Type: application/json

{"schema_version":"wuji.api.v2","command":"cancel","expected_version":"1","idempotency_key":"x"}
```

Response:

```http
HTTP/1.1 405 Method Not Allowed
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 06:56:10 GMT
Content-Type: application/json
Content-Length: 31
Connection: keep-alive
allow: GET

HTTP status: 405

{"detail":"Method Not Allowed"}
```
