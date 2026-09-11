export interface paths {
    "/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read current session
         * @description Read current session
         */
        get: operations["getSession"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Begin the configured OIDC login flow
         * @description Validates the local return path, creates a browser-bound handshake and redirects to the configured identity provider.
         */
        get: operations["beginLogin"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Complete the current browser-bound OIDC handshake
         * @description Always redirects to an allowed local page. Failures expose only a fixed error code and trace identifier.
         */
        get: operations["finishLogin"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke the current Wuji application session */
        post: operations["logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Report that the API process can serve requests */
        get: operations["getLiveness"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Report database and migration readiness */
        get: operations["getReadiness"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List accessible projects
         * @description Lists current memberships ordered by (created_at, id) descending. The signed cursor is bound to this endpoint, caller, permissions version and limit. Tampering or cross-user reuse returns 422; expiry or a changed permissions version returns 410. Every page reauthorizes current membership.
         */
        get: operations["listProjects"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read one accessible project
         * @description Missing and inaccessible projects both return 404.
         */
        get: operations["getProject"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/scopes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List usable approved HTTP scope versions
         * @description Only approved versions visible to this caller. Preview and creation revalidate expiry and current authorization. This read never contacts the target.
         */
        get: operations["listApprovedScopes"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/task-previews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview the effective task scope
         * @description Creates a short-lived, caller/project-bound preview. Canonicalization and policy evaluation only; no DNS/target/model execution. Phase 1 accepts only approved HTTP observation profiles. GET/HEAD alone do not prove absence of side effects.
         */
        post: operations["previewTask"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List tasks with stable cursor pagination
         * @description List tasks with stable cursor pagination
         */
        get: operations["listTasks"];
        put?: never;
        /**
         * Accept a task creation command
         * @description Reauthorize, resolve idempotency, validate caller/project-bound unexpired preview and exact canonical draft/digest, then atomically create Task queued + command receipt + Outbox. Cannot grant scope or arbitrary tools. Limits may only narrow approved limits. Concurrent same-key requests return one task. Never contact a target in this transaction.
         */
        post: operations["createTask"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read an authoritative task snapshot and consistent event cursor
         * @description Snapshot and cursor use one consistent committed view. Every later committed change must be replayable after this cursor; database sequence allocation alone is not commit ordering. Task terminal states require confirmed no active/unknown execution and egress revoked or never granted. Cleanup remains independent.
         */
        get: operations["getTask"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/commands": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept cancellation; reject unsupported pause or resume transitions
         * @description Reauthorize first. Same-key replay resolves before expected_version checking and returns the original receipt. A new command atomically checks the task version, transitions intent/state, writes receipt and Outbox. This batch only transitions never-executed queued tasks directly to cancelled; pause and resume return INVALID_TRANSITION. Terminal tasks reject new controls.
         */
        post: operations["controlTask"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/commands/{command_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read an immutable acceptance receipt
         * @description Project membership and receipt visibility are rechecked. Use task_id to query achieved execution state; the receipt does not change when execution later fails.
         */
        get: operations["getCommand"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/command-keys/{idempotency_key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Reconcile a command whose response was lost
         * @description Lookup is scoped to caller/project and all task command kinds. A 404 does not prove an in-flight transaction failed: resend the identical request with the same key, never mint a new key automatically. Minimum server idempotency retention is 24 hours; unknown commands beyond that window require explicit reconciliation.
         */
        get: operations["findCommandByKey"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Replay persisted task event notices
         * @description Phase 1 read API; Phase 2 SSE is not yet exposed. Omitting after returns bounded initial history from task sequence zero; supplied after is exclusive. Stable replay cursor ordering must not skip late commits. Empty pages preserve cursor, has_more bounds catch-up. Expired cursor returns 410 CURSOR_EXPIRED. Every page reauthorizes. No raw credentials or evidence body in events.
         */
        get: operations["listTaskEvents"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/artifacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List authorized artifact metadata
         * @description List authorized artifact metadata
         */
        get: operations["listArtifacts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/artifacts/{artifact_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read authorized artifact metadata
         * @description Read authorized artifact metadata
         */
        get: operations["getArtifact"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/artifacts/{artifact_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read bounded, redacted text evidence
         * @description Phase 1 returns escaped-as-data plain text in JSON only. The UI renders text, never raw HTML. Server checks artifact.read and classification, redacts sensitive values, caps content, disables external resources, and denies unsupported/unavailable previews.
         */
        get: operations["previewArtifact"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/artifacts/{artifact_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download evidence through the authorized API
         * @description Reauthorize on every request. Restricted content requires artifact.download_sensitive. Return attachment and nosniff; no bucket URL or signed public URL in Phase 1. Expired content returns 410. Audit downloads.
         */
        get: operations["downloadArtifact"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/task-drafts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * listTaskDrafts
         * @description User-owned incomplete task intent. Saving does not create a Task, grant Scope or contact any external service. PUT uses expected_version=0 for create; an immediate identical replay returns the saved version. Reads require current project access. Signed pagination binds user, permissions version, project, limit and task_drafts purpose.
         */
        get: operations["listTaskDrafts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/task-drafts/{draft_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * getTaskDraft
         * @description User-owned incomplete task intent. Saving does not create a Task, grant Scope or contact any external service. PUT uses expected_version=0 for create; an immediate identical replay returns the saved version. Reads require current project access. Signed pagination binds user, permissions version, project, limit and task_drafts purpose.
         */
        get: operations["getTaskDraft"];
        /**
         * saveTaskDraft
         * @description User-owned incomplete task intent. Saving does not create a Task, grant Scope or contact any external service. PUT uses expected_version=0 for create; an immediate identical replay returns the saved version. Reads require current project access. Signed pagination binds user, permissions version, project, limit and task_drafts purpose.
         */
        put: operations["saveTaskDraft"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Tenants
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["tenants_api_v1_tenants_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-services": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Definitions
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["list_service_definitions"];
        put?: never;
        /**
         * Create Definition
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["create_service_definition"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-services/{definition_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Versions
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["list_service_versions"];
        put?: never;
        /**
         * Create Version
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["create_service_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-service-versions/{version_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Version
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["get_service_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Definitions
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["list_profile_definitions"];
        put?: never;
        /**
         * Create Definition
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["create_profile_definition"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-profiles/{definition_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Versions
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["list_profile_versions"];
        put?: never;
        /**
         * Create Version
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["create_profile_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-profile-versions/{version_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Version
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["get_profile_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-profile-versions/{version_id}/checks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Check Model
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["check_model_api_v1_tenants__tenant_id__model_profile_versions__version_id__checks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-profile-versions/{version_id}/commands": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Command Model
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        post: operations["command_model_api_v1_tenants__tenant_id__model_profile_versions__version_id__commands_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-operations/{operation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Operation
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["operation_api_v1_tenants__tenant_id__model_operations__operation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/tenants/{tenant_id}/model-operation-keys/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Operation Key
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["operation_key_api_v1_tenants__tenant_id__model_operation_keys__key__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/model-profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Project Models
         * @description Tenant-scoped versioned model configuration. No inference is performed except an explicit connection check. Unknown operations are reconciled without resending checks. Writes use stable Idempotency-Key and current authority.
         */
        get: operations["project_models_api_v1_projects__project_id__model_profiles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        Version: number;
        Cursor: string;
        Sha256: string;
        /** @enum {string} */
        TaskState: "queued" | "provisioning" | "running" | "completing" | "completed" | "pausing" | "paused" | "cancelling" | "cancelled" | "reconciling" | "failed";
        /** @enum {string} */
        TaskAction: "pause" | "resume" | "cancel";
        /** @enum {string} */
        Permission: "project.read" | "model.profile.read" | "task.draft.read" | "task.draft.write" | "task.preview" | "task.read" | "task.create" | "task.control" | "artifact.read" | "artifact.download_sensitive";
        Error: {
            /** @enum {string} */
            code: "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND" | "VALIDATION_FAILED" | "SCOPE_DENIED" | "PREVIEW_EXPIRED" | "VERSION_CONFLICT" | "IDEMPOTENCY_CONFLICT" | "INVALID_TRANSITION" | "RATE_LIMITED" | "SERVICE_UNAVAILABLE" | "CURSOR_EXPIRED" | "INTERNAL_ERROR";
            message: string;
            /** Format: uuid */
            trace_id: string;
            field_errors?: {
                field: string;
                message: string;
            }[];
        };
        HealthStatus: {
            /** @enum {string} */
            status: "live" | "ready";
        };
        Session: {
            /** Format: uuid */
            user_id: string;
            display_name: string;
            csrf_token: string;
            /** Format: date-time */
            expires_at: string;
            permissions_version: components["schemas"]["Version"];
        };
        Project: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            tenant_id: string;
            name: string;
            permissions: components["schemas"]["Permission"][];
        };
        Limits: {
            max_total_requests: number;
            requests_per_second: number;
            max_concurrent_requests: number;
            request_timeout_seconds: number;
            max_response_bytes: number;
            max_runtime_seconds: number;
        };
        ScopeBinding: {
            /** Format: uuid */
            policy_id: string;
            version: components["schemas"]["Version"];
        };
        ApprovedScope: {
            binding: components["schemas"]["ScopeBinding"];
            label: string;
            /** Format: date-time */
            valid_until: string;
            origins: string[];
            allowed_path_prefixes: string[];
            excluded_path_prefixes: string[];
            allowed_methods: ("GET" | "HEAD")[];
            limits: components["schemas"]["Limits"];
        };
        TaskDraft: {
            name: string;
            scope: components["schemas"]["ScopeBinding"];
            /** Format: uri */
            target_url: string;
            /** @constant */
            tool: "http_observe";
            /** @enum {string} */
            method: "GET" | "HEAD";
            limits: components["schemas"]["Limits"];
        };
        TaskPreview: {
            /** Format: uuid */
            preview_id: string;
            /** Format: uuid */
            project_id: string;
            draft: components["schemas"]["TaskDraft"];
            input_digest: components["schemas"]["Sha256"];
            effective_scope: components["schemas"]["ApprovedScope"];
            /** Format: date-time */
            expires_at: string;
            can_create: boolean;
            blockers: {
                /** @enum {string} */
                code: "MISSING_ADAPTER" | "MISSING_IDENTITY" | "SCOPE_DENIED" | "AUTHORIZATION_EXPIRED" | "CREATION_UNAVAILABLE";
                message: string;
            }[];
        } & unknown;
        CreateTask: {
            /** Format: uuid */
            preview_id: string;
            input_digest: components["schemas"]["Sha256"];
            draft: components["schemas"]["TaskDraft"];
        };
        TaskControl: {
            action: components["schemas"]["TaskAction"];
            expected_version: components["schemas"]["Version"];
        };
        ExecutionSummary: {
            active_calls: number;
            unknown_calls: number;
            /** @enum {string} */
            egress_state: "pending" | "active" | "frozen" | "revoked" | "not_granted" | "unknown";
        };
        Task: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            tenant_id: string;
            /** Format: uuid */
            project_id: string;
            name: string;
            /** Format: uri */
            target_url: string;
            scope: components["schemas"]["ScopeBinding"];
            version: components["schemas"]["Version"];
            state: components["schemas"]["TaskState"];
            /** @enum {string} */
            cleanup_state: "not_required" | "pending" | "cleaning" | "cleaned" | "cleanup_pending";
            execution: components["schemas"]["ExecutionSummary"];
            allowed_actions: components["schemas"]["TaskAction"][];
            /** @enum {string} */
            assessment_outcome: "criteria_met" | "partial" | "inconclusive" | "not_assessed";
            /** @enum {string|null} */
            stop_reason: null | "criteria_met" | "plan_exhausted" | "budget_exhausted" | "deadline_exceeded" | "user_cancelled" | "runtime_error" | "authorization_expired";
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            updated_at: string;
        } & (unknown & unknown);
        TaskSnapshot: {
            task: components["schemas"]["Task"];
            event_cursor: components["schemas"]["Cursor"];
        };
        CommandReceipt: {
            /** Format: uuid */
            command_id: string;
            /** Format: uuid */
            idempotency_key: string;
            /** @enum {string} */
            kind: "create" | "pause" | "resume" | "cancel";
            /** @constant */
            disposition: "accepted";
            /** Format: uuid */
            project_id: string;
            /** Format: uuid */
            task_id: string;
            /** Format: date-time */
            accepted_at: string;
            accepted_task_version: components["schemas"]["Version"];
            request_digest: components["schemas"]["Sha256"];
        };
        TaskEvent: {
            /** @constant */
            schema_version: "1.0";
            /** Format: uuid */
            event_id: string;
            cursor: components["schemas"]["Cursor"];
            /** Format: uuid */
            tenant_id: string;
            /** Format: uuid */
            project_id: string;
            /** Format: uuid */
            task_id: string;
            aggregate_version: components["schemas"]["Version"];
            /** @enum {string} */
            type: "task.changed" | "task.cleanup_changed" | "artifact.available";
            /** Format: date-time */
            occurred_at: string;
            /** Format: uuid */
            trace_id: string;
            summary: string;
        };
        Artifact: {
            /** Format: uuid */
            id: string;
            /** Format: uuid */
            tenant_id: string;
            /** Format: uuid */
            project_id: string;
            /** Format: uuid */
            task_id: string;
            name: string;
            media_type: string;
            size_bytes: number;
            sha256: components["schemas"]["Sha256"];
            /** @enum {string} */
            classification: "redacted" | "restricted";
            /** @enum {string} */
            availability: "available" | "expired" | "unavailable";
            /** @enum {string} */
            preview_kind: "text" | "download_only";
            /** Format: date-time */
            created_at: string;
        };
        ArtifactPreview: {
            /** Format: uuid */
            artifact_id: string;
            text: string;
            truncated: boolean;
            /** @constant */
            redacted: true;
        };
        ProjectPage: {
            items: components["schemas"]["Project"][];
            next_cursor: string | null;
        };
        ScopePage: {
            items: components["schemas"]["ApprovedScope"][];
            next_cursor: string | null;
        };
        TaskPage: {
            items: components["schemas"]["Task"][];
            next_cursor: string | null;
        };
        ArtifactPage: {
            items: components["schemas"]["Artifact"][];
            next_cursor: string | null;
        };
        EventPage: {
            items: components["schemas"]["TaskEvent"][];
            next_cursor: components["schemas"]["Cursor"];
            has_more: boolean;
        };
        /** CodeAuditDraft */
        CodeAuditDraft: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Objective
             * @default
             */
            objective: string;
            /**
             * Starting Point
             * @default
             */
            starting_point: string;
            /**
             * Constraints
             * @default
             */
            constraints: string;
            /** Reference Ids */
            reference_ids?: string[];
            /**
             * Model Profile Version Id
             * @default null
             */
            model_profile_version_id: string | null;
            /**
             * Runtime Profile Version Id
             * @default null
             */
            runtime_profile_version_id: string | null;
            /**
             * Budget Usd
             * @default null
             */
            budget_usd: string | null;
            /**
             * Scenario
             * @constant
             */
            scenario: "code_audit";
            /**
             * Repository Url
             * @default null
             */
            repository_url: string | null;
            /**
             * Source Reference Id
             * @default null
             */
            source_reference_id: string | null;
            /**
             * Revision
             * @default null
             */
            revision: string | null;
        };
        /** ComprehensiveDraft */
        ComprehensiveDraft: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Objective
             * @default
             */
            objective: string;
            /**
             * Starting Point
             * @default
             */
            starting_point: string;
            /**
             * Constraints
             * @default
             */
            constraints: string;
            /** Reference Ids */
            reference_ids?: string[];
            /**
             * Model Profile Version Id
             * @default null
             */
            model_profile_version_id: string | null;
            /**
             * Runtime Profile Version Id
             * @default null
             */
            runtime_profile_version_id: string | null;
            /**
             * Budget Usd
             * @default null
             */
            budget_usd: string | null;
            /**
             * Scenario
             * @constant
             */
            scenario: "comprehensive";
            /** Assets */
            assets?: string[];
            /**
             * Access Notes
             * @default
             */
            access_notes: string;
        };
        /** CtfDraft */
        CtfDraft: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Objective
             * @default
             */
            objective: string;
            /**
             * Starting Point
             * @default
             */
            starting_point: string;
            /**
             * Constraints
             * @default
             */
            constraints: string;
            /** Reference Ids */
            reference_ids?: string[];
            /**
             * Model Profile Version Id
             * @default null
             */
            model_profile_version_id: string | null;
            /**
             * Runtime Profile Version Id
             * @default null
             */
            runtime_profile_version_id: string | null;
            /**
             * Budget Usd
             * @default null
             */
            budget_usd: string | null;
            /**
             * Scenario
             * @constant
             */
            scenario: "ctf";
            /**
             * Challenge
             * @default
             */
            challenge: string;
            /**
             * Entry Url
             * @default null
             */
            entry_url: string | null;
        };
        /** ExerciseDraft */
        ExerciseDraft: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Objective
             * @default
             */
            objective: string;
            /**
             * Starting Point
             * @default
             */
            starting_point: string;
            /**
             * Constraints
             * @default
             */
            constraints: string;
            /** Reference Ids */
            reference_ids?: string[];
            /**
             * Model Profile Version Id
             * @default null
             */
            model_profile_version_id: string | null;
            /**
             * Runtime Profile Version Id
             * @default null
             */
            runtime_profile_version_id: string | null;
            /**
             * Budget Usd
             * @default null
             */
            budget_usd: string | null;
            /**
             * Scenario
             * @constant
             */
            scenario: "exercise";
            /**
             * Organization Name
             * @default
             */
            organization_name: string;
            /** Known Domains */
            known_domains?: string[];
        };
        /** WebDraft */
        WebDraft: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Objective
             * @default
             */
            objective: string;
            /**
             * Starting Point
             * @default
             */
            starting_point: string;
            /**
             * Constraints
             * @default
             */
            constraints: string;
            /** Reference Ids */
            reference_ids?: string[];
            /**
             * Model Profile Version Id
             * @default null
             */
            model_profile_version_id: string | null;
            /**
             * Runtime Profile Version Id
             * @default null
             */
            runtime_profile_version_id: string | null;
            /**
             * Budget Usd
             * @default null
             */
            budget_usd: string | null;
            /**
             * Scenario
             * @constant
             */
            scenario: "web_single";
            /**
             * Entry Url
             * @default null
             */
            entry_url: string | null;
            /**
             * Include Subdomains
             * @default false
             */
            include_subdomains: boolean;
            /** Additional Origins */
            additional_origins?: string[];
        };
        /** SaveDraftRequest */
        SaveDraftRequest: {
            /** Expected Version */
            expected_version: number;
            /** Content */
            content: components["schemas"]["CtfDraft"] | components["schemas"]["WebDraft"] | components["schemas"]["ComprehensiveDraft"] | components["schemas"]["ExerciseDraft"] | components["schemas"]["CodeAuditDraft"];
        };
        /** TaskDraftResponse */
        SavedTaskDraft: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Tenant Id
             * Format: uuid
             */
            tenant_id: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Version */
            version: number;
            /** Content */
            content: components["schemas"]["CtfDraft"] | components["schemas"]["WebDraft"] | components["schemas"]["ComprehensiveDraft"] | components["schemas"]["ExerciseDraft"] | components["schemas"]["CodeAuditDraft"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** TaskDraftPageResponse */
        SavedTaskDraftPage: {
            /** Items */
            items: components["schemas"]["SavedTaskDraft"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ModelCheckRequest */
        ModelCheckRequest: Record<string, never>;
        /** ModelDefinitionPage */
        ModelDefinitionPage: {
            /** Items */
            items: components["schemas"]["ModelDefinition"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ModelDefinitionResponse */
        ModelDefinition: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Tenant Id
             * Format: uuid
             */
            tenant_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "service" | "profile";
            /** Name */
            name: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ModelOperationResponse */
        ModelOperation: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "create_service" | "create_profile" | "check" | "publish" | "retire" | "revoke";
            /**
             * Version Id
             * Format: uuid
             */
            version_id: string;
            /**
             * State
             * @enum {string}
             */
            state: "prepared" | "sent" | "succeeded" | "failed" | "unknown";
            result: components["schemas"]["ModelOperationResult"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ModelOperationResult */
        ModelOperationResult: {
            /** Error Code */
            error_code?: string | null;
            /** Usage */
            usage?: null;
            /** Cost Usd */
            cost_usd?: null;
        };
        /** ModelPricing */
        ModelPricing: {
            /** Source */
            source: string;
            /** Input Per Million */
            input_per_million: string;
            /** Output Per Million */
            output_per_million: string;
            /**
             * Cache Mode
             * @enum {string}
             */
            cache_mode: "standard_input" | "separate";
            /** Cache Read Per Million */
            cache_read_per_million?: string | null;
            /** Cache Creation Per Million */
            cache_creation_per_million?: string | null;
        };
        /** ModelVersionCommand */
        ModelVersionCommand: {
            /**
             * Action
             * @enum {string}
             */
            action: "publish" | "retire" | "revoke";
            /** Expected Version */
            expected_version: number;
        };
        /** ModelVersionPage */
        ModelVersionPage: {
            /** Items */
            items: components["schemas"]["ModelVersion"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ModelVersionResponse */
        ModelVersion: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Tenant Id
             * Format: uuid
             */
            tenant_id: string;
            /**
             * Definition Id
             * Format: uuid
             */
            definition_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "service" | "profile";
            /** Number */
            number: number;
            /** Name */
            name: string;
            /** Config */
            config: components["schemas"]["ServiceConfig"] | components["schemas"]["ProfileConfig"];
            /**
             * State
             * @enum {string}
             */
            state: "draft" | "published" | "retired" | "revoked";
            /** State Revision */
            state_revision: number;
            /**
             * Sync State
             * @enum {string}
             */
            sync_state: "pending" | "synced" | "failed" | "unknown";
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ProfileConfig */
        ProfileConfig: {
            /**
             * Service Version Id
             * Format: uuid
             */
            service_version_id: string;
            /** Model Id */
            model_id: string;
            /** Context Window */
            context_window?: number | null;
            /** Max Output Tokens */
            max_output_tokens?: number | null;
            /**
             * Timeout Seconds
             * @default 30
             */
            timeout_seconds: number;
            pricing?: components["schemas"]["ModelPricing"] | null;
        };
        /** ProfileVersionRequest */
        ProfileVersionRequest: {
            /** Name */
            name: string;
            config: components["schemas"]["ProfileConfig"];
        };
        /** ServiceConfig */
        ServiceConfig: {
            /**
             * Protocol
             * @enum {string}
             */
            protocol: "openai" | "anthropic";
            /** Base Url */
            base_url: string;
        };
        /** ServiceVersionRequest */
        ServiceVersionRequest: {
            /** Name */
            name: string;
            config: components["schemas"]["ServiceConfig"];
            /**
             * Api Key
             * Format: password
             */
            api_key: string;
        };
        /** TenantPage */
        TenantPage: {
            /** Items */
            items: components["schemas"]["Tenant"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** TenantResponse */
        Tenant: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Permissions */
            permissions: ("model.config.read" | "model.config.write")[];
        };
    };
    responses: never;
    parameters: {
        ProjectId: string;
        TaskId: string;
        ArtifactId: string;
        CommandId: string;
        KeyPath: string;
        /** @description Same key + same canonical request returns the original receipt after reauthorization. Reusing a key with a different request returns 409. */
        IdempotencyKey: string;
        PageSize: number;
        PageCursor: components["schemas"]["Cursor"];
        /** @description Opaque task stream cursor. Not an authorization credential. */
        After: components["schemas"]["Cursor"];
    };
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    getSession: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Session"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    beginLogin: {
        parameters: {
            query?: {
                return_to?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Redirect to the configured identity provider */
            302: {
                headers: {
                    Location: string;
                    "Cache-Control": "no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    finishLogin: {
        parameters: {
            query?: {
                code?: string;
                state?: string;
                error?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Redirect to the allowed return path or fixed login error page */
            303: {
                headers: {
                    Location: string;
                    "Cache-Control": "no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    logout: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Current application session revoked */
            204: {
                headers: {
                    "Cache-Control": "no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getLiveness: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Process is live */
            200: {
                headers: {
                    "Cache-Control": "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthStatus"];
                };
            };
        };
    };
    getReadiness: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Required dependencies and migrations are ready */
            200: {
                headers: {
                    "Cache-Control": "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthStatus"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listProjects: {
        parameters: {
            query?: {
                limit?: components["parameters"]["PageSize"];
                cursor?: components["parameters"]["PageCursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectPage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getProject: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Project"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listApprovedScopes: {
        parameters: {
            query?: {
                limit?: components["parameters"]["PageSize"];
                cursor?: components["parameters"]["PageCursor"];
            };
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScopePage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    previewTask: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskDraft"];
            };
        };
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskPreview"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listTasks: {
        parameters: {
            query?: {
                limit?: components["parameters"]["PageSize"];
                cursor?: components["parameters"]["PageCursor"];
            };
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskPage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    createTask: {
        parameters: {
            query?: never;
            header: {
                /** @description Same key + same canonical request returns the original receipt after reauthorization. Reusing a key with a different request returns 409. */
                "Idempotency-Key": components["parameters"]["IdempotencyKey"];
            };
            path: {
                project_id: components["parameters"]["ProjectId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateTask"];
            };
        };
        responses: {
            /** @description Successful response */
            202: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getTask: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                task_id: components["parameters"]["TaskId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskSnapshot"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    controlTask: {
        parameters: {
            query?: never;
            header: {
                /** @description Same key + same canonical request returns the original receipt after reauthorization. Reusing a key with a different request returns 409. */
                "Idempotency-Key": components["parameters"]["IdempotencyKey"];
            };
            path: {
                project_id: components["parameters"]["ProjectId"];
                task_id: components["parameters"]["TaskId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskControl"];
            };
        };
        responses: {
            /** @description Successful response */
            202: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getCommand: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                command_id: components["parameters"]["CommandId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    findCommandByKey: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                idempotency_key: components["parameters"]["KeyPath"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listTaskEvents: {
        parameters: {
            query?: {
                /** @description Omit to read bounded initial history from task sequence zero. A supplied cursor is exclusive. */
                after?: components["schemas"]["Cursor"];
                limit?: components["parameters"]["PageSize"];
            };
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                task_id: components["parameters"]["TaskId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventPage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listArtifacts: {
        parameters: {
            query?: {
                limit?: components["parameters"]["PageSize"];
                cursor?: components["parameters"]["PageCursor"];
            };
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                task_id: components["parameters"]["TaskId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ArtifactPage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getArtifact: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                artifact_id: components["parameters"]["ArtifactId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Artifact"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    previewArtifact: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                artifact_id: components["parameters"]["ArtifactId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ArtifactPreview"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    downloadArtifact: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: components["parameters"]["ProjectId"];
                artifact_id: components["parameters"]["ArtifactId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Authorized attachment */
            200: {
                headers: {
                    "Content-Disposition": string;
                    "Cache-Control": "no-store";
                    "X-Content-Type-Options": "nosniff";
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    listTaskDrafts: {
        parameters: {
            query?: {
                limit?: components["parameters"]["PageSize"];
                cursor?: components["parameters"]["PageCursor"];
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Current user draft page */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedTaskDraftPage"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    getTaskDraft: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                draft_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Saved draft */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedTaskDraft"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    saveTaskDraft: {
        parameters: {
            query?: never;
            header: {
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                project_id: string;
                draft_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SaveDraftRequest"];
            };
        };
        responses: {
            /** @description Saved draft */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedTaskDraft"];
                };
            };
            /** @description Session missing or expired */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Insufficient permission or invalid CSRF/Origin */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Resource unavailable to this caller */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Version, idempotency, transition or expired preview conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Cursor or artifact expired */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Invalid structured input */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unexpected server error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Authority unavailable; fail closed */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    tenants_api_v1_tenants_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TenantPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    list_service_definitions: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                tenant_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelDefinitionPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    create_service_definition: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServiceVersionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    list_service_versions: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                tenant_id: string;
                definition_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelVersionPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    create_service_version: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
                definition_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServiceVersionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    get_service_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tenant_id: string;
                version_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelVersion"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    list_profile_definitions: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                tenant_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelDefinitionPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    create_profile_definition: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileVersionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    list_profile_versions: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                tenant_id: string;
                definition_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelVersionPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    create_profile_version: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
                definition_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileVersionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    get_profile_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tenant_id: string;
                version_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelVersion"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    check_model_api_v1_tenants__tenant_id__model_profile_versions__version_id__checks_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
                version_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ModelCheckRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    command_model_api_v1_tenants__tenant_id__model_profile_versions__version_id__commands_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token"?: string | null;
                /** @description Must equal the configured platform origin. */
                Origin: string;
            };
            path: {
                tenant_id: string;
                version_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ModelVersionCommand"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    operation_api_v1_tenants__tenant_id__model_operations__operation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tenant_id: string;
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    operation_key_api_v1_tenants__tenant_id__model_operation_keys__key__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tenant_id: string;
                key: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOperation"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
    project_models_api_v1_projects__project_id__model_profiles_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelVersionPage"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Gone */
            410: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Error"];
                };
            };
        };
    };
}
