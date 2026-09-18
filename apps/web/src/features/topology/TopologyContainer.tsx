import { apiUrl } from '../../config';
import { Alert, Button, Spin } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  KnowledgeRef,
  LayoutPreference,
  LayoutReceipt,
  NodeEntityType,
  TopologyCommandRequest,
  TopologyExpandRequest,
  TopologySelection,
  TopologySnapshotInput,
  ViewMode,
} from './contracts';
import { TopologyFlowCanvas } from './TopologyFlowCanvas';
import {
  LayoutRequestError,
  layoutPatch,
  layoutViewName,
  readLayoutPreference,
  writeLayoutPreference,
  type LayoutReader,
  type LayoutWriter,
} from './layoutApi';
import { isRevisionString } from './revision';
import {
  applyViewPatches,
  openViewStream,
  type ViewStreamStatus,
} from './stream';
import styles from './topology.module.css';

// X04 binds each emitted revision to its new snapshot and rejects stale
// cursors with an explicit reset. The live subscription is enabled only after
// those guards are in the same release.
export const LIVE_VIEW_ENABLED = true;

const entityTypes = new Set<NodeEntityType>([
  'origin',
  'goal',
  'observation',
  'artifact',
  'claim',
  'intent',
  'work_item',
  'agent_run',
  'verification',
  'completion_review',
  'finding',
  'report',
]);

const snapshotKeys = new Set([
  'view_id',
  'snapshot_id',
  'view_revision',
  'query_digest',
  'access_scope_digest',
  'projection_version',
  'nodes',
  'edges',
  'opaque_cursor',
  'truncated',
  'continuation',
  'allowed_actions',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowed: ReadonlySet<string>): boolean {
  return Object.keys(value).every((key) => allowed.has(key));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value)
    && value.every(isNonEmptyString)
    && new Set(value).size === value.length;
}

function isRef(value: unknown): value is KnowledgeRef {
  if (!isRecord(value) || !hasOnlyKeys(value, new Set(['entity_type', 'id', 'revision']))) {
    return false;
  }
  return entityTypes.has(value.entity_type as NodeEntityType)
    && isNonEmptyString(value.id)
    && isRevisionString(value.revision);
}

function isTopologyNode(value: unknown): boolean {
  if (!isRecord(value) || !hasOnlyKeys(
    value,
    new Set(['id', 'ref', 'display_kind', 'label', 'state', 'allowed_actions']),
  )) {
    return false;
  }
  if (!isNonEmptyString(value.id) || !isRef(value.ref)) return false;
  return value.id === `${value.ref.entity_type}:${value.ref.id}@${value.ref.revision}`
    && isNonEmptyString(value.display_kind)
    && isNonEmptyString(value.label)
    && (value.state === undefined || value.state === null || typeof value.state === 'string')
    && (value.allowed_actions === undefined || isStringArray(value.allowed_actions));
}

function isTopologyEdge(value: unknown): boolean {
  if (!isRecord(value) || !hasOnlyKeys(
    value,
    new Set(['id', 'source', 'target', 'edge_type', 'label']),
  )) {
    return false;
  }
  return isNonEmptyString(value.id)
    && isNonEmptyString(value.source)
    && isNonEmptyString(value.target)
    && isNonEmptyString(value.edge_type)
    && (value.label === undefined || value.label === null || typeof value.label === 'string');
}

export function parseTopologySnapshot(value: unknown): TopologySnapshotInput {
  if (
    !isRecord(value)
    || !hasOnlyKeys(value, snapshotKeys)
    || !isNonEmptyString(value.view_id)
    || !isNonEmptyString(value.snapshot_id)
    || !isRevisionString(value.view_revision)
    || !isNonEmptyString(value.query_digest)
    || !isNonEmptyString(value.access_scope_digest)
    || !isNonEmptyString(value.projection_version)
    || !Array.isArray(value.nodes)
    || value.nodes.length > 1000
    || !value.nodes.every(isTopologyNode)
    || !Array.isArray(value.edges)
    || value.edges.length > 2000
    || !value.edges.every(isTopologyEdge)
    || !isNonEmptyString(value.opaque_cursor)
    || typeof value.truncated !== 'boolean'
    || (value.continuation !== null && !isNonEmptyString(value.continuation))
    || !isStringArray(value.allowed_actions)
  ) {
    throw new Error('拓扑响应不符合固定契约');
  }
  const nodeIds = value.nodes.map((node) => (node as Record<string, unknown>).id as string);
  const edgeIds = value.edges.map((edge) => (edge as Record<string, unknown>).id as string);
  const visibleNodes = new Set(nodeIds);
  if (
    visibleNodes.size !== nodeIds.length
    || new Set(edgeIds).size !== edgeIds.length
    || value.edges.some((edge) => {
      const record = edge as Record<string, unknown>;
      return !visibleNodes.has(record.source as string) || !visibleNodes.has(record.target as string);
    })
  ) {
    throw new Error('拓扑响应不符合固定契约');
  }
  return value as unknown as TopologySnapshotInput;
}

