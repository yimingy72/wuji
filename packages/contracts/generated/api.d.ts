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
        /** List Tasks */
        get: operations["list_tasks_api_v1_projects__project_id__tasks_get"];
        put?: never;
        /** Create Task */
        post: operations["create_task_api_v1_projects__project_id__tasks_post"];
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
        /** Get Task */
        get: operations["get_task_api_v1_projects__project_id__tasks__task_id__get"];
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
        /** Control Task */
        post: operations["control_task_api_v1_projects__project_id__tasks__task_id__commands_post"];
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
        /** List Task Events */
        get: operations["list_task_events_api_v1_projects__project_id__tasks__task_id__events_get"];
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
        /** Get Task Artifacts */
        get: operations["get_task_artifacts_api_v1_projects__project_id__tasks__task_id__artifacts_get"];
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
        /** List Drafts */
        get: operations["list_drafts_api_v1_projects__project_id__task_drafts_get"];
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
        /** Get Draft */
        get: operations["get_draft_api_v1_projects__project_id__task_drafts__draft_id__get"];
        /** Save Draft */
        put: operations["save_draft_api_v1_projects__project_id__task_drafts__draft_id__put"];
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
    "/projects/{project_id}/scenario-profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Profiles */
        get: operations["get_profiles_api_v1_projects__project_id__scenario_profiles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/task-creation-previews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview */
        post: operations["preview_api_v1_projects__project_id__task_creation_previews_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/agent-runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Agent Runs */
        get: operations["get_agent_runs_api_v1_projects__project_id__tasks__task_id__agent_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/tool-calls": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Tool Calls */
        get: operations["get_tool_calls_api_v1_projects__project_id__tasks__task_id__tool_calls_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/blackboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Blackboard */
        get: operations["blackboard_api_v1_projects__project_id__tasks__task_id__blackboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/result": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Result */
        get: operations["result_api_v1_projects__project_id__tasks__task_id__result_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/projects/{project_id}/tasks/{task_id}/artifacts/{artifact_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download */
        get: operations["download_api_v1_projects__project_id__tasks__task_id__artifacts__artifact_id__content_get"];
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
        /** TaskControlRequest */
        TaskControl: {
            /**
             * Action
             * @enum {string}
             */
            action: "start" | "pause" | "resume" | "cancel";
            /** Expected Version */
            expected_version: number;
        };
        ExecutionSummary: {
            active_calls: number;
            unknown_calls: number;
            /** @enum {string} */
            egress_state: "pending" | "active" | "frozen" | "revoked" | "not_granted" | "unknown";
        };
        Task: components["schemas"]["LegacyTask"] | components["schemas"]["WebTask"];
        /** TaskSnapshotResponse */
        TaskSnapshot: {
            /** Task */
            task: components["schemas"]["LegacyTask"] | components["schemas"]["WebTask"];
            /** Event Cursor */
            event_cursor: string;
        };
        /** CommandReceiptResponse */
        CommandReceipt: {
            /**
             * Command Id
             * Format: uuid
             */
            command_id: string;
            /**
             * Idempotency Key
             * Format: uuid
             */
            idempotency_key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "create" | "start" | "cancel";
            /**
             * Disposition
             * @constant
             */
            disposition: "accepted";
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /**
             * Accepted At
             * Format: date-time
             */
            accepted_at: string;
            /** Accepted Task Version */
            accepted_task_version: number;
            /** Request Digest */
            request_digest: string;
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
        /** Artifact */
        Artifact: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Mime */
            mime: string;
            /** Size */
            size: number;
            /** Sha256 */
            sha256: string;
            /** State */
            state: string;
            /**
             * Created At
             * Format: date-time
             */
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
        /** TaskPageResponse */
        TaskPage: {
            /** Items */
            items: (components["schemas"]["LegacyTask"] | components["schemas"]["WebTask"])[];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ArtifactPage */
        ArtifactPage: {
            /** Items */
            items: components["schemas"]["Artifact"][];
            /** Next Cursor */
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
            content: (components["schemas"]["CtfDraft"] | components["schemas"]["WebDraft"] | components["schemas"]["ComprehensiveDraft"] | components["schemas"]["ExerciseDraft"] | components["schemas"]["CodeAuditDraft"]) | (components["schemas"]["CtfDraftV2"] | components["schemas"]["WebDraftV2"] | components["schemas"]["ComprehensiveDraftV2"] | components["schemas"]["ExerciseDraftV2"] | components["schemas"]["CodeAuditDraftV2"]);
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
            content: (components["schemas"]["CtfDraft"] | components["schemas"]["WebDraft"] | components["schemas"]["ComprehensiveDraft"] | components["schemas"]["ExerciseDraft"] | components["schemas"]["CodeAuditDraft"]) | (components["schemas"]["CtfDraftV2"] | components["schemas"]["WebDraftV2"] | components["schemas"]["ComprehensiveDraftV2"] | components["schemas"]["ExerciseDraftV2"] | components["schemas"]["CodeAuditDraftV2"]);
            /**
             * Selected Model Summary
             * @default null
             */
            selected_model_summary: {
                [key: string]: unknown;
            } | null;
            /**
             * Last Created Task Id
             * @default null
             */
            last_created_task_id: string | null;
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
            /**
             * Cache Read Per Million
             * @default null
             */
            cache_read_per_million: string | null;
            /**
             * Cache Creation Per Million
             * @default null
             */
            cache_creation_per_million: string | null;
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
            /**
             * Context Window
             * @default null
             */
            context_window: number | null;
            /**
             * Max Output Tokens
             * @default null
             */
            max_output_tokens: number | null;
            /**
             * Timeout Seconds
             * @default 30
             */
            timeout_seconds: number;
            /** @default null */
            pricing: components["schemas"]["ModelPricing"] | null;
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
        /** ExecutionSummaryResponse */
        ExecutionSummaryResponse: {
            /** Active Calls */
            active_calls: number;
            /** Unknown Calls */
            unknown_calls: number;
            /**
             * Egress State
             * @constant
             */
            egress_state: "not_granted";
        };
        /** ScopeBindingModel */
        ScopeBindingModel: {
            /**
             * Policy Id
             * Format: uuid
             */
            policy_id: string;
            /** Version */
            version: number;
        };
        /** TaskResponse */
        LegacyTask: {
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
            /** Name */
            name: string;
            /** Target Url */
            target_url: string;
            scope: components["schemas"]["ScopeBindingModel"];
            /** Version */
            version: number;
            /**
             * State
             * @enum {string}
             */
            state: "queued" | "cancelled";
            /**
             * Cleanup State
             * @constant
             */
            cleanup_state: "not_required";
            execution: components["schemas"]["ExecutionSummaryResponse"];
            /** Allowed Actions */
            allowed_actions: "cancel"[];
            /**
             * Assessment Outcome
             * @constant
             */
            assessment_outcome: "not_assessed";
            /** Stop Reason */
            stop_reason: "user_cancelled" | null;
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
        /** CodeAuditDraftV2 */
        CodeAuditDraftV2: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "2.0";
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
            /** @default null */
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Completion Criteria */
            completion_criteria?: string[];
            /**
             * Supplemental Hints
             * @default
             */
            supplemental_hints: string;
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
        /** ComprehensiveDraftV2 */
        ComprehensiveDraftV2: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "2.0";
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
            /** @default null */
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Completion Criteria */
            completion_criteria?: string[];
            /**
             * Supplemental Hints
             * @default
             */
            supplemental_hints: string;
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
        /** CreationConfigSnapshot */
        CreationConfigSnapshot: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "1.0";
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Scenario
             * @constant
             */
            scenario: "web_single";
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Objective */
            objective: string;
            /** Completion Criteria */
            completion_criteria: string[];
            /** Supplemental Hints */
            supplemental_hints: string;
            /** Actual Input */
            actual_input: components["schemas"]["CtfDraftV2"] | components["schemas"]["WebDraftV2"] | components["schemas"]["ComprehensiveDraftV2"] | components["schemas"]["ExerciseDraftV2"] | components["schemas"]["CodeAuditDraftV2"];
            authorization: components["schemas"]["TaskAuthorization"];
            /**
             * Authorization Id
             * Format: uuid
             */
            authorization_id: string;
            /** Authorization Digest */
            authorization_digest: string;
            model: components["schemas"]["SelectedModelSnapshot"];
            /** Budget Usd */
            budget_usd: string;
            /**
             * Created By
             * Format: uuid
             */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Digest */
            digest: string;
        };
        /** CtfDraftV2 */
        CtfDraftV2: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "2.0";
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
            /** @default null */
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Completion Criteria */
            completion_criteria?: string[];
            /**
             * Supplemental Hints
             * @default
             */
            supplemental_hints: string;
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
        /** Endpoint */
        Endpoint: {
            /**
             * Scheme
             * @enum {string}
             */
            scheme: "http" | "https";
            /** Port */
            port: number;
        };
        /** ExcludeRule */
        ExcludeRule: {
            /** Host */
            host: string;
            /**
             * Include Subdomains
             * @default false
             */
            include_subdomains: boolean;
            /**
             * Endpoints
             * @default all_included
             */
            endpoints: "all_included" | components["schemas"]["Endpoint"][];
        };
        /** ExerciseDraftV2 */
        ExerciseDraftV2: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "2.0";
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
            /** @default null */
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Completion Criteria */
            completion_criteria?: string[];
            /**
             * Supplemental Hints
             * @default
             */
            supplemental_hints: string;
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
        /** GoalTemplateReference */
        GoalTemplateReference: {
            /** Id */
            id: string;
            /** Version */
            version: number;
            /** Digest */
            digest: string;
        };
        /** IncludeRule */
        IncludeRule: {
            /** Host */
            host: string;
            /**
             * Include Subdomains
             * @default false
             */
            include_subdomains: boolean;
            endpoint: components["schemas"]["Endpoint"];
        };
        /** SelectedModelSnapshot */
        SelectedModelSnapshot: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Definition Id
             * Format: uuid
             */
            definition_id: string;
            /** Number */
            number: number;
            /** Name */
            name: string;
            /** State Revision */
            state_revision: number;
            config: components["schemas"]["ProfileConfig"];
        };
        /** TaskAuthorization */
        TaskAuthorization: {
            /**
             * Schema Version
             * @default 1.0
             * @constant
             */
            schema_version: "1.0";
            /** Includes */
            includes?: components["schemas"]["IncludeRule"][];
            /** Excludes */
            excludes?: components["schemas"]["ExcludeRule"][];
            /**
             * Valid Until
             * @default null
             */
            valid_until: string | null;
        };
        /** TaskAuthorizationBindingResponse */
        TaskAuthorizationBindingResponse: {
            /**
             * Authorization Id
             * Format: uuid
             */
            authorization_id: string;
            /** Version */
            version: number;
            /** Hash */
            hash: string;
        };
        /** WebDraftV2 */
        WebDraftV2: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "2.0";
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
            /** @default null */
            goal_template: components["schemas"]["GoalTemplateReference"] | null;
            /** Completion Criteria */
            completion_criteria?: string[];
            /**
             * Supplemental Hints
             * @default
             */
            supplemental_hints: string;
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
            /** @default null */
            authorization: components["schemas"]["TaskAuthorization"] | null;
        };
        /** WebExecutionSummaryResponse */
        WebExecutionSummaryResponse: {
            /** Active Calls */
            active_calls: number;
            /** Unknown Calls */
            unknown_calls: number;
            /**
             * Egress State
             * @enum {string}
             */
            egress_state: "not_granted" | "fixture_only" | "revoking" | "revoked" | "unknown";
        };
        /** WebTaskResponse */
        WebTask: {
            /**
             * Task Kind
             * @default web_assessment
             * @constant
             */
            task_kind: "web_assessment";
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
            /** Name */
            name: string;
            /** Target Url */
            target_url: string;
            scope: components["schemas"]["TaskAuthorizationBindingResponse"];
            /** Version */
            version: number;
            /**
             * State
             * @enum {string}
             */
            state: "ready" | "provisioning" | "running" | "completing" | "completed" | "cancelling" | "cancelled" | "reconciling";
            /**
             * Cleanup State
             * @enum {string}
             */
            cleanup_state: "not_required" | "pending" | "running" | "completed" | "failed" | "unknown";
            execution: components["schemas"]["WebExecutionSummaryResponse"];
            /** Allowed Actions */
            allowed_actions: ("start" | "cancel")[];
            /**
             * Assessment Outcome
             * @enum {string}
             */
            assessment_outcome: "not_assessed" | "complete" | "partial" | "inconclusive";
            /** Stop Reason */
            stop_reason: string | null;
            creation_config: components["schemas"]["CreationConfigSnapshot"];
            /** Start Blockers */
            start_blockers?: string[];
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
        /** ScopeConfirmation */
        ScopeConfirmation: {
            /**
             * Accepted
             * @constant
             */
            accepted: true;
            /** Authorization Digest */
            authorization_digest: string;
        };
        /** NewCreateTaskRequest */
        NewCreateTaskRequest: {
            /**
             * Draft Id
             * Format: uuid
             */
            draft_id: string;
            /** Draft Version */
            draft_version: number;
            /**
             * Creation Kind
             * @constant
             */
            creation_kind: "saved_web_draft";
            /**
             * Preview Id
             * Format: uuid
             */
            preview_id: string;
            /** Input Digest */
            input_digest: string;
            scope_confirmation: components["schemas"]["ScopeConfirmation"];
        };
        /** CreationBlocker */
        CreationBlocker: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** TaskCreationPreview */
        TaskCreationPreview: {
            /**
             * Preview Id
             * Format: uuid
             */
            preview_id: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /**
             * Start Available
             * @default false
             * @constant
             */
            start_available: false;
            /**
             * Draft Id
             * Format: uuid
             */
            draft_id: string;
            /** Draft Version */
            draft_version: number;
            /** Normalized Content */
            normalized_content: (components["schemas"]["CtfDraft"] | components["schemas"]["WebDraft"] | components["schemas"]["ComprehensiveDraft"] | components["schemas"]["ExerciseDraft"] | components["schemas"]["CodeAuditDraft"]) | (components["schemas"]["CtfDraftV2"] | components["schemas"]["WebDraftV2"] | components["schemas"]["ComprehensiveDraftV2"] | components["schemas"]["ExerciseDraftV2"] | components["schemas"]["CodeAuditDraftV2"]);
            model_snapshot: components["schemas"]["SelectedModelSnapshot"] | null;
            /** Input Digest */
            input_digest: string;
            /** Authorization Digest */
            authorization_digest: string;
            /** Can Create */
            can_create: boolean;
            /** Blockers */
            blockers: components["schemas"]["CreationBlocker"][];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** ScenarioProfile */
        ScenarioProfile: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "1.0";
            /** Id */
            id: string;
            /** Version */
            version: number;
            /**
             * Scenario
             * @enum {string}
             */
            scenario: "ctf" | "web_single" | "comprehensive" | "exercise" | "code_audit";
            /** Name */
            name: string;
            /** Objective */
            objective: string;
            /** Completion Criteria */
            completion_criteria: string[];
            /** Digest */
            digest: string;
            /** Can Create */
            can_create: boolean;
        };
        /** ScenarioProfilePage */
        ScenarioProfilePage: {
            /** Items */
            items: components["schemas"]["ScenarioProfile"][];
        };
        SaveTaskDraftRequest: components["schemas"]["SaveDraftRequest"];
        DraftContentV2: components["schemas"]["CtfDraftV2"] | components["schemas"]["WebDraftV2"] | components["schemas"]["ComprehensiveDraftV2"] | components["schemas"]["ExerciseDraftV2"] | components["schemas"]["CodeAuditDraftV2"];
        WebDraftContentV2: components["schemas"]["WebDraftV2"];
        /** CreationPreviewRequest */
        CreationPreviewRequest: {
            /**
             * Draft Id
             * Format: uuid
             */
            draft_id: string;
            /** Draft Version */
            draft_version: number;
        };
        /** AgentRun */
        AgentRun: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Phase
             * @enum {string}
             */
            phase: "bootstrap" | "reason" | "explore";
            /** Intent Id */
            intent_id: string | null;
            /** Worker Profile Id */
            worker_profile_id: string;
            /** State */
            state: string;
            /** Result State */
            result_state: string;
            /** Outcome */
            outcome: string | null;
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
        /** AgentRunPage */
        AgentRunPage: {
            /** Items */
            items: components["schemas"]["AgentRun"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** ToolCall */
        ToolCall: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Agent Run Id
             * Format: uuid
             */
            agent_run_id: string;
            /** Tool */
            tool: string;
            /** State */
            state: string;
            /** Args */
            args: {
                [key: string]: unknown;
            };
            /** Result */
            result: {
                [key: string]: unknown;
            } | null;
            /** Cancel Requested */
            cancel_requested: boolean;
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
        /** ToolCallPage */
        ToolCallPage: {
            /** Items */
            items: components["schemas"]["ToolCall"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** GraphFact */
        GraphFact: {
            /** Id */
            id: string;
            /** Description */
            description: string;
        };
        /** NativeGraph */
        NativeGraph: {
            /** Project */
            project: {
                [key: string]: unknown;
            };
            /** Facts */
            facts: components["schemas"]["GraphFact"][];
            /** Intents */
            intents: {
                [key: string]: unknown;
            }[];
            /** Hints */
            hints: {
                [key: string]: unknown;
            }[];
        };
        /** BlackBoardSnapshot */
        BlackBoardSnapshot: {
            /**
             * State
             * @enum {string}
             */
            state: "pending" | "available";
            /** Native Project Id */
            native_project_id: string | null;
            graph: components["schemas"]["NativeGraph"] | null;
            /** Captured At */
            captured_at: string | null;
            /** Digest */
            digest: string | null;
        };
        /** TaskResult */
        TaskResult: {
            /**
             * State
             * @enum {string}
             */
            state: "pending" | "available";
            /**
             * Goal Status
             * @enum {string}
             */
            goal_status: "unknown" | "met" | "not_met";
            /** Summary */
            summary: string;
            /** Limitations */
            limitations: string[];
            /** Artifact Ids */
            artifact_ids: string[];
            /** Model Spend */
            model_spend: string | null;
            /** Cost State */
            cost_state: string;
        };
        /** EventPageResponse */
        EventPageResponse: {
            /** Items */
            items: components["schemas"]["TaskEventResponse"][];
            /** Next Cursor */
            next_cursor: string;
            /** Has More */
            has_more: boolean;
        };
        /** TaskEventResponse */
        TaskEventResponse: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "1.0";
            /**
             * Event Id
             * Format: uuid
             */
            event_id: string;
            /** Cursor */
            cursor: string;
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
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** Aggregate Version */
            aggregate_version: number;
            /**
             * Type
             * @constant
             */
            type: "task.changed";
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Trace Id
             * Format: uuid
             */
            trace_id: string;
            /** Summary */
            summary: string;
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
                /** @description Allowlisted local project/task/draft or tenant-model route; unsupported routes are rejected. */
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
    list_tasks_api_v1_projects__project_id__tasks_get: {
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
                    "application/json": components["schemas"]["TaskPage"];
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
    create_task_api_v1_projects__project_id__tasks_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token": string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateTask"] | components["schemas"]["NewCreateTaskRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
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
    get_task_api_v1_projects__project_id__tasks__task_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["TaskSnapshot"];
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
    control_task_api_v1_projects__project_id__tasks__task_id__commands_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
                "X-CSRF-Token": string | null;
            };
            path: {
                project_id: string;
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskControl"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommandReceipt"];
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
    list_task_events_api_v1_projects__project_id__tasks__task_id__events_get: {
        parameters: {
            query?: {
                after?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["EventPageResponse"];
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
    get_task_artifacts_api_v1_projects__project_id__tasks__task_id__artifacts_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["ArtifactPage"];
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
    list_drafts_api_v1_projects__project_id__task_drafts_get: {
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
                    "application/json": components["schemas"]["SavedTaskDraftPage"];
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
    get_draft_api_v1_projects__project_id__task_drafts__draft_id__get: {
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
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedTaskDraft"];
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
    save_draft_api_v1_projects__project_id__task_drafts__draft_id__put: {
        parameters: {
            query?: never;
            header: {
                "X-CSRF-Token": string | null;
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
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedTaskDraft"];
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
    get_profiles_api_v1_projects__project_id__scenario_profiles_get: {
        parameters: {
            query?: never;
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
                    "application/json": components["schemas"]["ScenarioProfilePage"];
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
    preview_api_v1_projects__project_id__task_creation_previews_post: {
        parameters: {
            query?: never;
            header: {
                "X-CSRF-Token": string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreationPreviewRequest"];
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
                    "application/json": components["schemas"]["TaskCreationPreview"];
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
    get_agent_runs_api_v1_projects__project_id__tasks__task_id__agent_runs_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["AgentRunPage"];
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
    get_tool_calls_api_v1_projects__project_id__tasks__task_id__tool_calls_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["ToolCallPage"];
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
    blackboard_api_v1_projects__project_id__tasks__task_id__blackboard_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["BlackBoardSnapshot"];
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
    result_api_v1_projects__project_id__tasks__task_id__result_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                task_id: string;
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
                    "application/json": components["schemas"]["TaskResult"];
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
    download_api_v1_projects__project_id__tasks__task_id__artifacts__artifact_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                task_id: string;
                artifact_id: string;
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
                    "application/json": unknown;
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
            /** @description Validation Error */
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
