# P10 M2 four-P2 repair report

The four findings in P10-M2-review.md have executed closure evidence. Locke's final rereview is PASS with all four addressed for this defined M2 slice.

The production chain now has a bounded RuntimeDispatcher service entry that consumes a real P09 outbox row outside network transactions. DispatchOutbox queries the original operation before one PUT and keeps its attempted journal on the runtime consumer Thread. Node bootstrap is the only credential delivery path.

RegisteredRun derives the exact harness profile ref and digest from the frozen TaskDefinition and exact work kind. Receipt validation rejects model/runtime refs. Receiver start authorization compares the complete receiver registration, including Pod UID, before launch.

Retained results use the actual verified receiver subject and a per-Run binding. Normal Worker writes recheck and lock the current credential. Current retained intake follows ordinary accepted P04 behavior; revoked intake is historical_only and creates no Claim or Intent. The receiver does not reconstruct a Worker Principal and the Worker does not gain can_settle.

The current path also covers the real raw-first recovery window. After P04 receive persisted the raw submission, a fault interrupted companion publication. Replay accepted only the exact source Worker SDK archive, rebuilt the deterministic context/tool binding, pinned one SDK and one binding under the stable result publication, re-read the three expected roles, and then used P04 reconcile. P04 remains the result authority.

## Source provenance

- Initial M2 core: 6e90a97fa507717e4f8b06229ca1d2fc5e1593c4
- Initial actual child tests: e40e7e2100cf528bf7eba797176b9bd033be48c3
- Strict Node settlement: 87e13042a62768b5ad1206f6e7837dee7b28c607
- Runtime/retained-result production source: 069b24280d45f287a0216010179c5738c23f93eb
- Runtime tests: 1304e93cbd17c55bba5bec61b3994cbfb7ff935f
- Credential locks: 750277c3dbb9c4eaa514f897da12f7ff90756c64
- Work-kind selection: b8b2b48aca385c86342ccd84b54e86b2340a0227
- Retained prelock fix: df24609e42e8933758ece80ad7ca0dccfb17728f
- Await-start/HTTP audit: 53f2d4671e745ab048bb7a2594ec3b42e2af1cfe
- Private binding authority: 854ec4826387fe2fb8ebb28be5879bc991c92c0b and 1efc3117202d50c5079f636bc5bfd3b5db9d6177
- Exact retained snapshot read: be7e7decd6d6a6696a6c949d94eae5580de0f148
- Explicit Session-disabled M1 boundary: 146d6d22905f2bee9b037bb62f1653518eb4a1fc
- Runtime Thread ownership: ad9a4c8a77f1d5ccafb37099137fbb91cad68014
- Correct retained-intake ordering tests: 7bc3d05539259e62557570d16f0370a9fdc063c2
- Mixed-writer companion repair: 4268b6ae6fc6dec23226803007047ee9b53eacc8
- Partial-publication recovery test: 0f545ba99eff00f7add8c614ffec7e7fc0d5d499
- Final tested HEAD: d61cb91cac633edcff8830586307e6efa61ada95

B2 source 1f17179 and follow-up 89e0813 were present in the frozen tree, but M2 explicitly used session_transport=False. Their presence is not P08 or W3-enabled acceptance.

## Round history

| Round | Actual result | New information retained |
| --- | --- | --- |
| r1 | 4 passed, 5 failed in 14.54s | Pure checks passed; real outbox selected an unsupported Reason profile |
| r2 | 1 passed, 4 failed in 57.52s | Wrong profile passed; exposed await transition, retained prelock and audit gaps |
| r3 | 1 passed, 3 failed in 65.59s | Pod path passed; exposed private retained table permission |
| r4 | 3 failed in 23.46s | Durable receipts reached P04 but exact snapshot reader denied receiver |
| r5 | 3 failed in 31.70s | Current accepted path reached; corrected test intake ordering/time representation |
| r6 | 2 passed, 1 failed in 45.26s | Revoked first intake and Worker writepoint passed; current exposed mixed-writer partial publication |
| r7 | 1 passed in 11.55s | Current accepted result and raw-first companion recovery passed |

The DB-free runtime Thread check separately passed in 1.27s after an exact ProgrammingError RED. All outputs and failures remain in raw/.

This evidence confirms the specified hosted Explore mechanism only. It does not claim Supervisor product completion, all work kinds, Session recovery, Kubernetes isolation, P08, full P10, full P07, or real model quality.
