import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Empty, Segmented, Select, Spin, Tag } from 'antd';
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { ApiRequestError } from '../../api';
import {
  downloadArtifact,
  readArtifactMaterial,
  readTaskActivity,
  type ModelMaterialV2,
  type TaskActivityItemV1,
  type TaskActivityPageV1,
  type TaskOverviewV1,
} from '../../v2WorkbenchApi';
import styles from './firstUseWorkbench.module.css';
import { CaptureInventory, CommandInventory, PublicationInventory } from './TaskRuntimeInventory';

const WORK_STATE: Record<string, string> = {
  ready: '排队中', leased: '准备中', running: '运行中', waiting_input: '等待输入',
  blocked: '已阻断', stopping: '正在停止', suspended: '已暂停', reconciling: '正在核对',
  done: '已完成', failed: '失败', cancelled: '已取消',
};

const ACTIVITY_STATUS: Record<string, { readonly label: string; readonly color: string }> = {
  pending: { label: '待处理', color: 'gold' }, running: { label: '进行中', color: 'blue' },
  succeeded: { label: '已完成', color: 'green' }, failed: { label: '失败', color: 'red' },
  blocked: { label: '受阻', color: 'orange' }, stopped: { label: '已停止', color: 'default' },
  info: { label: '记录', color: 'default' },
};

function criterionState(criterion: TaskOverviewV1['goal']['criteria'][number]) {
  if (criterion.judgment_applicability !== 'current') {
    return { label: criterion.judgment_applicability === 'missing' ? '尚未判断' : '判断已失效', color: 'default' };
  }
  return {
    met: { label: '已满足', color: 'green' },
    not_met: { label: '未满足', color: 'red' },
    unknown: { label: '待确认', color: 'gold' },
    not_applicable: { label: '不适用', color: 'default' },
    missing: { label: '尚未判断', color: 'default' },
  }[criterion.judgment_status];
}

function findingState(finding: TaskOverviewV1['latest_findings'][number]) {
  if (finding.evidence_state === 'supported' && finding.applicability_state === 'current') return { label: '已确认', color: 'green' };
  if (finding.evidence_state === 'contradicted') return { label: '有反证', color: 'red' };
  return { label: '待验证', color: 'gold' };
}

