# P05 fix round1 · 完整 HTTP 报文

这是 F2 同一用例中，对实际已发布 Session history artifact 的现有 P03 字节路由读取。它只证明该实际对象可读；F1/F2 控制行为的复现是生产 ControlService 与完整 SQL/前后状态，不伪造 P11 控制 HTTP 端点。

Bearer 为临时测试签发器生成的 JWT，归档替换为 `<EPHEMERAL_TEST_JWT_REISSUE>`。通过报告命令和同一测试 helper 重新签发/创建隔离前提，使用本次返回的 artifact ID；业务请求/响应体未截断。

```http
GET http://testserver/api/v2/artifacts/154b2891-62ce-4eaf-b58d-1996e9100a6c/content?version=1 HTTP/1.1
accept: */*
accept-encoding: gzip, deflate
authorization: Bearer <EPHEMERAL_TEST_JWT_REISSUE>
connection: keep-alive
host: testserver
idempotency-key: ecd3f680-c161-41ed-9474-f1325a69a7bf
user-agent: python-httpx/0.28.1


```

```http
HTTP/1.1 200
cache-control: no-store
content-disposition: attachment
content-security-policy: default-src 'none'
content-type: application/octet-stream
digest: sha-256=Xkzns2uje3il1fn9COa3tUumh51lGqRuyeHW+iTr4wo=
x-content-type-options: nosniff
x-request-id: be345e22-b663-460f-b229-a1ae29031c97

{"messages":[]}
```
