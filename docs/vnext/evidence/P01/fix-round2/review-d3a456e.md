# P01 scoped re-review — round 1

Date: 2026-09-13. Reviewer: current assistant, no subagents.

**Initial finding disposition: 3 ADDRESSED, 0 NOT ADDRESSED.** The durable evidence relocation, timeout/unknown publication behavior, and committed screenshot with provenance satisfy the three findings in `P01-review.md`.

**New breakage in `9186c1b..d3a456e`: 1 open Important / P2.** The newly published watchdog HTTP package uses the normal SDK package's fixed validation statement even though this run deliberately has no SDK and advertises no tools.

**Spec compliance: FAIL for round-1 acceptance while the new evidence-labeling defect remains open.** The raw watchdog observations are complete for what was captured, and the three original findings are addressed, but the published reproduction package makes claims contradicted by its own request.

**Code quality: CHANGES REQUIRED.** The timeout control flow is sound for the reviewed requirement; the shared HTTP renderer needs a scope-correct header for incomplete/watchdog evidence.

## Scope and evidence basis

- Worktree: `/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`; branch `codex/vnext-maf`; reviewed HEAD `d3a456ec15d70a4b363a6410702de37ae8889a21`. The worktree was clean at review entry.
- Fix range: `9186c1b895d3a1e710b495e03295cd43fc413710..d3a456ec15d70a4b363a6410702de37ae8889a21`; code fix commits `af4f609c28483de40df816bf57a299851923823b` and `1d779540f11bc9ce1aeaf0aa9357ff3e2f71c9d0`; documentation/evidence commit `d3a456e`.
- Read the complete `P01-review.md`, `P01-brief.md`, `P01-report.md` including its final round-1 addendum, and `P01-round1-review-package.md`. The package payload matches the actual `git diff -U5` after removing CR characters from byte-preserved HTTP evidence and its one extra final newline. The actual Git blobs and diff were used for byte-sensitive checks.
- This worktree has no `.codegraph/`; the review used scoped Git reads and direct file reads. No SDK implementation or unchanged SDK dependency path was re-audited.
- No suite or focused test was run. The reported `3 passed in 2.10s` on `1d77954` was checked against the committed log and code/evidence hashes. The earlier 13 SDK cases and five CLI gates remain historical evidence bound to `8c3fa9c`; they were not rerun or promoted to the fix commit.
- The only authored file is this review. No UI, browser, recapture, model, database, target, or network action was performed.

## Initial finding dispositions

### 1. ADDRESSED — durable evidence ownership and byte-preserved links

The current owner is explicitly Wuji vNext P01 documentation. Stable entry points are published in the stage [plan](../../../docs/stages/vnext-maf/plan.md), [acceptance record](../../../docs/stages/vnext-maf/acceptance.md), current [P01 report](../../../docs/vnext/P01-report.md), and [CapabilityRecord](../../../docs/vnext/capability-record.json). Current artifacts live under tracked `docs/vnext/evidence/P01/`, outside SDD scratch cleanup.

The [relocation manifest](../../../docs/vnext/evidence/P01/relocation.json) contains 13 source-to-destination mappings. All 13 destination hashes match both the recorded SHA-256 and the source bytes at the stated commit; the uncommitted initial review source also matches its historical copy. Git reports the original evidence files and original report as 100% renames. The historical CapabilityRecord is byte-identical to `9186c1b:docs/vnext/capability-record.json`, and the historical review is byte-identical to the current anchored `P01-review.md`.

The original [SHA manifest](../../../docs/vnext/evidence/P01/sha256.json) remains unchanged with its historical scratch keys. The original HTTP CRLF and pytest output whitespace remain intact. The current report's 43 local Markdown links resolve, all 24 current evidence/report paths extracted from the CapabilityRecord exist, and all durable artifacts, including the screenshot, are tracked. Scratch delivery paths are no longer tracked and no current CapabilityRecord link points into them.

Verdict: **ADDRESSED**.

### 2. ADDRESSED — finally-safe TimeoutExpired evidence and blocked/nonzero behavior

`scripts/vnext/probe_maf.py:243-291` catches the real `subprocess.TimeoutExpired` at the process boundary and records the command, timeout, UTC deadline observations, captured stdout/stderr as text and base64, `exit_code=null`, `outcome=timed_out`, and `execution_outcome=unknown`. A result file present at timeout is preserved as raw base64 and marked `available_at_timeout`; absence is marked `missing_at_timeout` rather than converted to success or zero execution.

`scripts/vnext/probe_maf.py:416-492` publishes per-case HTTP, case data, available event bytes and parsed event prefixes from `finally`, then publishes aggregate `probe.json` and the HTTP package from the outer `finally`. An incomplete case breaks the mode loop, so there is no retry, resume, or later SDK case. `capability_outcomes` returns a blocked watchdog result with unknown execution, and `main` skips distribution checking and returns 2. The `1d77954` preflight also refuses reused named evidence destinations before entering the publication `finally`, preserving prior bytes.

The committed final observations corroborate the control flow:

