# P01 initial review

Date: 2026-09-13. Reviewer: current assistant, no subagents.

**Spec compliance: FAIL — P01 delivery is not accepted at the reviewed HEAD.** The recorded local SDK feasibility results are supported; evidence ownership, the timeout failure-record path, and the required screenshot remain open in this revision.

**Code quality: CHANGES REQUIRED.** The real SDK integration is credible and appropriately isolated, but its outer watchdog bypasses the probe's durable failure reporting. The evidence handoff also needs a durable owner.

**Findings: 3, all Important / P2.** The screenshot finding is an acknowledged delivery blocker, not a claim that the SDK tests failed. No Critical / P1 finding.

## Scope and evidence basis

- Worktree: `/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`, branch `codex/vnext-maf`.
- Base: `c9871a66dcebb0ac74205bbae8e94ed00cd1892e`.
- Head: `9186c1b895d3a1e710b495e03295cd43fc413710`.
- Implementation commit: `8c3fa9c193927b77f076b78a84cd040ec10f3e00`; initial evidence commit: `1eccff9`.
- Read P01-brief.md, P01-report.md and P01-review-package.md; checked the actual three-commit diff. Read SPEC S08/S09/S17, PLAN's P01 and test-boundary provisions, decision-register D04/D06/D09, implementation-baseline, the background index and stage entries. No broad repository scan.
- The worktree was clean at entry and has no CodeGraph index. Direct reads and narrowly scoped searches were used. Later, an unrelated-to-this-write untracked `docs/vnext/evidence/` appeared; it was left untouched.
- Read-only checks used the existing venv's `python -B` for installed metadata, public API signatures, file/wheel hashes and existing JSON/HTTP records, plus scoped Git reads. No pytest, SDK probe, model request, package installation, database or browser run was performed by this reviewer. The only authored file is this report.

The user's later context update identifies `docs/vnext/evidence/P01/screenshots/test-results.png` as a new, uncommitted actual CUA screenshot of a dedicated loopback page containing recorded synthetic results. It is outside `c9871a6..9186c1b` and was not used to change the anchored verdict. It can address finding 3 together with the evidence-ownership fix in a scoped re-review. The original file:// and Terminal/Codex denials remain historical facts reported by the implementer; this review neither repeats nor rewrites them.

## Findings

### 1. Important / P2 — Permanent evidence links point into a workspace scheduled for cleanup

**Location:** `docs/vnext/capability-record.json:1467` and `:1468`; additional affected links at `:1340`, `:1364`, `:1372`. Handoff instructions: `.superpowers/sdd/vnext-v2/P01-report.md:125` and `:127`.

The durable CapabilityRecord points to the complete HTTP package, pytest raw record, test logs and screenshot instructions under `.superpowers/sdd/vnext-v2/`. Git confirms that the report and ten evidence files are tracked despite `.superpowers/sdd/.gitignore:1` matching them. Tracking prevents their loss through ordinary ignored-file cleaning, but does not establish an exemption from the SDD workspace deletion workflow.

The installed SDD workflow explicitly describes this as scratch at `/Users/yym1ng/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/skills/subagent-driven-development/SKILL.md:153` and directs deletion of the plan workspace at `:483`. This is an assessed handoff conflict, **not authorization to run cleanup during this review**. The stage plan uses the ledger for task records (`docs/stages/vnext-maf/plan.md:8`), but the reviewed change does not resolve retention ownership or publish stable replacement links before that cleanup.

If the documented workspace deletion is applied, tracked files become deletions and the CapabilityRecord's current-tree links break. Git history still permits recovery, and the CapabilityRecord embeds the CLI SDK/HTTP observations; therefore this is not a claim that all evidence is already lost. However, those facts do not preserve usable current links to the separate pytest observations, red/green logs, reproduction package and report. The report's statement that the screenshot is the *only* delivery gap (`P01-report.md:131`) overlooks this handoff risk.

**Required resolution:** Archive the report and required evidence under a durable, task-owned documentation/evidence location, or explicitly establish and enforce an equivalent retention exception. Publish the owner and stable links through the implementation/stage index. Copy raw files byte-for-byte, verify their existing digests, and add a relocation mapping if paths change. Preserve the original checksum list and historical reports/check results; a new location manifest or addendum must not rewrite the old run, SHA or whitespace-check outcome. Do not delete scratch originals before verified durable references exist. This relocation needs link/hash checks, not another unchanged SDK test run.

### 2. Important / P2 — The outer subprocess timeout loses the failure evidence instead of producing a blocked record

**Location:** `scripts/vnext/probe_maf.py:246`–`:253`. Propagation and lost captures: `:383`–`:396`; aggregate publication: `:402`–`:404`; CLI boundary: `:422`–`:427`.

The probe deliberately supplies `timeout=30` to `subprocess.run`, but does not catch `subprocess.TimeoutExpired`. If the watchdog expires during worker startup, SDK execution or shutdown, execution exits before constructing or writing the process record. The exception propagates through `run_probe`; the fixture context closes, but the captured in-memory HTTP exchanges are not copied to `http.json`/`case.json`, and no aggregate `probe.json`, reproduction package or capability failure summary is published for that invocation. The CLI's exception handler begins only *after* `run_probe` returns, so it cannot handle this path.

