import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  applyNodeChanges,
  type NodeProps,
  type NodeTypes,
  type Viewport,
} from '@xyflow/react';
import { Segmented } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import '@xyflow/react/dist/style.css';
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
import { updateLayoutEntry, updateLayoutViewport } from './layout';
import { TopologyListView } from './TopologyListView';
import {
  toFlowElements,
  type TopologyFlowNode,
  type TopologyNodeData,
} from './toFlowElements';
import styles from './topology.module.css';

interface RenderNodeData extends TopologyNodeData {
  readonly mode: ViewMode;
  readonly activate: (ref: KnowledgeRef) => void;
  readonly command: (request: TopologyCommandRequest) => void;
  readonly expand: (request: TopologyExpandRequest) => void;
}

type RenderNode = TopologyFlowNode & { data: RenderNodeData };

const kindLabels: Readonly<Record<NodeEntityType, string>> = {
  origin: 'Origin',
  goal: 'Goal',
  observation: 'Observation',
  artifact: 'Artifact',
  claim: 'Claim',
  intent: 'Intent',
  work_item: 'WorkItem',
  agent_run: 'AgentRun',
  verification: 'VerificationRun',
  completion_review: 'CompletionReview',
  finding: 'Finding',
  report: 'Report',
};

function TopologyNodeCard({ data, selected }: NodeProps<RenderNode>) {
  const displayLabel = data.displayKind === 'fact'
    ? 'Fact'
    : kindLabels[data.ref.entity_type];
  const actions = data.mode === 'history' ? [] : data.allowedActions;

  return (
    <article className={styles.nodeCard} data-display-kind={data.displayKind}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <button
        type="button"
        className={styles.nodeSelect}
        aria-pressed={selected}
        aria-label={`${displayLabel} · ${data.label}`}
        onClick={() => data.activate(data.ref)}
      >
        <span className={styles.kind}>{displayLabel}</span>
        <strong>{data.label}</strong>
        <span className={styles.state}>{data.state ?? '未标注状态'}</span>
        <code>{data.ref.entity_type}:{data.ref.id}@{data.ref.revision}</code>
      </button>
      {actions.length > 0 && (
        <div className={`${styles.nodeActions} nodrag`}>
          {actions.includes('expand') && (
            <button type="button" onClick={() => data.expand({ ref: { ...data.ref } })}>
              展开关联
            </button>
          )}
          {actions.filter((action) => action !== 'expand' && action !== 'inspect').map((action) => (
            <button
              type="button"
              key={action}
              onClick={() => data.command({ action, ref: { ...data.ref } })}
            >执行 {action}</button>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </article>
  );
}

const nodeTypes: NodeTypes = {
  origin: TopologyNodeCard,
  goal: TopologyNodeCard,
  observation: TopologyNodeCard,
  artifact: TopologyNodeCard,
  claim: TopologyNodeCard,
  intent: TopologyNodeCard,
  work_item: TopologyNodeCard,
  agent_run: TopologyNodeCard,
  verification: TopologyNodeCard,
  completion_review: TopologyNodeCard,
  finding: TopologyNodeCard,
  report: TopologyNodeCard,
};

export interface TopologyFlowCanvasProps {
  readonly snapshot: TopologySnapshotInput;
  readonly layout: LayoutPreference;
  readonly mode: ViewMode;
  readonly selection: TopologySelection | null;
  readonly onSelect: (selection: TopologySelection | null) => void;
  readonly onLayoutChange: (layout: LayoutPreference) => void;
  readonly onCommandRequested: (request: TopologyCommandRequest) => void;
  readonly onExpandRequested: (request: TopologyExpandRequest) => void;
}

export function TopologyFlowCanvas({
  snapshot,
  layout,
  mode,
  selection,
  onSelect,
  onLayoutChange,
  onCommandRequested,
  onExpandRequested,
}: TopologyFlowCanvasProps) {
  const [presentation, setPresentation] = useState<'canvas' | 'list'>('canvas');
  const [viewport, setViewport] = useState<Viewport>(() => ({ ...layout.viewport }));
  const activate = useCallback((ref: KnowledgeRef) => {
    onSelect(layout.selection_mode === 'follow_latest'
      ? { mode: 'follow_latest', anchor: { entity_type: ref.entity_type, id: ref.id } }
      : { mode: 'explicit_revision', ref: { ...ref } });
  }, [layout.selection_mode, onSelect]);
  const mapped = useMemo(
    () => toFlowElements(snapshot, layout, selection),
    [layout, selection, snapshot],
  );
  const rendered = useMemo<RenderNode[]>(() => mapped.nodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      mode,
      activate,
      command: onCommandRequested,
      expand: onExpandRequested,
    },
  })), [activate, mapped.nodes, mode, onCommandRequested, onExpandRequested]);
  const [nodes, setNodes] = useState<RenderNode[]>(rendered);

  useEffect(() => setNodes(rendered), [rendered]);
  useEffect(() => setViewport({ ...layout.viewport }), [layout.viewport]);

  const moveFinished = useCallback((_event: MouseEvent | TouchEvent | null, next: Viewport) => {
    setViewport(next);
    const changed = updateLayoutViewport(layout, next);
    if (changed !== layout) onLayoutChange(changed);
  }, [layout, onLayoutChange]);

  return (
    <section className={styles.topology} aria-label="任务拓扑">
      <header className={styles.toolbar}>
        <div>
          <strong>拓扑视图</strong>
          <span>快照 {snapshot.snapshot_id} · 视图修订 {snapshot.view_revision}</span>
        </div>
        <Segmented
          aria-label="拓扑呈现方式"
          value={presentation}
          onChange={setPresentation}
          options={[
            { label: '画布', value: 'canvas' },
            { label: '列表', value: 'list' },
          ]}
        />
      </header>
      {snapshot.truncated && (
        <p className={styles.notice} role="status">
          当前显示受权范围内的截断视图，可继续读取后续内容。
        </p>
      )}
      {presentation === 'list' ? (
        <TopologyListView
          snapshot={snapshot}
          layout={layout}
          mode={mode}
          selection={selection}
          onSelect={onSelect}
          onCommandRequested={onCommandRequested}
          onExpandRequested={onExpandRequested}
        />
      ) : (
        <div className={styles.canvas} role="region" aria-label="任务拓扑图">
          <ReactFlow
            nodes={nodes}
            edges={mapped.edges}
            nodeTypes={nodeTypes}
            viewport={viewport}
            onViewportChange={setViewport}
            onMoveEnd={moveFinished}
            onNodesChange={(changes) => setNodes((current) => applyNodeChanges(
              changes.filter((change) => change.type !== 'remove' && change.type !== 'select'),
              current,
            ) as RenderNode[])}
            onNodeDragStop={(_event, node) => {
              const changed = updateLayoutEntry(layout, node.data.ref, node.position);
              if (changed !== layout) onLayoutChange(changed);
            }}
            onPaneClick={() => onSelect(null)}
            nodesConnectable={false}
            edgesReconnectable={false}
            connectOnClick={false}
            deleteKeyCode={null}
            selectionKeyCode={null}
            multiSelectionKeyCode={null}
            selectionOnDrag={false}
            elevateNodesOnSelect={false}
            minZoom={0.2}
            maxZoom={2}
          >
            <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
    </section>
  );
}
