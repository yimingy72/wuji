export type CompletionDecision = 'wait' | 'ready' | 'blocked';
export type CriterionStatus = 'met' | 'not_met' | 'unknown' | 'not_applicable' | 'missing';
export type CriterionApplicability = 'current' | 'stale' | 'disputed' | 'retracted' | 'missing';
export type DisputeState = 'clear' | 'disputed';
export type CompletionAction = 'quiesce' | 'close';

export interface CriterionJudgmentView {
  readonly criterion_id: string;
  readonly revision: string | null;
  readonly required: boolean;
  readonly status: CriterionStatus;
  readonly applicability: CriterionApplicability;
}

export interface CompletionReview {
  readonly decision: CompletionDecision;
  readonly reasons: readonly string[];
  readonly criteria: readonly CriterionJudgmentView[];
  readonly open_work: readonly string[];
  readonly unsettled_runs: readonly string[];
}

export interface ReportSummary {
  readonly report_id: string;
  readonly body_digest: string;
  readonly dispute_state: DisputeState;
  readonly close_trigger: string;
  readonly result_outcome: string;
  readonly epoch_id: string;
  readonly created_at: string;
}

export interface TaskCompletionView {
  readonly task_id: string;
  readonly observed_state: string;
  readonly desired_state: string;
  readonly control_version: string;
  readonly completion_epoch_id: string | null;
  readonly close_trigger: string | null;
  readonly result_outcome: string | null;
  readonly review: CompletionReview;
  readonly report: ReportSummary | null;
}

export interface UnavailableMaterial {
  readonly source_ref: string;
  readonly sha256: string | null;
  readonly state: string;
  readonly reason: string;
  readonly purge_id: string | null;
}

export interface ReportAmendmentView {
  readonly amendment_id: string;
  readonly reason: string;
  readonly authority: string;
  readonly source_receipt: Record<string, unknown>;
}

export interface ReportView {
  readonly report_id: string;
  readonly task_id: string;
  readonly epoch_id: string;
  readonly close_trigger: string;
  readonly result_outcome: string;
  readonly body: Record<string, unknown>;
  readonly body_digest: string;
  readonly dispute_state: DisputeState;
  readonly amendments: readonly ReportAmendmentView[];
  readonly unavailable_evidence: readonly UnavailableMaterial[];
}

export type DeliveryState = 'delivery_pending' | 'ready' | 'incomplete' | 'failed';
export type DeliveryMode = 'offline' | 'http';

export interface DeliveryRequirement {
  readonly role: string;
  readonly media_type: string;
  readonly min_count: number;
  readonly required: boolean;
}

export interface DeliveryProfile {
  readonly schema_version: 'wuji.delivery-profile.v1';
  readonly profile_id: string;
  readonly mode: DeliveryMode;
  readonly requirements: readonly DeliveryRequirement[];
}

export interface DeliveryMaterial {
  readonly source: 'report_commit' | 'artifact';
  readonly source_ref: string;
  readonly media_type: string;
  readonly sha256: string;
  readonly size_bytes: number;
  readonly access_level: number;
}

export interface DeliveryMissing {
  readonly role: string;
  readonly media_type: string;
  readonly min_count: number;
  readonly present_count: number;
  readonly missing_count: number;
  readonly required: boolean;
}

export interface ReportDeliverySummary {
  readonly delivery_id: string;
  readonly report_id: string;
  readonly profile_id: string;
  readonly mode: DeliveryMode;
  readonly state: DeliveryState;
  readonly missing_required: number;
  readonly error_code: string | null;
  readonly created_at: string;
}

export interface ReportDeliveryManifest {
  readonly schema_version: 'wuji.report-delivery.v1';
  readonly report_id: string;
  readonly report_digest: string;
  readonly epoch_id: string;
  readonly profile: DeliveryProfile;
  readonly mode: DeliveryMode;
  readonly state: 'ready' | 'incomplete';
  readonly requirements: readonly (DeliveryRequirement & {
    readonly present_count: number;
    readonly present: readonly DeliveryMaterial[];
    readonly missing_count: number;
  })[];
  readonly materials: readonly DeliveryMaterial[];
  readonly missing: readonly DeliveryMissing[];
}