export function TaskOverviewPanel({ overview, taskId, onSelectRef, onSessionExpired }: {
  readonly overview: TaskOverviewV1;
  readonly taskId: string;
  readonly onSelectRef?: (ref: TaskActivityItemV1['evidence_refs'][number]) => void;
  readonly onSessionExpired: () => void;
}) {
  return <div className={styles.overviewGrid}>
    <section className={styles.sectionCard}>
      <header><div><span>目标</span><h2>{overview.goal.text}</h2></div><Tag>{overview.budget.amount} {overview.budget.currency}</Tag></header>
      <ul className={styles.criteriaList}>{overview.goal.criteria.map((criterion) => {
        const state = criterionState(criterion);
        return <li key={criterion.criterion_id}><Tag color={state.color}>{state.label}</Tag><div><strong>{criterion.condition}</strong><span>{criterion.object}{criterion.required ? ' · 必须满足' : ' · 可选'}</span></div></li>;
      })}</ul>
    </section>
    <section className={styles.sectionCard}>
      <header><div><span>当前工作</span><h2>{overview.current_work.length ? `最近 ${overview.current_work.length} 项` : '暂无进行中的工作'}</h2></div></header>
      {overview.current_work.length ? <ul className={styles.workList}>{overview.current_work.map((work) => <li key={work.work_item_id}><div><Tag>{work.kind}</Tag><Tag>{WORK_STATE[work.state] ?? work.state}</Tag></div><strong>{work.question ?? '任务内部工作'}</strong><span>{work.result_summary ?? work.blocked_reason ?? work.terminal_reason ?? '等待新的执行结果'}</span></li>)}</ul> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="启动后，当前工作会显示在这里" />}
    </section>
    <section className={styles.sectionCard}>
      <header><div><span>最新发现</span><h2>{overview.latest_findings.length ? `${overview.latest_findings.length} 条最近更新` : '暂无发现'}</h2></div></header>
      {overview.latest_findings.length ? <ul className={styles.findingList}>{overview.latest_findings.map((finding) => { const state = findingState(finding); return <li key={`${finding.claim_ref.id}:${finding.claim_ref.revision}`}><Tag color={state.color}>{state.label}</Tag><div><strong>{finding.text}</strong><span>{new Date(finding.updated_at).toLocaleString('zh-CN')}</span>{onSelectRef && <Button type="link" size="small" onClick={() => onSelectRef(finding.claim_ref)}>查看发现与依据</Button>}</div></li>; })}</ul> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前还没有发现" />}
    </section>
    <section className={styles.sectionCard}>
      <header><div><span>关键活动</span><h2>最近进展</h2></div></header>
      <TaskActivityPanel taskId={taskId} compact onSelectRef={onSelectRef} onSessionExpired={onSessionExpired} />
    </section>
    <section className={styles.sectionCard}>
      <header><div><span>执行环境</span><h2>{overview.runtime.state === 'stopped' ? '执行已停止' : overview.runtime.state === 'stopping' ? '正在停止执行' : overview.runtime.state === 'running' ? '执行中' : overview.runtime.state === 'unknown' ? '正在核对执行状态' : '尚未启动'}</h2></div></header>
      <span>运行批次 {overview.runtime.runtime_attempt} · 已确认容器 {Object.values(overview.runtime.containers).filter((state) => state === 'terminated' || state === 'not_started').length}/4</span>
      {overview.runtime.state === 'stopped' && <Tag color="green">外部容器终态已核对</Tag>}
    </section>
  </div>;
}

function mergeActivity(current: readonly TaskActivityItemV1[], incoming: readonly TaskActivityItemV1[]) {
  const values = new Map(current.map((item) => [item.activity_id, item]));
  for (const item of incoming) values.set(item.activity_id, item);
  return [...values.values()].sort((left, right) => right.occurred_at.localeCompare(left.occurred_at));
}

export function TaskActivityPanel({ taskId, compact = false, onSelectRef, onSessionExpired }: {
  readonly taskId: string;
  readonly compact?: boolean;
  readonly onSelectRef?: (ref: TaskActivityItemV1['evidence_refs'][number]) => void;
  readonly onSessionExpired: () => void;
}) {
  const [items, setItems] = useState<readonly TaskActivityItemV1[]>([]);
  const [pending, setPending] = useState<readonly TaskActivityItemV1[]>([]);
  const [page, setPage] = useState<TaskActivityPageV1 | null>(null);
  const [importance, setImportance] = useState<'key' | 'all'>('key');
  const [category, setCategory] = useState<TaskActivityItemV1['category'] | null>(null);
  const [workItemId, setWorkItemId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  const latest = useRef<string | null>(null);

  const load = useCallback(async (cursor: string | null, append: boolean) => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await readTaskActivity(taskId, { cursor, importance: compact ? 'key' : importance, category: compact ? null : category, workItemId: compact ? null : workItemId, limit: compact ? 5 : 20 }, controller.signal);
      if (controller.signal.aborted) return;
      setPage(next);
      if (!append) latest.current = next.latest_cursor;
      setItems((current) => append ? mergeActivity(current, next.items) : next.items);
      if (!append) setPending([]);
    } catch (reason) {
      if (controller.signal.aborted) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(reason instanceof Error ? reason.message : '活动读取失败');
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      if (active.current === controller) active.current = null;
    }
  }, [taskId, importance, category, workItemId, compact, onSessionExpired]);

  useEffect(() => {
    void load(null, false);
    return () => active.current?.abort();
  }, [load]);

  useEffect(() => {
    if (compact) return;
    let controller: AbortController | null = null;
    const timer = window.setInterval(() => {
      if (!latest.current || active.current || controller) return;
      controller = new AbortController();
      const current = controller;
      void readTaskActivity(taskId, { afterCursor: latest.current, importance, category, workItemId, limit: 100 }, current.signal).then((next) => {
        if (current.signal.aborted) return;
        latest.current = next.latest_cursor;
        if (next.items.length) setPending((current) => mergeActivity(current, next.items));
      }).catch((reason: unknown) => {
        if (current.signal.aborted) return;
        if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      }).finally(() => {
        if (controller === current) controller = null;
      });
    }, 5000);
    return () => {
      window.clearInterval(timer);
      controller?.abort();
    };
  }, [taskId, importance, category, workItemId, compact, onSessionExpired]);

  const workOptions = useMemo(() => [...new Set(items.map((item) => item.work_item_id).filter((value): value is string => Boolean(value)))].map((value, index) => ({ value, label: `工作 ${index + 1}` })), [items]);
  const visible = compact ? items.slice(0, 5) : items;
  return <div className={styles.activityPanel}>
    {!compact && <div className={styles.activityFilters}>
      <Segmented value={importance} options={[{ value: 'key', label: '关键活动' }, { value: 'all', label: '全部活动' }]} onChange={(value) => setImportance(value as 'key' | 'all')} />
      <Select allowClear aria-label="按活动类型筛选" placeholder="全部类型" value={category ?? undefined} onChange={(value) => setCategory(value ?? null)} options={[
        { value: 'task', label: '任务' }, { value: 'work', label: '工作' }, { value: 'finding', label: '发现' },
        { value: 'evidence', label: '证据' }, { value: 'input', label: '输入' }, { value: 'completion', label: '完成' }, { value: 'tool', label: '工具' },
      ]} />
      <Select allowClear aria-label="按工作筛选" placeholder="全部工作" value={workItemId ?? undefined} onChange={(value) => setWorkItemId(value ?? null)} options={workOptions} />
      <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load(null, false)}>刷新</Button>
    </div>}
    {pending.length > 0 && <Button type="primary" ghost onClick={() => { setItems((current) => mergeActivity(pending, current)); setPending([]); }}>显示 {pending.length} 条新活动</Button>}
    {error && <Alert showIcon type="warning" title="活动暂时不可用" description={error} />}
    {loading && items.length === 0 ? <Spin description="正在读取活动" /> : visible.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有可显示的活动" /> : <ol className={styles.activityList}>{visible.map((item) => { const state = ACTIVITY_STATUS[item.status] ?? ACTIVITY_STATUS.info!; return <li key={item.activity_id}><span className={styles.activityDot} /><details><summary><span><Tag color={state.color}>{state.label}</Tag><strong>{item.summary}</strong></span><time dateTime={item.occurred_at}>{new Date(item.occurred_at).toLocaleString('zh-CN')}</time></summary>{(item.reason || item.work_item_id || item.step_count || item.evidence_refs.length) && <div className={styles.activityDetail}>{item.reason && <p>{item.reason}</p>}{item.step_count > 0 && <span>工具步骤 {item.step_count}</span>}{!compact && item.work_item_id && <Button type="link" size="small" onClick={() => setWorkItemId(item.work_item_id)}>只看此工作</Button>}{onSelectRef && item.evidence_refs.map((ref, index) => <Button type="link" size="small" key={`${ref.entity_type}:${ref.id}:${ref.revision}`} onClick={() => onSelectRef(ref)}>查看记录 {index + 1}</Button>)}</div>}</details></li>; })}</ol>}
    {!compact && page?.next_cursor && <Button loading={loading} onClick={() => void load(page.next_cursor, true)}>加载更早活动</Button>}
  </div>;
}

