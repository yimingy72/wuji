import { ExecutionObservation } from './features/task-execution/ExecutionObservation';
import { AuthorizationSummary } from './features/task-creation/AuthorizationSummary';
import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeftOutlined,
  ClockCircleOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { Alert, Button, Descriptions, Empty, Modal, Spin, Tag } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  ApiRequestError,
  StaleContextError,
  isApiError,
  type CommandReceipt,
  type Session,
  type Task,
  type TaskEvent,
  type TaskSnapshot,
} from './api';
import {
  beginCommand,
  clearPendingCommand,
  getFrozenCommand,
  markPendingListInspected,
  PendingStorageError,
  usePendingCommand,
  type FrozenCommand,
  type PendingCommand,
} from './pendingCommand';
import { PrivatePage } from './pages';
import {
  findCommand,
  leaveUnavailableProject,
  projectQueryOptions,
  readTaskEvents,
  readTaskSnapshot,
  refreshSession,
  refreshTaskLists,
  submitCreateTask,
  submitTaskControl,
  taskPageQueryOptions,
} from './queries';
import { isTaskId } from './routing';
import { useIdentitySnapshot } from './state';
import styles from './workbench.module.css';

const stateLabels: Record<Task['state'], string> = {
  queued: '排队中',
  ready: '待启动',
  provisioning: '准备中',
  running: '运行中',
  completing: '收尾中',
  completed: '已完成',
  cancelling: '取消中',
  cancelled: '已取消',
  reconciling: '核对中',
};

const terminalStates = new Set<Task['state']>(['completed', 'cancelled']);

function taskStateTag(task: Task) {
  const color = task.state === 'cancelled'
    ? 'default'
    : task.state === 'completed'
        ? 'success'
        : 'processing';
  return <Tag color={color}>{stateLabels[task.state]}</Tag>;
}

function commandErrorCopy(error: unknown): { title: string; body: string } {
  if (error instanceof PendingStorageError) {
    return { title: '无法开始提交', body: '浏览器未能保存提交标记，请允许当前标签页使用会话存储后重试。' };
  }
  if (error instanceof ApiRequestError) {
    if (error.contractFailure) return { title: '响应无法确认', body: '平台响应无法识别，请先核对提交结果。' };
    if (error.status === 403) return { title: '当前操作无权限', body: '项目权限已更新，请重新读取后再操作。' };
    if (error.status === 409) return { title: '任务状态已更新', body: error.message };
    if (error.status === 404) return { title: '内容不可访问', body: error.message };
    if (error.status === 422) return { title: '提交内容无效', body: error.message };
    if (error.status === 0 || error.status >= 500) return { title: '提交结果待确认', body: '连接未完成，请使用原提交标记核对结果。' };
  }
  return { title: '请求未完成', body: '请重新读取当前状态后再试。' };
}

export function isExplicitCommandRejection(error: unknown) {
  return error instanceof ApiRequestError
    && !error.contractFailure
    && error.status >= 400
    && error.status < 500;
}

function assertReceipt(pending: PendingCommand, receipt: CommandReceipt): CommandReceipt {
  if (
    receipt.project_id !== pending.projectId
    || receipt.idempotency_key !== pending.idempotencyKey
    || receipt.kind !== pending.kind
    || (pending.kind !== 'create' && pending.resourceId !== null && receipt.task_id !== pending.resourceId)
  ) {
    throw new ApiRequestError({
      status: 200,
      code: 'INTERNAL_ERROR',
      message: '回执与当前提交不一致',
      contractFailure: true,
    });
  }
  return receipt;
}

export async function sendFrozenCommand(
  session: Session,
  pending: PendingCommand,
  frozen: FrozenCommand,
  signal: AbortSignal,
): Promise<CommandReceipt> {
  if (pending.kind === 'create' && frozen.kind === 'create') {
    return assertReceipt(pending, await submitCreateTask(
      session, pending.projectId, frozen.request, pending.idempotencyKey, signal,
    ));
  }
  if (pending.kind !== 'create' && frozen.kind === pending.kind && pending.resourceId) {
    return assertReceipt(pending, await submitTaskControl(
      session,
      pending.projectId,
      pending.resourceId,
      frozen.request,
      pending.idempotencyKey,
      signal,
    ));
  }
  throw new ApiRequestError({
    status: 0,
    code: 'INTERNAL_ERROR',
    message: '原提交内容已不可用',
    contractFailure: true,
  });
}

