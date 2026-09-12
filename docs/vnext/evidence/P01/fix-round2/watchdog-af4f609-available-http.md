# P01 HTTP observation record

This package reproduces captured HTTP messages only. It does not establish SDK capability, approval outcomes, tool execution, or retry/failure validation.

Observation completeness: incomplete.

Captured HTTP exchanges: 1.

Execution outcome: unknown. Capability outcome: blocked.

Missing observations do not prove zero execution.

A subprocess timeout was recorded. Only HTTP observations available at that boundary are reproduced.

## roundtrip exchange 1

URL: http://127.0.0.1:58389/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Accept-Encoding: identity
Content-Length: 133
Host: 127.0.0.1:58389
User-Agent: Python-urllib/3.13
Content-Type: application/json
X-P01-Purpose: watchdog-no-sdk
Connection: close

{"model": "watchdog-no-sdk", "tools": [], "messages": [{"role": "user", "content": "watchdog reporting fixture; no SDK invocation"}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 400
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```
