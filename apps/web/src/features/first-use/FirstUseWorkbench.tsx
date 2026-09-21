import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  DownloadOutlined,
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
  Tag,
  Typography,
} from 'antd';
import { useSearchParams } from 'react-router-dom';
import { webConfig } from '../../config';
import { ApiRequestError } from '../../api';
import {
  artifactContentPath,
  commandTask,
  createTask,
  downloadArtifact,
  listTasks,
  materialPath,
  readArtifactMaterial,
  readLaunch,
  readReadiness,
  readTask,
  readTaskOptions,
  type LaunchView,
  type ModelMaterialV2,
  type ReadinessCheck,
  type ReadinessReport,
  type TaskCreate,
  type TaskOptions,
  type TaskView,
  type WorkbenchSession,
} from '../../v2WorkbenchApi';
import { TopologyContainer } from '../topology/TopologyContainer';
import type { KnowledgeRef, TopologySelection, TopologySnapshotInput } from '../topology/contracts';
import { RecordPanel, readRecordView } from '../topology/panels/RecordPanel';
import { SnapshotSelector, type ViewChoice } from '../topology/panels/SnapshotSelector';
import { selectedRecordRef } from '../topology/record';
import { CompletionPanel } from '../completion/CompletionPanel';
import { ProblemBoard } from '../exploration/ProblemBoard';
import { InputPanel } from '../exploration/InputPanel';
import { commandStatusMessage, includeRequestedTask, selectAuthorizedTaskId, taskStatusLabel } from './workbenchState';
import styles from './firstUseWorkbench.module.css';

const CREATE_KEY = 'wuji.first-use.v2.create-key';