export interface ReportDeliveryView {
  readonly delivery_id: string;
  readonly task_id: string;
  readonly report_id: string;
  readonly report_digest: string;
  readonly epoch_id: string;
  readonly profile: DeliveryProfile;
  readonly profile_digest: string;
  readonly state: DeliveryState;
  readonly mode: DeliveryMode;
  readonly missing: readonly DeliveryMissing[];
  readonly manifest: ReportDeliveryManifest | null;
  readonly manifest_digest: string | null;
  readonly exchange: Record<string, unknown> | null;
  readonly error_code: string | null;
  readonly access_level: number;
  readonly created_at: string;
  readonly unavailable_materials: readonly UnavailableMaterial[];
}

export interface CompletionCommandBody {
  readonly action: CompletionAction;
  readonly close_trigger: string;
  readonly result_outcome: string;
  readonly deadline_seconds?: number;
}

export const CLOSE_TRIGGERS = [
  { value: 'goal_satisfied', label: '目标已满足' },
  { value: 'operator_finish', label: '操作者结束' },
  { value: 'budget_exhausted', label: '预算耗尽' },
  { value: 'time_limit', label: '时间上限' },
  { value: 'no_progress', label: '无进展' },
  { value: 'system_failure', label: '系统故障' },
] as const;

export const DECLARED_PROFILES = [
  {
    value: 'offline-document-v1',
    label: '离线文档（仅冻结正文）',
    mode: 'offline' as DeliveryMode,
    requirements: [
      {
        role: 'report_body',
        media_type: 'application/vnd.wuji.report+json',
        min_count: 1,
        required: true,
      },
    ],
  },
  {
    value: 'screenshot-bundle-v1',
    label: '含截图证据（要求 image/* 材料）',
    mode: 'offline' as DeliveryMode,
    requirements: [
      {
        role: 'report_body',
        media_type: 'application/vnd.wuji.report+json',
        min_count: 1,
        required: true,
      },
      { role: 'screenshot', media_type: 'image/*', min_count: 1, required: true },
    ],
  },
] as const;

function declaredProfile(profileId: string): DeliveryProfile {
  const found = DECLARED_PROFILES.find((item) => item.value === profileId);
  if (!found) throw new Error('未知交付 profile');
  return {
    schema_version: 'wuji.delivery-profile.v1',
    profile_id: found.value,
    mode: found.mode,
    requirements: found.requirements.map((item) => ({ ...item })),
  };
}

export function profileForDelivery(profileId: string): DeliveryProfile {
  return declaredProfile(profileId);
}

