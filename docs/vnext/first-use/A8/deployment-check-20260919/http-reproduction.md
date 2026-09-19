# 2026-09-19 入口 HTTP 完整复现包

执行者：Codex 主代理。请求均由本次复核直接使用 `curl` 发出，`--noproxy '*'`、HTTP/1.1、无 Cookie、无访问码、无供应商凭据；响应正文未截断。响应中的 `request_id` 为服务端本次生成的非敏感请求标识。

## 1. 正常入口：预期 200

复现命令：

```sh
curl --noproxy '*' --http1.1 -sS -i \
  -H 'Host: localhost:44180' \
  -H 'User-Agent: A8-deployment-check/20260919' \
  -H 'Accept: text/html' \
  -H 'Connection: close' \
  http://localhost:44180/
```

```http
GET / HTTP/1.1
Host: localhost:44180
User-Agent: A8-deployment-check/20260919
Accept: text/html
Connection: close

HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 14:14:35 GMT
Content-Type: text/html
Content-Length: 431
Last-Modified: Sat, 19 Sep 2026 09:46:49 GMT
Connection: close
ETag: "6aae5a09-1af"
Accept-Ranges: bytes

<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Wuji</title>
    <script src="/config.js"></script>
    <script type="module" crossorigin src="/assets/index-C7CxV_cZ.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-CfeaxKAx.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
```

curl exit code: `0`。
## 2. 未认证 session：预期 401

复现命令：

```sh
curl --noproxy '*' --http1.1 -sS -i \
  -H 'Host: localhost:44180' \
  -H 'User-Agent: A8-deployment-check/20260919' \
  -H 'Accept: application/json' \
  -H 'Connection: close' \
  http://localhost:44180/auth/session
```

```http
GET /auth/session HTTP/1.1
Host: localhost:44180
User-Agent: A8-deployment-check/20260919
Accept: application/json
Connection: close

HTTP/1.1 401 Unauthorized
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 14:14:35 GMT
Content-Type: application/json
Content-Length: 152
Connection: close
cache-control: no-store

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"3880d2c6-344e-4efa-b5a1-6e1a37d7c2e5","retryable":false,"details":{}}
```

curl exit code: `0`。

## 3. 未批准 Host：预期 400

复现命令：

```sh
curl --noproxy '*' --http1.1 -sS -i \
  -H 'Host: unapproved.invalid' \
  -H 'User-Agent: A8-deployment-check/20260919' \
  -H 'Accept: application/json' \
  -H 'Connection: close' \
  http://localhost:44180/auth/session
```

```http
GET /auth/session HTTP/1.1
Host: unapproved.invalid
User-Agent: A8-deployment-check/20260919
Accept: application/json
Connection: close

HTTP/1.1 400 Bad Request
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 14:14:35 GMT
Content-Type: application/json
Content-Length: 157
Connection: close
cache-control: no-store

{"code":"INVALID_SCHEMA","message":"Gateway request boundary is invalid.","request_id":"03aa5bd4-1b74-4d99-bc33-7102cc6d1c29","retryable":false,"details":{}}
```

curl exit code: `0`。

## 4. 未批准 Origin 的登录请求：预期 403

请求只有不批准的 Origin；没有 Cookie、访问码或请求体。复现命令：

```sh
curl --noproxy '*' --http1.1 -sS -i -X POST \
  -H 'Host: localhost:44180' \
  -H 'User-Agent: A8-deployment-check/20260919' \
  -H 'Origin: http://unapproved.invalid' \
  -H 'Accept: application/json' \
  -H 'Content-Length: 0' \
  -H 'Connection: close' \
  http://localhost:44180/auth/login
```

```http
POST /auth/login HTTP/1.1
Host: localhost:44180
User-Agent: A8-deployment-check/20260919
Origin: http://unapproved.invalid
Accept: application/json
Content-Length: 0
Connection: close

HTTP/1.1 403 Forbidden
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 14:14:35 GMT
Content-Type: application/json
Content-Length: 146
Connection: close
cache-control: no-store

{"code":"FORBIDDEN","message":"Browser origin is not allowed.","request_id":"018d5bf6-fc6f-4857-ac19-00c5b67b83a4","retryable":false,"details":{}}
```

curl exit code: `0`。
