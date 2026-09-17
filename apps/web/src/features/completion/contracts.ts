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
  return { ...(value as unknown as ReportView), amendments };
}
