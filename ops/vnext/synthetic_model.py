"""Explicit loopback synthetic model peer for the isolated Gate Pod (D12)."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from time import time
from uuid import uuid4


class Peer(BaseHTTPRequestHandler):
    def do_POST(self):
        size=int(self.headers.get("Content-Length","0"))
        if self.path != "/v1/chat/completions" or not 0 < size <= 1048576:
            self.send_error(400);return
        request=json.loads(self.rfile.read(size))
        if request.get("stream") is not True:
            self.send_error(400);return
        prior=[m for m in request["messages"] if m.get("role")=="tool"]
        if prior:
            receipt=json.loads(prior[-1]["content"])
            evidence=receipt["evidence_receipt"]
            if receipt["status"]!="complete" or evidence["status"]!="accepted":
                self.send_error(422);return
            text=json.dumps({"schema_version":"wuji.agent-payload.v2", "claims":[{
                "client_ref":"kali-version", "kind":"observation-summary", "assertion_role":"candidate_fact",
                "text":"The registered Kali read returned durable evidence.",
                "basis_refs":[evidence["observation_ref"]], "limitations":["one synthetic workspace read"]}],
                "intent_proposals":[], "limitations":["synthetic loopback mechanism peer"]})
            delta={"role":"assistant","content":text};reason="stop"
        else:
            if not any(t["function"]["name"]=="read_workspace" for t in request.get("tools",[])):
                self.send_error(422);return
            delta={"role":"assistant","tool_calls":[{"index":0,"id":"call-c2-read","type":"function",
                "function":{"name":"read_workspace","arguments":'{"path":"version.txt"}'}}]};reason="tool_calls"
        prefix={"id":"synthetic-"+str(uuid4()),"object":"chat.completion.chunk","created":int(time()),"model":request["model"]}
        chunks=[{**prefix,"choices":[{"index":0,"delta":delta,"finish_reason":None}]},
                {**prefix,"choices":[{"index":0,"delta":{},"finish_reason":reason}]}]
        data=b"".join(b"data: "+json.dumps(c).encode()+b"\n\n" for c in chunks)+b"data: [DONE]\n\n"
        self.send_response(200);self.send_header("Content-Type","text/event-stream")
        self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)

    def log_message(self,*_args):
        pass


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8081)
    args=parser.parse_args()
    if args.host not in {"127.0.0.1","::1","localhost"}:raise ValueError("D12 model peer must remain loopback-only")
    ThreadingHTTPServer((args.host,args.port),Peer).serve_forever()
