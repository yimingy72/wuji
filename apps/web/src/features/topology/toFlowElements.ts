import type { Edge, Node } from '@xyflow/react';
import type {
  KnowledgeRef,
  LayoutPreference,
  NodeEntityType,
  TopologySelection,
  TopologySnapshotInput,
} from './contracts';
import { layoutEntryForNode } from './layout';
import { compareRevisionStrings } from './revision';

export interface TopologyNodeData extends Record<string, unknown> {
  readonly ref: KnowledgeRef;
  readonly displayKind: string;
  readonly label: string;
  readonly state: string | null;
  readonly allowedActions: readonly string[];
}

export interface TopologyEdgeData extends Record<string, unknown> {
  readonly edgeType: string;
  readonly label: string | null;
}

export type TopologyFlowNode = Node<TopologyNodeData, NodeEntityType>;
export type TopologyFlowEdge = Edge<TopologyEdgeData>;

function logicalKey(ref: KnowledgeRef): string {
  return `${ref.entity_type}:${ref.id}`;
}

function exactKey(ref: KnowledgeRef): string {
  return `${logicalKey(ref)}@${ref.revision}`;
}

export function resolveSelectedNodeId(
  snapshot: TopologySnapshotInput,
  selection: TopologySelection | null,
): string | null {
  if (!selection) return null;
  if (selection.mode === 'explicit_revision') return exactKey(selection.ref);

  let latest: TopologySnapshotInput['nodes'][number] | null = null;
  for (const node of snapshot.nodes) {
    if (
      node.ref.entity_type !== selection.anchor.entity_type
      || node.ref.id !== selection.anchor.id
    ) {
      continue;
    }
    if (latest === null || compareRevisionStrings(node.ref.revision, latest.ref.revision) > 0) {
      latest = node;
    }
  }
  return latest?.id ?? null;
}

export function toFlowElements(
  snapshot: TopologySnapshotInput,
  layout: LayoutPreference,
  selection: TopologySelection | null,
): { readonly nodes: TopologyFlowNode[]; readonly edges: TopologyFlowEdge[] } {
  const selectedId = resolveSelectedNodeId(snapshot, selection);
  const revisionIndexes = new Map<string, number>();
  const logicalRows = new Map<NodeEntityType, number>();

  const nodes = snapshot.nodes.map<TopologyFlowNode>((node) => {
    const key = logicalKey(node.ref);
    const revisionIndex = revisionIndexes.get(key) ?? 0;
    revisionIndexes.set(key, revisionIndex + 1);
    const logicalRow = logicalRows.get(node.ref.entity_type) ?? 0;
    if (revisionIndex === 0) logicalRows.set(node.ref.entity_type, logicalRow + 1);
    const positioned = layoutEntryForNode(layout, node.ref, revisionIndex, logicalRow);

    return {
      id: node.id,
      type: node.ref.entity_type,
      position: { x: positioned.x, y: positioned.y },
      draggable: !positioned.pinned,
      selected: node.id === selectedId,
      data: {
        ref: { ...node.ref },
        displayKind: node.display_kind,
        label: node.label,
        state: node.state ?? null,
        allowedActions: [...(node.allowed_actions ?? [])],
      },
    };
  });

  const edges = snapshot.edges.map<TopologyFlowEdge>((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label ?? undefined,
    type: 'smoothstep',
    focusable: true,
    selectable: true,
    data: {
      edgeType: edge.edge_type,
      label: edge.label ?? null,
    },
  }));

  return { nodes, edges };
}
