#!/usr/bin/env python3
"""Probe the pinned LiteLLM Python release through a local fake provider.

Run this with an isolated official ``litellm==1.100.0`` environment.  It
does not contact DeepSeek, use a provider key, or modify a project lock.
"""

from __future__ import annotations

import json
import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeProvider:
    def __init__(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                return None

            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", "0"))
                body = json.loads(self.rfile.read(length))
                owner.request = {"path": self.path, "body": body}
                chunks = [
                    {
                        "id": "fake-deepseek",
                        "object": "chat.completion.chunk",
                        "created": 1,
                        "model": body.get("model", "deepseek-flash"),
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"role": "assistant", "content": "OK"},
                                "finish_reason": None,
                            }
                        ],
                    },
                    {
                        "id": "fake-deepseek",
                        "object": "chat.completion.chunk",
                        "created": 1,
                        "model": body.get("model", "deepseek-flash"),
                        "choices": [
                            {"index": 0, "delta": {}, "finish_reason": "stop"}
                        ],
                        "usage": {
                            "prompt_tokens": 8,
                            "completion_tokens": 1,
                            "total_tokens": 9,
                        },
                    },
                ]
                payload = b"".join(
                    b"data: " + json.dumps(item, separators=(",", ":")).encode() + b"\n\n"
                    for item in chunks
                ) + b"data: [DONE]\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.request: dict[str, object] | None = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/deepseek"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--maf-dialect",
        action="store_true",
        help="probe max_completion_tokens and report locked-provider incompatibility",
    )
    args = parser.parse_args()
    import litellm

    litellm.set_verbose = False
    litellm.suppress_debug_info = True
    provider = FakeProvider()
    try:
        response = litellm.completion(
            model="deepseek/deepseek-flash",
            api_base=provider.url,
            api_key="fake-provider-key",
            messages=[{"role": "user", "content": "fixture"}],
            stream=True,
            stream_options={"include_usage": True},
            parallel_tool_calls=False,
            **(
                {"max_completion_tokens": 32}
                if args.maf_dialect
                else {"max_tokens": 32}
            ),
            thinking={"type": "disabled"},
        )
        list(response)
        request = provider.request
        if request is None:
            raise AssertionError("fake provider received no request")
        body = request["body"]
        assert isinstance(body, dict)
        assert body["model"] == "deepseek-flash", body
        if args.maf_dialect and body.get("max_tokens") != 32:
            print(
                json.dumps(
                    {
                        "status": "blocked",
                        "reason": "locked LiteLLM forwarded max_completion_tokens",
                        "provider_wire": body,
                    },
                    sort_keys=True,
                )
            )
            return 3
        if not args.maf_dialect and body.get("max_tokens") != 32:
            raise AssertionError(json.dumps({"provider_wire": body}, sort_keys=True))
        assert "max_completion_tokens" not in body, body
        assert body["thinking"] == {"type": "disabled"}, body
        assert body["stream"] is True, body
        assert body["parallel_tool_calls"] is False, body
        print(json.dumps({"status": "pass", "path": request["path"], "body": body}, sort_keys=True))
        return 0
    finally:
        provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
