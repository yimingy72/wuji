import { apiUrl } from '../../config';
import { Alert, Button, Spin } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import type {
  KnowledgeRef,
  LayoutPreference,
  NodeEntityType,
  TopologyCommandRequest,
  TopologyExpandRequest,
  TopologySelection,
  TopologySnapshotInput,
  ViewMode,
} from './contracts';
import { TopologyFlowCanvas } from './TopologyFlowCanvas';
import { isRevisionString } from './revision';
import styles from './topology.module.css';

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
  readonly onSelect?: (selection: TopologySelection | null) => void;
  readonly onLayoutChange?: (layout: LayoutPreference) => void;
  readonly onCommandRequested?: (request: TopologyCommandRequest) => void;
  readonly onExpandRequested?: (request: TopologyExpandRequest) => void;
  readonly onSnapshotChange?: (snapshot: TopologySnapshotInput) => void;
}

interface TopologyContainerRequestProps extends Omit<TopologyContainerProps, 'readSnapshot'> {
  readonly readSnapshot: TopologySnapshotReader;
}

function initialLayout(mode: ViewMode): LayoutPreference {
  return {
    view_name: 'knowledge',
    layout_revision: 'local:0',
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
  if (error instanceof Error && error.message === '拓扑响应不符合固定契约') {
    return {
      title: '拓扑响应无法确认',
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
  onSelect,
  onLayoutChange,
  onCommandRequested,
  onExpandRequested,
  onSnapshotChange,
}: TopologyContainerRequestProps) {
  const [snapshot, setSnapshot] = useState<TopologySnapshotInput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [requestRevision, setRequestRevision] = useState(0);
  const [localLayout, setLocalLayout] = useState<LayoutPreference>(() => initialLayout(mode));
  const [localSelection, setLocalSelection] = useState<TopologySelection | null>(null);
  const [interactionNotice, setInteractionNotice] = useState<string | null>(null);
  const layout = controlledLayout ?? localLayout;
  const selection = controlledSelection === undefined ? localSelection : controlledSelection;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void readSnapshot(taskId, mode, snapshotId, controller.signal).then((next) => {
      if (controller.signal.aborted) return;
      setSnapshot(next);
      onSnapshotChange?.(next);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      setError(reason);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [mode, onSnapshotChange, readSnapshot, requestRevision, snapshotId, taskId]);

  const copy = useMemo(() => errorCopy(error), [error]);
  if (loading && !snapshot) {
    return <div className={styles.containerStatus}><Spin description="正在读取拓扑" /></div>;
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
      {interactionNotice && (
        <Alert
          closable
          type="info"
          title={interactionNotice}
          onClose={() => setInteractionNotice(null)}
        />
      )}
      <TopologyFlowCanvas
        snapshot={snapshot}
        layout={layout}
        mode={mode}
        selection={selection}
        onSelect={(next) => {
          if (controlledSelection === undefined) setLocalSelection(next);
          onSelect?.(next);
        }}
        onLayoutChange={(next) => {
          if (!controlledLayout) setLocalLayout(next);
          onLayoutChange?.(next);
        }}
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
  const requestKey = JSON.stringify([
    props.taskId,
    props.mode,
    props.snapshotId ?? null,
    readerIdentity(reader),
  ]);
  return <TopologyContainerRequest {...props} key={requestKey} readSnapshot={reader} />;
}