export function topologyRequestPath(
  taskId: string,
  mode: ViewMode,
  snapshotId: string | null = null,
): string {
  const query = new URLSearchParams({
    mode,
    node_limit: '1000',
    edge_limit: '2000',
  });
  if (snapshotId) query.set('snapshot_id', snapshotId);
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/topology?${query.toString()}`;
}

export class TopologyReadError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'TopologyReadError';
    this.status = status;
  }
}

export async function readTopologySnapshot(
  taskId: string,
  mode: ViewMode,
  snapshotId: string | null,
  signal: AbortSignal,
): Promise<TopologySnapshotInput> {
  let response: Response;
  try {
    response = await fetch(apiUrl(topologyRequestPath(taskId, mode, snapshotId)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new TopologyReadError(0, '无法连接拓扑服务');
  }
  if (!response.ok) throw new TopologyReadError(response.status, '拓扑请求未完成');

  const raw = await response.text();
  try {
    return parseTopologySnapshot(JSON.parse(raw));
  } catch (error) {
    if (error instanceof Error && error.message === '拓扑响应不符合固定契约') throw error;
    throw new Error('拓扑响应不符合固定契约');
  }
}

export type TopologySnapshotReader = typeof readTopologySnapshot;

const readerIdentities = new WeakMap<TopologySnapshotReader, number>();
let nextReaderIdentity = 1;

function readerIdentity(reader: TopologySnapshotReader): number {
  const existing = readerIdentities.get(reader);
  if (existing !== undefined) return existing;
  const assigned = nextReaderIdentity;
  nextReaderIdentity += 1;
  readerIdentities.set(reader, assigned);
  return assigned;
}

export interface TopologyContainerProps {
  readonly taskId: string;
  readonly mode: ViewMode;
  readonly snapshotId?: string | null;
  readonly layout?: LayoutPreference;
  readonly selection?: TopologySelection | null;
  readonly readSnapshot?: TopologySnapshotReader;
  readonly readLayout?: LayoutReader;
  readonly writeLayout?: LayoutWriter;
  readonly persistLayout?: boolean;
  readonly onSelect?: (selection: TopologySelection | null) => void;
  readonly onLayoutChange?: (layout: LayoutPreference) => void;
  readonly onCommandRequested?: (request: TopologyCommandRequest) => void;
  readonly onExpandRequested?: (request: TopologyExpandRequest) => void;
  readonly onSnapshotChange?: (snapshot: TopologySnapshotInput) => void;
}

interface TopologyContainerRequestProps extends Omit<
  TopologyContainerProps,
  'readSnapshot' | 'readLayout' | 'writeLayout'
> {
  readonly readSnapshot: TopologySnapshotReader;
  readonly readLayout: LayoutReader;
  readonly writeLayout: LayoutWriter;
}

function initialLayout(mode: ViewMode): LayoutPreference {
  return {
    schema_version: 'wuji.api.v2',
    view_name: layoutViewName(mode),
    layout_revision: '0',
    selection_mode: mode === 'history' ? 'explicit_revision' : 'follow_latest',
    entries: [],
    viewport: { x: 0, y: 0, zoom: 0.82 },
  };
}

function errorCopy(error: unknown): { title: string; description: string } {
  if (error instanceof TopologyReadError && error.status === 404) {
    return {
      title: '拓扑数据尚不可用',
      description: '当前任务没有可读取的受权拓扑快照。',
    };
  }
  if (error instanceof TopologyReadError && error.status === 410) {
    return {
      title: '历史拓扑不可用',
      description: '所选快照未保留或已过期，请返回可用快照列表。',
    };
  }
  if (error instanceof LayoutRequestError && error.status === 404) {
    return {
      title: '布局数据不可用',
      description: '当前任务或视图没有可读取的受权个人布局。',
    };
  }
  if (error instanceof Error && error.message === '拓扑响应不符合固定契约') {
    return {
      title: '拓扑响应无法确认',
      description: '平台响应与当前固定契约不一致，页面没有使用替代数据。',
    };
  }
  if (error instanceof Error && error.message === '布局响应不符合固定契约') {
    return {
      title: '布局响应无法确认',
      description: '平台响应与当前固定契约不一致，页面没有使用替代数据。',
    };
  }
  return {
    title: '拓扑读取失败',
    description: '当前页面没有取得可确认的拓扑快照。',
  };
}

function TopologyContainerRequest({
  taskId,
  mode,
  snapshotId = null,
  layout: controlledLayout,
  selection: controlledSelection,
  readSnapshot,
  readLayout,
  writeLayout,
  persistLayout = true,
  onSelect,
  onLayoutChange,
  onCommandRequested,
  onExpandRequested,
  onSnapshotChange,
}: TopologyContainerRequestProps) {
  const viewName = layoutViewName(mode);
  const canPersistLayout = persistLayout && controlledLayout === undefined;
  const [snapshot, setSnapshot] = useState<TopologySnapshotInput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [requestRevision, setRequestRevision] = useState(0);
  const [localLayout, setLocalLayout] = useState<LayoutPreference>(() => initialLayout(mode));
  const [layoutReady, setLayoutReady] = useState(!canPersistLayout);
  const [localSelection, setLocalSelection] = useState<TopologySelection | null>(null);
  const [interactionNotice, setInteractionNotice] = useState<string | null>(null);
  const [layoutNotice, setLayoutNotice] = useState<string | null>(null);
  const [pendingLayout, setPendingLayout] = useState<LayoutPreference | null>(null);
  const [savingLayout, setSavingLayout] = useState(false);
  const [layoutEpoch, setLayoutEpoch] = useState(0);
  const pendingRef = useRef<LayoutPreference | null>(null);
  // A 409 freezes the write queue until an explicit, successful reload: a
  // failed reload must never requeue the stale PUT, or the conflict re-fires
  // without any new user gesture.
  const layoutConflictRef = useRef(false);
  const reloadAbortRef = useRef(new AbortController());
  const [layoutConflict, setLayoutConflict] = useState(false);
  const [streamStatus, setStreamStatus] = useState<ViewStreamStatus>('closed');
  const snapshotRef = useRef<TopologySnapshotInput | null>(null);
  const savingRef = useRef(false);
  const activeRef = useRef(true);
  const saveAbortRef = useRef<AbortController | null>(null);
  // Last layout revision confirmed by the server. Layout objects computed from
  // an older revision are stale after a conflict and must never be written.
  const revisionRef = useRef<string | null>(null);
  const layout = controlledLayout ?? localLayout;
  const selection = controlledSelection === undefined ? localSelection : controlledSelection;

  useEffect(() => {
    activeRef.current = true;
    return () => {
      activeRef.current = false;
      saveAbortRef.current?.abort();
    };
  }, [taskId, mode, snapshotId, readLayout, writeLayout]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setLayoutNotice(null);
    setLayoutReady(!canPersistLayout);
    pendingRef.current = null;
    revisionRef.current = null;
    setPendingLayout(null);
    const snapshotPromise = readSnapshot(taskId, mode, snapshotId, controller.signal);
    const layoutPromise = canPersistLayout
      ? readLayout(taskId, viewName, controller.signal)
      : Promise.resolve(initialLayout(mode));
    void Promise.all([snapshotPromise, layoutPromise]).then(([next, nextLayout]) => {
      if (controller.signal.aborted) return;
      setSnapshot(next);
      setLocalLayout(nextLayout);
      revisionRef.current = nextLayout.layout_revision;
      setLayoutReady(true);
      onSnapshotChange?.(next);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      setError(reason);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [canPersistLayout, mode, onSnapshotChange, readLayout, readSnapshot, requestRevision, snapshotId, taskId, viewName]);

  useEffect(() => {
    snapshotRef.current = snapshot;
  }, [snapshot]);

  // A live view follows its own authorized change stream; anything the stream
  // cannot describe as one bounded patch batch falls back to an explicit
  // snapshot read instead of a partially patched graph.
  const activeViewId = snapshot?.view_id ?? null;

  useEffect(() => {
    if (!LIVE_VIEW_ENABLED || mode !== 'live' || activeViewId === null || loading) {
      setStreamStatus('closed');
      return undefined;
    }
    const viewId = activeViewId;
    return openViewStream(viewId, {
      onStatus: setStreamStatus,
      onEvent: (event) => {
        if (event.kind === 'reset') {
          setRequestRevision((value) => value + 1);
          return;
        }
        const current = snapshotRef.current;
        if (current === null || current.view_id !== viewId) return;
        const next = applyViewPatches(current, event.batch);
        if (next === null) {
          setRequestRevision((value) => value + 1);
          return;
        }
        snapshotRef.current = next;
        setSnapshot(next);
        onSnapshotChange?.(next);
      },
    });
  }, [activeViewId, loading, mode, onSnapshotChange]);

  const reloadLayout = useCallback(async () => {
    // Read-only recovery: take the server layout as the only truth, then allow
    // new edits again. Nothing here writes.
    try {
      const server = await readLayout(taskId, viewName, reloadAbortRef.current.signal);
      if (!activeRef.current || reloadAbortRef.current.signal.aborted) return;
      revisionRef.current = server.layout_revision;
      pendingRef.current = null;
      setPendingLayout(null);
      setLocalLayout(server);
      setLayoutEpoch((value) => value + 1);
      layoutConflictRef.current = false;
      setLayoutConflict(false);
      setLayoutNotice('服务器布局已更新，当前修改未覆盖它。');
    } catch (reloadError: unknown) {
      if (!activeRef.current) return;
      layoutConflictRef.current = true;
      setLayoutConflict(true);
      setLayoutNotice(
        reloadError instanceof Error
          ? reloadError.message
          : '布局冲突后无法重新读取服务器布局。',
      );
    }
  }, [readLayout, taskId, viewName]);

  const drainLayout = useCallback(async () => {
    if (layoutConflictRef.current) return;
    if (!canPersistLayout || !layoutReady || savingRef.current || !pendingRef.current) return;
    const requested = pendingRef.current;
    savingRef.current = true;
    setSavingLayout(true);
    const controller = new AbortController();
    saveAbortRef.current = controller;
    try {
      const receipt: LayoutReceipt = await writeLayout(
        taskId,
        viewName,
        layoutPatch(requested),
        requested.layout_revision,
        controller.signal,
      );
      if (!activeRef.current || controller.signal.aborted) return;
      // The local content stays the user's newest edit; only the confirmed
      // revision advances, so queued edits are rebased on the server's answer.
      revisionRef.current = receipt.layout_revision;
      setLocalLayout((current) => ({ ...current, layout_revision: receipt.layout_revision }));
      if (pendingRef.current === requested) {
        pendingRef.current = null;
        setPendingLayout(null);
      } else if (pendingRef.current !== null) {
        const rebased = { ...pendingRef.current, layout_revision: receipt.layout_revision };
        pendingRef.current = rebased;
        setPendingLayout(rebased);
      }
    } catch (reason: unknown) {
      if (!activeRef.current || controller.signal.aborted) return;
      if (reason instanceof LayoutRequestError && reason.status === 409) {
        // Freeze the queue before any I/O: the conflicting edit is dropped and
        // cannot be re-sent by the finally block or by a failed reload.
        layoutConflictRef.current = true;
        setLayoutConflict(true);
        pendingRef.current = null;
        setPendingLayout(null);
        if (!controller.signal.aborted) await reloadLayout();
      } else {
        pendingRef.current = null;
        setPendingLayout(null);
        setLayoutNotice(reason instanceof Error ? reason.message : '布局保存失败，当前修改尚未确认。');
      }
    } finally {
      if (saveAbortRef.current === controller) saveAbortRef.current = null;
      savingRef.current = false;
      if (activeRef.current && !controller.signal.aborted) setSavingLayout(false);
      if (activeRef.current && pendingRef.current !== null) void drainLayout();
    }
  }, [canPersistLayout, layoutReady, reloadLayout, taskId, viewName, writeLayout]);

  const handleLayoutChange = useCallback((next: LayoutPreference) => {
    // Unresolved conflict: only a successful reload may accept new edits.
    if (layoutConflictRef.current) return;
    // A change computed from a revision that the server already replaced is
    // dropped: the conflict reload owns the current layout.
    if (canPersistLayout && next.layout_revision !== revisionRef.current) return;
    if (!controlledLayout) setLocalLayout(next);
    onLayoutChange?.(next);
    if (!canPersistLayout || !layoutReady) return;
    pendingRef.current = next;
    setPendingLayout(next);
    setLayoutNotice(null);
    void drainLayout();
  }, [canPersistLayout, controlledLayout, drainLayout, layoutReady, onLayoutChange]);

  const copy = useMemo(() => errorCopy(error), [error]);
  if (loading && (!snapshot || !layoutReady)) {
    return (
      <div className={styles.containerStatus}>
        <Spin description={canPersistLayout ? '正在读取拓扑与个人布局' : '正在读取拓扑'} />
      </div>
    );
  }
  if (!snapshot) {
    return (
      <Alert
        showIcon
        type="warning"
        title={copy.title}
        description={copy.description}
        action={<Button onClick={() => setRequestRevision((value) => value + 1)}>重新读取</Button>}
      />
    );
  }

  return (
    <div className={styles.container}>
      {error !== null && (
        <Alert
          showIcon
          type="warning"
          title={copy.title}
          description="保留上一次确认的拓扑快照，可重新读取。"
          action={<Button onClick={() => setRequestRevision((value) => value + 1)}>重新读取</Button>}
        />
      )}
      {layoutNotice && (
        <Alert
          closable
          type={layoutConflict ? 'warning' : 'info'}
          title={layoutNotice}
          action={
            layoutConflict ? (
              <Button size="small" onClick={() => void reloadLayout()}>
                重新读取
              </Button>
            ) : null
          }
          onClose={() => setLayoutNotice(null)}
        />
      )}
      {mode === 'live' && !LIVE_VIEW_ENABLED && (
        <span
          className={styles.notice}
          role="status"
          data-stream-status="snapshot-only"
        >
          快照模式：实时订阅未启用，图为当前受权快照
          <Button
            size="small"
            style={{ marginLeft: 8 }}
            onClick={() => setRequestRevision((value) => value + 1)}
          >
            刷新快照
          </Button>
        </span>
      )}
      {mode === 'live' && LIVE_VIEW_ENABLED && (
        <span className={styles.notice} role="status" data-stream-status={streamStatus}>
          {streamStatus === 'live'
            ? '实时视图已连接'
            : streamStatus === 'connecting'
              ? '正在连接实时视图…'
              : streamStatus === 'retrying'
                ? '实时视图重连中…'
                : '实时视图已暂停'}
        </span>
      )}
      {savingLayout && <span className={styles.notice} role="status">正在保存个人布局…</span>}
      {pendingLayout && !savingLayout && <span className={styles.notice} role="status">个人布局等待保存</span>}
      {interactionNotice && (
        <Alert
          closable
          type="info"
          title={interactionNotice}
          onClose={() => setInteractionNotice(null)}
        />
      )}
      <TopologyFlowCanvas
        key={layoutEpoch}
        snapshot={snapshot}
        layout={layout}
        mode={mode}
        selection={selection}
        onSelect={(next) => {
          if (controlledSelection === undefined) setLocalSelection(next);
          onSelect?.(next);
        }}
        onLayoutChange={handleLayoutChange}
        onCommandRequested={(request) => {
          if (onCommandRequested) onCommandRequested(request);
          else setInteractionNotice('该领域操作尚未接入当前任务入口。');
        }}
        onExpandRequested={(request) => {
          if (onExpandRequested) onExpandRequested(request);
          else setInteractionNotice('当前查询尚未提供展开读取。');
        }}
      />
    </div>
  );
}

export function TopologyContainer(props: TopologyContainerProps) {
  const reader = props.readSnapshot ?? readTopologySnapshot;
  const readLayout = props.readLayout ?? readLayoutPreference;
  const writeLayout = props.writeLayout ?? writeLayoutPreference;
  const requestKey = JSON.stringify([
    props.taskId,
    props.mode,
    props.snapshotId ?? null,
    readerIdentity(reader),
    props.persistLayout !== false,
  ]);
  return (
    <TopologyContainerRequest
      {...props}
      key={requestKey}
      readSnapshot={reader}
      readLayout={readLayout}
      writeLayout={writeLayout}
    />
  );
}
