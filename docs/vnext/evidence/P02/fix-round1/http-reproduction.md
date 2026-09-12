# P02 fix round 1 完整 HTTP 复现包索引

被测代码：`8a90d408a4b99f80e951448c25455a4b3e99639f`。全部请求使用测试进程临时 RSA 私钥签发的合成 JWT；私钥不落盘，不含用户或生产凭据。

下列 JSONL 每行是一份未截断交换，完整保存 `request.method`、`request.url`、全部 request headers、base64 请求体、`response.status_code`、全部 response headers 和 base64 响应体。base64 只保证任意请求字节无损，不表示内容被省略。

| Finding / test_name | 完整交换 | 实际结果与漏洞点 |
| --- | --- | --- |
| R1 `test_large_integer_parser_failure_returns_safe_asgi_error` | [`runtime/ee0d1d020112/http-exchanges.jsonl`](runtime/ee0d1d020112/http-exchanges.jsonl) | 完整 4,301 位整数请求；422 `INVALID_SCHEMA`，无 HTTPX fallback 500 |
| R1 `test_json_nesting_beyond_configured_depth_is_rejected` | [`runtime/9d071f2b929a/http-exchanges.jsonl`](runtime/9d071f2b929a/http-exchanges.jsonl) | 深度 65；422 `INVALID_SCHEMA` |
| R2 `test_decimal_number_survives_actual_asgi_and_pydantic_path[1e400]` | [`runtime/45d4f56edff5/http-exchanges.jsonl`](runtime/45d4f56edff5/http-exchanges.jsonl) | 200，响应保持未加引号的 `1E+400`，无 `inf→null` |
| R2 `test_decimal_number_survives_actual_asgi_and_pydantic_path[1.0000000000000001]` | [`runtime/8129ab313bb9/http-exchanges.jsonl`](runtime/8129ab313bb9/http-exchanges.jsonl) | 200，响应保持未加引号的 `1.0000000000000001` |
| R2 ordinary dict return | [`runtime/0332ad73fd83/http-exchanges.jsonl`](runtime/0332ad73fd83/http-exchanges.jsonl) | 503 `CAPABILITY_UNAVAILABLE`，FastAPI 编码前 fail fast |
| R2 ordinary BaseModel return | [`runtime/d43d356330e7/http-exchanges.jsonl`](runtime/d43d356330e7/http-exchanges.jsonl) | 503 `CAPABILITY_UNAVAILABLE`，FastAPI 编码前 fail fast |
| R3 `test_unknown_input_key_is_redacted_from_public_error_location` | [`runtime/2f62af63c580/http-exchanges.jsonl`](runtime/2f62af63c580/http-exchanges.jsonl) | 422；loc 为 `body/<field>`，unknown key 不回显 |
| R3 `test_public_validation_diagnostics_are_bounded` | [`runtime/ba2ba7a1a1ab/http-exchanges.jsonl`](runtime/ba2ba7a1a1ab/http-exchanges.jsonl) | 422；16 条固定诊断，`truncated=true` |
| R7 `test_unknown_schema_version_has_a_distinct_asgi_error` | [`runtime/0bb5dfb2bafc/http-exchanges.jsonl`](runtime/0bb5dfb2bafc/http-exchanges.jsonl) | 422 `INVALID_SCHEMA_VERSION`，不回显 v3 值 |

可用以下离线命令把任一记录恢复成可读报文；它读取完整字段，不发网络请求：

```bash
./scripts/vnext/uv.sh run --frozen python - docs/vnext/evidence/P02/fix-round1/runtime/45d4f56edff5/http-exchanges.jsonl <<'PY'
import base64, json, sys
item = json.loads(open(sys.argv[1], encoding="utf-8").readline())
request = item["request"]
print(request["method"], request["url"], "HTTP/1.1")
for name, value in request["headers"].items():
    print(f"{name}: {value}")
print()
sys.stdout.buffer.write(base64.b64decode(request["body_base64"]))
print("\n")
response = item["response"]
print("HTTP/1.1", response["status_code"])
for name, value in response["headers"].items():
    print(f"{name}: {value}")
print()
sys.stdout.buffer.write(base64.b64decode(response["body_base64"]))
print()
PY
```

R1 的 chunk/deadline/disconnect/replay tests 直接驱动 ASGI `receive/send`，其原生媒介是测试命令和断言，不伪造 HTTP 交换。R4/R5 是 OpenAPI/Pydantic 对保存字节的离线验证；R6 是 PostgreSQL SQL/transaction 原生记录。它们分别在 [`test-results.json`](test-results.json) 和 [`report.md`](report.md) 引用。
