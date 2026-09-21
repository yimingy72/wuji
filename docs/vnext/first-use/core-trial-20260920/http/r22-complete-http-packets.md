# R22 complete HTTP packets

Task: `b058c399-3318-4a05-85a4-48b9a5801922`

This package distinguishes the platform-retained tool material from the
independent evidence replay. No credential value is included. There is no
claimed vulnerability in this trial; the validated point is the authorized,
non-destructive first-use execution path.

## Platform Task API

[r22-final.json](r22-final.json) contains the complete redacted request and
response packets for the final Task, launch and readiness reads. The operator
token is represented as `<operator SecretRef>`.

## Platform tool request 1 — entrance

[r22-target-root.json](r22-target-root.json) is the immutable tool artifact.
It contains the method, URL, request headers, response status and headers, and
the exact 12,429-byte response body as base64.

```http
GET / HTTP/1.1
Host: 39.97.227.109
User-Agent: wuji-target-read/1
Accept: */*

```

The request body is empty. The response is HTTP 200, is marked
`truncated=false`, and its decoded-body SHA-256 is
`1390ef07362ff9fd6e1f1fc4c147a778d86b586f1aca4ba11343bd6504ff790f`.

## Platform tool request 2 — evidence-derived static resource

[r22-target-follow-up-partial.json](r22-target-follow-up-partial.json) is the
immutable platform tool artifact for the follow-up selected from the entrance
HTML. It records the following request and the actual HTTP 200 response, but
the platform material is explicitly `truncated=true`: it retains 48,768 bytes
of a response whose origin `Content-Length` is 250,042 bytes.

```http
GET /static/js/app.f0661109.js HTTP/1.1
Host: 39.97.227.109
User-Agent: wuji-target-read/1
Accept: */*

```

The request body is empty. The retained prefix SHA-256 is
`81ebbb1f505b2c42ae6e2bd733474ee8b8b2bec3fece29f295074d5e7b88aea9`.
This partial artifact is not presented as a complete origin response.

## Complete independent replay of request 2

The same authorized read was replayed once at `2026-09-21 07:55:39
Asia/Shanghai` solely to package the complete response required by the
delivery rules. This replay is supporting evidence and is not represented as
the platform tool call.

```http
GET /static/js/app.f0661109.js HTTP/1.1
Host: 39.97.227.109
User-Agent: wuji-evidence-capture/1
Accept: */*

```

The request body is empty. The exact response headers are in
[r22-follow-up-replay-response.headers](r22-follow-up-replay-response.headers),
and the complete response body is
[r22-follow-up-replay-response.js](r22-follow-up-replay-response.js).

```http
HTTP/1.1 200 OK
Server: nginx/1.27.4
Date: Sun, 20 Sep 2026 23:55:39 GMT
Content-Type: application/javascript; charset=utf-8
Content-Length: 250042
Last-Modified: Thu, 06 Feb 2025 07:42:01 GMT
Connection: keep-alive
ETag: "67a467c9-3d0ba"
Accept-Ranges: bytes
```

The attached body is exactly 250,042 bytes with SHA-256
`db87b8ab46a43cd8597dff922c2496b02f63e93b4c79a8cbb113942679ac2abe`.
The 48,768-byte platform-retained body was byte-compared with this body and is
an identical prefix.
