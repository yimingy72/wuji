import { apiUrl } from '../../config';
import type { TopologySnapshotInput } from './contracts';

export type ViewPatchOperation = 'upsert_node' | 'remove_node' | 'upsert_edge' | 'remove_edge';

export interface ViewPatch {
  readonly op: ViewPatchOperation;
  readonly value: Record<string, unknown>;
}

export interface ViewEventBatch {
  readonly schema_version: 'wuji.view-event.v3';
  readonly view_id: string;
  readonly snapshot_id: string;
  readonly base_view_revision: string;
  readonly view_revision: string;
  readonly cursor: string;
  readonly patches: readonly ViewPatch[];
}

export type ViewStreamEvent =
  | { readonly kind: 'view'; readonly batch: ViewEventBatch }
  | { readonly kind: 'reset'; readonly reason: string };

export type ViewStreamStatus = 'connecting' | 'live' | 'retrying' | 'closed';

const MAX_PATCHES = 2000;
const MAX_NODES = 1000;
const MAX_EDGES = 2000;
const OPERATIONS = new Set<ViewPatchOperation>([
  'upsert_node',
  'remove_node',
  'upsert_edge',
  'remove_edge',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isRevision(value: unknown): value is string {
  return typeof value === 'string' && /^(0|[1-9][0-9]*)$/.test(value);
}

export function viewStreamPath(viewId: string): string {
  return `/api/v2/views/${encodeURIComponent(viewId)}/events`;
}

export function parseViewStreamEvent(
  name: string,
  data: unknown,
  expectedViewId: string,
): ViewStreamEvent | null {
  if (name === 'reset') {
    if (!isRecord(data) || data.action !== 'resnapshot' || data.view_id !== expectedViewId) {
      return null;
    }
    return { kind: 'reset', reason: typeof data.reason === 'string' ? data.reason : 'resnapshot' };
  }
  if (name !== 'view') return null;
  if (
    !isRecord(data)
    || data.schema_version !== 'wuji.view-event.v3'
    || data.view_id !== expectedViewId
    || typeof data.snapshot_id !== 'string'
    || data.snapshot_id.length === 0
    || !isRevision(data.base_view_revision)
    || !isRevision(data.view_revision)
    || typeof data.cursor !== 'string'
    || data.cursor.length === 0
    || !Array.isArray(data.patches)
    || data.patches.length > MAX_PATCHES
  ) {
    return null;
  }
  const patches: ViewPatch[] = [];
  for (const item of data.patches) {
    if (!isRecord(item) || !OPERATIONS.has(item.op as ViewPatchOperation) || !isRecord(item.value)) {
      return null;
    }
    patches.push({ op: item.op as ViewPatchOperation, value: item.value });
  }
  return {
    kind: 'view',
    batch: {
      schema_version: 'wuji.view-event.v3',
      view_id: data.view_id as string,
      snapshot_id: data.snapshot_id as string,
      base_view_revision: data.base_view_revision as string,
      view_revision: data.view_revision as string,
      cursor: data.cursor,
      patches,
    },
  };
}

/**
 * Apply one bounded patch batch to the current snapshot.
 *
 * ``null`` means the batch cannot be applied without guessing (a different base
 * revision, an unknown shape, or a bound violation); the caller must refetch an
 * explicit snapshot instead of rendering a partially patched graph.
 */
export function applyViewPatches(
  snapshot: TopologySnapshotInput,
  batch: ViewEventBatch,
): TopologySnapshotInput | null {
  if (
    batch.view_id !== snapshot.view_id
    || batch.base_view_revision !== snapshot.view_revision
    || batch.snapshot_id.length === 0
  ) {
    return null;
  }
  const nodes = new Map(snapshot.nodes.map((node) => [node.id, node]));
  const edges = new Map(snapshot.edges.map((edge) => [edge.id, edge]));
  for (const patch of batch.patches) {
    const id = patch.value.id;
    if (typeof id !== 'string' || id.length === 0) return null;
    switch (patch.op) {
      case 'upsert_node': {
        if (typeof patch.value.ref !== 'object' || patch.value.ref === null) return null;
        nodes.set(id, patch.value as unknown as TopologySnapshotInput['nodes'][number]);
        break;
      }
      case 'remove_node':
        nodes.delete(id);
        break;
      case 'upsert_edge': {
        if (typeof patch.value.source !== 'string' || typeof patch.value.target !== 'string') {
          return null;
        }
        edges.set(id, patch.value as unknown as TopologySnapshotInput['edges'][number]);
        break;
      }
      case 'remove_edge':
        edges.delete(id);
        break;
      default:
        return null;
    }
  }
  // A removed endpoint can never leave a dangling edge on the canvas.
  for (const [id, edge] of edges) {
    if (!nodes.has(edge.source) || !nodes.has(edge.target)) edges.delete(id);
  }
  if (nodes.size > MAX_NODES || edges.size > MAX_EDGES) return null;
  return {
    ...snapshot,
    snapshot_id: batch.snapshot_id,
    view_revision: batch.view_revision,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
  };
}

export interface ViewStreamHandlers {
  readonly onEvent: (event: ViewStreamEvent) => void;
  readonly onStatus: (status: ViewStreamStatus) => void;
}

/**
 * Subscribe to one saved view. The browser reconnects on its own and replays the
 * last ``id:`` it saw, so a reconnect resumes instead of resyncing.
 */
export function openViewStream(viewId: string, handlers: ViewStreamHandlers): () => void {
  if (typeof EventSource === 'undefined') {
    handlers.onStatus('closed');
    return () => undefined;
  }
  const source = new EventSource(apiUrl(viewStreamPath(viewId)), { withCredentials: true });
  handlers.onStatus('connecting');
  const receive = (name: string) => (message: MessageEvent<string>) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(message.data) as unknown;
    } catch {
      handlers.onEvent({ kind: 'reset', reason: 'unreadable_event' });
      return;
    }
    const event = parseViewStreamEvent(name, parsed, viewId);
    if (event === null) {
      handlers.onEvent({ kind: 'reset', reason: 'unexpected_event_shape' });
      return;
    }
    handlers.onEvent(event);
  };
  source.addEventListener('view', receive('view'));
  source.addEventListener('reset', receive('reset'));
  source.addEventListener('open', () => handlers.onStatus('live'));
  source.addEventListener('error', () => {
    // EventSource retries by itself; a closed stream is reported honestly.
    handlers.onStatus(source.readyState === EventSource.CLOSED ? 'closed' : 'retrying');
  });
  return () => {
    source.close();
    handlers.onStatus('closed');
  };
}
