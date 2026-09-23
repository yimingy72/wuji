import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  PauseOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Checkbox,
  Empty,
  Input,
  Select,
  Spin,
  Tabs,
  Tag,
} from 'antd';
import { useSearchParams } from 'react-router-dom';
import { webConfig } from '../../config';
import { ApiRequestError } from '../../api';
import {
  artifactContentPath,
  commandTask,
  createTask,
  listTasks,
  materialPath,
  readLaunch,
  readReadiness,
  readTask,
  readTaskOverview,
  readTaskOptions,
  type ReadinessCheck,
  type ReadinessReport,
  type LaunchView,
  type TaskCreate,
  type TaskOptions,
  type TaskOverviewV1,
  type TaskView,
  type WorkbenchSession,
} from '../../v2WorkbenchApi';
import { TopologyContainer } from '../topology/TopologyContainer';
import type { KnowledgeRef, TopologySelection, TopologySnapshotInput } from '../topology/contracts';
import { RecordPanel } from '../topology/panels/RecordPanel';
import { SnapshotSelector, type ViewChoice } from '../topology/panels/SnapshotSelector';
import { selectedRecordRef } from '../topology/record';
import { CompletionPanel } from '../completion/CompletionPanel';
import { ProblemBoard } from '../exploration/ProblemBoard';
import { InputPanel } from '../exploration/InputPanel';
import { TaskActivityPanel, TaskOverviewPanel, TaskWorkspacePanel } from './TaskWorkbenchSections';
import { commandStatusMessage, includeRequestedTask, selectAuthorizedTaskId, taskStatusLabel } from './workbenchState';
import styles from './firstUseWorkbench.module.css';

const CREATE_KEY = 'wuji.first-use.v2.create-key';

const scenarioLabels: Readonly<Record<TaskCreate['scenario'], string>> = {
  web_single: 'Web 单点',
  ctf: 'CTF（HTTP(S) 靶场入口）',
  comprehensive: '综合渗透（当前未发布）',
  adversary_emulation: '攻防演练（当前未发布）',
  code_audit: '代码审计（当前未发布）',
};

interface FirstUseWorkbenchProps {
  readonly session: WorkbenchSession;
  readonly onSessionExpired: () => void;
  readonly onLogout: () => Promise<void>;
}

interface CreateDraft {
  readonly scenario: Extract<TaskCreate['scenario'], 'web_single' | 'ctf'>;
  readonly name: string;
  readonly entryPoint: string;
  readonly goal: string;
  readonly criteria: string;
  readonly expiresAt: string;
  readonly modelRef: string;
  readonly runtimeRef: string;
  readonly exploreConcurrency: string;
  readonly budget: string;
  readonly targetConfirmed: boolean;
  readonly materialConfirmed: boolean;
}

interface ParsedEntry {
  readonly url: string;
  readonly protocol: 'http' | 'https';
  readonly host: string;
  readonly port: number;
}

interface CommandNotice {
  readonly kind: 'accepted' | 'unknown' | 'error';
  readonly command: TaskView['allowed_actions'][number];
  readonly message: string;
  readonly key: string;
}

export function resolveTaskSelection(
  taskIds: readonly string[],
  requestedTaskId: string | null,
  sessionTaskId: string | null | undefined,
  compatibleTaskId: string,
  explicitTaskId: string | null,
): string | null {
  return explicitTaskId ?? selectAuthorizedTaskId(taskIds, requestedTaskId, sessionTaskId, compatibleTaskId);
}

function initialDraft(options: TaskOptions | null): CreateDraft {
  return {
    scenario: 'web_single',
    name: '',
    entryPoint: '',
    goal: '',
    criteria: '',
    expiresAt: '',
    modelRef: options?.model_profiles.find((item) => item.real_model_allowed)?.ref ?? '',
    runtimeRef: options?.runtime_profiles.find((item) => item.real_model_allowed)?.ref ?? '',
    exploreConcurrency: '',
    budget: '',
    targetConfirmed: false,
    materialConfirmed: false,
  };
}

function parseEntryPoint(value: string): ParsedEntry | null {
  try {
    const parsed = new URL(value.trim());
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    if (parsed.username || parsed.password || parsed.hash || !parsed.hostname) return null;
    return {
      url: parsed.toString(),
      protocol: parsed.protocol === 'https:' ? 'https' : 'http',
      host: parsed.hostname.toLowerCase(),
      port: Number(parsed.port || (parsed.protocol === 'https:' ? 443 : 80)),
    };
  } catch {
    return null;
  }
}

function criteriaFromText(value: string): string[] {
  return value.split('\n').map((item) => item.trim()).filter(Boolean);
}

