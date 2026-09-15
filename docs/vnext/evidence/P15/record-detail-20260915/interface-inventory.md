# P15 record-detail interface inventory

| Interface | Verification state | Scope and limitation |
| --- | --- | --- |
| Topology selection callback | verified | Controlled selection resolves follow-latest to one exact visible revision |
| Snapshot propagation | verified | Parent receives the actual `snapshot_id` returned by `TopologyContainer` |
| Record request path | verified | Encodes Task/type/id and requires exact `revision` plus current `snapshot_id` |
| Record response parser | verified | Rejects an outer reference that differs from the selected node revision |
| Intent record panel | verified / HTTP 200 | Shows admitted question and complete public Intent record |
| Origin record panel | verified / HTTP 200 | Shows name, scenario, desired/observed state and complete public Task view |
| Browser rendering | verified | Node click updates selected state and renders the fixed record; zero console errors observed |
| Record permissions | inherited and exercised | Browser gateway only permits the fixed Task; P13 reauthorizes snapshot guards in PostgreSQL |
| Artifact byte preview | not utilized | Separate authorized content route and preview policy remain future work |
| ViewStream / layout persistence | not utilized | Still required for full P15/M4 acceptance |
