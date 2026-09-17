# P15 evidence index

- [Snapshot-bound record detail](record-detail-20260915/README.md): real browser node selection, fixed-snapshot RecordView reads, screenshot and complete HTTP exchanges.
- [Current record-detail interface inventory](record-detail-20260915/interface-inventory.md)
- [Historical snapshot browser](history-browser-20260915/README.md): saved snapshot directory, exact history selection, historical record detail, screenshot and complete HTTP exchanges.
- [Historical browser interface inventory](history-browser-20260915/interface-inventory.md)
- [Personal layout CAS](layout-cas-20260915/README.md): per-subject layout preference with `If-Match` CAS, 0018 migration, Kubernetes API/BFF/web paths, browser refresh persistence, live conflict evidence, the pre-fix write-back defect and its fix.
- [Layout CAS interface inventory](layout-cas-20260915/interface-inventory.md)

- [Authorized ViewStream](view-stream-20260917/README.md): `vnext_0025_p15_view_stream` lets one saved view advance; `GET /api/v2/views/{view_id}/events` streams bounded node/edge patches with resets, the same-origin adapter relays only views the pinned Task published, and the workbench followed a real pause/resume on the live canvas without a reload.

Reconnect/reset edges (expired view, oversized change) are covered by tests rather than a live run; layout CAS is verified for the two knowledge views.
