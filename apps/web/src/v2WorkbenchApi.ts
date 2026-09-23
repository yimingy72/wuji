import type { components } from '../../../packages/contracts/src/v2/generated';
import { apiUrl } from './config';
import { ApiRequestError } from './api';

export type TaskCreate = components['schemas']['TaskCreate'];
export type TaskCommand = components['schemas']['TaskCommand'];
export type TaskView = components['schemas']['TaskView'];
export type TaskList = components['schemas']['TaskList'];
export type TaskOptions = components['schemas']['TaskOptions'];
export type ReadinessReport = components['schemas']['ReadinessReport'];
export type LaunchView = components['schemas']['LaunchView'];
export type CommandReceipt = components['schemas']['CommandReceipt'];
export type ModelMaterialV2 = components['schemas']['ModelMaterialV2'];
export type ReadinessCheck = components['schemas']['ReadinessCheck'];
export type TaskProfileOption = components['schemas']['TaskProfileOption'];
export type TaskOverviewV1 = components['schemas']['TaskOverviewV1'];
export type RuntimeCaptureSessionPageV1 = components['schemas']['RuntimeCaptureSessionPageV1'];
export type RuntimeCaptureItemPageV1 = components['schemas']['RuntimeCaptureItemPageV1'];

export type CommandInventoryItem = components['schemas']['TaskCommandItemV1'];
export type PublicationInventoryItem = components['schemas']['TaskPublicationItemV1'];
export interface InventoryPage<T> {
  readonly schema_version: string;
  readonly items: readonly T[];
  readonly next_after: string | null;
}
export type TaskActivityPageV1 = components['schemas']['TaskActivityPageV1'];
export type TaskActivityItemV1 = components['schemas']['TaskActivityItemV1'];
export type ExplorationViewV1 = components['schemas']['ExplorationViewV1'];
export type TaskInputListV1 = components['schemas']['TaskInputListV1'];
export type InputAnswerReceiptV1 = components['schemas']['InputAnswerReceiptV1'];

export interface WorkbenchSession {
  readonly authenticated: true;
  readonly identity_mode: string;
  readonly project_id: string;
  readonly display_name: string;
  readonly task_id?: string | null;
  readonly expires_at?: string | null;
  readonly csrf_token?: string | null;
}

interface RawWorkbenchSession {
  readonly authenticated: true;
  readonly mode?: string;
  readonly identity_mode?: string;
  readonly project_id: string;
  readonly display_name: string;
  readonly task_id?: string | null;
  readonly initial_task_id?: string | null;
  readonly expires_at?: string | null;
  readonly csrf_token?: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string';
}

function isTaskCommand(value: unknown): value is TaskCommand['command'] {
  return value === 'start' || value === 'pause' || value === 'resume' || value === 'cancel' || value === 'finish';
}

function isTaskView(value: unknown): value is TaskView {
  if (!isRecord(value)) return false;
  return isString(value.task_id)
    && isString(value.tenant_id)
    && isString(value.project_id)
    && isString(value.version)
    && isString(value.name)
    && (value.scenario === 'ctf' || value.scenario === 'web_single' || value.scenario === 'comprehensive' || value.scenario === 'adversary_emulation' || value.scenario === 'code_audit')
    && (value.desired_state === 'run' || value.desired_state === 'pause' || value.desired_state === 'cancel' || value.desired_state === 'finish')
    && (value.observed_state === 'ready' || value.observed_state === 'running' || value.observed_state === 'quiescing' || value.observed_state === 'paused' || value.observed_state === 'reconciling' || value.observed_state === 'closed')
    && isString(value.goal_revision)
    && isString(value.execution_epoch)
    && (value.activated_at === undefined || value.activated_at === null || typeof value.activated_at === 'string')
    && (value.close_trigger === undefined || value.close_trigger === null || typeof value.close_trigger === 'string')
    && (value.result_outcome === undefined || value.result_outcome === null || typeof value.result_outcome === 'string')
    && Array.isArray(value.allowed_actions)
    && value.allowed_actions.every(isTaskCommand);
}

function isTaskList(value: unknown): value is TaskList {
  return isRecord(value)
    && Array.isArray(value.items)
    && value.items.every(isTaskView)
    && isNullableString(value.next_cursor);
}