export const RESULT_OUTCOMES = [
  { value: 'complete', label: '完整' },
  { value: 'partial', label: '部分' },
  { value: 'inconclusive', label: '不结论' },
  { value: 'not_assessed', label: '未评估' },
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isText(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isStringList(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

const DECISIONS: readonly string[] = ['wait', 'ready', 'blocked'];
const STATUSES: readonly string[] = ['met', 'not_met', 'unknown', 'not_applicable', 'missing'];
const APPLICABILITIES: readonly string[] = ['current', 'stale', 'disputed', 'retracted', 'missing'];
const DISPUTES: readonly string[] = ['clear', 'disputed'];

function parseCriterion(value: unknown): CriterionJudgmentView {
  if (
    !isRecord(value)
    || !isText(value.criterion_id)
    || !(value.revision === null || isText(value.revision))
    || typeof value.required !== 'boolean'
    || !STATUSES.includes(value.status as string)
    || !APPLICABILITIES.includes(value.applicability as string)
  ) {
    throw new Error('完成审核响应不符合固定契约');
  }
  return value as unknown as CriterionJudgmentView;
}

function parseReview(value: unknown): CompletionReview {
  if (
    !isRecord(value)
    || !DECISIONS.includes(value.decision as string)
    || !isStringList(value.reasons)
    || !Array.isArray(value.criteria)
    || !isStringList(value.open_work)
    || !isStringList(value.unsettled_runs)
  ) {
    throw new Error('完成审核响应不符合固定契约');
  }
  return { ...(value as unknown as CompletionReview), criteria: value.criteria.map(parseCriterion) };
}

function parseReportSummary(value: unknown): ReportSummary {
  if (
    !isRecord(value)
    || !isText(value.report_id)
    || !isText(value.body_digest)
    || !DISPUTES.includes(value.dispute_state as string)
    || !isText(value.close_trigger)
    || !isText(value.result_outcome)
    || !isText(value.epoch_id)
    || !isText(value.created_at)
  ) {
    throw new Error('完成审核响应不符合固定契约');
  }
  return value as unknown as ReportSummary;
}

export function completionRequestPath(taskId: string): string {
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/completion`;
}

export function reportRequestPath(taskId: string, reportId: string): string {
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/reports/${encodeURIComponent(reportId)}`;
}

export function parseTaskCompletionView(value: unknown): TaskCompletionView {
  if (
    !isRecord(value)
    || !isText(value.task_id)
    || !isText(value.observed_state)
    || !isText(value.desired_state)
    || !isText(value.control_version)
    || !/^(0|[1-9][0-9]*)$/.test(value.control_version)
    || !(value.completion_epoch_id === null || isText(value.completion_epoch_id))
    || !(value.close_trigger === null || isText(value.close_trigger))
    || !(value.result_outcome === null || isText(value.result_outcome))
  ) {
    throw new Error('完成审核响应不符合固定契约');
  }
  const review = parseReview(value.review);
  const report = value.report === null ? null : parseReportSummary(value.report);
  return { ...(value as unknown as TaskCompletionView), review, report };
}

const DELIVERY_STATES: readonly string[] = [
  'delivery_pending',
  'ready',
  'incomplete',
  'failed',
];
const DELIVERY_MODES: readonly string[] = ['offline', 'http'];

function parseDeliveryRequirement(value: unknown): DeliveryRequirement {
  if (
    !isRecord(value)
    || !isText(value.role)
    || !isText(value.media_type)
    || typeof value.min_count !== 'number'
    || typeof value.required !== 'boolean'
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return value as unknown as DeliveryRequirement;
}

function parseDeliveryProfile(value: unknown): DeliveryProfile {
  if (
    !isRecord(value)
    || value.schema_version !== 'wuji.delivery-profile.v1'
    || !isText(value.profile_id)
    || !DELIVERY_MODES.includes(value.mode as string)
    || !Array.isArray(value.requirements)
    || value.requirements.length === 0
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return {
    ...(value as unknown as DeliveryProfile),
    requirements: value.requirements.map(parseDeliveryRequirement),
  };
}

function parseDeliveryMissing(value: unknown): DeliveryMissing {
  if (
    !isRecord(value)
    || !isText(value.role)
    || !isText(value.media_type)
    || typeof value.min_count !== 'number'
    || typeof value.present_count !== 'number'
    || typeof value.missing_count !== 'number'
    || typeof value.required !== 'boolean'
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return value as unknown as DeliveryMissing;
}

function parseDeliveryMaterial(value: unknown): DeliveryMaterial {
  if (
    !isRecord(value)
    || !(value.source === 'report_commit' || value.source === 'artifact')
    || !isText(value.source_ref)
    || !isText(value.media_type)
    || !isText(value.sha256)
    || typeof value.size_bytes !== 'number'
    || typeof value.access_level !== 'number'
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return value as unknown as DeliveryMaterial;
}

function parseDeliveryManifest(value: unknown): ReportDeliveryManifest {
  if (
    !isRecord(value)
    || value.schema_version !== 'wuji.report-delivery.v1'
    || !isText(value.report_id)
    || !isText(value.report_digest)
    || !isText(value.epoch_id)
    || !(value.state === 'ready' || value.state === 'incomplete')
    || !Array.isArray(value.materials)
    || !Array.isArray(value.missing)
    || !Array.isArray(value.requirements)
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return {
    ...(value as unknown as ReportDeliveryManifest),
    profile: parseDeliveryProfile(value.profile),
    materials: value.materials.map(parseDeliveryMaterial),
    missing: value.missing.map(parseDeliveryMissing),
  };
}

export function parseReportDeliveryView(value: unknown): ReportDeliveryView {
  if (
    !isRecord(value)
    || !isText(value.delivery_id)
    || !isText(value.task_id)
    || !isText(value.report_id)
    || !isText(value.report_digest)
    || !isText(value.epoch_id)
    || !isText(value.profile_digest)
    || !DELIVERY_STATES.includes(value.state as string)
    || !DELIVERY_MODES.includes(value.mode as string)
    || !Array.isArray(value.missing)
    || !(value.manifest === null || isRecord(value.manifest))
    || !(value.manifest_digest === null || isText(value.manifest_digest))
    || !(value.exchange === null || isRecord(value.exchange))
    || !(value.error_code === null || isText(value.error_code))
    || typeof value.access_level !== 'number'
    || !isText(value.created_at)
    || !Array.isArray(value.unavailable_materials)
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return {
    ...(value as unknown as ReportDeliveryView),
    profile: parseDeliveryProfile(value.profile),
    missing: value.missing.map(parseDeliveryMissing),
    manifest: value.manifest === null ? null : parseDeliveryManifest(value.manifest),
    unavailable_materials: value.unavailable_materials.map(parseUnavailableMaterial),
  };
}

export function parseReportDeliverySummaries(value: unknown): readonly ReportDeliverySummary[] {
  if (!Array.isArray(value)) throw new Error('交付响应不符合固定契约');
  return value.map((item) => {
    if (
      !isRecord(item)
      || !isText(item.delivery_id)
      || !isText(item.report_id)
      || !isText(item.profile_id)
      || !DELIVERY_MODES.includes(item.mode as string)
      || !DELIVERY_STATES.includes(item.state as string)
      || typeof item.missing_required !== 'number'
      || !(item.error_code === null || isText(item.error_code))
      || !isText(item.created_at)
    ) {
      throw new Error('交付响应不符合固定契约');
    }
    return item as unknown as ReportDeliverySummary;
  });
}

export function deliveriesRequestPath(taskId: string, reportId: string): string {
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/reports/${encodeURIComponent(
    reportId,
  )}/deliveries`;
}

function parseUnavailableMaterial(value: unknown): UnavailableMaterial {
  if (
    !isRecord(value)
    || !isText(value.source_ref)
    || !(value.sha256 === null || isText(value.sha256))
    || !isText(value.state)
    || !isText(value.reason)
    || !(value.purge_id === null || isText(value.purge_id))
  ) {
    throw new Error('交付响应不符合固定契约');
  }
  return value as unknown as UnavailableMaterial;
}

export function parseReportView(value: unknown): ReportView {
  if (
    !isRecord(value)
    || !isText(value.report_id)
    || !isText(value.task_id)
    || !isText(value.epoch_id)
    || !isText(value.close_trigger)
    || !isText(value.result_outcome)
    || !isRecord(value.body)
    || !isText(value.body_digest)
    || !DISPUTES.includes(value.dispute_state as string)
    || !Array.isArray(value.amendments)
    || !Array.isArray(value.unavailable_evidence)
  ) {
    throw new Error('报告响应不符合固定契约');
  }
  const amendments = value.amendments.map((item) => {
    if (
      !isRecord(item)
      || !isText(item.amendment_id)
      || !isText(item.reason)
      || !isText(item.authority)
      || !isRecord(item.source_receipt)
    ) {
      throw new Error('报告响应不符合固定契约');
    }
    return item as unknown as ReportAmendmentView;
  });
  return {
    ...(value as unknown as ReportView),
    amendments,
    unavailable_evidence: value.unavailable_evidence.map(parseUnavailableMaterial),
  };
}