export function TaskWorkspacePanel({ taskId, overview }: { readonly taskId: string; readonly overview: TaskOverviewV1 }) {
  const [section, setSection] = useState<'files' | 'shared' | 'commands' | 'traffic' | 'evidence'>('evidence');
  const [selected, setSelected] = useState<TaskOverviewV1['artifacts'][number] | null>(null);
  const [material, setMaterial] = useState<ModelMaterialV2 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [captureArtifact, setCaptureArtifact] = useState<TaskOverviewV1['artifacts'][number]['artifact_ref'] | null>(null);
  const isCapturePcap = selected?.provenance === 'capture' && selected.media_type === 'application/vnd.tcpdump.pcap';

  useEffect(() => {
    if (!selected || isCapturePcap) { setMaterial(null); setError(null); return; }
    const controller = new AbortController();
    setMaterial(null);
    setError(null);
    void readArtifactMaterial(taskId, selected.artifact_ref.id, selected.artifact_ref.version, controller.signal).then(setMaterial).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '证据预览读取失败');
    });
    return () => controller.abort();
  }, [taskId, selected?.artifact_ref.id, selected?.artifact_ref.version, isCapturePcap]);

  const download = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const blob = await downloadArtifact(selected.artifact_ref.id, selected.artifact_ref.version, new AbortController().signal);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `artifact-${selected.artifact_ref.id}-${selected.artifact_ref.version}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '证据下载失败');
    } finally { setBusy(false); }
  };

  return <div className={styles.workspaceView}>
    <Segmented value={section} options={[{ value: 'files', label: '工作文件' }, { value: 'shared', label: '共享版本' }, { value: 'commands', label: '命令' }, { value: 'traffic', label: '网络采集' }, { value: 'evidence', label: `证据与材料 ${overview.artifacts.length}` }]} onChange={(value) => { setSection(value as typeof section); setSelected(null); setCaptureArtifact(null); }} />
    {section === 'files' && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={overview.workspace_capabilities.work_files ? '当前没有可显示的工作文件' : '当前运行配置尚未开放工作文件浏览'} />}
    {section === 'shared' && <PublicationInventory taskId={taskId} />}
    {section === 'commands' && <CommandInventory taskId={taskId} />}
    {section === 'traffic' && <CaptureInventory taskId={taskId} focusArtifactRef={captureArtifact} />}
    {section === 'evidence' && <div className={styles.workspaceGrid}>
      <div className={styles.artifactList}>{overview.artifacts.length ? overview.artifacts.map((artifact) => <button type="button" className={selected?.artifact_ref.id === artifact.artifact_ref.id && selected.artifact_ref.version === artifact.artifact_ref.version ? styles.artifactSelected : ''} key={`${artifact.artifact_ref.id}:${artifact.artifact_ref.version}`} onClick={() => setSelected(artifact)}><strong>{artifact.provenance === 'import' ? '用户材料' : artifact.provenance === 'capture' ? '采集证据' : '运行记录'} · {artifact.media_type}</strong><span>{artifact.completeness} · {artifact.size_bytes} bytes</span><time dateTime={artifact.created_at}>{new Date(artifact.created_at).toLocaleString('zh-CN')}</time></button>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有证据或用户材料" />}</div>
      <section className={styles.artifactPreview}>{!selected ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择一份证据查看内容" /> : <><header><div><strong>{selected.media_type}</strong><span>{selected.provenance} · {selected.completeness}</span></div>{isCapturePcap ? <Button icon={<DownloadOutlined />} onClick={() => { setCaptureArtifact(selected.artifact_ref); setSection('traffic'); }}>前往网络采集</Button> : selected.download_available && <Button icon={<DownloadOutlined />} loading={busy} onClick={() => void download()}>下载原文</Button>}</header>{error && <Alert showIcon type="warning" title="证据读取失败" description={error} />}{isCapturePcap ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="PCAP 没有文本预览，请在网络采集下载原始文件" /> : material?.status === 'delivered' && material.representation ? <pre className={styles.material}>{material.representation.text}</pre> : material?.status === 'omitted' ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={material.omission_reason === 'unsupported_media' ? '当前材料没有文本预览，可下载原文核对' : material.omission_reason ?? '当前证据没有可显示的文本预览'} /> : !error && <Spin description="正在读取证据" />}<details><summary>来源详情</summary><dl><div><dt>Artifact</dt><dd>{selected.artifact_ref.id}@{selected.artifact_ref.version}</dd></div><div><dt>摘要</dt><dd>{selected.artifact_ref.sha256}</dd></div><div><dt>来源工作</dt><dd>{selected.source_work_item_id ?? '未关联'}</dd></div></dl></details></>}</section>
    </div>}
  </div>;
}
