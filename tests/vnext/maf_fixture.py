"""Synthetic Chat Completions HTTP peer; never substitutes the MAF SDK."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class SyntheticModel:
    def __init__(self, mode):
        self.mode = mode
        self.exchanges = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                payload = json.loads(raw)
                status = 200
                if owner.mode == "http-error" or len(owner.exchanges) >= 4:
                    status = 503
                    body = {"error": {"message": "synthetic bounded failure", "type": "server_error"}}
                elif any(m.get("role") == "tool" for m in payload["messages"]):
                    message = {"role": "assistant", "content": "offline-p01-record received"}
                    body = completion(message, "stop")
                else:
                    name = "unregistered_probe_tool" if owner.mode == "unknown" else "read_record"
                    message = {"role": "assistant", "content": None, "tool_calls": [{
                        "id": "call-p01-read", "type": "function", "function": {
                            "name": name, "arguments": '{"record_id":"synthetic-001"}'
                        }
                    }]}
                    body = completion(message, "tool_calls")
                response_body = json.dumps(body, separators=(",", ":"))
                response_headers = [
                    ["Content-Type", "application/json"],
                    ["Content-Length", str(len(response_body.encode()))],
                    ["Connection", "close"],
                ]
                reason = "OK" if status == 200 else "Service Unavailable"
                response_head = f"HTTP/1.1 {status} {reason}\r\n" + "".join(
                    f"{k}: {v}\r\n" for k, v in response_headers
                ) + "\r\n"
                self.wfile.write((response_head + response_body).encode())
                self.wfile.flush()
                self.close_connection = True
                owner.exchanges.append({
                    "method": self.command,
                    "url": owner.url.removesuffix("/v1") + self.path,
                    "request_line": self.requestline,
                    "request_headers": list(self.headers.raw_items()),
                    "request_body": raw.decode(),
                    "response_status": status,
                    "response_headers": response_headers,
                    "response_body": response_body,
                    "response_http": response_head + response_body,
                })

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def completion(message, reason):
    return {
        "id": "chatcmpl-synthetic-p01", "object": "chat.completion", "created": 1,
        "model": "p01-synthetic", "choices": [{"index": 0, "message": message, "finish_reason": reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
