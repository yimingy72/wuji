# Managed Cairn Dispatcher

Run with the project's pinned Python environment:

    WUJI_CONTROL_URL=http://wuji-execution-control:8000 \
    WUJI_SERVICE_TOKEN_FILE=/run/wuji/credentials/dispatcher_token \
    WUJI_CAIRN_TOKEN_FILE=/run/wuji/credentials/cairn_token \
    python services/cairn-dispatcher/main.py --config /config/dispatcher.yaml

`example.yaml` is native Cairn YAML. Its local mode only constructs the native loop: no local worker command is executed. The backend is replaced before run. Pi driver builds only a logical tuple (fixed marker, worker name, prompt), never a shell command. Startup and per-task paid health checks are disabled. Worker profile capacity remains two even though native claim identities are unique AgentRun names.

Requires installed Cairn 0.2.1 from commit 8e7e0ea67552383851dfcabfba0c4e9c8d007878. Startup checks distribution provenance and pinned hashes of the seven reused Dispatcher sources. No source file is patched in place; no Cairn Core change.

All control requests use the service Bearer credential. Reads use the Cairn-only credential; list_projects is filtered by GET /internal/v1/dispatch/projects items. Admission POST /internal/v1/dispatch/admit receives native_project_id, phase, intent_id, worker_profile_id. Response needs worker_name, agent_run_id, native identifiers, assignment, model, tool_names, deadline, operation_id, tool_token, agent_url, backend_token. Ready Pod verification is the control service's responsibility before granting admission. ensure_running also GETs /internal/v1/dispatch/runs/{id}; it cannot provision resources.

Core side effects go through POST /internal/v1/cairn/{native_project_id}/{action}, body {args:[arguments excluding project_id]}, response {status_code,data,text}. The adapter uses actual ApiResult, whose ok derives from status_code. All writes retain original native argument ordering. Control service must journal and reconcile writes and enforce current ownership/permission. Ambiguous admission is not retried. Unknown or failed executions stay locally blocked; restart permission is controlled by the persistent admission service.

GET /runs/{id}/output is persisted via POST /internal/v1/dispatch/runs/{id}/output {output,returncode,receipt} before native parsing. Finish sends {outcome}; it must be idempotent because a response loss is reconciled by the same run ID. A rejected native claim is finished as rejected. Original result parse failure disables native conclude fallback to avoid another model run. Remote process timeout raises reconciliation-required and never invents a stopped code. Pod cleanup remains solely with Task Runtime Controller.

The graph prompt reference is replaced with graph_read; assignment.graph_snapshot must contain the current native export as YAML string or native graph dict. Default prompt contracts and native output parsing/writeback are retained. Native Bootstrap always proposes complete; controller returns 409 while evidence conditions are unmet, using its native deferred-success path. Final Reason complete is accepted only after actual HTTP/file evidence satisfies controller checks.
