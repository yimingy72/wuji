# M2 child/controller interface inventory

Status: reviewed / PASS for the defined hosted Explore M2 mechanism slice; 4/4 original P2 findings addressed.

| Interface | Verification state | Evidence boundary |
| --- | --- | --- |
| RuntimeDispatcher / real DispatchOutbox | verified for Explore slice | Reads authorized run.dispatch_requested, fixed Assignment and configured work kind; no caller operation |
| DispatchJournal / CLI service Thread | verified separately | Real SQLite attempted row created, used and closed on one owner Thread; not full HTTP service e2e |
| Supervisor HTTP | verified | Complete passive GET/PUT records, query-before-PUT and at most one PUT after unknown |
| Exact harness profile | verified | Actual mutated model-profile receipt rejected before P05 |
| Receiver Pod UID | verified | Current registration mismatch returned 409 and created no launch |
| P05 start barrier | verified | Same child, real persisted started observation, zero earlier model traffic |
| MAF / ModelGate / ToolGate | verified for synthetic Explore | Two native SSE requests and one real workspace read; localhost model only |
| P03/P04 current result | verified | Actual Artifact/Observation/EvidenceReceipt and accepted Claim from actual tool evidence |
| Revoked first intake | verified | Historical-only receipt, no Claim/Intent, no resumed Worker execution |
| Worker write revocation | verified | Actual Worker output HTTP 409; receiver settled retained bytes historically |
| Partial result publication | verified | Real P04 receive followed by injected companion failure, then exact SDK/binding pin repair |
| Single credential bootstrap | verified | Node adapter → receiver-bootstrap → P09 scoped retrieve → private Worker file |
| 0013 retained authority | verified in M2 runs | Receiver/run/digest/source/snapshot exact; no private table SELECT grant or fake Principal |
| Session transport enabled / P08 0014 | not verified here | M2 used session_transport=False |
| Reason/report work kinds | not verified here | This slice configured Explore only |
| Kubernetes/Pod isolation and P20 deployment | not verified | Hosted local process evidence only |
