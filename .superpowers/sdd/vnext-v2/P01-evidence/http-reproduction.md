# P01 synthetic HTTP reproduction package

All data and Authorization values below are synthetic. No target vulnerability is claimed.

Validation points: explicit nonempty tool advertisement; native call-p01-read routing; actual file reads; approval rejection; finite HTTP failure.

## roundtrip exchange 1

URL: http://127.0.0.1:54754/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54754
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 491

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 400
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## roundtrip exchange 2

URL: http://127.0.0.1:54754/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54754
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 769

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."},{"role":"assistant","tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},{"role":"tool","tool_call_id":"call-p01-read","content":"{\"id\":\"synthetic-001\",\"value\":\"offline-p01-record\"}"}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 281
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":"offline-p01-record received"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## roundtrip exchange 3

URL: http://127.0.0.1:54754/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54754
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 955

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."},{"role":"assistant","name":"p01readonly","tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},{"role":"tool","tool_call_id":"call-p01-read","content":"{\"id\":\"synthetic-001\",\"value\":\"offline-p01-record\"}"},{"role":"assistant","name":"p01readonly","content":"offline-p01-record received"},{"role":"user","content":"Continue with the restored history; do not read again."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 281
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":"offline-p01-record received"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## approve exchange 1

URL: http://127.0.0.1:54765/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54765
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 491

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 400
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## approve exchange 2

URL: http://127.0.0.1:54765/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54765
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 790

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."},{"role":"assistant","name":"p01readonly","tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},{"role":"tool","tool_call_id":"call-p01-read","content":"{\"id\":\"synthetic-001\",\"value\":\"offline-p01-record\"}"}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 281
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":"offline-p01-record received"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## reject exchange 1

URL: http://127.0.0.1:54773/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54773
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 491

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 400
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## reject exchange 2

URL: http://127.0.0.1:54773/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54773
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 780

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."},{"role":"assistant","name":"p01readonly","tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},{"role":"tool","tool_call_id":"call-p01-read","content":"Error: Tool call invocation was rejected by user."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 281
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":"offline-p01-record received"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## unknown exchange 1

URL: http://127.0.0.1:54776/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54776
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 491

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 412
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"unregistered_probe_tool","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## http-error exchange 1

URL: http://127.0.0.1:54778/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54778
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 491

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Read one synthetic offline record by its fixture ID.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Content-Length: 71
Connection: close

{"error":{"message":"synthetic bounded failure","type":"server_error"}}
```

## stub exchange 1

URL: http://127.0.0.1:54780/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54780
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 483

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Return without reading the synthetic record.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 400
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```

## stub exchange 2

URL: http://127.0.0.1:54780/v1/chat/completions

```http
POST /v1/chat/completions HTTP/1.1
Host: 127.0.0.1:54780
Accept-Encoding: gzip, deflate
Connection: keep-alive
authorization: Bearer synthetic-localhost-only
accept: application/json
content-type: application/json
user-agent: AsyncOpenAI/Python 3.13.0
x-stainless-lang: python
x-stainless-package-version: 3.13.0
x-stainless-os: MacOS
x-stainless-arch: arm64
x-stainless-runtime: CPython
x-stainless-runtime-version: 3.13.15
x-stainless-async: async:asyncio
x-stainless-retry-count: 0
x-stainless-read-timeout: 5
Content-Length: 734

{"messages":[{"role":"system","content":"Read only the synthetic fixture using the explicit tool."},{"role":"user","content":"Read synthetic-001."},{"role":"assistant","tool_calls":[{"id":"call-p01-read","type":"function","function":{"name":"read_record","arguments":"{\"record_id\":\"synthetic-001\"}"}}]},{"role":"tool","tool_call_id":"call-p01-read","content":"stub did not execute read_record"}],"model":"p01-synthetic","stream":false,"tool_choice":"auto","tools":[{"type":"function","function":{"name":"read_record","description":"Return without reading the synthetic record.","parameters":{"properties":{"record_id":{"title":"Record Id","type":"string"}},"required":["record_id"],"title":"read_record_input","type":"object"}}}]}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 281
Connection: close

{"id":"chatcmpl-synthetic-p01","object":"chat.completion","created":1,"model":"p01-synthetic","choices":[{"index":0,"message":{"role":"assistant","content":"offline-p01-record received"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
```