function isTaskProfileOption(value: unknown): value is TaskProfileOption {
  return isRecord(value)
    && isString(value.ref)
    && isString(value.name)
    && isString(value.revision)
    && isString(value.digest)
    && Array.isArray(value.capabilities)
    && value.capabilities.every(isString)
    && typeof value.real_model_allowed === 'boolean'
    && (value.max_explore_concurrency === undefined
      || value.max_explore_concurrency === null
      || (Number.isInteger(value.max_explore_concurrency)
        && Number(value.max_explore_concurrency) >= 1
        && Number(value.max_explore_concurrency) <= 256));
}

function isReadinessCheck(value: unknown): value is ReadinessCheck {
  return isRecord(value)
    && isString(value.id)
    && (value.layer === 'identity' || value.layer === 'profile' || value.layer === 'budget' || value.layer === 'model' || value.layer === 'runtime' || value.layer === 'target' || value.layer === 'material')
    && (value.status === 'pass' || value.status === 'fail' || value.status === 'unknown' || value.status === 'not_applicable')
    && isString(value.reason_code)
    && isString(value.observed_at)
    && (value.evidence_ref === undefined || value.evidence_ref === null || typeof value.evidence_ref === 'string')
    && (value.remediation_owner === 'user' || value.remediation_owner === 'application' || value.remediation_owner === 'gateway' || value.remediation_owner === 'infrastructure')
    && isString(value.message);
}

function isTaskOptions(value: unknown): value is TaskOptions {
  return isRecord(value)
    && isString(value.project_id)
    && Array.isArray(value.model_profiles)
    && value.model_profiles.every(isTaskProfileOption)
    && Array.isArray(value.runtime_profiles)
    && value.runtime_profiles.every(isTaskProfileOption)
    && Array.isArray(value.missing)
    && value.missing.every(isReadinessCheck);
}

function isTaskOverview(value: unknown): value is TaskOverviewV1 {
  if (!isRecord(value) || value.schema_version !== 'wuji.task-overview.v1' || !isString(value.task_id) || !isString(value.observed_at) || typeof value.status_message !== 'string') return false;
  if (!isRecord(value.goal) || !isString(value.goal.text) || !Array.isArray(value.goal.criteria)) return false;
  if (!value.goal.criteria.every((criterion) => isRecord(criterion)
    && isString(criterion.criterion_id) && isString(criterion.object) && isString(criterion.condition)
    && typeof criterion.required === 'boolean'
    && ['met', 'not_met', 'unknown', 'not_applicable', 'missing'].includes(String(criterion.judgment_status))
    && ['current', 'stale', 'disputed', 'retracted', 'missing'].includes(String(criterion.judgment_applicability)))) return false;
  if (!isRecord(value.budget) || !isString(value.budget.amount) || value.budget.currency !== 'USD') return false;
  if (!Array.isArray(value.current_work) || !value.current_work.every((work) => isRecord(work)
    && isString(work.work_item_id) && ['reason', 'explore', 'report'].includes(String(work.kind))
    && isString(work.state) && isNullableString(work.question) && isNullableString(work.result_summary)
    && isNullableString(work.blocked_reason) && isNullableString(work.terminal_reason)
    && isNullableString(work.run_process_state) && isNullableString(work.updated_at))) return false;
  if (!Array.isArray(value.latest_findings) || !value.latest_findings.every((finding) => isRecord(finding)
    && isKnowledgeRef(finding.claim_ref) && isString(finding.text) && isString(finding.kind)
    && isString(finding.grounding_state) && isString(finding.evidence_state) && isString(finding.applicability_state)
    && Array.isArray(finding.supporting_refs) && finding.supporting_refs.every(isKnowledgeRef)
    && Array.isArray(finding.opposing_refs) && finding.opposing_refs.every(isKnowledgeRef)
    && isString(finding.updated_at))) return false;
  if (!Array.isArray(value.artifacts) || !value.artifacts.every((artifact) => isRecord(artifact)
    && isBlobRef(artifact.artifact_ref) && isString(artifact.state) && isString(artifact.media_type)
    && isString(artifact.size_bytes) && isString(artifact.completeness) && isString(artifact.provenance)
    && isString(artifact.created_at) && isNullableString(artifact.source_work_item_id)
    && typeof artifact.download_available === 'boolean')) return false;
  if (!isRecord(value.runtime)
    || !['not_started', 'running', 'stopping', 'stopped', 'unknown'].includes(String(value.runtime.state))
    || !isString(value.runtime.runtime_attempt)
    || !isNullableString(value.runtime.pod_uid)
    || !isRecord(value.runtime.containers)
    || !Array.isArray(value.runtime.terminal_observation_ids)
    || !value.runtime.terminal_observation_ids.every(isString)
    || !Array.isArray(value.runtime.terminal_observations)) return false;
  return isRecord(value.workspace_capabilities)
    && typeof value.workspace_capabilities.work_files === 'boolean'
    && typeof value.workspace_capabilities.shared_versions === 'boolean'
    && typeof value.workspace_capabilities.command_output === 'boolean'
    && isRecord(value.technical) && isString(value.technical.definition_digest)
    && isString(value.technical.control_version) && isString(value.technical.execution_epoch)
    && isString(value.technical.runtime_attempt) && isString(value.technical.schema_version)
    && isNullableString(value.technical.latest_launch_operation_id)
    && isNullableString(value.technical.latest_launch_phase)
    && isNullableString(value.technical.latest_launch_reason_code);
}