- [Available-observation process](../../../docs/vnext/evidence/P01/fix-round1/final/true/roundtrip/initial-process.json): real timeout, null worker exit, unknown execution, exact stdout/stderr, result available at timeout, one captured HTTP exchange and one captured event.
- [Unknown-observation process](../../../docs/vnext/evidence/P01/fix-round1/final/false/roundtrip/initial-process.json): real timeout, null worker exit, unknown execution, exact stdout/stderr, no fabricated result, and null observed HTTP/event counts.
- Both CLI records return a blocked summary and the test asserts exactly one process start, so no automatic retry occurs. The committed [final focused log](../../../docs/vnext/evidence/P01/fix-round1/fix-round1-final.txt) reports `3 passed in 2.10s` on `1d77954`, including the no-overwrite guard. All 49 paths in the final fix-round SHA manifest match their recorded hashes.

The three current code files match the CapabilityRecord hashes and the `1d77954` Git blobs exactly; `d3a456e` did not modify them.

Verdict: **ADDRESSED**.

### 3. ADDRESSED — committed screenshot and provenance

The actual [JPEG screenshot](../../../docs/vnext/evidence/P01/screenshots/test-results.jpg) is committed at `d3a456e`, is 160,975 bytes and 1280×720, and has SHA-256 `0e85d91474dbd586b83d886bb5b74efe3533a88f7adeab358642cca0a2a8b7a7` both in the worktree and the commit blob. Direct `view_image` inspection shows a rendered page titled “Wuji P01 · Recorded SDK evidence,” the tested code SHA `8c3fa9c…`, the original `13 passed in 11.40s` output, and the recorded CLI output.

![Main-controller capture of original P01 SDK evidence](../../../docs/vnext/evidence/P01/screenshots/test-results.jpg)

The [provenance record](../../../docs/vnext/evidence/P01/screenshots/provenance.json) identifies a main-controller handoff from a permitted loopback browser page, records the media type, dimensions, image digest, displayed test commit, and exact hashes of `green-13.txt` and `cli.txt`. It truthfully leaves the unavailable capture time unspecified, states that the image was supplied after the `9186c1b` review, and retains the historical denial record without claiming a recapture or SDK rerun by this fix round.

The complete original [HTTP reproduction package](../../../docs/vnext/evidence/P01/http-reproduction.md) remains linked alongside the screenshot and retains methods, URLs, headers, request bodies, response headers/statuses, and response bodies.

Verdict: **ADDRESSED**.

## New breakage in the fix range

### Important / P2 — watchdog HTTP package claims SDK validations contradicted by its request

**Location:** `scripts/vnext/probe_maf.py:406-413` and `:487-491`; committed result `docs/vnext/evidence/P01/fix-round1/final/true/http-reproduction.md:1-21`. Current report links it as the complete watchdog HTTP record at `docs/vnext/P01-report.md:215`.

`exchange_markdown` always emits this statement:

> Validation points: explicit nonempty tool advertisement; native call-p01-read routing; actual file reads; approval rejection; finite HTTP failure.

The new timeout `finally` path now calls that renderer for an incomplete watchdog-only case. Its sole request explicitly says `X-P01-Purpose: watchdog-no-sdk`, uses model `watchdog-no-sdk`, and contains `"tools": []`. It does not exercise native MAF routing, approval rejection, or a 503 failure. The no-observation package contains the same validation statement with no HTTP exchange at all.

The raw method, URL, headers, body, response and timeout records are preserved correctly, and the surrounding report accurately says this child is not MAF. The fixed package header nevertheless attributes validations that this artifact cannot establish. That conflicts with P01's requirement to derive claims from actual observations and weakens the complete-request-package handoff precisely where the new timeout path is meant to distinguish known observations from unknown execution.

This is new behavior in the reviewed range even though the literal header predates it: before round 1, `exchange_markdown` was published after the complete six-case SDK probe, where the listed validation points were represented. Round 1 newly invokes it from `finally` after the first incomplete watchdog case and publishes the resulting partial package as watchdog evidence.

**Required resolution:** make the reproduction header describe the supplied cases and observation state. For watchdog output, state only that the package preserves HTTP observed before timeout, that execution remains unknown/blocked, and that it proves no SDK capability. When no exchange was captured, state that explicitly. Add a focused assertion covering the generated header and regenerate the affected watchdog HTTP evidence and hashes. Preserve the current raw records and history; do not rerun the unchanged SDK suite.

No new target asset or interface was discovered, so no asset inventory update is required.

## Verification summary

- Initial findings: **3 ADDRESSED / 0 NOT ADDRESSED**.
- New breakage: **1 open Important / P2**.
- Durable relocation: **13/13** source/destination mappings matched; current report links **43/43** resolved; CapabilityRecord paths **24/24** existed.
- Fix evidence: **49/49** SHA-manifest entries matched; all JSON parsed; scoped code/prose `git diff --check` returned 0.
- Screenshot: committed JPEG visually inspected; dimensions and commit/worktree SHA matched provenance.
- Tests: no reviewer rerun. Historical focused result remains `3 passed in 2.10s` on `1d77954`; unchanged SDK result remains `13 passed in 11.40s` plus five CLI gates on `8c3fa9c`.