function validDecimal(value: string): boolean {
  return /^(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(value) && Number(value) > 0;
}

function toDateTime(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function createBody(draft: CreateDraft, projectId: string, entry: ParsedEntry, criteria: string[]): TaskCreate {
  return {
    schema_version: 'wuji.api.v2',
    project_id: projectId,
    name: draft.name.trim(),
    scenario: draft.scenario,
    goal: {
      text: draft.goal.trim(),
      criteria: criteria.map((condition, index) => ({
        criterion_id: `criterion-${index + 1}`,
        object: '获准入口的非破坏性验证',
        condition,
        evidence_requirements: ['保存实际 HTTP/工具证据；未执行项保留明确原因'],
        allowed_methods: ['deterministic', 'reproduced_check', 'human_attestation'],
        responsible_party: 'operator',
        required: true,
      })),
    },
    authorization_scope: [{ host: entry.host, protocol: entry.protocol, port: entry.port }],
    authorization_expires_at: toDateTime(draft.expiresAt) ?? new Date(0).toISOString(),
    entry_points: [entry.url],
    external_analysis_approved: draft.materialConfirmed,
    model_profile_ref: draft.modelRef,
    runtime_profile_ref: draft.runtimeRef,
    ...(draft.exploreConcurrency ? { explore_concurrency: Number(draft.exploreConcurrency) } : {}),
    budget: { amount: draft.budget, currency: 'USD' },
  };
}

async function createSignature(body: TaskCreate): Promise<string> {
  const bytes = new TextEncoder().encode(JSON.stringify(body));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

async function createKeyFor(body: TaskCreate, projectId: string): Promise<string> {
  const signature = await createSignature(body);
  try {
    const stored = sessionStorage.getItem(CREATE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as { project_id?: unknown; signature?: unknown; key?: unknown };
      if (parsed.project_id === projectId && parsed.signature === signature && typeof parsed.key === 'string') return parsed.key;
    }
    const key = crypto.randomUUID();
    sessionStorage.setItem(CREATE_KEY, JSON.stringify({ project_id: projectId, signature, key }));
    return key;
  } catch {
    throw new Error('无法保存创建请求标识，请检查浏览器存储设置后重试。');
  }
}

function clearCreateKey(): void {
  try { sessionStorage.removeItem(CREATE_KEY); } catch { /* private browsing can reject storage */ }
}

function statusColor(label: string): string {
  if (label === '运行中') return 'green';
  if (label === '已暂停' || label === '停止收敛中') return 'orange';
  if (label === '待核对' || label === '收尾中' || label.includes('受理')) return 'gold';
  if (label.includes('阻断')) return 'red';
  if (label === '已停止' || label === '部分结果') return 'blue';
  return 'default';
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) return '会话已失效，请重新进入工作台。后台 Task 不会因为浏览器断开而被取消。';
    if (error.status === 403 || error.status === 404) return '内容不可访问，平台没有返回未授权的 Task 详情。';
    if (error.status === 409) return '平台拒绝了这次状态变化，请读取当前 Task 和原操作结果。';
    if (error.status === 503 || error.status === 0) return '平台暂时不可用，原操作可能已经受理，请使用原键查询。';
    return error.message;
  }
  return error instanceof Error ? error.message : '请求未完成';
}

function checkClass(status: ReadinessCheck['status']): string {
  return status === 'pass' ? (styles.checkPass ?? '') : status === 'fail' ? (styles.checkFail ?? '') : status === 'unknown' ? (styles.checkUnknown ?? '') : '';
}

function CheckList({ checks }: { readonly checks: readonly ReadinessCheck[] }) {
  if (checks.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="平台没有返回就绪检查项" />;
  return (
    <ul className={styles.checks} data-testid="readiness-checks">
      {checks.map((check) => (
        <li className={`${styles.check} ${checkClass(check.status)}`} key={check.id}>
          <span className={styles.checkDot} aria-hidden="true" />
          <div>
            <strong>{check.layer} · {check.id} · {check.status}</strong>
            <p>{check.message}（{check.reason_code}，处理方：{check.remediation_owner}）</p>
          </div>
          <time dateTime={check.observed_at}>{new Date(check.observed_at).toLocaleString('zh-CN')}</time>
        </li>
      ))}
    </ul>
  );
}

interface TaskWorkspaceProps {
  readonly taskId: string;
  readonly session: WorkbenchSession;
  readonly onSessionExpired: () => void;
  readonly onTaskUpdated: (task: TaskView) => void;
  readonly onLaunchUpdated: (taskId: string, launch: LaunchView) => void;
  readonly onRuntimeUpdated: (taskId: string, state: TaskOverviewV1['runtime']['state']) => void;
}

function TaskWorkspace({ taskId, session, onSessionExpired, onTaskUpdated, onLaunchUpdated, onRuntimeUpdated }: TaskWorkspaceProps) {
  const [task, setTask] = useState<TaskView | null>(null);
  const [overview, setOverview] = useState<TaskOverviewV1 | null>(null);
  const [launch, setLaunch] = useState<LaunchView | null>(null);
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [selection, setSelection] = useState<TopologySelection | null>(null);
  const [snapshot, setSnapshot] = useState<TopologySnapshotInput | null>(null);
  const [problemSnapshotId, setProblemSnapshotId] = useState<string | null>(null);
  const [viewChoice, setViewChoice] = useState<ViewChoice>({ mode: 'live', snapshotId: null });
  const [activeTab, setActiveTab] = useState('overview');
  const [completionOpen, setCompletionOpen] = useState(false);
  const [notice, setNotice] = useState<CommandNotice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [statusRefresh, setStatusRefresh] = useState(0);
  const generation = useRef(0);
  const active = useRef<AbortController | null>(null);
  const readinessActive = useRef<AbortController | null>(null);
  const commandKeys = useRef(new Map<string, string>());

  useEffect(() => {
    const currentGeneration = generation.current + 1;
    generation.current = currentGeneration;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    setOverviewError(null);
    void readTask(taskId, controller.signal).then((nextTask) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setTask(nextTask);
      onTaskUpdated(nextTask);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(errorMessage(reason));
    }).finally(() => {
      if (!controller.signal.aborted && generation.current === currentGeneration) setLoading(false);
    });
    void readTaskOverview(taskId, controller.signal).then((nextOverview) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setOverview(nextOverview);
      onRuntimeUpdated(taskId, nextOverview.runtime.state);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setOverviewError(errorMessage(reason));
    });
    void readLaunch(taskId, controller.signal).then((nextLaunch) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setLaunch(nextLaunch);
      onLaunchUpdated(taskId, nextLaunch);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted && reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
    });
    return () => {
      controller.abort();
    };
  }, [taskId, refresh, statusRefresh, onSessionExpired, onTaskUpdated, onLaunchUpdated, onRuntimeUpdated]);

  useEffect(() => () => readinessActive.current?.abort(), [taskId]);

  useEffect(() => {
    if (!task || !overview || !(
      ['running', 'quiescing', 'reconciling'].includes(task.observed_state)
      || overview.runtime.state === 'stopping'
    )) return;
    const timer = window.setInterval(() => setStatusRefresh((value) => value + 1), 5000);
    return () => window.clearInterval(timer);
  }, [task?.observed_state, overview?.runtime.state]);

  const selectedRef = useMemo(
    () => selection?.mode === 'explicit_revision' ? selection.ref : selectedRecordRef(snapshot, selection),
    [selection, snapshot],
  );
  const handleProblemSnapshot = useCallback((next: string) => setProblemSnapshotId(next), []);
  const handleProblemSelect = useCallback((ref: KnowledgeRef) => setSelection({ mode: 'explicit_revision', ref }), []);
  const openRecord = useCallback((ref: KnowledgeRef) => {
    setSelection({ mode: 'explicit_revision', ref });
    setSnapshot(null);
    setProblemSnapshotId(null);
    setViewChoice({ mode: 'live', snapshotId: null });
    setActiveTab('findings');
  }, []);
  const label = taskStatusLabel(task, launch, overview?.runtime.state);
  const allowed = task?.allowed_actions ?? [];

  const refreshCurrent = () => setRefresh((value) => value + 1);

  const loadReadiness = () => {
    if (readiness || readinessLoading) return;
    readinessActive.current?.abort();
    const controller = new AbortController();
    readinessActive.current = controller;
    setReadinessLoading(true);
    setReadinessError(null);
    void readReadiness(taskId, controller.signal).then((next) => {
      if (!controller.signal.aborted) setReadiness(next);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setReadinessError(errorMessage(reason));
    }).finally(() => {
      if (!controller.signal.aborted) setReadinessLoading(false);
    });
  };

  const submitCommand = async (command: TaskView['allowed_actions'][number]) => {
    if (!task || !allowed.includes(command)) return;
    const body = { schema_version: 'wuji.api.v2' as const, command, expected_version: task.version, reason: `workbench:${command}` };
    const scope = `${task.task_id}:${command}:${task.version}`;
    const key = commandKeys.current.get(scope) ?? crypto.randomUUID();
    commandKeys.current.set(scope, key);
    setNotice({ kind: 'accepted', command, key, message: `${command} 已提交，正在核对真实状态` });
    try {
      await commandTask(task.task_id, body, key, session.csrf_token, new AbortController().signal);
      setNotice({ kind: 'accepted', command, key, message: command === 'cancel' ? '取消已受理，正在核对；尚未显示已停止。' : `${command} 已受理，正在核对当前 Task。` });
      refreshCurrent();
      window.setTimeout(refreshCurrent, 800);
      window.setTimeout(refreshCurrent, 1800);
      window.setTimeout(refreshCurrent, 3600);
    } catch (reason) {
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      const unknown = reason instanceof ApiRequestError && (String(reason.code) === 'OPERATION_UNKNOWN' || reason.status === 0 || reason.status === 503);
      setNotice({ kind: unknown ? 'unknown' : 'error', command, key, message: unknown ? '执行状态未知，请查询原操作结果；不会换键重发。' : errorMessage(reason) });
      setError(unknown ? null : errorMessage(reason));
    }
  };

  if (loading && !task) return <div className={styles.detailBody}><div aria-live="polite"><Spin description="正在读取任务" /></div></div>;
  if (error && !task) return <div className={styles.detailBody}><Alert showIcon type="error" title="Task 读取失败" description={error} action={<Button onClick={refreshCurrent}>重新读取</Button>} /></div>;
  if (!task) return <div className={styles.detailBody}><Empty description="当前 Task 不可访问" /></div>;
  const launchPreparing = launch?.phase_status === 'pending' || launch?.phase_status === 'running';
  const statusMessage = task.observed_state !== 'closed' && overview?.runtime.state !== 'running'
    ? launch?.phase_status === 'failed' ? '执行环境准备失败，尚未开始工作'
      : launch?.phase_status === 'blocked' ? '执行环境准备受阻，尚未开始工作'
      : launchPreparing ? '正在准备执行环境，尚未开始工作'
      : overview?.runtime.state === 'stopped'
        ? task.observed_state === 'paused' ? '已暂停，执行环境已停止' : '执行已停止，结果结算中'
        : overview?.status_message ?? '正在读取任务概览'
    : overview?.status_message ?? '正在读取任务概览';

  return (
    <div className={styles.detailBody}>
      {error && <Alert showIcon type="warning" title="读取未完成" description={error} action={<Button onClick={refreshCurrent}>重新读取</Button>} />}
      {notice && <Alert showIcon type={notice.kind === 'error' ? 'error' : notice.kind === 'unknown' ? 'warning' : 'info'} title={commandStatusMessage(notice.command, label, notice.message)} action={<Button onClick={refreshCurrent}>查看当前状态</Button>} />}
      <div className={styles.taskHeader}>
        <div className={styles.taskTitle}>
          <span>{scenarioLabels[task.scenario]}</span>
          <h1>{task.name}</h1>
          <p>{statusMessage}</p>
        </div>
        <div className={styles.taskMeta} data-testid="task-status">
          <Tag color={statusColor(label)}>{label}</Tag>
          {task.result_outcome && <Tag>{task.result_outcome}</Tag>}
        </div>
        <div className={styles.controlBar} aria-label="Task 控制">
          {allowed.includes('start') && <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => void submitCommand('start')} data-testid="task-start">启动</Button>}
          {allowed.includes('pause') && <Button icon={<PauseOutlined />} onClick={() => void submitCommand('pause')} data-testid="task-pause">暂停</Button>}
          {allowed.includes('resume') && <Button icon={<ReloadOutlined />} onClick={() => void submitCommand('resume')} data-testid="task-resume">继续</Button>}
          {allowed.includes('cancel') && <Button danger icon={<StopOutlined />} onClick={() => void submitCommand('cancel')} data-testid="task-cancel">停止</Button>}
          <Button icon={<ReloadOutlined />} onClick={refreshCurrent}>刷新</Button>
        </div>
      </div>
      <Tabs className={styles.taskTabs} activeKey={activeTab} onChange={setActiveTab} items={[
        { key: 'overview', label: '概览', children: <div className={styles.tabBody}>
          {overviewError && <Alert showIcon type="warning" title="概览暂时不可用" description={overviewError} action={<Button onClick={refreshCurrent}>重试</Button>} />}
          {overview ? <TaskOverviewPanel overview={overview} taskId={task.task_id} onSelectRef={openRecord} onSessionExpired={onSessionExpired} /> : !overviewError && <Spin description="正在读取概览" />}
          <section className={styles.sectionCard}><header><div><span>需要你的处理</span><h2>输入与审批</h2></div></header><InputPanel taskId={task.task_id} csrfToken={session.csrf_token} refreshKey={refresh} onChanged={refreshCurrent} onSessionExpired={onSessionExpired} /></section>
          <details className={styles.technical} onToggle={(event) => setCompletionOpen(event.currentTarget.open)}><summary>完成审核详情</summary>{completionOpen && <CompletionPanel taskId={task.task_id} onChanged={refreshCurrent} />}</details>
        </div> },
        { key: 'activity', label: '活动', children: <TaskActivityPanel taskId={task.task_id} onSelectRef={openRecord} onSessionExpired={onSessionExpired} /> },
        { key: 'workspace', label: '工作区', children: overview ? <TaskWorkspacePanel taskId={task.task_id} overview={overview} /> : <Alert showIcon type="warning" title="工作区暂时不可用" description={overviewError ?? '正在读取工作区能力'} /> },
        { key: 'findings', label: '发现与证据', children: <div className={styles.tabBody}>
          <SnapshotSelector taskId={task.task_id} value={viewChoice} onChange={(next) => { setSelection(null); setSnapshot(null); setProblemSnapshotId(null); setViewChoice(next); }} />
          <ProblemBoard key={`${task.task_id}:${viewChoice.mode}:${viewChoice.snapshotId ?? 'live'}:${refresh}`} taskId={task.task_id} mode={viewChoice.mode} snapshotId={viewChoice.snapshotId} refreshKey={refresh} onSnapshotChange={handleProblemSnapshot} onSelect={handleProblemSelect} onSessionExpired={onSessionExpired} />
          <div className={styles.detail}><RecordPanel taskId={task.task_id} snapshotId={problemSnapshotId} ref={selectedRef} /></div>
          <details className={styles.technical}>
            <summary>高级关联视图</summary>
            {problemSnapshotId ? <TopologyContainer key={`${task.task_id}:${problemSnapshotId}`} taskId={task.task_id} mode="history" snapshotId={problemSnapshotId} selection={selection} onSelect={setSelection} onSnapshotChange={setSnapshot} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待发现快照" />}
          </details>
        </div> },
      ]} />
      <details className={styles.technical} onToggle={(event) => { if (event.currentTarget.open) loadReadiness(); }}>
        <summary>技术详情与启动诊断</summary>
        {overview && <dl className={styles.evidenceMeta}>
          <div><dt>Definition digest</dt><dd>{overview.technical.definition_digest}</dd></div>
          <div><dt>Control version</dt><dd>{overview.technical.control_version}</dd></div>
          <div><dt>Execution epoch / Runtime attempt</dt><dd>{overview.technical.execution_epoch} / {overview.technical.runtime_attempt}</dd></div>
          <div><dt>Schema</dt><dd>{overview.technical.schema_version}</dd></div>
          <div><dt>最近启动操作</dt><dd>{overview.technical.latest_launch_operation_id ?? '未请求'}</dd></div>
          <div><dt>最近启动阶段 / 原因</dt><dd>{overview.technical.latest_launch_phase ?? 'not_requested'} / {overview.technical.latest_launch_reason_code ?? '无'}</dd></div>
          {notice && <div><dt>Idempotency-Key</dt><dd>{notice.key}</dd></div>}
        </dl>}
        {readinessError && <Alert showIcon type="warning" title="启动诊断暂时不可用" description={readinessError} />}
        {readinessLoading ? <Spin description="正在读取启动诊断" /> : readiness && <><Tag color={readiness.can_request_start ? 'green' : 'orange'}>{readiness.can_request_start ? '可受理启动' : '当前阻断'}</Tag><CheckList checks={readiness.checks} /></>}
      </details>
    </div>
  );
}