const scenarioLabels: Readonly<Record<TaskCreate['scenario'], string>> = {
  web_single: 'Web 单点',
  ctf: 'CTF（当前未发布）',
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
  readonly name: string;
  readonly entryPoint: string;
  readonly goal: string;
  readonly criteria: string;
  readonly expiresAt: string;
  readonly modelRef: string;
  readonly runtimeRef: string;
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
    name: '',
    entryPoint: '',
    goal: '',
    criteria: '',
    expiresAt: '',
    modelRef: options?.model_profiles.find((item) => item.real_model_allowed)?.ref ?? '',
    runtimeRef: options?.runtime_profiles.find((item) => item.real_model_allowed)?.ref ?? '',
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
    scenario: 'web_single',
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
  if (label === '已暂停') return 'orange';
  if (label === '待核对' || label.includes('受理')) return 'gold';
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

interface EvidencePreviewProps {
  readonly taskId: string;
  readonly snapshotId: string | null;
  readonly ref: KnowledgeRef | null;
}

function EvidencePreview({ taskId, snapshotId, ref }: EvidencePreviewProps) {
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [material, setMaterial] = useState<ModelMaterialV2 | null>(null);
  const [artifact, setArtifact] = useState<{ id: string; version: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const recordKey = ref && snapshotId ? `${taskId}:${snapshotId}:${ref.entity_type}:${ref.id}:${ref.revision}` : '';

  useEffect(() => {
    if (!ref || !snapshotId) {
      setRecord(null);
      setMaterial(null);
      setArtifact(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setRecord(null);
    setMaterial(null);
    setArtifact(ref.entity_type === 'artifact' ? { id: ref.id, version: ref.revision } : null);
    setError(null);
    void readRecordView(taskId, ref, snapshotId, controller.signal).then((view) => {
      if (!controller.signal.aborted) {
        const next = view.record as unknown as Record<string, unknown>;
        setRecord(next);
        if (ref.entity_type !== 'artifact') {
          const refs = next.artifact_refs;
          const first = Array.isArray(refs) ? refs.find((item): item is { id: string; version: string } => typeof item === 'object' && item !== null && typeof (item as { id?: unknown }).id === 'string' && typeof (item as { version?: unknown }).version === 'string') : undefined;
          if (first) setArtifact({ id: first.id, version: first.version });
        }
      }
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    });
    return () => controller.abort();
  }, [recordKey]);

  useEffect(() => {
    if (!artifact) {
      setMaterial(null);
      return;
    }
    const controller = new AbortController();
    void readArtifactMaterial(taskId, artifact.id, artifact.version, controller.signal).then((next) => {
      if (!controller.signal.aborted) setMaterial(next);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    });
    return () => controller.abort();
  }, [artifact?.id, artifact?.version, taskId]);

  const download = async () => {
    if (!artifact) return;
    setDownloading(true);
    try {
      const blob = await downloadArtifact(artifact.id, artifact.version, new AbortController().signal);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `artifact-${artifact.id}-${artifact.version}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setDownloading(false);
    }
  };

  if (!ref || !snapshotId) {
    return <section className={styles.evidence} aria-label="证据预览"><h2>证据与材料</h2><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="从拓扑或记录中选择一个节点" /></section>;
  }
  const httpStatus = record?.http_status ?? record?.upstream_status ?? record?.status_code;
  return (
    <section className={styles.evidence} aria-label="证据预览">
      <div className={styles.readinessHeader}><h2>证据与材料</h2><Tag>{ref.entity_type} · {ref.id}@{ref.revision}</Tag></div>
      {error && <Alert showIcon type="warning" title="证据读取受限" description={error} />}
      {record && (
        <dl className={styles.evidenceMeta}>
          <div><dt>实际 HTTP 状态</dt><dd>{typeof httpStatus === 'number' || typeof httpStatus === 'string' ? String(httpStatus) : '当前记录未提供；不补写 200'}</dd></div>
          <div><dt>证据来源</dt><dd>{typeof record.evidence_origin === 'string' ? record.evidence_origin : '受权固定记录'}</dd></div>
          <div><dt>采集完整度</dt><dd>{typeof record.completeness === 'string' ? record.completeness : '未在当前记录提供'}</dd></div>
          <div><dt>当前修订</dt><dd>{ref.id}@{ref.revision}</dd></div>
        </dl>
      )}
      {artifact && <div className={styles.statusStrip}><code>Artifact {artifact.id}@{artifact.version}</code><Button size="small" icon={<DownloadOutlined />} loading={downloading} onClick={() => void download()}>下载原始 Artifact</Button><Typography.Text type="secondary">使用受权 content 路径，不在页面执行 HTML。</Typography.Text></div>}
      {material?.status === 'delivered' && material.source && material.representation ? (
        <>
          <dl className={styles.evidenceMeta}>
            <div><dt>源 Artifact 摘要</dt><dd>{material.source.artifact_sha256}</dd></div>
            <div><dt>源媒体类型 / 完整度</dt><dd>{material.source.media_type} / {material.source.completeness}</dd></div>
            <div><dt>表示摘要</dt><dd>{material.representation.representation_sha256}</dd></div>
            <div><dt>表示限制</dt><dd>{material.representation.byte_length} bytes · {material.representation.truncated ? '已截断' : '完整'} · {material.representation.redaction_applied ? '已脱敏' : '未脱敏'}</dd></div>
          </dl>
          <pre className={styles.material} data-testid="material-body">{material.representation.text}</pre>
          <Typography.Text type="secondary">以上是安全的纯文本表示；HTML/脚本不会被注入 DOM 或加载。</Typography.Text>
        </>
      ) : material?.status === 'omitted' ? (
        <div className={styles.omitted} data-testid="material-omitted">材料未交付：{material.omission_reason ?? '平台未提供原因'}。没有伪造正文。</div>
      ) : artifact && !error ? <Spin description="正在读取已封存材料" /> : null}
    </section>
  );
}

interface TaskWorkspaceProps {
  readonly taskId: string;
  readonly session: WorkbenchSession;
  readonly onSessionExpired: () => void;
  readonly onTaskUpdated: (task: TaskView) => void;
}

function TaskWorkspace({ taskId, session, onSessionExpired, onTaskUpdated }: TaskWorkspaceProps) {
  const [task, setTask] = useState<TaskView | null>(null);
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [launch, setLaunch] = useState<LaunchView | null>(null);
  const [selection, setSelection] = useState<TopologySelection | null>(null);
  const [snapshot, setSnapshot] = useState<TopologySnapshotInput | null>(null);
  const [problemSnapshotId, setProblemSnapshotId] = useState<string | null>(null);
  const [viewChoice, setViewChoice] = useState<ViewChoice>({ mode: 'live', snapshotId: null });
  const [notice, setNotice] = useState<CommandNotice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const generation = useRef(0);
  const active = useRef<AbortController | null>(null);
  const commandKeys = useRef(new Map<string, string>());

  useEffect(() => {
    const currentGeneration = generation.current + 1;
    generation.current = currentGeneration;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    setTask(null);
    setReadiness(null);
    setLaunch(null);
    setSelection(null);
    setSnapshot(null);
    setProblemSnapshotId(null);
    setViewChoice({ mode: 'live', snapshotId: null });
    void Promise.all([readTask(taskId, controller.signal), readReadiness(taskId, controller.signal), readLaunch(taskId, controller.signal)]).then(([nextTask, nextReadiness, nextLaunch]) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setTask(nextTask);
      onTaskUpdated(nextTask);
      setReadiness(nextReadiness);
      setLaunch(nextLaunch);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(errorMessage(reason));
    }).finally(() => {
      if (!controller.signal.aborted && generation.current === currentGeneration) setLoading(false);
    });
    return () => controller.abort();
  }, [taskId, refresh, onSessionExpired, onTaskUpdated]);

  const selectedRef = useMemo(
    () => selection?.mode === 'explicit_revision' ? selection.ref : selectedRecordRef(snapshot, selection),
    [selection, snapshot],
  );
  const handleProblemSnapshot = useCallback((next: string) => setProblemSnapshotId(next), []);
  const handleProblemSelect = useCallback((ref: KnowledgeRef) => setSelection({ mode: 'explicit_revision', ref }), []);
  const label = taskStatusLabel(task, launch);
  const allowed = task?.allowed_actions ?? launch?.allowed_actions ?? [];

  const refreshCurrent = () => setRefresh((value) => value + 1);

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

  if (loading && !task) return <div className={styles.detailBody}><div aria-live="polite"><Spin description="正在读取受权 Task、就绪诊断和启动状态" /></div></div>;
  if (error && !task) return <div className={styles.detailBody}><Alert showIcon type="error" title="Task 读取失败" description={error} action={<Button onClick={refreshCurrent}>重新读取</Button>} /></div>;
  if (!task) return <div className={styles.detailBody}><Empty description="当前 Task 不可访问" /></div>;

  return (
    <div className={styles.detailBody}>
      {error && <Alert showIcon type="warning" title="读取未完成" description={error} action={<Button onClick={refreshCurrent}>重新读取</Button>} />}
      {notice && <Alert showIcon type={notice.kind === 'error' ? 'error' : notice.kind === 'unknown' ? 'warning' : 'info'} title={commandStatusMessage(notice.command, label, notice.message)} description={<code>Idempotency-Key {notice.key} · 原操作不会自动换键重发</code>} action={<Button onClick={refreshCurrent}>查看原操作结果</Button>} />}
      <div className={styles.statusStrip} data-testid="task-status">
        <Tag color={statusColor(label)}>{label}</Tag>
        <code>{task.name} · {task.task_id} · version {task.version}</code>
        {task.result_outcome && <Tag>{task.result_outcome}</Tag>}
      </div>
      <div className={styles.controlBar} aria-label="Task 控制">
        {allowed.includes('start') && <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => void submitCommand('start')} data-testid="task-start">显式启动</Button>}
        {allowed.includes('pause') && <Button icon={<PauseOutlined />} onClick={() => void submitCommand('pause')} data-testid="task-pause">暂停 Task</Button>}
        {allowed.includes('resume') && <Button icon={<ReloadOutlined />} onClick={() => void submitCommand('resume')} data-testid="task-resume">恢复 Task</Button>}
        {allowed.includes('cancel') && <Button danger icon={<StopOutlined />} onClick={() => void submitCommand('cancel')} data-testid="task-cancel">取消 Task</Button>}
        <Button icon={<ReloadOutlined />} onClick={refreshCurrent}>刷新状态</Button>
      </div>
      <section className={styles.topology} aria-label="探索">
        <div className={styles.readinessHeader}><h2>问题中心黑板</h2><Typography.Text type="secondary">问题、认识和详情来自同一固定快照；缺失历史明确显示“未记录”。</Typography.Text></div>
        <SnapshotSelector taskId={task.task_id} value={viewChoice} onChange={(next) => { setSelection(null); setSnapshot(null); setProblemSnapshotId(null); setViewChoice(next); }} />
        <ProblemBoard
          key={`${task.task_id}:${viewChoice.mode}:${viewChoice.snapshotId ?? 'live'}:${refresh}`}
          taskId={task.task_id}
          mode={viewChoice.mode}
          snapshotId={viewChoice.snapshotId}
          refreshKey={refresh}
          onSnapshotChange={handleProblemSnapshot}
          onSelect={handleProblemSelect}
          onSessionExpired={onSessionExpired}
        />
        {viewChoice.mode === 'live' && <InputPanel taskId={task.task_id} csrfToken={session.csrf_token} refreshKey={refresh} onChanged={refreshCurrent} onSessionExpired={onSessionExpired} />}
        <div className={styles.detail}><RecordPanel taskId={task.task_id} snapshotId={problemSnapshotId} ref={selectedRef} /></div>
      </section>
      <section className={styles.launch} aria-label="启动进度" data-testid="launch-status">
        <div className={styles.launchLine}><strong>启动进度</strong><Tag>{launch?.phase ?? 'not_requested'} · {launch?.phase_status ?? 'not_requested'}</Tag><code>{launch?.reason_code ?? '无阻断原因'}</code></div>
        <div className={styles.launchLine}><span>真实 attempt</span><code>{launch?.runtime_attempt ?? '尚未生成'}</code><span>execution epoch</span><code>{launch?.execution_epoch ?? '尚未生成'}</code></div>
        {launch?.phase_status === 'reconciling' && <Typography.Text type="warning">启动或停止结果需要核对，页面不会写入成功状态。</Typography.Text>}
      </section>
      <section className={styles.readiness} aria-label="启动就绪诊断">
        <div className={styles.readinessHeader}><h2>启动就绪诊断</h2><Tag color={readiness?.can_request_start ? 'green' : 'orange'}>{readiness?.can_request_start ? '可受理 start' : '当前阻断'}</Tag></div>
        <Typography.Text type="secondary">只读配置事实；target 的 unknown 仍表示未实测网络，不会被解释为网络通过。</Typography.Text>
        <CheckList checks={readiness?.checks ?? []} />
      </section>
      <details className={styles.technical}>
        <summary>执行与证据（技术视图）</summary>
        <Typography.Text type="secondary">按需展开 Run、证据和实际调用；不会从布局写入领域关系。</Typography.Text>
        {problemSnapshotId ? <TopologyContainer key={`${task.task_id}:${problemSnapshotId}`} taskId={task.task_id} mode="history" snapshotId={problemSnapshotId} selection={selection} onSelect={setSelection} onSnapshotChange={setSnapshot} /> : <Spin description="等待问题快照" />}
        <EvidencePreview taskId={task.task_id} snapshotId={problemSnapshotId} ref={selectedRef} />
      </details>
      {viewChoice.mode === 'live' && <section className={styles.topology} aria-label="结论与完成"><div className={styles.readinessHeader}><h2>结论与完成</h2><Typography.Text type="secondary">工作结果、Goal 判断和实际停止分别核对。</Typography.Text></div><CompletionPanel taskId={task.task_id} onChanged={refreshCurrent} /></section>}
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
      && validDecimal(draft.budget)
      && draft.targetConfirmed
      && draft.materialConfirmed,
  );
  const body = ready && entry && expiry ? createBody(draft, session.project_id, entry, criteria) : null;
  const selectedModel = options?.model_profiles.find((item) => item.ref === draft.modelRef) ?? null;
  const selectedRuntime = options?.runtime_profiles.find((item) => item.ref === draft.runtimeRef) ?? null;

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
      <div className={styles.detailHeader}><div><strong>新建受权 Task</strong><span>创建完成后保持未启动</span></div><Button onClick={onClose}>关闭</Button></div>
      <div className={styles.detailBody}>
        {Boolean(optionsError) && <Alert showIcon type="error" title="目录加载失败" description="无法确认当前身份可用的发布 Profile；不会回落 synthetic 配置。" />}
        {options && options.missing.length > 0 && <Alert showIcon type="warning" title="当前不能创建" description={options.missing.map((item) => `${item.layer}/${item.id}: ${item.message}`).join('；')} />}
        {error && <Alert showIcon type="error" title="创建未完成" description={error} />}
        <div className={styles.form}>
          <div className={styles.formSection}>
            <h2>目标与场景</h2>
            <div className={styles.formGrid}>
              <label className={styles.full}>场景<Select aria-label="任务场景" value="web_single" options={Object.entries(scenarioLabels).map(([value, label]) => ({ value, label, disabled: value !== 'web_single' }))} /></label>
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
              <Checkbox checked={draft.materialConfirmed} onChange={(event) => patch('materialConfirmed', event.target.checked)}>我确认允许本 Task 按已发布政策将获准材料发送给外部 DeepSeek；这与目标访问授权是两项独立确认。</Checkbox>
            </div>
          </div>
          <div className={styles.formSection}>
            <h2>模型与运行配置</h2>
            <div className={styles.formGrid}>
              <label>模型方案<Select aria-label="模型方案" value={draft.modelRef || undefined} options={options?.model_profiles.map((item) => ({ value: item.ref, label: `${item.name} · ${item.revision}${item.real_model_allowed ? ' · DeepSeek／真实模型' : ''}` }))} onChange={(value) => patch('modelRef', value)} placeholder="选择已发布模型" /></label>
              <label>运行配置<Select aria-label="运行配置" value={draft.runtimeRef || undefined} options={options?.runtime_profiles.map((item) => ({ value: item.ref, label: `${item.name} · ${item.revision}` }))} onChange={(value) => patch('runtimeRef', value)} placeholder="选择已发布运行配置" /></label>
            </div>
            {selectedModel && <div className={styles.profileCard}><strong>{selectedModel.name} · {selectedModel.revision}</strong><code>{selectedModel.ref} · digest {selectedModel.digest}</code><div className={styles.profileCapabilities}>{selectedModel.capabilities.map((capability) => <span key={capability}>{capability}</span>)}</div><span>执行将使用所选模型配置的固定版本。</span></div>}
            {selectedRuntime && <div className={styles.profileCard}><strong>{selectedRuntime.name} · {selectedRuntime.revision}</strong><code>{selectedRuntime.ref} · digest {selectedRuntime.digest}</code><div className={styles.profileCapabilities}>{selectedRuntime.capabilities.map((capability) => <span key={capability}>{capability}</span>)}</div><span>运行上限由所选配置版本确定。</span></div>}
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
        <div><div className="eyebrow">FIRST-USE / AUTHORISED WORKBENCH</div><h1>真实任务工作台</h1><p>创建、显式启动、读取就绪诊断和核对结果；浏览器断开不会取消后台 Task。</p></div>
        <div className={styles.identityMeta}><Tag color="blue">{session.identity_mode}</Tag><span>Project</span><code>{session.project_id}</code><span>{session.display_name}</span><Button loading={loggingOut} onClick={() => void logout()}>退出</Button></div>
      </section>
      {Boolean(listError) && <Alert showIcon type="error" title="任务目录读取失败" description={errorMessage(listError)} action={<Button onClick={refreshList}>重试</Button>} />}
      <div className={styles.body}>
        <aside className={styles.directory} aria-label="受权任务目录" data-testid="task-list">
          <div className={styles.directoryHeader}><div><strong>受权任务</strong><span>当前主体 · Project 内</span></div><Button type="primary" onClick={() => setCreateOpen(true)} data-testid="new-task">新建任务</Button></div>
          {loading && tasks.length === 0 ? <div className={styles.directoryEmpty}><Spin description="正在读取 Task 目录" /></div> : tasks.length === 0 ? <div className={styles.directoryEmpty}><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有可访问的 Task" /><Button type="primary" onClick={() => setCreateOpen(true)}>创建首个 Task</Button></div> : <div className={styles.taskList}>{tasks.map((task) => { const label = taskStatusLabel(task, null); return <button className={`${styles.taskItem} ${selectedTaskId === task.task_id ? styles.taskItemActive : ''}`} type="button" key={task.task_id} onClick={() => selectTask(task.task_id)}><strong>{task.name}</strong><code>{task.task_id}</code><span className={styles.taskItemMeta}><Tag color={statusColor(label)}>{label}</Tag><span>{task.scenario}</span></span></button>; })}</div>}
          <div className={styles.directoryFooter}><Button size="small" icon={<ReloadOutlined />} onClick={refreshList}>刷新目录</Button>{cursor && <Button size="small" onClick={() => setTaskCursor(cursor)}>加载更多</Button>}</div>
        </aside>
        <main className={styles.detail} aria-label="Task 详情">
          {createOpen ? <TaskCreatePanel session={session} options={options} optionsError={optionsError} onCreated={openCreated} onClose={() => setCreateOpen(false)} onSessionExpired={onSessionExpired} /> : selectedTask ? <><div className={styles.detailHeader}><div><strong>{selectedTask.name}</strong><span>Task 详情 · 任务切换不会复用旧请求结果</span></div><code>{selectedTask.task_id}</code></div><TaskWorkspace key={selectedTask.task_id} taskId={selectedTask.task_id} session={session} onSessionExpired={onSessionExpired} onTaskUpdated={updateTask} /></> : <div className={styles.detailBody}><Empty description="从左侧选择一个 Task，或新建首个 Task" /></div>}
        </main>
      </div>
    </div>
  );
}

export { artifactContentPath, materialPath };
