# P14 Kubernetes browser interface inventory

| Asset / interface | Verification state | Scope and limitation |
| --- | --- | --- |
| `Deployment/wuji-web` | verified / 2 of 2 containers Ready | Nginx Web and loopback browser gateway in one Pod; no ServiceAccount token |
| `GET /healthz` | verified / 200 | Same `wuji-web` Service used by the browser at port 44180 |
| `POST /auth/login` | verified / 200 | Exact local Origin required; creates HttpOnly, SameSite=Strict, 30 minute cookie |
| `GET /auth/session` | verified / 401 then 200 | Anonymous rejected; active cookie returns only display name and fixed tenant/project/task metadata |
| Gateway to `Service/api` | verified / 200 | Each allowed read receives a newly signed bearer with at most 60 seconds lifetime |
| `GET /api/v2/tasks/{task_id}/topology` | verified / 200 | Browser received the persisted P13 snapshot and rendered both visible nodes |
| Cross Task topology path | verified / 404 | Gateway refuses a Task other than its fixed deployment binding before upstream I/O |
| `POST /auth/logout` | verified / 204 then 401 | Deletes the browser cookie; corrected curl jar and automated test both confirm invalidation |
| React Flow canvas | verified / rendered | Controlled canvas rendered the real snapshot; no browser console errors observed |
| Topology list view | verified / rendered | Both `intent@1` and `origin@1` visible with `admitted` and `ready` states |
| Browser bearer exposure | verified absent for this slice | Runtime config and browser responses contain no bearer; internal bearer exists only inside gateway memory |
| Production OIDC / organization identity | not utilized | This is a local mechanism session adapter, not the final production identity flow |
| Layout CAS, record panel, ViewStream | not utilized | Remain P15/M4 follow-up work |
