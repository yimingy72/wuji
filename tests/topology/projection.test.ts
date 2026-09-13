import { describe, expect, test } from 'vitest';
import {
  layoutEntryForNode,
  updateLayoutEntry,
} from '../../apps/web/src/features/topology/layout';
import {
  parseTopologySnapshot,
  topologyRequestPath,
} from '../../apps/web/src/features/topology/TopologyContainer';
import { toFlowElements } from '../../apps/web/src/features/topology/toFlowElements';
import { claimBeforeAssessment, layout, snapshot } from './fixtures';

describe('topology projection', () => {
  test('an assessment changes Claim display without creating a second identity', () => {
    const before = toFlowElements(claimBeforeAssessment, layout, null);
    const after = toFlowElements(snapshot, layout, null);

    expect(before.nodes.map((node) => node.id)).toEqual(after.nodes.map((node) => node.id));
    expect(after.nodes.filter((node) => node.id === 'claim:claim-1@1')).toHaveLength(1);
    expect(after.nodes.find((node) => node.id === 'claim:claim-1@1')?.data.displayKind).toBe('fact');
  });

  test('layout edits preserve exact business references and edge endpoints', () => {
    const positioned = toFlowElements(snapshot, layout, null);
    const automatic = toFlowElements(snapshot, { ...layout, entries: [] }, null);

    expect(automatic.nodes.map((node) => node.id)).toEqual(positioned.nodes.map((node) => node.id));
    expect(automatic.nodes.map((node) => node.data.ref)).toEqual(positioned.nodes.map((node) => node.data.ref));
    expect(automatic.edges.map(({ id, source, target }) => ({ id, source, target }))).toEqual([
      {
        id: 'edge:observation-claim-v1',
        source: 'observation:observation-1@1',
        target: 'claim:claim-1@1',
      },
      {
        id: 'edge:claim-v1-intent',
        source: 'claim:claim-1@1',
        target: 'intent:intent-1@4',
      },
    ]);
    expect(automatic.edges.some((edge) => edge.target === 'claim:claim-1@2')).toBe(false);
  });

  test('revision-specific positions override logical anchors and pinned anchors stay fixed', () => {
    const flow = toFlowElements(snapshot, layout, null);
    const revisionOne = flow.nodes.find((node) => node.id === 'claim:claim-1@1');
    const revisionTwo = flow.nodes.find((node) => node.id === 'claim:claim-1@2');

    expect(revisionOne?.position).toEqual({ x: 420, y: 160 });
    expect(revisionOne?.draggable).toBe(true);
    expect(revisionTwo?.position).toEqual({ x: 676, y: 312 });
    expect(revisionTwo?.draggable).toBe(false);
  });

  test('two revisions inheriting one logical anchor do not overlap', () => {
    const inheritedOnly = {
      ...layout,
      entries: layout.entries.filter((entry) => entry.anchor.revision == null),
    };
    const flow = toFlowElements(snapshot, inheritedOnly, null);
    const revisionOne = flow.nodes.find((node) => node.id === 'claim:claim-1@1')!;
    const revisionTwo = flow.nodes.find((node) => node.id === 'claim:claim-1@2')!;

    expect(
      Math.abs(revisionTwo.position.x - revisionOne.position.x) >= 224
      || Math.abs(revisionTwo.position.y - revisionOne.position.y) >= 120,
    ).toBe(true);
  });

  test('all specified entity types map to explicit visual node types and text states', () => {
    const flow = toFlowElements(snapshot, layout, null);

    expect(flow.nodes.map((node) => node.type)).toEqual([
      'origin',
      'goal',
      'observation',
      'artifact',
      'claim',
      'claim',
      'intent',
      'work_item',
      'agent_run',
      'verification',
      'completion_review',
      'finding',
      'report',
    ]);
    expect(flow.nodes.find((node) => node.id === 'claim:claim-1@1')?.data.state).toBe('supported');
  });

  test('automatic layout gives every visible node a distinct starting position', () => {
    const flow = toFlowElements(snapshot, { ...layout, entries: [] }, null);
    const positions = flow.nodes.map((node) => `${node.position.x}:${node.position.y}`);

    expect(new Set(positions).size).toBe(13);
  });

  test('explicit selection remains on its revision while follow-latest tracks the logical anchor', () => {
    const explicit = toFlowElements(snapshot, layout, {
      mode: 'explicit_revision',
      ref: { entity_type: 'claim', id: 'claim-1', revision: '1' },
    });
    const followLatest = toFlowElements(snapshot, layout, {
      mode: 'follow_latest',
      anchor: { entity_type: 'claim', id: 'claim-1' },
    });

    expect(explicit.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([
      'claim:claim-1@1',
    ]);
    expect(followLatest.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([
      'claim:claim-1@2',
    ]);
  });
});

describe('personal layout changes', () => {
  test('moving an unpinned node changes only its exact-revision entry', () => {
    const changed = updateLayoutEntry(
      layout,
      { entity_type: 'intent', id: 'intent-1', revision: '4' },
      { x: 812, y: 364 },
    );

    expect(changed).toEqual({
      ...layout,
      entries: [
        layout.entries[0],
        layout.entries[1],
        {
          anchor: { entity_type: 'intent', id: 'intent-1', revision: '4' },
          x: 812,
          y: 364,
          pinned: false,
        },
      ],
    });
    expect(changed.layout_revision).toBe('17');
    expect(changed.viewport).toEqual({ x: -92, y: 36, zoom: 0.84 });
  });

  test('a logical pinned entry is inherited by a new revision without being overwritten', () => {
    const inherited = layoutEntryForNode(
      layout,
      { entity_type: 'claim', id: 'claim-1', revision: '2' },
      1,
      2,
    );
    const unchanged = updateLayoutEntry(
      layout,
      { entity_type: 'claim', id: 'claim-1', revision: '2' },
      { x: 999, y: 999 },
    );

    expect(inherited).toEqual({ x: 676, y: 312, pinned: true });
    expect(unchanged).toBe(layout);
  });
});

describe('formal topology read boundary', () => {
  test('the request path fixes mode, exact snapshot, and public graph limits', () => {
    const url = new URL(
      topologyRequestPath('task / 17', 'history', 'snapshot / 9'),
      'https://wuji.invalid',
    );
    expect(url.pathname).toBe('/api/v2/tasks/task%20%2F%2017/topology');
    expect(Object.fromEntries(url.searchParams)).toEqual({
      mode: 'history',
      snapshot_id: 'snapshot / 9',
      node_limit: '1000',
      edge_limit: '2000',
    });
  });

  test('the response parser rejects a partial object instead of supplying fixture data', () => {
    expect(() => parseTopologySnapshot({
      view_id: 'view-incomplete',
      nodes: [],
      edges: [],
    })).toThrowError('拓扑响应不符合固定契约');
    expect(parseTopologySnapshot(structuredClone(snapshot)).snapshot_id).toBe('snapshot-current');
  });

  test('the response parser rejects mismatched identities and dangling edge endpoints', () => {
    const wrongIdentity = structuredClone(snapshot);
    wrongIdentity.nodes[0]!.id = 'origin:another-origin@1';
    const danglingEdge = structuredClone(snapshot);
    danglingEdge.edges[0]!.target = 'claim:missing@1';

    expect(() => parseTopologySnapshot(wrongIdentity)).toThrowError(
      '拓扑响应不符合固定契约',
    );
    expect(() => parseTopologySnapshot(danglingEdge)).toThrowError(
      '拓扑响应不符合固定契约',
    );
  });

  test('the response parser enforces non-empty identities and unique actions', () => {
    const emptyView = structuredClone(snapshot);
    emptyView.view_id = '';
    const duplicateAction = structuredClone(snapshot);
    duplicateAction.allowed_actions = ['inspect', 'inspect'];

    expect(() => parseTopologySnapshot(emptyView)).toThrowError(
      '拓扑响应不符合固定契约',
    );
    expect(() => parseTopologySnapshot(duplicateAction)).toThrowError(
      '拓扑响应不符合固定契约',
    );
  });
});
