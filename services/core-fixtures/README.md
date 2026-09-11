# Closed fixtures

Run `python services/core-fixtures/server.py` with PyYAML installed. PORT defaults 8000. `WUJI_FIXTURE_ORIGIN` defaults http://wuji-core-fixtures:8000 and must match the tool server's trusted origin registry. This single HTTP server exposes `/`, `/api/marker`, and `/delay?seconds=30` (bounded sixty seconds), plus `/v1/models` and `/v1/chat/completions`. It performs no outgoing requests. `/delay` is a target for the same controlled fixture_http route used in cancellation validation.

Chat completion supports native Pi OpenAI-compatible JSON and streaming SSE tool_calls, stop/tool_calls finish reasons, final usage chunk and [DONE]. Synthetic usage is exactly 100 prompt + 50 completion tokens per upstream request. Company prices and Task budget remain LiteLLM's concern. Responses require the explicit Wuji phase marker emitted by the trusted extension.

Normal flow: Bootstrap requests fixture_http and verifies the actual marker in the returned body. Reason requests graph_read and emits a producer Intent; Explore writes `/workspace/shared/handoff.txt` and checks the actual byte receipt. Following Reason emits consumer Intent from the producer Fact ID; Explore reads and verifies actual file content. Final Reason completes from the consumer Fact ID. Every Fact includes the actual tool result, never a fabricated count or finding. Failed tool observations are rejected. There is no in-memory session state to reset by changing AgentRun.

The fixture demonstrates framework integration, tool I/O and accounting only. It does not measure real model security assessment ability, production egress isolation, or vulnerability coverage.
