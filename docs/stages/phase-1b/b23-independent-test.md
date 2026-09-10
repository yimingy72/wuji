# B2/B3 independent test preparation

Status: `prepared`, execution pending the frozen integrated candidate.

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

Execution is intentionally not recorded here until root supplies the exact
integrated candidate SHA and private run file. The intended commands are:

```text
./scripts/uv.sh run --frozen pytest tests/api/test_phase1b_tasks.py -q
pnpm exec playwright test --config playwright.platform.config.ts tests/platform-browser/06-task-management.spec.ts --workers=1
```

The report must be updated after execution with the tested SHA, run id,
commands, exit codes, elapsed seconds, and actual pass/fail/deferred evidence.
