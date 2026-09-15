# P15 historical browser interface inventory

| Interface | Verification state | Scope and limitation |
| --- | --- | --- |
| `GET /api/v2/tasks/{task_id}/snapshots` | verified / 200 | Seven saved public summaries returned; no internal event sequence field |
| Snapshot summary parser | verified | Fixed field allowlist; rejects injected `event_seq` and malformed query documents |
| History selector | verified | Browser lists saved snapshots with creation time and opaque ID prefix |
| History topology request | verified / 200 | `mode=history` and exact `snapshot_id=529f4925…` returned the selected materialization |
| History mode label | verified | Browser displays `历史只读` while the saved snapshot is selected |
| Historical record detail | verified / 200 | Origin RecordView uses the same selected snapshot ID |
| Live mode return | implemented, not separately evidenced here | Selector offers `实时视图`; history evidence focused on the saved path |
| History pagination | implemented for opaque cursor | Current directory fits one page, so load-more behavior was not triggered |
| ViewStream/reconnect | not utilized | Remains a separate P15 task |
| Layout CAS | not utilized | Remains the next workbench persistence task |