function isTaskActivityPage(value: unknown): value is TaskActivityPageV1 {
  return isRecord(value) && value.schema_version === 'wuji.task-activity.v1'
    && isString(value.task_id) && isString(value.observed_at) && isString(value.latest_cursor)
    && isNullableString(value.next_cursor) && Array.isArray(value.items)
    && value.items.every((item) => isRecord(item) && isString(item.activity_id)
      && isString(item.event_cursor) && isString(item.occurred_at)
      && ['task', 'work', 'finding', 'evidence', 'input', 'completion', 'tool'].includes(String(item.category))
      && (item.importance === 'key' || item.importance === 'detail')
      && ['pending', 'running', 'succeeded', 'failed', 'blocked', 'stopped', 'info'].includes(String(item.status))
      && isString(item.summary) && isNullableString(item.work_item_id)
      && isNullableString(item.source_ref) && isNullableString(item.reason)
      && Array.isArray(item.evidence_refs) && item.evidence_refs.every(isKnowledgeRef)
      && Number.isInteger(item.step_count) && Number(item.step_count) >= 0);
}

function isReadinessReport(value: unknown): value is ReadinessReport {
  return isRecord(value)
    && isString(value.task_id)
    && isString(value.definition_digest)
    && isString(value.observed_at)
    && typeof value.can_request_start === 'boolean'
    && Array.isArray(value.checks)
    && value.checks.every(isReadinessCheck);
}

function isLaunchView(value: unknown): value is LaunchView {
  return isRecord(value)
    && isNullableString(value.operation_id)
    && isNullableString(value.command_id)
    && isString(value.task_id)
    && isString(value.definition_digest)
    && isNullableString(value.profile_digest)
    && isNullableString(value.runtime_attempt)
    && isNullableString(value.execution_epoch)
    && (value.phase === 'not_requested' || value.phase === 'prepare' || value.phase === 'activate' || value.phase === 'wire' || value.phase === 'capability' || value.phase === 'ready')
    && (value.phase_status === 'not_requested' || value.phase_status === 'pending' || value.phase_status === 'running' || value.phase_status === 'reconciling' || value.phase_status === 'blocked' || value.phase_status === 'succeeded' || value.phase_status === 'cancelled' || value.phase_status === 'failed')
    && isNullableString(value.reason_code)
    && Array.isArray(value.allowed_actions)
    && value.allowed_actions.every(isTaskCommand)
    && isString(value.observed_at);
}

function isCommandReceipt(value: unknown): value is CommandReceipt {
  return isRecord(value)
    && isString(value.command_id)
    && (value.disposition === 'accepted' || value.disposition === 'rejected' || value.disposition === 'already_recorded')
    && isRecord(value.resource_ref)
    && (value.resource_ref.entity_type === 'task' || value.resource_ref.entity_type === 'work_item' || value.resource_ref.entity_type === 'approval')
    && isString(value.resource_ref.id)
    && isString(value.resource_ref.revision)
    && isString(value.resource_version)
    && isString(value.request_id)
    && (value.code === undefined || value.code === null || typeof value.code === 'string');
}

function isBlobRef(value: unknown): value is components['schemas']['BlobRef'] {
  return isRecord(value) && isString(value.id) && isString(value.version) && isString(value.sha256);
}

