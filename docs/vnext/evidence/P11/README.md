# P11 evidence index

- [Task creation entry](task-creation-20260915/README.md): `POST /api/v2/tasks`, migration
  `vnext_0019_p11_task_creation`, published-profile catalog, real K8s 201/idempotent replay/409 and the
  created Task rows.
- [Task admission and control commands](task-admission-control-20260915/README.md): owner-side
  `publish_task_admission`, the same Task accepting `start`/`pause`/`cancel` through the runtime control
  API, with `runs=0` explicitly stated (no process-stop claim).

- [Pod-level cancel stop](pod-stop-20260915/README.md): the real Task Pod (new agent/kali digests)
  deleted within 5 s of an accepted `cancel`, with `reconciling` kept and no fabricated exit
  observation; also records the expired-token/image-roll environment work and the open
  worker-assignment dispatch finding.

- [Stage B branch 1 round trip](stage-b-roundtrip-20260916/README.md): a Task created through the
  public route reaching an accepted result and a real exit on the fixed `9e5bfb6` images, including the
  refused tool call whose bounded code the child now names, and the buffered-response defect that the
  first run of the branch exposed.

Still open: owner tooling that derives admission rows from deployment configuration, a runtime attempt
that carries no worker-assignment dispatch finding, Stage B branches 2 and 3 on their own fixtures, and
the multi-Task runtime host that would prove one Task is not stopped with another.
