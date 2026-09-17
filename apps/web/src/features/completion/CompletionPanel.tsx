import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, Descriptions, Empty, Select, Spin, Table, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { apiUrl } from '../../config';
import {
  CLOSE_TRIGGERS,
  DECLARED_PROFILES,
  RESULT_OUTCOMES,
  completionRequestPath,
  deliveriesRequestPath,
  parseReportDeliverySummaries,
  parseReportDeliveryView,
  parseReportView,
  parseTaskCompletionView,
  profileForDelivery,
  reportRequestPath,
  type CompletionAction,
  type ReportDeliverySummary,
  type ReportDeliveryView,
  type ReportView,
  type TaskCompletionView,
} from './contracts';
import styles from './completion.module.css';

const DECISION_COPY: Record<string, { color: string; text: string }> = {
  ready: { color: 'green', text: '可以收尾' },
  wait: { color: 'gold', text: '等待中' },
  blocked: { color: 'red', text: '被阻止' },
};

const STATUS_COPY: Record<string, { color: string; text: string }> = {
  met: { color: 'green', text: '已满足' },
  not_met: { color: 'red', text: '未满足' },
  unknown: { color: 'gold', text: '未知' },
  not_applicable: { color: 'default', text: '不适用' },
  missing: { color: 'default', text: '缺少判定' },
};

const APPLICABILITY_COPY: Record<string, string> = {
  current: '当前',
  stale: '已过期',
  disputed: '有争议',
  retracted: '已撤回',
  missing: '未记录',
};

const DELIVERY_STATE_COPY: Record<string, { color: string; text: string }> = {
  delivery_pending: { color: 'gold', text: '待检查' },
  ready: { color: 'green', text: '材料齐全' },
  incomplete: { color: 'red', text: '缺少必需材料' },
  failed: { color: 'default', text: '交付失败' },
};

const DELIVERY_PROFILE_OPTIONS = DECLARED_PROFILES.map((item) => ({
  value: item.value,
  label: item.label,
}));

const REASON_COPY: Record<string, string> = {
  criteria_invalidated: '判定已失效（过期/争议/撤回）',
  required_work_open: '仍有未完成工作',
  runs_unsettled: '仍有未结算的 Run',
  criteria_unmet: '目标判据尚未满足',
};

