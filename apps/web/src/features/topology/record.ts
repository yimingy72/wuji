import type {
  KnowledgeRef,
  RecordView,
  TopologySelection,
  TopologySnapshotInput,
} from './contracts';
import { resolveSelectedNodeId } from './toFlowElements';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isRef(value: unknown): value is KnowledgeRef {
  return isRecord(value)
    && typeof value.entity_type === 'string'
    && typeof value.id === 'string'
    && typeof value.revision === 'string';
}

function sameRef(left: KnowledgeRef, right: KnowledgeRef): boolean {
  return left.entity_type === right.entity_type
    && left.id === right.id
    && left.revision === right.revision;
}

export function selectedRecordRef(
  snapshot: TopologySnapshotInput | null,
  selection: TopologySelection | null,
): KnowledgeRef | null {
  if (!snapshot || !selection) return null;
  const selectedId = resolveSelectedNodeId(snapshot, selection);
  const node = selectedId
    ? snapshot.nodes.find((candidate) => candidate.id === selectedId)
    : undefined;
  return node ? { ...node.ref } : null;
}

export function recordRequestPath(
  taskId: string,
  ref: KnowledgeRef,
  snapshotId: string,
): string {
  const query = new URLSearchParams({
    revision: ref.revision,
    snapshot_id: snapshotId,
  });
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/records/`
    + `${encodeURIComponent(ref.entity_type)}/${encodeURIComponent(ref.id)}?${query.toString()}`;
}

export function parseRecordView(value: unknown, expectedRef: KnowledgeRef): RecordView {
  if (!isRecord(value)) throw new Error('记录响应不符合固定契约');
  const keys = new Set(Object.keys(value));
  if (
    !['ref', 'display_kind', 'record'].every((key) => keys.has(key))
    || [...keys].some((key) => !['assessment', 'ref', 'display_kind', 'record'].includes(key))
    || !isRef(value.ref)
    || !sameRef(value.ref, expectedRef)
    || typeof value.display_kind !== 'string'
    || value.display_kind.length === 0
    || !isRecord(value.record)
    || (value.assessment !== undefined && value.assessment !== null && !isRecord(value.assessment))
  ) {
    throw new Error('记录响应不符合固定契约');
  }
  return value as unknown as RecordView;
}
