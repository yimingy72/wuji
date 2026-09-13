import type { XYPosition } from '@xyflow/react';
import type {
  KnowledgeRef,
  LayoutEntry,
  LayoutPreference,
  NodeEntityType,
} from './contracts';

const revisionOffset = { x: 36, y: 132 } as const;

const columns: Readonly<Record<NodeEntityType, number>> = {
  origin: 0,
  goal: 0,
  observation: 1,
  artifact: 1,
  claim: 2,
  intent: 3,
  work_item: 3,
  agent_run: 4,
  verification: 4,
  completion_review: 5,
  finding: 5,
  report: 5,
};

const rowSlots: Readonly<Record<NodeEntityType, number>> = {
  origin: 0,
  goal: 1,
  observation: 0,
  artifact: 1,
  claim: 0,
  intent: 0,
  work_item: 1,
  agent_run: 0,
  verification: 1,
  completion_review: 0,
  finding: 1,
  report: 2,
};

const rowsPerColumn = [2, 2, 1, 2, 2, 3] as const;

function sameLogicalAnchor(entry: LayoutEntry, ref: KnowledgeRef): boolean {
  return entry.anchor.entity_type === ref.entity_type && entry.anchor.id === ref.id;
}

function sameExactAnchor(entry: LayoutEntry, ref: KnowledgeRef): boolean {
  return sameLogicalAnchor(entry, ref) && entry.anchor.revision === ref.revision;
}

function defaultPosition(
  ref: KnowledgeRef,
  revisionIndex: number,
  row: number,
): XYPosition {
  const column = columns[ref.entity_type];
  const rowStride = rowsPerColumn[column];
  if (rowStride === undefined) throw new Error('Unsupported topology layout column');
  return {
    x: 48 + column * 292 + revisionIndex * revisionOffset.x,
    y: 52
      + (rowSlots[ref.entity_type] + row * rowStride) * 148
      + revisionIndex * revisionOffset.y,
  };
}

export interface PositionedLayoutEntry extends XYPosition {
  readonly pinned: boolean;
}

export function layoutEntryForNode(
  layout: LayoutPreference,
  ref: KnowledgeRef,
  revisionIndex: number,
  logicalRow: number,
): PositionedLayoutEntry {
  const exact = layout.entries.find((entry) => sameExactAnchor(entry, ref));
  if (exact) return { x: exact.x, y: exact.y, pinned: exact.pinned };

  const logical = layout.entries.find(
    (entry) => sameLogicalAnchor(entry, ref) && entry.anchor.revision == null,
  );
  if (logical) {
    return {
      x: logical.x + revisionIndex * revisionOffset.x,
      y: logical.y + revisionIndex * revisionOffset.y,
      pinned: logical.pinned,
    };
  }

  return { ...defaultPosition(ref, revisionIndex, logicalRow), pinned: false };
}

export function updateLayoutEntry(
  layout: LayoutPreference,
  ref: KnowledgeRef,
  position: XYPosition,
): LayoutPreference {
  const exactIndex = layout.entries.findIndex((entry) => sameExactAnchor(entry, ref));
  const inherited = exactIndex >= 0
    ? layout.entries[exactIndex]
    : layout.entries.find(
        (entry) => sameLogicalAnchor(entry, ref) && entry.anchor.revision == null,
      );

  if (inherited?.pinned) return layout;

  const nextEntry: LayoutEntry = {
    anchor: { entity_type: ref.entity_type, id: ref.id, revision: ref.revision },
    x: position.x,
    y: position.y,
    pinned: false,
  };
  const entries = [...layout.entries];
  if (exactIndex >= 0) entries[exactIndex] = nextEntry;
  else entries.push(nextEntry);
  return { ...layout, entries };
}

export function updateLayoutViewport(
  layout: LayoutPreference,
  viewport: LayoutPreference['viewport'],
): LayoutPreference {
  if (
    layout.viewport.x === viewport.x
    && layout.viewport.y === viewport.y
    && layout.viewport.zoom === viewport.zoom
  ) {
    return layout;
  }
  return { ...layout, viewport: { ...viewport } };
}
