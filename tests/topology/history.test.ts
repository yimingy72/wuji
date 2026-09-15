import { describe, expect, test } from 'vitest';
import {
  parseSnapshotIndex,
  snapshotHistoryRequestPath,
} from '../../apps/web/src/features/topology/history';

const summary = {
  snapshot_id: 'snapshot-1',
  view_id: 'view-1',
  view_revision: '1',
  created_at: '2026-09-15T02:56:30.110681Z',
  query_digest: 'a'.repeat(64),
  projection_version: 'wuji.topology.v1',
  query: {
    mode: 'live', snapshot_id: null, cursor: null, node_limit: 1000, edge_limit: 2000,
  },
};

describe('snapshot history boundary', () => {
  test('request path carries only the opaque directory cursor', () => {
    const url = new URL(
      snapshotHistoryRequestPath('task / 1', 'opaque / cursor'),
      'https://wuji.invalid',
    );
    expect(url.pathname).toBe('/api/v2/tasks/task%20%2F%201/snapshots');
    expect(Object.fromEntries(url.searchParams)).toEqual({ cursor: 'opaque / cursor' });
  });

  test('parser accepts the fixed public summary and rejects internal watermarks', () => {
    expect(parseSnapshotIndex({ items: [summary], opaque_cursor: null })).toEqual({
      items: [summary], opaque_cursor: null,
    });
    expect(() => parseSnapshotIndex({
      items: [{ ...summary, event_seq: '41' }], opaque_cursor: null,
    })).toThrow('快照目录响应不符合固定契约');
  });
});