function isKnowledgeRef(value: unknown): value is components['schemas']['KnowledgeRef'] {
  return isRecord(value) && isString(value.entity_type) && isString(value.id) && isString(value.revision);
}

function isExplorationView(value: unknown): value is ExplorationViewV1 {
  return isRecord(value)
    && value.schema_version === 'wuji.exploration-view.v1'
    && isString(value.task_id)
    && isString(value.snapshot_id)
    && isString(value.view_revision)
    && isString(value.projection_version)
    && (value.mode === 'live' || value.mode === 'history')
    && Array.isArray(value.problems)
    && value.problems.every((problem) => isRecord(problem)
      && isKnowledgeRef(problem.intent_ref)
      && isString(problem.question)
      && (problem.public_rationale === null || typeof problem.public_rationale === 'string')
      && Array.isArray(problem.basis_refs)
      && problem.basis_refs.every(isKnowledgeRef)
      && Array.isArray(problem.attempts)
      && Array.isArray(problem.gaps))
    && Array.isArray(value.insights)
    && value.insights.every((insight) => isRecord(insight)
      && isKnowledgeRef(insight.claim_ref)
      && isString(insight.text)
      && Array.isArray(insight.source_refs)
      && insight.source_refs.every(isKnowledgeRef))
    && Array.isArray(value.relations)
    && value.relations.every((relation) => isRecord(relation)
      && isString(relation.relation_id)
      && isString(relation.source_ref)
      && isString(relation.target_ref)
      && Array.isArray(relation.witness_refs)
      && relation.witness_refs.every(isString))
    && isRecord(value.execution_summary)
    && isString(value.opaque_cursor)
    && isNullableString(value.continuation)
    && Array.isArray(value.missing_fields)
    && value.missing_fields.every(isString);
}

function isTaskInputList(value: unknown): value is TaskInputListV1 {
  return isRecord(value) && value.schema_version === 'wuji.task-inputs.v1'
    && isString(value.task_id) && Array.isArray(value.items)
    && value.items.every((item) => isRecord(item) && isString(item.input_request_id)
      && isString(item.work_item_id) && (item.kind === 'question' || item.kind === 'approval')
      && item.status === 'pending' && isString(item.prompt) && isString(item.manifest_ref));
}

function isInputAnswerReceipt(value: unknown): value is InputAnswerReceiptV1 {
  return isRecord(value) && value.schema_version === 'wuji.input-answer.v1'
    && isString(value.input_request_id) && isString(value.delivery_id)
    && value.status === 'resolved';
}

function isModelMaterial(value: unknown): value is ModelMaterialV2 {
  if (!isRecord(value) || value.schema_version !== 'wuji.model-material.v2' || !isString(value.tool_call_id)) return false;
  if (value.status !== 'delivered' && value.status !== 'omitted') return false;
  if (value.source !== null && (!isRecord(value.source) || !isBlobRef(value.source.artifact_ref) || !isString(value.source.artifact_sha256) || !isString(value.source.media_type)
    || (value.source.completeness !== 'complete' && value.source.completeness !== 'partial' && value.source.completeness !== 'unknown'))) return false;
  if (value.status === 'omitted') return value.representation === null && isString(value.omission_reason);
  if (value.source === null) return false;
  if (!isRecord(value.representation) || value.representation.renderer_version !== 'wuji-http-renderer.v2' || value.representation.media_type !== 'text/plain; charset=utf-8' || value.representation.encoding !== 'utf-8' || typeof value.representation.text !== 'string' || typeof value.representation.byte_length !== 'number' || !isString(value.representation.representation_sha256) || typeof value.representation.truncated !== 'boolean' || typeof value.representation.redaction_applied !== 'boolean') return false;
  return value.omission_reason === null;
}

function isWorkbenchSession(value: unknown): value is RawWorkbenchSession {
  return isRecord(value)
    && value.authenticated === true
    && (isString(value.identity_mode) || isString(value.mode))
    && isString(value.project_id)
    && isString(value.display_name)
    && (value.task_id === undefined || value.task_id === null || typeof value.task_id === 'string')
    && (value.initial_task_id === undefined || value.initial_task_id === null || typeof value.initial_task_id === 'string')
    && (value.expires_at === undefined || value.expires_at === null || typeof value.expires_at === 'string')
    && (value.csrf_token === undefined || value.csrf_token === null || typeof value.csrf_token === 'string');
}

