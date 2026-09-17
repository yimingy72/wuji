import { describe, expect, test } from 'vitest';
import {
  applyViewPatches,
  parseViewStreamEvent,
  viewStreamPath,
  type ViewEventBatch,
} from '../../apps/web/src/features/topology/stream';
import type { TopologySnapshotInput } from '../../apps/web/src/features/topology/contracts';

const snapshot = {
  view_id: 'view-1',
  snapshot_id: 'snapshot-1',
  view_revision: '1',
  query_digest: 'a'.repeat(64),
  access_scope_digest: 'b'.repeat(64),
  projection_version: 'wuji.topology.v1',
  nodes: [
    {
      id: 'claim:c1@1',
      ref: { entity_type: 'claim', id: 'c1', revision: '1' },
      display_kind: 'claim',
      label: 'first revision',
      state: 'unassessed',
      allowed_actions: [],
    },
  ],
  edges: [
    { id: 'e1', source: 'claim:c1@1', target: 'claim:c1@1', edge_type: 'supports' },
  ],
  opaque_cursor: 'page-cursor',
  truncated: false,
  continuation: null,
  allowed_actions: [],
} as unknown as TopologySnapshotInput;

const batch = {
  schema_version: 'wuji.view-event.v2',
  view_id: 'view-1',
  base_view_revision: '1',
  view_revision: '2',
  cursor: 'c'.repeat(43),
  patches: [
    {
      op: 'upsert_node',
      value: {
        id: 'claim:c1@2',
        ref: { entity_type: 'claim', id: 'c1', revision: '2' },
        display_kind: 'claim',
        label: 'second revision',
        state: 'unassessed',
        allowed_actions: [],
      },
    },
    { op: 'remove_node', value: { id: 'claim:c1@1' } },
    { op: 'remove_edge', value: { id: 'e1' } },
  ],
} as unknown as ViewEventBatch;

describe('view stream boundary', () => {
  test('the stream path carries only the opaque view id', () => {
    expect(viewStreamPath('view/1')).toBe('/api/v2/views/view%2F1/events');
  });

  test('a batch is accepted only for this view and shape', () => {
    const event = parseViewStreamEvent('view', batch, 'view-1');
    expect(event).not.toBeNull();
    expect(event?.kind).toBe('view');

    expect(parseViewStreamEvent('view', batch, 'view-2')).toBeNull();
    expect(parseViewStreamEvent('view', { ...batch, base_view_revision: 'x' }, 'view-1')).toBeNull();
    expect(
      parseViewStreamEvent('view', { ...batch, patches: [{ op: 'upsert_node', value: {} }] }, 'view-1'),
    ).not.toBeNull();
    expect(
      parseViewStreamEvent('view', { ...batch, patches: [{ op: 'merge_node', value: {} }] }, 'view-1'),
    ).toBeNull();
    expect(
      parseViewStreamEvent('reset', { action: 'resnapshot', view_id: 'view-1', reason: 'view_expired' }, 'view-1'),
    ).toEqual({ kind: 'reset', reason: 'view_expired' });
    expect(
      parseViewStreamEvent('reset', { action: 'resnapshot', view_id: 'view-2', reason: 'x' }, 'view-1'),
    ).toBeNull();
  });

  test('patches apply onto the same revision and advance it', () => {
    const next = applyViewPatches(snapshot, batch);
    expect(next).not.toBeNull();
    expect(next?.view_revision).toBe('2');
    expect(next?.nodes.map((node) => node.id)).toEqual(['claim:c1@2']);
    expect(next?.edges).toEqual([]);
    // The page cursor belongs to the old snapshot and is not reused.
    expect(next?.opaque_cursor).toBe('page-cursor');
  });

  test('a stale or unapplicable batch is refused instead of guessed', () => {
    expect(applyViewPatches(snapshot, { ...batch, base_view_revision: '9' })).toBeNull();
    expect(applyViewPatches(snapshot, { ...batch, view_id: 'view-9' })).toBeNull();
    expect(
      applyViewPatches(snapshot, {
        ...batch,
        patches: [{ op: 'upsert_node', value: { id: 'node-x' } }],
      } as unknown as ViewEventBatch),
    ).toBeNull();
    expect(
      applyViewPatches(snapshot, {
        ...batch,
        patches: [{ op: 'remove_node', value: {} }],
      } as unknown as ViewEventBatch),
    ).toBeNull();
  });
});
