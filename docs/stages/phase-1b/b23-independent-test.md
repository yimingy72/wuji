# B2/B3 independent test preparation

Status: `executed`, bounded candidate checks complete.

This test worktree is based on the exact result of `git rev-parse 235f05f`:
`235f05f5afe8bc53ff70c8f2b07950d4c2e6fa32`, on
`codex/phase-1b-b23-test`. It follows the approved B2/B3 specification and
uses the public routes and DTOs in `packages/contracts/openapi.yaml`.

The prepared API file groups the minimum checks into six cases:

1. create, list, snapshot, cancel, and persisted event replay;
2. same-key replay plus two concurrent requests yielding one task;
3. idempotency mismatch and accepted-control replay ordering;
4. input digest mismatch, an expired preview, and an isolated legacy
   `can_create=false` preview;
5. Viewer read access, write denial, creator-only receipt visibility, and a
   cross-project read boundary;
6. one-event pages followed by an empty page that preserves its cursor.

`tests/api/test_phase1b_tasks.py` uses the run manifest only for fixture
credentials and database connection details. The management connection only
sets one isolated preview expiry and one isolated legacy preview blocker; it
does not contact a target or dump credentials. The test data is scoped to the
private `wuji-test` run.

The prepared browser case in
`tests/platform-browser/06-task-management.spec.ts` uses Chrome, intercepts
the committed create response with `route.fetch()` followed by a client-side
abort, reloads, verifies command-key reconciliation uses the original key,
opens the real task list/detail, and cancels the recovered task.

The directly affected B1 expectations now require operator task permissions,
Viewer `task.read`, a valid preview with `can_create=true` and no blockers,
and migration revision `20260910_0003`.

Execution used the exact integrated product candidate and private run file
recorded below. The commands were:

```text
./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_tasks.py -q
pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/06-task-management.spec.ts --workers=1
```

## Execution record

- Product candidate: `e76a265d445ae9548d7f56fdb85f9b8b5c005759`.
- Test script revisions: `83e45706f5114db3b4d503f441a8689e79b20fce`, then
  `868d477faa7a165a9f88bc6859a3cb01ed360bd2`, then the unique-name fixture
  correction `9ea345c86d8ac379e346a615add76991a11353ff`.
- Run: `p1a20260910t0159448786fa`, using the private manifest
  `work/run/b23-candidate.json`.
- API command exited 0: `6 passed in 12.65s`.
- The first Chrome attempt exited 1 after completing server commit,
  reconciliation, list, cancel, and snapshot checks; its only failure was the
  non-unique UI locator for the cancelled state. The exact-text fix was
  `868d477faa7a165a9f88bc6859a3cb01ed360bd2`.
- Chrome command with the unique task-name fixture exited 0: `1 passed in
  8.9s`.
- Evidence screenshot: `/Users/yym/Documents/ChatGPT/Wuji 自动化渗透平台/work/worktrees/phase-1b/artifacts/phase-1a/platform/p1a20260910t0159448786fa/b23-task-management.png`.
- No target traffic, runtime execution, pause/resume, artifact, or deferred
  unrelated suites were run. The first browser failure was corrected and the
  bounded browser rerun passed; no further rerun was needed.