function errorFromResponse(response: Response, payload: unknown): ApiRequestError {
  const body = isRecord(payload) ? payload : null;
  const code = typeof body?.code === 'string' ? body.code : response.status === 401 ? 'UNAUTHENTICATED' : response.status === 404 ? 'NOT_FOUND_OR_FORBIDDEN' : response.status === 409 ? 'INPUT_DIGEST_CONFLICT' : 'INTERNAL_ERROR';
  const message = typeof body?.message === 'string' ? body.message : '平台请求未完成';
  const traceId = typeof body?.request_id === 'string' ? body.request_id : typeof body?.trace_id === 'string' ? body.trace_id : null;
  return new ApiRequestError({ status: response.status, code: code as never, message, traceId });
}

async function readPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function requestJson<T>(
  path: string,
  validator: (value: unknown) => value is T,
  signal: AbortSignal,
  options: RequestInit = {},
): Promise<T> {
  const { headers: extraHeaders, ...requestOptions } = options;
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      credentials: 'include',
      headers: { Accept: 'application/json', ...(extraHeaders ?? {}) },
      signal,
      ...requestOptions,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({ status: 0, code: 'INTERNAL_ERROR', message: '无法连接平台服务' });
  }
  const payload = await readPayload(response);
  if (!response.ok) throw errorFromResponse(response, payload);
  if (!validator(payload)) {
    throw new ApiRequestError({ status: response.status, code: 'INTERNAL_ERROR', message: '平台响应不符合 v2 工作台契约', contractFailure: true });
  }
  return payload;
}

function encoded(value: string): string {
  return encodeURIComponent(value);
}

function csrfHeaders(csrfToken?: string | null): Record<string, string> {
  return csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
}

export function readWorkbenchSession(signal: AbortSignal): Promise<WorkbenchSession | null> {
  return requestJson('/auth/session', (value): value is RawWorkbenchSession | null => value === null || isWorkbenchSession(value), signal)
    .then((value) => value === null ? null : normalizeSession(value))
    .catch((error: unknown) => {
      if (error instanceof ApiRequestError && error.status === 401) return null;
      throw error;
    });
}

export async function beginLocalWorkbenchSession(path: string, accessCode: string, signal: AbortSignal): Promise<WorkbenchSession> {
  const value = await requestJson(path, isWorkbenchSession, signal, { method: 'POST', headers: { ...csrfHeaders(), 'X-Wuji-Local-Access': accessCode } });
  return normalizeSession(value);
}

export async function beginPasswordWorkbenchSession(path: string, username: string, password: string, signal: AbortSignal): Promise<WorkbenchSession> {
  const value = await requestJson(path, isWorkbenchSession, signal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return normalizeSession(value);
}

function normalizeSession(value: RawWorkbenchSession): WorkbenchSession {
  return {
    authenticated: true,
    identity_mode: value.identity_mode ?? value.mode ?? 'unknown',
    project_id: value.project_id,
    display_name: value.display_name,
    ...((value.initial_task_id ?? value.task_id) === undefined ? {} : { task_id: value.initial_task_id ?? value.task_id }),
    ...(value.expires_at === undefined ? {} : { expires_at: value.expires_at }),
    ...(value.csrf_token === undefined ? {} : { csrf_token: value.csrf_token }),
  };
}

export async function endWorkbenchSession(path: string, csrfToken: string | null | undefined, signal: AbortSignal): Promise<void> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), { method: 'POST', credentials: 'include', headers: { Accept: 'application/json', ...csrfHeaders(csrfToken) }, signal });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({ status: 0, code: 'INTERNAL_ERROR', message: '退出请求未完成' });
  }
  if (!response.ok && response.status !== 401) throw errorFromResponse(response, await readPayload(response));
}

export function listTasks(projectId: string, cursor: string | null, signal: AbortSignal): Promise<TaskList> {
  const query = new URLSearchParams({ project_id: projectId, limit: '20' });
  if (cursor) query.set('cursor', cursor);
  return requestJson(`/api/v2/tasks?${query.toString()}`, isTaskList, signal);
}

export function readTaskOptions(projectId: string, signal: AbortSignal): Promise<TaskOptions> {
  return requestJson(`/api/v2/projects/${encoded(projectId)}/task-options`, isTaskOptions, signal);
}

