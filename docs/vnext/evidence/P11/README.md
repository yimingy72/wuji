# P11 evidence index

- [Task creation entry](task-creation-20260915/README.md): `POST /api/v2/tasks`, migration
  `vnext_0019_p11_task_creation`, published-profile catalog, real K8s 201/idempotent replay/409 and the
  created Task rows.
- [Task admission and control commands](task-admission-control-20260915/README.md): owner-side
  `publish_task_admission`, the same Task accepting `start`/`pause`/`cancel` through the runtime control
  API, with `runs=0` explicitly stated (no process-stop claim).

Still open: owner tooling that derives admission rows from deployment configuration, and the real
command → Pod/child process-stop observation loop.
