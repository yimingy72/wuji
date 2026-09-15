# Complete HTTP reproduction — Kubernetes LoadBalancer entry

These requests were sent after stopping every `kubectl port-forward` for port 44180. `Service/wuji-web` was `type: LoadBalancer`, reported external hostname `localhost`, and Docker Desktop owned the host listener. Both requests have no request body.

## 1. Health endpoint

### Request

```http
GET /healthz HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: curl/8.7.1
Accept: */*

```

### Response

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:31:07 GMT
Content-Type: text/plain
Content-Length: 3
Connection: keep-alive

ok
```

## 2. Web application root

### Request

```http
GET / HTTP/1.1
Host: 127.0.0.1:44180
User-Agent: curl/8.7.1
Accept: */*

```

### Response

```http
HTTP/1.1 200 OK
Server: nginx/1.29.1
Date: Tue, 15 Sep 2026 03:31:07 GMT
Content-Type: text/html
Content-Length: 431
Last-Modified: Tue, 15 Sep 2026 03:03:43 GMT
Connection: keep-alive
ETag: "6aa8b58f-1af"
Accept-Ranges: bytes

<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Wuji</title>
    <script src="/config.js"></script>
    <script type="module" crossorigin src="/assets/index-BzOhhZ3Y.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-IUG2yBo7.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
```

The native curl traces, headers and exact response bodies are retained under [`raw/`](raw/). No authentication credential appears in these two public Web entry requests.