interface TaskCreatePanelProps {
  readonly session: WorkbenchSession;
  readonly options: TaskOptions | null;
  readonly optionsError: unknown;
  readonly onCreated: (task: TaskView) => void;
  readonly onClose: () => void;
  readonly onSessionExpired: () => void;
}

function TaskCreatePanel({ session, options, optionsError, onCreated, onClose, onSessionExpired }: TaskCreatePanelProps) {
  const [draft, setDraft] = useState<CreateDraft>(() => initialDraft(options));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const entry = parseEntryPoint(draft.entryPoint);
  const criteria = criteriaFromText(draft.criteria);
  const expiry = toDateTime(draft.expiresAt);
  const selectedModel = options?.model_profiles.find((item) => item.ref === draft.modelRef) ?? null;
  const selectedRuntime = options?.runtime_profiles.find((item) => item.ref === draft.runtimeRef) ?? null;
  const exploreConcurrency = draft.exploreConcurrency === '' ? null : Number(draft.exploreConcurrency);
  const concurrencyValid = exploreConcurrency === null || (
    Number.isInteger(exploreConcurrency)
      && selectedRuntime?.max_explore_concurrency != null
      && exploreConcurrency >= 1
      && exploreConcurrency <= selectedRuntime.max_explore_concurrency
  );
  const ready = Boolean(
    options
      && options.missing.length === 0
      && draft.name.trim()
      && entry
      && draft.goal.trim()
      && criteria.length > 0
      && expiry
      && new Date(expiry).getTime() > Date.now()
      && draft.modelRef
      && draft.runtimeRef
      && concurrencyValid
      && validDecimal(draft.budget)
      && draft.targetConfirmed
      && draft.materialConfirmed,
  );
  const body = ready && entry && expiry ? createBody(draft, session.project_id, entry, criteria) : null;

  useEffect(() => {
    setDraft(initialDraft(options));
  }, [options]);

  const patch = <K extends keyof CreateDraft>(key: K, value: CreateDraft[K]) => setDraft((current) => ({ ...current, [key]: value }));

  const submit = async () => {
    if (!body) return;
    setBusy(true);
    setError(null);
    try {
      const key = await createKeyFor(body, session.project_id);
      const created = await createTask(body, key, session.csrf_token, new AbortController().signal);
      clearCreateKey();
      onCreated(created);
    } catch (reason) {
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      const unknown = reason instanceof ApiRequestError && (reason.status === 0 || reason.status === 503 || String(reason.code) === 'OPERATION_UNKNOWN');
      setError(unknown ? '创建响应不明；原 Idempotency-Key 已保留。请返回目录刷新核对，不会自动换键重发。' : errorMessage(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.detail} aria-label="新建任务" data-testid="task-create-form">
      <div className={styles.detailHeader}><div><strong>新建任务</strong><span>创建后可以再启动</span></div><Button onClick={onClose}>关闭</Button></div>
      <div className={styles.detailBody}>
        {Boolean(optionsError) && <Alert showIcon type="error" title="目录加载失败" description="无法确认当前身份可用的发布 Profile；不会回落 synthetic 配置。" />}
        {options && options.missing.length > 0 && <Alert showIcon type="warning" title="当前不能创建" description={options.missing.map((item) => `${item.layer}/${item.id}: ${item.message}`).join('；')} />}
        {error && <Alert showIcon type="error" title="创建未完成" description={error} />}
        <div className={styles.form}>
          <div className={styles.formSection}>
            <h2>目标与场景</h2>
            <div className={styles.formGrid}>
              <label className={styles.full}>场景<Select aria-label="任务场景" value={draft.scenario} options={Object.entries(scenarioLabels).map(([value, label]) => ({ value, label, disabled: value !== 'web_single' && value !== 'ctf' }))} onChange={(value) => patch('scenario', value as CreateDraft['scenario'])} /></label>
              {draft.scenario === 'ctf' && <p className={styles.formHint + ' ' + styles.full}>填写靶场 HTTP(S) 地址和本题完成条件。</p>}
              <label>任务名称<Input aria-label="任务名称" value={draft.name} onChange={(event) => patch('name', event.target.value)} placeholder="例如：授权入口首轮验证" /></label>
              <label>完整入口 URL<Input aria-label="完整入口 URL" data-testid="task-url" value={draft.entryPoint} onChange={(event) => patch('entryPoint', event.target.value)} placeholder="https://approved.example.test/path?view=summary" /></label>
              <p className={styles.formHint + ' ' + styles.full}>入口的 path/query 会原样进入创建快照；不会扩大 scheme/host/port 授权。禁止用户名、密码、fragment 和未支持协议。</p>
              <label className={styles.full}>任务目标<Input.TextArea aria-label="任务目标" data-testid="task-goal" rows={3} value={draft.goal} onChange={(event) => patch('goal', event.target.value)} /></label>
              <label className={styles.full}>完成条件（每行一条）<Input.TextArea aria-label="完成条件" data-testid="task-criteria" rows={4} value={draft.criteria} onChange={(event) => patch('criteria', event.target.value)} placeholder="保存实际状态与正文证据\n记录未执行或阻断原因" /></label>
            </div>
          </div>
          <div className={styles.formSection}>
            <h2>批准范围与期限</h2>
            <div className={styles.profileCard}><strong>{entry ? `${entry.protocol}://${entry.host}:${entry.port}` : '等待合法入口'}</strong><code>{entry?.url ?? '路径与 query 将按原文保留'}</code><span>范围仅含入口 origin；平台仍会在创建和启动时重验。</span></div>
            <label>授权截止时间<Input aria-label="授权截止时间" type="datetime-local" value={draft.expiresAt} onChange={(event) => patch('expiresAt', event.target.value)} /></label>
            <div className={styles.policy}>
              <Checkbox checked={draft.targetConfirmed} onChange={(event) => patch('targetConfirmed', event.target.checked)}>我确认对该入口及上述期限拥有目标访问授权。</Checkbox>
              <Checkbox checked={draft.materialConfirmed} onChange={(event) => patch('materialConfirmed', event.target.checked)}>我确认允许本 Task 按已发布政策将获准材料发送给所选外部模型服务；这与目标访问授权是两项独立确认。</Checkbox>
            </div>
          </div>
          <div className={styles.formSection}>
            <h2>模型与运行配置</h2>
            <div className={styles.formGrid}>
              <label>模型方案<Select aria-label="模型方案" value={draft.modelRef || undefined} options={options?.model_profiles.map((item) => ({ value: item.ref, label: `${item.name} · ${item.revision}` }))} onChange={(value) => patch('modelRef', value)} placeholder="选择已发布模型" /></label>
              <label>运行配置<Select aria-label="运行配置" value={draft.runtimeRef || undefined} options={options?.runtime_profiles.map((item) => ({ value: item.ref, label: `${item.name} · ${item.revision}` }))} onChange={(value) => setDraft((current) => ({ ...current, runtimeRef: value, exploreConcurrency: '' }))} placeholder="选择已发布运行配置" /></label>
            </div>
            {selectedModel && <div className={styles.profileCard}><strong>{selectedModel.name} · {selectedModel.revision}</strong><div className={styles.profileCapabilities}>{selectedModel.capabilities.map((capability) => <span key={capability}>{capability}</span>)}</div><span>执行将使用所选模型配置的固定版本。</span><details><summary>技术标识</summary><code>{selectedModel.ref} · digest {selectedModel.digest}</code></details></div>}
            {selectedRuntime && <div className={styles.profileCard}><strong>{selectedRuntime.name} · {selectedRuntime.revision}</strong><div className={styles.profileCapabilities}>{selectedRuntime.capabilities.map((capability) => <span key={capability}>{capability}</span>)}</div><span>运行上限与可用能力以此发布版本为准。</span><details><summary>技术标识</summary><code>{selectedRuntime.ref} · digest {selectedRuntime.digest}</code></details></div>}
            {selectedRuntime?.max_explore_concurrency != null && <label>Explore 并发（1–{selectedRuntime.max_explore_concurrency}）<Input aria-label="Explore 并发" type="number" min={1} max={selectedRuntime.max_explore_concurrency} step={1} value={draft.exploreConcurrency} onChange={(event) => patch('exploreConcurrency', event.target.value)} placeholder={`留空使用发布默认值 ${selectedRuntime.max_explore_concurrency}`} /></label>}
            {selectedRuntime && selectedRuntime.max_explore_concurrency == null && <p className={styles.formHint}>此运行配置未开放并发调整。</p>}
            <label>任务预算（USD）<Input aria-label="Task 金额预算" data-testid="task-budget" inputMode="decimal" value={draft.budget} onChange={(event) => patch('budget', event.target.value)} placeholder="1.00" /></label>
            <p className={styles.formHint}>任务内的所有分析调用共用这笔预算。</p>
          </div>
          <div className={styles.modalFooter}><Button onClick={onClose}>取消</Button><Button type="primary" loading={busy} disabled={!ready} data-testid="task-create-submit" onClick={() => void submit()}>创建待启动 Task</Button></div>
        </div>
      </div>
    </section>
  );
}

export function FirstUseWorkbench({ session, onSessionExpired, onLogout }: FirstUseWorkbenchProps) {
  const [search, setSearch] = useSearchParams();
  const [tasks, setTasks] = useState<TaskView[]>([]);
  const [launchByTask, setLaunchByTask] = useState<Record<string, LaunchView>>({});
  const [runtimeByTask, setRuntimeByTask] = useState<Record<string, TaskOverviewV1['runtime']['state']>>({});
  const [cursor, setCursor] = useState<string | null>(null);
  const [taskCursor, setTaskCursor] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [options, setOptions] = useState<TaskOptions | null>(null);
  const [optionsError, setOptionsError] = useState<unknown>(null);
  const [listError, setListError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [listNonce, setListNonce] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const listGeneration = useRef(0);
  const listController = useRef<AbortController | null>(null);
  const explicitSelection = useRef<string | null>(null);
  const initialRequestedTaskId = useRef(search.get('task')).current;

  const selectedTask = tasks.find((task) => task.task_id === selectedTaskId) ?? null;
  const updateTask = useCallback((nextTask: TaskView) => {
    setTasks((current) => current.map((task) => task.task_id === nextTask.task_id ? nextTask : task));
  }, []);
  const updateLaunch = useCallback((taskId: string, nextLaunch: LaunchView) => {
    setLaunchByTask((current) => ({ ...current, [taskId]: nextLaunch }));
  }, []);
  const updateRuntime = useCallback((taskId: string, state: TaskOverviewV1['runtime']['state']) => {
    setRuntimeByTask((current) => ({ ...current, [taskId]: state }));
  }, []);
  const selectTask = (taskId: string) => {
    if (!tasks.some((task) => task.task_id === taskId)) return;
    explicitSelection.current = taskId;
    setSelectedTaskId(taskId);
    setSearch((current) => { const next = new URLSearchParams(current); next.set('task', taskId); return next; }, { replace: true });
  };

  useEffect(() => {
    const currentGeneration = listGeneration.current + 1;
    listGeneration.current = currentGeneration;
    listController.current?.abort();
    const controller = new AbortController();
    listController.current = controller;
    setLoading(true);
    setListError(null);
    const requested = !taskCursor && initialRequestedTaskId
      ? readTask(initialRequestedTaskId, controller.signal).catch((reason: unknown) => {
        if (reason instanceof ApiRequestError && (reason.status === 403 || reason.status === 404)) return null;
        throw reason;
      })
      : Promise.resolve(null);
    void Promise.all([listTasks(session.project_id, taskCursor, controller.signal), requested]).then(([page, requestedTask]) => {
      if (controller.signal.aborted || listGeneration.current !== currentGeneration) return;
      setTasks((current) => taskCursor
        ? [...current, ...page.items.filter((item) => !current.some((existing) => existing.task_id === item.task_id))]
        : includeRequestedTask(page.items, requestedTask));
      setCursor(page.next_cursor);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || listGeneration.current !== currentGeneration) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setListError(reason);
    }).finally(() => {
      if (!controller.signal.aborted && listGeneration.current === currentGeneration) setLoading(false);
    });
    return () => controller.abort();
  }, [session.project_id, session.identity_mode, taskCursor, listNonce, onSessionExpired, initialRequestedTaskId]);

  useEffect(() => {
    const requested = search.get('task');
    const compatible = resolveTaskSelection(
      tasks.map((task) => task.task_id),
      requested,
      session.task_id,
      webConfig.taskId,
      explicitSelection.current,
    );
    if (compatible !== selectedTaskId) setSelectedTaskId(compatible);
  }, [search, session.task_id, tasks, selectedTaskId]);

  useEffect(() => {
    if (!createOpen) return;
    const controller = new AbortController();
    setOptionsError(null);
    void readTaskOptions(session.project_id, controller.signal).then(setOptions).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
        setOptionsError(reason);
      }
    });
    return () => controller.abort();
  }, [createOpen, session.project_id, onSessionExpired]);

  const refreshList = () => { setTaskCursor(null); setCursor(null); setListNonce((value) => value + 1); };
  const openCreated = (created: TaskView) => {
    listGeneration.current += 1;
    listController.current?.abort();
    explicitSelection.current = created.task_id;
    setCreateOpen(false);
    setTasks((current) => [created, ...current.filter((task) => task.task_id !== created.task_id)]);
    setLoading(false);
    setSelectedTaskId(created.task_id);
    setSearch((current) => { const next = new URLSearchParams(current); next.set('task', created.task_id); return next; }, { replace: true });
  };
  const logout = async () => {
    setLoggingOut(true);
    try { await onLogout(); } finally { setLoggingOut(false); }
  };

  return (
    <div className={styles.workbench}>
      <section className={styles.identity} aria-label="工作台身份">
        <div><h1>任务工作台</h1><p>创建任务、查看进展和核对结果。</p></div>
        <div className={styles.identityMeta}><span>{session.display_name}</span><Button loading={loggingOut} onClick={() => void logout()}>退出</Button></div>
      </section>
      {Boolean(listError) && <Alert showIcon type="error" title="任务目录读取失败" description={errorMessage(listError)} action={<Button onClick={refreshList}>重试</Button>} />}
      <div className={styles.body}>
        <aside className={styles.directory} aria-label="任务目录" data-testid="task-list">
          <div className={styles.directoryHeader}><div><strong>我的任务</strong></div><Button type="primary" onClick={() => setCreateOpen(true)} data-testid="new-task">新建任务</Button></div>
          {loading && tasks.length === 0 ? <div className={styles.directoryEmpty}><Spin description="正在读取 Task 目录" /></div> : tasks.length === 0 ? <div className={styles.directoryEmpty}><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有可访问的 Task" /><Button type="primary" onClick={() => setCreateOpen(true)}>创建首个 Task</Button></div> : <div className={styles.taskList}>{tasks.map((task) => { const label = taskStatusLabel(task, launchByTask[task.task_id] ?? null, runtimeByTask[task.task_id]); return <button className={`${styles.taskItem} ${selectedTaskId === task.task_id ? styles.taskItemActive : ''}`} type="button" key={task.task_id} onClick={() => selectTask(task.task_id)}><strong>{task.name}</strong><span className={styles.taskItemMeta}><Tag color={statusColor(label)}>{label}</Tag><span>{scenarioLabels[task.scenario]}</span></span></button>; })}</div>}
          <div className={styles.directoryFooter}><Button size="small" icon={<ReloadOutlined />} onClick={refreshList}>刷新目录</Button>{cursor && <Button size="small" onClick={() => setTaskCursor(cursor)}>加载更多</Button>}</div>
        </aside>
        <main className={styles.detail} aria-label="Task 详情">
          {createOpen ? <TaskCreatePanel session={session} options={options} optionsError={optionsError} onCreated={openCreated} onClose={() => setCreateOpen(false)} onSessionExpired={onSessionExpired} /> : selectedTask ? <TaskWorkspace key={selectedTask.task_id} taskId={selectedTask.task_id} session={session} onSessionExpired={onSessionExpired} onTaskUpdated={updateTask} onLaunchUpdated={updateLaunch} onRuntimeUpdated={updateRuntime} /> : <div className={styles.detailBody}><Empty description="从左侧选择一个 Task，或新建首个 Task" /></div>}
        </main>
      </div>
    </div>
  );
}

export { artifactContentPath, materialPath };