export function readTask(taskId: string, signal: AbortSignal): Promise<TaskView> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}`, isTaskView, signal);
}

export function readTaskOverview(taskId: string, signal: AbortSignal): Promise<TaskOverviewV1> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/overview`, isTaskOverview, signal);
}

function isInventoryPage<T>(value: unknown, schemaVersion: string, itemValid: (item: unknown) => item is T): value is InventoryPage<T> {
  return isRecord(value) && value.schema_version === schemaVersion && Array.isArray(value.items)
    && value.items.every(itemValid) && isNullableString(value.next_after);
}

function isCommandInventoryItem(value: unknown): value is CommandInventoryItem {
  return isRecord(value) && isString(value.work_item_id) && isString(value.exec_id)
    && typeof value.command === 'string' && isString(value.state)
    && (value.exit_code === null || Number.isInteger(value.exit_code))
    && isString(value.output_completeness) && Array.isArray(value.output_refs)
    && value.output_refs.every(isBlobRef) && value.assurance === 'executor_reported';
}

function isPublicationInventoryItem(value: unknown): value is PublicationInventoryItem {
  return isRecord(value) && isString(value.publication_id) && isString(value.asset_id)
    && isString(value.asset_revision) && isString(value.producer_work_item_id)
    && isString(value.producer_run_id) && isBlobRef(value.manifest_ref)
    && isString(value.created_at) && isString(value.download_url);
}

function inventoryPath(taskId: string, kind: 'command-inventory' | 'publications', after: string | null): string {
  const query = new URLSearchParams({ limit: '25' });
  if (after) query.set('after', after);
  return `/api/v2/tasks/${encoded(taskId)}/${kind}?${query}`;
}

export function readCommandInventory(taskId: string, after: string | null, signal: AbortSignal): Promise<InventoryPage<CommandInventoryItem>> {
  return requestJson(inventoryPath(taskId, 'command-inventory', after), (value): value is InventoryPage<CommandInventoryItem> => isInventoryPage(value, 'wuji.command-inventory.v1', isCommandInventoryItem), signal);
}

export function readPublications(taskId: string, after: string | null, signal: AbortSignal): Promise<InventoryPage<PublicationInventoryItem>> {
  return requestJson(inventoryPath(taskId, 'publications', after), (value): value is InventoryPage<PublicationInventoryItem> => isInventoryPage(value, 'wuji.task-publications.v1', isPublicationInventoryItem), signal);
}

function isCaptureSessionPage(value: unknown): value is RuntimeCaptureSessionPageV1 {
  return isRecord(value) && value.schema_version === 'wuji.runtime-capture-sessions.v1'
    && Array.isArray(value.sessions) && value.sessions.every((session) => isRecord(session)
      && isString(session.capture_session_id) && isRecord(session.binding)
      && isString(session.binding.task_id) && isString(session.binding.pod_uid)
      && ['ready', 'draining', 'sealed', 'failed'].includes(String(session.state)));
}

function isCaptureItemPage(value: unknown): value is RuntimeCaptureItemPageV1 {
  return isRecord(value) && value.schema_version === 'wuji.runtime-capture-items.v1'
    && isString(value.capture_session_id) && Array.isArray(value.items)
    && value.items.every((item) => isRecord(item) && isRecord(item.envelope)
      && Number.isInteger(item.envelope.item_seq)
      && ['http_exchange', 'pcap_segment', 'gap', 'manifest'].includes(String(item.envelope.kind))
      && Array.isArray(item.envelope.parts) && item.envelope.parts.every((part) => isRecord(part)
        && isString(part.part) && isString(part.media_type) && Number.isInteger(part.length)))
    && (value.next_item_seq === null || Number.isInteger(value.next_item_seq));
}

export function readCaptureSessions(taskId: string, signal: AbortSignal): Promise<RuntimeCaptureSessionPageV1> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/capture-sessions`, isCaptureSessionPage, signal);
}

export function readCaptureItems(taskId: string, sessionId: string, after: number, signal: AbortSignal): Promise<RuntimeCaptureItemPageV1> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/capture-sessions/${encoded(sessionId)}/items?after=${after}&limit=25`, isCaptureItemPage, signal);
}

