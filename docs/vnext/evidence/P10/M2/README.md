# P10 M2 production runtime / child evidence

Status: **reviewed / PASS for the defined hosted Explore M2 mechanism slice**. Locke's final rereview found all four original P2 items addressed.

The final current-intake case passed at tested HEAD d61cb91cac633edcff8830586307e6efa61ada95 with the related source tree clean and the temporary 0013 schema SHA-256 6803916d1c22f3df803c64d0a739df37b46f3b7329acb57388fe85e776dca815. The final product repair is 4268b6ae6fc6dec23226803007047ee9b53eacc8 and its recovery test is 0f545ba99eff00f7add8c614ffec7e7fc0d5d499. The real runtime service Thread fix is ad9a4c8a77f1d5ccafb37099137fbb91cad68014 with test source 7bc3d05539259e62557570d16f0370a9fdc063c2.

This is the hosted controller/Node/Python-child M2 slice. It does not accept all work kinds, Kubernetes/Pod isolation, P08 Session recovery/approval, W3 Session transport enabled, full P10, full P07, or real model effectiveness.

## Final targeted checks

| Check | Actual result | Evidence |
| --- | --- | --- |
| Four pure import/wire/profile contracts | passed in r1 batch | [r1 stdout](review-fix/raw/r1/pytest.stdout-stderr.txt) |
| Wrong actual Supervisor receipt profile | passed in r2 batch | [r2 stdout](review-fix/raw/r2/pytest.stdout-stderr.txt), [profile raw](review-fix/raw/r2/evidence/68b76ae26bcc/) |
| Wrong registered Pod UID | passed in r3 batch | [r3 stdout](review-fix/raw/r3/pytest.stdout-stderr.txt), [Pod raw](review-fix/raw/r3/evidence/2cabb5414cf6/) |
| Worker ready then revoked at output writepoint | passed in r6 batch | [r6 stdout](review-fix/raw/r6/pytest.stdout-stderr.txt), [race raw](review-fix/raw/r6/evidence/283331635b77/) |
| First receiver intake after real Worker revocation | passed in r6 batch | [revoked summary](review-fix/raw/r6/evidence/3094c7d71e0c/m2-result-summary.json), [revoked raw](review-fix/raw/r6/evidence/3094c7d71e0c/) |
| Current receiver raw-first partial publication recovery | 1 passed in 11.55s | [r7 stdout](review-fix/raw/r7/pytest.stdout-stderr.txt), [current summary](review-fix/raw/r7/evidence/b5cdd39aebb1/m2-result-summary.json), [current raw](review-fix/raw/r7/evidence/b5cdd39aebb1/) |
| Real service Thread owns DispatchJournal | 1 passed in 1.27s | [GREEN](review-fix/raw/local-checks/raw/runtime-thread-green.txt), [RED](review-fix/raw/local-checks/raw/runtime-thread-red-r2.txt) |

The current path consumed the real P09 run.dispatch_requested row through RuntimeDispatcher and DispatchOutbox, recorded GET before its single PUT, spawned the actual Node-managed Python child, held model traffic until the persisted P05 started observation, made two native SSE model requests and one actual ToolGate workspace read, then handled an injected 503 before controller intake. The source Worker archived the SDK. A second injected failure occurred after real P04 receive but before companion publication; the saved-submission path restored the exact SDK and binding pins, returned an accepted ResultReceipt with one accepted_shared Claim, replayed the same process, and made no additional model or tool request.

The revoked and writepoint cases returned historical_only with no new Claim. The ordinary Worker write returned 409 STALE_EXECUTION after real credential revocation. The Pod mismatch path recorded GET → PUT → GET, at most one PUT, controller 409 and no launch. Unknown settlement states never became a fabricated exit or release.

All r1–r7 stdout/stderr, exit codes, fingerprints, dirty patches and per-test records are retained under [review-fix/raw](review-fix/raw/). Failures are preserved rather than rewritten. [result-summary.json](review-fix/result-summary.json) maps final checks to raw directories, and [http-reproduction.md](review-fix/http-reproduction.md) describes the complete packet format.

Exactly 17 generated bootstrap run credentials were replaced with [REDACTED TEST RUN CREDENTIAL] in the publishable derivative. Authorization headers were already recorded as explicit redaction placeholders. No other request, response or SQL field was removed.

The byte-for-byte [initial and final reviews](review-fix/reviews/README.md) are archived with source SHA-256 values.

Verification screenshot:

![P10 M2 focused result](review-fix/screenshots/p10-m2-final.png)
