# Task workers

Build from repository root with Dockerfile.agent / Dockerfile.kali. Agent is Node 24, native Pi CLI exactly 0.73.0; CLI flags verified against v0.73.0 source. No custom model loop.

`WUJI_CONFIG=/config/binding.json`: JSON `task_id,tenant_id,project_id,execution_epoch` (integer), `runtime_attempt` (string), `control_url`, `fixture_origins` (exact origins array). `WUJI_CREDENTIALS=/run/wuji/credentials`: agent reads backend_token, lease_token, model_key; Kali reads router_token, lease_token. `WUJI_STATE` defaults /var/lib/wuji/agent or /workspace/.wuji. `WUJI_WORKSPACE=/workspace`; PORT defaults 8001/8003.

All routes require role-specific Bearer token. Agent PUT /runs/{id} accepts execution-contract body plus top-level write-only tool_token, stored in per-run 0600 file. GET /runs/{id} returns receipt. GET /runs/{id}/output returns receipt plus output (raw Pi JSONL string). POST /runs/{id}/cancel requests TERM followed by KILL after five seconds. Kali: PUT /calls/{id}, GET /calls/{id}, POST /calls/{id}/cancel. Same ID and digest returns existing receipt, mismatched request returns 409, missing ID 404. Restarted nonterminal records become unknown, never rerun.

Receipt: id,state (registered/running/exited/unknown),returncode,pid,started_at,finished_at,cancel_requested,output_digest,request_digest. Kali adds result: {ok,...} or {ok:false,error}. Only actual child close produces exited. Cancellation acceptance is not proof of stop.

Lease: GET /internal/v1/runtime/lease?task_id=...&runtime_attempt=...&execution_epoch=..., Bearer lease_token, every five seconds. Response {allowed:true,expires_at:ISO}; capped at fifteen seconds. No startup permission; expiry denies new work and stops children.

Extension POST /internal/v1/agent-runs/{id}/tool-calls with {request_id:nativeToolCallId,tool,args}, Bearer tool_token. Never retries ambiguous POST. Response must include id or tool_call_id. GET /internal/v1/tool-calls/{id} polls state (or status) until exited/completed/failed/cancelled/unknown. Explicit tool_cancel POSTs /internal/v1/tool-calls/{id}/cancel. Task/graph reads use assignment snapshots.

Allowed tools: fixture_http, workspace_read/write/list, fixture_wait, task_read, graph_read, tool_wait, tool_cancel. Reason rejects active tools. HTTP GET only, fixed origin registry, no redirect, 1MiB response. Paths reject traversal, symlinks and reserved .wuji. Run limits ninety seconds/twelve turns; Kali helper sixty seconds. Controller owns Task deadline, authorization and aggregate quota. Fixed helper entrypoint, no shell. Model key is read only inside extension, never argv/run JSON/Kali. No Pod network isolation or production egress claim.

Verification: node --test tests/task-workers/boundaries.test.mjs from root: shared-file handoff, traversal/symlink/reserved path, destination rejection, same-key reuse/conflict, real cancellation. Live Pi/LiteLLM/K8 belongs to unified acceptance.
