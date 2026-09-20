# Core first-use trial — 2026-09-20

Status: **incomplete**. The fixed build delivers more of the core path, but the
complete user flow has not passed on one Task and cancellation does not yet
converge to `stopped`.

## Fixed build

- Code SHA: `69cf02ef59b8e0081d103f47db744be60d7894de`
- Agent: `127.0.0.1:55529/wuji-vnext-agent@sha256:8f3414bd13e64d882b31e1910253dae25721b76ef34f170a0588d30955134289`
- Platform: `127.0.0.1:55529/wuji-vnext-platform@sha256:1c19814554b1b3b1a0bbe4535fd6978c983d570de07b5136df921d6b9e395b2b`
- Kali: `127.0.0.1:55529/wuji-vnext-kali@sha256:957a6c77c816ace0f7e20bb327ab0b730e6d7eccfd6ca82d7238bca80354190d`
- Web: `127.0.0.1:55529/wuji-web@sha256:bdf35fc3a7eea6da58c8a5d04d2724a3e38e6f46241375746cbf55b859a0ec7a`
- Rollout: API, Runtime, Scheduler, Gates, Web, first-use launch, fixture and
  isolated LiteLLM all reported Ready.

## What changed

1. HTTP material keeps the largest real body prefix that fits the canonical
   envelope and distinguishes malformed UTF-8 from malformed JSON.
2. Reason/Report may resolve with zero tools; Explore still requires its fixed
   published tools.
3. Native zero-tool MAF requests may omit `tools` and
   `parallel_tool_calls`; tool-bearing requests remain strict.
4. Session capability/profile resolution, generated wire contracts and Runtime
   session transport now agree on zero-tool roles and model material v2.
5. Initial Reason output is constrained to delivered references; follow-up work
   must be emitted as an evidence-backed Intent rather than a wait on the
   current Reason WorkItem.
6. Gates wait up to 60 seconds for a newly written Task executor to reach the
   projected ConfigMap, within the existing model request deadline.
7. A removed Task environment now settles a started, non-exited Run as
   `environment_stopped` without inventing a successful result; capacity is
   released.
8. A URL-selected Task remains selected even when it is outside the first
   directory page.

## Actual results

### Mechanism and focused checks

- HTTP target/material: 29 focused tests passed (`13 + 16`).
- Remote capability/release/task launch: 21 focused tests passed.
- Workbench selection: 7 tests passed; production Web build passed.
- Tool-less MAF request boundary: 2 passed.
- First-use owner/prompt release configuration: 7 passed.
- Removed-environment settlement: 2 passed.
- Gate projected-executor refresh: 4 focused configuration tests passed.
- OpenAPI/generated contract check passed with only the three pre-existing
  Redocly warnings.

### Real DeepSeek and fixture

R11 (`d2fcc0cd-1b42-4db1-9f3b-8488770fe4ef`) demonstrated:

- explicit workbench creation and start;
- two completed Reason Runs and one completed Explore Run;
- four completed DeepSeek calls with reported usage: 13,130 prompt tokens,
  3,539 completion tokens, 16,669 total tokens;
- one native provider tool call with provider id
  `call_00_I6rhvAslcMyILHoikQz51291`;
- one actual GET of
  `http://first-use-fixture.wuji-vnext-test.svc:8080/f1/entry`;
- one complete live-capture Observation and a sealed HTTP exchange artifact;
- the actual JSON body reached DeepSeek and produced evidence-backed claims,
  including the observed `source_path` and marker.

R11 did **not** complete the required follow-up GET. Its second Reason waited on
its own WorkItem; Scheduler rejected that decision as `INVALID_REFERENCE`.
The fixed v4 Reason instruction addresses this in subsequent Tasks.

R12 and R13, both on the fixed v4 instruction, failed before their first Reason
response. Each Gate ledger contains exactly one ended model attempt with
`send_state=unknown`, `response_state=unknown`, no response bytes, no usage and
no corresponding LiteLLM chat-completions request. The same external transport
condition repeated twice, so no further Task was created.

### Pause, cancel and actual state

- R9 pause converged to Task `paused`, WorkItem `suspended`, and no Task Pod.
- Cancel commands were accepted and Task Pods were removed.
- R11, R12 and R13 nevertheless remained `observed_state=quiescing` after their
  terminal WorkItems and exited Runs were gone. This is an uncompleted task-level
  stop-convergence boundary; it is not reported as stopped.

## Reproducible HTTP captures

The files below contain complete redacted GET requests and responses (method,
URL, headers, request body and full response body). Authorization headers are
represented by their SecretRef and are not written to Git.

- [R11 partial final state](http/r11-partial-final.json)
- [R9 paused state](http/r9-paused.json)
- [R12 cancellation state](http/r12-cancel.json)
- [R13 cancellation state](http/r13-cancel.json)

The actual workbench screenshot was captured from the in-app browser at R13
cancellation and retained in the task conversation. This repository snapshot
does not contain a binary PNG because the browser-control interface returned
image bytes without a filesystem export path; this is an explicit evidence
packaging gap, not a claim that screenshot-file acceptance passed.

## Scope and exclusions

- Only the self-built in-cluster first-use fixture was accessed.
- `http://39.102.208.182` was not accessed.
- No SSH credential was used.
- No synthetic result is presented as a real-model or target pass.
- Full core flow, final result display, and verified terminal cancellation remain
  unaccepted until a single fixed-build Task completes both HTTP observations
  and cancellation converges to `stopped`.