async function readCompletion(taskId: string, signal: AbortSignal): Promise<TaskCompletionView> {
  let response: Response;
  try {
    response = await fetch(apiUrl(completionRequestPath(taskId)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('无法连接完成审核服务');
  }
  if (response.status === 404) throw new Error('当前身份没有该 Task 的完成审核权限');
  if (!response.ok) throw new Error('完成审核读取失败');
  return parseTaskCompletionView(await response.json());
}

async function readReport(
  taskId: string,
  reportId: string,
  signal: AbortSignal,
): Promise<ReportView> {
  let response: Response;
  try {
    response = await fetch(apiUrl(reportRequestPath(taskId, reportId)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('无法连接报告服务');
  }
  if (response.status === 404) throw new Error('报告不可访问');
  if (!response.ok) throw new Error('报告读取失败');
  return parseReportView(await response.json());
}

function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `completion-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export interface CompletionPanelProps {
  readonly taskId: string;
  readonly onChanged?: () => void;
}

export function CompletionPanel({ taskId, onChanged }: CompletionPanelProps) {
  const [view, setView] = useState<TaskCompletionView | null>(null);
  const [report, setReport] = useState<ReportView | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [closeTrigger, setCloseTrigger] = useState<string>('goal_satisfied');
  const [resultOutcome, setResultOutcome] = useState<string>('complete');
  const [profileId, setProfileId] = useState<string>(DECLARED_PROFILES[0].value);
  const [deliveries, setDeliveries] = useState<readonly ReportDeliverySummary[]>([]);
  const [delivery, setDelivery] = useState<ReportDeliveryView | null>(null);
  const [deliveryBusy, setDeliveryBusy] = useState(false);
  const active = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await readCompletion(taskId, controller.signal);
      if (controller.signal.aborted) return;
      setView(next);
      setReport(null);
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : '完成审核读取失败');
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void load();
    return () => active.current?.abort();
  }, [load]);


  const submit = async (action: CompletionAction) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(apiUrl(completionRequestPath(taskId)), {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'Idempotency-Key': newIdempotencyKey(),
        },
        body: JSON.stringify({
          action,
          close_trigger: closeTrigger,
          result_outcome: resultOutcome,
          deadline_seconds: 900,
        }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const code = (payload as { code?: string } | null)?.code ?? `HTTP_${response.status}`;
        throw new Error(completionErrorCopy(code));
      }
      const next = parseTaskCompletionView(payload);
      setView(next);
      setReport(null);
      setNotice(next.observed_state === 'closed'
        ? '任务已关闭，报告已冻结。'
        : '收尾 epoch 已开启；在飞工作结算后可完成关闭。');
      onChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '完成动作未完成');
    } finally {
      setBusy(false);
    }
  };

  const openReport = async () => {
    if (!view?.report) return;
    setBusy(true);
    setError(null);
    try {
      const controller = new AbortController();
      setReport(await readReport(taskId, view.report.report_id, controller.signal));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '报告读取失败');
    } finally {
      setBusy(false);
    }
  };

  const refreshDeliveries = useCallback(
    async (reportId: string) => {
      try {
        const response = await fetch(apiUrl(deliveriesRequestPath(taskId, reportId)), {
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) throw new Error('交付记录读取失败');
        setDeliveries(parseReportDeliverySummaries(await response.json()));
      } catch {
        setDeliveries([]);
      }
    },
    [taskId],
  );

  const openDelivery = async (deliveryId: string) => {
    if (!view?.report) return;
    setDeliveryBusy(true);
    setError(null);
    try {
      const response = await fetch(
        apiUrl(`${deliveriesRequestPath(taskId, view.report.report_id)}/${encodeURIComponent(deliveryId)}`),
        { credentials: 'include', headers: { Accept: 'application/json' } },
      );
      if (!response.ok) throw new Error('交付记录读取失败');
      setDelivery(parseReportDeliveryView(await response.json()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '交付记录读取失败');
    } finally {
      setDeliveryBusy(false);
    }
  };

  const deliverReport = async () => {
    if (!view?.report) return;
    setDeliveryBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(apiUrl(deliveriesRequestPath(taskId, view.report.report_id)), {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'Idempotency-Key': newIdempotencyKey(),
        },
        body: JSON.stringify({ profile: profileForDelivery(profileId), exchange: null }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const code = (payload as { code?: string } | null)?.code ?? `HTTP_${response.status}`;
        throw new Error(completionErrorCopy(code));
      }
      const next = parseReportDeliveryView(payload);
      setDelivery(next);
      setNotice(next.state === 'ready'
        ? '交付记录已生成：profile 要求的材料齐全。'
        : '交付记录已生成：缺少必需材料，记录为 incomplete。');
      await refreshDeliveries(view.report.report_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '交付记录未生成');
    } finally {
      setDeliveryBusy(false);
    }
  };

  const reportId = view?.report?.report_id ?? null;
  useEffect(() => {
    if (reportId === null) {
      setDeliveries([]);
      setDelivery(null);
      return;
    }
    void refreshDeliveries(reportId);
  }, [reportId, refreshDeliveries]);

  if (loading && !view) {
    return (
      <section className={styles.completionPanel} aria-label="任务完成">
        <header><strong>任务完成</strong><span>读取中</span></header>
        <div className={styles.completionStatus}><Spin description="正在读取完成审核" /></div>
      </section>
    );
  }

  const review = view?.review;
  const decision = review ? DECISION_COPY[review.decision] : undefined;
  const closed = view?.observed_state === 'closed';
  const canQuiesce = Boolean(review && review.decision === 'ready' && !view?.completion_epoch_id && !closed);
  const canClose = Boolean(view?.completion_epoch_id && !closed && review?.unsettled_runs.length === 0);

  return (
    <section className={styles.completionPanel} aria-label="任务完成">
      <header>
        <div>
          <strong>任务完成</strong>
          <span>{closed ? '已关闭 · 报告已冻结' : '平台审核 · 收尾与报告'}</span>
        </div>
        <div className={styles.completionHeaderActions}>
          {decision && <Tag color={decision.color}>{decision.text}</Tag>}
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={() => void load()}
          >刷新</Button>
        </div>
      </header>

      {error && <Alert showIcon type="error" title="完成操作未完成" description={error} />}
      {notice && <Alert showIcon type="success" title="完成动作已受理" description={notice} />}

      {view && (
        <>
          <Descriptions
            className={styles.completionSummary}
            size="small"
            bordered
            column={{ xs: 1, sm: 2, md: 3 }}
            items={[
              { key: 'observed', label: '任务状态', children: <code>{view.observed_state}</code> },
              { key: 'control', label: '控制版本', children: <code>{view.control_version}</code> },
              {
                key: 'epoch',
                label: '收尾 epoch',
                children: <code>{view.completion_epoch_id ?? '未开启'}</code>,
              },
              { key: 'trigger', label: '关闭原因', children: <code>{view.close_trigger ?? '未定'}</code> },
              { key: 'outcome', label: '结果', children: <code>{view.result_outcome ?? '未定'}</code> },
            ]}
          />

          {review && review.reasons.length > 0 && (
            <div className={styles.completionReasons}>
              {review.reasons.map((reason) => (
                <Tag key={reason} color="gold">{REASON_COPY[reason] ?? reason}</Tag>
              ))}
            </div>
          )}

          {(review?.open_work.length || review?.unsettled_runs.length) ? (
            <div className={styles.completionReasons}>
              {review?.open_work.map((item) => <Tag key={`work-${item}`}>未完成工作 {item}</Tag>)}
              {review?.unsettled_runs.map((item) => <Tag key={`run-${item}`} color="blue">未结算 Run {item}</Tag>)}
            </div>
          ) : null}

          {review && review.criteria.length > 0 && (
            <Table
              className={styles.completionCriteria}
              size="small"
              pagination={false}
              rowKey={(item) => `${item.criterion_id}@${item.revision ?? 'missing'}`}
              dataSource={[...review.criteria]}
              columns={[
                { title: '判据', dataIndex: 'criterion_id', ellipsis: true },
                { title: '修订', dataIndex: 'revision', width: 88, render: (value: string | null) => <code>{value ?? '—'}</code> },
                { title: '必需', dataIndex: 'required', width: 72, render: (value: boolean) => (value ? '是' : '否') },
                {
                  title: '判定',
                  dataIndex: 'status',
                  width: 108,
                  render: (value: string) => {
                    const copy = STATUS_COPY[value] ?? { color: 'default', text: value };
                    return <Tag color={copy.color}>{copy.text}</Tag>;
                  },
                },
                {
                  title: '适用性',
                  dataIndex: 'applicability',
                  width: 96,
                  render: (value: string) => APPLICABILITY_COPY[value] ?? value,
                },
              ]}
            />
          )}

          {!closed && (
            <div className={styles.completionActions}>
              <Select
                aria-label="关闭原因"
                value={closeTrigger}
                onChange={setCloseTrigger}
                options={CLOSE_TRIGGERS.map((item) => ({ value: item.value, label: item.label }))}
                disabled={Boolean(view.completion_epoch_id)}
              />
              <Select
                aria-label="结果"
                value={resultOutcome}
                onChange={setResultOutcome}
                options={RESULT_OUTCOMES.map((item) => ({ value: item.value, label: item.label }))}
                disabled={Boolean(view.completion_epoch_id)}
              />
              <Button
                type="primary"
                loading={busy}
                disabled={!canQuiesce}
                onClick={() => void submit('quiesce')}
              >开始收尾</Button>
              <Button
                danger
                loading={busy}
                disabled={!canClose}
                onClick={() => void submit('close')}
              >完成关闭并冻结报告</Button>
            </div>
          )}

          {view.report && (
            <div className={styles.completionReport}>
              <div className={styles.completionReportHeader}>
                <strong>冻结报告</strong>
                <Tag color={view.report.dispute_state === 'disputed' ? 'red' : 'green'}>
                  {view.report.dispute_state === 'disputed' ? '有争议' : '无争议'}
                </Tag>
              </div>
              <Descriptions
                size="small"
                bordered
                column={1}
                items={[
                  { key: 'id', label: '报告', children: <code>{view.report.report_id}</code> },
                  { key: 'digest', label: '正文摘要', children: <code>{view.report.body_digest}</code> },
                  { key: 'trigger', label: '关闭原因', children: <code>{view.report.close_trigger}</code> },
                  { key: 'outcome', label: '结果', children: <code>{view.report.result_outcome}</code> },
                  {
                    key: 'created',
                    label: '冻结时间',
                    children: new Date(view.report.created_at).toLocaleString('zh-CN'),
                  },
                ]}
              />
              <Button size="small" loading={busy} onClick={() => void openReport()}>查看冻结正文</Button>
              {report && (
                <>
                  <pre className={styles.completionReportBody}>{JSON.stringify(report.body, null, 2)}</pre>
                  {report.amendments.length > 0 && (
                    <div className={styles.completionAmendments}>
                      {report.amendments.map((item) => (
                        <Alert
                          key={item.amendment_id}
                          showIcon
                          type="warning"
                          title={`迟到反证 · ${item.authority}`}
                          description={item.reason}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
              <div className={styles.completionDelivery}>
                <div className={styles.completionReportHeader}>
                  <strong>报告交付</strong>
                  {delivery && (
                    <Tag color={(DELIVERY_STATE_COPY[delivery.state] ?? { color: 'default' }).color}>
                      {(DELIVERY_STATE_COPY[delivery.state] ?? { text: delivery.state }).text}
                    </Tag>
                  )}
                </div>
                <div className={styles.completionActions}>
                  <Select
                    aria-label="交付 profile"
                    value={profileId}
                    onChange={setProfileId}
                    options={DELIVERY_PROFILE_OPTIONS}
                  />
                  <Button
                    type="primary"
                    loading={deliveryBusy}
                    onClick={() => void deliverReport()}
                  >生成交付记录</Button>
                </div>
                {deliveries.length > 0 && (
                  <Table
                    size="small"
                    pagination={false}
                    rowKey={(item) => item.delivery_id}
                    dataSource={[...deliveries]}
                    onRow={(item) => ({ onClick: () => void openDelivery(item.delivery_id) })}
                    columns={[
                      { title: '交付', dataIndex: 'delivery_id', ellipsis: true },
                      { title: 'Profile', dataIndex: 'profile_id', ellipsis: true },
                      { title: '媒介', dataIndex: 'mode', width: 84 },
                      {
                        title: '状态',
                        dataIndex: 'state',
                        width: 132,
                        render: (value: string) => {
                          const copy = DELIVERY_STATE_COPY[value] ?? { color: 'default', text: value };
                          return <Tag color={copy.color}>{copy.text}</Tag>;
                        },
                      },
                      {
                        title: '缺必需材料',
                        dataIndex: 'missing_required',
                        width: 108,
                      },
                    ]}
                  />
                )}
                {delivery && (
                  <>
                    <Descriptions
                      size="small"
                      bordered
                      column={1}
                      items={[
                        { key: 'id', label: '交付', children: <code>{delivery.delivery_id}</code> },
                        { key: 'state', label: '状态', children: <code>{delivery.state}</code> },
                        {
                          key: 'profile',
                          label: 'Profile 摘要',
                          children: <code>{delivery.profile_digest}</code>,
                        },
                        {
                          key: 'manifest',
                          label: '清单摘要',
                          children: <code>{delivery.manifest_digest ?? '未生成'}</code>,
                        },
                        {
                          key: 'exchange',
                          label: 'HTTP 交换',
                          children: <code>{delivery.exchange === null ? '离线交付，无交换' : '有交换回执'}</code>,
                        },
                      ]}
                    />
                    {delivery.missing.filter((item) => item.required).map((item) => (
                      <Alert
                        key={item.role}
                        showIcon
                        type="warning"
                        title={`缺少必需材料 · ${item.role}`}
                        description={`需要 ${item.min_count} 份 ${item.media_type}，当前 ${item.present_count} 份。`}
                      />
                    ))}
                  </>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {!view && !loading && !error && (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无完成审核数据" />
      )}
    </section>
  );
}

function completionErrorCopy(code: string): string {
  switch (code) {
    case 'COMPLETION_PRECHECK_INCOMPLETE':
      return '平台审核未通过：目标判据或未完成工作仍不满足关闭条件。';
    case 'COMPLETION_EPOCH_UNSETTLED':
    case 'OPERATION_UNKNOWN':
      return '仍有在飞 Run 未结算，稍后重试即可完成关闭。';
    case 'COMPLETION_EPOCH_ABSENT':
      return '需要先开始收尾，才能完成关闭。';
    case 'COMPLETION_NOT_CLOSED':
      return '任务尚未关闭，报告不能冻结。';
    case 'INPUT_DIGEST_CONFLICT':
      return '幂等键与内容不一致；请用新的操作重试。';
    case 'DELIVERY_EXCHANGE_REQUIRED':
      return 'HTTP 交付必须引用真实交换回执；离线 profile 不记录交换。';
    case 'DELIVERY_TOO_LARGE':
    case 'LIMIT_BLOCKED':
      return '交付材料超过平台上限，请缩小 profile 要求。';
    case 'NOT_FOUND_OR_FORBIDDEN':
      return '当前身份没有该 Task 的控制权限。';
    default:
      return `完成请求被拒绝（${code}）。`;
  }
}