This is a control-flow defect established by source inspection, **not an observed timeout in the archived successful runs**. The child remains bounded by the watchdog and the CLI fails nonzero; the issue is missing structured evidence, not a false exit-0 claim or an assertion that the process runs forever. Existing tests exercise a prompt HTTP 503, not watchdog expiration (`tests/vnext/test_dependency_probe.py:132`). A 503 cannot validate this exception path.

P01 requires actual commands, exit outcomes, observations and untested/blocked states to be saved (`docs/vnext/PLAN.md:170`; P01-brief.md:44). Losing precisely the observations needed to distinguish an SDK capability failure from a startup/shutdown problem defeats that contract and the CLI's advertised gated reporting.

**Required resolution:** Handle the watchdog exception at the process boundary, preserve its captured stdout/stderr and command/time-limit context, and retain available worker/HTTP/read observations in a `finally`-safe publication path. Record timeout/unknown outcome explicitly; do not fabricate a successful exit code, an SDK error response or zero execution count from missing evidence. Return nonzero with a blocked summary and do not retry the SDK operation. A follow-up should verify only this affected watchdog/reporting path using a real bounded harmless process; it must not substitute SDK/business behavior in the existing feasibility evidence. No such fault injection was run during this read-only review.

### 3. Important / P2 — Required verification screenshot is absent at the reviewed HEAD

**Location:** `docs/vnext/capability-record.json:1469`–`:1473`; `.superpowers/sdd/vnext-v2/P01-evidence/screenshots/README.md:5`; `.superpowers/sdd/vnext-v2/P01-report.md:123`–`:125`.

The reviewed CapabilityRecord has screenshot status `blocked` and an empty `paths` array. Its tracked screenshots directory contains only the README. This meets the requirement to report the omission honestly, but not the user's required delivery condition of at least one actual verification screenshot, stored in `screenshots/` and referenced with an image link. The full HTTP package is present; the screenshot half of that condition is not.

**Required resolution:** Include and link an actual screenshot of the recorded synthetic results in the durable P01 evidence location, retaining its capture provenance and the original blocked history. The later user-described loopback screenshot is an appropriate candidate for the next revision; check its contents, ownership and links in that scoped re-review. Do not claim it existed at `9186c1b`, rerun unchanged SDK tests merely to add the image, or replace the historical denial with a rewritten success record. Until the updated artifact is included and reviewed, the initial delivery verdict remains blocked.

## Verified substance of the implementation

**Actual installation and public API use.** Current Python is 3.13.15. The existing venv contains 26 distributions, exactly matching the record; its lock has 28 entries. Core 1.18.0 matches wheel SHA-256 `75f2fac5eed229c62f0665630cf1478eb45204bde41200a4c94dab57d441cc84`; OpenAI adapter 1.14.3 matches `b24b19b641531ef09e5cf52d5e5d20ba1be7299477d721e3516fc2da55e7f1ef`. Independently reading the cached wheels and installed files found zero mismatches across 111 and 11 files respectively, excluding the install-rewritten RECORD as disclosed. These are installed release bytes, not just pyproject strings or a source checkout.

All nine recorded inspected signatures match the currently installed objects: create_harness_agent, Agent.run, AgentSession.to_dict/from_dict, Content.from_dict/to_function_approval_response, tool, OpenAIChatCompletionClient and AsyncOpenAI. Public exports were checked in the installed distribution. Implementation modules with underscore names in introspection/tracebacks do not make the public imports private API usage. The worker imports through `agent_framework` and `agent_framework.openai` and restores opaque Session/Content dictionaries without patching SDK code (`scripts/vnext/probe_maf.py:163`, `:212`).

**Real protocol, function and restoration observations.** Both the archived pytest probe and CLI probe contain the following independently read counts:

| Case | Initial HTTP | Restore/resume HTTP | Actual fixture reads | Worker exit codes |
| --- | ---: | ---: | ---: | --- |
| roundtrip + settled restore | 2 | 1 | 1 | 0, 0 |
| approval + approve | 1 | 1 | 1 | 0, 0 |
| approval + reject | 1 | 1 | 0 | 0, 0 |
| unknown tool | 1 | 0 | 0 | 2 |
| HTTP 503 | 1 | 0 | 0 | 2 |
| nonexecuting stub | 2 | 0 | 0 | 0 |

Each run therefore has 9 worker processes and 11 HTTP exchanges. The protocol is actual `POST /v1/chat/completions`, not Responses or a renamed substitute. All 11 request bodies per run advertise exactly `read_record` with a required string `record_id`. Request/response Content-Length values match the full recorded bodies; response HTTP framing is retained. Fixture hashes/read values and native dispatch frames match. The second roundtrip request carries the real fixture tool result. Settled restoration uses distinct PIDs and an identical exported/imported Session boundary, with the original tool result and assistant reply visible in the new HTTP request.

