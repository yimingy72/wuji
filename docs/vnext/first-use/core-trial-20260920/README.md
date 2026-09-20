# Core first-use trial — 2026-09-20

Status: **incomplete**. Creation, explicit start, real Scheduler/Supervisor/MAF/Gate
execution, DeepSeek calls, one real target observation, evidence-backed analysis,
follow-up Intent admission, cancellation and actual-state reconciliation have all
run. They have not all completed on one Task: the assigned follow-up Explore may
still exit without invoking its required target tool, so result closure remains
unaccepted.

## Fixed deployment

- Platform/Agent/Kali source: `f8c1dbc3b1e9efb34f7fa00b8dcc463224e92903`
- Web source: `0d73f2de7162f43b34d1082f64b59bde450c39ea`
- Release-registration commit: `d27321a`
- Agent: `127.0.0.1:55529/wuji-vnext-agent@sha256:50851a60aee7cbc2b35618c36f1549bc12e467081a35c4b77abbf198cbfc0665`
- Platform: `127.0.0.1:55529/wuji-vnext-platform@sha256:617c0b17afb2f277285abec147e17897304644c8c56e6f560f6446a75a43f9da`
- Kali: `127.0.0.1:55529/wuji-vnext-kali@sha256:abe46bfc28188f0aa95bbd77b6c8e28a7f02d7caa13e749bf8866a90eb445864`
- Web: `127.0.0.1:55529/wuji-web@sha256:a8b8f8f96f590cd8e9dbeca04afb3883f18f81b286816d3278ff6ec69f95268a`
- Catalog Job: `first-use-catalog-deepseek-f8c1dbc3-523a3519`
- Owner SecretRef: `first-use-deepseek-owner-v6`
- Rollout result: API, Runtime, Scheduler, Gates, Web, launch service, fixture and
  isolated LiteLLM all reported Ready.

The Web-only follow-up reused the reviewed base image and replaced compiled
assets. It did not rebuild or change Platform, Agent, Kali, the model profile,
or task execution behavior.

## Implemented core fixes

1. Settled `cancel/quiescing` is displayed as `已停止`; `reconciling` remains
   `待核对`. A reconciled cancel notice now says `取消已确认`, and the refreshed
   Task is synchronized back into the left directory.
2. A malformed retained MAF result is persisted as one rejected receipt rather
   than restaging an artifact on every receiver cycle.
3. Initial Reason self/local basis references are normalized without rewriting
   the sealed raw model output. Unsupported follow-up Artifact bases are dropped
   only when supported Claim/Observation bases remain.
4. Launch reuses the already verified immutable capability when only release
   evidence references change, avoiding a false input-digest conflict.
5. The Explore profile explicitly limits target reads, forbids waiting on its
   own assigned Intent and directs a concrete unfulfilled HTTP Intent to the
   registered `http_target_get` tool.

## Actual validation

### Focused mechanism checks

- First-use workbench state: 7 passed.
- Production Web typecheck/build: passed.
- Release configuration and guards: 11 passed.
- First-use release configuration before the final Web-only change: 7 passed.
- First-use release guards before the final Web-only change: 4 passed.
- Launch capability reuse against real PostgreSQL: 1 passed.
- Initial local-reference, invalid retained result and valid replay paths: 3
  passed; the retained receiver replay check separately passed.
- No unrelated full suite or performance matrix was run.

The first test invocation used local pnpm 11 and was rejected by the repository
engine guard before test collection. The recorded pass used pinned pnpm
10.32.1. The initial Vitest invocation used the root contracts-only config and
found no matching test; the recorded 7-pass result used
`tests/topology/vitest.config.ts`.

### Real DeepSeek and target runs

R18 (`87d85331-da2c-4b8b-8764-cb09400f3d33`) is the most complete single run:

- formal workbench create and explicit start reached launch `ready/succeeded`;
- four completed DeepSeek calls reported 28,365 total tokens;
- the registered tool performed one non-destructive
  `GET http://39.97.227.109/`;
- the live capture is complete: HTTP 200, `nginx/1.27.4`, 12,429 response bytes,
  `text/html; charset=utf-8`, no truncation;
- DeepSeek produced two accepted, evidence-backed claims: the root is the
  `若依管理系统` SPA shell, and its observed static references include
  `/static/js/app.f0661109.js` and the listed CSS/chunk assets;
- a follow-up Intent for `/static/js/app.f0661109.js` was admitted with an
  Observation and Claim as its basis;