export function PendingCommandNotice({
  session,
  projectId,
  onResolved,
  listPage = false,
}: {
  session: Session;
  projectId: string;
  onResolved?: (receipt: CommandReceipt) => void;
  listPage?: boolean;
}) {
  const navigate = useNavigate();
  const pending = usePendingCommand(projectId, session.user_id);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [lookupMissing, setLookupMissing] = useState(false);
  const [abandonOpen, setAbandonOpen] = useState(false);
  const active = useRef<AbortController | null>(null);

  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => {
    if (listPage && pending) markPendingListInspected(pending);
  }, [listPage, pending]);
  if (!pending) return null;

  const accept = async (receipt: CommandReceipt, signal: AbortSignal) => {
    await readTaskSnapshot(session, projectId, receipt.task_id, signal);
    clearPendingCommand(pending);
    setError(null);
    setLookupMissing(false);
    onResolved?.(receipt);
    navigate(`/projects/${projectId}/tasks/${receipt.task_id}`);
  };

  const reconcile = async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setChecking(true);
    setError(null);
    setLookupMissing(false);
    try {
      await accept(assertReceipt(pending, await findCommand(
        session, projectId, pending.idempotencyKey, controller.signal,
      )), controller.signal);
    } catch (nextError) {
      if (controller.signal.aborted || nextError instanceof StaleContextError) return;
      if (isApiError(nextError, 404)) setLookupMissing(true);
      setError(nextError);
    } finally {
      if (active.current === controller) {
        active.current = null;
        setChecking(false);
      }
    }
  };

  const retryOriginal = async () => {
    const frozen = getFrozenCommand(pending);
    if (!frozen) return;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setChecking(true);
    setError(null);
    setLookupMissing(false);
    let accepted = false;
    try {
      const receipt = await sendFrozenCommand(session, pending, frozen, controller.signal);
      accepted = true;
      await accept(receipt, controller.signal);
    } catch (nextError) {
      if (controller.signal.aborted || nextError instanceof StaleContextError) return;
      if (!accepted && isExplicitCommandRejection(nextError)) clearPendingCommand(pending);
      setError(nextError);
    } finally {
      if (active.current === controller) {
        active.current = null;
        setChecking(false);
      }
    }
  };

  const copy = lookupMissing
    ? { title: '提交结果待确认', body: '当前未查到回执；这不代表服务端没有接受提交。请继续保留标记，或在同页使用原提交重试。' }
    : error ? commandErrorCopy(error) : null;
  const canRetryOriginal = getFrozenCommand(pending) !== null;
  return (
    <>
      <Alert
        className={styles.pendingNotice}
        role="status"
        type={error ? 'warning' : 'info'}
        showIcon
        title={copy?.title ?? '提交结果待确认'}
        description={(
          <div className={styles.pendingBody}>
            <p>{copy?.body ?? `正在核对${pending.kind === 'create' ? '任务创建' : pending.kind === 'start' ? '任务启动' : '任务取消'}结果。`}</p>
            <code>提交标记 {pending.idempotencyKey}</code>
            <div className={styles.inlineActions}>
              <Button type="primary" loading={checking} onClick={() => void reconcile()}>核对提交结果</Button>
              {canRetryOriginal && (
                <Button disabled={checking} onClick={() => void retryOriginal()}>使用原提交重试</Button>
              )}
              <Button disabled={checking} onClick={() => navigate(`/projects/${projectId}/tasks`)}>查看任务列表</Button>
              {pending.listInspectedAt && (
                <Button danger disabled={checking} onClick={() => setAbandonOpen(true)}>放弃本次核对</Button>
              )}
            </div>
          </div>
        )}
      />
      <Modal
        open={abandonOpen}
        title="确认放弃核对"
        okText="确认放弃核对"
        cancelText="继续保留"
        okButtonProps={{ danger: true }}
        onCancel={() => setAbandonOpen(false)}
        onOk={() => {
          clearPendingCommand(pending);
          setAbandonOpen(false);
          setError(null);
        }}
      >
        <p>这里只移除当前标签页的提交标记，不会取消服务端可能已接受的任务。</p>
      </Modal>
    </>
  );
}