For both approval cases, there are zero reads before resume. A new process restores the original Session and approval Content; approval `id` and complete nested function call are retained, including the separate protocol `call_id`. Approve executes one real read, reject executes none and returns the native rejection tool message. For example, the CLI approve path uses PIDs 4834/4900, approval ID `af-call-cbf8328037ab4f6187935b15cc9ab663` and protocol call ID `call-p01-read`. These are observations, not a fabricated approval boolean contract.

The only test-side peer is the permitted synthetic HTTP model (`tests/vnext/maf_fixture.py:17`). The function itself reads a real file in the actual SDK worker (`scripts/vnext/probe_maf.py:173`). The stub is explicitly a negative control and has zero real reads despite an ordinary model reply. There is no test-side business state machine or SDK substitute supporting these results.

**Isolation and finite behavior.** D04 permits the dedicated uv wrapper. The root pyproject, lock and wrapper are unchanged. The new projects own their workspace/lock, and recorded child commands use the new venv with a restricted environment. The recorded distribution/module inventories and commands contain no Cairn/Pi/Claude CLI runtime. Actual remote/production deployment, images, mounts and archive migration remain outside P01 and unverified.

The loopback URL check, synthetic key, `trust_env=False`, disabled telemetry, disabled default tools/providers and explicit tool list are consistent with this probe's scope. Public Harness construction confirms the optional outer loop is not installed when `loop_should_continue` is None. Native tool approval still operates through the function declaration; disabling automatic approval does not replace it with test logic.

The HTTP 503 observation contains exactly one request and no tool execution, supporting the configured zero transport retries. Request timeout is 5 seconds, Agent.run has a 20-second wrapper, and the process has a 30-second watchdog. SDK invocation limits are configured through real supported fields. Function-count and duration limits are best-effort at batch boundaries, as disclosed; installed SDK code also has a final tools-disabled response path on iteration exhaustion. These controls establish finite local behavior, not a strict product request/financial quota or proven arbitrary cancellation/recovery. Finding 2 concerns retaining evidence when the outer limit fires.

**CLI gate truthfulness within the observed run.** `capability_outcomes` checks the roundtrip/read counter, cold Session equality, native approve/reject linkage, nonempty advertised tools and the expected finite HTTP error. It does not equate a child exit 0 with capability success. The unknown-tool and 503 child exits of 2 are appropriate negative observations; the parent CLI's five local passes do not assert that every child succeeded. Distribution checks separately make the CLI fail nonzero on verification error. There is no basis to promote those five local checks to G2/G4 or complete product acceptance.

## Historical test and immutable-evidence reconciliation

- Read the preserved RED (1 failure), initial implementation run (9 passed / 2 failed), corrected run (11 passed), gate RED (2 failed / 11 deselected), final green (13 passed in 11.40s), and CLI five-pass logs. The two initial failures concern confusing native Content ID with model call ID; the current assertions retain both IDs and the full original call. The final test file has 12 test functions and 13 parameterized cases, consistent with the reported count.
- The final pytest/CLI exit codes are recorded in the implementation report/CapabilityRecord; the short pytest log itself does not independently encode a shell exit code. This review accepts them as attributed historical run records, corroborated by the raw observations, not as fresh reviewer executions.
- All nine current code/lock/test file hashes match the CapabilityRecord and `git show 8c3fa9c:<path>`. All four design-source hashes match. No changed implementation requires rerunning those successful cases merely for this review.
- All nine files listed in P01-evidence/sha256.json match their recorded hashes. Those files and the checksum list are byte-identical to their tracked `1eccff9` versions. The archived pytest-probe.json is byte-identical to `work/p01/final/probe.json`; the HTTP reproduction package is byte-identical to `work/p01/cli/http-reproduction.md`. Embedded CLI raw records and dependencies equal the original CLI JSON files.
- The review package matches the actual commit diff after CRLF normalization, but is not a byte-preserving raw archive: it has normalized the 264 HTTP CRLF sequences. The authoritative HTTP archive still retains those 264 sequences. The package is usable as a review derivative; it must not replace or be hashed as the original HTTP evidence. No original was normalized by this review.
- Full existing HTTP evidence: [P01 reproduction package](P01-evidence/http-reproduction.md). Existing test record: [pytest observations](P01-evidence/pytest-probe.json). Existing integrity list: [SHA-256 manifest](P01-evidence/sha256.json). **Screenshot at reviewed HEAD: absent**, so no nonexistent image link is supplied. These scratch links are included to identify the reviewed originals; their durable replacement is finding 1.
- The source package's original not_run statuses, historical validation report and raw whitespace-check outcome were not rewritten. The complete SessionManifest, single-writer recovery, atomic approval consumption/replay/revocation, P07 product adapter, compaction, other protocols, P20 release isolation and G5 real-model effects remain later-task work under D06. Their absence is not being counted as extra P01 defects.

Only the three findings above require disposition in the scoped follow-up. Adding durable links/a real screenshot calls for artifact and hash verification; the watchdog fix calls for a targeted check of that changed failure path. The successful unchanged SDK cases need not be repeated.
