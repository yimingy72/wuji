# P13 Kubernetes API interface inventory

| Asset / interface | Verification state | Scope and limitation |
| --- | --- | --- |
| `Deployment/api` | verified / Running | linux/arm64 public read API, source `24f984f`; local synthetic namespace |
| `Service/api:8443` | verified / reachable | TLS service port reached through local port-forward; CA verification enabled |
| `GET /api/v2/tasks/{task_id}/topology` | verified / 200 | P13 live snapshot and persisted view/materialization for one synthetic Task |
| Bearer boundary on topology route | verified / 401 | Missing bearer is rejected before projection access; no anonymous data |
| `ProjectionRepository` API composition | verified / source + live | Independent API Deployment uses `wuji_app`; full browser identity adapter is pending |
| Browser workbench session | not yet utilized | Web Pod is reachable at `44180`, but `apiBaseUrl`/identity entrypoint remain intentionally unconfigured |
