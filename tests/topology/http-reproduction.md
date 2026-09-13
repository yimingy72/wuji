# P14 固定 DTO 浏览器页 HTTP 复现包

日期：2026-09-13（Asia/Shanghai）。此报文只证明专用浏览器页由本地 Vite 服务真实返回；页面随后加载并渲染正式 `TopologyFlowCanvas`。它不是 P13 topology API 响应，也不证明 v2 auth、持久快照、布局保存、增量流或 M4 闭环。

启动命令：

```text
PATH="$PWD/work/toolchain/bin:$PATH" pnpm --dir apps/web exec vite ../../tests/topology/browser --config ../../tests/topology/browser/vite.config.ts --host 127.0.0.1 --port 4194 --strictPort
```

复现命令：

```text
curl --http1.1 --verbose --request GET 'http://127.0.0.1:4194/?theme=silver' --header 'Accept: text/html' --header 'User-Agent: Wuji-P14-Reproducer/1.0'
```

完整请求（GET 请求体为空）：

```http
GET /?theme=silver HTTP/1.1
Host: 127.0.0.1:4194
Accept: text/html
User-Agent: Wuji-P14-Reproducer/1.0

```

完整响应：

```http
HTTP/1.1 200 OK
Vary: Origin
Content-Type: text/html
Cache-Control: no-cache
Etag: W/"179-nZ67p6Gx2whTQ+pcRVe1yL8fS+8"
Date: Sun, 13 Sep 2026 04:47:50 GMT
Connection: keep-alive
Keep-Alive: timeout=5
Content-Length: 377

<!doctype html>
<html lang="zh-CN">
  <head>
    <script type="module" src="/@vite/client"></script>

    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TopologyFlowCanvas browser fixture</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.tsx"></script>
  </body>
</html>
```

安全边界：此成果没有漏洞利用点。与安全相关的验证点是画布不提供自由连线或重连，Delete 不删除领域对象，历史模式不显示领域动作；对应真实浏览器动作见 `browser.spec.ts`。固定 DTO 只存在于 `tests/topology/fixtures.ts`，生产容器读取失败时显示错误，不回退到该数据。