- the second Explore nevertheless exited without a tool call, so the follow-up
  observation and final result were not produced.

R19 (`853d88b9-d27e-4c40-87db-39e34e9c407b`) used the final v6 execution
profile and reached launch `ready/succeeded`. Two DeepSeek calls completed with
5,557 total tokens, but its first Explore exited without a tool call. It was
cancelled through the workbench. PostgreSQL records
`desired_state=cancel`, `observed_state=quiescing`,
`close_trigger=user_cancel`; both AgentRuns are exited, the Task Pod is absent,
and the workbench displays `已停止`. Only its completed workspace-init Job
remains.

R15 (`4990f614-1d16-4687-84cf-a0ee7f613447`) separately demonstrated two real
reads, `/` and `/static/js/app.f0661109.js`, and five completed model calls
(61,628 total tokens). Its JS material was partial at the then-current 65,536
byte capture limit, and its follow-up basis was rejected by the older policy;
it is supporting evidence, not a full-flow pass.

## Complete HTTP packets

These files contain complete redacted request and response records. Platform
authorization is represented by its SecretRef, never by a token value.

- [R18 final Task/launch/readiness GETs](http/r18-final.json)
- [R18 real target GET](http/r18-target-get.json) — the exact 12,429 response
  bytes are retained as base64; decoded SHA-256 is
  `1390ef07362ff9fd6e1f1fc4c147a778d86b586f1aca4ba11343bd6504ff790f`.
- [R19 final Task/launch/readiness GETs](http/r19-final.json)
- [R11 partial final state](http/r11-partial-final.json)
- [R9 paused state](http/r9-paused.json)
- [R12 cancellation state](http/r12-cancel.json)
- [R13 cancellation state](http/r13-cancel.json)

The R19 stopped-state screenshot was captured from the in-app browser and is
retained in the task conversation. The browser-control interface returned image
bytes without a filesystem export path, so this repository still lacks the
required PNG under `screenshots/`. Screenshot-file packaging is therefore
**not passed**; no synthetic image is substituted.

## Asset and interface inventory

| Asset/interface | Validation state | Evidence |
| --- | --- | --- |
| `http://39.97.227.109/` | 已利用（只读 GET） | R18 complete live capture |
| `/static/js/app.f0661109.js` | 已利用（R15，partial material）；R18 follow-up未执行 | R15/R18 task records |
| `/static/css/app.07b3ceaf.css` | 未利用，仅正文引用 | R18 root body |
| `/static/css/chunk-libs.d52e5467.css` | 未利用，仅正文引用 | R18 root body |
| `/static/js/chunk-elementUI.32b5af96.js` | 未利用，仅正文引用 | R18 root body |
| `/static/js/chunk-libs.1c571370.js` | 未利用，仅正文引用 | R18 root body |
| `/static/js/runtime.6d86708d.js` | 未利用，仅正文引用 | R18 root body |
| Task/launch/readiness API | 已验证，200 | R18/R19 HTTP captures |
| Workbench cancel and state read | 已验证；底层 `cancel/quiescing/user_cancel`，Task Pod absent | R19 UI/API/Kubernetes |

## Configuration and operation

- Workbench: `http://localhost:44180/`
- Authorized target: `http://39.97.227.109`, HTTP port 80 only.
- Authorization expiry supplied by the user: 2026-09-21 17:00 Asia/Shanghai.
- Model: published DeepSeek `deepseek-flash` profile; key remains behind the
  gateway SecretRef and is not in Git or Task material.
- Trial budget: USD 1 per Task.
- Login code can be read locally without posting it to chat:
  `kubectl --context docker-desktop -n wuji-vnext-test get secret wuji-web-gateway-credentials -o jsonpath='{.data.access\.token}' | base64 --decode`
- Normal use: establish the local session, create a Web single-target Task,
  confirm target and external analysis separately, select the published model
  and runtime, create the unstarted Task, click `显式启动`, inspect topology and
  evidence, then use pause/cancel and `查看原操作结果` to reconcile state.

## Remaining boundary and next code item

The user flow is not complete until one fixed-build Task performs its assigned
follow-up target read and reaches a result display. The next code item is a
deterministic Explore completion invariant: a concrete admitted target Intent
must not be accepted as `done` when the Run produced no registered tool attempt;
the scheduler/supervisor should requeue or fail it with an explicit reason. Once
that focused failure path passes, run one new authorized Task through the same
core path and stop—no broader test matrix is required.

No SSH credential was used, no destructive request was sent, and no synthetic
result is reported as a real-model or target pass.