function TasksList({ session, projectId, canCreate }: { session: Session; projectId: string; canCreate: boolean }) {
  const navigate = useNavigate();
  const pending = usePendingCommand(projectId, session.user_id);
  const [search, setSearch] = useSearchParams();
  const cursor = search.get('cursor');
  const [previous, setPrevious] = useState<(string | null)[]>([]);
  const [cursorVersion, setCursorVersion] = useState(session.permissions_version);
  const effectiveCursor = cursorVersion === session.permissions_version ? cursor : null;
  const page = useQuery(taskPageQueryOptions(session, projectId, effectiveCursor));

  useEffect(() => {
    if (cursorVersion === session.permissions_version) return;
    setSearch({}, { replace: true });
    setPrevious([]);
    setCursorVersion(session.permissions_version);
  }, [cursorVersion, session.permissions_version, setSearch]);

  useEffect(() => {
    if (isApiError(page.error, 410) && effectiveCursor !== null) {
      setSearch({}, { replace: true });
      setPrevious([]);
      setCursorVersion(session.permissions_version);
      void refreshSession().catch(() => undefined);
    }
    if (isApiError(page.error, 404)) navigate(`/projects/${projectId}`, { replace: true });
  }, [effectiveCursor, navigate, page.error, projectId, session.permissions_version, setSearch]);

  return (
    <section className={styles.taskPage} aria-labelledby="tasks-title">
      <Link className={styles.backLink} to={`/projects/${projectId}`}>
        <ArrowLeftOutlined aria-hidden="true" />返回项目工作区
      </Link>
      <header className={styles.workspaceHeading}>
        <div><span className={styles.eyebrow}>TASKS</span><h1 id="tasks-title">任务列表</h1></div>
        {canCreate && <Button type="primary" disabled={pending !== null} onClick={() => navigate(`/projects/${projectId}/tasks/new`)}>新建任务</Button>}
      </header>
      <Link to={`/projects/${projectId}/drafts`}>个人草稿</Link>
      <PendingCommandNotice session={session} projectId={projectId} listPage />
      <div className={styles.projectPanel}>
        <div className={styles.panelHeader}><h2>项目任务</h2><span>按创建时间排列</span></div>
        {page.isPending ? (
          <div className={styles.panelStatus} role="status"><Spin description="正在读取任务" /></div>
        ) : page.error && !isApiError(page.error, 410) ? (
          <div className={styles.panelStatus}>
            <Alert type="error" showIcon title="任务列表读取失败" description="请求未完成，请重试。" action={<Button onClick={() => void page.refetch()}>重试</Button>} />
          </div>
        ) : page.data?.items.length === 0 ? (
          <div className={styles.panelStatus}><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前项目暂无任务" /></div>
        ) : (
          <nav aria-label="任务列表" className={styles.taskList}>
            {page.data?.items.map((task) => (
              <Link
                key={task.id}
                className={styles.taskRow}
                to={`/projects/${projectId}/tasks/${task.id}${effectiveCursor ? `?list_cursor=${encodeURIComponent(effectiveCursor)}` : ''}`}
              >
                <span className={styles.taskIdentity}><strong>{task.name}</strong><code>{task.id}</code></span>
                <span className={styles.taskTarget}><span>目标</span><code>{task.target_url}</code></span>
                {taskStateTag(task)}
                <time dateTime={task.created_at}>{new Date(task.created_at).toLocaleString('zh-CN')}</time>
                <RightOutlined aria-hidden="true" />
              </Link>
            ))}
          </nav>
        )}
        <footer className={styles.pagination} aria-label="任务分页">
          <span>{effectiveCursor === null ? '当前为起始批次' : '当前为后续批次'}</span>
          <div>
            <Button disabled={previous.length === 0} onClick={() => {
              const prior = previous.at(-1);
              if (prior === undefined) return;
              setPrevious((items) => items.slice(0, -1));
              setSearch(prior ? { cursor: prior } : {});
            }}>上一页</Button>
            <Button disabled={!page.data?.next_cursor} onClick={() => {
              if (!page.data?.next_cursor) return;
              setPrevious((items) => [...items, effectiveCursor]);
              setSearch({ cursor: page.data.next_cursor });
            }}>下一页</Button>
          </div>
        </footer>
      </div>
    </section>
  );
}

