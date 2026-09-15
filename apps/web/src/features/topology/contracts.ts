import type { Viewport } from '@xyflow/react';
import type { components } from '../../../../../packages/contracts/src/v2/generated';

export type KnowledgeRef = components['schemas']['KnowledgeRef'];
export type LayoutAnchor = components['schemas']['LayoutAnchor'];
export type LayoutEntry = components['schemas']['LayoutEntry'];
export type NodeEntityType = components['schemas']['NodeEntityType'];
export type TopologyEdge = components['schemas']['TopologyEdge'];
export type TopologyNode = components['schemas']['TopologyNode'];
export type TopologySnapshot = components['schemas']['TopologySnapshot'];
export type RecordView = components['schemas']['RecordView'];
export type ViewMode = components['schemas']['ViewMode'];
export type ViewSelectionMode = components['schemas']['ViewSelectionMode'];

export interface LayoutPreference {
  readonly view_name: string;
  readonly layout_revision: string;
  readonly selection_mode: ViewSelectionMode;
  readonly entries: readonly LayoutEntry[];
  readonly viewport: Readonly<Viewport>;
}

export type TopologySnapshotInput = Readonly<
  Omit<TopologySnapshot, 'nodes' | 'edges' | 'allowed_actions'>
> & {
  readonly nodes: readonly Readonly<TopologyNode>[];
  readonly edges: readonly Readonly<TopologyEdge>[];
  readonly allowed_actions: readonly string[];
};

export type TopologySelection =
  | {
      readonly mode: 'explicit_revision';
      readonly ref: KnowledgeRef;
    }
  | {
      readonly mode: 'follow_latest';
      readonly anchor: LayoutAnchor;
    };

export interface TopologyCommandRequest {
  readonly action: string;
  readonly ref: KnowledgeRef;
}

export interface TopologyExpandRequest {
  readonly ref: KnowledgeRef;
}
