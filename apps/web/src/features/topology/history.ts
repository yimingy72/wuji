import type { SnapshotIndex, SnapshotSummary } from './contracts';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSummary(value: unknown): value is SnapshotSummary {
  if (!isRecord(value)) return false;
  const required = [
    'snapshot_id', 'view_id', 'view_revision', 'created_at',
    'query_digest', 'projection_version',
  ];
  const allowed = new Set([...required, 'query']);
  if (
    Object.keys(value).some((key) => !allowed.has(key))
    || !required.every((key) => typeof value[key] === 'string' && value[key] !== '')
  ) return false;
  if (value.query === undefined || value.query === null) return true;
  if (!isRecord(value.query)) return false;
  const queryKeys = ['mode', 'snapshot_id', 'cursor', 'node_limit', 'edge_limit'];
  return Object.keys(value.query).length === queryKeys.length
    && queryKeys.every((key) => Object.prototype.hasOwnProperty.call(value.query, key))
    && (value.query.mode === 'live' || value.query.mode === 'history')
    && (value.query.snapshot_id === null || typeof value.query.snapshot_id === 'string')
    && (value.query.cursor === null || typeof value.query.cursor === 'string')
    && Number.isInteger(value.query.node_limit)
    && Number.isInteger(value.query.edge_limit);
}

export function parseSnapshotIndex(value: unknown): SnapshotIndex {
  if (
    !isRecord(value)
    || Object.keys(value).some((key) => !['items', 'opaque_cursor'].includes(key))
    || !Array.isArray(value.items)
    || !value.items.every(isSummary)
    || !(value.opaque_cursor === null || typeof value.opaque_cursor === 'string')
  ) {
    throw new Error('快照目录响应不符合固定契约');
  }
  return value as unknown as SnapshotIndex;
}

export function snapshotHistoryRequestPath(
  taskId: string,
  cursor: string | null = null,
): string {
  const query = new URLSearchParams();
  if (cursor) query.set('cursor', cursor);
  const suffix = query.size ? `?${query.toString()}` : '';
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/snapshots${suffix}`;
}