function TaskListContent({ session, projectId }: { session: Session; projectId: string }) {
  const navigate = useNavigate();
  const project = useQuery(projectQueryOptions(session, projectId));
  useEffect(() => {
    if (isApiError(project.error, 404)) {
      leaveUnavailableProject(projectId);
      navigate('/projects?notice=project-unavailable', { replace: true });
    }
  }, [navigate, project.error, projectId]);
  if (project.isPending) return <div className={styles.centerStatus}><Spin description="正在读取项目" /></div>;
  if (!project.data) return <Alert type="error" showIcon title="项目读取失败" action={<Button onClick={() => void project.refetch()}>重试</Button>} />;
  if (!project.data.permissions.includes('task.read')) {
    return <Alert type="warning" showIcon title="当前身份不能查看任务" action={<Button onClick={() => navigate(`/projects/${projectId}`)}>返回项目工作区</Button>} />;
  }
  return <TasksList session={session} projectId={projectId} canCreate={project.data.permissions.includes('task.create')} />;
}

export function TasksPage() {
  const { projectId = '' } = useParams();
  return <PrivatePage>{(session) => <TaskListContent session={session} projectId={projectId} />}</PrivatePage>;
}

function TaskHistory({ events }: { events: readonly TaskEvent[] }) {
  return (
    <section className={styles.historyPanel} aria-labelledby="task-history-title">
      <header><div><h2 id="task-history-title">状态变更记录</h2><p>任务创建与状态变更</p></div></header>
      {events.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无状态变更记录" />
      ) : (
        <ol>
          {events.map((event) => (
            <li key={event.event_id}>
              <ClockCircleOutlined aria-hidden="true" />
              <div><strong>{event.summary}</strong><time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString('zh-CN')}</time></div>
              <code>版本 {event.aggregate_version}</code>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function TaskDetail({ session, projectId, taskId, canControl, listCursor }: { session: Session; projectId: string; taskId: string; canControl: boolean; listCursor: string | null }) {
  const navigate = useNavigate();
  const listPath = `/projects/${projectId}/tasks${listCursor ? `?cursor=${encodeURIComponent(listCursor)}` : ''}`;
  const pending = usePendingCommand(projectId, session.user_id);
  const [snapshot, setSnapshot] = useState<TaskSnapshot | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [pollError, setPollError] = useState<unknown>(null);
  const [manualRetry, setManualRetry] = useState(false);
  const [syncRevision, setSyncRevision] = useState(0);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [commandBusy, setCommandBusy] = useState(false);
  const [commandError, setCommandError] = useState<unknown>(null);
  const latestVersion = useRef(0);
  const commandController = useRef<AbortController | null>(null);

  useEffect(() => () => commandController.current?.abort(), []);

  useEffect(() => {
    let stopped = false;
    let timer: number | null = null;
    let controller: AbortController | null = null;
    let cursor: string | null = null;
    let currentSnapshot: TaskSnapshot | null = null;
    let transientFailures = 0;
    let paused = false;

    const acceptSnapshot = (next: TaskSnapshot) => {
      if (stopped) return;
      if (next.task.version < latestVersion.current) return;
      latestVersion.current = next.task.version;
      currentSnapshot = next;
      setSnapshot(next);
    };

    const acceptEvents = (incoming: TaskEvent[]) => {
      if (stopped || incoming.length === 0) return;
      setEvents((current) => {
        const byId = new Map(current.map((event) => [event.event_id, event]));
        for (const event of incoming) byId.set(event.event_id, event);
        return [...byId.values()].sort((left, right) => left.occurred_at.localeCompare(right.occurred_at));
      });
    };

    const freshSnapshot = async (signal: AbortSignal) => {
      const next = await readTaskSnapshot(session, projectId, taskId, signal);
      if (stopped || signal.aborted) throw new DOMException('Request aborted', 'AbortError');
      acceptSnapshot(next);
      return next;
    };

    const readPages = async (after: string | null, signal: AbortSignal) => {
      let position = after;
      const incoming: TaskEvent[] = [];
      for (let pageNumber = 0; pageNumber < 5; pageNumber += 1) {
        const page = await readTaskEvents(session, projectId, taskId, position, signal);
        incoming.push(...page.items);
        position = page.next_cursor;
        if (!page.has_more) break;
      }
      return { incoming, position, maxVersion: Math.max(0, ...incoming.map((event) => event.aggregate_version)) };
    };

    const stopTimer = () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
    };

    const schedule = (delay: number) => {
      stopTimer();
      if (stopped || document.hidden || paused || currentSnapshot && terminalStates.has(currentSnapshot.task.state)) return;
      timer = window.setTimeout(() => void cycle(), delay);
    };

    const handleFailure = async (error: unknown) => {
      if (stopped || error instanceof StaleContextError) return;
      if (isApiError(error, 410)) {
        try {
          const resyncController = new AbortController();
          controller = resyncController;
          const next = await freshSnapshot(resyncController.signal);
          const history = await readPages(null, resyncController.signal);
          if (history.maxVersion > next.task.version) await freshSnapshot(resyncController.signal);
          if (stopped || controller !== resyncController) return;
          acceptEvents(history.incoming);
          cursor = next.event_cursor;
          transientFailures = 0;
          paused = false;
          setPollError(null);
          schedule(5_000);
        } catch (resyncError) {
          await handleFailure(resyncError);
        }
        return;
      }
      if (isApiError(error, 404)) {
        setLoadError(error);
        setSnapshot(null);
        stopTimer();
        return;
      }
      const transient = error instanceof ApiRequestError && (error.status === 0 || error.status >= 500);
      setPollError(error);
      if (!transient) {
        paused = true;
        setManualRetry(true);
        return;
      }
      transientFailures += 1;
      if (transientFailures >= 3) {
        paused = true;
        setManualRetry(true);
        return;
      }
      schedule(transientFailures === 1 ? 10_000 : 20_000);
    };

    const cycle = async () => {
      if (stopped || document.hidden) return;
      controller?.abort();
      const requestController = new AbortController();
      controller = requestController;
      try {
        const pageResult = await readPages(cursor, requestController.signal);
        if (stopped || controller !== requestController) return;
        if (pageResult.maxVersion > latestVersion.current) await freshSnapshot(requestController.signal);
        if (stopped || controller !== requestController) return;
        acceptEvents(pageResult.incoming);
        cursor = pageResult.position;
        transientFailures = 0;
        paused = false;
        setPollError(null);
        schedule(5_000);
      } catch (error) {
        if (!requestController.signal.aborted && controller === requestController) await handleFailure(error);
      }
    };

    const initialize = async () => {
      setLoading(true);
      setLoadError(null);
      setPollError(null);
      setManualRetry(false);
      paused = false;
      const initialController = new AbortController();
      controller = initialController;
      try {
        const initial = await freshSnapshot(initialController.signal);
        const history = await readPages(null, initialController.signal);
        if (history.maxVersion > initial.task.version) await freshSnapshot(initialController.signal);
        if (stopped || controller !== initialController) return;
        acceptEvents(history.incoming);
        cursor = initial.event_cursor;
        transientFailures = 0;
        schedule(5_000);
      } catch (error) {
        if (!initialController.signal.aborted && controller === initialController && !(error instanceof StaleContextError)) setLoadError(error);
      } finally {
        if (!stopped) setLoading(false);
      }
    };

    const onVisibility = () => {
      if (document.hidden) {
        stopTimer();
        controller?.abort();
        return;
      }
      const visibleController = new AbortController();
      controller = visibleController;
      void freshSnapshot(visibleController.signal).then(() => {
        if (stopped || controller !== visibleController) return;
        transientFailures = 0;
        paused = false;
        setPollError(null);
        setManualRetry(false);
        void cycle();
      }).catch((error: unknown) => {
        if (!visibleController.signal.aborted && controller === visibleController) void handleFailure(error);
      });
    };

    void initialize();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stopped = true;
      stopTimer();
      controller?.abort();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [projectId, session, syncRevision, taskId]);

  const issueControl = async (action: 'start' | 'cancel') => {
    if (!snapshot) return;
    setCancelOpen(false);
    setCommandBusy(true);
    setCommandError(null);
    let command: PendingCommand;
    try {
      command = beginCommand(session.user_id, projectId, action, taskId, {
        kind: action, request: { action, expected_version: snapshot.task.version },
      });
    } catch (error) {
      setCommandBusy(false);
      setCommandError(error);
      return;
    }
    const frozen = getFrozenCommand(command);
    if (!frozen) return;
    commandController.current?.abort();
    const controller = new AbortController();
    commandController.current = controller;
    let accepted = false;
    try {
      const receipt = await sendFrozenCommand(session, command, frozen, controller.signal);
      accepted = true;
      await readTaskSnapshot(session, projectId, receipt.task_id, controller.signal);
      clearPendingCommand(command);
      await refreshTaskLists(projectId);
      setSyncRevision((value) => value + 1);
    } catch (error) {
      if (!accepted && isExplicitCommandRejection(error)) clearPendingCommand(command);
      if (!(error instanceof StaleContextError)) setCommandError(error);
    } finally {
      if (commandController.current === controller) commandController.current = null;
      setCommandBusy(false);
    }
  };

  if (loading) return <div className={styles.centerStatus}><Spin description="正在读取任务" /></div>;
  if (loadError || !snapshot) {
    return (
      <section className={styles.routeError}>
        <Alert type="error" showIcon title={isApiError(loadError, 404) ? '任务不可访问' : '任务读取失败'} description="请返回任务列表或重试。" />
        <div className={styles.inlineActions}>
          <Button onClick={() => navigate(listPath)}>返回任务列表</Button>
          {!isApiError(loadError, 404) && <Button type="primary" onClick={() => setSyncRevision((value) => value + 1)}>重试</Button>}
        </div>
      </section>
    );
  }

  const task = snapshot.task;
  const canCancel = canControl && task.allowed_actions.includes('cancel') && pending === null;
  const commandCopy = commandError ? commandErrorCopy(commandError) : null;
  return (
    <section className={styles.taskPage} aria-labelledby="task-detail-title">
      <Link className={styles.backLink} to={listPath}><ArrowLeftOutlined aria-hidden="true" />返回任务列表</Link>
      <header className={styles.workspaceHeading}>
        <div><span className={styles.eyebrow}>TASK DETAIL</span><h1 id="task-detail-title">{task.name}</h1><p>任务 {task.id}</p></div>
        <div className={styles.inlineActions}>{canControl && 'creation_config' in task && task.allowed_actions.includes('start') && <Button type="primary" loading={commandBusy} disabled={Boolean(pending)} onClick={() => void issueControl('start')}>启动任务</Button>}{canCancel && <Button danger loading={commandBusy} onClick={() => setCancelOpen(true)}>取消任务</Button>}</div>
      </header>
      <PendingCommandNotice session={session} projectId={projectId} onResolved={() => setSyncRevision((value) => value + 1)} />
      {commandCopy && <Alert className={styles.commandNotice} type="error" showIcon title={commandCopy.title} description={commandCopy.body} />}
      {pollError !== null && (
        <Alert
          className={styles.commandNotice}
          type="warning"
          showIcon
          title={manualRetry ? '自动同步已暂停' : '状态同步暂时中断'}
          description="当前页面保留最后一次确认的任务状态。"
          action={manualRetry ? <Button onClick={() => setSyncRevision((value) => value + 1)}>重新同步</Button> : undefined}
        />
      )}
      {task.state === 'cancelling' && <Alert type="warning" showIcon title="正在取消并核对停止" description="取消请求已接受；进程与工具停止尚待实际回执确认。" />}
      {'creation_config' in task && <ExecutionObservation session={session} projectId={projectId} task={task} />}
      <div className={styles.taskDetailGrid}>
        <section className={styles.taskSummaryPanel} aria-labelledby="task-summary-title">
          <header><h2 id="task-summary-title">任务详情</h2>{taskStateTag(task)}</header>
          <Descriptions
            bordered
            size="small"
            column={{ xs: 1, sm: 1, md: 2 }}
            items={[
              { key: 'target', label: '目标', span: 'filled', children: <code className={styles.breakCode}>{task.target_url}</code> },
              { key: 'scope', label: '批准范围版本', children: <code>{task.scope.version}</code> },
              { key: 'version', label: '任务版本', children: <code>{task.version}</code> },
              { key: 'created', label: '创建时间', children: <time dateTime={task.created_at}>{new Date(task.created_at).toLocaleString('zh-CN')}</time> },
              { key: 'updated', label: '更新时间', children: <time dateTime={task.updated_at}>{new Date(task.updated_at).toLocaleString('zh-CN')}</time> },
              { key: 'reason', label: '停止原因', span: 'filled', children: task.stop_reason ?? '—' },
            ]}
          />
        </section>
        {'creation_config' in task && <section className={styles.taskSummaryPanel} aria-labelledby="creation-snapshot-title">
          <header><h2 id="creation-snapshot-title">创建配置</h2></header>
          <div style={{padding: 20}}>
            <h3>任务目标</h3><p>{task.creation_config.objective}</p>
            <h3>完成条件</h3><ul>{task.creation_config.completion_criteria.map((condition, index) => <li key={index}>{condition}</li>)}</ul>
            <p>模板：{task.creation_config.goal_template ? `${task.creation_config.goal_template.id} · V${task.creation_config.goal_template.version}` : '自定义'}</p>
            {task.creation_config.supplemental_hints && <><h3>补充线索</h3><p>{task.creation_config.supplemental_hints}</p></>}
            <AuthorizationSummary authorization={task.creation_config.authorization} />
            <h3>模型与金额</h3><p>{task.creation_config.model.name} · V{task.creation_config.model.number}</p>
            {task.creation_config.model.config.pricing && <p>输入 {task.creation_config.model.config.pricing.input_per_million} / 输出 {task.creation_config.model.config.pricing.output_per_million} USD / 百万 token · {task.creation_config.model.config.pricing.source}</p>}
            <p>金额上限：{task.creation_config.budget_usd} USD</p>
            {task.start_blockers?.map((reason, index) => <Alert key={index} type="warning" title={reason} />)}
          </div>
        </section>}
        <TaskHistory events={events} />
      </div>
      <Modal
        open={cancelOpen}
        title="确认取消任务"
        okText="确认取消"
        cancelText="返回"
        okButtonProps={{ danger: true }}
        confirmLoading={commandBusy}
        onCancel={() => setCancelOpen(false)}
        onOk={() => void issueControl('cancel')}
      >
        <p>任务取消后不能恢复。取消请求接受后会继续核对执行是否停止。</p>
      </Modal>
    </section>
  );
}

function TaskDetailContent({ session, projectId, taskId, listCursor }: { session: Session; projectId: string; taskId: string; listCursor: string | null }) {
  const identity = useIdentitySnapshot();
  const navigate = useNavigate();
  const project = useQuery(projectQueryOptions(session, projectId));
  useEffect(() => {
    if (isApiError(project.error, 404)) {
      leaveUnavailableProject(projectId);
      navigate('/projects?notice=project-unavailable', { replace: true });
    }
  }, [navigate, project.error, projectId]);
  if (!isTaskId(taskId)) return <Alert type="error" showIcon title="任务路径无效" action={<Button onClick={() => navigate(`/projects/${projectId}/tasks`)}>返回任务列表</Button>} />;
  if (project.isPending) return <div className={styles.centerStatus}><Spin description="正在读取项目" /></div>;
  if (!project.data) return <Alert type="error" showIcon title="项目读取失败" />;
  if (!project.data.permissions.includes('task.read')) return <Alert type="warning" showIcon title="当前身份不能查看任务" />;
  return (
    <TaskDetail
      key={`${identity.identityGeneration}:${identity.projectGeneration}:${projectId}:${taskId}`}
      session={session}
      projectId={projectId}
      taskId={taskId}
      canControl={project.data.permissions.includes('task.control')}
      listCursor={listCursor}
    />
  );
}

export function TaskDetailPage() {
  const { projectId = '', taskId = '' } = useParams();
  const [search] = useSearchParams();
  const listCursor = search.get('list_cursor');
  return <PrivatePage>{(session) => <TaskDetailContent session={session} projectId={projectId} taskId={taskId} listCursor={listCursor} />}</PrivatePage>;
}
