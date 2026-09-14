# Internal HTTP packet index

Every model and ToolGate body referenced here is stored byte-for-byte in the adjacent raw file. The model request rows came from `vnext.model_call.request_json`, response SSE rows from `vnext.model_response_chunk.data`, ToolGate request rows from `vnext.tool_call.request_json`, and receipts from `vnext.tool_attempt.receipt_json` / `vnext.result_submission`.

| Flow | Method and URL | Request body | Response body | Status |
| --- | --- | --- | --- | --- |
| Model 1 | `POST https://gates.wuji-vnext-test.svc:8443/internal/v2/model/chat/completions` | [model-1-request.json](model-1-request.json) | [model-response-1.sse](model-response-1.sse) | 200 |
| Model 2 | same | [model-2-request.json](model-2-request.json) | [model-response-2.sse](model-response-2.sse) | 200 |
| Model 3 | same | [model-3-request.json](model-3-request.json) | [model-response-3.sse](model-response-3.sse) | 200 |
| Model 4 | same | [model-4-request.json](model-4-request.json) | [model-response-4.sse](model-response-4.sse) | 200 |
| Tool 1 | `POST https://gates.wuji-vnext-test.svc:8443/internal/v2/tool-calls` | [tool-1-request.json](tool-1-request.json) | [tool-1-receipt.json](tool-1-receipt.json) | 200 |
| Tool 2 | same | [tool-2-request.json](tool-2-request.json) | [tool-2-receipt.json](tool-2-receipt.json) | 200 |
| Result 1 | Runtime result intake over the registered Worker Host channel | [result-1-envelope.json](result-1-envelope.json) | [result-1-receipt.json](result-1-receipt.json) | received |
| Result 2 | same | [result-2-envelope.json](result-2-envelope.json) | [result-2-receipt.json](result-2-receipt.json) | received |

For model requests, the recorded headers were `Authorization: Bearer [redacted run credential]`, `Content-Type: application/json`, `Accept: text/event-stream`, and a per-attempt `X-Wuji-Request-ID`; the response carried `X-Wuji-Model-Attempt-ID`. Tool requests used the run credential, JSON content type, and the exact typed request body. The transport used `trust_env=False`, no retries and no redirects. The public start/cancel packets, including all headers and response bodies, are in [http-reproduction.md](../http-reproduction.md).
