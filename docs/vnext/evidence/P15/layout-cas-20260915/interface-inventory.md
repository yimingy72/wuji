# P15-L personal layout interfaces and assets

Verification state is scoped to the isolated `wuji-vnext-test` slice and code revision
`b465238486d3ffd0476bbfa9384dcf60656be237`. It does not describe production identity,
external targets or other work kinds.

| Asset / interface | Owner | Verification state | Scope and implication |
| --- | --- | --- | --- |
| `Deployment/api` | Kubernetes | verified / 1 of 1 Ready, platform image `sha256:6507e76a…` | Serves the isolated public API including the layout routes |
| `Deployment/wuji-web` | Kubernetes | verified / 2 of 2 Ready, `wuji-web@sha256:db056ea8…` + `wuji-vnext-platform@sha256:6507e76a…` | Nginx frontend plus loopback browser-session gateway |
| `Service/wuji-web` | Kubernetes | verified / `LoadBalancer`, external hostname `localhost`, `44180:32452/TCP` | Browser entry point used for every request in this package |
| `Job/p15l-migrate-0018` | Kubernetes | completed / one-shot | Applied `vnext_0018_p15_layout` with the `wuji_migration` role; no Task or Run data was inserted |
| `vnext.layout_preference` | PostgreSQL | verified / RLS enabled with `layout_read`, `layout_insert`, `layout_update` | One row per `(tenant, project, task, subject, view, schema)`; only the acting subject's row is readable or writable |
| `vnext.schema_migration` | PostgreSQL | verified / head `vnext_0018_p15_layout` | Layout is the latest ordered migration; older heads remain applied |
| `GET /api/v2/tasks/{task_id}/layouts/{view_name}` | Wuji public API | verified / 200, 401, 404, 409 | Returns the subject's preference or the default revision 0 |
| `PUT /api/v2/tasks/{task_id}/layouts/{view_name}` | Wuji public API | verified / 200, 404, 409, 422 | `If-Match` compare-and-swap, bounded JSON, anchor validation against the authorized projection |
| Browser gateway layout proxy | `services/wuji-web-gateway` | verified / GET and PUT only | Exact Origin, `application/json`, `If-Match` and 262144-byte bound; no other write route is exposed |
| `PUT`/`POST /api/v2/tasks/{task_id}/commands` | browser gateway | verified / 404 (PUT) and 405 (POST), never forwarded | Task control writes stay closed in the browser entry point |
| `wuji-vnext-build-registry` | Docker Desktop infrastructure | verified / active on `127.0.0.1:56615` | Node-reachable image distribution for the local cluster; not a Wuji request-serving component |
| Production OIDC / project selection | P11 product scope | not implemented | The browser session is the local mechanism operator minted by the BFF |
| ViewStream / reconnect / artifact preview | P15 remaining scope | not implemented | Layout CAS does not imply stream, preview or governance coverage |
