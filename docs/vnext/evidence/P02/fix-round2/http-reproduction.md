# P02 fix round 2 HTTP / ASGI / SQL 复现索引

被测代码：`5055f81`。本轮只有 N1 control 产生真实 in-memory HTTPX/ASGI 交换；替代 router 在 app composition 阶段被拒绝，R1 直接驱动 ASGI receive/send，N2 使用真实 PostgreSQL 上下文。没有为非 HTTP 结果伪造报文。

## N1 VNext control 完整 HTTP 包

- test_name：`test_composition_rejects_strict_route_without_vnext_response_guard`
- 完整未截断交换：[`runtime/a9cb66567449/http-exchanges.jsonl`](runtime/a9cb66567449/http-exchanges.jsonl)
- 记录包含 method、URL、全部合成 headers、base64 原始请求体、status、全部响应 headers 和 base64 响应体。实际状态为 503/`CAPABILITY_UNAVAILABLE`。
- 同一 test 随后构造真实 `APIRouter(route_class=StrictJsonRoute)`；`create_app` 抛出固定 `ValueError("vNext routers must use VNextAPIRouter")`，因此没有可声称的 HTTP 请求或响应。

## R1 原生 ASGI 消息

test_name：前三项 unsupported media 参数、headerless byte limit、empty replay、disconnect termination。输入是 test 中完整的 tiny ASGI message：

```text
limit = 7 bytes
unsupported body = b"{}" with Content-Type absent / text/plain / application/octet-stream
over-limit body = b'{"n":17}' with Content-Type absent
empty body = b"" with Content-Type absent
disconnect sequence = http.request(body=b"partial", more_body=True), http.disconnect
```

观察：前三种非空 unsupported media 和 over-limit body 都未进入 downstream，并发送安全 422；empty body 原样 replay 并得到 downstream 204；disconnect 未进入 downstream 且 `send` 为空，不伪造断连响应。

## N2 原生 PostgreSQL

- test_name：`test_force_rollback_records_the_native_normal_exit_rollback`
- 完整 SQL/receipt/readback：[`runtime/f8ccdc5d85b9/postgres-events.jsonl`](runtime/f8ccdc5d85b9/postgres-events.jsonl)
- `SHOW application_name` before/inside/after 为 `""` / `"p02-round2-force-rollback"` / `""`，证明真实 psycopg context 在 normal exit 回滚。
- Audit 为 `transaction_enter(force_rollback=true)`，随后 `transaction_rollback(force_rollback=true,outcome=forced_rollback,exception=null)`；没有 dummy commit 或伪造表写入。