export async function downloadCapturePart(taskId: string, sessionId: string, itemSeq: number, part: string, signal: AbortSignal): Promise<Blob> {
  const path = `/api/v2/tasks/${encoded(taskId)}/capture-sessions/${encoded(sessionId)}/items/${itemSeq}/parts/${encoded(part)}`;
  const response = await fetch(apiUrl(path), { credentials: 'include', headers: { Accept: 'application/octet-stream' }, signal });
  if (!response.ok) throw errorFromResponse(response, await readPayload(response));
  return response.blob();
}

export interface TaskActivityQuery {
  readonly cursor?: string | null;
  readonly afterCursor?: string | null;
  readonly importance?: 'key' | 'all';
  readonly category?: TaskActivityItemV1['category'] | null;
  readonly workItemId?: string | null;
  readonly limit?: number;
}

export function readTaskActivity(taskId: string, query: TaskActivityQuery, signal: AbortSignal): Promise<TaskActivityPageV1> {
  const params = new URLSearchParams({
    limit: String(query.limit ?? 20),
    importance: query.importance ?? 'key',
  });
  if (query.cursor) params.set('cursor', query.cursor);
  if (query.afterCursor) params.set('after_cursor', query.afterCursor);
  if (query.category) params.set('category', query.category);
  if (query.workItemId) params.set('work_item_id', query.workItemId);
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/activity?${params.toString()}`, isTaskActivityPage, signal);
}

export function readReadiness(taskId: string, signal: AbortSignal): Promise<ReadinessReport> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/readiness`, isReadinessReport, signal);
}

export function readLaunch(taskId: string, signal: AbortSignal): Promise<LaunchView> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/launch`, isLaunchView, signal);
}

export function readExploration(taskId: string, mode: 'live' | 'history', snapshotId: string | null, signal: AbortSignal): Promise<ExplorationViewV1> {
  const query = new URLSearchParams({ mode, node_limit: '300' });
  if (snapshotId) query.set('snapshot_id', snapshotId);
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/exploration?${query.toString()}`, isExplorationView, signal);
}

export function readTaskInputs(taskId: string, signal: AbortSignal): Promise<TaskInputListV1> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/inputs`, isTaskInputList, signal);
}

export function answerTaskInput(inputRequestId: string, text: string, idempotencyKey: string, csrfToken: string | null | undefined, signal: AbortSignal): Promise<InputAnswerReceiptV1> {
  return requestJson(`/api/v2/inputs/${encoded(inputRequestId)}/answers`, isInputAnswerReceipt, signal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey, ...csrfHeaders(csrfToken) },
    body: JSON.stringify({ schema_version: 'wuji.api.v2', text }),
  });
}

export function createTask(body: TaskCreate, idempotencyKey: string, csrfToken: string | null | undefined, signal: AbortSignal): Promise<TaskView> {
  return requestJson('/api/v2/tasks', isTaskView, signal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey, ...csrfHeaders(csrfToken) },
    body: JSON.stringify(body),
  });
}

export function commandTask(taskId: string, body: TaskCommand, idempotencyKey: string, csrfToken: string | null | undefined, signal: AbortSignal): Promise<CommandReceipt> {
  return requestJson(`/api/v2/tasks/${encoded(taskId)}/commands`, isCommandReceipt, signal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey, ...csrfHeaders(csrfToken) },
    body: JSON.stringify(body),
  });
}

export function materialPath(taskId: string, artifactId: string, version: string): string {
  const query = new URLSearchParams({ version });
  return `/api/v2/tasks/${encoded(taskId)}/artifacts/${encoded(artifactId)}/material?${query.toString()}`;
}

export function artifactContentPath(artifactId: string, version: string): string {
  const query = new URLSearchParams({ version });
  return `/api/v2/artifacts/${encoded(artifactId)}/content?${query.toString()}`;
}

export function readArtifactMaterial(taskId: string, artifactId: string, version: string, signal: AbortSignal): Promise<ModelMaterialV2> {
  return requestJson(materialPath(taskId, artifactId, version), isModelMaterial, signal);
}

export async function downloadArtifact(artifactId: string, version: string, signal: AbortSignal): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(apiUrl(artifactContentPath(artifactId, version)), { credentials: 'include', headers: { Accept: '*/*' }, signal });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({ status: 0, code: 'INTERNAL_ERROR', message: '原始 Artifact 下载未完成' });
  }
  if (!response.ok) throw errorFromResponse(response, await readPayload(response));
  return response.blob();
}
