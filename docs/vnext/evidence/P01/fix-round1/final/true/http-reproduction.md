# P01 synthetic HTTP reproduction package

All data and Authorization values below are synthetic. No target vulnerability is claimed.

Validation points: explicit nonempty tool advertisement; native call-p01-read routing; actual file reads; approval rejection; finite HTTP failure.

## roundtrip exchange 1

URL: http://127.0.0.1:58995/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Accept-Encoding: identity
Content-Length: 133
Host: 127.0.0.1:58995
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
