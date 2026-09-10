# Wuji Task Runtime Foundation

A production-oriented infrastructure library for one Task Pod with two containers (`agent`, `kali`). It does not start a service or load kubeconfig on import. It is not connected to the public 0.4.0 API, Cairn or real task execution yet.

## Responsibility

`TaskRuntimeController` is the only caller that creates/deletes the Task Pod. Future Cairn execution adapters launch AgentRun processes inside `agent`; they must not independently delete the Pod or launch models/tools just because infrastructure reports `ready`.

The library provides immutable execution configuration, manifest/ownership validation, permission-aware create/reuse, explicit stop observations, and an adapter over the official Kubernetes Python SDK. Platform storage must supply an authenticated, current start permit and an exclusive execution lease; this package does not replace those database transactions. Kubernetes list/check/create is not a cross-store atomic transaction.

## Resource contract

Images are separate digest references. The administrator-controlled `agent` image must idle until a managed AgentRun launch; the `kali` image must expose its managed tool/MCP entrypoint without starting target work. Image building, the agent launcher and MCP integration are later work.

ConfigMap, Secret and PVC names are derived from the Task UUID. They must already exist in the authorized namespace with the `app.kubernetes.io/managed-by`, `wuji.dev/task-id` and `wuji.dev/tenant-id` ownership labels. The controller verifies metadata and never returns Secret data from preflight. Agent credentials and state are not mounted in Kali; Kali working files are not mounted in Agent. Runtime/control credentials are Task-scoped, never upstream model or cluster administration keys.

Containers run as UIDs 10001/10002 with fsGroup 10000, read-only root filesystems and bounded temporary directories. Images and storage must support that contract. `restartPolicy: Never` prevents an implicit restart of unknown execution. The library does not create NetworkPolicies or claim that egress isolation has been verified.

## Usage boundary

Configure `kubernetes.client.Configuration` explicitly with authentication, cluster URL and `retries=0` before constructing `ApiClient`/`CoreV1Api`, then pass that API to `KubernetesPodClient`. Do not load a user's default cluster as an implicit fallback.

`TaskRuntimeController(pods, permits).ensure(config)` returns an infrastructure observation. `stop(config, previously_observed_uid)` requests conditional deletion; an accepted request is `stopping`, not `stopped`. Only explicit NotFound confirms absence of that Pod resource. Neither Pod readiness nor disappearance establishes target-operation results, traffic isolation or Task completion.

A different config/image does not silently patch an active Pod. Other generations block provisioning until reconciled. Unknown writes and non-404 reads are not retried blindly. Permission changes after creation trigger conditional cleanup of the verified returned UID.

## Local checks

Use the workspace `task-runtime` dependency group and run only `packages/task-runtime/tests`. Tests use synthetic config and API/permit substitutes and make no cluster/model calls. Resource values in test fixtures are examples, not product defaults. See the [Spec](../../docs/stages/phase-1c-runtime-foundation/spec.md), [Plan](../../docs/stages/phase-1c-runtime-foundation/plan.md) and [acceptance](../../docs/stages/phase-1c-runtime-foundation/acceptance.md) for the shared remaining budget and deferred live integration.
