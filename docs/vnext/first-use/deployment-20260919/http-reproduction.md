# 2026-09-19 正式入口完整报文

A0 实际读取，HTTPX 0.28.1；不是独立 A8 执行。以下正文未截断。时间为 UTC。无 Cookie、访问码、供应商凭据或付费请求。入口图片见 [实际截图](screenshots/workbench-login.png)。本记录证明部署入口及拒绝边界，不证明创建/启动到结果的闭环。

## 页面入口

```http
GET http://localhost:44180/ HTTP/1.1
Host: localhost:44180
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Accept: text/html

```

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 13:54:24 GMT
Content-Type: text/html
Content-Length: 431
Last-Modified: Sat, 19 Sep 2026 09:46:49 GMT
Connection: keep-alive
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

## 未认证读取被拒绝（预期401）

```http
GET http://localhost:44180/auth/session HTTP/1.1
Host: localhost:44180
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Accept: application/json

```

```http
HTTP/1.1 401 Unauthorized
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 13:54:24 GMT
Content-Type: application/json
Content-Length: 152
Connection: keep-alive
Cache-Control: no-store

{"code":"UNAUTHENTICATED","message":"Browser session is not active.","request_id":"87eb82a6-ccf0-40dc-8da1-3a8c60d70992","retryable":false,"details":{}}
```

## 非获准 Host 被拒绝（预期400）

```http
GET http://localhost:44180/auth/session HTTP/1.1
Host: unapproved.invalid
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Accept: application/json

```

```http
HTTP/1.1 400 Bad Request
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 13:54:24 GMT
Content-Type: application/json
Content-Length: 157
Connection: keep-alive
Cache-Control: no-store

{"code":"INVALID_SCHEMA","message":"Gateway request boundary is invalid.","request_id":"44c70b1a-32b9-4c34-8b18-8fac790edd6e","retryable":false,"details":{}}
```

## 非获准 Origin 被拒绝（预期403）

```http
POST http://localhost:44180/auth/login HTTP/1.1
Host: localhost:44180
Content-Length: 0
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
Origin: http://unapproved.invalid
Accept: application/json

```

```http
HTTP/1.1 403 Forbidden
Server: nginx/1.29.1
Date: Sat, 19 Sep 2026 13:54:24 GMT
Content-Type: application/json
Content-Length: 146
Connection: keep-alive
Cache-Control: no-store

{"code":"FORBIDDEN","message":"Browser origin is not allowed.","request_id":"e5886fc0-db82-4e4a-8c5e-ab0a54f840d4","retryable":false,"details":{}}
```

修复点：Nginx 原 `$host` 丢失非默认端口，合法44180入口此前返回400；改为保留 `$http_host`，未放宽 BFF 的精确 Host/Origin 校验。后续真实浏览器通过本地访问码建立会话并读取目录；访问码未进入本记录，临时0600传递文件已删除。
