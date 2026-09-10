# Wuji Cairn Bridge

Internal integration with the unmodified Cairn blackboard. The optional `cairn-bridge` workspace group pins upstream Git commit `8e7e0ea67552383851dfcabfba0c4e9c8d007878` (`cairn/` subdirectory). Native models, HTTP client and Server are reused. No Agent, server, Kubernetes client or default database is started by importing this package.

## Provided behavior

- Explicitly project only title/origin/goal/bootstrap into the native Project API; platform tools, credentials, budgets and execution settings remain with Wuji Task.
- Keep durable Task bindings and result operations in SQLAlchemy journal tables. Atomically claim pending operations before sending HTTP. Sent/unknown operations are never reset automatically for another write.
- Filter native active Projects by current trusted Task execution admission. Preselection is not a lasting grant; recheck immediately before real dispatch.
- Store Agent results before checking active AgentRun membership and execution epoch/config. Submit through native conclude; on lost response, inspect the known Intent and matching worker/Fact description instead of writing again.
- Keep an unknown project creation unresolved rather than guessing by title/goal or creating a duplicate.

## Integration boundaries

`SQLAlchemyJournal(engine)` uses an explicit engine and does not create tables. Its module `metadata` is intended as a schema definition for deployment migration. Production migration, Wuji Task foreign keys, RLS, service roles and authenticated API wiring are not part of this slice. Tests create temporary SQLite schemas only. Do not expose journal methods or caller-supplied DispatchContext as public authorization APIs.

`server_id` is an explicit identity of a persistent Cairn data instance, not a URL hash. A reset/replaced Core database must not silently inherit old bindings just because its URL and sequential native IDs look the same. Freeze and reconcile instance identity before reuse.

`ControlSource` must read authoritative Task/config/start/permit/Runtime state and the set of active AgentRun IDs. `execution_ready` includes the control-plane prerequisites that infrastructure Pod readiness alone cannot prove. Unknown or inactive contexts deny dispatch. Real Dispatcher/Worker entrypoints still need to be wired to this gate.

Native Cairn does not gain idempotency receipts or immutable events. The journal is platform audit/coordination state, not a second editable Fact graph. No production schema, Pod, model gateway or real target is activated by this package.

## Validation and licensing

The native integration fixture routes a requests adapter to the actual Cairn FastAPI app in-process, with its database redirected to pytest's temporary directory. It never uses the user's default Cairn directory or starts a network service. Model calls and target requests are zero. Actual results and historical checks are recorded in the [stage acceptance](../../docs/stages/phase-1c-cairn-bridge/acceptance.md); development verification has no aggregate time budget.

Upstream Cairn is AGPL-3.0; preserve its [license](https://github.com/oritera/Cairn/blob/8e7e0ea67552383851dfcabfba0c4e9c8d007878/LICENSE) and provenance. The dependency is not vendored or patched here. See the [Spec](../../docs/stages/phase-1c-cairn-bridge/spec.md) and [Plan](../../docs/stages/phase-1c-cairn-bridge/plan.md).

The package currently requires installation through this workspace and its frozen uv.lock. The Git source override is workspace-owned; do not install a standalone wheel by resolving the bare `cairn` name from PyPI. Standalone deployment packaging is deferred.
